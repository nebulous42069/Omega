# -*- coding: UTF-8 -*-
from __future__ import division
import sys, re, os, io
import six
from six.moves import urllib_parse

import time
import ast
import requests
from requests.compat import urlparse

import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc, xbmcvfs

import inputstreamhelper

from resources.lib.brotlipython import brotlidec
import json

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
addon = xbmcaddon.Addon(id='plugin.video.lookmovietomb')

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
	infol = ast.literal_eval(urllib_parse.unquote_plus(params.get('infoLabels', None)))

except:
	infol = {}
page = params.get('page',[1])

UA =  'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
TIMEOUT=15
mainurl = 'https://www.lookmovie2.to{}'


proxyport = addon.getSetting('proxyport')
playt = addon.getSetting('play')
headers = {'User-Agent': UA}
sess = requests.Session()

fsortv = addon.getSetting('fsortV')
fsortn = addon.getSetting('fsortN') if fsortv else 'newest first'

fkatv = addon.getSetting('fkatV')
fkatn = addon.getSetting('fkatN') if fkatv else 'all'

frokv = addon.getSetting('frokV')
frokn = addon.getSetting('frokN') if frokv else 'all'

fratyv = addon.getSetting('fratyV')
fratyn = addon.getSetting('fratyN') if fratyv else 'all'

sratyv = addon.getSetting('sratyV')
sratyn = addon.getSetting('sratyN') if sratyv else 'all'

ssortv = addon.getSetting('ssortV')
ssortn = addon.getSetting('ssortN') if ssortv else 'newest first'

skatv = addon.getSetting('skatV')
skatn = addon.getSetting('skatN') if skatv else 'all'

srokv = addon.getSetting('srokV')
srokn = addon.getSetting('srokN') if srokv else 'all'

dataf =  addon.getSetting('fdata')	
datas =  addon.getSetting('sdata')



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

    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url = build_url({'mode': mode, 'url' : url, 'page' : page, 'title':name,'image':image, 'infoLabels':urllib_parse.quote_plus(str(infoLabels))}),            
        listitem=list_item,
        isFolder=folder)
    xbmcplugin.addSortMethod(addon_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE, label2Mask = "%R, %Y, %P")

def home():

    add_item('movies', '[COLOR khaki][B]Movies[/COLOR][/B]', ikona, "listmenus",fanart=FANART, folder=True)
    add_item('series', '[COLOR khaki][B]TV Shows[/COLOR][/B]', ikona, "listmenus",fanart=FANART, folder=True)

def save_file(file, data, isJSON=False):
	with io.open(file, 'w', encoding="utf-8") as f:
		if isJSON == True:
			str_ = json.dumps(data,indent=4, sort_keys=True,separators=(',', ': '), ensure_ascii=False)
			f.write(str(str_))
		else:
			f.write(data)
	return
	
	
def load_file(file, isJSON=False):
	import collections
	if not os.path.isfile(file):
		return None
	
	with io.open(file, 'r', encoding='utf-8') as f:
		if isJSON == True:
			return json.load(f, object_pairs_hook=collections.OrderedDict)
		else:
			return f.read()
	
try:
	kukis = load_file(DATAPATH+'kukis', isJSON=True)
except:
	kukis = {}
	
def CreateCookies():
	zz=''
	url ='https://www.lookmovie2.to/'
	resp = sess.get(url, headers = headers, verify=False)

	cookies = (resp.cookies).get_dict()
	save_file(file=DATAPATH+'kukis', data=cookies, isJSON=True)
	return

def ListMenus(cd):
	CreateCookies()
	if 'movies' in cd:
		add_item('https://www.lookmovie2.to/movies/page/1', '[B][COLOR gold] >>>> MOVIES <<<< [/COLOR][/B]', ikona, 'nic',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies'})
		add_item('f', 'Filters', ikona, 'listfilters',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'Movies - categories'})

	
		add_item('https://www.lookmovie2.to/movies/page/1', 'Latest', ikona, 'listmovies',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'Movies - latest'})
		add_item('https://www.lookmovie2.to/movies/', 'Categories', ikona, 'listcateg',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'Movies - categories'})

		add_item('https://www.lookmovie2.to/movies/search/page/1?q=', 'Search', ikona, 'search',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies - search'})
	

	
	
	else:
		add_item('https://www.lookmovie2.to/movies/page/1', '[B][COLOR gold] >>>> TV SHOWS <<<< [/COLOR][/B]', ikona, 'nic',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'TV shows'})
		add_item('s', 'Filters', ikona, 'listfilters',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'Movies - categories'})

		
		
		add_item('https://www.lookmovie2.to/shows?page=1', 'Latest', ikona, 'listmovies',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'TV shows - latest'})
		add_item('https://www.lookmovie2.to/shows', 'Categories', ikona, 'listcateg',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'TV shows - categories'})
		add_item('https://www.lookmovie2.to/shows/search/page/1?q=', 'Search', ikona, 'search',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'TV shows - search'})
	
		
	xbmcplugin.endOfDirectory(addon_handle) 
def ListFilters(url):
	rokn = srokn if 's' in url else frokn
	sortn = ssortn if 's' in url else fsortn
	katn = skatn if 's' in url else fkatn
	ratyn = sratyn if 's' in url else fratyn
	

	if 's' in url:
		add_item('https://www.lookmovie2.to/movies/page/1', '[B][COLOR gold] >>>> TV SHOWS <<<< [/COLOR][/B]', ikona, 'nic',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'TV shows'})
		add_item('https://www.lookmovie2.to/shows/filter/page/1'+datas, '[B]List TV shows with filters:[/B]', ikona, 'listmovies',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'Movies - latest'})

	else:
		add_item('https://www.lookmovie2.to/movies/page/1', '[B][COLOR gold] >>>> MOVIES <<<< [/COLOR][/B]', ikona, 'nic',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'TV shows'})
		add_item('https://www.lookmovie2.to/page/1'+dataf, '[B]List movies with filters:[/B]', ikona, 'listmovies',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':'Movies - latest'})

	add_item('emp', "-	[COLOR lightblue]genre:[/COLOR] [B]"+katn+'[/B]', ikona, 'filtr:'+url+'kat',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies - search'})
	
	add_item('emp', "-	[COLOR lightblue]year:[/COLOR] [B]"+rokn+'[/B]', ikona, 'filtr:'+url+'rok',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies - search'})
	
	add_item('emp', "-	[COLOR lightblue]rating:[/COLOR] [B]"+ratyn+'[/B]', ikona, 'filtr:'+url+'raty',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies - search'})
	add_item('emp', "-	[COLOR lightblue]sorting:[/COLOR] [B]"+sortn+'[/B]', ikona, 'filtr:'+url+'sort',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies - search'})
	if 's' in url:
		add_item('https://www.lookmovie2.to/shows/search/page/1?q=', '[COLOR yellowgreen][B]Search TV SHOWS[/COLOR][/B]', ikona, 'search',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'TV shows - search'})
	else:
		add_item('https://www.lookmovie2.to/movies/search/page/1?q=', '[COLOR yellowgreen][B]Search MOVIES[/COLOR][/B]', ikona, 'search',fanart=FANART, folder=False, IsPlayable=False, infoLabels={'plot':'Movies - search'})
	

	
	xbmcplugin.endOfDirectory(addon_handle) 

def ListCateg(url):
	html = sess.get(url, headers = headers, cookies=kukis, verify=False).text

	result = re.findall('>categories(.*?)<\/ul>',html,re.DOTALL+re.I)[0]
	
	for categ in parseDOM(result,'li'):
		href = parseDOM(categ,'a', ret="href")[0]
		href = 'https://www.lookmovie2.to'+href if href.startswith('/') else href
		title = parseDOM(categ,'a')[0]
		add_item(href+'/page/1', title, ikona, 'listmovies',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':title})

	xbmcplugin.endOfDirectory(addon_handle) 

def ListMovies(url, pg):

	if not '?q=' in url:
		if '.to/shows' in url:
			if '?g[]=' in url:
				pass
			else:
				if '?page=' in url:
					url = re.sub('\?page\=\d+','?page=%d'%int(pg),url)
				else:
					url = url + '?page=%d' %int(pg)	
		else:
		
			if '/page/' in url:
				url = re.sub('/page/\\d+','/page/%d'%int(pg),url)
			else:
				url = url + '/page/%d' %int(pg)	
	else:
		if '/page/' in url:
			url = re.sub('/page/\\d+','/page/%d'%int(pg),url)
		else:
			url = url + '/page/%d' %int(pg)	
	np = '/page/%d?'%int(int(pg)+1)#?&g[]=
	#nextpage = unicode(int(pg)+1)
	html = sess.get(url, headers = headers, cookies=kukis, verify=False).text
	if '/shows?'  in url:
		ntpage = re.findall('li\s*class\s*=\s*"\s*next\s*"><a\s*href\s*=\s*"([^"]+)"', html,re.DOTALL+re.I)
	else:
		#if '?g[]=' in url and '/shows/' in url:
		#	ntpage = re.findall('li\s*class\s*=\s*"\s*next\s*"><a\s*href\s*=\s*"([^"]+)"', html,re.DOTALL+re.I)
		#else:
		ntpage = re.findall('pagination_next"\s*href\s*=\s*"([^"]+)"', html,re.DOTALL+re.I)
	
	ntpage = ntpage[0] if ntpage else ''
	ntpage = 'https:' + ntpage if ntpage.startswith('//') else ntpage

	ntpage = 'https://www.lookmovie2.to' + ntpage if ntpage.startswith('/shows') else ntpage
	npage = True if ntpage != "" else False
	if '?g[]=' in url:
		npage = True if np in ntpage else False
	
	ids = [(a.start(), a.end()) for a in re.finditer('<div\s*class\s*=\s*"movie\-item', html)] 
	ids.append( (-1,-1) )
	l = 1
	ok = False

	for i in range(len(ids[:-1])):
		item = html[ ids[i][1]:ids[i+1][0] ]
		
		href = parseDOM(item,'a', ret="href")[0]
		
		
		href = 'https://www.lookmovie2.to'+href if href.startswith('/') else href
		href = href.replace('/movies/view/', '/movies/play/')
		href = href.replace('/shows/view/', '/shows/play/')

		img = parseDOM(item,'img', ret="data-src")
		img = img[0] if img else ikona

		year = re.findall('year">([^<]+)<',item)
		year = year[0] if year else ''
		tit_tag = parseDOM(item,'h6')

		if '/shows?' in url or '/shows/' in url:
			title = tit_tag[0].replace('\n','').strip(' ')
			if 'href=' in title:
				title = parseDOM(title,'a')[0]
			info_data = parseDOM(item,'div', attrs={'class':"mv-item-infor" })
			if info_data:
				plot = parseDOM(info_data[0],'p')
				plot = plot[0] if plot else title
			else:
				plot = title
			mod = 'listserial' 
		else:
			
			title = parseDOM(tit_tag[0],'a')[0].replace('\n','').strip(' ')
			plot = title
			mod = 'listlinks' 
		
		ispla = False
		fold = True
		add_item(href, title, img, mod,fanart=FANART, folder=fold, IsPlayable=ispla, infoLabels={'plot':plot, 'year':year})
		ok = True
	if npage:
		add_item(ntpage, '>> next page >>' ,RESOURCES+'right.png', "listmovies",fanart=FANART, page=str(int(pg)+1), folder=True)
	if ok:
		xbmcplugin.endOfDirectory(addon_handle) 

def splitToSeasons(input, main_tit):
	out={}
	seasons = [x.get('season') for x in input]

	for s in set(seasons):

		out[main_tit+' - Season %02d'%s]=[input[i] for i, j in enumerate(seasons) if j == s]
	return out
	
def ListSerial(urlk,img):

	url2 = urlk.replace( '/shows/play/','/shows/view/')
	html = sess.get(url2, headers = headers, cookies=kukis, verify=False).text
	html = html.replace("\'",'"')
	plot = ''
	plot_data = parseDOM(html,'div', attrs={'class':"description-wrapper"} )
	if plot_data:
		plot = parseDOM(plot_data[0],'p')
		plot = plot[0] if plot else ''
	
	resp = sess.get(urlk, headers = headers, cookies=kukis, verify=False)#.text
	urlnew = resp.url
	html = resp.text

	html = html.replace('\\"',"'")
	html = html.replace("\'",'"')
	if 'g-recaptcha' in html:
		html = resolveCaptcha(html,urlk, urlnew)
	dt = re.findall('show_storage"\]\s*=\s*({.*?};\\n\s+)',html,re.DOTALL)

	
	
	dt = dt[0].replace('\\"',"'").replace('\n','').replace('   ', '')
	main_title = re.findall('title\:\s*"([^"]+)"',dt,re.DOTALL)[0]
	hash_ = re.findall('hash\:\s*"([^"]+)"',dt,re.DOTALL)[0]
	expire_ = re.findall('expires\:\s*(\d+)',dt,re.DOTALL)[0]

	seasons = re.findall('seasons\:\s*(\[.*?\])',dt,re.DOTALL)
	sezony = list( dict.fromkeys(re.findall('season\:\s*"(\d+)"',seasons[0],re.DOTALL)))
	out=[]
	for sez in sezony:
		for episode in re.findall('(\{.*?}),',seasons[0],re.DOTALL):
			print(episode)
			if re.findall('season\:\s*"(\d+)"',episode,re.DOTALL)[0] == sez:
				epis = re.findall('episode\:\s*"(\d+)"',episode,re.DOTALL)[0]
				id_epis = re.findall('id_episode\:\s*(\d+)',episode,re.DOTALL)[0]
				try:
					title = re.findall('title\:\s*"([^"]+)"',episode,re.DOTALL)[0]
				except:
					title = 'S%02dE%02d'%(int(sez),int(epis))
					pass
				title = '[B][COLOR khaki]'+main_title+'[/COLOR] '+ title + ' (S%02dE%02d)[/B]'%(int(sez),int(epis))
				plot = plot if plot != '' else title
				out.append({'title':title,'href':id_epis+'|'+hash_+'|'+str(expire_)+'|'+title, 'img':img, 'fnrt':FANART, 'plot':plot, 'season' : int(sez),'episode' : int(epis) })
	sezony =  splitToSeasons(out,main_title)
	
	for i in sorted(sezony.keys()):
		ac=urllib_parse.quote_plus(str(sezony[i]))

		add_item(ac, i, img, 'listepisodes',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':main_title})
	xbmcplugin.endOfDirectory(addon_handle) 
	
def ListEpisodes(exlink):
	import ast

	episodes = ast.literal_eval(urllib_parse.unquote_plus(exlink))
	
	itemz=episodes
	items = len(episodes)
	
	for f in itemz:

		add_item(f.get('href'), f.get('title'), f.get('img'), 'listlinks',fanart=FANART, folder=True, IsPlayable=False, infoLabels={'plot':f.get('plot')})

	xbmcplugin.endOfDirectory(addon_handle) 

def girc(page_data, url, size='invisible'):

	"""
	Code adapted from https://github.com/vb6rocod/utils/
	Copyright (C) 2019 vb6rocod
	and https://github.com/addon-lab/addon-lab_resolver_Project
	Copyright (C) 2021 ADDON-LAB, KAR10S
	"""
	from requests.compat import urlparse
	import re, random, string
	domain = urlparse(url).netloc
	host = 'https://'+ domain
	import base64
	
	co = base64.b64encode((host + ':443').encode('utf-8')).decode('utf-8').replace('=', '')
	hdrs = {'Referer': url}
	rurl = 'https://www.google.com/recaptcha/api.js'
	aurl = 'https://www.google.com/recaptcha/api2'
	key = re.search(r"""(?:src="{0}\?.*?render|data-sitekey)=['"]?([^"']+)""".format(rurl), page_data)
	if key:
		key = key.group(1)
		# rurl = '{0}?render={1}'.format(rurl, key)

		page_data1 = requests.get(rurl, headers=hdrs).text
		v = re.findall('releases/([^/]+)', page_data1)[0]
		rdata = {'ar': 1,
				'k': key,
				'co': co,
				'hl': 'it',
				'v': v,
				'size': size,
				'sa': 'submit',
				'cb': ''.join([random.choice(string.ascii_lowercase + string.digits) for i in range(12)])}

		page_data2 = requests.get('{0}/anchor?{1}'.format(aurl, urllib_parse.urlencode(rdata)), headers=hdrs).text
		
		rtoken = re.search('recaptcha-token.+?="([^"]+)', page_data2)
		if rtoken:
			rtoken = rtoken.group(1)
		else:
			return ''
		pdata = {'v': v,
				'reason': 'q',
				'k': key,
				'c': rtoken,
				'sa': '',
				'co': co}
		hdrs.update({'Referer': aurl})	
		page_data3 = requests.post('{0}/reload?k={1}'.format(aurl, key), data=pdata, headers=hdrs).text
		gtoken = re.search('rresp","([^"]+)', page_data3)
		if gtoken:
			return gtoken.group(1)
	
	return ''
def resolveCaptcha(html, urlk, urlnew):
	kukis2 = load_file(DATAPATH+'kukis', isJSON=True)
	token = girc(html,urlk)
	csr= re.findall('csrf\-token"\s*content="([^"]+)"',html,re.DOTALL) 
	if csr:
		csr = csr[0]
		
	
		headersx = {
			'Host': 'www.lookmovie2.to',
			'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
			'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
			'content-type': 'application/x-www-form-urlencoded',
			'origin': 'https://www.lookmovie2.to',
			'dnt': '1',
			'referer': urlnew, 
			'upgrade-insecure-requests': '1',
			'sec-fetch-dest': 'document',
			'sec-fetch-mode': 'navigate',
			'sec-fetch-site': 'same-origin',
	
		}
	
		data = {
			'_csrf': csr,
			'tk': token,
		}
		
		resp = sess.post(urlnew, headers=headersx, data= data, cookies=kukis2, verify=False)
		urlnew2 = resp.url
		html=resp.text	
		from resources.lib import recaptcha_v2
		
		sitek = re.findall('data\-sitekey\s*=\s*"([^"]+)"',html,re.DOTALL) [0]
	
		token = recaptcha_v2.UnCaptchaReCaptcha().processCaptcha(sitek, lang='en')
	
		csr= re.findall('csrf\-token"\s*content="([^"]+)"',html,re.DOTALL) 
		if csr:
			csr = csr[0]
			headersx = {
				'Host': 'www.lookmovie2.to',
				'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
				'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
				'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
				'content-type': 'application/x-www-form-urlencoded',
				'origin': 'https://www.lookmovie2.to',
				'dnt': '1',
				'referer': urlnew, 
				'upgrade-insecure-requests': '1',
				'sec-fetch-dest': 'document',
				'sec-fetch-mode': 'navigate',
				'sec-fetch-site': 'same-origin',
	
			}
	
			data = {
				'_csrf': csr,
				'g-recaptcha-response': token,
				}
				
			resp = sess.post(urlnew2, headers=headersx, data= data, cookies=kukis2, verify=False)
			urlnew2 = resp.url
			html=resp.text	
			if 'window.location.href' in html:
				cookies = (sess.cookies).get_dict()
				save_file(file=DATAPATH+'kukis', data=cookies, isJSON=True)
				
				resp = sess.get(urlk, headers = headers, cookies=kukis, verify=False)#.text
	
				
				
				urlnew = resp.url
				html = (resp.text).replace("\'",'"')
	return html		
			
			
			
	
def ListLinks(urlk, ima = None):

	try:
		ac=json.loads(infol)
	except:
		pass
	
	if '|' in urlk:
		
		id_episode, hash_, expires_, title = urlk.split('|')
		plot = title
		try:
			plot = infol.get('plot', None)
		except:
			plot = title
		
		ac=''
		url = 'https://www.lookmovie2.to/api/v1/security/episode-access'
		year = ''
		params = {
			'id_episode': id_episode,
			'hash': hash_,
			'expires': expires_
		}
		urlk = 'https://www.lookmovie2.to/shows' 
	else:
		url2 = urlk.replace( '/movies/play/','/movies/view/')
		kukis2 = load_file(DATAPATH+'kukis', isJSON=True)
		html = sess.get(url2, headers = headers, cookies=kukis2, verify=False).text
		html = html.replace("\'",'"')

		plot = ''
		plot_data = parseDOM(html,'div', attrs={'class':"description-wrapper"} )
		if plot_data:
			plot = parseDOM(plot_data[0],'p')
			plot = plot[0] if plot else ''
		resp = sess.get(urlk, headers = headers, cookies=kukis2, verify=False)#.text
		urlnew = resp.url
		html = (resp.text).replace("\'",'"')

		if 'g-recaptcha' in html:
			html = resolveCaptcha(html,urlk, urlnew)
		

		dt = re.findall('movie_storage"\]\s*=\s*({.*?})',html,re.DOTALL)
		#if dt:
		if not dt:
			return
		title = re.findall('title\s*\:\s*"([^"]+)"',dt[0],re.DOTALL)[0]
		plot = plot if plot !='' else title
		year = re.findall('year\s*\:\s*"([^"]+)"',dt[0],re.DOTALL)
		year = year[0] if year else ''
		hash_ = re.findall('hash\s*\:\s*"([^"]+)"',dt[0],re.DOTALL)[0]
		id_movie = re.findall('id_movie\s*\:\s*(\d+)',dt[0],re.DOTALL)[0]
		expires = re.findall('expires\s*\:\s*(\d+)',dt[0],re.DOTALL)[0]
		params = {
			'id_movie': str(id_movie),
			'hash': hash_,
			'expires': str(expires)}
			
		headers.update({'Referer': urlk, 'X-Requested-With': 'XMLHttpRequest'})	
		
		url = 'https://www.lookmovie2.to/api/v1/security/movie-access'
	html = sess.get(url, headers = headers, cookies=kukis, params = params, verify=False).json()
	vid_source = [x for x in list((html.get('streams', None)).values()) if x][0]
	add_item(vid_source+'|'+urlk, '[B]'+title + '[/B]', ima, 'playvid',fanart=FANART, folder=False, IsPlayable=True, infoLabels={'plot':plot,'year':year})

	subtitles = html.get('subtitles', None)
	for subt in subtitles:
		lang = subt.get('language', None)
		if isinstance(subt.get('file', None), basestring):

			subt_url = 'https://www.lookmovie2.to'+subt.get('file', None)

			t2='[B]'+title + '[/B] [I](subtitle: %s)[/I]'%(lang)
			add_item(vid_source+'|'+urlk+'|nap='+subt_url, t2, ima, 'playvid',fanart=FANART, folder=False, IsPlayable=True, infoLabels={'plot':plot,'year':year})

	xbmcplugin.endOfDirectory(addon_handle, cacheToDisc=True)
	
def PlayVid(url, ima):
	if '|nap=' in url:
		vid_source, ref, subt = url.split('|')
		subt = subt.replace('nap=', '')
	else:
		vid_source, ref = url.split('|')
		subt = None
	is_helper = inputstreamhelper.Helper('hls')
	if is_helper.check_inputstream():
		play_item = xbmcgui.ListItem(path=vid_source)
	
		if sys.version_info >= (3,0,0):
			play_item.setProperty('inputstream', is_helper.inputstream_addon)
		else:
			play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
	
	play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
	play_item.setMimeType('application/vnd.apple.mpegurl')
#	#	play_item.setMimeType('application/x-mpegurl')
#	##	play_item.setProperty('inputstream.adaptive.manifest_headers', abcv)
	if subt:
		play_item.setSubtitles([subt])
	play_item.setContentLookup(False)
	xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

	
def pla():

	if addon.getSetting('play') == 'default':
		return True
	else:
		return False


def router(paramstring):
	params = dict(urllib_parse.parse_qsl(paramstring))
	if params:    
	
		mode = params.get('mode', None)
	
		if mode == 'listmovies':
			ListMovies(exlink, page)	
		elif mode == 'menu':
			menu(exlink)
		elif mode == 'listsubmenu':
			submenu(exlink)

		elif mode == 'listserial':
			ListSerial(exlink,rys)
		elif mode == 'listlinks':
			ListLinks(exlink, rys)
			
		elif mode == 'playvid':
			PlayVid(exlink, rys)
		elif mode == 'listepisodes':
			ListEpisodes(exlink)
		elif mode == 'listsearch':
			ListSearch(exlink)
		elif mode == 'search':
			query = xbmcgui.Dialog().input(u'Search: ', type=xbmcgui.INPUT_ALPHANUM)
			if query:   
				query=query.replace(' ','+')
				urlk = build_url({'mode': 'listmovies', 'url' : exlink+query, 'page':'1'})
				xbmc.executebuiltin('Container.Update(%s)'% urlk)

		elif mode == 'listgenre':
			listgenre(exlink)
			
			
		elif mode =='nic':
			return
		elif mode == 'listcateg':
			ListCateg(exlink)
		elif mode == 'listmenus':
			ListMenus(exlink)
		
		elif mode == 'sett':
			addon.setSetting('play', 'default') if playt == 'proxy' else addon.setSetting('play', 'proxy')
			xbmc.executebuiltin('Container.Refresh')
			
		elif mode == 'listfilters':
			ListFilters(exlink)
			
		elif 'filtr:' in mode:
			ff = mode.split(':')[1]
			if 'rok' in ff:
				dd='year:'
				label = [str(x) for x in xrange(1913,2026)][::-1]#.insert(0,'all')
				label.insert(0,'all')
				value =  ['&y[]='+str(x) for x in xrange(1913,2026)][::-1]
				value.insert(0,'&y[]=')
			elif 'raty' in ff:
				dd= 'rating:'
				label=['all',"9+","8+","7+","6","5+","4+","3+","2+","1+"]
				value=['&r=',"&r=9","&r=8","&r=7","&r=6","&r=5","&r=4","&r=3","&r=2","&r=1"]
			elif 'kat' in ff:
				dd= 'genre:'
				if 'fkat' in ff:
					label=['all',"action", "adventure", "animation", "comedy", "crime", "drama", "documentary", "science fiction", "family", "history", "horror", "fantasy", "music", "mystery", "romance", "thriller", "war", "western"]
					value=['?g[]=', "?g[]=action", "?g[]=adventure", "?g[]=animation", "?g[]=comedy", "?g[]=crime", "?g[]=drama", "?g[]=documentary", "?g[]=science-fiction", "?g[]=family", "?g[]=history", "?g[]=horror", "?g[]=fantasy", "?g[]=music", "?g[]=mystery", "?g[]=romance", "?g[]=thriller", "?g[]=war", "?g[]=western"]
				else:
					label=["all", "action", "adventure", "animation", "comedy", "crime", "drama", "documentary", "family", "history", "horror", "fantasy", "music", "mystery", "romance", "science fiction", "soap", "western"]
					value=["?g[]=", "?g[]=action", "?g[]=adventure", "?g[]=animation", "?g[]=comedy", "?g[]=crime", "?g[]=drama", "?g[]=documentary", "?g[]=family", "?g[]=history", "?g[]=horror", "?g[]=fantasy", "?g[]=music", "?g[]=mystery", "?g[]=romance", "?g[]=science-fiction", "?g[]=soap", "?g[]=western"]
			elif 'sort' in ff:
				dd= 'sorting:'
				label=['newest first',"oldest First","top IMDb","bottom IMDb"]
				value=['&so=','&so=first_air_date-4"','&so=imdb_rating-3','&so=imdb_rating-4']			

			sel = xbmcgui.Dialog().select('Select '+dd,label)
			sel = sel if sel>-1 else quit()

			v = '%s'%value[sel] if value[sel] else ''
			if v=='&y[]=' :
				if 's' in ff:
					v=''
			#v = '?'+v if 'g[]=' in v else v
			n = label[sel]
			addon.setSetting(ff+'V',v)
			addon.setSetting(ff+'N',n)
			fsortv = addon.getSetting('fsortV')
			
			fkatv = addon.getSetting('fkatV')
			
			frokv = addon.getSetting('frokV')

			fratyv = addon.getSetting('fratyV')
			
			sratyv = addon.getSetting('sratyV')
			
			ssortv = addon.getSetting('ssortV')
			
			skatv = addon.getSetting('skatV')

			srokv = addon.getSetting('srokV')
			
			dataf = fkatv+frokv+fratyv+fsortv
			datas = skatv+srokv+sratyv+ssortv

			addon.setSetting('fdata',dataf)
			addon.setSetting('sdata',datas)
			xbmc.executebuiltin('Container.Refresh')

			
	else:
		home()
		xbmcplugin.endOfDirectory(addon_handle)    
if __name__ == '__main__':
    router(sys.argv[2][1:])