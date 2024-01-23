import json

import sys, io, os
import calendar
from datetime import datetime, timedelta
import time
import collections

import iso8601
import requests
from urllib.parse import quote, unquote

import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import xbmcplugin

from resources.lib.brotlipython import brotlidec
from resources.lib.cmf3 import parseDOM

def resp_text(resp):
	"""Return decoded response text."""
	if resp and resp.headers.get('content-encoding') == 'br':
		out = []
		# terrible implementation but it's pure Python
		return brotlidec(resp.content, out).decode('utf-8')
	response_content = resp.text

	return response_content.replace("\'",'"')

class Helper:
	def __init__(self, base_url=None, handle=None):

	
	
	
		self.base_url = base_url
		self.handle = handle
		self.addon = xbmcaddon.Addon()
		self.addon_name = xbmcaddon.Addon().getAddonInfo('id')
		self.addon_version = xbmcaddon.Addon().getAddonInfo('version')
		self.datapath = self.translate_path(self.get_path('profile'))
		
		self.proxyport = self.get_setting('proxyport')
		
		self.parseDOM = parseDOM


		
		
		
		
		
		try:
			self.kukis = self.load_file(self.datapath+'kukis', isJSON=True)
		except:
			self.kukis = {}
			
		self._sess = None
		self.kuk = {}
		
		self.avail_products = self.get_setting('avail_products')
		# API
		

		self.base_api_url = 'https://www.showtime.com/api/{}'
		self.main_url = 'https://www.shudder.com/{}'
		self.auth_url = 'https://www.shudder.com/auth/login'
		self.UA ='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0'



		self.username = self.get_setting('username')
		self.password = self.get_setting('password')

		self.logged = self.get_setting('logged')

		self.headers = {
   # 'Host': 'www.showtime.com',
	# Requests sorts cookies= alphabetically
	# 'Cookie': 'OptanonConsent=isGpcEnabled=0&datestamp=Tue+Apr+26+2022+18%3A58%3A31+GMT%2B0200+(czas+%C5%9Brodkowoeuropejski+letni)&version=6.32.0&isIABGlobal=false&hosts=&consentId=700b6ce3-4af4-4d55-93d2-4a6eb818950a&interactionCount=0&landingPath=https%3A%2F%2Fwww.showtime.com%2Flogin&groups=1%3A1%2C2%3A1%2C3%3A1%2C4%3A1%2C5%3A1; tve-did=7c632060-528c-480a-81cb-90be4e8b63a8; stat-kookie=10.23.99.15; server=TOMCAT-ASG-10; serverTS=1650992311599; el-mono-llamo=10.23.99.15; JSESSIONID=A13D4572034CF64CDC97C7545C8CD5A4; AWSALBAPP-0=AAAAAAAAAACdzvlBUFX3gxYJauA99A00r0FxmxJMZGI8Kqcv5gXnlsuRKO+TyqwRkl7qdMpH/fXb8hOKjEZyAWM7VgA2cBnuI5BScFme6tfLxPSnObltfNbvSAD2bypY7y2mcEO1jhBVfvc=; AWSALBAPP-1=_remove_; AWSALBAPP-2=_remove_; AWSALBAPP-3=_remove_',
			'user-agent': self.UA,
			'accept': '*/*',
			'accept-language': 'pl,en-US;q=0.7,en;q=0.3',
			'referer': 'https://www.showtime.com/login',
			# Already added when you pass json=
			# 'content-type': 'application/json',
			'x-stat-appversion': '1.2.8',
			'x-stat-contentversion': 'OTT',
			'x-stat-displaytype': 'WEB',
			'origin': 'https://www.showtime.com',
			'sec-fetch-dest': 'empty',
			'sec-fetch-mode': 'cors',
			'sec-fetch-site': 'same-origin',}
	# Requests doesn't support trailers
	# 'te': 'trailers',


	@property
	def sess(self):
		if self._sess is None:
			self._sess = requests.Session()
			if self.kukis:
				self._sess.cookies.update(self.kukis)
				
				
				self._sess.cookies.update(self.kuk)

		return self._sess	

	def input_dialog(self, text, typ=None):
		typ = xbmcgui.INPUT_ALPHANUM if not typ else typ
		return xbmcgui.Dialog().input(text, type=typ)
		
	def get_path(self ,data):	
		return self.addon.getAddonInfo(data)
		
	def translate_path(self ,data):
		try:
			return xbmcvfs.translatePath(data)
		except:
			return xbmc.translatePath(data).decode('utf-8')
			
	def save_file(self, file, data, isJSON=False):
		with io.open(file, 'w', encoding="utf-8") as f:
			if isJSON == True:
				str_ = json.dumps(data,indent=4, sort_keys=True,separators=(',', ': '), ensure_ascii=False)
				f.write(str(str_))
			else:
				f.write(data)

	def load_file(self, file, isJSON=False):

		if not os.path.isfile(file):
			return None
	
		with io.open(file, 'r', encoding='utf-8') as f:
			if isJSON == True:
				return json.load(f, object_pairs_hook=collections.OrderedDict)
			else:
				return f.read() 

		
	def get_setting(self, setting_id):
		setting = xbmcaddon.Addon(self.addon_name).getSetting(setting_id)
		if setting == 'true':
			return True
		elif setting == 'false':
			return False
		else:
			return setting
	
	def set_setting(self, key, value):
		return xbmcaddon.Addon(self.addon_name).setSetting(key, value)
		
		
	def open_settings(self):
		xbmcaddon.Addon(self.addon_name).openSettings()

	def sleep(self, time):
		return xbmc.sleep(int(time))
	
	def dialog_select(self, heading, label):
		return xbmcgui.Dialog().select(heading,label)
		
	def dialog_multiselect(self, heading, label):
		return xbmcgui.Dialog().dialog_multiselect(heading,label)
		
	def dialog_choice(self, heading, message, agree, disagree):
		return xbmcgui.Dialog().yesno(heading, message, yeslabel=agree, nolabel=disagree)
		
		
	def add_item(self, title, url, playable=False, info=None, art=None, content=None, folder=True, contextmenu = None):

		list_item = xbmcgui.ListItem(label=title)
		if playable:
			list_item.setProperty('IsPlayable', 'true')
			folder = False
		if art:
			list_item.setArt(art)
		else:
			art = {
				'icon': self.addon.getAddonInfo('icon'),
				'fanart': self.addon.getAddonInfo('fanart')
			}
			list_item.setArt(art)
		if info:
			list_item.setInfo('Video', info)
		if content:
			xbmcplugin.setContent(self.handle, content)
		if contextmenu:
			list_item.addContextMenuItems(contextmenu, replaceItems=True)
			
			
			

		xbmcplugin.addSortMethod(self.handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED, label2Mask = "%R, %P, %Y")

		xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=folder)
		
	def eod(self, cache=True):
		xbmcplugin.endOfDirectory(self.handle, cacheToDisc=cache)

	def refresh(self):
		return xbmc.executebuiltin('Container.Refresh()')
		
	def update(self,func=''):
		return xbmc.executebuiltin('Container.Refresh(%s)'%func)
		
	def runplugin(self,func=''):
		return xbmc.executebuiltin('RunPlugin(%s))'%func)
		
	def notification(self, heading, message):
		xbmcgui.Dialog().notification(heading, message, time=3000)

	def request_sess(self, url, method='get', data={}, headers={}, cookies={}, result=True, json=False, allow=True , json_data = False):
		if method == 'get':
			resp = self.sess.get(url, headers=headers, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
		elif method == 'post':
			if json_data:
				resp = self.sess.post(url, headers=headers, json=data, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
			else:
				resp = self.sess.post(url, headers=headers, data=data, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
		elif method == 'delete':
			resp = self.sess.delete(url, headers=headers, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
		if result:
			return resp.json() if json else resp_text(resp)
		else:
			return resp
			

	def PlayVid (self, mpdurl, lic_url='', PROTOCOL='', DRM='', certificate = '', flags=True, subs = None):
		from inputstreamhelper import Helper
		play_item = xbmcgui.ListItem(path=mpdurl)
		if subs:
			play_item.setSubtitles(subs)
		if PROTOCOL:

			is_helper = Helper(PROTOCOL, drm=DRM)
			if is_helper.check_inputstream():
				if sys.version_info >= (3,0,0):
					play_item.setProperty('inputstream', is_helper.inputstream_addon)
				else:
					play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
				if 'mpd' in PROTOCOL:
					play_item.setMimeType('application/xml+dash')
				else:
					play_item.setMimeType('application/vnd.apple.mpegurl')
				play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
				if DRM and lic_url:
					play_item.setProperty('inputstream.adaptive.license_type', DRM)
					play_item.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')
					play_item.setProperty('inputstream.adaptive.license_key', lic_url)
					if certificate:
						play_item.setProperty('inputstream.adaptive.server_certificate', certificate)
				if flags:
					play_item.setProperty('inputstream.adaptive.license_flags', "persistent_storage")
				play_item.setContentLookup(False)
		xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)
	

	def getCorrectTime(self, czas):
		try:
			current_date_temp = datetime.strptime(czas, "%Y-%m-%dT%H:%M:%SZ") #'2022-04-16T12:30:00Z'
		except TypeError:
			current_date_temp = datetime(*(time.strptime(czas, "%Y-%m-%dT%H:%M:%SZ")[0:6]))
		datastart = (current_date_temp + timedelta(hours=+2)).strftime('%H:%M')
		return datastart
	def timeNow(self):
		now=datetime.utcnow()+timedelta(hours=2)
	
		czas=now.strftime('%Y-%m-%d')
	
		try:
			format_date=datetime.strptime(czas, '%Y-%m-%d')
		except TypeError:
			format_date=datetime(*(time.strptime(czas, '%Y-%m-%d')[0:6]))	
		return format_date
	def CreateDays(self):
		dzis=self.timeNow()
		timestampdzis = calendar.timegm(dzis.timetuple())
		tydzien = int(timestampdzis)- 2627424
		out=[]
		for i in range(int(timestampdzis),tydzien,-86400):
			x = datetime.utcfromtimestamp(i)

			dzien = (x.strftime('%d.%m'))
			a1 = x.strftime("%Y.%d.%m")

			try:
				current_date_temp = datetime.strptime(a1, "%Y.%d.%m")
			except TypeError:
				current_date_temp = datetime(*(time.strptime(a1, "%Y.%d.%m")[0:6]))
			datastart = (current_date_temp + timedelta(days=-1)).strftime('%Y-%m-%dT')

			dataend = (current_date_temp).strftime('%Y-%m-%dT')
			dod ='&start_after_time='+datastart+'22%3A00%3A00.000Z&start_before_time='+dataend+'22%3A00%3A00.000Z'

			dnitygodnia = ("poniedziałek","wtorek","środa","czwartek","piątek","sobota","niedziela")
			
			day = x.weekday()
	
			dzientyg = dnitygodnia[day]
	
			out.append({'dzien':dzientyg+ ' '+dzien,'dodane':str(dod)}) 
			
		return out		 

	def string_to_date(self, string, string_format):
		s_tuple = tuple([int(x) for x in string[:10].split('-')]) + tuple([int(x) for x in string[11:].split(':')])
		s_to_datetime = datetime(*s_tuple).strftime(string_format)
		return s_to_datetime

	def parse_datetime(self, iso8601_string, localize=False):
		"""Parse ISO8601 string to datetime object."""
		datetime_obj = iso8601.parse_date(iso8601_string)
		if localize:
			return self.utc_to_local(datetime_obj)
		else:
			return datetime_obj

	def to_timestamp(self, a_date):
		if a_date.tzinfo:
			epoch = datetime(1970, 1, 1, tzinfo=pytz.UTC)
			diff = a_date.astimezone(pytz.UTC) - epoch
		else:
			epoch = datetime(1970, 1, 1)
			diff = a_date - epoch
		return int(diff.total_seconds())*1000
	

	
	def getCurTStamp(self):
		# gmt stores current gmtime
		gmt = time.gmtime()
		#print("gmt:-", gmt)
  
# ts stores timestamp
		ts = calendar.timegm(gmt)
	
	
	
		#import time
		#ts = time.time()
		return int(ts)
	
	@staticmethod
	def utc_to_local(utc_dt):
		# get integer timestamp to avoid precision lost
		timestamp = calendar.timegm(utc_dt.timetuple())
		local_dt = datetime.fromtimestamp(timestamp)
		assert utc_dt.resolution >= timedelta(microseconds=1)
		return local_dt.replace(microsecond=utc_dt.microsecond)
		
	@staticmethod
	def convertUnixTime(start, end):
		#import time
		try:
			start= time.localtime(start)
		#   czas=time.strftime("%Y-%m-%d %H:%M:%S", czas)
			start=time.strftime("%I:%M %p", start)
			
			end= time.localtime(end)
		#   czas=time.strftime("%Y-%m-%d %H:%M:%S", czas)
			end=time.strftime("%I:%M %p", end)
		except:
			start=None
			end = None
		return start, end
		
		
		
		
		
		
		
		
		
		
		
		
		
		
	
	@staticmethod
	def utc_to_local2(timestamp):
		# get integer timestamp to avoid precision lost
	# timestamp = calendar.timegm(utc_dt.timetuple())
		local_dt = datetime.fromtimestamp(timestamp)
		assert utc_dt.resolution >= timedelta(microseconds=1)
		return local_dt.replace(microsecond=utc_dt.microsecond)
		
	@staticmethod
	def gettimedif():
		import datetime
		import time
		a=datetime.datetime.utcnow()
		readable1 = a.strftime('%Y-%m-%dT%H:%M')
		b=datetime.datetime.now()
		readable2 = b.strftime('%Y-%m-%dT%H:%M')
	
		try:
			date_time_obj=datetime.datetime.strptime(readable1, '%Y-%m-%dT%H:%M')+datetime.timedelta(hours=1)
			date_time_obj2=datetime.datetime.strptime(readable2, '%Y-%m-%dT%H:%M')
	
		except TypeError:
			date_time_obj=datetime.datetime(*(time.strptime(readable1, '%Y-%m-%dT%H:%M')[0:6]))+datetime.timedelta(hours=1)
			date_time_obj2=datetime.datetime(*(time.strptime(readable2, '%Y-%m-%dT%H:%M')[0:6]))
	
		def to_timestampx(a_date):
			from datetime import datetime
			try:
				import pytz
			except:
				pass
			if a_date.tzinfo:
				epoch = datetime(1970, 1, 1, tzinfo=pytz.UTC)
				diff = a_date.astimezone(pytz.UTC) - epoch
			else:
				epoch = datetime(1970, 1, 1)
				diff = a_date - epoch
			return int(diff.total_seconds())*1000	
			
		tst4 =	 to_timestampx(date_time_obj)
		tst5 =	 to_timestampx(date_time_obj2)
		dif = tst5-tst4
		return int(dif)/3600000
	
	@staticmethod
	def getrealtime(dt,dif):
		import datetime
		try:
			date_time_obj=datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M')
		except TypeError:
			date_time_obj=datetime.datetime(*(time.strptime(dt, '%Y-%m-%dT%H:%M')[0:6]))
		
		rltime = date_time_obj + datetime.timedelta(hours=dif)
		rltime = rltime.strftime('%Y-%m-%d %H:%M')
	
		return rltime
