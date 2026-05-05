import json
import os
import threading
import time
import xml.etree.ElementTree as ET

import xbmc
import xbmcvfs

from resources.utils import giptv
from resources.utils.xtream import STATE
from resources.apis.xmltv_fetcher import fetch_xmltv, ensure_epg_source_is_current

ADDON_ID = "plugin.video.giptv"

EPG_KEEP_DAYS = 7
EPG_LOCK_FILENAME = ".epg.lock"
EPG_LOCK_TTL = 30 * 60  # 30 minutes safety
EPG_TTL_SECONDS = 6 * 60 * 60  # 6 hours

SOURCE_CHECK_INTERVAL = 5 * 60  # 5 minutes
NOW_NEXT_TTL_SECONDS = 120  # 2 minutes

_XMLTV_INDEX = None
_LAST_LOADED = 0
_LAST_SOURCE_CHECK = 0
_WARMING = False
_LOCK = threading.Lock()

_NOW_NEXT_CACHE = {}


def log(msg, level=xbmc.LOGINFO):
    giptv.log(msg, level)


def _cache_dir():
    base = xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}/cache")
    if not xbmcvfs.exists(base):
        xbmcvfs.mkdirs(base)
    return base


def _cache_filename():
    user = STATE.username or "default"
    server = STATE.server or "server"

    server = server.strip().lower()
    server = server.replace("http://", "").replace("https://", "")
    server = server.rstrip("/")

    safe_user = user.replace("/", "_").replace(":", "_")
    safe_server = server.replace("/", "_").replace(":", "_")

    return f"epg_index_{safe_user}_{safe_server}.json"


def _cache_path():
    return os.path.join(_cache_dir(), _cache_filename())


def _epg_lock_path():
    return os.path.join(_cache_dir(), EPG_LOCK_FILENAME)


def _clear_now_next_cache():
    _NOW_NEXT_CACHE.clear()


def _acquire_epg_lock():
    path = _epg_lock_path()

    if xbmcvfs.exists(path):
        try:
            stat = xbmcvfs.Stat(path)
            if time.time() - stat.st_mtime() < EPG_LOCK_TTL:
                log("EPG warm already running — skipping")
                return False
        except Exception:
            pass

    f = xbmcvfs.File(path, "w")
    try:
        f.write(str(int(time.time())))
    finally:
        f.close()

    return True


def _release_epg_lock():
    path = _epg_lock_path()
    if xbmcvfs.exists(path):
        xbmcvfs.delete(path)


def _norm(s):
    return str(s).strip().upper().replace(" ", "_").replace("-", "_")


def _parse_xmltv_time(t):
    """
    XMLTV time formats:
    - YYYYMMDDHHMMSS
    - YYYYMMDDHHMMSS +0000
    - YYYYMMDDHHMMSS +0100
    Returns unix timestamp or None if invalid.
    """
    if not t:
        return None

    try:
        t = str(t).strip()
        if not t:
            return None

        if " " in t:
            t = t.split(" ", 1)[0]

        t = t[:14]

        if len(t) != 14 or not t.isdigit():
            log(f"Invalid XMLTV timestamp: {t}", xbmc.LOGWARNING)
            return None

        return int(time.mktime(time.strptime(t, "%Y%m%d%H%M%S")))
    except Exception as e:
        log(f"Failed to parse XMLTV time '{t}': {e}", xbmc.LOGWARNING)
        return None


def _build_epg_index(xmltv_path):
    """
    Returns:
    {
      CHANNEL_ID: [
        (start_ts, end_ts, title, desc),
        ...
      ]
    }
    """
    log("Parsing XMLTV… (this may take a moment)")
    start_time = time.time()

    tree = ET.parse(xmltv_path)
    root = tree.getroot()

    index = {}
    skipped = 0

    for prog in root.findall("programme"):
        try:
            channel = prog.get("channel")
            if not channel:
                skipped += 1
                continue

            channel = _norm(channel)

            start = prog.get("start")
            stop = prog.get("stop")
            if not start or not stop:
                skipped += 1
                continue

            start_ts = _parse_xmltv_time(start)
            end_ts = _parse_xmltv_time(stop)

            if start_ts is None or end_ts is None:
                skipped += 1
                continue

            title_el = prog.find("title")
            desc_el = prog.find("desc")

            title = title_el.text if title_el is not None and title_el.text else ""
            desc = desc_el.text if desc_el is not None and desc_el.text else ""

            index.setdefault(channel, []).append((start_ts, end_ts, title, desc))
        except Exception as e:
            skipped += 1
            log(f"Skipping bad programme entry: {e}", xbmc.LOGWARNING)

    for channel in index:
        index[channel].sort(key=lambda x: x[0])

    log(
        f"XMLTV parsed: {len(index)} channels in {time.time() - start_time:.2f}s "
        f"(skipped {skipped} bad entries)",
        xbmc.LOGINFO,
    )
    return index


def _programme_key(prog):
    return (
        int(prog[0]),
        int(prog[1]),
        str(prog[2] or ""),
        str(prog[3] or ""),
    )


def _trim_index(index, keep_days=EPG_KEEP_DAYS):
    cutoff_ts = int(time.time()) - (keep_days * 24 * 60 * 60)
    trimmed = {}

    for channel, programmes in (index or {}).items():
        kept = [
            prog
            for prog in programmes
            if prog and len(prog) >= 2 and int(prog[1]) >= cutoff_ts
        ]
        if kept:
            kept.sort(key=lambda x: int(x[0]))
            trimmed[channel] = kept

    return trimmed


def _merge_indexes(old_index, new_index, keep_days=EPG_KEEP_DAYS):
    merged = {}
    all_channels = set((old_index or {}).keys()) | set((new_index or {}).keys())

    for channel in all_channels:
        seen = set()
        combined = []

        for source in (
            (old_index or {}).get(channel, []),
            (new_index or {}).get(channel, []),
        ):
            for prog in source:
                if not prog or len(prog) < 4:
                    continue

                key = _programme_key(prog)
                if key in seen:
                    continue

                seen.add(key)
                combined.append(prog)

        if combined:
            combined.sort(key=lambda x: int(x[0]))
            merged[channel] = combined

    return _trim_index(merged, keep_days=keep_days)


def _load_cache():
    path = _cache_path()
    if not xbmcvfs.exists(path):
        return None, 0

    try:
        f = xbmcvfs.File(path, "r")
        raw = f.read()
        f.close()

        data = json.loads(raw)
        index = data.get("index") or {}
        ts = int(data.get("timestamp", 0) or 0)

        index = _trim_index(index, keep_days=EPG_KEEP_DAYS)
        return index, ts
    except Exception as e:
        log(f"Failed to load EPG cache: {e}", xbmc.LOGWARNING)
        return None, 0


def _save_cache(index):
    path = _cache_path()

    existing_index, _ = _load_cache()
    merged_index = _merge_indexes(
        existing_index or {},
        index or {},
        keep_days=EPG_KEEP_DAYS,
    )

    payload = {
        "timestamp": int(time.time()),
        "index": merged_index,
    }

    try:
        f = xbmcvfs.File(path, "w")
        f.write(json.dumps(payload))
        f.close()
    except Exception as e:
        log(f"Failed to save EPG cache: {e}", xbmc.LOGWARNING)

    return merged_index


def _maybe_validate_epg_source():
    global _LAST_SOURCE_CHECK

    now = int(time.time())
    if now - _LAST_SOURCE_CHECK < SOURCE_CHECK_INTERVAL:
        return

    try:
        ensure_epg_source_is_current()
    except Exception as e:
        log(f"Failed EPG source check: {e}", xbmc.LOGWARNING)
    finally:
        _LAST_SOURCE_CHECK = now


def _warm_epg():
    global _XMLTV_INDEX, _LAST_LOADED, _WARMING

    with _LOCK:
        if _WARMING:
            return
        _WARMING = True

    if not _acquire_epg_lock():
        with _LOCK:
            _WARMING = False
        return

    try:
        username = STATE.username or "default"
        server = STATE.server or "server"

        log(f"EPG warm-up started for {username} / {server}")

        xmltv_path = fetch_xmltv()
        if not xmltv_path:
            log("XMLTV fetch failed during warm-up", xbmc.LOGERROR)
            return

        fresh_index = _build_epg_index(xmltv_path)
        merged_index = _save_cache(fresh_index)

        with _LOCK:
            _XMLTV_INDEX = merged_index
            _LAST_LOADED = int(time.time())

        _clear_now_next_cache()
        log("EPG warm-up complete")

    finally:
        _release_epg_lock()
        with _LOCK:
            _WARMING = False


def get_xmltv_index():
    """
    Fast, source-aware:
    - throttled source validation
    - returns memory cache if present
    - falls back to disk cache
    - warms in background when stale
    - warms synchronously if nothing cached
    """
    global _XMLTV_INDEX, _LAST_LOADED, _WARMING

    _maybe_validate_epg_source()

    with _LOCK:
        if _XMLTV_INDEX is not None:
            if (time.time() - _LAST_LOADED > EPG_TTL_SECONDS) and not _WARMING:
                threading.Thread(target=_warm_epg, daemon=True).start()
            return _XMLTV_INDEX

    index, ts = _load_cache()
    if index:
        with _LOCK:
            _XMLTV_INDEX = index
            _LAST_LOADED = ts

        if (time.time() - ts > EPG_TTL_SECONDS) and not _WARMING:
            threading.Thread(target=_warm_epg, daemon=True).start()

        log("Loaded EPG index from disk cache")
        return index

    log("No cached EPG found, warming synchronously")
    _warm_epg()

    with _LOCK:
        if _XMLTV_INDEX is not None:
            return _XMLTV_INDEX

    log("EPG warm failed, returning empty index", xbmc.LOGWARNING)
    return {}


def get_now(xmltv_index, channel_id):
    if not xmltv_index or not channel_id:
        return None

    cid = _norm(channel_id)
    programmes = xmltv_index.get(cid)
    if not programmes:
        return None

    now_ts = int(time.time())

    for start_ts, end_ts, title, desc in programmes:
        if start_ts <= now_ts < end_ts:
            return (title, desc, start_ts, end_ts)

        if start_ts > now_ts:
            break

    return None


def get_now_next(xmltv_index, channel_id, offset_minutes=0):
    if not xmltv_index or not channel_id:
        return None

    cid = _norm(channel_id)
    programmes = xmltv_index.get(cid)
    if not programmes:
        return None

    effective_ts = int(time.time()) + (int(offset_minutes) * 60)
    bucket = effective_ts // NOW_NEXT_TTL_SECONDS
    cache_key = f"{cid}:{int(offset_minutes)}:{bucket}"

    cached = _NOW_NEXT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    now_prog = None
    next_prog = None

    for start_ts, end_ts, title, desc in programmes:
        if start_ts <= effective_ts < end_ts:
            now_prog = (title, desc, start_ts, end_ts)
            continue

        if start_ts > effective_ts:
            next_prog = (title, desc, start_ts, end_ts)
            break

    result = {
        "now": now_prog,
        "next": next_prog,
    }

    _NOW_NEXT_CACHE[cache_key] = result
    return result


def resolve_xmltv_channel_id(stream):
    cid = stream.get("epg_channel_id") or stream.get("tvg_id")
    if not cid:
        return None
    return str(cid).strip().upper().replace(" ", "_").replace("-", "_")


def clear_epg_cache():
    global _XMLTV_INDEX, _LAST_LOADED, _WARMING, _LAST_SOURCE_CHECK

    cache_dir = _cache_dir()
    user = STATE.username or "default"
    server = STATE.server or "server"

    log(f"Clearing EPG cache for user='{user}' server='{server}'", xbmc.LOGINFO)

    json_cache = _cache_path()
    if xbmcvfs.exists(json_cache):
        try:
            xbmcvfs.delete(json_cache)
            log(f"Deleted EPG JSON cache: {json_cache}")
        except Exception as e:
            log(f"Failed to delete EPG JSON cache: {e}", xbmc.LOGWARNING)

    xmltv_filename = f"{user}_xmltv.xml"
    xmltv_path = os.path.join(cache_dir, xmltv_filename)

    if xbmcvfs.exists(xmltv_path):
        try:
            xbmcvfs.delete(xmltv_path)
            log(f"Deleted XMLTV cache: {xmltv_path}")
        except Exception as e:
            log(f"Failed to delete XMLTV cache: {e}", xbmc.LOGWARNING)

    with _LOCK:
        _XMLTV_INDEX = None
        _LAST_LOADED = 0
        _WARMING = False

    _LAST_SOURCE_CHECK = 0
    _clear_now_next_cache()

    try:
        _release_epg_lock()
    except Exception as e:
        log(f"Failed to release EPG lock: {e}", xbmc.LOGWARNING)

    log("EPG cache fully reset", xbmc.LOGINFO)
