"""Diggz Portal 10.24.35 native account adapter."""
import json
import time
import uuid
import os
import xbmc
import xbmcaddon
import xbmcvfs
from reauthorize.modules import sync_support

ADDON_ID = 'script.diggzportal'

def addon():
    return sync_support.addon_api(xbmcaddon).Addon(ADDON_ID)

def installed():
    return sync_support.installed(ADDON_ID)

def write(pairs):
    return sync_support.put(ADDON_ID, pairs, wipe=True)

def invalidate(source):
    try:
        os.remove(xbmcvfs.translatePath('special://profile/addon_data/%s/history_%s.json' % (ADDON_ID, source)))
    except FileNotFoundError:
        pass
    except OSError:
        xbmc.log('[Diggz Account Manager] Portal history cache could not be removed', xbmc.LOGWARNING)

def trakt(token, refresh, expires, username):
    if not installed() or not (token and refresh):
        return
    try:
        expiry = int(float(expires))
        if expiry <= 0:
            raise ValueError('missing expiry')
        target = addon()
        changed = target.getSetting('access_token') != token or target.getSetting('refresh_token') != refresh
        now = int(time.time())
        bundle = json.dumps({'access_token': token, 'refresh_token': refresh,
                             'created_at': now, 'expires_in': max(0, expiry-now), 'token_type': 'bearer'})
        if not changed and target.getSetting('trakt_token'):
            bundle = target.getSetting('trakt_token')
        if write([('trakt_oauth_client', 'diggz-2026'), ('refresh_token', refresh),
                  ('token_expires', str(expiry)), ('trakt_token', bundle),
                  ('trakt_user_name', username), ('trakt_slug', '' if changed else target.getSetting('trakt_slug')),
                  ('access_token', token)]) and changed:
            invalidate('trakt')
    except Exception:
        sync_support.failed(ADDON_ID)
        xbmc.log('[Diggz Account Manager] Portal Trakt sync failed', xbmc.LOGWARNING)

def supports_converted():
    if not installed():
        return False
    try:
        version = addon().getAddonInfo('version').split('.')
        return tuple(map(int, version[:3])) >= (10, 24, 47)
    except (ValueError, AttributeError):
        return False

def converted_tmdb(data):
    if not supports_converted():
        return False
    try:
        session = data['session_id']
        account_id = str(int(data['account_id']))
        if not session or int(account_id) <= 0:
            return False
        pairs = [('tmdb_session_client', 'v4-compatible'), ('tmdb_account', account_id), ('tmdb_session', session)]
        if not write(pairs):
            return False
        target = addon()
        return all(target.getSetting(key) == value for key, value in pairs)
    except (ValueError, KeyError, TypeError):
        return False

def tmdb(session, wipe=False):
    if not installed():
        return
    if wipe and not session:
        pairs=[('tmdb_session', ''), ('tmdb_account', '')]
        if supports_converted(): pairs.append(('tmdb_session_client', ''))
        return write(pairs)
    if not session:
        return
    try:
        target = addon()
        if target.getSetting('tmdb_session') == session and target.getSetting('tmdb_account').isdigit() and int(target.getSetting('tmdb_account')) > 0 and (not supports_converted() or not target.getSetting('tmdb_session_client')):
            return True
        import requests
        # Portal uses this same shipped v3 key; do not copy usernames/passwords or custom keys.
        response = requests.get('https://api.themoviedb.org/3/account', params={'api_key': 'f5608fba6ab49e9985828b35d5653321', 'session_id': session}, timeout=15)
        response.raise_for_status()
        account_id = int(response.json()['id'])
        if account_id <= 0:
            raise ValueError('invalid account id')
        pairs=[('tmdb_account', str(account_id)), ('tmdb_session', session)]
        if supports_converted(): pairs.insert(0, ('tmdb_session_client', ''))
        return write(pairs)
    except Exception:
        sync_support.failed(ADDON_ID)
        xbmc.log('[Diggz Account Manager] Portal TMDb account lookup failed', xbmc.LOGWARNING)

def revoke_tmdb(session):
    try:
        if installed() and session and addon().getSetting('tmdb_session') == session:
            pairs=[('tmdb_session', ''), ('tmdb_account', '')]
            if supports_converted(): pairs.append(('tmdb_session_client', ''))
            write(pairs)
    except Exception:
        sync_support.failed(ADDON_ID)
        xbmc.log('[Diggz Account Manager] Portal TMDb sign-out cleanup failed', xbmc.LOGWARNING)

def mdblist(data):
    target = addon()
    changed = target.getSetting('mdblist_access_token') != data['token']
    identity = target.getSetting('mdblist_identity')
    if changed or not identity:
        identity = uuid.uuid4().hex
    if not write([('mdblist_refresh_token', data['refresh']), ('mdblist_expires', str(data['expires'] or 0)),
                  ('mdblist_identity', identity), ('mdblist_key', ''), ('mdblist_access_token', data['token'])]):
        raise RuntimeError('Portal MDBList settings write failed')
    if changed:
        invalidate('mdblist')

def clear_mdblist():
    if not write([(key, '') for key in ('mdblist_access_token', 'mdblist_refresh_token', 'mdblist_expires', 'mdblist_identity', 'mdblist_key')]):
        raise RuntimeError('Portal MDBList settings clear failed')
    invalidate('mdblist')
