# -*- coding: utf-8 -*-
import os
import json
import requests
import xbmc
import xbmcaddon
import xbmcgui

from requests.adapters import HTTPAdapter
from debridmgr.modules import control

offcloud_icon = control.joinPath(control.artPath(), 'offcloud.png')
BASE_URL = 'https://offcloud.com/api'
session = requests.Session()
session.mount(BASE_URL, HTTPAdapter(max_retries=1, pool_maxsize=20))

class Offcloud:
    def auth(self):

        existing_key = control.setting('offcloud.token')
        if existing_key:
            control.notification(message="Offcloud is already authorized!", icon=offcloud_icon)
            return

        username = xbmcgui.Dialog().input('Enter Offcloud Account Email:')
        if not username:
            control.notification(message="Offcloud authorization failed!", icon=offcloud_icon)
            return

        password = xbmcgui.Dialog().input('Enter Offcloud Password:',option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password:
            control.notification(message="Offcloud authorization failed!", icon=offcloud_icon)
            return

        # ---------- LOGIN ----------
        try:
            # Offcloud sometimes requires JSON instead of form
            r = session.post(f'{BASE_URL}/login',json={'username': username, 'password': password},timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            control.notification(message="Offcloud authorization failed! Login request error.", icon=offcloud_icon)
            return

        # Offcloud sometimes returns success:false instead of error status
        if data.get('success') is False or data.get('error'):
            control.notification(message="Offcloud authorization failed! Invalid credentials.", icon=offcloud_icon)
            return

        # accept multiple possible user id fields
        user_id = (data.get('userId') or data.get('user_id') or data.get('id') or (data.get('user') or {}).get('id'))

        if not user_id:
            control.notification(message="Offcloud authorization failed! Unexpected login response.", icon=offcloud_icon)
            return

        # ---------- GET API KEY ----------
        try:
            r = session.post(f'{BASE_URL}/key',json={'userId': user_id},timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            control.notification(message="Offcloud authorization failed! API key request error.", icon=offcloud_icon)
            return

        api_key = data.get('apiKey') or data.get('apikey') or data.get('key')

        if not api_key:
            control.notification(message="Offcloud authorization failed! API key not returned.", icon=offcloud_icon)
            return

        # ---------- SAVE ONLY ON FULL SUCCESS ----------
        control.setSetting('offcloud.user', username)
        control.setSetting('offcloud.userid', str(user_id))
        control.setSetting('offcloud.token', api_key)
        control.setSetting('offcloud.pass', password)

        control.notification_offcloud(title='Offcloud',message='Offcloud Successfully Authorized',icon=offcloud_icon)

    def revoke(self):
        if not control.okDialog(title='Offcloud', message='Revoke Offcloud Authorization?'):
            return

        control.setSetting('offcloud.user', '')
        control.setSetting('offcloud.pass', '')
        control.setSetting('offcloud.userid', '')
        control.setSetting('offcloud.token', '')

        control.notification(message="Offcloud Authorization Revoked", icon=offcloud_icon)

