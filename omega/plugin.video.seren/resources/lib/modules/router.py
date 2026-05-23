import xbmc
import xbmcgui

from resources.lib.modules.exceptions import NoPlayableSourcesException
from resources.lib.modules.globals import g

"""
    Dispatch module — two-level dispatch: O(1) dict lookup for simple routes,
    elif fallback for complex routes (getSources, preScrape, etc.)
"""


# ---------------------------------------------------------------------------
# Route table helpers
# ---------------------------------------------------------------------------

def _menu(module_path, method_name, arg_key=None):
    """Create a handler for: from module import Menus; Menus().method(arg?)"""
    def handler(ctx):
        mod = __import__(module_path, fromlist=["Menus"])
        method = getattr(mod.Menus(), method_name)
        method(ctx[arg_key]) if arg_key else method()
    return handler


def _call(module_path, class_name, method_name, arg_key=None):
    """Create a handler for: from module import Class; Class().method(arg?)"""
    def handler(ctx):
        mod = __import__(module_path, fromlist=[class_name])
        method = getattr(getattr(mod, class_name)(), method_name)
        method(ctx[arg_key]) if arg_key else method()
    return handler


def _func(module_path, func_name, arg_key=None):
    """Create a handler for: from module import func; func(arg?)"""
    def handler(ctx):
        mod = __import__(module_path, fromlist=[func_name])
        func = getattr(mod, func_name)
        func(ctx[arg_key]) if arg_key else func()
    return handler


# ---------------------------------------------------------------------------
# Route table — O(1) lookup for simple routes (~95 routes)
# ---------------------------------------------------------------------------

_ROUTE_TABLE = {
    # --- Movie menus ---
    "moviesHome":           _menu("resources.lib.gui.movieMenus", "discover_movies"),
    "moviesUpdated":        _menu("resources.lib.gui.movieMenus", "movies_updated"),
    "moviesRecommended":    _menu("resources.lib.gui.movieMenus", "movies_recommended"),
    "moviesSearch":         _menu("resources.lib.gui.movieMenus", "movies_search", "action_args"),
    "moviesSearchResults":  _menu("resources.lib.gui.movieMenus", "movies_search_results", "action_args"),
    "moviesSearchHistory":  _menu("resources.lib.gui.movieMenus", "movies_search_history"),
    "myMovies":             _menu("resources.lib.gui.movieMenus", "my_movies"),
    "moviesMyCollection":   _menu("resources.lib.gui.movieMenus", "my_movie_collection"),
    "moviesMyWatchlist":    _menu("resources.lib.gui.movieMenus", "my_movie_watchlist"),
    "moviesRelated":        _menu("resources.lib.gui.movieMenus", "movies_related", "action_args"),
    "movieGenres":          _menu("resources.lib.gui.movieMenus", "movies_genres"),
    "movieGenresGet":       _menu("resources.lib.gui.movieMenus", "movies_genre_list", "action_args"),
    "movieYears":           _menu("resources.lib.gui.movieMenus", "movies_years"),
    "movieYearsMovies":     _menu("resources.lib.gui.movieMenus", "movie_years_results", "action_args"),
    "movieByActor":         _menu("resources.lib.gui.movieMenus", "movies_by_actor", "action_args"),
    "myWatchedMovies":      _menu("resources.lib.gui.movieMenus", "my_watched_movies"),
    "onDeckMovies":         _menu("resources.lib.gui.movieMenus", "on_deck_movies"),
    "moviePopularRecent":   _menu("resources.lib.gui.movieMenus", "movie_popular_recent"),
    "movieTrendingRecent":  _menu("resources.lib.gui.movieMenus", "movie_trending_recent"),

    # --- Show menus ---
    "showsHome":            _menu("resources.lib.gui.tvshowMenus", "discover_shows"),
    "myShows":              _menu("resources.lib.gui.tvshowMenus", "my_shows"),
    "showsMyCollection":    _menu("resources.lib.gui.tvshowMenus", "my_shows_collection"),
    "showsMyWatchlist":     _menu("resources.lib.gui.tvshowMenus", "my_shows_watchlist"),
    "showsMyProgress":      _menu("resources.lib.gui.tvshowMenus", "my_show_progress"),
    "showsMyRecentEpisodes": _menu("resources.lib.gui.tvshowMenus", "my_recent_episodes"),
    "showsRecommended":     _menu("resources.lib.gui.tvshowMenus", "shows_recommended"),
    "showsUpdated":         _menu("resources.lib.gui.tvshowMenus", "shows_updated"),
    "showsSearch":          _menu("resources.lib.gui.tvshowMenus", "shows_search", "action_args"),
    "showsSearchResults":   _menu("resources.lib.gui.tvshowMenus", "shows_search_results", "action_args"),
    "showsSearchHistory":   _menu("resources.lib.gui.tvshowMenus", "shows_search_history"),
    "showSeasons":          _menu("resources.lib.gui.tvshowMenus", "show_seasons", "action_args"),
    "seasonEpisodes":       _menu("resources.lib.gui.tvshowMenus", "season_episodes", "action_args"),
    "showsRelated":         _menu("resources.lib.gui.tvshowMenus", "shows_related", "action_args"),
    "showYears":            _menu("resources.lib.gui.tvshowMenus", "shows_years", "action_args"),
    "showsNextUp":          _menu("resources.lib.gui.tvshowMenus", "my_next_up"),
    "showsNew":             _menu("resources.lib.gui.tvshowMenus", "shows_new"),
    "showsNetworks":        _menu("resources.lib.gui.tvshowMenus", "shows_networks"),
    "showsNetworkShows":    _menu("resources.lib.gui.tvshowMenus", "shows_networks_results", "action_args"),
    "onDeckShows":          _menu("resources.lib.gui.tvshowMenus", "on_deck_shows"),
    "tvGenres":             _menu("resources.lib.gui.tvshowMenus", "shows_genres"),
    "showGenresGet":        _menu("resources.lib.gui.tvshowMenus", "shows_genre_list", "action_args"),
    "flatEpisodes":         _menu("resources.lib.gui.tvshowMenus", "flat_episode_list", "action_args"),
    "myUpcomingEpisodes":   _menu("resources.lib.gui.tvshowMenus", "my_upcoming_episodes"),
    "myWatchedEpisodes":    _menu("resources.lib.gui.tvshowMenus", "my_watched_episode"),
    "showsByActor":         _menu("resources.lib.gui.tvshowMenus", "shows_by_actor", "action_args"),
    "showsPopularRecent":   _menu("resources.lib.gui.tvshowMenus", "shows_popular_recent"),
    "showsTrendingRecent":  _menu("resources.lib.gui.tvshowMenus", "shows_trending_recent"),
    "showsRecentlyWatched": _menu("resources.lib.gui.tvshowMenus", "shows_recently_watched"),

    # --- Home / Search / Tools ---
    "searchMenu":           _menu("resources.lib.gui.homeMenu", "search_menu"),
    "toolsMenu":            _menu("resources.lib.gui.homeMenu", "tools_menu"),
    "providerTools":        _menu("resources.lib.gui.homeMenu", "provider_menu"),
    "traktSyncTools":       _menu("resources.lib.gui.homeMenu", "trakt_sync_tools"),
    "testWindows":          _menu("resources.lib.gui.homeMenu", "test_windows"),

    # --- Debrid services menus ---
    "debridServices":       _menu("resources.lib.gui.debridServices", "home"),
    "cacheAssistStatus":    _menu("resources.lib.gui.debridServices", "get_assist_torrents"),
    "premiumize_transfers": _menu("resources.lib.gui.debridServices", "list_premiumize_transfers"),
    "realdebridTransfers":  _menu("resources.lib.gui.debridServices", "list_rd_transfers"),
    "alldebridTransfers":   _menu("resources.lib.gui.debridServices", "list_ad_transfers"),
    "torboxTransfers":      _menu("resources.lib.gui.debridServices", "list_tb_transfers"),
    "debridlinkTransfers":  _menu("resources.lib.gui.debridServices", "list_dl_transfers"),
    "nonActiveAssistClear": _menu("resources.lib.gui.debridServices", "assist_non_active_clear"),
    "clearAllDebridTransfers": _menu("resources.lib.gui.debridServices", "clear_all_transfers"),
    "clearAllDebridCloudFiles": _menu("resources.lib.gui.debridServices", "clear_all_cloud_files"),

    # --- My Files ---
    "myFiles":              _menu("resources.lib.gui.myFiles", "home"),
    "myFilesFolder":        _menu("resources.lib.gui.myFiles", "my_files_folder", "action_args"),
    "myFilesPlay":          _menu("resources.lib.gui.myFiles", "my_files_play", "action_args"),

    # --- Lists ---
    "myTraktLists":         _call("resources.lib.modules.listsHelper", "ListsHelper", "my_trakt_lists", "mediatype"),
    "myLikedLists":         _call("resources.lib.modules.listsHelper", "ListsHelper", "my_liked_lists", "mediatype"),
    "TrendingLists":        _call("resources.lib.modules.listsHelper", "ListsHelper", "trending_lists", "mediatype"),
    "PopularLists":         _call("resources.lib.modules.listsHelper", "ListsHelper", "popular_lists", "mediatype"),
    "traktList":            _call("resources.lib.modules.listsHelper", "ListsHelper", "get_list_items"),

    # --- Trakt sync ---
    "syncTraktActivities":  _call("resources.lib.database.trakt_sync.activities", "TraktSyncDatabase", "sync_activities"),
    "flushTraktActivities": _call("resources.lib.database.trakt_sync", "TraktSyncDatabase", "flush_activities"),
    "rebuildTraktDatabase": _call("resources.lib.database.trakt_sync", "TraktSyncDatabase", "re_build_database"),
    "cleanOrphanedMetadata": _call("resources.lib.database.trakt_sync", "TraktSyncDatabase", "clean_orphaned_metadata"),

    # --- Cache management ---
    "clearTorrentCache":    _call("resources.lib.database.torrentCache", "TorrentCache", "clear_all"),
    "torrentCacheCleanup":  _call("resources.lib.database.torrentCache", "TorrentCache", "do_cleanup"),

    # --- Undesirables ---
    "undesirablesSelectDefaults": _func("resources.lib.database.undesirables", "undesirables_select_defaults"),
    "undesirablesUserInput":      _func("resources.lib.database.undesirables", "undesirables_user_input"),
    "undesirablesUserRemove":     _func("resources.lib.database.undesirables", "undesirables_user_remove"),
    "undesirablesUserRemoveAll":  _func("resources.lib.database.undesirables", "undesirables_user_remove_all"),
    "undesirablesReset":          _func("resources.lib.database.undesirables", "undesirables_reset_defaults"),
    # --- Title Substitutions ---
    "titleSubsAdd":              _func("resources.lib.database.titleSubs", "title_subs_add"),
    "titleSubsViewRemove":       _func("resources.lib.database.titleSubs", "title_subs_view_remove"),
    "titleSubsClearAll":         _func("resources.lib.database.titleSubs", "title_subs_clear_all"),
    # --- Anime Skip ---
    "showSkipIntro":             _func("resources.lib.modules.player", "show_skip_intro_dialog"),

    # --- Providers ---
    "installProviders":     _call("resources.lib.modules.providers.install_manager", "ProviderInstallManager", "install_package", "action_args"),
    "uninstallProviders":   _call("resources.lib.modules.providers.install_manager", "ProviderInstallManager", "uninstall_package"),
    "manualProviderUpdate": _call("resources.lib.modules.providers.install_manager", "ProviderInstallManager", "manual_update"),

    # --- Skins ---
    "installSkin":          _call("resources.lib.database.skinManager", "SkinManager", "install_skin"),
    "uninstallSkin":        _call("resources.lib.database.skinManager", "SkinManager", "uninstall_skin"),
    "switchSkin":           _call("resources.lib.database.skinManager", "SkinManager", "switch_skin"),
    "checkSkinUpdates":     _call("resources.lib.database.skinManager", "SkinManager", "check_for_updates"),

    # --- Maintenance / service ---
    "runMaintenance":       _func("resources.lib.common.maintenance", "run_maintenance"),
    "cleanInstall":         _func("resources.lib.common.maintenance", "wipe_install"),
    "premiumizeCleanup":    _func("resources.lib.common.maintenance", "premiumize_transfer_cleanup"),
    "toggleLanguageInvoker": _func("resources.lib.common.maintenance", "toggle_reuselanguageinvoker"),
    "longLifeServiceManager": _call("resources.lib.modules.providers.service_manager", "ProvidersServiceManager", "run_long_life_manager"),

    # --- Backup / Restore ---
    "backupSettings":       _func("resources.lib.modules.backup_restore", "backup_settings"),
    "restoreSettings":      _func("resources.lib.modules.backup_restore", "restore_settings"),

    # --- Playback helpers ---
    "cacheAssist":          _call("resources.lib.modules.cacheAssist", "CacheAssistHelper", "auto_cache", "action_args"),

    # --- Timezone ---
    "chooseTimeZone":       _func("resources.lib.modules.manual_timezone", "choose_timezone"),

    # --- Test windows ---
    "testPlayingNext":      _func("resources.lib.gui.mock_windows", "mock_playing_next"),
    "testStillWatching":    _func("resources.lib.gui.mock_windows", "mock_still_watching"),
    "testGetSourcesWindow": _func("resources.lib.gui.mock_windows", "mock_get_sources"),
    "testResolverWindow":   _func("resources.lib.gui.mock_windows", "mock_resolver"),
    "testSourceSelectWindow": _func("resources.lib.gui.mock_windows", "mock_source_select"),
    "testManualCacheWindow": _func("resources.lib.gui.mock_windows", "mock_cache_assist"),
    "testDownloadManagerWindow": _func("resources.lib.gui.mock_windows", "mock_download_manager"),
}


# ---------------------------------------------------------------------------
# Main dispatch function
# ---------------------------------------------------------------------------

def dispatch(params):
    url = params.get("url")
    action = params.get("action")
    action_args = params.get("action_args")
    pack_select = params.get("packSelect")
    source_select = params.get("source_select") == "true"
    overwrite_cache = params.get("seren_reload") == "true"
    resume = params.get("resume")
    force_resume_check = params.get("forceresumecheck") == "true"
    force_resume_off = params.get("forceresumeoff") == "true"
    force_resume_on = params.get("forceresumeon") == "true"
    smart_url_arg = params.get("smartPlay") == "true"
    mediatype = params.get("mediatype")
    endpoint = params.get("endpoint")

    # TMDb Helper alias passthrough: decode CJK aliases from player URL into action_args
    # so _build_simple_show_info() / _build_simple_movie_info() can use them
    tmdbhelper_aliases_raw = params.get("tmdbhelper_aliases")
    if tmdbhelper_aliases_raw and isinstance(action_args, dict):
        try:
            import json
            from urllib.parse import unquote
            decoded = json.loads(unquote(tmdbhelper_aliases_raw))
            if isinstance(decoded, list) and decoded:
                action_args['tmdbhelper_aliases'] = decoded
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    g.log(f"Seren, Running Path - {g.REQUEST_PARAMS}")

    # Home menu (no action)
    if action is None:
        from resources.lib.gui import homeMenu
        homeMenu.Menus().home()
        return

    # O(1) dict dispatch for simple routes (~95 of ~120 total)
    handler = _ROUTE_TABLE.get(action)
    if handler is not None:
        handler({
            "action_args": action_args,
            "mediatype": mediatype,
            "endpoint": endpoint,
        })
        return

    # Complex routes that need multiple local variables (elif fallback)
    if action == "genericEndpoint":
        if mediatype == "movies":
            from resources.lib.gui.movieMenus import Menus
        else:
            from resources.lib.gui.tvshowMenus import Menus
        Menus().generic_endpoint(endpoint)

    elif action == "forceResumeShow":
        from resources.lib.modules import smartPlay
        from resources.lib.common import tools

        smartPlay.SmartPlay(tools.get_item_information(action_args)).resume_show()

    elif action == "moviesHome":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().discover_movies()

    elif action == "moviesUpdated":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_updated()

    elif action == "moviesRecommended":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_recommended()

    elif action == "moviesSearch":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_search(action_args)

    elif action == "moviesSearchResults":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_search_results(action_args)

    elif action == "moviesSearchHistory":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_search_history()

    elif action == "myMovies":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_movies()

    elif action == "moviesMyCollection":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_movie_collection()

    elif action == "moviesMyWatchlist":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_movie_watchlist()

    elif action == "moviesRelated":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_related(action_args)

    elif action == "colorPicker":
        g.color_picker()

    elif action == "authTrakt":
        from resources.lib.indexers import trakt

        trakt.TraktAPI().auth()
        g.open_addon_settings(3, 6)

    elif action == "revokeTrakt":
        from resources.lib.indexers import trakt

        trakt.TraktAPI().revoke_auth()
        g.open_addon_settings(3, 5)

    elif action == "getSources":
        from resources.lib.modules.smartPlay import SmartPlay
        from resources.lib.common import tools
        from resources.lib.modules import helpers
        from resources.lib.database.providerCache import ProviderCache

        item_information = tools.get_item_information(action_args)
        if not item_information:
            g.log("getSources: Unable to identify item (missing or unresolvable Trakt ID)", "warning")
            g.cancel_playback()
            return
        smart_play = SmartPlay(item_information)
        background = None
        resolver_window = None

        try:
            # Check to confirm user has a debrid provider authenticated and enabled
            if not g.premium_check() and ProviderCache().debrid_providers_enabed():
                xbmcgui.Dialog().ok(
                    g.ADDON_NAME,
                    tools.create_multiline_message(
                        line1=g.get_language_string(30186),
                        line2=g.get_language_string(30187),
                    ),
                )
                return None

            # workaround for widgets not generating a playlist on playback request
            play_list = smart_play.playlist_present_check(smart_url_arg)

            if play_list:
                g.log("Cancelling non playlist playback", "warning")
                xbmc.Player().play(g.PLAYLIST)
                return

            resume_time = smart_play.handle_resume_prompt(resume, force_resume_off, force_resume_on, force_resume_check)
            background = helpers.show_persistent_window_if_required(item_information)
            # Clear out last resolved title for a show if we are doing a rescrape
            if overwrite_cache and item_information['info']['mediatype'] == g.MEDIA_EPISODE:
                g.clear_runtime_setting(f"last_resolved_release_title.{item_information['info']['trakt_show_id']}")

            # Get Sources
            sources_helper = helpers.SourcesHelper()
            uncached, sources_list, ii = sources_helper.get_sources(action_args, overwrite_cache=overwrite_cache)
            if background:
                background.set_process_started()
                background.set_text("")

            # Sort sources
            sources = sources_helper.sort_sources(ii, sources_list)
            if sources is None:
                return

            # Select and resolve source
            if item_information['info']['mediatype'] == g.MEDIA_EPISODE:
                source_select_style = "Episodes"
            else:
                source_select_style = "Movie"

            watchdog_used = False
            used_source_select = g.get_int_setting(f"general.playstyle{source_select_style}") == 1 or source_select
            if used_source_select:

                if background:
                    background.set_text(g.get_language_string(30178))
                from resources.lib.modules import sourceSelect

                xbmc.sleep(750)
                if background:
                    background.set_text("")
                stream_link = sourceSelect.source_select(uncached, sources, ii)
            else:
                # Clear any previous rescrape flag before resolving
                g.clear_runtime_setting("content_verify_rescrape")
                g.clear_runtime_setting("cloud_miss_rescrape")

                watchdog_enabled = g.get_bool_setting("playback.watchdog", False)
                watchdog_used = False

                if watchdog_enabled:
                    # Watchdog path: resolve + play + stall monitor in one loop
                    # Uses xbmc.Player().play() directly for retry capability
                    #
                    # Release the plugin handle BEFORE watchdog starts — the
                    # watchdog plays via Player.play() which is independent of
                    # the plugin resolution system. Without this, setResolvedUrl
                    # at commit time routes back through TMDb Helper and kills
                    # the working stream.
                    g.cancel_playback()

                    # Close Seren overlay windows (persistent_background,
                    # get_sources) so video is visible during monitoring
                    if background:
                        try:
                            background.close()
                        except Exception:
                            pass
                    g.close_busy_dialog()
                    g.close_all_dialogs()

                    from resources.lib.modules.playback_watchdog import PlaybackWatchdog
                    watchdog = PlaybackWatchdog()
                    stream_link = watchdog.attempt_playback(sources, ii, pack_select, resume_time=resume_time)
                    # attempt_playback returns (stream_link, release_title) tuple
                    _release_title = None
                    if isinstance(stream_link, tuple):
                        stream_link, _release_title = stream_link
                    watchdog_used = bool(stream_link)
                    # Set last resolved title for episode release group continuity
                    if watchdog_used and _release_title and ii['info']['mediatype'] == g.MEDIA_EPISODE:
                        g.set_runtime_setting(
                            f"last_resolved_release_title.{ii['info']['trakt_show_id']}",
                            _release_title,
                        )
                else:
                    stream_link = helpers.Resolverhelper().resolve_silent_or_visible(
                        sources, ii, pack_select, overwrite_cache=overwrite_cache
                    )

                # Cloud miss rescrape: if too many sources were no longer cached
                # on debrid, clear the cache and rescrape with fresh results
                rescrape_reason = None
                if (
                    stream_link is None
                    and g.get_runtime_setting("cloud_miss_rescrape") == "true"
                    and not g.get_runtime_setting("cloud_miss_rescrape_done")
                ):
                    rescrape_reason = "cloud_miss"
                    g.clear_runtime_setting("cloud_miss_rescrape")
                    g.set_runtime_setting("cloud_miss_rescrape_done", "true")
                    g.log(
                        "Cloud miss: Sources no longer cached on debrid — rescraping",
                        "warning",
                    )

                # Content verification rescrape: if too many mismatches were detected,
                # clear the cache and rescrape once with fresh results
                elif (
                    stream_link is None
                    and g.get_runtime_setting("content_verify_rescrape") == "true"
                    and not g.get_runtime_setting("content_verify_rescrape_done")
                ):
                    rescrape_reason = "content_verify"
                    g.clear_runtime_setting("content_verify_rescrape")
                    g.set_runtime_setting("content_verify_rescrape_done", "true")
                    g.log(
                        "Content verification: Rescraping after consecutive mismatches",
                        "warning",
                    )

                if rescrape_reason:
                    if background:
                        background.set_text(g.get_language_string(30714))

                    # Rescrape with cache overwrite
                    uncached2, sources_list2, ii2 = sources_helper.get_sources(
                        action_args, overwrite_cache=True
                    )
                    if background:
                        background.set_process_started()
                        background.set_text("")
                    sources2 = sources_helper.sort_sources(ii2, sources_list2)
                    if sources2:
                        if watchdog_enabled:
                            from resources.lib.modules.playback_watchdog import PlaybackWatchdog
                            watchdog = PlaybackWatchdog()
                            stream_link = watchdog.attempt_playback(sources2, ii2, pack_select, resume_time=resume_time)
                            _release_title = None
                            if isinstance(stream_link, tuple):
                                stream_link, _release_title = stream_link
                            watchdog_used = bool(stream_link)
                            if watchdog_used and _release_title and ii2['info']['mediatype'] == g.MEDIA_EPISODE:
                                g.set_runtime_setting(
                                    f"last_resolved_release_title.{ii2['info']['trakt_show_id']}",
                                    _release_title,
                                )
                        else:
                            stream_link = helpers.Resolverhelper().resolve_silent_or_visible(
                                sources2, ii2, pack_select, overwrite_cache=True
                            )

                # Clean up rescrape flags
                g.clear_runtime_setting("content_verify_rescrape")
                g.clear_runtime_setting("content_verify_rescrape_done")
                g.clear_runtime_setting("cloud_miss_rescrape")
                g.clear_runtime_setting("cloud_miss_rescrape_done")

                # Uncached torrent fallback: if all cached sources failed and
                # uncached sources exist, offer to cache-and-wait for the best one
                if stream_link is None and uncached:
                    from resources.lib.modules.cacheAssist import CacheAssistHelper

                    if xbmcgui.Dialog().yesno(
                        g.ADDON_NAME,
                        g.get_language_string(30748),
                    ):
                        try:
                            cache_helper = CacheAssistHelper()
                            cache_module = cache_helper.manual_cache(uncached[0])
                            if cache_module:
                                cache_result = cache_module.do_cache()
                                if cache_result and cache_result['result'] == 'success':
                                    cached_source = cache_result['source']
                                    stream_link = helpers.Resolverhelper().resolve_silent_or_visible(
                                        [cached_source], ii, pack_select, overwrite_cache=True
                                    )
                                    watchdog_used = False  # cache-assist uses normal path
                        except Exception as e:
                            g.log(f"Uncached torrent fallback failed: {e}", "error")
                            g.log_stacktrace()

                if stream_link is None:
                    g.close_busy_dialog()
                    g.close_all_dialogs()
                    g.notification(g.ADDON_NAME, g.get_language_string(30032), time=5000)

            # Clean up any remaining AD MagnetUpload IDs not consumed by the resolver.
            # Fires at both source select close and autoplay resolution, covering:
            #   - user cancels source select (no resolver call → IDs never cleaned)
            #   - user picks non-AD source (AD resolver never fires → IDs never cleaned)
            #   - autoplay resolves non-AD source (same)
            #   - all sources failed (IDs still set)
            # Safe when AD resolver DID succeed: _cleanup_other_upload_cached() already
            # cleared alldebrid.upload_cache_ids, so this finds nothing and exits early.
            try:
                _ad_ids = g.get_runtime_setting("alldebrid.upload_cache_ids")
                if _ad_ids and isinstance(_ad_ids, list):
                    from resources.lib.debrid.all_debrid import AllDebrid
                    AllDebrid().delete_magnets_background(_ad_ids)
                    g.clear_runtime_setting("alldebrid.upload_cache_ids")
                    g.log(
                        f"AD MagnetUpload: cleanup at source select/autoplay — "
                        f"{len(_ad_ids)} upload ID(s) released",
                        "info",
                    )
            except Exception:
                pass

            # Clean up any DL SeedboxProbe IDs not consumed by the DL resolver.
            # Fires at source select close and autoplay resolution, covering:
            #   - user cancels source select (no resolver call → IDs never cleaned)
            #   - user picks non-DL source (DL resolver never fires → IDs never cleaned)
            #   - all sources failed (IDs still set)
            # Safe when DL resolver DID play: _do_post_processing() already cleared
            # debridlink.probe_ids (deleting the unplayed cached probes and removing
            # the played ID from the runtime setting), so this finds nothing and exits
            # early — mirroring the AD MagnetUpload pattern.
            try:
                _dl_ids = g.get_runtime_setting("debridlink.probe_ids")
                if _dl_ids and isinstance(_dl_ids, list):
                    from resources.lib.debrid.debrid_link import DebridLink
                    DebridLink().delete_torrents_background(_dl_ids)
                    g.clear_runtime_setting("debridlink.probe_ids")
                    g.log(
                        f"DL SeedboxProbe: cleanup at source select/autoplay — "
                        f"{len(_dl_ids)} probe ID(s) released",
                        "info",
                    )
            except Exception:
                pass

            if not stream_link:
                raise NoPlayableSourcesException

            try:
                from resources.lib.modules import player as _player_module
                seren_player = _player_module.SerenPlayer()
                if watchdog_used:
                    # Stream is already playing via watchdog — attach lifecycle
                    seren_player.attach_to_playing(stream_link, ii, resume_time=resume_time)
                elif used_source_select:
                    # In-process source select loop — no PLAYLIST, no new plugin invocation.
                    # First play consumes setResolvedUrl (one-shot per handle); re-opens use
                    # Player.play() + attach_to_playing() which bypasses setResolvedUrl.
                    from resources.lib.gui.windows.source_select import SourceSelect
                    from resources.lib.database.skinManager import SkinManager as _SM
                    current_link = stream_link
                    first_play = True
                    while not g.abort_requested():
                        if first_play:
                            seren_player.play_source(current_link, ii, resume_time=resume_time)
                            first_play = False
                        else:
                            seren_player.playing_file = current_link
                            seren_player.item_information = ii
                            listitem = seren_player._create_list_item(current_link)
                            xbmc.Player().play(current_link, listitem=listitem)
                            g.wait_for_abort(0.5)
                            seren_player.attach_to_playing(current_link, ii, resume_time=None)

                        if seren_player.playback_ended or g.abort_requested():
                            break
                        if xbmc.Player().isPlaying():
                            break

                        needs_grace = seren_player.playback_error or (
                            not seren_player.playback_started and not seren_player.stop_event_received
                        )
                        if needs_grace:
                            g.log("Source select re-open: 3s grace period (stream error / dead stream)", "debug")
                            g.wait_for_abort(3)

                        if xbmc.Player().isPlaying() or g.abort_requested():
                            break

                        new_link = None
                        try:
                            window = SourceSelect(
                                *_SM().confirm_skin_path("source_select.xml"),
                                item_information=ii,
                                sources=sources,
                                uncached=uncached,
                            )
                            new_link = window.doModal()
                        except Exception:
                            g.log_stacktrace()
                        finally:
                            try:
                                del window
                            except (UnboundLocalError, NameError):
                                pass

                        if not new_link or new_link == "none":
                            break

                        del seren_player
                        seren_player = _player_module.SerenPlayer()
                        current_link = new_link
                else:
                    seren_player.play_source(stream_link, ii, resume_time=resume_time)
            finally:
                if background:
                    try:
                        background.close()
                    finally:
                        del background
                # Guard against UnboundLocalError if seren_player assignment threw —
                # without this, the original NameError would be replaced by a
                # confusing UnboundLocalError, masking the real cause.
                try:
                    del seren_player
                except (UnboundLocalError, NameError):
                    pass

        except NoPlayableSourcesException:
            try:
                background.close()
                del background
            except (UnboundLocalError, AttributeError):
                pass
            try:
                resolver_window.close()
                del resolver_window
            except (UnboundLocalError, AttributeError):
                pass

            g.cancel_playback()

    elif action == "preScrape":

        from resources.lib.database.skinManager import SkinManager
        from resources.lib.modules import helpers

        try:
            from resources.lib.common import tools

            item_information = tools.get_item_information(action_args)

            # Get Sources
            sources_helper = helpers.SourcesHelper()
            uncached, sources_list, ii = sources_helper.get_sources(action_args)

            # Sort sources
            sources = sources_helper.sort_sources(ii, sources_list)
            if sources is None:
                return

            if item_information["info"]["mediatype"] == g.MEDIA_EPISODE:
                source_select_style = "Episodes"
            else:
                source_select_style = "Movie"
            if g.get_int_setting(f"general.playstyle{source_select_style}") == 0 and sources:
                from resources.lib.modules import resolver

                helpers.Resolverhelper().resolve_silent_or_visible(sources, ii, pack_select)
        finally:
            g.set_runtime_setting("tempSilent", False)

        g.log("Pre-scraping completed")

    elif action == "authRealDebrid":
        from resources.lib.debrid import real_debrid

        real_debrid.RealDebrid().auth()
        g.open_addon_settings(3, 27)

    elif action == "rdAccountInfo":
        from resources.lib.debrid.real_debrid import RealDebrid

        RealDebrid().account_info_to_dialog()

    elif action == "showsHome":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().discover_shows()

    elif action == "myShows":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_shows()

    elif action == "showsMyCollection":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_shows_collection()

    elif action == "showsMyWatchlist":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_shows_watchlist()

    elif action == "showsMyProgress":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_show_progress()

    elif action == "showsMyRecentEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_recent_episodes()

    elif action == "showsRecommended":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_recommended()

    elif action == "showsUpdated":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_updated()

    elif action == "showsSearch":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_search(action_args)

    elif action == "showsSearchResults":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_search_results(action_args)

    elif action == "showsSearchHistory":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_search_history()

    elif action == "showSeasons":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().show_seasons(action_args)

    elif action == "seasonEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().season_episodes(action_args)

    elif action == "showsRelated":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_related(action_args)

    elif action == "showYears":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_years(action_args)

    elif action == "searchMenu":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().search_menu()

    elif action == "toolsMenu":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().tools_menu()

    elif action == "clearCache":
        from resources.lib.common import tools

        g.clear_cache()

    elif action == "traktManager":
        from resources.lib.gui.trakt_context_menu import TraktContextMenu
        from resources.lib.common import tools

        TraktContextMenu(tools.get_item_information(action_args))

    elif action == "onDeckShows":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().on_deck_shows()

    elif action == "onDeckMovies":
        from resources.lib.gui.movieMenus import Menus

        Menus().on_deck_movies()

    elif action == "cacheAssist":
        from resources.lib.modules.cacheAssist import CacheAssistHelper

        CacheAssistHelper().auto_cache(action_args)

    elif action == "tvGenres":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_genres()

    elif action == "showGenresGet":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_genre_list(action_args)

    elif action == "movieGenres":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_genres()

    elif action == "movieGenresGet":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_genre_list(action_args)

    elif action == "shufflePlay":
        from resources.lib.modules import smartPlay

        smartPlay.SmartPlay(action_args).shuffle_play()

    elif action == "resetSilent":
        g.set_runtime_setting("tempSilent", False)
        g.notification(
            f"{g.ADDON_NAME}: {g.get_language_string(30302)}",
            g.get_language_string(30033),
            time=5000,
        )

    elif action == "clearTorrentCache":
        from resources.lib.database.torrentCache import TorrentCache

        TorrentCache().clear_all()

    elif action == "clearDebridCache":
        from resources.lib.database.debridCache import DebridCache

        DebridCache().clear_all()
        g.notification(g.ADDON_NAME, "Debrid cache cleared")

    elif action == "clearProviderStats":
        from resources.lib.database.providerPerformance import ProviderPerformance

        ProviderPerformance().clear_all()
        g.notification(g.ADDON_NAME, g.get_language_string(30738))

    elif action == "reenableProviders":
        from resources.lib.database.providerPerformance import ProviderPerformance

        pp = ProviderPerformance()
        for stats in pp.get_all_stats():
            if stats['status'] in ('disabled', 'demoted'):
                pp.set_status(stats['provider'], 'active')
                pp.execute_sql(
                    "UPDATE provider_stats SET consecutive_failures = 0 WHERE provider = ?",
                    (stats['provider'],),
                )
        g.notification(g.ADDON_NAME, g.get_language_string(30741))

    elif action == "viewProviderStats":
        from resources.lib.database.providerPerformance import ProviderPerformance

        pp = ProviderPerformance()
        all_stats = pp.get_all_stats()
        if not all_stats:
            xbmcgui.Dialog().ok(
                g.get_language_string(30734),
                "No provider performance data recorded yet.\n"
                "Scrape some content first to begin tracking."
            )
        else:
            lines = []
            for s in all_stats:
                status_tag = ""
                if s['status'] == 'disabled':
                    status_tag = " [COLOR red][DISABLED][/COLOR]"
                elif s['status'] == 'demoted':
                    status_tag = " [COLOR orange][DEMOTED][/COLOR]"
                score = pp.get_provider_score(s['provider'])
                lines.append(
                    f"{s['provider'].upper()}{status_tag}  |  "
                    f"Score: {score:.0f}  |  "
                    f"Avg: {s['avg_response_ms']:.0f}ms  |  "
                    f"Results: {s['avg_results']:.1f}/scrape  |  "
                    f"Scrapes: {s['scrape_count']}  |  "
                    f"Fails: {s['consecutive_failures']}"
                )
            selected = xbmcgui.Dialog().select(
                g.get_language_string(30734), lines
            )
            if selected >= 0:
                stat = all_stats[selected]
                detail_lines = [
                    f"Provider: {stat['provider'].upper()}",
                    f"Status: {stat['status'].upper()}",
                    f"Performance Score: {pp.get_provider_score(stat['provider']):.1f} / 100",
                    f"Total Scrapes: {stat['scrape_count']}",
                    f"Avg Response: {stat['avg_response_ms']:.0f}ms",
                    f"Avg Results: {stat['avg_results']:.1f} per scrape",
                    f"Avg Cached: {stat['avg_cached']:.1f} per scrape",
                    f"Consecutive Failures: {stat['consecutive_failures']}",
                    f"Total Results: {stat['total_results']}",
                    f"Total Cached: {stat['total_cached']}",
                ]
                xbmcgui.Dialog().textviewer(
                    f"{stat['provider'].upper()} — Performance Details",
                    "\n".join(detail_lines),
                )

    elif action == "undesirablesSelectDefaults":
        from resources.lib.database.undesirables import undesirables_select_defaults

        undesirables_select_defaults()

    elif action == "undesirablesUserInput":
        from resources.lib.database.undesirables import undesirables_user_input

        undesirables_user_input()

    elif action == "undesirablesUserRemove":
        from resources.lib.database.undesirables import undesirables_user_remove

        undesirables_user_remove()

    elif action == "undesirablesUserRemoveAll":
        from resources.lib.database.undesirables import undesirables_user_remove_all

        undesirables_user_remove_all()

    elif action == "undesirablesReset":
        from resources.lib.database.undesirables import undesirables_reset_defaults

        undesirables_reset_defaults()

    elif action == "titleSubsAdd":
        from resources.lib.database.titleSubs import title_subs_add

        title_subs_add()

    elif action == "titleSubsViewRemove":
        from resources.lib.database.titleSubs import title_subs_view_remove

        title_subs_view_remove()

    elif action == "titleSubsClearAll":
        from resources.lib.database.titleSubs import title_subs_clear_all

        title_subs_clear_all()

    elif action == "showSkipIntro":
        from resources.lib.modules.player import show_skip_intro_dialog

        show_skip_intro_dialog()

    elif action == "openSettings":
        xbmc.executebuiltin(f"Addon.OpenSettings({g.ADDON_ID})")

    elif action == "myTraktLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().my_trakt_lists(mediatype)

    elif action == "myLikedLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().my_liked_lists(mediatype)

    elif action == "TrendingLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().trending_lists(mediatype)

    elif action == "PopularLists":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().popular_lists(mediatype)

    elif action == "traktList":
        from resources.lib.modules.listsHelper import ListsHelper

        ListsHelper().get_list_items()

    elif action == "nonActiveAssistClear":
        from resources.lib.gui import debridServices

        debridServices.Menus().assist_non_active_clear()

    elif action == "debridServices":
        from resources.lib.gui import debridServices

        debridServices.Menus().home()

    elif action == "cacheAssistStatus":
        from resources.lib.gui import debridServices

        debridServices.Menus().get_assist_torrents()

    elif action == "premiumize_transfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_premiumize_transfers()

    elif action == "showsNextUp":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_next_up()

    elif action == "providerTools":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().provider_menu()

    elif action == "installProviders":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        ProviderInstallManager().install_package(action_args)

    elif action == "uninstallProviders":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        ProviderInstallManager().uninstall_package()

    elif action == "showsNew":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_new()

    elif action == "realdebridTransfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_rd_transfers()

    elif action == "alldebridTransfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_ad_transfers()

    elif action == "torboxTransfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_tb_transfers()

    elif action == "debridlinkTransfers":
        from resources.lib.gui import debridServices

        debridServices.Menus().list_dl_transfers()

    elif action == "cleanInstall":
        from resources.lib.common import maintenance

        maintenance.wipe_install()

    elif action == "backupSettings":
        from resources.lib.modules.backup_restore import backup_settings

        backup_settings()

    elif action == "restoreSettings":
        from resources.lib.modules.backup_restore import restore_settings

        restore_settings()

    elif action == "premiumizeCleanup":
        from resources.lib.common import maintenance

        maintenance.premiumize_transfer_cleanup()

    elif action == "manualProviderUpdate":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        ProviderInstallManager().manual_update()
    elif action == "removeSearchHistory":
        from resources.lib.database.searchHistory import SearchHistory

        SearchHistory().remove_search_history(mediatype, endpoint)
        g.container_refresh()
    elif action == "clearSearchHistory":
        from resources.lib.database.searchHistory import SearchHistory

        SearchHistory().clear_search_history(mediatype)

    elif action == "externalProviderInstall":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        confirmation = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30166))
        if confirmation == 0:
            return
        ProviderInstallManager().install_package(1, url=url)

    elif action == "externalProviderUninstall":
        from resources.lib.modules.providers.install_manager import (
            ProviderInstallManager,
        )

        confirmation = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30168).format(url))
        if confirmation == 0:
            return
        ProviderInstallManager().uninstall_package(package=url, silent=False)

    elif action == "showsNetworks":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_networks()

    elif action == "showsNetworkShows":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_networks_results(action_args)

    elif action == "movieYears":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_years()

    elif action == "movieYearsMovies":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movie_years_results(action_args)

    elif action == "syncTraktActivities":
        from resources.lib.database.trakt_sync.activities import TraktSyncDatabase

        TraktSyncDatabase().sync_activities()

    elif action == "traktSyncTools":
        from resources.lib.gui import homeMenu

        homeMenu.Menus().trakt_sync_tools()

    elif action == "flushTraktActivities":
        from resources.lib.database import trakt_sync

        trakt_sync.TraktSyncDatabase().flush_activities()

    elif action == "myFiles":
        from resources.lib.gui import myFiles

        myFiles.Menus().home()

    elif action == "myFilesFolder":
        from resources.lib.gui import myFiles

        myFiles.Menus().my_files_folder(action_args)

    elif action == "myFilesPlay":
        from resources.lib.gui import myFiles

        myFiles.Menus().my_files_play(action_args)

    elif action == "forceTraktSync":
        from resources.lib.database.trakt_sync.activities import TraktSyncDatabase

        trakt_db = TraktSyncDatabase()
        trakt_db.flush_activities()
        trakt_db.sync_activities()

    elif action == "rebuildTraktDatabase":
        from resources.lib.database.trakt_sync import TraktSyncDatabase

        TraktSyncDatabase().re_build_database()

    elif action == "cleanOrphanedMetadata":
        from resources.lib.database.trakt_sync import TraktSyncDatabase

        trakt_db = TraktSyncDatabase()
        trakt_db.clean_orphaned_metadata()

    elif action == "myUpcomingEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_upcoming_episodes()

    elif action == "myWatchedEpisodes":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().my_watched_episode()

    elif action == "myWatchedMovies":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().my_watched_movies()

    elif action == "showsByActor":
        from resources.lib.gui import tvshowMenus

        tvshowMenus.Menus().shows_by_actor(action_args)

    elif action == "movieByActor":
        from resources.lib.gui import movieMenus

        movieMenus.Menus().movies_by_actor(action_args)

    elif action == "playFromRandomPoint":
        from resources.lib.modules import smartPlay

        smartPlay.SmartPlay(action_args).play_from_random_point()

    elif action == "refreshProviders":
        from resources.lib.modules.providers import CustomProviders

        providers = CustomProviders()
        providers.update_known_providers()
        providers.poll_database()

    elif action == "installSkin":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().install_skin()

    elif action == "uninstallSkin":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().uninstall_skin()

    elif action == "switchSkin":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().switch_skin()

    elif action == "manageProviders":
        g.show_busy_dialog()
        from resources.lib.gui.windows.provider_packages import ProviderPackages
        from resources.lib.database.skinManager import SkinManager

        try:
            window = ProviderPackages(*SkinManager().confirm_skin_path("provider_packages.xml"))
            window.doModal()
        finally:
            del window

    elif action == "flatEpisodes":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().flat_episode_list(action_args)

    elif action == "runPlayerDialogs":
        from resources.lib.modules.player import PlayerDialogs

        try:
            player_dialogs = PlayerDialogs()
            player_dialogs.display_dialog()
        finally:
            del player_dialogs

    elif action == "authAllDebrid":
        from resources.lib.debrid.all_debrid import AllDebrid

        AllDebrid().auth()
        g.open_addon_settings(3, 36)

    elif action == "adAccountInfo":
        from resources.lib.debrid.all_debrid import AllDebrid

        AllDebrid().account_info_to_dialog()

    elif action == "authTorBox":
        from resources.lib.debrid.torbox import TorBox

        TorBox().auth()
        g.open_addon_settings(3, 37)

    elif action == "tbAccountInfo":
        from resources.lib.debrid.torbox import TorBox

        TorBox().account_info_to_dialog()

    elif action == "authDebridLink":
        from resources.lib.debrid.debrid_link import DebridLink

        DebridLink().auth()
        g.open_addon_settings(3, 38)

    elif action == "dlAccountInfo":
        from resources.lib.debrid.debrid_link import DebridLink

        DebridLink().account_info_to_dialog()

    elif action == "checkSkinUpdates":
        from resources.lib.database.skinManager import SkinManager

        SkinManager().check_for_updates()

    elif action == "authPremiumize":
        from resources.lib.debrid.premiumize import Premiumize

        Premiumize().auth()
        g.open_addon_settings(3, 13)

    elif action == "smartAuthPremiumize":
        from resources.lib.debrid.premiumize import Premiumize
        pm = Premiumize()
        if g.get_setting("premiumize.token"):
            pm.revoke_auth()
        else:
            pm.auth()
            g.open_addon_settings(3, 13)

    elif action == "smartAuthRealDebrid":
        from resources.lib.debrid.real_debrid import RealDebrid
        rd = RealDebrid()
        if g.get_setting("rd.auth"):
            rd.revoke_auth()
        else:
            rd.auth()
            g.open_addon_settings(3, 27)

    elif action == "smartAuthAllDebrid":
        from resources.lib.debrid.all_debrid import AllDebrid
        ad = AllDebrid()
        if g.get_setting("alldebrid.apikey"):
            ad.revoke_auth()
        else:
            ad.auth()
            g.open_addon_settings(3, 36)

    elif action == "smartAuthTorBox":
        from resources.lib.debrid.torbox import TorBox
        tb = TorBox()
        if g.get_setting("torbox.token"):
            tb.revoke_auth()
        else:
            tb.auth()
            g.open_addon_settings(3, 37)

    elif action == "smartAuthDebridLink":
        from resources.lib.debrid.debrid_link import DebridLink
        dl = DebridLink()
        if g.get_setting("debridlink.token"):
            dl.revoke_auth()
        else:
            dl.auth()
            g.open_addon_settings(3, 38)

    elif action == "pmAccountInfo":
        from resources.lib.debrid.premiumize import Premiumize

        Premiumize().account_info_to_dialog()
    elif action == "revokePremiumize":
        from resources.lib.debrid.premiumize import Premiumize
        Premiumize().revoke_auth()

    elif action == "revokeRealDebrid":
        from resources.lib.debrid.real_debrid import RealDebrid
        RealDebrid().revoke_auth()

    elif action == "revokeAllDebrid":
        from resources.lib.debrid.all_debrid import AllDebrid
        AllDebrid().revoke_auth()

    elif action == "revokeTorBox":
        from resources.lib.debrid.torbox import TorBox
        TorBox().revoke_auth()

    elif action == "revokeDebridLink":
        from resources.lib.debrid.debrid_link import DebridLink
        DebridLink().revoke_auth()


    elif action == "testWindows":
        from resources.lib.gui.homeMenu import Menus

        Menus().test_windows()

    elif action == "testPlayingNext":
        from resources.lib.gui import mock_windows

        mock_windows.mock_playing_next()

    elif action == "testStillWatching":
        from resources.lib.gui import mock_windows

        mock_windows.mock_still_watching()

    elif action == "testGetSourcesWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_get_sources()

    elif action == "testResolverWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_resolver()

    elif action == "testSourceSelectWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_source_select()

    elif action == "testManualCacheWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_cache_assist()

    elif action == "testDownloadManagerWindow":
        from resources.lib.gui import mock_windows

        mock_windows.mock_download_manager()

    elif action == "showsPopularRecent":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().shows_popular_recent()

    elif action == "showsTrendingRecent":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().shows_trending_recent()

    elif action == "moviePopularRecent":
        from resources.lib.gui.movieMenus import Menus

        Menus().movie_popular_recent()

    elif action == "movieTrendingRecent":
        from resources.lib.gui.movieMenus import Menus

        Menus().movie_trending_recent()

    elif action == "downloadManagerView":
        from resources.lib.gui.windows.download_manager import DownloadManager
        from resources.lib.database.skinManager import SkinManager

        try:
            window = DownloadManager(*SkinManager().confirm_skin_path("download_manager.xml"))
            window.doModal()
        finally:
            del window

    elif action == "longLifeServiceManager":
        from resources.lib.modules.providers.service_manager import (
            ProvidersServiceManager,
        )

        ProvidersServiceManager().run_long_life_manager()

    elif action == "showsRecentlyWatched":
        from resources.lib.gui.tvshowMenus import Menus

        Menus().shows_recently_watched()

    elif action == "toggleLanguageInvoker":
        from resources.lib.common.maintenance import toggle_reuselanguageinvoker

        toggle_reuselanguageinvoker()

    elif action == "runMaintenance":
        from resources.lib.common.maintenance import run_maintenance

        run_maintenance()

    elif action == "torrentCacheCleanup":
        from resources.lib.database import torrentCache

        torrentCache.TorrentCache().do_cleanup()

    elif action == "undesirablesStartup":
        try:
            from resources.lib.database.undesirables import UndesirableCache
            uc = UndesirableCache()
            uc.add_new_defaults()
            g.log("Undesirables database initialized", "debug")
        except Exception as e:
            g.log(f"Undesirables startup error: {e}", "warning")

    elif action == "updateAnimeMappings":
        try:
            from resources.lib.modules.anime.anilist_mapping import update_mapping_db
            update_mapping_db()
        except Exception as e:
            g.log(f"Anime mappings update error: {e}", "warning")
        try:
            from resources.lib.modules.anime.dub_data import update_mal_dub_json
            update_mal_dub_json()
        except Exception as e:
            g.log(f"MAL-Dubs update error: {e}", "warning")
        try:
            from resources.lib.modules.anime.anidb_titles import download_titles_dump
            download_titles_dump()
        except Exception as e:
            g.log(f"AniDB titles dump update error: {e}", "warning")

    elif action == "animeRelated":
        try:
            anidb_id = int(params.get("anidb_id", 0))
            if anidb_id:
                from resources.lib.gui.tvshowMenus import TVShowMenus
                TVShowMenus().anime_related_shows(anidb_id)
        except Exception as e:
            g.log(f"animeRelated error: {e}", "warning")

    elif action == "chooseTimeZone":
        from resources.lib.modules.manual_timezone import choose_timezone

        choose_timezone()

    elif action == "widgetRefresh":
        if_playing = params.get('playing')
        if if_playing is not None:
            if_playing = False if if_playing.lower() == "false" else True if if_playing.lower() == "true" else None
        if if_playing is not None:
            g.trigger_widget_refresh(if_playing=if_playing)
        else:
            g.trigger_widget_refresh()

    elif action == "updateLocalTimezone":
        g.init_local_timezone()

    elif action == "chooseFilters":
        import resources.lib.gui.windows.filter_select as filter_select

        try:
            window = filter_select.FilterSelect("filter_select.xml", g.ADDON_PATH)
            window.doModal()
        finally:
            del window

    elif action == "chooseSorting":
        import resources.lib.gui.windows.sort_select as sort_select

        try:
            window = sort_select.SortSelect("sort_select.xml", g.ADDON_PATH)
            window.doModal()
        finally:
            del window
    else:
        g.log(f"Unknown action requested: {action}", "error")
