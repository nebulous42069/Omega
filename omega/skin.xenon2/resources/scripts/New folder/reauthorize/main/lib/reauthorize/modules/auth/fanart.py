# -*- coding: utf-8 -*-
"""
	Auth Station - Fanart.TV
"""

import os
import xbmcaddon
import xbmcgui
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
meta_icon = os.path.join(xbmcaddon.Addon(addon_id).getAddonInfo('path'), 'icon.png')

class Fanart:

	def auth(self):
		api = xbmcgui.Dialog().input('Enter Fanart.TV Personal API Key:')
		if api:
			control.setSetting('fanart.tv.api.key', api)
			control.notification(title='Fanart.TV', message='API Key saved', icon=meta_icon)

	def revoke(self):
		control.setSetting('fanart.tv.api.key', '')
		control.notification(title='Fanart.TV', message='API Key removed', icon=meta_icon)
