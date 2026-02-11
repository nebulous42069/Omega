# -*- coding: utf-8 -*-
import xbmc
import requests
from debridmgr.modules import control
from debridmgr.modules import log_utils

base_url_v4 = 'https://api.alldebrid.com/v4/'
base_url_v41 = 'https://api.alldebrid.com/v4.1/'
user_agent = 'Account%20Manager%20for%20Kodi'

ad_icon = control.joinPath(control.artPath(), 'alldebrid.png')

class AllDebrid:
    name = "AllDebrid"
    def __init__(self):
        self.token = control.setting('alldebrid.token')
        self.timeout = 15.0
        self.pin = None
        self.check = None

    def _headers(self):
        return {"User-Agent": user_agent,"Authorization": f"Bearer {self.token}" if self.token else ""}

    def _get(self, endpoint, params=None):
        if not self.token:
            return None

        url = base_url_v4 + endpoint

        params = params or {}
        params["agent"] = user_agent

        try:
            r = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            result = r.json()
            if result.get("status") == "success":
                return result.get("data")
        except requests.exceptions.ConnectionError:
            control.notification(title='default', message=40073, icon=ad_icon)
        except Exception:
            log_utils.error()

        return None

    def auth_loop(self):
        if not self.pin or not self.check:
            self.token = "failed"
            return

        control.sleep(5000)

        try:
            r = requests.post(base_url_v4 + "pin/check",data={"pin": self.pin,"check": self.check,},timeout=self.timeout,)
            result = r.json()
        except Exception:
            log_utils.error()
            self.token = "failed"
            return

        status = result.get("status")
        
        if status != "success":
            self.token = "failed"
            return

        data = result.get("data", {})

        if not data.get("activated"):
            return

        apikey = data.get("apikey")
        if not apikey:
            self.token = "failed"
            return

        try:
            control.progressDialog.close()
        except Exception:
            pass

        self.token = str(apikey)
        control.setSetting("alldebrid.token", self.token)

    def auth(self):
        self.token = ""
        self.pin = None
        self.check = None

        try:
            r = requests.get(base_url_v41 + "pin/get",timeout=self.timeout,)
            payload = r.json()
        except Exception:
            log_utils.error()
            control.notification(title='default', message=40021, icon=ad_icon)
            return

        if payload.get("status") != "success":
            control.notification(title='default', message=40021, icon=ad_icon)
            return

        data = payload.get("data", {})
        self.pin = data.get("pin")
        self.check = data.get("check")

        if not self.pin or not self.check:
            control.notification(title='default', message=40021, icon=ad_icon)
            return

        try:
            control.progressDialog.create(control.lang(40056))
        except Exception:
            control.progressDialog.create("AllDebrid Authorization")

        control.progressDialog.update(-1,control.progress_line % (control.lang(32513) % 'https://alldebrid.com/pin/',control.lang(32514) % self.pin,'',),)

        while not self.token:
            if control.progressDialog.iscanceled():
                try:
                    control.progressDialog.close()
                except Exception:
                    pass
                return

            self.auth_loop()

        if self.token in ("", None, "failed"):
            return

        account = self.account_info()
        if account and "user" in account:
            username = account["user"].get("username", "")
            control.setSetting("alldebrid.username", str(username))

        control.notification_ad(title=40059, message=40081, icon=ad_icon)

    def revoke(self):
        control.setSetting("alldebrid.username", "")
        control.setSetting("alldebrid.token", "")

    def account_info(self):
        return self._get("user")

    def account_info_to_dialog(self):
        from datetime import datetime

        try:
            data = self.account_info()
            if not data or "user" not in data:
                return

            user = data["user"]

            username = user.get("username", "")
            email = user.get("email", "")
            status = "Premium" if user.get("isPremium") else "Not Active"

            expires = datetime.fromtimestamp(user["premiumUntil"])
            days_remaining = (expires - datetime.today()).days

            items = [
                control.lang(40036) % username,
                control.lang(40035) % email,
                control.lang(40037) % status,
                control.lang(40041) % expires,
                control.lang(40042) % days_remaining,
            ]

            return control.selectDialog(items, "AllDebrid")

        except Exception:
            log_utils.error()
            return
