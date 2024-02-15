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
        function9,
        function10,
    )
    call = dialog.select('[B]Diggz Sports Website Browser[/B]', [
            '[B]The_TV_App Sports[/B]',
            '[B]SportsEast[/B]',
            '[B]CrackStreams/MethStreams[/B]',
            '[B]MrGamingStreams[/B]',
            '[B]Time4TV Sports[/B]',
            '[B]SportsCart[/B]',
            '[B]MarkyStreams[/B]',
            '[B]TopStreams[/B]',
            '[B]BuffStreams[/B]',
            '[B]Rojadirecta[/B]',
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
        func = funcs[call-10] # Number of functions (function10)
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


def function1(): # TV_App Sports
    link = 'https://thetvapp.to/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function2(): # Sportseast
    link = 'https://streameast.app/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function3(): # CrackStreams
    link = 'https://methstreams.com/watch/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function4(): # MrGamingStreams
    link = 'https://mrgamingstreams.com/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function5(): # Time4tv sports
    link = 'https://time4tv.top/schedule.php'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function6(): # SportsCart
    link = 'https://sportskart.xyz/schedule/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function7(): # MarkyStreams
    link = 'https://markkystreams.com/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function8(): # TopStreams
    link = 'https://topstreams.me/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function9(): # BuffStreams
    link = 'https://buff-streams.net/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)


def function10(): # Rojadirecta
    link = 'https://rojadirecta.io/'
    if myplatform == 'android':
        return xbmc.executebuiltin(mycommand % link)
    else:
        return webbrowser.open(link)



menuoptions()


