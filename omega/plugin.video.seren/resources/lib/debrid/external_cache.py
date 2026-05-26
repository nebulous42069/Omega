"""
External debrid cache checking via third-party APIs.

Instead of marking all torrents as cached for RD/AD (and failing at resolve time),
this module queries external services that maintain pre-indexed databases of which
info-hashes are cached on which debrid services.

Design principles (derived from POV and Otaku reference implementations):
  - Browser-like User-Agent required: Torrentio sits behind Cloudflare and
    silently returns {"streams": []} for non-browser UAs on authenticated debrid
    endpoints.  _get_session() picks randomly from _BROWSER_UAS on init.
  - Each checker uses the user's OWN debrid key so results reflect the correct service.
  - Fallbacks only exist where a valid same-service key is available.
  - AIOStreams is ONLY used for AD: it has a valid AD demo key fallback
    (staticDemoApikeyPrem). It is intentionally excluded from RD and DL — there
    is no equivalent RD/DL demo key, so falling back would return results from the
    wrong service pool, causing false positives at resolve time.
  - Torrentio hardcoded RD key is ONLY valid for RD checks. It must never be used
    as a fallback for AD or DL. The hardcoded key queries the RD cache pool; those
    hashes are RD-cached, not AD/DL-cached. Using them for AD/DL produces false
    positives (sources appear CACHED in source select but fail at resolve time).
    Simulation confirms: popular content ~12% false positive rate, niche content
    up to ~47% — both POV and Otaku block the RD key from AD/DL checks entirely.
  - Torrentio for RD: user key only. Hardcoded shared RD key used ONLY when no
    user token is configured (matches POV's single-call behaviour — no threshold
    double-call that doubles request rate).
  - Torrentio for AD: user key only. No fallback. AIOStreams is the AD fallback.
  - Torrentio for DL: user key only. No fallback. No equivalent DL demo key exists.

For Real-Debrid  (matches POV and Otaku exactly):
  - Torrentio: user's own RD key (hardcoded fallback only when no user key)
  - DMM Availability API: RD-crowdsourced hash index (no debrid key needed)

check_rd_external() and check_ad_external() return a 3-value success indicator:
  True  → cached hashes found (show them)
  None  → checkers ran but 0 hashes found (genuinely empty — no fallback)
  False → all checkers threw exceptions (network failure — caller falls back
          to instantAvailability for RD)

For AllDebrid — AIOStreams + direct checkers in parallel:
  AIOStreams: demo key (staticDemoApikeyPrem) — AD cache is shared infrastructure.
    Preset timeout 6500ms matches POV exactly. Outer _AIO_TIMEOUT=8s gives 1.5s
    margin for AIO to merge and respond. fortheweak.cloud is the primary instance.
  Torrentio:  user's own AD key only — no RD fallback.
  MediaFusion: AD demo key (shared cache).
  Comet:      AD demo key (cachedOnly=True).

For Debrid-Link — Comet only (S168a):
  - Comet: user's own DL key (cachedOnly=True, debridService="debridlink").
    The only aggregator confirmed to track DL cache status via CometNet user
    activity. Returns 2–8 hashes per scrape for popular movies.
  Torrentio REMOVED (S168a): accepts DL keys for stream resolution but the
    Torrentio developer explicitly never implemented a DL cache-status
    workaround. Log analysis confirmed 0 hashes on every call (15+ calls,
    1 timeout at 15 s). Not a "low user base" problem — it's a deliberate
    product decision by the Torrentio dev (see r/StremioAddons Dec 2024 / Apr 2025).
  Other sources removed earlier:
  - Native /v2/seedbox/cached: endpointDisabled since late 2024.
  - StremThru: 401 on every known public instance (store check requires auth).
  - MediaFusion: 0 hashes every scrape (public instance, no DL key).
  - Meteor: RD/TorBox only — its hashes are never DL-cached.
  - DMM: RD-crowdsourced, systematic DL false positives (S154).
  - AIOStreams: no valid DL demo key; AD-only (S131).
"""

import base64
import ctypes
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.modules.globals import g

# --------------------------------------------------------------------------- #
#  Shared HTTP session
# --------------------------------------------------------------------------- #

# Browser-like User-Agent pool — mirrors POV's randomagent() list.
# Torrentio (Cloudflare-protected) silently returns {"streams": []} for
# non-browser UAs on authenticated debrid endpoints.  Real browser UAs are
# required to receive actual cached stream results.
# Last updated: May 2026 — Firefox 151/150, Chrome/Edge 148/147
_BROWSER_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
]

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.2, status_forcelist=[500, 502, 503])
        _session.mount("https://", HTTPAdapter(max_retries=retries))
        _session.headers.update({
            "User-Agent": random.choice(_BROWSER_UAS),
            "Accept": "application/json",
        })
    return _session


# =========================================================================== #
#  Torrentio — per-service cache check
# =========================================================================== #
# URL format:  {BASE}/{OPTIONS}|{SERVICE}={KEY}/stream/{path}
#
# Fallback policy:
#   RD:    user key -> shared hardcoded RD key  (valid same-service fallback)
#   AD/DL: user key -> None                     (skip; shared RD key = wrong service)
# --------------------------------------------------------------------------- #

_TIO_BASE = "https://torrentio.strem.fun"
_TIO_FALLBACK_PARAM = "realdebrid=T2iZoymNCCD1T5c2sX5u8tIZVcgcFWlCsCJ72rCmrU2mDdmvgieM"
_TIO_OPTIONS = "debridoptions=nodownloadlinks,nocatalog"
_HASH_PATTERN = re.compile(r"\b[a-fA-F0-9]{40}\b")
_TIO_TIMEOUT = 8

_TIO_SERVICE_PARAM = {
    "rd": "realdebrid",
    "ad": "alldebrid",
    # "dl": "debridlink" — intentionally absent.
    # Torrentio accepts DL API keys for stream *resolution* (configured at
    # torrentio.strem.fun), but the Torrentio developer has explicitly NOT
    # implemented a cache-status workaround for DL (unlike RD, where user-activity
    # tracking drives the [RD+] indicator).  Calling Torrentio with a DL key for
    # cache checking always returns 0 hashes — confirmed across all scrapes in the
    # S168a log analysis and corroborated by r/StremioAddons community reports
    # (Dec 2024 / Apr 2025). Do not restore without upstream evidence of a fix.
}


def _get_torrentio_debrid_param(service, debrid_key):
    """
    Build the Torrentio debrid query segment.

    RD:    user key → hardcoded shared RD key fallback when no user key.
           The hardcoded key is an RD key, so returned hashes are genuinely
           RD-cached. Valid same-service fallback.
    AD/DL: user key only. If no user key is configured, Torrentio is skipped
           entirely for that service (returns None). The hardcoded RD key must
           NEVER be used for AD/DL — it returns RD-pool hashes which would
           appear as CACHED in source select but fail at resolve time for AD/DL.
           AIOStreams (with the AD demo key) is the correct AD fallback; there
           is no equivalent fallback for DL.
    PM/TB: have native cache-check APIs — Torrentio is never called for them.
           Returns None as a safety guard.

    :param service: "rd" | "ad" | "dl" | "pm" | "tb"
    :param debrid_key: user's token/apikey for that service, or None
    :return: query param string, or None to skip Torrentio for this service
    """
    svc = (service or "rd").lower()
    if debrid_key:
        param_name = _TIO_SERVICE_PARAM.get(svc, "realdebrid")
        return f"{param_name}={debrid_key}"

    # No user key:
    #   RD → hardcoded shared RD key (valid same-service fallback)
    #   AD/DL → skip entirely (hardcoded RD key = wrong service pool)
    if svc == "rd":
        g.log(
            "ExternalCache: Torrentio — no RD key, using hardcoded RD fallback",
            "debug",
        )
        return _TIO_FALLBACK_PARAM

    # AD, DL, PM, TB: skip
    g.log(
        f"ExternalCache: Torrentio — no {svc.upper()} key, skipping "
        f"(hardcoded RD key must not be used for {svc.upper()})",
        "debug",
    )
    return None


def torrentio_check_cache(imdb, season, episode, service="rd", debrid_key=None):
    """
    Query Torrentio for cached info-hashes for a given IMDB title.

    Key strategy:
      RD: user's own token first. If no user token is configured, falls back
          to the hardcoded shared RD key (same-service, valid fallback).
          Threshold-based double-call removed — hardcoded fallback only fires
          when there is no user key, not when user key returns < N hashes.
          This matches POV's single-call behaviour and halves request rate.
      AD: user's own token only. No hardcoded RD fallback — the RD key returns
          RD-pool hashes which are NOT equivalent to AD-cached hashes and would
          cause false positives at resolve time. AIOStreams (via aio_check_cache)
          is the correct AD fallback and runs independently in check_ad_external.
      DL: user's own token only. No hardcoded RD fallback for the same reason.
      PM/TB: have native cache-check APIs; Torrentio is not used for them.

    :param imdb: IMDB ID (e.g. 'tt1234567')
    :param season: Season number (int/str) or None for movies
    :param episode: Episode number (int/str) or None for movies
    :param service: Debrid service — "rd", "ad", or "dl" (default "rd")
    :param debrid_key: User's own token/apikey, or None
    :return: set of 40-char lowercase info-hashes confirmed cached on *service*
    """
    svc = (service or "rd").lower()
    svc_label = svc.upper()

    if season is not None and str(season).isdigit():
        path = f"series/{imdb}:{season}:{episode}.json"
    else:
        path = f"movie/{imdb}.json"

    def _fetch(debrid_param, label):
        hashes = set()
        try:
            url = f"{_TIO_BASE}/{_TIO_OPTIONS}|{debrid_param}/stream/{path}"
            resp = _get_session().get(url, timeout=_TIO_TIMEOUT)
            resp.raise_for_status()
            streams = resp.json().get("streams", [])
            g.log(
                f"ExternalCache: Torrentio ({label}) received {len(streams)} streams "
                f"for {svc_label} (before '+' filter)",
                "debug",
            )
            for stream in streams:
                name = stream.get("name", "")
                # '+' in name identifies cached results (e.g. "RD+") — identical
                # to POV's tio_check_cache filter.  Non-cached streams have no '+'.
                if "+" not in name:
                    continue
                # Try infoHash field first (modern Stremio format), then URL regex.
                h = stream.get("infoHash", "")
                if h and len(h) == 40:
                    hashes.add(h.lower())
                    continue
                stream_url = stream.get("url", "")
                if stream_url:
                    matches = _HASH_PATTERN.findall(stream_url)
                    if matches:
                        hashes.add(matches[-1].lower())
            g.log(
                f"ExternalCache: Torrentio returned {len(hashes)} cached hashes "
                f"for {svc_label} ({label})",
                "info",
            )
        except Exception as e:
            g.log(f"ExternalCache: Torrentio check failed ({label}): {e}", "warning")
        return hashes

    debrid_param = _get_torrentio_debrid_param(service, debrid_key)
    if debrid_param is None:
        return set()  # no key + AD/DL/PM/TB safety guard

    label = "user key" if debrid_key else "hardcoded RD fallback"
    cached_hashes = _fetch(debrid_param, label)

    # Hardcoded RD fallback — only when no user key is configured.
    # Previously threshold was 10 (fire if user key returns < 10 hashes), which
    # doubled request rate to Torrentio every scrape.  Now fires only when the
    # user has no RD token at all — matching POV's single-call behaviour.
    # AD and DL must never use the RD hardcoded key (wrong service pool).
    if svc == "rd" and not debrid_key:
        g.log(
            "ExternalCache: Torrentio — no RD user key, running hardcoded RD fallback",
            "debug",
        )
        fallback_hashes = _fetch(_TIO_FALLBACK_PARAM, "hardcoded RD fallback")
        cached_hashes = cached_hashes | fallback_hashes

    return cached_hashes


# =========================================================================== #
#  DMM — Real-Debrid cache check (hash-based)
# =========================================================================== #
# DMM's /api/availability/check returns hashes cached on RD via crowdsourced index.
# Requires challenge-response auth (dmmProblemKey + solution) computed locally.
# Max 100 hashes per request. RD-specific — used directly for RD and as a proxy
# for DL. Intentionally excluded from AD (different service pool, different users).
# --------------------------------------------------------------------------- #

_DMM_URL = "https://debridmediamanager.com/api/availability/check"
_DMM_TIMEOUT = 8


def _calc_value_alg(t, n, const):
    temp = t ^ n
    t = ctypes.c_long((temp * const)).value
    t4 = ctypes.c_long(t << 5).value
    t5 = ctypes.c_long((t & 0xFFFFFFFF) >> 27).value
    return t4 | t5


def _slice_hash(s, n):
    half = len(s) // 2
    left_s, right_s = s[:half], s[half:]
    left_n, right_n = n[:half], n[half:]
    interleaved = "".join(ls + ln for ls, ln in zip(left_s, left_n))
    return interleaved + right_n[::-1] + right_s[::-1]


def _generate_hash(e):
    t = ctypes.c_long(0xDEADBEEF ^ len(e)).value
    a = 1103547991 ^ len(e)
    for ch in e:
        n = ord(ch)
        t = _calc_value_alg(t, n, 2654435761)
        a = _calc_value_alg(a, n, 1597334677)
    t = ctypes.c_long(t + ctypes.c_long(a * 1566083941).value).value
    a = ctypes.c_long(a + ctypes.c_long(t * 2024237689).value).value
    return ctypes.c_long(t ^ a).value & 0xFFFFFFFF


def _dmm_get_secret():
    """Generate DMM challenge-response authentication pair."""
    hex_str = f"{random.randrange(10 ** 80):064x}"[:8]
    timestamp = int(time.time())
    dmm_key = f"{hex_str}-{timestamp}"
    s = f"{_generate_hash(dmm_key):x}"
    n = f"{_generate_hash('debridmediamanager.com%%fe7#td00rA3vHz%VmI-' + hex_str):x}"
    solution = _slice_hash(s, n)
    return dmm_key, solution


def dmm_check_cache(hashes, imdb):
    """
    Query DMM availability API for RD-cached hashes.

    :param hashes: list of 40-char info-hash strings
    :param imdb: IMDB ID (e.g. 'tt1234567')
    :return: set of lowercase info-hashes confirmed cached on RD
    """
    cached_hashes = set()
    if not hashes or not imdb:
        return cached_hashes

    try:
        valid_hashes = [h for h in hashes if len(h) == 40]
        if len(valid_hashes) > 100:
            # Take the first 100 rather than random sample — deterministic so
            # the same hashes are checked on retry and results can be compared.
            # Callers already pass hashes in scraper priority order (Tier 2 first).
            valid_hashes = valid_hashes[:100]

        if not valid_hashes:
            return cached_hashes

        dmm_key, solution = _dmm_get_secret()
        data = {
            "dmmProblemKey": dmm_key,
            "solution": solution,
            "imdbId": imdb,
            "hashes": valid_hashes,
        }
        resp = _get_session().post(_DMM_URL, json=data, timeout=_DMM_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()

        available = result.get("available", [])
        for item in available:
            h = item.get("hash", "")
            if h:
                cached_hashes.add(h.lower())

        g.log(
            f"ExternalCache: DMM returned {len(cached_hashes)} cached hashes "
            f"(checked {len(valid_hashes)})",
            "info",
        )
    except Exception as e:
        g.log(f"ExternalCache: DMM check failed: {e}", "warning")

    return cached_hashes


# =========================================================================== #
#  AIOStreams — AD-only cache check with dynamic per-service credentials
# =========================================================================== #
# AIOStreams aggregates MediaFusion + StremThru Torz via the x-aiostreams-user-data
# header (base64-encoded JSON blob built dynamically with the correct credentials).
#
# Only valid for AD:
#   AD user key:      accurate results from the user's own AD account context
#   AD demo key:      staticDemoApikeyPrem fallback — valid because AD's cache is
#                     shared infrastructure (any cached hash is available to all AD
#                     subscribers). This matches POV's approach exactly.
#   RD/DL:            intentionally excluded — no valid same-service demo key;
#                     falling back to AD demo would return AD-pool results for an
#                     RD/DL check, causing false positives at resolve time.
# --------------------------------------------------------------------------- #

# Ordered fallback list — tried in sequence, first success wins.
# fortheweak.cloud is first: it is POV's primary confirmed working instance.
# stremio.ru moved to second — reliable but occasionally slower.
_AIO_URLS = [
    "https://aiostreams.fortheweak.cloud/api/v1/search",
    "https://aiostreams.stremio.ru/api/v1/search",
    "https://aiostreams.viren070.me/api/v1/search",
    "https://aiostreamsfortheweebsstable.midnightignite.me/api/v1/search",
]
_AIO_TIMEOUT = 8   # Outer wall-clock timeout for AIO GET request.
                   # Preset timeouts are 6500ms (matching POV exactly), leaving
                   # 1.5s for AIO to merge and respond before Seren cuts the connection.
_AIO_AD_DEMO_KEY = "staticDemoApikeyPrem"

# AIOStreams preset timeouts set to 6500ms — matching POV's decoded blob exactly.
# Previous 14000ms was 2x longer than necessary, delaying source list on slow AIO.
# Meteor removed — it only indexes RD+TorBox; its hashes are never AD-cached and
# waste AIOStreams' internal aggregation budget.
_AIO_PRESETS = [
    {
        "type": "mediafusion",
        "instanceId": "5b8",
        "enabled": True,
        "options": {
            "name": "MediaFusion",
            "timeout": 6500,
            "resources": ["stream"],
            "useCachedResultsOnly": True,
            "enableWatchlistCatalogs": False,
            "downloadViaBrowser": False,
            "contributorStreams": False,
            "certificationLevelsFilter": [],
            "nudityFilter": [],
            "mediaTypes": [],
        },
    },
    {
        "type": "stremthruTorz",
        "instanceId": "548",
        "enabled": True,
        "options": {
            "name": "StremThru Torz",
            "timeout": 6500,
            "resources": ["stream"],
            "mediaTypes": [],
            "includeP2P": False,
            "useMultipleInstances": False,
        },
    },
]

_AIO_STATIC_CONFIG = {
    "formatter": {"id": "torrentio", "definition": {"name": "", "description": ""}},
    "sortCriteria": {"global": []},
    "deduplicator": {
        "enabled": False,
        "keys": ["infoHash"],
        "multiGroupBehaviour": "aggressive",
        "cached": "single_result",
        "uncached": "per_service",
        "p2p": "single_result",
        "excludeAddons": [],
    },
    "excludeUncached": True,
}


def _build_aio_user_data(service, api_key):
    """
    Build a base64-encoded AIOStreams UserData blob.

    AD: user key -> AD demo key fallback (staticDemoApikeyPrem).
    Other services: returns None — AIOStreams is excluded from RD and DL.

    :param service: "ad" (only supported service for cache checking)
    :param api_key: user's AD apikey, or None
    :return: base64 string, or None if service is unsupported
    """
    svc = (service or "ad").lower()
    if svc != "ad":
        g.log(
            f"ExternalCache: AIOStreams called for {svc.upper()} — excluded, skipping",
            "warning",
        )
        return None

    key = api_key if api_key else _AIO_AD_DEMO_KEY
    payload = {
        "services": [{"id": "alldebrid", "enabled": True, "credentials": {"apiKey": key}}],
        "presets": _AIO_PRESETS,
        **_AIO_STATIC_CONFIG,
    }
    return base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


def aio_check_cache(imdb, season, episode, service="ad", api_key=None):
    """
    Query AIOStreams for AD-cached hashes using the shared demo key.

    Tries each URL in _AIO_URLS in order — first successful response wins.
    Falls back to the next instance on connection errors, timeouts, or HTTP
    5xx responses.  HTTP 4xx (auth/config errors) are treated as permanent
    failures for that instance and are not retried.

    Always uses staticDemoApikeyPrem — AD cache is shared infrastructure so
    any cached hash is visible to all subscribers. Matches POV exactly.

    :param imdb:    IMDB ID (e.g. 'tt1234567')
    :param season:  Season number (int/str) or None for movies
    :param episode: Episode number (int/str) or None for movies
    :param service: Debrid service — only "ad" is supported (default "ad")
    :param api_key: Unused — kept for signature compatibility
    :return: set of 40-char lowercase info-hashes confirmed cached on AD
    """
    if season is not None and str(season).isdigit():
        params = {"type": "series", "id": f"{imdb}:{season}:{episode}"}
    else:
        params = {"type": "movie", "id": str(imdb)}

    hashes = set()
    user_data = _build_aio_user_data(service, None)
    if not user_data:
        return hashes

    headers = {"x-aiostreams-user-data": user_data}
    for url in _AIO_URLS:
        try:
            resp = _get_session().get(
                url, params=params, headers=headers, timeout=_AIO_TIMEOUT
            )
            if resp.status_code >= 500:
                g.log(
                    f"ExternalCache: AIOStreams {url.split('/')[2]} returned "
                    f"HTTP {resp.status_code} — trying next instance",
                    "warning",
                )
                continue
            resp.raise_for_status()
            results = resp.json().get("data", {}).get("results", [])
            for item in results:
                h = item.get("infoHash", "")
                if h:
                    hashes.add(h.lower())
            g.log(
                f"ExternalCache: AIOStreams ({url.split('/')[2]}) returned "
                f"{len(hashes)} cached hashes for AD",
                "info",
            )
            return hashes   # success — no need to try further instances
        except Exception as e:
            g.log(
                f"ExternalCache: AIOStreams {url.split('/')[2]} failed: {e} — "
                f"trying next instance",
                "warning",
            )
            continue

    g.log("ExternalCache: AIOStreams — all instances failed", "warning")
    return hashes


# =========================================================================== #
#  AD Direct Cache Checkers — per-scraper endpoints called in parallel
#  Always fire alongside AIO for AllDebrid to maximise hash coverage.
#  Each checker uses the user's AD key first; falls back to the shared
#  AD demo key (staticDemoApikeyPrem) — valid because AD's cache pool is
#  shared infrastructure (any cached hash is available to all subscribers).
# =========================================================================== #

_MF_BASES     = [
    "https://mediafusion.elfhosted.com",       # 0 — Production (default)
    "https://mediafusion-dev.elfhosted.com",   # 1 — Dev / Beta
]
_STT_BASE     = "https://stremio-stremthru.elfhosted.com"
_METEOR_BASE  = "https://meteorfortheweebs.midnightignite.me"
_COMET_BASES  = ["https://comet.feels.legal", "https://comet.stremio.ru", "https://cometfortheweebs.midnightignite.me"]
_DIRECT_TIMEOUT = 10


def _extract_hashes_from_streams(streams):
    """
    Extract info-hashes from a standard Stremio streams array.
    Checks the 'infoHash' field first, then falls back to regex on 'url'.
    """
    hashes = set()
    for stream in streams:
        h = stream.get("infoHash", "")
        if h and len(h) == 40:
            hashes.add(h.lower())
            continue
        url = stream.get("url", "")
        if url:
            matches = _HASH_PATTERN.findall(url)
            if matches:
                hashes.add(matches[-1].lower())
    return hashes


_COMET_SERVICE_MAP = {
    "ad": "alldebrid",
    "rd": "realdebrid",
    "dl": "debridlink",
    "pm": "premiumize",
    "tb": "torbox",
}

# Meteor only supports Real-Debrid and TorBox.
# It must NEVER be used for AD, DL, PM checks — returns RD/TB hashes only.
_METEOR_SERVICE_MAP = {
    "rd": "realdebrid",
    "tb": "torbox",
}


def _build_stremthru_user_data(api_key):
    """
    Build a base64-encoded StremThru Torz config blob for AD cached-only check.
    """
    payload = {
        "storeTokens": [{"store": "alldebrid", "token": api_key}],
        "prependUncachedStreams": False,
    }
    return base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


def _build_meteor_config(api_key, service="ad"):
    """
    Build a base64-encoded Meteor config blob for cached-only check.

    Meteor ONLY supports Real-Debrid and TorBox. Calling this for AD, DL, or PM
    will produce false positives — those service pools are not indexed by Meteor.
    Guard the call site with _METEOR_SERVICE_MAP before invoking this builder.

    :param api_key: User's debrid token for the target service
    :param service: Debrid service key — "rd" or "tb" only (default "ad" maps to RD
                    as a safety fallback, but callers should never pass "ad")
    """
    meteor_service = _METEOR_SERVICE_MAP.get(service, "realdebrid")
    payload = {
        "debridService": meteor_service,
        "debridApiKey": api_key,
        "onlyCachedStreams": True,
    }
    return base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


def _build_comet_config(api_key, service="ad"):
    """
    Build a base64-encoded Comet config blob for cached-only check.
    cachedOnly=True: Comet returns only hashes confirmed cached on the debrid service.

    :param api_key: User's debrid token for the target service
    :param service: Debrid service key — "ad", "rd", "dl", "pm", "tb" (default "ad")
    """
    comet_service = _COMET_SERVICE_MAP.get(service, "alldebrid")
    payload = {
        "maxResultsPerResolution": 0,
        "maxSize": 0,
        "cachedOnly": True,
        "removeTrash": True,
        "resultFormat": ["title", "metadata"],
        "debridService": comet_service,
        "debridApiKey": api_key,
        "debridStreamProxyPassword": "",
        "languages": {"required": [], "exclude": [], "preferred": []},
        "resolutions": {},
        "options": {
            "remove_ranks_under": -10000000000,
            "allow_english_in_languages": False,
            "remove_unknown_languages": False,
        },
    }
    return base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()


_MF_UUID_RE = __import__('re').compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)


def _get_mf_base():
    """Return the MF base URL based on Seren setting 'mf.instance' (0=Production, 1=Dev/Beta)."""
    try:
        idx = int(g.get_setting("mf.instance") or 0)
        return _MF_BASES[idx] if 0 <= idx < len(_MF_BASES) else _MF_BASES[0]
    except Exception:
        return _MF_BASES[0]


def _get_mf_token():
    """
    Return the user's MediaFusion secret token from Seren settings, or None if unset.
    Handles: full URL paste, D-/U- prefixed token, or bare UUID (auto-prepends U-).
    """
    import re as _re
    raw = g.get_setting("mf.token") or ""
    raw = raw.strip()
    if not raw:
        return None
    # Extract D-/U- token from a full URL or prefixed string
    m = _re.search(r'([DU]-[A-Za-z0-9_\-]+)', raw)
    if m:
        return m.group(1)
    # Bare UUID (copied from MF dashboard without the U- prefix) — add it
    if _MF_UUID_RE.match(raw):
        return 'U-' + raw
    return raw


def mediafusion_check_cache(imdb, season, episode):
    """
    Query MediaFusion directly for cached hashes using the user's personal token.

    Reads the user's D- token from the Seren setting 'mf.token'.
    Returns an empty set immediately if no token is configured — MF is disabled.
    Callers must gate this on 'mf.service' matching the debrid service being checked
    to avoid false positives from a mismatched service token.

    :param imdb: IMDB ID
    :param season: season number or None for movies
    :param episode: episode number or None for movies
    :return: set of 40-char lowercase info-hashes
    """
    hashes = set()
    token = _get_mf_token()
    if not token:
        g.log("ExternalCache: MediaFusion — no token configured, skipping", "debug")
        return hashes
    try:
        if season is not None and str(season).isdigit():
            path = f"series/{imdb}:{season}:{episode}.json"
        else:
            path = f"movie/{imdb}.json"
        url = f"{_get_mf_base()}/{token}/stream/{path}"
        resp = _get_session().get(url, timeout=_DIRECT_TIMEOUT)
        resp.raise_for_status()
        streams = resp.json().get("streams", [])
        # Detect invalid/expired token — MF returns a single placeholder stream
        # with no infoHash and a URL ending in 'invalid_config.mp4'.
        if any('invalid_config' in (s.get('url') or '') or
               'Invalid MediaFusion configuration' in (s.get('description') or '')
               for s in streams):
            g.log(
                "ExternalCache: MediaFusion — token invalid or expired, "
                "reconfigure at mediafusion.elfhosted.com",
                "warning",
            )
            return hashes  # empty set
        hashes = _extract_hashes_from_streams(streams)
        g.log(
            f"ExternalCache: MediaFusion direct returned {len(hashes)} hashes",
            "info",
        )
    except Exception as e:
        g.log(f"ExternalCache: MediaFusion direct check failed: {e}", "warning")
    return hashes


def stremthru_torz_check_cache(imdb, season, episode, api_key=None):
    """
    Query StremThru Torz directly for AD-cached hashes.

    :param imdb: IMDB ID
    :param season: season number or None for movies
    :param episode: episode number or None for movies
    :param api_key: AD apikey (uses demo key if None)
    :return: set of 40-char lowercase info-hashes
    """
    hashes = set()
    key = api_key or _AIO_AD_DEMO_KEY
    try:
        config = _build_stremthru_user_data(key)
        if season is not None and str(season).isdigit():
            path = f"series/{imdb}:{season}:{episode}.json"
        else:
            path = f"movie/{imdb}.json"
        url = f"{_STT_BASE}/{config}/stream/{path}"
        resp = _get_session().get(url, timeout=_DIRECT_TIMEOUT)
        resp.raise_for_status()
        streams = resp.json().get("streams", [])
        hashes = _extract_hashes_from_streams(streams)
        g.log(
            f"ExternalCache: StremThru Torz direct returned {len(hashes)} hashes "
            f"(key={'user' if api_key else 'demo'})",
            "info",
        )
    except Exception as e:
        g.log(f"ExternalCache: StremThru Torz direct check failed: {e}", "warning")
    return hashes


def meteor_check_cache(imdb, season, episode, api_key=None, service="ad"):
    """
    Query Meteor directly for cached hashes.

    Meteor ONLY supports Real-Debrid and TorBox. It must NEVER be called for AD,
    DL, or PM — its index only covers RD/TB pools and would produce false positives
    for other services. Callers must guard with _METEOR_SERVICE_MAP before calling.

    :param imdb: IMDB ID
    :param season: season number or None for movies
    :param episode: episode number or None for movies
    :param api_key: user debrid token (required — Meteor has no valid AD/DL demo key)
    :param service: Debrid service key — "rd" or "tb" only (default "ad" is rejected)
    :return: set of 40-char lowercase info-hashes
    """
    hashes = set()
    # Hard guard: Meteor only supports RD and TorBox.
    if service not in _METEOR_SERVICE_MAP:
        g.log(
            f"ExternalCache: Meteor — service '{service}' not supported "
            f"(RD/TB only). Skipping to prevent false positives.",
            "warning",
        )
        return hashes
    # No demo key fallback for non-AD services — user key required.
    key = api_key
    if not key:
        g.log(f"ExternalCache: Meteor — no {service.upper()} key, skipping", "debug")
        return hashes
    try:
        config = _build_meteor_config(key, service)
        if season is not None and str(season).isdigit():
            path = f"series/{imdb}:{season}:{episode}.json"
        else:
            path = f"movie/{imdb}.json"
        url = f"{_METEOR_BASE}/{config}/stream/{path}"
        resp = _get_session().get(url, timeout=_DIRECT_TIMEOUT)
        resp.raise_for_status()
        streams = resp.json().get("streams", [])
        hashes = _extract_hashes_from_streams(streams)
        g.log(
            f"ExternalCache: Meteor direct returned {len(hashes)} hashes "
            f"for {service.upper()} (user key)",
            "info",
        )
    except Exception as e:
        g.log(f"ExternalCache: Meteor direct check failed: {e}", "warning")
    return hashes


def comet_check_cache(imdb, season, episode, api_key=None, service="ad"):
    """
    Query Comet directly for cached hashes.
    Uses cachedOnly=True so Comet returns only hashes confirmed cached on the
    debrid service. AD falls back to demo key if no user key is configured.
    RD and DL require the user's own key — no valid demo key exists.

    :param imdb: IMDB ID
    :param season: season number or None for movies
    :param episode: episode number or None for movies
    :param api_key: user debrid token (uses AD demo key if None and service is "ad")
    :param service: Debrid service key — "ad", "rd", "dl" (default "ad")
    :return: set of 40-char lowercase info-hashes
    """
    hashes = set()
    # AD: fall back to demo key. RD/DL: user key required — no valid demo key exists.
    key = api_key or (_AIO_AD_DEMO_KEY if service == "ad" else None)
    if not key:
        g.log(f"ExternalCache: Comet — no {service.upper()} key, skipping", "debug")
        return hashes
    try:
        config = _build_comet_config(key, service)
        if season is not None and str(season).isdigit():
            path = f"stream/series/{imdb}:{season}:{episode}.json"
        else:
            path = f"stream/movie/{imdb}.json"
        for base in _COMET_BASES:
            try:
                url = f"{base}/{config}/{path}"
                resp = _get_session().get(url, timeout=_DIRECT_TIMEOUT)
                if resp.status_code >= 500:
                    g.log(
                        f"ExternalCache: Comet {base.split('//')[1][:30]} returned "
                        f"HTTP {resp.status_code} — trying next instance",
                        "warning",
                    )
                    continue
                resp.raise_for_status()
                streams = resp.json().get("streams", [])
                hashes = _extract_hashes_from_streams(streams)
                g.log(
                    f"ExternalCache: Comet direct returned {len(hashes)} hashes "
                    f"from {base.split('//')[1][:30]} for {service.upper()} "
                    f"(key={'user' if api_key else 'demo'})",
                    "info",
                )
                break   # stop at first instance that gives a clean response
            except Exception as e:
                g.log(
                    f"ExternalCache: Comet {base.split('//')[1][:30]} failed: {e} — "
                    f"trying next instance",
                    "warning",
                )
                continue
    except Exception as e:
        g.log(f"ExternalCache: Comet direct check failed: {e}", "warning")
    return hashes



# =========================================================================== #
#  Orchestration — parallel external checks per debrid service
# =========================================================================== #


def check_rd_external(hash_list, imdb, season, episode):
    """
    Run Torrentio + DMM in parallel for Real-Debrid.
    MediaFusion is added when the user has configured an RD token in mf.token/mf.service.

    Torrentio: user's own RD token first (checks their actual cached library).
               Falls back to hardcoded shared RD key only if no user token configured.
               Fallback logic is inside _get_torrentio_debrid_param().
    DMM: RD-crowdsourced index, no debrid key needed. Capped at 100 hashes.
    MediaFusion: only when mf.token is set and mf.service == 2 (Real-Debrid).
                 Uses the user's personal D- token embedded in the URL path.

    Returns:
      (cached_hashes, any_success) where:
        any_success=True  — at least 1 hash confirmed cached (hashes to show)
        any_success=False — all checkers raised exceptions (network failure;
                            caller may fall back to instantAvailability)
        any_success=None  — checkers ran OK but returned 0 cached hashes
                            (genuinely nothing cached; no fallback warranted)

    :param hash_list: list of 40-char info-hash strings to check
    :param imdb: IMDB ID
    :param season: season number or None
    :param episode: episode number or None
    :return: set of cached hashes, success indicator
    """
    all_cached = set()
    checks_ran = 0     # number of checkers that completed without exception

    rd_token = g.get_setting("rd.auth")
    use_mf = bool(_get_mf_token() and g.get_setting("mf.service") == "2")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                torrentio_check_cache, imdb, season, episode, "rd", rd_token
            ): "torrentio",
            executor.submit(dmm_check_cache, hash_list, imdb): "dmm",
        }
        if use_mf:
            futures[executor.submit(
                mediafusion_check_cache, imdb, season, episode
            )] = "mediafusion"
        try:
            for future in as_completed(futures, timeout=12):
                name = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        all_cached.update(result)
                        checks_ran += 1
                except Exception as e:
                    g.log(f"ExternalCache RD: {name} thread error: {e}", "warning")
        except Exception as e:
            g.log(
                f"ExternalCache RD: as_completed timeout — collecting partial results "
                f"({len(all_cached)} hashes so far): {e}",
                "warning",
            )
            for future, name in futures.items():
                if future.done():
                    try:
                        result = future.result()
                        if result is not None:
                            all_cached.update(result)
                            checks_ran += 1
                    except Exception as fe:
                        g.log(f"ExternalCache RD: {name} partial result error: {fe}", "warning")

    mf_label = "+MF" if use_mf else ""
    g.log(
        f"ExternalCache RD: {len(all_cached)} cached hashes from Torrentio+DMM{mf_label}",
        "info",
    )
    # any_success semantics:
    #   True  → found cached hashes (show them)
    #   None  → checkers ran but 0 found (genuinely empty, no fallback needed)
    #   False → all checkers failed with exceptions (network error; caller may
    #           fall back to instantAvailability)
    if all_cached:
        return all_cached, True
    if checks_ran > 0:
        return all_cached, None   # ran OK, genuinely 0 cached
    return all_cached, False      # all checkers threw exceptions


def check_ad_external(imdb, season, episode):
    """
    Run AIOStreams + Torrentio + Comet in parallel for AllDebrid.
    MediaFusion is added when the user has configured an AD token in mf.token/mf.service.

    AIOStreams:  always uses AD demo key (staticDemoApikeyPrem). Matches POV exactly.
                Internally queries MF + StremThru Torz via _AIO_PRESETS (Meteor
                removed — RD/TorBox-only, wastes AIO aggregation budget).
                Preset timeout 6500ms matches POV; outer _AIO_TIMEOUT gives 1.5s
                margin for AIO to merge and respond.
    Torrentio:  user's own AD key only — no hardcoded RD fallback for AD.
    MediaFusion: only when mf.token is set and mf.service == 1 (AllDebrid).
                 Uses the user's personal D- token embedded in the URL path.
    Comet:      always uses AD demo key (cachedOnly=True).

    NOTE: Meteor is intentionally excluded — it only supports Real-Debrid and TorBox,
    not AllDebrid. Using Meteor's demo key returns RD/TorBox-cached hashes which
    produce false positives for AD cache checking.

    All active checkers run in parallel and results are union-merged.

    Returns:
      (cached_hashes, success) where success matches check_rd_external semantics:
        True  — at least 1 hash confirmed cached
        None  — checkers ran but 0 found (genuinely empty)
        False — all checkers threw exceptions (network failure)

    :param imdb: IMDB ID
    :param season: season number or None
    :param episode: episode number or None
    :return: set of cached hashes, success indicator
    """
    all_cached = set()
    checks_ran = 0

    ad_key = g.get_setting("alldebrid.apikey")
    use_mf = bool(_get_mf_token() and g.get_setting("mf.service") == "1")

    executor = ThreadPoolExecutor(max_workers=4)
    futures = {
        executor.submit(
            aio_check_cache, imdb, season, episode, "ad"
        ): "aiostreams",
        executor.submit(
            torrentio_check_cache, imdb, season, episode, "ad", ad_key
        ): "torrentio",
        executor.submit(
            comet_check_cache, imdb, season, episode, None
        ): "comet",
    }
    if use_mf:
        futures[executor.submit(
            mediafusion_check_cache, imdb, season, episode
        )] = "mediafusion"

    try:
        for future in as_completed(futures, timeout=30):
            name = futures[future]
            try:
                result = future.result()
                if result is not None:
                    all_cached.update(result)
                    checks_ran += 1
            except Exception as e:
                g.log(f"ExternalCache AD: {name} thread error: {e}", "warning")
    except Exception as e:
        g.log(
            f"ExternalCache AD: as_completed timeout — collecting partial results "
            f"({len(all_cached)} hashes so far): {e}",
            "warning",
        )
        for future, name in futures.items():
            if future.done():
                try:
                    result = future.result()
                    if result is not None:
                        all_cached.update(result)
                        checks_ran += 1
                except Exception as fe:
                    g.log(f"ExternalCache AD: {name} partial result error: {fe}", "warning")

    executor.shutdown(wait=False)
    mf_label = "+MF" if use_mf else ""
    g.log(
        f"ExternalCache AD: {len(all_cached)} cached hashes from AIO+Torrentio+Comet{mf_label}",
        "info",
    )
    if all_cached:
        return all_cached, True
    if checks_ran > 0:
        return all_cached, None   # ran OK, genuinely 0 cached
    return all_cached, False      # all checkers threw exceptions


def check_dl_external(hash_list, imdb, season, episode):
    """
    Query Comet for Debrid-Link cached hashes.
    MediaFusion is added when the user has configured a DL token in mf.token/mf.service.

    Comet (CometNet user-activity pool) is the only aggregator that tracks DL
    cache status.  All other sources were evaluated and removed:

      Torrentio:    REMOVED (S168a) — Torrentio accepts DL API keys for stream
                    *resolution* but has never implemented a cache-status
                    workaround for DL.  Unlike RD (where Torrentio tracks user
                    activity to infer [RD+]), the developer explicitly opted out
                    for AD and DL.  Result: 0 cached hashes on every scrape in
                    S168a log analysis (15+ calls, 0 hits, 1 timeout at 15 s).
                    Corroborated by r/StremioAddons Dec 2024 / Apr 2025 threads.
      MediaFusion:  now supported via user personal token (mf.service == 0 = DL).
      StremThru:    401 Unauthorized on every known public instance (S159).
      Native probe: /v2/seedbox/cached returns endpointDisabled since late 2024.
      Meteor:       RD/TorBox only — its hashes are never DL-cached.
      DMM:          RD-crowdsourced, systematic DL false positives (S154).
      AIOStreams:   No valid DL demo key; AD-only (S131).

    Returns:
      (cached_hashes, success) — success semantics match check_rd/ad_external:
        True  — at least 1 hash confirmed cached
        None  — checkers ran but returned 0 (genuinely empty for this title)
        False — all checkers threw exceptions (network failure)

    :param hash_list: list of info-hash strings (unused — kept for caller compat)
    :param imdb: IMDB ID
    :param season: season number or None
    :param episode: episode number or None
    :return: (set of cached hashes, success indicator)
    """
    dl_token = g.get_setting("debridlink.token")
    if not dl_token:
        g.log("ExternalCache DL: no DL token — skipping Comet check", "debug")
        return set(), False

    all_cached = set()
    checks_ran = 0
    use_mf = bool(_get_mf_token() and g.get_setting("mf.service") == "0")

    executor = ThreadPoolExecutor(max_workers=2)
    futures = {
        executor.submit(
            comet_check_cache, imdb, season, episode, dl_token, "dl"
        ): "comet"
    }
    if use_mf:
        futures[executor.submit(
            mediafusion_check_cache, imdb, season, episode
        )] = "mediafusion"

    try:
        for future in as_completed(futures, timeout=10):
            name = futures[future]
            try:
                result = future.result()
                if result is not None:
                    all_cached.update(result)
                    checks_ran += 1
            except Exception as e:
                g.log(f"ExternalCache DL: {name} thread error: {e}", "warning")
    except Exception as e:
        g.log(
            f"ExternalCache DL: as_completed timeout — collecting partial results "
            f"({len(all_cached)} hashes so far): {e}",
            "warning",
        )
        for future, name in futures.items():
            if future.done():
                try:
                    result = future.result()
                    if result is not None:
                        all_cached.update(result)
                        checks_ran += 1
                except Exception as fe:
                    g.log(f"ExternalCache DL: {name} partial result error: {fe}", "warning")

    executor.shutdown(wait=False)
    mf_label = "+MF" if use_mf else ""
    g.log(
        f"ExternalCache DL: {len(all_cached)} cached hashes from Comet{mf_label}",
        "info",
    )
    if all_cached:
        return all_cached, True
    if checks_ran > 0:
        return all_cached, None   # ran OK, genuinely 0 cached for this title
    return all_cached, False      # all checkers threw exceptions
