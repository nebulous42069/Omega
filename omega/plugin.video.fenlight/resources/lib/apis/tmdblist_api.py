# -*- coding: utf-8 -*-
import requests
from modules.kodi_utils import progress_dialog, notification, sleep
from caches.settings_cache import get_setting, set_setting
from modules.utils import copy2clip
from modules.kodi_utils import logger

class TMDbListAPI:
	def __init__(self):
		self.requests = requests
		self.read_access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiMzcwYjYwNDQ3NzM3NzYyY2EzODQ1N2JkNzc1NzliMyIsIm5iZiI6MTY1MDIzNTExOS4wOSwic3ViIjoiNjI1Yzk2ZWZiYjI2MDIxMT'\
								'gzNTQ0MTZhIiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.8uevSMakSrdZb1t0ze4OIxq6PoL4N6DZN4VVkKUCayg'
		self.headers = {'Authorization': 'Bearer %s' % self.read_access_token}
		self.account_id = get_setting('tmdb.account_id')
	
	def auth(self):
		p_dialog_insert = ''
		data = self.requests.post('https://api.themoviedb.org/4/auth/request_token', headers=self.headers, timeout=5).json()
		if not 'success' in data: return notification('Failed to Auth Account')
		request_token = data['request_token']
		token_url = 'https://www.themoviedb.org/auth/access?request_token=%s' % request_token
		try:
			url = 'http://tinyurl.com/api-create.php'
			response = requests.get(url, params={'url': token_url})
			status = response.status_code
			if status == 200:
					short_url = response.text
					p_dialog_insert = '[CR]OR visit this URL: [B]%s[/B]' % short_url
					try: copy2clip(short_url)
					except: pass
			else: pass
		except: pass
		qrcode = 'https://api.qrserver.com/v1/create-qr-code/?size=256x256&qzone=1&data=%s' % self.requests.utils.quote(token_url)
		progressDialog = progress_dialog(heading='TMDb Account Authorization', icon=qrcode)
		progressDialog.update('Preparing QR Code[CR]Please Wait....', 0)
		sleep(2000)
		count, success = 72, None
		while not progressDialog.iscanceled() and count >= 0 and success == None:
			try:
				count -= 1
				response = self.requests.post('https://api.themoviedb.org/4/auth/access_token', json={'request_token': request_token}, headers=self.headers, timeout=5).json()
				if response.get('success') and response.get('access_token'): success = True
				progressDialog.update('1. Please Scan the QR Code%s[CR]3. Confirm Access to your TMDb Account' % p_dialog_insert, count)
				sleep(2500)
			except: success = False
		progressDialog.close()
		if success:
			set_setting('tmdb.token', response['access_token'])
			set_setting('tmdb.account_id', response['account_id'])
			notice = 'Success'
		else: notice = 'Failed'
		notification(notice)
	
	def revoke(self):
		data = self.requests.delete('https://api.themoviedb.org/4/auth/access_token', json={'access_token': get_setting('fenlight.tmdb.token')}, headers=self.headers, timeout=5).json()
		if not 'success' in data: notice = 'Failed to Revoke Account Auth'
		else:
			notice = 'Success Auth Revoke'
			set_setting('tmdb.token', 'empty_setting')
			set_setting('tmdb.account_id', 'empty_setting')
		return notification(notice)

	def get_user_lists(self):
		url = 'https://api.themoviedb.org/4/account/%s/lists' % self.account_id
		data = self.requests.get(url, headers=self.headers).json()
		return data

	def get_list_details(self, list_id, page_no=1):
		url = 'https://api.themoviedb.org/4/list/%s?page=%s' % (list_id, page_no)
		data = self.requests.get(url, headers=self.headers).json()
		return data

tmdb_list_api = TMDbListAPI()