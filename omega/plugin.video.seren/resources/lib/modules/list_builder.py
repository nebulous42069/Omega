import datetime
from threading import Thread

import xbmc
import xbmcplugin

from resources.lib.common import tools
from resources.lib.database.trakt_sync import movies
from resources.lib.database.trakt_sync import shows
from resources.lib.modules.globals import g

# L1 metadata cache — persists across plugin calls with reuselanguageinvoker.
# Key: plugin URL string (action + page + params), Value: formatted list from DB.
# Navigating back to a previously viewed list returns instantly from this cache
# instead of re-running the 5-table SQL JOIN + metadata update.
_L1_CACHE = {}
_L1_CACHE_MAX = 30  # Max cached list results (roughly 30 pages × 20 items each)


def _l1_key():
    """Generate cache key from current request — uniquely identifies each list page."""
    return f"{g.PATH}?{g.PARAM_STRING}"


def _l1_get():
    """Return cached list result or None."""
    return _L1_CACHE.get(_l1_key())


def _l1_set(result):
    """Store list result in L1 cache, evicting oldest if over limit."""
    if len(_L1_CACHE) >= _L1_CACHE_MAX:
        # Remove the oldest entry (first inserted)
        try:
            _L1_CACHE.pop(next(iter(_L1_CACHE)))
        except (StopIteration, RuntimeError):
            pass
    _L1_CACHE[_l1_key()] = result


def clear_l1_cache():
    """Clear the L1 metadata cache. Called when metadata settings change."""
    _L1_CACHE.clear()


class ListBuilder:
    """
    Ease of use class to handle building menus of lists or list items
    """

    def __init__(self):
        self.date_delay = g.get_bool_setting("general.datedelay")
        self.title_appends_mixed = g.get_setting("general.appendtitles")
        self.title_appends_general = g.get_setting("general.appendepisodegeneral")
        self.flatten_episodes = g.get_bool_setting("general.flatten.episodes")
        self.page_limit = g.get_int_setting("item.limit")
        self.hide_unaired = g.get_bool_setting("general.hideUnAired")
        self.list_title_appends = g.get_int_setting("general.appendListTitles")
        self.show_original_title = g.get_bool_setting("general.meta.showoriginaltitle", False)

    def season_list_builder(self, show_id, **params):
        """
        Builds a menu list of a shows seasons
        :param show_id: Trakt ID of show
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        return self._common_menu_builder(
            shows.TraktSyncDatabase().get_season_list(show_id, **params), g.CONTENT_SEASON, "seasonEpisodes", **params
        )

    def episode_list_builder(self, trakt_show_id, trakt_season=None, **params):
        """
        Builds a menu list of a episodes for specified show's season
        :param trakt_show_id: Trakt ID of show
        :param trakt_season: season number
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        params["is_folder"] = False
        params["is_playable"] = True
        action = "getSources"

        return self._common_menu_builder(
            shows.TraktSyncDatabase().get_episode_list(
                trakt_show_id, trakt_season, minimum_episode=params.pop("minimum_episode", None), **params
            ),
            g.CONTENT_EPISODE,
            action,
            **params,
        )

    def mixed_episode_builder(self, trakt_list, **params):
        """
        Builds a menu list of episodes of mixed shows/seasons
        :param trakt_list: List of episode objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        params["is_folder"] = False
        params["is_playable"] = True
        params["mixed_list"] = True
        action = "getSources"

        content_type = params.pop("content_type_override", g.CONTENT_EPISODE)
        return self._common_menu_builder(
            shows.TraktSyncDatabase().get_mixed_episode_list(trakt_list, **params), content_type, action, **params
        )

    def show_list_builder(self, trakt_list, **params):
        """
        Builds a menu list of shows
        :param trakt_list: List of show objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        action = "flatEpisodes" if self.flatten_episodes else "showSeasons"
        if g.get_bool_setting("smartplay.clickresume"):
            params["is_folder"] = False
            params["is_playable"] = True
            action = "forceResumeShow"

        content_type = params.pop("content_type_override", g.CONTENT_SHOW)
        self._common_menu_builder(
            shows.TraktSyncDatabase().get_show_list(trakt_list, **params), content_type, action, **params
        )

    def movie_menu_builder(self, trakt_list, **params):
        """
        Builds a mneu list of movies
        :param trakt_list: List of movie objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        params["is_folder"] = False
        params["is_playable"] = True
        action = "getSources"

        self._common_menu_builder(
            movies.TraktSyncDatabase().get_movie_list(trakt_list, **params), g.CONTENT_MOVIE, action, **params
        )

    def lists_menu_builder(self, trakt_list, **params):
        """
        Builds a menu list of lists
        :param trakt_list: List of list objects
        :param params: Parameters to send to common_menu_builder method
        :return: List list_items if smart_play Kwarg is True else None
        """
        self._common_menu_builder(
            [dict(item, art=g.create_icon_dict("list", g.ICONS_PATH)['art']) for item in trakt_list],
            g.CONTENT_MENU,
            "traktList",
            **params,
        )

    def _common_menu_builder(self, trakt_list, content_type, action="getSources", **params):
        # Background prefetch call (RunPlugin, PLUGIN_HANDLE=-1): data loading already done
        # by the caller (get_movie_list/_update_movies), L1 cache populated. Skip rendering.
        if g.PLUGIN_HANDLE < 0:
            return

        if len(trakt_list) == 0:
            g.log("We received no titles to build a list", "warning")
            g.cancel_directory()
            return

        list_items = []
        smart_play = params.pop("smart_play", False)
        no_paging = params.pop("no_paging", False)
        sort = params.pop("sort", False)
        prepend_date = params.pop("prepend_date", False)
        mixed_list = params.pop("mixed_list", False)
        next_args = params.pop("next_args", None)

        params.pop("hide_unaired", None)
        params.pop("hide_watched", None)
        params.pop("ignore_cache", None)

        try:
            params["bulk_add"] = True
            list_items = [
                g.add_directory_item(
                    item.get("name"), action=action, menu_item=item, action_args=item.get("args"), **params
                )
                for item in self._post_process_list(trakt_list, prepend_date, mixed_list)
                if item is not None
            ]

            if smart_play:
                return list_items
            else:
                xbmcplugin.addDirectoryItems(g.PLUGIN_HANDLE, list_items, len(list_items))
        except Exception as e:
            g.log_stacktrace()
            if not smart_play:
                g.cancel_directory()
            raise e

        finally:
            if not smart_play:
                has_next_page = (
                    not (g.FROM_WIDGET and g.get_bool_setting("general.widget.hide_next"))
                    and not no_paging
                    and len(list_items) >= self.page_limit
                )
                if has_next_page:
                    g.REQUEST_PARAMS["page"] = g.PAGE + 1
                    if next_args:
                        g.REQUEST_PARAMS["action_args"] = next_args
                    elif g.REQUEST_PARAMS.get("action_args") is not None:
                        g.REQUEST_PARAMS["action_args"] = g.REQUEST_PARAMS.get("action_args")
                    params = g.REQUEST_PARAMS
                    params.update({"special_sort": "bottom"})
                    g.add_directory_item(
                        g.get_language_string(33078, addon=False),
                        menu_item=g.create_icon_dict("next", base_path=g.ICONS_PATH),
                        **params,
                    )
                g.close_directory(content_type, sort=sort)

                # Prefetch next page metadata in background (populates SQLite + L1 cache)
                if has_next_page and content_type in (g.CONTENT_MOVIE, g.CONTENT_SHOW):
                    self._prefetch_next_page()

    def _prefetch_next_page(self):
        """Fire a background RunPlugin to prefetch the next page's metadata.

        The RunPlugin call replays the current action with page+1. This triggers:
        1. extract_trakt_page (Trakt API cache hit — instant)
        2. get_movie_list / get_show_list → _update_movies / _update_mill_format_shows
           (fetches TMDB/Fanart/OMDB for any missing items → into SQLite)
        3. L1 list cache populated with formatted results
        4. _common_menu_builder detects PLUGIN_HANDLE < 0 → skips rendering

        When the user clicks "Next Page", metadata is already local and L1-cached.
        """
        try:
            import json as _json
            from urllib import parse as _parse

            prefetch_params = {}
            for key, value in g.REQUEST_PARAMS.items():
                if key == "page":
                    continue
                if key == "action_args" and isinstance(value, dict):
                    prefetch_params[key] = _json.dumps(value, sort_keys=True)
                else:
                    prefetch_params[key] = value

            prefetch_params["page"] = g.PAGE + 1
            url = f"{g.BASE_URL}/?{_parse.urlencode(sorted(prefetch_params.items()))}"
            g.log(f"Prefetching next page metadata: page {g.PAGE + 1}", "debug")
            xbmc.executebuiltin(f'RunPlugin("{url}")')
        except Exception as e:
            g.log(f"Prefetch next page failed: {e}", "debug")

    def is_aired(self, item):
        """
        Confirms supplied item has aired based on meta
        :param info: Meta of item
        :return: Bool, True if object has aired else False
        """
        air_date = item.get("air_date", item["info"].get("aired", item["info"].get("premiered")))

        if not air_date:
            return False

        if int(air_date[:4]) < 1970:
            return True

        air_date = tools.parse_datetime(air_date, False)
        if self.date_delay:
            air_date += datetime.timedelta(days=1)

        return air_date < datetime.datetime.utcnow()

    def _post_process_list(self, item_list, prepend_date=False, mixed_list=False):
        return [self._post_process(item, prepend_date, mixed_list) for item in item_list]

    def _post_process(self, item, prepend_date=False, mixed_list=False):
        if not item:
            return

        if self.show_original_title and item.get("info", {}).get("originaltitle"):
            name = item.get("info", {}).get("originaltitle")
        else:
            name = item.get("info", {}).get("title")

        if not name:
            g.log(f"Item has no title: {item}", "error")

        if item["info"]["mediatype"] != "list" and not self.hide_unaired and not self.is_aired(item):
            name = g.color_string(tools.italic_string(name), "red")

        if item["info"]["mediatype"] == "episode":
            if self.title_appends_mixed and mixed_list:
                name = self._handle_episode_title_appending(name, item, self.title_appends_mixed)
            elif self.title_appends_general and not mixed_list:
                name = self._handle_episode_title_appending(name, item, self.title_appends_general)

            # Filler episode detection for anime
            name = self._handle_filler_tag(name, item)

        if item["info"]["mediatype"] == "list" and self.list_title_appends == 1:
            username = item["info"].get("username", "")
            if username:
                name += f" - {g.color_string(username)}"

        if item["info"]["mediatype"] != "list" and prepend_date:
            if release_date := g.utc_to_local(item.get("air_date", item["info"].get("aired", None))):
                release_day = tools.parse_datetime(release_date, date_only=False).strftime(
                    f"%a %d %b @ {g.KODI_TIME_NO_SECONDS_FORMAT}"
                )
                name = f"[{release_day}] {name}"
        item.update({"name": name})
        item["info"]["title"] = name

        return item

    @staticmethod
    def _handle_episode_title_appending(name, item, title_append_style):
        if title_append_style == "1":
            name = f"{str(item['info']['season']).zfill(2)}x{str(item['info']['episode']).zfill(2)} {name}"

        elif title_append_style == "2":
            name = f"{g.color_string(item['info']['tvshowtitle'])}: {name}"

        elif title_append_style == "3":
            name = f'{g.color_string(item["info"]["tvshowtitle"])}: {str(item["info"]["season"]).zfill(2)}x{str(item["info"]["episode"]).zfill(2)} {name}'

        return name

    @staticmethod
    def _handle_filler_tag(name, item):
        """Tag filler episodes for anime content with a colored FILLER label."""
        if not g.get_bool_setting("anime.fillerDetection"):
            return name
        try:
            genres = item.get("info", {}).get("genre", [])
            if not isinstance(genres, list):
                genres = [genres] if genres else []

            is_anime = any("anime" in genre.lower() for genre in genres)
            if not is_anime:
                country = item.get("info", {}).get("country_origin", "")
                has_animation = any("animation" in genre.lower() for genre in genres)
                if not (has_animation and str(country).upper() in ("JP", "JPN", "JAPAN")):
                    return name

            show_title = item.get("info", {}).get("tvshowtitle", "")
            episode_number = item.get("info", {}).get("episode")
            if not show_title or not episode_number:
                return name

            from resources.lib.modules.anime.filler import get_episode_type
            ep_type = get_episode_type(show_title, int(episode_number))
            if ep_type and "filler" in ep_type.lower() and "canon" not in ep_type.lower():
                name = f"{g.color_string('[FILLER]', 'red')} {name}"
            elif ep_type and "mixed" in ep_type.lower():
                name = f"{g.color_string('[MIXED]', 'orange')} {name}"
        except Exception as e:
            g.log(f"Filler detection error: {e}", "debug")
        return name
