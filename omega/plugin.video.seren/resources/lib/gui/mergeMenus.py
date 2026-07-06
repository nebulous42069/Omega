from functools import cached_property

from resources.lib.modules.globals import g


class Menus:
    """Merged Trakt + MDBList menus (Merge - In-Progress, Merge - Watched).

    v1 known limitation: if Trakt's scrobbler no-ops on a stop event that
    MDBList's scrobbler correctly records, an item can be watched=1 on
    MDBList while still carrying a stale Trakt in-progress bookmark for a
    different episode of the same show. It will appear in both
    Merge-Watched and Merge-In-Progress simultaneously. Not solved in v1.
    """

    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")

    @cached_property
    def movies_database(self):
        from resources.lib.database.trakt_sync.movies import TraktSyncDatabase

        return TraktSyncDatabase()

    @cached_property
    def shows_database(self):
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase

        return TraktSyncDatabase()

    @cached_property
    def bookmark_database(self):
        from resources.lib.database.trakt_sync.bookmark import TraktSyncDatabase as BookmarkDatabase

        return BookmarkDatabase()

    @cached_property
    def mdblist_menus(self):
        from resources.lib.gui.mdblistMenus import Menus as MDBListMenus

        return MDBListMenus()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder

        return ListBuilder()

    @staticmethod
    def _merge_by_key(trakt_rows, trakt_key_fn, trakt_ts_fn, mdb_resolved, mdb_key_fn, mdb_ts_by_key):
        merged = {}
        for r in trakt_rows:
            key = trakt_key_fn(r)
            if key is None:
                continue
            merged[key] = (trakt_ts_fn(r) or "", r)
        for obj in mdb_resolved:
            key = mdb_key_fn(obj)
            if key is None:
                continue
            ts = mdb_ts_by_key.get(key) or ""
            existing = merged.get(key)
            if existing is None or ts > existing[0]:
                merged[key] = (ts, obj)
        return [row for _, row in sorted(merged.values(), key=lambda pair: pair[0], reverse=True)]

    def watched_movies(self):
        trakt_rows = self.movies_database.get_watched_movies(1, force_all=True)
        mdb_rows = self.mdblist_menus.mdblist_database.get_recent_movies(self.page_limit, force_all=True)
        mdb_ts_by_tmdb = {row["tmdb_id"]: row["last_watched_at"] for row in mdb_rows}
        resolved = self.mdblist_menus._resolve([row["tmdb_id"] for row in mdb_rows], "movie")

        trakt_list = self._merge_by_key(
            trakt_rows,
            lambda r: r.get("tmdb_id"),
            lambda r: r.get("last_watched_at"),
            resolved,
            lambda obj: obj.get("tmdb_id"),
            mdb_ts_by_tmdb,
        )
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True, hide_watched=False)

    def watched_shows(self):
        trakt_rows = self.shows_database.get_recently_watched_shows(force_all=True)
        mdb_rows = self.mdblist_menus.mdblist_database.get_recent_shows(self.page_limit, force_all=True)
        mdb_ts_by_tmdb = {row["tmdb_id"]: row["last_watched_at"] for row in mdb_rows}
        resolved = self.mdblist_menus._resolve([row["tmdb_id"] for row in mdb_rows], "show")

        trakt_list = self._merge_by_key(
            trakt_rows,
            lambda r: r.get("tmdb_id"),
            lambda r: r.get("lw"),
            resolved,
            lambda obj: obj.get("tmdb_id"),
            mdb_ts_by_tmdb,
        )
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(
            trakt_list, no_paging=True, hide_watched=False, content_type_override=g.CONTENT_MENU
        )

    def in_progress_movies(self):
        trakt_rows = self.bookmark_database.get_all_bookmark_items("movie")
        mdb_rows = self.mdblist_menus._live_playback_rows("movie")
        mdb_ts_by_tmdb = {row["tmdb_id"]: row.get("paused_at") for row in mdb_rows}
        resolved = self.mdblist_menus._resolve([row["tmdb_id"] for row in mdb_rows], "movie")

        trakt_list = self._merge_by_key(
            trakt_rows,
            lambda r: r.get("tmdb_id"),
            lambda r: r.get("paused_at"),
            resolved,
            lambda obj: obj.get("tmdb_id"),
            mdb_ts_by_tmdb,
        )
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True)

    def in_progress_episodes(self):
        """One row per show (Trakt's own convention). When both sources have an
        in-progress episode for the same show, keeps whichever has the more
        recent paused_at, discarding the other entirely (not just deduping
        identical episodes - genuinely different episodes of the same show
        collapse too, per user's confirmed decision)."""
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        trakt_rows = self.bookmark_database.get_all_bookmark_items("episode")
        merged = {}
        for r in trakt_rows:
            show_id = r.get("trakt_show_id")
            if show_id is None:
                continue
            merged[show_id] = (r.get("paused_at") or "", r)

        shows_db = ShowsDatabase()
        for row in self.mdblist_menus._live_playback_rows("episode"):
            trakt_show = self.mdblist_menus.trakt_api.search_by_tmdb_id(row["tmdb_id"], "show")
            if not trakt_show or not trakt_show.get("trakt_id"):
                continue
            show_id = trakt_show["trakt_id"]
            ts = row.get("paused_at") or ""
            existing = merged.get(show_id)
            if existing is not None and existing[0] >= ts:
                continue
            episode = shows_db.get_episode_action_args(show_id, row["season"], row["number"])
            if not episode:
                continue
            merged[show_id] = (ts, episode)

        episodes = [row for _, row in sorted(merged.values(), key=lambda pair: pair[0], reverse=True)]
        if not episodes:
            g.cancel_directory()
            return
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)
