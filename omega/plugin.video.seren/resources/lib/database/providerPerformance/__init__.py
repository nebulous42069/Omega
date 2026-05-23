"""Provider Performance Learning database.

Tracks per-provider scraping metrics (response time, result count, cached count,
consecutive failures) in a persistent SQLite database.  Used by the tiered
scraping orchestrator to sort providers within each tier by effectiveness and
to auto-skip providers that consistently fail.

Schema: provider (PK), scrape_count, total_results, total_cached, total_time_ms,
        consecutive_failures, last_scrape_time, status
"""

import collections
import time
from threading import Thread

from resources.lib.database import Database
from resources.lib.modules.globals import g

# Providers with no scrapes in this many days are pruned during maintenance
STALE_DAYS = 30

schema = {
    "provider_stats": {
        "columns": collections.OrderedDict(
            [
                ("provider", ["TEXT", "NOT NULL"]),
                ("scrape_count", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("total_results", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("total_cached", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("total_time_ms", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("consecutive_failures", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("last_scrape_time", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("status", ["TEXT", "NOT NULL", "DEFAULT 'active'"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (provider)"],
        "indices": [
            ("idx_provider_stats_status", ["status"]),
        ],
        "default_seed": [],
    }
}


class ProviderPerformance(Database):
    """Persistent store for provider scraping performance metrics.

    Usage from getSources.py:
        pp = ProviderPerformance()
        pp.record_scrape('torrentio', results=42, cached=38, time_ms=1200)
        pp.record_failure('magnetdl', time_ms=30000)
        stats = pp.get_all_stats()           # list of dicts
        score = pp.get_provider_score('dmm')  # float 0-100
    """

    def __init__(self):
        super().__init__(g.PROVIDER_PERF_DB_PATH, schema)
        self.table_name = next(iter(schema))

    def record_scrape(self, provider, results, cached, time_ms):
        """Record a successful scrape (results > 0 or results == 0 but no error).

        A scrape with results=0 is still a valid response (content not found
        on that provider). Only record_failure() increments consecutive_failures.

        Args:
            provider: scraper name (lowercase)
            results: number of raw results returned
            cached: number of cached sources found (may be 0 if deferred)
            time_ms: response time in milliseconds
        """
        provider = provider.lower()
        now = int(time.time())
        try:
            existing = self.fetchone(
                "SELECT scrape_count, total_results, total_cached, total_time_ms "
                "FROM provider_stats WHERE provider = ?",
                (provider,),
            )
            if existing:
                self.execute_sql(
                    "UPDATE provider_stats SET "
                    "scrape_count = scrape_count + 1, "
                    "total_results = total_results + ?, "
                    "total_cached = total_cached + ?, "
                    "total_time_ms = total_time_ms + ?, "
                    "consecutive_failures = CASE WHEN ? > 0 THEN 0 ELSE consecutive_failures END, "
                    "last_scrape_time = ?, "
                    "status = CASE WHEN ? > 0 THEN 'active' ELSE status END "
                    "WHERE provider = ?",
                    (results, cached, time_ms, results, now, results, provider),
                )
            else:
                self.execute_sql(
                    "INSERT INTO provider_stats "
                    "(provider, scrape_count, total_results, total_cached, "
                    "total_time_ms, consecutive_failures, last_scrape_time, status) "
                    "VALUES (?, 1, ?, ?, ?, 0, ?, 'active')",
                    (provider, results, cached, time_ms, now),
                )
        except Exception as e:
            g.log(f"ProviderPerformance.record_scrape error: {e}", "warning")

    def record_scrape_background(self, provider, results, cached, time_ms):
        """Non-blocking version of record_scrape."""
        Thread(
            target=self.record_scrape,
            args=(provider, results, cached, time_ms),
            daemon=True,
        ).start()

    def record_failure(self, provider, time_ms):
        """Record a failed scrape (exception/timeout, not just 0 results).

        Increments consecutive_failures. If threshold is exceeded,
        status is set to 'demoted' or 'disabled' by the caller.

        Args:
            provider: scraper name (lowercase)
            time_ms: response time before failure/timeout
        """
        provider = provider.lower()
        now = int(time.time())
        try:
            existing = self.fetchone(
                "SELECT scrape_count FROM provider_stats WHERE provider = ?",
                (provider,),
            )
            if existing:
                self.execute_sql(
                    "UPDATE provider_stats SET "
                    "scrape_count = scrape_count + 1, "
                    "total_time_ms = total_time_ms + ?, "
                    "consecutive_failures = consecutive_failures + 1, "
                    "last_scrape_time = ? "
                    "WHERE provider = ?",
                    (time_ms, now, provider),
                )
            else:
                self.execute_sql(
                    "INSERT INTO provider_stats "
                    "(provider, scrape_count, total_results, total_cached, "
                    "total_time_ms, consecutive_failures, last_scrape_time, status) "
                    "VALUES (?, 1, 0, 0, ?, 1, ?, 'active')",
                    (provider, time_ms, now),
                )
        except Exception as e:
            g.log(f"ProviderPerformance.record_failure error: {e}", "warning")

    def record_failure_background(self, provider, time_ms):
        """Non-blocking version of record_failure."""
        Thread(
            target=self.record_failure,
            args=(provider, time_ms),
            daemon=True,
        ).start()

    def set_status(self, provider, status):
        """Set provider status: 'active', 'demoted', or 'disabled'.

        Args:
            provider: scraper name (lowercase)
            status: one of 'active', 'demoted', 'disabled'
        """
        provider = provider.lower()
        try:
            self.execute_sql(
                "UPDATE provider_stats SET status = ? WHERE provider = ?",
                (status, provider),
            )
        except Exception as e:
            g.log(f"ProviderPerformance.set_status error: {e}", "warning")

    def get_provider_stats(self, provider):
        """Get stats for a single provider.

        Returns dict with keys: provider, scrape_count, total_results,
        total_cached, total_time_ms, consecutive_failures, last_scrape_time,
        status, avg_response_ms, avg_results, avg_cached
        """
        provider = provider.lower()
        try:
            row = self.fetchone(
                "SELECT provider, scrape_count, total_results, total_cached, "
                "total_time_ms, consecutive_failures, last_scrape_time, status "
                "FROM provider_stats WHERE provider = ?",
                (provider,),
            )
            if row:
                return self._row_to_dict(row)
            return None
        except Exception as e:
            g.log(f"ProviderPerformance.get_provider_stats error: {e}", "warning")
            return None

    def get_all_stats(self):
        """Get stats for all tracked providers, sorted by scrape count descending.

        Returns list of dicts.
        """
        try:
            rows = self.fetchall(
                "SELECT provider, scrape_count, total_results, total_cached, "
                "total_time_ms, consecutive_failures, last_scrape_time, status "
                "FROM provider_stats ORDER BY scrape_count DESC"
            )
            return [self._row_to_dict(row) for row in (rows or [])]
        except Exception as e:
            g.log(f"ProviderPerformance.get_all_stats error: {e}", "warning")
            return []

    def get_provider_score(self, provider):
        """Compute a performance score (0-100) for ranking providers within a tier.

        Higher is better. Based on:
        - Average cached results per scrape (50% weight)
        - Average response time, inverted (30% weight)
        - Consecutive failure penalty (20% weight)

        Returns 50.0 for unknown providers (neutral).
        """
        stats = self.get_provider_stats(provider)
        if not stats or stats['scrape_count'] == 0:
            return 50.0  # Neutral score — untested providers sort to middle

        avg_cached = stats['avg_cached']
        avg_ms = stats['avg_response_ms']
        consec_fail = stats['consecutive_failures']

        # Cached score: 0-50 range, caps at 10 avg cached results
        cached_score = min(avg_cached / 10.0, 1.0) * 50.0

        # Speed score: 0-30 range. 0ms=30, 15000ms+=0
        speed_score = max(0, (1.0 - min(avg_ms / 15000.0, 1.0))) * 30.0

        # Failure penalty: 0-20 range. Each consecutive failure costs 4 points
        failure_penalty = min(consec_fail * 4.0, 20.0)

        return max(0.0, cached_score + speed_score - failure_penalty)

    def get_consecutive_failures(self, provider):
        """Get consecutive failure count for a provider. Returns 0 if unknown."""
        provider = provider.lower()
        try:
            row = self.fetchone(
                "SELECT consecutive_failures FROM provider_stats WHERE provider = ?",
                (provider,),
            )
            return row[0] if row else 0
        except Exception:
            return 0

    def get_status(self, provider):
        """Get status for a provider. Returns 'active' if unknown."""
        provider = provider.lower()
        try:
            row = self.fetchone(
                "SELECT status FROM provider_stats WHERE provider = ?",
                (provider,),
            )
            return row[0] if row else "active"
        except Exception:
            return "active"

    def get_disabled_providers(self):
        """Get set of provider names that are currently disabled."""
        try:
            rows = self.fetchall(
                "SELECT provider FROM provider_stats WHERE status = 'disabled'"
            )
            return {row[0] for row in (rows or [])}
        except Exception:
            return set()

    def cleanup(self):
        """Remove entries for providers not scraped in STALE_DAYS days."""
        try:
            cutoff = int(time.time()) - (STALE_DAYS * 86400)
            self.execute_sql(
                "DELETE FROM provider_stats WHERE last_scrape_time < ? AND last_scrape_time > 0",
                (cutoff,),
            )
        except Exception as e:
            g.log(f"ProviderPerformance.cleanup error: {e}", "warning")

    def clear_all(self):
        """Clear all provider performance data."""
        try:
            self.execute_sql("DELETE FROM provider_stats")
            g.log("ProviderPerformance: Cleared all entries", "info")
        except Exception as e:
            g.log(f"ProviderPerformance.clear_all error: {e}", "warning")

    def reset_provider(self, provider):
        """Reset stats for a single provider back to defaults."""
        provider = provider.lower()
        try:
            self.execute_sql(
                "DELETE FROM provider_stats WHERE provider = ?",
                (provider,),
            )
        except Exception as e:
            g.log(f"ProviderPerformance.reset_provider error: {e}", "warning")

    def get_summary(self):
        """Return summary statistics for logging/display."""
        try:
            total = self.fetchone("SELECT COUNT(*) FROM provider_stats")
            active = self.fetchone(
                "SELECT COUNT(*) FROM provider_stats WHERE status = 'active'"
            )
            demoted = self.fetchone(
                "SELECT COUNT(*) FROM provider_stats WHERE status = 'demoted'"
            )
            disabled = self.fetchone(
                "SELECT COUNT(*) FROM provider_stats WHERE status = 'disabled'"
            )
            return {
                "total": total[0] if total else 0,
                "active": active[0] if active else 0,
                "demoted": demoted[0] if demoted else 0,
                "disabled": disabled[0] if disabled else 0,
            }
        except Exception:
            return {"total": 0, "active": 0, "demoted": 0, "disabled": 0}

    @staticmethod
    def _row_to_dict(row):
        """Convert a DB row (dict or tuple) to a stats dict with computed averages."""
        if isinstance(row, dict):
            # row_factory returns dicts — read values by key
            provider = row.get("provider", "")
            scrape_count = row.get("scrape_count", 0)
            total_results = row.get("total_results", 0)
            total_cached = row.get("total_cached", 0)
            total_time_ms = row.get("total_time_ms", 0)
            consecutive_failures = row.get("consecutive_failures", 0)
            last_scrape_time = row.get("last_scrape_time", 0)
            status = row.get("status", "active")
        else:
            # Tuple fallback
            provider, scrape_count, total_results, total_cached, \
                total_time_ms, consecutive_failures, last_scrape_time, status = row
        # SQLite may return strings for integer columns in some configurations
        scrape_count = int(scrape_count or 0)
        total_results = int(total_results or 0)
        total_cached = int(total_cached or 0)
        total_time_ms = int(total_time_ms or 0)
        consecutive_failures = int(consecutive_failures or 0)
        last_scrape_time = int(last_scrape_time or 0)
        sc = max(scrape_count, 1)  # Avoid division by zero
        return {
            "provider": provider,
            "scrape_count": scrape_count,
            "total_results": total_results,
            "total_cached": total_cached,
            "total_time_ms": total_time_ms,
            "consecutive_failures": consecutive_failures,
            "last_scrape_time": last_scrape_time,
            "status": status or "active",
            "avg_response_ms": round(total_time_ms / sc, 1),
            "avg_results": round(total_results / sc, 2),
            "avg_cached": round(total_cached / sc, 2),
        }
