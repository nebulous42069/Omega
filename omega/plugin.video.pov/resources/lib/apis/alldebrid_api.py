import requests
from threading import Thread
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
base_url = 'https://api.alldebrid.com/v4/'
user_agent = 'pov_for_kodi'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class AllDebridAPI:
	def __init__(self):
		self.token = get_setting('ad.token')

	def _get(self, url, url_append=''):
		result = None
		try:
			if self.token == '': return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token) + url_append
			result = session.get(url, timeout=timeout).json()
			if result.get('status') == 'success' and 'data' in result: result = result['data']
		except: pass
		return result

	def _post(self, url, data={}):
		result = None
		try:
			if self.token == '': return None
			url = base_url + url + '?agent=%s&apikey=%s' % (user_agent, self.token)
			result = session.post(url, data=data, timeout=timeout).json()
			if result.get('status') == 'success' and 'data' in result: result = result['data']
		except: pass
		return result

	def days_remaining(self):
		import datetime
		try:
			account_info = self.account_info()['user']
			expires = datetime.datetime.fromtimestamp(account_info['premiumUntil'])
			days_remaining = (expires - datetime.datetime.today()).days
		except: days_remaining = None
		return days_remaining

	def account_info(self):
		response = self._get('user')
		return response

	def list_transfer(self, transfer_id):
		url = 'magnet/status'
		url_append = '&id=%s' % transfer_id
		result = self._get(url, url_append)
		result = result['magnets']
		return result

	def delete_transfer(self, transfer_id):
		url = 'magnet/delete'
		url_append = '&id=%s' % transfer_id
		result = self._get(url, url_append)
		if result.get('success', False):
			return True

	def unrestrict_link(self, link):
		url = 'link/unlock'
		url_append = '&link=%s' % link
		response = self._get(url, url_append)
		try: return response['link']
		except: return None

	def check_single_magnet(self, hash_string):
		cache_info = self.check_cache(hash_string)['magnets'][0]
		return cache_info['instant']

	def check_cache(self, hashes):
		data = {'magnets[]': hashes}
		response = self._post('magnet/instant', data)
		return response

	def create_transfer(self, magnet):
		url = 'magnet/upload'
		url_append = '&magnet=%s' % magnet
		result = self._get(url, url_append)
		result = result['magnets'][0]
		return result.get('id', '')

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		from modules.source_utils import supported_video_extensions, seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			transfer_id = self.create_transfer(magnet_url)
			for key in ['completionDate'] * 3:
				kodi_utils.sleep(500)
				transfer_info = self.list_transfer(transfer_id)
				if transfer_info[key]: break
			else: raise Exception('uncached magnet:\n%s' % magnet_url)
			torrent_files = transfer_info['links']
			selected_files = [i for i in torrent_files if i['filename'].lower().endswith(tuple(extensions))]
			if not selected_files: return None
			if season:
				selected_files = [i for i in selected_files if seas_ep_filter(season, episode, i['filename'])]
			else:
				selected_files = [i for i in selected_files if not any(x in i['filename'].lower() for x in extras_filtering_list)]
				selected_files.sort(key=lambda k: k['size'], reverse=True)
			if not selected_files: return None
			file_key = selected_files[0]['link']
			file_url = self.unrestrict_link(file_key)
			if not store_to_cloud: Thread(target=self.delete_transfer, args=(transfer_id,)).start()
			return file_url
		except Exception as e:
			kodi_utils.logger('main exception', str(e))
			if transfer_id: Thread(target=self.delete_transfer, args=(transfer_id,)).start()
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			transfer_id = self.create_transfer(magnet_url)
			for key in ['completionDate'] * 3:
				kodi_utils.sleep(500)
				transfer_info = self.list_transfer(transfer_id)
				if transfer_info[key]: break
			else: raise Exception('uncached magnet:\n%s' % magnet_url)
			torrent_files = [
				{'link': item['link'], 'filename': item['filename'], 'size': item['size']}
				for item in transfer_info['links'] if item['filename'].lower().endswith(tuple(extensions))
			]
			self.delete_transfer(transfer_id)
			return torrent_files
		except Exception:
			if transfer_id: self.delete_transfer(transfer_id)
			return None

	def get_hosts(self):
		string = 'pov_ad_valid_hosts'
		url = 'hosts'
		hosts_dict = {'AllDebrid': []}
		hosts = []
		try:
			result = cache_object(self._get, string, url, False, 168)
			result = result['hosts']
			for k, v in result.items():
				try: hosts.extend(v['domains'])
				except: pass
			hosts = list(set(hosts))
			hosts_dict['AllDebrid'] = hosts
		except: pass
		return hosts_dict

	def user_cloud(self):
		url = 'magnet/status'
		string = 'pov_ad_user_cloud'
		return cache_object(self._get, string, url, False, 0.5)

	def clear_cache(self):
		try:
			if not kodi_utils.path_exists(kodi_utils.maincache_db): return True
			from caches.debrid_cache import DebridCache
			dbcon = kodi_utils.database.connect(kodi_utils.maincache_db)
			dbcur = dbcon.cursor()
			# USER CLOUD
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_ad_user_cloud',))
				kodi_utils.clear_property('pov_ad_user_cloud')
				dbcon.commit()
				user_cloud_success = True
			except: user_cloud_success = False
			# HOSTERS
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_ad_valid_hosts',))
				kodi_utils.clear_property('pov_ad_valid_hosts')
				dbcon.commit()
				dbcon.close()
				hoster_links_success = True
			except: hoster_links_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('ad')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, hoster_links_success, hash_cache_status_success): return False
		return True

