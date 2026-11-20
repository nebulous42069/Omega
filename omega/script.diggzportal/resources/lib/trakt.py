import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import shutil

import datetime
from datetime import date, datetime, timedelta
import time
from pathlib import Path

from inspect import currentframe, getframeinfo
#xbmc.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))+'===>OPENINFO', level=xbmc.LOGINFO)

def addon_ID():
	addonID = xbmcaddon.Addon().getAddonInfo('id')
	return addonID

def addon_ID_short():
	addonID = xbmcaddon.Addon().getAddonInfo('id')
	addonID_short = addonID.replace('script.','')
	return addonID_short

def main_file_path():
	return xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path'))

def tmdb_settings_path():
	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
	tmdb_settings_path = addonUserDataFolder.replace(addonID,'plugin.video.themoviedb.helper') + '/settings.xml'
	tmdb_settings_path = Path(tmdb_settings_path)
	return tmdb_settings_path

def get_processor_info():
	import platform, subprocess
	if platform.system() == "Windows":
		return platform.processor()
	elif platform.system() == "Darwin":
		return subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
	elif platform.system() == "Linux":
		command = "cat /proc/cpuinfo"
		return subprocess.check_output(command, shell=True).strip()
	return ""

def tmdb_traktapi_path():
	tmdb_traktapi_path1 = Path(main_file_path().replace(addon_ID(),'plugin.video.themoviedb.helper') + 'resources/lib/traktapi.py')
	tmdb_traktapi_path2 = Path(main_file_path().replace(addon_ID(),'plugin.video.themoviedb.helper') + 'resources/lib/trakt/api.py')
	tmdb_traktapi_path3 = Path(main_file_path().replace(addon_ID(),'plugin.video.themoviedb.helper') + 'resources/lib/api/trakt/api.py')
	tmdb_traktapi_path4 = Path(main_file_path().replace(addon_ID(),'plugin.video.themoviedb.helper') + 'resources/tmdbhelper/lib/api/api_keys/trakt.py')
	if xbmcvfs.exists(str(tmdb_traktapi_path1)):
		return tmdb_traktapi_path1
	elif xbmcvfs.exists(str(tmdb_traktapi_path2)):
		return tmdb_traktapi_path2
	elif xbmcvfs.exists(str(tmdb_traktapi_path3)):
		return tmdb_traktapi_path3
	elif xbmcvfs.exists(str(tmdb_traktapi_path4)):
		return tmdb_traktapi_path4


def icon_path():
	icon_path = Path(main_file_path() + 'icon2.png')
	return str(icon_path)

def tmdb_api_key():
	return 'f5608fba6ab49e9985828b35d5653321'

def fanart_api_key():
	return '184e1a2b1fe3b94935365411f919f638'


def trakt_next_episode_normal(tmdb_id_num=None):
	#import requests
	#import json

	tmdb_id=tmdb_id_num
	#headers = trak_auth()

	try:
		#response = requests.get('https://api.trakt.tv/search/tmdb/'+str(tmdb_id)+'?type=show', headers=headers).json()
		response = get_trakt_data(url='https://api.trakt.tv/search/tmdb/'+str(tmdb_id)+'?type=show', cache_days=0.5)
	except:
		xbmc.executebuiltin('Dialog.Close(busydialog)')

	id = response[0]['show']['ids']['trakt']
	title = response[0]['show']['title']

	response1 = ''
	i = 0
	while response1 == '' and i < 11:
		try:
			#response1 = requests.get('https://api.trakt.tv/shows/'+str(id)+'/progress/watched',headers=headers).json()
			response1 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(id)+'/progress/watched', cache_days=0.00001)
		except:
			i = i + 1

	try:
		season = response1['next_episode']['season']
		episode = response1['next_episode']['number']
	except:
		season = '1'
		episode = '1'

	response2 = ''
	i = 0
	while response2 == '' and i < 22:
		try:
			#response2 = requests.get('https://api.trakt.tv/shows/'+str(id)+'/seasons/'+str(season)+'/episodes/'+str(episode)+'?extended=full', headers=headers).json()
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(id)+'/seasons/'+str(season)+'/episodes/'+str(episode)+'?extended=full', cache_days=0.00001)
		except:
			i = i + 1

	first_aired = response2['first_aired']
	try:
			first_aired2 = datetime.strptime(first_aired, '%Y-%m-%dT%H:%M:%S.%fZ')
	except TypeError:
			first_aired2 = datetime(*(time.strptime(first_aired, '%Y-%m-%dT%H:%M:%S.%fZ')[0:6]))

	now = datetime.now()

	if first_aired2 < now:
		#url = 'RunPlugin(plugin://plugin.video.themoviedb.helper?info=play&amp;query='+str(title)+'&amp;type=episode&amp;season='+str(season)+'&amp;episode='+str(episode)+')'
		url = 'plugin://plugin.video.themoviedb.helper?info=play&amp;type=episode&amp;tmdb_id='+ str(tmdb_id) + '&amp;season='+str(season)+'&amp;episode='+str(episode)
		xbmc.executebuiltin('Dialog.Close(busydialog)')
		return url
	else:
		xbmcgui.Dialog().notification(heading='Trakt Next Episode Normal', message='Next Episode Not aired yet', icon=icon_path(),time=1000,sound=False)

def trakt_next_episode_rewatch(tmdb_id_num=None):
	#import requests
	#import json

	tmdb_id=tmdb_id_num
	#headers = trak_auth()

	#response = requests.get('https://api.trakt.tv/search/tmdb/'+str(tmdb_id)+'?type=show', headers=headers).json()
	response = get_trakt_data(url='https://api.trakt.tv/search/tmdb/'+str(tmdb_id)+'?type=show', cache_days=0.5)
	id = response[0]['show']['ids']['trakt']
	title = response[0]['show']['title']

	response1 = ''
	i = 0
	while response1 == '' and i < 11:
		try:
			#response1 = requests.get('https://api.trakt.tv/shows/'+str(id)+'/progress/watched',headers=headers).json()
			response1 = get_trakt_data('https://api.trakt.tv/shows/'+str(id)+'/progress/watched', cache_days=0.00001)
		except:
			i = i + 1

	last_watched_at = ''
	next_season_to_watch  = ''
	next_ep_to_watch = ''
	try:
		for i in response1['seasons']:
			for j in i['episodes']:
				if last_watched_at == '':
					last_watched_at = j['last_watched_at']
				if j['last_watched_at'] != None:
					if last_watched_at != '' and last_watched_at <= j['last_watched_at']:
						last_watched_at  = j['last_watched_at']
						next_season_to_watch = i['number']
						next_ep_to_watch = j['number']
	except:
		last_watched_at = ''
		next_season_to_watch  = ''
		next_ep_to_watch = ''
		import sqlite3
		#import ast
		addon = xbmcaddon.Addon()
		addon_path = addon.getAddonInfo('path')
		addonID = addon.getAddonInfo('id')
		addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
		con = sqlite3.connect(str(Path(addonUserDataFolder + '/trakt_tv_watched.db')))
		cur = con.cursor()
		sql_query = "select * from trakt where trakt  like '%" + str(title) + "%'"
		sql_result = cur.execute(sql_query).fetchall()
		#try: response1 = ast.literal_eval(sql_result[0][1].replace('\'\'','"'))
		#except: response1= None
		try: response1 = eval(sql_result[0][1].replace("'overview': ''",'\'overview\': "').replace("'', 'first_aired':",'", \'first_aired\':').replace("'title': ''",'\'title\': "').replace("'', 'year':",'", \'year\':'))
		except: response1 = None
		try:
			for i in response1['seasons']:
				for j in i['episodes']:
					if last_watched_at == '':
						last_watched_at = j['last_watched_at']
					if last_watched_at != '' and last_watched_at <= j['last_watched_at']:
						last_watched_at  = j['last_watched_at']
						next_season_to_watch = i['number']
						next_ep_to_watch = j['number']
		except:
			xbmc.executebuiltin('Dialog.Close(busydialog)')
			xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
			xbmcgui.Dialog().notification(heading='Trakt Next Episode Rewatch', message='Not REWATCHING!', icon=icon_path(),time=1000,sound=False)
			return

	next_flag = 'false'
	for i in response1['seasons']:
		for j in i['episodes']:
			if next_flag == 'true':
				last_watched_at  = j['last_watched_at']
				next_season_to_watch = i['number']
				next_ep_to_watch = j['number']
				next_flag = 'false'
				break
			try:
				if int(i['number']) == int(next_season_to_watch) and int(j['number']) == int(next_ep_to_watch):
					next_flag = 'true'
			except:
				xbmc.executebuiltin('Dialog.Close(busydialog)')
				xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
				xbmcgui.Dialog().notification(heading='Trakt Next Episode Rewatch', message='Not REWATCHING!', icon=icon_path(),time=1000,sound=False)
				return

	try:	
		season = int(next_season_to_watch)
		episode = int(next_ep_to_watch)
	except:
		season = '1'
		episode = '1'

	response2 = ''
	i = 0
	while response2 == '' and i < 22:
		try:
			#response2 = requests.get('https://api.trakt.tv/shows/'+str(id)+'/seasons/'+str(season)+'/episodes/'+str(episode)+'?extended=full', headers=headers).json()
			response2 = get_trakt_data('https://api.trakt.tv/shows/'+str(id)+'/seasons/'+str(season)+'/episodes/'+str(episode)+'?extended=full', cache_days=0.00001)
		except:
			i = i + 1

	first_aired = response2['first_aired']
	#first_aired2 = datetime.datetime.strptime(first_aired, '%Y-%m-%dT%H:%M:%S.%fZ')
	import time
	try:
		first_aired2 = datetime.strptime(first_aired, '%Y-%m-%dT%H:%M:%S.%fZ')
	except TypeError:
		first_aired2 = datetime(*(time.strptime(first_aired, '%Y-%m-%dT%H:%M:%S.%fZ')[0:6]))

	now = datetime.now()

	if first_aired2 < now:
		url = 'plugin://plugin.video.themoviedb.helper?info=play&amp;type=episode&amp;tmdb_id='+ str(tmdb_id) + '&amp;season='+str(season)+'&amp;episode='+str(episode)
		xbmc.executebuiltin('Dialog.Close(busydialog)')
		return url
	else:
		xbmcgui.Dialog().notification(heading='Trakt Next Episode Rewatch', message='Next Episode Not aired yet', icon=icon_path(),time=1000,sound=False)

def trakt_calendar_hide_show(tmdb_id_num=None, unhide=False):
	import requests, json
	tmdb_id=tmdb_id_num
	try:
		#response = requests.get('https://api.trakt.tv/search/tmdb/'+str(tmdb_id)+'?type=show', headers=headers).json()
		response = get_trakt_data(url='https://api.trakt.tv/search/tmdb/'+str(tmdb_id)+'?type=show', cache_days=0.5)
	except:
		xbmc.executebuiltin('Dialog.Close(busydialog)')
	id = response[0]['show']['ids']['trakt']
	slug = response[0]['show']['ids']['slug']
	tvdb = response[0]['show']['ids']['tvdb']
	imdb = response[0]['show']['ids']['imdb']
	title = response[0]['show']['title']
	year = response[0]['show']['year']
	trakt_dict = {'shows': [{'title': title, 'year': year, 'ids': {'trakt': id, 'slug': slug, 'tvdb': tvdb, 'imdb': imdb, 'tmdb': tmdb_id}}]}

	values = """
	  {
		"shows": [
		  {
		  "title": """+'"'+title+'"'+ """,
		  "year": """+str(year)+""",
		  "ids": {
			"trakt": """+str(id)+""",
			"slug": """+'"'+slug+'"'+ """,
			"imdb": """+'"'+str(imdb)+'"'+ """,
			"tmdb": """+str(tmdb_id)+ """
			}
		  }
		]
	  }
	"""
	headers = trak_auth()
	if unhide:
		url = 'https://api.trakt.tv/users/hidden/calendar/remove'
	else:
		url = 'https://api.trakt.tv/users/hidden/calendar'
	response_collect = requests.post(url, data=values, headers=headers).json()
	return response_collect

def trakt_in_lists(type=None,imdb_id=None,return_var='movies'):
	from resources.lib import Utils
	import urllib.parse
	#import json
	#headers = trak_auth()
	if type == 'movie':
		#url = 'https://api.trakt.tv/movies/%s/lists/all/popular' % (imdb_id)
		url = 'https://api.trakt.tv/movies/%s/lists/personal/popular' % (imdb_id)
	else:
		#url = 'https://api.trakt.tv/shows/%s/lists/all/popular' % (imdb_id)
		url = 'https://api.trakt.tv/shows/%s/lists/personal/popular' % (imdb_id)
	response = get_trakt_data(url, 1)
	trakt_list = []
	for i in response:
		trakt_list.append(i['name'] + str(' (%s)') % i['item_count'])
	index = xbmcgui.Dialog().select(heading='Select Trakt List', list=trakt_list)
	if index == -1:
		if return_var == 'movies':
			return None
		else:
			return None, None, None, None, None
	list_name = response[index]['name']
	user_id = response[index]['user']['ids']['slug']
	list_slug = response[index]['ids']['slug']
	sort_by = response[index]['sort_by']
	sort_order = response[index]['sort_how']
	if return_var == 'movies':
		movies = trakt_lists(list_name=list_name,user_id=user_id,list_slug=list_slug,sort_by=sort_by,sort_order=sort_order)
		return movies
	else:
	   return list_name, user_id, list_slug, sort_by, sort_order

def trakt_lists(list_name=None,user_id=None,list_slug=None,sort_by=None,sort_order=None, limit=0):
	from resources.lib import Utils
	import urllib.parse
	#import json
	#headers = trak_auth()
	if list_slug.lower() == 'watchlist':
		url = 'https://api.trakt.tv/users/'+str(user_id)+'/watchlist'
	else:
		url = 'https://api.trakt.tv/users/'+str(user_id)+'/lists/'+str(list_slug)+'/items'
	#response = requests.get(url, headers=headers).json()

	from resources.lib.Utils import tools_log
	x = 1
	url1 = url + '?limit=250&page=' + str(x)
	tools_log(url1)
	response = get_trakt_data(url1, 1)
	item_count = len(response)
	tools_log(item_count)
	new_response = []
	if limit == 0:
		limit = 1000
	while item_count < limit:
		x = x + 1
		url1 = url + '?limit=250&page=' + str(x)
		tools_log(url1)
		old_response = response
		new_response = get_trakt_data(url1, 1)
		response = response + new_response
		if len(new_response) == 0 or new_response == old_response:
			break
		if x * 250 > limit:
			break
		item_count = len(response)
		tools_log(item_count)

	if sort_order == 'asc':
		reverse_order = False
	if sort_order == 'desc':
		reverse_order = True
	try: 
		response = sorted(response, key=lambda k: k[sort_by], reverse=reverse_order)
	except:
		try: 
			response = sorted(response, key=lambda k: k['listed_at'], reverse=False)
		except: 
			message = str('%s - List missing') % (urllib.parse.unquote(list_name))
			Utils.notify(message=message, time=1000, sound=False)
			return
	movies = []
	x = 0
	for i in response:
		try: 
			tmdb_id = i['movie']
			tmdb_id['type'] = 'movie'
		except:
			try:
				tmdb_id = i['show']
				tmdb_id['type'] = 'show'
			except:
				pass
		if tmdb_id not in movies:
			movies.append(tmdb_id)
		if x + 1 == int(limit) and limit != 0:
			break
		x = x + 1
	return movies

def get_trakt_data(url='', cache_days=14, folder='Trakt'):
	from resources.lib.Utils import get_JSON_response
	from resources.lib.Utils import tools_log
	headers = trak_auth()
	#tools_log(url,'url')
	#tools_log(headers,'headers')
	return get_JSON_response(url, cache_days, folder,headers=headers)

def trakt_refresh_all():
	try:
		trakt_watched_tv_movies_cleanup()
		trakt_watched_movies(cache_days=0.00001)
		trakt_watched_movies_full()
		trakt_watched_tv_shows_full()
		trakt_watched_tv_shows(cache_days=0.00001)
		trakt_popular_shows(cache_days=0.00001)
		trakt_popular_movies(cache_days=0.00001)
		trakt_trending_shows(cache_days=0.00001)
		trakt_trending_movies(cache_days=0.00001)
		trakt_collection_shows(cache_days=0.00001)
		trakt_collection_movies(cache_days=0.00001)
		trakt_watched_tv_movies_cleanup()
	except TypeError: 
		pass
	

def trakt_watched_movies(cache_days=None):
	#import requests
	#import json
	#headers = trak_auth()
	url = 'https://api.trakt.tv/sync/watched/movies'
	#response = requests.get(url, headers=headers).json()
	if cache_days:
		#response = get_trakt_data(url, cache_days)
		x = 1
		url = 'https://api.trakt.tv/sync/watched/movies?page=%s&limit=250' % (str(x))
		response = get_trakt_data(url=url, cache_days=cache_days)
		new_response = response
		while new_response != []:
			x = x + 1
			url = 'https://api.trakt.tv/sync/watched/movies?page=%s&limit=250' % (str(x))
			new_response = get_trakt_data(url=url, cache_days=cache_days)
			if new_response == []:
				break
			response.extend(new_response)
		#xbmc.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))+'===>OPENINFO', level=xbmc.LOGINFO)
	else:
		#response = get_trakt_data(url, 1)
		x = 1
		url = 'https://api.trakt.tv/sync/watched/movies?page=%s&limit=250' % (str(x))
		response = get_trakt_data(url=url, cache_days=1)
		new_response = response
		while new_response != []:
			x = x + 1
			url = 'https://api.trakt.tv/sync/watched/movies?page=%s&limit=250' % (str(x))
			new_response = get_trakt_data(url=url, cache_days=1)
			if new_response == []:
				break
			response.extend(new_response)
	reverse_order = True
	response = sorted(response, key=lambda k: k['last_updated_at'], reverse=reverse_order)
	return response
  
def trakt_watched_movies_full():
	#import requests
	#import json
	from resources.lib.Utils import tools_log
	from pathlib import Path
	headers = trak_auth()
	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
	url = 'https://api.trakt.tv/sync/watched/movies'
	trakt_watched_stats = xbmcaddon.Addon(addon_ID()).getSetting('trakt_watched_stats')
	if trakt_watched_stats == 'true':
		x = 1
		url = 'https://api.trakt.tv/sync/watched/movies?page=%s&limit=250' % (str(x))
		response = get_trakt_data(url=url, cache_days=0.000001)
		new_response = response
		while new_response != []:
			x = x + 1
			url = 'https://api.trakt.tv/sync/watched/movies?page=%s&limit=250' % (str(x))
			new_response = get_trakt_data(url=url, cache_days=0.000001)
			if new_response == []:
				break
			response.extend(new_response)
			#tools_log(new_response)
	else:
		trakt_data = None
		return None
	import os
	if os.path.exists(Path(addonUserDataFolder + '/trakt_movies_watched.db')):
		try: os.remove(Path(addonUserDataFolder + '/trakt_movies_watched.db'))
		except PermissionError: return

	import sqlite3
	con = sqlite3.connect(str(Path(addonUserDataFolder + '/trakt_movies_watched.db')))
	cur = con.cursor()

	sql_result = cur.execute("""
	CREATE TABLE trakt (
		tmdb_id INTEGER PRIMARY KEY,
		trakt VARCHAR NOT NULL
	);
	""").fetchall()
	con.commit()

	for i in response:
		sql_result = """
		INSERT INTO trakt (tmdb_id,trakt)
		VALUES( %s,%s);
		""" % (i['movie']['ids']['tmdb'],'"'+str(i).replace(" '',",' "",').replace("': ''", '\': "').replace("'', '",'", \'').replace('"','\'\'')+'"')
		sql_result = cur.execute(sql_result).fetchall()
		con.commit()
	cur.close()
	con.close()

def trakt_watched_tv_shows_full():
	import requests
	import json
	from pathlib import Path
	from resources.lib.Utils import tools_log
	#from resources.lib import Utils
	from datetime import datetime, timedelta
	headers = trak_auth()
	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress'
	trakt_watched_stats = xbmcaddon.Addon(addon_ID()).getSetting('trakt_watched_stats')
	#if trakt_watched_stats == 'true':
	#	#response = requests.get(url, headers=headers).json()
	#	response = get_trakt_data(url=url, cache_days=0.000001)
	#else:
	#	trakt_data = None
	#	return
#	if trakt_watched_stats == 'true':
#	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress'
#	trakt_watched_stats = xbmcaddon.Addon(addon_ID()).getSetting('trakt_watched_stats')
	if trakt_watched_stats == 'true':
		x = 1
		url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress&page=%s&limit=100' % (str(x))
		response = get_trakt_data(url=url, cache_days=0.000001)
		new_response = response
		while new_response != []:
			x = x + 1
			url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress&page=%s&limit=100' % (str(x))
			new_response = get_trakt_data(url=url, cache_days=0.000001)
			if new_response == []:
				break
			response.extend(new_response)
			#tools_log(new_response)
	else:
		trakt_data = None
		return None

	import os
	if os.path.exists(Path(addonUserDataFolder + '/trakt_tv_watched.db')):
		try: os.remove(Path(addonUserDataFolder + '/trakt_tv_watched.db'))
		except PermissionError: return

	import sqlite3
	con = sqlite3.connect(str(Path(addonUserDataFolder + '/trakt_tv_watched.db')))
	cur = con.cursor()

	sql_result = cur.execute("""
	CREATE TABLE trakt (
		tmdb_id INTEGER PRIMARY KEY,
		trakt VARCHAR NOT NULL
	);
	""").fetchall()
	con.commit()

	for i in response:
		last_updated_at = i['last_updated_at']
		updated_dt = datetime.strptime(last_updated_at,'%Y-%m-%dT%H:%M:%S.%fZ')
		within_last_X_days = updated_dt >= (datetime.utcnow() - timedelta(days=9))
		if within_last_X_days:
			#Utils.tools_log(i)
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=0.000001)
		else:
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=8)
		i['seasons'] = []

		for season in response2['seasons']:
			new_season = {'number': season['number'],'episodes': []}
			for ep in season['episodes']:
				new_season['episodes'].append({'number': ep['number'],'plays': ep['stats']['play_count'], 'last_watched_at': ep['last_watched_at']})
			i['seasons'].append(new_season)

		sql_result = """
		INSERT INTO trakt (tmdb_id,trakt)
		VALUES( %s,%s);
		""" % (i['show']['ids']['tmdb'],'"'+str(i).replace(" '',",' "",').replace("': ''", '\': "').replace("'', '",'", \'').replace('"','\'\'')+'"')
		sql_result = cur.execute(sql_result).fetchall()
		con.commit()
	cur.close()
	con.close()



def trakt_watched_tv_movies_cleanup():
	import requests
	import json
	headers = trak_auth()
	url = 'https://api.trakt.tv/sync/history'
	remove_url = 'https://api.trakt.tv/sync/history/remove'

	params = {'limit': 100}
	response = requests.get(url, headers=headers, params=params)
	total_items = response.headers.get('X-Pagination-Item-Count')
	try: response = response.json()
	except: return
	#xbmc.log(str(total_items)+'===>OPEN_INFO', level=xbmc.LOGFATAL)

	last_movie = None
	curr_movie = None
	history_id_list = []
	history_items_list = []

	for i in response:
		if i['type'] == 'episode':
			deets = '%s - S%sE%s' % (str(i['show']['ids']['slug']), str(i['episode']['season']), str(i['episode']['number']))
		else:
			deets = '%s' % (str(i['movie']['ids']['slug']))
		curr_movie = deets
		if curr_movie == last_movie:
			#xbmc.log(deets+'===>OPEN_INFO', level=xbmc.LOGFATAL)
			#xbmc.log(str(i['id'])+'===>OPEN_INFO', level=xbmc.LOGFATAL)
			history_id_list.append(i['id'])
			history_items_list.append(deets)
		last_movie = deets
	# Payload with the history ID
	if len(history_id_list) > 0:
		payload = {"ids": history_id_list}
		response = requests.post(remove_url, headers=headers, json=payload)
		response = response.json()
		xbmc.log(str(response)+'===>OPEN_INFO', level=xbmc.LOGFATAL)
		xbmc.log(str(history_items_list)+'===>OPEN_INFO', level=xbmc.LOGFATAL)
	return
	#url = 'https://api.trakt.tv/sync/watched/movies'
	#response = get_trakt_data(url=url, cache_days=0.000001)

"""
def trakt_watched_get(mode=None):
	return None
	from resources.lib.Utils import show_busy
	show_busy()
	trakt_watched_stats = xbmcaddon.Addon(addon_ID()).getSetting('trakt_watched_stats')
	if trakt_watched_stats == 'false':
		return None

	from pathlib import Path
	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)

	if mode == 'tv':
		trakt_data_file = open(Path(addonUserDataFolder + '/trakt_tv_watched'), "r")	
	else:
		trakt_data_file = open(Path(addonUserDataFolder + '/trakt_movies_watched'), "r")

	from threading import Thread
	import threading
	class TraktWatchedThread(threading.Thread):

		def __init__(self, trakt_data_file=None):
			threading.Thread.__init__(self)
			self.trakt_data_file = trakt_data_file

		def run(self):
			import ast
			self.trakt_data_file_read = ast.literal_eval(trakt_data_file.read())

	trakt_data_file_thread = TraktWatchedThread(trakt_data_file)
	trakt_data_file_thread.start()

	trakt_data_file_thread.join()
	trakt_data_file_read = trakt_data_file_thread.trakt_data_file_read 
	return trakt_data_file_read
"""

def trakt_watched_tv_shows_progress(cache_days=None):
	#import requests
	#import json
	#headers = trak_auth()
	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress'
	#response = requests.get(url, headers=headers).json()
	#response = get_trakt_data(url, 0.125)

	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress'

	x = 1
	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress&page=%s&limit=100' % (str(x))
	response = get_trakt_data(url=url, cache_days=0.125)
	new_response = response
	while new_response != []:
		x = x + 1
		url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress&page=%s&limit=100' % (str(x))
		new_response = get_trakt_data(url=url, cache_days=0.125)
		if new_response == []:
			break
		response.extend(new_response)


	new_response = []
	for i in response:
		last_updated_at = i['last_updated_at']
		updated_dt = datetime.strptime(last_updated_at,'%Y-%m-%dT%H:%M:%S.%fZ')
		within_last_X_days = updated_dt >= (datetime.utcnow() - timedelta(days=9))
		if within_last_X_days:
			#Utils.tools_log(i)
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=0.000001)
		else:
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=8)
		i['seasons'] = []

		for season in response2['seasons']:
			new_season = {'number': season['number'],'episodes': []}
			for ep in season['episodes']:
				new_season['episodes'].append({'number': ep['number'],'plays': ep['stats']['play_count'], 'last_watched_at': ep['last_watched_at']})
			i['seasons'].append(new_season)
		new_response.append(i)
	response = new_response



	response2 = []
	for i in response:
		x = 0
		aired_episodes = i['show']['aired_episodes']
		tmdb_id = i['show']['ids']['tmdb']
		show_title = i['show']['title']
		for j in i['seasons']:
			for k in j['episodes']:
				if int(k['plays']) >= 1:
					x = x + 1
		played_episodes = x
		if aired_episodes > played_episodes:
			response2.append(i)
			print(show_title, tmdb_id, aired_episodes, played_episodes)

	#reverse_order = True
	#response = sorted(response2, key=lambda k: k['updated_at'], reverse=reverse_order)
	return response2


def trakt_watched_tv_shows(cache_days=None):
	#import requests
	#import json
	#headers = trak_auth()
	url = 'https://api.trakt.tv/sync/watched/shows?extended=noseasons'
	#response = requests.get(url, headers=headers).json()
	#response = get_trakt_data(url, 0)

	x = 1
	url = 'https://api.trakt.tv/sync/watched/shows?extended=noseasons&page=%s&limit=250' % (str(x))
	response = get_trakt_data(url=url, cache_days=0)
	new_response = response
	while new_response != []:
		x = x + 1
		url = 'https://api.trakt.tv/sync/watched/shows?extended=noseasons&page=%s&limit=250' % (str(x))
		new_response = get_trakt_data(url=url, cache_days=0)
		if new_response == []:
			break
		response.extend(new_response)

	reverse_order = True
	response = sorted(response, key=lambda k: k['last_updated_at'], reverse=reverse_order)
	return response


def trakt_unwatched_tv_shows(cache_days=None,conn=None):
	#import requests
	#import json
	#headers = trak_auth()
	from resources.lib import Utils
	if conn:
		Utils.db_con = conn
	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress'
	#response = requests.get(url, headers=headers).json()
	#response = get_trakt_data(url, 0)

	x = 1
	url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress&page=%s&limit=100' % (str(x))
	response = get_trakt_data(url=url, cache_days=0)
	new_response = response
	while new_response != []:
		x = x + 1
		url = 'https://api.trakt.tv/sync/watched/shows?extended=full,progress&page=%s&limit=100' % (str(x))
		new_response = get_trakt_data(url=url, cache_days=0)
		if new_response == []:
			break
		response.extend(new_response)


	new_response = []
	for i in response:
		last_updated_at = i['last_updated_at']
		updated_dt = datetime.strptime(last_updated_at,'%Y-%m-%dT%H:%M:%S.%fZ')
		within_last_X_days = updated_dt >= (datetime.utcnow() - timedelta(days=9))
		if within_last_X_days:
			#Utils.tools_log(i)
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=0.000001)
		else:
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=8)
		i['seasons'] = []

		for season in response2['seasons']:
			new_season = {'number': season['number'],'episodes': []}
			for ep in season['episodes']:
				new_season['episodes'].append({'number': ep['number'],'plays': ep['stats']['play_count'], 'last_watched_at': ep['last_watched_at']})
			i['seasons'].append(new_season)
		new_response.append(i)
	response = new_response

	reverse_order = True
	response = sorted(response, key=lambda k: k['last_updated_at'], reverse=reverse_order)

	shows_last_watched = {}
	for i in response:
		watched_episodes = 0
		shows_last_watched[i['show']['ids']['tmdb']] = {}
		shows_last_watched[i['show']['ids']['tmdb']]['name'] = i['show']['title'] 
		shows_last_watched[i['show']['ids']['tmdb']]['aired_episodes'] = i['show']['aired_episodes']
		shows_last_watched[i['show']['ids']['tmdb']]['imdb'] = i['show']['ids']['imdb']
		response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['show']['ids']['trakt'])+'/progress/watched?extended=full', cache_days=7)
		i['seasons'] = response2['seasons']
		#Utils.tools_log(response2)
		#for x in response2:
		#	Utils.tools_log(x)
		#	Utils.tools_log(response2[x])
		old_shows_last_watched = None
		for s in i['seasons']:
			shows_last_watched[i['show']['ids']['tmdb']]['season'] = s['number']
			for e in s['episodes']:
				watched_episodes = watched_episodes + 1
				shows_last_watched[i['show']['ids']['tmdb']]['episode'] = e['number']
				shows_last_watched[i['show']['ids']['tmdb']]['last_watched_at'] = e['last_watched_at']
				#Utils.tools_log(e)
				try: 
					shows_last_watched[i['show']['ids']['tmdb']]['last_watched_timestamp'] = datetime.fromisoformat(e['last_watched_at'][:-1] + '+00:00').timestamp()
					continue
				except: 
					shows_last_watched[i['show']['ids']['tmdb']]['last_watched_timestamp'] = datetime.fromisoformat(response2['last_watched_at'][:-1] + '+00:00').timestamp()
					continue
				try: shows_last_watched[i['show']['ids']['tmdb']]['last_watched_timestamp'] = datetime.fromisoformat(response2['next_episode']['first_aired'][:-1] + '+00:00').timestamp()
				except: pass

		shows_last_watched[i['show']['ids']['tmdb']]['watched_episodes'] = watched_episodes
		#break

	url = 'https://api.trakt.tv/sync/collection/shows'
	#response = requests.get(url, headers=headers).json()
	if cache_days:
		response = get_trakt_data(url, cache_days)
	else:
		response = get_trakt_data(url, 0.125)
	reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	new_list = []
	for i in response:
		new_list.append(i['show'])
	response = sorted(new_list , key=lambda k: k['title'], reverse=False)

	coll_unwatched = {}
	for i in response:
		if i['ids']['tmdb'] not in list(shows_last_watched):
			coll_unwatched[i['ids']['tmdb']] = {}
			coll_unwatched[i['ids']['tmdb']]['name'] = i['title']
			coll_unwatched[i['ids']['tmdb']]['year'] = i['year']
			coll_unwatched[i['ids']['tmdb']]['date'] = str(i['year']) + '-12-31T12:00:00.000Z'
			response2 = get_trakt_data(url='https://api.trakt.tv/shows/'+str(i['ids']['trakt'])+'/progress/watched?extended=full', cache_days=7)
			#xbmc.log(str(response2)+'===>OPEN_INFO', level=xbmc.LOGINFO)
			coll_unwatched[i['ids']['tmdb']]['date_timestamp'] = datetime.fromisoformat(str(i['year']) + '-12-31T12:00:00.000Z'[:-1] + '+00:00').timestamp()
			try: coll_unwatched[i['ids']['tmdb']]['date_timestamp'] = datetime.fromisoformat(response2['next_episode']['first_aired'][:-1] + '+00:00').timestamp()
			except: pass
			coll_unwatched[i['ids']['tmdb']]['imdb'] = i['ids']['imdb']
		#break

	#shows_last_watched2 = sorted(unwatched , key=lambda k: shows_last_watched[k]['last_watched_timestamp'], reverse=True)
	shows_unwatched = {}
	for i in shows_last_watched:
		if shows_last_watched[i]['aired_episodes'] > shows_last_watched[i]['watched_episodes']:
			shows_unwatched[i] = {}
			shows_unwatched[i] = shows_last_watched[i]

	unwatched = {}
	for i in coll_unwatched:
		unwatched[i] = {}
		unwatched[i]['date_timestamp'] = coll_unwatched[i]['date_timestamp']

	for i in shows_unwatched:
		unwatched[i] = {}
		unwatched[i]['date_timestamp'] = shows_last_watched[i]['last_watched_timestamp']

	unwatched2 = sorted(unwatched , key=lambda k: unwatched[k]['date_timestamp'], reverse=True)
	unwatched = {}
	for i in unwatched2:
		unwatched[i] = {}
		try: 
			unwatched[i] = shows_last_watched[i]
			unwatched[i]['ids'] = {}
			unwatched[i]['ids']['imdb'] = shows_last_watched[i]['imdb']
			unwatched[i]['show'] = {}
			unwatched[i]['show']['ids'] = {}
			unwatched[i]['show']['ids']['imdb'] = shows_last_watched[i]['imdb']
			unwatched[i]['show']['ids']['tmdb'] = i
			
		except: 
			unwatched[i] = coll_unwatched[i]
			unwatched[i]['ids'] = {}
			unwatched[i]['ids']['imdb'] = coll_unwatched[i]['imdb']
			unwatched[i]['show'] = {}
			unwatched[i]['show']['ids'] = {}
			unwatched[i]['show']['ids']['imdb'] = coll_unwatched[i]['imdb']
			unwatched[i]['show']['ids']['tmdb'] = i
		unwatched[i]['tmdb'] = i
		unwatched[i]['ids']['tmdb'] = i
	unwatched_list = []
	for i in unwatched:
		unwatched_list.append(unwatched[i])
	xbmc.log(str('trakt.trakt_unwatched_tv_shows()_finished')+'===>OPEN_INFO', level=xbmc.LOGINFO)
	return unwatched_list


def trakt_collection_movies(cache_days=None):
	import requests
	import json

	headers = trak_auth()
	url = 'https://api.trakt.tv/sync/collection/movies'
	#response = requests.get(url, headers=headers).json()
	if cache_days:
		response = get_trakt_data(url, cache_days)
	else:
		response = get_trakt_data(url, 0.125)
	reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	new_list = []
	for i in response:
		new_list.append(i['movie'])
	response = sorted(new_list , key=lambda k: k['title'], reverse=False)
	return response

def trakt_unwatched_collection_movies():
	response1 = trakt_watched_movies()
	response2 = trakt_collection_movies()
	response = []
	for i in response2:
		if i['ids']['slug'] not in str(response1):
			response.append(i)
	return response

def trakt_uncollected_watched_movies():
	response1 = trakt_watched_movies()
	response2 = trakt_collection_movies()
	response = []
	for i in response1:
		if i['movie']['ids']['slug'] not in str(response2):
			response.append(i)
	return response


def trakt_collection_shows(cache_days=None):
	import requests
	import json

	headers = trak_auth()
	url = 'https://api.trakt.tv/sync/collection/shows'
	#response = requests.get(url, headers=headers).json()
	if cache_days:
		response = get_trakt_data(url, cache_days)
	else:
		response = get_trakt_data(url, 0.125)
	reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	new_list = []
	if response == None:
		return new_list
	for i in response:
		new_list.append(i['show'])
	response = sorted(new_list , key=lambda k: k['title'], reverse=False)
	return response

def trakt_trending_movies(cache_days=None):
	import requests
	import json

	headers = trak_auth()
	url = 'https://api.trakt.tv/movies/trending?limit=600'
	urls = ['https://api.trakt.tv/movies/trending?limit=250&page=1', 'https://api.trakt.tv/movies/trending?limit=250&page=2', 'https://api.trakt.tv/movies/trending?limit=100&page=3']
	response = []
	for i in urls:
		url = i
		if cache_days:
			response = response + get_trakt_data(url, cache_days)
		else:
			response = response + get_trakt_data(url, 1)
	#reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	#new_list = []
	#for i in response:
	#	new_list.append(i['show'])
	#response = sorted(new_list , key=lambda k: k['title'], reverse=False)
	return response

def trakt_trending_shows(cache_days=None):
	import requests
	import json

	headers = trak_auth()
	url = 'https://api.trakt.tv/shows/trending?limit=600'
	urls = ['https://api.trakt.tv/shows/trending?limit=250&page=1', 'https://api.trakt.tv/shows/trending?limit=250&page=2', 'https://api.trakt.tv/shows/trending?limit=100&page=3']
	response = []
	for i in urls:
		url = i
		if cache_days:
			response = response + get_trakt_data(url, cache_days)
		else:
			response = response + get_trakt_data(url, 1)
	#reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	#new_list = []
	#for i in response:
	#	new_list.append(i['show'])
	#response = sorted(new_list , key=lambda k: k['title'], reverse=False)
	return response

def trakt_popular_movies(cache_days=None):
	#import requests
	#import json
	#headers = trak_auth()
	url = 'https://api.trakt.tv/movies/popular?limit=600'
	urls = ['https://api.trakt.tv/movies/popular?limit=250&page=1', 'https://api.trakt.tv/movies/popular?limit=250&page=2', 'https://api.trakt.tv/movies/popular?limit=100&page=3']
	response = []
	for i in urls:
		url = i
		if cache_days:
			response = response + get_trakt_data(url, cache_days)
		else:
			response = response + get_trakt_data(url, 1)
	#reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	#new_list = []
	#for i in response:
	#	new_list.append(i['show'])
	#response = sorted(new_list , key=lambda k: k['title'], reverse=False)
	return response

def trakt_popular_shows(cache_days=None):
	#import requests
	#import json
	#headers = trak_auth()
	url = 'https://api.trakt.tv/shows/popular?limit=600'
	urls = ['https://api.trakt.tv/shows/popular?limit=250&page=1', 'https://api.trakt.tv/shows/popular?limit=250&page=2', 'https://api.trakt.tv/shows/popular?limit=100&page=3']
	response = []
	for i in urls:
		url = i
		if cache_days:
			response = response + get_trakt_data(url, cache_days)
		else:
			response = response + get_trakt_data(url, 1)
	#reverse_order = True
	#response = sorted(response, key=lambda k: k['collected_at'], reverse=reverse_order)

	#new_list = []
	#for i in response:
	#	new_list.append(i['show'])
	#response = sorted(new_list , key=lambda k: k['title'], reverse=False)
	return response


def trak_auth():
	from resources.lib.trakt_api import get_trakt_auth
	headers = get_trakt_auth()
	return headers

