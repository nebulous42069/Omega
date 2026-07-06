import collections
import datetime

from resources.lib.common import tools
from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "movies": {
        "columns": collections.OrderedDict(
            [
                ("tmdb_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("imdb_id", ["TEXT", "NULL"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": [],
        "indices": [("idx_mdblist_movies_watched", ["watched"])],
        "default_seed": [],
    },
    "episodes": {
        "columns": collections.OrderedDict(
            [
                ("show_tmdb_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("number", ["INTEGER", "NOT NULL"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("last_watched_at", ["TEXT", "NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(show_tmdb_id, season, number)"],
        "indices": [("idx_mdblist_episodes_show", ["show_tmdb_id"])],
        "default_seed": [],
    },
    "bookmarks": {
        "columns": collections.OrderedDict(
            [
                ("tmdb_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NULL"]),
                ("number", ["INTEGER", "NULL"]),
                ("media_type", ["TEXT", "NOT NULL"]),
                ("percent_played", ["TEXT", "NOT NULL"]),
                ("resume_time", ["TEXT", "NULL"]),
                ("paused_at", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY(tmdb_id, season, number, media_type)"],
        "indices": [("idx_mdblist_bookmarks_paused", ["paused_at"])],
        "default_seed": [],
    },
    "activities": {
        "columns": collections.OrderedDict(
            [
                ("sync_id", ["INTEGER", "PRIMARY KEY"]),
                ("watched_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("episode_watched_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("playback_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("watchlisted_at", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("mdblist_username", ["TEXT", "NULL"]),
                ("last_activities_call", ["INTEGER", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": ["UNIQUE(sync_id)"],
        "default_seed": [],
    },
}


class MDBListSyncDatabase(Database):
    def __init__(self):
        super().__init__(g.MDBLIST_SYNC_DB_PATH, schema)

        self.activities = {}
        self.base_date = "1970-01-01T00:00:00"
        self.refresh_activities()

        if self.activities is None:
            self.set_base_activities()

    def refresh_activities(self):
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    def set_base_activities(self):
        self.execute_sql(
            "REPLACE INTO activities(sync_id, mdblist_username) VALUES(1, ?)",
            (g.get_setting("mdblist.username"),),
        )
        self.activities = self.fetchone("SELECT * FROM activities WHERE sync_id=1")

    @staticmethod
    def _get_datetime_now():
        return g.datetime_to_string(datetime.datetime.utcnow())

    @staticmethod
    def requires_update(new_date, old_date):
        return tools.parse_datetime(new_date, False) > tools.parse_datetime(old_date, False)

    def write_watched_locally(self, mediatype, info):
        """Writes a movie/episode watched mark directly to the local sync tables and
        clears any matching stale bookmark. Shared by the scrobbler (player.py) and the
        context-menu mark-watched action, since MDBList's GET /sync/watched never
        returns movies and a mark made via either path would otherwise be invisible
        in Seren's own local view until the next full sync (movies: never, since the
        remote endpoint never returns them at all)."""
        try:
            now = self._get_datetime_now()
            if mediatype == "movie":
                tmdb_id = info.get("tmdb_id")
                if not tmdb_id:
                    return
                self.execute_sql(
                    "REPLACE INTO movies (tmdb_id, imdb_id, watched, last_watched_at) VALUES (?, ?, 1, ?)",
                    (tmdb_id, info.get("imdb_id"), now),
                )
                self.execute_sql("DELETE FROM bookmarks WHERE tmdb_id=? AND media_type='movie'", (tmdb_id,))
            elif mediatype == "episode":
                tmdb_show_id = info.get("tmdb_show_id")
                season = info.get("season")
                episode = info.get("episode")
                if not tmdb_show_id or season is None or episode is None:
                    return
                self.execute_sql(
                    "REPLACE INTO episodes (show_tmdb_id, season, number, watched, last_watched_at) VALUES (?, ?, ?, 1, ?)",
                    (tmdb_show_id, season, episode, now),
                )
                self.execute_sql(
                    "DELETE FROM bookmarks WHERE tmdb_id=? AND season=? AND number=? AND media_type='episode'",
                    (tmdb_show_id, season, episode),
                )
        except Exception:
            g.log_stacktrace()

    def get_recent_movies(self, limit, offset=0, force_all=False):
        """Locally-synced watched movies, newest first. Scrobbler/context-menu-written
        only - MDBList's own GET /sync/watched never returns movies (Phase B/D gap)."""
        query = """
            SELECT tmdb_id, last_watched_at
            FROM movies
            WHERE watched = 1
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {limit} OFFSET {offset}"
        return self.fetchall(query)

    def get_recent_shows(self, limit, offset=0, force_all=False):
        """Locally-synced watched episodes rolled up to show level (latest episode's
        last_watched_at per show), newest first."""
        query = """
            SELECT show_tmdb_id AS tmdb_id, MAX(last_watched_at) AS last_watched_at
            FROM episodes
            WHERE watched = 1
            GROUP BY show_tmdb_id
            ORDER BY last_watched_at DESC
            """
        if not force_all:
            query += f" LIMIT {limit} OFFSET {offset}"
        return self.fetchall(query)
