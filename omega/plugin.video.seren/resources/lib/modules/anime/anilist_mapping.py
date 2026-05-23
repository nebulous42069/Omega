"""Anime ID Mapping — bridges Seren's TMDB/IMDB/Trakt IDs to all anime database IDs.

Primary source:  Otaku-Mappings offline SQLite DB (downloaded from GitHub, ~all anime).
Fallback 1:      arm.haglund.dev API (same service Otaku and other anime addons use).
Fallback 2:      AniList reverse search (title → AniList ID → cross-reference via ARM).
Fallback 3:      Simkl API (public, client_id only — no user auth required).

The Otaku-Mappings DB (github.com/Goldenfreddy0703/Otaku-Mappings) provides instant
offline lookups by any ID type including trakt_id. It contains:
  mal_id, anilist_id, kitsu_id, anidb_id, simkl_id, thetvdb_id, themoviedb_id,
  imdb_id, trakt_id, plus thetvdb_season, thetvdb_part, duration, score, status.

Maps between: anilist, mal, thetvdb, themoviedb, imdb, anidb, kitsu, simkl, trakt.

Results are cached in SQLite (anime_id_map table in animeCache.db) with 30-day TTL,
surviving across sessions.  A fast module-level dict provides L1 cache within the
current session to avoid repeated DB reads.
"""

import os

import requests

from resources.lib.modules.globals import g

# L1 session cache: {cache_key: {anilist_id, mal_id, anidb_id, kitsu_id, ...}}
# Backed by SQLite L2 cache in AnimeCache.anime_id_map (30-day TTL).
_id_cache = {}

# Simkl public API — only needs client_id, no user authentication
_SIMKL_CLIENT_ID = '59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8'
_SIMKL_BASE = 'https://api.simkl.com'

# Otaku-Mappings DB download URL
_MAPPING_DB_URL = 'https://github.com/Goldenfreddy0703/Otaku-Mappings/raw/refs/heads/main/anime_mappings.db'

# AniList GraphQL endpoint
_ANILIST_URL = 'https://graphql.anilist.co'


def get_anime_ids(imdb_id=None, tmdb_id=None, trakt_id=None):
    """Map IMDB, TMDB, or Trakt ID to all anime database IDs.

    Args:
        imdb_id: IMDB ID string (e.g. "tt5370118")
        tmdb_id: TMDB ID int or string
        trakt_id: Trakt show ID int or string

    Returns:
        dict with keys: anilist_id, mal_id, anidb_id, kitsu_id, thetvdb_id,
        themoviedb_id, simkl_id.  Any value may be None if unmapped.
        Returns None entirely if no mapping found at all.
    """
    if imdb_id:
        cache_key = imdb_id
    elif tmdb_id:
        cache_key = f"tmdb_{tmdb_id}"
    elif trakt_id:
        cache_key = f"trakt_{trakt_id}"
    else:
        return None

    # ── L1: session dict ─────────────────────────────────────────────────
    if cache_key in _id_cache:
        return _id_cache[cache_key]

    # ── L2: SQLite persistent cache (30-day TTL) ─────────────────────────
    result = _get_from_sqlite(cache_key)
    if result:
        _id_cache[cache_key] = result
        return result

    result = None

    # ── Stage 0: Otaku-Mappings local DB (instant, offline) ──────────────
    result = _query_mapping_db(imdb_id=imdb_id, tmdb_id=tmdb_id, trakt_id=trakt_id)
    if result:
        g.log(
            f"Anime ID mapping (Otaku-Mappings DB): "
            f"MAL={result.get('mal_id')}, AniDB={result.get('anidb_id')}, "
            f"Simkl={result.get('simkl_id')}, Kitsu={result.get('kitsu_id')}",
            "debug"
        )

    # ── Stage 1: ARM API fallback (if DB missed or incomplete) ───────────
    if not result:
        if imdb_id:
            result = _query_arm(imdb_id, "imdb")
        if not result and tmdb_id:
            result = _query_arm(str(tmdb_id), "tmdb")

    # ── Stage 2: AniList reverse search (title → AniList ID) ────────────
    if not result:
        result = _anilist_reverse_search(imdb_id=imdb_id, tmdb_id=tmdb_id)

    # ── Stage 3: Simkl fallback for missing AniDB ────────────────────────
    if result and not result.get('anidb_id'):
        anidb_from_simkl = _simkl_get_anidb(
            mal_id=result.get('mal_id'),
            anilist_id=result.get('anilist_id'),
            imdb_id=imdb_id,
            tmdb_id=tmdb_id
        )
        if anidb_from_simkl:
            result.update(anidb_from_simkl)

    # ── Stage 4: Full Simkl fallback if everything else returned nothing ─
    if not result:
        result = _simkl_full_lookup(imdb_id=imdb_id, tmdb_id=tmdb_id)

    # ── Persist to both caches ───────────────────────────────────────────
    _id_cache[cache_key] = result
    if result:
        _save_to_sqlite(cache_key, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  SQLite Persistent Cache (L2) — via AnimeCache
# ═══════════════════════════════════════════════════════════════════════════

def _get_from_sqlite(cache_key):
    """Read cached ID mapping from SQLite.  Returns dict or None."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        row = AnimeCache().get_id_map(cache_key)
        if row and (row.get('anilist_id') or row.get('mal_id')):
            g.log(f"Anime ID mapping (SQLite cache hit): key={cache_key}", "debug")
            return row
    except Exception as e:
        g.log(f"Anime ID SQLite read failed: {e}", "debug")
    return None


def _save_to_sqlite(cache_key, ids):
    """Persist ID mapping to SQLite cache."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().set_id_map(cache_key, ids)
    except Exception as e:
        g.log(f"Anime ID SQLite write failed: {e}", "debug")


# ═══════════════════════════════════════════════════════════════════════════
#  Otaku-Mappings offline DB (github.com/Goldenfreddy0703/Otaku-Mappings)
# ═══════════════════════════════════════════════════════════════════════════

def _query_mapping_db(imdb_id=None, tmdb_id=None, trakt_id=None):
    """Query the local Otaku-Mappings SQLite DB for anime ID mappings.

    Tries trakt_id first (most direct for Seren), then imdb_id, then tmdb_id.
    Returns full ID dict or None.
    """
    db_path = g.ANIME_MAPPING_DB_PATH
    if not os.path.exists(db_path):
        return None

    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=3)
        conn.row_factory = sqlite3.Row

        try:
            row = None
            if trakt_id:
                try:
                    row = conn.execute(
                        "SELECT * FROM anime WHERE trakt_id=?", (int(trakt_id),)
                    ).fetchone()
                except (ValueError, TypeError):
                    pass
            if not row and imdb_id:
                row = conn.execute(
                    "SELECT * FROM anime WHERE imdb_id=?", (str(imdb_id),)
                ).fetchone()
            if not row and tmdb_id:
                try:
                    row = conn.execute(
                        "SELECT * FROM anime WHERE themoviedb_id=?", (int(tmdb_id),)
                    ).fetchone()
                except (ValueError, TypeError):
                    pass
        finally:
            conn.close()

        if not row:
            return None

        return {
            "anilist_id":     row["anilist_id"],
            "mal_id":         row["mal_id"],
            "anidb_id":       row["anidb_id"],
            "kitsu_id":       row["kitsu_id"],
            "simkl_id":       row["simkl_id"],
            "thetvdb_id":     row["thetvdb_id"],
            "themoviedb_id":  row["themoviedb_id"],
            "thetvdb_season": row["thetvdb_season"] if "thetvdb_season" in row.keys() else None,
            "thetvdb_part":   row["thetvdb_part"] if "thetvdb_part" in row.keys() else None,
        }

    except Exception as e:
        g.log(f"Otaku-Mappings DB query failed: {e}", "debug")
        return None


def update_mapping_db():
    """Download or update the Otaku-Mappings DB from GitHub.

    Called from service.py at startup and periodically.  Same pattern as Otaku's service.py.
    Skips download if the DB was updated within the last 7 days.
    """
    import time
    db_path = g.ANIME_MAPPING_DB_PATH

    # Skip if recently updated (within 7 days)
    if os.path.exists(db_path):
        age_days = (time.time() - os.path.getmtime(db_path)) / 86400
        if age_days < 7:
            g.log(f"Anime mappings DB is {age_days:.1f} days old, skipping update", "debug")
            return True

    g.log("Updating Otaku-Mappings anime database...", "info")
    try:
        import urllib.request
        import tempfile
        # Download to temp file first, then rename atomically to avoid corruption
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(db_path), suffix='.tmp')
        os.close(temp_fd)
        try:
            urllib.request.urlretrieve(_MAPPING_DB_URL, temp_path)
            # Verify it's a valid SQLite file
            import sqlite3
            conn = sqlite3.connect(temp_path)
            conn.execute("SELECT count(*) FROM anime")
            conn.close()
            # Atomic replace
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rename(temp_path, db_path)
            g.log("Otaku-Mappings DB updated successfully", "info")
            return True
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
    except Exception as e:
        g.log(f"Failed to update Otaku-Mappings DB: {e}", "warning")
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  ARM API (arm.haglund.dev)
# ═══════════════════════════════════════════════════════════════════════════

def _query_arm(external_id, source):
    """Query arm.haglund.dev to map external IDs to all anime database IDs.

    Returns:
        dict with all available ID fields, or None.
    """
    url_map = {
        "imdb":     f"https://arm.haglund.dev/api/v2/imdb?id={external_id}",
        "tmdb":     f"https://arm.haglund.dev/api/v2/themoviedb?id={external_id}",
        "thetvdb":  f"https://arm.haglund.dev/api/v2/thetvdb?id={external_id}",
    }
    url = url_map.get(source)
    if not url:
        return None

    try:
        response = requests.get(url, timeout=5, headers={"User-Agent": "Seren"})
        if not response.ok:
            return None

        data = response.json()
        if not data:
            return None

        # ARM API returns a list when multiple anime map to the same external ID
        # (e.g. multi-season shows).  Take the first entry (typically best match).
        if isinstance(data, list):
            data = data[0] if data else None
            if not data:
                return None

        result = _extract_arm_ids(data)
        if not result:
            return None

        g.log(
            f"Anime ID mapping (ARM): {source}={external_id} → "
            f"AniList={result.get('anilist_id')}, MAL={result.get('mal_id')}, "
            f"AniDB={result.get('anidb_id')}, Kitsu={result.get('kitsu_id')}",
            "debug"
        )
        return result

    except requests.RequestException as e:
        g.log(f"ARM API failed ({source}={external_id}): {e}", "warning")
        return None
    except (ValueError, KeyError) as e:
        g.log(f"ARM API parse error ({source}={external_id}): {e}", "warning")
        return None


def _extract_arm_ids(data):
    """Extract all available IDs from an ARM API response dict."""
    anilist_id = data.get("anilist")
    mal_id = data.get("mal")

    if not anilist_id and not mal_id:
        return None

    return {
        "anilist_id":     anilist_id,
        "mal_id":         mal_id,
        "anidb_id":       data.get("anidb"),
        "kitsu_id":       data.get("kitsu"),
        "thetvdb_id":     data.get("thetvdb"),
        "themoviedb_id":  data.get("themoviedb"),
        "simkl_id":       None,  # ARM doesn't return Simkl IDs
    }


# ═══════════════════════════════════════════════════════════════════════════
#  AniList Reverse Search (title → AniList ID → cross-reference via ARM)
# ═══════════════════════════════════════════════════════════════════════════

def _anilist_reverse_search(imdb_id=None, tmdb_id=None):
    """Search AniList by title when ARM and Otaku-Mappings both miss.

    Uses TMDb title to search AniList, then maps the found MAL ID back through
    ARM to get the full ID set.

    Returns:
        dict with all anime IDs, or None.
    """
    # We need a title to search with — attempt a lightweight TMDb lookup.
    title = None
    try:
        if tmdb_id:
            tmdb_key = g.get_setting("tmdb.apikey", "9f3ca569aa46b6fb13931ec96ab8ae7e")
            if tmdb_key:
                resp = requests.get(
                    f"https://api.themoviedb.org/3/tv/{tmdb_id}",
                    params={"api_key": tmdb_key},
                    timeout=5,
                    headers={"User-Agent": "Seren"},
                )
                if resp.ok:
                    data = resp.json()
                    title = data.get("name") or data.get("original_name")
    except Exception:
        pass

    if not title:
        return None

    # Search AniList by title
    query = """
    query ($search: String) {
        Media(search: $search, type: ANIME) {
            id
            idMal
        }
    }
    """
    try:
        resp = requests.post(
            _ANILIST_URL,
            json={"query": query, "variables": {"search": title}},
            timeout=5,
            headers={"Content-Type": "application/json", "User-Agent": "Seren"},
        )
        if not resp.ok:
            return None

        data = resp.json()
        media = data.get("data", {}).get("Media")
        if not media:
            return None

        anilist_id = media.get("id")
        mal_id = media.get("idMal")

        if not anilist_id:
            return None

        g.log(
            f"Anime ID mapping (AniList search): title='{title}' → "
            f"AniList={anilist_id}, MAL={mal_id}",
            "debug"
        )

        # Try to get the full ID set via ARM using the MAL ID
        full_ids = None
        if mal_id:
            try:
                arm_resp = requests.get(
                    f"https://arm.haglund.dev/api/v2/mal?id={mal_id}",
                    timeout=5,
                    headers={"User-Agent": "Seren"},
                )
                if arm_resp.ok:
                    arm_data = arm_resp.json()
                    if isinstance(arm_data, list):
                        arm_data = arm_data[0] if arm_data else None
                    if arm_data:
                        full_ids = _extract_arm_ids(arm_data)
            except Exception:
                pass

        if full_ids:
            # Ensure AniList ID is set (ARM may not return it)
            full_ids["anilist_id"] = full_ids.get("anilist_id") or anilist_id
            full_ids["mal_id"] = full_ids.get("mal_id") or mal_id
            return full_ids

        # Minimal result if ARM didn't work
        return {
            "anilist_id": anilist_id,
            "mal_id": mal_id,
            "anidb_id": None,
            "kitsu_id": None,
            "thetvdb_id": None,
            "themoviedb_id": int(tmdb_id) if tmdb_id else None,
            "simkl_id": None,
        }

    except Exception as e:
        g.log(f"AniList reverse search failed: {e}", "warning")

    # ── Last resort: AniDB Titles Dump offline reverse lookup ────────────
    # Zero API cost — uses pre-indexed SQLite from weekly dump download
    if not title:
        return None
    try:
        from resources.lib.modules.anime.anidb_titles import lookup_anidb_id_by_title
        anidb_id = lookup_anidb_id_by_title(title)
        if anidb_id:
            g.log(f"Anime ID mapping (AniDB Titles Dump): title='{title}' → AniDB={anidb_id}", "debug")
            return {
                'anilist_id': None, 'mal_id': None, 'anidb_id': anidb_id,
                'kitsu_id': None, 'simkl_id': None,
                'thetvdb_id': None, 'themoviedb_id': int(tmdb_id) if tmdb_id else None,
            }
    except Exception as e:
        g.log(f"AniDB Titles Dump fallback failed: {e}", "debug")
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Simkl API (api.simkl.com) — public, no user auth needed
# ═══════════════════════════════════════════════════════════════════════════

def _simkl_get_anidb(mal_id=None, anilist_id=None, imdb_id=None, tmdb_id=None):
    """Query Simkl specifically to get anidb_id (and any other missing IDs).

    Tries MAL → AniList → IMDB → TMDB in order of reliability.

    Returns:
        dict with discovered IDs to merge into existing result, or None.
    """
    ids = _simkl_search_ids(mal_id=mal_id, anilist_id=anilist_id,
                            imdb_id=imdb_id, tmdb_id=tmdb_id)
    if ids and ids.get('anidb_id'):
        return ids
    return None


def _simkl_full_lookup(imdb_id=None, tmdb_id=None):
    """Full Simkl lookup when ARM returned nothing.  Returns full ID dict or None."""
    ids = _simkl_search_ids(imdb_id=imdb_id, tmdb_id=tmdb_id)
    if ids and (ids.get('anilist_id') or ids.get('mal_id')):
        return ids
    return None


def _simkl_search_ids(mal_id=None, anilist_id=None, imdb_id=None, tmdb_id=None):
    """Search Simkl for an anime by available IDs, return all mapped IDs.

    Flow: search/id → get simkl_id → /anime/{simkl_id}?extended=full → extract ids
    """
    simkl_id = None
    search_order = []
    if mal_id:
        search_order.append(('mal', mal_id))
    if anilist_id:
        search_order.append(('anilist', anilist_id))
    if imdb_id:
        search_order.append(('imdb', imdb_id))
    if tmdb_id:
        search_order.append(('tmdb', tmdb_id))

    for id_type, id_val in search_order:
        simkl_id = _simkl_find(id_type, id_val)
        if simkl_id:
            break

    if not simkl_id:
        return None

    return _simkl_get_full_ids(simkl_id)


def _simkl_find(id_type, id_value):
    """Search Simkl by external ID to get the simkl_id."""
    try:
        params = {
            id_type: id_value,
            'client_id': _SIMKL_CLIENT_ID,
        }
        response = requests.get(
            f'{_SIMKL_BASE}/search/id',
            params=params,
            timeout=5,
            headers={"User-Agent": "Seren"}
        )
        if not response.ok:
            return None

        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get('ids', {}).get('simkl')
        return None

    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"Simkl search failed ({id_type}={id_value}): {e}", "warning")
        return None


def _simkl_get_full_ids(simkl_id):
    """Get full anime info from Simkl to extract all mapped IDs."""
    try:
        params = {
            'extended': 'full',
            'client_id': _SIMKL_CLIENT_ID,
        }
        response = requests.get(
            f'{_SIMKL_BASE}/anime/{simkl_id}',
            params=params,
            timeout=5,
            headers={"User-Agent": "Seren"}
        )
        if not response.ok:
            return None

        data = response.json()
        if not data or 'ids' not in data:
            return None

        ids = data['ids']
        result = {
            "anilist_id":     ids.get('anilist'),
            "mal_id":         ids.get('mal'),
            "anidb_id":       ids.get('anidb'),
            "kitsu_id":       ids.get('kitsu'),
            "thetvdb_id":     ids.get('tvdb') or ids.get('thetvdb'),
            "themoviedb_id":  ids.get('tmdb') or ids.get('themoviedb'),
            "simkl_id":       ids.get('simkl') or simkl_id,
        }

        g.log(
            f"Anime ID mapping (Simkl): simkl={simkl_id} → "
            f"AniList={result.get('anilist_id')}, MAL={result.get('mal_id')}, "
            f"AniDB={result.get('anidb_id')}, Kitsu={result.get('kitsu_id')}",
            "debug"
        )
        return result

    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"Simkl full lookup failed (simkl={simkl_id}): {e}", "warning")
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Public convenience methods
# ═══════════════════════════════════════════════════════════════════════════

def get_anime_ids_for_item(item_information):
    """Convenience method to extract anime IDs from Seren's item_information dict.

    Args:
        item_information: Seren's standard item info dict

    Returns:
        dict with all anime database IDs, or None if not anime or mapping fails.
    """
    info = item_information.get("info", {})

    # Quick genre check — only look up IDs for anime content
    genres = info.get("genre", [])
    if not isinstance(genres, list):
        genres = [genres] if genres else []
    is_anime = any("anime" in g_str.lower() for g_str in genres)

    # Also check country_origin for Japanese content with animation genre
    if not is_anime:
        country = info.get("country_origin", "")
        has_animation = any("animation" in g_str.lower() for g_str in genres)
        if has_animation and country.upper() in ("JP", "JPN", "JAPAN", "CN", "CHN", "CHINA"):
            is_anime = True

    if not is_anime:
        return None

    imdb_id = info.get("imdb_id", "")
    tmdb_id = info.get("tmdb_id", "") or info.get("tmdb_show_id", "")
    trakt_id = info.get("trakt_show_id", "") or info.get("trakt_id", "")

    return get_anime_ids(imdb_id=imdb_id or None, tmdb_id=tmdb_id or None, trakt_id=trakt_id or None)


def invalidate_cache():
    """Clear the session-level ID cache."""
    global _id_cache
    _id_cache = {}
