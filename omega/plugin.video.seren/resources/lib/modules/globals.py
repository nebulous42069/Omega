# Import Thread lock workaround
# noinspection PyUnresolvedReferences
import contextlib
import json
import os
import re
import traceback
import unicodedata
from functools import cached_property
from urllib import parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.settings_cache import PersistedSettingsCache
from resources.lib.modules.settings_cache import RuntimeSettingsCache

viewTypes = [
    ("Default", 50),
    ("Poster", 51),
    ("Icon Wall", 52),
    ("Shift", 53),
    ("Info Wall", 54),
    ("Wide List", 55),
    ("Wall", 500),
    ("Banner", 501),
    ("Fanart", 502),
]

colorChart = [
    "black",
    "white",
    "whitesmoke",
    "gainsboro",
    "lightgray",
    "silver",
    "darkgray",
    "gray",
    "dimgray",
    "snow",
    "floralwhite",
    "ivory",
    "beige",
    "cornsilk",
    "antiquewhite",
    "bisque",
    "blanchedalmond",
    "burlywood",
    "darkgoldenrod",
    "ghostwhite",
    "azure",
    "aliveblue",
    "lightsaltegray",
    "lightsteelblue",
    "powderblue",
    "lightblue",
    "skyblue",
    "lightskyblue",
    "deepskyblue",
    "dodgerblue",
    "royalblue",
    "blue",
    "mediumblue",
    "midnightblue",
    "navy",
    "darkblue",
    "cornflowerblue",
    "slateblue",
    "slategray",
    "yellowgreen",
    "springgreen",
    "seagreen",
    "steelblue",
    "teal",
    "fuchsia",
    "deeppink",
    "darkmagenta",
    "blueviolet",
    "darkviolet",
    "darkorchid",
    "darkslateblue",
    "darkslategray",
    "indigo",
    "cadetblue",
    "darkcyan",
    "darkturquoise",
    "turquoise",
    "cyan",
    "paleturquoise",
    "lightcyan",
    "mintcream",
    "honeydew",
    "aqua",
    "aquamarine",
    "chartreuse",
    "greenyellow",
    "palegreen",
    "lawngreen",
    "lightgreen",
    "lime",
    "mediumspringgreen",
    "mediumturquoise",
    "lightseagreen",
    "mediumaquamarine",
    "mediumseagreen",
    "limegreen",
    "darkseagreen",
    "forestgreen",
    "green",
    "darkgreen",
    "darkolivegreen",
    "olive",
    "olivedab",
    "darkkhaki",
    "khaki",
    "gold",
    "goldenrod",
    "lightyellow",
    "lightgoldenrodyellow",
    "lemonchiffon",
    "yellow",
    "seashell",
    "lavenderblush",
    "lavender",
    "lightcoral",
    "indianred",
    "darksalmon",
    "lightsalmon",
    "pink",
    "lightpink",
    "hotpink",
    "magenta",
    "plum",
    "violet",
    "orchid",
    "palevioletred",
    "mediumvioletred",
    "purple",
    "marron",
    "mediumorchid",
    "mediumpurple",
    "mediumslateblue",
    "thistle",
    "linen",
    "mistyrose",
    "palegoldenrod",
    "oldlace",
    "papayawhip",
    "moccasin",
    "navajowhite",
    "peachpuff",
    "sandybrown",
    "peru",
    "chocolate",
    "orange",
    "darkorange",
    "tomato",
    "orangered",
    "red",
    "crimson",
    "salmon",
    "coral",
    "firebrick",
    "brown",
    "darkred",
    "tan",
    "rosybrown",
    "sienna",
    "saddlebrown",
]

info_labels = {
    "genre",
    "country",
    "year",
    "episode",
    "season",
    "sortepisode",
    "sortseason",
    "episodeguide",
    "showlink",
    "top250",
    "setid",
    "tracknumber",
    "rating",
    "userrating",
    "watched",
    "playcount",
    "overlay",
    "castandrole",
    "director",
    "mpaa",
    "plot",
    "plotoutline",
    "title",
    "originaltitle",
    "sorttitle",
    "duration",
    "studio",
    "tagline",
    "writer",
    "tvshowtitle",
    "premiered",
    "status",
    "set",
    "setoverview",
    "tag",
    "imdbnumber",
    "code",
    "aired",
    "credits",
    "lastplayed",
    "album",
    "artist",
    "votes",
    "path",
    "trailer",
    "dateadded",
    "mediatype",
    "dbid",
}

info_dates = {
    "premiered",
    "aired",
    "lastplayed",
    "dateadded",
}

listitem_properties = [
    (("awards",), "Awards"),
    (("oscar_wins",), "Oscar_Wins"),
    (("oscar_nominations",), "Oscar_Nominations"),
    (("award_wins",), "Award_Wins"),
    (("award_nominations",), "Award_Nominations"),
    (("metacritic_rating",), "Metacritic_Rating"),
    (("rating.tmdb", "rating"), "TMDb_Rating"),
    (("rating.tmdb", "votes"), "TMDb_Votes"),
    (("rating.tvdb", "rating"), "Tvdb_Rating"),
    (("rating.tvdb", "votes"), "Tvdb_Votes"),
    (("rating.imdb", "rating"), "IMDb_Rating"),
    (("rating.imdb", "votes"), "IMDb_Votes"),
    (("rating.trakt", "rating"), "Trakt_Rating"),
    (("rating.trakt", "votes"), "Trakt_Votes"),
    (("rottentomatoes_rating",), "RottenTomatoes_Rating"),
    (("rottentomatoes_image",), "RottenTomatoes_Image"),
    (("rottentomatoes_reviewstotal",), "RottenTomatoes_ReviewsTotal"),
    (("rottentomatoes_reviewsfresh",), "RottenTomatoes_ReviewsFresh"),
    (("rottentomatoes_reviewsrotten",), "RottenTomatoes_ReviewsRotten"),
    (("rottentomatoes_consensus",), "RottenTomatoes_Consensus"),
    (("rottentomatoes_usermeter",), "RottenTomatoes_UserMeter"),
    (("rottentomatoes_userreviews",), "RottenTomatoes_UserReviews"),
]


class GlobalVariables:
    CONTENT_MENU = ""
    CONTENT_FILES = "files"
    CONTENT_MOVIE = "movies"
    CONTENT_SHOW = "tvshows"
    CONTENT_SEASON = "seasons"
    CONTENT_EPISODE = "episodes"
    CONTENT_GENRES = "genres"
    CONTENT_YEARS = "years"
    MEDIA_MENU = ""
    MEDIA_FOLDER = "file"
    MEDIA_MOVIE = "movie"
    MEDIA_SHOW = "tvshow"
    MEDIA_SEASON = "season"
    MEDIA_EPISODE = "episode"

    SEMVER_REGEX = re.compile(r"^((?:\d+\.){2}\d+)")
    _SERVICE_STATE_KEY = "seren.service_state"
    _ID_KEYS = {"tmdb_id": "tmdb", "imdb_id": "imdb", "tvdb_id": "tvdb"}
    _EPISODE_SEASON_TYPES = frozenset({"episode", "season"})

    # cached_property names that depend on settings and must be cleared when settings change
    # (with reuselanguageinvoker, these persist across plugin calls)
    _CACHED_SETTING_PROPS = (
        "_debrid_available", "_premiumize_enabled", "_real_debrid_enabled",
        "_all_debrid_enabled", "_torbox_enabled", "_debridlink_enabled", "_offcloud_enabled",
        "menu_caching_enabled", "set_views_enabled", "disable_notification_sound",
        "fanart_fallback_disabled", "studio_limit", "_local_is_utc",
    )

    def __init__(self):
        self.IS_ADDON_FIRSTRUN = None
        self.ADDON = None
        self.ADDON_DATA_PATH = None
        self.ADDON_ID = None
        self.ADDON_NAME = None
        self.VERSION = None
        self.CLEAN_VERSION = None
        self.USER_AGENT = None
        self.DEFAULT_FANART = None
        self.DEFAULT_ICON = None
        self.DEFAULT_LOGO = None
        self.DEFAULT_POSTER = None
        self.NEXT_PAGE_ICON = None
        self.ADDON_USERDATA_PATH = None
        self.SETTINGS_CACHE = None
        self.RUNTIME_SETTINGS_CACHE = None
        self.LANGUAGE_CACHE = {}
        self.PLAYLIST = None
        self.HOME_WINDOW = None
        self.KODI_DATE_LONG_FORMAT = None
        self.KODI_DATE_SHORT_FORMAT = None
        self.KODI_TIME_FORMAT = None
        self.KODI_TIME_NO_SECONDS_FORMAT = None
        self.KODI_FULL_VERSION = None
        self.KODI_VERSION = None
        self.PLATFORM = None
        self.UTC_TIMEZONE = None
        self.LOCAL_TIMEZONE = None
        self.URL = None
        self.PLUGIN_HANDLE = 0
        self.IS_SERVICE = True
        self.BASE_URL = None
        self.PATH = None
        self.PARAM_STRING = None
        self.REQUEST_PARAMS = None
        self.FROM_WIDGET = False
        self.PAGE = 1

    def __del__(self):
        self.deinit()

    def deinit(self):
        self.ADDON = None
        del self.ADDON
        self.PLAYLIST = None
        del self.PLAYLIST
        self.HOME_WINDOW = None
        del self.HOME_WINDOW
        # Release the singleton Monitor so Kodi's Python invoker can clean up.
        # Without this, xbmc.Monitor objects accumulate across plugin calls
        # and Kodi warns "has left several classes in memory".
        GlobalVariables._MONITOR = None

    def clear_cached_settings_properties(self):
        """Clear all cached_property values that depend on settings.

        Must be called when settings change (onSettingsChanged) so that
        with reuselanguageinvoker enabled, stale cached values are discarded.
        Next access recalculates from the fresh settings cache.
        """
        for prop in self._CACHED_SETTING_PROPS:
            self.__dict__.pop(prop, None)

    def init_globals(self, argv=None, addon_id=None):
        self.IS_ADDON_FIRSTRUN = self.IS_ADDON_FIRSTRUN is None
        self.ADDON = xbmcaddon.Addon()

        # Lazy-load pytz only when needed (first call per session)
        if self.UTC_TIMEZONE is None:
            from resources.lib.third_party import pytz
            self.UTC_TIMEZONE = pytz.utc

        if self._load_service_state():
            # Fast path: immutable state loaded from window properties set by service.py
            self.PLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            self.HOME_WINDOW = xbmcgui.Window(10000)
            self._init_settings_cache()
        else:
            # Full init: service hasn't stored state yet (first boot or service restart)
            self.ADDON_ID = addon_id or self.ADDON.getAddonInfo("id")
            self.ADDON_NAME = self.ADDON.getAddonInfo("name")
            self.VERSION = self.ADDON.getAddonInfo("version")
            self.CLEAN_VERSION = self.SEMVER_REGEX.findall(self.VERSION)[0]
            self.USER_AGENT = f"{self.ADDON_NAME} - {self.CLEAN_VERSION}"
            self.PLATFORM = self._get_system_platform()
            self._init_kodi()
            self._init_settings_cache()
            self._init_local_timezone()
            self._init_paths()
            self.DEFAULT_FANART = self.ADDON.getAddonInfo("fanart")
            self.DEFAULT_ICON = self.ADDON.getAddonInfo("icon")
            self.DEFAULT_LOGO = f"{self.IMAGES_PATH}logo-seren-3.png"
            self.DEFAULT_POSTER = f"{self.IMAGES_PATH}poster-seren-3.png"
            self.NEXT_PAGE_ICON = f"{self.IMAGES_PATH}next.png"

        self.init_request(argv)
        self._init_cache()

    def _store_service_state(self):
        """
        Store all immutable state as a single JSON blob in a window property.
        Called once from service.py after full init_globals().
        Plugin-side init_globals() reads this back via _load_service_state().
        """
        state = {
            "ADDON_ID": self.ADDON_ID,
            "ADDON_NAME": self.ADDON_NAME,
            "VERSION": self.VERSION,
            "CLEAN_VERSION": self.CLEAN_VERSION,
            "USER_AGENT": self.USER_AGENT,
            "PLATFORM": self.PLATFORM,
            "KODI_DATE_LONG_FORMAT": self.KODI_DATE_LONG_FORMAT,
            "KODI_DATE_SHORT_FORMAT": self.KODI_DATE_SHORT_FORMAT,
            "KODI_TIME_FORMAT": self.KODI_TIME_FORMAT,
            "KODI_TIME_NO_SECONDS_FORMAT": self.KODI_TIME_NO_SECONDS_FORMAT,
            "KODI_FULL_VERSION": self.KODI_FULL_VERSION,
            "KODI_VERSION": self.KODI_VERSION,
            "LOCAL_TIMEZONE_ZONE": self.LOCAL_TIMEZONE.zone if self.LOCAL_TIMEZONE else "UTC",
            "ADDONS_PATH": self.ADDONS_PATH,
            "ADDON_PATH": self.ADDON_PATH,
            "ADDON_DATA_PATH": self.ADDON_DATA_PATH,
            "ADDON_USERDATA_PATH": self.ADDON_USERDATA_PATH,
            "SETTINGS_PATH": self.SETTINGS_PATH,
            "ADVANCED_SETTINGS_PATH": self.ADVANCED_SETTINGS_PATH,
            "KODI_DATABASE_PATH": self.KODI_DATABASE_PATH,
            "GUI_PATH": self.GUI_PATH,
            "IMAGES_PATH": self.IMAGES_PATH,
            "ICONS_PATH": self.ICONS_PATH,
            "GENRES_PATH": self.GENRES_PATH,
            "SKINS_PATH": self.SKINS_PATH,
            "CACHE_DB_PATH": self.CACHE_DB_PATH,
            "TORRENT_CACHE": self.TORRENT_CACHE,
            "TORRENT_ASSIST": self.TORRENT_ASSIST,
            "PROVIDER_CACHE_DB_PATH": self.PROVIDER_CACHE_DB_PATH,
            "PREMIUMIZE_DB_PATH": self.PREMIUMIZE_DB_PATH,
            "DEBRID_CACHE_DB_PATH": self.DEBRID_CACHE_DB_PATH,
            "PROVIDER_PERF_DB_PATH": self.PROVIDER_PERF_DB_PATH,
            "UNDESIRABLES_DB_PATH": self.UNDESIRABLES_DB_PATH,
            "TITLE_SUBS_DB_PATH": self.TITLE_SUBS_DB_PATH,
            "TRAKT_SYNC_DB_PATH": self.TRAKT_SYNC_DB_PATH,
            "MDBLIST_SYNC_DB_PATH": self.MDBLIST_SYNC_DB_PATH,
            "SEARCH_HISTORY_DB_PATH": self.SEARCH_HISTORY_DB_PATH,
            "SKINS_DB_PATH": self.SKINS_DB_PATH,
            "ANIME_CACHE_DB_PATH": self.ANIME_CACHE_DB_PATH,
            "ANIME_MAPPING_DB_PATH": self.ANIME_MAPPING_DB_PATH,
            "DEFAULT_FANART": self.DEFAULT_FANART,
            "DEFAULT_ICON": self.DEFAULT_ICON,
            "DEFAULT_LOGO": self.DEFAULT_LOGO,
            "DEFAULT_POSTER": self.DEFAULT_POSTER,
            "NEXT_PAGE_ICON": self.NEXT_PAGE_ICON,
        }
        self.HOME_WINDOW.setProperty(self._SERVICE_STATE_KEY, json.dumps(state))

    def _load_service_state(self):
        """
        Load immutable state from window property set by service.py.
        Returns True if state was loaded (fast path), False if not available (full init needed).
        """
        try:
            window = xbmcgui.Window(10000)
            state_json = window.getProperty(self._SERVICE_STATE_KEY)
            if not state_json:
                return False

            state = json.loads(state_json)

            # Version check: if the cached version doesn't match the actual addon version,
            # reject the cached state so do_version_change() detects the upgrade.
            # This prevents stale state from a previous version persisting after a zip install.
            actual_version = self.ADDON.getAddonInfo("version")
            if state.get("VERSION") != actual_version:
                window.clearProperty(self._SERVICE_STATE_KEY)
                return False

            # Addon info
            self.ADDON_ID = state["ADDON_ID"]
            self.ADDON_NAME = state["ADDON_NAME"]
            self.VERSION = state["VERSION"]
            self.CLEAN_VERSION = state["CLEAN_VERSION"]
            self.USER_AGENT = state["USER_AGENT"]
            self.PLATFORM = state["PLATFORM"]

            # Kodi info
            self.KODI_DATE_LONG_FORMAT = state["KODI_DATE_LONG_FORMAT"]
            self.KODI_DATE_SHORT_FORMAT = state["KODI_DATE_SHORT_FORMAT"]
            self.KODI_TIME_FORMAT = state["KODI_TIME_FORMAT"]
            self.KODI_TIME_NO_SECONDS_FORMAT = state["KODI_TIME_NO_SECONDS_FORMAT"]
            self.KODI_FULL_VERSION = state["KODI_FULL_VERSION"]
            self.KODI_VERSION = int(state["KODI_VERSION"])

            # Timezone
            tz_zone = state.get("LOCAL_TIMEZONE_ZONE", "UTC")
            try:
                from resources.lib.third_party import pytz
                self.LOCAL_TIMEZONE = pytz.timezone(tz_zone)
            except Exception:
                self.LOCAL_TIMEZONE = self.UTC_TIMEZONE

            # Paths
            self.ADDONS_PATH = state["ADDONS_PATH"]
            self.ADDON_PATH = state["ADDON_PATH"]
            self.ADDON_DATA_PATH = state["ADDON_DATA_PATH"]
            self.ADDON_USERDATA_PATH = state["ADDON_USERDATA_PATH"]
            self.SETTINGS_PATH = state["SETTINGS_PATH"]
            self.ADVANCED_SETTINGS_PATH = state["ADVANCED_SETTINGS_PATH"]
            self.KODI_DATABASE_PATH = state["KODI_DATABASE_PATH"]
            self.GUI_PATH = state["GUI_PATH"]
            self.IMAGES_PATH = state["IMAGES_PATH"]
            self.ICONS_PATH = state["ICONS_PATH"]
            self.GENRES_PATH = state["GENRES_PATH"]
            self.SKINS_PATH = state["SKINS_PATH"]
            self.CACHE_DB_PATH = state["CACHE_DB_PATH"]
            self.TORRENT_CACHE = state["TORRENT_CACHE"]
            self.TORRENT_ASSIST = state["TORRENT_ASSIST"]
            self.PROVIDER_CACHE_DB_PATH = state["PROVIDER_CACHE_DB_PATH"]
            self.PREMIUMIZE_DB_PATH = state["PREMIUMIZE_DB_PATH"]
            self.DEBRID_CACHE_DB_PATH = state["DEBRID_CACHE_DB_PATH"]
            self.PROVIDER_PERF_DB_PATH = state["PROVIDER_PERF_DB_PATH"]
            self.UNDESIRABLES_DB_PATH = state["UNDESIRABLES_DB_PATH"]
            self.TITLE_SUBS_DB_PATH = state["TITLE_SUBS_DB_PATH"]
            self.TRAKT_SYNC_DB_PATH = state["TRAKT_SYNC_DB_PATH"]
            self.MDBLIST_SYNC_DB_PATH = state["MDBLIST_SYNC_DB_PATH"]
            self.SEARCH_HISTORY_DB_PATH = state["SEARCH_HISTORY_DB_PATH"]
            self.SKINS_DB_PATH = state["SKINS_DB_PATH"]
            self.ANIME_CACHE_DB_PATH = state["ANIME_CACHE_DB_PATH"]
            self.ANIME_MAPPING_DB_PATH = state["ANIME_MAPPING_DB_PATH"]

            # Assets
            self.DEFAULT_FANART = state["DEFAULT_FANART"]
            self.DEFAULT_ICON = state["DEFAULT_ICON"]
            self.DEFAULT_LOGO = state["DEFAULT_LOGO"]
            self.DEFAULT_POSTER = state["DEFAULT_POSTER"]
            self.NEXT_PAGE_ICON = state["NEXT_PAGE_ICON"]

            return True
        except (KeyError, ValueError, TypeError):
            return False

    def _init_kodi(self):
        self.PLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.HOME_WINDOW = xbmcgui.Window(10000)
        self.KODI_DATE_LONG_FORMAT = xbmc.getRegion("datelong")
        self.KODI_DATE_SHORT_FORMAT = xbmc.getRegion("dateshort")
        self.KODI_TIME_FORMAT = xbmc.getRegion("time")
        self.KODI_TIME_NO_SECONDS_FORMAT = self.KODI_TIME_FORMAT.replace(":%S", "")
        self.KODI_FULL_VERSION = xbmc.getInfoLabel("System.BuildVersion")
        if version := re.findall(r'(?:(?:((?:\d+\.?){1,3}\S+))?\s+\(((?:\d+\.?){2,3})\))', self.KODI_FULL_VERSION):
            self.KODI_FULL_VERSION = version[0][1]
            if len(version[0][0]) > 1:
                pre_ver = version[0][0][:2]
                full_ver = version[0][1][:2]
                if pre_ver > full_ver:
                    self.KODI_VERSION = int(pre_ver[:2])
                else:
                    self.KODI_VERSION = int(full_ver[:2])
            else:
                self.KODI_VERSION = int(version[0][1][:2])
        else:
            self.KODI_FULL_VERSION = self.KODI_FULL_VERSION.split(' ')[0]
            self.KODI_VERSION = int(self.KODI_FULL_VERSION[:2])

    def _init_settings_cache(self):
        self.RUNTIME_SETTINGS_CACHE = RuntimeSettingsCache()
        self.SETTINGS_CACHE = PersistedSettingsCache()

    def _init_local_timezone(self):
        from resources.lib.third_party import pytz
        try:
            timezone_string = self.get_setting("general.localtimezone")
            if timezone_string:
                self.LOCAL_TIMEZONE = pytz.timezone(timezone_string)
        except pytz.UnknownTimeZoneError:
            self.log(f"Invalid local timezone '{timezone_string}' in settings.xml", "debug")
        except Exception as e:
            self.log(f"Error using local timezone '{timezone_string}' in settings.xml: {e}", "warning")
        finally:
            if not self.LOCAL_TIMEZONE or self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                self.init_local_timezone()

    def init_local_timezone(self):
        """
        Attempts to detect the local timezone via a variety of approaches
        Initializes LOCAL_TIMEZONE to correct tzinfo value
        If this fails we should just use UTC as lack of any LOCAL_TIMEZONE will cause many failures
        :return: None
        """
        from resources.lib.third_party import pytz
        timezone_string = None
        try:
            try:
                response = self.json_rpc("Settings.GetSettingValue", {"setting": "locale.timezone"})
                timezone_string = response.get("value", '')

                self.LOCAL_TIMEZONE = pytz.timezone(timezone_string)
            except pytz.UnknownTimeZoneError:
                if timezone_string:
                    self.log(
                        f"Kodi provided an invalid local timezone '{timezone_string}', trying a different approach",
                        "warning",
                    )
                else:
                    self.log(
                        "Kodi does not support locale.timezone JSON RPC call on your platform, trying a different "
                        "approach",
                        "debug",
                    )
            except Exception as e:
                self.log(f"Error detecting local timezone with Kodi, trying a different approach: {e}", "warning")
            # If Kodi detection failed, fall back on tzlocal
            try:
                if not self.LOCAL_TIMEZONE or self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                    from resources.lib.third_party import tzlocal

                    self.LOCAL_TIMEZONE = tzlocal.get_localzone()
            except Exception as e:
                self.log(f"Error detecting local timezone with alternative approach: {e}", "warning")
            # If we still don't have a timezone, try manual setting
            try:
                if not self.LOCAL_TIMEZONE or self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                    g.set_setting("general.manualtimezone", True)
                    timezone_string = self.get_setting("general.localtimezone")
                    if timezone_string:
                        self.LOCAL_TIMEZONE = pytz.timezone(timezone_string)
                else:
                    g.set_setting("general.manualtimezone", False)
            except pytz.UnknownTimeZoneError:
                self.log(f"Invalid local timezone '{timezone_string}' in settings.xml", "debug")
            except Exception as e:
                self.log(f"Error using local timezone '{timezone_string}' in settings.xml: {e}", "warning")
        finally:
            # If Kodi and tzocal detection fails and we don't have a valid manual setting, fallback to UTC
            if not self.LOCAL_TIMEZONE:
                self.LOCAL_TIMEZONE = self.UTC_TIMEZONE
            if self.LOCAL_TIMEZONE == self.UTC_TIMEZONE:
                self.log(
                    "Unable to detect local timezone, defaulting to UTC for displayed dates/times. "
                    "Note that this does not affect filtering or sorting, only display",
                    "debug",
                )
            self.set_setting("general.localtimezone", self.LOCAL_TIMEZONE.zone)

    @staticmethod
    def _get_system_platform():
        """
        get platform on which xbmc run
        """
        platform = "unknown"
        if xbmc.getCondVisibility("system.platform.android"):
            platform = "android"
        elif xbmc.getCondVisibility("system.platform.linux"):
            platform = "linux"
        elif xbmc.getCondVisibility("system.platform.xbox"):
            platform = "xbox"
        elif xbmc.getCondVisibility("system.platform.windows"):
            platform = "xbox" if "Users\\UserMgr" in os.environ.get("TMP") else "windows"
        elif xbmc.getCondVisibility("system.platform.osx"):
            platform = "osx"

        return platform

    def _init_cache(self):
        from resources.lib.database.cache import Cache

        self.CACHE = Cache()

    def init_request(self, argv):
        if argv is None:
            return

        self.URL = parse.urlparse(argv[0])
        try:
            self.PLUGIN_HANDLE = int(argv[1])
            self.IS_SERVICE = False
        except IndexError:
            self.PLUGIN_HANDLE = 0
            self.IS_SERVICE = True

        self.BASE_URL = f"{self.URL[0]}://{self.URL[1]}" if self.URL[1] != "" else ""
        self.PATH = parse.unquote(self.URL[2])
        try:
            self.PARAM_STRING = argv[2].lstrip('?/')
        except IndexError:
            self.PARAM_STRING = ""
        self.REQUEST_PARAMS = self.legacy_params_converter(dict(parse.parse_qsl(self.PARAM_STRING)))
        if "action_args" in self.REQUEST_PARAMS:
            self.REQUEST_PARAMS["action_args"] = tools.deconstruct_action_args(self.REQUEST_PARAMS["action_args"])
            if isinstance(self.REQUEST_PARAMS["action_args"], dict):
                self.REQUEST_PARAMS["action_args"] = self.legacy_action_args_converter(
                    self.REQUEST_PARAMS["action_args"]
                )
        self.FROM_WIDGET = not self.is_addon_visible()
        self.PAGE = int(g.REQUEST_PARAMS.get("page", 1))

    @staticmethod
    def legacy_action_args_converter(action_args):
        if "item_type" not in action_args:
            return action_args

        if not action_args.get("trakt_id"):
            g.log("legacy_action_args_converter: trakt_id is missing or None, cannot resolve", "warning")
            action_args["mediatype"] = action_args.pop("item_type")
            return action_args

        if "season" in action_args["item_type"]:
            from resources.lib.database.trakt_sync import shows

            action_args.update(
                shows.TraktSyncDatabase().get_season_action_args(action_args["trakt_id"], action_args["season"])
            )

        if "episode" in action_args["item_type"]:
            from resources.lib.database.trakt_sync import shows

            action_args.update(
                shows.TraktSyncDatabase().get_episode_action_args(
                    action_args["trakt_id"],
                    action_args["season"],
                    action_args["episode"],
                )
            )

        if "show" in action_args["item_type"]:
            action_args["item_type"] = "shows"

        action_args["mediatype"] = action_args.pop("item_type")
        return action_args

    @staticmethod
    def legacy_params_converter(params):
        if "actionArgs" in params:
            params["action_args"] = params.pop("actionArgs")
        if "action" in params:
            if params["action"] == "moviesTrending":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "trending"
                params["mediatype"] = "movies"
            if params["action"] == "moviesPopular":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "popular"
                params["mediatype"] = "movies"
            if params["action"] == "moviesWatched":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "watched"
                params["mediatype"] = "movies"
            if params["action"] == "moviesCollected":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "collected"
                params["mediatype"] = "movies"
            if params["action"] == "moviesAnticipated":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "anticipated"
                params["mediatype"] = "movies"
            if params["action"] == "moviesBoxOffice":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "boxoffice"
                params["mediatype"] = "movies"
            if params["action"] == "showsTrending":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "trending"
                params["mediatype"] = "shows"
            if params["action"] == "showsPopular":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "popular"
                params["mediatype"] = "shows"
            if params["action"] == "showsWatched":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "watched"
                params["mediatype"] = "shows"
            if params["action"] == "showsCollected":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "collected"
                params["mediatype"] = "shows"
            if params["action"] == "showsAnticipated":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "anticipated"
                params["mediatype"] = "shows"
            if params["action"] == "showsBoxOffice":
                params["action"] = "genericEndpoint"
                params["endpoint"] = "boxoffice"
                params["mediatype"] = "shows"
        return params

    def _init_paths(self):
        self.ADDONS_PATH = tools.translate_path(os.path.join("special://home/", "addons/"))
        self.ADDON_PATH = tools.translate_path(os.path.join("special://home/", f"addons/{self.ADDON_ID.lower()}"))
        self.ADDON_DATA_PATH = tools.translate_path(self.ADDON.getAddonInfo("path"))  # Addon folder
        self.ADDON_USERDATA_PATH = tools.translate_path(
            f"special://profile/addon_data/{self.ADDON_ID}/"
        )  # Addon user data folder
        self.SETTINGS_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "settings.xml"))
        self.ADVANCED_SETTINGS_PATH = tools.translate_path("special://profile/advancedsettings.xml")
        self.KODI_DATABASE_PATH = tools.translate_path("special://database/")
        self.GUI_PATH = tools.translate_path(os.path.join(self.ADDON_DATA_PATH, "resources", "lib", "gui"))
        self.IMAGES_PATH = f"{self.ADDON.getAddonInfo('path')}/resources/images/"
        self.ICONS_PATH = f"{self.IMAGES_PATH}icons/"
        self.GENRES_PATH = f"{self.IMAGES_PATH}genres/"
        self.SKINS_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "skins"))
        self.CACHE_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "cache.db"))
        self.TORRENT_CACHE = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "torrentCache.db"))
        self.TORRENT_ASSIST = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "torentAssist.db"))
        self.PROVIDER_CACHE_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "providers.db"))
        self.PREMIUMIZE_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "premiumize.db"))
        self.DEBRID_CACHE_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "debridCache.db"))
        self.PROVIDER_PERF_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "providerPerf.db"))
        self.UNDESIRABLES_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "undesirables.db"))
        self.TITLE_SUBS_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "titleSubs.db"))
        self.TRAKT_SYNC_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "traktSync.db"))
        self.MDBLIST_SYNC_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "mdblistSync.db"))
        self.SEARCH_HISTORY_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "search.db"))
        self.SKINS_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "skins.db"))
        self.ANIME_CACHE_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "animeCache.db"))
        self.ANIME_MAPPING_DB_PATH = tools.translate_path(os.path.join(self.ADDON_USERDATA_PATH, "animeMappings.db"))

    def get_kodi_video_db_connection(self):
        config = self.get_kodi_video_db_config()
        if config["type"] == "sqlite3":
            from resources.lib.database import SQLiteConnection

            return SQLiteConnection(os.path.join(self.KODI_DATABASE_PATH, f"{config['database']}.db"))
        elif config["type"] == "mysql":
            from resources.lib.database import MySqlConnection

            return MySqlConnection(config)

    def get_kodi_database_version(self):
        kodi_myvideos_version_map = {
            17: 107,
            18: 116,
            19: 119,
            20: 121,
            21: 131,
            22: 132,
        }

        if (db_version := kodi_myvideos_version_map.get(self.KODI_VERSION)) is None:
            raise KeyError("Unsupported kodi version")

        return db_version

    def get_kodi_video_db_config(self):
        result = {"type": "sqlite3", "database": f"MyVideos{self.get_kodi_database_version()}"}

        if xbmcvfs.exists(self.ADVANCED_SETTINGS_PATH):
            if advanced_settings_text := g.read_all_text(self.ADVANCED_SETTINGS_PATH):
                from xml.etree import ElementTree
                try:
                    advanced_settings = ElementTree.fromstring(advanced_settings_text)
                    if settings := advanced_settings.find("videodatabase"):
                        for setting in settings:
                            if setting.tag == 'type':
                                result["type"] = setting.text
                            elif setting.tag == 'host':
                                result["host"] = setting.text
                            elif setting.tag == 'port':
                                result["port"] = setting.text
                            elif setting.tag == 'name':
                                result["database"] = setting.text
                            elif setting.tag == 'user':
                                result["user"] = setting.text
                            elif setting.tag == 'pass':
                                result["password"] = setting.text
                except ElementTree.ParseError as pe:
                    g.log(f"Failed to parse advanced settings.xml: {pe}", "warning")
        return result

    def clear_kodi_bookmarks(self):
        try:
            with self.get_kodi_video_db_connection() as video_database:
                if file_ids := [
                    str(i["idFile"])
                    for i in video_database.fetchall("SELECT * FROM files WHERE strFilename LIKE '%plugin.video.seren%'")
                ]:
                    video_database.execute_sql(
                        [
                            f"DELETE FROM {table} WHERE idFile IN ({','.join(file_ids)})"
                            for table in ["bookmark", "streamdetails", "files"]
                        ]
                    )
                else:
                    return
        except Exception as e:
            g.log(f"Failed to clear Kodi bookmarks: {e}", "warning")

    # region runtime settings
    def set_runtime_setting(self, setting_id, value):
        """
        Set a runtime setting value

        Lists and Dict may only contain simple types

        :param setting_id: The name of the setting
        :type setting_id: str
        :param value: The value to store in settings
        :type value: str|float|int|bool|list|dict
        """
        self.RUNTIME_SETTINGS_CACHE.set_setting(setting_id, value)

    def clear_runtime_setting(self, setting_id):
        """
        Clear a runtime setting from the cache.

        :param setting_id: The name of the setting
        :type setting_id: str
        """
        self.RUNTIME_SETTINGS_CACHE.clear_setting(setting_id)

    def get_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: str|float|int|bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or None
        :rtype: str|float|int|bool|list|dict
        """
        return self.RUNTIME_SETTINGS_CACHE.get_setting(setting_id, default_value)

    def get_float_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting as a float value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: float
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0.0
        :rtype: float
        """
        return self.RUNTIME_SETTINGS_CACHE.get_float_setting(setting_id, default_value)

    def get_int_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting as an int value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: int
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0
        :rtype: int
        """
        return self.RUNTIME_SETTINGS_CACHE.get_int_setting(setting_id, default_value)

    def get_bool_runtime_setting(self, setting_id, default_value=None):
        """
        Get a runtime setting as a bool value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or False
        :rtype: bool
        """
        return self.RUNTIME_SETTINGS_CACHE.get_bool_setting(setting_id, default_value)

    # endregion

    # region KODI setting
    def set_setting(self, setting_id, value):
        """
        Set a setting value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param value: The value to store in settings
        :type value: str|float|int|bool
        """
        self.SETTINGS_CACHE.set_setting(setting_id, value)

    def clear_setting(self, setting_id):
        """
        Clear a setting from the cache and settings.xml

        :param setting_id: The name of the setting
        :type setting_id: str
        """
        self.SETTINGS_CACHE.clear_setting(setting_id)

    def get_setting(self, setting_id, default_value=None):
        """
        Get a setting value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value:
        :type default_value: str
        :return: The value of the setting as a string
                 If the setting is not stored, the optional default_value if provided or None
        :rtype: str
        """
        return self.SETTINGS_CACHE.get_setting(setting_id, default_value)

    def get_float_setting(self, setting_id, default_value=None):
        """
        Get a setting as a float value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: float
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0.0
        :rtype: float
        """
        return self.SETTINGS_CACHE.get_float_setting(setting_id, default_value)

    def get_int_setting(self, setting_id, default_value=None):
        """
        Get a setting as an int value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: int
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or 0
        :rtype: int
        """
        return self.SETTINGS_CACHE.get_int_setting(setting_id, default_value)

    def get_bool_setting(self, setting_id, default_value=None):
        """
        Get a setting as a bool value

        :param setting_id: The name of the setting
        :type setting_id: str
        :param default_value: An optional default value to provide if the setting is not stored
        :type default_value: bool
        :return: The value of the setting.
                 If the setting is not stored, the optional default_value if provided or False
        :rtype: bool
        """
        return self.SETTINGS_CACHE.get_bool_setting(setting_id, default_value)

    # endregion

    def get_language_string(self, localization_id, addon=True):
        """
        Gets a localized string from cache if feasible, if not from localization files
        Will retrieve from addon localizations by default but can be requested from Kodi localizations

        :param localization_id: The id of the localization to retrieve
        :type localization_id: int
        :param addon: True to retrieve from addon, False from Kodi localizations.  Default True
        :type addon bool
        :return: The localized text matching the localization_id from the appropriate localization files.
        :rtype: str
        """
        cache_id = f"A{str(localization_id)}" if addon else f"K{str(localization_id)}"
        text = self.LANGUAGE_CACHE.get(cache_id)
        if not text:
            text = self.ADDON.getLocalizedString(localization_id) if addon else xbmc.getLocalizedString(localization_id)
            self.LANGUAGE_CACHE.update({cache_id: text})

        return text

    def get_view_type(self, content_type):
        view_type = None

        if not self.get_bool_setting("general.viewidswitch"):
            if content_type == self.CONTENT_MENU:
                view_type = self.get_setting("addon.view")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view")
            if view_type is not None and view_type.isdigit() and int(view_type) > 0:
                view_name, view_type = viewTypes[int(view_type)]
                return view_type
        else:
            if content_type == self.CONTENT_MENU:
                view_type = self.get_setting("addon.view.id")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view.id")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view.id")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view.id")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view.id")
            if view_type is not None and view_type.isdigit() and int(view_type) > 0:
                return int(view_type)

        return 0

    def log(self, msg, level="info"):
        msg = msg
        msg = f"{self.ADDON_NAME.upper()} ({self.PLUGIN_HANDLE}): {msg}"
        if level == "error":
            xbmc.log(msg, level=xbmc.LOGERROR)
        elif level == "info":
            xbmc.log(msg, level=xbmc.LOGINFO)
        elif level == "notice":
            if self.KODI_VERSION >= 19:
                xbmc.log(msg, level=xbmc.LOGINFO)
            else:
                xbmc.log(msg, level=xbmc.LOGNOTICE)  # pylint: disable=no-member
        elif level == "warning":
            xbmc.log(msg, level=xbmc.LOGWARNING)
        else:
            xbmc.log(msg)

    def log_stacktrace(self):
        """Gets the latest traceback stacktrace and logs it."""
        self.log(traceback.format_exc(), "error")

    def color_picker(self):
        """Method that generates color list and handles the popup."""
        select_list = [self.color_string("inherit")]
        select_list.extend(self.color_string(i, i) for i in colorChart)
        color = xbmcgui.Dialog().select(f"{self.ADDON_NAME}: {self.get_language_string(30016)}", select_list)
        if color == -1:
            return
        if color == 0:
            self.set_setting("general.textColor", "inherit")
            self.set_setting("general.displayColor", "inherit")
        else:
            color -= 1
            self.set_setting("general.textColor", colorChart[color])
            self.set_setting("general.displayColor", colorChart[color])
        self.open_addon_settings(1, 2)

    @staticmethod
    def _try_get_color_from_skin():
        skin_color_lookup = {
            "skin.arctic.horizon": "ff0385b5",
            "skin.arctic.horizon.2": "ff0385b5",
            "skin.arctic.zephyr": "ff0385b5",
            "skin.arctic.zephyr.2": "ff0385b5",
            "skin.aura": "ff0385b5",
            "skin.auramod": "deepskyblue",
            "skin.confluence": "ffeb9e17",
            "skin.eminence": {
                "default": "ff33b5e5",
                "crimson": "ffdc143c",
                "emerald": "ffdc143c",
                "lilac": "ffa682a6",
                "lime": "ffb5e533",
                "magenta": "ffe533b5",
                "orange": "ffd76c38",
            },
            "skin.eminence.2": "ff287ba8",
            "skin.estouchy": "ff11e7b1",
            "skin.estuary": {
                "default": "ff11e7b1",
                "brown": "ffff4400",
                "charcoal": "ff11e7b1",
                "chartreuse": "ff24c6c9",
                "concrete": "ffff8c00",
                "gold": "fffff000",
                "green": "ff14d519",
                "maroon": "ff24c6c9",
                "midnight": "ff5be5ee",
                "orange": "fffff100",
                "pink": "ff94d800",
                "rose": "ffff0261",
                "teal": "ffc67f03",
                "violet": "ffff0054",
            },
            "skin.fuse.neue": "ffe53564",
        }

        if focus_color := xbmc.getInfoLabel("Skin.String(focuscolor.name)"):  # jurial based skins.
            return focus_color

        if skin_dir := xbmc.getSkinDir():
            if isinstance(skin_color := skin_color_lookup.get(skin_dir), dict):
                skin_color = skin_color.get(
                    xbmc.getInfoLabel("Skin.CurrentTheme").lower(), skin_color.get("default", None)
                )
            return skin_color
        return None

    def get_user_text_color(self):
        """Get the user selected color setting when nothing is selecting it returns
        the default value (deepskyblue) or the default form the installed skin.

        :return:Selected color from the user or the default from the skin or the Seren default (deepskyblue)
        :rtype:str
        """
        color = self.get_setting("general.displayColor")
        if not color or color == "None" or color == "inherit":
            color = self._try_get_color_from_skin() or "deepskyblue"

        return color

    def color_string(self, text, color=None):
        """Method that wraps the text with the supplied color, or takes the user default.

        :param text:Text that needs to be wrapped
        :type text:str|int|float
        :param color:Color name used in the Kodi color tag
        :type color:str
        :return:Text wrapped in a Kodi color tag.
        :rtype:str
        """
        if color == "default" or not color or color == "inherit":
            color = self.get_user_text_color()

        return f"[COLOR {color}]{text}[/COLOR]"

    def clear_cache(self, silent=False):
        if not silent:
            confirm = xbmcgui.Dialog().yesno(self.ADDON_NAME, self.get_language_string(30029))
            if confirm != 1:
                return
        g.show_busy_dialog()
        try:
            try:
                g.CACHE.clear_all()
                g._init_cache()
                self.log("Clear All Cache: metadata cache cleared", "info")
            except Exception as e:
                self.log(f"Clear All Cache: metadata cache error: {e}", "warning")
            try:
                from resources.lib.database.debridCache import DebridCache
                DebridCache().clear_all()
                self.log("Clear All Cache: debrid cache cleared", "info")
            except Exception as e:
                self.log(f"Clear All Cache: debrid cache error: {e}", "warning")
            try:
                from resources.lib.database.torrentCache import TorrentCache
                TorrentCache().rebuild_database()
                self.log("Clear All Cache: torrent cache cleared", "info")
            except Exception as e:
                self.log(f"Clear All Cache: torrent cache error: {e}", "warning")
            try:
                from resources.lib.database.providerPerformance import ProviderPerformance
                ProviderPerformance().clear_all()
                self.log("Clear All Cache: provider stats cleared", "info")
            except Exception as e:
                self.log(f"Clear All Cache: provider stats error: {e}", "warning")
            try:
                from resources.lib.database.searchHistory import SearchHistory
                SearchHistory().execute_sql("DELETE FROM search_history")
                self.log("Clear All Cache: search history cleared", "info")
            except Exception as e:
                self.log(f"Clear All Cache: search history error: {e}", "warning")
            # TorrentAssist is only cleared on manual button press (silent=False).
            # Excluded from install/version-change clears (silent=True) so that
            # in-progress transfers are not orphaned mid-upgrade.
            if not silent:
                try:
                    from resources.lib.database.torrentAssist import TorrentAssist
                    TorrentAssist().clear_all()
                    self.log("Clear All Cache: torrent assist cleared", "info")
                except Exception as e:
                    self.log(f"Clear All Cache: torrent assist error: {e}", "warning")
        finally:
            g.close_busy_dialog()
        self.log(f"{self.ADDON_NAME}: All caches cleared", "info")
        if not silent:
            xbmcgui.Dialog().notification(self.ADDON_NAME, self.get_language_string(30052))

    def cancel_playback(self):
        self.PLAYLIST.clear()
        xbmcplugin.setResolvedUrl(self.PLUGIN_HANDLE, False, xbmcgui.ListItem(offscreen=True))
        self.close_busy_dialog()
        self.close_all_dialogs()

    def show_busy_dialog(self):
        xbmc.executebuiltin("ActivateWindow(busydialognocancel)")

    def close_all_dialogs(self):
        xbmc.executebuiltin("Dialog.Close(all,true)")

    def close_ok_dialog(self):
        xbmc.executebuiltin("Dialog.Close(okdialog, true)")

    def close_busy_dialog(self):
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        xbmc.executebuiltin("Dialog.Close(busydialognocancel)")

    @staticmethod
    def deaccent_string(text):
        """Deaccent the provided text leaving other unicode characters intact
        Example: Mîxéd ДљфӭЖ Tëst -> Mixed ДљфэЖ Test
        :param: text: Text to deaccent
        :type text: str
        :return: Deaccented string
        :rtype:str
        """
        nfkd_form = unicodedata.normalize('NFKD', text)  # pylint: disable=c-extension-no-member
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])  # pylint: disable=c-extension-no-member

    @staticmethod
    def transliterate_string(text):
        """Transliterate the provided text into ascii equivalents
        Example: 张新成 -> Zhang Xincheng
        Note that this method will remove any extra whitespace leaving only single spaces *between* characters
        :param: text: Text to transliterate
        :type text: str
        :return: Transliterated string
        :rtype:str
        """
        from unidecode import unidecode
        transliterted_text = unidecode(text)
        # Remove extra whitespace
        transliterted_text = " ".join(transliterted_text.split())
        return transliterted_text

    def premium_check(self):
        return bool(self.PLAYLIST.getposition() > 0 or self.debrid_available())

    @cached_property
    def _debrid_available(self):
        return self.premiumize_enabled() or self.real_debrid_enabled() or self.all_debrid_enabled() or self.torbox_enabled() or self.debridlink_enabled() or self.offcloud_enabled()

    def debrid_available(self):
        return self._debrid_available

    @cached_property
    def _premiumize_enabled(self):
        return bool(self.get_setting("premiumize.token") != "" and self.get_bool_setting("premiumize.enabled"))

    def premiumize_enabled(self):
        return self._premiumize_enabled

    @cached_property
    def _real_debrid_enabled(self):
        return bool(self.get_setting("rd.auth") and self.get_bool_setting("realdebrid.enabled"))

    def real_debrid_enabled(self):
        return self._real_debrid_enabled

    @cached_property
    def _all_debrid_enabled(self):
        return bool(self.get_setting("alldebrid.apikey") != "" and self.get_bool_setting("alldebrid.enabled"))

    def all_debrid_enabled(self):
        return self._all_debrid_enabled

    @cached_property
    def _torbox_enabled(self):
        return bool(self.get_setting("torbox.token") != "" and self.get_bool_setting("torbox.enabled"))

    def torbox_enabled(self):
        return self._torbox_enabled

    @cached_property
    def _debridlink_enabled(self):
        return bool(self.get_setting("debridlink.token") != "" and self.get_bool_setting("debridlink.enabled"))

    def debridlink_enabled(self):
        return self._debridlink_enabled

    @cached_property
    def _offcloud_enabled(self):
        return bool(self.get_setting("offcloud.apikey") != "" and self.get_bool_setting("offcloud.enabled"))

    def offcloud_enabled(self):
        return self._offcloud_enabled

    def container_refresh(self):
        return xbmc.executebuiltin("Container.Refresh")

    def trigger_widget_refresh(self, if_playing=True):
        """
        Trigger a widget refresh using the update library with an invalid path trick
        Widget refresh will not be attempted if playing if if_playing is False or if another process is waiting to
        refresh widgets.
        The widget refresh will not occur until the user returns to the home window to prevent updating other addon
        containers.

        Care must be taken when executing this method as it will block until the home window becomes available or
        playback is started or if the library is already being scanned
        :param if_playing: Whether to attempt to refresh widgets if playing.  Default: True
        :type if_playing: bool
        """
        player = xbmc.Player()
        if (
            self.get_bool_runtime_setting("widget_refreshing")
            or (player.isPlaying() and not if_playing)
            or xbmc.getCondVisibility(  # Don't wait if we are playing as it will refresh after
                "Library.IsScanningVideo"
            )  # Don't do library update if already scanning library
        ):
            del player
            return
        try:
            g.set_runtime_setting("widget_refreshing", True)
            while not self.abort_requested():
                if xbmcgui.getCurrentWindowId() == 10000:
                    if not (
                        self.wait_for_abort(0.2)
                        or xbmc.getCondVisibility(  # Short wait to see if anything else kicks off a widget refresh
                            "Container().isUpdating"
                        )  # Check if widgets currently refreshing
                    ):
                        self.log("TRIGGERING WIDGET REFRESH")
                        xbmc.executebuiltin('UpdateLibrary(video,widget_refresh,true)')
                    else:
                        self.log("Aborting widget refresh as container on home screen already refreshing", "debug")
                    break
                elif (
                    self.wait_for_abort(0.3) or player.isPlaying() or xbmc.getCondVisibility("Library.IsScanningVideo")
                ):
                    self.log("Aborting queued widget refresh as another process will trigger it", "debug")
                    break
        finally:
            del player
            g.clear_runtime_setting("widget_refreshing")

    def get_language_code(self, country=None):
        lang = self.json_rpc("Application.getProperties", {"properties": ["language"]}).get("language")
        if lang is None:
            g.log("Could not determine language", "warning")
            return ""
        if country:
            from resources.lib.third_party import pytz
            if lang == "en_GB" and g.get_setting("general.localtimezone") in pytz.country_timezones["US"]:
                lang = "en_US"  # Workaround for Americans that just can't comprehend that Kodi default is en_GB
            lang = lang.split("_")
            if len(lang) > 1 and len(lang[1]) == 2:
                lang = f"{lang[0].lower()}-{lang[1].upper()}"
                return lang
            else:
                g.log("Could not determine country part of language", "warning")
                return ""
        return lang.split("_")[0].lower()

    @cached_property
    def common_video_extensions(self):
        return tuple({ext for ext in xbmc.getSupportedMedia("video").split("|") if ext not in {"", ".zip", ".rar", ".url"}})

    def add_directory_item(self, name, **params):
        menu_item = params.pop("menu_item", {})
        if not isinstance(menu_item, dict):
            menu_item = {}

        item = xbmcgui.ListItem(label=name, offscreen=True)
        item.setContentLookup(False)

        info = menu_item.pop("info", {})
        item.addStreamInfo("video", {})

        if info is None or not isinstance(info, dict):
            info = {}

        self._apply_listitem_properties(item, info)
        if self.studio_limit:
            self.handle_studio_icon_skin_workaround(item, info)

        if "unwatched_episodes" in menu_item:
            item.setProperty("UnWatchedEpisodes", str(menu_item["unwatched_episodes"]))
        if "watched_episodes" in menu_item:
            item.setProperty("WatchedEpisodes", str(menu_item["watched_episodes"]))
        if (
            menu_item.get("episode_count", 0)
            and menu_item.get("watched_episodes", 0)
            and menu_item.get("episode_count", 0) == menu_item.get("watched_episodes", 0)
        ):
            info["playcount"] = 1
        if (
            menu_item.get("watched_episodes", 0) == 0
            and menu_item.get("episode_count", 0)
            and menu_item.get("episode_count", 0) > 0
        ):
            item.setProperty("WatchedEpisodes", str(0))
            item.setProperty("UnWatchedEpisodes", str(menu_item.get("episode_count", 0)))
        if "episode_count" in menu_item:
            item.setProperty("TotalEpisodes", str(menu_item["episode_count"]))
        if "season_count" in menu_item:
            item.setProperty("TotalSeasons", str(menu_item["season_count"]))
        if (
            "percent_played" in menu_item
            and menu_item.get("percent_played") is not None
            and float(menu_item.get("percent_played", 0)) > 0
        ):
            item.setProperty("percentplayed", str(menu_item["percent_played"]))
        if (
            "resume_time" in menu_item
            and menu_item.get("resume_time") is not None
            and int(menu_item.get("resume_time", 0)) > 0
        ):
            params["resume"] = str(menu_item["resume_time"])
            item.setProperty("resumetime", str(menu_item["resume_time"]))
        if "play_count" in menu_item and menu_item.get("play_count") is not None:
            info["playcount"] = menu_item["play_count"]
        if "air_date" in menu_item and menu_item.get("air_date") is not None:
            info["premiered"] = menu_item["air_date"]
            info["aired"] = menu_item["air_date"]
        if "description" in params:
            info["plot"] = info["overview"] = info["description"] = params.pop("description", None)
        if menu_item.get("user_rating"):
            item.setProperty("userrating", str(menu_item["user_rating"]))

        special_sort = params.pop("special_sort", None)
        if special_sort is not None:
            item.setProperty("SpecialSort", str(special_sort))
        label2 = params.pop("label2", None)
        if label2 is not None:
            item.setLabel2(label2)

        if params.pop("is_playable", False):
            item.setProperty("IsPlayable", "true")
            is_folder = params.pop("is_folder", False)
        else:
            item.setProperty("IsPlayable", "false")
            is_folder = params.pop("is_folder", True)

        cast = menu_item.get("cast", [])
        if cast is None or not isinstance(cast, (set, list)):
            cast = []
        item.setCast(cast)

        for key, value in info.items():
            if key.endswith("_id"):
                item.setProperty(key, str(value))

        media_type = info.get("mediatype", None)
        is_child_type = media_type in self._EPISODE_SEASON_TYPES
        item.setUniqueIDs(
            {
                unique_id_key: info[f"tvshow.{id_key}" if is_child_type else id_key]
                for id_key, unique_id_key in self._ID_KEYS.items()
                if info.get(f"tvshow.{id_key}" if is_child_type else id_key)
            }
        )

        for i in info:
            if i.startswith("rating."):
                item.setRating(i.split(".")[1], float(info[i].get("rating", 0.0)), int(info[i].get("votes", 0)), False)

        cm = params.pop("cm", [])
        if cm is None or not isinstance(cm, (set, list)):
            cm = []
        item.addContextMenuItems(cm)

        art = menu_item.pop("art", {})
        if art is None or not isinstance(art, dict):
            art = {}
        if (
            art.get("fanart", art.get("season.fanart", art.get("tvshow.fanart", None))) is None
        ) and not self.fanart_fallback_disabled:
            art["fanart"] = self.DEFAULT_FANART
        if art.get("poster", art.get("season.poster", art.get("tvshow.poster", None))) is None:
            art["poster"] = self.DEFAULT_POSTER
        if not art.get("icon"):
            art["icon"] = self.DEFAULT_ICON
        if not art.get("thumb"):
            art["thumb"] = ""
        with contextlib.suppress(Exception):
            item.setArt(art)

        # Clear out keys not relevant to Kodi info labels
        self.clean_info_keys(info)
        # Convert dates to localtime for display
        self.convert_info_dates(info)

        item.setInfo("video", info)

        bulk_add = params.pop("bulk_add", False)
        url = self.create_url(self.BASE_URL, params)
        if bulk_add:
            return url, item, is_folder
        else:
            xbmcplugin.addDirectoryItem(handle=self.PLUGIN_HANDLE, url=url, listitem=item, isFolder=is_folder)

    def add_menu_items(self, item_list):
        xbmcplugin.addDirectoryItems(self.PLUGIN_HANDLE, item_list, len(item_list))

    @staticmethod
    def clean_info_keys(info_dict):
        if not isinstance(info_dict, dict):
            return info_dict

        for key in info_dict.keys() - info_labels:
            info_dict.pop(key)

        return info_dict

    @cached_property
    def _local_is_utc(self):
        """True if local timezone is UTC — skip date conversions."""
        return self.LOCAL_TIMEZONE == self.UTC_TIMEZONE

    def convert_info_dates(self, info_dict):
        if not isinstance(info_dict, dict) or self._local_is_utc:
            return info_dict

        converted_dates = {key: self.utc_to_local(info_dict.get(key)) for key in info_dict.keys() & info_dates}
        info_dict.update(converted_dates)

        return info_dict

    def close_directory(self, content_type, sort=False, cache=False):
        if sort == "title":
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        if sort == "episode":
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        if not sort:
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.setContent(self.PLUGIN_HANDLE, content_type)
        menu_caching = self.menu_caching_enabled or cache
        xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, cacheToDisc=menu_caching)
        self.set_view_type(content_type)

    def set_view_type(self, content_type):
        def _execute_set_view_mode(view):
            xbmc.sleep(50)
            xbmc.executebuiltin(f"Container.SetViewMode({view})")

        if self.set_views_enabled and self.is_addon_visible():
            view_type = self.get_view_type(content_type)
            if view_type > 0:
                tools.run_threaded(_execute_set_view_mode, view_type)

    def is_addon_visible(self):
        return xbmc.getInfoLabel('Container.PluginName') == "plugin.video.seren"

    def cancel_directory(self):
        if g.FROM_WIDGET:
            g.add_directory_item(
                g.get_language_string(284, addon=False),
                menu_item=g.create_icon_dict("trakt_sync", base_path=g.ICONS_PATH),
            )
            xbmcplugin.setContent(self.PLUGIN_HANDLE, g.CONTENT_MENU)
            xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, succeeded=True, cacheToDisc=False)
        else:
            xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, succeeded=False, cacheToDisc=False)

    def read_all_text(self, file_path):
        try:
            f = xbmcvfs.File(file_path, "r")
            return f.read()
        except OSError:
            return None
        finally:
            with contextlib.suppress(Exception):
                f.close()

    def write_all_text(self, file_path, content):
        try:
            f = xbmcvfs.File(file_path, "w")
            return f.write(content)
        except OSError:
            return None
        finally:
            with contextlib.suppress(Exception):
                f.close()

    def notification(self, heading, message, time=5000, sound=True):
        if self.disable_notification_sound:
            sound = False
        dialogue = xbmcgui.Dialog()
        dialogue.notification(heading, message, time=time, sound=sound)
        del dialogue

    def get_keyboard_input(self, heading=None, default=None, hidden=False):
        k = xbmc.Keyboard(default, heading, hidden)
        k.doModal()
        input_value = k.getText() if k.isConfirmed() else None
        del k
        return input_value

    def json_rpc(self, method, params=None):
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": params or {},
        }
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request_data)))
        if "error" in response:
            self.log(f"JsonRPC Error {response['error']['code']}: {response['error']['message']}", "debug")
        return response.get("result", {})

    def get_kodi_subtitle_languages(self, iso_format=False):
        subtitle_language = self.json_rpc("Settings.GetSettingValue", {"setting": "subtitles.languages"})
        if iso_format:
            return [self.convert_language_iso(x) for x in subtitle_language["value"]]
        else:
            return list(subtitle_language["value"])

    def get_kodi_preferred_subtitle_language(self, iso_format=False):
        subtitle_language = self.json_rpc("Settings.GetSettingValue", {"setting": "locale.subtitlelanguage"})
        if subtitle_language["value"] in ["forced_only", "original", "default", "none"]:
            return subtitle_language["value"]
        if iso_format:
            return self.convert_language_iso(subtitle_language["value"])
        else:
            return subtitle_language["value"]

    def convert_language_iso(self, from_value):
        return xbmc.convertLanguage(from_value, xbmc.ISO_639_1)

    @staticmethod
    def _apply_listitem_properties(item, info):
        for prop in listitem_properties:
            value = info
            for subkey in prop[0]:
                value = value.get(subkey, {})

            if value:
                item.setProperty(prop[1], str(value))

    @cached_property
    def menu_caching_enabled(self):
        return g.get_bool_setting("general.menucaching")

    @cached_property
    def set_views_enabled(self):
        return g.get_bool_setting("general.setViews")

    @cached_property
    def disable_notification_sound(self):
        return g.get_bool_setting("general.disableNotificationSound")

    @cached_property
    def fanart_fallback_disabled(self):
        return g.get_bool_setting("general.fanart.fallback", False)

    @cached_property
    def studio_limit(self):
        return g.get_bool_setting("general.meta.studiolimit", True)

    def handle_studio_icon_skin_workaround(self, item, info):
        media_type = info.get("mediatype")
        studios = info.get("studio", [])
        property_name = "studio" if media_type == g.MEDIA_MOVIE else "network"

        if isinstance(studios, list) and len(studios) >= 1:
            for studio in reversed(studios):
                if (lower_studio := studio.lower()) in self.studio_icons or (
                    lower_studio.endswith(" ltd.") and (lower_studio := lower_studio[:-5]) in self.studio_icons
                ):
                    item.setProperty(property_name, lower_studio)
                    info['studio'] = studio
                    return

            item.setProperty(property_name, studios[0].lower())
            info['studio'] = studios[0]
        elif studios and isinstance(studios, str):
            item.setProperty(property_name, studios.lower())
            info['studio'] = studios

    _STUDIO_ICONS_KEY = "seren.studio_icons"

    @cached_property
    def studio_icons(self):
        # Try loading from window property (pre-warmed in service.py)
        try:
            window = xbmcgui.Window(10000)
            cached = window.getProperty(self._STUDIO_ICONS_KEY)
            if cached:
                return set(json.loads(cached))
        except Exception:
            pass

        # Fallback: scan filesystem (two listdir calls)
        colored = {i[:-4] for i in xbmcvfs.listdir("resource://resource.images.studios.coloured")[1]}
        white = {i[:-4] for i in xbmcvfs.listdir("resource://resource.images.studios.white")[1]}
        icons = colored | white if (colored and white) else colored or white

        # Store for future plugin calls
        try:
            window = xbmcgui.Window(10000)
            window.setProperty(self._STUDIO_ICONS_KEY, json.dumps(list(icons)))
        except Exception:
            pass

        return icons

    def create_url(self, base_url, params):
        if params is None:
            return base_url
        if "action_args" in params and isinstance(params["action_args"], dict):
            params["action_args"] = json.dumps(params["action_args"], sort_keys=True)
        return f"{base_url}/?{parse.urlencode(sorted(params.items()))}"

    # Singleton monitor — avoids creating/destroying xbmc.Monitor() on every call.
    # During scraping keep-alive loops, abort_requested() and wait_for_abort() are
    # called hundreds of times.
    _MONITOR = None

    @classmethod
    def _get_monitor(cls):
        if cls._MONITOR is None:
            cls._MONITOR = xbmc.Monitor()
        return cls._MONITOR

    @classmethod
    def abort_requested(cls):
        return cls._get_monitor().abortRequested()

    @classmethod
    def wait_for_abort(cls, timeout=1.0):
        return cls._get_monitor().waitForAbort(timeout)

    @staticmethod
    def reload_profile():
        xbmc.executebuiltin(f"LoadProfile({xbmc.getInfoLabel('system.profilename')})")

    @staticmethod
    def validate_date(date_string):
        """Validates the date string and returns in standard date time format, if it is invalid it just returns none.

        :param date_string:string value with a supposed date.
        :type date_string:str
        :return:formatted datetime or none
        :rtype:str
        """
        if not date_string:
            return date_string

        try:
            result = tools.parse_datetime(date_string, False)
        except ValueError:
            return None

        if result and result.year > 1900:
            return str(g.datetime_to_string(result))
        return None

    @staticmethod
    def datetime_to_string(date_time_or_date):
        """
        Converts a datetime or date object to a string in ISO format truncated to seconds and without TZ offset
        If this is a date, then the isoformat for a date without time is returned
        :param date_time_or_date: A datetime.datetime or a datetime.date object
        :return: Datetime or date string in ISO format truncated to seconds and without TZ offset.
                 Empty string if invalid object provided
        :rtype str
        """
        try:
            if hasattr(date_time_or_date, "second"):
                return date_time_or_date.isoformat(timespec="seconds").split("+", 1)[0]
            return date_time_or_date.isoformat()
        except (ValueError, AttributeError):
            return ""

    def utc_to_local(self, utc_string):
        """
        Converts a UTC style datetime string to the local timezone
        :param utc_string: UTC datetime string
        :return: localized datetime string
        """
        if not utc_string:
            return None

        utc = tools.parse_datetime(utc_string, False)
        utc = self.UTC_TIMEZONE.localize(utc)
        local_time = utc.astimezone(self.LOCAL_TIMEZONE)
        return g.datetime_to_string(local_time)

    def local_to_utc_by_country(self, datetime_string, country_code):
        """
        Converts a local datetime string to the utc timezone based on a provided country code
        Note that some countries have moe than one timezone, we choose the first as there is no perfect solution
        :param datetime_string: Local date time string
        :type datetime_string: str
        :param country_code: The ISO-3166 2 char country code
        :return: UTC datetime string
        """
        if not datetime_string:
            return None

        try:
            from resources.lib.third_party import pytz
            local_time = tools.parse_datetime(datetime_string, False)
            tz = pytz.timezone(pytz.country_timezones[country_code][0])  # First timezone for a country
            local_time = tz.localize(local_time)
            utc_time = local_time.astimezone(self.UTC_TIMEZONE)
            return g.datetime_to_string(utc_time)
        except (KeyError, IndexError, Exception) as e:
            g.log(
                f"Unable to covert local time to utc based on country_code='{country_code}', "
                f"datetime_string='{datetime_string}'/n{e}",
                "error",
            )
            return None

    def open_addon_settings(self, section_offset, setting_offset=None):
        """
        Open seren settings at a particular section and setting
        :param section_offset: Section number starting at 0
        :type section_offset: int
        :param setting_offset: Setting number within section, starting at 0.  Note that sep / lsep are counted.
        :type setting_offset: None|int
        :return:
        """
        xbmc.executebuiltin(f"Addon.OpenSettings({self.ADDON_ID})")
        xbmc.executebuiltin(f"SetFocus({-(100 - section_offset)})")
        if setting_offset is not None:
            xbmc.executebuiltin(f"SetFocus({-(80 - setting_offset)})")

    def create_icon_dict(self, icon_slug, base_path, art_types=None):
        keys = art_types or ['icon', 'poster', 'thumb', 'fanart']
        return {"art": dict.fromkeys(keys, f"{base_path}{icon_slug}.png")}


g = GlobalVariables()
