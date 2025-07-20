import requests
from threading import Thread
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
base_url = 'https://api.torbox.app/v1/api'
user_agent = 'POV for Kodi'
timeout = 28.0
session = requests.Session()
session.headers['User-Agent'] = user_agent
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class TorBoxAPI:
	download = 'torrents/requestdl'
	download_usenet = 'usenet/requestdl'
	download_webdl = 'webdl/requestdl'
	remove = 'torrents/controltorrent'
	remove_usenet = 'usenet/controlusenetdownload'
	remove_webdl = 'webdl/controlwebdownload'
	stats = 'user/me'
	history = 'torrents/mylist'
	history_usenet = 'usenet/mylist'
	history_webdl = 'webdl/mylist'
	explore = 'torrents/mylist?id=%s'
	explore_usenet = 'usenet/mylist?id=%s'
	explore_webdl = 'webdl/mylist?id=%s'
	cache = 'torrents/checkcached'
	cloud = 'torrents/createtorrent'
	cloud_usenet = 'usenet/createusenetdownload'

	def __init__(self):
		self.token = get_setting('tb.token')

	def _request(self, method, path, params=None, json=None, data=None):
		session.headers['Authorization'] = 'Bearer %s' % self.token
		url = '%s/%s' % (base_url, path) if not path.startswith('http') else path
		try:
			response = session.request(method, url, params=params, json=json, data=data, timeout=timeout)
			result = response.json()
			if not response.ok: response.raise_for_status()
		except requests.exceptions.RequestException as e:
			kodi_utils.logger('torbox error', str(e))
		return result

	def _process(self, result, path):
		if   'control' in path: result = result.get('success')
		elif 'success' in result and 'data' in result: result = result['data']
		return result

	def _get(self, url, params=None):
		result = self._request('get', url, params=params)
		return self._process(result, url)

	def _post(self, url, params=None, json=None, data=None):
		result = self._request('post', url, params=params, json=json, data=data)
		return self._process(result, url)

	def add_headers_to_url(self, url):
		return url + '|' + kodi_utils.urlencode(self.headers())

	def headers(self):
		return {'User-Agent': user_agent}

	def days_remaining(self):
		import datetime, time
		try:
			account_info = self.account_info()
			FormatDateTime = '%Y-%m-%dT%H:%M:%SZ'
			try: expires = datetime.datetime.strptime(account_info['premium_expires_at'], FormatDateTime)
			except: expires = datetime.datetime(*(time.strptime(account_info['premium_expires_at'], FormatDateTime)[0:6]))
			days_remaining = (expires - datetime.datetime.today()).days
		except: days_remaining = None
		return days_remaining

	def account_info(self):
		return self._get(self.stats)

	def torrent_info(self, request_id=''):
		url = self.explore % request_id
		return self._get(url)

	def delete_torrent(self, request_id=''):
		data = {'torrent_id': request_id, 'operation': 'delete'}
		return self._post(self.remove, json=data)

	def delete_usenet(self, request_id=''):
		data = {'usenet_id': request_id, 'operation': 'delete'}
		return self._post(self.remove_usenet, json=data)

	def delete_webdl(self, request_id=''):
		data = {'webdl_id': request_id, 'operation': 'delete'}
		return self._post(self.remove_webdl, json=data)

	def unrestrict_link(self, file_id):
		torrent_id, file_id = file_id.split(',')
		params = {'token': self.token, 'torrent_id': torrent_id, 'file_id': file_id}
		return self._get(self.download, params=params)

	def unrestrict_usenet(self, file_id):
		usenet_id, file_id = file_id.split(',')
		params = {'token': self.token, 'usenet_id': usenet_id, 'file_id': file_id}
		return self._get(self.download_usenet, params=params)

	def unrestrict_webdl(self, file_id):
		webdl_id, file_id = file_id.split(',')
		params = {'token': self.token, 'web_id': webdl_id, 'file_id': file_id}
		return self._get(self.download_webdl, params=params)

	def check_cache_single(self, hash):
		result = self._get(self.cache, params={'hash': hash, 'format': 'list'})
		return hash in [i['hash'] for i in result]

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		result = self._post(self.cache, params={'format': 'list'}, json=data)
		return [i['hash'] for i in result]

	def add_nzb(self, nzb, name=''):
		data = {'link': nzb}
		if name: data['name'] = name
		return self._post(self.cloud_usenet, data=data)

	def add_magnet(self, magnet):
		data = {'magnet': magnet, 'seed': 3, 'allow_zip': 'false'}
		return self._post(self.cloud, data=data)

	def create_transfer(self, link, name=''):
		if link.startswith('magnet'): key, result = 'torrent_id', self.add_magnet(link)
		else: key, result = 'usenetdownload_id', self.add_nzb(link, name)
		return result.get(key, '')

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		from modules.source_utils import supported_video_extensions, seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			if not self.check_cache_single(info_hash): return None
			torrent_id = self.create_transfer(magnet_url)
			torrent_files = self.torrent_info(torrent_id)
			selected_files = []
			for i in torrent_files['files']:
				link, filename, size = '%d,%d' % (torrent_id, i['id']), i['short_name'].lower(), i['size']
				if filename.endswith('.m2ts'): raise Exception('_m2ts_check failed')
				if not filename.endswith(tuple(extensions)): continue
				if (seas_ep_filter(season, episode, filename)
					if season else
					not any(x in filename for x in extras_filtering_list)
				): selected_files += [{'link': link, 'size': size}]
			if not selected_files: return None
			if not season: selected_files.sort(key=lambda k: k['size'], reverse=True)
			file_key = next((i['link'] for i in selected_files), None)
			file_url = self.unrestrict_link(file_key)
			if not store_to_cloud: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
			return file_url
		except Exception as e:
			kodi_utils.logger('main exception', str(e))
			if torrent_id: Thread(target=self.delete_torrent, args=(torrent_id,)).start()
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent_id = self.create_transfer(magnet_url)
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [
				{'link': '%d,%d' % (torrent_id, item['id']), 'filename': item['short_name'], 'size': item['size']}
				for item in torrent_files['files'] if item['short_name'].lower().endswith(tuple(extensions))
			]
			self.delete_torrent(torrent_id)
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def usenet_search(self, query, season='', episode='', imdb=''):
		sort = int(get_setting('tb.sort', '0'))
		if imdb: query = 'imdb:%s' % imdb
		else: query = 'search/%s' % requests.utils.quote(query)
		url = 'https://search-api.torbox.app/usenet/%s' % query
		params = {'check_cache': 'true', 'check_owned': 'true', 'search_user_engines': 'true'}
		if season and episode: params.update({'season': int(season), 'episode': int(episode)})
		result = self._get(url, params=params)
		try: result = result['nzbs']
		except: result = []
		if   sort == 1: result.sort(key=lambda k: int(k['size']), reverse=True)
		elif sort == 2: result.sort(key=lambda k: k['tracker'], reverse=False)
		else: result.sort(key=lambda k: int(k['age'].rstrip('d')), reverse=False)
		return result

	def user_cloud(self, request_id=None, check_cache=True):
		string = 'pov_tb_user_cloud_info_%s' % request_id if request_id else 'pov_tb_user_cloud'
		url = self.explore % request_id if request_id else self.history
		if check_cache: result = cache_object(self._get, string, url, False, 0.5)
		else: result = self._get(url)
		return result

	def user_cloud_usenet(self, request_id=None, check_cache=True):
		string = 'pov_tb_user_cloud_usenet_info_%s' % request_id if request_id else 'pov_tb_user_cloud_usenet'
		url = self.explore_usenet % request_id if request_id else self.history_usenet
		if check_cache: result = cache_object(self._get, string, url, False, 0.5)
		else: result = self._get(url)
		return result

	def user_cloud_webdl(self, request_id=None, check_cache=True):
		string = 'pov_tb_user_cloud_webdl_info_%s' % request_id if request_id else 'pov_tb_user_cloud_webdl'
		url = self.explore_webdl % request_id if request_id else self.history_webdl
		if check_cache: result = cache_object(self._get, string, url, False, 0.5)
		else: result = self._get(url)
		return result

	def clear_cache(*args):
		try:
			if not kodi_utils.path_exists(kodi_utils.maincache_db): return True
			from caches.debrid_cache import DebridCache
			user_cloud_success = False
			dbcon = kodi_utils.database.connect(kodi_utils.maincache_db)
			dbcur = dbcon.cursor()
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('torbox_usenet_queries',))
				kodi_utils.clear_property(str(i))
			except: pass
			# USER CLOUD
			try:
				dbcur.execute("""SELECT id FROM maincache WHERE id LIKE ?""", ('pov_tb_user_cloud%',))
				try:
					user_cloud_cache = dbcur.fetchall()
					user_cloud_cache = [i[0] for i in user_cloud_cache]
				except:
					user_cloud_success = True
				if not user_cloud_success:
					for i in user_cloud_cache:
						dbcur.execute("""DELETE FROM maincache WHERE id = ?""", (i,))
						kodi_utils.clear_property(str(i))
					dbcon.commit()
					user_cloud_success = True
			except: user_cloud_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('tb')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True

