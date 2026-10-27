# -*- coding: utf-8 -*-
"""
    ReAuthorize - PunchPlay sign-in to the add-ons (1.4.1)

    ReAuthorize is the only one that renews a PunchPlay sign-in (auth/punchplay.py says why), so
    an add-on gets the ACCESS token only, never the refresh token, and its own expiry is written
    so that it does not try to renew. Each add-on was read on the bench (2026-10-13); all of them
    send 'Authorization: Bearer' and nothing else on API calls, and none signs itself out over a
    token it cannot renew:

    Cosmos 4.3.65      <profile>/punchplay_token.json {access_token, refresh_token, expires_in,
                       stored_at, username, ...}; signed in = the file has an access_token; the
                       settings punchplay_auth_done / punchplay_username only mirror it. With no
                       refresh_token it keeps using the stored token.
    Red Light 2.8.3    settings.db: punchplay.token (signed in = token), punchplay.refresh,
                       punchplay.expires ('0' = keep until PunchPlay refuses it), punchplay.user.
    TMDb Movies        punchplay_access_token (signed in = token), punchplay_refresh_token,
                       punchplay_token_expiry (blank = never tries to renew), punchplay_username,
                       punchplay_status 'Connected: <user>'.
    The Archives       punchplay.access_token (signed in = token), punchplay.refresh_token,
                       punchplay.expires, punchplay.refresh_expires, punchplay.username,
                       punchplay.user_id; renews only after a refusal AND with a refresh token.
    Umbrella           its database punchplaySync.db, table punchplay_state, key 'tokens': JSON with
                       access_token, refresh_token, expires_at, generation and client_id, which
                       must equal the CLIENT_ID line in its own resources/lib/modules/punchplay.py
                       or the row is ignored; plus the settings punchplay.accesstoken,
                       punchplay.isauthed 'true', punchplay.tokenexpiry, punchplay.username. An
                       expires_at in the past with no refresh token makes it ask the user to sign
                       in again, so a far-off one is written.

    An add-on that holds a sign-in WITH a refresh token made it itself (under its own app, renewing
    itself): the renewals leave it alone; the sign-in button and "Sync Add-ons" replace it.
    The official PunchPlay scrobbler (script.punchplay) signs in another way, with no app id, and
    is not fed.
"""

import json
import os
import re
import sqlite3
import uuid

import xbmc
import xbmcaddon
import xbmcvfs

from reauthorize.modules.control import accountmgr

LOG_TAG = '[ReAuthorize PunchPlay]'
COSMOS, REDLIGHT, TMDBMOVIES, ARCHIVES, UMBRELLA = ('plugin.video.cosmos', 'plugin.video.redlight', 'plugin.video.tmdbmovies',
                                                    'plugin.video.thearchives', 'plugin.video.umbrella')
ADDONS = (COSMOS, REDLIGHT, TMDBMOVIES, ARCHIVES, UMBRELLA)

LIFETIME = 3600
FAR_OFF = 4102444800            # 2100-01-01: "does not run out" for Umbrella, the same at every write
_UMBRELLA_ID_LINE = re.compile(r'^CLIENT_ID\s*=\s*["\']([^"\']+)["\']', re.M)
_UMBRELLA_TABLES = ('punchplay_state', 'punchplay_watched_movies', 'punchplay_watched_episodes', 'punchplay_lists',
                    'bookmarks', 'watched')         # what Umbrella's own sign-out drops
_REDLIGHT_BLANK = (None, '', '0', 'empty_setting')
# Umbrella's "where do watched marks and scrobbles go" choices; 7 = PunchPlay. A sign-out has to
# take them off PunchPlay (Umbrella's own does), and the user should not have to set them again
# after signing back in: which ones were on PunchPlay is remembered here (the user, 2026-10-13:
# 'it is still set to PunchPlay, I never changed it' - it had been reset behind their back).
_UMBRELLA_CHOICES = (('indicators.alt', 'indicators'), ('scrobble.source', 'scrobble'))
UMBRELLA_CHOICES_SETTING = 'punchplay.umbrella.choices'


def _log(message):
    xbmc.log('%s %s' % (LOG_TAG, message), xbmc.LOGINFO)


def _settings_ready(addon_id):
    return (xbmcvfs.exists('special://home/addons/%s/' % addon_id) and
            xbmcvfs.exists('special://profile/addon_data/%s/settings.xml' % addon_id))


def _profile(addon_id, name):
    return xbmcvfs.translatePath('special://profile/addon_data/%s/%s' % (addon_id, name))


def _umbrella_app_id():
    """Umbrella's own PunchPlay app id, from its code ('' when this Umbrella has no PunchPlay)."""
    path = xbmcvfs.translatePath('special://home/addons/%s/resources/lib/modules/punchplay.py' % UMBRELLA)
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            found = _UMBRELLA_ID_LINE.search(f.read())
        return found.group(1).strip() if found else ''
    except Exception:
        return ''


def _ready(addon_id):
    if addon_id == REDLIGHT:
        from reauthorize.modules.db import redlight_db
        return redlight_db.available()
    if addon_id == UMBRELLA:
        return _settings_ready(UMBRELLA) and bool(_umbrella_app_id())
    return _settings_ready(addon_id)


def _read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path, data):
    text = json.dumps(data)
    xbmcvfs.mkdirs(os.path.dirname(path))
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(path + '.tmp', path)


def _redlight_rows(*ids):
    from libs.common import var
    rows = {}
    try:
        conn = sqlite3.connect(var.redlight_settings_db, timeout=10)
        try:
            for sid in ids:
                row = conn.execute('SELECT setting_value FROM settings WHERE setting_id = ?', (sid,)).fetchone()
                value = row[0] if row else ''
                rows[sid] = '' if value in _REDLIGHT_BLANK else str(value)
        finally:
            conn.close()
    except Exception:
        pass
    return rows


def _umbrella_state():
    path = _profile(UMBRELLA, 'punchplaySync.db')
    if not os.path.isfile(path):
        return {}
    try:
        conn = sqlite3.connect(path, timeout=10)
        try:
            row = conn.execute("SELECT value FROM punchplay_state WHERE key = 'tokens'").fetchone()
        finally:
            conn.close()
        data = json.loads(row[0]) if row else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _held(addon_id):
    """(access token, refresh token) an add-on holds now; '' for none."""
    if addon_id == COSMOS:
        data = _read_json(_profile(COSMOS, 'punchplay_token.json'))
        return str(data.get('access_token') or ''), str(data.get('refresh_token') or '')
    if addon_id == REDLIGHT:
        rows = _redlight_rows('punchplay.token', 'punchplay.refresh')
        return rows.get('punchplay.token', ''), rows.get('punchplay.refresh', '')
    if addon_id == UMBRELLA:
        state = _umbrella_state()
        if state.get('access_token'):
            return str(state['access_token']), str(state.get('refresh_token') or '')
        addon = xbmcaddon.Addon(UMBRELLA)
        return addon.getSetting('punchplay.accesstoken'), addon.getSetting('punchplay.refreshtoken')
    ids = {TMDBMOVIES: ('punchplay_access_token', 'punchplay_refresh_token'),
           ARCHIVES: ('punchplay.access_token', 'punchplay.refresh_token')}[addon_id]
    addon = xbmcaddon.Addon(addon_id)
    return addon.getSetting(ids[0]), addon.getSetting(ids[1])


def _account():
    try:
        expires = int(float(accountmgr.getSetting('punchplay.expires') or 0))
    except (TypeError, ValueError):
        expires = 0
    return {'token': accountmgr.getSetting('punchplay.token'),
            'expires': expires,
            'user': accountmgr.getSetting('punchplay.username') or 'PunchPlay User',
            'user_id': accountmgr.getSetting('punchplay.user.id')}


def _set(addon_id, pairs):
    addon = xbmcaddon.Addon(addon_id)
    for sid, value in pairs:
        if addon.getSetting(sid) != value:
            addon.setSetting(sid, value)


def _write(addon_id, a):
    # Times come from the sign-in's own expiry, not the clock, so the same sign-in is always
    # written the same way.
    made = a['expires'] - LIFETIME if a['expires'] else 0
    if addon_id == COSMOS:
        _write_json(_profile(COSMOS, 'punchplay_token.json'),
                    {'access_token': a['token'], 'token_type': 'bearer', 'expires_in': LIFETIME,
                     'stored_at': made, 'username': a['user']})
        _set(COSMOS, [('punchplay_auth_done', 'true'), ('punchplay_username', a['user'])])
    elif addon_id == REDLIGHT:
        from reauthorize.modules.db import redlight_db
        redlight_db.push([('punchplay.token', a['token']), ('punchplay.refresh', '0'), ('punchplay.expires', '0'),
                          ('punchplay.user', a['user'])])
    elif addon_id == TMDBMOVIES:
        _set(TMDBMOVIES, [('punchplay_access_token', a['token']), ('punchplay_refresh_token', ''),
                          ('punchplay_token_expiry', ''), ('punchplay_username', a['user']),
                          ('punchplay_status', 'Connected: %s' % a['user'])])
    elif addon_id == ARCHIVES:
        _set(ARCHIVES, [('punchplay.access_token', a['token']), ('punchplay.refresh_token', ''),
                        ('punchplay.expires', str(a['expires'] or '')), ('punchplay.refresh_expires', ''),
                        ('punchplay.username', a['user']), ('punchplay.user_id', a['user_id'])])
    elif addon_id == UMBRELLA:
        app_id = _umbrella_app_id()
        # One "generation" per account: Umbrella cancels a request when it changes under it.
        generation = str(uuid.uuid5(uuid.NAMESPACE_URL, 'reauthorize-punchplay:%s' % a['user']))
        state = {'access_token': a['token'], 'refresh_token': '', 'token_type': 'bearer', 'expires_in': LIFETIME,
                 'username': a['user'], 'client_id': app_id, 'generation': generation, 'expires_at': FAR_OFF}
        conn = sqlite3.connect(_profile(UMBRELLA, 'punchplaySync.db'), timeout=30)
        try:
            with conn:
                conn.execute('CREATE TABLE IF NOT EXISTS punchplay_state (key TEXT PRIMARY KEY, value TEXT)')
                conn.execute('INSERT OR REPLACE INTO punchplay_state VALUES (?, ?)', ('tokens', json.dumps(state)))
        finally:
            conn.close()
        _set(UMBRELLA, [('punchplay.accesstoken', a['token']), ('punchplay.refreshtoken', ''),
                        ('punchplay.tokenexpiry', str(FAR_OFF)), ('punchplay.isauthed', 'true'),
                        ('punchplay.username', a['user'])])
        # Put back the choices a sign-out took off PunchPlay, unless the user has since picked
        # something else for them (anything but Local).
        remembered = [k for k in accountmgr.getSetting(UMBRELLA_CHOICES_SETTING).split(',') if k]
        if remembered:
            addon = xbmcaddon.Addon(UMBRELLA)
            for key, label in _UMBRELLA_CHOICES:
                if key in remembered and addon.getSetting(key) in ('', '0'):
                    addon.setSetting(key, '7')
                    addon.setSetting(label, 'PunchPlay')
            accountmgr.setSetting(UMBRELLA_CHOICES_SETTING, '')


def _clear(addon_id, remember=False):
    if addon_id == COSMOS:
        for name in ('punchplay_token.json', 'punchplay_partner_sync.json'):     # the second mirrors the account
            path = _profile(COSMOS, name)
            if os.path.isfile(path):
                os.remove(path)
        _set(COSMOS, [('punchplay_auth_done', 'false'), ('punchplay_username', '')])
    elif addon_id == REDLIGHT:
        from reauthorize.modules import control
        from reauthorize.modules.db import redlight_db
        before = control.wiping()
        control.set_wiping(True)                  # redlight_db puts rows back to Red Light's defaults
        try:
            redlight_db.push([('punchplay.token', ''), ('punchplay.refresh', ''), ('punchplay.expires', ''),
                              ('punchplay.user', '')])
        finally:
            control.set_wiping(before)
    elif addon_id == TMDBMOVIES:
        _set(TMDBMOVIES, [('punchplay_access_token', ''), ('punchplay_refresh_token', ''), ('punchplay_token_expiry', ''),
                          ('punchplay_username', ''), ('punchplay_status', 'Disconnected')])
    elif addon_id == ARCHIVES:
        _set(ARCHIVES, [(sid, '') for sid in ('punchplay.access_token', 'punchplay.refresh_token', 'punchplay.user_id',
                                              'punchplay.username', 'punchplay.expires', 'punchplay.refresh_expires')])
    elif addon_id == UMBRELLA:
        # What Umbrella's own sign-out does, without calling PunchPlay.
        path = _profile(UMBRELLA, 'punchplaySync.db')
        if os.path.isfile(path):
            conn = sqlite3.connect(path, timeout=30)
            try:
                with conn:
                    for table in _UMBRELLA_TABLES:
                        conn.execute('DROP TABLE IF EXISTS %s' % table)
            finally:
                conn.close()
        addon = xbmcaddon.Addon(UMBRELLA)
        _set(UMBRELLA, [('punchplay.%s' % key, '') for key in ('accesstoken', 'refreshtoken', 'tokenexpiry', 'isauthed', 'username')])
        were = []
        for key, label in _UMBRELLA_CHOICES:
            if addon.getSetting(key) == '7':      # 7 = PunchPlay: back to Local, as Umbrella does
                addon.setSetting(key, '0')
                addon.setSetting(label, 'Local')
                were.append(key)
        # A sign-out remembers them for the next sign-in; a wipe (a reset, a build being
        # prepared) does not: nothing of the old owner's set-up is carried over.
        if remember and were:
            accountmgr.setSetting(UMBRELLA_CHOICES_SETTING, ','.join(were))
        elif not remember:
            accountmgr.setSetting(UMBRELLA_CHOICES_SETTING, '')


def push(force=False):
    """
    Give every ready add-on ReAuthorize's PunchPlay access token. An add-on already holding it is
    left alone; one holding a sign-in of its own (it has a refresh token) is replaced only with
    force (the sign-in button, "Sync Add-ons"). How many add-ons were written.
    """
    a = _account()
    if not a['token']:
        return 0
    sent = 0
    for addon_id in ADDONS:
        try:
            if not _ready(addon_id):
                continue
            held, own_refresh = _held(addon_id)
            if held == a['token'] or (own_refresh and not force):
                continue
            _write(addon_id, a)
            sent += 1
            _log('sign-in sent to %s' % addon_id)
        except Exception as e:
            _log('could not send the sign-in to %s: %s' % (addon_id, e))
    return sent


def ensure():
    """Between renewals: put the sign-in back where an update, a build or the add-on itself removed it."""
    return push()


def holding():
    """The add-ons that hold ReAuthorize's current token (for the account window and the tests)."""
    token = accountmgr.getSetting('punchplay.token')
    found = []
    for addon_id in ADDONS:
        try:
            if token and _ready(addon_id) and _held(addon_id)[0] == token:
                found.append(addon_id)
        except Exception:
            pass
    return found


def wipe(token=None):
    """
    No token (a wipe): clear every add-on's PunchPlay sign-in. A token (a sign-out): only where
    that token is held, or where a token sits with no refresh token (one ReAuthorize sent
    earlier); a sign-in the add-on made for itself is left alone. How many add-ons were cleared.
    """
    cleared = 0
    for addon_id in ADDONS:
        try:
            if not _ready(addon_id):
                continue
            held, own_refresh = _held(addon_id)
            if not held and not own_refresh:
                continue
            if token is not None and held != token and own_refresh:
                continue
            _clear(addon_id, remember=token is not None)
            cleared += 1
            _log('sign-in removed from %s' % addon_id)
        except Exception as e:
            _log('could not clear %s: %s' % (addon_id, e))
    return cleared
