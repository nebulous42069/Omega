"""AniDB character and episode rating data — thin wrappers over anidb_data.py.

get_anime_cast(anidb_id)       → list of Kodi setCast() dicts
get_episode_ratings(anidb_id)  → {ep_num: {rating, votes}}

Both functions delegate to anidb_data.get_anidb_data() which owns the single
shared XML fetch and 30-day SQLite cache. No direct API calls are made here.
All failures return empty results — never raises.
"""

from resources.lib.modules.globals import g


def get_anime_cast(anidb_id):
    """Return voice actor cast for an anime in Kodi setCast() format.

    Args:
        anidb_id: AniDB anime ID (int)

    Returns:
        list of dicts: [{'name': str, 'role': str, 'thumbnail': str, 'order': int}]
        name      = character name (e.g. "Eren Yeager")
        role      = voice actor name (e.g. "Kaji, Yuuki")
        thumbnail = seiyuu photo URL from AniDB CDN (may be empty string)
        order     = display order (main characters first)
        Returns [] on failure or if no characters available.
    """
    if not anidb_id:
        return []
    try:
        from resources.lib.modules.anime.anidb_data import get_anidb_data
        data = get_anidb_data(anidb_id)
        if not data:
            return []
        cast = data.get("characters", [])
        if cast:
            g.log(f"AniDB cast: {len(cast)} characters for anidb_id={anidb_id}", "debug")
        return cast
    except Exception as e:
        g.log(f"AniDB cast fetch failed (anidb_id={anidb_id}): {e}", "debug")
        return []


def get_episode_ratings(anidb_id):
    """Return per-episode ratings from AniDB.

    Args:
        anidb_id: AniDB anime ID (int)

    Returns:
        dict: {ep_num(int): {'rating': float, 'votes': int}}
        Returns {} on failure or if no ratings available.
    """
    if not anidb_id:
        return {}
    try:
        from resources.lib.modules.anime.anidb_data import get_anidb_data
        data = get_anidb_data(anidb_id)
        if not data:
            return {}
        return data.get("ratings", {})
    except Exception as e:
        g.log(f"AniDB episode ratings fetch failed (anidb_id={anidb_id}): {e}", "debug")
        return {}
