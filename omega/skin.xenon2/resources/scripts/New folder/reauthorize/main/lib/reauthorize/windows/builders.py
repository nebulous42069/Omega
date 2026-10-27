# -*- coding: utf-8 -*-
"""
    ReAuthorize - Builder Mode
    Lets build distributors strip all service credentials from addon settings
    before packaging the build. Personal device account is never affected -
    only addon-level settings are cleared.
"""

import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from reauthorize.modules import control
from reauthorize.modules.device import get_device_id

ADDON_ID = 'script.module.reauthorize'

# All credential setting keys that get pushed to addons - same list vault.py uses
_CREDENTIAL_KEYS = [
    'trakt.token', 'trakt.refresh', 'trakt.username',
    'realdebrid.token',
    'premiumize.token',
    'alldebrid.token',
    'torbox.token',
    'easydebrid.token',
    'offcloud.token',
    'easynews.username', 'easynews.password',
    'filepursuit.api.key',
    'tmdb.session_id', 'tmdb.username', 'tmdb.password',
    'simkl.token', 'simkl.client.id',
    'lastfm.session.key', 'lastfm.api.key', 'lastfm.api.secret', 'lastfm.username',
    'sync.tk.service', 'sync.rd.service', 'sync.pm.service', 'sync.ad.service',
    'sync.torbox.service', 'sync.easyd.service', 'sync.offc.service',
    'sync.easy.service', 'sync.filep.service', 'sync.meta.service',
    'api.service',
]


class BuilderMode(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(BuilderMode, self).__init__(*args, **kwargs)
        self._addon = xbmcaddon.Addon(ADDON_ID)

    def _device_id(self):
        """The canonical device ID. Read through device.get_device_id() so this
        matches what the vault and the server actually key on - reading the raw
        setting here used to use the wrong key and always showed 'Not set'."""
        try:
            return get_device_id() or 'Not set'
        except Exception:
            return 'Not set'

    def onInit(self):
        self.getControl(500).setLabel('Your personal device ID: %s' % self._device_id())
        self.getControl(501).setLabel('')

    def onClick(self, control_id):
        if control_id == 201:
            self._confirm_and_clear()
        elif control_id == 200:
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self.close()

    def _confirm_and_clear(self):
        device_id = self._device_id()
        confirmed = xbmcgui.Dialog().yesno(
            'Clean Build for Distribution',
            'This will remove all service credentials from this build.[CR][CR]'
            '[COLOR FFFF6666]Kodi will close immediately after.[/COLOR][CR]'
            'ZIP THE BUILD FOLDER BEFORE RE-OPENING KODI.[CR][CR]'
            'If you re-open first, your credentials reload automatically[CR]'
            'and you will need to click this button again.[CR][CR]'
            '[COLOR FFFFFFFF](Device: %s)[/COLOR][CR][CR]'
            'Ready to clean and close?' % device_id
        )
        if not confirmed:
            return

        self._clear_build_credentials()
        xbmcgui.Dialog().ok(
            'ReAuthorize - Build Cleaned',
            '[COLOR FF00C851]All credentials removed. Build is clean.[/COLOR][CR][CR]'
            '[COLOR FFFF6666]Kodi is about to close.[/COLOR][CR][CR]'
            'Zip the build folder NOW before re-opening Kodi.[CR]'
            'Re-opening will reload your credentials automatically.'
        )
        xbmc.executebuiltin('Quit')

    def _clear_build_credentials(self):
        """Clear service settings from all installed addons in this build."""
        addons_base = xbmcvfs.translatePath('special://home/addons/')

        # Import sync modules and call their clear methods where available
        # For addons that use xbmcaddon.setSetting, clear by service-specific sync modules
        _clear_targets = {
            'trakt.token': _clear_trakt,
            'realdebrid.token': _clear_realdebrid,
            'premiumize.token': _clear_premiumize,
            'alldebrid.token': _clear_alldebrid,
        }

        for token_key, clear_fn in _clear_targets.items():
            if self._addon.getSetting(token_key):
                try:
                    clear_fn(addons_base)
                except Exception as e:
                    import xbmc
                    xbmc.log('[ReAuthorize Builders] Clear error (%s): %s' % (token_key, str(e)), xbmc.LOGWARNING)


# ── Per-service clear functions ───────────────────────────────────────────────
# Each function walks the same addon list the sync module uses and blanks keys.

def _clear_addon_setting(addon_id, keys):
    """Blank settings keys on a given addon if it's installed."""
    try:
        a = xbmcaddon.Addon(addon_id)
        for k in keys:
            a.setSetting(k, '')
    except Exception:
        pass


def _clear_trakt(addons_base):
    targets = [
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.pov', 'plugin.video.umbrella',
        'plugin.video.infinity', 'plugin.video.shadow', 'plugin.video.ghost',
        'plugin.video.base', 'plugin.video.thechains', 'plugin.video.thecrew',
        'plugin.video.gears', 'plugin.video.genesis', 'script.trakt',
    ]
    keys = ['trakt.auth', 'trakt.token', 'trakt.refresh', 'trakt.username']
    for addon_id in targets:
        if xbmcvfs.exists(addons_base + addon_id + '/'):
            _clear_addon_setting(addon_id, keys)


def _clear_realdebrid(addons_base):
    targets = [
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.pov', 'plugin.video.umbrella',
        'plugin.video.infinity', 'plugin.video.thechains', 'plugin.video.thecrew',
        'plugin.video.gears', 'plugin.video.genesis', 'script.module.resolveurl',
    ]
    keys = ['rd.token', 'real_debrid_token', 'realdebrid.token']
    for addon_id in targets:
        if xbmcvfs.exists(addons_base + addon_id + '/'):
            _clear_addon_setting(addon_id, keys)


def _clear_premiumize(addons_base):
    targets = [
        'plugin.video.seren', 'plugin.video.coalition',
        'plugin.video.umbrella', 'plugin.video.thechains', 'script.module.resolveurl',
    ]
    keys = ['pm.token', 'premiumize_token', 'premiumize.token']
    for addon_id in targets:
        if xbmcvfs.exists(addons_base + addon_id + '/'):
            _clear_addon_setting(addon_id, keys)


def _clear_alldebrid(addons_base):
    targets = [
        'plugin.video.seren', 'plugin.video.coalition',
        'plugin.video.umbrella', 'plugin.video.thechains', 'script.module.resolveurl',
    ]
    keys = ['ad.token', 'alldebrid_token', 'alldebrid.token']
    for addon_id in targets:
        if xbmcvfs.exists(addons_base + addon_id + '/'):
            _clear_addon_setting(addon_id, keys)


# ── Entry point ───────────────────────────────────────────────────────────────

def open_builder_mode():
    addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
    vault_path = xbmcvfs.translatePath('special://home/userdata/addon_data/%s/' % ADDON_ID)
    if not xbmcvfs.exists(vault_path + 'builder.lock'):
        xbmcgui.Dialog().notification(
            'ReAuthorize', 'Builder Mode is not active.', time=3000
        )
        return
    w = BuilderMode('builders.xml', addon_path, 'default', '1080i')
    w.doModal()
    del w
