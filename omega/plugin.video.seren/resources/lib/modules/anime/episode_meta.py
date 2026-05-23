"""Anime episode metadata enrichment — Simkl → AniZip → Jikan (MAL) → AniDB → Kitsu.

Fetches anime-specific episode titles, thumbnails, plots, air dates, and durations
from multiple sources in a cascading fallback chain. First source that returns usable
data wins. All results are cached in SQLite (30-day TTL) via animeCache.

This module is called from metadataHandler during episode list formatting.
It overlays anime-specific data onto the standard TMDB/TVDB metadata, replacing
generic "Episode 1" titles with actual anime episode titles and screenshots.

Reference: Otaku Testing 5.2.81 uses the same Simkl → AniZip → Jikan fallback chain.
"""

import time

import requests

from resources.lib.modules.globals import g

# Simkl public API — client_id only, no user auth
_SIMKL_CLIENT_ID = '59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8'
_SIMKL_BASE = 'https://api.simkl.com'

# AniZip API
_ANIZIP_BASE = 'https://api.ani.zip'

# Jikan (MAL) API v4
_JIKAN_BASE = 'https://api.jikan.moe/v4'

# AniDB HTTP API
# Client name 'otakukodi' is registered with AniDB (shared with Otaku addon).
# Rate limit: 4 seconds between requests (AniDB enforced).
_ANIDB_BASE = 'http://api.anidb.net:9001/httpapi'
_ANIDB_CLIENT = 'otakukodi'
_ANIDB_CLIENTVER = '1'
_ANIDB_LAST_REQUEST = 0  # module-level timestamp for 4s rate limit

# Kitsu API
_KITSU_BASE = 'https://kitsu.io/api/edge'

# Request timeout for all API calls
_TIMEOUT = 10


def get_episode_data(mal_id=None, anidb_id=None, simkl_id=None, kitsu_id=None,
                     season=1, episode_count=None, anilist_id=None):
    """Main entry point — fetch episode metadata using the cascading fallback chain.

    Checks SQLite cache first. On cache miss, tries each API source in order:
    Simkl → AniZip → Jikan (MAL) → AniDB → Kitsu

    Args:
        mal_id: MyAnimeList ID
        anidb_id: AniDB anime ID
        simkl_id: Simkl anime ID
        kitsu_id: Kitsu anime ID
        season: Season number (default 1)
        episode_count: Expected episode count (optional, for validation)
        anilist_id: AniList anime ID (used as AniZip key)

    Returns:
        dict mapping episode numbers to metadata dicts:
        {1: {title, plot, thumb, airdate, duration}, 2: {...}, ...}
        Returns empty dict if all sources fail.
    """
    # Build a composite cache key from available IDs
    cache_key = _build_cache_key(mal_id, anidb_id, simkl_id, kitsu_id, anilist_id)
    if not cache_key:
        return {}

    # ── Check SQLite cache first ─────────────────────────────────────────
    try:
        from resources.lib.database.animeCache import AnimeCache
        cache = AnimeCache()
        cached = cache.get_season_episodes(cache_key, season)
        if cached:
            g.log(f"AnimeEpisodeMeta: cache hit for {cache_key} S{season} "
                  f"({len(cached)} episodes, source={next(iter(cached.values())).get('source', '?')})", "debug")
            return cached
    except Exception as e:
        g.log(f"AnimeEpisodeMeta: cache read error (non-fatal): {e}", "debug")
        cache = None

    # ── Fallback chain: try each source ──────────────────────────────────
    episodes = {}
    source_name = None

    # Source 1: Simkl
    if not episodes and simkl_id:
        try:
            episodes = _fetch_simkl(simkl_id, season)
            if episodes:
                source_name = 'simkl'
                g.log(f"AnimeEpisodeMeta: Simkl returned {len(episodes)} episodes "
                      f"for simkl_id={simkl_id}", "info")
        except Exception as e:
            g.log(f"AnimeEpisodeMeta: Simkl failed (non-fatal): {e}", "debug")

    # Source 2: AniZip (uses mal_id or anilist_id)
    if not episodes:
        lookup_id = mal_id or anilist_id
        id_type = 'mal_id' if mal_id else 'anilist_id' if anilist_id else None
        if lookup_id and id_type:
            try:
                episodes = _fetch_anizip(lookup_id, id_type, season)
                if episodes:
                    source_name = 'anizip'
                    g.log(f"AnimeEpisodeMeta: AniZip returned {len(episodes)} episodes "
                          f"for {id_type}={lookup_id}", "info")
            except Exception as e:
                g.log(f"AnimeEpisodeMeta: AniZip failed (non-fatal): {e}", "debug")

    # Source 3: Jikan (MAL)
    if not episodes and mal_id:
        try:
            episodes = _fetch_jikan(mal_id, season)
            if episodes:
                source_name = 'jikan'
                g.log(f"AnimeEpisodeMeta: Jikan returned {len(episodes)} episodes "
                      f"for mal_id={mal_id}", "info")
        except Exception as e:
            g.log(f"AnimeEpisodeMeta: Jikan failed (non-fatal): {e}", "debug")

    # Source 4: AniDB (2s rate limit, XML parse)
    if not episodes and anidb_id:
        try:
            episodes = _fetch_anidb(anidb_id, season)
            if episodes:
                source_name = 'anidb'
                g.log(f"AnimeEpisodeMeta: AniDB returned {len(episodes)} episodes "
                      f"for anidb_id={anidb_id}", "info")
        except Exception as e:
            g.log(f"AnimeEpisodeMeta: AniDB failed (non-fatal): {e}", "debug")

    # Source 5: Kitsu
    if not episodes and kitsu_id:
        try:
            episodes = _fetch_kitsu(kitsu_id, season)
            if episodes:
                source_name = 'kitsu'
                g.log(f"AnimeEpisodeMeta: Kitsu returned {len(episodes)} episodes "
                      f"for kitsu_id={kitsu_id}", "info")
        except Exception as e:
            g.log(f"AnimeEpisodeMeta: Kitsu failed (non-fatal): {e}", "debug")

    if not episodes:
        g.log(f"AnimeEpisodeMeta: all sources exhausted for cache_key={cache_key} S{season}", "debug")
        return {}

    # ── Overlay AniDB per-episode ratings (unique — no other source has this) ──
    if anidb_id and episodes:
        try:
            from resources.lib.modules.anime.anidb_characters import get_episode_ratings
            ratings = get_episode_ratings(anidb_id)
            for ep_num, ep_data in episodes.items():
                if ep_num in ratings:
                    ep_data['anidb_rating'] = ratings[ep_num].get('rating')
                    ep_data['anidb_votes'] = ratings[ep_num].get('votes')
        except Exception as e:
            g.log(f"AnimeEpisodeMeta: ratings overlay failed (non-fatal): {e}", "debug")

    # ── Write to SQLite cache ────────────────────────────────────────────
    if cache and source_name:
        try:
            cache.set_episodes(cache_key, season, episodes, source_name)
            g.log(f"AnimeEpisodeMeta: cached {len(episodes)} episodes from {source_name}", "debug")
        except Exception as e:
            g.log(f"AnimeEpisodeMeta: cache write error (non-fatal): {e}", "debug")

    return episodes


def _build_cache_key(mal_id, anidb_id, simkl_id, kitsu_id, anilist_id):
    """Build a stable cache key from the best available ID."""
    if mal_id:
        return f"mal_{mal_id}"
    if anilist_id:
        return f"al_{anilist_id}"
    if anidb_id:
        return f"adb_{anidb_id}"
    if simkl_id:
        return f"smk_{simkl_id}"
    if kitsu_id:
        return f"kit_{kitsu_id}"
    return None


# ═════════════════════════════════════════════════════════════════════════
# Source 1: Simkl
# ═════════════════════════════════════════════════════════════════════════

def _fetch_simkl(simkl_id, season):
    """Fetch episode data from Simkl API.

    Simkl returns episodes with title, description, and still image URLs.
    Endpoint: GET /anime/episodes/{simkl_id}
    """
    resp = requests.get(
        f"{_SIMKL_BASE}/anime/episodes/{simkl_id}",
        params={'client_id': _SIMKL_CLIENT_ID, 'extended': 'full'},
        headers={'Content-Type': 'application/json'},
        timeout=_TIMEOUT,
    )
    if resp.status_code != 200:
        return {}

    data = resp.json()
    if not isinstance(data, list):
        return {}

    episodes = {}
    for ep in data:
        # Simkl marks episode type — only include regular episodes
        if ep.get('type') and ep['type'] != 'episode':
            continue
        ep_season = ep.get('season', 1) or 1
        if ep_season != season:
            continue
        ep_num = ep.get('episode')
        if not ep_num:
            continue

        thumb = ''
        if ep.get('img'):
            # Otaku uses _w (wide) suffix — higher res than _c (compact)
            thumb = f"https://wsrv.nl/?url=https://simkl.in/episodes/{ep['img']}_w.webp"

        episodes[int(ep_num)] = {
            'title': ep.get('title', ''),
            'plot': ep.get('description', ''),
            'thumb': thumb,
            'airdate': ep.get('date', ''),
            'duration': 0,
        }

    return episodes


# ═════════════════════════════════════════════════════════════════════════
# Source 2: AniZip
# ═════════════════════════════════════════════════════════════════════════

def _fetch_anizip(lookup_id, id_type, season):
    """Fetch episode data from AniZip (api.ani.zip).

    AniZip provides the richest episode metadata: titles, images, plots.
    Endpoint: GET /mappings?{id_type}={id}
    """
    resp = requests.get(
        f"{_ANIZIP_BASE}/mappings",
        params={id_type: str(lookup_id)},
        timeout=_TIMEOUT,
    )
    if resp.status_code != 200:
        return {}

    data = resp.json()
    ep_data = data.get('episodes', {})
    if not ep_data:
        return {}

    episodes = {}
    for ep_key, ep in ep_data.items():
        # AniZip uses string keys like "1", "2", or "S1" for specials
        try:
            ep_num = int(ep_key)
        except (ValueError, TypeError):
            continue  # skip specials like "S1"

        if ep_num < 1:
            continue

        thumb = ''
        if ep.get('image'):
            thumb = ep['image']

        # AniZip provides titles in multiple languages
        title = (ep.get('title', {}).get('en', '')
                 or ep.get('title', {}).get('x-jat', '')
                 or ep.get('title', {}).get('ja', '')
                 or '')

        episodes[ep_num] = {
            'title': title,
            'plot': ep.get('overview', '') or ep.get('summary', ''),
            'thumb': thumb,
            'airdate': ep.get('airDate', '') or ep.get('airdate', ''),
            'duration': ep.get('length') or ep.get('runtime') or 0,
        }

    return episodes


# ═════════════════════════════════════════════════════════════════════════
# Source 3: Jikan (MAL)
# ═════════════════════════════════════════════════════════════════════════

def _fetch_jikan(mal_id, season):
    """Fetch episode data from Jikan MAL API v4.

    Jikan is paginated (100 per page). Episodes have titles and some have plots.
    Endpoint: GET /anime/{mal_id}/episodes?page={n}
    """
    episodes = {}
    page = 1
    max_pages = 10  # safety limit

    while page <= max_pages:
        resp = requests.get(
            f"{_JIKAN_BASE}/anime/{mal_id}/episodes",
            params={'page': page},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 429:
            # Jikan rate limit — wait and retry once
            time.sleep(1)
            resp = requests.get(
                f"{_JIKAN_BASE}/anime/{mal_id}/episodes",
                params={'page': page},
                timeout=_TIMEOUT,
            )
        if resp.status_code != 200:
            break

        data = resp.json()
        ep_list = data.get('data', [])
        if not ep_list:
            break

        for ep in ep_list:
            ep_num = ep.get('mal_id')  # Jikan v4 uses mal_id as episode number
            if not ep_num:
                continue

            episodes[int(ep_num)] = {
                'title': ep.get('title', '') or ep.get('title_romanji', '') or '',
                'plot': ep.get('synopsis', '') or '',
                'thumb': '',  # Jikan v4 episodes don't reliably have images
                'airdate': ep.get('aired', '') or '',
                'duration': 0,
            }

        # Check pagination
        pagination = data.get('pagination', {})
        if not pagination.get('has_next_page', False):
            break
        page += 1

    return episodes


# ═════════════════════════════════════════════════════════════════════════
# Source 4: AniDB (HTTP API, 2s rate limit, XML)
# ═════════════════════════════════════════════════════════════════════════

def anidb_request(url, params, timeout=10):
    """Shared AniDB HTTP API request with 4-second rate limit enforcement.

    Called by episode_meta._fetch_anidb() and anidb_titles.get_anidb_titles().
    Returns raw response text, or None on failure.
    """
    global _ANIDB_LAST_REQUEST
    elapsed = time.time() - _ANIDB_LAST_REQUEST
    if elapsed < 4.0:
        time.sleep(4.0 - elapsed)
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        _ANIDB_LAST_REQUEST = time.time()
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception:
        _ANIDB_LAST_REQUEST = time.time()
        return None


def _fetch_anidb(anidb_id, season):
    """Fetch episode data from AniDB via the shared anidb_data module.

    Delegates to anidb_data.get_anidb_data() which owns the single XML fetch
    and 30-day SQLite cache. This avoids duplicate API calls when
    anidb_characters.py also needs the same response.
    """
    try:
        from resources.lib.modules.anime.anidb_data import get_anidb_data
        data = get_anidb_data(anidb_id)
        if not data:
            return {}
        # Return episodes section — same format as the old _parse_anidb_xml()
        # Add thumb key (AniDB HTTP API has no episode thumbnails)
        episodes = {}
        for ep_num, ep in data.get("episodes", {}).items():
            episodes[ep_num] = {
                "title": ep.get("title", ""),
                "plot": ep.get("plot", ""),
                "thumb": "",
                "airdate": ep.get("airdate", ""),
                "duration": ep.get("duration", 0),
            }
        return episodes
    except Exception as e:
        g.log(f"AniDB episode fetch failed (anidb_id={anidb_id}): {e}", "debug")
        return {}


def _parse_anidb_xml(xml_text, season):
    """Parse AniDB XML response for episode data."""
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(xml_text)
    except Exception:
        return {}

    # Check for error responses
    if root.tag == 'error':
        return {}

    episodes_el = root.find('episodes')
    if episodes_el is None:
        return {}

    episodes = {}
    for ep_el in episodes_el.findall('episode'):
        ep_type = ep_el.find('epno')
        if ep_type is None:
            continue

        # AniDB episode types: 1=regular, 2=special, 3=credit, 4=trailer, 5=parody, 6=other
        type_attr = ep_type.get('type', '1')
        if type_attr != '1':
            continue  # only regular episodes

        try:
            ep_num = int(ep_type.text.strip())
        except (ValueError, TypeError, AttributeError):
            continue

        # Get English title, fallback to romanized Japanese, then Japanese
        title = ''
        for title_el in ep_el.findall('title'):
            lang = title_el.get('{http://www.w3.org/XML/1998/namespace}lang', '')
            if lang == 'en' and title_el.text:
                title = title_el.text.strip()
                break
            elif lang == 'x-jat' and title_el.text and not title:
                title = title_el.text.strip()
            elif lang == 'ja' and title_el.text and not title:
                title = title_el.text.strip()

        # AniDB provides air dates per episode
        airdate = ''
        airdate_el = ep_el.find('airdate')
        if airdate_el is not None and airdate_el.text:
            airdate = airdate_el.text.strip()

        # AniDB provides episode length in minutes
        duration = 0
        length_el = ep_el.find('length')
        if length_el is not None and length_el.text:
            try:
                duration = int(length_el.text.strip())
            except (ValueError, TypeError):
                pass

        # AniDB has per-episode synopsis in <summary> (often sparse)
        plot = ''
        summary_el = ep_el.find('summary')
        if summary_el is not None and summary_el.text:
            plot = summary_el.text.strip()

        episodes[ep_num] = {
            'title': title,
            'plot': plot,
            'thumb': '',  # AniDB doesn't serve episode thumbnails via HTTP API
            'airdate': airdate,
            'duration': duration,
        }

    return episodes


# ═════════════════════════════════════════════════════════════════════════
# Source 5: Kitsu
# ═════════════════════════════════════════════════════════════════════════

def _fetch_kitsu(kitsu_id, season):
    """Fetch episode data from Kitsu API.

    Kitsu provides titles, thumbnails, and synopses via JSON:API.
    Endpoint: GET /anime/{kitsu_id}/episodes?page[limit]=20&page[offset]=N
    """
    episodes = {}
    offset = 0
    page_size = 20
    max_iterations = 50  # safety limit (1000 episodes)

    while offset < page_size * max_iterations:
        resp = requests.get(
            f"{_KITSU_BASE}/anime/{kitsu_id}/episodes",
            params={
                'page[limit]': page_size,
                'page[offset]': offset,
                'sort': 'number',
            },
            headers={
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json',
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            break

        data = resp.json()
        ep_list = data.get('data', [])
        if not ep_list:
            break

        for ep in ep_list:
            attrs = ep.get('attributes', {})
            ep_num = attrs.get('number') or attrs.get('relativeNumber')
            if not ep_num:
                continue

            # Kitsu provides seasonNumber but many anime are season 1
            ep_season = attrs.get('seasonNumber') or 1
            if ep_season != season:
                continue

            thumb = ''
            thumbnail = attrs.get('thumbnail')
            if thumbnail:
                # Kitsu thumbnail object has 'original', 'large', 'small' etc.
                if isinstance(thumbnail, dict):
                    thumb = (thumbnail.get('original')
                             or thumbnail.get('large')
                             or thumbnail.get('small')
                             or '')
                elif isinstance(thumbnail, str):
                    thumb = thumbnail

            # Kitsu titles: canonicalTitle, then titles dict
            title = attrs.get('canonicalTitle', '')
            if not title:
                titles = attrs.get('titles', {})
                title = (titles.get('en', '')
                         or titles.get('en_jp', '')
                         or titles.get('ja_jp', '')
                         or '')

            episodes[int(ep_num)] = {
                'title': title,
                'plot': attrs.get('synopsis', '') or attrs.get('description', ''),
                'thumb': thumb,
                'airdate': attrs.get('airdate', ''),
                'duration': attrs.get('length') or 0,
            }

        # Check for next page
        links = data.get('links', {})
        if not links.get('next'):
            break
        offset += page_size

    return episodes
