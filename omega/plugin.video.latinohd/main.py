# -*- coding: UTF-8 -*-

import sys,re, ast 
import six
from six.moves import urllib_parse

import requests
from requests.compat import urlparse
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc, xbmcvfs

if six.PY3:
    basestring = str
    unicode = str
    xrange = range
    from resources.lib.cmf3 import parseDOM
else:
    from resources.lib.cmf2 import parseDOM
sess = requests.Session()    

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.latinohd')

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

try:
    inflabel = ast.literal_eval(params.get('ilabel', None))
except:
    inflabel = params.get('ilabel', None)
    
page = params.get('page',[1])[0]

def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(query)

def add_item(url, name, image, mode, itemcount=1, page=1,fanart=FANART, infoLabels=False,contextmenu=None,IsPlayable=False, folder=False):

    if six.PY3:    
        list_item = xbmcgui.ListItem(name)

    else:
        list_item = xbmcgui.ListItem(name, iconImage=image, thumbnailImage=image)
    if IsPlayable:
        list_item.setProperty("IsPlayable", 'True')    
        
    if not infoLabels:
        infoLabels={'title': name}    
    list_item.setInfo(type="video", infoLabels=infoLabels)    
    list_item.setArt({'thumb': image,'icon': image,  'poster': image, 'banner': image, 'fanart': fanart})
    
    if contextmenu:
        out=contextmenu
        list_item.addContextMenuItems(out, replaceItems=True)

    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url = build_url({'mode': mode, 'url' : url, 'page' : page, 'title':name,'image':image, 'ilabel':infoLabels}),            
        listitem=list_item,
        isFolder=folder)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")
    
def resp_text(resp):
    """Return decoded response text."""
    
    if resp and resp.headers.get('content-encoding') == 'br':
        from resources.lib.brotlipython import brotlidec
        out = []
        # terrible implementation but it's pure Python
        return brotlidec(resp.content, out).decode('utf-8')
    response_content = resp.text

    return response_content.replace("\'",'"')
    
    
def request_sess(url, method='get', data={}, headers={}, result=True, json=False, allow=True , json_data = False):
    if method == 'get':
        resp = sess.get(url, headers=headers, timeout=15, verify=False, allow_redirects=allow)
        
    elif method == 'post':
        if json_data:
            resp = sess.post(url, headers=headers, json=data, timeout=15, verify=False, allow_redirects=allow)
        else:
            resp = sess.post(url, headers=headers, data=data, timeout=15, verify=False, allow_redirects=allow)

    if result:
        return resp.json() if json else resp_text(resp)
    else:
        return resp
        
def home():

    add_item('', '[COLOR gold][B]Tele Latino HD[/B][/COLOR]', ikona, "latinohd", folder=True, IsPlayable=False)
    add_item('', '[COLOR lightblue][B]Buscar canal...[/B][/COLOR]', ikona, "szukaj", folder=True, IsPlayable=False)

def LatinoHd(szuk = False):
	headers = {
	'Host': 'www.telelatinohd.com',
	'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0',
	'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
	'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
	'dnt': '1',
	'upgrade-insecure-requests': '1',
	'sec-fetch-dest': 'document',
	'sec-fetch-mode': 'navigate',
	'sec-fetch-site': 'none',
	'sec-fetch-user': '?1',
	
	}

	html = request_sess('https://www.telelatinohd.com/', 'get', headers=headers)
	ids = [(a.start(), a.end()) for a in re.finditer('canal-item ', html)]
	ids.append( (-1,-1) )
	hosty =[]
	ok = False
	for i in range(len(ids[:-1])):
		subset = html[ ids[i][1]:ids[i+1][0] ]
		href = parseDOM(subset,'a', ret="href")[0]
		if 'telelatinohd' in href:

			
			tit = parseDOM(subset,'h4')[0]
			try:
				tit = tit.encode('latin-1').decode('utf-8')  
			except:
				tit = tit
			img = parseDOM(subset,'img', ret="src")[0]
			if szuk:
				if szuk.lower() in tit.lower():
					ok = True
					add_item(href, '[B]'+tit+'[/B]', img, "listplaylatino",fanart=FANART, folder=True, IsPlayable=False)
			else:
				ok = True
				add_item(href, '[B]'+tit+'[/B]', img, "listplaylatino",fanart=FANART, folder=True, IsPlayable=False)
	if ok:
		xbmcplugin.endOfDirectory(addon_handle)


def ListPlayLatino(url):   
    UAx = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0'
    headers = {
    'Host': 'www.telelatinohd.com',
    'user-agent': UAx,
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
    'dnt': '1',
    'upgrade-insecure-requests': '1',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    
    }
    zz=''
    html = request_sess(url, 'get', headers=headers)
    ok = False
    for href,title in re.findall('target="iframe" href="([^"]+)">([^<]+)<',html,re.DOTALL):
        ok =True
        title = title.encode('latin-1').decode('utf-8')
        add_item(href, nazwa+' [COLOR lightgreen]'+title+'[/COLOR]', rys, "playlatino",fanart=FANART, folder=False, IsPlayable=True)
    if not ok:
        nturl = parseDOM(html, 'iframe', ret='src')[0]
        if 'live' in nturl:
            ok = True
            add_item(url, nazwa+' [COLOR lightgreen](WATCH)[/COLOR]', rys, "playlatino",fanart=FANART, folder=False, IsPlayable=True)
    if ok:
        xbmcplugin.endOfDirectory(addon_handle)

def PlayLatino(url):
	stream_url =''
	try:
		from requests.compat import urlparse
	
	
		pa2 = dict(urllib_parse.parse_qsl(urlparse(url).query))
		if 'url' in pa2 and 'kid' in pa2:
			import base64
			st_u = re.findall('url\=(.*?)\&',url,re.DOTALL)[0]

			st_u = base64.b64decode(st_u).decode("utf-8")
			st_ux = 'https'+st_u
			playitem = xbmcgui.ListItem(path=st_ux)
			playitem.setProperty('inputstream', 'inputstream.adaptive')
			playitem.setProperty("IsPlayable", "true")
			
			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
				'Accept': '*/*',
				'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
				# 'Accept-Encoding': 'gzip, deflate, br',
				'Origin': 'https://embed.telelatinohd.com',
				'DNT': '1',
				'Connection': 'keep-alive',
				'Sec-Fetch-Dest': 'empty',
				'Sec-Fetch-Mode': 'cors',
				'Sec-Fetch-Site': 'cross-site',
			#	'If-None-Match': 'bpk-3FACDECB',
			}
			hea= '&'.join(['%s=%s' % (name, urllib_parse.quote(value)) for (name, value) in headers.items()]) 
			
			
			playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
			playitem.setProperty('inputstream.adaptive.manifest_headers', hea)
			xbmcplugin.setResolvedUrl(addon_handle, True, listitem=playitem)
			#xbmcgui.Dialog().notification('[B]Error[/B]', "Can't play this stream!",xbmcgui.NOTIFICATION_INFO, 6000,False)
			return
			#ac=''
		else:
			pass
	except:
		pass
	if 'clarovideo.repl' in url:
		xbmcgui.Dialog().notification('[B]Error[/B]', "Can't play this stream!",xbmcgui.NOTIFICATION_INFO, 6000,False)
		return
	UAx = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
	headers = {
	'Host': 'www.telelatinohd.com',
	'user-agent': UAx,
	'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
	'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
	'dnt': '1',
	'referer': 'https://www.telelatinohd.com/',
	'upgrade-insecure-requests': '1',
	'sec-fetch-dest': 'document',
	'sec-fetch-mode': 'navigate',
	'sec-fetch-site': 'none',
	'sec-fetch-user': '?1',
	
	}
	
	if 'livestream' in url and 'php' in url:
		
		headers = {
			'Host': 'live.telelatinohd.com',
			'User-Agent': UAx,
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
			'Referer': 'https://www.telelatinohd.com/',
			'Upgrade-Insecure-Requests': '1',
			'Sec-Fetch-Dest': 'iframe',
			'Sec-Fetch-Mode': 'navigate',
			'Sec-Fetch-Site': 'same-site',
			'Sec-Fetch-User': '?1',
		}
	
		nturl3 = 'https://live.telelatinohd.com'
		html = request_sess(url, 'get', headers=headers, result=False).text
	
	else:
		html = request_sess(url, 'get', headers=headers)
	
	nturl = parseDOM(html, 'iframe', ret='src')#[0]
	if nturl:
		nturl = nturl[0]
		headers.update({'referer': url})
		if 'livestream' in nturl and 'php' in nturl:
			headers = {
				'Host': 'live.telelatinohd.com',
				'User-Agent': UAx,
				'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
				'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
				'Referer': 'https://www.telelatinohd.com/',
				'Upgrade-Insecure-Requests': '1',
				'Sec-Fetch-Dest': 'iframe',
				'Sec-Fetch-Mode': 'navigate',
				'Sec-Fetch-Site': 'same-site',
				'Sec-Fetch-User': '?1',
			}
		
			nturl3 = 'https://live.telelatinohd.com'
			html = request_sess(nturl, 'get', headers=headers, result=False).text
		else:
			html = request_sess(nturl, 'get', headers=headers)
	nturl2 = re.findall('href\s*=\s*"([^"]+)"\s*onmou',html,re.DOTALL)#[0]
	if nturl2:
		nturl2 = nturl2[0]
		headers.update({'referer': nturl})
		html = request_sess(nturl2, 'get', headers=headers)
		nturl3 = parseDOM(html, 'iframe', ret='src')[0]
		headers.update({'referer': nturl2})
		resp = request_sess(nturl3, 'get', headers=headers, result=False)
		
		html = resp.text
	packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
	packeds = packer.findall(html)
	unpacked = ''
	stream_url = ''
	if packeds:
		import resources.lib.jsunpack as jsunpack
		for packed in packeds:
			packed = packed.replace('\\\\','\\')
			unpacked += jsunpack.unpack(packed)
	if unpacked:
		import base64
		try:
			vidmultibase64 = re.findall('mariocscryptold\("([^"]+)"',unpacked,re.DOTALL+re.I)[0]
	
		except:
			vidmultibase64 = re.findall('\("([^"]+)"',unpacked,re.DOTALL)[0]
		for x in range(10):
			try:
				
				vidmultibase64 = base64.b64decode(vidmultibase64).decode("utf-8")
				if 'http' in vidmultibase64:
					stream_url = vidmultibase64
					break
			except:
				pass
				
	if stream_url:
		headers.update({'referer': 'https://live.telelatinohd.com/'})
	
		html = request_sess(stream_url, 'get', headers=headers)
		if '404 not found' in html.lower():
			xbmcgui.Dialog().notification('[B]Error[/B]', 'Stream is OFFLINE!!!',xbmcgui.NOTIFICATION_INFO, 6000,False)
			sys.exit(1)
		else:
			certificate_data = "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"
			stream_url += '|User-Agent='+UAx+'&Referer='+urllib_parse.quote_plus(nturl3)
			hdrs = 'User-Agent='+UAx+'&Referer='+urllib_parse.quote_plus(nturl3)
			play_item = xbmcgui.ListItem(path=stream_url)
			play_item.setProperty('inputstream', 'inputstream.ffmpegdirect')
	
			play_item.setMimeType('application/x-mpegurl')
	
			play_item.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
			play_item.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
			play_item.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
	
			xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item) 

def router(paramstring):
	params = dict(urllib_parse.parse_qsl(paramstring))
	if params:    
		mode = params.get('mode', None)
	
		if mode == 'playlatino':
			PlayLatino(exlink)    
	
			
		elif mode == 'latinohd':
			LatinoHd()
			
		#elif mode =='listsubmenulatino':
		#    ListSubmenuLatino(exlink)
		elif mode =='listplaylatino':
			ListPlayLatino(exlink)
		elif mode =='szukaj':
			query = xbmcgui.Dialog().input(u'Buscar canal...', type=xbmcgui.INPUT_ALPHANUM)
			if query:  
				try:
					query = query.encode('latin-1').decode('utf-8')  
				except:
					query = query
				LatinoHd(query)
			#	ListMovies(url,'1')
			
			
	else:
		home()
		xbmcplugin.endOfDirectory(addon_handle)    
if __name__ == '__main__':
    router(sys.argv[2][1:])