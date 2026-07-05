import copy
import importlib
import json
import sys
import time
from functools import cached_property
from urllib import parse

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib.common import tools
from resources.lib.database.trakt_sync import bookmark
from resources.lib.indexers import trakt
from resources.lib.modules import smartPlay
from resources.lib.modules.globals import g


class SerenPlayer(xbmc.Player):
    """
    Class to handle playback methods and accept callbacks from Kodi player
    """

    def __init__(self):
        super().__init__()

        self.trakt_id = None
        self.mediatype = None
        self.offset = None
        self.playing_file = None
        self.scrobbling_enabled = g.get_bool_setting("trakt.scrobbling")
        self.item_information = None
        self.smart_playlists = g.get_bool_setting("smartplay.playlistcreate")
        self.smart_module = None
        self.current_time = 0
        self.total_time = 0
        self.watched_percentage = 0
        self.ignoreSecondsAtStart = g.get_int_setting("trakt.ignoreSecondsAtStart")
        self.min_time_before_scrape = 600
        self.playCountMinimumPercent = g.get_int_setting("trakt.playCountMinimumPercent")
        self.dialogs_enabled = g.get_bool_setting("smartplay.playingnextdialog") or g.get_bool_setting(
            "smartplay.stillwatching"
        )
        self.pre_scrape_enabled = g.get_bool_setting("smartPlay.preScrape")
        self.playing_next_time = g.get_int_setting("playingnext.time")
        self.trakt_enabled = bool(g.get_setting("trakt.auth", ""))
        self._running_path = None

        # Flags
        self.resumed = False
        self.playback_started = False
        self.playback_error = False
        self.playback_ended = False
        self.playback_stopped = False
        self.stop_event_received = False  # Set by onPlayBackStopped regardless of playback_started
        self._end_playback_done = False  # Guard: prevents double-execution of _end_playback()
        self.scrobbled = False
        self.scrobble_started = False
        self.last_attempted_scrobble_stop = 0
        self.last_attempted_scrobble_pause = 0
        self.marked_watched = False
        self.dialogs_triggered = False
        self.pre_scrape_initiated = False
        self.playback_timestamp = 0

        # Skip segment handler (intro/recap/credits/preview across anime/TV/movies)
        self._skip_handler = None
        # Per-segment-type one-shot trigger guard. Resets if user seeks back into a segment.
        self._skip_state = {
            "intro": {"inside": False, "shown": False, "last_t": None},
            "recap": {"inside": False, "shown": False, "last_t": None},
            "credits": {"inside": False, "shown": False, "last_t": None},
            "preview": {"inside": False, "shown": False, "last_t": None},
        }

        # Per-type enable toggles (introduced in 3.3.92 — replaces anime.skip* names).
        self._skip_enabled = {
            "intro": g.get_bool_setting("skip.intro"),
            "recap": g.get_bool_setting("skip.recap"),
            "credits": g.get_bool_setting("skip.credits"),
            "preview": g.get_bool_setting("skip.preview"),
        }
        self._skip_auto = {
            "intro":   g.get_bool_setting("skip.autoIntro"),
            "recap":   g.get_bool_setting("skip.autoRecap"),
            "credits": g.get_bool_setting("skip.autoCredits"),
            "preview": g.get_bool_setting("skip.autoPreview"),
        }
        self._skip_offset = g.get_int_setting("skip.offset")

        # Anime-only fallback timer (used when AniSkip/Anime-Skip have no data)
        self._skip_fallback_delay = g.get_int_setting("anime.skipFallbackDelay")
        self._skip_fallback_duration = g.get_int_setting("anime.skipFallbackDuration")
        self._skip_fallback_offset = g.get_int_setting("anime.skipFallbackOffset")

    @cached_property
    def _trakt_api(self):
        return trakt.TraktAPI()

    @cached_property
    def bookmark_sync(self):
        return bookmark.TraktSyncDatabase()

    def play_source(self, stream_link, item_information, resume_time=None):
        """Method for handling playing of sources.

        :param stream_link: Direct link of source to be played or dict containing more information about the stream
        to play
        :type stream_link: str|dict
        :param item_information: Information about the item to be played
        :type item_information:dict
        :param resume_time:Time to resume the source at
        :type resume_time:int
        :rtype:None
        """
        self.pre_scrape_initiated = False
        if resume_time:
            self.offset = float(resume_time)

        if not stream_link:
            g.cancel_playback()
            return

        self.playing_file = stream_link
        self.item_information = item_information
        self.smart_module = smartPlay.SmartPlay(item_information)
        self.mediatype = self.item_information["info"]["mediatype"]
        self.trakt_id = self.item_information["info"]["trakt_id"]

        if self.item_information.get("resume", "false") == "true":
            self._try_get_bookmark()

        self._handle_bookmark()
        self._add_support_for_external_trakt_scrobbling()

        self.playing_next_time = max(self.playing_next_time, self.item_information["info"]["duration"] * (1 - (g.get_int_setting("playingnext.percent") / 100)))

        xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, True, self._create_list_item(stream_link))

        # Start skip-segment handler in background for episodes and movies
        if any(self._skip_enabled.values()) and self.mediatype in (g.MEDIA_EPISODE, g.MEDIA_MOVIE):
            try:
                from resources.lib.modules.skip.skip_handler import SkipHandler
                episode_number = self.item_information["info"].get("episode", 0) if self.mediatype == g.MEDIA_EPISODE else 0
                if self.mediatype == g.MEDIA_MOVIE or episode_number:
                    self._skip_handler = SkipHandler(self.item_information, episode_number)
                    self._skip_handler.start()
            except Exception as e:
                g.log(f"Skip handler init failed: {e}", "debug")

        self._keep_alive()

    def attach_to_playing(self, stream_link, item_information, resume_time=None):
        """Attach lifecycle management to an already-playing stream.

        Used by PlaybackWatchdog — the stream is already playing via
        xbmc.Player().play(). This sets up Trakt scrobbling, bookmarks,
        Playing Next dialogs, anime skip, and enters _keep_alive() —
        everything play_source() does except setResolvedUrl.

        :param stream_link: URL of the currently playing stream
        :param item_information: Metadata on the playing item
        :param resume_time: Time to seek to (if resuming)
        """
        self.pre_scrape_initiated = False
        if resume_time:
            self.offset = float(resume_time)
            # Watchdog already seeked to the resume position before the
            # monitoring window. Mark as resumed so _keep_alive() doesn't
            # do a second seek 30s later.
            self.resumed = True

        if not stream_link:
            return

        self.playing_file = stream_link
        self.item_information = item_information
        self.smart_module = smartPlay.SmartPlay(item_information)
        self.mediatype = self.item_information["info"]["mediatype"]
        self.trakt_id = self.item_information["info"]["trakt_id"]

        if self.item_information.get("resume", "false") == "true":
            self._try_get_bookmark()

        self._handle_bookmark()
        self._add_support_for_external_trakt_scrobbling()

        self.playing_next_time = max(
            self.playing_next_time,
            self.item_information["info"]["duration"]
            * (1 - (g.get_int_setting("playingnext.percent") / 100)),
        )

        # Stream is already playing via watchdog's Player.play().
        # Do NOT call setResolvedUrl here — when TMDb Helper is the
        # launching player, setResolvedUrl(True) causes Kodi to route
        # the resolution back through TMDb Helper, which opens a new
        # VideoPlayer and kills the watchdog's working stream.
        # The plugin handle is released by g.cancel_playback() in the
        # router before the watchdog starts.

        # Manually trigger start state
        self.playback_started = True
        self.playback_timestamp = time.time()
        try:
            self._running_path = self.getPlayingFile()
        except Exception:
            self._running_path = stream_link

        g.close_busy_dialog()
        g.close_all_dialogs()

        # Smart playlist handling
        if self.smart_playlists and self.mediatype == "episode":
            if g.PLAYLIST.size() == 1 and not self.smart_module.is_season_final():
                self.smart_module.build_playlist()
            elif g.PLAYLIST.size() == g.PLAYLIST.getposition() + 1:
                self.smart_module.append_next_season()

        # Start skip-segment handler in background for episodes and movies
        if any(self._skip_enabled.values()) and self.mediatype in (g.MEDIA_EPISODE, g.MEDIA_MOVIE):
            try:
                from resources.lib.modules.skip.skip_handler import SkipHandler
                episode_number = self.item_information["info"].get("episode", 0) if self.mediatype == g.MEDIA_EPISODE else 0
                if self.mediatype == g.MEDIA_MOVIE or episode_number:
                    self._skip_handler = SkipHandler(self.item_information, episode_number)
                    self._skip_handler.start()
            except Exception as e:
                g.log(f"Skip handler init failed: {e}", "debug")

        self._keep_alive()

    # region Kodi player overrides
    def getTotalTime(self):
        """
        Returns total time for playing file if user is playing a file
        :return: Total length of file else 0 if not playing an item
        :rtype: int
        """
        try:
            return super().getTotalTime()
        except RuntimeError:
            g.log("Trying to get player total time while not playing", "warning")
            return 0

    def getTime(self):
        """
        Gets current position in seconds from start of item
        :return: Current position or 0 if not playing a file
        :rtype: int
        """
        try:
            return current_time if (current_time := super().getTime()) > 0 else 0
        except RuntimeError:
            g.log("Trying to get player time while not playing", "warning")
            return 0

    def isPlayingVideo(self):
        """
        Returns true if currently playing item is a video file
        :return: True if playing a file and it is video else False
        :rtype: bool
        """
        return super().isPlayingVideo()

    def seekTime(self, time):
        """
        Seeks the specified amount of time as fractional seconds if playing a file. The time specified is relative to
        the beginning of the currently. playing media file.
        :param time: Time to seek as fractional seconds
        :type time: float
        :return: None
        :rtype: None
        """
        try:
            super().seekTime(time)
        except RuntimeError:
            g.log("Trying to seek player when not playing a file", "warning")

    def getSubtitles(self):
        """
        Get subtitle stream name if playing a file
        :return: Stream Name if playing a file else None
        :rtype: str, None
        """
        return subtitles if (subtitles := super().getSubtitles()) else None

    def getAvailableSubtitleStreams(self):
        """
        Get Subtitle stream names.
        :return: List of available subtitle streams
        :rtype: list, None
        """
        return super().getAvailableSubtitleStreams() if self.isPlaying() else None

    def setSubtitles(self, subtitle):
        """
        Set subtitle file and enable subtitles if currently playing an item.
        :param subtitle:  Path to file to use as source of subtitles
        :type subtitle: str
        :return: None
        :rtype: None
        """
        if self.isPlaying():
            super().setSubtitles(subtitle)
        else:
            g.log("Trying to set subtitles when not playing a file", "warning")

    def getPlayingFile(self):
        """
        Fetches the path to the playing file else returns None
        :return: Path to file
        :rtype: str/None
        """
        try:
            return super().getPlayingFile()
        except RuntimeError:
            # seems that we have a racing condition between isPlaying() and getPlayingFile()
            g.log("Trying to get playing file when not playing a file", "warning")

    # endregion

    # region Kodi player callbacks
    def onAVStarted(self):
        """
        Callback method from Kodi to advise that AV stream has started
        :return: None
        :rtype: None
        """
        self._start_playback()

    def onAVChange(self):
        """
        Callback method from Kodi to advise that AV stream has started
        This is being used as a fallback for instances where AVStarted fails
        :return: None
        :rtype: None
        """
        self._start_playback()

    def onPlayBackSeek(self, time, seekOffset):
        """
        Callback method from Kodi when a seek event has occured
        :param time: Time to seek to
        :type time: int
        :param seekOffset: Offset from previous position
        :type seekOffset: int
        :return: None
        :rtype: None
        """
        seekOffset /= 1000
        self._trakt_start_watching(offset=seekOffset, re_scrobble=True)

    def onPlayBackSeekChapter(self, chapter):
        """
        Callback method from Kodi when user performs a chapter seek.
        :param chapter: Chapter seeked to
        :type chapter: int
        :return: None
        :rtype: None
        """
        self._trakt_start_watching(re_scrobble=True)

    def onPlayBackResumed(self):
        """
        Callback method from Kodi when user resumes a paused file.
        :return: None
        :rtype: None
        """
        self._trakt_start_watching(re_scrobble=True)

    def onPlayBackEnded(self):
        """
        Callback method from Kodi when playback has finished
        :return: None
        :rtype: None
        """
        self.playback_ended = bool(self.playback_started)
        self._end_playback()
        if g.PLAYLIST.getposition() == g.PLAYLIST.size() or g.PLAYLIST.size() == 1:
            g.PLAYLIST.clear()

    def onPlayBackStopped(self):
        """
        Callback method from Kodi when user stops a file.
        :return: None
        :rtype: None
        """
        self.playback_stopped = bool(self.playback_started)
        self.stop_event_received = True
        g.PLAYLIST.clear()
        g.close_busy_dialog()
        g.close_all_dialogs()
        self._end_playback()

    def onPlayBackPaused(self):
        """
        Callback method from Kodi when user pauses a file.
        :return: None
        :rtype: None
        """
        self._handle_bookmark()
        self._trakt_stop_watching()

    def onPlayBackError(self):
        """
        Callback method from Kodi when playback stops due to an error
        :return: None
        :rtype: None
        """
        g.log("Kodi has reported an error and has stopped playback!", "warning")
        self.playback_error = True
        g.PLAYLIST.clear()
        g.close_busy_dialog()
        g.close_all_dialogs()
        self._end_playback()

    # endregion

    def _start_playback(self):
        if self.playback_started:
            return

        self.playback_started = True
        self.playback_timestamp = time.time()
        self._running_path = self.getPlayingFile()

        g.close_busy_dialog()
        g.close_all_dialogs()

        if self.smart_playlists and self.mediatype == "episode":
            if g.PLAYLIST.size() == 1 and not self.smart_module.is_season_final():
                self.smart_module.build_playlist()
            elif g.PLAYLIST.size() == g.PLAYLIST.getposition() + 1:
                self.smart_module.append_next_season()

    def _end_playback(self):
        if self._end_playback_done:
            return
        self._end_playback_done = True
        self._handle_bookmark()
        self._trakt_stop_watching()
        self._trakt_mark_playing_item_watched()
        self._debrid_post_playback_cleanup()
        if g.get_bool_setting("general.force.widget.refresh.playback"):
            # trigger_widget_refresh() has a blocking wait loop — never call it directly
            # from within a Kodi player callback (onPlayBackStopped fires inside
            # g.wait_for_abort(), so a nested wait_for_abort() inside the refresh loop
            # deadlocks the thread permanently). Run it on a daemon thread instead.
            import threading
            threading.Thread(target=g.trigger_widget_refresh, daemon=True).start()

    def _debrid_post_playback_cleanup(self):
        """Unified smart auto-delete for all debrid services.
        Deletes the resolved torrent/transfer from cloud if fully watched.
        Keeps in cloud if stopped early (for later viewing).
        Works for Real-Debrid, Premiumize, AllDebrid, TorBox, and Debrid-Link."""
        try:
            from resources.lib.debrid.debrid_utils import get_pending_cleanup

            pending = get_pending_cleanup()
            if not pending:
                return

            # If playback never started (CDN failed, stream error, etc.),
            # silently discard the cleanup record — nothing to decide on.
            if not self.playback_started:
                g.log(
                    f"Smart delete ({pending['service']}): Discarding cleanup for "
                    f"{pending['item_id']} — playback never started",
                    "debug",
                )
                return

            service = pending["service"]
            item_id = pending["item_id"]
            delete_method = pending["delete_method"]

            # Check if fully watched using same threshold as Trakt scrobbling
            if self.watched_percentage >= self.playCountMinimumPercent:
                # Fully watched — delete from cloud
                debrid_module = self._get_debrid_module(service)
                if debrid_module:
                    getattr(debrid_module, delete_method)(item_id)
                    g.log(
                        f"Smart delete ({service}): Deleted item {item_id} "
                        f"(watched {self.watched_percentage}%)",
                        "info",
                    )
            else:
                # Stopped early — keep in cloud for later
                g.log(
                    f"Smart delete ({service}): Keeping item {item_id} "
                    f"in cloud (watched {self.watched_percentage}%)",
                    "info",
                )
        except Exception as e:
            g.log(f"Smart delete cleanup error: {e}", "warning")

    @staticmethod
    def _get_debrid_module(service):
        """Lazy-load the appropriate debrid module by service name."""
        if service == "real_debrid":
            from resources.lib.debrid.real_debrid import RealDebrid
            return RealDebrid()
        elif service == "premiumize":
            from resources.lib.debrid.premiumize import Premiumize
            return Premiumize()
        elif service == "all_debrid":
            from resources.lib.debrid.all_debrid import AllDebrid
            return AllDebrid()
        elif service == "torbox":
            from resources.lib.debrid.torbox import TorBox
            return TorBox()
        elif service == "debrid_link":
            from resources.lib.debrid.debrid_link import DebridLink
            return DebridLink()
        return None

    def _get_kodi_preferred_subtitle_language(self):
        language = g.get_kodi_preferred_subtitle_language(True)
        if language == "original":
            audio_streams = self.getAvailableAudioStreams()
            if not audio_streams or len(audio_streams) == 0:
                return None
            return audio_streams[0]
        elif language == "default":
            return xbmc.getLanguage(xbmc.ISO_639_2)
        elif language in ["none", "forced_only"]:
            return None
        else:
            return language

    def _create_list_item(self, stream_link):
        info = copy.deepcopy(self.item_information["info"])
        g.clean_info_keys(info)
        g.convert_info_dates(info)

        if isinstance(stream_link, dict) and stream_link["type"] == "adaptive":
            if g.ADDON_USERDATA_PATH not in sys.path:
                sys.path.append(g.ADDON_USERDATA_PATH)
            provider = stream_link["provider_imports"]
            provider_module = importlib.import_module(f"{provider[0]}.{provider[1]}")
            if not hasattr(provider_module, "get_listitem") and hasattr(provider_module, "sources"):
                provider_module = provider_module.sources()
            item = provider_module.get_listitem(stream_link)
            item.setInfo("video", info)
        else:
            item = xbmcgui.ListItem(path=stream_link)
            info["FileNameAndPath"] = parse.unquote(self.playing_file)
            item.setInfo("video", info)
            item.setProperty("IsPlayable", "true")

        art = self.item_information.get("art", {})
        item.setArt(art if isinstance(art, dict) else {})
        cast = self.item_information.get("cast", [])
        item.setCast(cast if isinstance(cast, list) else [])
        item.setUniqueIDs(
            {i.split("_")[0]: info[i] for i in info if i.endswith("id")},
        )
        return item

    def _add_support_for_external_trakt_scrobbling(self):
        trakt_meta = {}
        keys = {
            "tmdb_id": "tmdb",
            "imdb_id": "imdb",
            "trakt_slug": "slug",
            "tvdb_id": "tvdb",
            "trakt_id": "trakt",
        }

        info = self.item_information.get("info", {})
        for id in keys:
            meta_id = info.get(f"tvshow.{id}" if info.get("mediatype") == "episode" else id)
            if meta_id:
                trakt_meta[keys[id]] = meta_id

        g.HOME_WINDOW.setProperty("script.trakt.ids", json.dumps(trakt_meta, sort_keys=True))

    def _update_progress(self, offset=None):
        if not self._is_file_playing():
            return

        self.current_time = self.getTime()

        if offset is not None:
            self.current_time += offset

        if self.total_time > 0:
            try:
                self.watched_percentage = tools.safe_round(float(self.current_time) / float(self.total_time) * 100, 2)
                self.watched_percentage = min(self.watched_percentage, 100)
            except TypeError:
                pass

    def _log_debug_information(self):
        g.log(f"PlaybackIdentifedAt: {self.getTime()}", "debug")
        g.log(f"IgnoringSecondsAtStart: {self.ignoreSecondsAtStart}", "debug")
        g.log(f"PreScrapeSeconds: {self.min_time_before_scrape}", "debug")
        g.log(f"PlayCountMin: {self.playCountMinimumPercent}", "debug")
        g.log(f"DialogsEnabled: {self.dialogs_enabled}", "debug")
        g.log(f"TraktEnabled: {self.trakt_enabled}", "debug")
        g.log(f"DialogSeconds: {self.playing_next_time}", "debug")
        g.log(f"TotalMediaLength: {self.getTotalTime()}", "debug")

    # region Trakt
    def _trakt_start_watching(self, offset=None, re_scrobble=False):
        if (
            not self.trakt_enabled
            or not self.scrobbling_enabled
            or (self.scrobbled and not re_scrobble)
            or (self.scrobble_started and not re_scrobble)
        ):
            return

        if self.watched_percentage >= self.playCountMinimumPercent or self.current_time < self.ignoreSecondsAtStart:
            return

        try:
            post_data = self._build_trakt_object(offset=offset)

            self._trakt_api.post("scrobble/start", post_data)
        except Exception:
            g.log_stacktrace()
        self.scrobble_started = True

    def _trakt_stop_watching(self):
        if (
            not self.trakt_enabled
            or not self.scrobbling_enabled
            or self.scrobbled
            or self.current_time < self.ignoreSecondsAtStart
        ):
            return

        post_data = self._build_trakt_object()

        if post_data["progress"] >= self.playCountMinimumPercent:
            if time.time() - self.last_attempted_scrobble_stop < 30 and not g.abort_requested():
                return
            post_data["progress"] = max(post_data["progress"], 80)
            try:
                scrobble_response = self._trakt_api.post("scrobble/stop", post_data)
            except Exception:
                g.log_stacktrace()
                return
            finally:
                self.last_attempted_scrobble_stop = time.time()
            if scrobble_response.status_code in (201, 409):
                self.scrobbled = True
                self._trakt_mark_playing_item_watched()
                if scrobble_response.status_code == 201:
                    try:
                        action = scrobble_response.json()["action"]
                        if action != "scrobble":
                            g.log(f"Trakt scrobble/stop returned action: {action}", "warning")
                    except Exception:
                        g.log_stacktrace()
                return
            else:
                g.log(f"Trakt scrobble/stop returned status code: {scrobble_response.status_code}", "warning")
        elif self.current_time > self.ignoreSecondsAtStart:
            if (pause_time := time.time() - self.last_attempted_scrobble_pause) < 5:
                g.log(f"Trakt scrobble/pause repeat called: {pause_time}s", "warning")
            try:
                scrobble_response = self._trakt_api.post("scrobble/pause", post_data)
            except Exception:
                g.log_stacktrace()
                return
            finally:
                self.last_attempted_scrobble_pause = time.time()
            if scrobble_response.status_code != 201:
                g.log(f"Trakt scrobble/pause returned status code: {scrobble_response.status_code}", "warning")

    def _trakt_mark_playing_item_watched(self):
        if (
            self.marked_watched
            or not self.playback_started
            or not self.watched_percentage >= self.playCountMinimumPercent
        ):
            return

        self.marked_watched = True

        if self.mediatype == "episode":
            from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

            TraktSyncDatabase().mark_episode_watched(
                self.item_information["info"]["trakt_show_id"],
                self.item_information["info"]["season"],
                self.item_information["info"]["episode"],
            )
        if self.mediatype == "movie":
            from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

            TraktSyncDatabase().mark_movie_watched(self.trakt_id)

        # Clear L1 list cache so watched status reflects immediately on next list build
        try:
            from resources.lib.database.trakt_sync import clear_list_cache
            clear_list_cache()
        except Exception:
            pass

    def _build_trakt_object(self, offset=None):
        post_data = {self.mediatype: {"ids": {"trakt": self.trakt_id}}}
        if offset:
            self._update_progress(offset)
        post_data["app_version"] = g.VERSION

        post_data["progress"] = self.watched_percentage
        return post_data

    # endregion

    def _keep_alive(self):
        for _ in range(480):
            if self._is_file_playing() or self._playback_has_stopped() or g.wait_for_abort(0.25):
                break

        self.total_time = self.getTotalTime()
        self.min_time_before_scrape = max(self.total_time * 0.2, self.min_time_before_scrape)

        if self.offset and not self.resumed:
            self.seekTime(self.offset)
            self.resumed = True

        self._log_debug_information()

        while not g.wait_for_abort(0.5) and self._is_file_playing():  # This order is correct! Wait then check.
            self._update_progress()

            if not self.scrobble_started:
                self._trakt_start_watching()

            time_left = int(self.total_time) - int(self.current_time)

            # Skip-segment check (intro/recap/credits/preview)
            self._check_skip()

            if self.min_time_before_scrape > time_left and not self.pre_scrape_initiated:
                self._handle_pre_scrape()

            if self.watched_percentage >= self.playCountMinimumPercent and self.scrobble_started and not self.scrobbled:
                self._handle_bookmark()
                self._trakt_stop_watching()

            if self.dialogs_enabled and not self.dialogs_triggered and time_left <= self.playing_next_time:
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runPlayerDialogs")')
                self.dialogs_triggered = True

        if not self._playback_has_stopped():
            # Kodi fires onPlayBackStopped/onPlayBackEnded asynchronously — wait up to 2s
            # for the callback to arrive before falling back to a direct _end_playback() call.
            for _i in range(40):  # 40 × 50 ms = 2 s max
                if self._playback_has_stopped() or g.wait_for_abort(0.05):
                    break
            if not self._playback_has_stopped():
                # Kodi did not fire any callback — call _end_playback() directly
                # (guard inside prevents double-execution if callback races in later)
                self._end_playback()

    def _playback_has_stopped(self):
        return self.playback_stopped or self.playback_error or self.playback_ended or self.stop_event_received

    def _check_skip(self):
        """Check if current playback position is in any enabled skip segment.

        Handles up to four segment types in chronological order:
        - intro:   start..end → "Skip Intro" overlay (or auto-skip when enabled)
        - recap:   start..end → "Skip Recap" overlay
        - credits: start..end → mid-file credits "Skip Credits" overlay
                   start..None (runs to end of media) → trigger Playing Next
        - preview: same dual behaviour as credits

        Re-entry on seek-back is detected and re-shows the overlay once per entry.
        Anime fallback timer (anime.skipFallback*) still applies when no API data
        is available and the underlying handler reports anime content.
        """
        if not self._skip_handler or not self._skip_handler.ready:
            return

        current = int(self.current_time)
        segments = self._skip_handler.segments

        # Walk segment types in chronological order so the right overlay fires when
        # ranges overlap. A real episode plays as: recap → intro → … → credits → preview.
        for seg_type in ("recap", "intro", "credits", "preview"):
            if not self._skip_enabled.get(seg_type):
                continue

            seg_list = segments.get(seg_type) or []
            base_offset = self._skip_offset

            # Anime intro fallback: AniSkip/Anime-Skip miss → use timer
            if (
                seg_type == "intro"
                and not seg_list
                and self._skip_handler.is_anime
                and self._skip_fallback_duration > 0
            ):
                seg_list = [(self._skip_fallback_delay,
                             self._skip_fallback_delay + self._skip_fallback_duration)]
                base_offset = self._skip_fallback_offset

            for idx, seg_tup in enumerate(seg_list):
                offset = base_offset
                start, end = seg_tup

                # credits/preview with end=None means "runs to end of media" — handle below
                ends_at_media_end = end is None
                if ends_at_media_end:
                    try:
                        end = max(0, int(self.total_time) - 10)
                    except Exception:
                        continue

                if start is None or end is None or end <= start:
                    continue

                if not self._segment_entry_check((seg_type, idx), current, start, end):
                    continue

                # We've entered the segment for the first time (or re-entered after seek-back)
                self._dispatch_segment(seg_type, start, end, offset, ends_at_media_end)

    def _segment_entry_check(self, state_key, current, seg_start, seg_end, margin=0.25):
        """One-shot-per-entry guard. Mirrors TheIntroDB addon's re-entry logic.

        Returns True the first poll after the playhead enters the segment range,
        and False on every subsequent poll until the playhead leaves it. If the
        user seeks back into the segment, the next entry yields True again.
        """
        state = self._skip_state.setdefault(
            state_key, {"inside": False, "shown": False, "last_t": None}
        )

        inside = seg_start <= current < (seg_end - margin)
        prev_t = state.get("last_t")

        if not inside:
            state["inside"] = False
            state["shown"] = False
            state["last_t"] = current
            return False

        reentered = (not state["inside"])
        if prev_t is not None and current + margin < prev_t:
            reentered = True

        if reentered:
            state["shown"] = False

        state["inside"] = True
        state["last_t"] = current

        if state["shown"]:
            return False

        state["shown"] = True
        return True

    def _dispatch_segment(self, seg_type, start, end, offset, ends_at_media_end):
        """Auto-skip, fire Playing Next, or show the Skip overlay for a segment."""
        target = end + offset
        src = self._skip_handler.sources.get(seg_type, "?")

        if self._skip_auto.get(seg_type, False):
            # credits/preview at end-of-media with auto-skip on → trigger Playing Next silently
            if seg_type in ("credits", "preview") and ends_at_media_end:
                if self.dialogs_enabled and not self.dialogs_triggered:
                    g.set_runtime_setting("anime.skipOutroEnd", str(int(end)))
                    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runPlayerDialogs")')
                    self.dialogs_triggered = True
                    g.log(f"Skip: auto-triggered Playing Next from {seg_type} ({src})", "debug")
            else:
                self.seekTime(target)
                g.log(f"Skip: auto-skipped {seg_type} ({src}) → {target}s", "debug")
            return

        # credits/preview that run to the end of media → use Playing Next dialog
        if seg_type in ("credits", "preview") and ends_at_media_end:
            if self.dialogs_enabled and not self.dialogs_triggered:
                g.set_runtime_setting("anime.skipOutroEnd", str(int(end)))
                xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=runPlayerDialogs")')
                self.dialogs_triggered = True
                g.log(f"Skip: triggered Playing Next from {seg_type} ({src})", "debug")
            return

        # Otherwise show the Skip overlay (intro/recap, or mid-file credits/preview)
        g.set_runtime_setting("seren.skipSegmentEnd", str(int(target)))
        g.set_runtime_setting("seren.skipSegmentType", seg_type)
        xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=showSkipIntro")')
        g.log(f"Skip: showing {seg_type} overlay (target={target}s, src={src})", "debug")

    def _handle_pre_scrape(self):
        if self.pre_scrape_enabled and not self.pre_scrape_initiated:
            self.smart_module.pre_scrape()
            self.pre_scrape_initiated = True

    def _try_get_bookmark(self):
        bm = self.bookmark_sync.get_bookmark(self.trakt_id)
        self.offset = bm.get("resumeTime") if bm else None

    def _handle_bookmark(self):
        try:
            g.clear_kodi_bookmarks()
        except Exception:
            g.log_stacktrace()
        try:
            if self.current_time == 0 or self.total_time == 0:
                self.bookmark_sync.remove_bookmark(self.trakt_id)
                return

            if self.watched_percentage < self.playCountMinimumPercent and self.current_time >= self.ignoreSecondsAtStart:
                self.bookmark_sync.set_bookmark(
                    self.trakt_id,
                    int(self.current_time),
                    self.mediatype,
                    self.watched_percentage,
                )
            else:
                self.bookmark_sync.remove_bookmark(self.trakt_id)
        except Exception:
            g.log("_handle_bookmark: DB unavailable at teardown — skipping bookmark sync", "warning")

    def _is_file_playing(self):
        if not self.playback_started or self._playback_has_stopped() or self._running_path is None:
            return False

        return self.isPlayingVideo()


class PlayerDialogs(xbmc.Player):
    """
    Handles dialogs that appear over playing items
    """

    def __init__(self):
        super().__init__()
        self._min_time = g.get_int_setting("playingnext.time")
        self.playing_file = None

    def display_dialog(self):
        """
        Handles the initiating of dialogs and deciding which dialog to display if required
        :return: None
        :rtype: None
        """
        try:
            self.playing_file = self.getPlayingFile()
        except RuntimeError:
            g.log("Kodi did not return a playing file, killing playback dialogs", "error")
            return
        if g.PLAYLIST.size() > 0 and g.PLAYLIST.getposition() != (g.PLAYLIST.size() - 1):
            if g.get_bool_setting("smartplay.stillwatching") and self._still_watching_calc():
                target = self._show_still_watching
            elif g.get_bool_setting("smartplay.playingnextdialog"):
                target = self._show_playing_next
            else:
                return

            if self.playing_file != self.getPlayingFile():
                return

            if not self.isPlayingVideo():
                return

            if not self._is_video_window_open():
                return

            target()

    @staticmethod
    def _still_watching_calc():
        calculation = float(g.PLAYLIST.getposition() + 1) / g.get_float_setting("stillwatching.numepisodes")

        return False if calculation == 0 else calculation.is_integer()

    def _show_playing_next(self):
        from resources.lib.gui.windows.playing_next import PlayingNext
        from resources.lib.database.skinManager import SkinManager

        try:
            window = PlayingNext(
                *SkinManager().confirm_skin_path("playing_next.xml"),
                item_information=self._get_next_item_item_information(),
            )
            window.doModal()
        finally:
            del window

    def _show_still_watching(self):
        from resources.lib.gui.windows.still_watching import StillWatching
        from resources.lib.database.skinManager import SkinManager

        try:
            window = StillWatching(
                *SkinManager().confirm_skin_path("still_watching.xml"),
                item_information=self._get_next_item_item_information(),
            )
            window.doModal()
        finally:
            del window

    @staticmethod
    def _get_next_item_item_information():
        current_position = g.PLAYLIST.getposition()
        url = g.PLAYLIST[current_position + 1].getPath()  # pylint: disable=unsubscriptable-object
        params = dict(parse.parse_qsl(parse.unquote(url.split("?")[1])))
        return tools.get_item_information(tools.deconstruct_action_args(params.get("action_args")))

    @staticmethod
    def _is_video_window_open():
        return xbmcgui.getCurrentWindowId() == 12005


def show_skip_intro_dialog():
    """Module-level function called via RunPlugin to show the Skip overlay.

    Reads the segment end-time and type from runtime settings and forwards them
    to the SkipIntro window so it can render the correct button label.
    """
    try:
        # Prefer new generic key; fall back to legacy anime-only key for compatibility.
        skip_end = g.get_runtime_setting("seren.skipSegmentEnd")
        seg_type = g.get_runtime_setting("seren.skipSegmentType") or "intro"
        if not skip_end:
            skip_end = g.get_runtime_setting("anime.skipIntroEnd")
            seg_type = "intro"
        if not skip_end:
            return
        skip_end = int(float(skip_end))
        g.clear_runtime_setting("seren.skipSegmentEnd")
        g.clear_runtime_setting("seren.skipSegmentType")
        g.clear_runtime_setting("anime.skipIntroEnd")

        from resources.lib.database.skinManager import SkinManager
        from resources.lib.gui.windows.skip_intro import SkipIntro

        window = SkipIntro(
            *SkinManager().confirm_skin_path("skip_intro.xml"),
            skip_end=skip_end,
            segment_type=seg_type,
        )
        window.doModal()
        del window
    except Exception:
        g.log_stacktrace()
