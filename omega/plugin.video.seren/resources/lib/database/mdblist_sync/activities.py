from functools import cached_property

import xbmc

from resources.lib.database import mdblist_sync
from resources.lib.modules.exceptions import ActivitySyncFailure
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g


class MDBListSyncDatabase(mdblist_sync.MDBListSyncDatabase):
    def __init__(self):
        super().__init__()

    @cached_property
    def mdblist_api(self):
        from resources.lib.indexers.mdblist import MDBListAPI

        return MDBListAPI()

    def _update_activity_record(self, record, value):
        self.execute_sql(f"UPDATE activities SET {record}=? WHERE sync_id=1", (value,))

    def sync_activities(self):
        with GlobalLock("mdblist.sync"):
            if not g.get_setting("mdblist.apikey"):
                g.log("MDBListSync: No MDBList auth present, no sync will occur", "warning")
                return

            self.refresh_activities()
            remote_activities = self.mdblist_api.get_json("sync/last_activities")
            if not remote_activities:
                g.log("MDBList Activities Sync Failure: unable to connect to MDBList", "error")
                return True

            update_time = self._get_datetime_now()
            watched_count = 0
            playback_count = 0

            watched_stale = self.requires_update(
                remote_activities.get("watched_at") or self.base_date, self.activities["watched_at"]
            )
            episode_watched_stale = self.requires_update(
                remote_activities.get("episode_watched_at") or self.base_date,
                self.activities["episode_watched_at"],
            )
            if watched_stale or episode_watched_stale:
                try:
                    watched_count = self._sync_watched()
                    self._update_activity_record("watched_at", update_time)
                    self._update_activity_record("episode_watched_at", update_time)
                except ActivitySyncFailure as e:
                    g.log(f"Failed to sync MDBList watched status: {e}", "error")

            playback_remote = max(
                remote_activities.get("paused_at") or self.base_date,
                remote_activities.get("episode_paused_at") or self.base_date,
            )
            if self.requires_update(playback_remote, self.activities["playback_at"]):
                try:
                    playback_count = self._sync_playback()
                    self._update_activity_record("playback_at", update_time)
                except ActivitySyncFailure as e:
                    g.log(f"Failed to sync MDBList playback: {e}", "error")

            g.notification(g.ADDON_NAME, g.get_language_string(30953).format(watched_count, playback_count))
            xbmc.executebuiltin('RunPlugin("plugin://plugin.video.seren/?action=widgetRefresh&playing=False")')

    def _sync_watched(self):
        """Pulls GET /sync/watched (cursor-paginated). Movies section is
        currently always empty per MDBList's own documented gap, but the
        insert path is kept schema-complete for when that changes."""
        total = 0
        cursor = None
        self.execute_sql("UPDATE episodes SET watched=0")
        try:
            while True:
                params = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor
                page = self.mdblist_api.get_json("sync/watched", **params)
                if not page:
                    break

                movies = page.get("movies") or []
                episodes = page.get("episodes") or []

                if movies:
                    movie_rows = [
                        (m["ids"]["tmdb"], m["ids"].get("imdb"), m.get("last_watched_at"))
                        for m in movies
                        if m.get("ids", {}).get("tmdb")
                    ]
                    if movie_rows:
                        self.execute_sql(
                            "REPLACE INTO movies (tmdb_id, imdb_id, watched, last_watched_at) VALUES (?, ?, 1, ?)",
                            movie_rows,
                        )
                    total += len(movie_rows)

                if episodes:
                    episode_rows = [
                        (
                            e["episode"]["show"]["ids"]["tmdb"],
                            e["episode"]["season"],
                            e["episode"]["number"],
                            e.get("last_watched_at"),
                        )
                        for e in episodes
                        if e.get("episode", {}).get("show", {}).get("ids", {}).get("tmdb")
                    ]
                    if episode_rows:
                        self.execute_sql(
                            "REPLACE INTO episodes (show_tmdb_id, season, number, watched, last_watched_at) "
                            "VALUES (?, ?, ?, 1, ?)",
                            episode_rows,
                        )
                    total += len(episode_rows)

                pagination = page.get("pagination") or {}
                if pagination.get("has_more") and pagination.get("next_cursor"):
                    cursor = pagination["next_cursor"]
                else:
                    break
        except Exception as e:
            raise ActivitySyncFailure(e) from e
        return total

    def _sync_playback(self):
        """Pulls GET /sync/playback (flat array, not paginated per the
        live-confirmed response for accounts of this size)."""
        try:
            entries = self.mdblist_api.get_json("sync/playback") or []
            if isinstance(entries, dict):
                entries = entries.get("items") or []

            rows = []
            for entry in entries:
                progress = entry.get("progress")
                runtime = entry.get("runtime")
                if progress is None or runtime is None:
                    continue
                try:
                    percent = float(progress)
                    resume_time = round(percent / 100 * float(runtime) * 60)
                except (TypeError, ValueError):
                    continue
                paused_at = entry.get("paused_at")
                media_type = entry.get("type")

                if media_type == "movie":
                    movie = entry.get("movie") or {}
                    tmdb_id = movie.get("ids", {}).get("tmdb")
                    if not tmdb_id:
                        continue
                    rows.append((tmdb_id, None, None, "movie", str(percent), str(resume_time), paused_at))
                elif media_type == "episode":
                    episode = entry.get("episode") or {}
                    show = entry.get("show") or {}
                    tmdb_id = show.get("ids", {}).get("tmdb")
                    season = episode.get("season")
                    number = episode.get("number")
                    if not tmdb_id or season is None or number is None:
                        continue
                    rows.append((tmdb_id, season, number, "episode", str(percent), str(resume_time), paused_at))

            self.execute_sql("DELETE FROM bookmarks")
            if rows:
                self.execute_sql(
                    "INSERT INTO bookmarks (tmdb_id, season, number, media_type, percent_played, "
                    "resume_time, paused_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                    rows,
                )
            return len(rows)
        except Exception as e:
            raise ActivitySyncFailure(e) from e
