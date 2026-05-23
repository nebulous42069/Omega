"""AniSkip API client — community-maintained anime intro/outro skip timestamps.

API docs: https://api.aniskip.com/api-docs
Endpoint: GET /v2/skip-times/{mal_id}/{episode_number}
No auth required. Returns skip timestamps by type (op, ed, recap, mixed-op, mixed-ed).
"""

import requests

from resources.lib.modules.globals import g

ANISKIP_BASE_URL = "https://api.aniskip.com/v2/skip-times"


def get_skip_times(mal_id, episode_number, skip_type):
    """Fetch skip timestamps for an anime episode.

    Args:
        mal_id: MyAnimeList ID (int or string)
        episode_number: Episode number (int)
        skip_type: Type of skip — 'op' (intro), 'ed' (outro), 'recap', 'mixed-op', 'mixed-ed'

    Returns:
        dict with 'results' list containing interval data, or None on failure.
        Each result has: {'interval': {'startTime': float, 'endTime': float}, 'skipType': str}
    """
    if not mal_id or not episode_number:
        return None

    try:
        url = f"{ANISKIP_BASE_URL}/{mal_id}/{int(episode_number)}"
        params = {"types": skip_type, "episodeLength": 0}
        response = requests.get(url, params=params, timeout=5, headers={"User-Agent": "Seren"})

        if not response.ok:
            return None

        data = response.json()
        if data.get("found") and data.get("results"):
            return data

        return None

    except requests.RequestException as e:
        g.log(f"AniSkip API error (MAL={mal_id}, ep={episode_number}, type={skip_type}): {e}", "warning")
        return None
    except (ValueError, KeyError) as e:
        g.log(f"AniSkip parse error: {e}", "warning")
        return None


def get_intro_times(mal_id, episode_number):
    """Get intro (opening) skip times for an episode.

    Returns:
        tuple of (start_time, end_time) in seconds, or (None, None)
    """
    result = get_skip_times(mal_id, episode_number, "op")
    if result and result.get("results"):
        interval = result["results"][0]["interval"]
        return int(interval["startTime"]), int(interval["endTime"])
    return None, None


def get_outro_times(mal_id, episode_number):
    """Get outro (ending) skip times for an episode.

    Returns:
        tuple of (start_time, end_time) in seconds, or (None, None)
    """
    result = get_skip_times(mal_id, episode_number, "ed")
    if result and result.get("results"):
        interval = result["results"][0]["interval"]
        return int(interval["startTime"]), int(interval["endTime"])
    return None, None
