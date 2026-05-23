"""
Anime-specific source filtering and ranking.

Ported from Otaku Testing 5.2.81's battle-tested filter_sources() regex
patterns with additions for fansub version preference and group recognition.

Provides:
- Fansub version parsing (v2/v3/v4) with highest-version preference
- Fansub group recognition (sub-only, dual-audio, quality)
- Anime batch/complete series detection
- Part/cour detection in release titles
- TVDB season mapping override
- Advanced anime episode matching patterns
"""

import re

from resources.lib.modules.globals import g


# ── Fansub Version Parsing ────────────────────────────────────────────────────
# Anime fansubs release v2/v3 patches fixing subs or video.  We want the
# highest version of any given release.
#
# Matches: [SubsPlease] Show - 05v2.mkv, Show.S01E05.v3.1080p, EP05v2
# Does NOT match: AV1, DV, HEVC (version-like patterns in codec names)

_VERSION_RE = re.compile(
    r'(?<![a-zA-Z])'          # not preceded by a letter (avoid AV1, DV, etc.)
    r'v(\d)'                   # v + single digit (v2, v3, v4)
    r'(?![a-zA-Z0-9])'        # not followed by alphanumeric (avoid v10bit, v2x)
)


def parse_fansub_version(release_title):
    """Extract the fansub version number from a release title.

    Returns the highest version found (e.g. 2 for "v2"), or 1 if no
    version tag is present (v1 is implied for unversioned releases).

    :param release_title: raw release title string
    :return: int version number (1 = default/unversioned)
    """
    matches = _VERSION_RE.findall(release_title)
    if not matches:
        return 1
    return max(int(v) for v in matches)


# ── Fansub Group Recognition ─────────────────────────────────────────────────
# Known fansub groups categorised by their typical release characteristics.
# Used for sort boosting and display labels.

FANSUB_GROUPS = {
    # Sub-only groups — simulcast rips, sub-focused
    'sub': {
        'subsplease', 'erai-raws', 'erai', 'horriblesubs', 'horrible',
        'nc-raws', 'ohys-raws', 'ohys', 'commie', 'coalgirls', 'gg',
        'underwater', 'vivid', 'doki', 'hiryuu', 'chihiro', 'mazui',
        'utw', 'sakurato', 'yameii', 'nep_blanc',
    },
    # Dual audio groups — typically include both JP and EN audio
    'dual': {
        'judas', 'shiro', 'ember', 'sxales', 'tenrai-sensei',
        'hakata-ramen', 'neolemuria', 'reaktor', 'dual-audio',
        'ssa', 'asakura', 'kaidencore',
    },
    # Quality groups — high bitrate BDRips, often with ordered chapters
    'quality': {
        'kametsu', 'ctr', 'scy', 'kawaiika-raws', 'beatrice-raws',
        'yousei-raws', 'reinforce', 'thd', 'sam', 'flsubs',
        'dragsterps', 'a-l', 'uccuss', 'cleo',
    },
}

# Flat lookup: group_name → category
_GROUP_CATEGORY = {}
for _cat, _groups in FANSUB_GROUPS.items():
    for _grp in _groups:
        _GROUP_CATEGORY[_grp] = _cat

# Regex to extract fansub group from bracket notation: [GroupName]
_GROUP_BRACKET_RE = re.compile(r'^\[([^\]]+)\]')


def get_fansub_group(release_title, anidb_id=None):
    """Extract the fansub group name and category from a release title.

    Two-tier lookup:
    1. AniDB UDP cache (dynamic, per-anime) — if anidb_id provided and cached
    2. Hardcoded FANSUB_GROUPS dict (static fallback — always present)

    :param release_title: raw release title string
    :param anidb_id: optional AniDB ID for per-anime UDP data lookup
    :return: tuple of (group_name, category) where category is
             'sub', 'dual', 'quality', 'complete', 'active', or None
    """
    match = _GROUP_BRACKET_RE.search(release_title)
    if not match:
        return None, None
    group = match.group(1).strip()
    group_lower = group.lower()

    # Tier 1: AniDB UDP cache (per-anime dynamic data)
    if anidb_id:
        try:
            from resources.lib.modules.anime.anidb_udp import get_cached_group_data
            udp_data = get_cached_group_data(anidb_id)
            if udp_data and group_lower in udp_data:
                return group, udp_data[group_lower].get("category")
        except Exception:
            pass

    # Tier 2: Hardcoded group dict (always present)
    category = _GROUP_CATEGORY.get(group_lower)
    return group, category


# ── Anime Batch / Complete Series Detection ───────────────────────────────────
# Enhanced regex for anime batch releases.  These patterns supplement Seren's
# existing season/show pack detection which is geared toward western TV naming.
# Mirrors Otaku's getInfo() BATCH detection plus additional anime-specific
# patterns.

_BATCH_PATTERNS = [
    # Explicit batch keywords (same as Otaku)
    re.compile(r'\bbatch\b', re.IGNORECASE),
    re.compile(r'\bcomplete\s*series\b', re.IGNORECASE),
    re.compile(r'\bcomplete\s*collection\b', re.IGNORECASE),

    # Anime-specific BD/box patterns
    re.compile(r'\bblu-?ray\s*box\b', re.IGNORECASE),
    re.compile(r'\bbd\s*box\b', re.IGNORECASE),

    # Episode range patterns: (01-24), (01~24), [01-24], (01-12+SP)
    re.compile(
        r'[\(\[]\s*\d{1,3}\s*[-~]\s*\d{1,3}'
        r'\s*(?:\+\s*(?:SP|OVA|OAD))?\s*[\)\]]',
        re.IGNORECASE,
    ),

    # "Episodes 1-24", "Eps 01-12"
    re.compile(r'\b(?:episodes?|eps?)\s*\d{1,3}\s*[-~]\s*\d{1,3}\b', re.IGNORECASE),

    # Vol/Volume patterns common in BD releases: Vol.1-4, Volume 1~6
    re.compile(r'\bvol(?:ume)?s?\s*\.?\s*\d+\s*[-~]\s*\d+\b', re.IGNORECASE),
]


def is_anime_batch(release_title):
    """Check if a release title indicates an anime batch/complete release.

    :param release_title: raw release title string
    :return: True if batch patterns detected
    """
    return any(pattern.search(release_title) for pattern in _BATCH_PATTERNS)


# ── Part / Cour Detection ────────────────────────────────────────────────────
# Ported from Otaku's regex_part pattern.

_PART_COUR_RE = re.compile(
    r'(?i)\b(?:part|cour)[ ._-]?(\d+)(?:[&-](\d+))?\b'
)

_ORDINAL_SEASON_RE = re.compile(
    r'\b(\d+)(?:st|nd|rd|th)\s*(?:season|cour)\b',
    re.IGNORECASE,
)


def detect_part_cour(release_title):
    """Detect part/cour number(s) from a release title.

    Handles: "Part 2", "Cour 3", "Part2", "Part 1-2", "2nd Season"

    :param release_title: raw release title string
    :return: list of int part/cour numbers, or empty list
    """
    parts = []

    for match in _PART_COUR_RE.finditer(release_title):
        parts.append(int(match.group(1)))
        if match.group(2):
            parts.append(int(match.group(2)))

    for match in _ORDINAL_SEASON_RE.finditer(release_title):
        val = int(match.group(1))
        if val not in parts:
            parts.append(val)

    return parts


# ── TVDB Season Mapping ──────────────────────────────────────────────────────
# Ported from Otaku's filter_sources() and get_season() logic.
# When thetvdb_season is 'a' (absolute) or 0, override season to None
# so scrapers/filters search without a season constraint.

def get_tvdb_season_override(mal_id=None, imdb_id=None, tmdb_id=None, trakt_id=None):
    """Check Otaku-Mappings DB for TVDB season override.

    Ported from Otaku's filter_sources() + get_season() logic.
    When thetvdb_season is 'a' (absolute) or 0, returns None so
    scrapers/filters search without a season constraint.

    :return: int season number if mapped, None if season should be ignored
             (absolute/specials), or False if no mapping found.
    """
    try:
        from resources.lib.modules.anime.anilist_mapping import get_anime_ids
        ids = get_anime_ids(
            imdb_id=imdb_id or None,
            tmdb_id=tmdb_id or None,
            trakt_id=trakt_id or None,
        )
        if not ids:
            return False

        tvdb_season = ids.get('thetvdb_season')
        if tvdb_season is None:
            return False

        # Absolute ordering or specials → no season filter
        if str(tvdb_season) in ('a', '0'):
            return None

        try:
            return int(tvdb_season)
        except (ValueError, TypeError):
            return False
    except Exception as e:
        g.log(f"TVDB season override lookup failed: {e}", "warning")
        return False


# ── Advanced Anime Episode Regex ──────────────────────────────────────────────
# Ported from Otaku's filter_sources() regex patterns.

# Clean text for extraction (remove codec/quality info that confuses numbers)
_REMOVE_INFO_PATTERNS = re.compile(
    r'\b(?:360p|480p|720p|1080p|2160p|4k)\b'
    r'|\b10\s?bits?\b'
    r'|\b(?:h\.?\s?264|x\.?\s?264|h\.?\s?265|x\.?\s?265|hevc|avc)\b'
    r'|\b(?:web-?dl|webrip|bluray|hdrip|dvdrip|hdtv|pdtv)\b'
    r'|\b(?:hdr10|hdr|sdr|dv|dolby\s?vision|dovi)\b'
    r'|\b(?:mp4|vp9|av1|mpeg|xvid|divx|wmv|flac)\b'
    r'|\b(?:aac|mp3|opus|ddp|dd[257]?|ac3|dts(?:-hdma|-hdhr|-x)?|atmos|truehd)\b'
    r'|\b(?:multi\s?audio|dual\s?audio|dub(?:bed)?|multi\s?sub|batch|complete\s?series)\b',
    re.IGNORECASE,
)

_CLEANUP_BRACKETS = re.compile(r'\[.*?\]|\(.*?\)')
_CLEANUP_SPECIAL = re.compile(r'[:/,!?()\'"\\._]')
_CLEANUP_SPACES = re.compile(r'\s+')


def _clean_text_for_episode(title):
    """Clean a release title for episode number extraction.

    Removes codec/quality tags, bracket content, and fansub version tags
    that could contain confusing numbers.  Mirrors Otaku's clean_text()
    pipeline with added v-tag stripping.
    """
    text = _REMOVE_INFO_PATTERNS.sub('', title)
    text = _CLEANUP_BRACKETS.sub('', text).strip()
    # Strip fansub version tags (v2, v3) so "05v2" becomes "05"
    text = _VERSION_RE.sub('', text)
    text = _CLEANUP_SPECIAL.sub(' ', text)
    return _CLEANUP_SPACES.sub(' ', text).strip()


# Episode extraction regexes (from Otaku's filter_sources)
_RE_SEASON = re.compile(r'(?i)\b(?:s(?:eason)?[ ._-]?(\d{1,2}))(?!\d)')

_RE_EPISODE = re.compile(r"""(?ix)
    (?:^|[\s._-])                     # separator
    (?:e(?:p)?\s?(\d{1,4}))           # E12, EP12
    |
    -\s?(\d{1,4})\b                   # - 12
    |
    \b(?:episode|ep|e)\s?(\d{1,4})\b  # ep 03
    |
    s\d{1,2}e(\d{1,4})               # s01e07
    |
    (\d{1,4})\s+(\d{1,4})            # standalone episode range
""")

_RE_EPISODE_RANGE = re.compile(r'(\d{1,4})\s*[~\-]\s*(\d{1,4})')

_RE_TRAILING_NUMBER = re.compile(r'(?ix)\b(?:[a-z]{3,})\s+(\d{1,3})\b')

_RE_ORDINAL_CHECK = re.compile(r'\b\d+(?:st|nd|rd|th)\b', re.IGNORECASE)


def extract_episode_info(release_title, part_nums=None):
    """Extract episode number(s) from an anime release title.

    Uses Otaku's multi-stage extraction logic:
    1. SxxExx pattern
    2. Episode range with ~ or -
    3. EP/e/episode prefix patterns, dash-separated numbers
    4. Trailing number fallback

    :param release_title: raw release title string
    :param part_nums: list of detected part numbers to exclude from episode matching
    :return: tuple of (episode_list, season_list)
    """
    title_lower = release_title.lower()
    clean = _clean_text_for_episode(title_lower)
    part_strs = {str(p) for p in (part_nums or [])}

    # Extract seasons
    season_matches = _RE_SEASON.findall(title_lower)
    seasons = [int(s) for s in season_matches if s]

    # Remove part tokens from clean title for episode extraction
    clean_no_parts = _PART_COUR_RE.sub('', clean)

    episodes = []

    # Stage 1: SxxExx
    se_match = re.search(r'(?i)s\d{1,2}e(\d{1,4})', clean_no_parts)
    if se_match:
        epnum = se_match.group(1)
        if epnum not in part_strs:
            return [int(epnum)], seasons

    # Stage 2: Episode range (~ or -)
    range_match = _RE_EPISODE_RANGE.search(clean_no_parts)
    if range_match:
        start, end = range_match.group(1), range_match.group(2)
        if start not in part_strs and end not in part_strs:
            try:
                return list(range(int(start), int(end) + 1)), seasons
            except (ValueError, TypeError):
                pass

    # Stage 3: EP/e/episode patterns, dash-number
    ep_matches = _RE_EPISODE.findall(clean_no_parts)
    if ep_matches:
        found = []
        for match in ep_matches:
            for group in match:
                if group and group not in part_strs:
                    found.append(group)

        # Drop leading number if it matches a season
        if seasons and found:
            try:
                if found[0].isdigit() and int(found[0]) in seasons:
                    found = found[1:]
            except (ValueError, IndexError):
                pass

        if len(found) >= 2 and found[0].isdigit() and found[-1].isdigit():
            try:
                episodes = list(range(int(found[0]), int(found[-1]) + 1))
            except (ValueError, TypeError):
                episodes = [int(f) for f in found if f.isdigit()]
        elif found:
            episodes = [int(f) for f in found if f.isdigit()]

        if episodes:
            return episodes, seasons

    # Stage 4: Trailing number fallback
    trail_matches = _RE_TRAILING_NUMBER.findall(clean_no_parts)
    if trail_matches:
        last_num = trail_matches[-1]
        if last_num not in part_strs:
            if seasons:
                try:
                    if last_num.isdigit() and int(last_num) in seasons:
                        return [], seasons
                    if not _RE_ORDINAL_CHECK.search(clean_no_parts):
                        return [int(last_num)], seasons
                except (ValueError, TypeError):
                    pass
            elif not _RE_ORDINAL_CHECK.search(clean_no_parts):
                return [int(last_num)], seasons

    return episodes, seasons


def anime_episode_match(release_title, target_episode, target_season=None, target_part=None):
    """Check if a release title matches target episode/season/part.

    Ported from Otaku's filter_sources() validation logic.

    :param release_title: raw release title
    :param target_episode: int episode number to match
    :param target_season: int season number (or None to skip season check)
    :param target_part: int part/cour number (or None to skip)
    :return: True if matches, False if should be filtered out,
             None if no extractable info (batch/pack — keep it)
    """
    parts = detect_part_cour(release_title)
    episodes, seasons = extract_episode_info(release_title, part_nums=parts)

    has_info = bool(episodes or seasons or parts)
    if not has_info:
        return None  # no info → likely a batch/pack, keep it

    # Check episode
    if target_episode is not None and episodes:
        try:
            if int(target_episode) not in episodes:
                return False
        except (ValueError, TypeError):
            return False

    # Check season
    if target_season is not None and seasons:
        try:
            if int(target_season) not in seasons:
                return False
        except (ValueError, TypeError):
            return False

    # Check part/cour
    if target_part is not None and parts:
        try:
            if int(target_part) not in parts:
                return False
        except (ValueError, TypeError):
            return False

    return True


# ── Version-Based Sort Key ────────────────────────────────────────────────────

def get_version_sort_key(source):
    """Sort key that prefers higher fansub versions.

    :param source: source dict with 'release_title'
    :return: int version number for sorting (higher = better)
    """
    return parse_fansub_version(source.get('release_title', ''))
