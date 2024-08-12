"""

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import urllib, sys, re, os, string, random, unicodedata
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

#==============================================================================================================================

IS_PY3 = sys.version_info[0] > 2

if IS_PY3:
	from urllib.request import Request
	from urllib.request import urlopen
	from urllib.parse import unquote_plus, quote_plus
else:
	from urllib2 import Request, urlopen
	from urllib import unquote_plus, quote_plus

dlg = xbmcgui.Dialog()
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_id = addon.getAddonInfo('id')
plugin_path = xbmcaddon.Addon(id=addon_id).getAddonInfo('path')
addon_handle = int(sys.argv[1])

try:
    fanart = xbmcvfs.translatePath(os.path.join(plugin_path, 'fanart.jpg'))
    icon = xbmcvfs.translatePath(os.path.join(plugin_path, 'icon.png'))
except:
    fanart = xbmc.translatePath(os.path.join(plugin_path, 'fanart.jpg'))
    icon = xbmc.translatePath(os.path.join(plugin_path, 'icon.png'))

HOME     = 'special://home'
PROFILE  = 'special://profile'
DATABASE = os.path.join(PROFILE,'Database')

#==============================================================================================================================

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

#==============================================================================================================================

def addDirMain(name,url,mode,iconimage,fanart):
  try: #Python 3
    u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)
    ok=True
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': iconimage, 'icon': "DefaultVideo.png", 'fanart': fanart})
    liz.setInfo( type = "Video", infoLabels = { "Title": name } )
    liz.setProperty('IsPlayable', 'false')
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok
  except: #Python2
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setProperty('fanart_image', fanart)
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok

def add_link_info(name, iconimage, fanart):
  try: #Python3
    u = sys.argv[0] + "&name=" + urllib.parse.quote_plus(name) + "&iconimage=" + urllib.parse.quote_plus(iconimage)	
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': iconimage,
                      'icon': "DefaultVideo.png",
                      'fanart': fanart})
    ok = xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = u, listitem = liz) 
    return ok
  except: #Python2
    u = sys.argv[0] + "&name=" + urllib.quote_plus(name) + "&iconimage=" + urllib.quote_plus(iconimage)	
    liz = xbmcgui.ListItem(name, iconImage = "DefaultVideo.png", thumbnailImage = iconimage)
    liz.setInfo( type = "Video", infoLabels = { "Title": name } )
    liz.setProperty('fanart_image', fanart)
    liz.setProperty('IsPlayable', 'false') 
    ok = xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = u, listitem = liz) 

def addLink(name, url, mode, iconimage, fanart):
  try: #Python 3
    u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)
    ok=True
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': iconimage, 'icon': "DefaultVideo.png", 'fanart': fanart})
    liz.setInfo( type = "Video", infoLabels = { "Title": name } )
    liz.setProperty('IsPlayable', 'true')
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
    return ok
  except: #Python2
    u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&iconimage="+urllib.quote_plus(iconimage)
    liz=xbmcgui.ListItem(name)
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={"Title": name})		
    liz.setProperty('fanart_image', fanart)
    liz.setProperty('IsPlayable', 'true')
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)		
    return ok

def Add_Dir(name, url='', mode='', folder=False, icon='', fanart='', description='', info_labels={}, set_art={}, set_property={}, content_type='', context_items=None, context_override=False, playable=False):

    filepath=HOME

    info_labels["Title"] = name
    info_labels["FileName"] = name

    try:
        plot = info_labels["plot"]
        if plot == '':
            info_labels["plot"] = description
    except:
        info_labels["plot"] = description
    try:
        set_art["icon"]
    except:
        set_art["icon"] = icon
    try:
        set_property["Fanart_Image"] = fanart
    except:
        set_property["Fanart_Image"]

    iconImage=str(icon) 
    thumbnailImage=str(icon)

    liz = xbmcgui.ListItem(label=str(name))
    liz.setArt({'thumb': str(icon), 'icon': iconImage, 'fanart': fanart})
    liz.setInfo(type=content_type, infoLabels=info_labels)

    for item in set_property.items():
        liz.setProperty(item[0], item[1])

    if context_items:
        liz.addContextMenuItems(context_items, context_override)

    u   = sys.argv[0]
    u += "?mode="           +str(mode)
		
    try: #Python 3
        Ncodepath  = urllib.parse.quote(HOME)
        Ncodepath2 = Ncodepath.replace('%3A','%3a').replace('%5C','%5c')
        theString = filepath.replace(HOME, 'special://home/').replace(Ncodepath, 'special://home/').replace(Ncodepath2, 'special://home/')
	
        u += "&url="            +urllib.parse.quote_plus(theString)
        u += "&name="           +urllib.parse.quote_plus(name)
        u += "&iconimage="      +urllib.parse.quote_plus(icon)
        u += "&fanart="         +urllib.parse.quote_plus(fanart)
        u += "&description="    +urllib.parse.quote_plus(description)
 
    except: #Python 2	
        Ncodepath  = urllib.quote(HOME)
        Ncodepath2 = Ncodepath.replace('%3A','%3a').replace('%5C','%5c')
        theString = filepath.replace(HOME, 'special://home/').replace(Ncodepath, 'special://home/').replace(Ncodepath2, 'special://home/')
	
        u += "&url="            +urllib.quote_plus(theString)
        u += "&name="           +urllib.quote_plus(name)
        u += "&iconimage="      +urllib.quote_plus(icon)
        u += "&fanart="         +urllib.quote_plus(fanart)
        u += "&description="    +urllib.quote_plus(description)
   
    if url.startswith('plugin://'):
        xbmcplugin.addDirectoryItem(handle=addon_handle,url=url,listitem=liz,isFolder=True) 

    elif folder:
        xbmcplugin.addDirectoryItem(handle=addon_handle,url=u,listitem=liz,isFolder=True)

    elif playable:
        liz.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle=addon_handle,url=url,listitem=liz,isFolder=False) 

    else:
        xbmcplugin.addDirectoryItem(handle=addon_handle,url=u,listitem=liz,isFolder=False) 
	
#===============================================================================

def regex_get_all(text, start_with, end_with):
	r = re.findall("(?i)(" + start_with + "[\S\s]+?" + end_with + ")", text)
	return r

#===============================================================================
