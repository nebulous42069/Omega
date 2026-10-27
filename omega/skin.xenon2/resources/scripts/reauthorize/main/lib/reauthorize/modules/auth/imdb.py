# -*- coding: utf-8 -*-
"""
	Auth Station - IMDb

	Feeds nine addons' own "imdb.user" setting (meta_sync.py). Confirmed against
	the real source of four of them (Homelander, Quicksilver, Moria, Absolution,
	all sharing the same code): it is the numeric ID from the user's own IMDb
	profile URL - imdb.com/user/ur12345678/ - used to pull that person's public
	Watchlist and Lists. Not a login. The 'ur' prefix is optional; each addon
	strips it itself (`.replace('ur', '')`) before rebuilding the URL. The Crew's
	own settings.xml declares the same field, but its code never reads it.
"""

import os
import xbmcaddon
import xbmcgui
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
meta_icon = os.path.join(xbmcaddon.Addon(addon_id).getAddonInfo('path'), 'icon.png')

class IMDb:

	def auth(self):
		api = xbmcgui.Dialog().input(
			"Enter your IMDb Profile ID - the numbers in imdb.com/user/urXXXXXXXX (the 'ur' is optional):")
		if api:
			control.setSetting('imdb.user', api)
			control.notification(title='IMDb', message='Profile ID saved', icon=meta_icon)

	def revoke(self):
		control.setSetting('imdb.user', '')
		control.notification(title='IMDb', message='Profile ID removed', icon=meta_icon)
