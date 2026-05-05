# -*- coding: utf-8 -*-
"""
Control module for client.py
Provides settings and path management for the addon
"""

import os
import xbmc
import xbmcaddon
import xbmcvfs

# Get addon info
ADDON_ID = 'plugin.video.newson'
ADDON = xbmcaddon.Addon(id=ADDON_ID)

# Data path for storing cookies/cache
dataPath = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

def log(msg):
    """Simple logging function"""
    xbmc.log('[%s] %s' % (ADDON_ID, str(msg)), xbmc.LOGDEBUG)

def getSetting(key):
    """Get addon setting"""
    try:
        return ADDON.getSetting(key)
    except:
        return ''

def setSetting(key, value):
    """Set addon setting"""
    try:
        ADDON.setSetting(key, str(value))
        return True
    except:
        return False

def getNumber(key):
    """Get numeric setting"""
    try:
        value = getSetting(key)
        return float(value) if value else 0
    except:
        return 0

def setNumber(key, value):
    """Set numeric setting"""
    try:
        setSetting(key, str(value))
        return True
    except:
        return False

def getBool(key):
    """Get boolean setting"""
    try:
        value = getSetting(key)
        return value.lower() == 'true'
    except:
        return False

def getInt(key):
    """Get integer setting"""
    try:
        value = getSetting(key)
        return int(value) if value else 0
    except:
        return 0

def pathExists(path):
    """Check if path exists"""
    try:
        return xbmcvfs.exists(path)
    except:
        return False
