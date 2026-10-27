# -*- coding: utf-8 -*-
"""
    ReAuthorize - its own settings, one read or write at a time (1.4.3)

    Every setSetting makes Kodi rewrite the whole settings.xml, and the first read through a new
    handle loads it back. When two threads of the start-up service do that at the same moment,
    one can read the file half-written: Kodi logs 'failed to load addon settings from ...', and a
    handle that loaded nothing cannot save anything (CAddon::SaveSettings). Seen on the first start
    of the Kodi 22 copy (2026-10-13 21:38:36) and again of the Kodi 22 test bench with 1.4.3
    (2026-10-16 03:15:53), where the restore thread (server, vault, owner, device) used its own
    handles while the start-up wrote its status lines through control.accountmgr's lock.

    So every handle on ReAuthorize's own settings comes from here, and every get/set on it holds
    one lock for the whole process. Only metadata (getAddonInfo, getLocalizedString) skips it.
    Thread-safe by design: an RLock, so code holding it can call code that takes it again.
"""

import threading

import xbmcaddon

ADDON_ID = 'script.module.reauthorize'
LOCK = threading.RLock()

# Not openSettings: that blocks while the window is open, and every service thread would wait.
_GUARDED = ('getSetting', 'setSetting', 'getSettingBool', 'setSettingBool', 'getSettingInt', 'setSettingInt',
            'getSettingNumber', 'setSettingNumber', 'getSettingString', 'setSettingString')


class _Locked(object):
    """An xbmcaddon.Addon for ReAuthorize whose settings calls take turns with every other one."""

    def __init__(self):
        with LOCK:                          # in case Kodi reads the file as the handle is made
            self._addon = xbmcaddon.Addon(ADDON_ID)

    def __getattr__(self, name):
        target = getattr(self._addon, name)
        if name not in _GUARDED:
            return target

        def locked(*args, **kwargs):
            with LOCK:
                return target(*args, **kwargs)
        return locked


def addon():
    """A fresh handle on ReAuthorize's own settings (never keep one: control.py says why)."""
    return _Locked()
