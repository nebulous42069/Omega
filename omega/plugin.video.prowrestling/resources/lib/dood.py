# -*- coding: UTF-8 -*-

import six
from six.moves import urllib_parse


import ssl
from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

import requests
from requests import Session
from resources.lib.brotlipython import brotlidec
from requests.compat import urlparse

import re, sys
import random
import string
import time

PY3 = sys.version_info >= (3,0,0)
class TLS12HttpAdapter(HTTPAdapter):
	""""Transport adapter that forces the use of TLS v1.2."""
	def init_poolmanager(self, connections, maxsize, block=False):
		tls = ssl.PROTOCOL_TLSv1_2 if PY3 else ssl.PROTOCOL_TLSv1
		self.poolmanager = PoolManager(
					num_pools=connections, maxsize=maxsize,
						block=block, ssl_version=tls)


session2 = Session()

session2.mount("https://", TLS12HttpAdapter())	

sess = Session()
UA = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0'
headers = {
	'User-Agent': UA,
	'Accept': '*/*',
	'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
	'Accept-Encoding': 'gzip, deflate, br',

	'TE': 'trailers',
}
headerswaaw = {
	'User-Agent': UA,
	'Accept': '*/*',
	'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
	'TE': 'trailers',
}
def getLink(url):
	response = session2.get(url, headers=headers, verify=False)#.content
	out = []
	html = brotlidec(response.content, out).decode('utf-8')

	match = re.search(r'''dsplayer\.hotkeys[^']+'([^']+).+?function\s*makePlay.+?return[^?]+([^"]+)''', html, re.DOTALL)

	host = urlparse(response.url).netloc
	headers.update({'Referer':url})
	token = match.group(2)
	url2 = 'https://{0}{1}'.format(host, match.group(1))
	response = session2.get(url2, headers=headers, verify=False)#.content

	out = []
	html = brotlidec(response.content, out).decode('utf-8')

	def dood_decode(data):
			t = string.ascii_letters + string.digits
			return data + ''.join([random.choice(t) for _ in range(10)])
	link = dood_decode(html) + token + str(int(time.time() * 1000))
	
	return link +'|User-Agent='+UA+'&Referer='+url

	
def getsawlive(url,ref):
	headerswaaw.update({'Referer':ref})
	host = urlparse(ref).netloc
	response = sess.get(url, headers=headerswaaw, verify=False)
	html = response.content
	html = html.decode(encoding='utf-8', errors='strict') if PY3 else html
	
	html2 = ''
	abc = re.findall('script src\s*=\s*"(\/jq.*?)"',html,re.DOTALL)
	ab = 'https://sawlive.net'+abc[0] if abc else ''
	if ab:
		response = sess.get(ab, headers=headerswaaw, verify=False)
		html2 = response.content
		html2 = html2.decode(encoding='utf-8', errors='strict') if PY3 else html2
		unpacked = ''
	
		from resources.lib import jsunpack
		
		packedMulti = re.compile('eval(.*?)\\{\\}\\)\\)',re.DOTALL).findall(html2)
		for packed in packedMulti:
			packed=re.sub('  ',' ',packed)
			packed=re.sub('\n','',packed)
			try:
				unpacked += jsunpack.unpack(packed)
			except:
				unpacked=''
			
		unpacked = unpacked.replace("\\\'","'").replace('\\\\',"")
		html+=unpacked

	docwrite = re.findall('document\.write\(([^\)]+)\)',html,re.DOTALL)[0]
	dc=''
	pt = re.findall('(\w+)',docwrite,re.DOTALL)

	for p in pt:
		if 'finaloutput' in p:
			try:
				dod = re.findall(host+".*?finaloutput\s*=\s*\\'([^\\']+)",html,re.DOTALL)[0]
			except:
				dod = re.findall("finaloutput\s*=\s*\\'([^\\']+)",html,re.DOTALL)[-1]
		elif 'phpoutput' in p:
			try:
				dod = re.findall(host+".*?phpoutput\s*=\s*\\'([^\\']+)",html,re.DOTALL)[0]
			except:
				dod = re.findall("phpoutput\s*=\s*\\'([^\\']+)",html,re.DOTALL)[-1]
		else:
			try:
				dod = re.findall(p+"\s*=\s*\\'([^\\']+)",html,re.DOTALL)[0]
			except:
				dod = re.findall(p+'\s*=\s*"([^"]+)',html,re.DOTALL)[0]
		dc+= dod

	nturl = re.findall('src\s*=\s*"([^"]+)',dc,re.DOTALL)[0]

	nturl = 'https:' + nturl if nturl.startswith('//') else nturl
	headerswaaw.update({'Referer':url})
	response = sess.get(nturl, headers=headerswaaw, verify=False)
	html = response.content
	html = html.decode(encoding='utf-8', errors='strict') if PY3 else html
	unpacked = ''

	from resources.lib import jsunpack

	packedMulti = re.compile('eval(.*?)\\{\\}\\)\\)',re.DOTALL).findall(html)
	for packed in packedMulti:
		packed=re.sub('  ',' ',packed)
		packed=re.sub('\n','',packed)
		try:
			unpacked += jsunpack.unpack(packed)
		except:
			unpacked=''
	unpacked = unpacked.replace("\\\'",'"').replace('\\\\',"")
	
	ifr = re.findall('iframe src\s*=\s*"([^"]+)"', unpacked,re.DOTALL)[0].lstrip()
	if 'hdfree' in ifr:
		ifr = 'https:' + ifr if ifr.startswith('//') else ifr

		cod = re.findall('(?:\?|\&)code=([^&]*)',nturl ,re.DOTALL)[0]
		lin = re.findall('(?:\?|\&)line=([^&]*)',nturl ,re.DOTALL)[0]

		nxturl = 'https://www.hdfree.info/finalpage/{cod}.php?line={lin}'.format(cod=cod, lin=lin)

		headers6 = {
			'Host': 'www.hdfree.info',
			'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
			'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
			'referer': 'https://www.educ.top/',
			'upgrade-insecure-requests': '1',
			'sec-fetch-dest': 'iframe',
			'sec-fetch-mode': 'navigate',
			'sec-fetch-site': 'cross-site',}
		headers6 = {
			'Host': 'www.hdfree.info',
			'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
			'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
			'referer': 'https://www.hdfree.info/embed.php?code='+cod+'&line='+lin,
			'upgrade-insecure-requests': '1',
			'sec-fetch-dest': 'iframe',
			'sec-fetch-mode': 'navigate',
			'sec-fetch-site': 'same-origin',

		}
		
		response = sess.get(nxturl, headers=headers6, verify=False)
		html = response.content
		html = html.decode(encoding='utf-8', errors='strict') if PY3 else html
		headers6 = {

			'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
			'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
			'referer': 'https://www.hdfree.info/',
			'upgrade-insecure-requests': '1',
			'sec-fetch-dest': 'iframe',
			'sec-fetch-mode': 'navigate',
			'sec-fetch-site': 'cross-site',

		}
		iframex=re.findall('iframe src="([^"]+)"',html,re.DOTALL)[0]
		iframex = 'https:' + iframex if iframex.startswith('//') else iframex
		response = sess.get(iframex, headers=headers6, verify=False)

		html = response.content
		html = html.decode(encoding='utf-8', errors='strict') if PY3 else html
		iframex=re.findall('iframe src="([^"]+)"',html,re.DOTALL)[0]
		iframex = 'https:' + iframex if iframex.startswith('//') else iframex
		ref = iframex.replace('group/','group/secure/')
		vidurl = iframex.replace('group/?line=','chatbox/')+'.m3u8'
		return vidurl +'|User-Agent='+UA+'&Referer='+ref

def getDropDown(url):
	from resources.lib import jsunpack
	packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
	response = sess.get(url, headers=headerswaaw, verify=False)
	html = response.content
	html = html.decode(encoding='utf-8', errors='strict') if PY3 else html
	nturl = response.url
	headerswaaw.update({'Referer':nturl, 'content-type': 'application/x-www-form-urlencoded'})
	
	
	
	
	post = {k: v for k, v in re.findall('<input type="hidden" name="([^"]+)" value="([^"]+)">', html)}

	post.update({'usr_login':'', 'referer': '', 'method_free': 'Free Download >>'})

	response = sess.post(nturl, headers=headerswaaw, data=post, verify=False)#.content
	
	ab=response.content
	ab = ab.decode(encoding='utf-8', errors='strict') if PY3 else ab
	packer = re.compile('(eval\(function\(p,a,c,k,e,(?:r|d).*)')
	unpacked = ''

	packeds= packer.findall(ab)

	for i in packeds: 
		try: unpacked += jsunpack.unpack(i)
		except: pass
	
	
	link =re.findall('\{file:"([^"]+)"',unpacked, re.DOTALL)[0]
	return link +'|User-Agent='+UA+'&Referer='+nturl

def getm2list(url,ref):
	vidurl=''
	headersx = {
		'User-Agent': UA,
		'Accept': '*/*',
		'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
		'Accept-Encoding': 'gzip, deflate',#, br',
		'Referer' : ref,
		'TE': 'trailers',
	}

	html = sess.get(url, headers=headersx, verify=False).text

	html=html.replace("\'",'"')
	nturl = 'https://www.newss.top/goto.html?'+re.findall('(lister.*?)$',url,re.DOTALL)[0]
	headers.update({'Referer':url})
	html = sess.get(nturl, headers=headersx, verify=False).text

	unpacked = ''

	from resources.lib import jsunpack

	packedMulti = re.compile('eval(.*?)\\{\\}\\)\\)',re.DOTALL).findall(html)
	for packed in packedMulti:
		packed=re.sub('  ',' ',packed)
		packed=re.sub('\n','',packed)
		try:
			unpacked += jsunpack.unpack(packed)
		except:
			unpacked=''
	
	
	
	unpacked = unpacked.replace("\\\'",'"').replace('\\\\',"")
	src = re.findall('src="([^"]+)"',unpacked,re.DOTALL)[0]
	src = 'https:' + src if src.startswith('//') else src
	lister = re.findall('(?:\?|\&)lister=([^&]*)',url,re.DOTALL)[0]
	mainid = re.findall('(?:\?|\&)mainid=([^&]*)',url,re.DOTALL)[0]
	mirror = re.findall('(?:\?|\&)mirror=([^&]*)',url,re.DOTALL)[0]
	nturl = src+'{mainid}?lister={lister}&mirror={mirror}'.format(mainid=mainid, lister=lister, mirror=mirror)

	headersx2 = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
		'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
		'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
		'Accept-Encoding': 'gzip, deflate',
		'Referer': 'https://www.newss.top/',
		'Alt-Used': 'files.m2list.com',
		'Connection': 'keep-alive',
	}

	nturl='https://files.m2list.com/ajax/movie/get_sources/{mainid}/{mirror}'.format(mainid=mainid, mirror=mirror)
	

	html = sess.get(nturl, headers=headersx2, verify=False).json()

	nturl = html.get("sources", None)
	nturl = 'https:' + nturl if nturl.startswith('//') else nturl
	if 'news=' in nturl:# or 'line=' in nturl:
		headers6 = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
			'Accept-Encoding': 'gzip, deflate',
			'Alt-Used': 'newss.top',
			'Connection': 'keep-alive',
			'Referer': 'https://files.m2list.com/',
			'Upgrade-Insecure-Requests': '1',
			'Sec-Fetch-Dest': 'iframe',
			'Sec-Fetch-Mode': 'navigate',
			'Sec-Fetch-Site': 'cross-site',}
		html = sess.get(nturl, headers=headers6, verify=False).text	
		from resources.lib import jsunpack
	
		packedMulti = re.compile('eval(.*?)\\{\\}\\)\\)',re.DOTALL).findall(html)
		for packed in packedMulti:
			packed=re.sub('  ',' ',packed)
			packed=re.sub('\n','',packed)
			try:
				unpacked += jsunpack.unpack(packed)
			except:
				unpacked=''
		unpacked.replace("\\\'",'"').replace('\\\\',"")	  

		cd = nturl.split('news=')[-1]
		import resolveurl
		ifr = 'https://www.dailymotion.com/embed/video/'+cd
		try:
			link = resolveurl.resolve(ifr)
		except:
			link =''
		return link

	else:
		if 'android-devs.' in nturl:
			headers5 = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0',
				'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
				'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
				# 'Accept-Encoding': 'gzip, deflate, br',
				'Alt-Used': 'www.android-devs.top',
				'Connection': 'keep-alive',
				'Referer': 'https://files.m2list.com/',
				'Upgrade-Insecure-Requests': '1',
				'Sec-Fetch-Dest': 'iframe',
				'Sec-Fetch-Mode': 'navigate',
				'Sec-Fetch-Site': 'cross-site',}
		elif 'pvpstage' in nturl:
			headers5 = {
				'Host': 'www.pvpstage.com',
				'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0',
				'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
				'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
				'referer': 'https://files.m2list.com/',
				'upgrade-insecure-requests': '1',
				'sec-fetch-dest': 'iframe',
				'sec-fetch-mode': 'navigate',
				'sec-fetch-site': 'cross-site'}
		else:
			headers5 = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
				'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
				'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
				'Accept-Encoding': 'gzip, deflate',
				'Connection': 'keep-alive',
				'Referer': 'https://www.funsocialclub.com/',
				'Upgrade-Insecure-Requests': '1',
				'Sec-Fetch-Dest': 'iframe',
				'Sec-Fetch-Mode': 'navigate',
				'Sec-Fetch-Site': 'same-site',
		
				}
		
		nturl = nturl.replace('www.funsocialclub.com/chatbox/','share.funsocialclub.com/chatbox/secure/')
		#nturl = nturl.replace('www.android-devs.top/f/','developer.android-devs.top/chatbox/')
		
		
		#https://developer.android-devs.top/chatbox/?line=WWE_Main_Event_2022_09_01_SD

		response = sess.get(nturl, headers=headers5, verify=False)#.text
		respurl = response.url
		html = response.text
		if 'android-devs.' in respurl:
			skrypty = re.findall('script src="([^"]+)"',html,re.DOTALL)
			for sk in skrypty:
				if not 'query' in sk:
					break
			nt2 = 'https://www.android-devs.top'+sk
			html2 = html
			html = sess.get(nt2, headers=headers5, verify=False).text
			#ht
		elif 'pvpstage' in respurl:

			src = re.findall('src="([^"]+)" allow',html,re.DOTALL)[0]
			respurl = respurl.replace('www.pvpstage.com/files','player6.pvpstage.com/secure')

			headers5.update({'Referer':urlparse(src).netloc})
			response = sess.get(respurl, headers=headers5, verify=False)#.text
			respurl = response.url
			html = response.text
			mainurl = respurl.split('/secure')[0]
			xxx = re.findall('src"\:"([^"]+)"',html,re.DOTALL)[0]
			src = mainurl+xxx
			
		unpacked = ''

		from resources.lib import jsunpack
	
		packedMulti = re.compile('eval(.*?)\\{\\}\\)\\)',re.DOTALL).findall(html)
		for packed in packedMulti:
			packed=re.sub('  ',' ',packed)
			packed=re.sub('\n','',packed)
			try:
				unpacked += jsunpack.unpack(packed)
			except:
				unpacked=''
		unpacked.replace("\\\'",'"').replace('\\\\',"")	
		if not 'android-devs.' in respurl:	
			html = html+unpacked
		else:
			html = unpacked
		html = html.replace("\\\'",'"')
		if 'android-devs.' in respurl:
			#html = html+unpacked
			jedensrc = re.findall('src\s*=\s*"([^"]+)"', html,re.DOTALL)
			phptwo = re.findall('phptwo\s*=\s*"([^"]+)"', html,re.DOTALL)
			phpfour = re.findall('phpfour\s*=\s*"([^"]+)"', html,re.DOTALL)
			phpfour = phpfour[0] if phpfour else ''
			line = re.findall('var line\s*=\s*"([^"]+)"', html2,re.DOTALL)

			nt3 = jedensrc[0]+phptwo[0]+line[0]+phpfour#[0]
			
			headers5 = {
				'Host': 'developer.android-devs.top',
				'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0',
				'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
				'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
				'referer': 'https://www.android-devs.top/',
				'upgrade-insecure-requests': '1',
				'sec-fetch-dest': 'iframe',
				'sec-fetch-mode': 'navigate',
				'sec-fetch-site': 'same-site',
				# Requests doesn't support trailers
				# 'te': 'trailers',
			}
			
			resp = sess.get(nt3, headers=headers5, verify=False)#.text
			respurl = resp.url.replace('chatbox/','chatbox/secure/')
			resp2 = sess.get(respurl, headers=headers5, verify=False)#.text
			xx=resp2.text#.replace("\'",'"')
			unpacked = ''
	
			from resources.lib import jsunpack
		
			packedMulti = re.compile('eval(.*?)\\{\\}\\)\\)',re.DOTALL).findall(xx)
			for packed in packedMulti:
				packed=re.sub('  ',' ',packed)
				packed=re.sub('\n','',packed)
				try:
					unpacked += jsunpack.unpack(packed)
				except:
					unpacked=''
			unpacked.replace("\\\'",'"').replace('\\\\',"")
			unpacked = re.sub("\\\\'", '"', unpacked)
			html = html+unpacked
			ponerthree= re.findall('ponerthree\s*=\s*"([^"]+)"',html,re.DOTALL)[0]
		
			vidurl = respurl.replace('/chatbox/secure/?line=','/f/')+ponerthree
			vidurl = 'https:' + vidurl if vidurl.startswith('//') else vidurl
			vidurl+='|User-Agent='+UA+'&Referer='+nturl


		elif 'pvpstage' in respurl:
			vidurl = src+'|User-Agent='+UA+'&Referer='+respurl
		else:
			ponerthree= re.findall('ponerthree\s*=\s*"([^"]+)"',html,re.DOTALL)[0]
		
			vidurl = respurl.replace('/chatbox/secure/?line=','/f/')+ponerthree
			vidurl = 'https:' + vidurl if vidurl.startswith('//') else vidurl
			vidurl+='|User-Agent='+UA+'&Referer='+nturl
		
	return vidurl

def getShh(html):
	def ll1ll1(matchobj):
		return str(eval(matchobj.group(0)))
	def l11l11(data):
		l1llll = re.findall('\\*/(\\(\\w+\\)\\[\\w+\\])\\+', data, re.DOTALL)[0]
		l1llll_re = l1llll.replace('(', '\\(').replace(')', '\\)').replace('[', '\\[').replace(']', '\\]')
		l1lll1 = re.findall('%s(.*?)\\+%s' % (l1llll_re, l1llll_re), data, re.DOTALL)[0].replace(' ', '')
		l11l1l = []
		l111l1 = '--13340'
		for w in re.findall('\\w+', l1lll1, re.DOTALL):
			if w not in l11l1l:
				l11l1l.append(w)
	
		if len(l11l1l) == 7:
			for i in range(2, 7):
				l1lll1 = l1lll1.replace(l11l1l[i], l111l1[i])
	
		l11111 = ''
		for b in l1lll1.split('+(%s)[%s]+' % (l11l1l[0], l11l1l[1])):
			if not b:
				continue
			b = re.sub('\\((\\(.*?\\))\\)', ll1ll1, b)
			b = re.sub('\\(.*?\\)', ll1ll1, b)
			b = b.replace('+', '')
			l11111 += chr(int(b, 8))
	
		return l11111

	html = re.findall("""adding events'\)\;(.*?)catch""",html,re.DOTALL)[0]
	sh = None
	lll1l1 = None

	aux = html.splitlines()
	for x in aux:
		x=x.replace('\n','')
		if x.endswith("');"):
			lll1l1 = x
			break
	
	if lll1l1:
		l1l1ll = ''
		l111l11 = []
		l111l12 = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
		for x in lll1l1.decode('utf-8').replace('\n', ''):
			if x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-*^~/=[](){}:;,. "\'\\':
				l1l1ll += x
			else:
				if x not in l111l11:
					l111l11.append(x)
				i = l111l11.index(x)
				l1l1ll += l111l12[i]
	
		data2 = l11l11(l1l1ll)

		sh=re.findall("shh='([^']+)",data2,re.DOTALL)

	return sh[0]
	
def getWaaw(url):
	mainpart = url.split('/watch')[0]
	v = url.split('v=')[-1]
	html = sess.get(url, headers=headerswaaw, verify=False).content
	nturlx= re.findall("replace\('(.*?)\'\)",html,re.DOTALL)
	nturl = mainpart+nturlx[0]

	headerswaaw.update({'Referer':url})
	html = sess.get(nturl, headers=headerswaaw, verify=False).content
	iframex=re.findall('iframe src="([^"]+)"',html,re.DOTALL)
	iframe = mainpart+iframex[0]
	html = sess.get(iframe, headers=headerswaaw, verify=False).content
	shh=getShh(html)
	vidid = re.findall('videoid\s*=\s"([^"]+)"',html, re.DOTALL)[0]
	userid = re.findall('userid\s*=\s"([^"]+)"',html, re.DOTALL)[0]# = "
	vdomd5 = re.findall('videokeyorig\s*=\s"([^"]+)"',html, re.DOTALL)[0]

	hdrs = {
		'Host': 'waaw.to',
		'user-agent': UA,
		'accept': '*/*',
		'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
		'referer': iframe,
		'x-requested-with': 'XMLHttpRequest',
		'origin': 'https://waaw.to',
		'dnt': '1',
		'sec-fetch-dest': 'empty',
		'sec-fetch-mode': 'cors',
		'sec-fetch-site': 'same-origin',
		'te': 'trailers',
	}
	
	json_data = {
		'videoid': vidid,
		'videokey': v,
		'width': 1324,
		'height': 563,
	}
	

	responsex = requests.post('https://waaw.to/player/get_player_image.php', headers=hdrs, json=json_data, verify=False)#.json()
	response = responsex.json()
	hash_image = urllib_parse.quote(response.get("hash_image", None))##urllib_parse.quote())

	hdrs = {
		'Host': 'waaw.to',
		'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
		'accept': 'application/json, text/javascript, */*; q=0.01',
		'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
		'referer': iframe,#
		'dnt': '1',
		'sec-fetch-dest': 'empty',
		'sec-fetch-mode': 'cors',
		'sec-fetch-site': 'same-origin',
		'te': 'trailers',
	}
	
	json_data = {
		'htoken': '',
		'sh': shh,
		'ver': '4',
		'secure': '0',
		'adb': userid,
		'v': urllib_parse.quote(vdomd5),
		'token': '',
		'gt': '',
		'embed_from': '0',
		'wasmcheck': 1,
		'adscore': '',
		'click_hash': hash_image.replace('/','%2F'),
		'clickx': 444,
		'clicky': 204,
	}
	ab = responsex.cookies
	abc = sess.cookies
	cookies = {
	'EU_COOKIE_LAW_CONSENT': 'true',
	}

	response = sess.post('https://waaw.to/player/get_md5.php', headers=hdrs, json=json_data,verify=False).text

	link = re.findall("olplayer.*?src\:\s*'([^']+)",html,re.DOTALL)#[0]
	return link[0] +'|User-Agent='+UA+'&Referer='+url

