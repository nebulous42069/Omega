import sys
from apis.offcloud_api import OffcloudAPI as Debrid
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, normalize
# from modules.kodi_utils import logger

get_setting, set_setting = kodi_utils.get_setting, kodi_utils.set_setting
ls, build_url, make_listitem = kodi_utils.local_string, kodi_utils.build_url, kodi_utils.make_listitem
folder_str, file_str, delete_str, down_str = ls(32742).upper(), ls(32743).upper(), ls(32785), ls(32747)
fanart = kodi_utils.translate_path('special://home/addons/plugin.video.pov/fanart.png')
default_icon = kodi_utils.translate_path('special://home/addons/plugin.video.pov/resources/media/offcloud.png')
default_art = {'icon': default_icon, 'poster': default_icon, 'thumb': default_icon, 'fanart': fanart, 'banner': default_icon}
extensions = supported_video_extensions()

class Indexer(Debrid):
	def run(self, params):
		if   '_delete' in params['mode']:
			return self.cloud_delete(params['folder_id'])
		elif '_browse_cloud' in params['mode']:
			items = self.user_cloud(params['folder_id'])
			_builder = self.browse_cloud
		elif '_torrent_cloud' in params['mode']:
			items = self.user_cloud()
			_builder = self.torrent_cloud
		else: return getattr(self, params['mode'].split('.')[-1])()
		__handle__ = int(sys.argv[1])
		kodi_utils.add_items(__handle__, list(_builder(items)))
		kodi_utils.set_content(__handle__, 'files')
		kodi_utils.end_directory(__handle__)
		kodi_utils.set_view_mode('view.premium')

	def torrent_cloud(self, items):
		for count, item in enumerate(items, 1):
			try:
				if not item['status'] == 'downloaded': continue
				cm = []
				cm_append = cm.append
				request_id, server = item['requestId'], item['server']
				folder_name, is_folder = item['fileName'], item['isDirectory']
				delete_params = {'mode': 'offcloud.oc_delete', 'folder_id': request_id}
				if is_folder:
					display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, clean_file_name(normalize(folder_name)).upper())
					url_params = {'mode': 'offcloud.oc_browse_cloud', 'folder_id': request_id}
					cm_append(('[B]%s %s[/B]' % (delete_str, folder_str.capitalize()), 'RunPlugin(%s)' % build_url(delete_params)))
				else:
					display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, file_str, clean_file_name(normalize(folder_name)).upper())
					link = self.requote_uri(self.build_url(server, request_id, folder_name))
					url_params = {'mode': 'media_play', 'url': link, 'media_type': 'video'}
					down_file_params = {'mode': 'downloader', 'action': 'cloud.offcloud_direct', 'name': folder_name, 'url': link, 'image': default_icon}
					cm_append(('[B]%s %s[/B]' % (delete_str, file_str.capitalize()), 'RunPlugin(%s)' % build_url(delete_params)))
					cm.append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				yield (url, listitem, is_folder)
			except: pass

	def browse_cloud(self, items):
		for count, item in enumerate(items, 1):
			try:
				if not item.lower().endswith(tuple(extensions)): continue
				cm = []
				cm_append = cm.append
				name = item.split('/')[-1]
				name = clean_file_name(name).upper()
				link = self.requote_uri(item)
				display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, file_str, name)
				url_params = {'mode': 'media_play', 'url': link, 'media_type': 'video'}
				down_file_params = {'mode': 'downloader', 'action': 'cloud.offcloud_direct', 'name': name, 'url': link, 'image': default_icon}
				cm_append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				listitem.setInfo('video', {})
				yield (url, listitem, False)
			except: pass

	def cloud_delete(self, folder_id):
		if not kodi_utils.confirm_dialog(): return
		result = self.delete_torrent(folder_id)
		if 'success' not in result: return kodi_utils.notification(32574)
		self.clear_cache()
		kodi_utils.container_refresh()

	def user_cloud_clear(self):
		if not kodi_utils.confirm_dialog(): return
		from threading import Thread
		files = self.user_cloud(check_cache=False)
		if not files: return kodi_utils.notification(32760)
		len_files = len(files)
		progressBG = kodi_utils.progressDialogBG
		progressBG.create('Offcloud', 'Clearing cloud files')
		for count, i in enumerate(files, 1):
			try:
				req = Thread(target=self.delete_torrent, args=(i['requestId'],), name=i['fileName'])
				req.start()
				progressBG.update(int(count / len_files * 100), '%s: %s...' % (ls(32785), req.name))
				req.join(1)
			except: pass
		try: progressBG.close()
		except: pass
		self.clear_cache()

	def show_account_info(self):
		try:
			kodi_utils.show_busy_dialog()
			account_info = self.account_info()
			body = []
			append = body.append
			append(ls(32758) % account_info['email'])
			append(ls(32755) % account_info['userId'])
			append('[B]Premium[/B]: %s' % account_info['isPremium'])
			append(ls(32750) % account_info['expirationDate'])
			append('[B]Cloud Limit[/B]: {:,}'.format(account_info['limits']['cloud']))
			kodi_utils.hide_busy_dialog()
			return kodi_utils.show_text('Offcloud'.upper(), '\n\n'.join(body), font_size='large')
		except: kodi_utils.hide_busy_dialog()

