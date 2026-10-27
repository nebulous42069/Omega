# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon
import json
import urllib.parse
import urllib.request
from reauthorize.modules import control
from reauthorize.modules import own_settings  # one read or write of our settings at a time

mdb_icon = control.joinPath(control.artPath(), 'mdblist.png')
ADDON_ID = "script.module.reauthorize"
ADDON_NAME = "ReAuthorize"
API_BASE = "https://api.mdblist.com"


class MDBListAuth:
    def __init__(self):
        self.addon = own_settings.addon()

    def _request_json(self, url, timeout=10):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Kodi ReAuthorize", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read().decode("utf-8", "replace")
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        return status, data, body

    def fetch_user(self, api_key):
        api_key = (api_key or "").strip()
        if not api_key:
            return False, "Missing API key", None
        url = f"{API_BASE}/user?apikey={urllib.parse.quote(api_key)}"
        try:
            status, data, raw = self._request_json(url)
        except Exception as e:
            xbmc.log(f"{ADDON_NAME}: MDBList request failed - {e}", xbmc.LOGERROR)
            return False, f"Request failed: {e}", None
        if status != 200:
            message = None
            if isinstance(data, dict):
                message = data.get("error") or data.get("message") or data.get("detail")
            if not message:
                message = f"HTTP {status}"
            xbmc.log(f"{ADDON_NAME}: MDBList auth failed - status={status} response={raw}", xbmc.LOGERROR)
            return False, message, None
        username = ""
        if isinstance(data, dict):
            username = (data.get("username") or "").strip()
        if not username:
            xbmc.log(f"{ADDON_NAME}: MDBList auth succeeded but no username returned: {raw}", xbmc.LOGERROR)
            return False, "Username not returned by MDBList", None
        return True, "OK", username

    def authorize(self, api_key=None):
        if not api_key:
            keyboard = xbmc.Keyboard(control.setting('mdb.api.key') or '', "Enter MDBList API Key")
            keyboard.doModal()
            if not keyboard.isConfirmed():
                return False
            api_key = keyboard.getText()
        api_key = (api_key or "").strip()
        if not api_key:
            xbmcgui.Dialog().notification(ADDON_NAME, "MDBList API key is empty", mdb_icon, 3000)
            return False
        ok, msg, username = self.fetch_user(api_key)
        if not ok:
            xbmcgui.Dialog().notification(ADDON_NAME, f"MDBList: {msg}", mdb_icon, 3000)
            return False
        control.setSetting("mdb.api.key", api_key)
        control.setSetting("mdb.username", username)
        xbmc.log(f"{ADDON_NAME}: MDBList authorized - username={username}", xbmc.LOGINFO)
        control.notification(title='MDBList', message='Successfully Authorized!', icon=mdb_icon)
        return True

    def revoke(self):
        control.setSetting("mdb.api.key", "")
        control.setSetting("mdb.username", "")
        control.notification(title='MDBList', message='Authorization Removed', icon=mdb_icon)
