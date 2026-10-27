# -*- coding: utf-8 -*-
import os.path
import xbmc
import xbmcaddon
import xbmcgui
from libs.common import var
from reauthorize.modules import control

addon_id = 'script.module.reauthorize'
addon = xbmcaddon.Addon(addon_id)
joinPath = os.path.join
dl_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'debridlink.png')

class Debridlink:

    def auth(self):
        api = xbmcgui.Dialog().input('Enter Debrid-Link API Key:')
        if not api:
            control.notification(message='Debrid-Link authorization failed!', icon=dl_icon)
            return
        control.setSetting('debridlink.token', api)
        control.notification(title='Debrid-Link', message='Debrid-Link Credentials saved', icon=dl_icon)

    def revoke(self):
        if not control.confirm_remove('Debrid-Link'):
            return
        control.setSetting('debridlink.token', '')
        control.notification(message='Debrid-Link Authorization Revoked', icon=dl_icon)
