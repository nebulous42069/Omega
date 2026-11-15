"""Credential storage used by SALTS 2.9.74."""
import json
import os

import xbmc
import xbmcaddon
import xbmcvfs

from reauthorize.modules import control, sync_support

ADDON_ID = 'plugin.video.salts'
DEBRID = {
    'rd': ('realdebrid', {
        'realdebrid_client_id': 'realdebrid.client_id',
        'realdebrid_client_secret': 'realdebrid.secret',
        'realdebrid_refresh': 'realdebrid.refresh',
        'realdebrid_token': 'realdebrid.token',
    }),
    'ad': ('alldebrid', {'alldebrid_token': 'alldebrid.token'}),
    'torbox': ('torbox', {'torbox_token': 'torbox.token'}),
    'easyd': ('easydebrid', {'easydebrid_token': 'easydebrid.token'}),
    'offc': ('offcloud', {'offcloud_token': 'offcloud.token'}),
    'debridlink': ('debridlink', {'debridlink_token': 'debridlink.token'}),
    'easy': ('easynews', {
        'easynews_username': 'easynews.username',
        'easynews_password': 'easynews.password',
    }),
}


def send(tag):
    if tag not in DEBRID or not sync_support.installed(ADDON_ID):
        return False
    service, fields = DEBRID[tag]
    wipe = control.wiping()
    pairs = [(field, '' if wipe else control.setting(source)) for field, source in fields.items()]
    if not wipe and not all(value for _, value in pairs):
        return False
    if tag == 'rd':
        addon = xbmcaddon.Addon(ADDON_ID)
        if wipe or any(addon.getSetting(field) != value for field, value in pairs):
            expiry = '' if wipe else control.setting('realdebrid.expires')
            pairs.insert(0, ('realdebrid_expires', expiry or '0'))
    pairs.append((service + '_enabled', 'false' if wipe else 'true'))
    return sync_support.put(ADDON_ID, pairs, wipe)


def _token_file():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/trakt_auth.json' % ADDON_ID)


def trakt_file_has_token():
    try:
        with open(_token_file(), encoding='utf-8') as stream:
            data = json.load(stream)
        float(data.get('expires', 0))
        return bool(data.get('access_token'))
    except (OSError, ValueError, TypeError, AttributeError):
        return None  # SALTS falls back to settings when the file cannot be read.


def _remove_trakt_file():
    try:
        os.remove(_token_file())
    except FileNotFoundError:
        pass


def clear_trakt():
    if not sync_support.installed(ADDON_ID):
        return True
    file_cleared = True
    try:
        _remove_trakt_file()
    except OSError:
        file_cleared = False
        xbmc.log('[Diggz Account Manager] Could not clear the SALTS Trakt token file.', xbmc.LOGWARNING)
    settings_cleared = sync_support.put(ADDON_ID, [
        ('trakt_access_token', ''), ('trakt_refresh_token', ''),
        ('trakt_expires', '0'), ('trakt_enabled', 'false'),
    ], wipe=True)
    return file_cleared and settings_cleared


def send_trakt(token, refresh, expiry):
    if not (token and refresh and expiry and sync_support.installed(ADDON_ID)):
        return
    from libs.common import var
    try:
        sync_support.patch_constants(var.path_salts, {
            'CLIENT_ID': var.client_am, 'CLIENT_SECRET': var.secret_am,
        })
        if sync_support.put(ADDON_ID, [
            ('trakt_refresh_token', refresh), ('trakt_expires', expiry),
            ('trakt_access_token', token), ('trakt_enabled', 'true'),
        ]):
            # SALTS prefers this file over settings. Remove stale tokens only
            # once the replacement credentials have been verified.
            _remove_trakt_file()
    except Exception as exc:
        sync_support.failed(ADDON_ID)
        xbmc.log('[Diggz Account Manager] SALTS Trakt sync failed (%s).' % type(exc).__name__, xbmc.LOGWARNING)
