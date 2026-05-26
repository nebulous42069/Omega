"""
Handling of scraping and cache checking for sources
"""
import contextlib
import copy
import importlib
import json
import random
import re
import sys
import time
import threading
from collections import Counter
from collections import OrderedDict
from importlib import reload as reload_module
from urllib import parse

import xbmc
import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.common.thread_pool import ThreadPool
from resources.lib.database.skinManager import SkinManager
from resources.lib.database.torrentCache import TorrentCache
from resources.lib.debrid import all_debrid
from resources.lib.debrid import debrid_link
from resources.lib.debrid import premiumize
from resources.lib.debrid import real_debrid
from resources.lib.debrid import torbox
from resources.lib.debrid import external_cache
from resources.lib.gui.windows.get_sources_window import GetSourcesWindow
from resources.lib.gui.windows.manual_caching import ManualCacheWindow
from resources.lib.modules import monkey_requests
from resources.lib.modules import resolver as resolver
from resources.lib.modules.cloud_scrapers import AllDebridCloudScraper
from resources.lib.modules.cloud_scrapers import DebridLinkCloudScraper
from resources.lib.modules.cloud_scrapers import PremiumizeCloudScraper
from resources.lib.modules.cloud_scrapers import RealDebridCloudScraper
from resources.lib.modules.cloud_scrapers import TorBoxCloudScraper
from resources.lib.modules.globals import g
from resources.lib.modules.source_sorter import SourceSorter

approved_qualities = ["4K", "1080p", "720p", "SD"]
approved_qualities_set = set(approved_qualities)

# Tiered scraping configuration
# Scrapers are grouped by reliability and speed. Tier 0 runs first (cloud cache).
# If any tier finds >= threshold cached sources, lower tiers are skipped.
# Threshold is user-configurable via Settings > Scraping > Tier Skip Threshold (default 10).
TIER_MIN_CACHED_DEFAULT = 10  # Fallback if setting is missing

# S15 — Maximum seconds to wait for in-flight debrid cache checks after the
# keep-alive loop exits. Cold-cache first runs need this to let debrid workers
# finish verifying hashes before _finalise_results() reads torrentCacheSources.
# Warm-cache runs complete instantly (Event already set by the time we wait).
_CACHE_CHECK_GRACE_SECONDS = 20

SCRAPER_TIERS = {
    # Tier 0 — Cloud cache lookup (pre-crawled results from other users, instant if hit)
    'cached': 0,
    # Tier 1 — Anime (dedicated anime trackers, fast, return nothing for non-anime; auto-skipped for non-anime)
    'animetosho': 1, 'anirena': 1, 'nekobt': 1, 'nyaa': 1, 'subsplease': 1,
    # Tier 2 — Stremio Direct (Torrentio — largest single Stremio index, fast JSON API)
    'torrentio': 2,
    # Tier 3 — Stremio Direct-Alt (Comet, MediaFusion, Meteor — standalone Stremio scrapers)
    'comet': 3, 'mediafusion': 3, 'meteor': 3,
    # Tier 4 — IMDB Hash Lookup (debrid-optimized IMDB-ID hash lookup, instant JSON APIs)
    'bitmagnet': 4, 'dmm': 4, 'torrentsdb': 4, 'torz': 4, 'zilean': 4,
    # Tier 5 — Keyword Scrapers (title-based text search, broader coverage)
    'bitsearch': 5, 'knaben': 5, 'torrentz2': 5,
    # Tier 6 — Reliable public trackers
    'eztv': 6, 'kickass2': 6, 'leet': 6, 'piratebay': 6, 'yts': 6,
    # Tier 7 — Slow or unreliable
    'kickass': 7, 'magnetdl': 7, 'showrss': 7,
    'torrentdownload': 7, 'torrentproject2': 7,
}

# Scrapers to skip entirely — these providers are ignored even if installed in the package
SCRAPER_BLACKLIST = {'aiostreams'}

_TORRENT_CLEAN_RE = re.compile(r"[:''\u2019\u2018\u2013\u2014&!★√…\?\.]")
_PARENS_RE = re.compile(r"\s*\([^)]*\)")
_MULTI_SPACE_RE = re.compile(r"\s+")
_TRAILING_DASH_RE = re.compile(r"\s*-\s*$")

# Asian drama enrichment (Session 48)
ASIAN_DRAMA_COUNTRIES = {'CN', 'KR', 'TW', 'TH', 'HK', 'VN', 'PH', 'MY', 'IN', 'SG', 'ID', 'JP'}
# CJK bracket/decoration chars that appear in titles but break torrent search
_CJK_DECORATION_RE = re.compile(r'[~「」『』【】《》〈〉（）\(\)\[\]～〜]')


def _clean_cjk_alias(alias):
    """Strip CJK decoration characters and normalize whitespace for torrent search.

    e.g. "Saikai ~Silent Truth~" → "Saikai Silent Truth"
         "再会【Silent Truth】"   → "再会 Silent Truth"

    Returns cleaned string, or None if unchanged/empty.
    """
    if not alias:
        return None
    stripped = _CJK_DECORATION_RE.sub('', alias).strip()
    stripped = _MULTI_SPACE_RE.sub(' ', stripped)
    return stripped if stripped and stripped != alias else None


def _torrent_clean_title(title):
    """Strip characters that break torrent site searches.

    Removes colons, apostrophes, ampersands, dashes (en/em), ellipsis, question
    marks, periods, special unicode, and parenthesized content like '(2005)'.
    Applied to all content — movies, TV shows, and anime.

    Returns cleaned string, or None if result is empty/too short or unchanged.
    """
    if not title:
        return None
    cleaned = _TORRENT_CLEAN_RE.sub("", title)
    cleaned = _PARENS_RE.sub("", cleaned)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned).strip()
    cleaned = _TRAILING_DASH_RE.sub("", cleaned).strip()
    return cleaned if cleaned and len(cleaned) > 1 and cleaned.lower() != title.lower() else None


def _coerce_seeds(value):
    """Defensive int() cast for torrent['seeds'].

    Some scrapers (notably a4kScrapers feeds) return seeds as a string
    e.g. '42' or '' or '?' — which causes TypeError when Python's tuple
    sort falls through to compare str vs int. This helper normalises any
    truthy value to a non-negative int, anything else to 0, so the sort
    keys in `_rd_storeall_sort_key` and friends can't crash the RD worker
    thread. Patched by user (Session 15) to fix the Frieren playback
    failure caused by a string-seeds row poisoning the entire getSources
    run via Pre-emptive Termination.
    """
    if isinstance(value, int):
        return value if value >= 0 else 0
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)
    return 0


class Sources:
    """
    Handles fetching and processing of available sources for provided meta data
    """

    def __init__(self, item_information):
        self.hash_regex = re.compile(r'btih:(.*?)(?:&|$)')
        self.canceled = False
        self.torrent_cache = TorrentCache()
        self.torrent_threads = ThreadPool()
        self.hoster_threads = ThreadPool()
        self.adaptive_threads = ThreadPool()
        self.direct_threads = ThreadPool()
        self.item_information = item_information
        self.media_type = self.item_information['info']['mediatype']
        self.torrent_providers = []
        self.hoster_providers = []
        self.adaptive_providers = []
        self.direct_providers = []
        self.cloud_scrapers = []
        self.running_providers = []
        self.language = 'en'
        self._apikeys = self._build_apikeys()
        self._cache_checked_hashes = set()
        self._cache_check_lock = threading.Lock()
        # S15 — Debrid cache grace: tracks in-flight TorrentCacheCheck batches.
        # _cache_check_active_count > 0 means debrid workers are running.
        # _cache_check_done is set() when count reaches 0, clear() while > 0.
        # get_sources() waits on this event after the keep-alive exits so that
        # cold-cache runs let debrid workers finish before _finalise_results()
        # reads torrentCacheSources.
        self._cache_check_active_count = 0
        self._cache_check_done = threading.Event()
        self._cache_check_done.set()  # "no active check" = set
        self.sources_information = {
            "directSources": [],
            "adaptiveSources": [],
            "torrentCacheSources": {},
            "hosterSources": {},
            "cloudFiles": [],
            "allTorrents": {},
            "cached_hashes": set(),
            "local_cache_hashes": set(),
            "statistics": {
                "torrents": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "torrentsCached": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "cloudFiles": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "totals": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                "filtered": {
                    "torrents": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                    "torrentsCached": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                    "hosters": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                    "cloudFiles": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                    "adaptiveSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                    "directSources": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                    "totals": {"4K": 0, "1080p": 0, "720p": 0, "SD": 0, "total": 0},
                },
                "remainingProviders": [],
            },
        }

        self.hoster_domains = {}
        self.progress = 0
        self.timeout_progress = 0
        self.runtime = 0
        self.host_domains = []
        self.host_names = []
        self.timeout = g.get_int_setting('general.timeout')
        self.window = SourceWindowAdapter(self.item_information, self)

        self.silent = g.get_bool_runtime_setting('tempSilent')

        self.source_sorter = SourceSorter(self.item_information)

        self.preem_enabled = g.get_bool_setting('preem.enabled')
        self.preem_waitfor_cloudfiles = g.get_bool_setting("preem.waitfor.cloudfiles")
        self.preem_cloudfiles = g.get_bool_setting('preem.cloudfiles')
        self.preem_adaptive_sources = g.get_bool_setting('preem.adaptiveSources')
        self.preem_direct_sources = g.get_bool_setting('preem.directSources')
        self.preem_type = g.get_int_setting('preem.type')
        self.preem_limit = g.get_int_setting('preem.limit')
        self.preem_resolutions = approved_qualities[
            g.get_int_setting("general.maxResolution") : self._get_pre_term_min()
        ]

    def get_sources(self, overwrite_torrent_cache=False):
        """
        Main endpoint to initiate scraping process
        :param overwrite_cache:
        :return: Returns (uncached_sources, sorted playable sources, items metadata)
        :rtype: tuple
        """
        try:
            g.log('Starting Scraping', 'debug')
            g.log(f"Timeout: {self.timeout}", 'debug')
            g.log(f"Pre-term-enabled: {self.preem_enabled}", 'debug')
            g.log(f"Pre-term-limit: {self.preem_limit}", 'debug')
            g.log(f"Pre-term-res: {self.preem_resolutions}", 'debug')
            g.log(f"Pre-term-type: {self.preem_type}", 'debug')
            g.log(f"Pre-term-cloud-files: {self.preem_cloudfiles}", 'debug')
            g.log(f"Pre-term-adaptive-files: {self.preem_adaptive_sources}", 'debug')
            g.log(f"Pre-term-direct-files: {self.preem_direct_sources}", 'debug')

            self._handle_pre_scrape_modifiers()
            self._get_imdb_info()

            if overwrite_torrent_cache:
                self._clear_local_torrent_results()
            else:
                self._check_local_torrent_database()

            self._update_progress()
            if self._prem_terminate():
                return self._finalise_results()

            self.window.create()
            self.window.set_text(
                g.get_language_string(30054),
                self.progress,
                self.timeout_progress,
                self.sources_information,
                self.runtime,
            )
            self._init_providers()

            # Add the users cloud inspection to the threads to be run
            self.torrent_threads.put(self._user_cloud_inspection)

            # Add TorBox Usenet search (runs alongside cloud inspection)
            if g.torbox_enabled() and g.get_bool_setting('torbox.usenet', False):
                self.torrent_threads.put(self._torbox_usenet_search)

            # Load threads for all sources
            self._create_torrent_threads()
            self._create_hoster_threads()
            self._create_adaptive_threads()
            self._create_direct_threads()

            start_time = time.time()
            while (
                len(self.torrent_providers)
                + len(self.hoster_providers)
                + len(self.adaptive_providers)
                + len(self.direct_providers)
                + len(self.cloud_scrapers)
                <= 0
            ):
                self.runtime = time.time() - start_time
                if self.runtime > 5:
                    g.notification(g.ADDON_NAME, g.get_language_string(30615))
                    g.log('No providers enabled', 'warning')
                    return

            self.window.set_property("has_torrent_providers", "true" if len(self.torrent_providers) > 0 else "false")
            self.window.set_property("has_hoster_providers", "true" if len(self.hoster_providers) > 0 else "false")
            self.window.set_property("has_adaptive_providers", "true" if len(self.adaptive_providers) > 0 else "false")
            self.window.set_property("has_cloud_scrapers", "true" if len(self.cloud_scrapers) > 0 else "false")
            self.window.set_property(
                "has_direct_providers",
                "true" if len(self.direct_providers) > 0 else "false",
            )
            self._update_progress()
            self.window.set_property('process_started', 'true')

            # Keep alive for gui display and threading
            g.log('Entering Keep Alive', 'info')

            while self.progress < 100 and not g.abort_requested():
                self.runtime = time.time() - start_time
                self._update_progress()
                self.timeout_progress = int(100 - float(1 - (self.runtime / float(self.timeout))) * 100)
                self.progress = int(
                    100
                    - (
                        len(self.sources_information['statistics']['remainingProviders'])
                        / float(
                            len(self.torrent_providers)
                            + len(self.hoster_providers)
                            + len(self.adaptive_providers)
                            + len(self.direct_providers)
                            + (1 if self.cloud_scrapers else 0)
                        )
                        * 100
                    )
                )

                try:
                    self.window.set_text(  # sourcery skip: use-fstring-for-formatting
                        "4K: {} | 1080: {} | 720: {} | SD: {}".format(
                            g.color_string(self.sources_information['statistics']['filtered']['totals']['4K']),
                            g.color_string(self.sources_information['statistics']['filtered']['totals']['1080p']),
                            g.color_string(self.sources_information['statistics']['filtered']['totals']['720p']),
                            g.color_string(self.sources_information['statistics']['filtered']['totals']['SD']),
                        ),
                        self.progress,
                        self.timeout_progress,
                        self.sources_information,
                        self.runtime,
                    )

                except (KeyError, IndexError) as e:
                    g.log(f"Failed to set window text, {e}", "error")

                g.log(f"Remaining Providers {self.sources_information['statistics']['remainingProviders']}", "debug")
                if self._prem_terminate() is True or (
                    len(self.sources_information['statistics']['remainingProviders']) == 0 and self.runtime > 5
                ):
                    # Give some time for scrapers to initiate
                    break

                if self.canceled or self.runtime >= self.timeout:
                    monkey_requests.PRE_TERM_BLOCK = True
                    break

                xbmc.sleep(200)

            g.log('Exited Keep Alive', 'info')

            # S15 — Debrid cache grace period (two-stage).
            #
            # Stage 1 (new — background overlap scraping):
            #   When keep-alive exits via timeout, a background Tier overlap
            #   thread may still be in the SCRAPING phase — scrapers haven't
            #   finished yet so TorrentCacheCheck hasn't even been called.
            #   _cache_check_done is still set() at this point (no debrid
            #   workers launched yet), so the original Stage 2 check is a no-op.
            #   Result: _finalise_results() runs with 0 cached sources on every
            #   cold-cache first scrape from source_select / Openinfo.
            #
            #   Fix: wait for remainingProviders to drain.  CACHE_CHECK_TIER_N
            #   sentinels are present while any tier's scraping or cache-check
            #   phase is in progress, so an empty list means all background work
            #   is done and _cache_check_done is now reliable.
            #
            # Stage 2 (original — in-flight debrid workers):
            #   Handles the case where scrapers finished BEFORE keep-alive
            #   exited but debrid API workers are still in-flight.
            #   _cache_check_done is clear() while workers run.
            #
            # Both stages are no-ops on warm-cache runs (fast DB reads complete
            # before keep-alive exits, all events already set).
            if not self.canceled:
                remaining = self.sources_information['statistics']['remainingProviders']
                if remaining:
                    grace_seconds = g.get_int_setting('general.cacheCheckGrace', _CACHE_CHECK_GRACE_SECONDS)
                    g.log(
                        f'Cache check grace (stage 1): waiting up to {grace_seconds}s for background providers {list(remaining)}',
                        'info',
                    )
                    deadline = time.time() + grace_seconds
                    while remaining and time.time() < deadline and not self.canceled:
                        xbmc.sleep(200)
                    if remaining:
                        g.log(
                            f'Cache check grace (stage 1): timed out — {list(remaining)} still running, finalising with partial results',
                            'warning',
                        )
                    else:
                        g.log('Cache check grace (stage 1): background providers completed', 'info')

            if not self._cache_check_done.is_set():
                grace_seconds = g.get_int_setting('general.cacheCheckGrace', _CACHE_CHECK_GRACE_SECONDS)
                g.log(f'Cache check grace (stage 2): waiting up to {grace_seconds}s for debrid workers to finish', 'info')
                completed = self._cache_check_done.wait(timeout=grace_seconds)
                if completed:
                    g.log('Cache check grace (stage 2): debrid workers completed — proceeding to finalise', 'info')
                else:
                    g.log(f'Cache check grace (stage 2): timed out after {grace_seconds}s — finalising with partial results', 'warning')

            return self._finalise_results()

        finally:
            self.window.close()

    def _handle_pre_scrape_modifiers(self):
        """
        Detects preScrape, disables pre-termination and sets timeout to maximum value
        :return:
        :rtype:
        """
        if g.REQUEST_PARAMS.get('action', '') == "preScrape":
            self.silent = True
            self.timeout = 180
            self._prem_terminate = self._disabled_prem_terminate

    def _disabled_prem_terminate(self):
        return False

    def _create_hoster_threads(self):
        if self._hosters_enabled():
            random.shuffle(self.hoster_providers)
            for i in self.hoster_providers:
                self.hoster_threads.put(self._get_hosters, self.item_information, i)

    def _create_torrent_threads(self):
        if self._torrents_enabled():
            # Launch tiered scraping in a single background thread
            self.torrent_threads.put(self._tiered_torrent_orchestrator)

    def _get_cached_source_count(self):
        """Returns current count of cached torrent sources found so far.
        Reads directly from torrentCacheSources dict (updated in real-time by
        store_torrent) instead of statistics dict (only updated by _update_progress
        on the main thread).
        """
        return len(self.sources_information.get('torrentCacheSources', {}))

    def _tiered_torrent_orchestrator(self):
        """
        Runs torrent providers tier-by-tier with deferred batch cache checking
        and parallel tier overlap.

        Deferred batch cache check: all providers in a tier scrape first, then
        ONE batch cache check runs for all collected hashes (1×5 API rounds
        instead of N×5).

        Parallel tier overlap: while a tier's cache check runs, the NEXT tier's
        scraping starts in the background. If the cache check meets the threshold,
        the background scrape is abandoned. If not, the background results are
        already collected and ready for their own cache check.

        Anime-aware tier ordering:
        - Non-anime: Tier 2 → 3 (Comet/MF/Meteor) → 4 → 5 → 6 → 7 (skip Tier 1 anime scrapers entirely)
        - Anime: Tier 1 → 2 → 3 → 4 → 5 → 6 → 7

        Provider Performance Learning (when enabled):
        - Providers within each tier are sorted by performance score (best first)
        - Providers auto-disabled due to consecutive failures are skipped
        """
        import concurrent.futures
        import threading

        # Read user-configurable threshold (0 = always run all tiers)
        tier_min_cached = g.get_int_setting('general.tierThreshold', TIER_MIN_CACHED_DEFAULT)

        # Detect anime content from genre metadata
        genres = self.item_information.get('info', {}).get('genre', [])
        if not isinstance(genres, list):
            genres = [genres] if genres else []
        genres_lower = [g.lower() for g in genres]
        is_anime = any('anime' in g for g in genres_lower)
        if not is_anime and any('animation' in g for g in genres_lower):
            # "Animation" genre appears for both anime and western animation.
            # Use country of origin to distinguish: anime scrapers index Japanese content.
            _country = (self.item_information.get('info', {}).get('country_origin', '') or '').upper()
            is_anime = _country in ('JP', 'JPN', 'JAPAN', 'CN', 'CHN', 'CHINA')

        # Load provider performance data if feature is enabled
        pp = self._get_provider_perf_db()
        disabled_providers = pp.get_disabled_providers() if pp else set()

        # Group providers by tier, skipping blacklisted/disabled scrapers
        tier_groups = {}  # {1: [provider_tuples], 2: [...], ...}
        perf_skipped = []
        for provider in self.torrent_providers:
            provider_name = provider[1].lower()
            if provider_name in SCRAPER_BLACKLIST:
                g.log(f"Tiered scraping: Skipping blacklisted scraper '{provider_name}'", "info")
                continue
            # Skip providers auto-disabled by performance learning
            if provider_name in disabled_providers:
                perf_skipped.append(provider_name.upper())
                continue
            # Handle parenthesized names if any provider uses that convention
            base_name = provider_name.split('(')[0].strip() if '(' in provider_name else provider_name
            tier = SCRAPER_TIERS.get(provider_name, SCRAPER_TIERS.get(base_name, 7))
            tier_groups.setdefault(tier, []).append(provider)

        if perf_skipped:
            g.log(
                f"Provider Performance: Skipping {len(perf_skipped)} auto-disabled providers: "
                f"{perf_skipped}",
                "info",
            )

        # Tier toggles: skip entire tiers disabled in settings
        for tier_num in list(tier_groups.keys()):
            if not g.get_bool_setting(f'scraping.tier{tier_num}', True):
                skipped = [p[1].upper() for p in tier_groups[tier_num]]
                g.log(
                    f"Tiered scraping: Tier {tier_num} disabled in settings, skipping {skipped}",
                    "info",
                )
                del tier_groups[tier_num]

        # Skip anime tier (1) for non-anime content
        if not is_anime and 1 in tier_groups:
            skipped_anime = [p[1].upper() for p in tier_groups[1]]
            g.log(
                f"Tiered scraping: Non-anime content, skipping Tier 1 anime scrapers ({skipped_anime})",
                "info",
            )
            del tier_groups[1]

        # Sort providers within each tier by performance score (highest first)
        if pp:
            for tier_num in tier_groups:
                providers = tier_groups[tier_num]
                if len(providers) > 1:
                    scored = []
                    for p in providers:
                        score = pp.get_provider_score(p[1].lower())
                        scored.append((p, score))
                    scored.sort(key=lambda x: x[1], reverse=True)
                    tier_groups[tier_num] = [p for p, s in scored]
                    score_log = [(p[1].upper(), f"{s:.0f}") for p, s in scored]
                    g.log(f"  Tier {tier_num} sorted by score: {score_log}", "debug")

        sorted_tiers = sorted(tier_groups.keys())
        total_tiers = len(sorted_tiers)

        g.log(
            f"Tiered scraping: {total_tiers} tiers with {len(self.torrent_providers)} total providers "
            f"(threshold={tier_min_cached}, anime={is_anime})",
            "info",
        )
        for t in sorted_tiers:
            names = [p[1].upper() for p in tier_groups[t]]
            g.log(f"  Tier {t}: {names}", "info")

        # ── All-Tier Sweep: divide timeout evenly so every tier gets a slice ──
        _MIN_TIER_SECONDS = 4  # hard floor — no tier gets less than this
        all_tier_sweep = g.get_bool_setting('scraping.allTierSweep', False)
        tier_deadlines = {}
        per_tier_budget = 0.0
        if all_tier_sweep:
            # tier_min_cached is intentionally NOT zeroed out here so that the
            # Tier Skip Threshold setting is still honoured during the sweep.
            # If the cached source count meets the threshold after any tier, the
            # sweep will stop early just like the non-sweep path does.
            sweep_start = time.time()
            per_tier_budget = max(_MIN_TIER_SECONDS, self.timeout / max(len(sorted_tiers), 1))
            _t = sweep_start
            for _tn in sorted_tiers:
                _t += per_tier_budget
                tier_deadlines[_tn] = _t
            g.log(
                f"All-tier sweep: {len(sorted_tiers)} tiers, {per_tier_budget:.1f}s each "
                f"(timeout={self.timeout}s, floor={_MIN_TIER_SECONDS}s, threshold={tier_min_cached})",
                "info",
            )

        # ── Helper: thread-safe collector for parallel scraping ──
        class ThreadSafeCollector:
            def __init__(self):
                self._items = []
                self._lock = threading.Lock()
            def extend(self, items):
                with self._lock:
                    self._items.extend(items)
            @property
            def items(self):
                with self._lock:
                    return list(self._items)

        def _scrape_tier_providers(providers, collector):
            """Scrape all providers in a tier in parallel, collecting results."""
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(providers), 1)) as executor:
                futures = [
                    executor.submit(
                        self._get_provider_sources,
                        self.item_information,
                        provider,
                        'torrentCache',
                        self._process_torrent_source,
                        True,       # skip_cache_check
                        collector,  # result_collector
                    )
                    for provider in providers
                ]
                concurrent.futures.wait(futures)

        # ── State for background overlap scraping ──
        bg_thread = None        # Thread running the background scrape
        bg_collector = None     # ThreadSafeCollector with background results
        bg_tier_num = None      # Which tier is being scraped in background

        for idx, tier_num in enumerate(sorted_tiers):
            if self.canceled:
                g.log("Tiered scraping: Canceled, stopping", "info")
                break

            providers = tier_groups[tier_num]

            # ── Phase 1: Scrape this tier ──
            # If a background scrape was started for this tier by the previous
            # iteration's overlap, wait for it and use its results.
            if bg_thread is not None and bg_tier_num == tier_num:
                g.log(
                    f"Tiered scraping: Collecting background Tier {tier_num} scrape "
                    f"({len(providers)} providers, {self._get_cached_source_count()} cached so far)",
                    "info",
                )
                if all_tier_sweep:
                    # Deadline-aware join: don't let a slow background tier block the sweep
                    _join_timeout = max(0.5, tier_deadlines.get(tier_num, float('inf')) - time.time())
                    bg_thread.join(timeout=_join_timeout)
                    if bg_thread.is_alive():
                        g.log(
                            f"All-tier sweep: Tier {tier_num} bg scrape exceeded deadline — "
                            f"using {len(bg_collector.items)} partial results, advancing",
                            "warning",
                        )
                else:
                    bg_thread.join()
                tier_results = bg_collector.items
                g.log(
                    f"Tiered scraping: Tier {tier_num} scraping done (background overlap) — "
                    f"{len(tier_results)} torrents from {len(providers)} providers",
                    "info",
                )
                bg_thread = None
                bg_collector = None
                bg_tier_num = None
            else:
                # Normal foreground scrape (first tier, or background wasn't started)
                g.log(
                    f"Tiered scraping: Starting Tier {tier_num} "
                    f"({len(providers)} providers, {self._get_cached_source_count()} cached so far)",
                    "info",
                )

                collector = ThreadSafeCollector()

                # Add sentinel to keep main thread's keep-alive loop running
                cache_check_sentinel = f"CACHE_CHECK_TIER_{tier_num}"
                self.sources_information['statistics']['remainingProviders'].append(cache_check_sentinel)

                _scrape_tier_providers(providers, collector)

                tier_results = collector.items
                g.log(
                    f"Tiered scraping: Tier {tier_num} scraping done — "
                    f"{len(tier_results)} torrents from {len(providers)} providers",
                    "info",
                )

            # ── All-Tier Sweep: skip cache check entirely if tier is over budget ──
            if all_tier_sweep and time.time() > tier_deadlines.get(tier_num, float('inf')):
                g.log(
                    f"All-tier sweep: Tier {tier_num} over budget — skipping cache check, "
                    f"advancing to next tier",
                    "info",
                )
                try:
                    self.sources_information['statistics']['remainingProviders'].remove(
                        f"CACHE_CHECK_TIER_{tier_num}"
                    )
                except ValueError:
                    pass
                continue  # skip bg overlap + cache check + threshold gate for this tier

            # ── Phase 2: Cache check + overlapped next-tier scraping ──
            # Determine the next tier and start its scraping in background
            next_tier_num = sorted_tiers[idx + 1] if idx + 1 < len(sorted_tiers) else None

            if next_tier_num is not None and not self.canceled:
                next_providers = tier_groups[next_tier_num]
                bg_collector = ThreadSafeCollector()
                bg_tier_num = next_tier_num

                # Add sentinel for the background tier so main loop stays alive
                bg_sentinel = f"CACHE_CHECK_TIER_{next_tier_num}"
                self.sources_information['statistics']['remainingProviders'].append(bg_sentinel)

                bg_thread = threading.Thread(
                    target=_scrape_tier_providers,
                    args=(next_providers, bg_collector),
                    daemon=True,
                )
                bg_thread.start()
                g.log(
                    f"Tiered scraping: Overlap — started Tier {next_tier_num} scrape "
                    f"({len(next_providers)} providers) during Tier {tier_num} cache check",
                    "info",
                )

            # Run cache check for current tier (while next tier scrapes in background)
            # Ensure sentinel exists for current tier
            cache_check_sentinel = f"CACHE_CHECK_TIER_{tier_num}"
            if cache_check_sentinel not in self.sources_information['statistics']['remainingProviders']:
                self.sources_information['statistics']['remainingProviders'].append(cache_check_sentinel)

            if tier_results:
                start_time = time.time()
                if all_tier_sweep:
                    remaining_budget = max(1.0, tier_deadlines.get(tier_num, float('inf')) - time.time())
                    _cc_done = threading.Event()
                    _tr_snap = tier_results  # capture snapshot for closure

                    def _run_cache_check(_tr=_tr_snap, _done=_cc_done):
                        TorrentCacheCheck(self).torrent_cache_check(_tr, self.item_information)
                        _done.set()

                    _cc_thread = threading.Thread(target=_run_cache_check, daemon=True)
                    _cc_thread.start()
                    _completed = _cc_done.wait(timeout=remaining_budget)
                    if not _completed:
                        g.log(
                            f"All-tier sweep: Tier {tier_num} cache check timed out after "
                            f"{remaining_budget:.1f}s — using partial results",
                            "warning",
                        )
                else:
                    TorrentCacheCheck(self).torrent_cache_check(tier_results, self.item_information)
                g.log(
                    f"Tiered scraping: Tier {tier_num} batch cache check took "
                    f"{time.time() - start_time:.1f}s ({len(tier_results)} hashes)",
                    "debug",
                )

            # Remove current tier's sentinel — cache check done
            try:
                self.sources_information['statistics']['remainingProviders'].remove(cache_check_sentinel)
            except ValueError:
                pass

            # ── Phase 3: Check threshold ──
            cached_count = self._get_cached_source_count()
            g.log(
                f"Tiered scraping: Tier {tier_num} complete — {cached_count} cached sources total",
                "info",
            )

            remaining_tiers = [t for t in sorted_tiers if t > tier_num]
            if tier_min_cached > 0 and cached_count >= tier_min_cached and remaining_tiers:
                skipped_providers = []
                for t in remaining_tiers:
                    skipped_providers.extend([p[1].upper() for p in tier_groups[t]])
                g.log(
                    f"Tiered scraping: {cached_count} cached sources >= {tier_min_cached} threshold, "
                    f"skipping Tiers {remaining_tiers} ({len(skipped_providers)} providers: {skipped_providers})",
                    "info",
                )
                # Abandon background scrape — remove its sentinel so main loop can exit
                if bg_thread is not None:
                    g.log(
                        f"Tiered scraping: Abandoning background Tier {bg_tier_num} scrape (threshold met)",
                        "info",
                    )
                    try:
                        bg_sentinel = f"CACHE_CHECK_TIER_{bg_tier_num}"
                        self.sources_information['statistics']['remainingProviders'].remove(bg_sentinel)
                    except ValueError:
                        pass
                    # Don't join — let daemon thread finish on its own
                    bg_thread = None
                    bg_collector = None
                    bg_tier_num = None
                break

            # ── All-Tier Sweep: bank leftover time from fast tiers ──
            if all_tier_sweep and next_tier_num is not None:
                leftover = max(0.0, tier_deadlines.get(tier_num, 0.0) - time.time())
                elapsed = per_tier_budget - leftover
                g.log(
                    f"All-tier sweep: Tier {tier_num} used {elapsed:.1f}s of {per_tier_budget:.1f}s budget"
                    + (f" — banking {leftover:.1f}s to Tier {next_tier_num}" if leftover > 0 else ""),
                    "info",
                )
                if leftover > 0:
                    tier_deadlines[next_tier_num] += leftover


    def _create_adaptive_threads(self):
        for i in self.adaptive_providers:
            self.adaptive_threads.put(
                self._get_provider_sources, self.item_information, i, 'adaptive', self._process_adaptive_source
            )

    def _create_direct_threads(self):
        if not g.get_bool_setting("scraping.easynews", True):
            g.log("Easynews provider disabled in settings, skipping direct providers", "info")
            self.direct_providers = []
            return
        for i in self.direct_providers:
            self.direct_threads.put(
                self._get_provider_sources, self.item_information, i, 'direct', self._process_direct_source
            )

    def _check_local_torrent_database(self):
        if g.get_bool_setting('general.torrentCache'):
            self.window.set_text(
                g.get_language_string(30053),
                self.progress,
                self.timeout_progress,
                self.sources_information,
                self.runtime,
            )
            self._get_local_torrent_results()

    def _is_playable_source(self, filtered=False):
        stats = self.sources_information['statistics']
        stats = stats['filtered'] if filtered else stats
        return any(
            stats[stype]["total"] > 0
            for stype in ["torrentsCached", "cloudFiles", "adaptiveSources", "hosters", "directSources"]
        )

    def _finalise_results(self):
        monkey_requests.allow_provider_requests = False
        self._send_provider_stop_event()

        # Backfill seed data across all sources before assembling final list
        self._backfill_seed_data()

        uncached = [
            i
            for i in self.sources_information['allTorrents'].values()
            if i['hash'].lower() not in self.sources_information['cached_hashes']
        ]

        # Check to see if we have any playable unfiltered sources, if not do cache assist
        if not self._is_playable_source():
            self._build_cache_assist()
            g.cancel_playback()
            if self.silent:
                g.notification(g.ADDON_NAME, g.get_language_string(30055))
            return uncached, [], self.item_information

        # Return sources list
        sources_list = (
            list(self.sources_information['torrentCacheSources'].values())
            + list(self.sources_information['hosterSources'].values())
            + self.sources_information['cloudFiles']
            + self.sources_information['adaptiveSources']
            + self.sources_information['directSources']
        )

        # Re-stamp "(Local Cache)" on any source whose hash was in Tier 0.
        # store_torrent() may have overwritten the Tier 0 entry with a live
        # scraper result that had better size data, losing the label.
        # Also set _from_local_cache flag for the UI display layer.
        local_hashes = self.sources_information['local_cache_hashes']
        if local_hashes:
            restamped = 0
            for source in sources_list:
                if source.get('hash', '') in local_hashes:
                    source['_from_local_cache'] = True
                    provider = source.get('provider', '')
                    if '(Local Cache)' not in provider:
                        source['provider'] = f"{provider} (Local Cache)"
                        restamped += 1
            g.log(
                f"Local Cache: {len(local_hashes)} tracked hashes, "
                f"re-stamped {restamped}/{len(sources_list)} sources",
                "info",
            )

        return uncached, sources_list, self.item_information

    # ── Tracker name → scraper module mapping ──────────────────────────────
    # Maps tracker names (from Torrentio/AIOStreams name field, local cache
    # local cache provider names, etc.) to a4kScrapers torrent module names.
    # Keys are lowercase. Only trackers with working site scrapers are listed.
    TRACKER_TO_SCRAPER = {
        'thepiratebay': 'piratebay', 'tpb': 'piratebay', 'piratebay': 'piratebay',
        '1337x': 'leet', 'leet': 'leet',
        'yts': 'yts', 'yts.mx': 'yts', 'yify': 'yts',
        'eztv': 'eztv',
        'kickasstorrents': 'kickass2', 'kickass': 'kickass2', 'kat': 'kickass2', 'kickass2': 'kickass2',
        'nyaa': 'nyaa', 'nyaa.si': 'nyaa',
        'torrentdownload': 'torrentdownload', 'torrentdownloads': 'torrentdownload',
        'magnetdl': 'magnetdl',
        'torrentz2': 'torrentz2',
        'bitsearch': 'bitsearch',
        'animetosho': 'animetosho', 'animetosho.org': 'animetosho', 'animetosho.xyz': 'animetosho',
        'anidex': 'anirena', 'anidex.info': 'anirena', 'anidex.moe': 'anirena',  # AniDex removed — redirect to AniRena
        'anirena': 'anirena', 'anirena.com': 'anirena', 'www.anirena.com': 'anirena',
        'subsplease': 'subsplease', 'subsplease.org': 'subsplease',
        'tokyotosho': 'anirena', 'tokyotosho.info': 'anirena', 'tokyo toshokan': 'anirena',  # TT removed; redirect seed backfill to AniRena (replacement anime tracker)
        'nekobt': 'nekobt',
        'knaben': 'knaben',
    }

    def _backfill_seed_data(self):
        """Populate missing seed counts using real data sources only.

        Three stages, each only processes torrents still at seeds=0:

        Stage 1 — Cross-scraper backfill:
            The same hash may appear from multiple scrapers. If Torrentio
            returned it with seeds=247 and DMM returned it with seeds=0,
            use the 247. Cheap — no API calls, just a dict lookup.

        Stage 2 — Targeted site scraper:
            For torrents still at seeds=0 where we know the tracker
            (from Torrentio/AIOStreams name field, or from the original
            the original scraper name in local cache), fire up ONLY that
            specific site scraper to get real seed data. Groups by tracker
            so each site is hit at most once. Matches results by hash.

        Stage 3 — Hash-level max seed propagation:
            After stages 1-2, propagate the best known seed count for
            each hash across ALL debrid copies in torrentCacheSources.
            E.g. if hash X has PM=247, RD=0, TB=0, set all three to 247.

        Stage 4 — Write back to Tier 0 torrent cache DB.
        """
        try:
            all_torrents = self.sources_information['allTorrents']
            cached_sources = self.sources_information['torrentCacheSources']

            if not all_torrents and not cached_sources:
                return

            # ── Stage 1: Cross-scraper hash → max_seeds ─────────────────
            hash_max_seeds = {}
            hash_tracker = {}  # hash → tracker name (best known)
            for torrent in all_torrents.values():
                h = torrent.get('hash', '')
                if not h:
                    continue
                seeds = self._torrent_seeds(torrent)
                if seeds > hash_max_seeds.get(h, 0):
                    hash_max_seeds[h] = seeds
                # Collect tracker info from any source that has it
                tracker = self._get_tracker(torrent)
                if tracker and h not in hash_tracker:
                    hash_tracker[h] = tracker

            stage1_count = 0
            for tor_key, source in list(cached_sources.items()):  # snapshot to avoid dict-changed-size race
                if self._torrent_seeds(source) == 0:
                    h = source.get('hash', '')
                    if h in hash_max_seeds and hash_max_seeds[h] > 0:
                        source['seeds'] = hash_max_seeds[h]
                        stage1_count += 1

            # ── Stage 2: Targeted site scraper for remaining zeros ──────
            # Collect zero-seed hashes grouped by tracker
            tracker_hashes = {}  # scraper_module → set of hashes needing seeds
            for tor_key, source in list(cached_sources.items()):  # snapshot to avoid dict-changed-size race
                if self._torrent_seeds(source) > 0:
                    continue
                h = source.get('hash', '')
                if not h:
                    continue
                tracker = self._get_tracker(source) or hash_tracker.get(h, '')
                scraper_module = self.TRACKER_TO_SCRAPER.get(tracker.lower(), '') if tracker else ''
                if scraper_module:
                    tracker_hashes.setdefault(scraper_module, set()).add(h)

            stage2_count = 0
            site_seeds = {}
            if tracker_hashes:
                # Fire targeted scrapers and collect hash→seeds
                site_seeds = self._fetch_seeds_from_sites(tracker_hashes)
                for tor_key, source in cached_sources.items():
                    if self._torrent_seeds(source) == 0:
                        h = source.get('hash', '')
                        if h in site_seeds and site_seeds[h] > 0:
                            source['seeds'] = site_seeds[h]
                            stage2_count += 1
                # Also update allTorrents
                for h, torrent in all_torrents.items():
                    if self._torrent_seeds(torrent) == 0 and h in site_seeds and site_seeds[h] > 0:
                        torrent['seeds'] = site_seeds[h]

            # ── Stage 3: Hash-level max seed propagation ────────────────
            # Build hash → max seeds from torrentCacheSources (which now has
            # cross-scraper + site scraper data applied from stages 1-2)
            hash_best_seeds = {}
            for tor_key, source in cached_sources.items():
                h = source.get('hash', '')
                s = self._torrent_seeds(source)
                if h and s > hash_best_seeds.get(h, 0):
                    hash_best_seeds[h] = s

            # Also fold in allTorrents (may have seeds from scrapers that
            # didn't make it through cache check)
            for torrent in all_torrents.values():
                h = torrent.get('hash', '')
                s = self._torrent_seeds(torrent)
                if h and s > hash_best_seeds.get(h, 0):
                    hash_best_seeds[h] = s

            # Propagate: every debrid copy of a hash gets the best known seeds
            stage3_count = 0
            for tor_key, source in cached_sources.items():
                h = source.get('hash', '')
                best = hash_best_seeds.get(h, 0)
                if best > 0 and self._torrent_seeds(source) < best:
                    source['seeds'] = best
                    stage3_count += 1

            # Also propagate back to allTorrents
            for h, torrent in all_torrents.items():
                best = hash_best_seeds.get(h, 0)
                if best > 0 and self._torrent_seeds(torrent) < best:
                    torrent['seeds'] = best

            # ── Stage 4: Write back to Tier 0 torrent cache DB ──────────
            # Re-store torrents with updated seeds so Tier 0 has fresh data
            # next time. Uses REPLACE INTO so safe to re-write.
            try:
                # Collect all hashes that got real seed data from any stage
                all_updated = set()
                for h, best in hash_best_seeds.items():
                    if best > 0:
                        all_updated.add(h)
                if site_seeds:
                    all_updated.update(h for h in site_seeds if site_seeds[h] > 0)

                if all_updated and hasattr(self, 'torrent_cache') and self.torrent_cache:
                    updated_torrents = []
                    for t in all_torrents.values():
                        if t.get('hash', '') in all_updated:
                            # Clean copy for DB — strip runtime-only fields
                            clean = dict(t)
                            clean['provider'] = clean.get('provider', '').replace(' (Local Cache)', '')
                            clean.pop('_from_local_cache', None)
                            clean.pop('_cloud_miss', None)
                            updated_torrents.append(clean)
                    if updated_torrents:
                        self.torrent_cache.add_torrent(self.item_information, updated_torrents)
                        g.log(
                            f"Seed backfill: Wrote {len(updated_torrents)} updated torrents "
                            f"back to Tier 0 cache",
                            "info",
                        )
            except Exception as e:
                g.log(f"Seed backfill: Tier 0 write-back failed (non-fatal): {e}", "warning")

            total = stage1_count + stage2_count + stage3_count
            if total > 0:
                scrapers_used = list(tracker_hashes.keys()) if tracker_hashes else []
                g.log(
                    f"Seed backfill: {stage1_count} cross-scraper, "
                    f"{stage2_count} from site scrapers ({', '.join(scrapers_used)}), "
                    f"{stage3_count} hash-propagated",
                    "info",
                )

        except Exception as e:
            g.log(f"Seed backfill failed (non-fatal): {e}", "warning")

    @staticmethod
    def _get_tracker(source):
        """Extract tracker/site name from a torrent source dict.

        Checks (in order):
          1. Explicit 'tracker' field (set by Torrentio/AIOStreams)
          2. 'scraper' field if it's a known site name
          3. 'provider' field stripped of '(Local Cache)' suffix
        """
        # Explicit tracker from Torrentio/AIOStreams name parsing
        tracker = source.get('tracker', '')
        if tracker:
            return tracker

        # Scraper field — for direct site scrapers, this IS the site name
        scraper = source.get('scraper', '')
        if scraper and not any(scraper.lower().startswith(x) for x in ('torrentio', 'cached')):
            return scraper

        # Provider field — strip "(Local Cache)" suffix for Tier 0 results
        provider = source.get('provider', '')
        if provider:
            provider = provider.replace('(Local Cache)', '').strip()
            if provider and not any(provider.lower().startswith(x) for x in ('torrentio', 'cached')):
                return provider

        return ''

    def _fetch_seeds_from_sites(self, tracker_hashes):
        """Fire targeted site scrapers to get real seed counts for specific hashes.

        Args:
            tracker_hashes: dict of {scraper_module_name: set_of_hashes}
                e.g. {'piratebay': {'abc123', 'def456'}, 'eztv': {'ghi789'}}

        Returns:
            dict of {hash: seed_count} for all hashes found by site scrapers
        """
        hash_seeds = {}
        info = self.item_information

        # Build simple_info once
        if self.media_type == g.MEDIA_EPISODE:
            simple_info = self._build_simple_show_info(info)
        else:
            simple_info = self._build_simple_movie_info(info)

        for scraper_name, hashes in tracker_hashes.items():
            try:
                module_path = f'providers.a4kScrapers.en.torrent.{scraper_name}'
                provider_module = importlib.import_module(module_path)
                if not hasattr(provider_module, 'sources'):
                    continue

                provider_source = provider_module.sources()
                g.log(f"Seed backfill: Firing {scraper_name} for {len(hashes)} hashes", "info")

                if self.media_type == g.MEDIA_EPISODE:
                    if not hasattr(provider_source, 'episode'):
                        continue
                    results = provider_source.episode(simple_info, info)
                else:
                    if not hasattr(provider_source, 'movie'):
                        continue
                    try:
                        results = provider_source.movie(
                            info['info']['title'],
                            str(info['info']['year']),
                            info['info'].get('imdb_id'),
                            simple_info=simple_info,
                            info=info,
                        )
                    except TypeError:
                        results = provider_source.movie(
                            info['info']['title'],
                            str(info['info']['year']),
                            simple_info=simple_info,
                            info=info,
                        )

                if not results:
                    continue

                # Match by hash, collect seed data
                found = 0
                for result in results:
                    h = result.get('hash', '').lower()
                    seeds = result.get('seeds', 0)
                    if h and seeds and isinstance(seeds, int) and seeds > 0:
                        if h in hashes:
                            hash_seeds[h] = max(hash_seeds.get(h, 0), seeds)
                            found += 1

                g.log(
                    f"Seed backfill: {scraper_name} returned {len(results)} results, "
                    f"matched {found}/{len(hashes)} hashes with seed data",
                    "info",
                )

            except Exception as e:
                g.log(f"Seed backfill: {scraper_name} failed (non-fatal): {e}", "warning")

        return hash_seeds

    def _get_imdb_info(self):
        if self.media_type != 'movie':
            return
        # Confirm movie year against IMDb's information
        imdb_id = self.item_information['info'].get("imdb_id")
        if imdb_id is None:
            return
        import requests

        try:
            resp = self._imdb_suggestions(imdb_id)
            year = resp.get('y', self.item_information['info']['year'])
            if year is not None and year != self.item_information['info']['year']:
                self.item_information['info']['year'] = str(year)
        except requests.exceptions.ConnectionError as ce:
            g.log("Unable to obtain IMDB suggestions to confirm movie year", "warning")
            g.log(ce, "debug")

    @staticmethod
    def _imdb_suggestions(imdb_id):
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3 import Retry

            session = requests.Session()
            retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
            session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))

            resp = session.get(f'https://v2.sg.media-imdb.com/suggestion/t/{imdb_id}.json')
            resp = json.loads(resp.text)['d'][0]
            return resp
        except (ValueError, KeyError, IndexError):
            g.log("Failed to get IMDB suggestion", "warning")
            return {}

    def _send_provider_stop_event(self):
        for provider in self.running_providers:
            if hasattr(provider, 'cancel_operations') and callable(provider.cancel_operations):
                provider.cancel_operations()

    @staticmethod
    def _torrents_enabled():
        return bool(
            (g.get_bool_setting('premiumize.torrents') and g.premiumize_enabled())
            or (g.get_bool_setting('rd.torrents') and g.real_debrid_enabled())
            or (g.get_bool_setting('alldebrid.torrents') and g.all_debrid_enabled())
            or (g.get_bool_setting('torbox.torrents') and g.torbox_enabled())
            or (g.get_bool_setting('debridlink.torrents') and g.debridlink_enabled())
        )

    @staticmethod
    def _hosters_enabled():
        return bool(
            (g.get_bool_setting('premiumize.hosters') and g.premiumize_enabled())
            or (g.get_bool_setting('rd.hosters') and g.real_debrid_enabled())
            or (g.get_bool_setting('alldebrid.hosters') and g.all_debrid_enabled())
            or (g.get_bool_setting('torbox.hosters') and g.torbox_enabled())
            or (g.get_bool_setting('debridlink.hosters') and g.debridlink_enabled())
        )

    def _store_torrent_results(self, torrent_list):
        if len(torrent_list) == 0:
            return
        self.torrent_cache.add_torrent(self.item_information, torrent_list)

    def _clear_local_torrent_results(self):
        if g.get_bool_setting('general.torrentCache'):
            g.log("Clearing existing local torrent cache items", "info")
            self.torrent_cache.clear_item(self.item_information)

    def _get_local_torrent_results(self):
        relevant_torrents = self.torrent_cache.get_torrents(self.item_information)

        if len(relevant_torrents) > 0:
            for torrent in relevant_torrents:
                # Strip any previously baked-in "(Local Cache)" from DB to prevent doubling
                torrent['provider'] = torrent.get('provider', '').replace(' (Local Cache)', '')
                torrent['provider'] = f"{torrent['provider']} (Local Cache)"
                torrent['_from_local_cache'] = True

                # Track which hashes came from local cache — survives store_torrent overwrites
                self.sources_information['local_cache_hashes'].add(torrent.get('hash', ''))

                self._merge_torrents({torrent['hash']: torrent})

            TorrentCacheCheck(self).torrent_cache_check(relevant_torrents, self.item_information)

    @staticmethod
    def _get_best_torrent_to_cache(sources):
        sources = [i for i in sources if i.get('seeds', 0) != 0 and i.get("magnet")]

        for quality in [i for i in approved_qualities if i in source_utils.get_accepted_resolution_set()]:
            if quality_filter := [i for i in sources if i['quality'] == quality]:
                packtype_filter = [i for i in quality_filter if i['package'] in ['show', 'season']]

                sorted_list = sorted(packtype_filter, key=lambda k: k['seeds'], reverse=True)
                if len(sorted_list) > 0:
                    return sorted_list[0]
                package_type_list = [i for i in quality_filter if i['package'] == 'single']
                sorted_list = sorted(package_type_list, key=lambda k: k['seeds'], reverse=True)
                if len(sorted_list) > 0:
                    return sorted_list[0]

        return None

    def _build_cache_assist(self):
        if len(self.sources_information['allTorrents']) == 0:
            return
        valid_packages = {'show', 'season', 'single'}

        if self.media_type == 'episode' and self.item_information['is_airing']:
            valid_packages.remove('show')
            if int(self.item_information['info']['season']) >= int(self.item_information['season_count']):
                valid_packages.remove('season')

        sources = [i for i in self.sources_information['allTorrents'].values() if i['package'] in valid_packages]

        if g.get_bool_setting("general.autocache") and g.get_int_setting('general.cacheAssistMode') == 0:
            if sources := self._get_best_torrent_to_cache(sources):
                action_args = parse.quote(json.dumps(sources, default=tools.serialize_sets))
                xbmc.executebuiltin(f'RunPlugin({g.BASE_URL}?action=cacheAssist&action_args={action_args})')
        elif not self.silent:
            if confirmation := xbmcgui.Dialog().yesno(
                f'{g.ADDON_NAME} - {g.get_language_string(30308)}', g.get_language_string(30056)
            ):
                try:
                    window = ManualCacheWindow(
                        *SkinManager().confirm_skin_path('manual_caching.xml'),
                        item_information=self.item_information,
                        sources=sources,
                    )
                    window.doModal()
                finally:
                    del window

    def _init_providers(self):
        sys.path.append(g.ADDON_USERDATA_PATH)
        try:
            if g.ADDON_USERDATA_PATH not in sys.path:
                sys.path.append(g.ADDON_USERDATA_PATH)
                providers = importlib.import_module("providers")
            else:
                providers = reload_module(importlib.import_module("providers"))
        except ValueError:
            g.notification(g.ADDON_NAME, g.get_language_string(30443))
            g.log('No providers installed', 'warning')
            return

        providers_dict = providers.get_relevant(self.language)

        torrent_providers = providers_dict['torrent']
        hoster_providers = providers_dict['hosters']
        adaptive_providers = providers_dict['adaptive']
        direct_providers = providers_dict['direct']

        hoster_providers, torrent_providers = self._remove_duplicate_providers(torrent_providers, hoster_providers)

        self.hoster_domains = resolver.Resolver.get_hoster_list()
        self.torrent_providers = torrent_providers
        self.hoster_providers = hoster_providers
        self.adaptive_providers = adaptive_providers
        self.direct_providers = direct_providers
        self.host_domains = OrderedDict.fromkeys(
            [
                host[0].lower()
                for provider in self.hoster_domains['premium']
                for host in self.hoster_domains['premium'][provider]
            ]
        )
        self.host_names = OrderedDict.fromkeys(
            [
                host[1].lower()
                for provider in self.hoster_domains['premium']
                for host in self.hoster_domains['premium'][provider]
            ]
        )

    @staticmethod
    def _remove_duplicate_providers(torrent, hosters):
        temp_list = []
        filter_list = []
        for i in torrent:
            if i[1] not in filter_list:
                temp_list.append(i)
                filter_list.append(i[1])

        torrent = temp_list
        temp_list = []
        for i in hosters:
            if i[1] not in filter_list:
                temp_list.append(i)
                filter_list.append(i[1])

        hosters = temp_list

        return hosters, torrent

    def _exit_thread(self, provider_name):
        if provider_name in self.sources_information['statistics']['remainingProviders']:
            self.sources_information['statistics']['remainingProviders'].remove(provider_name)

    def _get_provider_sources(self, info, provider, provider_type, process_function,
                              skip_cache_check=False, result_collector=None):
        provider_name = provider[1].upper()
        perf_start = time.time()
        perf_result_count = 0
        perf_failed = False
        try:
            self.sources_information['statistics']['remainingProviders'].append(provider_name)
            provider_module = importlib.import_module(f'{provider[0]}.{provider[1]}')
            if not hasattr(provider_module, "sources"):
                g.log("Invalid provider, Source Class missing", "warning")
                return
            provider_source = provider_module.sources()

            if not hasattr(provider_source, self.media_type):
                g.log(f"Skipping provider: {provider_name} - Does not support {self.media_type} types", "warning")
                return

            self.running_providers.append(provider_source)

            try:
                if self.media_type == g.MEDIA_EPISODE:
                    simple_info = self._build_simple_show_info(info)

                    results = provider_source.episode(simple_info, info, apikeys=self._apikeys)
                else:
                    simple_info = self._build_simple_movie_info(info)

                    try:
                        results = provider_source.movie(
                            info['info']['title'],
                            str(info['info']['year']),
                            info['info'].get('imdb_id'),
                            simple_info=simple_info,
                            info=info,
                            apikeys=self._apikeys,
                        )
                    except TypeError:
                        results = provider_source.movie(
                            info['info']['title'], str(info['info']['year']), simple_info=simple_info, info=info
                        )
            except Exception:
                perf_failed = True
                raise

            if results is None:
                self.sources_information['statistics']['remainingProviders'].remove(provider_name)
                return

            if self.canceled:
                return

            perf_result_count = len(results) if results else 0

            if len(results) > 0:
                # Begin filling in optional dictionary returns
                for result in results:
                    process_function(result, provider_name, provider, info)

                if provider_type == "torrentCache":
                    torrent_results = {value['hash']: value for value in results if value['hash']}

                    self._store_torrent_results(torrent_results.values())

                    if self.canceled:
                        return

                    if skip_cache_check and result_collector is not None:
                        # Deferred batch mode: collect results, skip per-provider cache check
                        self._merge_torrents(torrent_results)
                        result_collector.extend(torrent_results.values())
                    else:
                        # Original mode: run cache check immediately
                        start_time = time.time()

                        self._merge_torrents(torrent_results)

                        TorrentCacheCheck(self).torrent_cache_check(list(torrent_results.values()), info)
                        g.log(f"{provider_name} cache check took {time.time() - start_time} seconds", "debug")
                else:
                    self.sources_information[f'{provider_type}Sources'] += results

            self.running_providers.remove(provider_source)

            return
        finally:
            self.sources_information['statistics']['remainingProviders'].remove(provider_name)
            # Record provider performance metrics
            self._record_provider_performance(
                provider_name, perf_start, perf_result_count, perf_failed
            )

    def _process_torrent_source(self, source, provider_name, provider_module, info):
        source["type"] = "torrent"
        source["release_title"] = source.get("release_title", provider_name)
        source["source"] = provider_name.upper()
        source["quality"] = source.get("quality", source_utils.get_quality(source["release_title"]))
        source["size"] = self._torrent_filesize(source, info)
        source["info"] = set(source.get("info", source_utils.get_info(source["release_title"])))
        source["seeds"] = source.get("seeds", self._torrent_seeds(source))
        source["provider_imports"] = provider_module
        source["provider"] = source.get("provider_name_override", provider_name.upper())
        source["hash"] = source.get("hash", self.hash_regex.findall(source["magnet"])[0]).lower()
        return source

    @staticmethod
    def _process_adaptive_source(source, provider_name, provider_module, info):
        source["type"] = "adaptive"
        source["release_title"] = source.get("release_title", provider_name)
        source["source"] = provider_name.upper()
        source["quality"] = source.get("quality", source_utils.get_quality(source["release_title"]))
        source["size"] = source.get("size", "Variable")
        source["info"] = set(source.get("info", {}))
        source["provider_imports"] = provider_module
        source["provider"] = source.get("provider_name_override", provider_name.upper())
        return source

    @staticmethod
    def _process_direct_source(source, provider_name, provider_module, info):
        source['type'] = 'direct'
        source['release_title'] = source.get("release_title", provider_name)
        source['source'] = provider_name.upper()
        source['quality'] = source.get("quality", source_utils.get_quality(source['release_title']))
        source['size'] = source.get("size", "Variable")
        source['info'] = set(source.get("info", {}))
        source['provider_imports'] = provider_module
        source['provider'] = source.get('provider_name_override', provider_name.upper())
        return source

    def _do_hoster_episode(self, provider_source, provider_name, info):
        if not hasattr(provider_source, 'tvshow'):
            return
        imdb, tvdb, title, localtitle, aliases, year = self._build_hoster_variables(info, 'tvshow')

        if self.canceled:
            self._exit_thread(provider_name)
            return

        url = provider_source.tvshow(imdb, tvdb, title, localtitle, aliases, year)

        if self.canceled:
            self._exit_thread(provider_name)
            return

        imdb, tvdb, title, premiered, season, episode = self._build_hoster_variables(info, 'episode')

        if self.canceled:
            self._exit_thread(provider_name)
            return

        url = provider_source.episode(url, imdb, tvdb, title, premiered, season, episode)

        if self.canceled:
            self._exit_thread(provider_name)
            return

        return url

    def _do_hoster_movie(self, provider_source, provider_name, info):
        if not hasattr(provider_source, 'movie'):
            self._exit_thread(provider_name)
            return
        imdb, title, localtitle, aliases, year = self._build_hoster_variables(info, 'movie')
        return provider_source.movie(imdb, title, localtitle, aliases, year)

    def _get_hosters(self, info, provider):
        provider_name = provider[1].upper()
        self.sources_information['statistics']['remainingProviders'].append(provider_name.upper())
        try:
            provider_module = importlib.import_module(f'{provider[0]}.{provider[1]}')
            if hasattr(provider_module, "source"):
                provider_class = provider_module.source()
            else:
                self._exit_thread(provider_name)
                return

            self.running_providers.append(provider_class)

            if self.media_type == g.MEDIA_EPISODE:
                sources = self._do_hoster_episode(provider_class, provider_name, info)
            else:
                sources = self._do_hoster_movie(provider_class, provider_name, info)

            if not sources:
                self._exit_thread(provider_name)
                return

            host_dict, hostpr_dict = self._build_hoster_variables(info, 'sources')

            if self.canceled:
                self._exit_thread(provider_name)
                return

            sources = provider_class.sources(sources, host_dict, hostpr_dict)

            if not sources:
                g.log(f'{provider_name}: Found No Sources', 'info')
                return

            if self.media_type == g.MEDIA_EPISODE:
                title = f"{self.item_information['info']['tvshowtitle']} - {self.item_information['info']['title']}"
            else:
                title = f"{self.item_information['info']['title']} ({self.item_information['info']['year']})"

            for source in sources:
                source.update(
                    {
                        "type": "hoster",
                        "release_title": source.get('release_title', title),
                        "source": source['source'].upper().split('.')[0],
                        "size": source.get('size', '0'),
                        "info": source.get('info', []),
                        "provider_imports": provider,
                        "provider": source.get('provider_name_override', provider_name.upper()),
                    }
                )

            sources1 = [i for i in sources for host in self.host_domains if host in i['url']]
            sources2 = [i for i in sources if i['source'].lower() not in self.host_names and i['direct']]

            sources = sources1 + sources2

            self._debrid_hoster_duplicates(sources)
            self._exit_thread(provider_name)

        finally:
            with contextlib.suppress(ValueError):
                self.sources_information['statistics']['remainingProviders'].remove(provider_name)

    def _user_cloud_inspection(self):
        self.sources_information['statistics']['remainingProviders'].append("Cloud Inspection")
        try:
            thread_pool = ThreadPool()
            if self.media_type == g.MEDIA_EPISODE:
                simple_info = self._build_simple_show_info(self.item_information)
            else:
                simple_info = self._build_simple_movie_info(self.item_information)

            cloud_scrapers = [
                {
                    "setting": "premiumize.cloudInspection",
                    "provider": PremiumizeCloudScraper,
                    "enabled": g.premiumize_enabled(),
                },
                {
                    "setting": "rd.cloudInspection",
                    "provider": RealDebridCloudScraper,
                    "enabled": g.real_debrid_enabled(),
                },
                {
                    "setting": "alldebrid.cloudInspection",
                    "provider": AllDebridCloudScraper,
                    "enabled": g.all_debrid_enabled(),
                },
                {
                    "setting": "torbox.cloudInspection",
                    "provider": TorBoxCloudScraper,
                    "enabled": g.torbox_enabled(),
                },
                {
                    "setting": "debridlink.cloudInspection",
                    "provider": DebridLinkCloudScraper,
                    "enabled": g.debridlink_enabled(),
                },
            ]

            for cloud_scraper in cloud_scrapers:
                if cloud_scraper['enabled'] and g.get_bool_setting(cloud_scraper['setting']):
                    self.cloud_scrapers.append(cloud_scraper['provider'])
                    thread_pool.put(
                        cloud_scraper['provider'](self._prem_terminate).get_sources, self.item_information, simple_info
                    )

            sources = thread_pool.wait_completion()
            self.sources_information['cloudFiles'] = sources or []

        finally:
            self.sources_information['statistics']['remainingProviders'].remove("Cloud Inspection")

    def _torbox_usenet_search(self):
        """Search TorBox's usenet index for the current item.

        Calls TorBox's search-api.torbox.app/usenet/imdb:{id} endpoint.
        Pre-cached results are added directly to torrentCacheSources (bypassing
        normal torrent cache check since NZB hashes aren't torrent info_hashes).
        Uncached results are added to allTorrents for display / uncached resolution.

        Reference: POV torboxnews.py — Seren equivalent built into the pipeline
        rather than as an external scraper package."""
        self.sources_information['statistics']['remainingProviders'].append("TorBox Usenet")
        try:
            import hashlib
            tb = torbox.TorBox()

            # Build search params from item_information
            info = self.item_information.get('info', {})
            imdb_id = info.get('imdb_id')
            if not imdb_id:
                g.log("TorBox Usenet: No IMDB ID available, skipping", "info")
                return

            season = info.get('season') if self.media_type == g.MEDIA_EPISODE else None
            episode = info.get('episode') if self.media_type == g.MEDIA_EPISODE else None

            g.log(
                f"TorBox Usenet: Searching imdb:{imdb_id}"
                + (f" S{season}E{episode}" if season else ""),
                "info",
            )

            results = tb.search_usenet(imdb_id, season, episode)
            if not results:
                g.log("TorBox Usenet: No results", "info")
                return

            # Build title matching data (same approach as cloud scrapers)
            show_title = ""
            aliases = set()
            if self.media_type == g.MEDIA_EPISODE:
                show_title = source_utils.clean_title(
                    info.get('tvshowtitle', '') or info.get('title', '')
                )
                if self.media_type == g.MEDIA_EPISODE:
                    simple_info = self._build_simple_show_info(self.item_information)
                    alias_list = simple_info.get('show_aliases', [])
                    aliases = {source_utils.clean_title(a) for a in alias_list if a}
                    aliases.add(show_title)
                    aliases.discard("")
                    ep_filter = source_utils.get_filter_single_episode_fn(simple_info)
                    season_filter = source_utils.get_filter_season_pack_fn(simple_info)
                    show_filter = source_utils.get_filter_show_pack_fn(simple_info)
            else:
                simple_info = {
                    'year': info.get('year'),
                    'title': info.get('title'),
                }

            cached_count = 0
            uncached_count = 0
            skipped_count = 0
            user_engines_only = g.get_bool_setting('torbox.usenetUserEnginesOnly', False)

            for item in results:
                try:
                    if user_engines_only and not item.get('user_search'):
                        continue

                    raw_title = item.get('raw_title', '')
                    if not raw_title:
                        continue

                    nzb_url = item.get('nzb', '')
                    if not nzb_url:
                        continue

                    # Hash: use API hash or fall back to MD5 of NZB URL
                    hash_value = item.get('hash') or hashlib.md5(
                        nzb_url.encode('utf-8')
                    ).hexdigest()
                    hash_value = hash_value.lower()

                    # Title filter — match show/movie title
                    clean = source_utils.clean_title(raw_title)
                    if self.media_type == g.MEDIA_EPISODE:
                        if aliases and not any(a in clean for a in aliases if a):
                            skipped_count += 1
                            continue
                        if not (ep_filter(clean) or season_filter(clean) or show_filter(clean)):
                            skipped_count += 1
                            continue
                    else:
                        if not source_utils.filter_movie_title(
                            None, clean, info.get('title', ''), simple_info
                        ):
                            skipped_count += 1
                            continue

                    # Extract metadata
                    try:
                        size_bytes = int(item.get('size', 0))
                    except (ValueError, TypeError):
                        size_bytes = 0
                    size_mb = round(size_bytes / (1024 * 1024), 2)

                    try:
                        seeds = int(item.get('last_known_seeders', 0))
                    except (ValueError, TypeError):
                        seeds = 0

                    quality = source_utils.get_quality(raw_title)
                    info_tags = source_utils.get_info(raw_title)
                    is_cached = bool(item.get('cached', False))

                    source_dict = {
                        'type': 'torrent',
                        'release_title': raw_title,
                        'hash': hash_value,
                        'size': size_mb,
                        'seeds': seeds,
                        'source': 'TORBOXNEWS',
                        'provider': 'TORBOXNEWS',
                        'quality': quality,
                        'info': info_tags if isinstance(info_tags, list) else list(info_tags),
                        'language': 'en',
                        'debrid_provider': 'torbox',
                        'nzb_url': nzb_url,
                        # No magnet for NZB sources — resolver detects nzb_url
                    }

                    if is_cached:
                        # Add directly to cached sources (bypasses torrent cache check)
                        tor_key = hash_value + 'torbox'
                        self.sources_information['cached_hashes'].add(hash_value)
                        if tor_key not in self.sources_information['torrentCacheSources']:
                            self.sources_information['torrentCacheSources'][tor_key] = source_dict
                        cached_count += 1
                    else:
                        # Add to allTorrents for uncached display / fallback
                        if hash_value not in self.sources_information['allTorrents']:
                            self.sources_information['allTorrents'][hash_value] = source_dict
                        uncached_count += 1

                except Exception:
                    continue

            g.log(
                f"TorBox Usenet: {len(results)} results → "
                f"{cached_count} cached, {uncached_count} uncached, "
                f"{skipped_count} filtered out",
                "info",
            )

        except Exception as e:
            g.log(f"TorBox Usenet search failed: {e}", "warning")
        finally:
            self.sources_information['statistics']['remainingProviders'].remove("TorBox Usenet")

    @staticmethod
    def _color_number(number):

        if int(number) > 0:
            return g.color_string(number, 'green')
        else:
            return g.color_string(number, 'red')

    def _update_progress(self):
        def _get_quality_count_dict(source_list):
            _4k = 0
            _1080p = 0
            _720p = 0
            _sd = 0
            _variable = 0

            for source in source_list:
                if '4K' in source['quality']:
                    _4k += 1
                elif '1080p' in source['quality']:
                    _1080p += 1
                elif '720p' in source['quality']:
                    _720p += 1
                elif 'SD' in source['quality']:
                    _sd += 1
                elif source["quality"] in ["Unknown", "Variable"]:
                    _variable += 1

            return {
                "4K": _4k,
                "1080p": _1080p,
                "720p": _720p,
                "SD": _sd,
                "total": _4k + _1080p + _720p + _sd + _variable,
            }

        def _get_total_quality_dict(quality_dict_list):
            total_counter = Counter()

            for quality_dict in quality_dict_list:
                total_counter.update(quality_dict)

            return dict(total_counter)

        # Get qualities by source type and store result
        self.sources_information['statistics']['torrents'] = _get_quality_count_dict(
            list(self.sources_information['allTorrents'].values())
        )
        self.sources_information['statistics']['torrentsCached'] = _get_quality_count_dict(
            list(self.sources_information['torrentCacheSources'].values())
        )
        self.sources_information['statistics']['hosters'] = _get_quality_count_dict(
            list(self.sources_information['hosterSources'].values())
        )
        self.sources_information['statistics']['cloudFiles'] = _get_quality_count_dict(
            self.sources_information['cloudFiles']
        )
        self.sources_information['statistics']['adaptiveSources'] = _get_quality_count_dict(
            self.sources_information['adaptiveSources']
        )
        self.sources_information['statistics']['directSources'] = _get_quality_count_dict(
            self.sources_information['directSources']
        )

        self.sources_information['statistics']['totals'] = _get_total_quality_dict(
            [
                self.sources_information['statistics']['torrents'],
                self.sources_information['statistics']['hosters'],
                self.sources_information['statistics']['cloudFiles'],
                self.sources_information['statistics']['adaptiveSources'],
                self.sources_information['statistics']['directSources'],
            ]
        )

        # Get qualities by source type after source filtering and store result
        self.sources_information['statistics']['filtered']['torrents'] = _get_quality_count_dict(
            self.source_sorter.filter_sources(list(self.sources_information['allTorrents'].values()))
        )
        self.sources_information['statistics']['filtered']['torrentsCached'] = _get_quality_count_dict(
            self.source_sorter.filter_sources(list(self.sources_information['torrentCacheSources'].values()))
        )
        self.sources_information['statistics']['filtered']['hosters'] = _get_quality_count_dict(
            self.source_sorter.filter_sources(list(self.sources_information['hosterSources'].values()))
        )
        self.sources_information['statistics']['filtered']['cloudFiles'] = _get_quality_count_dict(
            self.source_sorter.filter_sources(self.sources_information['cloudFiles'])
        )
        self.sources_information['statistics']['filtered']['adaptiveSources'] = _get_quality_count_dict(
            self.source_sorter.filter_sources(self.sources_information['adaptiveSources'])
        )
        self.sources_information['statistics']['filtered']['directSources'] = _get_quality_count_dict(
            self.source_sorter.filter_sources(self.sources_information['directSources'])
        )
        self.sources_information['statistics']['filtered']['totals'] = _get_total_quality_dict(
            [
                self.sources_information['statistics']['filtered']['torrentsCached'],
                self.sources_information['statistics']['filtered']['hosters'],
                self.sources_information['statistics']['filtered']['cloudFiles'],
                self.sources_information['statistics']['filtered']['adaptiveSources'],
                self.sources_information['statistics']['filtered']['directSources'],
            ]
        )

    @staticmethod
    def _build_simple_show_info(info):
        simple_info = {
            'show_title': info['info'].get('tvshowtitle', ''),
            'episode_title': info['info'].get('originaltitle', ''),
            'year': str(info['info'].get('tvshow.year', info['info'].get('year', ''))),
            'season_number': str(info['info']['season']),
            'episode_number': str(info['info']['episode']),
            'show_aliases': info['info'].get('aliases', []),
            'country': info['info'].get('country_origin', ''),
            'no_seasons': str(info.get('season_count', '')),
            'absolute_number': str(info.get('absoluteNumber', '')),
            'is_airing': info.get('is_airing', False),
            'no_episodes': str(info.get('episode_count', '')),
            'isanime': False,
        }

        if '.' in simple_info['show_title']:
            simple_info['show_aliases'].append(source_utils.clean_title(simple_info['show_title'].replace('.', '')))

        # Auto-clean: add torrent-friendly variant (strips colons, apostrophes, &, etc.)
        if g.get_bool_setting('general.smartSearch', True) and g.get_bool_setting('general.smartSearch.tvshows', True):
            cleaned = _torrent_clean_title(simple_info['show_title'])
            if cleaned and cleaned not in simple_info['show_aliases']:
                simple_info['show_aliases'].append(cleaned)

        _genre_list = info['info'].get('genre', [])
        if not isinstance(_genre_list, list):
            _genre_list = [_genre_list] if _genre_list else []
        _genre_lower = [g.lower() for g in _genre_list]
        if any('anime' in g for g in _genre_lower):
            simple_info['isanime'] = True
        elif any('animation' in g for g in _genre_lower):
            _c = (simple_info.get('country', '') or '').upper()
            simple_info['isanime'] = _c in ('JP', 'JPN', 'JAPAN', 'CN', 'CHN', 'CHINA')

        # Title substitution: replace show_title with user-defined alternative
        if g.get_bool_setting('general.titleSubs'):
            try:
                from resources.lib.database.titleSubs import TitleSubsCache
                substitute = TitleSubsCache().get_substitute(simple_info['show_title'])
                if substitute:
                    original = simple_info['show_title']
                    simple_info['show_title'] = substitute
                    # Keep original as alias so scrapers can still match it
                    if original not in simple_info['show_aliases']:
                        simple_info['show_aliases'].append(original)
                    g.log(f"Title substitution: '{original}' → '{substitute}'", "info")
            except Exception as e:
                g.log(f"Title substitution lookup failed: {e}", "warning")

        # Asian drama title enrichment (Session 48): add native-language titles for CJK content
        # Gated on country_origin (mirrors anime gate on isanime) — mutually exclusive with anime path
        if (not simple_info['isanime']
                and simple_info.get('country', '').upper() in ASIAN_DRAMA_COUNTRIES
                and g.get_bool_setting('general.smartSearch', True)
                and g.get_bool_setting('general.smartSearch.asiandrama', True)):
            try:
                # 1. Merge aliases passed from TMDb Helper
                # Primary: window property (reliable — bypasses URL encoding pipeline)
                # Fallback: action_args (for player JSONs with {aliases_urlencoded} template var)
                tmdbhelper_aliases = []
                try:
                    import xbmcgui
                    _aliases_prop = xbmcgui.Window(10000).getProperty('TMDbHelper.AsianDramaAliases')
                    if _aliases_prop:
                        import json as _json
                        _decoded = _json.loads(_aliases_prop)
                        if isinstance(_decoded, list) and _decoded:
                            tmdbhelper_aliases = _decoded
                except Exception:
                    pass
                if not tmdbhelper_aliases:
                    tmdbhelper_aliases = info.get('action_args', {}).get('tmdbhelper_aliases', [])
                for alias in tmdbhelper_aliases:
                    if alias and alias not in simple_info['show_aliases'] and alias.lower() != simple_info['show_title'].lower():
                        simple_info['show_aliases'].append(alias)

                # 2. Add originaltitle (TMDb original_name — native language title)
                # For episodes, use tvshow.originaltitle (show-level); for shows, use originaltitle
                original_title = info['info'].get('tvshow.originaltitle', '') or info['info'].get('originaltitle', '')
                if original_title and original_title != simple_info['show_title']:
                    if original_title not in simple_info['show_aliases']:
                        simple_info['show_aliases'].append(original_title)
                    # Also add torrent-cleaned variant
                    cleaned_original = _torrent_clean_title(original_title)
                    if cleaned_original and cleaned_original not in simple_info['show_aliases']:
                        simple_info['show_aliases'].append(cleaned_original)

                # 3. Clean CJK decoration from all aliases (tildes, brackets, etc.)
                cleaned_aliases = []
                for alias in list(simple_info['show_aliases']):
                    cleaned = _clean_cjk_alias(alias)
                    if (cleaned and cleaned not in simple_info['show_aliases']
                            and cleaned not in cleaned_aliases
                            and cleaned.lower() != simple_info['show_title'].lower()):
                        cleaned_aliases.append(cleaned)
                simple_info['show_aliases'].extend(cleaned_aliases)

                g.log(f"Asian drama enrichment: country={simple_info['country']}, "
                      f"original_title='{original_title}', "
                      f"tmdbhelper_injected={len(tmdbhelper_aliases)}, "
                      f"total_aliases={len(simple_info['show_aliases'])}: "
                      f"{simple_info['show_aliases']}", "notice")
            except Exception as e:
                g.log(f"Asian drama title enrichment failed: {e}", "warning")

        # Smart anime search: enrich aliases from AniList + MAL, fix season/episode numbering
        if simple_info['isanime'] and g.get_bool_setting('general.smartSearch', True) and g.get_bool_setting('general.smartSearch.anime', True):
            try:
                from resources.lib.modules.anime.anilist_mapping import get_anime_ids
                imdb_id = info['info'].get('imdb_id', '')
                tmdb_id = info['info'].get('tmdb_show_id', '') or info['info'].get('tmdb_id', '')
                anime_ids = get_anime_ids(imdb_id=imdb_id or None, tmdb_id=tmdb_id or None)
                g.log(f"Anime enrichment: imdb={imdb_id}, tmdb={tmdb_id} → IDs={anime_ids}", "notice")

                if anime_ids:
                    # Store all anime database IDs in simple_info for scrapers
                    # (anidb_id, mal_id, anilist_id are useful for ID-based filtering;
                    # tvdb_season/tvdb_part drive cour-correction for split-cour anime)
                    for id_key in ('anilist_id', 'mal_id', 'anidb_id', 'kitsu_id',
                                   'thetvdb_id', 'themoviedb_id', 'simkl_id',
                                   'thetvdb_season', 'thetvdb_part'):
                        val = anime_ids.get(id_key)
                        if val is not None:
                            simple_info[id_key] = val

                    # Enrich title aliases from AniList + MAL
                    from resources.lib.modules.anime.smart_search import get_enriched_aliases
                    extra_aliases = get_enriched_aliases(
                        anilist_id=anime_ids.get('anilist_id'),
                        mal_id=anime_ids.get('mal_id'),
                        anidb_id=anime_ids.get('anidb_id'),
                    )
                    g.log(f"Anime enrichment: {len(extra_aliases)} aliases from AniList+MAL+AniDB: {extra_aliases}", "notice")
                    for alias in extra_aliases:
                        if alias and alias not in simple_info['show_aliases'] and alias.lower() != simple_info['show_title'].lower():
                            simple_info['show_aliases'].append(alias)

                    # Fix season/episode numbering for cour splits
                    from resources.lib.modules.anime.smart_search import get_alternative_episode_numbers
                    alt_ep = get_alternative_episode_numbers(
                        anilist_id=anime_ids.get('anilist_id'),
                        trakt_season=int(simple_info['season_number']),
                        trakt_episode=int(simple_info['episode_number']),
                        absolute_number=simple_info.get('absolute_number'),
                    )
                    if alt_ep:
                        g.log(f"Anime enrichment: cour correction {alt_ep}", "notice")
                        if 'alt_season' in alt_ep and 'alt_episode' in alt_ep:
                            simple_info['alternative_season'] = str(alt_ep['alt_season'])
                            simple_info['alternative_episode'] = str(alt_ep['alt_episode'])
                            # Also write into item_information['info'] so the debrid cache-check
                            # workers (which receive item_information, not simple_info) can pass
                            # the correct cour-corrected season/episode to external cache APIs.
                            info['info']['alternative_season'] = simple_info['alternative_season']
                            info['info']['alternative_episode'] = simple_info['alternative_episode']
                            # Update season_number/episode_number so cloud scraper file-match
                            # regex (get_filter_single_episode_fn) uses the cour-corrected values.
                            # Without this, a saved cloud file named e.g. "Frieren S2E02.mkv"
                            # would never match a regex built for S1E30.
                            simple_info['season_number'] = simple_info['alternative_season']
                            simple_info['episode_number'] = simple_info['alternative_episode']
                        if 'absolute' in alt_ep and not simple_info.get('absolute_number'):
                            simple_info['absolute_number'] = str(alt_ep['absolute'])
                else:
                    g.log(f"Anime enrichment: ARM+Simkl returned None for imdb={imdb_id}, tmdb={tmdb_id}", "warning")
            except Exception as e:
                g.log(f"Smart anime search enrichment failed: {e}", "warning")

        g.log(f"Anime scraper handoff: isanime={simple_info['isanime']}, title='{simple_info['show_title']}', "
              f"aliases={simple_info['show_aliases']}, abs={simple_info.get('absolute_number','')}, "
              f"alt_s={simple_info.get('alternative_season','')}, alt_e={simple_info.get('alternative_episode','')}, "
              f"anidb={simple_info.get('anidb_id','')}, mal={simple_info.get('mal_id','')}, "
              f"kitsu={simple_info.get('kitsu_id','')}, simkl={simple_info.get('simkl_id','')}, "
              f"tvdb_season={simple_info.get('thetvdb_season','')}, tvdb_part={simple_info.get('thetvdb_part','')}", "notice")

        return simple_info

    @staticmethod
    def _build_simple_movie_info(info):
        simple_info = {
            'title': info['info'].get('title', ''),
            'year': str(info['info'].get('year', '')),
            'aliases': info['info'].get('aliases', []),
            'country': info['info'].get('country_origin', ''),
        }

        if '.' in simple_info['title']:
            simple_info['aliases'].append(source_utils.clean_title(simple_info['title'].replace('.', '')))

        # Auto-clean: add torrent-friendly variant (strips colons, apostrophes, &, etc.)
        if g.get_bool_setting('general.smartSearch', True) and g.get_bool_setting('general.smartSearch.movies', True):
            cleaned = _torrent_clean_title(simple_info['title'])
            if cleaned and cleaned not in simple_info['aliases']:
                simple_info['aliases'].append(cleaned)

        # Title substitution: replace title with user-defined alternative
        if g.get_bool_setting('general.titleSubs'):
            try:
                from resources.lib.database.titleSubs import TitleSubsCache
                substitute = TitleSubsCache().get_substitute(simple_info['title'])
                if substitute:
                    original = simple_info['title']
                    simple_info['title'] = substitute
                    if original not in simple_info['aliases']:
                        simple_info['aliases'].append(original)
                    g.log(f"Title substitution: '{original}' → '{substitute}'", "info")
            except Exception as e:
                g.log(f"Title substitution lookup failed: {e}", "warning")

        # Asian drama title enrichment for movies (Session 48)
        if (simple_info.get('country', '').upper() in ASIAN_DRAMA_COUNTRIES
                and g.get_bool_setting('general.smartSearch', True)
                and g.get_bool_setting('general.smartSearch.asiandrama', True)):
            try:
                # 1. Merge aliases passed from TMDb Helper
                # Primary: window property (reliable — bypasses URL encoding pipeline)
                # Fallback: action_args (for player JSONs with {aliases_urlencoded} template var)
                tmdbhelper_aliases = []
                try:
                    import xbmcgui
                    _aliases_prop = xbmcgui.Window(10000).getProperty('TMDbHelper.AsianDramaAliases')
                    if _aliases_prop:
                        import json as _json
                        _decoded = _json.loads(_aliases_prop)
                        if isinstance(_decoded, list) and _decoded:
                            tmdbhelper_aliases = _decoded
                except Exception:
                    pass
                if not tmdbhelper_aliases:
                    tmdbhelper_aliases = info.get('action_args', {}).get('tmdbhelper_aliases', [])
                for alias in tmdbhelper_aliases:
                    if alias and alias not in simple_info['aliases'] and alias.lower() != simple_info['title'].lower():
                        simple_info['aliases'].append(alias)

                # 2. Add originaltitle (TMDb original_title — native language title)
                original_title = info['info'].get('originaltitle', '')
                if original_title and original_title != simple_info['title']:
                    if original_title not in simple_info['aliases']:
                        simple_info['aliases'].append(original_title)
                    cleaned_original = _torrent_clean_title(original_title)
                    if cleaned_original and cleaned_original not in simple_info['aliases']:
                        simple_info['aliases'].append(cleaned_original)

                # 3. Clean CJK decoration from all aliases
                cleaned_aliases = []
                for alias in list(simple_info['aliases']):
                    cleaned = _clean_cjk_alias(alias)
                    if (cleaned and cleaned not in simple_info['aliases']
                            and cleaned not in cleaned_aliases
                            and cleaned.lower() != simple_info['title'].lower()):
                        cleaned_aliases.append(cleaned)
                simple_info['aliases'].extend(cleaned_aliases)

                g.log(f"Asian drama movie enrichment: country={simple_info['country']}, "
                      f"original_title='{original_title}', "
                      f"tmdbhelper_injected={len(tmdbhelper_aliases)}, "
                      f"total_aliases={len(simple_info['aliases'])}: "
                      f"{simple_info['aliases']}", "notice")
            except Exception as e:
                g.log(f"Asian drama movie title enrichment failed: {e}", "warning")

        return simple_info

    def _build_hoster_variables(self, info, media_type):

        info = copy.deepcopy(info)

        if media_type == 'tvshow':
            return self.__build_hoster_tvshow_variables(info)
        elif media_type == 'episode':
            return self.__build_hoster_episode_variables(info)
        elif media_type == 'movie':
            return self.__build_hoster_movie_variables(info)
        elif media_type == 'sources':
            hostpr_dict = [host[0] for debrid in self.hoster_domains['premium'].values() for host in debrid]
            host_dict = self.hoster_domains['free']
            return host_dict, hostpr_dict

    @staticmethod
    def __build_hoster_movie_variables(info):
        imdb = info['info'].get('imdb_id')
        title = info['info'].get('originaltitle')
        localtitle = info['info'].get('title')
        aliases = info['info'].get('aliases', [])
        year = str(info['info'].get('year'))
        return imdb, title, localtitle, aliases, year

    @staticmethod
    def __build_hoster_episode_variables(info):
        imdb = info['info'].get('imdb_id')
        tvdb = info['info'].get('tvdb_id')
        title = info['info'].get('title')
        premiered = info['info'].get('premiered')
        season = str(info['info'].get('season'))
        episode = str(info['info'].get('episode'))
        return imdb, tvdb, title, premiered, season, episode

    @staticmethod
    def __build_hoster_tvshow_variables(info):
        imdb = info['info'].get('imdb_id')
        tvdb = info['info'].get('tvdb_id')
        title = info['info'].get('tvshowtitle')
        localtitle = ''
        aliases = info['info'].get('aliases', [])
        if '.' in title:
            aliases.append(source_utils.clean_title(title.replace('.', '')))
        return imdb, tvdb, title, localtitle, aliases, str(info['info']['year'])

    def _debrid_hoster_duplicates(self, sources):
        updated_sources = {}
        for provider in self.hoster_domains['premium']:
            for hoster in self.hoster_domains['premium'][provider]:
                for source in sources:
                    if hoster[1].lower() == source['source'].lower() or hoster[0].lower() in str(source['url']).lower():
                        source['debrid_provider'] = provider
                        updated_sources[f"{provider}_{source['url'].lower()}"] = source
        self.sources_information['hosterSources'].update(updated_sources)

    def _get_pre_term_min(self):
        return (
            g.get_int_setting('preem.tvres') + 1
            if self.media_type == 'episode'
            else g.get_int_setting('preem.movieres') + 1
        )

    def _get_filtered_count_by_resolutions(self, resolutions, quality_count_dict):
        return sum(quality_count_dict[resolution] for resolution in resolutions)

    def _prem_terminate(self):  # pylint: disable=method-hidden
        if self.canceled:
            monkey_requests.PRE_TERM_BLOCK = True
            return True

        if not self.preem_enabled:
            return False

        if (
            self.preem_waitfor_cloudfiles
            and "Cloud Inspection" in self.sources_information['statistics']['remainingProviders']
        ):
            return False

        if self.preem_cloudfiles and self.sources_information['statistics']['filtered']['cloudFiles']['total'] > 0:
            monkey_requests.PRE_TERM_BLOCK = True
            return True
        if (
            self.preem_adaptive_sources
            and self.sources_information['statistics']['filtered']['adaptiveSources']['total'] > 0
        ):
            monkey_requests.PRE_TERM_BLOCK = True
            return True
        if (
            self.preem_direct_sources
            and self.sources_information['statistics']['filtered']['directSources']['total'] > 0
        ):
            monkey_requests.PRE_TERM_BLOCK = True
            return True

        pre_term_log_string = 'Pre-emptively Terminated'

        try:
            if (
                self.preem_type == 0
                and self._get_filtered_count_by_resolutions(
                    self.preem_resolutions, self.sources_information['statistics']['filtered']['torrentsCached']
                )
                >= self.preem_limit
            ):
                return self.__preterm_block(pre_term_log_string)
            if (
                self.preem_type == 1
                and self._get_filtered_count_by_resolutions(
                    self.preem_resolutions, self.sources_information['statistics']['filtered']['hosters']
                )
                >= self.preem_limit
            ):
                return self.__preterm_block(pre_term_log_string)
            if (
                self.preem_type == 2
                and self._get_filtered_count_by_resolutions(
                    self.preem_resolutions, self.sources_information['statistics']['filtered']['torrentsCached']
                )
                + self._get_filtered_count_by_resolutions(
                    self.preem_resolutions, self.sources_information['statistics']['filtered']['hosters']
                )
                >= self.preem_limit
            ):
                return self.__preterm_block(pre_term_log_string)
        except (ValueError, KeyError, IndexError) as e:
            g.log(f"Error getting data for preterm determination: {repr(e)}", "error")
        return False

    @staticmethod
    def __preterm_block(pre_term_log_string):
        g.log(pre_term_log_string, 'info')
        monkey_requests.PRE_TERM_BLOCK = True
        return True

    @staticmethod
    def _torrent_filesize(torrent, info):
        size = torrent.get("episode_size", torrent.get("size", 0))
        try:
            size = float(size)
        except (ValueError, TypeError):
            return 0
        size = int(size)

        if "episode_size" in torrent:
            return size

        if torrent['package'] == "show":
            count = int(info.get('show_episode_count', 0) or 0)
            if count > 0:
                size /= count
        elif torrent['package'] == 'season':
            count = int(info.get('episode_count', 0) or 0)
            if count > 0:
                size /= count
        return size

    @staticmethod
    def _torrent_seeds(torrent):
        seeds = torrent.get('seeds')
        if seeds is None or isinstance(seeds, str) and not seeds.isdigit():
            return 0

        return int(torrent['seeds'])

    def _merge_torrents(self, new_torrents):
        """Merge new torrents into allTorrents, preserving the highest seed count per hash."""
        all_torrents = self.sources_information['allTorrents']
        for hash_key, torrent in new_torrents.items():
            if hash_key in all_torrents:
                existing_seeds = self._torrent_seeds(all_torrents[hash_key])
                new_seeds = self._torrent_seeds(torrent)
                if new_seeds > existing_seeds:
                    all_torrents[hash_key] = torrent
                # else keep existing entry with higher seeds
            else:
                all_torrents[hash_key] = torrent

    @staticmethod
    def _build_apikeys():
        """Build debrid API keys dict for passthrough to scrapers that support it."""
        apikeys = {}
        if g.real_debrid_enabled():
            apikeys['rd'] = g.get_setting('rd.auth')
        if g.premiumize_enabled():
            apikeys['pm'] = g.get_setting('premiumize.token')
        if g.all_debrid_enabled():
            apikeys['ad'] = g.get_setting('alldebrid.apikey')
        if g.torbox_enabled():
            apikeys['tb'] = g.get_setting('torbox.token')
        if g.debridlink_enabled():
            apikeys['dl'] = g.get_setting('debridlink.token')
        anirena_key = (g.get_setting('anirena.apikey') or '').strip()
        if anirena_key:
            apikeys['anirena'] = anirena_key
        return apikeys

    @staticmethod
    def _get_provider_perf_db():
        """Lazy-load the ProviderPerformance DB (returns None if feature disabled)."""
        if not g.get_bool_setting('general.providerPerformance'):
            return None
        try:
            from resources.lib.database.providerPerformance import ProviderPerformance
            return ProviderPerformance()
        except Exception as e:
            g.log(f"ProviderPerformance DB load error: {e}", "warning")
            return None

    def _record_provider_performance(self, provider_name, start_time, result_count, failed):
        """Record scrape metrics to the provider performance DB.

        Called from _get_provider_sources finally block. Non-blocking (background thread).

        Args:
            provider_name: provider name (UPPER from provider tuple)
            start_time: time.time() when scraping started
            result_count: number of raw results returned (0 if none/failed)
            failed: True if the scrape raised an exception
        """
        pp = self._get_provider_perf_db()
        if pp is None:
            return

        elapsed_ms = int((time.time() - start_time) * 1000)
        name_lower = provider_name.lower()

        if failed:
            pp.record_failure_background(name_lower, elapsed_ms)
            # Check for auto-disable threshold
            try:
                fail_threshold = g.get_int_setting('general.providerFailThreshold', 5)
                consec = pp.get_consecutive_failures(name_lower)
                # consec was before this failure was recorded; the background thread
                # will increment it. Check against threshold - 1 since the write
                # hasn't happened yet, or just let next scrape catch it.
                if consec + 1 >= fail_threshold:
                    pp.set_status(name_lower, 'disabled')
                    g.log(
                        f"Provider Performance: {provider_name} auto-disabled after "
                        f"{consec + 1} consecutive failures (threshold={fail_threshold})",
                        "warning",
                    )
            except Exception:
                pass
        else:
            pp.record_scrape_background(name_lower, result_count, 0, elapsed_ms)


class TorrentCacheCheck:
    def __init__(self, scraper_class):
        self.premiumize_cached = []
        self.realdebrid_cached = []
        self.all_debrid_cached = []
        self.torbox_cached = []
        self.threads = ThreadPool()

        self.episode_strings = None
        self.season_strings = None
        self.scraper_class = scraper_class
        self.rd_api = real_debrid.RealDebrid()

        # Debrid hash cache — loaded once before threads start
        self._db_cached_rows = []

    def store_torrent(self, torrent):
        """
        Pushes cached torrents back up to the calling class
        :param torrent: Torrent to return
        :type torrent: dict
        :return: None
        :rtype: None
        """
        try:
            sources_information = self.scraper_class.sources_information
            # Compare and combine source meta
            tor_key = torrent['hash'] + torrent['debrid_provider']
            sources_information['cached_hashes'].add(torrent['hash'].lower())
            if tor_key in sources_information['torrentCacheSources']:
                existing = sources_information['torrentCacheSources'][tor_key]
                c_size = existing.get('size', 0)
                n_size = torrent.get('size', 0)
                info = torrent.get('info', [])

                # Preserve the best known seed count across overwrites
                c_seeds = Sources._torrent_seeds(existing)
                n_seeds = Sources._torrent_seeds(torrent)
                best_seeds = max(c_seeds, n_seeds)

                if c_size < n_size:
                    sources_information['torrentCacheSources'].update({tor_key: torrent})

                    sources_information['torrentCacheSources'][tor_key]['info'].extend(
                        [
                            i
                            for i in info
                            if i not in sources_information['torrentCacheSources'][tor_key].get('info', [])
                        ]
                    )

                # Always keep the highest seed count regardless of which entry won on size
                if best_seeds > 0:
                    sources_information['torrentCacheSources'][tor_key]['seeds'] = best_seeds
            else:
                sources_information['torrentCacheSources'].update({tor_key: torrent})
        except AttributeError:
            return

    def torrent_cache_check(self, torrent_list, info):
        """
        Run cache check threads for given torrents.
        Deduplicates hashes across scraper batches so each hash is only sent to
        debrid cache-check APIs once. Loads debrid cache DB first to skip
        already-known hashes.
        :param torrent_list: List of torrents to check
        :type torrent_list: list
        :param info: Metadata on item to check
        :type info: dict
        :return: None
        :rtype: None
        """
        # Pre-cache-check dedup: filter out hashes already sent to cache-check APIs
        # by a previous scraper batch (thread-safe via lock on Sources instance)
        scraper_class = self.scraper_class
        with scraper_class._cache_check_lock:
            new_hashes = set()
            deduped_list = []
            for t in torrent_list:
                h = t.get('hash', '').lower()
                if h and h not in scraper_class._cache_checked_hashes and h not in new_hashes:
                    new_hashes.add(h)
                    deduped_list.append(t)
            skipped = len(torrent_list) - len(deduped_list)
            if skipped > 0:
                g.log(
                    f"Pre-cache dedup: {skipped}/{len(torrent_list)} hashes already checked, "
                    f"sending {len(deduped_list)} new hashes to debrid APIs",
                    "info",
                )
            scraper_class._cache_checked_hashes.update(new_hashes)

        if not deduped_list:
            return

        torrent_list = deduped_list

        # Load cached debrid results from DB before spawning threads.
        # Retry up to 3 times with 100 ms backoff — multiple parallel tier
        # cache-check calls can collide on the DB open during tiered overlap.
        self._db_cached_rows = []
        for _attempt in range(3):
            try:
                from resources.lib.database.debridCache import DebridCache
                dc = DebridCache()
                hash_list = [t['hash'] for t in torrent_list if t.get('hash')]
                self._db_cached_rows = dc.get_many(hash_list)
                if self._db_cached_rows:
                    db_hit_count = len({r["hash"] for r in self._db_cached_rows})
                    g.log(
                        f"DebridCache: {db_hit_count}/{len(hash_list)} hashes found in DB cache",
                        "info",
                    )
                break  # success — exit retry loop
            except Exception as e:
                if _attempt < 2:
                    import time as _time
                    _time.sleep(0.1 * (_attempt + 1))  # 100 ms, 200 ms
                else:
                    g.log(f"DebridCache load error (continuing without cache): {e}", "warning")

        if g.real_debrid_enabled() and g.get_bool_setting('rd.torrents'):
            self.threads.put(self._realdebrid_worker, copy.deepcopy(torrent_list), info)

        if g.premiumize_enabled() and g.get_bool_setting('premiumize.torrents'):
            self.threads.put(self._premiumize_worker, copy.deepcopy(torrent_list))

        if g.all_debrid_enabled() and g.get_bool_setting('alldebrid.torrents'):
            self.threads.put(self._all_debrid_worker, copy.deepcopy(torrent_list), info)

        if g.torbox_enabled() and g.get_bool_setting('torbox.torrents'):
            self.threads.put(self._torbox_worker, copy.deepcopy(torrent_list))

        if g.debridlink_enabled() and g.get_bool_setting('debridlink.torrents'):
            self.threads.put(self._debridlink_worker, copy.deepcopy(torrent_list), info)

        # S15 — Register this batch as active BEFORE wait_completion so
        # get_sources() can detect in-flight debrid API calls and wait for them.
        # Uses _cache_check_lock (already on scraper_class) to protect the count.
        _sc = scraper_class
        with _sc._cache_check_lock:
            _sc._cache_check_active_count += 1
            _sc._cache_check_done.clear()

        try:
            self.threads.wait_completion()
        finally:
            # Decrement count and signal done when last active batch finishes.
            with _sc._cache_check_lock:
                _sc._cache_check_active_count -= 1
                if _sc._cache_check_active_count <= 0:
                    _sc._cache_check_active_count = 0  # floor at 0
                    _sc._cache_check_done.set()

    def _split_by_db_cache(self, torrent_list, debrid_key):
        """Split torrent_list into DB-cached and unchecked lists for a debrid service.

        Returns: (db_cached_torrents, unchecked_torrents)
          - db_cached_torrents: list of torrents whose hashes are cached=True in DB
          - unchecked_torrents: list of torrents not yet checked for this service
        """
        try:
            from resources.lib.database.debridCache import DebridCache
            dc = DebridCache()
            known_cached = dc.get_cached_hashes_for_service(self._db_cached_rows, debrid_key)
            known_all = dc.get_known_hashes_for_service(self._db_cached_rows, debrid_key)
        except Exception:
            return [], torrent_list

        db_cached = [t for t in torrent_list if t['hash'] in known_cached]
        unchecked = [t for t in torrent_list if t['hash'] not in known_all]
        return db_cached, unchecked

    @staticmethod
    def _write_cache_results(unchecked_torrents, cached_hashes_set, debrid_key):
        """Write cache check results to DB in background thread."""
        try:
            from resources.lib.database.debridCache import DebridCache
            results = []
            for t in unchecked_torrents:
                h = t['hash']
                cached = 'True' if h in cached_hashes_set else 'False'
                results.append((h, cached))
            if results:
                DebridCache().set_many_background(results, debrid_key)
        except Exception:
            pass

    # ── AD Magnet/Upload batch cache check constants ──────────────────────────
    _AD_UPLOAD_BATCH_SIZE  = 10   # torrents uploaded per API call
    _AD_UPLOAD_MAX_TOTAL   = 50   # hard cap — never exceed this many uploads
    _AD_UPLOAD_CACHED_GOAL = 10   # stop early once this many cached found
    _AD_UPLOAD_IDS_KEY     = "alldebrid.upload_cache_ids"  # runtime-setting key

    _DL_PROBE_MAX      = 20    # top-N unchecked hashes to probe per tier
    _DL_PROBE_WORKERS  = 5     # concurrent seedbox/add probe threads
    _DL_PROBE_GOAL     = 10    # stop storing cached once this many found
    _DL_PROBE_IDS_KEY  = "debridlink.probe_ids"  # runtime-setting key for cleanup

    @staticmethod
    def _ad_upload_sort_key(torrent):
        """Quality-then-seeds sort key for magnet/upload candidate list."""
        _quality_order = {"4K": 3, "1080p": 2, "720p": 1, "SD": 0}
        quality = torrent.get("quality", "")
        if quality and "/" in quality:
            quality = quality.split("/")[0]
        return (_quality_order.get(quality, -1), _coerce_seeds(torrent.get("seeds", 0)))

    @staticmethod
    def _dl_probe_sort_key(torrent):
        """Quality-then-seeds sort key for DL seedbox probe candidates."""
        _quality_order = {"4K": 3, "1080p": 2, "720p": 1, "SD": 0}
        quality = torrent.get("quality", "")
        if quality and "/" in quality:
            quality = quality.split("/")[0]
        return (_quality_order.get(quality, -1), _coerce_seeds(torrent.get("seeds", 0)))

    @staticmethod
    def _rd_storeall_sort_key(torrent):
        """Quality-then-seeds sort key for RD StoreAll candidates."""
        _quality_order = {"4K": 3, "1080p": 2, "720p": 1, "SD": 0}
        quality = torrent.get("quality", "")
        if quality and "/" in quality:
            quality = quality.split("/")[0]
        return (_quality_order.get(quality, -1), _coerce_seeds(torrent.get("seeds", 0)))

    def _ad_cleanup_stale_uploads(self, ad):
        """
        Delete any cached-upload IDs left over from the previous scrape session.

        Called at the start of _all_debrid_worker so that magnets uploaded
        during a scrape where the user never played anything are cleaned up
        before the next scrape begins.
        """
        stale = g.get_runtime_setting(self._AD_UPLOAD_IDS_KEY)
        if not stale:
            return
        g.clear_runtime_setting(self._AD_UPLOAD_IDS_KEY)
        if isinstance(stale, list) and stale:
            g.log(f"AD MagnetUpload: deleting {len(stale)} stale upload IDs from previous scrape", "info")
            ad.delete_magnets_background(stale)

    def _dl_cleanup_stale_probes(self, dl):
        """Delete any probe torrent IDs left over from the previous scrape.

        Called at the start of _debridlink_worker so that probe adds from a
        scrape where the user never played anything are cleaned up before the
        next scrape begins.  Mirrors _ad_cleanup_stale_uploads().
        """
        stale = g.get_runtime_setting(self._DL_PROBE_IDS_KEY)
        if not stale:
            return
        g.clear_runtime_setting(self._DL_PROBE_IDS_KEY)
        if isinstance(stale, list) and stale:
            g.log(
                f"DL SeedboxProbe: deleting {len(stale)} stale probe IDs "
                f"from previous scrape",
                "info",
            )
            dl.delete_torrents_background(stale)

    def _all_debrid_worker(self, torrent_list, info):
        try:
            if not torrent_list:
                return

            from resources.lib.debrid.all_debrid import AllDebrid
            ad = AllDebrid()

            # ── Stale-upload cleanup from previous scrape ─────────────────────
            self._ad_cleanup_stale_uploads(ad)

            # ── Layer 1: DB cache ─────────────────────────────────────────────
            db_cached, unchecked = self._split_by_db_cache(torrent_list, 'ad')
            for i in db_cached:
                i['debrid_provider'] = 'all_debrid'
                self.store_torrent(i)

            if not unchecked:
                return

            # ── Layer 2: ExternalCache (Torrentio + AIOStreams + direct) ───────
            cached_hashes = set()
            if g.get_bool_setting('alldebrid.externalcache'):
                # Use tvshow.imdb_id (parent show) for Stremio cache APIs.
                # For anime, IMDB creates separate per-season entries (e.g.
                # tt39372996 for Frieren S2). Those season-specific IDs end up
                # in info['info']['imdb_id'] but Torrentio/AIOStreams index by
                # the parent show ID (tvshow.imdb_id). Using the season ID
                # returns 0 streams — root-cause confirmed in kodi.log S179.
                imdb    = (info.get('info', {}).get('tvshow.imdb_id')
                           or info.get('info', {}).get('imdb_id'))
                season  = (info.get('info', {}).get('alternative_season')
                           or info.get('info', {}).get('season'))
                episode = (info.get('info', {}).get('alternative_episode')
                           or info.get('info', {}).get('episode'))

                if imdb:
                    ext_cached, success = external_cache.check_ad_external(
                        imdb, season, episode
                    )
                    if success:
                        for i in unchecked:
                            if i['hash'].lower() in ext_cached:
                                i['debrid_provider'] = 'all_debrid'
                                self.store_torrent(i)
                                cached_hashes.add(i['hash'].lower())

                        _mf_ad = bool(g.get_setting("mf.token") and g.get_setting("mf.service") == "1")
                        _ad_label = "AIO+Torrentio+Comet" + ("+MF" if _mf_ad else "")
                        g.log(
                            f"ExternalCache AD: {len(cached_hashes)}/{len(unchecked)} "
                            f"hashes confirmed cached via {_ad_label}",
                            "info",
                        )

            # ── Layer 3: Magnet/Upload batch cache check ──────────────────────
            # Uploads Seren-sorted torrents 10 at a time. AD's upload response
            # includes ready=True for each already-cached hash — no separate
            # cache-check API call needed. Uncached uploads (ready=False) are
            # deleted immediately in the background so they don't clutter the
            # transfer list. Stops when 10 cached found or 50 uploads reached.
            if g.get_bool_setting('alldebrid.magnetupload'):
                # Only check hashes not already confirmed by external cache
                candidates = [t for t in unchecked if t['hash'].lower() not in cached_hashes]
                candidates.sort(key=self._ad_upload_sort_key, reverse=True)

                total_uploaded  = 0
                total_cached    = 0
                upload_cache_ids = []   # magnet IDs confirmed ready=True

                for batch_start in range(0, len(candidates), self._AD_UPLOAD_BATCH_SIZE):
                    if total_uploaded >= self._AD_UPLOAD_MAX_TOTAL:
                        break
                    if total_cached >= self._AD_UPLOAD_CACHED_GOAL:
                        break

                    batch = candidates[batch_start : batch_start + self._AD_UPLOAD_BATCH_SIZE]
                    magnet_list = [
                        t.get('magnet') or f"magnet:?xt=urn:btih:{t['hash']}"
                        for t in batch
                    ]
                    hash_to_torrent = {t['hash'].lower(): t for t in batch}

                    results = ad.upload_magnet_batch(magnet_list)
                    total_uploaded += len(results)

                    ready_ids   = []
                    unready_ids = []
                    for r in results:
                        h = r.get('hash', '').lower()
                        if r.get('ready'):
                            if h in hash_to_torrent:
                                t = hash_to_torrent[h]
                                t['debrid_provider'] = 'all_debrid'
                                self.store_torrent(t)
                                cached_hashes.add(h)
                                total_cached += 1
                            ready_ids.append(r['id'])
                        else:
                            unready_ids.append(r['id'])

                    upload_cache_ids.extend(ready_ids)

                    # Delete uncached uploads immediately — no pending transfers
                    if unready_ids:
                        ad.delete_magnets_background(unready_ids)

                g.log(
                    f"AD MagnetUpload: {total_cached} cached from {total_uploaded} uploads "
                    f"({len(upload_cache_ids)} ready IDs stored)",
                    "info",
                )

                # Accumulate ready IDs for post-play cleanup — extend, not overwrite.
                # Same race condition as DL probe_ids: tiers run concurrently so
                # each tier's upload_cache_ids must be ADDED to the runtime setting.
                if upload_cache_ids:
                    _existing = g.get_runtime_setting(self._AD_UPLOAD_IDS_KEY)
                    if _existing and isinstance(_existing, list):
                        _all_ids = list(set(_existing + upload_cache_ids))
                    else:
                        _all_ids = upload_cache_ids
                    g.set_runtime_setting(self._AD_UPLOAD_IDS_KEY, _all_ids)

            # ── Step 4: Store-All (optional) ─────────────────────────────────
            # Same mechanic as DL StoreAll: when enabled and confirmed cached
            # count is below threshold, store top-N unchecked hashes as AD
            # sources without confirmation.  Resolver handles CloudMiss.
            if g.get_bool_setting('alldebrid.storeall'):
                _sa_threshold = g.get_int_setting('alldebrid.storeall.threshold', 5)
                if len(cached_hashes) < _sa_threshold:
                    _sa_limit = g.get_int_setting('alldebrid.storeall.limit', 30)
                    _sa_candidates = [
                        t for t in unchecked
                        if t.get('hash', '').lower() not in cached_hashes
                    ]
                    _sa_candidates.sort(key=self._ad_upload_sort_key, reverse=True)
                    _sa_candidates = _sa_candidates[:_sa_limit]
                    _sa_stored = 0
                    for t in _sa_candidates:
                        t['debrid_provider'] = 'all_debrid'
                        self.store_torrent(t)
                        _sa_stored += 1
                    if _sa_stored:
                        g.log(
                            f"AD StoreAll: {_sa_stored} unverified sources added "
                            f"(confirmed={len(cached_hashes)} < "
                            f"threshold={_sa_threshold})",
                            "info",
                        )
                else:
                    g.log(
                        f"AD StoreAll: skipped "
                        f"(confirmed={len(cached_hashes)} >= threshold={_sa_threshold})",
                        "debug",
                    )

            # Write ALL unchecked results — cached and not-cached.
            # Not-cached entries use a shorter 4h TTL (see DebridCache.set_many).
            self._write_cache_results(unchecked, cached_hashes, 'ad')

        except Exception:
            g.log_stacktrace()

    def _realdebrid_worker(self, torrent_list, info):
        try:
            # ── Layer 1: DB cache ─────────────────────────────────────────────
            db_cached, unchecked = self._split_by_db_cache(torrent_list, 'rd')
            for i in db_cached:
                i['debrid_provider'] = 'real_debrid'
                self.store_torrent(i)

            if not unchecked:
                return

            # ── Layer 2: Option C — Torrentio pre-verified rd_cached hashes ───
            # When Torrentio scraper ran with the RD key, it tagged confirmed-cached
            # hashes with rd_cached=True. These bypass the external cache check
            # entirely — Torrentio already verified them at the scraper level,
            # exactly matching POV's combined scrape+cache-check architecture.
            confirmed_cached = set()
            needs_check = []
            for i in unchecked:
                if i.get('rd_cached'):
                    i['debrid_provider'] = 'real_debrid'
                    self.store_torrent(i)
                    confirmed_cached.add(i['hash'].lower())
                else:
                    needs_check.append(i)

            if confirmed_cached:
                g.log(
                    f"RD Torrentio pre-verified: {len(confirmed_cached)} hashes confirmed "
                    f"cached at scraper level (rd_cached=True)",
                    "info",
                )

            if not needs_check:
                self._write_cache_results(unchecked, confirmed_cached, 'rd')
                return

            # ── Layer 3: External cache check via Torrentio (user key) + DMM ──
            # Tracks whether ExternalCache ran cleanly so Strategy 2
            # (instantAvailability) only runs when ExternalCache disabled or all
            # its checkers threw exceptions. ext_cache_zero_clean signals the
            # legacy "Option A" branch: ExternalCache ran but returned 0 hashes.
            ext_cache_done = False
            ext_cache_zero_clean = False
            if g.get_bool_setting('rd.externalcache'):
                # Use tvshow.imdb_id (parent show) for Stremio cache APIs.
                # For anime, IMDB creates separate per-season entries (e.g.
                # tt39372996 for Frieren S2). Those season-specific IDs end up
                # in info['info']['imdb_id'] but Torrentio/DMM index by the
                # parent show ID (tvshow.imdb_id). Using the season ID returns
                # 0 streams — root-cause confirmed in kodi.log S179.
                imdb = (info.get('info', {}).get('tvshow.imdb_id')
                        or info.get('info', {}).get('imdb_id'))
                season = (info.get('info', {}).get('alternative_season')
                          or info.get('info', {}).get('season'))
                episode = (info.get('info', {}).get('alternative_episode')
                           or info.get('info', {}).get('episode'))
                if imdb:
                    hash_list = [i['hash'].lower() for i in needs_check]
                    ext_cached, success = external_cache.check_rd_external(
                        hash_list, imdb, season, episode
                    )
                    if success is True:
                        for i in needs_check:
                            if i['hash'].lower() in ext_cached:
                                i['debrid_provider'] = 'real_debrid'
                                self.store_torrent(i)
                                confirmed_cached.add(i['hash'].lower())
                        _mf_rd = bool(g.get_setting("mf.token") and g.get_setting("mf.service") == "2")
                        _rd_label = "Torrentio+DMM" + ("+MF" if _mf_rd else "")
                        g.log(
                            f"ExternalCache RD: {len(ext_cached)}/{len(needs_check)} "
                            f"hashes confirmed cached via {_rd_label}",
                            "info",
                        )
                        ext_cache_done = True
                    elif success is None:
                        # Ran cleanly but found 0 — legacy Option A trigger.
                        g.log(
                            f"ExternalCache RD: 0 confirmed cached (clean run)",
                            "info",
                        )
                        ext_cache_done = True
                        ext_cache_zero_clean = True
                    else:
                        # success=False: all checkers threw exceptions
                        # (network/API failure). Fall through to Strategy 2.
                        g.log(
                            "ExternalCache RD: all checkers failed — "
                            "falling back to instantAvailability",
                            "warning",
                        )

            # ── Layer 4: instantAvailability (last resort) ────────────────────
            # Only reached when: (a) ExternalCache disabled, or (b) all its
            # checkers threw exceptions (network/Cloudflare outage).
            if not ext_cache_done:
                hash_list = [i['hash'].lower() for i in needs_check]
                rd_cached_set = self.rd_api.check_cache_batch(hash_list)
                for i in needs_check:
                    if i['hash'].lower() in rd_cached_set:
                        i['debrid_provider'] = 'real_debrid'
                        self.store_torrent(i)
                        confirmed_cached.add(i['hash'].lower())
                if rd_cached_set:
                    g.log(
                        f"RD instantAvailability: {len(rd_cached_set)}/{len(needs_check)} "
                        f"hashes confirmed cached",
                        "info",
                    )

            # ── Layer 5: StoreAll (toggle-gated) + legacy Option A fallback ───
            # Two mutually-exclusive code paths:
            #
            # 1. realdebrid.storeall = ON
            #    Mirrors AD/DL StoreAll: when total confirmed cached count
            #    across ALL strategies is below threshold, store the top-N
            #    unchecked hashes (sorted by quality+seeds) as RD sources.
            #    The resolver verifies at play time — CloudMiss is handled
            #    gracefully (RD's check_hash auto-deletes uncached magnets).
            #
            # 2. realdebrid.storeall = OFF (default)
            #    Preserves legacy Option A behaviour: when ExternalCache ran
            #    cleanly but found 0 hashes, store ALL remaining unchecked
            #    hashes unconditionally (no threshold, no limit). Existing
            #    users see no behaviour change on upgrade.
            if g.get_bool_setting('realdebrid.storeall'):
                _sa_threshold = g.get_int_setting('realdebrid.storeall.threshold', 5)
                if len(confirmed_cached) < _sa_threshold:
                    _sa_limit = g.get_int_setting('realdebrid.storeall.limit', 30)
                    _sa_candidates = [
                        t for t in needs_check
                        if t.get('hash', '').lower() not in confirmed_cached
                    ]
                    _sa_candidates.sort(key=self._rd_storeall_sort_key, reverse=True)
                    _sa_candidates = _sa_candidates[:_sa_limit]
                    _sa_stored = 0
                    for t in _sa_candidates:
                        t['debrid_provider'] = 'real_debrid'
                        self.store_torrent(t)
                        confirmed_cached.add(t['hash'].lower())
                        _sa_stored += 1
                    if _sa_stored:
                        g.log(
                            f"RD StoreAll: {_sa_stored} unverified sources added "
                            f"(confirmed={len(confirmed_cached) - _sa_stored} < "
                            f"threshold={_sa_threshold})",
                            "info",
                        )
                else:
                    g.log(
                        f"RD StoreAll: skipped "
                        f"(confirmed={len(confirmed_cached)} >= threshold={_sa_threshold})",
                        "debug",
                    )
            elif ext_cache_zero_clean:
                # ── Legacy Option A — preserved for backward compatibility ───
                # ExternalCache ran cleanly with 0 confirmed and the new
                # StoreAll toggle is OFF — fall back to the old unconditional
                # store-all so users who never touch the setting see exactly
                # the same behaviour they had on 3.3.90.
                _legacy_added = 0
                for i in needs_check:
                    h = i['hash'].lower()
                    if h not in confirmed_cached:
                        i['debrid_provider'] = 'real_debrid'
                        self.store_torrent(i)
                        confirmed_cached.add(h)
                        _legacy_added += 1
                g.log(
                    f"ExternalCache RD: 0 confirmed — store-all fallback "
                    f"(Option A): {_legacy_added} hashes marked as potentially "
                    f"cached, resolver will verify",
                    "info",
                )

            self._write_cache_results(unchecked, confirmed_cached, 'rd')
        except Exception:
            g.log_stacktrace()

    def _premiumize_worker(self, torrent_list):
        try:
            # Restore DB-cached results and filter unchecked
            db_cached, unchecked = self._split_by_db_cache(torrent_list, 'pm')
            for i in db_cached:
                i['debrid_provider'] = 'premiumize'
                self.store_torrent(i)

            if not unchecked:
                return

            hash_list = [i['hash'].lower() for i in unchecked]
            if not hash_list:
                return
            premiumize_cache = premiumize.Premiumize().hash_check(hash_list)
            premiumize_cache = premiumize_cache['response']
            cached_hashes = set()
            for count, i in enumerate(unchecked):
                if premiumize_cache[count] is True:
                    i['debrid_provider'] = 'premiumize'
                    self.store_torrent(i)
                    cached_hashes.add(i['hash'].lower())

            # Write results to DB
            self._write_cache_results(unchecked, cached_hashes, 'pm')
        except Exception:
            g.log_stacktrace()

    def _torbox_worker(self, torrent_list):
        try:
            # Skip NZB sources — they're pre-checked by _torbox_usenet_search()
            torrent_list = [t for t in torrent_list if not t.get('nzb_url')]

            # Restore DB-cached results and filter unchecked
            db_cached, unchecked = self._split_by_db_cache(torrent_list, 'tb')
            for i in db_cached:
                i['debrid_provider'] = 'torbox'
                self.store_torrent(i)

            if not unchecked:
                return

            hash_list = [i['hash'].lower() for i in unchecked]
            if not hash_list:
                return
            tb = torbox.TorBox()
            cached_hashes_list = tb.check_hash(hash_list)
            cached_hashes = set(h.lower() for h in cached_hashes_list)
            for i in unchecked:
                if i['hash'].lower() in cached_hashes:
                    i['debrid_provider'] = 'torbox'
                    self.store_torrent(i)

            # Write results to DB
            self._write_cache_results(unchecked, cached_hashes, 'tb')
        except Exception:
            g.log_stacktrace()

    def _debridlink_worker(self, torrent_list, info):
        try:
            dl = debrid_link.DebridLink()

            # ── Stale probe cleanup from previous scrape ──────────────────────
            self._dl_cleanup_stale_probes(dl)

            # ── Step 1: DB cache ──────────────────────────────────────────────
            db_cached, unchecked = self._split_by_db_cache(torrent_list, 'dl')
            for i in db_cached:
                i['debrid_provider'] = 'debrid_link'
                self.store_torrent(i)

            if not unchecked:
                return

            # ── Step 2: Seedbox-list oracle ───────────────────────────────────
            # Consult the per-session hash set built from /v2/seedbox/list.
            # Any match is 100% confirmed cached — the torrent is fully
            # downloaded in the user's DL cloud (downloadPercent==100).
            # Populated once per session; window property is the fast path.
            oracle_set = dl.get_seedbox_oracle_hashes()
            if oracle_set:
                oracle_hits = set()
                oracle_hit_items = []
                remaining = []
                for item in unchecked:
                    h = item.get('hash', '').lower()
                    if h in oracle_set:
                        item['debrid_provider'] = 'debrid_link'
                        self.store_torrent(item)
                        oracle_hits.add(h)
                        oracle_hit_items.append(item)
                    else:
                        remaining.append(item)
                if oracle_hits:
                    g.log(
                        f"SeedboxOracle DL: {len(oracle_hits)}/{len(unchecked)} "
                        f"hashes confirmed cached via seedbox/list",
                        "info",
                    )
                    self._write_cache_results(oracle_hit_items, oracle_hits, 'dl')
                unchecked = remaining

            if not unchecked:
                return

            # ── Step 3: Comet external cache ──────────────────────────────────
            # (Torrentio removed S168a — DL cache detection never implemented.)
            # Results collected into confirmed_cached; no early return so the
            # probe step below can run on whatever Comet doesn't cover.
            confirmed_cached = set()
            if g.get_bool_setting('debridlink.externalcache'):
                # Use tvshow.imdb_id (parent show) for Stremio cache APIs.
                # Same per-season IMDB issue as RD/AD — see S179 root-cause.
                imdb    = (info.get('info', {}).get('tvshow.imdb_id')
                           or info.get('info', {}).get('imdb_id'))
                season  = (info.get('info', {}).get('alternative_season')
                           or info.get('info', {}).get('season'))
                episode = (info.get('info', {}).get('alternative_episode')
                           or info.get('info', {}).get('episode'))

                if imdb:
                    hash_list = [i['hash'].lower() for i in unchecked]
                    ext_cached, success = external_cache.check_dl_external(
                        hash_list, imdb, season, episode
                    )
                    if success and ext_cached:
                        for i in unchecked:
                            if i['hash'].lower() in ext_cached:
                                i['debrid_provider'] = 'debrid_link'
                                self.store_torrent(i)
                                confirmed_cached.add(i['hash'].lower())
                        _mf_dl = bool(g.get_setting("mf.token") and g.get_setting("mf.service") == "0")
                        _dl_label = "Comet" + ("+MF" if _mf_dl else "")
                        g.log(
                            f"ExternalCache DL: {len(confirmed_cached)}/{len(unchecked)} "
                            f"hashes confirmed cached via {_dl_label}",
                            "info",
                        )
                    else:
                        g.log(
                            f"ExternalCache DL: 0 cached hashes from Comet",
                            "info",
                        )

            # ── Step 4: Speculative seedbox/add probe ─────────────────────────
            # POST the top-N unchecked hashes to /v2/seedbox/add?async=true in
            # parallel.  DL returns downloadPercent=100 immediately for hashes
            # already in its shared pool (~200–400 ms).  Uncached hashes also
            # return quickly (<1 s with async=true — DL doesn't wait for tracker
            # metadata) and are deleted immediately in the background.
            # Catches hashes that Comet has never indexed: niche scrapers (DMM,
            # Knaben, Zilean), private trackers, and content added via magnet.
            if unchecked and g.get_bool_setting('debridlink.seedboxprobe'):
                candidates = [
                    t for t in unchecked
                    if t.get('hash', '').lower() not in confirmed_cached
                ]
                candidates.sort(key=self._dl_probe_sort_key, reverse=True)
                candidates = candidates[:self._DL_PROBE_MAX]

                if candidates:
                    import concurrent.futures
                    probe_futures = {}
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=self._DL_PROBE_WORKERS
                    ) as executor:
                        for t in candidates:
                            magnet = (t.get('magnet')
                                      or f"magnet:?xt=urn:btih:{t['hash']}")
                            probe_futures[executor.submit(dl.probe_magnet, magnet)] = t
                    # All futures complete by here (executor.__exit__ joined them)

                    probe_cache_ids    = []
                    probe_uncached_ids = []
                    total_probe_cached = 0

                    for future, torrent in probe_futures.items():
                        try:
                            result = future.result()
                        except Exception:
                            continue
                        if result is None:
                            continue
                        torrent_id = result['id']
                        if result['is_cached']:
                            # Track for router.py cleanup regardless of goal
                            probe_cache_ids.append(torrent_id)
                            if total_probe_cached < self._DL_PROBE_GOAL:
                                torrent['debrid_provider'] = 'debrid_link'
                                self.store_torrent(torrent)
                                confirmed_cached.add(torrent['hash'].lower())
                                total_probe_cached += 1
                        else:
                            probe_uncached_ids.append(torrent_id)

                    g.log(
                        f"DL SeedboxProbe: {total_probe_cached} cached from "
                        f"{len(candidates)} probes "
                        f"({len(probe_cache_ids)} IDs stored, "
                        f"{len(probe_uncached_ids)} deleted)",
                        "info",
                    )

                    # Delete uncached probe entries immediately
                    if probe_uncached_ids:
                        dl.delete_torrents_background(probe_uncached_ids)

                    # Accumulate cached probe IDs for post-play cleanup.
                    # IMPORTANT: use extend, not overwrite — tiers run concurrently
                    # so each tier's probe_cache_ids must be ADDED to the runtime
                    # setting rather than replacing it.  Overwriting loses earlier
                    # tiers' IDs from the setting and leaves those cached torrents
                    # in DL cloud forever if the user doesn't play anything.
                    if probe_cache_ids:
                        _existing = g.get_runtime_setting(self._DL_PROBE_IDS_KEY)
                        if _existing and isinstance(_existing, list):
                            _all_ids = list(set(_existing + probe_cache_ids))
                        else:
                            _all_ids = probe_cache_ids
                        g.set_runtime_setting(self._DL_PROBE_IDS_KEY, _all_ids)

            # ── Step 5: Store-All (optional) ─────────────────────────────────
            # When enabled and confirmed cached count is below the user-set
            # threshold, take the top-N unchecked hashes (by quality+seeds)
            # and store them as DL sources without confirmation.  These will
            # appear in the source list and the resolver attempts them at play
            # time — CloudMiss is handled gracefully (auto-try next source).
            # Only fires when the cascade hasn't found enough confirmed sources,
            # so it doesn't add noise when the user already has plenty to pick.
            if g.get_bool_setting('debridlink.storeall'):
                _sa_threshold = g.get_int_setting('debridlink.storeall.threshold', 5)
                if len(confirmed_cached) < _sa_threshold:
                    _sa_limit = g.get_int_setting('debridlink.storeall.limit', 30)
                    _sa_candidates = [
                        t for t in unchecked
                        if t.get('hash', '').lower() not in confirmed_cached
                    ]
                    _sa_candidates.sort(key=self._dl_probe_sort_key, reverse=True)
                    _sa_candidates = _sa_candidates[:_sa_limit]
                    _sa_stored = 0
                    for t in _sa_candidates:
                        t['debrid_provider'] = 'debrid_link'
                        self.store_torrent(t)
                        _sa_stored += 1
                    if _sa_stored:
                        g.log(
                            f"DL StoreAll: {_sa_stored} unverified sources added "
                            f"(confirmed={len(confirmed_cached)} < "
                            f"threshold={_sa_threshold})",
                            "info",
                        )
                else:
                    g.log(
                        f"DL StoreAll: skipped "
                        f"(confirmed={len(confirmed_cached)} >= threshold={_sa_threshold})",
                        "debug",
                    )

            # ── Final DB write — covers all unchecked hashes for this tier ────
            self._write_cache_results(unchecked, confirmed_cached, 'dl')

        except Exception:
            g.log_stacktrace()


class SourceWindowAdapter:
    """
    Class to handle different window style for scraper module
    """

    def __init__(self, item_information, scraper_sclass):
        self.trakt_id = 0
        self.silent = g.get_bool_runtime_setting('tempSilent')

        try:
            self.display_style = g.get_int_setting('general.scrapedisplay')
        except ValueError:
            self.display_style = 0
        self.item_information = item_information
        self.media_type = self.item_information['info']['mediatype']
        self.background_dialog = None
        self.dialog = None
        self.scraper_class = scraper_sclass

    def create(self):
        if self.silent:
            return
        if self.display_style == 2:
            self.background_dialog = xbmcgui.DialogProgressBG()
            self.background_dialog.create("Loading","")
            g.close_busy_dialog()
        if self.display_style == 1:
            # this one is deleted in `close()`
            self.background_dialog = xbmcgui.DialogProgressBG()
            self.trakt_id = self.item_information['trakt_id']
            if self.media_type == 'episode':
                self.background_dialog.create(
                    f"{self.item_information['info']['tvshowtitle']} - "
                    f"S{self.item_information['info']['season']}E{self.item_information['info']['episode']}"
                )
            else:
                self.background_dialog.create(
                    f"{self.item_information['info']['title']} ({self.item_information['info']['year']})"
                )
            g.close_busy_dialog()
        elif self.display_style == 0:
            # this one seems tricky, but is deleted in `close()`
            self.dialog = GetSourcesWindow(
                *SkinManager().confirm_skin_path('get_sources.xml'), item_information=self.item_information
            )
            self.dialog.set_scraper_class(self.scraper_class)
            self.dialog.show()

    def set_text(self, text, progress, timeout_progress, sources_information, runtime):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            if text is not None:
                self.dialog.setProperty("notification_text", text)
            self.dialog.update_properties(sources_information['statistics'])
            self.dialog.setProperty("progress", str(progress))
            self.dialog.setProperty("timeout_progress", str(timeout_progress))
            self.dialog.setProperty("runtime", str(f"{round(runtime, 2)} {g.get_language_string(30554)}"))
        elif self.display_style == 1 and self.background_dialog:
            self.background_dialog.update(progress, message=text)
        elif self.display_style == 2 and self.background_dialog:
            self.background_dialog.update(progress)

    def set_property(self, key, value):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            self.dialog.setProperty(key, str(value))
        elif self.display_style == 1 or self.display_style == 2:
            return

    def set_progress(self, progress):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            self.dialog.setProgress(progress)
        elif (self.display_style == 1 or self.display_style == 2) and self.background_dialog:
            self.background_dialog.update(progress)

    def close(self):
        if self.silent:
            return
        if self.display_style == 0 and self.dialog:
            self.dialog.close()
            del self.dialog
        elif (self.display_style == 1 or self.display_style == 2) and self.background_dialog:
            self.background_dialog.close()
            del self.background_dialog
