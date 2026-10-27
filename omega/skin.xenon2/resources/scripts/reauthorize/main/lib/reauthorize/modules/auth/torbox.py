# -*- coding: utf-8 -*-
"""
	Account Manager
"""

import os.path
import xbmc
import xbmcaddon
import xbmcgui
import requests
from datetime import datetime, timezone
from libs.common import var
from reauthorize.modules import control
from reauthorize.modules import qr
from reauthorize.windows import device_auth

addon_id = 'script.module.reauthorize'
addon = xbmcaddon.Addon(addon_id)
joinPath = os.path.join
api_key = control.setting('torbox.token')
torbox_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'torbox.png')

DEVICE_START_URL = 'https://api.torbox.app/v1/api/user/auth/device/start'
DEVICE_TOKEN_URL = 'https://api.torbox.app/v1/api/user/auth/device/token'

class Torbox:

        def auth(self):
                choice = xbmcgui.Dialog().select('Authorize TorBox', ['Enter API Key', 'Scan QR / Device Code'])
                if choice < 0:
                        return
                if choice == 0:
                        return self.auth_manual()
                return self.auth_device()

        def auth_manual(self):
                api = xbmcgui.Dialog().input('Enter TorBox API Key:')
                if api == '':
                        control.notification(message='TorBox authorization failed!', icon=torbox_icon)
                        return
                control.setSetting('torbox.token', api)
                control.setSetting('torbox.acct_id', api)
                control.notification(title='TorBox', message='TorBox Credentials saved', icon=torbox_icon)

        def auth_device(self):
                try:
                        resp = requests.get(DEVICE_START_URL, timeout=15).json()
                except Exception:
                        control.notification(message='TorBox authorization failed!', icon=torbox_icon)
                        return
                if not resp.get('success'):
                        control.notification(message='TorBox authorization failed!', icon=torbox_icon)
                        return

                data = resp.get('data') or {}
                device_code = data.get('device_code')
                user_code = data.get('code')
                interval = int(data.get('interval', 5) or 5)
                verification_url = data.get('friendly_verification_url') or 'https://torbox.app/oauth/device'

                expires_in = 600
                expires_at = data.get('expires_at')
                if expires_at:
                        try:
                                exp = datetime.strptime(expires_at[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
                                expires_in = max(60, int((exp - datetime.now(timezone.utc)).total_seconds()))
                        except Exception:
                                pass

                if not device_code or not user_code:
                        control.notification(message='TorBox authorization failed!', icon=torbox_icon)
                        return

                result = {'token': None}

                def poll_once():
                        try:
                                r = requests.post(DEVICE_TOKEN_URL, json={'device_code': device_code}, timeout=15).json()
                        except Exception:
                                return None
                        if r.get('success'):
                                token_data = r.get('data') or {}
                                token = token_data.get('access_token') or token_data.get('token')
                                if token:
                                        result['token'] = token
                                        return True
                                return None
                        err = (r.get('error') or '').upper()
                        if err and 'PENDING' not in err and 'NOT_USED' not in err and 'SLOW_DOWN' not in err:
                                return False
                        return None

                device_auth.run('TorBox', qr.qr_image_url(verification_url), verification_url, user_code,
                                                 poll_once, interval=interval, expires_in=expires_in)
                if not result['token']:
                        return
                control.setSetting('torbox.token', result['token'])
                control.setSetting('torbox.acct_id', result['token'])
                control.notification(title='TorBox', message='TorBox Credentials saved', icon=torbox_icon)

        def revoke(self):
                if not control.confirm_remove('TorBox'):
                        return
                control.setSetting('torbox.token', '')
                control.setSetting('torbox.acct_id', '')
                control.notification(message="TorBox Authorization Revoked", icon=torbox_icon)


