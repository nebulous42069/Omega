"""Universal Playback Watchdog

Monitors actual playback after source resolution. If a stream stalls
(getTime() stops advancing), automatically stops and cycles to the next
source. Works for all source types: Easynews direct, Premiumize CDN,
Real-Debrid, TorBox, AllDebrid, hosters, etc.

Architecture:
  - Replaces resolve_silent_or_visible() + play_source() when enabled
  - Contains its own resolve loop (reuses Resolver.resolve_single_source)
  - Reuses ContentVerifier for content mismatch detection
  - Reuses CloudMiss detection with same runtime flags
  - Uses xbmc.Player().play() instead of setResolvedUrl for retry capability
  - On success: returns (stream_link, release_title) — caller attaches SerenPlayer
  - On failure: returns (None, None) — caller handles rescrape/fallback

Integration:
  - Router.getSources action (autoplay path only, not source select)
  - Controlled by playback.watchdog setting (default off)
  - Sets cloud_miss_rescrape / content_verify_rescrape flags for router rescrape
"""

import copy
import importlib
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.modules.globals import g
from resources.lib.modules.resolver import Resolver
from resources.lib.modules.resolver.content_verifier import ContentVerifier


class PlaybackWatchdog(xbmc.Player):
    """Stall-detecting playback manager.

    Resolves sources one at a time, plays each via xbmc.Player().play(),
    monitors getTime() for progress, and automatically retries the next
    source if the stream stalls.
    """

    def __init__(self):
        super().__init__()
        self.stall_timeout = g.get_int_setting("watchdog.stallTimeout", 10)
        self.monitor_window = g.get_int_setting("watchdog.monitorWindow", 30)
        self.max_retries = g.get_int_setting("watchdog.maxRetries", 3)

        # Playback state — set by Kodi callbacks
        self._playback_error = False
        self._playback_stopped = False
        self._user_stopped = False  # True only when user explicitly stopped (backspace/stop)
        self.user_stopped_early = False  # Public: caller can check if user stopped during retry
        self._monitor = xbmc.Monitor()

        # AV change tracking — fires when subtitle/audio streams change
        self._last_av_change = 0.0

        # Detect subtitle services so we can wait for them to finish.
        # Gated on user setting — some setups have subtitle services that
        # are fast enough to not need the extended settle window.
        self._subtitle_detection = (
            g.get_bool_setting("watchdog.subtitleDetection", False)
            and self._detect_subtitle_service()
        )

    @staticmethod
    def _detect_subtitle_service():
        """Check if a subtitle service addon is installed and enabled."""
        for addon_id in (
            "service.subtitles.a4ksubtitles",
            "service.subtitles.opensubtitles",
            "service.subtitles.subscene",
        ):
            try:
                xbmcaddon.Addon(addon_id)
                g.log(f"Watchdog: Detected subtitle service '{addon_id}'", "info")
                return True
            except Exception:
                continue
        return False

    # ── Kodi player callbacks ──────────────────────────────────────────────

    def onAVChange(self):
        self._last_av_change = time.time()

    def onPlayBackError(self):
        self._playback_error = True

    def onPlayBackStopped(self):
        self._playback_stopped = True
        self._user_stopped = True  # Explicit stop — backspace, stop button, or OS signal

    def onPlayBackEnded(self):
        self._playback_stopped = True

    # ── Main entry point ───────────────────────────────────────────────────

    def attempt_playback(self, sources, item_information, pack_select=False, resume_time=None):
        """Resolve sources with playback stall detection.

        Iterates through sources, resolves each, verifies content, plays it,
        and monitors for stalls. On stall, stops and tries the next source.

        Args:
            sources: Sorted list of source dicts
            item_information: Metadata on the item to play
            pack_select: Force manual file selection if True
            resume_time: Seek position in seconds (from bookmark) or None

        Returns:
            (stream_link, release_title) on success — stream is already playing
            (None, None) if all sources failed or retries exhausted
        """
        self._resume_time = float(resume_time) if resume_time else None
        resolver = Resolver()
        verifier = ContentVerifier(item_information, sources)
        attempts = 0
        cloud_miss_count = 0
        cloud_miss_threshold = g.get_int_setting("general.cloudMissThreshold", 3)
        failed_titles = set()  # Skip same release on different debrid after failure

        g.log(
            f"Watchdog: Starting with {len(sources)} sources, "
            f"max {self.max_retries} retries, "
            f"stall timeout {self.stall_timeout}s, "
            f"monitor window {self.monitor_window}s",
            "info",
        )

        for source in sources:
            if attempts >= self.max_retries:
                g.log(
                    f"Watchdog: Max retries ({self.max_retries}) reached, giving up",
                    "warning",
                )
                break

            if self._monitor.abortRequested():
                break

            # Skip sources with same release title as a previously failed
            # attempt — if a file stalled on Premiumize, the same file on
            # Real-Debrid will likely have the same problem.
            src_title = source.get("release_title", "")
            if src_title and src_title in failed_titles:
                continue

            # ── Resolve ────────────────────────────────────────────────────
            try:
                stream_link, release_title = resolver.resolve_single_source(
                    source, item_information, pack_select
                )
            except Exception:
                g.log_stacktrace()
                continue

            # ── Cloud miss detection ───────────────────────────────────────
            if stream_link is None and source.get("_cloud_miss"):
                cloud_miss_count += 1
                g.log(
                    f"Watchdog: Cloud miss {cloud_miss_count}/{cloud_miss_threshold}: "
                    f"{source.get('debrid_provider', '?')} no longer has "
                    f"{source.get('release_title', 'N/A')}",
                    "warning",
                )
                if cloud_miss_count >= cloud_miss_threshold:
                    g.set_runtime_setting("cloud_miss_rescrape", "true")
                    break
                continue

            if not stream_link:
                continue

            # ── Content verification ───────────────────────────────────────
            if not verifier.verify(source, release_title):
                g.log(
                    f"Watchdog: Content mismatch — "
                    f"'{release_title or source.get('release_title', 'N/A')}'",
                    "warning",
                )
                stream_link = None
                if verifier.should_rescrape():
                    g.set_runtime_setting("content_verify_rescrape", "true")
                    break
                continue

            # ── Play and monitor ───────────────────────────────────────────
            attempts += 1
            g.log(
                f"Watchdog: Attempt {attempts}/{self.max_retries} — "
                f"'{source.get('release_title', 'N/A')}' "
                f"[{source.get('quality', '?')}] "
                f"via {source.get('debrid_provider', source.get('provider', '?'))}",
                "info",
            )

            result = self._try_play(stream_link, source, item_information)

            if result == "success":
                g.log(
                    f"Watchdog: Playback committed after {attempts} attempt(s)",
                    "info",
                )
                return stream_link, release_title

            if result == "stall":
                failed_titles.add(src_title)
                g.log(
                    f"Watchdog: Stall on attempt {attempts}, "
                    f"blacklisting '{src_title}', cycling to next source",
                    "warning",
                )
                xbmcgui.Dialog().notification(
                    g.ADDON_NAME,
                    "Stream stalled — trying next source...",
                    time=3000,
                )
                continue

            # "error" — playback never started OR user explicitly stopped.
            if self._user_stopped:
                self.user_stopped_early = True
                g.log("Watchdog: User stopped playback — exiting retry loop", "info")
                return None, None

            failed_titles.add(src_title)
            g.log(
                f"Watchdog: Playback error on attempt {attempts}, "
                f"blacklisting '{src_title}'",
                "warning",
            )
            continue

        return None, None

    # ── Playback attempt ───────────────────────────────────────────────────

    def _try_play(self, stream_link, source, item_information):
        """Play a stream and monitor for stalls.

        Returns:
            "success" — stream is playing and progressing normally
            "stall"   — stream started but getTime() stopped advancing
            "error"   — stream never started or Kodi reported an error
        """
        # Reset state
        self._playback_error = False
        self._playback_stopped = False
        self._user_stopped = False
        self._last_av_change = time.time()

        # Build ListItem
        listitem = self._build_listitem(stream_link, source, item_information)

        # Add to Kodi playlist so SerenPlayer's smart playlist logic
        # sees size==1 and can build the binge-watch queue
        g.PLAYLIST.clear()
        g.PLAYLIST.add(stream_link, listitem)

        # Play from playlist via xbmc.Player (NOT setResolvedUrl)
        self.play(g.PLAYLIST)

        # Wait for playback to actually start by polling isPlayingVideo().
        # We do NOT rely on onAVStarted callbacks — they may not route to
        # this Player instance when the plugin context has been cancelled.
        playback_started = False
        for _ in range(40):  # 40 × 0.5s = 20s max wait
            if self._monitor.waitForAbort(0.5):
                return "error"
            if self._playback_error or self._playback_stopped:
                return "error"
            if self.isPlayingVideo():
                try:
                    t = self.getTime()
                    if t >= 0:
                        playback_started = True
                        break
                except Exception:
                    pass

        if not playback_started:
            g.log("Watchdog: Playback never started within 20s", "warning")
            self._safe_stop()
            return "error"

        g.log(
            f"Watchdog: Playback confirmed at {self.getTime():.1f}s",
            "info",
        )

        # Close all Seren overlay windows (persistent_background, get_sources)
        # so the video is visible during the monitoring window
        g.close_busy_dialog()
        g.close_all_dialogs()

        # Seek to resume position BEFORE monitoring starts — so the user
        # sees the correct position immediately, not 30s from the beginning.
        if self._resume_time and self._resume_time > 0:
            try:
                self.seekTime(self._resume_time)
                g.log(
                    f"Watchdog: Seeked to resume position {self._resume_time:.0f}s",
                    "info",
                )
            except Exception as e:
                g.log(f"Watchdog: Seek failed: {e}", "warning")

        # Wait for playback to settle after seek + subtitle loading before
        # starting the stall monitor. This prevents false stall detection
        # from seek rebuffering or a4kSubtitles loading external subs.
        if not self._wait_for_settle():
            self._safe_stop()
            return "error"

        # Playback settled — monitor for stalls during the monitoring window
        return self._monitor_playback()

    def _wait_for_settle(self):
        """Wait for playback to stabilize after seek and subtitle loading.

        Two conditions must be met before the stall monitor starts:
        1. Seek settled (if a seek was performed): getTime() reports a
           position within 30s of the resume target AND is advancing.
           This prevents false settle when getTime() returns 0.0 before
           Kodi has processed the seek.
        2. AV settled: no onAVChange callbacks for a quiet period.
           When a subtitle service (e.g. a4kSubtitles) selects or downloads
           subtitles, Kodi fires onAVChange. We wait for these to stop
           before starting the stall monitor. If a subtitle service is
           detected, we use a longer quiet period and timeout to give it
           time to finish searching providers and downloading.

        Returns True when settled, False if playback died during settle.
        """
        # Subtitle services like a4kSubtitles can take 20-60s to search
        # multiple providers and download. Use longer timeouts when detected.
        if self._subtitle_detection:
            settle_timeout = 30
            av_quiet_threshold = 5.0
        else:
            settle_timeout = 15
            av_quiet_threshold = 2.0

        settle_start = time.time()
        last_time = -1.0
        seek_settled = not bool(self._resume_time)  # Skip seek check if no resume
        seek_target = float(self._resume_time) if self._resume_time else 0.0
        seek_position_ok = False  # getTime() is near the resume target

        g.log(
            f"Watchdog: Waiting for playback to settle... "
            f"(subtitle_detection={self._subtitle_detection}, "
            f"av_quiet={av_quiet_threshold}s, timeout={settle_timeout}s)",
            "info",
        )

        while time.time() - settle_start < settle_timeout:
            if self._monitor.waitForAbort(0.5):
                return False
            if self._playback_error or self._playback_stopped:
                return False
            if not self.isPlayingVideo():
                return False

            # ── Check seek settled ─────────────────────────────────────
            try:
                current = self.getTime()
            except Exception:
                continue

            if not seek_settled:
                # First check: is getTime() reporting a position near the
                # seek target? Before Kodi processes the seek, getTime()
                # returns 0.0 or the pre-seek position.
                if not seek_position_ok:
                    if abs(current - seek_target) <= 30:
                        seek_position_ok = True
                        last_time = current
                    continue  # Keep waiting for position to reach target

                # Second check: is getTime() advancing from the new position?
                if current > last_time + 0.3:
                    seek_settled = True
                    g.log(
                        f"Watchdog: Seek settled at {current:.1f}s "
                        f"(target was {seek_target:.0f}s)",
                        "info",
                    )
                last_time = current
                continue  # Don't check AV until seek is done

            # ── Check AV changes have quieted ──────────────────────────
            # onAVChange fires whenever subtitle/audio streams are added,
            # removed, or selected — by Kodi itself or subtitle services.
            time_since_av = time.time() - self._last_av_change
            if time_since_av >= av_quiet_threshold:
                g.log(
                    f"Watchdog: Settled — seek done, no AV changes "
                    f"for {time_since_av:.1f}s "
                    f"(total settle: {time.time() - settle_start:.1f}s)",
                    "info",
                )
                return True

            last_time = current

        # Timed out — proceed anyway (better than blocking forever)
        g.log(
            f"Watchdog: Settle timeout ({settle_timeout}s) — proceeding with monitoring",
            "warning",
        )
        return True

    def _monitor_playback(self):
        """Watch getTime() for stalls during the monitoring window.

        Returns "success" if playback progresses normally through the
        monitoring window, "stall" if getTime() doesn't advance for
        stall_timeout seconds, "error" if playback stops unexpectedly.

        AV changes from subtitle services (stream selection, subtitle
        download) can cause brief rebuffers. If an onAVChange fired
        recently, we forgive the stall rather than cycling sources.
        """
        monitor_start = time.time()
        last_time = -1.0
        stall_start = None

        while not self._monitor.abortRequested():
            if self._playback_error or self._playback_stopped:
                return "error"

            if not self.isPlayingVideo():
                return "error"

            # Check if we've passed the monitoring window
            elapsed = time.time() - monitor_start
            if elapsed >= self.monitor_window:
                return "success"

            # Check playback progress
            try:
                current = self.getTime()
            except Exception:
                return "error"

            if current > last_time + 0.5:
                # Time is advancing — playback is healthy
                last_time = current
                stall_start = None
            else:
                # Time not advancing — but if subtitle detection is on and
                # a subtitle service just triggered an AV change, forgive
                # the brief pause rather than counting it as a stall.
                if self._subtitle_detection:
                    time_since_av = time.time() - self._last_av_change
                    if time_since_av < 3.0:
                        stall_start = None
                        if self._monitor.waitForAbort(0.5):
                            return "error"
                        continue

                if stall_start is None:
                    stall_start = time.time()
                elif time.time() - stall_start >= self.stall_timeout:
                    # Stalled for too long
                    g.log(
                        f"Watchdog: Stream stalled for {self.stall_timeout}s "
                        f"at position {current:.1f}s",
                        "warning",
                    )
                    self._safe_stop()
                    return "stall"

            if self._monitor.waitForAbort(0.5):
                return "error"

        return "error"

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _safe_stop(self):
        """Stop playback, suppressing errors if already stopped."""
        try:
            if self.isPlaying():
                self.stop()
            xbmc.sleep(500)
        except Exception:
            pass

    @staticmethod
    def _build_listitem(stream_link, source, item_information):
        """Build a Kodi ListItem with metadata for OSD display.

        Handles both direct URL strings and adaptive source dicts.
        """
        info = copy.deepcopy(item_information.get("info", {}))
        g.clean_info_keys(info)
        g.convert_info_dates(info)

        if isinstance(stream_link, dict) and stream_link.get("type") == "adaptive":
            if g.ADDON_USERDATA_PATH not in sys.path:
                sys.path.append(g.ADDON_USERDATA_PATH)
            provider = stream_link["provider_imports"]
            provider_module = importlib.import_module(f"{provider[0]}.{provider[1]}")
            if not hasattr(provider_module, "get_listitem") and hasattr(
                provider_module, "sources"
            ):
                provider_module = provider_module.sources()
            item = provider_module.get_listitem(stream_link)
            item.setInfo("video", info)
        else:
            item = xbmcgui.ListItem(path=stream_link)
            info["FileNameAndPath"] = stream_link
            item.setInfo("video", info)
            item.setProperty("IsPlayable", "true")

        art = item_information.get("art", {})
        item.setArt(art if isinstance(art, dict) else {})
        cast = item_information.get("cast", [])
        item.setCast(cast if isinstance(cast, list) else [])
        item.setUniqueIDs(
            {i.split("_")[0]: info[i] for i in info if i.endswith("id")},
        )
        return item
