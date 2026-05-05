import requests
import datetime
from requests.adapters import HTTPAdapter
from resources.utils import giptv
from urllib3.util.retry import Retry
import xbmc
import json

from resources.lib.manager.fetch_manager import cache_handler
from resources.utils.config import ensure_api_ready
from resources.utils.xtream import STATE

# Required User-Agent to mimic a browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
# ------------------------------------------------------------
# Robust shared HTTP session for Xtream API
# ------------------------------------------------------------
_session = None


def get_session():
    global _session

    if _session is not None:
        return _session

    session = requests.Session()

    retry = Retry(
        total=5,  # total retries
        connect=3,
        read=3,
        backoff_factor=1.2,  # exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update(HEADERS)

    _session = session
    return _session


LIVE_TYPE = "live"  # Standard API key for Live TV
VOD_TYPE = "vod"  # Standard API key for Movies
SERIES_TYPE = "series"  # Standard API key for Series


def stream_supports_catchup(stream_obj):
    """
    stream_obj = item from get_live_streams()
    """
    return (
        str(stream_obj.get("tv_archive")) == "1"
        and int(stream_obj.get("tv_archive_duration", 0)) > 0
    )


# --- Core API Calls ---


def authenticate():
    """Authenticates user credentials and returns the JSON response."""
    if not ensure_api_ready():
        return None

    url = get_authenticate_URL()
    try:
        response = get_session().get(url, timeout=(5, 20))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        giptv.log(f"Xtream API Authentication Error: {e}", xbmc.LOGERROR)
        return None


def categories(streamType):
    """Fetches categories for Live, VOD, or Series streams."""
    if not ensure_api_ready():
        return None

    if streamType == LIVE_TYPE:
        url = get_live_categories_URL()
    elif streamType == VOD_TYPE:
        url = get_vod_cat_URL()
    elif streamType == SERIES_TYPE:
        url = get_series_cat_URL()
    else:
        return None

    try:
        response = get_session().get(url, timeout=(5, 20))
        response.raise_for_status()
        cache_handler.set(
            "categories", f"{STATE.username}_{streamType}", response.json()
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        giptv.log(
            f"Xtream API Category Fetch Error for {streamType}: {e}", xbmc.LOGERROR
        )
        return None


def streams_by_category(streamType, category_id):
    """Fetches streams within a specific category."""
    if not ensure_api_ready():
        return None

    if streamType == LIVE_TYPE:
        url = get_live_streams_URL_by_category(category_id)
    elif streamType == VOD_TYPE:
        url = get_vod_streams_URL_by_category(category_id)
    elif streamType == SERIES_TYPE:
        url = get_series_URL_by_category(category_id)
    else:
        return None

    try:
        response = get_session().get(url, timeout=(5, 20))
        response.raise_for_status()
        cache_handler.set(
            streamType, f"{STATE.username}_{streamType}_{category_id}", response.json()
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        giptv.log(f"Xtream API Stream Fetch Error for {streamType}: {e}", xbmc.LOGERROR)
        return None


def series_info_by_id(series_id):
    """Fetches detailed information, including episodes, for a specific TV series ID."""
    if not ensure_api_ready():
        return None

    url = get_series_info_URL_by_ID(series_id)
    try:
        response = get_session().get(url, timeout=(5, 20))
        response.raise_for_status()
        cache_handler.set(
            "series_info", f"{STATE.username}_{series_id}", response.json()
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        giptv.log(
            f"Xtream API Series Info Fetch Error for ID {series_id}: {e}", xbmc.LOGERROR
        )
        return None


# --- Stream URL Builder ---


def build_stream_url(stream_id, stream_type, container_extension="ts"):
    api_path_map = {
        "live": "live",
        "vod": "movie",
        "series": "series",
    }
    api_path = api_path_map.get(stream_type.lower())
    if not api_path or not ensure_api_ready():
        return None

    return f"{STATE.server.rstrip('/')}/{api_path}/{STATE.username}/{STATE.password}/{stream_id}.{container_extension}"


# --- URL-builder methods ---


def get_authenticate_URL():
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}"


def get_live_categories_URL():
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_live_categories"


def get_live_streams_URL_by_category(category_id):
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_live_streams&category_id={category_id}"


def get_vod_cat_URL():
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_vod_categories"


def get_vod_streams_URL_by_category(category_id):
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_vod_streams&category_id={category_id}"


def get_series_cat_URL():
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_series_categories"


def get_series_URL_by_category(category_id):
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_series&category_id={category_id}"


def get_series_info_URL_by_ID(series_id):
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_series_info&series_id={series_id}"


def get_live_epg_URL_by_stream(stream_id):
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_short_epg&stream_id={stream_id}"

def get_simple_data_table(stream_id):
    return f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_simple_data_table&stream_id={stream_id}"


def build_timeshift_url(stream_id, start_ts, duration_minutes):
    """
    start_ts = unix timestamp (int)
    duration_minutes = int
    """
    dt = datetime.datetime.fromtimestamp(start_ts)

    date_part = dt.strftime("%Y-%m-%d:%H-%M")

    return (
        f"{STATE.server.rstrip('/')}/timeshift/"
        f"{STATE.username}/{STATE.password}/"
        f"{duration_minutes}/{date_part}/{stream_id}.ts"
    )


def get_live_streams():
    """Fetches the list of live streams from the Xtream API."""
    if not ensure_api_ready():
        return None

    URL = f"{STATE.server}/player_api.php?username={STATE.username}&password={STATE.password}&action=get_live_streams"
    redacted_url = f"{STATE.server}/player_api.php?username=XXX&password=XXX&action=get_live_streams"
    giptv.log(
        f"Xtream API: Attempting to fetch live streams from {redacted_url}",
        xbmc.LOGDEBUG,
    )

    try:
        response = get_session().get(URL, timeout=(5, 20))
        response.raise_for_status()
        data = response.json()

        # Handle API auth errors
        if isinstance(data, dict):
            if data.get("user_info", {}).get("auth") == 0:
                error_message = data.get("user_info", {}).get(
                    "message", "Authentication failed."
                )
                giptv.log(
                    f"Xtream API Authentication Failed: {error_message}", xbmc.LOGERROR
                )
                return []
            if "message" in data:
                giptv.log(
                    f"Xtream API Response Error: {data['message']}", xbmc.LOGERROR
                )
                return []

        if isinstance(data, list):
            original_count = len(data)
            filtered_streams = [s for s in data if s.get("epg_channel_id")]
            skipped_count = original_count - len(filtered_streams)
            giptv.log(
                f"Xtream API: Fetched {original_count} live streams, skipped {skipped_count}.",
                xbmc.LOGINFO,
            )
            return filtered_streams

        giptv.log(
            f"Xtream API: Unexpected response format: {str(data)[:100]}", xbmc.LOGERROR
        )
        return []

    except requests.exceptions.RequestException as e:
        giptv.log(f"Xtream API Network Error for {STATE.server}: {e}", xbmc.LOGERROR)
        return None
    except json.JSONDecodeError as e:
        giptv.log(f"Xtream API Decoding Error for {STATE.server}: {e}", xbmc.LOGERROR)
        return None
    except Exception as e:
        giptv.log(f"Xtream API Unexpected Error: {e}", xbmc.LOGERROR)
        return None
