# -*- coding: utf-8 -*-
"""
	Auth Station - Simkl Authorization
	Device/PIN flow: https://simkl.docs.apiary.io/#reference/authentication/authorize
"""
import requests
import xbmcaddon
import os

from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import qr
from reauthorize.windows import device_auth

joinPath = os.path.join
simkl_icon = joinPath(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'),
                      'resources', 'icons', 'simkl.png')

DEVICE_CODE_URL = 'https://api.simkl.com/oauth/pin'
TOKEN_POLL_URL  = 'https://api.simkl.com/oauth/pin/%s'
USER_URL        = 'https://api.simkl.com/users/settings'

SIMKL_CLIENT_ID     = 'd6e5105efc2bd3d0c6827997b359271316299e6a603cf432b6ff34b9dae1908c'
SIMKL_CLIENT_SECRET = 'e2cf61004b749c197c4f01845e9b83652f5f7c391ec62f4030d8f3d7cedde495'


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
			resp = requests.get(
				DEVICE_CODE_URL,
				params={'client_id': self.client_id, 'redirect': 'urn:ietf:wg:oauth:2.0:oob'},
				timeout=15
			)
			return resp.json()
		except Exception:
			log_utils.error()
			return None

	def poll_for_token(self, user_code, expires_in, interval):
		url = TOKEN_POLL_URL % user_code
		verification_url = 'simkl.com/pin/%s' % user_code.upper()
		qr_url = qr.qr_image_url('https://%s' % verification_url)
		result = {'token': None}

		def poll_once():
			try:
				resp = requests.get(url, params={'client_id': self.client_id}, timeout=15)
				data = resp.json()
				if data.get('result') == 'OK' and data.get('access_token'):
					result['token'] = data['access_token']
					return True
				# result == 'KO' means still pending - keep polling
				return None
			except Exception:
				log_utils.error()
				return None

		device_auth.run('Simkl', qr_url, verification_url, user_code.upper(), poll_once,
						 interval=max(interval, 5), expires_in=expires_in)
		return result['token']

	def auth(self):
		try:
			code_data = self.get_device_code()
			if not code_data or code_data.get('result') != 'OK':
				control.notification('Simkl', 'Could not connect to Simkl. Check your internet connection and try again.', icon=simkl_icon)
				return False

			user_code  = code_data.get('user_code', '')
			expires_in = int(code_data.get('expires_in', 600))
			interval   = int(code_data.get('interval', 5))

			token = self.poll_for_token(user_code, expires_in, interval)
			if not token:
				control.notification('Simkl', 'Authorization cancelled or timed out.', icon=simkl_icon)
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
		control.dialog.ok('Simkl', 'Simkl account removed from ReAuthorize.')

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
