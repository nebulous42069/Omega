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
ls_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'linksnappy.png')

class Linksnappy:

    def auth(self):
        username = xbmcgui.Dialog().input('Enter Linksnappy Username:')
        if not username:
            control.notification(message='Linksnappy authorization failed!', icon=ls_icon)
            return
        password = xbmcgui.Dialog().input('Enter Linksnappy Password:', option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            control.notification(message='Linksnappy authorization failed!', icon=ls_icon)
            return
        control.setSetting('linksnappy.username', username)
        control.setSetting('linksnappy.password', password)
        control.notification(title='Linksnappy', message='Linksnappy Credentials saved', icon=ls_icon)

    def revoke(self):
        if not control.confirm_remove('Linksnappy'):
            return
        control.setSetting('linksnappy.username', '')
        control.setSetting('linksnappy.password', '')
        control.notification(message='Linksnappy Authorization Revoked', icon=ls_icon)
