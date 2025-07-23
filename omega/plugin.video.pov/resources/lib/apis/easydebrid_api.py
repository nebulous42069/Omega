import requests
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
ip_url = 'https://api.ipify.org'
base_url = 'https://easydebrid.com/api/v1'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class EasyDebridAPI:
	download = 'link/generate'
	stats = 'user/details'
	cache = 'link/lookup'
	cloud = 'link/request'

	def __init__(self):
		self.token = get_setting('ed.token')

	def _request(self, method, path, params=None, json=None, data=None):
		session.headers['Authorization'] = 'Bearer %s' % self.token
		url = '%s/%s' % (base_url, path)
		try:
			response = session.request(method, url, params=params, json=json, data=data, timeout=timeout)
			result = response.json() if 'json' in response.headers.get('Content-Type', '') else response.text
			if not response.ok: response.raise_for_status()
		except requests.exceptions.RequestException as e:
			kodi_utils.logger('easydebrid error', str(e))
		return result

	def _get(self, url, params=None):
		return self._request('get', url, params=params)

	def _post(self, url, params=None, json=None, data=None):
		return self._request('post', url, params=params, json=json, data=data)

	def days_remaining(self):
		from datetime import datetime
		try:
			account_info = self.account_info()
			expires = datetime.fromtimestamp(account_info['paid_until'])
			days_remaining = (expires - datetime.today()).days
		except: days_remaining = None
		return days_remaining

	def account_info(self):
		return self._get(self.stats)

	def check_cache_single(self, hash_string):
		cached_info = self.check_cache([hash_string])
		return hash_string in cached_info

	def check_cache(self, hashlist):
		data = {'urls': hashlist}
		result = self._post(self.cache, json=data)
		return [h for h, cached in zip(hashlist, result['cached']) if cached]

	def instant_transfer(self, magnet_url):
		try: user_ip = requests.get(ip_url, timeout=2.0).text
		except: user_ip = ''
		if user_ip: session.headers['X-Forwarded-For'] = user_ip
		data = {'url': magnet_url}
		return self._post(self.download, json=data)

	def create_transfer(self, magnet):
		data = {'url': magnet}
		result = self._post(self.cloud, json=data)
		return result.get('success', '')

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		from modules.source_utils import supported_video_extensions, seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			if not self.check_cache_single(info_hash): return None
			torrent = self.instant_transfer(magnet_url)
			torrent_files = torrent['files']
			selected_files = []
			for i in torrent_files:
				link, filename, size = i['url'], i['filename'].lower(), i['size']
				if filename.endswith('.m2ts'): raise Exception('_m2ts_check failed')
				if not filename.endswith(tuple(extensions)): continue
				if (seas_ep_filter(season, episode, filename)
					if season else
					not any(x in filename for x in extras_filtering_list)
				): selected_files += [i]
			if not selected_files: return None
			if not season: selected_files.sort(key=lambda k: k['size'], reverse=True)
			file_url = next((i['url'] for i in selected_files), None)
			return file_url
		except Exception as e:
			kodi_utils.logger('main exception', str(e))
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent = self.instant_transfer(magnet_url)
			torrent_files = torrent['files']
			torrent_files = [
				{'link': item['url'], 'filename': item['filename'], 'size': item['size']}
				for item in torrent_files if item['filename'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			return None

	def clear_cache(*args):
		try:
			if not kodi_utils.path_exists(kodi_utils.maincache_db): return True
			from caches.debrid_cache import DebridCache
			dbcon = kodi_utils.database.connect(kodi_utils.maincache_db)
			dbcur = dbcon.cursor()
			# USER CLOUD
			try:
#				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_ed_user_cloud',))
				kodi_utils.clear_property('pov_ed_user_cloud')
#				dbcon.commit()
				user_cloud_success = True
			except: user_cloud_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('ed')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True

