"""AniDB full data fetch — single XML owner for all AniDB-derived features.

The AniDB HTTP API returns a single XML response per anime containing:
  <titles>     — multi-language title variants (used by anidb_titles.py)
  <episodes>   — per-episode metadata with ratings
  <characters> — character list with seiyuu (voice actor) names and photos

This module is the single owner of that fetch. It parses all three sections
in one pass and caches the structured result as JSON (30-day TTL). All other
modules (episode_meta.py, anidb_characters.py) import from here — they never
call anidb_request() for a full anime fetch themselves.

This avoids duplicate API calls under the 4-second AniDB rate limit.
"""

import json
import xml.etree.ElementTree as ET

from resources.lib.modules.globals import g

_ANIDB_BASE = "http://api.anidb.net:9001/httpapi"
_ANIDB_CLIENT = "otakukodi"
_ANIDB_CLIENTVER = "1"
_CDN_BASE = "https://cdn.anidb.net/images/main"


def get_anidb_data(anidb_id):
    """Fetch and return all AniDB data for an anime in a single cached call.

    Checks SQLite cache first (30-day TTL). On miss, calls the AniDB HTTP API
    and parses episodes, characters, and ratings in one XML parse pass.

    Args:
        anidb_id: AniDB anime ID (int)

    Returns:
        dict with keys:
          'episodes'   — {ep_num(int): {title, plot, airdate, duration}}
          'characters' — [{name, role, thumbnail, order}]  (Kodi setCast format)
          'ratings'    — {ep_num(int): {rating(float), votes(int)}}
        Returns None on failure — callers must handle gracefully.
    """
    if not anidb_id:
        return None

    # 1. SQLite cache
    cached = _get_cached(anidb_id)
    if cached is not None:
        return cached

    # 2. HTTP API fetch
    xml_text = _fetch_xml(anidb_id)
    if not xml_text:
        return None

    # 3. Parse all sections in one pass
    data = _parse_full_xml(xml_text)
    if data is None:
        return None

    # 4. Cache and return
    _set_cached(anidb_id, data)
    g.log(
        f"AniDB data: fetched anidb_id={anidb_id} — "
        f"{len(data['episodes'])} eps, {len(data['characters'])} chars, "
        f"{len(data['ratings'])} ep ratings",
        "debug",
    )
    return data


# ── Private: fetch ────────────────────────────────────────────────────────────

def _fetch_xml(anidb_id):
    """Call AniDB HTTP API, return raw XML text or None."""
    try:
        from resources.lib.modules.anime.episode_meta import anidb_request
        return anidb_request(
            _ANIDB_BASE,
            params={
                "request": "anime",
                "aid": str(anidb_id),
                "client": _ANIDB_CLIENT,
                "clientver": _ANIDB_CLIENTVER,
                "protover": "1",
            },
            timeout=10,
        )
    except Exception as e:
        g.log(f"AniDB data fetch failed (anidb_id={anidb_id}): {e}", "debug")
        return None


# ── Private: parse ────────────────────────────────────────────────────────────

def _parse_full_xml(xml_text):
    """Parse AniDB XML into structured dict. Returns None on error."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        g.log(f"AniDB XML parse error: {e}", "debug")
        return None

    if root.tag == "error":
        g.log(f"AniDB API error: {root.text}", "debug")
        return None

    return {
        "episodes": _parse_episodes(root),
        "characters": _parse_characters(root),
        "ratings": _parse_episode_ratings(root),
    }


def _parse_episodes(root):
    """Parse <episodes> section. Returns {ep_num: {title, plot, airdate, duration}}."""
    result = {}
    episodes_el = root.find("episodes")
    if episodes_el is None:
        return result

    for ep_el in episodes_el.findall("episode"):
        epno_el = ep_el.find("epno")
        if epno_el is None:
            continue
        # Only regular episodes (type 1)
        if epno_el.get("type", "1") != "1":
            continue
        try:
            ep_num = int(epno_el.text.strip())
        except (ValueError, TypeError, AttributeError):
            continue

        # Title: prefer EN, fallback x-jat, then ja
        title = ""
        for title_el in ep_el.findall("title"):
            lang = title_el.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            text = (title_el.text or "").strip()
            if lang == "en" and text:
                title = text
                break
            elif lang == "x-jat" and text and not title:
                title = text
            elif lang == "ja" and text and not title:
                title = text

        airdate = ""
        airdate_el = ep_el.find("airdate")
        if airdate_el is not None and airdate_el.text:
            airdate = airdate_el.text.strip()

        duration = 0
        length_el = ep_el.find("length")
        if length_el is not None and length_el.text:
            try:
                duration = int(length_el.text.strip())
            except (ValueError, TypeError):
                pass

        plot = ""
        summary_el = ep_el.find("summary")
        if summary_el is not None and summary_el.text:
            plot = summary_el.text.strip()

        result[ep_num] = {
            "title": title,
            "plot": plot,
            "airdate": airdate,
            "duration": duration,
        }

    return result


def _parse_episode_ratings(root):
    """Parse per-episode ratings from <episodes>. Returns {ep_num: {rating, votes}}."""
    result = {}
    episodes_el = root.find("episodes")
    if episodes_el is None:
        return result

    for ep_el in episodes_el.findall("episode"):
        epno_el = ep_el.find("epno")
        if epno_el is None or epno_el.get("type", "1") != "1":
            continue
        try:
            ep_num = int(epno_el.text.strip())
        except (ValueError, TypeError, AttributeError):
            continue

        rating_el = ep_el.find("rating")
        if rating_el is None or not rating_el.text:
            continue
        try:
            rating = float(rating_el.text.strip())
            votes = int(rating_el.get("votes", 0))
            result[ep_num] = {"rating": rating, "votes": votes}
        except (ValueError, TypeError):
            continue

    return result


def _parse_characters(root):
    """Parse <characters> section into Kodi setCast() format.

    Returns list of dicts: [{name, role, thumbnail, order}]
    Main characters first (type contains 'main'), sorted by position.
    """
    characters_el = root.find("characters")
    if characters_el is None:
        return []

    main_chars = []
    supporting_chars = []

    for idx, char_el in enumerate(characters_el.findall("character")):
        char_type = char_el.get("type", "").lower()

        name_el = char_el.find("name") or char_el.find("n")
        # AniDB uses <name> in some versions, <n> in others
        if name_el is None:
            # Try both tags
            for tag in ("name", "n"):
                name_el = char_el.find(tag)
                if name_el is not None:
                    break
        if name_el is None or not name_el.text:
            continue

        char_name = name_el.text.strip()

        # Voice actor from <seiyuu>
        seiyuu_el = char_el.find("seiyuu")
        role = ""
        thumbnail = ""
        if seiyuu_el is not None:
            role = (seiyuu_el.text or "").strip()
            picture = seiyuu_el.get("picture", "")
            if picture:
                thumbnail = f"{_CDN_BASE}/{picture}"

        cast_entry = {
            "name": char_name,
            "role": role,
            "thumbnail": thumbnail,
            "order": idx,
        }

        if "main" in char_type:
            main_chars.append(cast_entry)
        else:
            supporting_chars.append(cast_entry)

    # Main characters first, then supporting
    all_chars = main_chars + supporting_chars
    # Re-index order after sort
    for i, entry in enumerate(all_chars):
        entry["order"] = i

    return all_chars


# ── Private: cache ────────────────────────────────────────────────────────────

def _get_cached(anidb_id):
    """Return cached data dict from SQLite, or None on miss/expiry."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        return AnimeCache().get_anidb_full_data(anidb_id)
    except Exception:
        return None


def _set_cached(anidb_id, data):
    """Store data dict in SQLite cache."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().set_anidb_full_data(anidb_id, data)
    except Exception:
        pass
