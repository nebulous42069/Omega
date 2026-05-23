"""Anime metadata cache database.

Caches anime episode metadata (titles, plots, thumbnails) fetched from external APIs
(Simkl, AniZip, Jikan/MAL, AniDB, Kitsu) with a 30-day TTL. Also provides persistent
storage for anime ID mappings (replacing the session-level dict in anilist_mapping.py).

Schema:
  anime_episodes: per-episode metadata keyed by (show_id, season, episode)
  anime_id_map:   persistent anime ID mappings keyed by lookup_key (imdb/tmdb)
"""

import collections
import json
import time

from resources.lib.database import Database
from resources.lib.modules.globals import g

CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 days

schema = {
    "anime_episodes": {
        "columns": collections.OrderedDict(
            [
                ("show_id", ["TEXT", "NOT NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("episode", ["INTEGER", "NOT NULL"]),
                ("title", ["TEXT", ""]),
                ("plot", ["TEXT", ""]),
                ("thumb", ["TEXT", ""]),
                ("airdate", ["TEXT", ""]),
                ("duration", ["INTEGER", ""]),
                ("source", ["TEXT", ""]),
                ("anidb_rating", ["REAL", ""]),
                ("anidb_votes", ["INTEGER", ""]),
                ("expires", ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (show_id, season, episode)"],
        "indices": [
            ("idx_anime_ep_expires", ["expires"]),
        ],
        "default_seed": [],
    },
    "anime_id_map": {
        "columns": collections.OrderedDict(
            [
                ("lookup_key", ["TEXT", "NOT NULL"]),
                ("anilist_id", ["INTEGER", ""]),
                ("mal_id", ["INTEGER", ""]),
                ("anidb_id", ["INTEGER", ""]),
                ("kitsu_id", ["INTEGER", ""]),
                ("simkl_id", ["INTEGER", ""]),
                ("thetvdb_id", ["INTEGER", ""]),
                ("themoviedb_id", ["INTEGER", ""]),
                ("expires", ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (lookup_key)"],
        "indices": [],
        "default_seed": [],
    },
    "anime_titles": {
        "columns": collections.OrderedDict(
            [
                ("anidb_id",    ["INTEGER", "NOT NULL"]),
                ("titles_json", ["TEXT", "NOT NULL"]),
                ("expires",     ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (anidb_id)"],
        "indices": [],
        "default_seed": [],
    },
    "anidb_titles_dump": {
        "columns": collections.OrderedDict(
            [
                ("anidb_id",    ["INTEGER", "NOT NULL"]),
                ("lang",        ["TEXT", "NOT NULL"]),
                ("title_lower", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (anidb_id, lang, title_lower)"],
        "indices": [
            ("idx_anidb_dump_title", ["title_lower"]),
        ],
        "default_seed": [],
    },
    "anidb_full_data": {
        "columns": collections.OrderedDict(
            [
                ("anidb_id",  ["INTEGER", "NOT NULL"]),
                ("data_json", ["TEXT", "NOT NULL"]),
                ("expires",   ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (anidb_id)"],
        "indices": [],
        "default_seed": [],
    },
    "anime_relations": {
        "columns": collections.OrderedDict(
            [
                ("anidb_id",       ["INTEGER", "NOT NULL"]),
                ("relations_json", ["TEXT", "NOT NULL"]),
                ("expires",        ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (anidb_id)"],
        "indices": [],
        "default_seed": [],
    },
    "anime_fansub_groups": {
        "columns": collections.OrderedDict(
            [
                ("anidb_id",    ["INTEGER", "NOT NULL"]),
                ("groups_json", ["TEXT", "NOT NULL"]),
                ("expires",     ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (anidb_id)"],
        "indices": [],
        "default_seed": [],
    },
}


class AnimeCache(Database):
    """Persistent cache for anime episode metadata and ID mappings."""

    _pruned = False  # class-level flag — prune once per session

    def __init__(self):
        super().__init__(g.ANIME_CACHE_DB_PATH, schema)
        if not AnimeCache._pruned:
            self._prune_expired()
            AnimeCache._pruned = True

    def _prune_expired(self):
        """Remove expired rows (background, non-fatal)."""
        try:
            now = int(time.time())
            self.execute_sql("DELETE FROM anime_episodes WHERE expires < ?", (now,))
            self.execute_sql("DELETE FROM anime_id_map WHERE expires < ?", (now,))
        except Exception:
            pass

    # ── Episode metadata ─────────────────────────────────────────────────

    def get_episode(self, show_id, season, episode):
        """Return cached episode dict or None if missing/expired."""
        now = int(time.time())
        row = self.fetchone(
            "SELECT title, plot, thumb, airdate, duration, source "
            "FROM anime_episodes WHERE show_id=? AND season=? AND episode=? AND expires>?",
            (str(show_id), int(season), int(episode), now),
        )
        if not row:
            return None
        return {
            "title": row["title"],
            "plot": row["plot"],
            "thumb": row["thumb"],
            "airdate": row["airdate"],
            "duration": row["duration"],
            "source": row["source"],
        }

    def get_season_episodes(self, show_id, season):
        """Return all cached episodes for a season as {episode_num: dict}."""
        now = int(time.time())
        rows = self.fetchall(
            "SELECT episode, title, plot, thumb, airdate, duration, source "
            "FROM anime_episodes WHERE show_id=? AND season=? AND expires>?",
            (str(show_id), int(season), now),
        )
        if not rows:
            return {}
        return {
            row["episode"]: {
                "title": row["title"],
                "plot": row["plot"],
                "thumb": row["thumb"],
                "airdate": row["airdate"],
                "duration": row["duration"],
                "source": row["source"],
            }
            for row in rows
        }

    def set_episodes(self, show_id, season, episodes_dict, source):
        """Store multiple episodes at once.

        Args:
            show_id: identifier string (e.g. mal_id or composite key)
            season: season number
            episodes_dict: {episode_num: {title, plot, thumb, airdate, duration}}
            source: API source name (e.g. 'simkl', 'anizip')
        """
        expires = int(time.time()) + CACHE_TTL_SECONDS
        self.execute_sql(
            "INSERT OR REPLACE INTO anime_episodes "
            "(show_id, season, episode, title, plot, thumb, airdate, duration, source, expires) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    str(show_id),
                    int(season),
                    int(ep_num),
                    ep.get("title", ""),
                    ep.get("plot", ""),
                    ep.get("thumb", ""),
                    ep.get("airdate", ""),
                    ep.get("duration") or 0,
                    source,
                    expires,
                )
                for ep_num, ep in episodes_dict.items()
            ],
        )

    # ── ID mappings ──────────────────────────────────────────────────────

    def get_id_map(self, lookup_key):
        """Return cached anime ID mapping dict or None."""
        now = int(time.time())
        row = self.fetchone(
            "SELECT anilist_id, mal_id, anidb_id, kitsu_id, simkl_id, thetvdb_id, themoviedb_id "
            "FROM anime_id_map WHERE lookup_key=? AND expires>?",
            (str(lookup_key), now),
        )
        if not row:
            return None
        return {
            "anilist_id": row["anilist_id"],
            "mal_id": row["mal_id"],
            "anidb_id": row["anidb_id"],
            "kitsu_id": row["kitsu_id"],
            "simkl_id": row["simkl_id"],
            "thetvdb_id": row["thetvdb_id"],
            "themoviedb_id": row["themoviedb_id"],
        }

    def set_id_map(self, lookup_key, ids):
        """Store anime ID mapping."""
        expires = int(time.time()) + CACHE_TTL_SECONDS
        self.execute_sql(
            "INSERT OR REPLACE INTO anime_id_map "
            "(lookup_key, anilist_id, mal_id, anidb_id, kitsu_id, simkl_id, "
            "thetvdb_id, themoviedb_id, expires) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(lookup_key),
                ids.get("anilist_id"),
                ids.get("mal_id"),
                ids.get("anidb_id"),
                ids.get("kitsu_id"),
                ids.get("simkl_id"),
                ids.get("thetvdb_id"),
                ids.get("themoviedb_id"),
                expires,
            ),
        )

    # ── AniDB Title Variants (anime_titles table) ─────────────────────────

    def get_titles(self, anidb_id):
        """Return cached title list for anidb_id, or None on miss/expiry."""
        now = int(time.time())
        row = self.fetchone(
            "SELECT titles_json FROM anime_titles WHERE anidb_id=? AND expires>?",
            (int(anidb_id), now),
        )
        if not row:
            return None
        try:
            return json.loads(row["titles_json"])
        except Exception:
            return None

    def set_titles(self, anidb_id, titles):
        """Store title list for anidb_id."""
        expires = int(time.time()) + CACHE_TTL_SECONDS
        self.execute_sql(
            "INSERT OR REPLACE INTO anime_titles (anidb_id, titles_json, expires) VALUES (?, ?, ?)",
            (int(anidb_id), json.dumps(titles), expires),
        )

    # ── AniDB Titles Dump (anidb_titles_dump table) ───────────────────────

    def store_titles_dump(self, rows):
        """Bulk-insert (anidb_id, lang, title_lower) rows from dump parse.

        Clears existing dump data first to ensure freshness.
        rows: list of (anidb_id, lang, title_lower) tuples
        """
        self.execute_sql("DELETE FROM anidb_titles_dump", ())
        self.execute_sql(
            "INSERT OR IGNORE INTO anidb_titles_dump (anidb_id, lang, title_lower) VALUES (?, ?, ?)",
            rows,
        )
        # Record download timestamp in a dedicated key in anime_titles (anidb_id=0)
        self.execute_sql(
            "INSERT OR REPLACE INTO anime_titles (anidb_id, titles_json, expires) VALUES (0, '[]', ?)",
            (int(time.time()) + 365 * 24 * 3600,),  # effectively permanent — age checked via mtime
        )

    def get_dump_age_days(self):
        """Return age of titles dump in days, or None if never downloaded."""
        row = self.fetchone(
            "SELECT COUNT(*) as cnt FROM anidb_titles_dump",
            (),
        )
        if not row or not row["cnt"]:
            return None
        # Use the sentinel row timestamp stored in anime_titles anidb_id=0
        sentinel = self.fetchone(
            "SELECT expires FROM anime_titles WHERE anidb_id=0",
            (),
        )
        if not sentinel:
            return None
        # expires was stored as now + 1 year; age = 1year - remaining
        stored_at = sentinel["expires"] - 365 * 24 * 3600
        return (time.time() - stored_at) / 86400

    def lookup_title_dump(self, title):
        """Case-insensitive title → AniDB ID lookup in the dump table."""
        row = self.fetchone(
            "SELECT anidb_id FROM anidb_titles_dump WHERE title_lower=? LIMIT 1",
            (title.lower().strip(),),
        )
        return row["anidb_id"] if row else None

    def get_dump_titles_for_id(self, anidb_id):
        """Return all title strings from dump for a specific anidb_id."""
        rows = self.fetchall(
            "SELECT title_lower FROM anidb_titles_dump WHERE anidb_id=?",
            (int(anidb_id),),
        )
        return [r["title_lower"] for r in rows] if rows else []

    # ── AniDB Full Data Cache (anidb_full_data table) ─────────────────────

    def get_anidb_full_data(self, anidb_id):
        """Return cached full AniDB data dict, or None on miss/expiry."""
        now = int(time.time())
        row = self.fetchone(
            "SELECT data_json FROM anidb_full_data WHERE anidb_id=? AND expires>?",
            (int(anidb_id), now),
        )
        if not row:
            return None
        try:
            data = json.loads(row["data_json"])
            # JSON keys are strings — convert episode/rating dicts back to int keys
            if "episodes" in data:
                data["episodes"] = {int(k): v for k, v in data["episodes"].items()}
            if "ratings" in data:
                data["ratings"] = {int(k): v for k, v in data["ratings"].items()}
            return data
        except Exception:
            return None

    def set_anidb_full_data(self, anidb_id, data):
        """Store full AniDB data dict in cache (30-day TTL)."""
        expires = int(time.time()) + CACHE_TTL_SECONDS
        self.execute_sql(
            "INSERT OR REPLACE INTO anidb_full_data (anidb_id, data_json, expires) VALUES (?, ?, ?)",
            (int(anidb_id), json.dumps(data), expires),
        )


    # ── Anime Relations (anime_relations table) ───────────────────────────

    def get_anime_relations(self, anidb_id):
        """Return cached related anime list, or None on miss/expiry."""
        now = int(time.time())
        row = self.fetchone(
            "SELECT relations_json FROM anime_relations WHERE anidb_id=? AND expires>?",
            (int(anidb_id), now),
        )
        if not row:
            return None
        try:
            return json.loads(row["relations_json"])
        except Exception:
            return None

    def set_anime_relations(self, anidb_id, relations):
        """Store related anime list."""
        expires = int(time.time()) + CACHE_TTL_SECONDS
        self.execute_sql(
            "INSERT OR REPLACE INTO anime_relations (anidb_id, relations_json, expires) VALUES (?, ?, ?)",
            (int(anidb_id), json.dumps(relations), expires),
        )

    # ── Fansub Groups (anime_fansub_groups table) ─────────────────────────

    def get_fansub_groups(self, anidb_id):
        """Return cached fansub group dict, or None on miss/expiry."""
        now = int(time.time())
        row = self.fetchone(
            "SELECT groups_json FROM anime_fansub_groups WHERE anidb_id=? AND expires>?",
            (int(anidb_id), now),
        )
        if not row:
            return None
        try:
            return json.loads(row["groups_json"])
        except Exception:
            return None

    def set_fansub_groups(self, anidb_id, groups):
        """Store fansub group dict."""
        expires = int(time.time()) + CACHE_TTL_SECONDS
        self.execute_sql(
            "INSERT OR REPLACE INTO anime_fansub_groups (anidb_id, groups_json, expires) VALUES (?, ?, ?)",
            (int(anidb_id), json.dumps(groups), expires),
        )
