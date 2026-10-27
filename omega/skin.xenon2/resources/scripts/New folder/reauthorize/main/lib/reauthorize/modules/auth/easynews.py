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
easy_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'easynews.png')

class Easynews:

        def auth(self):
                username = xbmcgui.Dialog().input('Enter Easynews Username:')
                password = xbmcgui.Dialog().input('Enter Easynews Password:', option=xbmcgui.ALPHANUM_HIDE_INPUT)
                if username == '' or password == '':
                        control.notification(message='Easynews authorization failed!', icon=easy_icon)
                        return
                control.setSetting('easynews.username', username)
                control.setSetting('easynews.password', password)
                control.notification(title='Easynews', message='Easynews Credentials saved', icon=easy_icon)


