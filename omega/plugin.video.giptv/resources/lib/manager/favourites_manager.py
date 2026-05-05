try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import sys
import json
import time
import base64
import datetime

import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

from resources.utils import settings
from resources.lib.manager.epg_manager import get_xmltv_index, get_now_next

ADDON = xbmcaddon.Addon()

if len(sys.argv) > 1 and sys.argv[1].isdigit():
    PLUGIN_HANDLE = int(sys.argv[1])
else:
    PLUGIN_HANDLE = -1

ADDON_ID = ADDON.getAddonInfo("id")

FAVOURITES_PATH = xbmcvfs.translatePath(
    f"special://profile/addon_data/{ADDON_ID}/favourites.json"
)


def _encode_meta(meta_dict):
    try:
        raw = json.dumps(meta_dict, separators=(",", ":"))
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _fmt_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M")


def _epg_progress(start_ts, end_ts):
    now = int(time.time())
    if end_ts <= start_ts:
        return 0
    return max(0, min(100, int((now - start_ts) * 100 / (end_ts - start_ts))))


def _progress_bar(percent, width=10):
    filled = int(width * percent / 100)
    return "●" * filled + "○" * (width - filled)


def _build_live_epg(channel_id):
    if not channel_id:
        return None

    try:
        epg_offset_minutes = settings.get_epg_offset(ADDON)
        xmltv_index = get_xmltv_index()
        data = get_now_next(xmltv_index, channel_id, epg_offset_minutes)

        if not data or not data.get("now"):
            return None

        title, desc, start_ts, end_ts = data["now"]
        duration = max(0, end_ts - start_ts)

        display_start_ts = start_ts - (epg_offset_minutes * 60)
        display_end_ts = end_ts - (epg_offset_minutes * 60)

        pct = _epg_progress(display_start_ts, display_end_ts)
        bar = _progress_bar(pct)

        plot_lines = [
            f"[COLOR yellow][B]Now: {title}[/B][/COLOR] "
            f"[COLOR grey][I]from {_fmt_time(display_start_ts)} – {_fmt_time(display_end_ts)}[/I][/COLOR]",
            f"[COLOR green]{bar}  {pct}%[/COLOR]",
            f"[COLOR white]{desc}[/COLOR]",
        ]

        if data.get("next"):
            next_title, next_desc, next_start, next_end = data["next"]
            display_next_start = next_start - (epg_offset_minutes * 60)
            display_next_end = next_end - (epg_offset_minutes * 60)

            plot_lines += [
                f"[COLOR yellow][B]Next: {next_title}[/B][/COLOR] "
                f"[COLOR grey][I]from {_fmt_time(display_next_start)} – {_fmt_time(display_next_end)}[/I][/COLOR]",
                f"[COLOR white]{next_desc}[/COLOR]",
            ]

        return {
            "title": title,
            "plot": "\n".join(plot_lines),
            "duration": duration,
        }
    except Exception:
        return None


def _read():
    if not xbmcvfs.exists(FAVOURITES_PATH):
        return []

    try:
        f = xbmcvfs.File(FAVOURITES_PATH, "r")
        data = json.loads(f.read())
        f.close()
    except Exception:
        return []

    cleaned = _autoclean(data)

    if cleaned != data:
        _write(cleaned)

    return cleaned


def _write(data):
    try:
        f = xbmcvfs.File(FAVOURITES_PATH, "w")
        f.write(json.dumps(data))
        f.close()
    except Exception:
        pass


def _autoclean(data):
    cleaned = []

    for item in data:
        item_id = item.get("id")
        play_url = item.get("play_url")

        if not item_id:
            continue

        if not play_url or "." not in play_url:
            continue

        if "None" in play_url or play_url.endswith("/") or play_url.endswith(".."):
            continue

        cleaned.append(item)

    return cleaned


def add_favourite(
    item_id,
    title,
    stream_type,
    play_url,
    thumb="",
    poster="",
    fanart="",
    icon="",
    plot="",
    rating=0,
    year=0,
    tmdb_id="",
    channel_id="",
    stream_id="",
):
    data = _read()

    data = [i for i in data if i.get("id") != item_id]

    payload = {
        "id": item_id,
        "title": title,
        "type": stream_type,
        "thumb": thumb or "",
        "poster": poster or "",
        "fanart": fanart or "",
        "icon": icon or "",
        "plot": plot or "",
        "rating": rating or 0,
        "year": year or 0,
        "tmdb_id": tmdb_id or "",
        "play_url": play_url,
        "channel_id": channel_id or "",
        "stream_id": str(stream_id or ""),
        "is_live_epg": (stream_type == "live"),
        "timestamp": int(time.time()),
    }

    data.insert(0, payload)
    _write(data)


def remove_favourite(item_id):
    data = _read()
    data = [i for i in data if str(i.get("id")) != str(item_id)]
    _write(data)


def is_favourite(item_id):
    return any(str(i.get("id")) == str(item_id) for i in _read())


def toggle_favourite(
    item_id,
    title,
    stream_type,
    play_url,
    thumb="",
    poster="",
    fanart="",
    icon="",
    plot="",
    rating=0,
    year=0,
    tmdb_id="",
    channel_id="",
    stream_id="",
):
    if is_favourite(item_id):
        remove_favourite(item_id)
        return False

    add_favourite(
        item_id=item_id,
        title=title,
        stream_type=stream_type,
        play_url=play_url,
        thumb=thumb,
        poster=poster,
        fanart=fanart,
        icon=icon,
        plot=plot,
        rating=rating,
        year=year,
        tmdb_id=tmdb_id,
        channel_id=channel_id,
        stream_id=stream_id,
    )
    return True


def add_favourite_from_params(
    item_id,
    title,
    stream_type,
    play_url,
    thumb="",
    poster="",
    fanart="",
    icon="",
    plot="",
    rating=0,
    year=0,
    tmdb_id="",
    channel_id="",
    stream_id="",
):
    add_favourite(
        item_id=item_id,
        title=title,
        stream_type=stream_type,
        play_url=play_url,
        thumb=thumb,
        poster=poster,
        fanart=fanart,
        icon=icon,
        plot=plot,
        rating=rating,
        year=year,
        tmdb_id=tmdb_id,
        channel_id=channel_id,
        stream_id=stream_id,
    )


def remove_favourite_from_params(item_id):
    remove_favourite(item_id)


def list_favourites():
    favourites = sorted(_read(), key=lambda x: x.get("timestamp", 0), reverse=True)

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, "Favourites")
    xbmcplugin.setContent(PLUGIN_HANDLE, "videos")

    if not favourites:
        item = xbmcgui.ListItem("No favourites yet.")
        xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, "", item, isFolder=False)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    for entry in favourites:
        title = entry.get("title", "Unknown")
        thumb = entry.get("thumb", "")
        poster = entry.get("poster", "")
        fanart = entry.get("fanart", "")
        icon = entry.get("icon", "")
        plot = entry.get("plot", "")
        rating = entry.get("rating", 0)
        year = entry.get("year", 0)
        tmdb_id = entry.get("tmdb_id", "")
        play_url = entry.get("play_url")
        stream_type = entry.get("type", "vod")
        stream_id = entry.get("stream_id") or entry.get("id", "")
        channel_id = entry.get("channel_id", "")
        is_live_epg = entry.get("is_live_epg", False)

        display_title = title
        display_plot = plot

        if stream_type == "live" and is_live_epg and channel_id:
            live_epg = _build_live_epg(channel_id)
            if live_epg:
                display_plot = live_epg.get("plot", plot)

        meta = {
            "thumb": thumb,
            "poster": poster,
            "fanart": fanart,
            "icon": icon,
            "plot": display_plot,
            "rating": rating,
            "year": year,
            "tmdb_id": tmdb_id,
            "stream_type": stream_type,
            "channel_id": channel_id,
            "stream_id": stream_id,
        }

        plugin_url = (
            sys.argv[0]
            + "?"
            + urlparse.urlencode(
                {
                    "mode": "play_stream",
                    "url": play_url,
                    "id": stream_id,
                    "type": stream_type,
                    "name": title,
                    "meta": _encode_meta(meta),
                }
            )
        )

        li = xbmcgui.ListItem(label=display_title)

        art = {
            "thumb": thumb,
            "icon": icon or thumb,
            "poster": poster or thumb,
            "fanart": fanart or poster or thumb,
        }
        li.setArt(art)

        tag = li.getVideoInfoTag()
        tag.setTitle(display_title)
        tag.setPlot(display_plot)

        if year:
            try:
                tag.setYear(int(year))
            except Exception:
                pass

        if rating:
            try:
                tag.setRating(float(rating), 10)
            except Exception:
                pass

        li.setProperty("IsPlayable", "true")

        if stream_type == "live":
            li.setProperty("IsLive", "true")

        if tmdb_id:
            li.setProperty("tmdbnumber", str(tmdb_id))
            li.setProperty("imdbnumber", str(tmdb_id))

        li.addContextMenuItems(
            [
                (
                    "Remove Favourite",
                    f"RunPlugin({sys.argv[0]}?mode=remove_favourite&item_id={entry.get('id')})",
                )
            ]
        )

        xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, plugin_url, li, isFolder=False)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
