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
