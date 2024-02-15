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
    )
    call = dialog.select('[B]Diggz Website Browser[/B]', [
            '[B]The_TV_App[/B]',
            '[B]Daddy Live[/B]',
            '[B]Xumo Live[/B]',
            '[B]Classic On Demand[/B]',
            '[B]Squid TV[/B]',
            '[B]TV 24/7[/B]',
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
        func = funcs[call-6] # Number of functions (function10)
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
    link = 'https://daddylive.watch/24-7-channels.php'
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


def function4(): # Classic On Demand
    link = 'https://webapp.airy.tv/on-demand/Sci%20Fi'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function5(): # Squid TV
    link = 'https://www.squidtv.net/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function6(): # tv 247
    link = 'https://tv247.us/all-channels/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)



menuoptions()


