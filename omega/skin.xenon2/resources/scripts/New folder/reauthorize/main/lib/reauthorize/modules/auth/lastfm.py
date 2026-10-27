# -*- coding: utf-8 -*-
"""
	ReAuthorize - Last.fm sign-in (1.4.1: username + password)

	The Last.fm Scrobbler (service.scrobbler.lastfm, the one in Kodi's repo) signs itself in with
	the user's Last.fm username and password and its own built-in key, and scrobbles only when it
	has both (sync/lastfm_sync.py). So ReAuthorize asks for exactly those: no Last.fm API key or
	developer account for anyone. Until 1.4.1 the button needed the user's OWN API key and secret
	and a browser approval, and the Scrobbler still had no password after a build install.

	ReAuthorize has no key of its own to check the password with, so it hands the pair to the
	Scrobbler and watches for the Scrobbler's session: Last.fm's own error, if any, is shown by the
	Scrobbler.
"""
import os

import xbmcaddon
import xbmcgui

from reauthorize.modules import control, log_utils

lastfm_icon = os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons', 'lastfm.png')
OLD_KEYS = ('lastfm.api.key', 'lastfm.api.secret', 'lastfm.session.key')    # the sign-in before 1.4.1


class LastFM():

	def auth(self):
		try:
			from reauthorize.modules.sync import lastfm_sync
			if lastfm_sync.pick_up_from_scrobbler():
				control.setSetting('sync.lastfm.service', 'true')
				control.notification('Last.fm', 'Signed in as %s (from the Last.fm Scrobbler).' % control.setting('lastfm.username'), icon=lastfm_icon)
				return True
			dialog = xbmcgui.Dialog()
			user = (dialog.input('Last.fm username', defaultt=control.setting('lastfm.username')) or '').strip()
			if not user:
				return False
			pwd = dialog.input('Last.fm password', option=getattr(xbmcgui, 'ALPHANUM_HIDE_INPUT', 2)) or ''
			if not pwd:
				return False
			control.setSetting('lastfm.username', user)
			control.setSetting('lastfm.password', pwd)
			for key in OLD_KEYS:
				control.setSetting(key, '')
			control.setSetting('sync.lastfm.service', 'true')
			if not lastfm_sync.installed():
				control.notification('Last.fm', 'Saved. Install the Last.fm Scrobbler from Kodi\'s add-on repo to scrobble.', icon=lastfm_icon)
				return True
			lastfm_sync.Auth().lastfm_auth()
			if lastfm_sync.wait_for_session(15):
				control.notification('Last.fm', 'Signed in as %s.' % user, icon=lastfm_icon)
			else:
				control.notification('Last.fm', 'Saved. The Last.fm Scrobbler signs in with it.', icon=lastfm_icon, time=6000)
			return True
		except Exception:
			log_utils.error()
			return False

	def revoke(self):
		user, pwd = control.setting('lastfm.username'), control.setting('lastfm.password')
		session = control.setting('lastfm.session.key')
		for key in OLD_KEYS + ('lastfm.username', 'lastfm.password'):
			control.setSetting(key, '')
		control.setSetting('sync.lastfm.service', 'false')
		if pwd:
			from reauthorize.modules.sync import lastfm_sync
			lastfm_sync.clear_scrobbler(user, pwd)       # only when it holds this same sign-in
		if session and not pwd:
			from reauthorize.modules.sync import lastfm_sync
			if lastfm_sync.scrobbler_session() == session:
				lastfm_sync.clear_scrobbler()
		control.dialog.ok('Last.fm', 'Signed out of Last.fm.')

	def account_info_to_dialog(self):
		try:
			from reauthorize.modules.sync import lastfm_sync
			user = control.setting('lastfm.username')
			if not (control.setting('lastfm.password') or control.setting('lastfm.session.key')):
				control.notification('Last.fm', 'Not signed in.', icon=lastfm_icon)
				return
			if not lastfm_sync.installed():
				state = 'Last.fm Scrobbler not installed'
			elif lastfm_sync.scrobbler_session():
				state = 'Last.fm Scrobbler: signed in'
			else:
				state = 'Last.fm Scrobbler: not signed in yet'
			control.selectDialog(['Username: %s' % (user or 'Unknown'), state], 'Last.fm Account')
		except Exception:
			log_utils.error()
