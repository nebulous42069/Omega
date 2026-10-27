# -*- coding: utf-8 -*-
"""
    ReAuthorize - TorrentClaw key to the add-ons (1.4.4)

    Cosmos (resources/lib/torrentclaw.py, read on the bench 2026-10-18): the key is the one setting
    'torrentclaw_api_key' (hidden and greyed in its window, written with setSetting all the same).
    Cosmos counts as connected when it is not empty (search_sources, run); its web address is a
    constant in its code, so nothing else is needed. Playback there also needs a debrid account,
    which ReAuthorize already sends.

    push()      : the key into every add-on that does not hold it yet (Sync Add-ons, the automatic send).
    sign_out(k) : blank only where the add-on holds k, ReAuthorize's key; a key typed inside the
                  add-on itself is the user's own business and stays.
    a wipe      : (run_all_syncs with 'torrentclaw' in wipe: reset, foreign sign-ins, Prepare for
                  Distribution) blank everywhere.
"""

import xbmc
import xbmcaddon
import xbmcvfs
from reauthorize.modules import control
from libs.common import var

KEY = 'torrentclaw.api.key'
LOG_TAG = '[ReAuthorize TorrentClaw]'

# (add-on id, its setting, installed folder, its settings file)
ADDONS = (
    ('plugin.video.cosmos', 'torrentclaw_api_key', var.chk_cosmos, var.chkset_cosmos),
)


def _ready(folder, settings_file):
    return xbmcvfs.exists(folder) and xbmcvfs.exists(settings_file)


def _write(addon_id, setting, value):
    addon = xbmcaddon.Addon(addon_id)
    if addon.getSetting(setting) != value:
        addon.setSetting(setting, value)
        return True
    return False


def push():
    """Returns the add-ons written to."""
    key = control.setting(KEY)
    blank = control.wiping()
    if not key and not blank:
        return []
    written = []
    for addon_id, setting, folder, settings_file in ADDONS:
        try:
            if _ready(folder, settings_file) and _write(addon_id, setting, '' if blank else key):
                written.append(addon_id)
        except Exception as e:
            xbmc.log('%s %s: %s' % (LOG_TAG, addon_id, e), xbmc.LOGERROR)
    if written:
        xbmc.log('%s key %s %s' % (LOG_TAG, 'removed from' if blank else 'sent to', ', '.join(written)),
                 xbmc.LOGINFO)
    return written


def sign_out(key):
    """Take ReAuthorize's key (only that one) out of the add-ons."""
    removed = []
    for addon_id, setting, folder, settings_file in ADDONS:
        try:
            if key and _ready(folder, settings_file) and xbmcaddon.Addon(addon_id).getSetting(setting) == key:
                xbmcaddon.Addon(addon_id).setSetting(setting, '')
                removed.append(addon_id)
        except Exception as e:
            xbmc.log('%s %s: %s' % (LOG_TAG, addon_id, e), xbmc.LOGERROR)
    if removed:
        xbmc.log('%s key removed from %s' % (LOG_TAG, ', '.join(removed)), xbmc.LOGINFO)
    return removed
