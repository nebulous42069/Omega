# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import threading

from resources.utils import giptv
from resources.utils.config import ensure_api_ready
from resources.lib.manager.index_manager import ensure_index
from resources.lib.manager.epg_manager import get_xmltv_index
from resources.lib.cache.history_cache import shutdown_writer
from resources.lib.manager import index_manager as index
from resources.lib.manager import epg_manager as epg

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")

SETTINGS_CHANGED = False

# ============================================================
#  SMALL HELPERS
# ============================================================


def get_profile_path(subpath=""):
    base = "special://profile/addon_data/{}/".format(ADDON_ID)
    if subpath:
        base = base + subpath.lstrip("/")
    return xbmcvfs.translatePath(base)


def ensure_profile_dir():
    path = get_profile_path()
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path


def get_service_lock_path():
    ensure_profile_dir()
    return get_profile_path(".serviceRan")


def warm_epg():
    giptv.log("Warming EPG", xbmc.LOGINFO)
    index = get_xmltv_index()
    if index:
        giptv.log(f"EPG ready with {len(index)} channels", xbmc.LOGINFO)
    else:
        giptv.log("EPG warm started in background", xbmc.LOGINFO)


def read_service_lock():
    path = get_service_lock_path()

    giptv.log(f"Reading service lock from: {path}", xbmc.LOGINFO)

    if not xbmcvfs.exists(path):
        return ""

    try:
        f = xbmcvfs.File(path, "r")
        try:
            return f.read().strip()
        finally:
            f.close()
    except Exception as e:
        giptv.log(f"Failed to read service lock: {e}", xbmc.LOGWARNING)
        return ""


def write_service_lock(version):
    ensure_profile_dir()
    path = get_service_lock_path()

    try:
        f = xbmcvfs.File(path, "w")
        try:
            f.write(str(version))
        finally:
            f.close()

        giptv.log(f"Wrote service lock '{version}' to: {path}", xbmc.LOGINFO)
    except Exception as e:
        giptv.log(f"Failed to write service lock: {e}", xbmc.LOGERROR)


def show_changelog():
    version = ADDON.getAddonInfo("version")
    message = (
        f"GIPTV updated to v{version}\n\n"
        f"• First Custom Menu\n\n"
        f"• New fixes and Performance improvements\n\n"
        f"Please continue to report any bugs, Kodi may need to be re-opened upon update\n\n\n"
    )
    xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"), message)


def _version_tuple(version):
    try:
        return tuple(int(part) for part in str(version).split("."))
    except Exception:
        return (0, 0, 0)


def run_update_tasks_once():
    current_version = ADDON.getAddonInfo("version")
    last_ran_version = read_service_lock()

    if last_ran_version == current_version:
        giptv.log(
            f"Service update tasks already ran for version {current_version}",
            xbmc.LOGINFO,
        )
        return

    giptv.log(
        f"Running one-time update tasks for version {current_version} "
        f"(previous: {last_ran_version or 'none'})",
        xbmc.LOGINFO,
    )

    # Only old updates up to and including 2.6.1 should wipe/reset
    if _version_tuple(current_version) <= _version_tuple("2.6.1"):
        giptv.log(
            f"Applying cache reset + thumbnail wipe for version {current_version}",
            xbmc.LOGINFO,
        )
        giptv.wipe_all_thumbnails()
        giptv.clear_cache()
    else:
        giptv.log(
            f"Skipping cache reset + thumbnail wipe for version {current_version}",
            xbmc.LOGINFO,
        )

    write_service_lock(current_version)

    verify = read_service_lock()
    giptv.log(f"Service lock verification readback: '{verify}'", xbmc.LOGINFO)

    xbmc.sleep(500)
    show_changelog()


# ============================================================
#  SETTINGS MONITOR
# ============================================================
class SettingsMonitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()

    def onSettingsChanged(self):
        """
        Triggered when addon settings change.
        We:
          - refresh containers
          - request index rebuild
        """
        giptv.log("Settings Changed", xbmc.LOGINFO)

        giptv.container_refresh()


# ============================================================
#  MAIN SERVICE LOOP
# ============================================================
if __name__ == "__main__":
    monitor = SettingsMonitor()

    # Wait a few seconds for Kodi to initialize
    xbmc.sleep(10)

    run_update_tasks_once()

    # Initial setup
    if ensure_api_ready():
        epg._release_epg_lock()
        index._release_index_lock()
        threading.Thread(target=warm_epg, daemon=True).start()
        ensure_index(monitor)

    # Persistent loop to keep monitor active
    giptv.log("Entering main monitor loop", xbmc.LOGINFO)
    try:
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
            # Optional: periodically do maintenance tasks here
    finally:
        shutdown_writer()
        giptv.log("Service shutting down", xbmc.LOGINFO)
