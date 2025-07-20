from threading import Thread
from apis import real_debrid_api, premiumize_api, alldebrid_api, offcloud_api, torbox_api, easydebrid_api
from caches.debrid_cache import DebridCache
from modules.utils import make_thread_list
from modules.settings import enabled_debrids_check, store_resolved_torrent_to_cloud
from modules import kodi_utils
# from modules.kodi_utils import logger

ls, get_setting, ok_dialog = kodi_utils.local_string, kodi_utils.get_setting, kodi_utils.ok_dialog
show_busy_dialog, hide_busy_dialog, notification = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.notification
plswait_str, checking_debrid_str, remaining_debrid_str = ls(32577), ls(32578), ls(32579)
main_line = '%s[CR]%s[CR]%s'

debrid_list = (
	('Real-Debrid', 'rd', 'realdebrid.png', real_debrid_api.RealDebridAPI),
	('Premiumize.me', 'pm', 'premiumize.png', premiumize_api.PremiumizeAPI),
	('AllDebrid', 'ad', 'alldebrid.png', alldebrid_api.AllDebridAPI),
	('EasyDebrid', 'ed', 'easydebrid.png', easydebrid_api.EasyDebridAPI),
	('TorBox', 'tb', 'torbox.png', torbox_api.TorBoxAPI),
	('Offcloud', 'oc', 'offcloud.png', offcloud_api.OffcloudAPI)
)

def import_debrid(debrid_provider):
	return next((i[3] for i in debrid_list if i[0] == debrid_provider), None)

def debrid_enabled():
	return [i[0] for i in debrid_list if enabled_debrids_check(i[1])]

def debrid_type_enabled(debrid_type, enabled_debrids):
	return [i[0] for i in debrid_list if i[0] in enabled_debrids and get_setting('%s.%s.enabled' % (i[1], debrid_type)) == 'true']

def debrid_valid_hosts(enabled_debrids):
	def _get_hosts(function):
		debrid_hosts_append(function().get_hosts())
	if not enabled_debrids: return []
	debrid_hosts = []
	debrid_hosts_append = debrid_hosts.append
	threads = list(make_thread_list(_get_hosts, [import_debrid(i[0]) for i in debrid_list if i[0] in enabled_debrids], Thread))
	[i.join() for i in threads]
	return debrid_hosts

def manual_add_magnet_to_cloud(params):
	show_busy_dialog()
	function = import_debrid(params['provider'])
	result = function().create_transfer(params['magnet_url'])
	function().clear_cache()
	hide_busy_dialog()
	if result: notification(32576)
	else: notification(32575)

def manual_add_nzb_to_cloud(params):
	show_busy_dialog()
	function = import_debrid(params['provider'])
	result = function().create_transfer(params['url'], params['name'])
	function().clear_cache()
	hide_busy_dialog()
	text = '%s...[CR][CR]%s' % (params['name'][:40], ls(32576) if result else ls(32575))
	ok_dialog(heading=32733, text=text, top_space=True)

def resolve_cached_torrents(debrid_provider, item_url, _hash, title, season, episode):
	debrid_function = import_debrid(debrid_provider)
	store_to_cloud = store_resolved_torrent_to_cloud(debrid_provider)
	try: url = debrid_function().resolve_magnet(item_url, _hash, store_to_cloud, title, season, episode)
	except: url = None
	return url

def resolve_debrid(debrid_provider, item_provider, item_url):
	debrid_function = import_debrid(debrid_provider)
	try: url = debrid_function().unrestrict_link(item_url)
	except: url = None
	return url

def resolve_internal_sources(scrape_provider, item_id, url_dl, direct_debrid_link=False):
	try:
		if scrape_provider == 'easynews':
			from indexers.easynews import resolve_easynews
			url = resolve_easynews({'url_dl': url_dl, 'play': 'false'})
		elif scrape_provider == 'rd_cloud':
			if direct_debrid_link: url = url_dl
			else: url = real_debrid_api.RealDebridAPI().unrestrict_link(item_id)
		elif scrape_provider == 'pm_cloud':
			details = premiumize_api.PremiumizeAPI().get_item_details(item_id)
			url = details['link']
			if url.startswith('/'): url = 'https' + url
		elif scrape_provider == 'ad_cloud':
			url = alldebrid_api.AllDebridAPI().unrestrict_link(item_id)
		elif scrape_provider == 'oc_cloud':
			url = url_dl
		elif scrape_provider == 'tb_cloud':
			if direct_debrid_link == 'usenet':
				url = torbox_api.TorBoxAPI().unrestrict_usenet(url_dl)
			elif direct_debrid_link == 'webdl':
				url = torbox_api.TorBoxAPI().unrestrict_webdl(url_dl)
			else:
				url = torbox_api.TorBoxAPI().unrestrict_link(item_id)
		elif scrape_provider == 'folders':
			if url_dl.endswith('.strm'):
				with kodi_utils.open_file(url_dl) as f: url = f.read()
			else: url = url_dl
	except: url = None
	return url

class DebridCheck:
	hash_list = []
	cached_hashes = []

	@classmethod
	def set_cached_hashes(cls, hash_list):
		cls.hash_list = hash_list
		cls.cached_hashes = DebridCache().get_many(hash_list) or []

	def __init__(self, *args):
		self.completed = False
		self.cached_list, self.hashes_to_cache = [], []
		self.name, self.debrid, self.function = args[0], args[1], args[3]
		self.thread = Thread(target=self.cache_check, name=args[0])

	def cache_write(self):
		DebridCache().set_many(self.hashes_to_cache, self.debrid)

	def cache_check(self):
		try:
			self.cached_list = [
				i[0] for i in self.cached_hashes if i[1] == self.debrid and i[2] == 'True'
			]
			unchecked_filter = {h[0] for h in self.cached_hashes if h[1] == self.debrid}
			unchecked_hashes = [i for i in self.hash_list if not i in unchecked_filter]
			if self.debrid in ('rd', 'ad') or not unchecked_hashes: return
			checked_hashes = self.function().check_cache(unchecked_hashes)
			if not checked_hashes: return
			cached_append = self.cached_list.append
			process_append = self.hashes_to_cache.append
			try:
				for h in unchecked_hashes:
					cached = 'False'
					if h in checked_hashes:
						cached_append(h)
						cached = 'True'
					process_append((h, cached))
			except:
				for i in unchecked_hashes: process_append((i, 'False'))
			if self.hashes_to_cache: Thread(target=self.cache_write).start()
		finally: self.completed = True

