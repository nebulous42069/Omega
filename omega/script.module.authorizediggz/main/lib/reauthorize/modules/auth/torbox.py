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
from urllib.parse import urlsplit
from libs.common import var
from reauthorize.modules import control
from reauthorize.modules import qr
from reauthorize.windows import device_auth

addon_id = 'script.module.authorizediggz'
addon = xbmcaddon.Addon(addon_id)
joinPath = os.path.join
api_key = control.setting('torbox.token')
torbox_icon = joinPath(os.path.join(addon.getAddonInfo('path'), 'resources', 'icons'), 'torbox.png')

VERIFICATION_URL = 'https://torbox.app/oauth/device'
APP_NAME = 'Diggz Account Manager'
DEVICE_START_URL = 'https://api.torbox.app/v1/api/user/auth/device/start'
DEVICE_TOKEN_URL = 'https://api.torbox.app/v1/api/user/auth/device/token'

def _torbox_url(value):
        """Use only HTTPS verification links from TorBox itself."""
        if not isinstance(value, str):
                return None
        try:
                parts = urlsplit(value)
                if (parts.scheme == 'https' and parts.hostname in ('torbox.app', 'www.torbox.app')
                        and parts.port in (None, 443) and not parts.username and not parts.password):
                        return value
        except ValueError:
                pass
        return None


def _timing(data):
        try:
                interval = max(1, int(data.get('interval') or 5))
        except (TypeError, ValueError, OverflowError):
                interval = 5
        try:
                expires_in = int(data.get('expires_in') or 600)
        except (TypeError, ValueError, OverflowError):
                expires_in = 600
        if data.get('expires_at'):
                try:
                        exp = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
                        if exp.tzinfo is None:
                                exp = exp.replace(tzinfo=timezone.utc)
                        expires_in = int((exp - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, AttributeError, OverflowError):
                        pass
        return interval, max(0, expires_in)


class Torbox:

        def auth(self):
                choice = xbmcgui.Dialog().select('Authorize TorBox', ['Enter API Key', 'Scan QR / Device Code'])
                if choice < 0:
                        return
                if choice == 0:
                        return self.auth_manual()
                return self.auth_device()

        def auth_manual(self):
                api = xbmcgui.Dialog().input('Enter TorBox API Key:').strip()
                if api == '':
                        control.notification(message='TorBox authorization failed!', icon=torbox_icon)
                        return
                control.setSetting('torbox.token', api)
                control.setSetting('torbox.acct_id', api)
                control.setSetting('torbox.enabled', 'true')
                control.notification(title='TorBox', message='TorBox Credentials saved', icon=torbox_icon)

        def auth_device(self):
                try:
                        response = requests.get(DEVICE_START_URL, params={'app': APP_NAME}, timeout=15)
                        resp = response.json()
                        if not isinstance(resp, dict) or not resp.get('success'):
                                raise ValueError('Device initiation rejected')
                        data = resp.get('data')
                        if not isinstance(data, dict):
                                raise ValueError('Missing device authorization data')
                except Exception:
                        control.notification(message='TorBox could not start device authorization. Please try again.', icon=torbox_icon)
                        return

                device_code = data.get('device_code')
                user_code = data.get('code')
                interval, expires_in = _timing(data)
                # The old friendly_verification_url may point to a retired page.
                # Use the documented URL, otherwise the current canonical page.
                verification_url = _torbox_url(data.get('verification_url')) or VERIFICATION_URL
                qr_url = _torbox_url(data.get('verification_url_complete')) or verification_url

                if not device_code or not user_code or expires_in <= 0:
                        control.notification(message='TorBox device code missing or expired. Please try again.', icon=torbox_icon)
                        return

                result = {'token': None}

                def poll_once():
                        try:
                                response = requests.post(DEVICE_TOKEN_URL, json={'device_code': device_code}, timeout=15)
                                if response.status_code == 429:
                                        return 'slow_down'
                                if response.status_code >= 500:
                                        return None
                                r = response.json()
                        except Exception:
                                return None
                        if not isinstance(r, dict):
                                return None
                        if r.get('success'):
                                token_data = r.get('data') or {}
                                if isinstance(token_data, dict):
                                        token = token_data.get('access_token') or token_data.get('token')
                                elif isinstance(token_data, str):
                                        token = token_data
                                else:
                                        token = None
                                if isinstance(token, str) and token.strip():
                                        result['token'] = token.strip()
                                        return True
                                return False
                        err = str(r.get('error') or '').upper()
                        if err in ('ITEM_NOT_FOUND', 'EXPIRED_TOKEN', 'DEVICE_CODE_EXPIRED'):
                                return 'expired_token'
                        if err == 'SLOW_DOWN':
                                return 'slow_down'
                        if err in ('DEVICE_CODE_NOT_USED', 'AUTHORIZATION_PENDING', 'PENDING'):
                                return None
                        if err or response.status_code >= 400:
                                return False
                        return None

                # Display only the short manual-entry address. Render any
                # complete URL locally, never via the external QR service.
                # If local rendering fails, the fallback encodes ONLY the
                # public page, so the user can enter the code manually.
                approved = device_auth.run('TorBox', qr.qr_image_url(VERIFICATION_URL),
                                           VERIFICATION_URL, str(user_code), poll_once,
                                           interval=interval, expires_in=expires_in,
                                           local_qr_data=qr_url)
                if not approved or not result['token']:
                        return
                control.setSetting('torbox.token', result['token'])
                control.setSetting('torbox.acct_id', result['token'])
                control.setSetting('torbox.enabled', 'true')
                control.notification(title='TorBox', message='TorBox Credentials saved', icon=torbox_icon)

        def revoke(self):
                if not control.confirm_remove('TorBox'):
                        return
                control.setSetting('torbox.token', '')
                control.setSetting('torbox.acct_id', '')
                control.setSetting('torbox.enabled', 'false')
                control.notification(message="TorBox Authorization Revoked", icon=torbox_icon)


