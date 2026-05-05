# Python 2/3 compatibility for URL parsing
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import urllib.request
import urllib.parse
import json
import base64

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib.manager import history_manager
import resources.apis.xtream_api as xtream_api
import resources.lib.navigator as navigator
import resources.utils.giptv as giptv
from resources.lib.manager.history_manager import clear_history
from resources.lib.cache.history_cache import enqueue_write
from resources.lib.proxy.proxy_instance import ensure_proxy_running
from resources.lib.manager.favourites_manager import (
    list_favourites,
    add_favourite_from_params,
    remove_favourite_from_params,
)
import resources.lib.manager.search_manager as search

ADDON = xbmcaddon.Addon()


def open_addon_settings():
    giptv.open_settings()


def _decode_meta(meta_value):
    if not meta_value:
        return {}
    try:
        raw = base64.urlsafe_b64decode(meta_value.encode("utf-8")).decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        giptv.log(f"Failed to decode meta: {e}", xbmc.LOGWARNING)
        return {}


def build_stream_fallbacks(url):
    fallbacks = [url]

    if url.endswith(".ts"):
        fallbacks.append(url[:-3] + ".m3u8")

    base = url.rsplit(".", 1)[0]
    fallbacks.append(base)

    seen = set()
    out = []
    for u in fallbacks:
        if u not in seen:
            out.append(u)
            seen.add(u)

    return out


HEADER_PROFILES = [
    {"User-Agent": "VLC/3.0.20 LibVLC/3.0.20"},
    {"User-Agent": "Lavf/60.16.100"},
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    },
]


def open_with_rotating_headers(url, timeout):
    for headers in HEADER_PROFILES:
        try:
            giptv.log(f"Trying headers: {headers['User-Agent']}", xbmc.LOGINFO)
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=timeout)
        except Exception as e:
            giptv.log(f"Header failed: {e}", xbmc.LOGINFO)

    raise RuntimeError("All header profiles failed to open stream")


def stream_responds(url, timeout=2):
    try:
        with open_with_rotating_headers(url, timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _is_vod_url(url):
    url_lower = url.lower()
    return (
        url_lower.endswith((".mkv", ".mp4"))
        or "/movie/" in url_lower
        or "/series/" in url_lower
        or "vod" in url_lower
    )


def _is_hls_url(url):
    return ".m3u8" in url.lower()


def _detect_stream_type(url):
    url_lower = url.lower()
    if "/live/" in url_lower:
        return "live"
    if "/movie/" in url_lower or "vod" in url_lower:
        return "vod"
    return "series"


def _extract_stream_id(url):
    last_part = url.split("/")[-1]
    return last_part.split(".")[0]


def _write_history_entry(url, name, stream_type, metadata=None):
    metadata = metadata or {}

    stream_id = metadata.get("stream_id") or _extract_stream_id(url)

    entry = {
        "item_id": stream_id,
        "title": name,
        "stream_type": stream_type,
        "thumb": metadata.get("thumb", ""),
        "fanart": metadata.get("fanart", ""),
        "poster": metadata.get("poster", ""),
        "icon": metadata.get("icon", ""),
        "plot": metadata.get("plot", ""),
        "rating": metadata.get("rating", 0),
        "year": metadata.get("year", 0),
        "tmdb_id": metadata.get("tmdb_id", ""),
        "channel_id": metadata.get("channel_id", ""),
        "play_url": url,
    }

    enqueue_write(entry)


def _resolve_direct_stream(url, name, is_live=False, metadata=None):
    metadata = metadata or {}

    stream_type = metadata.get("stream_type") or _detect_stream_type(url)
    if is_live and stream_type == "series":
        stream_type = "live"

    li = xbmcgui.ListItem(path=url)
    li.setLabel(name)
    li.setProperty("IsPlayable", "true")
    li.setContentLookup(False)
    li.setProperty("seekable", "false" if is_live else "true")

    if is_live:
        li.setProperty("isLive", "true")

    _write_history_entry(url, name, stream_type, metadata=metadata)
    xbmcplugin.setResolvedUrl(navigator.PLUGIN_HANDLE, True, li)


def _resolve_proxied_stream(url, name, port, metadata=None, is_live=True):
    metadata = metadata or {}

    proxied = "http://127.0.0.1:{}/stream?u={}".format(
        port,
        urllib.parse.quote(url, safe=""),
    )

    giptv.log(f"Using proxied stream: {proxied}", xbmc.LOGINFO)

    li = xbmcgui.ListItem(path=proxied)
    li.setLabel(name)
    li.setProperty("IsPlayable", "true")
    li.setContentLookup(False)
    li.setProperty("isLive", "true" if is_live else "false")
    li.setProperty("seekable", "false" if is_live else "true")

    stream_type = metadata.get("stream_type") or (
        "live" if is_live else _detect_stream_type(url)
    )

    _write_history_entry(url, name, stream_type, metadata=metadata)
    xbmcplugin.setResolvedUrl(navigator.PLUGIN_HANDLE, True, li)


def play_stream(url, name, metadata=None):
    metadata = metadata or {}

    is_vod = _is_vod_url(url)
    is_hls = _is_hls_url(url)
    is_live = not is_vod

    giptv.log(
        f"name={name} vod={is_vod} hls={is_hls} url={url}",
        xbmc.LOGINFO,
    )

    if is_hls:
        giptv.log(f"Using direct HLS stream: {url}", xbmc.LOGINFO)
        _resolve_direct_stream(url, name, is_live=is_live, metadata=metadata)
        return

    candidates = build_stream_fallbacks(url)
    working = None

    for candidate in candidates:
        giptv.log(f"Trying stream: {candidate}", xbmc.LOGINFO)
        if stream_responds(candidate):
            working = candidate
            giptv.log(f"Stream OK: {candidate}", xbmc.LOGINFO)
            break

    if not working:
        xbmcgui.Dialog().notification(
            "Playback failed",
            "Stream unavailable",
            xbmcgui.NOTIFICATION_ERROR,
            5000,
        )
        giptv.return_action()
        giptv.container_refresh()
        return

    if _is_hls_url(working):
        giptv.log(f"Fallback selected direct HLS stream: {working}", xbmc.LOGINFO)
        _resolve_direct_stream(working, name, is_live=is_live, metadata=metadata)
        return

    port = ensure_proxy_running()

    if is_vod:
        giptv.log(f"Using proxied VOD stream: {working}", xbmc.LOGINFO)
        _resolve_proxied_stream(working, name, port, metadata=metadata, is_live=False)
        return

    _resolve_proxied_stream(working, name, port, metadata=metadata, is_live=True)


def _handle_play(url_params):
    url = url_params.get("url", [""])[0]
    name = url_params.get("name", [""])[0]
    metadata = _decode_meta(url_params.get("meta", [""])[0])

    giptv.log(
        f"play_stream name={name} url={url} meta_keys={list(metadata.keys())}",
        xbmc.LOGINFO,
    )

    play_stream(url, name, metadata)


def _handle_add_favourite(url_params):
    add_favourite_from_params(
        item_id=url_params.get("item_id", [""])[0],
        title=url_params.get("title", [""])[0],
        stream_type=url_params.get("stream_type", [""])[0],
        play_url=url_params.get("play_url", [""])[0],
        thumb=url_params.get("thumb", [""])[0],
        poster=url_params.get("poster", [""])[0],
        fanart=url_params.get("fanart", [""])[0],
        icon=url_params.get("icon", [""])[0],
        plot=url_params.get("plot", [""])[0],
        rating=url_params.get("rating", ["0"])[0],
        year=url_params.get("year", ["0"])[0],
        tmdb_id=url_params.get("tmdb_id", [""])[0],
        channel_id=url_params.get("channel_id", [""])[0],
        stream_id=url_params.get("stream_id", [""])[0],
    )
    giptv.notification(
        ADDON.getAddonInfo("name"),
        "Channel added to Favourites",
        icon="INFO",
    )
    giptv.container_refresh()


def handle_routing(url_params):
    mode = url_params.get("mode", [None])[0]
    search_query = url_params.get("search_query", [None])[0]

    giptv.log(
        f"mode={mode} search_query={search_query} params={list(url_params.keys())}",
        xbmc.LOGINFO,
    )

    if mode is None:
        giptv.log("Initial launch → root menu", xbmc.LOGINFO)
        navigator.root_menu()
        return

    if mode == "list_streams":
        navigator.list_streams(
            url_params.get("stream_type", [""])[0],
            url_params.get("category_id", [""])[0],
            url_params.get("name", [""])[0],
            search_query,
        )

    elif mode == "catchup_dates":
        s_id = url_params.get("stream_id", [""])[0]
        c_id = url_params.get("channel_id", [""])[0]
        name = url_params.get("name", [""])[0]
        if s_id and c_id:
            navigator.list_catchup_dates(stream_id=s_id, channel_id=c_id, name=name)

    elif mode == "list_catchup_programmes":
        s_id = url_params.get("stream_id", [""])[0]
        c_id = url_params.get("channel_id", [""])[0]
        date = url_params.get("date", [""])[0]
        if s_id and c_id and date:
            navigator.list_catchup_programmes(
                stream_id=s_id, channel_id=c_id, date=date
            )

    elif mode == "list_series_streams":
        navigator.list_series_streams(
            url_params.get("stream_type", [""])[0],
            url_params.get("category_id", [""])[0],
            url_params.get("name", [""])[0],
            search_query,
        )

    elif mode == "list_series_seasons":
        navigator.list_series_seasons(
            url_params.get("series_id", [""])[0],
            url_params.get("series_name", [""])[0],
        )

    elif mode == "list_series_episodes":
        navigator.list_series_episodes(
            url_params.get("series_id", [""])[0],
            url_params.get("season_num", [""])[0],
            url_params.get("series_name", [""])[0],
        )

    elif mode == "play_stream":
        _handle_play(url_params)

    elif mode == "play_catchup":
        _handle_play(url_params)

    elif mode == "open_settings":
        open_addon_settings()

    elif mode == "recently_watched":
        history_manager.recently_watched()

    elif mode == "clear_history":
        clear_history()
        giptv.notification(
            ADDON.getAddonInfo("name"),
            "Recently Watched Reset Done",
            icon="INFO",
        )
        giptv.container_refresh()

    elif mode == "favourites":
        list_favourites()

    elif mode == "add_favourite":
        _handle_add_favourite(url_params)

    elif mode == "remove_favourite":
        remove_favourite_from_params(item_id=url_params.get("item_id", [""])[0])
        giptv.container_refresh()

    elif mode == "search":
        current_items = navigator.get_current_items(
            url_params.get("stream_type", [None])[0],
            url_params.get("category_id", [None])[0],
        )
        search.dynamic_filter_search(items=current_items)

    elif mode == "global_search":
        search.global_search()

    elif mode == "global_vod_search":
        search.global_vod_search()

    elif mode == "global_series_search":
        search.global_series_search()

    elif mode == "global_live_search":
        search.global_live_search()

    elif mode == "list_categories":
        navigator.list_categories(
            url_params.get("stream_type", [xtream_api.LIVE_TYPE])[0],
            search_query,
        )

    else:
        giptv.log(f"Unknown mode received: {mode}", xbmc.LOGERROR)
        giptv.ok_dialog(
            ADDON.getAddonInfo("name"),
            f"Unknown mode: {mode}",
        )
