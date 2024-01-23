#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Various helper methods'''

import xbmcgui
import xbmc
import sys
import urllib
import traceback
from traceback import format_exc

ADDON_ID = "script.skin.helper.backgrounds"


def log_msg(msg, loglevel=xbmc.LOGINFO):
    """log message to kodi logfile"""
    if sys.version_info.major < 3:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
    if loglevel == xbmc.LOGDEBUG and FORCE_DEBUG_LOG:
        loglevel = xbmc.LOGINFO
    xbmc.log("Skin Helper Backgrounds --> %s" % msg, level=loglevel)

def log_exception(modulename, exceptiondetails):
    '''helper to properly log an exception'''
    if sys.version_info.major == 3:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        log_msg("Exception details: Type: %s Value: %s Traceback: %s" % (exc_type.__name__, exc_value, ''.join(line for line in lines)), xbmc.LOGWARNING)
    else:
        log_msg(format_exc(sys.exc_info()), xbmc.LOGWARNING)
    log_msg("Exception in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGERROR)

def try_encode(text, encoding="utf-8"):
    """helper to encode a string to utf-8"""
    try:
        if sys.version_info.major == 3:
            return text
        else:
            return text.encode(encoding, "ignore")
    except Exception:
        return text
        
def urlencode(text):
    '''urlencode a string'''
    if sys.version_info.major == 3:
        blah = urllib.parse.urlencode({'blahblahblah': try_encode(text)})
    else:
        blah = urllib.urlencode({'blahblahblah': try_encode(text)})
    blah = blah[13:]
    return blah

def get_content_path(lib_path):
    '''helper to get the real browsable path'''
    if "$INFO" in lib_path and "reload=" not in lib_path:
        lib_path = lib_path.replace("$INFO[Window(Home).Property(", "")
        lib_path = lib_path.replace(")]", "")
        win = xbmcgui.Window(10000)
        lib_path = win.getProperty(lib_path)
        del win
    if "activate" in lib_path.lower():
        if "activatewindow(musiclibrary," in lib_path.lower():
            lib_path = lib_path.lower().replace("activatewindow(musiclibrary,", "musicdb://")
            lib_path = lib_path.replace(",return", "/")
            lib_path = lib_path.replace(", return", "/")
        else:
            lib_path = lib_path.lower().replace(",return", "")
            lib_path = lib_path.lower().replace(", return", "")
            if ", " in lib_path:
                lib_path = lib_path.split(", ", 1)[1]
            elif " , " in lib_path:
                lib_path = lib_path.split(" , ", 1)[1]
            elif " ," in lib_path:
                lib_path = lib_path.split(", ", 1)[1]
            elif "," in lib_path:
                lib_path = lib_path.split(",", 1)[1]
        lib_path = lib_path.replace(")", "")
        lib_path = lib_path.replace("\"", "")
        lib_path = lib_path.replace("musicdb://special://", "special://")
        lib_path = lib_path.replace("videodb://special://", "special://")
    if "&reload=" in lib_path:
        lib_path = lib_path.split("&reload=")[0]
    return lib_path
