"""Unified skip-segment orchestrator.

Routes to the appropriate data source based on content type:
- Anime episodes  → AniSkip + Anime-Skip (existing clients in modules/anime/)
- TV episodes     → TheIntroDB
- Movies          → TheIntroDB

Anime falls back to TheIntroDB if both AniSkip and Anime-Skip return nothing —
TheIntroDB does have community submissions for popular anime via TMDB ids.

The handler runs lookups in a background thread and exposes a unified
`segments` dict with up to four keys (intro/recap/credits/preview), each
mapping to the best segment as `(start, end)` in seconds. `end` may be None
for credits/preview when the segment runs to the end of the media.
"""

import threading

from resources.lib.modules.globals import g


class SkipHandler:
    """Background-loaded skip-segment lookup for a single playback session.

    Usage:
        handler = SkipHandler(item_information, episode_number)
        handler.start()
        # ... in playback loop:
        if handler.ready:
            intro = handler.segments.get("intro")  # (start, end) or None
            credits = handler.segments.get("credits")  # (start, end) or None
            ...
    """

    def __init__(self, item_information, episode_number=None):
        self.item_information = item_information or {}
        try:
            self.episode_number = int(episode_number) if episode_number else 0
        except (TypeError, ValueError):
            self.episode_number = 0

        # Unified result map. Each value is (start, end) in seconds, end may be None.
        self.segments = {}

        # Per-segment data source label (for diagnostics): "aniskip" | "anime_skip" | "theintrodb"
        self.sources = {}

        self.ready = False
        self._thread = None
        self._info = self.item_information.get("info", {}) or {}
        self.is_anime = self._detect_anime()
        self.is_movie = self._info.get("mediatype") == g.MEDIA_MOVIE

    def start(self):
        """Spawn the background lookup thread."""
        self._thread = threading.Thread(target=self._resolve, daemon=True)
        self._thread.start()

    def wait(self, timeout=5):
        """Block until lookup completes or timeout elapses."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    # --- Backwards compatibility shims (anime/skip_handler.py interface) ---

    @property
    def intro_times(self):
        """Tuple (start, end) or None — preserved for legacy callers."""
        return self.segments.get("intro")

    @property
    def outro_times(self):
        """Tuple (start, end) or None — anime 'outro' maps to 'credits'."""
        return self.segments.get("credits")

    @property
    def source(self):
        """First source that produced data, or None."""
        for seg_type in ("intro", "credits", "recap", "preview"):
            src = self.sources.get(seg_type)
            if src:
                return src
        return None

    # --- Internals ---

    def _detect_anime(self):
        """Same heuristic used by anilist_mapping.get_anime_ids_for_item."""
        genres = self._info.get("genre") or []
        if not isinstance(genres, list):
            genres = [genres] if genres else []
        if any("anime" in str(item).lower() for item in genres):
            return True
        country = str(self._info.get("country_origin") or "").upper()
        has_animation = any("animation" in str(item).lower() for item in genres)
        if has_animation and country in ("JP", "JPN", "JAPAN"):
            return True
        return False

    def _resolve(self):
        try:
            if self.is_anime and self.episode_number:
                self._resolve_anime()
                # If anime APIs found nothing, try TheIntroDB as a third source
                if not self.segments:
                    self._resolve_theintrodb()
            else:
                self._resolve_theintrodb()

            if self.segments:
                summary = ", ".join(
                    f"{k}={self.sources.get(k, '?')}" for k in self.segments
                )
                g.log(f"SkipHandler: resolved [{summary}]", "debug")
            else:
                g.log("SkipHandler: no skip data available", "debug")

        except Exception as e:
            g.log(f"SkipHandler error: {e}", "warning")
        finally:
            self.ready = True

    def _resolve_anime(self):
        """Existing AniSkip + Anime-Skip path. Maps anime intro→intro, ed→credits."""
        try:
            from resources.lib.modules.anime.anilist_mapping import get_anime_ids_for_item

            anime_ids = get_anime_ids_for_item(self.item_information)
            if not anime_ids:
                return

            mal_id = anime_ids.get("mal_id")
            anilist_id = anime_ids.get("anilist_id")

            if mal_id:
                self._try_aniskip(mal_id)

            if anilist_id and ("intro" not in self.segments or "credits" not in self.segments):
                self._try_anime_skip(anilist_id)

        except Exception as e:
            g.log(f"SkipHandler anime resolve error: {e}", "debug")

    def _try_aniskip(self, mal_id):
        try:
            from resources.lib.modules.anime.aniskip import get_intro_times, get_outro_times

            i_start, i_end = get_intro_times(mal_id, self.episode_number)
            if i_start is not None and i_end is not None and "intro" not in self.segments:
                self.segments["intro"] = (i_start, i_end)
                self.sources["intro"] = "aniskip"

            o_start, o_end = get_outro_times(mal_id, self.episode_number)
            if o_start is not None and o_end is not None and "credits" not in self.segments:
                self.segments["credits"] = (o_start, o_end)
                self.sources["credits"] = "aniskip"

        except Exception as e:
            g.log(f"AniSkip lookup failed: {e}", "debug")

    def _try_anime_skip(self, anilist_id):
        try:
            from resources.lib.modules.anime.anime_skip import get_skip_times

            result = get_skip_times(anilist_id, self.episode_number)
            if not result:
                return

            if "intro" not in self.segments and "intro" in result:
                self.segments["intro"] = (result["intro"]["start"], result["intro"]["end"])
                self.sources["intro"] = "anime_skip"

            if "credits" not in self.segments and "outro" in result:
                self.segments["credits"] = (result["outro"]["start"], result["outro"]["end"])
                self.sources["credits"] = "anime_skip"

        except Exception as e:
            g.log(f"Anime-Skip lookup failed: {e}", "debug")

    def _resolve_theintrodb(self):
        """Movies and TV episodes go through TheIntroDB."""
        try:
            from resources.lib.modules.skip.theintrodb import query_segments

            tmdb_id = self._info.get("tmdb_id") or self._info.get("tmdb_show_id")
            imdb_id = self._info.get("imdb_id")
            season = self._info.get("season") if not self.is_movie else None
            episode = self.episode_number if not self.is_movie else None

            if not tmdb_id and not imdb_id:
                g.log("SkipHandler: no TMDB or IMDb id available", "debug")
                return

            api_key = (g.get_setting("skip.theIntroDbApiKey") or "").strip() or None

            # duration in info is Kodi seconds; v3 API takes milliseconds
            duration_sec = self._info.get("duration")
            try:
                duration_ms = int(duration_sec) * 1000 if duration_sec else None
            except (TypeError, ValueError):
                duration_ms = None

            data = query_segments(
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                season=season,
                episode=episode,
                is_movie=self.is_movie,
                api_key=api_key,
                duration_ms=duration_ms,
            )
            if not data:
                return

            for seg_type in ("intro", "recap", "credits", "preview"):
                if seg_type in self.segments:
                    continue  # don't override anime API data
                segments = data.get(seg_type) or []
                if not segments:
                    continue
                best = segments[0]
                start = best.get("start") if best.get("start") is not None else 0.0
                end = best.get("end")  # may be None for credits/preview
                self.segments[seg_type] = (start, end)
                self.sources[seg_type] = "theintrodb"

        except Exception as e:
            g.log(f"TheIntroDB lookup failed: {e}", "debug")
