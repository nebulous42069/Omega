import json
import os
import tempfile
import webbrowser
from datetime import datetime, timezone

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcvfs
except ImportError:  # pragma: no cover - used for local development only
    xbmc = None
    xbmcaddon = None
    xbmcgui = None
    xbmcvfs = None


ADDON_ID = "service.kodi.favourites.sync"
LOG_PREFIX = "[Kodi Favourites Sync] "


class StandaloneMonitor:
    def abortRequested(self):
        return False

    def waitForAbort(self, timeout):
        return False


class StandaloneAddon:
    def __init__(self):
        self._settings = {}

    def getAddonInfo(self, key):
        base = os.environ.get("KODI_SYNC_STANDALONE_BASE", tempfile.gettempdir())
        profile = os.path.join(base, "service.kodi.favourites.sync")
        if key == "profile":
            os.makedirs(profile, exist_ok=True)
            return profile
        if key == "path":
            return os.getcwd()
        if key == "name":
            return "Kodi Favourites Sync"
        return ""

    def getSettingString(self, key):
        return self._settings.get(key, os.environ.get("KODI_SYNC_%s" % key.upper(), ""))

    def getSettingBool(self, key):
        raw = self.getSettingString(key)
        return str(raw).lower() in ("1", "true", "yes", "on")

    def getSetting(self, key):
        return self.getSettingString(key)

    def setSetting(self, key, value):
        self._settings[key] = value


def get_addon():
    if xbmcaddon is not None:
        return xbmcaddon.Addon(id=ADDON_ID)
    return StandaloneAddon()


def get_monitor():
    if xbmc is not None:
        return xbmc.Monitor()
    return StandaloneMonitor()


def set_setting_string(addon, key, value):
    if hasattr(addon, "setSettingString"):
        addon.setSettingString(key, "" if value is None else str(value))
        return
    if hasattr(addon, "setSetting"):
        addon.setSetting(key, "" if value is None else str(value))


def open_browser(url):
    if not url:
        return False
    try:
        return bool(webbrowser.open(url))
    except Exception:  # pragma: no cover
        return False


def show_ok_dialog(heading, message):
    if xbmcgui is None:
        print("%s: %s" % (heading, message))
        return
    xbmcgui.Dialog().ok(heading, message)


def show_yesno_dialog(heading, message, yeslabel="Yes", nolabel="No"):
    if xbmcgui is None:
        return False
    return xbmcgui.Dialog().yesno(heading, message, yeslabel=yeslabel, nolabel=nolabel)


def reload_current_profile():
    """Reload Kodi's active profile so Kodi reads newly synced favourites.xml.

    Only call after an explicit user choice. Profile reloads may close Kodi's
    current window or interrupt playback and should never happen in a service
    background sync. JSON-RPC safely quotes profile names.
    """
    if xbmc is None:
        return False
    profile_name = xbmc.getInfoLabel("System.ProfileName")
    if not profile_name:
        raise RuntimeError("Kodi did not report the active profile name")
    request = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "Profiles.LoadProfile",
        "params": {"profile": profile_name, "prompt": True},
    })
    response = json.loads(xbmc.executeJSONRPC(request))
    if "error" in response:
        raise RuntimeError("Kodi profile reload was refused: %s" % response["error"].get("message", "unknown error"))
    return True


def offer_reload_after_sync(addon, result):
    """Offer a user-approved refresh after a foreground download only."""
    if result.get("status") != "ok" or not result.get("changed_local_file") or xbmc is None:
        return False
    count = result.get("count", 0)
    confirmed = show_yesno_dialog(
        "Kodi Favourites Sync",
        "Saved %s synced favourite(s) to Kodi userdata. "
        "Kodi may still show an older in-memory list. "
        "Reload the active Kodi profile now to display them? "
        "This may close open windows or interrupt playback. "
        "Choose No to reload later or restart Kodi instead." % count,
        yeslabel="Reload now", nolabel="Later",
    )
    if not confirmed:
        return False
    try:
        return reload_current_profile()
    except Exception as exc:
        log("Could not reload Kodi profile: %s" % exc, level="warning", addon=addon)
        show_ok_dialog("Kodi Favourites Sync", "Could not reload the Kodi profile. Restart Kodi to display the synced favourites. (%s)" % exc)
        return False


def offer_first_import_restart(addon, result):
    """Offer a normal Kodi exit after the first cloud favourites import.

    Historical function name retained for callers. Kodi must read the updated
    favourites.xml on its next launch, but a forced profile reload is slow and
    RestartApp is not cross-platform. Only the user's explicit confirmation
    requests a normal Quit; never force-kill the Kodi process.

    Return True if the first-import prompt was shown, including when declined.
    """
    if not (
        result.get("status") == "ok"
        and result.get("changed_local_file")
        and result.get("first_cloud_import")
        and result.get("imported_count", 0) > 0
    ) or xbmc is None:
        return False

    count = int(result["imported_count"])
    message = (
        "Favourites backup found! "
        "Downloaded %d favourite(s) from Google Drive and saved them to Kodi. "
        "Close Kodi now and reopen it to load your imported favourites? "
        "Choose Later to close Kodi yourself when convenient." % count
    )
    if show_yesno_dialog("Kodi Favourites Sync", message,
                         yeslabel="Close Kodi", nolabel="Later"):
        try:
            # Kodi's built-in Quit performs a normal cross-platform shutdown.
            # Do not call RestartApp, os.kill, or force-stop on Android.
            xbmc.executebuiltin("Quit")
        except Exception as exc:
            log("Could not close Kodi after first import: %s" % exc,
                level="error", addon=addon)
            show_ok_dialog(
                "Kodi Favourites Sync",
                "Could not close Kodi automatically. Close and reopen Kodi "
                "to display your imported favourites.",
            )
    return True


def offer_manual_sync_close(addon, result):
    """Offer a normal, cross-platform Kodi exit after a manual sync.

    The XML may have been written by *this* sync or a background sync during
    the same Kodi process. A new Kodi launch will read the saved favourites.
    Returns True when the Yes/No dialog was displayed, even if declined.
    """
    if xbmc is None or result.get("status") != "ok":
        return False
    count = int(result.get("count", 0))
    message = (
        "Favourites synchronized. %d favourite(s) saved in Kodi's shared collection. "
        "The updated favourites.xml is already on this device, but Kodi may "
        "still be showing its previously loaded favourites. "
        "Close Kodi now and reopen it to display the latest favourites? "
        "Choose Later to close Kodi yourself when convenient." % count
    )
    if show_yesno_dialog("Kodi Favourites Sync", message,
                         yeslabel="Close Kodi", nolabel="Later"):
        try:
            xbmc.executebuiltin("Quit")
        except Exception as exc:
            log("Could not close Kodi after manual sync: %s" % exc,
                level="error", addon=addon)
            show_ok_dialog("Kodi Favourites Sync",
                           "Could not close Kodi automatically. Close and reopen Kodi "
                           "to display synced favourites.")
    return True


def progress_dialog(heading, line1=""):
    if xbmcgui is None:
        return StandaloneProgressDialog(heading, line1)
    dialog = xbmcgui.DialogProgress()
    dialog.create(heading, line1)
    return dialog


class StandaloneProgressDialog:
    def __init__(self, heading, line1):
        self.heading = heading
        self.line1 = line1
        self._closed = False

    def update(self, percent, line1="", line2="", line3=""):
        if self._closed:
            return
        text = " | ".join(part for part in (line1, line2, line3) if part)
        print("%s [%s%%] %s" % (self.heading, percent, text))

    def iscanceled(self):
        return False

    def close(self):
        self._closed = True


def translate_path(path):
    if xbmcvfs is not None and hasattr(xbmcvfs, "translatePath"):
        return xbmcvfs.translatePath(path)
    if xbmc is not None and hasattr(xbmc, "translatePath"):
        return xbmc.translatePath(path)
    if path == "special://profile/favourites.xml":
        base = os.environ.get("KODI_SYNC_STANDALONE_PROFILE", tempfile.gettempdir())
        return os.path.join(base, "favourites.xml")
    if path.startswith("special://profile/"):
        base = os.environ.get("KODI_SYNC_STANDALONE_PROFILE", tempfile.gettempdir())
        relative = path.replace("special://profile/", "", 1)
        return os.path.join(base, relative)
    return path


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def profile_dir(addon):
    return ensure_dir(translate_path(addon.getAddonInfo("profile")))


def addon_path(addon):
    return translate_path(addon.getAddonInfo("path"))


def log(message, level="info", verbose_only=False, addon=None):
    addon = addon or get_addon()
    if verbose_only and not get_setting_bool(addon, "log_verbose", False):
        return

    text = LOG_PREFIX + message
    if xbmc is None:
        print(text)
        return

    level_map = {
        "debug": xbmc.LOGDEBUG,
        "info": xbmc.LOGINFO,
        "warning": xbmc.LOGWARNING,
        "error": xbmc.LOGERROR,
    }
    xbmc.log(text, level_map.get(level, xbmc.LOGINFO))


def notify(addon, heading, message, icon=""):
    if xbmc is None:
        print("%s: %s" % (heading, message))
        return
    safe_heading = json.dumps(str(heading))
    safe_message = json.dumps(str(message))
    safe_icon = json.dumps(str(icon))
    xbmc.executebuiltin(
        "Notification(%s,%s,5000,%s)" % (safe_heading, safe_message, safe_icon)
    )


def get_setting_string(addon, key, default=""):
    try:
        if hasattr(addon, "getSettingString"):
            value = addon.getSettingString(key)
        else:
            value = addon.getSetting(key)
    except Exception:  # pragma: no cover
        return default
    return value if value != "" else default


def get_enum_index(addon, key, default=0):
    """Read a Kodi enum without triggering an Invalid setting type log error.

    Kodi's getSettingString() is for text values, not integer-backed enums.
    Older settings APIs expose enum indices through getSetting() instead.
    """
    getter = getattr(addon, "getSettingInt", None)
    if callable(getter):
        try:
            return int(getter(key))
        except (TypeError, ValueError, RuntimeError, AttributeError):
            pass
    try:
        raw = addon.getSetting(key)
        if raw is None or raw == "":
            return int(default)
        return int(raw)
    except (TypeError, ValueError, RuntimeError, AttributeError):
        return int(default)


def get_setting_bool(addon, key, default=False):
    try:
        raw = addon.getSetting(key)
    except Exception:  # pragma: no cover
        return default
    if raw == "":
        return default
    return str(raw).lower() in ("1", "true", "yes", "on")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
