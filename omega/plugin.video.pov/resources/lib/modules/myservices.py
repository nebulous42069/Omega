import requests, time
from threading import Thread, Timer
from windows import create_window
from modules import kodi_utils, cache_utils
from modules.source_utils import source_warning
# logger = kodi_utils.logger

quote, clear_cache = requests.utils.quote, cache_utils.clear_cache
get_setting, set_setting, sleep = kodi_utils.get_setting, kodi_utils.set_setting, kodi_utils.sleep
notification, confirm_dialog = kodi_utils.notification, kodi_utils.confirm_dialog
qr_str = 'https://api.qrserver.com/v1/create-qr-code/?size=256x256&qzone=1%s'
meta_keys = 'title year poster fanart clearlogo tmdblogo'
code_str, nav2_str = 'PIN CODE: [B]%s[/B]', 'LOCATION: [B]%s[/B]'
await_str = 'REMAINING: [B]%02d:%02d[/B]'
timeout = 3.05

def _make_progress_dialog(**kwargs):
	progress_dialog = create_window(('windows.sources', 'ProgressMedia'), 'progress_media.xml', **kwargs)
	Thread(target=progress_dialog.run).start()
	return progress_dialog

def authorize(service):
	return {
		'realdebrid': RealDebrid, 'premiumize': Premiumize, 'alldebrid': AllDebrid,
		'easydebrid': EasyDebrid, 'torbox': TorBox, 'offcloud': Offcloud,
		'trakt': Trakt, 'mdblist': MDBList, 'tmdblist': TMDbList
	}[service]().set_auth()

class RepeatTimer(Timer):
	def run(self):
		while not self.finished.wait(self.interval):
			self.function(*self.args, **self.kwargs)

class RealDebrid:
	def __init__(self):
		self.token = get_setting('rd.token')
		self.client_id = get_setting('rd.client_id') or 'X245A4XAIBGVM'
		self.secret = get_setting('rd.secret')

	def base_url(self, path):
		return 'https://app.real-debrid.com/%s' % path

	def poll_auth(self, data):
		params = {'client_id': self.client_id, 'code': data['code']}
		response = requests.get(self.base_url('oauth/v2/device/credentials'), params=params, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.secret = data['client_secret']

	@source_warning
	def set_auth(self):
		cls_name = 'Real Debrid'
		if self.token:
			if not confirm_dialog(): return
			set_setting('rd.username', '')
			set_setting('rd.client_id', '')
			set_setting('rd.token', '')
			set_setting('rd.refresh', '')
			set_setting('rd.secret', '')
			clear_cache('rd_cloud', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		params = {'client_id': self.client_id, 'new_credentials': 'yes'}
		response = requests.get(self.base_url('oauth/v2/device/code'), params=params, timeout=timeout)
		result = response.json()
		data = {'code': result['device_code'], 'grant_type': 'http://oauth.net/grant_type/device/1.0'}
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&data=%s' % quote(result['direct_verification_url'])
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon}
		detail = code_str % result['user_code'], nav2_str % result['verification_url']
		progress_dialog = _make_progress_dialog(meta=meta)
		timer = RepeatTimer(result['interval'], self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.secret or progress_dialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progress_dialog.update('[CR]'.join(lines), progress)
			sleep(1000)
		timer.cancel()
		progress_dialog.close()
		if progress_dialog.iscanceled(): return False
		if not self.secret: return notification(32574)
		response = requests.post(self.base_url('oauth/v2/token'), data=data, timeout=timeout)
		data.update(response.json())
		sleep(500)
		headers = {}
		headers.update({'Authorization': 'Bearer %s' % data['access_token']})
		response = requests.get(self.base_url('rest/1.0/user'), headers=headers, timeout=timeout)
		username = response.json()['username']
		client_id, secret = data['client_id'], data['client_secret']
		token, refresh = data['access_token'], data['refresh_token']
		set_setting('rd.username', str(username))
		set_setting('rd.client_id', client_id)
		set_setting('rd.token', token)
		set_setting('rd.refresh', refresh)
		set_setting('rd.secret', secret)
		notification('Set %s Authorization' % cls_name)
		return True

class Premiumize:
	user_agent = 'POV for Kodi'

	def __init__(self):
		self.token = get_setting('pm.token')
		self.client_id = '663882072'

	def base_url(self, path):
		return 'https://www.premiumize.me/%s' % path

	def poll_auth(self, data):
		response = requests.post(self.base_url('token'), json=data, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.token = data['access_token']

	def set_auth(self):
		cls_name = 'Premiumize.me'
		if self.token:
			if not confirm_dialog(): return
			set_setting('pm.account_id', '')
			set_setting('pm.token', '')
			clear_cache('pm_cloud', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		data = {'client_id': self.client_id, 'response_type': 'device_code'}
		response = requests.post(self.base_url('token'), json=data, timeout=timeout)
		result = response.json()
		data = {'client_id': self.client_id, 'code': result['device_code'], 'grant_type': 'device_code'}
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&data=%s' % quote(result['verification_uri'])
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon}
		detail = code_str % result['user_code'], nav2_str % result['verification_uri']
		progress_dialog = _make_progress_dialog(meta=meta)
		timer = RepeatTimer(result['interval'], self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progress_dialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progress_dialog.update('[CR]'.join(lines), progress)
			sleep(1000)
		timer.cancel()
		progress_dialog.close()
		if progress_dialog.iscanceled(): return False
		if not self.token: return notification(32574)
		sleep(500)
		headers = {'User-Agent': self.user_agent}
		headers.update({'Authorization': 'Bearer %s' % self.token})
		response = requests.get(self.base_url('api/account/info'), headers=headers, timeout=timeout)
		username = response.json()['customer_id']
		token = str(data['access_token'])
		set_setting('pm.account_id', str(username))
		set_setting('pm.token', token)
		notification('Set %s Authorization' % cls_name)
		return True

class AllDebrid:
	user_agent = 'pov_for_kodi'

	def __init__(self):
		self.token = get_setting('ad.token')

	def base_url(self, path):
		return 'https://api.alldebrid.com/%s' % path

	def poll_auth(self, url):
		response = requests.get(url, timeout=timeout)
		result = response.json()['data']
		self.token = result.get('apikey', '')

	@source_warning
	def set_auth(self):
		cls_name = self.__class__.__name__
		if self.token:
			if not confirm_dialog(): return
			set_setting('ad.account_id', '')
			set_setting('ad.token', '')
			clear_cache('ad_cloud', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		params = {'agent': self.user_agent}
		response = requests.get(self.base_url('v4/pin/get'), params=params, timeout=timeout)
		result = response.json()['data']
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&bgcolor=ffd700&data=%s' % quote(result['user_url'])
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon}
		detail = code_str % result['pin'], nav2_str % result['base_url']
		progress_dialog = _make_progress_dialog(meta=meta)
		timer = RepeatTimer(5, self.poll_auth, args=(result['check_url'],))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progress_dialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progress_dialog.update('[CR]'.join(lines), progress)
			sleep(1000)
		timer.cancel()
		progress_dialog.close()
		if progress_dialog.iscanceled(): return False
		if not self.token: return notification(32574)
		sleep(500)
		headers = {}
		headers.update({'Authorization': 'Bearer %s' % self.token})
		response = requests.get(self.base_url('v4/user'), params=params, headers=headers, timeout=timeout)
		result = response.json()['data']
		username = result['user']['username']
		set_setting('ad.account_id', str(username))
		set_setting('ad.token', self.token)
		notification('Set %s Authorization' % cls_name)
		return True

class EasyDebrid:
	def base_url(self, path):
		return 'https://easydebrid.com/api/v1/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if get_setting('ed.token'):
			if not confirm_dialog(): return
			set_setting('ed.token', '')
			set_setting('ed.account_id', '')
			clear_cache('ed_cloud', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		api_key = kodi_utils.dialog.input('EasyDebrid API Key:')
		if not api_key: return
		headers = {'Authorization': 'Bearer %s' % api_key}
		response = requests.get(self.base_url('user/details'), headers=headers, timeout=timeout)
		result = response.json()
		customer = result['id']
		set_setting('ed.account_id', str(customer))
		set_setting('ed.token', api_key)
		notification('Set %s Authorization' % cls_name)
		return True

class TorBox:
	def base_url(self, path):
		return 'https://api.torbox.app/v1/api/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if get_setting('tb.token'):
			if not confirm_dialog(): return
			set_setting('tb.token', '')
			set_setting('tb.account_id', '')
			clear_cache('tb_cloud', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		api_key = kodi_utils.dialog.input('TorBox API Key:')
		if not api_key: return
		headers = {'Authorization': 'Bearer %s' % api_key}
		response = requests.get(self.base_url('user/me'), headers=headers, timeout=timeout)
		result = response.json()
		customer = result['data']['customer']
		set_setting('tb.account_id', str(customer))
		set_setting('tb.token', api_key)
		notification('Set %s Authorization' % cls_name)
		return True

class Offcloud:
	def base_url(self, path):
		return 'https://offcloud.com/api/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if get_setting('oc.token'):
			if not confirm_dialog(): return
			set_setting('oc.token', '')
			set_setting('oc.account_id', '')
			clear_cache('oc_cloud', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		username = kodi_utils.dialog.input('Offcloud Email:')
		password = kodi_utils.dialog.input('Offcloud Password:', option=2)
		if not all((username, password)): return
		data = {'username': username, 'password': password}
		response = requests.post(self.base_url('login'), json=data, timeout=timeout)
		result = response.json()
		user_id = result.get('userId')
		if not user_id: return notification(32574)
		result = requests.post(self.base_url('key'), cookies=response.cookies, timeout=timeout).json()
		api_key = result.get('apiKey')
		if not api_key: return notification(32574)
		set_setting('oc.account_id', str(user_id))
		set_setting('oc.token', api_key)
		notification('Set %s Authorization' % cls_name)
		return True

class Trakt:
	def __init__(self):
		self.token = get_setting('trakt.token')
		self.client_id = get_setting('trakt.client_id')
		self.secret = get_setting('trakt.client_secret')

	def base_url(self, path):
		return 'https://api.trakt.tv/%s' % path

	def poll_auth(self, data):
		response = requests.post(self.base_url('oauth/device/token'), json=data, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.token = data['access_token']

	def set_auth(self):
		cls_name = self.__class__.__name__
		if self.token:
			if not confirm_dialog(): return
			data = {'token': self.token, 'client_id': self.client_id, 'client_secret': self.secret}
			response = requests.post(self.base_url('oauth/revoke'), json=data, timeout=timeout)
			set_setting('trakt_user', '')
			set_setting('trakt.token', '')
			set_setting('trakt.refresh', '')
			set_setting('trakt.expires', '')
			set_setting('trakt_indicators_active', 'false')
			set_setting('watched_indicators', '0')
			sleep(500)
			clear_cache('trakt', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		data = {'client_id': self.client_id, 'client_secret': self.secret, 'code': ''}
		response = requests.post(self.base_url('oauth/device/code'), json=data, timeout=timeout)
		result = response.json()
		data['code'] = result['device_code']
		expires_in, expires_at = result['expires_in'], result['expires_in'] + time.monotonic()
		try: qr_icon = qr_str % '&color=f00&data=%s' % quote('%s/%s' % (result['verification_url'], result['user_code']))
		except: qr_icon = ''
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon}
		detail = code_str % result['user_code'], nav2_str % result['verification_url']
		progress_dialog = _make_progress_dialog(meta=meta)
		timer = RepeatTimer(result['interval'], self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progress_dialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progress_dialog.update('[CR]'.join(lines), progress)
			sleep(1000)
		timer.cancel()
		progress_dialog.close()
		if progress_dialog.iscanceled(): return False
		if not self.token: return notification(32574)
		sleep(500)
		headers = {'trakt-api-key': self.client_id, 'trakt-api-version': '2', 'Content-Type': 'application/json'}
		headers.update({'Authorization': 'Bearer %s' % self.token})
		response = requests.get(self.base_url('users/me'), headers=headers, timeout=timeout)
		username = response.json()['username']
		expires = int(data['created_at']) + int(data['expires_in'])
		refresh, token = data['refresh_token'], data['access_token']
		set_setting('trakt_user', str(username))
		set_setting('trakt.token', token)
		set_setting('trakt.refresh', refresh)
		set_setting('trakt.expires', str(expires))
		set_setting('trakt_indicators_active', 'true')
		set_setting('watched_indicators', '1')
		notification('Set %s Authorization' % cls_name)
		sleep(500)
		clear_cache('trakt', silent=True)
		return True

class MDBList:
	def base_url(self, path):
		return 'https://api.mdblist.com/%s' % path

	def set_auth(self):
		cls_name = self.__class__.__name__
		if get_setting('mdblist.token'):
			if not confirm_dialog(): return
			set_setting('mdblist_user', '')
			set_setting('mdblist.token', '')
			clear_cache('mdblist', silent=True)
			return notification('Removed %s Authorization' % cls_name)

		api_key = kodi_utils.dialog.input('MDBList API Key:')
		if not api_key: return
		params = {'apikey': api_key}
		response = requests.get(self.base_url('user'), params=params, timeout=timeout)
		result = response.json()
		user_id, username = result['user_id'], result['username']
		set_setting('mdblist_user', str(username))
		set_setting('mdblist.token', api_key)
		notification('Set %s Authorization' % cls_name)
		return True

class TMDbList:
	def __init__(self):
		self.read = get_setting('tmdb_read_token')
		self.token = get_setting('tmdb.token')
		self.headers = {'Authorization': 'Bearer %s' % self.read}

	def base_url(self, path):
		return 'https://api.themoviedb.org/%s' % path

	def poll_auth(self, data):
		response = requests.post(self.base_url('4/auth/access_token'), json=data, headers=self.headers, timeout=timeout)
		if not response.ok: return
		data.update(response.json())
		self.token = data['access_token']

	def set_auth(self):
		cls_name = self.__class__.__name__
		if self.token:
			if not confirm_dialog(): return
			data = {'access_token': self.token}
			response = requests.delete(self.base_url('4/auth/access_token'), json=data, headers=self.headers, timeout=timeout)
			result = response.json()
			if not result['success']: return notification(32574)
			set_setting('tmdb.account_id', '')
			set_setting('tmdb.token', '')
			clear_cache('tmdblist', silent=True)
			notification('Removed %s Authorization' % cls_name)
			session_id = get_setting('tmdb.session_id')
			data = {'session_id': session_id}
			response = requests.delete(self.base_url('3/authentication/session'), json=data, headers=self.headers, timeout=timeout)
			result = response.json()
			if not result['success']: return
			set_setting('tmdb.session_account_id', '')
			set_setting('tmdb.session_id', '')
			set_setting('tmdb.username', '')
			return

		response = requests.post(self.base_url('4/auth/request_token'), headers=self.headers, timeout=timeout)
		result = response.json()
		if not result['success']: return
		data = {'request_token': result['request_token']}
		expires_in, expires_at = 600, 600 + time.monotonic()
		url = 'https://www.themoviedb.org/auth/access?request_token=%s' % result['request_token']
		tiny_url = 'http://tinyurl.com/api-create.php'
		try: tiny_url = requests.get(tiny_url, params={'url': url}, timeout=timeout).text
		except: tiny_url = url
		qr_icon = qr_str % '&data=%s' % quote(tiny_url)
		kodi_utils.logger('tmdblist', '%s\n%s' % (tiny_url, url))
		meta = {**dict.fromkeys(meta_keys.split(), ''), 'poster': qr_icon}
		detail = nav2_str % tiny_url, ''
		progress_dialog = _make_progress_dialog(meta=meta)
		timer = RepeatTimer(5, self.poll_auth, args=(data,))
		timer.start()
		for i in range(1, expires_in + 1):
			if self.token or progress_dialog.iscanceled(): break
			lines = await_str % divmod(expires_at - time.monotonic(), 60), *detail
			progress = 100 - int(100 * i / expires_in)
			progress_dialog.update('[CR]'.join(lines), progress)
			sleep(1000)
		timer.cancel()
		progress_dialog.close()
		if progress_dialog.iscanceled(): return False
		if not self.token: return notification(32574)
		account_id, access_token = str(data['account_id']), str(data['access_token'])
		set_setting('tmdb.account_id', account_id)
		set_setting('tmdb.token', access_token)
		notification('Set %s Authorization' % cls_name)
		sleep(500)
		if not self.token and not get_setting('tmdb.token'): return
		access_token = self.token or get_setting('tmdb.token')
		data = {'access_token': access_token}
		response = requests.post(self.base_url('3/authentication/session/convert/4'), json=data, headers=self.headers, timeout=timeout)
		result = response.json()
		if not result['success']: return
		session_id = result['session_id']
		params = {'session_id': session_id}
		response = requests.get(self.base_url('3/account'), params=params, headers=self.headers, timeout=timeout)
		result = response.json()
		if not 'id' in result: return
		username, session_account_id = str(result['username']), str(result['id'])
		set_setting('tmdb.username', username)
		set_setting('tmdb.session_id', session_id)
		set_setting('tmdb.session_account_id', session_account_id)
		return True

