import sys
from apis.easydebrid_api import EasyDebridAPI as Debrid
from modules import kodi_utils
# from modules.kodi_utils import logger

ls, get_setting, set_setting = kodi_utils.local_string, kodi_utils.get_setting, kodi_utils.set_setting

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

	def show_account_info(self):
		from datetime import datetime
		try:
			kodi_utils.show_busy_dialog()
			account_info = self.account_info()
			if account_info['paid_until']:
				expires = datetime.fromtimestamp(account_info['paid_until'])
				days_remaining = (expires - datetime.today()).days
				expires = expires.strftime('%Y-%m-%d')
			else: expires, days_remaining = 'Expired', 'None'
			body = []
			append = body.append
			append(ls(32755) % account_info['id'])
			append(ls(32750) % expires)
			append(ls(32751) % days_remaining)
			kodi_utils.hide_busy_dialog()
			return kodi_utils.show_text('EasyDebrid'.upper(), '\n\n'.join(body), font_size='large')
		except: kodi_utils.hide_busy_dialog()

	def set_auth(self):
		api_key = kodi_utils.dialog.input('EasyDebrid API Key:')
		if not api_key: return
		from apis.easydebrid_api import base_url, session, timeout
		session.cookies.clear()
		headers = {'Authorization': f"Bearer {api_key}"}
		result = session.get(f"{base_url}/user/details", headers=headers, timeout=timeout).json()
		customer = result['id']
		set_setting('ed.account_id', str(customer))
		set_setting('ed.token', api_key)
		kodi_utils.notification('%s %s' % (ls(32576), 'EasyDebrid'))
		return True

	def del_auth(self):
		if not kodi_utils.confirm_dialog(): return
		set_setting('ed.token', '')
		set_setting('ed.account_id', '')
		self.clear_cache()
		kodi_utils.notification('%s %s' % (ls(32576), ls(32059)))

