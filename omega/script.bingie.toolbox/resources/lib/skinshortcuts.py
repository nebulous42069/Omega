#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
from resources.lib.utils import kodi_json, log_msg, urlencode, ADDON_ID, getCondVisibility, try_encode, try_decode
import xbmc
import xbmcvfs
import xbmcplugin
import xbmcgui
import xbmcaddon

def set_skinshortcuts_property(property_name="", value="", label=""):
    '''set custom property in skinshortcuts menu editor'''
    if value or label:
        wait_for_skinshortcuts_window()
        xbmc.sleep(250)
        xbmc.executebuiltin("SetProperty(customProperty,%s)" % try_encode(property_name))
        xbmc.executebuiltin("SetProperty(customValue,%s)" % try_encode(value))
        xbmc.executebuiltin("SendClick(404)")
        xbmc.sleep(250)
        xbmc.executebuiltin("SetProperty(customProperty,%s.name)" % try_encode(property_name))
        xbmc.executebuiltin("SetProperty(customValue,%s)" % try_encode(label))
        xbmc.executebuiltin("SendClick(404)")
        xbmc.sleep(250)
        xbmc.executebuiltin("SetProperty(customProperty,%sName)" % try_encode(property_name))
        xbmc.executebuiltin("SetProperty(customValue,%s)" % try_encode(label))
        xbmc.executebuiltin("SendClick(404)")

def wait_for_skinshortcuts_window():
    '''wait untill skinshortcuts is active window (because of any animations that may have been applied)'''
    for i in range(40):
        if not (getCondVisibility(
                "Window.IsActive(DialogSelect.xml) | "
                "Window.IsActive(DialogKeyboard.xml)")):
            break
        else:
            xbmc.sleep(100)
