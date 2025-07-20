import sys
from apis.real_debrid_api import RealDebridAPI as Debrid
from modules import kodi_utils
from modules.source_utils import supported_video_extensions, source_warning
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

	@source_warning
	def set_auth(self):
		import json, urllib.parse
		from apis.real_debrid_api import base_url, auth_url, session, timeout
		session.cookies.clear()
		client_id = get_setting('rd.client_id') or 'X245A4XAIBGVM'
		data = {'grant_type': 'http://oauth.net/grant_type/device/1.0', 'client_id': '', 'client_secret': '', 'code': ''}
		url = '%sdevice/code?client_id=%s&new_credentials=yes' % (auth_url, client_id)
		response = session.get(url, timeout=timeout)
		result = response.json()
		data['code'] = result['device_code']
		try:
			qr_url = '&data=%s' % urllib.parse.quote(result['direct_verification_url'])
			qr_icon = 'https://api.qrserver.com/v1/create-qr-code/?size=256x256&qzone=1%s' % qr_url
		except: pass
		line2 = '%s, %s' % (ls(32700) % result['verification_url'], ls(32701) % result['user_code'])
		choices = [
			('none', 'Use the QR Code to approve access at Real-Debrid', 'Step 1: %s' % line2),
			('approve', 'Access approved at Real-Debrid', 'Step 2'), 
			('cancel', 'Cancel', 'Cancel')
		]
		list_items = [{'line1': item[1], 'line2': item[2], 'icon': qr_icon} for item in choices]
		kwargs = {'items': json.dumps(list_items), 'heading': 'Real-Debrid', 'multi_line': 'true'}
		choice = kodi_utils.select_dialog([i[0] for i in choices], **kwargs)
		if choice != 'approve': return
		url = '%sdevice/credentials?client_id=%s&code=%s' % (auth_url, client_id, data['code'])
		response = session.get(url, timeout=timeout)
		result = response.json()
		data.update({'client_id': result['client_id'], 'client_secret': result['client_secret']})
		url = '%stoken' % auth_url
		response = session.post(url, data=data, timeout=timeout)
		result = response.json()
		client_id, secret = data['client_id'], data['client_secret']
		token, refresh = result['access_token'], result['refresh_token']
		kodi_utils.sleep(500) # from My Accounts
		result = session.get(f"{base_url}user?auth_token={token}", timeout=timeout).json()
		username = result['username']
		set_setting('rd.username', str(username))
		set_setting('rd.client_id', client_id)
		set_setting('rd.token', token)
		set_setting('rd.refresh', refresh)
		set_setting('rd.secret', secret)
		kodi_utils.notification('%s %s' % (ls(32576), ls(32054)))
		return True

	def del_auth(self):
		if not kodi_utils.confirm_dialog(): return
		set_setting('rd.username', '')
		set_setting('rd.client_id', '')
		set_setting('rd.token', '')
		set_setting('rd.refresh', '')
		set_setting('rd.secret', '')
		self.clear_cache()
		kodi_utils.notification('%s %s' % (ls(32576), ls(32059)))

def resolve_rd(params):
	url = params['url']
	resolved_link = Debrid().unrestrict_link(url)
	if params.get('play', 'false') != 'true' : return resolved_link
	from modules.player import POVPlayer
	POVPlayer().run(resolved_link, 'video')

