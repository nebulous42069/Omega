# -*- coding: utf-8 -*-

# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)

import urllib, sys, re, os, unicodedata
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

try:
    # Python 3
    from urllib.request import urlopen, Request
except ImportError:
    # Python 2
    from urllib2 import urlopen, Request

try:
    # Python 3
    from html.parser import HTMLParser
except ImportError:
    # Python 2
    from HTMLParser import HTMLParser

from resources.lib.modules.risque import *
from resources.lib.modules.sexyFlicks import *
from resources.lib.modules.common import *
from resources.lib.modules.showVID import *

import sexyFlicks

params = get_params()
mode = None

addon_id = xbmcaddon.Addon().getAddonInfo('id') 

selfAddon = xbmcaddon.Addon(id=addon_id)
plugin_handle = int(sys.argv[1])
dialog = xbmcgui.Dialog()
mysettings = xbmcaddon.Addon(id = 'plugin.video.risque')
profile = mysettings.getAddonInfo('profile')
home = mysettings.getAddonInfo('path')

try:
    datapath= xbmcvfs.translatePath(selfAddon.getAddonInfo('profile'))
except:
    datapath= xbmc.translatePath(selfAddon.getAddonInfo('profile'))

try:
    fanart = xbmcvfs.translatePath(os.path.join(home, 'fanart.jpg'))
    icon = xbmcvfs.translatePath(os.path.join(home, 'icon.png'))
    mediapath = xbmcvfs.translatePath(os.path.join('special://home/addons/' + addon_id + '/resources/media/'))
except:
    fanart = xbmc.translatePath(os.path.join(home, 'fanart.jpg'))
    icon = xbmc.translatePath(os.path.join(home, 'icon.png'))
    mediapath = xbmc.translatePath(os.path.join('special://home/addons/' + addon_id + '/resources/media/'))

genreImage = 'special://home/addons/script.j1.artwork/lib/resources/images/genres/'

BASE  = "plugin://plugin.video.youtube/playlist/"

#==========================================================================================================

def Main():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]', icon, fanart)
	addDirMain('[COLOR white][B]Sexy Movies[/B][/COLOR]',BASE,10, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Swimwear[/B][/COLOR]',BASE,0, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Channels[/B][/COLOR]',BASE,1, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Just Plain Sexy[/B][/COLOR]',BASE,2, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Fashion N Arts[/B][/COLOR]',BASE,3, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Sports N More[/B][/COLOR]',BASE,4, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Cooking N Home[/B][/COLOR]',BASE,5, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Dance N Twerk[/B][/COLOR]',BASE,6, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Tattoo N Art[/B][/COLOR]',BASE,7, mediapath+"risque.png", fanart)
	addDirMain('[COLOR white][B]Sexy Fitness[/B][/COLOR]',BASE,8, mediapath+"risque.png", fanart)
	add_link_info('[B][COLORorange] [/COLOR][/B]', icon, fanart)

#==========================================================================================================

def sexyList():

	add_link_info('[B][COLORorange]== Sexy Movies ==[/COLOR][/B]', genreImage+'Risque-Blue.jpg', fanart)
	
	addDirMain('[COLOR white][B]All Movies[/B][/COLOR]',BASE,903,genreImage+'All.png', fanart)
	addDirMain('[COLOR white][B]Action Movies[/B][/COLOR]',BASE,910,genreImage+'Action.png', fanart)
	addDirMain('[COLOR white][B]Anime Movies[/B][/COLOR]',BASE,926,genreImage+'Anime.png', fanart)
	addDirMain('[COLOR white][B]Classic Movies[/B][/COLOR]',BASE,912,genreImage+'Classic.png', fanart)
	addDirMain('[COLOR white][B]Comedy Movies[/B][/COLOR]',BASE,913,genreImage+'Comedy.png', fanart)
	addDirMain('[COLOR white][B]Crime Movies[/B][/COLOR]',BASE,914,genreImage+'Crime.png', fanart)
	addDirMain('[COLOR white][B]Documentaries[/B][/COLOR]',BASE,915,genreImage+'Documentary.png', fanart)
	addDirMain('[COLOR white][B]Drama Movies[/B][/COLOR]',BASE,916,genreImage+'Drama.png', fanart)
	addDirMain('[COLOR white][B]Fantasy Movies[/B][/COLOR]',BASE,918,genreImage+'Fantasy.png', fanart)
	addDirMain('[COLOR white][B]Horror Movies[/B][/COLOR]',BASE,919,genreImage+'Horror.png', fanart)
	addDirMain('[COLOR white][B]Mystery Movies[/B][/COLOR]',BASE,927,genreImage+'Mystery.png', fanart)
	addDirMain('[COLOR white][B]Romance Movies[/B][/COLOR]',BASE,917,genreImage+'Romance.png', fanart)
	addDirMain('[COLOR white][B]Scifi Movies[/B][/COLOR]',BASE,921,genreImage+'Scifi.png', fanart)
	addDirMain('[COLOR white][B]Sports Movies[/B][/COLOR]',BASE,922,genreImage+'Sports.png', fanart)
	addDirMain('[COLOR white][B]Thriller Movies[/B][/COLOR]',BASE,923,genreImage+'Thriller.png', fanart)
	addDirMain('[COLOR white][B]Western Movies[/B][/COLOR]',BASE,924,genreImage+'Western.png', fanart)
	#addDirMain('[COLOR white][B]Zombie Movies[/B][/COLOR]',BASE,925,genreImage+'Zombie.png', fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]', genreImage+'Risque-Blue.jpg', fanart)

#==========================================================================================================

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


def get_setting(setting):
    return addon.getSetting(setting)

def set_setting(setting, string):
    return addon.setSetting(setting, string)

def get_string(string_id):
    return addon.getLocalizedString(string_id)

#==========================================================================================================
		
params=get_params()
url=None
name=None
mode = None
iconimage=None
description=None

#===================== Python 2 ======================

try:
        url=urllib.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode = urllib.unquote_plus(params["mode"])
except:
        pass
try:
        iconimage=urllib.unquote_plus(params["iconimage"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass

#===================== Python 3 ======================

try:
        url=urllib.parse.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.parse.unquote_plus(params["name"])
except:
        pass
try:
        mode = urllib.parse.unquote_plus(params["mode"])
except:
        pass
try:
        iconimage=urllib.parse.unquote_plus(params["iconimage"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass
		
#errorMsg="%s" % (mode)
#xbmcgui.Dialog().ok("mode", errorMsg)
 
#=======================================================

if mode == 0:
	Sexy_bikini()
		
elif mode == 1:
	Sexy_channels()		
		
elif mode == 2:
	Plain_sexy()

elif mode == 3:
	Sexy_fashion()
	
elif mode == 4:
	Sexy_sports()

elif mode == 5:
	Sexy_home()

elif mode == 6:
	Sexy_dance()

elif mode == 7:
	Sexy_tattoo()
	
elif mode == 8:
	Sexy_fitness()

elif mode == 9:
	Sexy_mix()

elif mode == 10:
	sexyList()


#=========================================

elif mode == 903:
    Listing.Genres("All")

#=========================================

elif mode == 910:
    Listing.Genres("Action")

#elif mode == 911:
    #Listing.Genres("Animation")

elif mode == 912:
    Listing.Genres("Classic")

elif mode == 913:
    Listing.Genres("Comedy")

elif mode == 914:
    Listing.Genres("Crime")

elif mode == 915:
    Listing.Genres("Docs")

elif mode == 916:
    Listing.Genres("Drama")

elif mode == 917:
    Listing.Genres("Romance")

elif mode == 918:
    Listing.Genres("Fantasy")

elif mode == 919:
    Listing.Genres("Horror")

elif mode == 920:
    Listing.Genres("Music")

elif mode == 921:
    Listing.Genres("Scifi")

elif mode == 922:
    Listing.Genres("Sports")

elif mode == 923:
    Listing.Genres("Thriller")

elif mode == 924:
    Listing.Genres("Western")

elif mode == 925:
    Listing.Genres("Zombie")

elif mode == 926:
    Listing.Genres("Anime")

elif mode == 927:
    Listing.Genres("Mystery")

#=========================================

elif mode == 801:
		
	#errorMsg="%s" % (url)
	#xbmcgui.Dialog().ok("url", errorMsg)

	Common.getVID(url)

#=========================================

elif mode is None:
	Main()
		
xbmcplugin.endOfDirectory(plugin_handle)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
