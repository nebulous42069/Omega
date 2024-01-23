# -*- coding: utf-8 -*-

import time
import xbmc
import os
import xbmcgui
import webbrowser




def menuoptions():
    dialog = xbmcgui.Dialog()
    funcs = (
        function1,
        )
        
    call = dialog.select('[B][COLOR=white]Click Here for Diggz Help..[/COLOR][/B]',
	[
	'[COLOR orange]DiggzWiki Forum[/COLOR]',])

    # dialog.selectreturns
    #   0 -> escape pressed
    #   1 -> first item
    #   2 -> second item
    if call:
        # esc is not pressed
        if call < 0:
            return
        func = funcs[call-42]
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

def function1():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://diggz1.me/forum/' ) )   
    else:
        opensite = webbrowser . open('https://diggz1.me/forum/')        




 
			
menuoptions()

