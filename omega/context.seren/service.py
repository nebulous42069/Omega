import xbmc
import xbmcaddon

SEREN_ADDON_ID = "plugin.video.seren"

properties = [
    "context.seren.quickResume",
    "context.seren.shuffle",
    "context.seren.playFromRandomPoint",
    "context.seren.rescrape",
    "context.seren.rescrape_ss",
    "context.seren.sourceSelect",
    "context.seren.findSimilar",
    "context.seren.browseShow",
    "context.seren.browseSeason",
]

# properties gated on both this addon's own toggle AND the matching Seren watch-service
# actually being enabled/authorized, keyed by the Seren setting id used to check that
service_aware_properties = {
    "context.seren.traktManager": "trakt.auth",
    "context.seren.mdblistManager": "mdblist.enabled",
}


class PropertiesUpdater(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self._update_window_properties()

    def onSettingsChanged(self):
        self._update_window_properties()

    @staticmethod
    def _is_service_enabled(seren, seren_setting):
        if seren_setting == "trakt.auth":
            return bool(seren.getSetting("trakt.auth")) and seren.getSetting("trakt.enabled") != "false"
        if seren_setting == "mdblist.enabled":
            return seren.getSetting("mdblist.enabled") == "true" and bool(seren.getSetting("mdblist.apikey"))
        return False

    def _update_window_properties(self):
        # a fresh Addon() is constructed on every call rather than cached on self, since a
        # long-lived Addon object can snapshot settings at construction time and never see
        # later changes — this function now runs on a timer, not just on this addon's own
        # onSettingsChanged callback, so a stale cached handle is a real risk here
        addon = xbmcaddon.Addon()
        seren_addon = xbmcaddon.Addon(SEREN_ADDON_ID)

        for prop in properties:
            setting = addon.getSetting(prop)
            if setting == "false":
                xbmc.executebuiltin(f"SetProperty({prop},{setting},home)")
            else:
                xbmc.executebuiltin(f"ClearProperty({prop},home)")
            xbmc.log(f'Context menu item {"disabled" if setting == "false" else "enabled"}: {prop}')

        for prop, seren_setting in service_aware_properties.items():
            manual_setting = addon.getSetting(prop)
            enabled = manual_setting != "false" and self._is_service_enabled(seren_addon, seren_setting)
            if not enabled:
                xbmc.executebuiltin(f"SetProperty({prop},false,home)")
            else:
                xbmc.executebuiltin(f"ClearProperty({prop},home)")
            xbmc.log(f'Context menu item {"disabled" if not enabled else "enabled"}: {prop}')


xbmc.log("context.seren service: starting", xbmc.LOGINFO)

try:
    # start monitoring settings changes events
    properties_monitor = PropertiesUpdater()

    # onSettingsChanged only fires for this addon's own settings, not Seren's — poll
    # every 5s so the service-aware properties pick up Seren-side auth/enable changes
    while not properties_monitor.waitForAbort(5):
        properties_monitor._update_window_properties()
except Exception as e:
    xbmc.log(f"context.seren service: error - {e}", xbmc.LOGERROR)
finally:
    del properties_monitor

xbmc.log("context.seren service: stopped", xbmc.LOGINFO)
