import xbmcgui
import xbmc
import xbmcaddon
import xbmcplugin
import urllib
import sys
import re
import requests
from urllib.parse import parse_qsl,urlparse,urlencode
from bs4 import BeautifulSoup as BS

EndOfDirectory      = lambda: xbmcplugin.endOfDirectory(int(sys.argv[1]))
Log                 =  lambda x: xbmc.log(str(x),2)
AddonInfo           =  xbmcaddon.Addon().getAddonInfo
UserAgent           = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"

def Add(name, url='', mode='', iconimage=AddonInfo('icon'), fanart=AddonInfo('fanart'), description='',folder=False,playable=False):
	#This Is Where The Params Are Defined. Were Creating The Following Params ['url','mode','name','iconimage']
	u=urllib.parse.urlunparse(['plugin', AddonInfo('id'), '/', '', urlencode({'url':url,'mode':mode,'name':name,'iconimage':iconimage,"description":description}), ''])
	liz = xbmcgui.ListItem(name)
	handle=sys.argv[1]
	if playable:
		liz.setProperty('isPlayable', 'true')
		liz.setInfo(type='video', infoLabels={'title':name,'mediatype':'video'})
	liz.setArt({ 'fanart': fanart,'thumb': iconimage})
	ok = xbmcplugin.addDirectoryItem(handle=int(handle), url=u, listitem=liz, isFolder=folder)
	return ok

def Get(url):
	return requests.get(url,headers={"referer":url,"user-agent":UserAgent}).text

def Index():
	url = "https://fullmatchtv.com/wp-json/wp/v2/categories"
	categories = requests.get(url,headers={"user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"}).json()
	for category in categories:
		title = category["name"]
		catid = str(category["id"])
		Add(title,catid,"Category",description="1",folder=True)

def Category(name,catid,page):
	url = "https://fullmatchtv.com/wp-json/wp/v2/posts?categories={categoryId}&page={page}&per_page=25".format(categoryId=catid,page=page)
	replays = requests.get(url,headers={"user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"}).json()
	for replay in replays:
		description = replay["yoast_head_json"]["description"]
		title = replay["yoast_head_json"]["og_title"]
		url = replay["_links"]["self"][0]["href"]
		Add(title,url,"List Replay",folder=True)
	Add("Next Page",catid,"Category",description=int(page)+1,folder=True)

def Replays(url):
	replays = requests.get(url,headers={"user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"}).json()
	html = replays["content"]["rendered"]
	links = re.findall(r"iframe .+?src=\\?\"(.+?)?\"",html)
	for url in links:
		if url[0] == "/":url = "http:"+url
		domain = urlparse(url).netloc
		if "youtube" in domain:
			Add(domain,url,"Play")
		else:
			Add(domain,url,"Play",playable=True)

def streamlare(url):
	videoId = url.split("/e/")[1]
	api = "https://streamlare.com/api/video/get"
	apiInfo = {"id":videoId}
	response = requests.post(api,data=apiInfo).json()
	url = response["result"]["Original"]["src"]
	return url

def streamtape(url):
	videoid = re.findall(r"\/e\/(.*)",url)[0]
	url = "https://streamta.pe/e/%s/"%(videoid)
	response = Get(url)
	url = re.findall(r"<div id=\"ideoolink\" .+?>\/(.+?)<\/div>",response)[0]
	if url[0] != "h":
		url = "http://"+url
	else:
		url = url[0]
	# headers = requests.get(url,headers={"user-agent":UserAgent}).text
	return url

def okru(url):
	response = Get(url)
	url = re.findall(r"hlsManifestUrl.+?(ht.+?)\\&quot;",response)[0].replace("\\\\u0026","&")
	return url

def Playit(name,url):
	domain = urlparse(url).netloc
	if "ok.ru" == domain:
		url = okru(url)
	elif "streamtape.com" in url:
		url = streamtape(url)
	elif "streamlare.com" in url:
		url = streamlare(url)
	xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, xbmcgui.ListItem(path=url))


###############################################################################################################
for x in parse_qsl(sys.argv[2][1:]):globals()[x[0]] = x[1]
###############################################################################################################
try:
	if      mode        ==      "Category":    	Category(name,url,description)
	elif    mode        ==      "List Replay":  Replays(url)
	elif    mode        ==      "Play":         Playit(name,url)
	elif    mode        ==      "Test":         Resolve(url)
except:Index()
###############################################################################################################
EndOfDirectory()