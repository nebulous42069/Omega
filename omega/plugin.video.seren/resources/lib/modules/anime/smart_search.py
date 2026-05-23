"""Smart Anime Search — enriches scraper search titles and corrects season/episode numbering.

Three layers:
1. Title enrichment: AniList titles + MAL titles + auto-cleaned variants
2. Season/episode mapping: AniList cour detection to fix Trakt→torrent numbering
3. Auto-clean: strips colons, apostrophes, special chars for torrent-friendly searches

Results cached per show for session duration.
"""

import re

import requests

from resources.lib.modules.globals import g

ANILIST_URL = "https://graphql.anilist.co"
JIKAN_URL = "https://api.jikan.moe/v4/anime"

# Session caches
_title_cache = {}  # {anilist_id: [list of title variants]}
_season_cache = {}  # {anilist_id: {episodes_per_cour: [...], total_prequel_eps: int}}


def _clean_title(title):
    """Strip characters that break torrent site searches."""
    if not title:
        return None
    # Remove colons, apostrophes, dashes, special unicode, parenthesized content like (2005)
    cleaned = re.sub(r"[:''\u2019\u2018\u2013\u2014&!★√…?.]", "", title)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)  # Remove parenthesized content
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s*-\s*$", "", cleaned).strip()  # Trailing dash
    return cleaned if cleaned and len(cleaned) > 1 else None


def get_enriched_aliases(anilist_id=None, mal_id=None, anidb_id=None):
    """Fetch title variants from AniList + MAL + AniDB + auto-cleaned versions.

    Args:
        anilist_id: AniList ID (int)
        mal_id: MAL ID (int)
        anidb_id: AniDB ID (int) — adds x-jat romanized + short abbreviations

    Returns:
        list of unique, cleaned title strings suitable for torrent search
    """
    cache_key = anilist_id or f"mal_{mal_id}"
    if cache_key in _title_cache:
        return _title_cache[cache_key]

    raw_titles = set()

    # AniList titles
    if anilist_id:
        raw_titles.update(_fetch_anilist_titles(anilist_id))

    # MAL titles via Jikan
    if mal_id:
        raw_titles.update(_fetch_mal_titles(mal_id))

    # AniDB title variants: x-jat romanized + short abbreviations + EN synonyms
    # These match fansub release filenames that AniList/MAL miss
    if anidb_id:
        try:
            from resources.lib.modules.anime.anidb_titles import get_anidb_titles
            raw_titles.update(get_anidb_titles(anidb_id))
        except Exception as e:
            g.log(f"Smart search: AniDB titles fetch failed (anidb_id={anidb_id}): {e}", "debug")

    # Build cleaned variants
    all_variants = set()
    for title in raw_titles:
        if not title:
            continue
        all_variants.add(title)
        cleaned = _clean_title(title)
        if cleaned and cleaned.lower() != title.lower():
            all_variants.add(cleaned)

    # Deduplicate case-insensitively, keep shortest + longest variants
    result = _deduplicate_titles(all_variants)

    _title_cache[cache_key] = result
    if result:
        g.log(f"Smart search: enriched {len(result)} title variants (AniList={anilist_id}, MAL={mal_id}, AniDB={anidb_id})", "debug")

    return result


def _fetch_anilist_titles(anilist_id):
    """Fetch title variants from AniList GraphQL."""
    query = """
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            title { romaji english native }
            synonyms
        }
    }
    """
    try:
        response = requests.post(
            ANILIST_URL,
            json={"query": query, "variables": {"id": anilist_id}},
            timeout=5,
            headers={"User-Agent": "Seren"},
        )
        if not response.ok:
            return set()

        media = response.json().get("data", {}).get("Media", {})
        if not media:
            return set()

        titles = set()
        title_obj = media.get("title", {})
        if title_obj.get("romaji"):
            titles.add(title_obj["romaji"])
        if title_obj.get("english"):
            titles.add(title_obj["english"])
        # Skip native (Japanese characters) — not useful for torrent search
        for syn in media.get("synonyms", []):
            if syn and not _is_cjk(syn):
                titles.add(syn)

        return titles
    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"AniList title fetch error (id={anilist_id}): {e}", "debug")
        return set()


def _fetch_mal_titles(mal_id):
    """Fetch title variants from MyAnimeList via Jikan API."""
    try:
        response = requests.get(
            f"{JIKAN_URL}/{mal_id}",
            timeout=5,
            headers={"User-Agent": "Seren"},
        )
        if not response.ok:
            return set()

        data = response.json().get("data", {})
        if not data:
            return set()

        titles = set()
        if data.get("title"):
            titles.add(data["title"])
        if data.get("title_english"):
            titles.add(data["title_english"])
        # Skip title_japanese (CJK characters)
        for syn in data.get("title_synonyms", []):
            if syn and not _is_cjk(syn):
                titles.add(syn)

        return titles
    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"MAL/Jikan title fetch error (id={mal_id}): {e}", "debug")
        return set()


def get_alternative_episode_numbers(anilist_id, trakt_season, trakt_episode, absolute_number=None):
    """Compute alternative season/episode numbers for anime cour splits.

    Many anime are listed as one continuous season on Trakt (S01E29) but torrent
    sites split them by cour (S02E01). This uses AniList's relation data to
    detect the split and compute the alternative numbering.

    Args:
        anilist_id: AniList ID of the current show
        trakt_season: Season number from Trakt
        trakt_episode: Episode number from Trakt
        absolute_number: Absolute episode number (if available)

    Returns:
        dict with optional keys:
        - 'alt_season': alternative season number (int)
        - 'alt_episode': alternative episode number (int)
        - 'absolute': absolute episode number (int)
        or None if no alternative numbering found
    """
    if not anilist_id:
        return None

    cour_data = _get_cour_data(anilist_id)
    if not cour_data:
        return None

    result = {}

    # Always use trakt_episode for cour mapping — NOT absolute_number.
    # Trakt's absolute_number counts across the entire franchise (all AniList entries),
    # but AniList's cour structure only covers THIS entry + immediate prequel/sequel.
    # E.g. Frieren: Trakt absolute=54, but AniList entry 154587 has [28, 11] = 39 eps.
    # trakt_episode=29 correctly maps to cour 2 ep 1 (29 - 28 = 1).
    ep_num = int(trakt_episode)

    episodes_per_cour = cour_data.get("episodes_per_cour", [])
    g.log(f"Smart search: cour data for AniList {anilist_id}: episodes_per_cour={episodes_per_cour}, "
          f"trakt S{trakt_season:02d}E{trakt_episode:02d}, absolute={absolute_number}, using ep_num={ep_num}", "info")
    if episodes_per_cour and len(episodes_per_cour) > 1:
        # Multiple cours detected — compute which cour this episode falls in
        cumulative = 0
        for cour_idx, cour_eps in enumerate(episodes_per_cour):
            if cour_eps and ep_num <= cumulative + cour_eps:
                alt_season = cour_idx + 1
                alt_episode = ep_num - cumulative
                if alt_season != int(trakt_season) or alt_episode != int(trakt_episode):
                    result["alt_season"] = alt_season
                    result["alt_episode"] = alt_episode
                    g.log(
                        f"Smart search: S{trakt_season:02d}E{trakt_episode:02d} → "
                        f"alt S{alt_season:02d}E{alt_episode:02d} (cour {cour_idx + 1})",
                        "debug",
                    )
                break
            cumulative += cour_eps if cour_eps else 0

    if absolute_number:
        result["absolute"] = int(absolute_number)
    elif ep_num != int(trakt_episode):
        result["absolute"] = ep_num

    return result if result else None


def _get_cour_data(anilist_id):
    """Fetch cour/season split data from AniList via relations."""
    if anilist_id in _season_cache:
        return _season_cache[anilist_id]

    query = """
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            episodes
            relations {
                edges {
                    relationType
                    node {
                        id
                        episodes
                        format
                        title { romaji }
                    }
                }
            }
        }
    }
    """
    try:
        response = requests.post(
            ANILIST_URL,
            json={"query": query, "variables": {"id": anilist_id}},
            timeout=5,
            headers={"User-Agent": "Seren"},
        )
        if not response.ok:
            _season_cache[anilist_id] = None
            return None

        media = response.json().get("data", {}).get("Media", {})
        if not media:
            _season_cache[anilist_id] = None
            return None

        # Build cour list: find all prequels and sequels that are TV format
        episodes_per_cour = []
        current_eps = media.get("episodes") or 0

        # Find prequels (earlier cours) and sequels (later cours)
        prequels = []
        sequels = []
        for edge in media.get("relations", {}).get("edges", []):
            node = edge.get("node", {})
            relation = edge.get("relationType", "")
            fmt = node.get("format", "")

            if fmt not in ("TV", "TV_SHORT"):
                continue

            if relation == "PREQUEL":
                prequels.append(node)
            elif relation == "SEQUEL":
                sequels.append(node)

        # Walk prequels backward to build full cour list
        # Note: for a simple 2-cour show, there's one prequel
        prequel_eps = []
        if prequels:
            for p in prequels:
                p_eps = p.get("episodes") or 0
                if p_eps > 0:
                    prequel_eps.append(p_eps)

        # Build ordered list: prequels + current + sequels
        episodes_per_cour = prequel_eps + [current_eps]
        for s in sequels:
            s_eps = s.get("episodes") or 0
            if s_eps > 0:
                episodes_per_cour.append(s_eps)

        result = {"episodes_per_cour": episodes_per_cour}
        _season_cache[anilist_id] = result
        return result

    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"AniList cour data error (id={anilist_id}): {e}", "debug")
        _season_cache[anilist_id] = None
        return None


def _is_cjk(text):
    """Check if text contains CJK (Chinese/Japanese/Korean) characters."""
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text))


def _deduplicate_titles(titles):
    """Deduplicate titles case-insensitively, keeping unique variants."""
    seen_lower = set()
    result = []
    for t in sorted(titles, key=len):
        lower = t.lower().strip()
        if lower and lower not in seen_lower:
            seen_lower.add(lower)
            result.append(t)
    return result


def invalidate_cache():
    """Clear session caches."""
    global _title_cache, _season_cache
    _title_cache = {}
    _season_cache = {}
