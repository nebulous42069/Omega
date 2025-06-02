import sys
import json
import xbmc
import xbmcplugin
from .utils import add_dir

addon_fanart = 'special://home/addons/plugin.program.maxql/icons/fanart.jpg'
min_icon = 'special://home/addons/plugin.program.maxql/icons/1080p.png'
max_icon = 'special://home/addons/plugin.program.maxql/icons/4k.png'
on_icon = 'special://home/addons/plugin.program.maxql/icons/on.png'
off_icon = 'special://home/addons/plugin.program.maxql/icons/off.png'

handle = int(sys.argv[1])

def main_menu():
    xbmcplugin.setPluginCategory(handle, 'Main Menu')

    add_dir('Enable Max 1080P Resolution','',1,min_icon,addon_fanart,isFolder=False)
    
    add_dir('Enable Max 4K Resolution','',2,max_icon,addon_fanart,isFolder=False)

    add_dir('Enable Dolby Vision Results','',3,on_icon,addon_fanart,isFolder=False)

    add_dir('Disable Dolby Vision Results','',4,off_icon,addon_fanart,isFolder=False)

    add_dir('Enable 3D Results','',5,on_icon,addon_fanart,isFolder=False)

    add_dir('Disable 3D Results','',6,off_icon,addon_fanart,isFolder=False)

    add_dir('Enable Auto-Play','',7,on_icon,addon_fanart,isFolder=False)

    add_dir('Disable Auto-Play','',8,off_icon,addon_fanart,isFolder=False)


