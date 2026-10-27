# -*- coding: utf-8 -*-
"""
	Account Manager
"""

import os.path
import xbmc
import xbmcaddon
import xbmcgui
from libs.common import var
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
addon = xbmcaddon.Addon(addon_id)
joinPath = os.path.join
apikey = control.setting('offcloud.token')
offcloud_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'offcloud.png')

class Offcloud:

        def auth(self):
                api = xbmcgui.Dialog().input('Enter OffCloud API Key:')
                if api == '':
                        control.notification(message='OffCloud authorization failed!', icon=offcloud_icon)
                        return
                control.setSetting('offcloud.token', api)
                control.notification(title='OffCloud', message='OffCloud Credentials saved', icon=offcloud_icon)

        def revoke(self):
                if not control.confirm_remove('OffCloud'):
                        return
                control.setSetting('offcloud.token', '')
                #Clear legacy email/password fields from older versions
                control.setSetting('offcloud.user', '')
                control.setSetting('offcloud.pass', '')
                control.setSetting('offcloud.userid', '')
                control.notification(message="OffCloud Authorization Revoked", icon=offcloud_icon)
