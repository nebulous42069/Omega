import json
from sys import argv
from apis.alldebrid_api import AllDebridAPI
from modules import kodi_utils
from modules.source_utils import supported_video_extensions, source_warning
from modules.utils import clean_file_name, normalize
# from modules.kodi_utils import logger

get_setting, set_setting = kodi_utils.get_setting, kodi_utils.set_setting
ls, build_url, make_listitem = kodi_utils.local_string, kodi_utils.build_url, kodi_utils.make_listitem
folder_str, file_str, archive_str, down_str = ls(32742).upper(), ls(32743).upper(), ls(32982), ls(32747)
fanart = kodi_utils.translate_path('special://home/addons/plugin.video.pov/fanart.png')
default_icon = kodi_utils.translate_path('special://home/addons/plugin.video.pov/resources/media/alldebrid.png')
default_art = {'icon': default_icon, 'poster': default_icon, 'thumb': default_icon, 'fanart': fanart, 'banner': default_icon}
AllDebrid, extensions = AllDebridAPI(), supported_video_extensions()

def ad_torrent_cloud(folder_id=None):
	def _builder():
		for count, item in enumerate(cloud_dict, 1):
			try:
				folder_name = item['filename']
				display = '%02d | [B]%s[/B] | [I]%s [/I]' % (count, folder_str, clean_file_name(normalize(folder_name)).upper())
				url_params = {'mode': 'alldebrid.browse_ad_cloud', 'folder': json.dumps(item['links'])}
				url = build_url(url_params)
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.setArt(default_art)
				yield (url, listitem, True)
			except: pass
	try: cloud_dict = [i for i in AllDebrid.user_cloud()['magnets'] if i['statusCode'] == 4]
	except: cloud_dict = []
	__handle__ = int(argv[1])
	kodi_utils.add_items(__handle__, list(_builder()))
	kodi_utils.set_content(__handle__, 'files')
	kodi_utils.end_directory(__handle__)
	kodi_utils.set_view_mode('view.premium')

def browse_ad_cloud(folder):
	def _builder():
		for count, item in enumerate(links, 1):
			try:
				cm = []
				url_link = item['link']
				name = clean_file_name(item['filename']).upper()
				size = item['size']
				display_size = float(int(size))/1073741824
				display = '%02d | [B]%s[/B] | %.2f GB | [I]%s [/I]' % (count, file_str, display_size, name)
				url_params = {'mode': 'alldebrid.resolve_ad', 'url': url_link, 'play': 'true'}
				url = build_url(url_params)
				down_file_params = {'mode': 'downloader', 'name': name, 'url': url_link,
									'action': 'cloud.alldebrid', 'image': default_icon}
				cm.append((down_str,'RunPlugin(%s)' % build_url(down_file_params)))
				listitem = make_listitem()
				listitem.setLabel(display)
				listitem.addContextMenuItems(cm)
				listitem.setArt(default_art)
				listitem.setInfo('video', {})
				yield (url, listitem, False)
			except: pass
	try: links = [i for i in json.loads(folder) if i['filename'].lower().endswith(tuple(extensions))]
	except: links = []
	__handle__ = int(argv[1])
	kodi_utils.add_items(__handle__, list(_builder()))
	kodi_utils.set_content(__handle__, 'files')
	kodi_utils.end_directory(__handle__)
	kodi_utils.set_view_mode('view.premium')

def resolve_ad(params):
	url = params['url']
	resolved_link = AllDebrid.unrestrict_link(url)
	if params.get('play', 'false') != 'true' : return resolved_link
	from modules.player import POVPlayer
	POVPlayer().run(resolved_link, 'video')

def show_account_info():
	from datetime import datetime
	try:
		kodi_utils.show_busy_dialog()
		account_info = AllDebrid.account_info()['user']
		username = account_info['username']
		email = account_info['email']
		status = 'Premium' if account_info['isPremium'] else 'Not Active'
		expires = datetime.fromtimestamp(account_info['premiumUntil'])
		days_remaining = (expires - datetime.today()).days
		body = []
		append = body.append
		append(ls(32755) % username)
		append(ls(32756) % email)
		append(ls(32757) % status)
		append(ls(32750) % expires)
		append(ls(32751) % days_remaining)
		kodi_utils.hide_busy_dialog()
		return kodi_utils.show_text(ls(32063).upper(), '\n\n'.join(body), font_size='large')
	except: kodi_utils.hide_busy_dialog()

@source_warning
def set_auth():
	import urllib.parse
	from apis.alldebrid_api import base_url, user_agent, session, timeout
	session.cookies.clear()
	url = base_url + 'pin/get?agent=%s' % user_agent
	response = session.get(url, timeout=timeout)
	result = response.json()['data']
	try:
		qr_url = '&bgcolor=ffd700&data=%s' % urllib.parse.quote(result['user_url'])
		qr_icon = 'https://api.qrserver.com/v1/create-qr-code/?size=256x256&qzone=1%s' % qr_url
	except: pass
	line2 = '%s, %s' % (ls(32700) % result['base_url'], ls(32701) % result['pin'])
	choices = [
		('none', 'Use the QR Code to approve access at AllDebrid', 'Step 1: %s' % line2),
		('approve', 'Access approved at AllDebrid', 'Step 2'), 
		('cancel', 'Cancel', 'Cancel')
	]
	list_items = [{'line1': item[1], 'line2': item[2], 'icon': qr_icon} for item in choices]
	kwargs = {'items': json.dumps(list_items), 'heading': 'AllDebrid', 'multi_line': 'true'}
	choice = kodi_utils.select_dialog([i[0] for i in choices], **kwargs)
	if choice != 'approve': return
	url = result['check_url']
	response = session.get(url, timeout=timeout)
	result = response.json()['data']
	token = result['apikey']
	kodi_utils.sleep(500)
	url = base_url + 'user?agent=%s&apikey=%s' % (user_agent, token)
	result = session.get(url, timeout=timeout).json()['data']
	username = result['user']['username']
	set_setting('ad.account_id', str(username))
	set_setting('ad.token', token)
	kodi_utils.notification('%s %s' % (ls(32576), ls(32063)))
	return True

def del_auth():
	if not kodi_utils.confirm_dialog(): return
	set_setting('ad.account_id', '')
	set_setting('ad.token', '')
	kodi_utils.notification('%s %s' % (ls(32576), ls(32059)))

