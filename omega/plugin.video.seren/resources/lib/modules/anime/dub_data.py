"""Anime dub/sub awareness — audio classification, source filtering, and sort boost.

Ported from Otaku Testing 5.2.88's dub/sub system with adaptations for Seren's
architecture.

Provides:
- Audio language classification (Otaku's getAudio_lang pattern): every source gets
  a numeric lang code (0=multi, 1=dual, 2=sub/none, 3=dub)
- Hard source filtering (Otaku's general.source pattern): remove sources that don't
  match user's dub/sub preference
- Sort boost scoring: rank matching sources higher within the filtered set
- MAL-Dubs JSON for show-level dub availability (same source as Otaku)

Preference modes (anime.dubSubPreference):
  0 = No Preference  — no filter, no boost
  1 = Prefer Dubbed   — filter + boost dub/dual-audio sources
  2 = Prefer Subbed   — filter + boost sub/quality fansub sources

Filter behavior (matches Otaku's general.source):
  Prefer Dubbed: keep sources where lang in [0, 1, 3] (multi, dual, dub)
  Prefer Subbed: keep sources where lang in [0, 1, 2] (multi, dual, sub)
  Multi-audio and dual-audio always pass both filters.
"""

import json
import os
import time

from resources.lib.modules.globals import g

# MAL-Dubs JSON — same source as Otaku
_MAL_DUBS_URL = 'https://raw.githubusercontent.com/MAL-Dubs/MAL-Dubs/main/data/dubInfo.json'
_mal_dub_cache = None


# ═══════════════════════════════════════════════════════════════════════════
#  Audio Language Classification (ported from Otaku's getAudio_lang)
# ═══════════════════════════════════════════════════════════════════════════

# Lang codes (same as Otaku):
#   0 = MULTI-AUDIO
#   1 = DUAL-AUDIO
#   2 = SUB / none (default — no dub indicators found)
#   3 = DUB (dubbed only, no dual audio)

LANG_MULTI = 0
LANG_DUAL = 1
LANG_SUB = 2
LANG_DUB = 3


def classify_audio_lang(source):
    """Classify a source's audio language type from its info tags.

    Uses Seren's existing info set (DUAL-AUDIO, MULTI-AUDIO, DUB) which are
    already parsed by source_utils.py during scraping.

    Also checks fansub group category for additional signal when info tags
    are absent.

    Args:
        source: source dict with 'info' (set) and 'release_title' (str)

    Returns:
        int lang code: 0=multi, 1=dual, 2=sub, 3=dub
    """
    info_tags = source.get('info', set())

    if 'MULTI-AUDIO' in info_tags:
        return LANG_MULTI
    if 'DUAL-AUDIO' in info_tags:
        return LANG_DUAL
    if 'DUB' in info_tags:
        return LANG_DUB

    # Check fansub group for additional signal
    from resources.lib.modules.anime.source_filter import get_fansub_group
    _name, category = get_fansub_group(source.get('release_title', ''))  # anidb_id not available here
    if category == 'dual':
        return LANG_DUAL

    return LANG_SUB


# ═══════════════════════════════════════════════════════════════════════════
#  Hard Source Filter (ported from Otaku's general.source filter)
# ═══════════════════════════════════════════════════════════════════════════

def should_filter_source(source, preference):
    """Check if a source should be filtered out based on dub/sub preference.

    Matches Otaku's hard filter logic from pages/__init__.py:
      Sub mode: keep lang in [0, 1, 2] (multi, dual, sub) — remove dub-only
      Dub mode: keep lang in [0, 1, 3] (multi, dual, dub) — remove sub-only

    Multi-audio and dual-audio always pass both filters.

    Args:
        source: source dict
        preference: int (0=none, 1=dubbed, 2=subbed)

    Returns:
        True if source should be REMOVED (filtered out), False to keep.
    """
    if preference == PREF_NONE:
        return False

    lang = classify_audio_lang(source)

    if preference == PREF_DUBBED:
        # Keep multi(0), dual(1), dub(3) — remove sub-only(2)
        return lang == LANG_SUB
    elif preference == PREF_SUBBED:
        # Keep multi(0), dual(1), sub(2) — remove dub-only(3)
        return lang == LANG_DUB

    return False


# ═══════════════════════════════════════════════════════════════════════════
#  Sort Boost Scoring
# ═══════════════════════════════════════════════════════════════════════════

# Preference values matching settings.xml:
PREF_NONE = 0
PREF_DUBBED = 1
PREF_SUBBED = 2


def get_dub_sub_sort_score(source, preference, anidb_id=None):
    """Calculate a sort boost score based on dub/sub preference.

    Combines audio lang classification with fansub group quality signal.
    If anidb_id is provided, uses AniDB UDP cache for group lookup first.

    Args:
        source: source dict with 'release_title' and 'info' (set of tags)
        preference: int (0=none, 1=dubbed, 2=subbed)
        anidb_id: optional AniDB ID for per-anime UDP fansub group data

    Returns:
        int sort score (higher = better match). Range: 0–10.
    """
    if preference == PREF_NONE:
        return 0

    lang = classify_audio_lang(source)

    # Get fansub group category for tiebreaking (UDP tier first if anidb_id known)
    from resources.lib.modules.anime.source_filter import get_fansub_group
    _name, group_cat = get_fansub_group(source.get('release_title', ''), anidb_id=anidb_id)

    if preference == PREF_DUBBED:
        # Otaku sort order: multi(0) > dual(1) > dub(3) > sub(2)
        if lang == LANG_MULTI:
            return 10
        elif lang == LANG_DUAL:
            return 8
        elif lang == LANG_DUB:
            return 6
        elif group_cat == 'quality':
            # Quality BDRips often include dual audio
            return 3
        else:
            return 1

    elif preference == PREF_SUBBED:
        # Otaku sort order: multi(0) > dual(1) > sub(2) > dub(3)
        if lang == LANG_MULTI:
            return 10
        elif lang == LANG_DUAL:
            return 8
        elif lang == LANG_SUB:
            if group_cat == 'sub':
                return 7  # Known sub group
            elif group_cat == 'quality':
                return 6  # Quality group (excellent subs)
            else:
                return 5  # Default sub
        else:
            return 1  # DUB — lowest for sub preference

    return 0


# ═══════════════════════════════════════════════════════════════════════════
#  MAL-Dubs JSON — Show-Level Dub Availability
#  (same source as Otaku: github.com/MAL-Dubs/MAL-Dubs)
# ═══════════════════════════════════════════════════════════════════════════

def has_dub(mal_id):
    """Check if an anime has a known English dub via MAL-Dubs database.

    Args:
        mal_id: MyAnimeList ID (int or str)

    Returns:
        bool: True if dub is available.
    """
    dub_data = _get_mal_dub_data()
    return str(mal_id) in dub_data


def update_mal_dub_json():
    """Download or update the MAL-Dubs JSON from GitHub.

    Same source and pattern as Otaku's service.py update_dub_json().
    Called from service.py at startup. Skips if updated within 7 days.
    """
    global _mal_dub_cache
    dub_file = _get_mal_dub_path()

    # Skip if recently updated
    if os.path.exists(dub_file):
        age_days = (time.time() - os.path.getmtime(dub_file)) / 86400
        if age_days < 7:
            g.log(f"MAL-Dubs JSON is {age_days:.1f} days old, skipping update", "debug")
            return True

    g.log("Updating MAL-Dubs JSON...", "info")
    try:
        import requests
        response = requests.get(_MAL_DUBS_URL, timeout=10, headers={"User-Agent": "Seren"})
        if response.ok:
            data = response.json()
            dub_list = data.get("dubbed", [])
            mal_dub = {str(item): {'dub': True} for item in dub_list}
            with open(dub_file, 'w') as f:
                json.dump(mal_dub, f)
            _mal_dub_cache = mal_dub
            g.log(f"MAL-Dubs updated: {len(mal_dub)} entries", "info")
            return True
        else:
            g.log(f"MAL-Dubs download failed: HTTP {response.status_code}", "warning")
            return False
    except Exception as e:
        g.log(f"MAL-Dubs update failed: {e}", "warning")
        return False


def _get_mal_dub_data():
    """Load MAL-Dubs data (cached in memory after first read)."""
    global _mal_dub_cache
    if _mal_dub_cache is None:
        dub_file = _get_mal_dub_path()
        try:
            with open(dub_file) as f:
                _mal_dub_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _mal_dub_cache = {}
    return _mal_dub_cache


def _get_mal_dub_path():
    """Path to the MAL-Dubs JSON file in Seren's userdata."""
    return os.path.join(g.ADDON_USERDATA_PATH, 'mal_dub.json')
