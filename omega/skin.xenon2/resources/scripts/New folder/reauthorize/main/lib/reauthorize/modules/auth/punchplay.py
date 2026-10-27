# -*- coding: utf-8 -*-
"""
    ReAuthorize - PunchPlay sign-in (1.4.1)

    PunchPlay (punchplay.tv) tracks what is watched, like Trakt. The add-ons that support it
    (Cosmos, Red Light, TMDb Movies, The Archives, Umbrella) each sign in under their own app.
    ReAuthorize is registered as its own public app (the user, 2026-10-12, no client secret), so
    the sign-in is the usual "enter this code" screen, and the result is handed to the add-ons
    (sync/punchplay_sync.py).

    What makes PunchPlay different from every other service here, all seen live 2026-10-13:
      - an access token lasts ONE HOUR;
      - the moment a renewal answers, the old access token is dead (no overlap);
      - a renewal also replaces the refresh token, and when two holders renew from the same
        refresh token the LAST one wins and the other is signed out.
    So ReAuthorize is the ONLY one that renews. The add-ons get the access token and never the
    refresh token (none of the five signs itself out over a token it cannot renew, read from
    their code), and ReAuthorize renews well before the hour is up, at start and while Kodi
    runs (startup._keep_signed_in), and re-sends at once.

    Backups: the refresh token changes at every renewal, so each renewal rewrites the local
    vault (a file write). The server copy is NOT rewritten each time (thousands of boxes, every
    40 minutes); it is refreshed whenever another sign-in changes, so it usually holds a USED
    refresh token.

    NEVER SHOW PUNCHPLAY A REFRESH TOKEN THAT IS NOT THE NEWEST ONE (1.4.2). PunchPlay answers a
    used one by ending the sign-in everywhere, the newest pair included. Found the day 1.4.1
    went out: a second Kodi on the dev PC (same store, same device id) started with no sign-ins,
    restored the seven-hour-old pair from the server and tried to renew with it at 21:38:38;
    PunchPlay refused, and six minutes later refused the bench's own, never-used pair too. 1.4.1
    tried the settings' token first and the vault's only after a refusal, which is too late. So
    before every renewal, and at every look, the vault is read: if it holds a pair that runs
    out LATER than the one in the settings, that pair is taken over without calling PunchPlay
    (_adopt_newer_from_vault). That covers a restore from the server, a settings dialog that
    saved an old pair back, and two Kodis sharing one store. The server's copy is only ever the
    newest when there is no vault, and then there is no vault's device id to fetch it with.

    API: https://punchplay.tv/api/platform/v1 - POST /auth/device/code {client_id} (no scope:
    PunchPlay then grants the app's allowed ones), POST /auth/device/token {client_id,
    device_code, device_name, device_id}, POST /auth/refresh {client_id, refresh_token},
    POST /oauth/revoke {client_id, token}, GET /me. API calls send 'Authorization: Bearer' only.
"""

import json
import threading
import time
import uuid

import xbmc
import xbmcgui

from reauthorize.modules import control

CLIENT_ID = 'ppc_9a3280db2460683659cb4f09'
API = 'https://punchplay.tv/api/platform/v1'
LOG_TAG = '[ReAuthorize PunchPlay]'

TOKEN = 'punchplay.token'
REFRESH = 'punchplay.refresh'
EXPIRES = 'punchplay.expires'
USERNAME = 'punchplay.username'
USER_ID = 'punchplay.user.id'
DEVICE_ID = 'punchplay.device.id'
DISPLAY = 'punchplay.username.display'
KEYS = (TOKEN, REFRESH, EXPIRES, USERNAME, USER_ID)

LIFETIME = 60 * 60                  # what PunchPlay issues (expires_in 3600)
# The start-up service looks every five minutes: renewing with 25 minutes left means an add-on
# never holds a token with less than about 20 minutes on it while Kodi runs.
RENEW_WHEN_LEFT = 25 * 60

_renew_lock = threading.Lock()
# The service renews, and so can the "Sync Add-ons" button, which is another process: two
# renewals at once would leave one of them holding a dead pair. Kodi's home window is shared.
_BUSY = 'reauthorize.punchplay.renewing'


def _renewing_elsewhere():
    try:
        return time.time() - float(control.window.getProperty(_BUSY) or 0) < 45
    except (TypeError, ValueError):
        return False


def _log(message, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (LOG_TAG, message), level)


def _user_agent():
    try:
        version = control.addonVersion()
    except Exception:
        version = '1'
    return 'ReAuthorize/%s (+https://the-hermit.com)' % version


def _call(path, payload=None, token=None, timeout=20):
    """(status, json body) - (None, {}) when PunchPlay cannot be reached. Never raises."""
    try:
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
    except ImportError:
        return None, {}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': _user_agent()}
    if token:
        headers['Authorization'] = 'Bearer %s' % token
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    try:
        response = urlopen(Request(API + path, data=body, headers=headers), timeout=timeout)
        raw = response.read().decode('utf-8', 'replace')
        status = response.getcode()
    except HTTPError as e:
        try:
            raw = e.read().decode('utf-8', 'replace')
        except Exception:
            raw = ''
        status = e.code
    except Exception as e:
        _log('could not reach PunchPlay (%s): %s' % (path, e))
        return None, {}
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    return status, data if isinstance(data, dict) else {}


def signed_in():
    return bool(control.setting(TOKEN))


def seconds_left():
    try:
        return float(control.setting(EXPIRES)) - time.time()
    except (TypeError, ValueError):
        return 0


def _device_id():
    device_id = control.setting(DEVICE_ID)
    if not device_id:
        device_id = str(uuid.uuid4())
        control.setSetting(DEVICE_ID, device_id)
    return device_id


# The pair this process last stored. Kodi's settings dialog writes back the values it was opened
# with when it closes, so a dialog left open across a renewal puts the OLD pair back into the
# settings: a dead access token and a used refresh token. The service remembers what it stored
# and puts it back (_undo_revert), where the next renewal would otherwise be refused.
_last = {}


def _store(token):
    control.setSetting(TOKEN, token['access_token'])
    if token.get('refresh_token'):
        control.setSetting(REFRESH, token['refresh_token'])
    try:
        lifetime = float(token.get('expires_in') or LIFETIME)
    except (TypeError, ValueError):
        lifetime = LIFETIME
    control.setSetting(EXPIRES, str(int(time.time() + lifetime)))
    if token.get('username'):
        control.setSetting(USERNAME, str(token['username']))
    _last.update({TOKEN: control.setting(TOKEN), REFRESH: control.setting(REFRESH), EXPIRES: control.setting(EXPIRES)})


def _undo_revert():
    """
    Put back the pair this process stored, if the settings now hold an OLDER one (a settings
    dialog saved over it). A blank (signed out) or a newer pair (signed in again) is left alone:
    those are the user's doing. True if the newer pair was put back.
    """
    if not _last or not control.setting(TOKEN) or control.setting(TOKEN) == _last.get(TOKEN):
        return False
    try:
        if float(control.setting(EXPIRES) or 0) >= float(_last.get(EXPIRES) or 0):
            return False
    except (TypeError, ValueError):
        return False
    for key in (TOKEN, REFRESH, EXPIRES):
        control.setSetting(key, _last[key])
    _log('the settings held an older PunchPlay sign-in than the one last renewed - put the newer one back')
    return True


def _send(force=False):
    try:
        from reauthorize.modules.sync import punchplay_sync
        return punchplay_sync.push(force=force)
    except Exception as e:
        _log('could not send the sign-in to the add-ons: %s' % e)
        return 0


def _back_up_locally():
    # The vault only: see the note on backups at the top of this file.
    try:
        from reauthorize.modules import vault
        vault.backup()
    except Exception as e:
        _log('could not back up the sign-in: %s' % e)


def sign_in():
    """The 'Authorize PunchPlay' button. True if signed in."""
    from reauthorize.modules import qr
    from reauthorize.windows import device_auth
    status, start = _call('/auth/device/code', {'client_id': CLIENT_ID})
    if not (start.get('device_code') and start.get('user_code')):
        _log('device sign-in could not start (HTTP %s %s)' % (status, start.get('error') or ''), xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('ReAuthorize', 'PunchPlay sign-in did not start. Try again later.')
        return False

    result = {}

    def poll_once():
        code, token = _call('/auth/device/token', {'client_id': CLIENT_ID, 'device_code': start['device_code'],
                                                   'device_name': 'ReAuthorize for Kodi', 'device_id': _device_id()})
        if code == 200 and token.get('access_token'):
            result['token'] = token
            return True
        error = str(token.get('error') or '').lower()
        if code is None or error in ('authorization_pending', 'slow_down'):
            return None
        if error or (code or 0) >= 400:
            return False
        return None

    verification = start.get('verification_uri') or 'https://punchplay.tv/link'
    try:
        expires_in = int(start.get('expires_in') or 600)
    except (TypeError, ValueError):
        expires_in = 600
    device_auth.run('PunchPlay', qr.qr_image_url(start.get('verification_uri_complete') or verification),
                    verification, start['user_code'], poll_once, interval=5, expires_in=expires_in)
    if 'token' not in result:
        return False

    token = result['token']
    _store(token)
    name = str(token.get('username') or '')
    code, me = _call('/me', token=token['access_token'])
    if code == 200:
        name = name or str(me.get('username') or me.get('name') or '')
        control.setSetting(USER_ID, str(me.get('id') or ''))
    control.setSetting(USERNAME, name)
    control.setSetting(DISPLAY, name or 'Signed in')
    _log('signed in%s' % (' as %s' % name if name else ''))
    # No backup here: the button's automatic backup (default.py, autosave) makes it and says so.
    sent = _send(force=True)
    control.notification(title='PunchPlay', message='Signed in. Sent to %d add-on%s.' % (sent, '' if sent == 1 else 's')
                         if sent else 'Signed in.')
    return True


def _renew_with(refresh):
    """
    'ok' if PunchPlay accepted this refresh token (the new pair is stored), 'refused' if it said
    the token is no good, 'unreachable' when there was no usable answer.
    """
    if not refresh:
        return 'refused'
    status, token = _call('/auth/refresh', {'client_id': CLIENT_ID, 'refresh_token': refresh})
    if status == 200 and token.get('access_token'):
        _store(token)
        return 'ok'
    error = str(token.get('error') or '').lower()
    if status in (400, 401) and error in ('invalid_grant', 'invalid_token', 'invalid_client', 'access_denied'):
        _refusal['why'] = 'HTTP %s %s: %s' % (status, error, str(token.get('message') or token.get('error_description') or '')[:120])
        return 'refused'
    return 'unreachable'


_refusal = {}       # what PunchPlay said the last time it refused, for the log


def _adopt_newer_from_vault():
    """
    Take over the vault's pair when it runs out later than the one in the settings (see the top
    of this file): another Kodi on this device renewed, or the settings were put back to an
    older pair. Nothing is asked of PunchPlay. Only for a box that holds a pair: one that is
    signed out stays signed out. True if the vault's pair was taken over.
    """
    mine = control.setting(REFRESH)
    if not mine:
        return False
    try:
        from reauthorize.modules import vault
        stored = vault.stored()
    except Exception:
        return False
    theirs = {key: str(stored.get(key) or '') for key in KEYS}
    if not (theirs[TOKEN] and theirs[REFRESH]) or theirs[REFRESH] == mine:
        return False
    try:
        if float(theirs[EXPIRES] or 0) <= float(control.setting(EXPIRES) or 0):
            return False
    except (TypeError, ValueError):
        return False
    for key in (TOKEN, REFRESH, EXPIRES):
        control.setSetting(key, theirs[key])
    for key in (USERNAME, USER_ID):
        if theirs[key]:
            control.setSetting(key, theirs[key])
    _last.update({TOKEN: theirs[TOKEN], REFRESH: theirs[REFRESH], EXPIRES: theirs[EXPIRES]})
    _log('the local backup holds a newer PunchPlay sign-in than the settings - using that one')
    return True


def refresh_if_due(quiet=True, force=False):
    """
    Renew when less than RENEW_WHEN_LEFT of the hour remains (or force), then re-send at once:
    the old access token is dead the moment PunchPlay answers. Not due: just make sure the
    add-ons still hold the sign-in. True if renewed.
    """
    if not signed_in() and not control.setting(REFRESH):
        return False
    with _renew_lock:
        _undo_revert()
        if _adopt_newer_from_vault():
            _send()                 # the add-ons hold the pair that was just replaced
        if not force and seconds_left() > RENEW_WHEN_LEFT:
            try:
                from reauthorize.modules.sync import punchplay_sync
                punchplay_sync.ensure()
            except Exception as e:
                _log('could not check the add-ons: %s' % e)
            return False
        if _renewing_elsewhere():
            return False
        control.window.setProperty(_BUSY, str(time.time()))
        try:
            outcome = _renew_with(control.setting(REFRESH))
        finally:
            control.window.clearProperty(_BUSY)
        if outcome == 'ok':
            _log('sign-in renewed - sending it to the add-ons')
            _send()
            _back_up_locally()
            return True
        if outcome == 'unreachable':
            if not quiet:
                control.notification(title='PunchPlay', message='Renewal failed. Try again later.')
            return False
        # Refused: this sign-in is over, and so is every other copy of it (PunchPlay ends them
        # all together). Keeping it would only repeat a refused request every few minutes and
        # leave the add-ons holding a dead token.
        _log('PunchPlay refused the renewal (%s) - the sign-in has ended' % (_refusal.get('why') or 'no reason given'), xbmc.LOGWARNING)
        _forget()
        _back_up_locally()
        control.notification(title='PunchPlay', message='Please sign in to PunchPlay again.', time=6000)
        return False


def _forget():
    _last.clear()
    token = control.setting(TOKEN)
    for key in KEYS + (DISPLAY,):
        control.setSetting(key, '')
    try:
        from reauthorize.modules.sync import punchplay_sync
        punchplay_sync.wipe(token=token)
    except Exception as e:
        _log('could not clear the add-ons: %s' % e)


def sign_out():
    """The 'Revoke' button: end the sign-in at PunchPlay and take it out of the add-ons."""
    token = control.setting(REFRESH) or control.setting(TOKEN)
    if token:
        _call('/oauth/revoke', {'client_id': CLIENT_ID, 'token': token})
    _forget()
    control.notification(title='PunchPlay', message='Signed out of PunchPlay.')


def account_info_to_dialog():
    if not signed_in():
        control.notification(title='PunchPlay', message='Not signed in.')
        return
    minutes = max(0, int(seconds_left() // 60))
    control.selectDialog(['Username: %s' % (control.setting(USERNAME) or 'Unknown'),
                          'Renewed automatically (next in about %d minutes)' % max(0, minutes - RENEW_WHEN_LEFT // 60)],
                         'PunchPlay Account')
