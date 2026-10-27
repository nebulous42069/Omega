# -*- coding: utf-8 -*-
"""
	Account Manager
"""

import requests
from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import qr
from reauthorize.windows import device_auth

base_url = 'https://api.alldebrid.com/v4/'
user_agent = 'Account%20Manager%20for%20Kodi'
ad_icon = control.joinPath(control.artPath(), 'alldebrid.png')

class AllDebrid:
	name = "AllDebrid"

	def __init__(self):
		self.token = control.setting('alldebrid.token')
		self.timeout = 15.0

	def _get(self, url, url_append=''):
		result = None
		try:
			if self.token == '': return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token) + url_append
			result = requests.get(url, timeout=self.timeout).json()
			if result.get('status') == 'success':
				if 'data' in result: result = result['data']
		except requests.exceptions.ConnectionError:
			control.notification(title='default', message=40073, icon=ad_icon)
		except BaseException:
			log_utils.error()
		return result

	def auth(self):
		self.token = ''
		url = base_url + 'pin/get?agent=%s' % user_agent
		response = requests.get(url, timeout=self.timeout).json()
		response = response['data']
		pin = response['pin']
		user_url = response.get('user_url') or ('https://alldebrid.com/pin/?pin=%s' % pin)
		check_url = response.get('check_url')
		expires_in = int(response.get('expires_in', 600))

		def poll_once():
			try:
				data = requests.get(check_url, timeout=self.timeout).json()['data']
			except Exception:
				log_utils.error()
				return None
			if 'error' in data:
				control.notification(title='default', message=40021, icon=ad_icon)
				return False
			if data.get('activated'):
				try:
					self.token = str(data['apikey'])
					control.setSetting('alldebrid.token', self.token)
					return True
				except Exception:
					control.notification(title='default', message=40021, icon=ad_icon)
					return False
			return None

		device_auth.run('AllDebrid', qr.qr_image_url(user_url), 'https://alldebrid.com/pin/', pin, poll_once,
						 interval=5, expires_in=expires_in)
		if not self.token: return
		control.sleep(2000)
		account_info = self.account_info()
		control.setSetting('alldebrid.username', str(account_info['user']['username']))
		control.notification(title=40059, message=40081, icon=ad_icon)

	def revoke(self):
		try:
			control.setSetting('alldebrid.username', '')
			control.setSetting('alldebrid.token', '')
			control.dialog.ok(control.lang(40059), control.lang(32314))
		except:
			log_utils.error()

	def account_info(self):
		response = self._get('user')
		return response

	def account_info_to_dialog(self):
		from datetime import datetime
		try:
			account_info = self.account_info()['user']
			username = account_info['username']
			email = account_info['email']
			status = 'Premium' if account_info['isPremium'] else 'Not Active'
			expires = datetime.fromtimestamp(account_info['premiumUntil'])
			days_remaining = (expires - datetime.today()).days
			heading = control.lang(40059).upper()
			items = []
			items += [control.lang(40036) % username]
			items += [control.lang(40035) % email]
			items += [control.lang(40037) % status]
			items += [control.lang(40041) % expires]
			items += [control.lang(40042) % days_remaining]
			return control.selectDialog(items, 'All Debrid')
		except:
			log_utils.error()
		return
