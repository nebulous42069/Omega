import os, re, time, json, urllib.request, urllib.parse, urllib.error, hashlib, requests, threading, sys
from datetime import datetime
import time
from datetime import date
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, xbmcplugin
from functools import wraps
from resources.lib.trakt import addon_ID
#from resources.lib.trakt import fanart_api_key

try: from infotagger.listitem import ListItemInfoTag
except: pass

from inspect import currentframe, getframeinfo
#log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))

ADDON_PATH = xbmcvfs.translatePath('special://home/addons/'+str(addon_ID()))
ADDON_DATA_PATH = xbmcvfs.translatePath('special://profile/addon_data/'+str(addon_ID()))
CACHE_PATH = xbmcvfs.translatePath('special://profile/addon_data/'+str(addon_ID())+'/cache.db')

IMAGES_DATA_PATH = xbmcvfs.translatePath('special://profile/addon_data/'+str(addon_ID())+'/images')
SKIN_DIR = xbmc.getSkinDir()
if 'skin.estuary' in str(SKIN_DIR):
	SKIN_DIR = 'skin.estuary'
def netflix_view(info_only=False):
	addon = xbmcaddon.Addon('script.diggzportal')
	return addon.getSettingBool('netflix_view') or (info_only and addon.getSettingBool('netflix_info_view'))

window_stack_enable = 'true'  # Window stack is always enabled.


def set_setting(setting_name, setting_value):
	#setting_line = '    <setting id="%s">%s</setting>' % (setting_name, setting_value)
	new_setting_file = ''
	update = False
	ADDON_USERDATA_PATH = ADDON_DATA_PATH
	SETTING_XML = os.path.join(ADDON_USERDATA_PATH, 'settings.xml')
	with open(SETTING_XML) as f:
		lines = f.readlines()
		for line in lines:
			if setting_name in str(line):
				line_split_1 = line.split('"')[0] + '"'
				line_split_2 = setting_name
				line_split_3 = '"' + line.split('"',2)[2].split('>')[0] + '>'
				line_split_4 = setting_value
				try: line_split_5 = '<' + line.split('"',2)[2].split('<')[1]
				except: line_split_5 = '</setting>\n'
				setting_line = str(line_split_1) + str(line_split_2) + str(line_split_3) + str(line_split_4) + str(line_split_5)
				setting_line = setting_line.replace('default="true" />','default="true">')
				setting_line = setting_line.replace(' />','>')
				new_setting_file = new_setting_file + setting_line
				if setting_line != line:
					update = True
			else:
				new_setting_file = new_setting_file + line
	if update == True:
		with open(SETTING_XML, 'w') as file:
			# Write new content to the file
			file.write(new_setting_file)


db_con = None
def test_db():
	import sqlite3
	os.makedirs(ADDON_DATA_PATH, exist_ok=True)
	db_con = sqlite3.connect(CACHE_PATH, check_same_thread=False)
	return db_con

def encode_db(sample_string):
	import base64
	sample_string_bytes = sample_string.encode("ascii")
	base64_bytes = base64.b64encode(sample_string_bytes)
	base64_string = base64_bytes.decode("ascii")
	return base64_string

def decode_db(base64_string):
	import base64
	base64_bytes = base64_string.encode("ascii")
	sample_string_bytes = base64.b64decode(base64_bytes)
	sample_string = sample_string_bytes.decode("ascii")
	return sample_string

def clear_db(connection=None,table_name=None):
	if db_con == None:
		connection = test_db()
	cur = connection.cursor()
	#dbfile = '/home/osmc/.kodi/userdata/addon_data/script.diggzportal/cache.db'
	#con = sqlite3.connect(dbfile)
	#cur = con.cursor()

	table_list = [a for a in cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
	for i in table_list:
		#cur.execute("SELECT * from %s" % (i)).fetchall()
		if table_name:
			i = table_name#
		tools_log(str(i))
		result = cur.execute('SELECT * FROM %s' % (i)).fetchall()
		tools_log(str(len(result)))
		cur.execute('DELETE FROM %s' % (i))
		tools_log(str('DELETE FROM %s ' % (i))) 
		if table_name:
			break
	connection.commit()
	cur.execute('VACUUM')
	cur.close()

def tools_log(*args, **kwargs):
	for i in args:
		try:
			import xbmc
			xbmc.log(str(i)+'===>diggzportal', level=xbmc.LOGINFO)
		except:
			print(i)


def write_db(connection=None,url=None, cache_days=7.0, folder=False,cache_val=None, headers=False):
	if db_con == None:
		connection = test_db()
	try: cur = connection.cursor()
	except: connection = test_db()
	try: url = url.encode('utf-8')
	except: pass
	hashed_url = hashlib.md5(url).hexdigest()
	cache_seconds = int(cache_days * 86400.0)
	#tools_log(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))
	#tools_log(cache_val)
	if isinstance(cache_val, str) == True:
		cache_val = encode_db(cache_val)
		cache_type = 'str'
	elif isinstance(cache_val, list) == True or isinstance(cache_val, dict) == True:
		try: 
			cache_val = encode_db(json.dumps(cache_val))
			cache_type = 'json'
		except: 
			cache_val = encode_db(str(cache_val))
			cache_type = 'list'

	expire = round(time.time() + cache_seconds,0)
	sql_query = """
	CREATE TABLE IF NOT EXISTS %s (
		url VARCHAR PRIMARY KEY,
		cache_val BLOB NOT NULL,
		cache_type VARCHAR NOT NULL,
		expire INT NOT NULL
	); 
	""" % (folder)
	sql_result = cur.execute(sql_query).fetchall()
	try: 
		connection.commit()
	except:
		connection.commit()
	sql_query = """
	INSERT INTO %s (url,cache_val,cache_type,expire)
	VALUES( '%s','%s','%s',%s);
	""" % (folder, hashed_url,cache_val,cache_type,int(expire))
	#sql_result = cur.execute(sql_query).fetchall()
	try: 
		sql_result = cur.execute(sql_query).fetchall()
	except Exception as ex:
		if 'UNIQUE constraint failed' in str(ex):
			sql_query = """
			REPLACE INTO %s (url,cache_val,cache_type,expire)
			VALUES( '%s','%s','%s',%s);
			""" % (folder, hashed_url,cache_val,cache_type,int(expire))
			sql_result = cur.execute(sql_query).fetchall()
	try: 
		connection.commit()
	except:
		try: connection.commit()
		except: pass
	cur.close()

def query_db(connection=None,url=None, cache_days=7.0, folder=False, headers=False):
	if db_con == None:
		connection = test_db()
	cur = connection.cursor()
	#if cache_days == 0:
	#	cache_days = 7
	try: url = url.encode('utf-8')
	except: pass
	cache_val = None
	cache_seconds = int(cache_days * 86400.0)
	hashed_url = hashlib.md5(url).hexdigest()

	sql_query = """select cache_val, expire,cache_type from %s
	where url = '%s'
	""" % (folder, hashed_url)


	try: 
		sql_result = cur.execute(sql_query).fetchall()
	except Exception as ex:
		if 'no such table' in str(ex):
			return None, None
		else:
			tools_log(str(ex))
	if len(sql_result) ==0:
		cur.close()
		return None, None

	#if cache_days <=0.00001:
	#	tools_log(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))
	#	tools_log(str(url))
	#	tools_log(str(int(time.time()))+str('<><>')+str(int(sql_result[0][1])))
	
	expire = round(time.time() + cache_seconds,0)
	cache_type = sql_result[0][2]
	if cache_type == 'str':
		cache_val = decode_db(sql_result[0][0])
	elif cache_type == 'list':
		cache_val = eval(decode_db(sql_result[0][0]))
	elif cache_type == 'json':
		cache_val = json.loads(decode_db(sql_result[0][0]))

	if int(time.time()) >= int(sql_result[0][1]) or expire <= int(sql_result[0][1]) :
		sql_query = """DELETE FROM %s
		where url = '%s'
		""" % (folder, hashed_url)
		sql_result = cur.execute(sql_query).fetchall()
		connection.commit()
		cur.close()
		return None, cache_val
	else:
		cur.close()
		return cache_val, None

def db_delete_expired(connection=None):
	if db_con == None:
		connection = test_db()
	cur = connection.cursor()
	curr_time = int(time.time())
	db_delete_expired_query = """SELECT * FROM sqlite_master WHERE type='table'
	"""  
	sql_result = cur.execute(db_delete_expired_query).fetchall()
	tools_log('DELETE____')
	for i in sql_result:
		folder = i[1]
		#tools_log(folder)
		#tools_log(str(folder))
		#db_delete_expired_query = """select * FROM %s
		#where expire < %s
		#""" % (folder, curr_time)
		#sql_result = cur.execute(db_delete_expired_query).fetchall()
		#tools_log(str(len(sql_result))+str(folder))
		db_delete_expired_query = """select * FROM %s
		where expire < %s
		""" %  (folder, curr_time)
		sql_result1 = cur.execute(db_delete_expired_query).fetchall()
		if len(sql_result1) == 0:
			continue
		tools_log(folder)
		db_delete_expired_query = """DELETE FROM %s
		where expire < %s
		""" % (folder, curr_time)
		sql_result2 = cur.execute(db_delete_expired_query).fetchall()
		tools_log(str(len(sql_result1))+str(folder),'===>DELETED')
	connection.commit()
	try: cur.execute('VACUUM')
	except Exception as ex:
		if 'SQL statements in progress' in str(ex):
			return None
		else:
			tools_log(str(ex))
	cur.close()
	tools_log('DELETED')
	return None

def normalize_path(path):
	import re
	if not isinstance(path, str):
		return path

	# Preserve URL schemes like http://, https://, smb:// etc.
	match = re.match(r'^([a-zA-Z]+://)', path)
	prefix = match.group(1) if match else ''

	# Remove prefix temporarily
	rest = path[len(prefix):]

	# Replace multiple slashes/backslashes with single forward slash
	rest = re.sub(r'[\\/]+', '/', rest)

	return prefix + rest


db_con = test_db()

def show_busy():
	#window_id = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"GUI.GetProperties","params":{"properties":["currentwindow", "currentcontrol"]},"id":1}')
	#window_id = json.loads(window_id)
	#if not window_id['result']['currentwindow']['id'] == 10025 and not window_id['result']['currentwindow']['id'] > 13000:
	if str(os.environ.get('first_run', 'False')) == 'True':
		os.environ['first_run'] = str('False')
		return
	if 'widget=true' in str(sys.argv) or 'autocomplete' in str(sys.argv) or xbmc.getCondVisibility('Window.IsActive(12000)'):
		return
	elif xbmc.Player().isPlaying():
		return
	elif int(xbmc.getInfoLabel('System.BuildVersion')[:2]) > 17:
		xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
	else:
		xbmc.executebuiltin('ActivateWindow(busydialog)')

def hide_busy():
	if int(xbmc.getInfoLabel('System.BuildVersion')[:2]) > 17:
		xbmc.sleep(250)
		xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
		xbmc.executebuiltin('Dialog.Close(busydialog)')
		xbmc.executebuiltin('Dialog.Close(ExtendedProgressDialog,True)')
		xbmc.executebuiltin('Dialog.Close(progressdialog,True)')
	else:
		xbmc.sleep(250)
		xbmc.executebuiltin('Dialog.Close(busydialog)')


def context_play(window=None, tmdb_id=None, listitem=None):
	from resources.lib.tmdb_helper import choose_player
	info = getattr(window, 'info', {})
	kind = (listitem and listitem.getProperty('media_type')) or info.get('media_type') or xbmc.getInfoLabel('ListItem.DBTYPE')
	params = {'info': 'play', 'tmdb_id': tmdb_id}
	if kind in ('tv', 'tvshow', 'episode', 'season'):
		params.update(type='episode', season=info.get('season') or xbmc.getInfoLabel('ListItem.Season') or 1,
					  episode=info.get('episode') or xbmc.getInfoLabel('ListItem.Episode') or 1)
	else:
		params['type'] = 'movie'
	choose_player('plugin://plugin.video.themoviedb.helper/?' + urllib.parse.urlencode(params))



def busy_dialog(func):
	@wraps(func)
	def decorator(self, *args, **kwargs):
		show_busy()
		result = func(self, *args, **kwargs)
		hide_busy()
		return result
	return decorator


def run_async(func):
	@wraps(func)
	def async_func(*args, **kwargs):
		func_hl = threading.Thread(target=func, args=args, kwargs=kwargs)
		func_hl.start()
		return func_hl
	return async_func

def translate_path(*args):
	return xbmcvfs.translatePath(os.path.join(*args))



def dictfind(lst, key, value):
	for i, dic in enumerate(lst):
		if dic[key] == value:
			return dic
	return ''

def format_time(time, format=None):
	try:
		intTime = int(time)
	except:
		return time
	hour = str(intTime / 60)
	minute = str(intTime % 60).zfill(2)
	if format == 'h':
		return round(float(hour),2)
	elif format == 'm':
		return minute
	elif intTime >= 60:
		return str(int(float(hour))) + 'h ' + minute + 'm'
	else:
		return minute + 'm'

def url_quote(input_string):
	try:
		return urllib.parse.quote_plus(input_string.encode('utf8', 'ignore'))
	except:
		return urllib.parse.quote_plus(str(input_string, 'utf-8').encode('utf-8'))

def calculate_age(born, died=False):
	if died:
		ref_day = died.split('-')
	elif born:
		date1 = date.today()
		ref_day = [date1.year, date1.month, date1.day]
	else:
		return ''
	actor_born = born.split('-')
	base_age = int(ref_day[0]) - int(actor_born[0])
	if len(actor_born) > 1:
		diff_months = int(ref_day[1]) - int(actor_born[1])
		diff_days = int(ref_day[2]) - int(actor_born[2])
		if diff_months < 0 or (diff_months == 0 and diff_days < 0):
			base_age -= 1
		elif diff_months == 0 and diff_days == 0 and not died:
			notify('Happy Birthday (%i)' % base_age)
	return base_age

def millify(n):
	millnames = [' ', '.000', ' ' + 'Million', ' ' + 'Billion', ' ' + 'Trillion']
	if not n or n <= 100:
		return ''
	n = float(n)
	char_count = len(str(n))
	millidx = int((char_count / 3)) - 1
	if millidx == 3 or char_count == 9:
		return '%.2f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
	else:
		return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])


def fetch(dictionary, key):
	if key in dictionary:
		if dictionary[key] is not None:
			return dictionary[key]
	else:
		return ''

def get_year(year_string):
	if year_string and len(year_string) > 3:
		return year_string[:4]
	else:
		return ''

def get_http(url, headers=False):
	succeed = 0
	if not headers:
		headers = {'User-agent': 'Kodi/18.0 ( phil65@kodi.tv )'}
	while (succeed < 2) :
		try:
			request = requests.get(url, headers=headers, timeout=5)
			if 'Trakt is down for scheduled' in str(request.text):
				return None
			return request.text
		except Exception as e:
			log('get_http: could not get data from %s' % url)
			xbmc.sleep(500)
			succeed += 1
	return None

def get_JSON_response(url='', cache_days=7.0, folder=False, headers=False):
	now = time.time()
	url = url.encode('utf-8')
	hashed_url = hashlib.md5(url).hexdigest()
	cache_seconds = int(cache_days * 86400.0)

	try: 
		db_result, expired_db_result = query_db(connection=db_con,url=url, cache_days=cache_days, folder=folder, headers=headers)
	except:
		db_result, expired_db_result = None, None
	try: 
		db_result_flag = True if len(db_result)> 0 else False
	except: 
		db_result_flag = False
	if db_result_flag:
		return db_result
	else:
		response = get_http(url, headers)
		try: results = json.loads(response)
		except: results = []
	if not results or len(results) == 0:
		if expired_db_result == None:
			return []
		if len(expired_db_result) > 0:
			write_db(connection=db_con,url=url, cache_days=0.25, folder=folder,cache_val=expired_db_result)
			return expired_db_result
		return []
	else:
		write_db(connection=db_con,url=url, cache_days=cache_days, folder=folder,cache_val=results)
	return results


class GetFileThread(threading.Thread):
	def __init__(self, url):
		threading.Thread.__init__(self)
		self.url = url

	def run(self):
		self.file = get_file(self.url)

def get_file(url):
	clean_url = translate_path(urllib.parse.unquote(url)).replace('image://', '')
	clean_url = clean_url.rstrip('/')
	cached_thumb = xbmc.getCacheThumbName(clean_url)
	vid_cache_file = os.path.join('special://profile/Thumbnails/Video', cached_thumb[0], cached_thumb)
	cache_file_jpg = os.path.join('special://profile/Thumbnails/', cached_thumb[0], cached_thumb[:-4] + '.jpg').replace('\\', '/')
	cache_file_png = cache_file_jpg[:-4] + '.png'
	if xbmcvfs.exists(cache_file_jpg):
		log('cache_file_jpg Image: %s --> %s' % (url, cache_file_jpg))
		return translate_path(cache_file_jpg)
	elif xbmcvfs.exists(cache_file_png):
		log('cache_file_png Image: %s --> %s' % (url, cache_file_png))
		return cache_file_png
	elif xbmcvfs.exists(vid_cache_file):
		log('vid_cache_file Image: %s --> %s' % (url, vid_cache_file))
		return vid_cache_file
	try:
		r = requests.get(clean_url, stream=True, timeout=5)
		if r.status_code != 200:
			return ''
		data = r.content
		log('image downloaded: %s' % clean_url)
	except Exception as e:
		log('image download failed: %s' % clean_url)
		return ''
	if not data:
		return ''
	image = cache_file_png if url.endswith('.png') else cache_file_jpg
	try:
		with open(translate_path(image), 'wb') as f:
			f.write(data)
		return translate_path(image)
	except Exception as e:
		log('failed to save image %s' % url)
		return ''

def log(txt):
	if isinstance(txt, str):
		message = ''+str(addon_ID())+':  %s' % txt
	tools_log(str(message),'Utils.log')

def get_browse_dialog(default='', heading='Browse', dlg_type=3, shares='files', mask='', use_thumbs=False, treat_as_folder=False):
	value = xbmcgui.Dialog().browse(dlg_type, heading, shares, mask, use_thumbs, treat_as_folder, default)
	return value

def save_to_file(content, filename, path=''):
	if path == '':
		text_file_path = '%s%s.txt' % (get_browse_dialog(), filename)
	else:
		if not xbmcvfs.exists(path):
			xbmcvfs.mkdirs(path)
		text_file_path = os.path.join(path, '%s.txt' % filename)
	now = time.time()
	text_file = xbmcvfs.File(text_file_path, 'w')
	json.dump(content, text_file)
	text_file.close()
	log('saved textfile %s. Time: %f' % (text_file_path, time.time() - now))
	return True

def read_from_file(path='', raw=False):
	if path == '':
		path = get_browse_dialog(dlg_type=1)
	if not xbmcvfs.exists(path):
		return False
	try:
		with open(path) as f:
			log('opened textfile  %s' % path)
			if not raw:
				result = json.load(f)
			else:
				result = f.read()
		return result
	except:
		log('failed to load textfile: %s' % path)
		return False

def notify(header='', message='', icon=None, time=5000, sound=True):
	icon = xbmcaddon.Addon().getAddonInfo('icon')
	if not xbmc.Player().isPlaying():
		xbmcgui.Dialog().notification(heading=header, message=message, icon=icon, time=time, sound=sound)

def get_kodi_json(method, params):
	json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, params))
	json_query = str(json_query).encode('utf-8')
	return json.loads(json_query)

def pass_dict_to_skin(data=None, prefix='', debug=False, precache=False, window_id=10000):
	if not data:
		return None
	threads = []
	image_requests = []
	
	for (key, value) in data.items():
		if not value:
			continue
		value = str(value)
		if precache:
			if value.startswith('http') and (value.endswith('.jpg') or value.endswith('.png')):
				if value not in image_requests and value:
					thread = GetFileThread(value)
					threads += [thread]
					thread.start()
					image_requests.append(value)
		xbmcgui.Window(window_id).setProperty('%s%s' % (prefix, str(key)), value)
		if debug:
			log('%s%s' % (prefix, str(key)) + value)
	for x in threads:
		x.join()

def merge_dict_lists(items, key='job'):
	crew_id_list = []
	crew_list = []
	for item in items:
		if item['id'] not in crew_id_list:
			crew_id_list.append(item['id'])
			crew_list.append(item)
		else:
			index = crew_id_list.index(item['id'])
			if key in crew_list[index]:
				crew_list[index][key] = '%s / %s' % (crew_list[index][key], item[key])
	return crew_list

def pass_list_to_skin(name='', data=[], prefix='', handle=None, limit=False):
	if data and limit and int(limit) < len(data) and limit not in ("0", 0):
		data = data[:int(limit)]
	if not handle:
		set_window_props(name, data, prefix)
		return None
	xbmcgui.Window(10000).clearProperty(name)
	if data:
		xbmcgui.Window(10000).setProperty('%s.Count' % name, str(len(data)))
		items = create_listitems(data)
		itemlist = [(item.getProperty('path'), item, bool(item.getProperty('directory'))) for item in items]
		xbmcplugin.addDirectoryItems(handle=handle, items=itemlist, totalItems=len(itemlist))
	xbmcplugin.endOfDirectory(handle)

def set_window_props(name, data, prefix='', debug=False):
	if not data:
		xbmcgui.Window(10000).setProperty('%s%s.Count' % (prefix, name), '0')
		log('%s%s.Count = None' % (prefix, name))
		return None
	for (count, result) in enumerate(data):
		if debug:
			log('%s%s.%i = %s' % (prefix, name, count + 1, str(result)))
		for (key, value) in result.items():
			value = str(value)
			xbmcgui.Window(10000).setProperty('%s%s.%i.%s' % (prefix, name, count + 1, str(key)), value)
			if key.lower() in ['poster', 'banner', 'fanart', 'clearart', 'clearlogo', 'landscape', 'discart', 'characterart', 'tvshow.fanart', 'tvshow.poster', 'tvshow.banner', 'tvshow.clearart', 'tvshow.characterart']:
				xbmcgui.Window(10000).setProperty('%s%s.%i.Art(%s)' % (prefix, name, count + 1, str(key)), value)
			if debug:
				log('%s%s.%i.%s --> ' % (prefix, name, count + 1, str(key)) + value)
	xbmcgui.Window(10000).setProperty('%s%s.Count' % (prefix, name), str(len(data)))

def create_listitems(data=None, preload_images=0, enable_clearlogo=True, info=None, history_source='combined'):
	from resources.lib.TheMovieDB import extended_season_info
	from pathlib import Path
	#tools_log('create_listitems',str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))

	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
	#fanart_api = fanart_api_key()
	#tools_log(str(enable_clearlogo))
	#tools_log(str('create_listitems'))
	INT_INFOLABELS = ['year', 'episode', 'season', 'tracknumber', 'playcount', 'overlay', 'percentplayed']
	FLOAT_INFOLABELS = ['rating']
	#STRING_INFOLABELS = ['mediatype', 'genre', 'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle', 'sorttitle', 'duration', 'studio', 'tagline', 'writer', 'tvshowtitle', 'premiered', 'status', 'code', 'aired', 'credits', 'lastplayed', 'album', 'votes', 'trailer', 'dateadded', 'IMDBNumber']
	STRING_INFOLABELS = ['mediatype', 'genre', 'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle', 'sorttitle', 'duration', 'studio', 'tagline', 'writer', 'tvshowtitle', 'premiered', 'status', 'code', 'aired', 'credits', 'lastplayed', 'album', 'votes', 'trailer', 'dateadded']
	if not data:
		return []
	itemlist = []
	threads = []
	image_requests = []

	try: show_id = info['tmdb_id']
	except: show_id = 0
	from resources.lib import accounts
	try: history = accounts.history(scope=history_source)
	except Exception: history = {'movies':{},'shows':{},'episodes':{}}

	for (count, result) in enumerate(data):
		listitem = xbmcgui.ListItem('%s' % str(count))
		#listitem = xbmcgui.ListItem('%s' % str(count), offscreen=True)
		listitem.setProperty("dateadded", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		listitem.setProperty("nocache", "true")

		try: tmdb_id = result['id']
		except: tmdb_id = 0
		try: media_type = result['media_type']
		except: media_type = 0
		try: mediatype = result['mediatype']
		except: mediatype = 0
		

		#if enable_clearlogo and not 'info=library' in str(sys.argv) and not 'script=False' in str(sys.argv):
		if enable_clearlogo:
			if media_type == 'tv' and tmdb_id != 0:
				from resources.lib.TheMovieDB import get_tvshow_ids
				imdb_id = fetch(get_tvshow_ids(tmdb_id), 'imdb_id')
				result['IMDBNumber'] = imdb_id


			elif media_type == 'movie' and tmdb_id != 0:
				from resources.lib.TheMovieDB import get_imdb_id_from_movie_id
				imdb_id = get_imdb_id_from_movie_id(tmdb_id)
				result['IMDBNumber'] = imdb_id

		if mediatype == 'movie':
			listitem.setProperty("tmdb_id", str(result['id']))
		elif mediatype == 'tvshow':
			listitem.setProperty("tmdb_id", str(result['id']))
		elif mediatype == 'episode':
			#tools_log(str(result))
			listitem.setProperty("tmdb_id", str(result.get("tmdb_id") or show_id))

		result=accounts.clean_history_row(dict(result),show_id,history_source)
		try: accounts.mark(result,show_id,listitem,history)
		except Exception: pass
		try: accounts.status_overlay(result,show_id,listitem,history)
		except Exception: pass

		if enable_clearlogo and not 'logo\':' in str(result.items()) and tmdb_id != 0 and (media_type != 0 and (media_type == 'tv' or media_type == 'movie')):
			from resources.lib.TheMovieDB import get_fanart_clearlogo
			try: clearlogo = get_fanart_clearlogo(tmdb_id=tmdb_id,media_type=media_type)
			except: clearlogo = ''
			result['clearlogo'] = clearlogo
			result['logo'] = clearlogo

		#tools_log(result)
		try:
			try: 
				#listitem.setUniqueIDs({ 'imdb': result['imdb_id'], 'tmdb' : result['id'] }, "imdb")
				vinfo = listitem.getVideoInfoTag()
				vinfo.setUniqueID( result['imdb_id'], type='imdb',  isdefault=False)
				vinfo.setIMDBNumber( result['imdb_id'])
			except KeyError: 
				pass
			try: 
				vinfo = listitem.getVideoInfoTag()
				vinfo.setUniqueID( str(result['id']), type='tmdb',  isdefault=True)
			except KeyError: 
				pass
		except AttributeError:
			try:
				try: unique_ids = {"imdb": result['imdb_id'], "tmdb": str(result['id'])}
				except KeyError: unique_ids = { "tmdb": str(result['id'])}
				listitem.setUniqueIDs(unique_ids, "tmdb")
			except KeyError: 
				pass
		for (key, value) in result.items():
			if not value:
				continue
			value = str(value)
			if count < preload_images:
				if value.startswith('http://') and (value.endswith('.jpg') or value.endswith('.png')) or value.startswith('image://') and (value.endswith('.jpg/') or value.endswith('.png/')):
					if value not in image_requests:
						thread = GetFileThread(value)
						threads += [thread]
						thread.start()
						image_requests.append(value)
			if key.lower() in ['name', 'label']:
				listitem.setLabel(value)
			elif key.lower() in ['label2']:
				listitem.setLabel2(value)
			elif key.lower() in ['status']:
				#set_key = value + '(' + str(result['TotalSeasons']) + ')'
				listitem.setLabel2(value)
			elif key.lower() in ['title']:
				listitem.setLabel(value)
				#listitem.setInfo('video', {key.lower(): value})

				try: 
					info_tag = ListItemInfoTag(listitem, 'video')
					info_tag.set_info({key.lower(): value})
				except:
					listitem.setInfo('video', {key.lower(): value})

			elif key.lower() in ['thumb']:
				#listitem.setThumbnailImage(value)
				listitem.setArt({key.lower(): value})
				#if mediatype == 'episode':
				#	listitem.setProperty('Fanart_small', value)
			elif key.lower() in ['icon']:
				listitem.setIconImage(value)
				listitem.setArt({key.lower(): value})
				if mediatype == 'episode':
					listitem.setArt({'thumb': value})
			elif key.lower() in ['clearlogo','logo']:
				listitem.setArt({'clearlogo': value})

			#elif key.lower() in ['imdbnumber','IMDBNumber']:
			#	#listitem.setInfo('video', {'IMDBNumber': str(value)})
			#	try: 
			#		info_tag = ListItemInfoTag(listitem, 'video')
			#		info_tag.set_info({'IMDBNumber': str(value)})
			#	except: 
			#		listitem.setInfo('video', {'IMDBNumber': str(value)})

			elif key.lower() in ['path']:
				listitem.setPath(path=value)
			elif key.lower() in ['poster', 'banner', 'fanart', 'clearart', 'clearlogo', 'landscape', 'discart', 'characterart', 'tvshow.fanart', 'tvshow.poster', 'tvshow.banner', 'tvshow.clearart', 'tvshow.characterart']:
				listitem.setArt({key.lower(): value})
				if mediatype == 'episode':
					listitem.setProperty('Fanart_small', value)
			elif key.lower() in INT_INFOLABELS:
				try:
					
					if key.lower() == 'percentplayed':
						listitem.setProperty('StartPercent', str(value))
					else:
						#listitem.setInfo('video', {key.lower(): int(value)})
						try: 
						#	info_tag = ListItemInfoTag(listitem, 'video')
							info_tag.set_info({key.lower(): int(value)})
						except: 
							listitem.setInfo('video', {key.lower(): int(value)})
				except:
					pass
			elif key.lower() in STRING_INFOLABELS:
				#listitem.setInfo('video', {key.lower(): value})
				try: 
					info_tag = ListItemInfoTag(listitem, 'video')
					if key.lower() in ['genre', 'director', 'studio','writer']:
						info_tag.set_info({key.lower(): value.split(' / ')})
					else:
						try:
							info_tag.set_info({key.lower(): value})
						except:
							if key.lower() == 'duration':
								try: pt = time.strptime(str(value).lower(),'%Hh%Mm%Ss')
								except: 
									try: pt = time.strptime(str(value).lower(),'%Mm%Ss')
									except: 
										try: pt = time.strptime(str(value).lower(),'%Ss')
										except: 
											try: pt = time.strptime(str(value).lower(),'%Mm')
											except: 
												try: pt = time.strptime(str(value).lower(),'%Hh')
												except: 
													try: pt = time.strptime(str(value).lower(),'%Hh%Mm')
													except: pt = time.strptime(str(value).lower(),'%Hh%Ss')
								total_seconds = pt.tm_sec + pt.tm_min*60 + pt.tm_hour*3600
								info_tag.set_info({key.lower(): total_seconds})
							else:
								#info_tag.set_info({key.lower(): value})
								tools_log(str(key.lower()),'===>EXCEPTION!!')
								tools_log(str(value),'===>EXCEPTION!!')
				except:
					listitem.setInfo('video', {key.lower(): value})
			elif key.lower() in FLOAT_INFOLABELS:
				try:
					#listitem.setInfo('video', {key.lower(): '%1.1f' % float(value)})
					try: 
						info_tag = ListItemInfoTag(listitem, 'video')
						info_tag.set_info({key.lower(): '%1.1f' % float(value)})
					except:
						listitem.setInfo('video', {key.lower(): '%1.1f' % float(value)})
				except:
					pass
			listitem.setProperty('%s' % key, value)
		listitem.setProperty('index', str(count))
		itemlist.append(listitem)
	for x in threads:
		x.join()
	return itemlist

def clean_text(text):
	if not text:
		return ''
	text = re.sub('(From Wikipedia, the free encyclopedia)|(Description above from the Wikipedia.*?Wikipedia)', '', text)
	text = re.sub('<(.|\n|\r)*?>', '', text)
	text = text.replace('<br \/>', '\n')
	text = text.replace('<em>', '[I]').replace('</em>', '[/I]')
	text = text.replace('&amp;', '&')
	text = text.replace('&gt;', '>').replace('&lt;', '<')
	text = text.replace('&#39;', "'").replace('&quot;', '"')
	text = re.sub('\n\\.$', '', text)
	text = text.replace('User-contributed text is available under the Creative Commons By-SA License and may also be available under the GNU FDL.', '')
	while text:
		s = text[0]
		e = text[-1]
		if s in ['\u200b', ' ', '\n']:
			text = text[1:]
		elif e in ['\u200b', ' ', '\n']:
			text = text[:-1]
		elif s.startswith('.') and not s.startswith('..'):
			text = text[1:]
		else:
			break
	return text.strip()
