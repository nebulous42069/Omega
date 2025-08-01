import sys
from apis.real_debrid_api import RealDebridAPI as Debrid
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, clean_title, normalize, jsondate_to_datetime
# from modules.kodi_utils import logger

get_setting, set_setting = kodi_utils.get_setting, kodi_utils.set_setting
ls, build_url, make_listitem = kodi_utils.local_string, kodi_utils.build_url, kodi_utils.make_listitem
folder_str, file_str, delete_str, down_str = ls(32742).upper(), ls(32743).upper(), ls(32785), ls(32747)
fanart = kodi_utils.translate_path('special://home/addons/plugin.video.pov/fanart.png')
default_icon = kodi_utils.translate_path('special://home/addons/plugin.video.pov/resources/media/realdebrid.png')
default_art = {'icon': default_icon, 'poster': default_icon, 'thumb': default_icon, 'fanart': fanart, 'banner': default_icon}
extensions = supported_video_extensions()

class Indexer(Debrid):
	def run(self, params):
		if   '_delete' in params['mode']:
			return self.cloud_delete(params['id'], params['cache_type'])
		elif '_browse_cloud' in params['mode']:
			torrent_files = self.user_cloud_info(params['id'])
			items = (i for i in torrent_files['files'] if i['selected'])
			items = [{**i, 'url_link': link} for i, link in zip(items, torrent_files['links'])]
			_builder = self.browse_cloud
		elif '_torrent_cloud' in params['mode']:
			items = self.user_cloud()
			_builder = self.torrent_cloud
		elif '_downloads' in params['mode']:
			items = self.downloads()
			_builder = self.browse_downloads
		else: return getattr(self, params['mode'].split('.')[-1])()
		__handle__ = int(sys.argv[1])
		kodi_utils.add_items(__handle__, list(_builder(items)))
		kodi_utils.set_content(__handle__, 'files')
		kodi_utils.end_directory(__handle__)
		kodi_utils.set_view_mode('view.premium')

	def torrent_cloud(self, items):
		for count, item in enumerate(items, 1):
			try:
				if not item.get('ended'): continue
				cm = []
				cm_append = cm.append
				display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, clean_file_name(normalize(item['filename'])).upper())
				url_params = {'mode': 'real_debrid.rd_browse_cloud', 'id': item['id']}
				delete_params = {'mode': 'real_debrid.rd_delete', 'id': item['id'], 'cache_type': 'torrent'}
				cm_append(('[B]%s %s[/B]' % (delete_str, folder_str.capitalize()), 'RunPlugin(%s)' % build_url(delete_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				yield (url, listitem, True)
			except: pass

	def browse_cloud(self, items):
		for count, item in enumerate(items, 1):
			try:
				cm = []
				name = item['path'].lstrip('/')
				name = clean_file_name(name).upper()
				url_link = item['url_link']
				if url_link.startswith('/'): url_link = 'http' + url_link
				size = float(int(item['bytes']))/1073741824
				display = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, size, name)
				url_params = {'mode': 'real_debrid.resolve_rd', 'url': url_link, 'play': 'true'}
				url = build_url(url_params)
				down_file_params = {'mode': 'downloader', 'action': 'cloud.realdebrid',
									'name': name, 'url': url_link, 'image': default_icon}
				cm.append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				listitem.setInfo('video', {})
				yield (url, listitem, False)
			except: pass

	def browse_downloads(self, items):
		for count, item in enumerate(items, 1):
			try:
				if not item['download'].lower().endswith(tuple(extensions)): continue
				cm = []
				cm_append = cm.append
				datetime_object = jsondate_to_datetime(item['generated'], '%Y-%m-%dT%H:%M:%S.%fZ', remove_time=True)
				filename, url_link = item['filename'], item['download']
				name = clean_file_name(filename).upper()
				size = float(int(item['filesize']))/1073741824
				display = '%02d | %.2f GB | %s  | [I]%s [/I]' % (count, size, datetime_object, name)
				url_params = {'mode': 'media_play', 'url': url_link, 'media_type': 'video'}
				delete_params = {'mode': 'real_debrid.rd_delete', 'id': item['id'], 'cache_type': 'download'}
				down_file_params = {'mode': 'downloader', 'action': 'cloud.realdebrid_direct',
									'name': name, 'url': url_link, 'image': default_icon}
				cm_append((down_str, 'RunPlugin(%s)' % build_url(down_file_params)))
				cm_append(('[B]%s %s[/B]' % (delete_str, file_str.capitalize()), 'RunPlugin(%s)' % build_url(delete_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				yield (url, listitem, False)
			except: pass

	def cloud_delete(self, file_id, cache_type):
		if not kodi_utils.confirm_dialog(): return
		if cache_type == 'torrent': result = self.delete_torrent(file_id)
		else: result = self.delete_download(file_id) # cache_type: 'download'
		if result.status_code in (401, 403, 404): return kodi_utils.notification(32574)
		self.clear_cache()
		kodi_utils.container_refresh()

	def show_account_info(self):
		from datetime import datetime
		from modules.utils import datetime_workaround
		try:
			kodi_utils.show_busy_dialog()
			account_info = self.account_info()
			expires = datetime_workaround(account_info['expiration'], '%Y-%m-%dT%H:%M:%S.%fZ')
			days_remaining = (expires - datetime.today()).days
			body = []
			append = body.append
			append(ls(32758) % account_info['email'])
			append(ls(32755) % account_info['username'])
			append(ls(32757) % account_info['type'].capitalize())
			append(ls(32750) % expires)
			append(ls(32751) % days_remaining)
			append(ls(32759) % account_info['points'])
			kodi_utils.hide_busy_dialog()
			return kodi_utils.show_text(ls(32054).upper(), '\n\n'.join(body), font_size='large')
		except: kodi_utils.hide_busy_dialog()

def resolve_rd(params):
	url = params['url']
	resolved_link = Debrid().unrestrict_link(url)
	if params.get('play', 'false') != 'true' : return resolved_link
	from modules.player import POVPlayer
	POVPlayer().run(resolved_link, 'video')

