# -*- coding: utf-8 -*-
"""
	Auth Station
"""

import requests
from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import settings_display

API_key = control.setting('tmdb.api.key')
if API_key == '' or API_key is None:
	API_key = '05a454b451f2f9003fbca293744e4a85'

tmdb_icon = control.joinPath(control.artPath(), 'tmdb.png')


def sync_tmdb_display_values():
	"""Backwards-compatible wrapper around centralized display sync."""
	settings_display.sync_authorized_display_values()

class Auth:
	def __init__(self):
		self.auth_base_link = 'https://api.themoviedb.org/3/authentication'

	def create_session_id(self):
		try:
			import xbmcgui

			username = xbmcgui.Dialog().input(
				'TMDB - Step 1 of 3: Enter your TMDB username',
				defaultt=control.setting('tmdb.username') or '')
			if not username:
				return

			password = xbmcgui.Dialog().input(
				'TMDB - Step 2 of 3: Enter your TMDB password',
				defaultt=control.setting('tmdb.password') or '',
				option=xbmcgui.ALPHANUM_HIDE_INPUT)
			if not password:
				return

			use_own = xbmcgui.Dialog().yesno(
				'TMDB - Step 3 of 3: API Key',
				'Use your own TMDB API key, or use the built-in one included with ReAuthorize?[CR][CR]Most users should choose [B]Use Built-in[/B].',
				nolabel='Use Built-in', yeslabel='Use My Own Key')

			if use_own:
				api_key = xbmcgui.Dialog().input(
					'TMDB - Enter your API key',
					defaultt=control.setting('tmdb.api.key') or '')
				if not api_key:
					return
			else:
				api_key = '05a454b451f2f9003fbca293744e4a85'

			url = self.auth_base_link + '/token/new?api_key=%s' % api_key
			result = requests.get(url).json()
			token = result.get('request_token')

			url2 = self.auth_base_link + '/token/validate_with_login?api_key=%s' % api_key
			result2 = requests.post(url2, data={
				'username': username,
				'password': password,
				'request_token': token,
			}).json()
			if not result2.get('success'):
				msg = result2.get('status_message', 'Invalid username or password.')
				return control.notification(title='ReAuthorize', message='TMDB: %s' % msg, icon=tmdb_icon, time=6000)

			url3 = self.auth_base_link + '/session/new?api_key=%s' % api_key
			result3 = requests.post(url3, data={'request_token': token}).json()
			if result3.get('success') is True:
				session_id = result3.get('session_id')
				if xbmcgui.Dialog().yesno('ReAuthorize', 'TMDB login confirmed for [B]%s[/B]. Authorize now?' % username,
				                          nolabel='Cancel', yeslabel='Authorize'):
					control.setSetting('tmdb.username', username)
					control.setSetting('tmdb.password', password)
					if use_own:
						control.setSetting('tmdb.api.key', api_key)
					control.setSetting('tmdb.session_id', session_id)
					settings_display.sync_authorized_display_values()
					control.notification(title='ReAuthorize', message='TMDB authorized!', icon=tmdb_icon)
				else:
					control.notification(title='ReAuthorize', message='TMDB authorization cancelled.', icon=tmdb_icon)
			else:
				msg = result3.get('status_message', 'Authentication failed.')
				control.notification(title='ReAuthorize', message='TMDB: %s' % msg, icon=tmdb_icon, time=6000)
		except:
			log_utils.error()

	def revoke_session_id(self):
		try:
			if control.setting('tmdb.session_id') == '': return
			url = self.auth_base_link + '/session?api_key=%s' % API_key
			post = {"session_id": "%s" % control.setting('tmdb.session_id')}
			result = requests.delete(url, data=post).json()
			if result.get('success') is True:
				control.setSetting('tmdb.session_id', '')
				settings_display.sync_authorized_display_values()
				control.notification(title='ReAuthorize', message='TMDB session revoked.', icon=tmdb_icon)
			else:
				control.notification(title='ReAuthorize', message='Could not revoke TMDB session.', icon=tmdb_icon)
		except:
			log_utils.error()
