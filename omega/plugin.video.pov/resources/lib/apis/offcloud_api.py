import re
import requests
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
base_url = 'https://offcloud.com/api'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class OffcloudAPI:
	download = 'https://%s.offcloud.com/cloud/download/%s/%s'
	zip = 'https://%s.offcloud.com/cloud/zip/%s/%s.zip'
	remove = 'https://offcloud.com/cloud/remove/%s' # undocumented
	stats = 'account/stats' # undocumented
	history = 'cloud/history' # undocumented
	explore = 'cloud/explore/%s'
	files = 'cloud/list/%s'
	status = 'cloud/status'
	cache = 'cache'
	cloud = 'cloud'

	@staticmethod
	def requote_uri(url):
		return requests.utils.requote_uri(url)

	def __init__(self):
		self.token = get_setting('oc.token')

	def _request(self, method, path, params=None, data=None):
		params = params or {}
		params['key'] = self.token
		url = '%s/%s' % (base_url, path) if not path.startswith('http') else path
		try:
			response = session.request(method, url, params=params, json=data, timeout=timeout)
			result = response.json()
			if not response.ok: response.raise_for_status()
		except requests.exceptions.RequestException as e:
			kodi_utils.logger('offcloud error', str(e))
		return result

	def _get(self, url, params=None):
		return self._request('get', url, params=params)

	def _post(self, url, data=None):
		return self._request('post', url, data=data)

	def build_url(self, server, request_id, file_name):
		return self.download % (server, request_id, file_name)

	def build_zip(self, server, request_id, file_name):
		return self.zip % (server, request_id, file_name)

	def requestid_from_url(self, url):
		match = re.search(r'download/[A-Za-z0-9]+/', url)
		if not match: return None
		request_id = match.group(0).split('/')[-2]
		return request_id

	def account_info(self):
		return self._get(self.stats)

	def torrent_info(self, request_id=''):
		url = self.explore % request_id
		return self._get(url)

	def delete_torrent(self, request_id=''):
		params = {'key': self.token}
		url = self.remove % request_id
		return self._get(url, params=params)

	def check_cache_single(self, hash):
		result = self.check_cache([hash])
		return hash in result

	def check_cache(self, hashlist):
		data = {'hashes': hashlist}
		result = self._post(self.cache, data=data)
		return result['cachedItems']

	def add_magnet(self, magnet):
		data = {'url': magnet}
		return self._post(self.cloud, data=data)

	def create_transfer(self, magnet_url):
		result = self.add_magnet(magnet_url)
		return result.get('requestId', '')

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		from modules.source_utils import supported_video_extensions, seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			if not self.check_cache_single(info_hash): return None
			torrent = self.add_magnet(magnet_url)
			if not torrent['status'] == 'downloaded': return None
			single_file_torrent = '%s/%s' % (torrent['url'], torrent['fileName'])
			torrent_id = torrent['requestId']
			torrent_files = self.torrent_info(torrent_id)
			if not isinstance(torrent_files, list): torrent_files = [single_file_torrent]
			selected_files = []
			for i in torrent_files:
				link, filename, size = i, i.split('/')[-1].lower(), 0
				if filename.endswith('.m2ts'): raise Exception('_m2ts_check failed')
				if not filename.endswith(tuple(extensions)): continue
				if (seas_ep_filter(season, episode, filename)
					if season else
					not any(x in filename for x in extras_filtering_list)
				): selected_files += [i]
			if not selected_files: return None
			file_key = next(iter(selected_files), None)
			file_url = self.requote_uri(file_key) # requote, oc why give us a list of urls that may have spaces in name
			return file_url
		except Exception as e:
			kodi_utils.logger('main exception', str(e))
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent_id = self.create_transfer(magnet_url)
			torrent_files = self.torrent_info(torrent_id)
			torrent_files = [
				{'link': self.requote_uri(item), 'filename': item.split('/')[-1], 'size': 0}
				for item in torrent_files if item.lower().endswith(tuple(extensions))
			]
#			self.delete_torrent(torrent_id) # cannot delete the torrent, play link will not persist, will return 502
			return torrent_files
		except Exception:
			if torrent_id: self.delete_torrent(torrent_id)
			return None

	def user_cloud(self, request_id=None, check_cache=True):
		string = 'pov_oc_user_cloud_info_%s' % request_id if request_id else 'pov_oc_user_cloud'
		url = self.explore % request_id if request_id else self.history
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
			# USER CLOUD
			try:
				dbcur.execute("""SELECT id FROM maincache WHERE id LIKE ?""", ('pov_oc_user_cloud%',))
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
				DebridCache().clear_debrid_results('oc')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, hash_cache_status_success): return False
		return True

