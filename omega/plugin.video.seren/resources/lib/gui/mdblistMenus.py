from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cached_property

from resources.lib.modules.globals import g


class Menus:
    """MDBList-sourced menus (Recently Watched, In-Progress).

    Items are local mdblistSync.db (or, for in-progress, live sync/playback) rows
    keyed by tmdb_id. Each is resolved to a Trakt object via TraktAPI.search_by_tmdb_id
    (Trakt's ID lookup - no personal OAuth needed) before being handed to the existing,
    unmodified Trakt-native ListBuilder methods. This lets MDBList-only items render
    and play through the exact same proven pipeline as any normally-browsed Trakt item,
    rather than a parallel MDBList-native pipeline that would still need to separately
    solve source-search's own trakt_id requirement.
    """

    def __init__(self):
        self.page_limit = g.get_int_setting("item.limit")

    @cached_property
    def mdblist_database(self):
        from resources.lib.database.mdblist_sync import MDBListSyncDatabase

        return MDBListSyncDatabase()

    @cached_property
    def mdblist_api(self):
        from resources.lib.indexers.mdblist import MDBListAPI

        return MDBListAPI()

    @cached_property
    def trakt_api(self):
        from resources.lib.indexers.trakt import TraktAPI

        return TraktAPI()

    @cached_property
    def list_builder(self):
        from resources.lib.modules.list_builder import ListBuilder

        return ListBuilder()

    def _resolve(self, tmdb_ids, media_type):
        """Resolves tmdb_ids to Trakt objects in parallel (mirrors debrid/external_cache.py's
        ThreadPoolExecutor + as_completed pattern), dropping (and logging) any id Trakt has
        no match for - or that errors/times out - rather than failing the whole list."""
        if not tmdb_ids:
            return []

        resolved = []
        with ThreadPoolExecutor(max_workers=min(10, len(tmdb_ids))) as executor:
            futures = {
                executor.submit(self.trakt_api.search_by_tmdb_id, tmdb_id, media_type): tmdb_id
                for tmdb_id in tmdb_ids
            }
            try:
                for future in as_completed(futures, timeout=20):
                    resolved_item = self._collect_resolved(future, futures[future], media_type)
                    if resolved_item:
                        resolved.append(resolved_item)
            except Exception as e:
                g.log(f"MDBList menus: resolve batch timed out, using partial results: {e}", "warning")
                for future in futures:
                    if future.done():
                        resolved_item = self._collect_resolved(future, futures[future], media_type)
                        if resolved_item:
                            resolved.append(resolved_item)
        return resolved

    @staticmethod
    def _collect_resolved(future, tmdb_id, media_type):
        try:
            trakt_object = future.result()
        except Exception as e:
            g.log(f"MDBList menus: error resolving tmdb_id {tmdb_id} ({media_type}): {e}", "warning")
            return None
        if not trakt_object or not trakt_object.get("trakt_id"):
            g.log(f"MDBList menus: no Trakt match for tmdb_id {tmdb_id} ({media_type}), skipping", "debug")
            return None
        return trakt_object

    def _live_playback_rows(self, media_type):
        """Live GET /sync/playback - fresher than the local bookmarks cache, which
        only updates on scrobble events and can go stale between syncs."""
        entries = self.mdblist_api.get_json("sync/playback") or []
        if isinstance(entries, dict):
            entries = entries.get("items") or []

        rows = []
        for entry in entries:
            if entry.get("type") != media_type:
                continue
            paused_at = entry.get("paused_at")
            if media_type == "movie":
                tmdb_id = (entry.get("movie") or {}).get("ids", {}).get("tmdb")
                if tmdb_id:
                    rows.append({"tmdb_id": tmdb_id, "paused_at": paused_at})
            elif media_type == "episode":
                show = entry.get("show") or {}
                episode = entry.get("episode") or {}
                tmdb_id = show.get("ids", {}).get("tmdb")
                season = episode.get("season")
                number = episode.get("number")
                if tmdb_id and season is not None and number is not None:
                    rows.append(
                        {"tmdb_id": tmdb_id, "season": season, "number": number, "paused_at": paused_at}
                    )
        return rows

    def recent_movies(self):
        rows = self.mdblist_database.get_recent_movies(self.page_limit)
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True, hide_watched=False)

    def recent_shows(self):
        rows = self.mdblist_database.get_recent_shows(self.page_limit)
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "show")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.show_list_builder(
            trakt_list, no_paging=True, hide_watched=False, content_type_override=g.CONTENT_MENU
        )

    def in_progress_movies(self):
        rows = self._live_playback_rows("movie")
        trakt_list = self._resolve([r["tmdb_id"] for r in rows], "movie")
        if not trakt_list:
            g.cancel_directory()
            return
        self.list_builder.movie_menu_builder(trakt_list, no_paging=True)

    def in_progress_episodes(self):
        from resources.lib.database.trakt_sync.shows import TraktSyncDatabase as ShowsDatabase

        rows = self._live_playback_rows("episode")
        shows_db = ShowsDatabase()
        episodes = []
        for row in rows:
            trakt_show = self.trakt_api.search_by_tmdb_id(row["tmdb_id"], "show")
            if not trakt_show or not trakt_show.get("trakt_id"):
                g.log(
                    f"MDBList menus: no Trakt match for tmdb_id {row['tmdb_id']} (show), "
                    "skipping in-progress episode",
                    "debug",
                )
                continue
            episode = shows_db.get_episode_action_args(trakt_show["trakt_id"], row["season"], row["number"])
            if not episode:
                continue
            episodes.append(episode)
        if not episodes:
            g.cancel_directory()
            return
        self.list_builder.mixed_episode_builder(episodes, no_paging=True)
