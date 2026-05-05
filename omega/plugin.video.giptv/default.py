# Python 2/3 compatibility for URL parsing
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import sys
import os

sys.path.insert(0, os.getcwd())

import xbmc
import xbmcaddon

import resources.lib.router as router
import resources.utils.giptv as giptv
from resources.lib.manager.index_manager import build_index

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")


def _handle_action(action):
    if action == "close_settings":
        giptv.close_setting()
        return True

    if action == "donate":
        giptv.donate()
        return True

    if action == "clear_cache":
        giptv.clear_cache()
        return True


    if action == "build_search_index":
        giptv.notification("Building Search Index may take ~2 minutes initially")
        build_index(notify=True, source="manual_build_search_index", force=False)
        return True

    if action == "build_search_index_refresh":
        xbmc.executebuiltin("Container.Refresh")
        build_index(notify=True, source="manual_build_search_index_refresh", force=True)
        return True

    if action == "clear_epg_url":
        selected = ADDON.getSetting("account")

        if selected == "1":
            ADDON.setSetting("epg_url1", "")
        elif selected == "2":
            ADDON.setSetting("epg_url2", "")
        else:
            ADDON.setSetting("epg_url", "")

        xbmc.executebuiltin("Container.Refresh")
        return True

    if action == "open_context_window":
        item_id = params.get("item_id", [""])[0]
        name = params.get("name", [""])[0]
        play_url = params.get("play_url", [""])[0]
        stream_type = params.get("stream_type", [""])[0]
        thumb = params.get("thumb", [""])[0]
        poster = params.get("poster", [""])[0]
        fanart = params.get("fanart", [""])[0]
        icon = params.get("icon", [""])[0]
        plot = params.get("plot", [""])[0]
        rating = params.get("rating", ["0"])[0]
        year = params.get("year", ["0"])[0]
        tmdb_id = params.get("tmdb_id", [""])[0]
        channel_id = params.get("channel_id", [""])[0]
        has_archive = params.get("has_archive", ["0"])[0] == "1"

        from resources.lib.manager import favourites_manager

        items = [{"key": "play", "label": "Play"}]

        if has_archive:
            items.append({"key": "catchup", "label": "Catch-up"})

        if favourites_manager.is_favourite(item_id):
            items.append({"key": "remove_favourite", "label": "Remove from Favourites"})
        else:
            items.append({"key": "add_favourite", "label": "Add to Favourites"})

        items.extend(
            [
                {"key": "open_tools", "label": "Open Tools Menu"},
                {"key": "open_settings", "label": "Open Settings"},
            ]
        )

        choice = giptv.open_context_window(name or "GIPTV Menu", items)
        xbmc.sleep(100)

        if choice == "play":
            xbmc.executebuiltin(
                "RunPlugin(plugin://{}/?mode=play_stream&url={}&name={})".format(
                    ADDON_ID,
                    urlparse.quote(play_url, safe=""),
                    urlparse.quote(name, safe=""),
                )
            )

        elif choice == "catchup":
            xbmc.executebuiltin(
                "Container.Update(plugin://{}/?mode=catchup_dates&stream_id={}&channel_id={}&name={})".format(
                    ADDON_ID,
                    urlparse.quote(item_id, safe=""),
                    urlparse.quote(channel_id, safe=""),
                    urlparse.quote(name, safe=""),
                )
            )

        elif choice == "add_favourite":
            from resources.lib.manager.favourites_manager import (
                add_favourite_from_params,
            )

            add_favourite_from_params(
                item_id=item_id,
                title=name,
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
                stream_id=item_id,
            )
            giptv.notification("Channel added to Favourites", icon="INFO")
            xbmc.executebuiltin("Container.Refresh")

        elif choice == "remove_favourite":
            from resources.lib.manager.favourites_manager import (
                remove_favourite_from_params,
            )

            remove_favourite_from_params(item_id=item_id)
            giptv.notification("Channel removed from Favourites", icon="INFO")
            xbmc.executebuiltin("Container.Refresh")

        elif choice == "open_tools":
            _handle_action("open_tools_window")

        elif choice == "open_settings":
            giptv.open_settings()

        return True

    if action == "open_tools_window":
        choice = giptv.open_tools_window()
        xbmc.sleep(100)

        if choice == "open_settings":
            giptv.open_settings()

        # elif choice == "favourites":
        #     xbmc.sleep(150)
        #     xbmc.executebuiltin(
        #         f"Container.Update(plugin://{ADDON_ID}/?mode=favourites)"
        #     )
        #
        # elif choice == "recently_watched":
        #     xbmc.sleep(150)
        #     xbmc.executebuiltin(
        #         f"Container.Update(plugin://{ADDON_ID}/?mode=recently_watched)"
        #     )

        elif choice == "clear_history":
            from resources.lib.manager.history_manager import clear_history

            clear_history()
            giptv.notification("Recently Watched Reset Done", icon="INFO")
            xbmc.executebuiltin("Container.Refresh")

        elif choice == "clear_cache":
            giptv.clear_cache()

        elif choice == "build_search_index":
            build_index(notify=True)

    return False


if __name__ == "__main__":
    params = urlparse.parse_qs(sys.argv[2][1:])
    action = params.get("action", [None])[0]

    if not _handle_action(action):
        router.handle_routing(params)
