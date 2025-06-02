import xbmc
import xbmcgui
import xbmcplugin
import sys
from inspect import getframeinfo, stack
from urllib.parse import quote_plus, unquote_plus

def add_dir(name,url,mode,icon,fanart, name2='', version='', addcontext=False,isFolder=True):
    u=sys.argv[0]+"?url="+quote_plus(url)+"&mode="+str(mode)+"&name="+quote_plus(name)+"&icon="+quote_plus(icon) +"&fanart="+quote_plus(fanart)+"&name2="+quote_plus(name2)+"&version="+quote_plus(version)
    liz=xbmcgui.ListItem(name)
    liz.setArt({'fanart':fanart,'icon':icon,'thumb':icon})
    liz.setInfo(type="Video", infoLabels={ "Title": name})
    if addcontext:
        contextMenu = []
        liz.addContextMenuItems(contextMenu)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=isFolder)

