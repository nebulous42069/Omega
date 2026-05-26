"""TheIntroDB API client — community-submitted intro/recap/credits/preview timestamps.

API docs: https://api.theintrodb.org/v3
Endpoint: GET /media?tmdb_id={id}[&season={s}&episode={e}][&duration_ms={ms}]
         or GET /media?imdb_id=tt{id}[&season={s}&episode={e}][&duration_ms={ms}]

Returns segments grouped by type:
- intro / recap: start can be null (treated as 0); end required
- credits / preview: start required; end can be null (means "end of media")

No auth required for low-volume use; optional Bearer API key for higher rate limits.
duration_ms (v3): media duration in milliseconds; improves segment accuracy.
"""

import time
import threading

import requests

from resources.lib.modules.globals import g

_API_BASE = "https://api.theintrodb.org/v3"
_MIN_REQUEST_GAP = 0.4  # seconds between requests
_REQUEST_TIMEOUT = 8

# Module-level rate-limit state (shared across calls in a single process)
_lock = threading.Lock()
_last_request_time = 0.0
_rate_limit_until = 0.0


def _wait_rate_limit():
    """Honour the inter-request gap and any active 429 backoff.

    Returns:
        True if request may proceed, False if currently rate-limited.
    """
    global _last_request_time
    with _lock:
        now = time.time()
        if now < _rate_limit_until:
            g.log(f"TheIntroDB rate-limited until {_rate_limit_until:.0f}", "debug")
            return False
        gap = now - _last_request_time
        if gap < _MIN_REQUEST_GAP:
            time.sleep(_MIN_REQUEST_GAP - gap)
        _last_request_time = time.time()
        return True


def _do_request(url, api_key=None):
    """Fetch and parse JSON from the API. Returns dict or None on failure."""
    global _rate_limit_until

    headers = {
        "Accept": "application/json",
        "User-Agent": "Seren/TheIntroDB",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT)

        if resp.status_code == 429:
            retry = 300
            for header in ("X-UsageLimit-Reset", "X-RateLimit-Reset", "Retry-After"):
                val = resp.headers.get(header)
                if val:
                    try:
                        retry = int(val)
                    except ValueError:
                        pass
                    break
            with _lock:
                _rate_limit_until = time.time() + retry
            g.log(f"TheIntroDB 429 — backoff {retry}s", "warning")
            return None

        if resp.status_code == 404:
            g.log("TheIntroDB: media not in database", "debug")
            return None

        if not resp.ok:
            g.log(f"TheIntroDB HTTP {resp.status_code}", "warning")
            return None

        return resp.json()

    except requests.RequestException as e:
        g.log(f"TheIntroDB network error: {e}", "warning")
        return None
    except (ValueError, KeyError) as e:
        g.log(f"TheIntroDB parse error: {e}", "warning")
        return None


def _build_url(tmdb_id, imdb_id, season, episode, is_movie, duration_ms=None):
    """Build the /media query URL. Prefers TMDB id, falls back to IMDb."""
    dur_q = ""
    try:
        if duration_ms is not None:
            dur_int = int(duration_ms)
            if dur_int > 0:
                dur_q = f"&duration_ms={dur_int}"
    except (TypeError, ValueError):
        pass

    # TMDB path
    if tmdb_id:
        try:
            tid = str(tmdb_id).strip()
            if int(tid) <= 0:
                tid = None
        except (ValueError, TypeError):
            tid = None

        if tid:
            if is_movie:
                return f"{_API_BASE}/media?tmdb_id={tid}{dur_q}", "tmdb"
            try:
                s = int(season)
                e = int(episode)
                if s > 0 and e > 0:
                    return (
                        f"{_API_BASE}/media?tmdb_id={tid}&season={s}&episode={e}{dur_q}",
                        "tmdb",
                    )
            except (TypeError, ValueError):
                pass

    # IMDb path
    if imdb_id:
        imdb = str(imdb_id).strip()
        if imdb.startswith("tt"):
            if is_movie:
                return f"{_API_BASE}/media?imdb_id={imdb}{dur_q}", "imdb"
            try:
                s = int(season)
                e = int(episode)
                if s > 0 and e > 0:
                    return (
                        f"{_API_BASE}/media?imdb_id={imdb}&season={s}&episode={e}{dur_q}",
                        "imdb",
                    )
            except (TypeError, ValueError):
                pass

    return None, None


def _pick_best_segments(raw, segment_type):
    """Filter and rank segments of a given type.

    intro/recap: start optional (default 0), end required.
    credits/preview: start required, end optional (None = end of media).

    Returns list of dicts: [{'start': float|None, 'end': float|None, 'score': float}, ...],
    sorted by score descending (best first).
    """
    if not raw:
        return []

    valid = []
    for seg in raw:
        if not isinstance(seg, dict):
            continue
        start_ms = seg.get("start_ms")
        end_ms = seg.get("end_ms")

        if segment_type in ("intro", "recap"):
            if end_ms is None:
                continue
            if start_ms is None:
                start_ms = 0
        elif segment_type in ("credits", "preview"):
            if start_ms is None:
                continue
            # end_ms can be None (means end of media)

        if end_ms is not None and end_ms <= (start_ms or 0):
            continue

        confidence = seg.get("confidence")
        if confidence is None:
            confidence = 0.5
        count = seg.get("submission_count", 1) or 1
        score = float(confidence) + count * 0.001

        valid.append({
            "start": (start_ms / 1000.0) if start_ms is not None else None,
            "end": (end_ms / 1000.0) if end_ms is not None else None,
            "score": score,
        })

    valid.sort(key=lambda x: x["score"], reverse=True)
    return valid


def query_segments(tmdb_id=None, imdb_id=None, season=None, episode=None,
                   is_movie=False, api_key=None, duration_ms=None):
    """Fetch all segment types for a media item.

    Returns:
        dict mapping segment_type -> list of segments (best-first), e.g.:
            {'intro': [{'start': 0.0, 'end': 95.5, 'score': 0.85}], 'credits': [...]}
        Empty dict on failure or if media not in DB.
    """
    url, mode = _build_url(tmdb_id, imdb_id, season, episode, is_movie, duration_ms=duration_ms)
    if not url:
        if tmdb_id or imdb_id:
            g.log("TheIntroDB: need TMDB id, or IMDb tt… id with season/episode for TV", "debug")
        return {}

    g.log(f"TheIntroDB query ({mode}): {url}", "debug")

    if not _wait_rate_limit():
        return {}

    data = _do_request(url, api_key=api_key)
    if not data:
        return {}

    if "error" in data:
        g.log(f"TheIntroDB error: {data['error']}", "debug")
        return {}

    result = {}
    for seg_type in ("intro", "recap", "credits", "preview"):
        segments = _pick_best_segments(data.get(seg_type, []), seg_type)
        if segments:
            result[seg_type] = segments

    return result
