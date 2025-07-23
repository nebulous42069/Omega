import sys
from apis.torbox_api import TorBoxAPI as Debrid
from modules import kodi_utils
from modules.source_utils import supported_video_extensions
from modules.utils import clean_file_name, normalize
# from modules.kodi_utils import logger

get_setting, set_setting = kodi_utils.get_setting, kodi_utils.set_setting
ls, build_url, make_listitem = kodi_utils.local_string, kodi_utils.build_url, kodi_utils.make_listitem
folder_str, file_str, delete_str, down_str = ls(32742).upper(), ls(32743).upper(), ls(32785), ls(32747)
fanart = kodi_utils.translate_path('special://home/addons/plugin.video.pov/fanart.png')
default_icon = kodi_utils.translate_path('special://home/addons/plugin.video.pov/resources/media/torbox.png')
default_art = {'icon': default_icon, 'poster': default_icon, 'thumb': default_icon, 'fanart': fanart, 'banner': default_icon}
extensions = supported_video_extensions()

class Indexer(Debrid):
	def run(self, params):
		if   '_delete' in params['mode']:
			return self.cloud_delete(params['folder_id'], params['media_type'])
		elif '_browse_cloud' in params['mode']:
			folder_id, media_type = params['folder_id'], params['media_type']
			if   media_type == 'usenet': items = self.user_cloud_usenet(folder_id)
			elif media_type == 'webdl': items = self.user_cloud_webdl(folder_id)
			else: items = self.user_cloud(folder_id)
			items = [{**i, 'url': '%d,%d' % (int(folder_id), i['id']), 'mediatype': media_type} for i in items['files']]
			_builder = self.browse_cloud
		elif '_torrent_cloud' in params['mode']:
			media_type = params['media_type']
			if   media_type == 'usenet': items = self.user_cloud_usenet()
			elif media_type == 'webdl': items = self.user_cloud_webdl()
			else: items = self.user_cloud()
			items = [{**i, 'mediatype': media_type} for i in items]
			_builder = self.torrent_cloud
		elif '_usenet_query' in params['mode']:
			query, imdb_id = params.get('query'), params.get('imdb_id')
			season, episode = params.get('season'), params.get('episode')
			items = self.usenet_search(query, season, episode, imdb_id)
			_builder = self.usenet_query
		else: return getattr(self, params['mode'].split('.')[-1])()
		__handle__ = int(sys.argv[1])
		kodi_utils.add_items(__handle__, list(_builder(items)))
		kodi_utils.set_content(__handle__, 'files')
		kodi_utils.end_directory(__handle__)
		kodi_utils.set_view_mode('view.premium')

	def torrent_cloud(self, items):
		items.sort(key=lambda k: k['updated_at'], reverse=True)
		for count, item in enumerate(items, 1):
			try:
				if not item['download_finished']: continue
				cm = []
				cm_append = cm.append
				display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, clean_file_name(normalize(item['name'])).upper())
				url_params = {'mode': 'torbox.tb_browse_cloud', 'folder_id': item['id'], 'media_type': item['mediatype']}
				delete_params = {'mode': 'torbox.tb_delete', 'folder_id': item['id'], 'media_type': item['mediatype']}
				cm_append(('[B]%s %s[/B]' % (delete_str, folder_str.capitalize()), 'RunPlugin(%s)' % build_url(delete_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				yield (url, listitem, True)
			except: pass

	def browse_cloud(sel, items):
		for count, item in enumerate(items, 1):
			try:
				if not item['short_name'].lower().endswith(tuple(extensions)): continue
				cm = []
				cm_append = cm.append
				name = clean_file_name(item['short_name']).upper()
				size = float(int(item['size']))/1073741824
				display = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, size, name)
				params = {'url': item['url'], 'media_type': item['mediatype']}
				url_params = {'mode': 'torbox.resolve_tb', 'play': 'true', **params}
				down_file_params = {'mode': 'downloader', 'action': 'cloud.torbox', 'name': name, 'image': default_icon, **params}
				cm_append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				listitem.setInfo('video', {})
				yield (url, listitem, False)
			except: pass

	def usenet_query(self, items):
		KODI_VERSION = kodi_utils.get_kodi_version()
		uncached = [i for i in items if not i['cached']]
		items = [i for i in items if i['cached']] + uncached
		for count, item in enumerate(items, 1):
			try:
				name = clean_file_name(item['raw_title']).upper()
				age, parts, tracker = item['age'], item['files'], item['tracker']
				size = float(int(item['size']))/1073741824
				if item['owned']: display = '%02d | %.2f GB | [COLOR cyan]CLOUD[/COLOR] | [I]%s[/I]'
				elif item['cached']: display = '%02d | %.2f GB | [COLOR magenta]CACHED[/COLOR] | [I]%s[/I]'
				else: display = '%02d | %.2f GB | [I]%s[/I]'
				display = display % (count, size, name)
				plot = '[B]Tracker[/B]: [I]%s[/I][CR][CR][B]Files[/B]: %s[CR][CR][B]Age[/B]: %s' % (tracker, parts, age)
				url_params = {'mode': 'manual_add_nzb_to_cloud', 'provider': 'TorBox', 'url': item['nzb'], 'name': name}
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt(default_art)
				listitem.setInfo('video', {'plot': plot}) if KODI_VERSION < 20 else listitem.getVideoInfoTag().setPlot(plot)
				yield (url, listitem, False)
			except: pass

	def cloud_delete(self, folder_id, media_type):
		if not kodi_utils.confirm_dialog(): return
		if   media_type == 'usenet': result = self.delete_usenet(folder_id)
		elif media_type == 'webdl': result = self.delete_webdl(folder_id)
		else: result = self.delete_torrent(folder_id)
		if not result: return kodi_utils.notification(32574)
		self.clear_cache()
		kodi_utils.container_refresh()

	def user_cloud_clear(self):
		if not kodi_utils.confirm_dialog(): return
		data = {'all': True, 'operation': 'delete'}
		self._post(self.remove, json=data)
		self._post(self.remove_usenet, json=data)
		self.clear_cache()

	def show_account_info(self):
		from datetime import datetime
		from modules.utils import datetime_workaround
		try:
			kodi_utils.show_busy_dialog()
			plans = {0: 'Free', 1: 'Essential', 2: 'Pro', 3: 'Standard'}
			account_info = self.account_info()
			expires = datetime_workaround(account_info['premium_expires_at'], '%Y-%m-%dT%H:%M:%SZ')
			days_remaining = (expires - datetime.today()).days
			body = []
			append = body.append
			append(ls(32758) % account_info['email'])
			append(ls(32755) % account_info['customer'])
			append(ls(32757) % plans[account_info['plan']])
			append(ls(32750) % expires.strftime('%Y-%m-%d'))
			append(ls(32751) % days_remaining)
			append('[B]Downloaded[/B]: %s' % account_info['total_downloaded'])
			kodi_utils.hide_busy_dialog()
			return kodi_utils.show_text('TorBox'.upper(), '\n\n'.join(body), font_size='large')
		except: kodi_utils.hide_busy_dialog()

def resolve_tb(params):
	file_id, media_type = params['url'], params['media_type']
	if   media_type == 'usenet': resolved_link = Debrid().unrestrict_usenet(file_id)
	elif media_type == 'webdl': resolved_link = Debrid().unrestrict_webdl(file_id)
	else: resolved_link = Debrid().unrestrict_link(file_id)
	if params.get('play', 'false') != 'true': return resolved_link
	from modules.player import POVPlayer
	POVPlayer().run(resolved_link, 'video')

