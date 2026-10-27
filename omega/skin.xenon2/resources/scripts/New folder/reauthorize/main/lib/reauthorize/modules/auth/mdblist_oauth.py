# -*- coding: utf-8 -*-
"""
    ReAuthorize - MDBList account sign-in (1.3.7)

    The MDBList API key under Metadata is for ratings and lists. Scrobbling (and anything else
    that acts on the user's MDBList account) needs an account sign-in, which MDBList does with
    OAuth. ReAuthorize is registered with MDBList as its own Device Code app (2026-10-02, no
    client secret: a public client, the id ships in every zip), so the sign-in is the same
    "enter this code" screen as Trakt and Real-Debrid. The result goes to the MDBList Scrobbler
    (sync/mdblist_oauth_sync.py).

    MDBList's access tokens last 30 days and renew with the refresh token and the client id
    alone. ReAuthorize renews when half of that is left, at start and while Kodi runs
    (startup._keep_signed_in), and re-sends, so the Scrobbler's own last-minute renewal is
    rarely needed. If ReAuthorize's renewal is refused, the Scrobbler may have renewed first:
    its copy is tried before the user is asked.

    Endpoints (all need the trailing slash): https://api.mdblist.com/oauth/device-authorization/,
    /oauth/token/, /oauth/revoke_token/; API calls send 'Authorization: Bearer <token>'.

    One MDBList for the user (1.4.0; the user, 2026-10-09: 'treat it like it was one program no
    matter which way they log in'). This is the only MDBList button. MDBList never gives the API
    key to an account sign-in, and several add-ons still take only the key, so the sign-in offers
    to add the key in the same flow (skipped when one is already there). Signing out clears both.
"""

import time

import xbmc
import xbmcgui

from reauthorize.modules import control

CLIENT_ID = 'zpDb4MuNZn0pnbRxqPym8j9Ls7GiNMtpDjas3nrE'
API = 'https://api.mdblist.com'
DEVICE_GRANT = 'urn:ietf:params:oauth:grant-type:device_code'
LOG_TAG = '[ReAuthorize MDBList]'
# The API key (auth/mdblist.py) and what goes with it; cleared with the sign-in.
API_KEY_SETTINGS = ('mdb.api.key', 'mdb.username', 'mdb.api.key.display', 'mdb.username.display')

TOKEN = 'mdblist.oauth.token'
REFRESH = 'mdblist.oauth.refresh'
EXPIRES = 'mdblist.oauth.expires'
USERNAME = 'mdblist.oauth.username'
DISPLAY = 'mdblist.oauth.username.display'
KEYS = (TOKEN, REFRESH, EXPIRES, USERNAME)

LIFETIME = 30 * 24 * 60 * 60        # what MDBList issues (expires_in 2592000)
RENEW_WHEN_LEFT = LIFETIME / 2


def _log(message, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (LOG_TAG, message), level)


def _post(path, data, timeout=15):
    """(status, json body or None), or (None, None) when MDBList cannot be reached."""
    try:
        import requests          # here, not at the top: the sync code reads CLIENT_ID without needing it
        response = requests.post(API + path, data=data, timeout=timeout)
    except Exception as e:
        _log('could not reach MDBList (%s): %s' % (path, e))
        return None, None
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, None


def _username(token):
    try:
        import requests
        response = requests.get(API + '/user', headers={'Authorization': 'Bearer %s' % token}, timeout=15)
        data = response.json() if response.status_code == 200 else {}
        for key in ('username', 'user_name', 'name'):
            if isinstance(data, dict) and data.get(key):
                return str(data[key])
    except Exception as e:
        _log('could not read the account name: %s' % e)
    return ''


def signed_in():
    return bool(control.setting(TOKEN))


def _store(token):
    control.setSetting(TOKEN, token['access_token'])
    control.setSetting(REFRESH, token.get('refresh_token') or control.setting(REFRESH))
    try:
        lifetime = float(token.get('expires_in') or LIFETIME)
    except (TypeError, ValueError):
        lifetime = LIFETIME
    control.setSetting(EXPIRES, str(int(time.time() + lifetime)))


def _send_and_back_up(api_key_added=False, back_up=True):
    try:
        from reauthorize.modules.sync import mdblist_oauth_sync
        mdblist_oauth_sync.push()
    except Exception as e:
        _log('could not send the sign-in to the add-ons: %s' % e)
    if api_key_added:
        try:
            from reauthorize.modules.sync import meta_sync
            meta_sync.Auth().meta_auth()
            control.setSetting('sync.meta.service', 'true')
        except Exception as e:
            _log('could not send the API key to the add-ons: %s' % e)
    if not back_up:
        return
    try:
        from reauthorize.modules import vault, server
        vault.backup()
        server.backup()
    except Exception as e:
        _log('could not back up the sign-in: %s' % e)


def _offer_api_key():
    """After the account sign-in: offer the API key too, unless one is there. True if added."""
    if control.setting('mdb.api.key'):
        return False
    if not xbmcgui.Dialog().yesno('ReAuthorize',
                                  'Add your MDBList API key too?[CR][CR]Some add-ons only take the key. '
                                  'It is on mdblist.com under Preferences. You can skip this.',
                                  nolabel='Skip', yeslabel='Add key'):
        return False
    from reauthorize.modules.auth import mdblist
    return bool(mdblist.MDBListAuth().authorize())


def sign_in():
    """The 'Authorize MDBList' button. True if signed in."""
    from reauthorize.modules import qr
    from reauthorize.windows import device_auth
    status, start = _post('/oauth/device-authorization/', {'client_id': CLIENT_ID, 'scope': 'write'})
    if not (isinstance(start, dict) and start.get('device_code') and start.get('user_code')):
        _log('device sign-in could not start (HTTP %s)' % status, xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('ReAuthorize', 'MDBList sign-in did not start. Try again later.')
        return False

    result = {}

    def poll_once():
        code, token = _post('/oauth/token/', {'grant_type': DEVICE_GRANT,
                                              'device_code': start['device_code'],
                                              'client_id': CLIENT_ID})
        if isinstance(token, dict) and token.get('access_token'):
            result['token'] = token
            return True
        if isinstance(token, dict) and token.get('error') in ('access_denied', 'expired_token'):
            return False
        return None         # authorization_pending, slow_down, or no answer: keep waiting

    verification = start.get('verification_uri') or 'https://mdblist.com/oauth/device/'
    try:
        interval = max(int(start.get('interval', 5)), 1)
        expires_in = int(start.get('expires_in', 900))
    except (TypeError, ValueError):
        interval, expires_in = 5, 900
    device_auth.run('MDBList', qr.qr_image_url(start.get('verification_uri_complete') or verification),
                    verification, start['user_code'], poll_once, interval=interval, expires_in=expires_in)
    if 'token' not in result:
        return False

    _store(result['token'])
    name = _username(result['token']['access_token'])
    control.setSetting(USERNAME, name)
    control.setSetting(DISPLAY, name or 'Signed in')
    _log('signed in%s' % (' as %s' % name if name else ''))
    # No backup here: the button's automatic backup (default.py, autosave) makes it and says so,
    # or says why not. A renewal in the background still backs up by itself.
    _send_and_back_up(api_key_added=_offer_api_key(), back_up=False)
    control.notification(title='MDBList', message='Signed in. Sent to your MDBList add-ons.')
    return True


def _renew_with(refresh):
    """True if MDBList accepted this refresh token (and the new pair is stored)."""
    if not refresh:
        return False
    status, token = _post('/oauth/token/', {'grant_type': 'refresh_token', 'refresh_token': refresh,
                                           'client_id': CLIENT_ID})
    if status == 200 and isinstance(token, dict) and token.get('access_token'):
        _store(token)
        return True
    return False


def refresh_if_due(quiet=False, force=False):
    """
    Renew when half the 30 days are gone (or force). If not due, just make sure the Scrobbler
    still holds the sign-in (an update of it, or a build install, may have removed it).
    True if renewed.
    """
    if not signed_in():
        return False
    try:
        left = float(control.setting(EXPIRES)) - time.time()
    except (TypeError, ValueError):
        left = 0
    if not force and left > RENEW_WHEN_LEFT:
        try:
            from reauthorize.modules.sync import mdblist_oauth_sync
            mdblist_oauth_sync.ensure()
        except Exception as e:
            _log('could not check the add-ons: %s' % e)
        return False
    if _renew_with(control.setting(REFRESH)):
        _log('sign-in renewed - sending it to the add-ons')
        _send_and_back_up()
        return True
    # Refused or unreachable. The Scrobbler may have renewed first and hold the live pair.
    try:
        from reauthorize.modules.sync import mdblist_oauth_sync
        theirs = mdblist_oauth_sync.scrobbler_refresh_token()
    except Exception:
        theirs = ''
    if theirs and theirs != control.setting(REFRESH) and _renew_with(theirs):
        _log('renewal recovered from the MDBList Scrobbler\'s copy - sending it to the add-ons')
        _send_and_back_up()
        return True
    # 1.4.0: POV, Red Light, Cosmos and TMDb Movies renew with ReAuthorize's app id too.
    try:
        from reauthorize.modules.sync import mdblist_oauth_sync
        others = mdblist_oauth_sync.addon_refresh_tokens()
    except Exception:
        others = []
    for refresh in others[:6]:
        if refresh in (control.setting(REFRESH), theirs):
            continue
        if _renew_with(refresh):
            _log('renewal recovered from an add-on\'s copy - sending it to the add-ons')
            _send_and_back_up()
            return True
    if left <= 0:
        _log('sign-in expired and could not be renewed', xbmc.LOGWARNING)
        control.notification(title='MDBList', message='Please sign in to MDBList again.')
    elif not quiet:
        control.notification(title='MDBList', message='Renewal failed. Try again later.')
    return False


def sign_out():
    """The 'Sign out' button: end the sign-in at MDBList and take it out of the add-ons."""
    token = control.setting(TOKEN)
    api_key = control.setting('mdb.api.key')
    if token:
        _post('/oauth/revoke_token/', {'token': token, 'client_id': CLIENT_ID})
    for key in KEYS + (DISPLAY,) + API_KEY_SETTINGS:
        control.setSetting(key, '')
    try:
        from reauthorize.modules.sync import mdblist_oauth_sync
        mdblist_oauth_sync.wipe(token=token)
        mdblist_oauth_sync.remove_api_key(api_key)    # one sign-in: the key goes too (1.4.0)
    except Exception as e:
        _log('could not clear the add-ons: %s' % e)
    control.notification(title='MDBList', message='Signed out of MDBList.')
