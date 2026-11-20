# -*- coding: utf-8 -*-
"""
    Diggz Account Manager - its own settings, one read or write at a time (1.4.3)

    Every setSetting makes Kodi rewrite the whole settings.xml, and the first read through a new
    handle loads it back. When two threads of the start-up service do that at the same moment,
    one can read the file half-written: Kodi logs 'failed to load addon settings from ...', and a
    handle that loaded nothing cannot save anything (CAddon::SaveSettings). Seen on the first start
    of the Kodi 22 copy (2026-10-13 21:38:36) and again of the Kodi 22 test bench with 1.4.3
    (2026-10-16 03:15:53), where the restore thread (server, vault, owner, device) used its own
    handles while the start-up wrote its status lines through control.accountmgr's lock.

    So every handle on Diggz Account Manager's own settings comes from here, and every get/set on it holds
    one lock for the whole process. Only metadata (getAddonInfo, getLocalizedString) skips it.
    Thread-safe by design: an RLock, so code holding it can call code that takes it again.
"""

import threading

import xbmcaddon

ADDON_ID = 'script.module.authorizediggz'
LOCK = threading.RLock()

# Legacy service flags remain in settings and backups, but credentials alone
# determine their value. Never treat an old disabled flag as a preference.
SERVICE_CREDENTIALS = {
    'torbox': ('torbox.token',),
    'easydebrid': ('easydebrid.token',),
    'offcloud': ('offcloud.token',),
    'easynews': ('easynews.username', 'easynews.password'),
    'filepursuit': ('filepursuit.api.key',),
    'linksnappy': ('linksnappy.username', 'linksnappy.password'),
    'debridlink': ('debridlink.token',),
}
_SERVICE_FLAG_KEYS = {service + '.enabled': credentials for service, credentials in SERVICE_CREDENTIALS.items()}
_SERVICE_KEYS = frozenset(_SERVICE_FLAG_KEYS) | frozenset(k for keys in SERVICE_CREDENTIALS.values() for k in keys)


def reconcile_service_flags(raw_addon, changed_key=None):
    """Repair derived flags on this same Addon handle while LOCK is held."""
    if changed_key is not None and changed_key not in _SERVICE_KEYS:
        return
    for flag, credentials in _SERVICE_FLAG_KEYS.items():
        if changed_key is not None and changed_key != flag and changed_key not in credentials:
            continue
        value = 'true' if all(raw_addon.getSetting(key) for key in credentials) else 'false'
        if raw_addon.getSetting(flag) != value:
            raw_addon.setSetting(flag, value)


def sync_service_flags():
    """Repair pre-upgrade profiles and legacy writers before reading/saving."""
    with LOCK:
        reconcile_service_flags(xbmcaddon.Addon(ADDON_ID))


# Not openSettings: that blocks while the window is open, and every service thread would wait.
_GUARDED = ('getSetting', 'setSetting', 'getSettingBool', 'setSettingBool', 'getSettingInt', 'setSettingInt',
            'getSettingNumber', 'setSettingNumber', 'getSettingString', 'setSettingString')


class _Locked(object):
    """An xbmcaddon.Addon for Diggz Account Manager whose settings calls take turns with every other one."""

    def __init__(self):
        with LOCK:                          # in case Kodi reads the file as the handle is made
            self._addon = xbmcaddon.Addon(ADDON_ID)

    def __getattr__(self, name):
        target = getattr(self._addon, name)
        if name not in _GUARDED:
            return target

        def locked(*args, **kwargs):
            with LOCK:
                result = target(*args, **kwargs)
                if name.startswith('setSetting'):
                    changed_key = args[0] if args else kwargs.get('id')
                    reconcile_service_flags(self._addon, changed_key)
                return result
        return locked


def addon():
    """A fresh handle on Diggz Account Manager's own settings (never keep one: control.py says why)."""
    return _Locked()
