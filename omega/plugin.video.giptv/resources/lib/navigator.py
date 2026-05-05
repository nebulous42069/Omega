import sys
import threading
import datetime
import time
import os
import json
import base64

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

import resources.apis.tmdb_helper as TMDbHelper
import resources.apis.xtream_api as xtream_api
import resources.utils.giptv as giptv
from resources.utils import settings
import resources.lib.manager.index_manager as index_manager
from resources.lib.manager.fetch_manager import cache_handler
from resources.lib.manager.epg_manager import (
    get_now_next,
    get_xmltv_index,
    resolve_xmltv_channel_id,
)
from resources.lib.cache.picon_cache import get_picon
import resources.utils.config as config
from resources.utils.xtream import STATE


ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path")
ADDON_ID = ADDON.getAddonInfo("id")

GLOBAL_FANART = os.path.join(ADDON_PATH, "fanart.png")
LIVE_ICON = os.path.join(ADDON_PATH, "resources", "media", "thumb", "tv.png")
SERIES_ICON = os.path.join(ADDON_PATH, "resources", "media", "thumb", "series.png")
MOVIE_ICON = os.path.join(ADDON_PATH, "resources", "media", "thumb", "movies.png")
SEARCH_ICON = os.path.join(ADDON_PATH, "resources", "media", "thumb", "search.png")
WATCHED_ICON = os.path.join(ADDON_PATH, "resources", "media", "thumb", "watched.png")
FAVOURITES_ICON = os.path.join(
    ADDON_PATH, "resources", "media", "thumb", "favourite.png"
)

if len(sys.argv) > 1 and sys.argv[1].isdigit():
    PLUGIN_HANDLE = int(sys.argv[1])
else:
    PLUGIN_HANDLE = -1

SETTINGS_ACTION_URL = f"RunPlugin(plugin://{ADDON_ID}/?mode=open_settings)"
INDEX_ACTION_URL = f"RunPlugin(plugin://{ADDON_ID}/?action=build_search_index)"

SETTINGS_CONTEXT_MENU = [
    ("Global Search", f"Container.Update(plugin://{ADDON_ID}/?mode=global_search)"),
    ("Favourites", f"Container.Update(plugin://{ADDON_ID}/?mode=favourites)"),
    ("Open Settings", SETTINGS_ACTION_URL),
    ("Refresh", "Container.Refresh"),
    ("Build Search Index", INDEX_ACTION_URL),
    ("Reset Recently Watched", f"RunPlugin(plugin://{ADDON_ID}/?mode=clear_history)"),
]

tmdb_helper = TMDbHelper.TMDbHelper()

_current_items = {}
_picon_memory_cache = {}
_xmltv_channel_cache = {}


def _ensure_ready():
    if not config.ensure_api_ready():
        return False
    if not index_manager.index_exists_and_valid():
        threading.Thread(target=index_manager.build_index, daemon=True).start()
    return True


def _plugin_url(**params):
    return sys.argv[0] + "?" + urlparse.urlencode(params)


def _encode_meta(meta_dict):
    try:
        raw = json.dumps(meta_dict, separators=(",", ":"))
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _add_dir_items(items):
    if PLUGIN_HANDLE < 0:
        return
    if items:
        xbmcplugin.addDirectoryItems(PLUGIN_HANDLE, items, len(items))
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def _add_shortcuts(items, stream_type=None):
    if stream_type == "vod":
        search_all_mode = "global_vod_search"
        search_label = "[COLOR yellow]Search ALL Movies[/COLOR]"
    elif stream_type == "series":
        search_all_mode = "global_series_search"
        search_label = "[COLOR yellow]Search ALL TV Series[/COLOR]"
    elif stream_type == "live":
        search_all_mode = "global_live_search"
        search_label = "[COLOR yellow]Search ALL Live TV[/COLOR]"

        fav_item = xbmcgui.ListItem(label="[COLOR gold]Favourites[/COLOR]")
        fav_item.setArt(
            {
                "icon": FAVOURITES_ICON,
                "thumb": FAVOURITES_ICON,
                "fanart": FAVOURITES_ICON,
            }
        )
        items.append((_plugin_url(mode="favourites"), fav_item, True))

    else:
        search_all_mode = None
        search_label = None

    if search_all_mode:
        li = xbmcgui.ListItem(label=search_label)
        li.setArt({"icon": "DefaultAddonSearch.png"})
        items.append((_plugin_url(mode=search_all_mode), li, True))

    rw_item = xbmcgui.ListItem(label="[COLOR cyan]Recently Watched[/COLOR]")
    rw_item.setArt(
        {"icon": WATCHED_ICON, "thumb": WATCHED_ICON, "fanart": WATCHED_ICON}
    )
    items.append((_plugin_url(mode="recently_watched"), rw_item, True))


def _show_filter_keyboard(title):
    keyboard = xbmc.Keyboard("", title)
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return None
    value = keyboard.getText().strip().lower()
    return value or None


def _apply_offset_minutes(timestamp, offset_minutes):
    return timestamp + (offset_minutes * 60)


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


def _store_current_items(stream_type, category_id, items):
    _current_items[f"{stream_type}_{category_id}"] = items


def get_current_items(stream_type, category_id):
    return _current_items.get(f"{stream_type}_{category_id}", [])


def _extract_tmdb_id(data):
    return (
        data.get("tmdb")
        or data.get("tmdb_id")
        or data.get("tmdbId")
        or data.get("tmdbID")
        or data.get("imdb_id")
        or (data.get("info", {}) or {}).get("tmdb")
        or (data.get("info", {}) or {}).get("tmdb_id")
        or None
    )


def _get_picon_cached(stream_id, stream_icon, category_id):
    key = (str(stream_id), stream_icon or "", str(category_id or ""))
    if key not in _picon_memory_cache:
        _picon_memory_cache[key] = get_picon(stream_id, stream_icon, category_id)
    return _picon_memory_cache[key]


def _resolve_xmltv_channel_id_cached(stream):
    stream_id = str(stream.get("stream_id", ""))
    if stream_id in _xmltv_channel_cache:
        return _xmltv_channel_cache[stream_id]
    value = resolve_xmltv_channel_id(stream)
    _xmltv_channel_cache[stream_id] = value
    return value


def _build_live_plot(now_data, next_data, epg_offset_minutes):
    title, desc, start_ts, end_ts = now_data
    duration = max(0, end_ts - start_ts)

    # Invert offset for displayed label times
    display_start_ts = _apply_offset_minutes(start_ts, -epg_offset_minutes)
    display_end_ts = _apply_offset_minutes(end_ts, -epg_offset_minutes)

    # Progress should match displayed time range
    pct = _epg_progress(display_start_ts, display_end_ts)
    bar = _progress_bar(pct)

    plot_lines = [
        f"[COLOR yellow][B]Now: {title}[/B][/COLOR] "
        f"[COLOR grey][I]from {_fmt_time(display_start_ts)} – {_fmt_time(display_end_ts)}[/I][/COLOR]",
        f"[COLOR green]{bar}  {pct}%[/COLOR]",
        f"[COLOR white]{desc}[/COLOR]",
    ]

    if next_data:
        next_title, next_desc, next_start, next_end = next_data

        display_next_start = _apply_offset_minutes(next_start, -epg_offset_minutes)
        display_next_end = _apply_offset_minutes(next_end, -epg_offset_minutes)

        plot_lines += [
            f"[COLOR yellow][B]Next: {next_title}[/B][/COLOR] "
            f"[COLOR grey][I]from {_fmt_time(display_next_start)} – {_fmt_time(display_next_end)}[/I][/COLOR]",
            f"[COLOR white]{next_desc}[/COLOR]",
        ]

    return title, "\n".join(plot_lines), duration


def root_menu():
    if not _ensure_ready():
        return

    items = []

    global_search_item = xbmcgui.ListItem(
        label="[COLOR yellow]\ue836[/COLOR] [B]Global Search (All Content)[/B]"
    )
    global_search_item.setArt(
        {
            "icon": "DefaultAddonSearch.png",
            "thumb": "DefaultAddonSearch.png",
            "fanart": SEARCH_ICON,
        }
    )
    global_search_item.addContextMenuItems(
        [
            (
                "Rebuild Search Index",
                f"RunPlugin(plugin://{ADDON_ID}/?action=build_search_index)",
            )
        ]
    )
    items.append((_plugin_url(mode="global_search"), global_search_item, True))

    fav_item = xbmcgui.ListItem("[B][COLOR gold]Favourites[/COLOR][/B]")
    fav_item.setArt(
        {
            "icon": FAVOURITES_ICON,
            "thumb": FAVOURITES_ICON,
            "fanart": FAVOURITES_ICON,
        }
    )
    items.append((_plugin_url(mode="favourites"), fav_item, True))

    recent_item = xbmcgui.ListItem("[B][COLOR orange]Recently Watched[/COLOR][/B]")
    recent_item.setArt(
        {
            "icon": WATCHED_ICON,
            "thumb": WATCHED_ICON,
            "fanart": WATCHED_ICON,
        }
    )
    items.append((_plugin_url(mode="recently_watched"), recent_item, True))

    for label, stream_type, thumb in [
        ("[B]Live TV[/B]", "live", LIVE_ICON),
        ("[B]Movies[/B]", "vod", MOVIE_ICON),
        ("[B]TV Series[/B]", "series", SERIES_ICON),
    ]:
        li = xbmcgui.ListItem(label=label)
        li.setArt({"thumb": thumb, "icon": thumb, "fanart": thumb})
        li.addContextMenuItems(SETTINGS_CONTEXT_MENU)
        items.append(
            (_plugin_url(mode="list_categories", stream_type=stream_type), li, True)
        )

    tools_item = xbmcgui.ListItem("[B][COLOR cyan]Tools Menu[/COLOR][/B]")
    tools_item.setArt(
        {
            "icon": "DefaultAddonProgram.png",
            "thumb": "DefaultAddonProgram.png",
            "fanart": GLOBAL_FANART,
        }
    )
    items.append(
        (
            f"plugin://{ADDON_ID}/?action=open_tools_window",
            tools_item,
            False,
        )
    )

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, "Xtream Content Streams")
    xbmcplugin.setContent(PLUGIN_HANDLE, "videos")
    _add_dir_items(items)


def list_categories(stream_type, search_query=None):
    if not _ensure_ready():
        return

    if search_query is None:
        params = dict(urlparse.parse_qsl(sys.argv[2]))
        search_query = params.get("search") or params.get("search_query")

    items = []
    _add_shortcuts(items, stream_type)

    category_list = cache_handler.get("categories", f"{STATE.username}_{stream_type}")
    if not category_list:
        category_list = xtream_api.categories(stream_type)

    if not category_list:
        giptv.notification(
            ADDON.getAddonInfo("name"), "No categories found.", icon="INFO"
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if search_query == "__clear__":
        search_query = None

    if search_query is None:
        li = xbmcgui.ListItem(
            label=f"[COLOR yellow]\ue836[/COLOR] Filter {stream_type.capitalize()} Category"
        )
        li.setArt({"icon": "DefaultAddonSearch.png"})
        items.append(
            (
                _plugin_url(
                    mode="list_categories",
                    stream_type=stream_type,
                    search="trigger",
                ),
                li,
                True,
            )
        )

    if search_query == "trigger":
        search_query = _show_filter_keyboard(f"Filter {stream_type.upper()} Categories")
        if search_query is None:
            giptv.return_action()
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
            return

    if search_query:
        category_list = [
            c
            for c in category_list
            if search_query in c.get("category_name", "").lower()
        ]
        if not category_list:
            giptv.notification(
                ADDON.getAddonInfo("name"),
                f"No categories found matching '{search_query}'.",
                icon="INFO",
            )
            giptv.return_action()
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
            return

        clear_item = xbmcgui.ListItem(label="[COLOR red]\u2716[/COLOR] Clear Filter")
        clear_item.setArt({"icon": "DefaultAddonSearch.png"})
        items.append(
            (
                _plugin_url(
                    mode="list_categories",
                    stream_type=stream_type,
                    search_query="__clear__",
                ),
                clear_item,
                True,
            )
        )

    next_mode = "list_series_streams" if stream_type == "series" else "list_streams"

    for category in category_list:
        name = category.get("category_name", "Unknown Category")
        category_id = category.get("category_id")

        li = xbmcgui.ListItem(label=name)
        li.setArt({"icon": "DefaultFolder.png", "thumb": "DefaultFolder.png"})
        li.addContextMenuItems(SETTINGS_CONTEXT_MENU)

        items.append(
            (
                _plugin_url(
                    mode=next_mode,
                    stream_type=stream_type,
                    category_id=category_id,
                    name=name,
                ),
                li,
                True,
            )
        )

    _add_dir_items(items)


def list_streams(stream_type, category_id, name, search_query=None):
    if not _ensure_ready():
        return

    from resources.lib.manager import favourites_manager

    items = []
    _add_shortcuts(items, stream_type=stream_type)

    cache_key = f"{STATE.username}_{stream_type}_{category_id}"
    stream_list = cache_handler.get(stream_type, cache_key)
    if not stream_list:
        if settings.get_cache_on_off(ADDON):
            giptv.notification(f"{stream_type.capitalize()} not Cached", icon="INFO")
        stream_list = xtream_api.streams_by_category(stream_type, category_id)

    if not stream_list:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"No streams found in {name}.",
            icon="INFO",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if search_query == "__clear__":
        search_query = None

    if search_query is None:
        li = xbmcgui.ListItem(
            label=f"[COLOR yellow]\ue836[/COLOR] Filter {stream_type.capitalize()} Streams"
        )
        li.setArt({"icon": "DefaultAddonSearch.png"})
        items.append(
            (
                _plugin_url(
                    mode="list_streams",
                    stream_type=stream_type,
                    category_id=category_id,
                    name=name,
                    search_query="trigger",
                ),
                li,
                True,
            )
        )

    if search_query == "trigger":
        search_query = _show_filter_keyboard(f"Filter {stream_type.upper()} Streams")
        if search_query is None:
            giptv.return_action()
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
            return

    if search_query:
        q = search_query.lower()

        def _matches(stream):
            return (
                q in (stream.get("name") or "").lower()
                or q in (stream.get("title") or "").lower()
                or q in (stream.get("stream_display_name") or "").lower()
            )

        stream_list = [s for s in stream_list if _matches(s)]
        if not stream_list:
            giptv.notification(
                ADDON.getAddonInfo("name"),
                f"No streams found matching '{search_query}'.",
                icon="INFO",
            )
            giptv.return_action()
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
            return

        clear_item = xbmcgui.ListItem(label="[COLOR red]\u2716[/COLOR] Clear Filter")
        clear_item.setArt({"icon": "DefaultAddonSearch.png"})
        items.append(
            (
                _plugin_url(
                    mode="list_streams",
                    stream_type=stream_type,
                    category_id=category_id,
                    name=name,
                    search_query="__clear__",
                ),
                clear_item,
                True,
            )
        )

    _store_current_items(stream_type, category_id, stream_list)

    is_live = stream_type == "live"
    is_vod = stream_type == "vod"

    xbmcplugin.setContent(PLUGIN_HANDLE, "movies" if is_vod else "videos")

    epg_offset_minutes = settings.get_epg_offset(ADDON) if is_live else 0
    start = time.time()
    xmltv_index = get_xmltv_index() if is_live else {}
    giptv.log(f"EPG load took {time.time() - start:.3f}s", xbmc.LOGINFO)

    for stream in stream_list:
        stream_id = str(
            stream.get("stream_id")
            or stream.get("movie_id")
            or stream.get("vod_id")
            or ""
        )
        if not stream_id:
            continue

        stream_name = (
            stream.get("name")
            or stream.get("title")
            or stream.get("stream_display_name")
            or "Unknown Stream"
        )

        stream_icon = _get_picon_cached(
            stream_id, stream.get("stream_icon"), stream.get("category_id")
        )

        list_item = xbmcgui.ListItem(label=stream_name)
        art_dict = {}
        play_url = None
        ext = stream.get("container_extension", "mp4")
        stream_type_for_api = "live"

        plot_value = ""
        rating_value = 0
        year_value = 0
        tmdb_id_value = ""
        channel_id_value = ""
        stream_type_value = "vod" if is_vod else "live"

        if is_vod:
            stream_type_for_api = "vod"
            info_data = stream.get("info", {}) or {}
            ext = stream.get("container_extension", "mp4")
            tmdb_id = stream.get("tmdb") or stream.get("tmdb_id")
            tmdb_id = str(tmdb_id) if tmdb_id else None
            tmdb_details = tmdb_helper.get_movie_details(tmdb_id) if tmdb_id else None

            if tmdb_details:
                cast_list = [
                    xbmc.Actor(actor.get("name"), actor.get("role"))
                    for actor in tmdb_details.get("cast", [])
                    if actor.get("name")
                ]

                directors = tmdb_details.get("director") or []
                if isinstance(directors, str):
                    directors = [directors]
                if not directors and info_data.get("director"):
                    directors = [info_data["director"]]

                genres = tmdb_details.get("genre") or []
                if isinstance(genres, str):
                    genres = [genres]
                if not genres and info_data.get("genre"):
                    genres = [info_data["genre"]]

                art_dict = tmdb_details.get("art", {}) or {}
                if not art_dict.get("poster") and stream_icon:
                    art_dict["poster"] = stream_icon
                    art_dict["thumb"] = stream_icon
                if not art_dict.get("thumb") and art_dict.get("poster"):
                    art_dict["thumb"] = art_dict["poster"]
                if stream_icon and not art_dict.get("icon"):
                    art_dict["icon"] = stream_icon
                if not art_dict.get("fanart"):
                    art_dict["fanart"] = art_dict.get("poster", "")

                if tmdb_id:
                    list_item.setProperty("tmdbnumber", tmdb_id)
                    list_item.setProperty("imdbnumber", tmdb_id)

                tag = list_item.getVideoInfoTag()
                tag.setTitle(tmdb_details.get("title") or stream_name)
                tag.setPlot(tmdb_details.get("plot") or "")
                tag.setMediaType("movie")

                if tmdb_details.get("year") and str(tmdb_details["year"]).isdigit():
                    tag.setYear(int(tmdb_details["year"]))

                try:
                    if tmdb_details.get("rating") is not None:
                        tag.setRating(float(tmdb_details["rating"]), 10)
                except (ValueError, TypeError):
                    pass

                try:
                    if tmdb_details.get("duration") is not None:
                        tag.setDuration(int(tmdb_details["duration"]))
                    elif info_data.get("duration_secs"):
                        tag.setDuration(int(info_data["duration_secs"]))
                except (ValueError, TypeError):
                    pass

                if genres:
                    tag.setGenres(genres)
                if directors:
                    tag.setDirectors(directors)
                if cast_list:
                    tag.setCast(cast_list)

                if tmdb_id:
                    tag.setUniqueIDs({"tmdb": tmdb_id}, "tmdb")

                plot_value = tmdb_details.get("plot") or ""
                rating_value = tmdb_details.get("rating") or 0
                year_value = (
                    int(tmdb_details["year"])
                    if tmdb_details.get("year") and str(tmdb_details["year"]).isdigit()
                    else 0
                )
                tmdb_id_value = tmdb_id or ""

            else:
                movie_plot = (
                    stream.get("plot")
                    or info_data.get("plot")
                    or "No description available."
                )

                duration = 0
                try:
                    if info_data.get("duration_secs"):
                        duration = int(info_data["duration_secs"])
                except (ValueError, TypeError):
                    duration = 0

                year = 0
                release_date = stream.get("release_date") or ""
                if "-" in release_date:
                    year_part = release_date.split("-")[0]
                    if year_part.isdigit():
                        year = int(year_part)
                elif len(release_date) == 4 and release_date.isdigit():
                    year = int(release_date)

                tag = list_item.getVideoInfoTag()
                tag.setTitle(stream_name)
                tag.setPlot(movie_plot)
                tag.setMediaType("movie")
                if duration > 0:
                    tag.setDuration(duration)
                if year > 0:
                    tag.setYear(year)

                if stream_icon:
                    art_dict.update(
                        {
                            "thumb": stream_icon,
                            "icon": stream_icon,
                            "poster": stream_icon,
                            "fanart": stream_icon,
                        }
                    )

                plot_value = movie_plot
                rating_value = 0
                year_value = year
                tmdb_id_value = ""

        else:
            stream_type_for_api = "live"
            ext = stream.get("container_extension", "ts")

            selected_format = settings.get_stream_format(ADDON)

            if selected_format == "ts":
                ext = "ts"
            elif selected_format == "m3u8":
                ext = "m3u8"
            else:
                ext = stream.get("container_extension", "ts")

            if stream_icon:
                art_dict = {
                    "thumb": stream_icon,
                    "icon": stream_icon,
                    "poster": stream_icon,
                    "fanart": stream_icon,
                }
            else:
                art_dict = {
                    "thumb": "DefaultVideo.png",
                    "icon": "DefaultVideo.png",
                    "poster": "DefaultVideo.png",
                    "fanart": "DefaultVideo.png",
                }

            channel_id = _resolve_xmltv_channel_id_cached(stream)
            channel_id_value = channel_id or ""

            loop_start = time.time()
            data = (
                get_now_next(xmltv_index, channel_id, epg_offset_minutes)
                if channel_id
                else None
            )
            giptv.log(
                f"EPG lookup for {stream_name} took {time.time() - loop_start:.4f}s",
                xbmc.LOGINFO,
            )

            if data and data.get("now"):
                title, plot, duration = _build_live_plot(
                    data["now"], data.get("next"), epg_offset_minutes
                )
                list_item.setLabel(f"[COLOR green][LIVE][/COLOR] {stream_name}")

                tag = list_item.getVideoInfoTag()
                tag.setTitle(title)
                tag.setPlot(plot)
                tag.setDuration(duration)
                tag.setMediaType("video")
                list_item.setProperty("IsLive", "true")

                plot_value = plot
            else:
                tag = list_item.getVideoInfoTag()
                tag.setTitle(stream_name)
                tag.setPlot(stream_name)
                tag.setMediaType("video")

                plot_value = stream_name

            rating_value = 0
            year_value = 0
            tmdb_id_value = ""

        play_url = xtream_api.build_stream_url(
            stream_id=stream_id,
            stream_type=stream_type_for_api,
            container_extension=ext,
        )
        if not play_url:
            continue

        metadata = {
            "thumb": art_dict.get("thumb", ""),
            "poster": art_dict.get("poster", ""),
            "fanart": art_dict.get("fanart", ""),
            "icon": art_dict.get("icon", ""),
            "plot": plot_value,
            "rating": rating_value,
            "year": year_value,
            "tmdb_id": tmdb_id_value,
            "stream_type": stream_type_value,
            "channel_id": channel_id_value,
            "stream_id": stream_id,
        }

        url = _plugin_url(
            mode="play_stream",
            url=play_url,
            name=stream_name,
            meta=_encode_meta(metadata),
        )
        list_item.setProperty("IsPlayable", "true")

        menu_items = []

        if str(stream.get("tv_archive", stream.get("has_archive", "0"))) == "1":
            catchup_url = giptv.build_url(
                mode="catchup_dates",
                stream_id=str(stream_id),
                channel_id=str(stream.get("epg_channel_id")),
                name=stream_name,
            )
            menu_items.append(("Catch-up", f"Container.Update({catchup_url})"))

        if is_live:
            if favourites_manager.is_favourite(stream_id):
                fav_url = giptv.build_url(mode="remove_favourite", item_id=stream_id)
                menu_items.append(
                    ("Remove Channel from GIPTV Favourites", f"RunPlugin({fav_url})")
                )
            else:
                fav_url = giptv.build_url(
                    mode="add_favourite",
                    item_id=stream_id,
                    title=stream_name,
                    stream_type=stream_type_value,
                    play_url=play_url,
                    thumb=art_dict.get("thumb", ""),
                    poster=art_dict.get("poster", ""),
                    fanart=art_dict.get("fanart", ""),
                    icon=art_dict.get("icon", ""),
                    plot=plot_value,
                    rating=str(rating_value),
                    year=str(year_value),
                    tmdb_id=tmdb_id_value,
                    channel_id=channel_id_value,
                    stream_id=stream_id,
                )
                menu_items.append(
                    ("Add Channel to GIPTV Favourites", f"RunPlugin({fav_url})")
                )

        # HERE
        # custom_menu_url = giptv.build_url(
        #     action="open_context_window",
        #     title=stream_name,
        #     item_id=stream_id,
        #     name=stream_name,
        #     play_url=play_url,
        #     stream_type=stream_type_value,
        #     thumb=art_dict.get("thumb", ""),
        #     poster=art_dict.get("poster", ""),
        #     fanart=art_dict.get("fanart", ""),
        #     icon=art_dict.get("icon", ""),
        #     plot=plot_value,
        #     rating=str(rating_value),
        #     year=str(year_value),
        #     tmdb_id=tmdb_id_value,
        #     channel_id=channel_id_value,
        #     has_archive=str(stream.get("tv_archive", stream.get("has_archive", "0"))),
        # )
        # menu_items.append(("GIPTV Menu", f"RunPlugin({custom_menu_url})"))
        menu_items.extend(SETTINGS_CONTEXT_MENU)
        list_item.addContextMenuItems(menu_items, replaceItems=False)
        list_item.setArt(art_dict)

        items.append((url, list_item, False))

    _add_dir_items(items)


def get_direct_epg_index():
    if not _ensure_ready():
        return {}

    user = (STATE.username or "default").replace("/", "_").replace(":", "_")
    server = (STATE.server or "server").replace("/", "_").replace(":", "_")
    filename = f"epg_index_{user}_{server}.json"

    path = xbmcvfs.translatePath(
        f"special://profile/addon_data/plugin.video.giptv/cache/{filename}"
    )

    giptv.log(f"[EPG DEBUG] Attempting to read file: {path}")

    if not xbmcvfs.exists(path):
        giptv.log(f"[EPG DEBUG] FILE NOT FOUND on disk at: {path}", xbmc.LOGWARNING)
        return {}

    try:
        f = xbmcvfs.File(path, "r")
        raw_data = f.read()
        f.close()

        giptv.log(f"[EPG DEBUG] File read successfully. Size: {len(raw_data)} bytes")

        data = json.loads(raw_data)
        index = data.get("index", {})
        giptv.log(f"[EPG DEBUG] JSON parsed. Number of channels in index: {len(index)}")
        if index:
            giptv.log(f"[EPG DEBUG] Sample keys in JSON: {list(index.keys())[:5]}")
        return index
    except Exception as e:
        giptv.log(f"[EPG DEBUG] Error during direct read: {str(e)}", xbmc.LOGERROR)
        return {}


def list_catchup_dates(stream_id, channel_id, name):
    if not _ensure_ready():
        return

    xmltv_index = get_xmltv_index()
    cid = str(channel_id).strip().upper().replace(" ", "_").replace("-", "_")
    programmes = xmltv_index.get(cid, [])

    items = []
    if not programmes:
        _add_dir_items(items)
        return

    now_ts = int(time.time())
    dates = {
        datetime.datetime.fromtimestamp(start_ts).date()
        for start_ts, _, _, _ in programmes
        if start_ts <= now_ts
    }

    for d in sorted(dates, reverse=True):
        li = xbmcgui.ListItem(label=d.strftime("%A %d %B"))
        items.append(
            (
                giptv.build_url(
                    mode="list_catchup_programmes",
                    stream_id=stream_id,
                    channel_id=channel_id,
                    date=d.isoformat(),
                    name=name,
                ),
                li,
                True,
            )
        )

    _add_dir_items(items)


def list_catchup_programmes(stream_id, channel_id, date):
    if not _ensure_ready():
        return

    xmltv = get_xmltv_index()
    cid = str(channel_id).strip().upper().replace(" ", "_").replace("-", "_")
    now_ts = int(time.time())
    programmes = xmltv.get(cid, [])
    catchup_offset = settings.get_catchup_offset(ADDON)

    items = []

    for start_ts, end_ts, title, desc in programmes:
        dt = datetime.datetime.fromtimestamp(start_ts)

        if dt.date().isoformat() != date:
            continue
        if start_ts > now_ts:
            continue

        duration = int((end_ts - start_ts) / 60)
        adjusted_start_ts = _apply_offset_minutes(start_ts, catchup_offset)
        dt_adjusted = datetime.datetime.fromtimestamp(adjusted_start_ts)
        start_str = dt_adjusted.strftime("%Y-%m-%d:%H-%M")

        dt_display = dt.astimezone()
        label_time = dt_display.strftime("%H:%M")

        final_url = (
            f"{STATE.server.rstrip('/')}/timeshift/"
            f"{STATE.username}/{STATE.password}/"
            f"{duration}/{start_str}/{stream_id}.ts"
        )

        url = giptv.build_url(mode="play_catchup", url=final_url, name=title)

        li = xbmcgui.ListItem(label=f"{label_time} — {title}")
        li.getVideoInfoTag().setPlot(desc)
        li.setProperty("IsPlayable", "true")

        items.append((url, li, False))

    _add_dir_items(items)


def list_series_streams(stream_type, category_id, name, search_query=None):
    if not _ensure_ready():
        return

    items = []
    _add_shortcuts(items, stream_type)

    series_list = cache_handler.get(
        stream_type, f"{STATE.username}_{stream_type}_{category_id}"
    )
    if not series_list:
        if settings.get_cache_on_off(ADDON):
            giptv.notification("Series not Cached", icon="INFO")
        series_list = xtream_api.streams_by_category(stream_type, category_id)

    if not series_list:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"No streams found in {name}.",
            icon="INFO",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if search_query == "__clear__":
        search_query = None

    if search_query is None:
        li = xbmcgui.ListItem(
            label=f"[COLOR yellow]\ue836[/COLOR] Filter {stream_type.capitalize()} Series"
        )
        li.setArt({"icon": "DefaultAddonSearch.png"})
        items.append(
            (
                _plugin_url(
                    mode="list_series_streams",
                    stream_type=stream_type,
                    category_id=category_id,
                    name=name,
                    search_query="trigger",
                ),
                li,
                True,
            )
        )

    if search_query == "trigger":
        search_query = _show_filter_keyboard(f"Filter {stream_type.upper()} Series")
        if search_query is None:
            giptv.return_action()
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
            return

    if search_query:
        q = search_query.lower()

        def _matches(series):
            return (
                q in (series.get("name") or "").lower()
                or q in (series.get("title") or "").lower()
                or q in (series.get("stream_display_name") or "").lower()
            )

        series_list = [s for s in series_list if _matches(s)]
        if not series_list:
            giptv.notification(
                ADDON.getAddonInfo("name"),
                f"No series found matching '{search_query}'.",
                icon="INFO",
            )
            giptv.return_action()
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
            return

        clear_item = xbmcgui.ListItem(label="[COLOR red]\u2716[/COLOR] Clear Filter")
        clear_item.setArt({"icon": "DefaultAddonSearch.png"})
        items.append(
            (
                _plugin_url(
                    mode="list_series_streams",
                    stream_type=stream_type,
                    category_id=category_id,
                    name=name,
                    search_query="__clear__",
                ),
                clear_item,
                False,
            )
        )

    xbmcplugin.setContent(PLUGIN_HANDLE, "tvshows")

    for series in series_list:
        series_name = series.get("name", "Unknown Series")
        series_id = series.get("series_id")
        plot = series.get("plot", "No description available.")
        rating_str = series.get("rating", "0")
        genre = series.get("genre", "")
        cast_str = series.get("cast", "")
        series_icon = series.get("cover", "")

        release_date = series.get("release_date") or ""
        year_str = release_date.split("-")[0] if "-" in release_date else ""
        year = int(year_str) if year_str.isdigit() else 0

        try:
            rating = float(rating_str)
        except (ValueError, TypeError):
            rating = 0.0

        cast_list = [c.strip() for c in cast_str.split(",")] if cast_str else []
        tmdb_id = _extract_tmdb_id(series)
        backdrop_list = series.get("backdrop_path", [])
        fanart_url = backdrop_list[0] if backdrop_list else ""

        url = _plugin_url(
            mode="list_series_seasons",
            series_id=series_id,
            series_name=series_name,
        )

        li = xbmcgui.ListItem(label=series_name)
        li.addContextMenuItems(SETTINGS_CONTEXT_MENU)

        art_dict = {"icon": "DefaultTVShows.png", "thumb": "DefaultTVShows.png"}
        if series_icon:
            art_dict.update(
                {"thumb": series_icon, "icon": series_icon, "poster": series_icon}
            )
        if fanart_url:
            art_dict["fanart"] = fanart_url
        li.setArt(art_dict)

        tag = li.getVideoInfoTag()
        tag.setTitle(series_name)
        tag.setPlot(plot)
        if genre:
            tag.setGenres([genre])
        tag.setYear(year)
        tag.setMediaType("tvshow")
        tag.setRating(rating, 10)
        tag.setCast([xbmc.Actor(actor) for actor in cast_list if actor])

        if tmdb_id:
            tag.setUniqueIDs({"tmdb": str(tmdb_id)}, "tmdb")
            li.setProperty("imdbnumber", str(tmdb_id))

        items.append((url, li, True))

    _add_dir_items(items)


def list_series_seasons(series_id, series_name):
    if not _ensure_ready():
        return

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, series_name)
    xbmcplugin.setContent(PLUGIN_HANDLE, "videos")

    series_info_response = cache_handler.get(
        "series_info", f"{STATE.username}_{series_id}"
    )
    if not series_info_response:
        if settings.get_cache_on_off(ADDON):
            giptv.notification("Series info not Cached", icon="INFO")
        series_info_response = xtream_api.series_info_by_id(series_id)

    if not series_info_response or "episodes" not in series_info_response:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"Could not retrieve details or episodes for {series_name}.",
            icon="ERROR",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    episodes_by_season = series_info_response.get("episodes", {})
    if not episodes_by_season:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"No seasons or episodes found for {series_name}.",
            icon="INFO",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    series_info = series_info_response.get(
        "info", series_info_response.get("series_info", {})
    )
    series_poster = series_info_response.get("cover", series_info.get("cover", ""))
    backdrop_paths = series_info_response.get("backdrop_path", [])
    series_fanart = backdrop_paths[0] if backdrop_paths else ""
    tmdb_id = _extract_tmdb_id(series_info_response)

    items = []

    for season_num in sorted(episodes_by_season.keys(), key=int):
        season_title = f"Season {season_num}"
        url = _plugin_url(
            mode="list_series_episodes",
            series_id=series_id,
            season_num=season_num,
            series_name=series_name,
            series_poster=series_poster,
            series_fanart=series_fanart,
            tmdb_id=tmdb_id,
        )

        li = xbmcgui.ListItem(label=season_title)
        li.addContextMenuItems(SETTINGS_CONTEXT_MENU)

        art_dict = {"icon": "DefaultSeason.png", "thumb": "DefaultSeason.png"}
        if series_poster:
            art_dict["poster"] = series_poster
            art_dict["thumb"] = series_poster
        if series_fanart:
            art_dict["fanart"] = series_fanart
        li.setArt(art_dict)

        tag = li.getVideoInfoTag()
        tag.setMediaType("season")
        tag.setTitle(season_title)
        tag.setTvShowTitle(series_name)
        tag.setSeason(int(season_num))
        if series_info.get("plot"):
            tag.setPlot(series_info.get("plot"))
        if series_info.get("releaseDate"):
            try:
                tag.setYear(int(series_info.get("releaseDate")[:4]))
            except Exception:
                pass

        if tmdb_id:
            tag.setUniqueIDs({"tmdb": str(tmdb_id)})
            if series_info.get("rating"):
                try:
                    tag.setRating("tmdb", float(series_info.get("rating")), 0, True)
                except (ValueError, TypeError):
                    pass
            else:
                tag.setRating("tmdb", 0, 0, True)

        li.setProperty("tvshow.tmdb_id", str(tmdb_id or ""))
        li.setProperty("season", str(season_num))
        li.setProperty("mediatype", "season")

        items.append((url, li, True))

    _add_dir_items(items)


def list_series_episodes(
    series_id, season_num, series_name, series_poster="", series_fanart="", tmdb_id=""
):
    if not _ensure_ready():
        return

    params = dict(urlparse.parse_qsl(sys.argv[2]))
    series_poster = params.get("series_poster", series_poster)
    series_fanart = params.get("series_fanart", series_fanart)
    tmdb_id = params.get("tmdb_id") or tmdb_id

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, f"{series_name} - Season {season_num}")
    xbmcplugin.setContent(PLUGIN_HANDLE, "episodes")

    series_info = cache_handler.get("series_info", f"{STATE.username}_{series_id}")
    if not series_info:
        if settings.get_cache_on_off(ADDON):
            giptv.notification("Series info not cached", icon="INFO")
        series_info = xtream_api.series_info_by_id(series_id)

    if not series_info:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"Could not retrieve series info for {series_name}.",
            icon="ERROR",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    episodes = series_info.get("episodes", {}).get(season_num, [])
    if not episodes:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"No episodes found for Season {season_num}.",
            icon="INFO",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    tmdb_series_details = tmdb_helper.get_series_details(tmdb_id) if tmdb_id else None
    series_fanart_hd = (
        tmdb_series_details["art"].get("fanart") if tmdb_series_details else None
    )

    items = []

    for episode in episodes:
        episode_data = episode.get("info")
        if isinstance(episode_data, list):
            episode_data = episode_data[0] if episode_data else {}
        if not isinstance(episode_data, dict):
            episode_data = {}

        episode_num_str = str(episode.get("episode_num", "1"))
        base_title = episode.get("title", f"Episode {episode_num_str}")
        episode_title = (
            f"S{int(season_num):02d}E{int(episode_num_str):02d} - {base_title}"
        )

        stream_id = episode.get("id")
        ext = episode.get("container_extension", "mp4")
        play_url = xtream_api.build_stream_url(
            stream_id=stream_id,
            stream_type="series",
            container_extension=ext,
        )
        if not play_url:
            continue

        li = xbmcgui.ListItem(label=episode_title)
        li.setProperty("IsPlayable", "true")
        li.addContextMenuItems(SETTINGS_CONTEXT_MENU)

        episode_icon = episode_data.get("movie_image", "") or episode.get(
            "thumbnail", ""
        )
        episode_still = None
        episode_fanart = series_fanart_hd or series_fanart

        tmdb_ep_details = None
        if tmdb_id:
            tmdb_ep_details = tmdb_helper.get_episode_details(
                tmdb_id, int(season_num), int(episode_num_str)
            )
            if tmdb_ep_details:
                stills = tmdb_ep_details.get("images", {}).get("stills", [])
                if stills:
                    file_path = stills[0].get("file_path")
                    if file_path:
                        episode_still = (
                            f"https://image.tmdb.org/t/p/original{file_path}"
                        )

        art_dict = {"icon": "DefaultVideo.png"}
        art_dict["thumb"] = episode_still or episode_icon or series_poster
        art_dict["poster"] = series_poster or art_dict["thumb"]
        art_dict["fanart"] = episode_fanart or art_dict["thumb"]
        li.setArt(art_dict)

        tag = li.getVideoInfoTag()
        tag.setTitle(base_title)
        tag.setTvShowTitle(series_name)
        tag.setSeason(int(season_num))
        tag.setEpisode(int(episode_num_str))
        tag.setMediaType("episode")

        plot_value = ""
        rating_value = 0
        year_value = 0

        if tmdb_ep_details:
            plot_value = tmdb_ep_details.get("overview") or ""
            rating_value = tmdb_ep_details.get("vote_average") or 0
            air_date = tmdb_ep_details.get("air_date") or ""
            if len(air_date) >= 4 and air_date[:4].isdigit():
                year_value = int(air_date[:4])

            tag.setPlot(plot_value)
            tag.setRating(rating_value, 10)
            tag.setFirstAired(air_date)
            tag.setDuration(tmdb_ep_details.get("runtime") or 0)
        else:
            plot_value = episode_data.get("plot", "")
            tag.setPlot(plot_value)

        if tmdb_id:
            tag.setUniqueIDs({"tmdb": str(tmdb_id)}, "tmdb")
            li.setProperty("tmdbnumber", str(tmdb_id))
            li.setProperty("season", str(season_num))
            li.setProperty("episode", str(episode_num_str))

        metadata = {
            "thumb": art_dict.get("thumb", ""),
            "poster": art_dict.get("poster", ""),
            "fanart": art_dict.get("fanart", ""),
            "icon": art_dict.get("icon", ""),
            "plot": plot_value,
            "rating": rating_value,
            "year": year_value,
            "tmdb_id": str(tmdb_id or ""),
            "stream_type": "series",
        }

        url = _plugin_url(
            mode="play_stream",
            url=play_url,
            name=episode_title,
            meta=_encode_meta(metadata),
        )

        items.append((url, li, False))

    _add_dir_items(items)
