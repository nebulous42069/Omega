# -*- coding: utf-8 -*-
import xbmc, xbmcvfs, xbmcplugin, xbmcaddon, xbmcgui
import os, sys, glob, base64
from datetime import datetime
from urllib.parse import parse_qs

addon_id = xbmcaddon.Addon().getAddonInfo('id')

'''#####-----Build File-----#####'''
buildfile = 'https://raw.githubusercontent.com/Buildtexts69/omegabuilds/main/X2/xenonlive.xml'

'''#####-----Notifications File-----#####'''
notify_url  = 'http://'

'''#####-----Excludes-----#####'''
EXCLUDES  = [addon_id]

translatePath = xbmcvfs.translatePath
addon_id = xbmcaddon.Addon().getAddonInfo('id')
addon           = xbmcaddon.Addon(addon_id)
addoninfo       = addon.getAddonInfo
addon_version   = addoninfo('version')
addon_name      = addoninfo('name')
addon_icon      = addoninfo("icon")
addon_fanart    = addoninfo("fanart")
addon_profile   = translatePath(addoninfo('profile'))
addon_path      = translatePath(addoninfo('path'))	
setting         = addon.getSetting
setting_true    = lambda x: bool(True if setting(str(x)) == "true" else False)
setting_set     = addon.setSetting
local_string    = addon.getLocalizedString
home = translatePath('special://home/')
dialog = xbmcgui.Dialog()
dp = xbmcgui.DialogProgress()
xbmcPath=os.path.abspath(home)
addons_path = os.path.join(home, 'addons/')
user_path = os.path.join(home, 'userdata/')
data_path = os.path.join(user_path, 'addon_data/')
db_path = os.path.join(user_path, 'Database/')
addons_db = os.path.join(db_path,'Addons33.db')
textures_db = os.path.join(db_path,'Textures13.db')
packages = os.path.join(addons_path, 'packages/')
resources = os.path.join(addon_path, 'resources/')
installed_date = str(datetime.now())[:-7]
def isBase64(s):
    if base64.b64encode(base64.b64decode(s)).decode('utf8') == s:
    	return True
    else:
        return False
advancedsettings_xml =  os.path.join(user_path, 'advancedsettings.xml')
advancedsettings_folder = os.path.join(resources, 'advancedsettings/')
user_agent = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
headers = {'User-Agent': user_agent}