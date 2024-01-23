
import sys,re,requests
import urllib.parse
import xbmcgui, xbmcaddon, xbmcplugin, os, xbmcvfs
from resources.lib import tools

addon_id            = xbmcaddon.Addon().getAddonInfo('id')
addon_name          = xbmcaddon.Addon().getAddonInfo('name')
home_folder         = xbmcvfs.translatePath('special://home/')
addon_folder        = os.path.join(home_folder, 'addons')
art_path            = os.path.join(addon_folder, addon_id)
icon                = os.path.join(art_path,'icon.png')
fanart              = os.path.join(art_path,'fanart.jpg')

def start():
  tools.addDir('[COLOR=white]Black and White Movies[/COLOR]','Black_and_White',1,icon,fanart,"Black and White movies")


def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    return param

xbmcplugin.setContent(int(sys.argv[1]), 'movies')

params=get_params()
url=None
name=None
mode=None
iconimage=None
description=None
query=None
type=None

try:
    url=urllib.parse.unquote_plus(params["url"])
except:
    pass
try:
    name=urllib.parse.unquote_plus(params["name"])
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
try:
    description=urllib.parse.unquote_plus(params["description"])
except:
    pass
try:
    query=urllib.parse.unquote_plus(params["query"])
except:
    pass
try:
    type=urllib.parse.unquote_plus(params["type"])
except:
    pass

if mode==None or url==None or len(url)<1:
    start()
elif mode==1:
	tools.bandw(url)
elif mode==2:
    tools.categories(url)
elif mode==3:
    User_Agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
    headers = {'User-Agent': User_Agent}

    html = requests.get(url, headers=headers).content.decode('utf-8')
    match = re.compile('<source src="(.+?)"',re.DOTALL).findall(html)
    for link in match:
        link = link 
    liz = xbmcgui.ListItem(name, path=link)
    liz.setArt({'thumb' : iconimage,
            'icon' : iconimage,
            'fanart' : fanart})
    infoLabels={"title": name}
    liz.setInfo(type="video", infoLabels=infoLabels)
    liz.setProperty('IsPlayable', 'true')
    xbmc.Player().play(item=link, listitem=liz)
    quit()

xbmcplugin.endOfDirectory(int(sys.argv[1]))