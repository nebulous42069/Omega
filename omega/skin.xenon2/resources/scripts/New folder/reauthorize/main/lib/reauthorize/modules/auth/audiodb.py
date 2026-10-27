# -*- coding: utf-8 -*-
"""
	Auth Station - TheAudioDB
"""

import os
import xbmcaddon
import xbmcgui
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
meta_icon = os.path.join(xbmcaddon.Addon(addon_id).getAddonInfo('path'), 'icon.png')

class AudioDB:

	def auth(self):
		api = xbmcgui.Dialog().input('Enter TheAudioDB API Key:')
		if api:
			control.setSetting('audiodb.api.key', api)
			control.notification(title='TheAudioDB', message='API Key saved', icon=meta_icon)

	def revoke(self):
		control.setSetting('audiodb.api.key', '')
		control.notification(title='TheAudioDB', message='API Key removed', icon=meta_icon)
