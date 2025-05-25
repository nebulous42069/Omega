# -*- coding: UTF-8 -*-

import os
import time
import webbrowser
from kodi_six import xbmc, xbmcgui


def menuoptions():
    dialog = xbmcgui.Dialog()
    funcs = (
        function1,
        function2,
        function3,
        function4,
        function5,
        function6,
        function7,
        function8,        
    )
    call = dialog.select('[B]Diggz Website Browser[/B]', [
            '[B]The_TV_App[/B]',
            '[B]Daddy Live[/B]',
            '[B]Xumo Live[/B]',
            '[B]TV 24/7[/B]',
            '[B]Time4Tv[/B]',         
        ]
    )
    # dialog.selectreturns
    #   0 -> escape pressed
    #   1 -> first item
    #   2 -> second item
    if call:
        # esc is not pressed
        if call < 0:
            return
        func = funcs[call-8] # Number of functions (function10)
        return func()
    else:
        func = funcs[call]
        return func()
    return


def platform():
    if xbmc.getCondVisibility('system.platform.android'):
        return 'android'
    elif xbmc.getCondVisibility('system.platform.linux'):
        return 'linux'
    elif xbmc.getCondVisibility('system.platform.windows'):
        return 'windows'
    elif xbmc.getCondVisibility('system.platform.osx'):
        return 'osx'
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return 'atv2'
    elif xbmc.getCondVisibility('system.platform.ios'):
        return 'ios'
myplatform = platform()
mycommand = 'StartAndroidActivity(,android.intent.action.VIEW,,%s)'


def function1(): # TV_App
    link = 'https://thetvapp.to/tv'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function2(): # Daddylive
    link = 'https://daddylive.dad/24-7-channels.php'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function3(): # Xumo
    link = 'https://play.xumo.com/live-guide/abc-news-live'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function4(): # tv 247
    link = 'https://tv247.us/all-channels/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function5(): # Time4tv
    link = 'https://time4tv.top/tv-channels.php'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)        



menuoptions()


