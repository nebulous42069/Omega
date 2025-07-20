import requests
from threading import Thread
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting = kodi_utils.local_string, kodi_utils.get_setting
client_id = '663882072'
user_agent = 'POV for Kodi'
base_url = 'https://www.premiumize.me/api/'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))

class PremiumizeAPI:
	def __init__(self):
		self.token = get_setting('pm.token')

	def _get(self, url, data={}):
		if self.token == '': return None
		headers = {'User-Agent': user_agent, 'Authorization': 'Bearer %s' % self.token}
		url = base_url + url
		response = session.get(url, data=data, headers=headers, timeout=timeout)
		try: return response.json()
		except: return response.text

	def _post(self, url, data={}):
		if self.token == '' and not 'token' in url: return None
		headers = {'User-Agent': user_agent, 'Authorization': 'Bearer %s' % self.token}
		if not 'token' in url: url = base_url + url
		response = session.post(url, data=data, headers=headers, timeout=timeout)
		try: return response.json()
		except: return response.text

	def add_headers_to_url(self, url):
		return url + '|' + kodi_utils.urlencode(self.headers())

	def headers(self):
		return {'User-Agent': user_agent, 'Authorization': 'Bearer %s' % self.token}

	def days_remaining(self):
		import datetime
		try:
			account_info = self.account_info()
			expires = datetime.datetime.fromtimestamp(account_info['premium_until'])
			days_remaining = (expires - datetime.datetime.today()).days
		except: days_remaining = None
		return days_remaining

	def account_info(self):
		url = 'account/info'
		response = self._get(url)
		return response

	def transfers_list(self):
		url = 'transfer/list'
		return self._get(url)

	def delete_transfer(self, transfer_id):
		data = {'id': transfer_id}
		url = 'transfer/delete'
		return self._post(url, data)

	def unrestrict_link(self, link):
		data = {'src': link}
		url = 'transfer/directdl'
		response = self._post(url, data)
		try: return self.add_headers_to_url(response['content'][0]['link'])
		except: return None

	def check_single_magnet(self, hash_string):
		cache_info = self.check_cache([hash_string])
		return hash_string in cache_info

	def check_cache(self, hashes):
		url = 'cache/check'
		data = {'items[]': hashes}
		response = self._post(url, data)
		return [h for h, cached in zip(hashes, response['response']) if cached]

	def instant_transfer(self, magnet_url):
		url = 'transfer/directdl'
		data = {'src': magnet_url}
		return self._post(url, data)

	def create_transfer(self, magnet):
		data = {'src': magnet, 'folder_id': 0}
		url = 'transfer/create'
		response = self._post(url, data)
		return response.get('id', '')

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		from modules.source_utils import supported_video_extensions, seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			torrent = self.instant_transfer(magnet_url)
			if not 'status' in torrent and not torrent['status'] == 'success': return None
			torrent_files = torrent['content']
			selected_files = []
			for i in torrent_files:
				link, filename, size = i['link'], i['path'].split('/')[-1], i['size']
				if filename.endswith('.m2ts'): raise Exception('_m2ts_check failed')
				if not filename.endswith(tuple(extensions)): continue
				if (seas_ep_filter(season, episode, filename)
					if season else
					not any(x in filename for x in extras_filtering_list)
				): selected_files += [i]
			if not selected_files: return None
			if not season: selected_files.sort(key=lambda k: k['size'], reverse=True)
			file_key = next((i['link'] for i in selected_files), None)
			file_url = self.add_headers_to_url(file_key)
			if store_to_cloud: Thread(target=self.create_transfer, args=(magnet_url,)).start()
			return file_url
		except Exception as e:
			kodi_utils.logger('main exception', str(e))
			return None

	def display_magnet_pack(self, magnet_url, info_hash):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent = self.instant_transfer(magnet_url)
			if not 'status' in torrent and not torrent['status'] == 'success': return None
			torrent_files = [
				{'link': item['link'], 'filename': item['path'].split('/')[-1], 'size': item['size']}
				for item in torrent['content'] if item['path'].lower().endswith(tuple(extensions))
			]
			return torrent_files
		except Exception:
			return None

	def zip_folder(self, folder_id):
		url = 'zip/generate'
		data = {'folders[]': folder_id}
		response = self._post(url, data)
		return response

	def download_link_magnet_zip(self, magnet_url, info_hash):
		try:
#			result = self.create_transfer(magnet_url)
#			if not 'status' in result or result['status'] != 'success': return None
#			transfer_id = result['id']
			transfer_id = self.create_transfer(magnet_url)
			if not transfer_id: return None
			transfers = self.transfers_list()['transfers']
			folder_id = [i['folder_id'] for i in transfers if i['id'] == transfer_id][0]
			result = self.zip_folder(folder_id)
			if result['status'] == 'success':
				return result['location']
			else: return None
		except:
			pass

	def rename_cache_item(self, file_type, file_id, new_name):
		if file_type == 'folder': url = 'folder/rename'
		else: url = 'item/rename'
		data = {'id': file_id , 'name': new_name}
		response = self._post(url, data)
		return response['status']

	def delete_object(self, object_type, object_id):
		data = {'id': object_id}
		url = '%s/delete' % object_type
		response = self._post(url, data)
		return response['status']

	def get_item_details(self, item_id):
		string = 'pov_pm_item_details_%s' % item_id
		url = 'item/details'
		data = {'id': item_id}
		args = [url, data]
		return cache_object(self._post, string, args, False, 24)

	def get_hosts(self):
		string = 'pov_pm_valid_hosts'
		url = 'services/list'
		hosts_dict = {'Premiumize.me': []}
		hosts = []
		append = hosts.append
		try:
			result = cache_object(self._get, string, url, False, 168)
			for x in result['directdl']:
				for alias in result['aliases'][x]: append(alias)
			hosts_dict['Premiumize.me'] = list(set(hosts))
		except: pass
		return hosts_dict

	def user_cloud(self, folder_id=None):
		if folder_id:
			string = 'pov_pm_user_cloud_%s' % folder_id
			url = 'folder/list?id=%s' % folder_id
		else:
			string = 'pov_pm_user_cloud_root'
			url = 'folder/list'
		return cache_object(self._get, string, url, False, 0.5)

	def user_cloud_all(self):
		string = 'pov_pm_user_cloud_all_files'
		url = 'item/listall'
		return cache_object(self._get, string, url, False, 0.5)

	def clear_cache(*args):
		try:
			from modules.kodi_utils import clear_property, path_exists, database, maincache_db
			if not path_exists(maincache_db): return True
			from caches.debrid_cache import DebridCache
			user_cloud_success = False
			dbcon = database.connect(maincache_db)
			dbcur = dbcon.cursor()
			# USER CLOUD
			try:
				dbcur.execute("""SELECT id FROM maincache WHERE id LIKE ?""", ('pov_pm_user_cloud%',))
				try:
					user_cloud_cache = dbcur.fetchall()
					user_cloud_cache = [i[0] for i in user_cloud_cache]
				except:
					user_cloud_success = True
				if not user_cloud_success:
					for i in user_cloud_cache:
						dbcur.execute("""DELETE FROM maincache WHERE id = ?""", (i,))
						clear_property(str(i))
					dbcon.commit()
					user_cloud_success = True
			except: user_cloud_success = False
			# DOWNLOAD LINKS
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_pm_transfers_list',))
				clear_property('pov_pm_transfers_list')
				dbcon.commit()
				download_links_success = True
			except: download_links_success = False
			# HOSTERS
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_pm_valid_hosts',))
				clear_property('pov_pm_valid_hosts')
				dbcon.commit()
				dbcon.close()
				hoster_links_success = True
			except: hoster_links_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('pm')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, download_links_success, hoster_links_success, hash_cache_status_success): return False
		return True

