# -*- coding: utf-8 -*-
"""
	Account Manager
"""
import xbmc
import requests
from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import qr
from reauthorize.windows import device_auth

# ReAuthorize's own Premiumize app, registered by the user 2026-10-13 at premiumize.me/registerclient
# (a public id: the code sign-in sends no secret). The id inherited from Account Manager,
# 621824280, has been refused since 2026-09-30.
CLIENT_ID = '436240593'
BaseUrl = 'https://www.premiumize.me/api'
account_info_url = '%s/account/info' % BaseUrl
pm_icon = control.joinPath(control.artPath(), 'premiumize.png')

# Kept as the fallback for the day Premiumize refuses the id again (it refused the old one with
# HTTP 400 invalid_client, the same answer a made-up id gets, and this button then crashed with a
# KeyError). A Premiumize API key works as the Bearer token every add-on sends (checked by hand on
# 2026-09-30), so offer to sign in with one. (Signing in inside any add-on with its own
# Premiumize sign-in and letting the importer adopt it also still works.)
NOT_ACCEPTED = ('Premiumize is not accepting ReAuthorize\'s sign-in request right now.[CR][CR]'
				'You can sign in with your Premiumize API key instead. You will find it on premiumize.me '
				'under My Account.[CR][CR]Enter it now?')

class Premiumize:
	name = "Premiumize.me"

	def __init__(self):
		self.token = control.setting('premiumize.token')
		self.headers = {'User-Agent': 'My Accounts for Kodi', 'Authorization': 'Bearer %s' % self.token}
		self.server_notifications = False

	def _get(self, url):
		response = None
		try:
			response = requests.get(url, headers=self.headers, timeout=15).json()
			if 'status' in response:
				if response.get('status') == 'success':
					return response
				if response.get('status') == 'error' and self.server_notifications:
					control.notification(title='default', message=response.get('message'), icon=pm_icon)
		except:
			log_utils.error()
		return response

	def _post(self, url, data=None):
		response = None
		try:
			response = requests.post(url, data, headers=self.headers, timeout=15).json()
			if 'status' in response:
				if response.get('status') == 'success':
					return response
				if response.get('status') == 'error' and self.server_notifications:
					control.notification(title='default', message=response.get('message'), icon=pm_icon)
		except:
			log_utils.error()
		return response

	def auth(self):
		data = {'client_id': CLIENT_ID, 'response_type': 'device_code'}
		try:
			token = requests.post('https://www.premiumize.me/token', data=data, timeout=15).json()
		except Exception:
			log_utils.error()
			control.okDialog(title='Premiumize', message='Could not reach Premiumize. Check your connection and try again.')
			return
		if not isinstance(token, dict) or 'verification_uri' not in token:
			xbmc.log('[ReAuthorize Premiumize] sign-in request refused: %s' % (token.get('error') if isinstance(token, dict) else token), xbmc.LOGWARNING)
			if control.dialog.yesno('Premiumize', NOT_ACCEPTED, nolabel='Not now', yeslabel='Enter key'):
				self.auth_with_api_key()
			return

		def poll_once():
			return self.poll_token(token['device_code'])

		success = device_auth.run('Premiumize', qr.qr_image_url(token['verification_uri']), token['verification_uri'], token['user_code'],
								   poll_once, interval=token['interval'], expires_in=token['expires_in'])
		if success:
			control.notification(title=40057, message=40081, icon=pm_icon) #Authorization complete. Start sync process

	def auth_with_api_key(self):
		"""Sign in with the user's own Premiumize API key. Returns True if it was accepted and stored."""
		import xbmcgui
		key = (control.dialog.input('Premiumize API key', option=getattr(xbmcgui, 'ALPHANUM_HIDE_INPUT', 2)) or '').strip()
		if not key:
			return False
		try:
			info = requests.get(account_info_url, headers={'User-Agent': 'ReAuthorize for Kodi', 'Authorization': 'Bearer %s' % key}, timeout=15).json()
		except Exception:
			log_utils.error()
			control.okDialog(title='Premiumize', message='Could not reach Premiumize. Check your connection and try again.')
			return False
		if not isinstance(info, dict) or info.get('status') != 'success':
			control.okDialog(title='Premiumize', message='Premiumize did not accept that key. Check it on premiumize.me under My Account and try again.')
			return False
		control.setSetting('premiumize.token', key)
		control.setSetting('premiumize.username', str(info.get('customer_id', '')))
		self.token = key
		self.headers = {'User-Agent': 'ReAuthorize for Kodi', 'Authorization': 'Bearer %s' % key}
		control.notification(title=40057, message=40081, icon=pm_icon) #Authorization complete. Start sync process
		return True

	def poll_token(self, device_code):
		data = {'client_id': CLIENT_ID, 'code': device_code, 'grant_type': 'device_code'}
		token = requests.post('https://www.premiumize.me/token', data=data, timeout=15).json()
		if 'error' in token:
			if token['error'] == "access_denied":
				control.okDialog(title='default', message=control.lang(40020))
				return False
			return None
		self.token = token['access_token']
		self.headers = {'User-Agent': 'Account Manager for Kodi', 'Authorization': 'Bearer %s' % self.token}
		control.sleep(500)
		account_info = self.account_info()
		control.setSetting('premiumize.token', token['access_token'])
		control.setSetting('premiumize.username', str(account_info['customer_id']))
		return True

	def revoke(self):
		try:
			control.setSetting('premiumize.token', '')
			control.setSetting('premiumize.username', '')
			control.dialog.ok(control.lang(40057), control.lang(32314))
		except:
			log_utils.error()

	def account_info(self):
		try:
			accountInfo = self._get(account_info_url)
			return accountInfo
		except:
			log_utils.error()
		return None

	def account_info_to_dialog(self):
		from datetime import datetime
		import math
		try:
			accountInfo = self.account_info()
			expires = datetime.fromtimestamp(accountInfo['premium_until'])
			days_remaining = (expires - datetime.today()).days
			expires = expires.strftime("%A, %B %d, %Y")
			points_used = int(math.floor(float(accountInfo['space_used']) / 1073741824.0))
			space_used = float(int(accountInfo['space_used']))/1073741824
			percentage_used = str(round(float(accountInfo['limit_used']) * 100.0, 1))
			items = []
			items += [control.lang(40040) % accountInfo['customer_id']]
			items += [control.lang(40041) % expires]
			items += [control.lang(40042) % days_remaining]
			items += [control.lang(40043) % points_used]
			items += [control.lang(40044) % space_used]
			items += [control.lang(40045) % percentage_used]
			return control.selectDialog(items, 'Premiumize')
		except:
			log_utils.error()
		return
