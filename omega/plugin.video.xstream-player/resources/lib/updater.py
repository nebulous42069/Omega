# -*- coding: utf-8 -*-
"""Self-update system for XStream Player"""

import json
import os
import re
import sys
import time
import traceback
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from lang import _t

ADDON_ID = "plugin.video.xstream-player"


_LOG_REDACT_PATH_RE = re.compile(
    r"(/(?:live|movie|series)/)([^/?\s]+)(/?)([^/?\s]*)", re.IGNORECASE
)
_LOG_REDACT_QUERY_RE = re.compile(r"(?i)\b(password|pwd|pass)=([^&\s]+)")
_LOG_MAX_LEN = 4000


def _log(msg, level=xbmc.LOGINFO):
    """Unified logging for updater — prefixes all messages consistently."""
    safe_msg = str(msg)
    safe_msg = _LOG_REDACT_PATH_RE.sub(
        lambda m: (
            m.group(1)
            + "***REDACTED***"
            + m.group(3)
            + ("***REDACTED***" if m.group(4) else "")
        ),
        safe_msg,
    )
    safe_msg = _LOG_REDACT_QUERY_RE.sub(r"\1=***REDACTED***", safe_msg)
    if len(safe_msg) > _LOG_MAX_LEN:
        safe_msg = safe_msg[:_LOG_MAX_LEN] + "...[truncated]"
    xbmc.log(f"[XStream Player] {safe_msg}", level)


# Security: HTTPS enforced URLs for update sources
RELEASES_API = (
    "https://api.github.com/repos/Pesicp/XStream-Player-Kodi21/contents/releases"
)
RELEASES_BASE = "https://pesicp.github.io/XStream-Player-Kodi21/releases"


def get_addon():
    """Get addon instance"""
    return xbmcaddon.Addon(id=ADDON_ID)


def get_current_version():
    """Get currently installed version"""
    return get_addon().getAddonInfo("version")


def _version_key(v):
    """Parse a version string into a comparable tuple. Tolerates suffixes like '1.0.6-rc1'."""
    parts = re.findall(r"\d+", v or "")
    return tuple(int(p) for p in parts) if parts else (0,)


def _release_url(filename):
    url = f"{RELEASES_BASE}/{filename}"
    # Security: validate filename to prevent path traversal in URL construction
    import re

    if not re.match(r"^[\w\-.]+$", filename):
        raise ValueError(f"Invalid filename: {filename}")
    return url


import urllib.request
import zipfile
import shutil

# Memoize GitHub API responses (60 req/h unauthenticated limit).
_VERSIONS_CACHE_TTL = 300  # seconds
_versions_cache = {"ts": 0.0, "data": None}


def fetch_all_versions(force=False):
    """Fetch all available versions from GitHub API.
    Returns list of dicts with 'version', 'filename', 'url' (sorted newest first).
    Results are memoised for _VERSIONS_CACHE_TTL seconds. Pass force=True to
    bypass the memo (e.g. for the revert-version UI which the user opens
    explicitly and expects fresh data for).
    """
    now = time.time()
    if (
        not force
        and _versions_cache["data"] is not None
        and (now - _versions_cache["ts"]) < _VERSIONS_CACHE_TTL
    ):
        return _versions_cache["data"]
    try:
        req = urllib.request.Request(
            RELEASES_API, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        versions = []
        for item in data:
            name = item.get("name", "")
            match = re.match(r"plugin\.video\.xstream-player-([\d.]+)\.zip", name)
            if match:
                versions.append(
                    {
                        "version": match.group(1),
                        "filename": name,
                        "url": _release_url(name),
                    }
                )

        versions.sort(key=lambda v: _version_key(v["version"]), reverse=True)
        _versions_cache["ts"] = now
        _versions_cache["data"] = versions
        return versions
    except Exception as e:
        _log(f"Failed to fetch versions: {str(e)}")
        # Don't poison the cache with a failure — keep serving the previous
        # successful result if we have one, otherwise return empty.
        return _versions_cache["data"] or []


def check_for_update():
    """Check if update is available.
    Returns: (update_available, latest_version, download_url)
    """
    versions = fetch_all_versions()
    if not versions:
        return False, None, None

    latest = versions[0]
    if _version_key(latest["version"]) > _version_key(get_current_version()):
        return True, latest["version"], latest["url"]
    return False, latest["version"], None


def _verify_zip(target_path):
    """Verify downloaded file is a valid ZIP and contains expected addon structure."""

    try:
        with zipfile.ZipFile(target_path, "r") as zf:
            # Check for corruption
            bad_file = zf.testzip()
            if bad_file:
                _log(
                    f"ZIP verification failed: {bad_file}",
                    xbmc.LOGERROR,
                )
                return False
            # Security: validate all entries are safe
            for name in zf.namelist():
                # Normalize path separators for cross-platform check
                normalized = name.replace("\\", "/")
                if normalized.startswith("..") or normalized.startswith("/"):
                    _log(
                        f"ZIP contains unsafe path: {name}",
                        xbmc.LOGERROR,
                    )
                    return False
                # Block Windows-absolute paths (e.g., C:/foo, D:/bar)
                if len(normalized) >= 2 and normalized[1] == ":":
                    _log(
                        f"ZIP contains unsafe Windows path: {name}",
                        xbmc.LOGERROR,
                    )
                    return False
                # Must be within expected addon directory
                if not normalized.startswith("plugin.video.xstream-player/"):
                    _log(
                        f"ZIP contains unexpected path: {name}",
                        xbmc.LOGERROR,
                    )
                    return False
            # Must contain addon.xml
            if "plugin.video.xstream-player/addon.xml" not in [
                n.replace("\\", "/") for n in zf.namelist()
            ]:
                _log("ZIP missing addon.xml")
                return False
        return True
    except zipfile.BadZipFile:
        _log("Invalid ZIP file")
        return False
    except Exception as e:
        _log(f"ZIP verification error: {str(e)}")
        return False


def download_update(url, target_path):
    """Download update zip to temp location with HTTPS enforcement and verification."""
    try:
        # Security: enforce HTTPS for downloads
        if not url.startswith("https://"):
            _log(
                f"Update download rejected: non-HTTPS URL",
                xbmc.LOGERROR,
            )
            return False

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            # Limit download size (10MB max for addon)
            max_size = 10 * 1024 * 1024
            data = response.read(max_size + 1)
            if len(data) > max_size:
                _log(
                    "Update download rejected: file too large",
                    xbmc.LOGERROR,
                )
                return False
            with open(target_path, "wb") as f:
                f.write(data)

        # Verify the downloaded ZIP
        if not _verify_zip(target_path):
            os.remove(target_path)
            return False

        return True
    except Exception as e:
        _log(f"Download failed: {str(e)}")
        _log(f"Traceback: {traceback.format_exc()}")
        return False


def _perform_install(new_version, url, dialog, completion_title_id=30811):
    """Download, extract, and prompt-restart for a given version. Returns True on success."""

    progress = xbmcgui.DialogProgress()
    progress.create("XStream Player", _t(30762, new_version))

    # Download to packages/ folder (Kodi standard location)
    packages_dir = xbmcvfs.translatePath("special://home/addons/packages/")
    if not xbmcvfs.exists(packages_dir):
        xbmcvfs.mkdirs(packages_dir)
    zip_path = os.path.join(packages_dir, f"{ADDON_ID}-{new_version}.zip")

    success = download_update(url, zip_path)
    progress.close()

    if not success:
        dialog.notification("XStream Player", _t(30400), xbmcgui.NOTIFICATION_ERROR)
        return False

    progress = xbmcgui.DialogProgress()
    progress.create("XStream Player", _t(30401))

    addon_path = xbmcvfs.translatePath("special://home/addons/")
    try:
        # Security: validate addon_path is within expected location
        expected_base = os.path.normpath(xbmcvfs.translatePath("special://home/"))
        if not os.path.normpath(addon_path).startswith(expected_base):
            raise ValueError("Invalid addon installation path")

        # Security: verify ZIP structure before extraction
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                target = os.path.normpath(os.path.join(addon_path, member))
                if not target.startswith(os.path.normpath(addon_path)):
                    raise ValueError(f"ZIP traversal attempt: {member}")

        # Delete old addon folder first — merged files cause update corruption
        addon_folder = os.path.join(addon_path, ADDON_ID)
        if os.path.exists(addon_folder):
            shutil.rmtree(addon_folder)
            _log(f"Removed old addon folder")

        # Extract fresh (silently)
        _log(f"Extracting to: {addon_path}")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for name in zip_ref.namelist():
                basename = os.path.basename(name)
                target = os.path.normpath(os.path.join(addon_path, name))
                if not target.startswith(os.path.normpath(addon_path)):
                    _log(
                        f"Skipped unsafe update entry: {name}",
                        xbmc.LOGWARNING,
                    )
                    continue
                if basename.startswith(".") or not basename:
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as f:
                    f.write(zip_ref.read(name))

        # Give filesystem time to sync
        xbmc.sleep(1000)

        # Refresh addon database (disable/enable removed - was causing "remove from recents" popup)
        xbmc.executebuiltin("UpdateLocalAddons")
    except Exception as e:
        _log(f"Extract failed: {str(e)}")
        progress.close()
        dialog.notification("XStream Player", _t(30710), xbmcgui.NOTIFICATION_ERROR)
        return False

    progress.close()

    # Update version setting so user sees new version in settings
    get_addon().setSetting("current_version_display", new_version)

    restart = dialog.yesno(
        _t(completion_title_id),
        _t(30402, new_version),
        nolabel=_t(30403),
        yeslabel=_t(30404),
    )

    if restart:
        if xbmc.getCondVisibility("System.Platform.Android"):
            # RestartApp is a no-op on Android. Ask the user to fully close and reopen Kodi.
            xbmcgui.Dialog().ok(
                "XStream Player",
                _t(30763),
            )
        else:
            xbmc.executebuiltin("RestartApp")
    return True


def do_direct_update_install(new_version, url):
    """Direct install without check - used from startup prompt"""
    dialog = xbmcgui.Dialog()
    try:
        _perform_install(new_version, url, dialog)
    except Exception as e:
        _log(f"Direct update ERROR: {str(e)}")
        dialog.ok("XStream Player", _t(30405))


def check_and_install_update():
    """Main entry point: Check for update and prompt user (for Tools menu)"""
    _log("Check update started")
    dialog = xbmcgui.Dialog()

    try:
        progress = xbmcgui.DialogProgress()
        progress.create("XStream Player", _t(30406))

        update_available, new_version, url = check_for_update()
        _log(
            f"Update check: available={update_available}, version={new_version}",
            xbmc.LOGDEBUG,
        )

        progress.close()

        if not update_available:
            if new_version is None:
                dialog.ok("XStream Player", _t(30407))
            else:
                dialog.ok("XStream Player", _t(30408))
            return

        current = get_current_version()
        result = dialog.yesno(_t(30409), _t(30410, current, new_version))
        if not result:
            return

        _perform_install(new_version, url, dialog)

    except Exception as e:
        _log(f"Update ERROR: {str(e)}")

        _log(f"Traceback: {traceback.format_exc()}")
        dialog.ok("XStream Player", _t(30411))


def silent_check_on_startup():
    """Background check on startup (if enabled in settings)"""
    addon = get_addon()
    check_interval = addon.getSetting("update_check_interval")

    # settings.xml stores the raw English value from values="Never|On Startup|Daily|Weekly|Monthly"
    if check_interval == "Never":
        return

    last_check = addon.getSetting("last_update_check")
    today = time.strftime("%Y-%m-%d")

    if check_interval == "Daily":
        if last_check == today:
            return
    elif check_interval == "Weekly":
        if last_check:
            last_time = time.mktime(time.strptime(last_check, "%Y-%m-%d"))
            now_time = time.mktime(time.strptime(today, "%Y-%m-%d"))
            if (now_time - last_time) < (7 * 24 * 60 * 60):
                return
    elif check_interval == "Monthly":
        if last_check:
            last_time = time.mktime(time.strptime(last_check, "%Y-%m-%d"))
            now_time = time.mktime(time.strptime(today, "%Y-%m-%d"))
            if (now_time - last_time) < (30 * 24 * 60 * 60):
                return
    # "On Startup" always proceeds here

    update_available, new_version, url = check_for_update()

    if update_available:
        current = get_current_version()
        result = xbmcgui.Dialog().yesno(
            _t(30706),
            _t(30707, current, new_version),
            nolabel=_t(30708),
            yeslabel=_t(30709),
        )

        if result:
            # Update timestamp before install so failures don't cause immediate recheck
            addon.setSetting("last_update_check", today)
            do_direct_update_install(new_version, url)
            return
        else:
            addon.setSetting("update_available", "true")
            addon.setSetting("update_version", new_version)

    addon.setSetting("last_update_check", today)


def get_available_versions():
    """Get list of all available version strings (newest first), for revert UI."""
    return [v["version"] for v in fetch_all_versions()]


def revert_to_version(version):
    """Revert to a specific older version."""
    filename = f"plugin.video.xstream-player-{version}.zip"
    url = _release_url(filename)

    dialog = xbmcgui.Dialog()
    result = dialog.yesno(
        _t(30764),
        _t(30765, version),
    )
    if not result:
        return False

    return _perform_install(version, url, dialog, completion_title_id=30812)


def revert_version_menu():
    """Show menu to select version to revert to"""
    dialog = xbmcgui.Dialog()

    versions = get_available_versions()
    current = get_current_version()

    if not versions:
        dialog.notification("XStream Player", _t(30766), xbmcgui.NOTIFICATION_ERROR)
        return

    older_versions = [v for v in versions if v != current]

    if not older_versions:
        dialog.ok("XStream Player", _t(30767))
        return

    selected = dialog.select(_t(30768, current), older_versions)
    if selected == -1:
        return

    revert_to_version(older_versions[selected])


# Entry point for RunScript calls
if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "check":
            check_and_install_update()
        elif action == "silent":
            silent_check_on_startup()
