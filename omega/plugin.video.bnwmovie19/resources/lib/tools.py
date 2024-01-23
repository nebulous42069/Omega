# -*- coding: utf-8 -*-

import requests,os,re,sys,xbmc,xbmcaddon,xbmcplugin,xbmcgui
import urllib.parse

def addDir(name,url,mode,iconimage,fanart,description):
    u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)+"&fanart="+urllib.parse.quote_plus(fanart)+"&description="+urllib.parse.quote_plus(description)
    ok=True
    liz=xbmcgui.ListItem(name)
    liz.setArt({'thumb' : iconimage,
                'icon' : iconimage,
                'fanart' : fanart})
    liz.setInfo( type="Video", infoLabels={"Title": name,"Plot":description,})
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def bandw(url):
    User_Agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
    headers = {'User-Agent': User_Agent}

    url = "https://bnwmovies.com/"
    html = requests.get(url, headers=headers).content.decode('utf-8')
    match = re.compile('<div class="genreicon"><a href="(.+?)".+?title="(.+?)".+?<img src="(.+?)"',re.DOTALL).findall(html)
    for link, name, image in match:
        name = name.replace("&#8217;","'")
        link = "https://bnwmovies.com"+link
        addDir(name,link,2,image,"",name)
            
def categories(url):
    User_Agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
    headers = {'User-Agent': User_Agent}

    html = requests.get(url, headers=headers).content.decode('utf-8')
    match = re.compile('<div class="cattombstone"><a href="(.+?)".+?src="(.+?)".+?<br>(.+?)</a>',re.DOTALL).findall(html)
    for link, image, name in match:
        name = name.replace("&#8217;","'")
        addDir(name,link,3,image,"",name) 

