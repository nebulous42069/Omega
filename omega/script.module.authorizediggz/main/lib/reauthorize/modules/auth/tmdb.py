"""TMDB browser approval and dual API session support."""
import json
import hashlib
import time
from urllib.parse import urlencode
import requests
from reauthorize.modules import control, settings_display, sync_support
from reauthorize.modules.sync import portal_sync

BASE = 'https://api.themoviedb.org'
API_key = 'f5608fba6ab49e9985828b35d5653321'
APP_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhMDczMjRjNjY5Y2FjNGQ5Njc4OTE5NzEzNGNlMjcyYiIsIm5iZiI6MTUxOTkzOTM2NC42MDYwMDAyLCJzdWIiOiI1YTk4NmYyNGMzYTM2ODA3M2EwMDZiYzAiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.YMASJX_w-l8tDnqGHl_6EZljra3TOp-hnkgKjyFM4Y8'
HELPER = 'plugin.video.themoviedb.helper'
FIELD = 'tmdb_user_token'
tmdb_icon = control.joinPath(control.artPath(), 'tmdb.png')

def sync_tmdb_display_values():
    settings_display.sync_authorized_display_values()

def bundle(raw):
    try:
        value = json.loads(raw or '{}')
        if isinstance(value, dict) and all(isinstance(value.get(k), str) and value[k].strip() for k in ('access_token', 'account_id')):
            return value
    except (ValueError, TypeError):
        pass
    return None

def sync_helper(wipe=False):
    raw = control.setting('tmdb.authorization')
    if wipe or bundle(raw):
        return sync_support.put(HELPER, [(FIELD, '' if wipe else raw)], wipe=wipe)

def sync_umbrella(wipe=False):
    aid = 'plugin.video.umbrella'
    if not sync_support.installed(aid):
        return True
    grant = bundle(control.setting('tmdb.authorization'))
    if not grant and not wipe:
        return True
    addon = sync_support._Addon(aid)
    pairs = [('tmdb.v4.accesstoken', '' if wipe else grant['access_token']),
             ('tmdb.v4.accountid', '' if wipe else grant['account_id'])]
    # The read token is application identification, not personal authorization.
    # Preserve the user's independent read token when wiping a grant.
    if not wipe:
        pairs.insert(0, ('tmdb.v4.readtoken', APP_READ_TOKEN))
    elif addon.getSetting('tmdb.v4.readtoken') == APP_READ_TOKEN:
        pairs.append(('tmdb.v4.readtoken', ''))
    return sync_support.put(aid, pairs, wipe=wipe)


def clear_umbrella_matching(raw, session):
    aid = 'plugin.video.umbrella'
    if not sync_support.installed(aid):
        return
    addon = sync_support._Addon(aid)
    grant = bundle(raw)
    if grant and addon.getSetting('tmdb.v4.accesstoken') == grant['access_token']:
        sync_umbrella(wipe=True)
    if session and addon.getSetting('tmdb.sessionid') == session:
        sync_support.put(aid, [('tmdb.sessionid', ''), ('tmdbusername', ''), ('tmdbpassword', '')], wipe=True)


def clear_helper_matching(raw):
    if not bundle(raw) or not sync_support.installed(HELPER):
        return
    import xbmcaddon
    held = bundle(xbmcaddon.Addon(HELPER).getSetting(FIELD))
    if held and held['access_token'] == bundle(raw)['access_token']:
        sync_support.put(HELPER, [(FIELD, '')], wipe=True)

def diagnostic(stage, response=None, error=None):
    import xbmc
    # Never log URLs with query strings, response bodies or credentials.
    message = '[Diggz Account Manager] TMDB ' + stage
    if response is not None:
        message += ' HTTP %s' % response.status_code
        try:
            code = response.json().get('status_code')
            if isinstance(code, int):
                message += ' API status %d' % code
        except (ValueError, AttributeError):
            pass
    if error is not None:
        message += ' ' + type(error).__name__
    xbmc.log(message, xbmc.LOGINFO)


def request(method, path, **kwargs):
    response = requests.request(method, BASE + path, timeout=15, **kwargs)
    diagnostic(method + " " + path, response)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or data.get('success') is False:
        raise ValueError('TMDB rejected request')
    return data

PORTAL_FIELD = 'tmdb.portal.authorization'

def grant_identity(grant):
    return hashlib.sha256(grant['access_token'].encode('utf-8')).hexdigest()

def portal_bundle(raw, grant):
    try:
        data = json.loads(raw or '{}')
        if (grant and data.get('grant') == grant_identity(grant)
                and isinstance(data.get('session_id'), str) and data['session_id'].strip()
                and int(data['account_id']) > 0):
            return data
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return None

def convert(grant):
    headers = {'Authorization': 'Bearer ' + APP_READ_TOKEN}
    data = request('POST', '/3/authentication/session/convert/4', headers=headers, json={'access_token': grant['access_token']})
    session = data['session_id']
    if not isinstance(session, str) or not session.strip():
        raise ValueError('Missing V3 session')
    account = request('GET', '/3/account', headers=headers, params={'session_id': session})
    account_id = int(account['id'])
    if account_id <= 0:
        raise ValueError('Invalid account ID')
    converted = {'grant': grant_identity(grant), 'session_id': session, 'account_id': str(account_id), 'username': account.get('username') or ''}
    legacy_ok = False
    try:
        legacy = request('GET', '/3/account', params={'api_key': API_key, 'session_id': session})
        legacy_ok = int(legacy['id']) == account_id
    except Exception as exc:
        diagnostic('legacy V3 compatibility check failed', error=exc)
    return converted, legacy_ok

def sync_portal(wipe=False):
    if wipe:
        return portal_sync.tmdb('', wipe=True)
    grant = bundle(control.setting('tmdb.authorization'))
    if grant and portal_sync.supports_converted():
        data = portal_bundle(control.setting(PORTAL_FIELD), grant)
        if not data:
            try:
                data, _ = convert(grant)
                control.setSetting(PORTAL_FIELD, json.dumps(data))
            except Exception as exc:
                diagnostic('Portal session recovery failed', error=exc)
                sync_support.failed(portal_sync.ADDON_ID)
                return False
        ok = portal_sync.converted_tmdb(data)
        if not ok: sync_support.failed(portal_sync.ADDON_ID)
        return ok
    return portal_sync.tmdb(control.setting('tmdb.session_id'))

def poll_approval(token, headers, result):
    try:
        response = requests.post(BASE + '/4/auth/access_token', headers=headers,
                                 json={'request_token': token}, timeout=12)
    except requests.exceptions.RequestException:
        return None
    if response.status_code == 429:
        return 'slow_down'
    if response.status_code >= 500:
        return None
    try:
        data = response.json()
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    if response.ok and data.get('success') is not False and bundle(json.dumps(data)):
        diagnostic('V4 token exchange accepted', response)
        result['grant'] = data
        return True
    # TMDB reports unapproved tokens as 41; some v4 responses use 33
    # for both unapproved and invalid tokens. Bound retries by token lifetime.
    if data.get('status_code') in (33, 41):
        return None
    diagnostic('V4 token exchange rejected', response)
    return False


class Auth:
    def create_session_id(self):
        import xbmcgui
        from reauthorize.windows import tmdb_auth
        dialog = xbmcgui.Dialog()
        headers = {'Authorization': 'Bearer ' + APP_READ_TOKEN}
        stage = 'request token'
        try:
            started = time.monotonic()
            token = request('POST', '/4/auth/request_token', headers=headers, json={})['request_token']
            url = 'https://www.themoviedb.org/auth/access?' + urlencode({'request_token': token})
            result = {}
            stage = 'V4 approval exchange'
            approved = tmdb_auth.run(url, lambda: poll_approval(token, headers, result), started + 900)
            if not approved or not result.get('grant'):
                return
            grant = result['grant']
        except Exception as exc:
            diagnostic(stage + ' failed', error=exc)
            dialog.ok('TMDB Account', 'Failed during %s. Your existing credentials were preserved. See Kodi log for diagnostic status.' % stage)
            return
        # V4 approval is independently valid: a V3 compatibility failure
        # must not prevent synchronization to TMDb Helper.
        converted = None
        legacy_ok = False
        try:
            converted, legacy_ok = convert(grant)
        except Exception as exc:
            diagnostic('V3 compatibility check failed; retaining existing V3 settings', error=exc)
        try:
            control.setSetting('tmdb.authorization', json.dumps(grant))
            control.setSetting(PORTAL_FIELD, json.dumps(converted) if converted else '')
            if converted and legacy_ok:
                control.setSetting('tmdb.session_id', converted['session_id'])
                control.setSetting('tmdb.username', converted['username'])
                control.setSetting('tmdb.password', '')
            helper_ok = sync_helper()
            umbrella_ok = sync_umbrella()
            portal_ok = False
            if converted and portal_sync.supports_converted():
                portal_ok = portal_sync.converted_tmdb(converted)
            elif converted and legacy_ok:
                portal_ok = portal_sync.tmdb(converted['session_id'])
            sync_tmdb_display_values()
            if sync_support.installed(HELPER) and not helper_ok:
                dialog.ok('TMDB Account', 'TMDB V4 authorization saved, but TMDb Helper synchronization failed. Use Sync Addons to retry.')
            elif not umbrella_ok:
                dialog.ok('TMDB Account', 'Authorization saved, but Umbrella synchronization could not finish. Use Sync Addons to retry.')
            elif portal_sync.installed() and not portal_ok:
                dialog.ok('TMDB Account', 'TMDB V4 authorization saved for TMDb Helper. Diggz Portal synchronization could not finish. Update Portal and use Sync Addons to retry. Existing legacy credentials were preserved.')
            else:
                control.notification(title='Diggz Account Manager', message='TMDB account authorized.', icon=tmdb_icon)
        except Exception as exc:
            diagnostic('saving or synchronizing authorization failed', error=exc)
            dialog.ok('TMDB Account', 'Account approval succeeded, but saving or synchronizing credentials could not finish. Check account status and use Sync Addons.')

    def revoke_session_id(self):
        import xbmcgui
        if not xbmcgui.Dialog().yesno('TMDB Account', 'Sign out of this TMDB account?'):
            return
        session = control.setting('tmdb.session_id')
        raw = control.setting('tmdb.authorization')
        grant = bundle(raw)
        converted = portal_bundle(control.setting(PORTAL_FIELD), grant)
        failed = False
        if converted:
            try:
                request('DELETE', '/3/authentication/session', headers={'Authorization': 'Bearer ' + APP_READ_TOKEN}, json={'session_id': converted['session_id']})
            except Exception:
                failed = True
            portal_sync.revoke_tmdb(converted['session_id'])
        if grant:
            try:
                request('DELETE', '/4/auth/access_token', headers={'Authorization': 'Bearer ' + APP_READ_TOKEN}, json={'access_token': grant['access_token']})
            except Exception:
                failed = True
        if session and (not converted or session != converted['session_id']):
            try:
                request('DELETE', '/3/authentication/session', params={'api_key': control.setting('tmdb.api.key') or API_key}, json={'session_id': session})
            except Exception:
                failed = True
        clear_helper_matching(raw)
        clear_umbrella_matching(raw, session)
        portal_sync.revoke_tmdb(session)
        for k in ('tmdb.authorization', 'tmdb.session_id', 'tmdb.username', 'tmdb.password', PORTAL_FIELD):
            control.setSetting(k, '')
        sync_tmdb_display_values()
        control.notification(title='Diggz Account Manager', message='Local TMDB sign-out complete. Remote revocation could not be confirmed.' if failed else 'TMDB account revoked.', icon=tmdb_icon)
