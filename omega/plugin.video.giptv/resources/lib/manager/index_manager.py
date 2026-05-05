# -*- coding: utf-8 -*-
import json
import os
import unicodedata
import threading
import time

import xbmc
import xbmcaddon
import xbmcvfs

from resources.utils.config import ensure_api_ready
from resources.utils.xtream import STATE
import resources.apis.xtream_api as xtream_api
import resources.utils.giptv as giptv

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")

_INDEX_LOCK = threading.Lock()
_INDEX_BUILDING = False

# Tunables
RECENT_BUILD_COOLDOWN = 600  # 10 minutes
INDEX_FRESH_AGE = 21600  # 6 hours
STALE_RUNNING_AGE = 7200  # 2 hours
STALE_LOCK_AGE = 7200  # 2 hours


# ============================================================
#  PATH / STATE HELPERS
# ============================================================


def _safe_part(value, default="default"):
    value = value or default
    value = str(value)
    for ch in ("://", "/", "\\", ":", "?", "&", "=", " "):
        value = value.replace(ch, "_")
    return value.strip("_") or default


def _state_key():
    username = _safe_part(getattr(STATE, "username", None), "default")
    server = _safe_part(getattr(STATE, "server", None), "server")
    return f"{username}_{server}"


def _index_dir():
    path = xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}/index")
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path


def _index_path(name):
    return os.path.join(_index_dir(), f"{_state_key()}_{name}_index.json")


def _index_lock_path():
    return os.path.join(_index_dir(), f".{_state_key()}.index.lock")


def _state_path():
    return os.path.join(_index_dir(), f"{_state_key()}_index_state.json")


def _read_text_file(path):
    if not xbmcvfs.exists(path):
        return ""

    f = xbmcvfs.File(path, "r")
    try:
        return f.read() or ""
    finally:
        f.close()


def _write_text_file(path, text):
    f = xbmcvfs.File(path, "w")
    try:
        f.write(text)
    finally:
        f.close()


def _read_state():
    raw = _read_text_file(_state_path())
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except Exception:
        return {}


def _write_state(data):
    try:
        _write_text_file(_state_path(), json.dumps(data, ensure_ascii=False))
    except Exception as exc:
        giptv.log(f"[INDEX_MANAGER] Failed writing state file: {exc}", xbmc.LOGWARNING)


def _clear_state():
    path = _state_path()
    if xbmcvfs.exists(path):
        xbmcvfs.delete(path)


# ============================================================
#  LOCK HELPERS
# ============================================================


def _acquire_index_lock(max_age=STALE_LOCK_AGE):
    lock_path = _index_lock_path()
    now = time.time()

    if xbmcvfs.exists(lock_path):
        raw = _read_text_file(lock_path)
        ts = 0
        try:
            ts = float(raw or 0)
        except Exception:
            ts = 0

        age = now - ts if ts else 0

        if ts and age < max_age:
            giptv.log(
                "[INDEX_MANAGER] Lock exists — build already running", xbmc.LOGINFO
            )
            return False

        giptv.log("[INDEX_MANAGER] Stale lock found — removing", xbmc.LOGWARNING)
        xbmcvfs.delete(lock_path)

    try:
        _write_text_file(lock_path, str(now))
        return True
    except Exception as exc:
        giptv.log(f"[INDEX_MANAGER] Failed creating lock file: {exc}", xbmc.LOGERROR)
        return False


def _release_index_lock():
    lock_path = _index_lock_path()
    if xbmcvfs.exists(lock_path):
        xbmcvfs.delete(lock_path)


# ============================================================
#  UTIL
# ============================================================


def _normalize_title(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _write_index(name, data):
    path = _index_path(name)
    payload = json.dumps(data, ensure_ascii=False)
    _write_text_file(path, payload)


def _read_index(name):
    if not ensure_api_ready():
        return []

    path = _index_path(name)
    if not xbmcvfs.exists(path):
        return []

    raw = _read_text_file(path)
    if not raw:
        return []

    try:
        return json.loads(raw)
    except Exception:
        return []


def _file_mtime(path):
    try:
        stat = xbmcvfs.Stat(path)
        # Kodi vfs Stat usually exposes st_mtime()
        return stat.st_mtime()
    except Exception:
        return 0


def _index_last_modified():
    latest = 0
    for name in ("vod", "series", "live"):
        path = _index_path(name)
        if not xbmcvfs.exists(path):
            return 0
        latest = max(latest, _file_mtime(path))
    return latest


def index_exists_and_valid():
    if not ensure_api_ready():
        return False

    for name in ("vod", "series", "live"):
        path = _index_path(name)
        if not xbmcvfs.exists(path):
            return False

        try:
            stat = xbmcvfs.Stat(path)
            if stat.st_size() < 16:
                return False
        except Exception:
            return False

    return True


def index_is_fresh(max_age_seconds=INDEX_FRESH_AGE):
    last_mod = _index_last_modified()
    if not last_mod:
        return False
    return (time.time() - last_mod) < max_age_seconds


def ran_recently(cooldown_seconds=RECENT_BUILD_COOLDOWN):
    state = _read_state()
    finished_at = state.get("finished_at", 0) or 0
    if not finished_at:
        return False
    return (time.time() - finished_at) < cooldown_seconds


def build_in_progress(max_stale_seconds=STALE_RUNNING_AGE):
    state = _read_state()

    if state.get("status") != "running":
        return False

    started_at = state.get("started_at", 0) or 0
    if not started_at:
        return False

    age = time.time() - started_at
    if age > max_stale_seconds:
        giptv.log(
            "[INDEX_MANAGER] Stale running state detected — ignoring", xbmc.LOGWARNING
        )
        return False

    return True


def should_build(
    force=False,
    cooldown_seconds=RECENT_BUILD_COOLDOWN,
    fresh_age_seconds=INDEX_FRESH_AGE,
):
    if force:
        return True, "forced"

    if build_in_progress():
        return False, "build already running"

    if ran_recently(cooldown_seconds=cooldown_seconds):
        return False, "build ran recently"

    if index_exists_and_valid() and index_is_fresh(max_age_seconds=fresh_age_seconds):
        return False, "index is still fresh"

    return True, "build needed"


# ============================================================
#  CORE BUILDER
# ============================================================


def build_index(monitor=None, notify=True, source="unknown", force=False):
    """
    Unified index builder with:
      - in-process lock
      - cross-invocation file lock
      - recent-run cooldown
      - fresh-index skip
      - stale lock/state handling
    """
    global _INDEX_BUILDING

    allowed, reason = should_build(force=force)
    if not allowed:
        giptv.log(
            f"[INDEX_MANAGER] Skipping build: {reason} | source={source}", xbmc.LOGINFO
        )
        return False

    with _INDEX_LOCK:
        if _INDEX_BUILDING:
            giptv.log(
                f"[INDEX_MANAGER] Build already running in-process | source={source}",
                xbmc.LOGINFO,
            )
            return False
        _INDEX_BUILDING = True

    acquired = False
    started_at = time.time()

    try:
        # Double-check after in-process lock
        if not force and build_in_progress():
            giptv.log(
                f"[INDEX_MANAGER] Skipping build: running state already active | source={source}",
                xbmc.LOGINFO,
            )
            return False

        acquired = _acquire_index_lock()
        if not acquired:
            return False

        _write_state(
            {
                "status": "running",
                "started_at": started_at,
                "finished_at": 0,
                "source": source,
            }
        )

        if not ensure_api_ready():
            giptv.log("[INDEX_MANAGER] API not configured", xbmc.LOGERROR)
            return False

        giptv.log(
            f"[INDEX_MANAGER] Building index for {STATE.username} / {STATE.server} | source={source}",
            xbmc.LOGINFO,
        )

        # ------------------ VOD ------------------
        vod_index = {}
        vod_cats = xtream_api.categories(xtream_api.VOD_TYPE) or []

        for cat in vod_cats:
            if monitor and monitor.abortRequested():
                giptv.log(
                    "[INDEX_MANAGER] Build aborted during VOD categories",
                    xbmc.LOGWARNING,
                )
                return False

            if not isinstance(cat, dict):
                continue

            cat_id = cat.get("category_id")
            cat_name = cat.get("category_name", "")
            if not cat_id:
                continue

            movies = xtream_api.streams_by_category(xtream_api.VOD_TYPE, cat_id) or []

            for m in movies:
                if monitor and monitor.abortRequested():
                    giptv.log(
                        "[INDEX_MANAGER] Build aborted during VOD streams",
                        xbmc.LOGWARNING,
                    )
                    return False

                if not isinstance(m, dict):
                    continue

                sid = m.get("stream_id")
                if not sid:
                    continue

                title = m.get("name") or m.get("title") or "Unknown"
                vod_index[str(sid)] = {
                    "id": str(sid),
                    "title": title,
                    "lower": _normalize_title(title),
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "thumb": m.get("stream_icon") or m.get("cover") or "",
                    "tmdb": m.get("tmdb") or m.get("tmdb_id"),
                    "ext": m.get("container_extension", "mp4"),
                }

        _write_index("vod", list(vod_index.values()))

        # ------------------ SERIES ------------------
        series_index = {}
        series_cats = xtream_api.categories(xtream_api.SERIES_TYPE) or []

        for cat in series_cats:
            if monitor and monitor.abortRequested():
                giptv.log(
                    "[INDEX_MANAGER] Build aborted during SERIES categories",
                    xbmc.LOGWARNING,
                )
                return False

            if not isinstance(cat, dict):
                continue

            cat_id = cat.get("category_id")
            cat_name = cat.get("category_name", "")
            if not cat_id:
                continue

            shows = xtream_api.streams_by_category(xtream_api.SERIES_TYPE, cat_id) or []

            for s in shows:
                if monitor and monitor.abortRequested():
                    giptv.log(
                        "[INDEX_MANAGER] Build aborted during SERIES streams",
                        xbmc.LOGWARNING,
                    )
                    return False

                if not isinstance(s, dict):
                    continue

                sid = s.get("series_id")
                if not sid:
                    continue

                title = s.get("name") or "Unknown"
                series_index[str(sid)] = {
                    "id": str(sid),
                    "title": title,
                    "lower": _normalize_title(title),
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "thumb": s.get("cover") or "",
                    "tmdb": s.get("tmdb") or s.get("tmdb_id"),
                }

        _write_index("series", list(series_index.values()))

        # ------------------ LIVE ------------------
        live_index = {}
        live_cats = xtream_api.categories(xtream_api.LIVE_TYPE) or []

        for cat in live_cats:
            if monitor and monitor.abortRequested():
                giptv.log(
                    "[INDEX_MANAGER] Build aborted during LIVE categories",
                    xbmc.LOGWARNING,
                )
                return False

            if not isinstance(cat, dict):
                continue

            cat_id = cat.get("category_id")
            cat_name = cat.get("category_name", "")
            if not cat_id:
                continue

            chans = xtream_api.streams_by_category(xtream_api.LIVE_TYPE, cat_id) or []

            for c in chans:
                if monitor and monitor.abortRequested():
                    giptv.log(
                        "[INDEX_MANAGER] Build aborted during LIVE streams",
                        xbmc.LOGWARNING,
                    )
                    return False

                if not isinstance(c, dict):
                    continue

                sid = c.get("stream_id")
                if not sid:
                    continue

                title = (
                    c.get("name") or c.get("stream_display_name") or "Unknown Channel"
                )
                live_index[str(sid)] = {
                    "id": str(sid),
                    "title": title,
                    "lower": _normalize_title(title),
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "thumb": c.get("stream_icon") or c.get("tv_logo") or "",
                    "ext": c.get("container_extension", "ts"),
                }

        _write_index("live", list(live_index.values()))

        finished_at = time.time()

        _write_state(
            {
                "status": "idle",
                "started_at": started_at,
                "finished_at": finished_at,
                "source": source,
            }
        )

        giptv.log(
            f"[INDEX_MANAGER] Index build complete in {finished_at - started_at:.2f}s | source={source}",
            xbmc.LOGINFO,
        )

        if notify:
            giptv.notification(
                ADDON.getAddonInfo("name"),
                "Search index rebuilt",
                icon="INFO",
            )

        return True

    except Exception as exc:
        _write_state(
            {
                "status": "error",
                "started_at": started_at,
                "finished_at": time.time(),
                "source": source,
                "error": str(exc),
            }
        )
        giptv.log(
            f"[INDEX_MANAGER] Build failed: {exc} | source={source}", xbmc.LOGERROR
        )
        return False

    finally:
        if acquired:
            _release_index_lock()

        with _INDEX_LOCK:
            _INDEX_BUILDING = False


# ============================================================
#  AUTO / SAFE ENTRY
# ============================================================


def ensure_index(monitor=None):
    """
    Called by service / navigator.
    Rebuild only if missing, invalid, or stale.
    Skip if already running.
    """
    if build_in_progress():
        giptv.log(
            "[INDEX_MANAGER] ensure_index skipped: build already running", xbmc.LOGINFO
        )
        return False

    if index_exists_and_valid() and index_is_fresh():
        return True

    giptv.log(
        "[INDEX_MANAGER] Index missing, invalid, or stale — rebuilding", xbmc.LOGINFO
    )
    return build_index(
        monitor=monitor, notify=False, source="ensure_index", force=False
    )
