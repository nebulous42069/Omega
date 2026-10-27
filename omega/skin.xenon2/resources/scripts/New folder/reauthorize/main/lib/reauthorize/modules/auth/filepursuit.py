# -*- coding: utf-8 -*-
"""
	Account Manager
"""

import os.path
import xbmc
import xbmcaddon
import xbmcgui
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
addon = xbmcaddon.Addon(addon_id)
joinPath = os.path.join
file_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'filepursuit.png')

class Filepursuit:

        def auth(self):
                api = xbmcgui.Dialog().input('Enter FilePursuit API Key:')
                if not api:
                        return
                control.setSetting('filepursuit.api.key', api)
                control.notification(title='FilePursuit', message='FilePursuit Successfully Authorized', icon=file_icon) #Authorization complete. Start sync process


