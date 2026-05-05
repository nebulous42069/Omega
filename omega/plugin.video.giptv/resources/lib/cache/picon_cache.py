# resources/lib/cache/picon_cache.py
import os
import threading
import requests
from resources.utils import giptv
import xbmc
import xbmcvfs
import xbmcaddon
import time
from urllib.parse import urlparse

ADDON = xbmcaddon.Addon()

ADDON_ID = ADDON.getAddonInfo("id")

BASE_PROFILE = xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}")

CACHE_DIR = os.path.join(BASE_PROFILE, "picons")
PLACEHOLDER = os.path.join(
    xbmcvfs.translatePath("special://home"), "media", "DefaultVideo.png"
)
CACHE_EXPIRY_DAYS = 30

# In-memory server speed cache
fast_servers = {}

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


def _sanitize_filename(name):
    if isinstance(name, int):
        name = str(name)
    return "".join(c if c.isalnum() else "_" for c in name)


def _get_local_path(stream_id, category_id, url):
    cat_part = _sanitize_filename(category_id or "")
    filename = f"{_sanitize_filename(stream_id)}_{cat_part}.png"
    return os.path.join(CACHE_DIR, filename)


def _download_async(url, local_path):
    def _worker():
        try:
            giptv.log(f"Downloading picon {url}", xbmc.LOGINFO)
            r = requests.get(url, timeout=10, stream=True)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            giptv.log(f"Saved picon to {local_path}", xbmc.LOGINFO)
        except Exception as e:
            giptv.log(
                f"Exception while downloading picon {url}: {e}",
                xbmc.LOGERROR,
            )

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def get_picon(stream_id, url, category_id=None):
    """
    Return the path to a picon for the given stream_id and category.
    Fast servers return the URL immediately; slow/unreliable servers use a placeholder
    and download the picon in the background.
    """
    if not url:
        return PLACEHOLDER

    local_path = _get_local_path(stream_id, category_id, url)

    # Return cached file if exists
    if os.path.exists(local_path):
        giptv.log(
            f"Returning cached picon {local_path}", xbmc.LOGDEBUG
        )
        return local_path

    host = urlparse(url).netloc
    is_fast = fast_servers.get(host, None)

    # Known fast server → return URL directly
    if is_fast is True:
        return url

    # Unknown or slow server → probe quickly
    if is_fast is None:
        try:
            giptv.log(f"Probing picon server {host}", xbmc.LOGDEBUG)
            r = requests.head(url, timeout=0.5)
            if r.status_code == 200:
                fast_servers[host] = True
                return url
        except Exception as e:
            giptv.log(
                f"Probe failed for {host}: {e}", xbmc.LOGDEBUG
            )
            fast_servers[host] = False

    # Slow server → return placeholder and download async
    _download_async(url, local_path)
    return PLACEHOLDER


def cleanup(expiry_days=CACHE_EXPIRY_DAYS):
    """
    Remove cached picons older than `expiry_days` to avoid stale files.
    """
    now = time.time()
    removed_count = 0
    for fname in os.listdir(CACHE_DIR):
        path = os.path.join(CACHE_DIR, fname)
        if os.path.isfile(path):
            age_days = (now - os.path.getmtime(path)) / 86400
            if age_days > expiry_days:
                try:
                    os.remove(path)
                    removed_count += 1
                    giptv.log(
                        f"Removed old picon {path}", xbmc.LOGINFO
                    )
                except Exception as e:
                    giptv.log(
                        f"Failed to remove picon {path}: {e}",
                        xbmc.LOGERROR,
                    )
    giptv.log(
        f"Cleanup complete, removed {removed_count} files",
        xbmc.LOGINFO,
    )
