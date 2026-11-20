# -*- coding: utf-8 -*-
"""
	Auth Station - Simkl Authorization
	OAuth V2 device authorization for Kodi.
"""
import requests
import xbmc
import xbmcaddon
import os
import time
import uuid
import json

from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import qr
from reauthorize.windows import device_auth

joinPath = os.path.join
simkl_icon = joinPath(xbmcaddon.Addon('script.module.authorizediggz').getAddonInfo('path'),
                      'resources', 'icons', 'simkl.png')

DEVICE_CODE_URL = 'https://api.simkl.com/oauth2/device'
TOKEN_POLL_URL  = 'https://api.simkl.com/oauth2/token'
DEVICE_GRANT    = 'urn:ietf:params:oauth:grant-type:device_code'
USER_URL        = 'https://api.simkl.com/users/settings'

SIMKL_CLIENT_ID     = '00ce4b288e913a45e9d6df007acf523ba21f1fa806142322649be1746060548a'


class Simkl():
	def __init__(self):
		self.client_id = SIMKL_CLIENT_ID

	def _headers(self):
		return {
			'Content-Type': 'application/json',
			'simkl-api-key': control.setting('simkl.client.id') or self.client_id,
			'User-Agent': 'DiggzAccountManager/1.4.5.53',
			'Authorization': 'Bearer %s' % control.setting('simkl.token'),
		}

	def _user_response(self):
		client = control.setting('simkl.client.id') or self.client_id
		response = requests.get(USER_URL, headers=self._headers(), params={
			'client_id': client, 'app-name': 'Diggz Account Manager', 'app-version': '1.4.5.53'}, timeout=15)
		xbmc.log('[Diggz Account Manager] SIMKL account check HTTP %s' % response.status_code, xbmc.LOGINFO)
		response.raise_for_status()
		return response

	def get_device_code(self):
		try:
			resp = requests.post(
				DEVICE_CODE_URL,
				data={'client_id': self.client_id, 'scope': 'media:read media:write'},
				timeout=15,
			)
		except requests.RequestException as exc:
			xbmc.log('[Diggz Account Manager Simkl] PIN request failed (%s).' % type(exc).__name__, xbmc.LOGWARNING)
			control.notification('Simkl', 'Could not reach Simkl. Check your connection and retry.', icon=simkl_icon)
			return None

		try:
			data = resp.json()
		except ValueError:
			data = None
		if resp.ok and isinstance(data, dict) and all(
				data.get(field) for field in ('device_code', 'user_code', 'verification_uri')):
			return data

		# Keep request URLs, response bodies and credentials out of the log.
		reason = 'non-JSON response' if data is None else 'PIN not issued'
		if isinstance(data, dict):
			error = data.get('error')
			if error in ('invalid_client', 'unauthorized_client', 'invalid_request',
			             'unsupported_grant_type', 'access_denied'):
				reason = error
		xbmc.log('[Diggz Account Manager Simkl] PIN request returned HTTP %d (%s).' %
		         (resp.status_code, reason), xbmc.LOGWARNING)
		if resp.status_code in (400, 401, 403) or reason in ('invalid_client', 'unauthorized_client'):
			message = 'Simkl refused the PIN request. Check that your Client ID supports PIN sign-in.'
		else:
			message = 'Simkl did not issue a PIN. See kodi.log for the response status.'
		control.notification('Simkl', message, icon=simkl_icon)
		return None

	def poll_for_token(self, code_data):
		result = {'token': None, 'expired': False}
		verification_url = code_data['verification_uri']
		qr_link = code_data.get('verification_uri_complete') or verification_url

		def poll_once():
			try:
				resp = requests.post(
					TOKEN_POLL_URL,
					data={'grant_type': DEVICE_GRANT, 'client_id': self.client_id,
					      'device_code': code_data['device_code']},
					timeout=15,
				)
			except requests.RequestException as exc:
				xbmc.log('[Diggz Account Manager Simkl] Device poll failed (%s).' % type(exc).__name__, xbmc.LOGWARNING)
				return 'slow_down'
			try:
				data = resp.json()
			except ValueError:
				data = {}
			if not isinstance(data, dict):
				data = {}
			if resp.ok and data.get('access_token'):
				result['token'] = data
				return True
			error = data.get('error')
			if error == 'authorization_pending':
				return None
			if error == 'slow_down' or resp.status_code == 429:
				return 'slow_down'
			if error == 'expired_token':
				result['expired'] = True
				return 'expired_token'
			reason = error if error in ('access_denied', 'invalid_client', 'unauthorized_client',
			                            'invalid_request', 'unsupported_grant_type') else 'token not issued'
			xbmc.log('[Diggz Account Manager Simkl] Device poll returned HTTP %d (%s).' %
			         (resp.status_code, reason), xbmc.LOGWARNING)
			return False

		approved = device_auth.run(
			'Simkl', qr.qr_image_url(qr_link), verification_url, code_data['user_code'], poll_once,
			interval=max(1, int(code_data.get('interval') or 5)),
			expires_in=max(1, int(code_data.get('expires_in') or 900)),
		)
		return result['token'] if approved else None, result['expired']

	def auth(self):
		try:
			while True:
				code_data = self.get_device_code()
				if not code_data:
					return False
				token, expired = self.poll_for_token(code_data)
				if token:
					break
				if not expired or not control.dialog.yesno('Simkl', 'The code expired. Request a new code?'):
					return False

			bundle = make_bundle(token, self.client_id)
			if not bundle:
				control.dialog.ok('Simkl', 'SIMKL did not return a renewable read/write grant. Existing accounts were not changed.')
				return False
			save_bundle(bundle)
			control.setSetting('simkl.username', '')

			# Fetch username
			try:
				resp = self._user_response()
				info = resp.json()
				username = info.get('user', {}).get('name', '') or info.get('account', {}).get('username', '')
				control.setSetting('simkl.username', username)
			except Exception:
				pass

			control.notification('Simkl', 'Authorization complete!', icon=simkl_icon)
			return True
		except Exception:
			log_utils.error()
			return False

	def revoke(self):
		control.setSetting('simkl.authorization', '')
		control.setSetting('simkl.client.id', '')
		control.setSetting('simkl.token', '')
		control.setSetting('simkl.username', '')
		control.dialog.ok('Simkl', 'Simkl account removed from Diggz Account Manager.')

	def account_info_to_dialog(self):
		try:
			if not control.setting('simkl.token'):
				control.notification('Simkl', 'Not authorized.', icon=simkl_icon)
				return
			resp = self._user_response()
			info = resp.json()
			user = info.get('user', {})
			acct = info.get('account', {})
			username  = user.get('name', 'Unknown')
			joined    = acct.get('created_at', 'Unknown')
			plan_name = acct.get('plan', {}).get('name', 'Free') if isinstance(acct.get('plan'), dict) else acct.get('plan', 'Free')
			items = [
				'Username: %s'  % username,
				'Plan: %s'      % plan_name,
				'Member since: %s' % str(joined)[:10],
			]
			control.selectDialog(items, 'Simkl Account')
		except Exception as exc:
			xbmc.log('[Diggz Account Manager] SIMKL account verification failed (%s)' % type(exc).__name__, xbmc.LOGWARNING)
			control.dialog.ok('SIMKL', 'Stored authorization could not be verified. See the Kodi log for the HTTP status. Existing credentials were retained.')


# Keep the full grant in one setting; the legacy access token is a compatibility mirror.
def make_bundle(data, client, previous=None):
    previous = previous or {}
    scope = data.get('scope') or previous.get('scope') or ''
    refresh = data.get('refresh_token') or previous.get('refresh_token')
    try:
        lifetime = int(data.get('expires_in') or 0)
    except (TypeError, ValueError):
        return None
    if not data.get('access_token') or not refresh or lifetime <= 0 or not {'media:read', 'media:write'}.issubset(scope.split()):
        return None
    return dict(client_id=client, session_id=previous.get('session_id') or uuid.uuid4().hex,
                access_token=data['access_token'], refresh_token=refresh,
                expires_at=time.time()+lifetime, scope=scope)


def read_bundle():
    try:
        a = json.loads(control.setting('simkl.authorization') or '{}')
        if valid_bundle(a) and a['access_token'] == control.setting('simkl.token'):
            return a
    except (ValueError, TypeError, KeyError):
        pass
    return {}


def valid_bundle(a):
    try:
        return bool(a['client_id'] == SIMKL_CLIENT_ID and a['session_id'] and a['access_token'] and a['refresh_token']
                    and float(a['expires_at']) > 0 and {'media:read','media:write'}.issubset(a['scope'].split()))
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def save_bundle(a):
    control.setSetting('simkl.authorization', json.dumps(a))
    control.setSetting('simkl.client.id', a['client_id'])
    control.setSetting('simkl.token', a['access_token'])


def refresh_if_due():
    from reauthorize.modules import tmdbh_compat, vault, server
    from reauthorize.modules.sync import simkl_sync
    a = read_bundle()
    if not a:
        return False  # existing legacy grants continue to work until user reconnects
    previous_token = a['access_token']
    # Other Kodi installations on this device can renew the same session.
    stored = vault.stored()
    try:
        backup = json.loads(stored.get('simkl.authorization') or '{}')
    except (TypeError, ValueError):
        backup = {}
    changed = False
    if valid_bundle(backup) and backup['session_id'] == a['session_id'] and float(backup['expires_at']) > float(a['expires_at']):
        a = backup
        save_bundle(a)
        changed = True
    # Only adopt the exact same authorization session, never a different account.
    other = tmdbh_compat.read_bundle(tmdbh_compat.SIMKL, 'authorization') if tmdbh_compat.installed(tmdbh_compat.SIMKL) else {}
    if valid_bundle(other) and other['session_id'] == a['session_id'] and float(other['expires_at']) > float(a['expires_at']):
        a = other
        save_bundle(a)
        changed = True
    if float(a['expires_at']) <= time.time() + 3600:
        try:
            response = requests.post(TOKEN_POLL_URL, data={'client_id': a['client_id'], 'grant_type': 'refresh_token',
                                     'refresh_token': a['refresh_token']}, timeout=15)
        except requests.RequestException:
            xbmc.log('[Diggz Account Manager] SIMKL renewal network failure; retaining grant.', xbmc.LOGWARNING)
            response = None
        if response is not None and response.ok:
            try:
                renewed = make_bundle(response.json(), a['client_id'], a)
            except (ValueError, TypeError, AttributeError):
                renewed = None
            # Do not replace a newly authorized account while this request was outstanding.
            if renewed and read_bundle() == a:
                save_bundle(renewed)
                changed = True
        elif response is not None and response.status_code in (400, 401, 403):
            xbmc.log('[Diggz Account Manager] SIMKL renewal rejected; reconnect if authorization has expired.', xbmc.LOGWARNING)
    if changed:
        simkl_sync.Auth().simkl_auth(portal_explicit=False, previous_token=previous_token)
        vault.backup()
        server.backup()
    return changed
