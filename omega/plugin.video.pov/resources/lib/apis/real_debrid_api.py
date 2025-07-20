import requests
from threading import Thread
from caches.main_cache import cache_object
from modules import kodi_utils
# logger = kodi_utils.logger

ls, get_setting, set_setting = kodi_utils.local_string, kodi_utils.get_setting, kodi_utils.set_setting
base_url = 'https://app.real-debrid.com/rest/1.0/'
auth_url = 'https://app.real-debrid.com/oauth/v2/'
timeout = 28.0
session = requests.Session()
session.mount('https://app.real-debrid.com', requests.adapters.HTTPAdapter(max_retries=1))

class RealDebridAPI:
	def __init__(self):
		self.token = get_setting('rd.token')

	def _get(self, url):
		original_url = url
		url = base_url + url
		if self.token == '': return None
#		if '?' not in url: url += '?auth_token=%s' % self.token
#		else: url += '&auth_token=%s' % self.token
		session.headers['Authorization'] = f"Bearer {self.token}"
		response = session.get(url, timeout=timeout)
		if any(value in response.text for value in ('bad_token', 'Bad Request')):
			if self.refresh_token(): response = self._get(original_url)
			else: return None
		try: return response.json()
		except: return response

	def _post(self, url, post_data):
		original_url = url
		url = base_url + url
		if self.token == '': return None
#		if '?' not in url: url += '?auth_token=%s' % self.token
#		else: url += '&auth_token=%s' % self.token
		session.headers['Authorization'] = f"Bearer {self.token}"
		response = session.post(url, data=post_data, timeout=timeout)
		if any(value in response.text for value in ('bad_token', 'Bad Request')):
			if self.refresh_token(): response = self._post(original_url, post_data)
			else: return None
		try: return response.json()
		except: return response

	def refresh_token(self):
		try:
			client_id, secret, refresh = get_setting('rd.client_id'), get_setting('rd.secret'), get_setting('rd.refresh')
			data = {'client_id': client_id, 'client_secret': secret, 'code': refresh, 'grant_type': 'http://oauth.net/grant_type/device/1.0'}
			url = auth_url + 'token'
			response = session.post(url, data=data).json()
			self.token, refresh = response['access_token'], response['refresh_token']
			set_setting('rd.token', self.token)
			set_setting('rd.refresh', refresh)
		except: return False
		else: return True

	def torrents_activeCount(self):
		url = 'torrents/activeCount'
		return self._get(url)

	def days_remaining(self):
#		import datetime, time
		try:
			account_info = self.account_info()
#			FormatDateTime = "%Y-%m-%dT%H:%M:%S.%fZ"
#			try: expires = datetime.datetime.strptime(account_info['expiration'], FormatDateTime)
#			except: expires = datetime.datetime(*(time.strptime(account_info['expiration'], FormatDateTime)[0:6]))
#			days_remaining = (expires - datetime.datetime.today()).days
			days_remaining = int(account_info['premium']/86400)
		except: days_remaining = None
		return days_remaining

	def account_info(self):
		url = 'user'
		return self._get(url)

	def check_single_magnet(self, hash_string):
		cache_info = self.check_hash(hash_string)
		cached = False
		if hash_string in cache_info:
			info = cache_info[hash_string]
			if isinstance(info, dict) and len(info.get('rd')) > 0:
				cached = True
		return cached

	def check_hash(self, hash_string):
		url = 'torrents/instantAvailability/%s' % hash_string
		return self._get(url)

	def check_cache(self, hashes):
		hash_string = '/'.join(hashes)
		url = 'torrents/instantAvailability/%s' % hash_string
		return self._get(url)

	def torrent_info(self, file_id):
		url = 'torrents/info/%s' % file_id
		return self._get(url)

	def delete_torrent(self, folder_id):
		if self.token == '': return None
		url = 'torrents/delete/%s&auth_token=%s' % (folder_id, self.token)
		response = session.delete(base_url + url, timeout=timeout)
		return response

	def delete_download(self, download_id):
		if self.token == '': return None
		url = 'downloads/delete/%s&auth_token=%s' % (download_id, self.token)
		response = session.delete(base_url + url, timeout=timeout)
		return response

	def unrestrict_link(self, link):
		url = 'unrestrict/link'
		post_data = {'link': link}
		response = self._post(url, post_data)
		try: return response['download']
		except: return None

	def add_torrent_select(self, torrent_id, file_ids):
		self.clear_cache()
		url = 'torrents/selectFiles/%s' % torrent_id
		post_data = {'files': file_ids}
		return self._post(url, post_data)

	def add_magnet(self, magnet):
		post_data = {'magnet': magnet}
		url = 'torrents/addMagnet'
		return self._post(url, post_data)

	def create_transfer(self, magnet_url):
		from modules.source_utils import supported_video_extensions
		try:
			extensions = supported_video_extensions()
			torrent = self.add_magnet(magnet_url)
			torrent_id = torrent['id']
#			info = self.torrent_info(torrent_id)
#			files = info['files']
#			torrent_keys = [str(item['id']) for item in files if item['path'].lower().endswith(tuple(extensions))]
#			torrent_keys = ','.join(torrent_keys)
#			self.add_torrent_select(torrent_id, torrent_keys)
			self.add_torrent_select(torrent_id, 'all')
			return torrent_id
		except:
			self.delete_torrent(torrent_id)
			return ''

	def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
		from modules.source_utils import supported_video_extensions, seas_ep_filter, extras_filter
		try:
			extensions = supported_video_extensions()
			extras_filtering_list = tuple(i for i in extras_filter() if not i in title.lower())
			torrent_id = self.create_transfer(magnet_url)
			for key in ['ended'] * 3:
				kodi_utils.sleep(500)
				torrent_info = self.torrent_info(torrent_id)
				if key in torrent_info: break
			else: raise Exception('uncached magnet:\n%s' % magnet_url)
			torrent_files = (i for i in torrent_info['files'] if i['selected'])
			selected_files = []
			for i, link in zip(torrent_files, torrent_info['links']):
				link, filename, size = link, i['path'].lower().replace('/', ''), i['bytes']
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
			transfer_id = self.create_transfer(magnet_url)
			for key in ['ended'] * 3:
				kodi_utils.sleep(500)
				torrent_info = self.torrent_info(transfer_id)
				if key in torrent_info: break
			else: raise Exception('uncached magnet:\n%s' % magnet_url)
			torrent_files = (i for i in torrent_info['files'] if i['selected'])
			torrent_files = [
				{'link': link, 'filename': item['path'].replace('/', ''), 'size': item['bytes']}
				for item, link in zip(torrent_files, torrent_info['links'])
			]
			self.delete_torrent(transfer_id)
			return torrent_files
		except Exception:
			if transfer_id: self.delete_torrent(transfer_id)
			return None

	def get_hosts(self):
		string = 'pov_rd_valid_hosts'
		url = 'hosts/domains'
		hosts_dict = {'Real-Debrid': []}
		try:
			result = cache_object(self._get, string, url, False, 48)
			hosts_dict['Real-Debrid'] = result
		except: pass
		return hosts_dict

	def downloads(self):
		string = 'pov_rd_downloads'
		url = 'downloads'
		return cache_object(self._get, string, url, False, 0.5)

	def user_cloud(self):
		string = 'pov_rd_user_cloud'
		url = 'torrents'
		return cache_object(self._get, string, url, False, 0.5)

	def user_cloud_info(self, file_id):
		string = 'pov_rd_user_cloud_info_%s' % file_id
		url = 'torrents/info/%s' % file_id
		return cache_object(self._get, string, url, False, 2)

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
				dbcur.execute("""SELECT id FROM maincache WHERE id LIKE ?""", ('pov_rd_user_cloud%',))
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
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_rd_downloads',))
				clear_property('pov_rd_downloads')
				dbcon.commit()
				download_links_success = True
			except: download_links_success = False
			# HOSTERS
			try:
				dbcur.execute("""DELETE FROM maincache WHERE id = ?""", ('pov_rd_valid_hosts',))
				clear_property('pov_rd_valid_hosts')
				dbcon.commit()
				dbcon.close()
				hoster_links_success = True
			except: hoster_links_success = False
			# HASH CACHED STATUS
			try:
				DebridCache().clear_debrid_results('rd')
				hash_cache_status_success = True
			except: hash_cache_status_success = False
		except: return False
		if False in (user_cloud_success, download_links_success, hoster_links_success, hash_cache_status_success): return False
		return True

