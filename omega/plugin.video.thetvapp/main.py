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

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.thetvapp')
typi = addon.getSetting('typi')
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

UA = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'
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

def home():

    add_item('https://thetvapp.to/tv', 'Live TV', ikona, "listmovies",fanart=FANART, folder=True)
    add_item('https://thetvapp.to/nba', 'NBA', ikona, "listmovies",fanart=FANART, folder=True)
    add_item('https://thetvapp.to/mlb', 'MLB', ikona, "listmovies",fanart=FANART, folder=True)
    add_item('https://thetvapp.to/nhl', 'NHL', ikona, "listmovies",fanart=FANART, folder=True)
    add_item('https://thetvapp.to/nfl', 'NFL', ikona, "listmovies",fanart=FANART, folder=True)
	
def ListMovies(url):
	typix = addon.getSetting('typi')
	add_item('xxx', '[B][COLOR yellowgreen]---=== Play===--- [/COLOR] [COLOR gold]'+typix+'[/COLOR][/B]', ikona, "typi",fanart=FANART, folder=False, IsPlayable=False)
	ok = False
	html = sess.get(url, headers = headers, verify=False).text
	html = parseDOM(html,'ol', attrs={'class':"list.*?"} )[0].replace('<span>','').replace('</span>','').replace('\n','').replace('  ','').replace('@',' @')
	
	hreftitle = re.findall('href\s*=\s*"([^"]+)"\s*class.*?>([^<]+)<\/a>',html,re.DOTALL)

	for href,title in hreftitle:
		ok = True
		href = 'https://thetvapp.to'+href if href.startswith('/') else href
		add_item(href, title.replace('&amp;','&'), ikona, 'playvideo',fanart=FANART, folder=False, IsPlayable=True, infoLabels={'plot':title})

	if ok:
		xbmcplugin.endOfDirectory(addon_handle) 
	else:
		xbmcgui.Dialog().notification('[B]Info[/B]', 'No streams found',xbmcgui.NOTIFICATION_INFO, 6000)
		
def decr(e, i="Try9-Stubble9"):
### 	function Ul(e) {
### 	  const i = "Try9-Stubble9";
### 	  let o = "";
### 	  const l = atob(e);
### 	  for (let c = 0; c < l.length; c++) {
### 	    o += String.fromCharCode(l.charCodeAt(c) ^ i.charCodeAt(c % i.length));
### 	  }
### 	  return o;
### 	}


	if i == "requests":
		response = requests.get('https://raw.githubusercontent.com/matecky/bub/keys/keys.json', verify=False)
		xx = re.findall('\s+file\:\s*(\w*)\,',response.text,re.DOTALL+re.I)
		ff = None
		if xx:
			ff=re.findall(xx[0]+'\s*\=\s*(\w*)\(',response.text,re.DOTALL+re.I)

		if ff:
			key = re.findall('function\s*'+ff[0]+".*?'([^']+)'",response.text,re.DOTALL+re.I)
			if key:
				i=key[0]
			else:
				return ''
		else:
			return ''
		
	import base64
	l = base64.b64decode(e).decode('utf-8')
	o=''
	for c in range(len(e)):
	
		try:
			a=ord(l[c])
			b = ord(i[c%len(i)])
			o+=chr(a^b)
		except:
			pass
	
	return o   
def PlayVideo(url):	

	stream_url = ''
	html = sess.get(url, headers = headers, verify=False).text
	html = html.replace("\'",'"')
	ajax = re.findall('ajaxSetup(.*?)\$\.ajax',html,re.DOTALL)
	encrypt = re.findall('encryption"\s*content="([^"]+)"',html,re.DOTALL)
	encrypt2 = re.findall('const\s*|\w*encrypted\s*=\s*"([^"]+)"',html,re.DOTALL)
	kolejny =re.findall('player.setup.*?file\:\s*"([^"]+)"',(html.replace("\'",'"')),re.DOTALL+re.I)

	if ajax:
		url = re.findall('url\:\s*"([^"]+)"',ajax[0],re.DOTALL)[0]
		url = 'https://thetvapp.to'+url if url.startswith('/') else url
		tok = re.findall('csrf\-token"\s*content\s*=\s*"([^"]+)"',html,re.DOTALL)[0]
		headers.update({"X-CSRF-TOKEN": tok,"X-Requested-With":"XMLHttpRequest"}) #
		stream_url = sess.post(url, headers = headers, verify=False).text
	elif encrypt:
		stream_url = decr(encrypt[0])
	elif kolejny:
		stream_url = kolejny[0]
	elif encrypt2:
		stream_url = decr(encrypt2[0],"requests")
	if stream_url:	
		play_item = xbmcgui.ListItem(path=stream_url)

		play_item.setProperty("IsPlayable", "true")
		if typi =='ISA':
			play_item.setProperty('inputstream', 'inputstream.adaptive')
			play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
			play_item.setMimeType('application/vnd.apple.mpegurl')
			play_item.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')

		xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

def router(paramstring):
	params = dict(urllib_parse.parse_qsl(paramstring))
	if params:    
	
		mode = params.get('mode', None)
	
		if mode == 'listmovies':
			ListMovies(exlink)	
		elif mode == 'playvideo':
			PlayVideo(exlink)
		elif mode == 'typi':
			addon.setSetting('typi', 'DEFAULT') if typi == 'ISA' else addon.setSetting('typi', 'ISA')
			xbmc.executebuiltin('Container.Refresh')
	else:
		home()
		xbmcplugin.endOfDirectory(addon_handle)    
if __name__ == '__main__':
    router(sys.argv[2][1:])