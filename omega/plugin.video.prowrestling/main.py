# -*- coding: UTF-8 -*-
from __future__ import division
import sys,re,os
import six
from six.moves import urllib_parse

import json

import requests
from requests.compat import urlparse

import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc, xbmcvfs
from resources.lib.brotlipython import brotlidec

if six.PY3:
    basestring = str
    unicode = str
    xrange = range
    from resources.lib.cmf3 import parseDOM
else:
    from resources.lib.cmf2 import parseDOM
import resolveurl

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.prowrestling')

PATH            = addon.getAddonInfo('path')
if six.PY2:
    DATAPATH        = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
else:
    DATAPATH        = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
RESOURCES       = PATH+'/resources/'
FANART=RESOURCES+'../fanart.jpg'
ikona =RESOURCES+'../icon.png'

exlink = params.get('url', None)
nazwa= params.get('title', None)
rys = params.get('image', None)

page = params.get('page',[1])#[0]

UA= 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36'
TIMEOUT=15

headers = {'User-Agent': UA,}
sess = requests.Session()

def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(query)

def add_item(url, name, image, mode, itemcount=1, page=1,fanart=FANART, infoLabels=False,contextmenu=None,IsPlayable=False, folder=False):
    list_item = xbmcgui.ListItem(label=name)
    if IsPlayable:
        list_item.setProperty("IsPlayable", 'True')    
    if not infoLabels:
        infoLabels={'title': name}    
    list_item.setInfo(type="video", infoLabels=infoLabels)    
    list_item.setArt({'thumb': image, 'poster': image, 'banner': image, 'fanart': fanart})
    
    if contextmenu:
        out=contextmenu
        list_item.addContextMenuItems(out, replaceItems=True)
    else:
        out = []
        out.append(('Informacja', 'XBMC.Action(Info)'),)
        list_item.addContextMenuItems(out, replaceItems=False)

    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url = build_url({'mode': mode, 'url' : url, 'page' : page, 'title':name,'image':image}),            
        listitem=list_item,
        isFolder=folder)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
   

   
def Clean_title(tit):
    zmiany = (('full ',''),('watch ',''),('online ',''),(' free',''),(' show',''))
    
    for z in zmiany:
        tit = re.sub(z[0], z[1], tit, 0, re.IGNORECASE)
    return tit
 
 
def ListLinks(url):
    html=getUrlReqOk(url)
    
    zz=''

    try:
       # videos = parseDOM(html,'div', attrs={'id':"content_section"})[0]
        
        videos = parseDOM(html,'div', attrs={'class':"entry-content rich-content"})[0]
        
        
        
    except:
        videos = parseDOM(html,'center')[0]
    xx = re.findall('href="([^"]+)" class=.*?>([^<]+)<\/span>',videos,re.DOTALL)
    typ = re.findall('>([^<]+)<\/span>',videos,re.DOTALL)
    for x,nazw in xx:
        href = x.replace('&amp;','&')
        try:
            title = re.findall('campaign=(.+?)\&',href,re.DOTALL)[0]
        except:
            title = urlparse(href).netloc
        if 'watch prev' in nazw.lower() or 'previous' in nazw.lower() :
            break
        tit = '[B][COLOR gold]'+nazwa + ' [/COLOR]'+'[COLOR khaki]'+nazw + '[/B][/COLOR][I]      (' +title+')[/I]'
        
        add_item(href, tit ,rys, 'playlink',fanart=FANART, folder=False, IsPlayable=True)
    xbmcplugin.endOfDirectory(addon_handle)

def PlayLink(url):

    ref=''
    if '|' in url:
        url,ref = url.split('|')
    link=''
    if 'premiumplug' in url or 'issuessolution' in url or 'gpllicense' in url:

        html=getUrlReqOk(url,ref)

        iframe = parseDOM(html,'iframe', ret="src")[0]
        iframe = 'https:' + iframe if iframe.startswith('//') else iframe
    else:
        iframe = url
    try:
        link = resolveurl.resolve(iframe)
    except:
        if 'dood' in iframe:
            from resources.lib import dood
            try:
                link = dood.getLink(iframe)
            except:
                pass
    if 'drop.down' in iframe and not link:
        from resources.lib import dood
        try:
            link =dood.getDropDown(iframe)
        except:
            pass
    elif 'm2list' in iframe and not link:
        from resources.lib import dood

        try:
            link =dood.getm2list(iframe,url)
        except:
            pass
    elif 'sawlive' in iframe and not link:
        from resources.lib import dood

        try:
            link =dood.getsawlive(iframe,url)
        except:
            pass
        
    if link:
        play_item = xbmcgui.ListItem(path=link)
        play_item.setInfo(type="Video", infoLabels={"title": nazwa,'plot':nazwa, 'thumb' :rys, 'icon': rys})
        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)  
    else:
        xbmcgui.Dialog().notification('[COLOR orangered][B]Error[/B][/COLOR]', "[COLOR orangered][B]Video has been removed\n or can't resolve link[/B][/COLOR]", xbmcgui.NOTIFICATION_INFO, 5000,False)
        sys.exit(1)
def ListPage(url, pg):
    if '/page/' in url:
        url = re.sub('/page/\\d+','/page/%d'%int(pg),url)
    else:
        url = url + '/page/%d' %int(pg)
    
    html=getUrlReqOk(url)

    nextpage=False 
    if html.find('rel="next"')>0:
        nextpage = unicode(int(pg)+1)
    posty = parseDOM(html,'article', attrs={'id':"post\-.*?"})
    for p in posty:
        try:
            dane = re.findall('(<a.*?\s*title\s*=\s*".*?)<\/a>',p,re.DOTALL)[0]
        except:

            dane = re.findall('(a.*?\s*alt\s*=\s*".*?)<\/a>',p,re.DOTALL)[0]
        title = Clean_title(re.findall('title\s*=\s*"([^"]+)"',dane,re.DOTALL)[0])

        href = re.findall('href\s*=\s*"([^"]+)"',dane,re.DOTALL)[0]
        img = re.findall('data\-lazy\-src\s*=\s*"([^"]+)"',dane,re.DOTALL)[0]
        add_item(href, PLchar(title) ,img, 'listlinks',fanart=FANART, folder=True)
    if nextpage:
        add_item(url, '>> next page >>' ,RESOURCES+'right.png', "listpage",fanart=FANART, page=nextpage, folder=True)
    xbmcplugin.endOfDirectory(addon_handle)

def ListSubmenu(dt,tyt):

    maintyt,poz = dt.split('|')
    add_item(maintyt, tyt ,ikona, "listpage",fanart=FANART, folder=True)

    dt = json.loads(poz)
    for d in dt:

        add_item(d.get('href', None), d.get('title', None),ikona, "listpage",fanart=FANART, folder=True)

    xbmcplugin.endOfDirectory(addon_handle)
    
    
def home():

    add_item('https://watchprowrestling.org/', 'Most recent shows' ,ikona, 'getRecent' ,fanart=FANART, folder=True)

    try:
        url = 'https://watchprowrestling.org/'
        html=getUrlReqOk(url)

        result = parseDOM(html,'ul', attrs={'id':"main-menu"})[0]
        titlehref = re.findall('a title="([^"]+)"\s*href="([^"]+)"',result)
        for title,href in titlehref:
            if href == '#':
                continue
            add_item(href, title ,ikona, 'getRecent',fanart=FANART, folder=True)

    except:
        add_item('', '[COLOR pink][B]>=>=>=>=>=>=> error occured <=<=<=<=<=<=<[/B][/COLOR]', ikona, "err",fanart=FANART, folder=False, IsPlayable=False)

    xbmcplugin.endOfDirectory(addon_handle)
    
def getUrlReqOk(url,ref=''):    

    headersok = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
    'Connection': 'keep-alive',

    'Referer': ref,}

    content=sess.get(url, headers=headersok,verify=False, timeout=30).content
    if six.PY3:
        content= (content).decode(encoding='utf-8', errors='strict') 
    else:
        content = content
    return content

#     Wrestling.live
#
#    

def ListRecent(url,page):
    if '/page/' in url:
        url = re.sub('/page/\\d+','/page/%d'%int(page),url)
    else:
        url = url + '/page/%d' %int(page)
    


    html=getUrlReqOk(url)
    if not 'category' in url:
        recent = re.findall('Most Recent Shows(.*?)<div class="vc_separator',html, re.DOTALL)[0]
    else:
        recent = parseDOM(html,'div', attrs={'class':"video-section"})[0] # =  <div class="video-section">
    article = parseDOM(recent,'article')
    for art in article:

        title = parseDOM((parseDOM(art,'h3')[0]),'a')[0].replace('&#8211;','-')
        title = re.sub('^watch','',title, 0, re.IGNORECASE)
        href = parseDOM(art,'a', ret="href")[0]
        dt = parseDOM(art,'span', attrs={'class':"date"})[0]
        img = parseDOM(art,'img', ret="src")[0]
        add_item(href, title, img, "listlinks2",fanart=FANART, folder=True, infoLabels={"title": title,'plot':title, 'code':dt})

    ntpage = re.findall('"([^"]+)"\>Next',recent,re.DOTALL)
    if ntpage:

        nextpage = unicode(int(page)+1)
        add_item(url, '>> next page >>' ,RESOURCES+'right.png', "getRecent",fanart=FANART, page=nextpage, folder=True)

    xbmcplugin.endOfDirectory(addon_handle)        

def ListLinks2(url):
    zz=''
    html=getUrlReqOk(url)
    html = html.replace("\'",'"')
    videos = parseDOM(html,'div', attrs={'class':"post-entry"})
    ab = len(nazwa)
    
    iksy = ''
    for x in xrange(ab-5):
        iksy+='#'
    if videos:
        add_item('empty', '[B][COLOR gold]'+iksy+'[/COLOR][/B]', rys, "empty",fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':nazwa})
        add_item('empty', '[B][COLOR gold]'+nazwa + ' [/COLOR][/B]', rys, "empty",fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':nazwa})
        add_item('empty', '[B][COLOR gold]'+iksy+'[/COLOR][/B]', rys, "empty",fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':nazwa})
        videos = videos[0]
        srcs = parseDOM(videos,'p', attrs={'style':"text\-align.*?"})
        com =''

        for src in srcs:

            if 'ommentary' in src:
                try:
                    src = src.replace('<strong>','').replace('</strong>','')
                    com = re.findall('>([^<]+)<\/span>',src)[0]
                except:

                    com=''
            if 'bk-button-wrappe' in src:
                try:
                    host = re.findall('strong>([^<]+)',src)[0]
                except:
                    host = re.findall('small">([^<]+)',src)[0]#small">Dropapk<

                if 'download links' in host.lower():
                    continue
                if 'waav' in host.lower() or 'netu' in host.lower():
                    continue
                hreftitle = re.findall('href="([^"]+)".*?>([^<]+)',src)
                for href,title in hreftitle:
                    href = href.replace('&amp;','&')
                    if 'waav' in title.lower() or 'netu' in title.lower():
                        continue

                    tit = '[B][COLOR khaki]'+title + '[/B][/COLOR][I]      (' +host+')[/I]'
                    add_item(href+'|'+url, tit, rys, "playlink",fanart=FANART, folder=False, IsPlayable=True, infoLabels={'plot':title, 'code':com})

    xbmcplugin.setContent(addon_handle, 'videos')
    xbmcplugin.endOfDirectory(addon_handle)    

def PLchar(char):
    if type(char) is not str:
        char = char if six.PY3 else char.encode('utf-8')
    char = char.replace('\\u0105','\xc4\x85').replace('\\u0104','\xc4\x84')
    char = char.replace('\\u0107','\xc4\x87').replace('\\u0106','\xc4\x86')
    char = char.replace('\\u0119','\xc4\x99').replace('\\u0118','\xc4\x98')
    char = char.replace('\\u0142','\xc5\x82').replace('\\u0141','\xc5\x81')
    char = char.replace('\\u0144','\xc5\x84').replace('\\u0144','\xc5\x83')
    char = char.replace('\\u00f3','\xc3\xb3').replace('\\u00d3','\xc3\x93')
    char = char.replace('\\u015b','\xc5\x9b').replace('\\u015a','\xc5\x9a')
    char = char.replace('\\u017a','\xc5\xba').replace('\\u0179','\xc5\xb9')
    char = char.replace('\\u017c','\xc5\xbc').replace('\\u017b','\xc5\xbb')
    char = char.replace('&#8217;',"'")
    char = char.replace('&#8211;',"-")    
    char = char.replace('&#8230;',"...")    
    char = char.replace('&#8222;','"').replace('&#8221;','"')    
    char = char.replace('[&hellip;]',"...")
    char = char.replace('&#038;',"&")    
    char = char.replace('&#039;',"'")
    char = char.replace('&quot;','"').replace('&oacute;','ó').replace('&rsquo;',"'")
    char = char.replace('&nbsp;',".").replace('&amp;','&').replace('&eacute;','e')
    return char    
def PLcharx(char):
    char=char.replace("\xb9","ą").replace("\xa5","Ą").replace("\xe6","ć").replace("\xc6","Ć")
    char=char.replace("\xea","ę").replace("\xca","Ę").replace("\xb3","ł").replace("\xa3","Ł")
    char=char.replace("\xf3","ó").replace("\xd3","Ó").replace("\x9c","ś").replace("\x8c","Ś")
    char=char.replace("\x9f","ź").replace("\xaf","Ż").replace("\xbf","ż").replace("\xac","Ź")
    char=char.replace("\xf1","ń").replace("\xd1","Ń").replace("\x8f","Ź");
    return char    
 
def Playlin(link) :
    play_item = xbmcgui.ListItem(path=link)

    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)    

 
def router(paramstring):
    params = dict(urllib_parse.parse_qsl(paramstring))
    if params:    
    
        mode = params.get('mode', None)
    
        if mode =='menu':
            Menu()
            
        elif mode =="menu2":
            Menu2()
        
        elif mode == 'getRecent':
            ListRecent(exlink,page)
            
        elif mode =="listpage":
            ListPage(exlink,page)
            
        elif mode =="listsubmenu":
            ListSubmenu(exlink, nazwa)
            
        elif mode == "listlinks":
            ListLinks(exlink)
            
        elif mode == "listlinks2":
            ListLinks2(exlink)
            
        elif mode == 'playlink':
            PlayLink(exlink)

    else:
        home()
        xbmcplugin.endOfDirectory(addon_handle)    
if __name__ == '__main__':
    router(sys.argv[2][1:])