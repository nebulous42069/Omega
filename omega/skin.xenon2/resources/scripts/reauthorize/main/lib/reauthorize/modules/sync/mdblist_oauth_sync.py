# -*- coding: utf-8 -*-
"""
    ReAuthorize - MDBList account sign-in to the add-ons (1.3.7)

    The official MDBList Scrobbler (service.mdblist-scrobbler, by MDBList; read from 1.3.5) keeps
    its sign-in in <its profile>/oauth_tokens.json as {"access_token", "refresh_token",
    "expires_at": <int>} and shows 'Connected' in its setting 'oauth_status'. Its own app id is the
    constant MDBLIST_CLIENT_ID in resources/lib/oauth.py, and it renews itself only in the last
    five minutes before expiry, with that id.

    A token is tied to the app that asked for it, so ReAuthorize's sign-in only renews under
    ReAuthorize's id. The Scrobbler's id is therefore swapped for ReAuthorize's (as Trakt keys are
    swapped in other add-ons) and put back on sign-out or wipe; the original is remembered in the
    hidden setting below. If the swap is impossible (the file moved), the token is still written:
    it works until ReAuthorize renews and re-sends it, which happens long before it runs out.

    1.4.0: the add-ons that take an MDBList ACCOUNT sign-in themselves get it too (ADDONS below; each
    read from the add-on, 2026-10-10). MDBList renews a sign-in only under the app that made it, so
    where an add-on lets a setting choose its app id, that setting gets ReAuthorize's; Umbrella's id is
    a line in its code and is left alone, because it renews only after MDBList refuses its token and
    ReAuthorize renews (and re-sends) at half the 30 days. A sign-out takes ReAuthorize's sign-in only
    out of the add-ons that hold it; a wipe clears them all.
"""

import json
import os
import re
import sqlite3
import time

import xbmc
import xbmcaddon
import xbmcvfs

from reauthorize.modules.control import accountmgr

SCROBBLER = 'service.mdblist-scrobbler'
LOG_TAG = '[ReAuthorize MDBList]'
ORIGINAL_ID_SETTING = 'mdblist.scrobbler.client'
_ID_LINE = re.compile(r'(MDBLIST_CLIENT_ID\s*=\s*["\'])([^"\']*)(["\'])')


def _log(message):
    xbmc.log('%s %s' % (LOG_TAG, message), xbmc.LOGINFO)


def installed():
    return xbmcvfs.exists('special://home/addons/%s/' % SCROBBLER)


def _oauth_py():
    return xbmcvfs.translatePath('special://home/addons/%s/resources/lib/oauth.py' % SCROBBLER)


def _token_file():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/oauth_tokens.json' % SCROBBLER)


def _our_id():
    from reauthorize.modules.auth.mdblist_oauth import CLIENT_ID
    return CLIENT_ID


def _swap_id(to_ours):
    """Put ReAuthorize's app id into the Scrobbler (or its own back). True if the file is as wanted."""
    path = _oauth_py()
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return False
    found = _ID_LINE.search(text)
    if not found:
        _log('the Scrobbler\'s app id was not found in oauth.py - left as it is')
        return False
    current, ours = found.group(2), _our_id()
    if to_ours:
        if current == ours:
            return True
        accountmgr.setSetting(ORIGINAL_ID_SETTING, current)
        wanted = ours
    else:
        original = accountmgr.getSetting(ORIGINAL_ID_SETTING)
        if current != ours or not original:
            return True
        wanted = original
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(_ID_LINE.sub(lambda m: m.group(1) + wanted + m.group(3), text, count=1))
        return True
    except Exception as e:
        _log('could not update the Scrobbler\'s app id: %s' % e)
        return False


def _read_tokens():
    try:
        with open(_token_file(), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def scrobbler_refresh_token():
    """The refresh token the Scrobbler holds now (it may have renewed on its own), or ''."""
    return str(_read_tokens().get('refresh_token') or '')


POV, UMBRELLA, REDLIGHT, COSMOS, TMDBMOVIES = ('plugin.video.pov', 'plugin.video.umbrella', 'plugin.video.redlight',
                                              'plugin.video.cosmos', 'plugin.video.tmdbmovies')
ADDONS = (POV, UMBRELLA, REDLIGHT, COSMOS, TMDBMOVIES)
# POV 6.09: signed in = mdblist_user (+ mdblist.token); renews with its mdblist.client_id setting when
#   mdblist.expires (whole seconds) is near; mdbl_indicators_active only shows its watched-provider choice.
# Umbrella 6.7.90: signed in = mdblist.token; mdblist.refresh.token; app id is a constant in its code.
# Red Light 2.8: settings.db; signed in = mdblist.user + mdblist.token + mdblist.refresh; mdblist.client
#   overrides its shipped app id (as simkl.client does).
# Cosmos 4.3.53: <profile>/mdblist_token.json {access_token, refresh_token, expires_in, stored_at,
#   client_id}; signed in = that file (or its API key) unless mdblist_disconnected; its own sign-in
#   button needs mdblist_client_id, which is filled only when empty.
# TMDb Movies 1.1.3: mdblist_access_token / mdblist_refresh_token / mdblist_token_created /
#   mdblist_token_expires (seconds of lifetime), mdblist_username, mdblist_status 'Connected: <user>';
#   mdblist_client_id overrides the id in its code.


def _settings_ready(addon_id):
    return (xbmcvfs.exists('special://home/addons/%s/' % addon_id) and
            xbmcvfs.exists('special://profile/addon_data/%s/settings.xml' % addon_id))


def _ready(addon_id):
    if addon_id == REDLIGHT:
        from reauthorize.modules.db import redlight_db
        return redlight_db.available()
    return _settings_ready(addon_id)


def _cosmos_file():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/mdblist_token.json' % COSMOS)


def _read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _redlight_rows(*ids):
    from libs.common import var
    rows = {}
    try:
        conn = sqlite3.connect(var.redlight_settings_db, timeout=10)
        try:
            for sid in ids:
                row = conn.execute('SELECT setting_value FROM settings WHERE setting_id = ?', (sid,)).fetchone()
                value = row[0] if row else ''
                rows[sid] = '' if value in (None, '0', 'empty_setting') else str(value)
        finally:
            conn.close()
    except Exception:
        pass
    return rows


def _held(addon_id):
    """(access token, refresh token) an add-on holds now; '' for none."""
    if addon_id == COSMOS:
        data = _read_json(_cosmos_file())
        return str(data.get('access_token') or ''), str(data.get('refresh_token') or '')
    if addon_id == REDLIGHT:
        rows = _redlight_rows('mdblist.token', 'mdblist.refresh')
        return rows.get('mdblist.token', ''), rows.get('mdblist.refresh', '')
    ids = {POV: ('mdblist.token', 'mdblist.refresh'), UMBRELLA: ('mdblist.token', 'mdblist.refresh.token'),
           TMDBMOVIES: ('mdblist_access_token', 'mdblist_refresh_token')}[addon_id]
    addon = xbmcaddon.Addon(addon_id)
    return addon.getSetting(ids[0]), addon.getSetting(ids[1])


def _account():
    try:
        expires = int(float(accountmgr.getSetting('mdblist.oauth.expires') or 0))
    except (TypeError, ValueError):
        expires = 0
    return {'token': accountmgr.getSetting('mdblist.oauth.token'),
            'refresh': accountmgr.getSetting('mdblist.oauth.refresh'),
            'expires': expires,
            'user': accountmgr.getSetting('mdblist.oauth.username') or 'MDBList User'}


def _set(addon_id, pairs):
    addon = xbmcaddon.Addon(addon_id)
    for sid, value in pairs:
        if addon.getSetting(sid) != value:
            addon.setSetting(sid, value)


LIFETIME = 2592000          # MDBList sign-ins last 30 days


def _write(addon_id, a):
    # When the sign-in was made, worked out from its expiry (not the clock), so the same sign-in is
    # always written the same way and an add-on is not rewritten at every check.
    made = a['expires'] - LIFETIME if a['expires'] else int(time.time())
    lifetime = str(LIFETIME)
    if addon_id == POV:
        _set(POV, [('mdblist.token', a['token']), ('mdblist.refresh', a['refresh']),
                   ('mdblist.expires', str(a['expires'] or made + LIFETIME)), ('mdblist.client_id', _our_id()),
                   ('mdblist_user', a['user']), ('mdbl_indicators_active', 'true')])
    elif addon_id == UMBRELLA:
        _set(UMBRELLA, [('mdblist.token', a['token']), ('mdblist.refresh.token', a['refresh'])])
    elif addon_id == REDLIGHT:
        from reauthorize.modules.db import redlight_db
        redlight_db.push([('mdblist.token', a['token']), ('mdblist.refresh', a['refresh']),
                          ('mdblist.user', a['user']), ('mdblist.client', _our_id())])
    elif addon_id == COSMOS:
        path = _cosmos_file()
        text = json.dumps({'access_token': a['token'], 'refresh_token': a['refresh'], 'token_type': 'Bearer',
                           'expires_in': int(lifetime), 'stored_at': made, 'client_id': _our_id()})
        xbmcvfs.mkdirs(os.path.dirname(path))
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(path + '.tmp', path)
        addon = xbmcaddon.Addon(COSMOS)
        _set(COSMOS, [('mdblist_auth_done', 'true'), ('mdblist_disconnected', 'false'), ('mdblist_username', a['user'])])
        if not addon.getSetting('mdblist_client_id').strip():
            addon.setSetting('mdblist_client_id', _our_id())
    elif addon_id == TMDBMOVIES:
        _set(TMDBMOVIES, [('mdblist_access_token', a['token']), ('mdblist_refresh_token', a['refresh']),
                          ('mdblist_token_created', str(made)), ('mdblist_token_expires', lifetime),
                          ('mdblist_username', a['user']), ('mdblist_status', 'Connected: %s' % a['user']),
                          ('mdblist_client_id', _our_id())])


def _shipped_default(addon_id, setting_id):
    """The add-on's own default for a setting, from its resources/settings.xml ('' if none)."""
    try:
        path = xbmcvfs.translatePath('special://home/addons/%s/resources/settings.xml' % addon_id)
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
        m = re.search(r'<setting id="%s"[^>]*?default="([^"]*)"' % re.escape(setting_id), text)
        return m.group(1) if m else ''
    except Exception:
        return ''


def _clear(addon_id):
    if addon_id == POV:
        _set(POV, [('mdblist.token', ''), ('mdblist.refresh', ''), ('mdblist.expires', ''), ('mdblist_user', ''),
                   ('mdbl_indicators_active', 'false'),
                   ('mdblist.client_id', _shipped_default(POV, 'mdblist.client_id'))])
    elif addon_id == UMBRELLA:
        _set(UMBRELLA, [('mdblist.token', ''), ('mdblist.refresh.token', '')])
    elif addon_id == REDLIGHT:
        from reauthorize.modules import control
        from reauthorize.modules.db import redlight_db
        before = control.wiping()
        control.set_wiping(True)                  # redlight_db puts rows back to Red Light's defaults
        try:
            redlight_db.push([('mdblist.token', ''), ('mdblist.refresh', ''), ('mdblist.user', ''),
                              ('mdblist.client', '')])
        finally:
            control.set_wiping(before)
    elif addon_id == COSMOS:
        path = _cosmos_file()
        if os.path.isfile(path):
            os.remove(path)
        _set(COSMOS, [('mdblist_auth_done', 'false'), ('mdblist_username', '')])
    elif addon_id == TMDBMOVIES:
        _set(TMDBMOVIES, [('mdblist_access_token', ''), ('mdblist_refresh_token', ''), ('mdblist_token_created', ''),
                          ('mdblist_token_expires', ''), ('mdblist_username', ''), ('mdblist_status', 'Disconnected'),
                          ('mdblist_client_id', '')])


def push_addons(only_missing=False):
    """Send the account sign-in to every ready add-on in ADDONS that does not hold it. How many got it."""
    a = _account()
    if not a['token']:
        return 0
    sent = 0
    for addon_id in ADDONS:
        try:
            if not _ready(addon_id):
                continue
            held = _held(addon_id)[0]
            if held == a['token'] or (only_missing and held):
                continue
            _write(addon_id, a)
            sent += 1
            _log('sign-in sent to %s' % addon_id)
        except Exception as e:
            _log('could not send the sign-in to %s: %s' % (addon_id, e))
    return sent


def wipe_addons(token=None):
    """No token (a wipe): clear every add-on's MDBList sign-in. A token (a sign-out): only where it is held."""
    cleared = 0
    for addon_id in ADDONS:
        try:
            if not _ready(addon_id):
                continue
            held = _held(addon_id)[0]
            if not held or (token and held != token):
                continue
            _clear(addon_id)
            cleared += 1
            _log('sign-in removed from %s' % addon_id)
        except Exception as e:
            _log('could not clear %s: %s' % (addon_id, e))
    return cleared


def remove_api_key(old_key):
    """
    Revoke (1.4.0, the user: MDBList is one sign-in, so Revoke takes the key out too): blank the
    MDBList API key in every add-on that holds THIS key - the places come from import_map, so a new
    add-on is covered once its sync block is recorded - and in the Fentastic/Nimbus skin string. A
    different key typed into an add-on by hand is left alone. How many values were cleared.
    """
    if not old_key:
        return 0
    from reauthorize.modules import import_map
    cleared = 0
    for addon_id, mapping in sorted(getattr(import_map, 'SETTINGS', {}).items()):
        ids = [sid for sid, key in mapping.items() if key == 'mdb.api.key']
        if not ids or not _settings_ready(addon_id):
            continue
        try:
            addon = xbmcaddon.Addon(addon_id)
            mine = [sid for sid in ids if addon.getSetting(sid) == old_key]
            for sid in mine:
                addon.setSetting(sid, '')
            if mine and addon_id == 'plugin.video.thearchives':
                addon.setSetting('mdblist.username', '')      # shown beside the key
            if mine:
                cleared += len(mine)
                _log('API key removed from %s' % addon_id)
        except Exception as e:
            _log('could not remove the API key from %s: %s' % (addon_id, e))
    try:
        if xbmc.getInfoLabel('Skin.String(mdblist_api_key)') == old_key:
            xbmc.executebuiltin('Skin.Reset(mdblist_api_key)')
            cleared += 1
    except Exception:
        pass
    return cleared


def addon_refresh_tokens():
    """Refresh tokens the add-ons hold, for a refused renewal (one of them may have renewed first)."""
    found = []
    for addon_id in ADDONS:
        try:
            if _ready(addon_id):
                refresh = _held(addon_id)[1]
                if refresh and refresh not in found:
                    found.append(refresh)
        except Exception:
            pass
    return found


def push():
    """Give the Scrobbler and the add-ons ReAuthorize's MDBList sign-in. True if anything was written."""
    token = accountmgr.getSetting('mdblist.oauth.token')
    if not token:
        return False
    sent = push_addons() > 0
    if not installed():
        return sent
    _swap_id(True)
    try:
        expires_at = int(float(accountmgr.getSetting('mdblist.oauth.expires') or 0))
    except (TypeError, ValueError):
        expires_at = 0
    path = _token_file()
    try:
        xbmcvfs.mkdirs(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'access_token': token,
                       'refresh_token': accountmgr.getSetting('mdblist.oauth.refresh'),
                       'expires_at': expires_at}, f)
    except Exception as e:
        _log('could not write the Scrobbler\'s sign-in: %s' % e)
        return False
    try:
        xbmcaddon.Addon(SCROBBLER).setSetting('oauth_status', 'Connected')
    except Exception:
        pass
    _log('sign-in sent to the MDBList Scrobbler')
    return True


def ensure():
    """At start: put the sign-in back where an update or a build removed it (the Scrobbler, the add-ons)."""
    if not accountmgr.getSetting('mdblist.oauth.token'):
        return False
    added = push_addons(only_missing=True) > 0
    if not installed():
        return added
    if _read_tokens().get('access_token') == accountmgr.getSetting('mdblist.oauth.token'):
        _swap_id(True)          # an update of the Scrobbler restores its own id
        return added
    return push()


def wipe(token=None):
    """
    Take the sign-in out of the Scrobbler (giving it back its own app id) and out of the add-ons.
    token: a sign-out of that sign-in, so add-ons holding a different one are left alone.
    True if anything changed.
    """
    changed = wipe_addons(token) > 0
    if not installed():
        return changed
    path = _token_file()
    if os.path.isfile(path):
        try:
            os.remove(path)
            changed = True
        except Exception as e:
            _log('could not remove the Scrobbler\'s sign-in: %s' % e)
    try:
        addon = xbmcaddon.Addon(SCROBBLER)
        if addon.getSetting('oauth_status') != 'Not connected':
            addon.setSetting('oauth_status', 'Not connected')
    except Exception:
        pass
    _swap_id(False)
    if changed:
        _log('sign-in removed from the MDBList Scrobbler')
    return changed
