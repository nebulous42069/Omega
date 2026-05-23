"""Anime-Skip API client — community anime skip timestamps via GraphQL.

API: https://api.anime-skip.com/graphql
Uses a permanent client ID (shared with Otaku community).
Uses AniList ID for lookups.
Provides typed timestamps: Intro, Credits, Canon, Preview, Branding, etc.
"""

import requests

from resources.lib.modules.globals import g

ANIME_SKIP_URL = "https://api.anime-skip.com/graphql"
ANIME_SKIP_CLIENT_ID = "buT57NJMu4G65vxGJWdj4UXgnq65Agfi"

ANIME_SKIP_HEADERS = {
    "X-Client-ID": ANIME_SKIP_CLIENT_ID,
    "Content-Type": "application/json",
    "User-Agent": "Seren",
}


def get_episode_ids(anilist_id, episode_number):
    """Find Anime-Skip episode IDs for an anime episode.

    Args:
        anilist_id: AniList ID (string or int)
        episode_number: Episode number (int)

    Returns:
        list of Anime-Skip episode ID strings, or empty list
    """
    if not anilist_id or not episode_number:
        return []

    query = """
    query($service: ExternalService!, $serviceId: String!) {
        findShowsByExternalId(service: $service, serviceId: $serviceId) {
            episodes {
                id
                number
            }
        }
    }
    """
    variables = {"service": "ANILIST", "serviceId": str(anilist_id)}

    try:
        response = requests.post(
            ANIME_SKIP_URL,
            headers=ANIME_SKIP_HEADERS,
            json={"query": query, "variables": variables},
            timeout=5,
        )
        if not response.ok:
            return []

        data = response.json()
        shows = data.get("data", {}).get("findShowsByExternalId", [])

        id_list = []
        for show in shows:
            for ep in show.get("episodes", []):
                if ep.get("number") and int(ep["number"]) == int(episode_number):
                    id_list.append(ep["id"])
        return id_list

    except (requests.RequestException, ValueError, KeyError) as e:
        g.log(f"Anime-Skip episode lookup error (AniList={anilist_id}, ep={episode_number}): {e}", "warning")
        return []


def get_timestamps(episode_ids):
    """Fetch typed timestamps for Anime-Skip episode IDs.

    Args:
        episode_ids: list of Anime-Skip episode ID strings

    Returns:
        list of timestamp dicts: [{'at': float, 'type': {'name': str}}, ...]
        or empty list
    """
    if not episode_ids:
        return []

    query = """
    query($episodeId: ID!) {
        findTimestampsByEpisodeId(episodeId: $episodeId) {
            at
            type {
                name
            }
        }
    }
    """

    for ep_id in episode_ids:
        try:
            response = requests.post(
                ANIME_SKIP_URL,
                headers=ANIME_SKIP_HEADERS,
                json={"query": query, "variables": {"episodeId": ep_id}},
                timeout=5,
            )
            if not response.ok:
                continue

            data = response.json()
            timestamps = data.get("data", {}).get("findTimestampsByEpisodeId", [])
            if timestamps:
                return timestamps

        except (requests.RequestException, ValueError, KeyError) as e:
            g.log(f"Anime-Skip timestamp error (ep_id={ep_id}): {e}", "warning")
            continue

    return []


def get_skip_times(anilist_id, episode_number):
    """Get intro and outro skip times from Anime-Skip.

    Combines get_episode_ids + get_timestamps + parses typed timestamps
    into intro/outro start/end pairs.

    Args:
        anilist_id: AniList ID (string or int)
        episode_number: Episode number (int)

    Returns:
        dict with optional 'intro' and 'outro' keys, each containing
        {'start': int, 'end': int} in seconds. Returns None if no data.
    """
    episode_ids = get_episode_ids(anilist_id, episode_number)
    if not episode_ids:
        return None

    timestamps = get_timestamps(episode_ids)
    if not timestamps:
        return None

    result = {}
    intro_start = None
    intro_end = None
    outro_start = None
    outro_end = None

    for ts in timestamps:
        ts_type = ts.get("type", {}).get("name", "")
        ts_at = ts.get("at")
        if ts_at is None:
            continue

        # Intro detection
        if intro_start is None and ts_type in ("Intro", "New Intro", "Branding"):
            intro_start = int(ts_at)
        elif intro_start is not None and intro_end is None and ts_type == "Canon":
            intro_end = int(ts_at)

        # Outro detection
        if outro_start is None and ts_type in ("Credits", "New Credits", "Mixed Credits"):
            outro_start = int(ts_at)
        elif outro_start is not None and outro_end is None and ts_type in ("Canon", "Preview"):
            outro_end = int(ts_at)

    if intro_start is not None and intro_end is not None:
        result["intro"] = {"start": intro_start, "end": intro_end}
    if outro_start is not None and outro_end is not None:
        result["outro"] = {"start": outro_start, "end": outro_end}

    return result if result else None
