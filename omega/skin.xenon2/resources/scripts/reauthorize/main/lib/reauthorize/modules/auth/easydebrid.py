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
api_key = control.setting('easydebrid.token')
easyd_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'easydebrid.png')

class Easydebrid:

        def auth(self):
                api = xbmcgui.Dialog().input('Enter Easy Debrid API Key:')
                if api == '':
                        control.notification(message='Easy Debrid authorization failed!', icon=easyd_icon)
                        return
                control.setSetting('easydebrid.token', api)
                control.setSetting('easydebrid.acct_id', api)
                control.notification(title='Easy Debrid', message='Easy Debrid Credentials saved', icon=easyd_icon)

        def revoke(self):
                if not control.confirm_remove('Easy Debrid'):
                        return
                control.setSetting('easydebrid.token', '')
                control.setSetting('easydebrid.acct_id', '')
                control.notification(message="Easy Debrid Authorization Revoked", icon=easyd_icon)


