# -*- coding: utf-8 -*-
"""
	Auth Station
"""
import xbmc
import requests
import time
from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import qr
from reauthorize.windows import device_auth
import xbmcaddon
import os
joinPath = os.path.join
trakt_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'trakt.png')

class Trakt():
	def __init__(self):
		self.api_endpoint = 'https://api.trakt.tv/%s'
		self.auth_endpoint = 'https://auth.trakt.tv/%s'
		self.client_id = self.traktClientID()
		self.client_secret = self.traktClientSecret()
		# Kodi hands settings back as strings, and `time.time() > '1790000000'`
		# is a TypeError in Python 3. That comparison sat inside a bare except,
		# so the refresh below never ran once - every token simply died at 90
		# days and the user had to re-authorize by hand. Trakt now treats each
		# re-authorization as a new Community App connection, and free accounts
		# get one, so a token this addon fails to refresh can lock a user out
		# of their own account.
		self.expires_at = self._as_timestamp(control.setting('trakt.expires'))
		self.token = control.setting('trakt.token')

	@staticmethod
	def _as_timestamp(value):
		"""Stored expiry as a float. 0 means 'unknown', which forces a refresh."""
		try:
			return float(value)
		except (TypeError, ValueError):
			return 0.0

	def call(self, path, data=None, with_auth=True, method=None, return_str=False, suppress_error_notification=False):
		try:
			def error_notification(line1, error):
				if suppress_error_notification: return
				return control.notification(title='default', message='%s: %s' % (line1, error), icon=trakt_icon)
			def send_query():
				resp = None
				if with_auth:
					if time.time() > self.expires_at and control.setting('trakt.refresh'):
						try:
							self.refresh_token()
						except Exception as e:
							# Worth a line in the log: a refresh that keeps
							# failing is what ends up costing the user their
							# one free Trakt connection.
							log_utils.log('Trakt token refresh failed: %s' % e,
							              __name__, level=log_utils.LOGWARNING)
					if not self.token:
						return None
					headers['Authorization'] = 'Bearer ' + self.token
				try:
					if data is not None: resp = requests.post(url, json=data, headers=headers, timeout=timeout)
					else: resp = requests.get(url, headers=headers, timeout=timeout)
				except requests.exceptions.RequestException as e:
					error_notification('Trakt Error', str(e))
				except Exception as e:
					error_notification('', str(e))
				return resp
			# OAuth uses Trakt's auth host; account/data calls stay on the API host.
			path = path.lstrip('/')
			endpoint = self.auth_endpoint if path.startswith('oauth/') else self.api_endpoint
			url = endpoint % path
			timeout = 15.0
			headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': self.traktClientID()}
			response = send_query()
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
		try:
			data = {"code": device_codes["device_code"],
					"client_id": self.traktClientID(),
					"client_secret": self.traktClientSecret()}
			verification_url = str(device_codes['verification_url'])
			user_code = str(device_codes['user_code'])
			result = {'response': None}

			def poll_once():
				response = self.call("oauth/device/token", data=data, with_auth=False, suppress_error_notification=True)
				if response and 'access_token' in response:
					result['response'] = response
					return True
				return None

			device_auth.run('Trakt', qr.qr_image_url(verification_url), verification_url, user_code, poll_once,
							 interval=max(device_codes['interval'], 1), expires_in=device_codes['expires_in'])
			return result['response']
		except:
			log_utils.error()

	# ReAuthorize renews the Trakt token well before it runs out. Every add-on holds a
	# copy of the same refresh token and Trakt hands out a new one each time it is used
	# (single-use since 2025), so whoever refreshes first leaves the rest with a dead
	# copy. Renewing early, ourselves, and re-sending the result means no add-on ever
	# reaches a refresh of its own.
	#
	# How early depends on how long Trakt's tokens last. Until 2025 they lasted 90 days
	# and this was a fixed 30 days; now they last 7 (Trakt's docs), so 30 days meant
	# "renew at every single start", racing every add-on and every other Kodi that
	# shares the backup ("Token expired - please re-authorize", 2026-10-01). Renew at
	# half the token's own lifetime instead, as Trakt recommends (based on expires_in).
	DAY = 24 * 60 * 60
	LIFETIME_SETTING = 'trakt.lifetime'
	DEFAULT_LIFETIME = 7 * DAY          # what Trakt issues now, when none was recorded
	MIN_WINDOW, MAX_WINDOW = DAY, 30 * DAY

	@classmethod
	def window(cls):
		"""Seconds before expiry at which ReAuthorize renews: half the token's lifetime, 1 to 30 days."""
		try:
			lifetime = float(control.setting(cls.LIFETIME_SETTING))
		except (TypeError, ValueError):
			lifetime = 0
		if lifetime <= 0:
			lifetime = cls.DEFAULT_LIFETIME
		return max(cls.MIN_WINDOW, min(cls.MAX_WINDOW, lifetime / 2))

	# The newest pair wins (1.4.4, as PunchPlay since 1.4.2). Every Kodi on one device shares one vault (two
	# Kodis on a PC, Kodi and a fork on one Android box). When one of them renews, the others still hold the
	# old pair, whose refresh token Trakt has already spent: their renewal is refused, their add-ons get 401s
	# and ask to sign in again, and a backup made there wrote the dead pair over the good one (the MQ9 build,
	# 2026-10-17). So: a pair in the vault that runs out LATER, with a different refresh token, is taken over
	# without asking Trakt anything, and sent to the add-ons; and a backup never replaces a newer pair with an
	# older one (vault.keep_newer_pairs).
	PAIR = ('trakt.token', 'trakt.refresh', 'trakt.expires')

	def adopt_newer_from_vault(self):
		"""Take over the vault's Trakt pair when it runs out later than this one. Only for a box that is
		signed in: one that is signed out stays signed out. True if it was taken over."""
		mine = control.setting('trakt.refresh')
		if not (mine and control.setting('trakt.token')):
			return False
		try:
			from reauthorize.modules import vault
			stored = vault.stored()
		except Exception:
			return False
		token, refresh, expires = (str(stored.get(key) or '') for key in self.PAIR)
		if not (token and refresh) or refresh == mine:
			return False
		theirs = self._as_timestamp(expires)
		if theirs <= self._as_timestamp(control.setting('trakt.expires')):
			return False
		self.token, self.expires_at = token, theirs
		control.setSetting('trakt.token', token)
		control.setSetting('trakt.refresh', refresh)
		control.setSetting('trakt.expires', str(int(theirs)))
		if stored.get('trakt.username'):
			control.setSetting('trakt.username', str(stored['trakt.username']))
		xbmc.log('[ReAuthorize Trakt] the local backup holds a newer Trakt sign-in than the settings - using that one',
				 xbmc.LOGINFO)
		return True

	def adopt_and_send(self):
		"""adopt_newer_from_vault(), and when it took over, send the pair to every add-on and back it up
		(the server copy may still hold the old one). True if it took over."""
		if self.adopt_newer_from_vault():
			self._resend()
			return True
		return False

	def refresh_if_due(self, window=None, quiet=False):
		"""Renew the token if it runs out within `window` seconds (default: window()). True if renewed."""
		if not (control.setting('trakt.token') and control.setting('trakt.refresh')):
			return False
		self.adopt_and_send()       # never show Trakt a refresh token another Kodi here has already spent
		if self.expires_at - time.time() > (self.window() if window is None else window):
			return False
		return self.refresh_token(quiet=quiet)

	@staticmethod
	def _expiry(token, fallback=7776000):
		"""When a token response says it stops working (Trakt sends created_at + expires_in)."""
		try:
			return float(token['created_at']) + float(token['expires_in'])
		except (KeyError, TypeError, ValueError):
			return time.time() + fallback

	def _store(self, token):
		self.expires_at = self._expiry(token)
		self.token = token['access_token']
		control.setSetting('trakt.token', self.token)
		control.setSetting('trakt.refresh', token['refresh_token'])
		# Whole seconds, never '1791750555.0': add-ons receive this as it is, and POV reads it with int()
		# (its Trakt monitor failed every 30 minutes on the '.0', found on the bench 2026-10-06).
		control.setSetting('trakt.expires', str(int(self.expires_at)))
		self._store_lifetime(token)

	def _store_lifetime(self, token):
		try:
			control.setSetting(self.LIFETIME_SETTING, str(int(float(token['expires_in']))))
		except (KeyError, TypeError, ValueError):
			pass

	def _resend(self):
		"""
		The refresh token just rotated, so every copy of the old one - in the add-ons
		and in both backups - is dead. Replace them now, while the new one is fresh.
		"""
		try:
			# db/trakt_db.py reads the token when it is first imported: without this, a renewal made
			# hours into a Kodi session re-sent the OLD token to Gears (sync_all.refresh_sync_modules).
			from reauthorize.modules.sync_all import refresh_sync_modules
			refresh_sync_modules()
			from reauthorize.modules.sync import trakt_sync
			trakt_sync.Auth().trakt_auth()
		except Exception as e:
			xbmc.log('[ReAuthorize Trakt] could not send the renewed token to the add-ons: %s' % e, xbmc.LOGINFO)
		try:
			from reauthorize.modules import vault, server
			vault.backup()
			server.backup()
		except Exception as e:
			xbmc.log('[ReAuthorize Trakt] could not back up the renewed token: %s' % e, xbmc.LOGINFO)

	def _exchange(self, refresh):
		"""Ask Trakt for a new pair for this refresh token, as ReAuthorize's app. The raw response, or None."""
		data = {
			"client_id": self.traktClientID(),
			"client_secret": self.traktClientSecret(),
			"redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
			"grant_type": "refresh_token",
			"refresh_token": refresh
		}
		return self.call("oauth/token", data=data, with_auth=False, return_str=True)

	# The add-ons that keep the whole Trakt sign-in as one JSON value (see sync/trakt_wipe.py).
	_JSON_SIGNINS = (('plugin.video.themoviedb.helper', 'trakt_token'), ('script.trakt', 'authorization'))
	MAX_CANDIDATES = 12

	@classmethod
	def addon_refresh_tokens(cls):
		"""Every refresh token the installed add-ons hold that differs from ReAuthorize's own."""
		mine = control.setting('trakt.refresh')
		found = []

		def add(value):
			if value and value != mine and value not in found:
				found.append(value)
		try:
			from reauthorize.modules import importer
			for held in importer._collect().values():
				for value in held.get('trakt.refresh', {}):
					add(value)
		except Exception as e:
			xbmc.log('[ReAuthorize Trakt] could not read the add-ons: %s' % e, xbmc.LOGINFO)
		import json
		import xbmcvfs
		for addon_id, setting_id in cls._JSON_SIGNINS:
			try:
				if xbmcvfs.exists('special://home/addons/%s/' % addon_id):
					raw = xbmcaddon.Addon(addon_id).getSetting(setting_id)
					add((json.loads(raw) if raw else {}).get('refresh_token'))
			except Exception:
				pass
		return found[:cls.MAX_CANDIDATES]

	def _recover_from_addons(self):
		"""
		ReAuthorize's refresh token was refused. Try each different one an add-on holds; the first
		Trakt accepts (it must belong to ReAuthorize's app, which every linked add-on uses) becomes
		ReAuthorize's own and is sent to every add-on again. One that belongs to an add-on's own
		app is simply refused, which changes nothing. True if a working copy was adopted.
		"""
		for refresh in self.addon_refresh_tokens():
			response = self._exchange(refresh)
			if response is None or response.status_code != 200:
				continue
			try:
				token = response.json()
			except Exception:
				continue
			if isinstance(token, dict) and 'access_token' in token and 'refresh_token' in token:
				self._store(token)
				xbmc.log('[ReAuthorize Trakt] renewal recovered from a working copy in an add-on - sending it to every add-on', xbmc.LOGINFO)
				self._resend()
				return True
		return False

	def refresh_token(self, quiet=False):
		"""
		Trade the refresh token for a new pair. True on success. On any failure
		nothing stored is overwritten, so a bad network day cannot cost the user
		their login. `quiet` keeps the routine failures (Trakt down, locked) off
		the screen; a refresh token Trakt no longer accepts is always shown,
		because only the user can fix that.
		"""
		if self.adopt_and_send() and self.expires_at > time.time():
			return True             # the vault held a newer pair that still works: nothing to renew
		response = self._exchange(control.setting('trakt.refresh'))
		if response is None:
			xbmc.log('[ReAuthorize Trakt] token renewal: no answer from Trakt', xbmc.LOGINFO)
			return False
		code = response.status_code
		if code >= 500:  # maintenance pages come back as HTML
			log_utils.log('Temporary Trakt Server Problems', __name__, level=log_utils.LOGINFO)
			if not quiet: control.notification(title='Trakt', message='Server error - try again later.')
			return False
		if code == 423:
			log_utils.log('Locked User Account - Contact Trakt Support', __name__, level=log_utils.LOGWARNING)
			if not quiet: control.notification(title='Trakt', message='Your Trakt account is locked. Contact Trakt support.')
			return False
		try:
			token = response.json()
		except Exception:
			log_utils.error()
			return False
		if not isinstance(token, dict) or code != 200 or 'access_token' not in token or 'refresh_token' not in token:
			if isinstance(token, dict) and token.get('error') == 'invalid_grant':
				# Usually not a dead account: an add-on (or another Kodi sharing this backup)
				# renewed first and holds the live pair. Take it from there before asking.
				if self._recover_from_addons():
					return True
				xbmc.log('[ReAuthorize Trakt] token renewal refused (invalid_grant) and no add-on holds a working copy', xbmc.LOGWARNING)
				control.notification(title='Trakt', message='Token expired - please re-authorize your Trakt account.')
			else:
				xbmc.log('[ReAuthorize Trakt] token renewal refused (HTTP %s)' % code, xbmc.LOGINFO)
			return False

		self._store(token)
		xbmc.log('[ReAuthorize Trakt] token renewed - sending it to every add-on', xbmc.LOGINFO)
		self._resend()
		return True

	def auth(self):
		try:
			code = self.get_device_code()
			token = self.get_device_token(code)
			if token:
				expires_at = self._expiry(token)
				control.setSetting('trakt.expires', str(int(expires_at)))
				control.setSetting('trakt.token', token["access_token"])
				control.setSetting('trakt.refresh', token["refresh_token"])
				self._store_lifetime(token)
				self.expires_at = expires_at
				self.token = token["access_token"]
				control.sleep(1000)
				try:
					user = self.call("users/me", with_auth=True)
					control.setSetting('trakt.username', str(user['username']))
				except: pass
				control.notification(message=40074, icon=trakt_icon)
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
	def sign_out_everywhere(self):
		"""
		The Trakt tab's Revoke (1.3.8). Until then that button only took Trakt out of the add-ons and
		left ReAuthorize itself signed in, with Authorize hidden: no way to sign in again (found on the
		bench, 2026-10-04, with a sign-in whose refresh token was dead). End it at Trakt, clear
		ReAuthorize's copy, then blank it in every add-on. Returns how many add-on values were cleared.
		"""
		self.revoke()
		control.setSetting(self.LIFETIME_SETTING, '')
		control.setSetting('sync.tk.service', '')
		control.setSetting('trakt.username.display', '')   # the status line; else it waits for the next start
		try:
			from reauthorize.modules.sync import trakt_wipe
			return trakt_wipe.wipe_addons()
		except Exception as e:
			xbmc.log('[ReAuthorize Trakt] could not clear Trakt from the add-ons: %s' % e, xbmc.LOGWARNING)
			return 0

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
		return '12ab9767aa51f805d963553442c3784b634075ef2868d3e6552c2073fecced5b'

	def traktClientSecret(self):
		return 'dcaa2635dda30ebb76bce44ce00db8842210b1f0271d70d8f3dcdeca8302022e'
