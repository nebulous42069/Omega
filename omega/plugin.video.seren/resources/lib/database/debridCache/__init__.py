"""Debrid hash cache database.

Caches the results of debrid service hash/cache checks (cached=True/False per service)
with a 24-hour TTL. On subsequent scrapes, hashes already in the DB skip the API call.

Schema: hash TEXT, debrid TEXT (pm/rd/ad/tb), cached TEXT (True/False), expires INTEGER
Primary key: (hash, debrid) — one row per hash per service.
"""

import collections
import time
from threading import Thread

from resources.lib.database import Database
from resources.lib.modules.globals import g

CACHE_TTL_HOURS = 24   # confirmed-cached hashes — stable, long TTL
CACHE_TTL_HOURS_UNCACHED = 4  # confirmed-not-cached — short TTL so newly-cached
                               # content is re-checked sooner (default was 24h)
CACHE_TTL_HOURS_INFRINGING = 168  # 7 days — DMCA/infringing blocks are structural

schema = {
    "debrid_data": {
        "columns": collections.OrderedDict(
            [
                ("hash", ["TEXT", "NOT NULL"]),
                ("debrid", ["TEXT", "NOT NULL"]),
                ("cached", ["TEXT", "NOT NULL"]),
                ("expires", ["INTEGER", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (hash, debrid)"],
        "indices": [
            ("idx_debrid_data_debrid", ["debrid"]),
            ("idx_debrid_data_expires", ["expires"]),
        ],
        "default_seed": [],
    }
}


class DebridCache(Database):
    """Persistent cache for debrid hash check results.

    Usage from TorrentCacheCheck:
        dc = DebridCache()
        known = dc.get_many(hash_list)          # {(hash, debrid): 'True'/'False'}
        dc.set_many([(hash, 'True'), ...], 'pm') # store results after API check
        dc.cleanup()                              # remove expired entries
    """

    def __init__(self):
        super().__init__(g.DEBRID_CACHE_DB_PATH, schema)
        self.table_name = next(iter(schema))

    def get_many(self, hash_list):
        """Fetch all cached debrid results for a list of hashes.

        Returns a list of tuples: [(hash, debrid, cached_str, expires), ...]
        Only returns non-expired entries. Expired entries are pruned in background.
        Queries are batched in chunks of 500 to avoid SQLite's variable limit.
        """
        if not hash_list:
            return []
        try:
            current_time = int(time.time())
            results = []
            batch_size = 500
            hash_list = list(hash_list)
            for i in range(0, len(hash_list), batch_size):
                batch = hash_list[i:i + batch_size]
                placeholders = ",".join("?" for _ in batch)
                rows = self.fetchall(
                    f"SELECT hash, debrid, cached, expires FROM debrid_data "
                    f"WHERE hash IN ({placeholders}) AND expires > ?",
                    (*batch, current_time),
                )
                if rows:
                    results.extend(rows)
            return results
        except Exception as e:
            g.log(f"DebridCache.get_many error: {e}", "warning")
            return []

    def set_many(self, hash_results, debrid):
        """Store cache check results for a debrid service.

        Uses split TTLs:
            cached=True  → 24h (CACHE_TTL_HOURS): confirmed-cached hashes are stable
            cached=False →  4h (CACHE_TTL_HOURS_UNCACHED): content gets newly cached
                            frequently; short TTL means re-checked sooner

        Args:
            hash_results: list of (hash, cached_str) tuples where cached_str is 'True' or 'False'
            debrid: debrid service key ('pm', 'rd', 'ad', 'tb')
        """
        if not hash_results:
            return
        try:
            now = int(time.time())
            for h, cached in hash_results:
                ttl_hours = CACHE_TTL_HOURS if cached == 'True' else CACHE_TTL_HOURS_UNCACHED
                expires   = now + (ttl_hours * 3600)
                self.execute_sql(
                    "INSERT OR REPLACE INTO debrid_data (hash, debrid, cached, expires) "
                    "VALUES (?, ?, ?, ?)",
                    (h, debrid, cached, expires),
                )
        except Exception as e:
            g.log(f"DebridCache.set_many error: {e}", "warning")

    def set_many_background(self, hash_results, debrid):
        """Store results in a background thread (non-blocking)."""
        if hash_results:
            Thread(target=self.set_many, args=(hash_results, debrid), daemon=True).start()

    def set_infringing(self, hash_list, debrid):
        """Mark hashes as legally blocked (DMCA/infringing) with a 7-day TTL.

        Uses INSERT OR REPLACE so this overwrites any existing short-TTL False entry.
        Suppresses the hashes for 7 days across all scrape sessions — DMCA blocks
        are structural and will not resolve on their own within a day.

        Args:
            hash_list: list of torrent hash strings
            debrid: debrid service key ('rd', etc.)
        """
        if not hash_list:
            return
        try:
            now = int(time.time())
            expires = now + (CACHE_TTL_HOURS_INFRINGING * 3600)
            for h in hash_list:
                self.execute_sql(
                    "INSERT OR REPLACE INTO debrid_data (hash, debrid, cached, expires) "
                    "VALUES (?, ?, ?, ?)",
                    (h, debrid, 'False', expires),
                )
            g.log(
                f"DebridCache: Marked {len(hash_list)} hash(es) as infringing for "
                f"{debrid} (7-day suppression)",
                "warning",
            )
        except Exception as e:
            g.log(f"DebridCache.set_infringing error: {e}", "warning")

    def get_cached_hashes_for_service(self, all_cached_rows, debrid):
        """Extract the set of hashes known to be cached for a specific service.

        Args:
            all_cached_rows: result from get_many()
            debrid: service key ('pm', 'rd', 'ad', 'tb')
        Returns:
            set of hashes that are cached (True) for this service
        """
        return {row["hash"] for row in all_cached_rows if row["debrid"] == debrid and row["cached"] == "True"}

    def get_known_hashes_for_service(self, all_cached_rows, debrid):
        """Extract the set of all hashes already checked for a specific service (True or False).

        Args:
            all_cached_rows: result from get_many()
            debrid: service key ('pm', 'rd', 'ad', 'tb')
        Returns:
            set of hashes already checked for this service
        """
        return {row["hash"] for row in all_cached_rows if row["debrid"] == debrid}

    def cleanup(self):
        """Remove expired entries from the database."""
        try:
            current_time = int(time.time())
            self.execute_sql(
                "DELETE FROM debrid_data WHERE expires <= ?", (current_time,)
            )
        except Exception as e:
            g.log(f"DebridCache.cleanup error: {e}", "warning")

    def clear_all(self):
        """Clear all cached debrid results."""
        try:
            self.execute_sql("DELETE FROM debrid_data")
            g.log("DebridCache: Cleared all entries", "info")
        except Exception as e:
            g.log(f"DebridCache.clear_all error: {e}", "warning")

    def clear_service(self, debrid):
        """Clear cached results for a specific debrid service."""
        try:
            self.execute_sql(
                "DELETE FROM debrid_data WHERE debrid = ?", (debrid,)
            )
            g.log(f"DebridCache: Cleared {debrid} entries", "info")
        except Exception as e:
            g.log(f"DebridCache.clear_service error: {e}", "warning")

    def invalidate_hashes(self, hash_list):
        """Remove specific hashes from the cache so they are re-checked on next scrape.

        Used after bulk cloud mismatch deletion — ensures deleted items are not
        still reported as 'cached' from stale DB entries.
        Queries are batched in chunks of 500 to avoid SQLite's variable limit.

        Args:
            hash_list: list of torrent hash strings to remove
        """
        if not hash_list:
            return
        try:
            batch_size = 500
            hash_list = list(hash_list)
            for i in range(0, len(hash_list), batch_size):
                batch = hash_list[i:i + batch_size]
                placeholders = ",".join("?" for _ in batch)
                self.execute_sql(
                    f"DELETE FROM debrid_data WHERE hash IN ({placeholders})",
                    tuple(batch),
                )
            g.log(
                f"DebridCache: Invalidated {len(hash_list)} hashes after cloud mismatch cleanup",
                "info",
            )
        except Exception as e:
            g.log(f"DebridCache.invalidate_hashes error: {e}", "warning")

    def get_stats(self):
        """Return cache statistics for logging."""
        try:
            total = self.fetchone("SELECT COUNT(*) FROM debrid_data")
            cached = self.fetchone(
                "SELECT COUNT(*) FROM debrid_data WHERE cached = 'True'"
            )
            expired = self.fetchone(
                "SELECT COUNT(*) FROM debrid_data WHERE expires <= ?",
                (int(time.time()),),
            )
            return {
                "total": total[0] if total else 0,
                "cached": cached[0] if cached else 0,
                "expired": expired[0] if expired else 0,
            }
        except Exception:
            return {"total": 0, "cached": 0, "expired": 0}
