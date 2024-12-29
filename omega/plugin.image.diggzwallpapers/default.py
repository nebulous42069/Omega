################################################################################
#(_)                                                                           #
# |_________________________________________                                   #
# |*  *  *  *  * |##########################|                                  #
# | *  *  *  *  *|==========================|                                  #
# |*  *  *  *  * |##########################|                                  #
# | *  *  *  *  *|==========================|                                  #
# |*  *  *  *  * |##########################|      If your going to copy       #
# | *  *  *  *  *|==========================|         this addon just          #
# |*  *  *  *  * |##########################|         give credit!!!!          #
# |--------------|==========================|                                  #
# |#########################################|                                  #
# |=========================================|                                  #
# |#########################################|                                  #
# |=========================================|                                  #
# |#########################################|                                  #
# |-----------------------------------------|                                  #
# |                                                                            #
# |    Diggz Walpapers Add-on                                                  #
# |    Copyright (C) 2017 FTG                                                  #
# |                                                                            #
# |    This program is free software: you can redistribute it and/or modify    #
# |    it under the terms of the GNU General Public License as published by    #
# |    the Free Software Foundation, either version 3 of the License, or       #
# |    (at your option) any later version.                                     #
# |                                                                            #
# |    This program is distributed in the hope that it will be useful,         #
# |    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
# |    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
# |    GNU General Public License for more details.                            #
# |                                                                            #
################################################################################

import xbmc, xbmcvfs, xbmcaddon, xbmcgui, xbmcplugin,os,sys
import urllib.request, urllib.error, urllib.parse
import re
import downloader
from bs4 import BeautifulSoup as bs


AddonID      = 'plugin.image.diggzwallpapers'
selfAddon    = xbmcaddon.Addon(id=AddonID)
addon_handle = int(sys.argv[1])
ADDON_DATA   = xbmcvfs.translatePath(os.path.join('special://','home'))
ADDON        = xbmcaddon.Addon(id='plugin.image.diggzwallpapers')
dialog       = xbmcgui.Dialog()    
FANARTICO    = xbmcvfs.translatePath(os.path.join('special://home/addons/' + AddonID , 'fanart.jpg'))
icon         = xbmcvfs.translatePath(os.path.join('special://home/addons/' + AddonID, 'icon.png'))
backupdir    = str(selfAddon.getSetting('remote_path'))   
download_dir = xbmcvfs.translatePath(os.path.join(backupdir,''))
ADDON        = xbmcaddon.Addon()
dialog       = xbmcgui.Dialog()
dp           = xbmcgui.DialogProgress()
base= 'https://diggz1.me/WALLPAPERS/'
if not os.path.exists(download_dir): os.makedirs(download_dir)

def CATEGORIES():
	addDir1('[COLOR yellow][B]Pick and choose your wallpapers below..[/B][/COLOR]','url',1,icon,FANARTICO,'')
	addDir2('[B][COLOR blue]ABSTRACT[/COLOR][/B]', base + 'ABSTRACT/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]ANIMALS[/COLOR][/B]', base + 'ANIMALS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]CHRISTMAS[/COLOR][/B]', base + 'CHRISTMAS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]CLASSIC_CARS[/COLOR][/B]', base + 'CLASSIC_CARS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]DISNEY[/COLOR][/B]', base + 'DISNEY/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]DRAGONS[/COLOR][/B]', base + 'DRAGONS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]DISPARITY[/COLOR][/B]', base + 'Disparity/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Dark Blue[/COLOR][/B]', base + 'Disparity_Darkblue/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Cyan[/COLOR][/B]', base + 'Disparity_cyan/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Green[/COLOR][/B]', base + 'Disparity_green/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Indigo[/COLOR][/B]',base + 'Disparity_indigo/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Orange[/COLOR][/B]',base + 'Disparity_orange/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Pink[/COLOR][/B]', base + 'Disparity_pink/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Red[/COLOR][/B]',base + 'Disparity_red/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Disparity Yellow[/COLOR][/B]',base + 'Disparity_yellow/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Exotic Cars[/COLOR][/B]', base + 'EXOTIC_CARS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]FANTASY[/COLOR][/B]', base + 'FANTASY/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]FISH TANK[/COLOR][/B]', base + 'FISH_TANK/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]FLOWERS[/COLOR][/B]', base + 'FLOWERS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]GOTHIC[/COLOR][/B]', base + 'GOTHIC/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]HALLOWEEN[/COLOR][/B]', base + 'HALLOWEEN/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]HORROR[/COLOR][/B]', base + 'HORROR/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]LIONS AND TIGERS[/COLOR][/B]', base + 'LIONS_TIGERS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]MANCAVE[/COLOR][/B]', base + 'MANCAVE/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]MARVEL[/COLOR][/B]', base + 'MARVEL/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]MATRIX[/COLOR][/B]', base + 'MATRIX/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]METAL[/COLOR][/B]', base + 'METAL/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]MOUNTAINS[/COLOR][/B]',base + 'MOUNTAINS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]MOVIE ART[/COLOR][/B]',base + 'MOVIE_ART/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]NORTHERN LIGHTS[/COLOR][/B]', base + 'NORTHERN_LIGHTS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]Nvidia[/COLOR][/B]',base + 'Nvidia/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]RETRO ARCADE[/COLOR][/B]',base + 'RETRO_ARCADE/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]AUTUMN[/COLOR][/B]', base + 'SEASONS_FALL/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]SKULLS[/COLOR][/B]', base + 'SKULLS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]SPACE[/COLOR][/B]', base + 'SPACE/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]STEAMPUNK[/COLOR][/B]', base + 'STEAMPUNK/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]TRIPPY[/COLOR][/B]',base + 'TRIPPY/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]URBAN[/COLOR][/B]',base + 'Urban/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]WISEGUYS[/COLOR][/B]', base + 'WISEGUYS/',5,icon,FANARTICO)
	addDir2('[B][COLOR blue]cg VARIOUS[/COLOR][/B]', base + 'cg_VARIOUS/',5,icon,FANARTICO)
	
#############Diggz Wallpapers########
def Diggz_content(name,url):
	link = OPEN_URL(url).decode('utf-8')
	match = re.compile('href="(.+?)">(.+?)</a>').findall(link)
	for url2, img in match[1:]:
		name1 = img
		url3 = url + url2
		img = url + img
		addDir1(name1,url3,51,img,img,'')

def Download_Diggz(name1,img):
	choice = dialog.yesno("[COLOR blue]Diggz Background Chooser[/COLOR]", "[COLOR cyan]Would you like to add this wallpaper to Xenon?[/COLOR]", nolabel='[B][COLOR red]Na, nevermind[/COLOR][/B]',yeslabel='[B][COLOR green]Heck yea!![/COLOR][/B]')
	if choice == 0:
		return
	elif choice == 1:
		path = download_dir
		dp = xbmcgui.DialogProgress()
		lib=os.path.join(path, name)
		dp.create("Diggz Wallpaper","Downloading " +'\n'+ 'Please Wait')		
		downloader.download(img, lib, dp)
		dialog.ok('[COLOR blue]Well that was easy!![/COLOR]' ,'This image has been added as a background. You can delete images from the Downloaded wallpaper folder by hitting the context menu/Delete. Download as many as you wish. They will rotate every so often. If you have any requests, let me know.')
		return

############ HD WALLPAPERS ##############	
def Hdwallpapers_list(name,url):
	addDir2('[B]Search >>>[/B]','url',33,icon,FANARTICO)	
	link = OPEN_URL(url)
	soup=bs(link)
	tag=soup.find('ul',{'class':'side-panel categories'})
	match=re.compile('href="(.+?)">(.+?)</a>', re.DOTALL).findall(str(tag))
	for url, name in match:
		name = name.replace('&amp;','&')
		url = "http://www.hdwallpapers.in/%s" % url
		addDir('[B]'+name+'[/B]',url,31,icon,FANARTICO,'')
def Hdwallpapers_content(name,url):
	link = OPEN_URL(url)
	match=re.compile('<div class="thumb"><a href="(.+?)"><p>(.+?)</p><img src="(.+?)"').findall(link)
	for url, name, img in match:
		url = "http://www.hdwallpapers.in/%s" % url
		img = "http://www.hdwallpapers.in/%s" % img
		addDir(name,url,32,img,img,'')		
	for nextpage in parse_dom(link, 'div', {'class': 'pagination'}):
		match = re.compile('<a href="(.+?)">(\d+)</a>').findall(nextpage)
		for url,pageid in match:
			url = "http://www.hdwallpapers.in/%s" % url
			addDir('Page ' + pageid + " >>>",url,31,icon,FANARTICO,'')
def Hdwallpapers_quality(name,url,iconimage):
	link = OPEN_URL(url)
	img = iconimage
	for items in parse_dom(link, 'div', {'class': 'wallpaper-resolutions'}):
		match = re.compile('<a href="(.+?)" title=".+?">(.+?)</a>').findall(items)
		for url,name in match:
			url = "http://www.hdwallpapers.in/%s" % url
			liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
			liz.setArt({'icon': "DefaultFolder.png", 'thumb': iconimage, 'fanart': img}) 
			liz.setInfo( type="Image", infoLabels={ "Title": name } )
			liz.setProperty('fanart_image', img)		
			cm = []
			cm.append(('Download Item', 'RunPlugin(%s?mode=100&name=%s&url=%s&)'%(sys.argv[0],name,url)))
			liz.addContextMenuItems(cm, replaceItems=False)		
			xbmcplugin.addDirectoryItem(addon_handle, url, liz, False)
############ WALLPAPER WIDE ##############			
def Wallpapers_wide(name,url):
	addDir2('[B]Search >>>[/B]','url',23,icon,FANARTICO)	
	link = OPEN_URL(url)
	soup=bs(link)
	tag=soup.find('ul',{'class':'side-panel categories'})
	match=re.compile('<a href="(.+?)" title=".+?">(.+?)</a>').findall(str(tag))
	for url, name in match:
		url = "http://wallpaperswide.com%s" % url
		addDir('[B]'+name+'[/B]',url,21,icon,FANARTICO,'')
		
def Wallpapers_wide_content(name,url,description):
	link = OPEN_URL(url)
	for item in parse_dom(link, 'div', {'class': 'thumb'}):
		match = re.compile('<a href="(.+?)" title="(.+?)" itemprop=".+?">').findall(item)
		match2 = re.compile('<img src="(.+?)"').findall(item)
		for img in match2:
				for url, name in match:
					url = "http://wallpaperswide.com%s" % url
					addDir(name,url,22,img,img,'')
	for nextpage in parse_dom(link, 'div', {'class': 'pagination'}):
		match = re.compile('<a href="(.+?)">(\d+)</a>').findall(nextpage)
		for url,pageid in match:
			url = "http://wallpaperswide.com%s" % url
			addDir('Page ' + pageid + " >>>",url,21,icon,FANARTICO,'')				
def Wallpapers_wide_quality(name,url,iconimage):
	link = OPEN_URL(url)
	img = iconimage
	match = re.compile('<a target="_self" href="(.+?)" title=".+?">(.+?)</a>').findall(link)
	for url,name in match:
		liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
		liz.setInfo( type="Image", infoLabels={ "Title": name } )
		url = "http://wallpaperswide.com%s" % url
		liz.setProperty('fanart_image', img)		
		cm = []
		cm.append(('Download Item', 'RunPlugin(%s?mode=100&name=%s&url=%s&)'%(sys.argv[0],name,url)))
		liz.addContextMenuItems(cm, replaceItems=False)		
		xbmcplugin.addDirectoryItem(addon_handle, url, liz, False)

		
############ SEARCH ##############		
def SEARCH_Wallpaperwide(url):
	search_entered =''
	keyboard = xbmc.Keyboard(search_entered, 'Search')
	keyboard.doModal()
	if keyboard.isConfirmed(): search_entered = keyboard.getText()
	if len(search_entered)>1:
		search_entered = search_entered.replace(' ','%20')
		search_link = 'http://wallpaperswide.com/search.html?q=%s' % search_entered
		name = ''
		iconimage = ''
		Wallpapers_wide_content(name,search_link,iconimage)
def SEARCH_Hdwallpapers(url):
	search_entered =''
	keyboard = xbmc.Keyboard(search_entered, 'Search')
	keyboard.doModal()
	if keyboard.isConfirmed(): search_entered = keyboard.getText()
	if len(search_entered)>1:
		search_entered = search_entered.replace(' ','%20')
		search_link = 'http://www.hdwallpapers.in/search.html?q=%s' % search_entered
		name = ''
		iconimage = ''
		Hdwallpapers_content(name,search_link)

#################DOWNLOAD#####################

def Download_wallpapers(name,url):
	import datetime
	name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
	name = "wallpaper_" + name + ".jpg"
	path = download_dir
	dp = xbmcgui.DialogProgress()
	lib=os.path.join(path, name)
	dp.create("Diggz Wallpaper","Downloading ",'', 'Please Wait')		
	downloader.download(url, lib, dp)
	dialog.ok('[COLOR blue]Diggz Download Complete[/COLOR]' ,'Your Image is located at', '%s' % getSet('remote_path'),'This image has been succesfully added to Diggz Xenon')

#################MISC#########################
def getSet(name):
	return ADDON.getSetting(name)

def SETTINGS():
	xbmcaddon.Addon(id='plugin.image.easywallpapers').openSettings()
		
def OPEN_URL(url):
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
			   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
			   'Accept-Encoding': 'none',
			   'Accept-Language': 'en-US,en;q=0.8',
			   'Connection': 'keep-alive'}
        req = urllib.request.Request(url, headers=hdr)	
        # limit = int(scrapetimeout)
        response = urllib.request.urlopen(req, timeout=30)
        link=response.read()
        response.close()
        return link

def OPEN_URL2(url):
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
    response = urllib.request.urlopen(req)
    link=response.read()
    response.close()
    return link			

def addDir(name,url,mode,iconimage,fanart,description):
        u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)+"&fanart="+urllib.parse.quote_plus(fanart)+"&description="+str(description)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="image", infoLabels={ "Title": name } )
        liz.setProperty( "Fanart_Image", fanart )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok
def addDir1(name,url,mode,iconimage,fanart,description):
        u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)+"&fanart="+urllib.parse.quote_plus(fanart)+"&description="+str(description)
        ok=True
        liz=xbmcgui.ListItem(name)
        liz.setArt({'icon': "DefaultFolder.png", 'thumb': iconimage, 'fanart': fanart}) 
        liz.setInfo( type="image", infoLabels={ "Title": name } )
        liz.setProperty( "Fanart_Image", fanart )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
        return ok

def addDir2(name,url,mode,iconimage,fanart):
        u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)+"&fanart="+urllib.parse.quote_plus(fanart)
        ok=True
        liz=xbmcgui.ListItem(name)
        liz.setArt({'icon': "DefaultFolder.png", 'thumb': iconimage, 'fanart': fanart})
        liz.setInfo( type="Video", infoLabels={ "Title": name } )
        liz.setProperty( "Fanart_Image", fanart )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok       

def _getDOMContent(html, name, match, ret):
    end_str = "</%s" % (name)
    start_str = '<%s' % (name)

    start = html.find(match)
    end = html.find(end_str, start)
    pos = html.find(start_str, start + 1)

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(end_str, end + len(end_str))
        if tend != -1:
            end = tend
        pos = html.find(start_str, pos + 1)

    if start == -1 and end == -1:
        result = ''
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]
    else:
        result = ''

    if ret:
        endstr = html[end:html.find(">", html.find(end_str)) + 1]
        result = match + result + endstr

    return result

def _getDOMAttributes(match, name, ret):
    pattern = '''<%s[^>]* %s\s*=\s*(?:(['"])(.*?)\\1|([^'"].*?)(?:>|\s))''' % (name, ret)
    results = re.findall(pattern, match, re.I | re.M | re.S)
    return [result[1] if result[1] else result[2] for result in results]

def _getDOMElements(item, name, attrs):
    if not attrs:
        pattern = '(<%s(?: [^>]*>|/?>))' % (name)
        this_list = re.findall(pattern, item, re.M | re.S | re.I)
    else:
        last_list = None
        for key in attrs:
            pattern = '''(<%s [^>]*%s=['"]%s['"][^>]*>)''' % (name, key, attrs[key])
            this_list = re.findall(pattern, item, re.M | re. S | re.I)
            if not this_list and ' ' not in attrs[key]:
                pattern = '''(<%s [^>]*%s=%s[^>]*>)''' % (name, key, attrs[key])
                this_list = re.findall(pattern, item, re.M | re. S | re.I)
    
            if last_list is None:
                last_list = this_list
            else:
                last_list = [item for item in this_list if item in last_list]
        this_list = last_list
    
    return this_list

def parse_dom(html, name='', attrs=None, ret=False):
    if attrs is None: attrs = {}
    if isinstance(html, str):
        try:
            html = [html.decode("utf-8")]  # Replace with chardet thingy
        except:
            print("none")
            try:
                html = [html.decode("utf-8", "replace")]
            except:
                
                html = [html]
    elif isinstance(html, str):
        html = [html]
    elif not isinstance(html, list):
        
        return ''

    if not name.strip():
        
        return ''
    
    if not isinstance(attrs, dict):
        
        return ''

    ret_lst = []
    for item in html:
        for match in re.findall('(<[^>]*\n[^>]*>)', item):
            item = item.replace(match, match.replace('\n', ' ').replace('\r', ' '))

        lst = _getDOMElements(item, name, attrs)

        if isinstance(ret, str):
            lst2 = []
            for match in lst:
                lst2 += _getDOMAttributes(match, name, ret)
            lst = lst2
        else:
            lst2 = []
            for match in lst:
                temp = _getDOMContent(item, name, match, ret).strip()
                item = item[item.find(temp, item.find(match)):]
                lst2.append(temp)
            lst = lst2
        ret_lst += lst

    # log_utils.log("Done: " + repr(ret_lst), xbmc.LOGDEBUG)
    return ret_lst        
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
        
                      
params=get_params()
url=None
name=None
mode=None
iconimage=None
fanart=None
description=None


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
        fanart=urllib.parse.unquote_plus(params["fanart"])
except:
        pass
try:        
        description=int(params["description"])
except:
        pass


print("Mode: "+str(mode))
print("URL: "+str(url))
print("Name: "+str(name))
print("IconImage: "+str(iconimage))
        
        
if mode==None or url==None or len(url)<1:
        CATEGORIES()

elif mode==2:
        Wallpapers_wide(name,url)
elif mode==21:
        Wallpapers_wide_content(name,url,description)       
elif mode==22:
        Wallpapers_wide_quality(name,url,iconimage)
elif mode==23:
        SEARCH_Wallpaperwide(url)

elif mode==3:
        Hdwallpapers_list(name,url)
elif mode==31:
        Hdwallpapers_content(name,url)
elif mode==32:
        Hdwallpapers_quality(name,url,iconimage)
elif mode==33:
        SEARCH_Hdwallpapers(url)

elif mode==5:
        Diggz_content(name,url)
elif mode==51:
        Download_Diggz(name,url)

elif mode==100:
        Download_wallpapers(name,url)	
		
	
xbmcplugin.endOfDirectory(int(sys.argv[1]))

