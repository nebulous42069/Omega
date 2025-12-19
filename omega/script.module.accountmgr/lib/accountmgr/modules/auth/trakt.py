# -*- coding: utf-8 -*-
"""
	Account Manager
"""
import xbmc
import requests
import time
from accountmgr.modules import control
from accountmgr.modules import log_utils
import xbmcaddon
import os
joinPath = os.path.join
trakt_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'trakt.png')

class Trakt():
	def __init__(self):
		self.api_endpoint = 'https://api.trakt.tv/%s'
		self.client_id = self.traktClientID()
		self.client_secret = self.traktClientSecret()
		# trakt.expires is stored as a string; make it numeric so refresh checks don't silently fail
		try:
			self.expires_at = float(control.setting('trakt.expires') or 0)
		except:
			self.expires_at = 0
		self.token = control.setting('trakt.token')

	def call(self, path, data=None, with_auth=True, method=None, return_str=False, suppress_error_notification=False):
		try:
			def error_notification(line1, error):
				if suppress_error_notification: return
				return control.notification(title='default', message='%s: %s' % (line1, error), icon=trakt_icon)

			def send_query():
				resp = None
				if with_auth:
					try:
						if self.token and time.time() > float(self.expires_at or 0):
							self.refresh_token()
					except:
						pass
					if self.token:
						headers['Authorization'] = 'Bearer ' + self.token
				try:
					if data is not None:
						resp = requests.post(self.api_endpoint % path, json=data, headers=headers, timeout=timeout)
					else:
						resp = requests.get(self.api_endpoint % path, headers=headers, timeout=timeout)
				except requests.exceptions.RequestException as e:
					error_notification('Trakt Error', str(e))
				except Exception as e:
					error_notification('', str(e))
				return resp

			timeout = 15.0
			headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': self.traktClientID()}
			response = send_query()
			if not response:
				return response if return_str else None
			response.encoding = 'utf-8'
			if return_str: return response
			try: result = response.json()
			except: result = None
			return result
		except:
			log_utils.error()

	def get_device_code(self):
		data = {'client_id': self.traktClientID()}
		return self.call("oauth/device/code", data=data, with_auth=False)

	def get_device_token(self, device_codes):
		"""Poll Trakt's device-token endpoint until we get an access_token or time out."""
		try:
			data = {"code": device_codes.get("device_code"),
					"client_id": self.traktClientID(),
					"client_secret": self.traktClientSecret()}
			start = time.time()
			expires_in = int(device_codes.get('expires_in', 0) or 0)
			interval = int(device_codes.get('interval', 5) or 5)
			verification_url = control.lang(32513) % str(device_codes.get('verification_url'))
			user_code = control.lang(32514) % str(device_codes.get('user_code'))
			control.progressDialog.create(control.lang(32073), control.progress_line % (verification_url, user_code, ''))
			try:
				while not control.progressDialog.iscanceled():
					time_passed = time.time() - start
					if expires_in and time_passed >= expires_in:
						break
					progress = int(100 * time_passed / float(expires_in)) if expires_in else 0
					try: control.progressDialog.update(progress)
					except: pass

					response = self.call("oauth/device/token", data=data, with_auth=False, suppress_error_notification=True)

					if isinstance(response, dict):
						if response.get('access_token'):
							return response
						err = response.get('error')
						if err == 'slow_down':
							interval = max(interval + 5, 5)
							control.sleep(interval * 1000)
							continue
						if err in ('authorization_pending', 'invalid_request'):
							control.sleep(max(interval, 1) * 1000)
							continue
						if err in ('access_denied', 'expired_token'):
							break

					control.sleep(max(interval, 1) * 1000)
			finally:
				control.progressDialog.close()
			return None
		except:
			log_utils.error()

	def refresh_token(self):
		traktToken = None
		traktRefresh = None

		old_token = control.setting('trakt.token') or ''
		old_refresh = control.setting('trakt.refresh') or ''

		data = {
			"client_id": self.traktClientID(),
			"client_secret": self.traktClientSecret(),
			"redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
			"grant_type": "refresh_token",
			"refresh_token": control.setting('trakt.refresh')
		}

		response = self.call("oauth/token", data=data, with_auth=False, return_str=True)
		try: status = int(getattr(response, 'status_code', 0) or 0)
		except: status = 0
		try: resp_text = (getattr(response, 'text', '') or '').lower()
		except: resp_text = ''

		# Maintenance / gateway errors can come back as HTML or empty.
		if status >= 500 or ('<html' in resp_text) or not response:
			log_utils.log('Temporary Trakt Server Problems', level=log_utils.LOGNOTICE)
			control.notification(title=32315, message=33676)
			return False
		elif status == 423:
			log_utils.log('Locked User Account - Contact Trakt Support', level=log_utils.LOGWARNING)
			control.notification(title=32315, message=33675)
			return False
		elif status in (401, 405):
			control.notification(title=32315, message=33677)
			return False

		try: payload = response.json() if response else {}
		except: payload = {}

		if isinstance(payload, dict) and payload.get('error') == 'invalid_grant':
			log_utils.log('Please Re-Authorize your Trakt Account: %s' % payload.get('error'), __name__, level=log_utils.LOGWARNING)
			control.notification(title=32315, message=33677)
			return False

		traktToken = payload.get("access_token") if isinstance(payload, dict) else None
		traktRefresh = payload.get("refresh_token") if isinstance(payload, dict) else None

		# Use Trakt-provided expiry fields instead of hardcoding 24 hours
		try: created_at = int(payload.get('created_at', time.time()))
		except: created_at = int(time.time())
		try: expires_in = int(payload.get('expires_in', 86400))
		except: expires_in = 86400
		expires_at = created_at + expires_in

		if traktToken:
			control.setSetting('trakt.token', traktToken or '')
			control.setSetting('trakt.refresh', traktRefresh or '')
			control.setSetting('trakt.expires', str(expires_at))
			self.token = traktToken
			self.expires_at = expires_at

			# After refresh, resync tokens into supported addons (guard against recursion)
			if (traktToken != old_token) or (traktRefresh and traktRefresh != old_refresh):
				try:
					if control.window.getProperty('accountmgr.trakt.resync') != 'true':
						control.window.setProperty('accountmgr.trakt.resync', 'true')
						try:
							from accountmgr.modules.sync import trakt_sync
							trakt_sync.Auth().trakt_auth()
						finally:
							control.window.clearProperty('accountmgr.trakt.resync')
				except:
					log_utils.error()
		return True

	def auth(self):
		try:
			code = self.get_device_code()
			token = self.get_device_token(code)
			if token:
				# Use Trakt-provided expiry fields instead of hardcoding 24 hours
				try: created_at = int(token.get('created_at', time.time()))
				except: created_at = int(time.time())
				try: expires_in = int(token.get('expires_in', 86400))
				except: expires_in = 86400
				expires_at = created_at + expires_in

				control.setSetting('trakt.expires', str(expires_at))
				control.setSetting('trakt.token', token.get("access_token", ""))
				control.setSetting('trakt.refresh', token.get("refresh_token", ""))
				self.expires_at = expires_at
				self.token = token.get("access_token", "")
				control.sleep(1000)
				try:
					user = self.call("users/me", with_auth=True)
					control.setSetting('trakt.username', str(user['username']))
				except: pass
				control.notification_trakt(message=40074, icon=trakt_icon) #Authorization complete. Start sync process
				return True
			control.notification(message=40075, icon=trakt_icon)
			return False
		except:
			log_utils.error()

	def revoke(self):
		data = {"token": control.setting('trakt.token')}
		try: self.call("oauth/revoke", data=data, with_auth=False)
		except: pass
		control.setSetting('trakt.username', '')
		control.setSetting('trakt.expires', '')
		control.setSetting('trakt.token', '')
		control.setSetting('trakt.refresh', '')
		control.dialog.ok(control.lang(32315), control.lang(32314))

	def account_info(self):
		response = self.call("users/me", with_auth=True)
		return response

	def extended_account_info(self):
		account_info = self.call("users/settings", with_auth=True)
		stats = self.call("users/%s/stats" % account_info['user']['ids']['slug'], with_auth=True)
		return account_info, stats

	def account_info_to_dialog(self):
		from datetime import datetime, timedelta
		try:
			account_info, stats = self.extended_account_info()
			username = account_info['user']['username']
			timezone = account_info['account']['timezone']
			joined = control.jsondate_to_datetime(account_info['user']['joined_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
			private = account_info['user']['private']
			vip = account_info['user']['vip']
			if vip: vip = '%s Years' % str(account_info['user']['vip_years'])
			total_given_ratings = stats['ratings']['total']
			movies_collected = stats['movies']['collected']
			movies_watched = stats['movies']['watched']
			movie_minutes = stats['movies']['minutes']
			if movie_minutes == 0: movies_watched_minutes = ['0 days', '0:00:00']
			elif movie_minutes < 1440: movies_watched_minutes = ['0 days', "{:0>8}".format(str(timedelta(minutes=movie_minutes)))]
			else: movies_watched_minutes = ("{:0>8}".format(str(timedelta(minutes=movie_minutes)))).split(', ')
			movies_watched_minutes = control.lang(40071) % (movies_watched_minutes[0], movies_watched_minutes[1].split(':')[0], movies_watched_minutes[1].split(':')[1])
			shows_collected = stats['shows']['collected']
			shows_watched = stats['shows']['watched']
			episodes_watched = stats['episodes']['watched']
			episode_minutes = stats['episodes']['minutes']
			if episode_minutes == 0: episodes_watched_minutes = ['0 days', '0:00:00']
			elif episode_minutes < 1440: episodes_watched_minutes = ['0 days', "{:0>8}".format(str(timedelta(minutes=episode_minutes)))]
			else: episodes_watched_minutes = ("{:0>8}".format(str(timedelta(minutes=episode_minutes)))).split(', ')
			episodes_watched_minutes = control.lang(40071) % (episodes_watched_minutes[0], episodes_watched_minutes[1].split(':')[0], episodes_watched_minutes[1].split(':')[1])
			heading = control.lang(32315)
			items = []
			items += [control.lang(40036) % username]
			items += [control.lang(40063) % timezone]
			items += [control.lang(40064) % joined]
			items += [control.lang(40065) % private]
			items += [control.lang(40066) % vip]
			items += [control.lang(40067) % str(total_given_ratings)]
			items += [control.lang(40068) % (movies_collected, movies_watched, movies_watched_minutes)]
			items += [control.lang(40069) % (shows_collected, shows_watched)]
			items += [control.lang(40070) % (episodes_watched, episodes_watched_minutes)]
			return control.selectDialog(items, heading)
		except:
			log_utils.error()
			return

	def traktClientID(self):
		traktId = '4a479b95c8224999eef8d418cfe6c7a4389e2837441672c48c9c8168ea42a407'
		if control.setting('trakt.client.id') != '' and control.setting('traktuserkey.enabled') == 'true':
			traktId = control.setting('trakt.client.id')
		if control.setting('dev.client.id') != '' and control.setting('devuserkey.enabled') == 'true':
			traktId = control.setting('dev.client.id')
		return traktId

	def traktClientSecret(self):
		traktSecret = '89d8f8f71b312985a9e1f91e9eb426e23050102734bb1fa36ec76cdc74452ab6'
		if control.setting('trakt.client.secret') != '' and control.setting('traktuserkey.enabled') == 'true':
			traktSecret = control.setting('trakt.client.secret')
		if control.setting('dev.client.secret') != '' and control.setting('devuserkey.enabled') == 'true':
			traktSecret = control.setting('dev.client.secret')
		return traktSecret
