# -*- coding: utf-8 -*-
"""
	Auth Station - OMDb
"""

import os
import xbmcaddon
import xbmcgui
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
meta_icon = os.path.join(xbmcaddon.Addon(addon_id).getAddonInfo('path'), 'icon.png')

class OMDb:

	def auth(self):
		api = xbmcgui.Dialog().input('Enter OMDb API Key:')
		if api:
			control.setSetting('omdb.api.key', api)
			control.notification(title='OMDb', message='API Key saved', icon=meta_icon)

	def revoke(self):
		control.setSetting('omdb.api.key', '')
		control.notification(title='OMDb', message='API Key removed', icon=meta_icon)
