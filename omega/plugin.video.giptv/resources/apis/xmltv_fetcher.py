import io
import gzip
import json
import urllib.request
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

from resources.utils import giptv, settings
from resources.utils.xtream import STATE

ADDON_ID = "plugin.video.giptv"
ADDON = xbmcaddon.Addon()


# ============================================================
# PATH HELPERS
# ============================================================


def profile_path(sub=""):
    base = f"special://profile/addon_data/{ADDON_ID}/"
    return xbmcvfs.translatePath(base + sub)


def ensure_cache_dir():
    path = profile_path("cache")
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path


def get_current_epg_source():
    custom_epg = get_custom_epg_url().strip()
    if custom_epg:
        return f"custom:{custom_epg}"
    return "provider:default"


# ============================================================
# HTTP FETCH (gzip + UA fallback)
# ============================================================

KODI_UA = "Kodi-GIPTV/1.0"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/44.0.2403.89 Safari/537.36"
)


def fetch_url(url, timeout=30, use_browser_ua=False):
    headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": BROWSER_UA if use_browser_ua else KODI_UA,
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()

        if r.headers.get("Content-Encoding") == "gzip" or url.endswith(".gz"):
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()

        return raw.decode("utf-8", errors="ignore")


# ============================================================
# LOCAL FILE HELPERS
# ============================================================


def is_remote_url(value):
    value = (value or "").strip().lower()
    return value.startswith("http://") or value.startswith("https://")


def normalize_local_path(path):
    """
    Supports:
    - special:// paths
    - plain local absolute paths
    - file:// paths
    """
    path = (path or "").strip()
    if not path:
        return ""

    if path.startswith("file://"):
        path = path[7:]

    if path.startswith("special://"):
        return xbmcvfs.translatePath(path)

    return path


def read_local_file(path):
    """
    Reads local XML or GZ-compressed XML and returns decoded text.
    """
    resolved = normalize_local_path(path)

    if not resolved or not xbmcvfs.exists(resolved):
        raise IOError(f"Local EPG file not found: {resolved}")

    f = xbmcvfs.File(resolved, "rb")
    try:
        raw = f.read()
    finally:
        f.close()

    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="ignore")

    if resolved.lower().endswith(".gz"):
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()

    return raw.decode("utf-8", errors="ignore")


def _safe_name(value):
    value = (value or "").strip().lower()
    return (
        value.replace("http://", "")
        .replace("https://", "")
        .replace("/", "_")
        .replace(":", "_")
    )


def get_epg_source_lock_path():
    cache_dir = ensure_cache_dir()
    user = _safe_name(STATE.username or "default")
    server = _safe_name(STATE.server or "server")
    return f"{cache_dir}/.last_epg_source_{user}_{server}"


def read_last_epg_source():
    path = get_epg_source_lock_path()
    if not xbmcvfs.exists(path):
        return ""

    f = xbmcvfs.File(path, "r")
    try:
        return f.read().strip()
    finally:
        f.close()


def write_last_epg_source(value):
    path = get_epg_source_lock_path()
    f = xbmcvfs.File(path, "w")
    try:
        f.write(value or "")
    finally:
        f.close()


def ensure_epg_source_is_current():
    current_source = get_current_epg_source()
    last_source = read_last_epg_source()

    if current_source != last_source:
        giptv.log(
            f"EPG source changed for current account "
            f"(old='{last_source}' new='{current_source}')",
            xbmc.LOGINFO,
        )

        try:
            from resources.lib.manager import epg_manager as epg

            epg.clear_epg_cache()
            giptv.log("Old EPG source cache cleared")
            giptv.container_refresh()
        except Exception as e:
            giptv.log(
                f"Failed to clear EPG cache on source change: {e}", xbmc.LOGWARNING
            )

        write_last_epg_source(current_source)

    return current_source


# ============================================================
# XTREAM URL BUILDERS
# ============================================================


def get_custom_epg_url():
    """
    Returns only the saved custom EPG value from settings.
    This may be:
    - http(s) URL
    - local file path
    - special:// path
    """
    return settings.get_epg_url(ADDON).strip()


def candidate_xmltv_urls():
    base = STATE.server.rstrip("/")
    u = STATE.username
    p = STATE.password

    return [
        f"{base}/xmltv.php?username={u}&password={p}",
        f"{base}/xmltv.php?u={u}&p={p}",
        f"{base}/epg.xml",
        f"{base}/epg.xml.gz",
        f"{base}/xmltv.xml",
        f"{base}/xmltv.xml.gz",
    ]


def build_player_api_epg_url():
    base = STATE.server.rstrip("/")
    u = STATE.username
    p = STATE.password

    return f"{base}/player_api.php?username={u}&password={p}&action=get_epg"


# ============================================================
# VALIDATION
# ============================================================


def is_html_block(data):
    snippet = data[:500].lower()
    return "<html" in snippet or "<!doctype html" in snippet


def validate_xmltv(data):
    if "<tv" not in data[:1000].lower():
        return False, 0

    try:
        root = ET.fromstring(data)
        programmes = root.findall("programme")
        return True, len(programmes)
    except Exception:
        return False, 0


# ============================================================
# STORE HELPERS
# ============================================================


def store_xmltv_data(data, xmltv_path, source_label="XMLTV"):
    if is_html_block(data):
        giptv.log(f"{source_label}: HTML response detected (blocked)", xbmc.LOGWARNING)
        return None

    valid, count = validate_xmltv(data)
    if not valid:
        giptv.log(f"{source_label}: Invalid XMLTV structure", xbmc.LOGWARNING)
        return None

    with xbmcvfs.File(xmltv_path, "w") as f:
        f.write(data)

    giptv.log(f"{source_label}: stored successfully ({count} programmes)", xbmc.LOGINFO)
    return xmltv_path


def try_store_xmltv_from_url(url, xmltv_path):
    for ua_mode in (False, True):
        try:
            giptv.log(
                f"Trying XMLTV URL: {url} | UA={'browser' if ua_mode else 'kodi'}",
                xbmc.LOGINFO,
            )
            data = fetch_url(url, use_browser_ua=ua_mode)
            result = store_xmltv_data(data, xmltv_path, "Remote XMLTV")
            if result:
                return result
        except Exception as e:
            giptv.log(f"XMLTV URL error from {url}: {e}", xbmc.LOGWARNING)

    return None


def try_store_xmltv_from_local(path, xmltv_path):
    try:
        resolved = normalize_local_path(path)
        giptv.log(f"Trying local XMLTV: {resolved}", xbmc.LOGINFO)
        data = read_local_file(path)
        return store_xmltv_data(data, xmltv_path, "Local XMLTV")
    except Exception as e:
        giptv.log(f"Local XMLTV error from {path}: {e}", xbmc.LOGWARNING)
        return None


# ============================================================
# PROVIDER FETCHERS
# ============================================================


def fetch_xmltv():
    cache_dir = ensure_cache_dir()
    xmltv_path = f"{cache_dir}/{STATE.username}_xmltv.xml"

    custom_epg = get_custom_epg_url()

    # --- FIRST: CUSTOM EPG (REMOTE OR LOCAL) ---
    if custom_epg:
        giptv.log(f"Custom EPG configured: {custom_epg}", xbmc.LOGINFO)

        if is_remote_url(custom_epg):
            result = try_store_xmltv_from_url(custom_epg, xmltv_path)
        else:
            result = try_store_xmltv_from_local(custom_epg, xmltv_path)

        if result:
            return result

        giptv.log(
            "Custom EPG failed, falling back to provider XMLTV",
            xbmc.LOGWARNING,
        )

    # --- SECOND: PROVIDER XMLTV ENDPOINTS ---
    for url in candidate_xmltv_urls():
        result = try_store_xmltv_from_url(url, xmltv_path)
        if result:
            return result

    # --- THIRD: PLAYER_API JSON EPG ---
    try:
        url = build_player_api_epg_url()
        giptv.log("Falling back to Xtream player_api EPG", xbmc.LOGINFO)
        data = fetch_url(url, use_browser_ua=True)
        epg_json = json.loads(data)

        giptv.log(f"player_api EPG fetched ({len(epg_json)} entries)", xbmc.LOGINFO)
        # NOTE: Conversion to XMLTV would go here

    except Exception as e:
        giptv.log(f"player_api fallback failed: {e}", xbmc.LOGERROR)

    giptv.log("XMLTV unavailable from provider", xbmc.LOGERROR)
    return None


def fetch_provider_data():
    return fetch_xmltv()
