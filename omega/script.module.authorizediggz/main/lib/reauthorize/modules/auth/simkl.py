# -*- coding: utf-8 -*-
"""
	Auth Station - Simkl Authorization
	OAuth V2 device authorization for Kodi.
"""
import requests
import xbmc
import xbmcaddon
import os

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
			'simkl-api-key': self.client_id,
			'Authorization': 'Bearer %s' % control.setting('simkl.token'),
		}

	def get_device_code(self):
		try:
			resp = requests.post(
				DEVICE_CODE_URL,
				data={'client_id': self.client_id},
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
				result['token'] = data['access_token']
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

			control.setSetting('simkl.token', token)
			control.setSetting('simkl.client.id', SIMKL_CLIENT_ID)

			# Fetch username
			try:
				resp = requests.get(USER_URL, headers=self._headers(), timeout=15)
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
		control.setSetting('simkl.token', '')
		control.setSetting('simkl.username', '')
		control.dialog.ok('Simkl', 'Simkl account removed from Diggz Account Manager.')

	def account_info_to_dialog(self):
		try:
			if not control.setting('simkl.token'):
				control.notification('Simkl', 'Not authorized.', icon=simkl_icon)
				return
			resp = requests.get(USER_URL, headers=self._headers(), timeout=15)
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
		except Exception:
			log_utils.error()
