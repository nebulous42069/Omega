# -*- coding: utf-8 -*-
"""
    ReAuthorize - Blank Trakt in every add-on (1.3.6)

    Part of every full wipe (owner.wipe_local): the reset, the leak failsafe's clear of a
    build's sign-ins, and Prepare for Distribution. Until 1.3.6 Trakt was left in the
    add-ons on purpose, on the idea that ending it means revoking the token at Trakt. But
    Prepare for Distribution never revokes (the builder keeps using his Trakt), so a
    "cleaned" build still carried the builder's live Trakt inside The Archives, Umbrella,
    Genocide and the rest, to every box it went on. And after a reset the dead copies left
    behind made the importer report "Trakt - in The Archives" as a sign-in the user had made
    there (found 2026-10-01, a builder's screenshot; confirmed on the bench).

    Where each add-on keeps Trakt comes from import_map, which is generated from the sync
    code's own recorded writes, so this reaches every place sync can put Trakt and stays
    complete as add-ons are added. Settings are blanked; database rows go back to the
    add-on's own default. The Trakt API key ReAuthorize patched into some add-ons' source
    is left in place: it is ReAuthorize's app key, not a sign-in.
"""

import sqlite3

import xbmc
import xbmcaddon
import xbmcvfs

LOG_TAG = '[ReAuthorize Trakt]'
TRAKT_KEYS = ('trakt.token', 'trakt.refresh', 'trakt.expires', 'trakt.username')

# Add-ons that keep the whole Trakt sign-in as one JSON value in a single setting. import_map
# cannot see these (the value is not equal to any one ReAuthorize setting), so they are named.
_JSON_SETTINGS = {
    'plugin.video.themoviedb.helper': ('trakt_token',),
    'script.trakt': ('authorization',),
}

# Settings that only mean "signed in" next to a token and hold no ReAuthorize value, so import_map
# cannot see them either. Mad Titan Sports counts as signed in while trakt.user_id is set (1.4.0).
# Retired add-ons are no longer sent anything, so import_map no longer lists them, but a box can
# still hold what an earlier version sent: Moria (unmaintained, 1.4.0).
_ALSO_BLANK = {
    'plugin.video.umbrella': ('trakt.authed.clientid',),
    'plugin.video.madtitansports': ('trakt.user_id',),
    'plugin.video.moria': ('trakt.user', 'trakt.token', 'trakt.refresh'),
}

# Red Light reads its settings into memory; after a database change it must be told to reload.
_REDLIGHT = 'plugin.video.redlight'
_REDLIGHT_RELOAD = ('RunPlugin(plugin://plugin.video.redlight/?mode=sync_settings'
                    '&silent=true&load_properties=false&force=true)')


def _installed(addon_id):
    return xbmcvfs.exists('special://home/addons/%s/' % addon_id)


def _blank_settings(addon_id, setting_ids):
    changed = 0
    addon = xbmcaddon.Addon(addon_id)
    for setting_id in setting_ids:
        try:
            if addon.getSetting(setting_id):
                addon.setSetting(setting_id, '')
                changed += 1
        except Exception as e:
            xbmc.log('%s could not blank %s in %s: %s' % (LOG_TAG, setting_id, addon_id, e), xbmc.LOGINFO)
    return changed


def _reset_database(addon_id, spec, setting_ids):
    path = xbmcvfs.translatePath('special://profile/addon_data/%s/%s' % (addon_id, spec['file']))
    if not xbmcvfs.exists(path):
        return 0
    changed = 0
    conn = sqlite3.connect(path, timeout=10)
    try:
        columns = [row[1] for row in conn.execute('PRAGMA table_info(settings)')]
        with conn:
            for setting_id in setting_ids:
                if 'setting_default' in columns:
                    cur = conn.execute('UPDATE settings SET setting_value = setting_default '
                                       'WHERE setting_id = ? AND setting_value IS NOT setting_default',
                                       (setting_id,))
                else:
                    cur = conn.execute("UPDATE settings SET setting_value = '' "
                                       "WHERE setting_id = ? AND setting_value IS NOT ''", (setting_id,))
                changed += cur.rowcount
    finally:
        conn.close()
    return changed


_GRATISRED = 'plugin.video.gratisred'


def _gratisred_app_key():
    """
    GratisRed 2.0.4 is given ReAuthorize's Trakt app key in two settings (trakt_sync). Take it out
    again, so GratisRed goes back to its own key, but only when it is ours: a key the user typed
    there is theirs. How many values changed.
    """
    if not _installed(_GRATISRED):
        return 0
    from libs.common import var
    addon = xbmcaddon.Addon(_GRATISRED)
    if addon.getSetting('trakt.client_id') != var.client_am:
        return 0
    addon.setSetting('trakt.client_id', '')
    addon.setSetting('trakt.client_secret', '')
    return 2


def wipe_addons():
    """Blank Trakt in every installed add-on ReAuthorize knows about. Returns how many values changed."""
    from reauthorize.modules import import_map
    changed = 0
    targets = {}
    for addon_id, mapping in getattr(import_map, 'SETTINGS', {}).items():
        targets[addon_id] = {s for s, key in mapping.items() if key in TRAKT_KEYS}
    for addon_id, setting_ids in _JSON_SETTINGS.items():
        targets.setdefault(addon_id, set()).update(setting_ids)
    for addon_id, setting_ids in _ALSO_BLANK.items():
        targets.setdefault(addon_id, set()).update(setting_ids)
    for addon_id, ids in sorted(targets.items()):
        ids = sorted(ids)
        if ids and _installed(addon_id):
            try:
                changed += _blank_settings(addon_id, ids)
            except Exception as e:
                xbmc.log('%s could not clear Trakt in %s: %s' % (LOG_TAG, addon_id, e), xbmc.LOGINFO)
    for addon_id, spec in sorted(getattr(import_map, 'DATABASES', {}).items()):
        ids = sorted(s for s, key in spec.get('keys', {}).items() if key in TRAKT_KEYS)
        if ids and _installed(addon_id):
            try:
                n = _reset_database(addon_id, spec, ids)
                changed += n
                if n and addon_id == _REDLIGHT:
                    xbmc.executebuiltin(_REDLIGHT_RELOAD)
            except Exception as e:
                xbmc.log('%s could not clear Trakt in %s: %s' % (LOG_TAG, addon_id, e), xbmc.LOGINFO)
    try:
        changed += _gratisred_app_key()
    except Exception as e:
        xbmc.log('%s could not take the app key out of GratisRed: %s' % (LOG_TAG, e), xbmc.LOGINFO)
    # The Crew keeps more Trakt state than import_map lists, and copies of all its settings
    # that it can restore a sign-in from (sync/crew_trakt.py, 1.3.8).
    try:
        from reauthorize.modules.sync import crew_trakt
        if crew_trakt.wipe():
            changed += 1
    except Exception as e:
        xbmc.log('%s could not clear The Crew: %s' % (LOG_TAG, e), xbmc.LOGINFO)
    if changed:
        xbmc.log('%s Trakt sign-in removed from add-ons (%d values).' % (LOG_TAG, changed), xbmc.LOGINFO)
    return changed
