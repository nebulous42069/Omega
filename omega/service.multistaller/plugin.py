import xbmc
import xbmcvfs
import xbmcaddon
import os
import json
import time


class Installer:
    """Install all addon ids listed in resources/addons.json and keep retrying until done."""

    ADDON_ID = 'service.multistaller'
    BOOT_DELAY_MS = 15000
    INSTALL_TIMEOUT = 90
    RETRY_SLEEP = 30
    REPO_REFRESH_INTERVAL = 300

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.monitor = xbmc.Monitor()
        self.addon_data = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.addon_json = os.path.join(addon_path, 'resources', 'addons.json')

    def log(self, message, level=xbmc.LOGINFO):
        xbmc.log('[%s] %s' % (self.ADDON_ID, message), level)

    def get_setting(self, setting_id):
        return self.addon.getSetting(setting_id)

    def set_setting(self, setting_id, value):
        self.addon.setSetting(setting_id, value)

    def create_folder(self, folder_path):
        if not xbmcvfs.exists(folder_path):
            return xbmcvfs.mkdir(folder_path)
        return True

    def load_required_addons(self):
        with open(self.addon_json, 'r', encoding='utf-8', errors='ignore') as f:
            addon_data = json.loads(f.read())

        required = []
        seen = set()
        for item in addon_data.values():
            plugin_id = item.get('plugin_id') if isinstance(item, dict) else None
            if plugin_id and plugin_id not in seen:
                required.append(plugin_id)
                seen.add(plugin_id)
        return required

    def installer(self):
        xbmc.sleep(self.BOOT_DELAY_MS)

        required_addons = self.load_required_addons()
        if not required_addons:
            self.log('No addon ids found in addons.json', xbmc.LOGWARNING)
            self.set_setting('activate_installer', 'false')
            return

        # Keep this on until every required addon is confirmed installed.
        self.set_setting('activate_installer', 'true')

        last_repo_refresh = 0
        while not self.monitor.abortRequested():
            missing = self.get_missing_addons(required_addons)
            if not missing:
                self.log('All required addons are installed. Disabling startup installer.')
                self.set_setting('activate_installer', 'false')
                return

            now = time.time()
            if now - last_repo_refresh >= self.REPO_REFRESH_INTERVAL:
                self.refresh_repositories()
                last_repo_refresh = now

            failed = []
            for plugin_id in missing:
                if self.monitor.abortRequested():
                    break
                if not self.install_addon(plugin_id):
                    failed.append(plugin_id)

            still_missing = self.get_missing_addons(required_addons)
            if not still_missing:
                self.log('All required addons are installed. Disabling startup installer.')
                self.set_setting('activate_installer', 'false')
                return

            self.set_setting('activate_installer', 'true')
            self.log('Still missing addons: %s. Will retry.' % ', '.join(still_missing), xbmc.LOGWARNING)

            if self.monitor.waitForAbort(self.RETRY_SLEEP):
                break

        # Kodi is shutting down/rebooting. Leave the toggle enabled so next boot retries.
        self.set_setting('activate_installer', 'true')

    def refresh_repositories(self):
        self.log('Refreshing local addons and addon repositories before install attempts.')
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.executebuiltin('UpdateAddonRepos')
        # Give Kodi a short window to start processing repo metadata. The retry loop handles the rest.
        self.monitor.waitForAbort(10)

    def get_missing_addons(self, addon_ids):
        return [addon_id for addon_id in addon_ids if not self.isinstalled(addon_id)]

    def install_addon(self, plugin_id):
        if self.isinstalled(plugin_id):
            return True

        self.log('Attempting install: %s' % plugin_id)
        xbmc.executebuiltin('InstallAddon(%s)' % plugin_id)

        clicked = False
        start = time.time()
        while not self.monitor.abortRequested() and time.time() - start < self.INSTALL_TIMEOUT:
            if self.isinstalled(plugin_id):
                self.log('Installed: %s' % plugin_id)
                return True

            if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)') and not clicked:
                xbmc.executebuiltin('SendClick(yesnodialog, 11)')
                clicked = True

            if self.monitor.waitForAbort(0.5):
                break

        installed = self.isinstalled(plugin_id)
        if not installed:
            self.log('Install attempt timed out or failed: %s' % plugin_id, xbmc.LOGWARNING)
        return installed

    def isinstalled(self, addonid):
        if xbmc.getCondVisibility('System.HasAddon(%s)' % addonid):
            return True

        query = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': addonid,
                'properties': ['installed']
            }
        }

        try:
            response = xbmc.executeJSONRPC(json.dumps(query))
            details = json.loads(response)
            return bool(details.get('result', {}).get('addon', {}).get('installed'))
        except Exception as exc:
            self.log('Could not check install status for %s: %s' % (addonid, exc), xbmc.LOGWARNING)
            return False
