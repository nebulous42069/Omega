"""AniDB title variants + offline Titles Dump.

Two features in one module:

1. get_anidb_titles(anidb_id) — fetches x-jat (romanized Japanese), short
   abbreviations, and EN synonyms from AniDB's HTTP API. These match fansub
   release filenames that AniList/MAL title enrichment misses.
   Results cached in SQLite anime_titles table (30-day TTL).

2. download_titles_dump() / lookup_anidb_id_by_title(title) — downloads
   AniDB's anime-titles.xml.gz (~30MB, weekly) and parses it into an indexed
   SQLite table for offline title → AniDB ID reverse lookup. Used as a last
   resort in anilist_mapping.py when ARM + Otaku-Mappings + AniList all miss.

Rate limit: AniDB HTTP API requires ~4s between requests. This module uses the
shared _anidb_request() helper extracted from episode_meta.py, which enforces
the rate limit at module level across both callers.
"""

import gzip
import json
import os
import time
import xml.etree.ElementTree as ET

import requests

from resources.lib.modules.globals import g

_ANIDB_BASE = "http://api.anidb.net:9001/httpapi"
_ANIDB_CLIENT = "otakukodi"
_ANIDB_CLIENTVER = "1"
_TITLES_DUMP_URL = "https://anidb.net/api/anime-titles.xml.gz"
_DUMP_MAX_AGE_DAYS = 7
_TIMEOUT = 10

# Title language codes to include (all others skipped)
_INCLUDE_LANGS = {"x-jat", "en", "short"}


def get_anidb_titles(anidb_id):
    """Return AniDB title variants for a given AniDB ID.

    Fetches x-jat (romanized Japanese), short abbreviations, and EN synonyms.
    Checks SQLite cache first (30-day TTL). Falls back to HTTP API on miss.
    Last resort: Titles Dump SQLite table (offline, no API call).

    Args:
        anidb_id: AniDB anime ID (int)

    Returns:
        list of title strings — empty list on failure, never raises
    """
    if not anidb_id:
        return []

    # 1. SQLite cache
    cached = _get_cached_titles(anidb_id)
    if cached is not None:
        return cached

    # 2. HTTP API
    titles = _fetch_titles_from_api(anidb_id)
    if titles:
        _cache_titles(anidb_id, titles)
        g.log(f"AniDB titles: fetched {len(titles)} variants for anidb_id={anidb_id}", "debug")
        return titles

    # 3. Titles Dump fallback (offline — no API call needed)
    titles = _get_titles_from_dump(anidb_id)
    if titles:
        _cache_titles(anidb_id, titles)
        g.log(f"AniDB titles: {len(titles)} variants from dump for anidb_id={anidb_id}", "debug")
        return titles

    # Cache empty result to avoid repeated failed API calls
    _cache_titles(anidb_id, [])
    return []


def lookup_anidb_id_by_title(title):
    """Offline reverse lookup: title string → AniDB ID.

    Uses the pre-indexed anidb_titles_dump SQLite table.
    Case-insensitive exact match. Returns None if dump not downloaded
    or title not found.

    Args:
        title: anime title string to search

    Returns:
        int AniDB ID or None
    """
    if not title:
        return None
    try:
        from resources.lib.database.animeCache import AnimeCache
        return AnimeCache().lookup_title_dump(title)
    except Exception as e:
        g.log(f"AniDB title dump lookup failed: {e}", "debug")
        return None


def download_titles_dump():
    """Download and parse AniDB's anime-titles.xml.gz into SQLite.

    Skips download if dump is less than 7 days old.
    Called from router.py updateAnimeMappings action at startup.

    Returns:
        True on success or skip, False on failure
    """
    try:
        from resources.lib.database.animeCache import AnimeCache
        cache = AnimeCache()
        age_days = cache.get_dump_age_days()
        if age_days is not None and age_days < _DUMP_MAX_AGE_DAYS:
            g.log(f"AniDB titles dump is {age_days:.1f} days old, skipping", "debug")
            return True
    except Exception:
        pass

    g.log("AniDB: downloading anime-titles.xml.gz...", "info")
    try:
        resp = requests.get(_TITLES_DUMP_URL, timeout=30, headers={"User-Agent": "Seren"})
        if not resp.ok:
            g.log(f"AniDB titles dump download failed: HTTP {resp.status_code}", "warning")
            return False

        gz_data = resp.content
        xml_data = gzip.decompress(gz_data)
        _parse_and_store_dump(xml_data)
        g.log("AniDB: titles dump parsed and stored", "info")
        return True

    except Exception as e:
        g.log(f"AniDB titles dump error: {e}", "warning")
        return False


# ── Private helpers ───────────────────────────────────────────────────────────

def _fetch_titles_from_api(anidb_id):
    """Fetch title variants from AniDB HTTP API for a specific anime.

    Returns list of title strings (filtered to _INCLUDE_LANGS), or [].
    """
    from resources.lib.modules.anime.episode_meta import anidb_request
    try:
        params = {
            "request": "anime",
            "client": _ANIDB_CLIENT,
            "clientver": _ANIDB_CLIENTVER,
            "protover": "1",
            "aid": anidb_id,
        }
        xml_text = anidb_request(_ANIDB_BASE, params, _TIMEOUT)
        if not xml_text:
            return []
        return _parse_titles_from_xml(xml_text)
    except Exception as e:
        g.log(f"AniDB title API fetch failed (aid={anidb_id}): {e}", "debug")
        return []


def _parse_titles_from_xml(xml_text):
    """Parse <titles> block from AniDB anime XML response."""
    titles = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter("title"):
            lang = elem.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            if lang not in _INCLUDE_LANGS:
                continue
            text = (elem.text or "").strip()
            if text and not _is_cjk(text):
                titles.append(text)
    except ET.ParseError as e:
        g.log(f"AniDB titles XML parse error: {e}", "debug")
    return titles


def _get_titles_from_dump(anidb_id):
    """Get titles for a specific anidb_id from the pre-parsed dump table."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        return AnimeCache().get_dump_titles_for_id(anidb_id)
    except Exception:
        return []


def _parse_and_store_dump(xml_data):
    """Parse anime-titles.xml and bulk-insert into anidb_titles_dump table."""
    try:
        root = ET.fromstring(xml_data)
        rows = []
        for anime_elem in root.findall("anime"):
            try:
                anidb_id = int(anime_elem.get("aid", 0))
            except (ValueError, TypeError):
                continue
            if not anidb_id:
                continue
            for title_elem in anime_elem.findall("title"):
                lang = title_elem.get("{http://www.w3.org/XML/1998/namespace}lang", "")
                if lang not in _INCLUDE_LANGS:
                    continue
                text = (title_elem.text or "").strip()
                if not text or _is_cjk(text):
                    continue
                rows.append((anidb_id, lang, text.lower()))

        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().store_titles_dump(rows)
        g.log(f"AniDB titles dump: stored {len(rows)} title entries", "info")
    except Exception as e:
        g.log(f"AniDB titles dump parse/store error: {e}", "warning")


def _get_cached_titles(anidb_id):
    """Return cached title list from SQLite, or None on miss."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        return AnimeCache().get_titles(anidb_id)
    except Exception:
        return None


def _cache_titles(anidb_id, titles):
    """Store title list in SQLite cache."""
    try:
        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().set_titles(anidb_id, titles)
    except Exception:
        pass


def _is_cjk(text):
    """True if text contains CJK characters (Japanese/Chinese/Korean)."""
    import re
    return bool(re.search(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]", text))
