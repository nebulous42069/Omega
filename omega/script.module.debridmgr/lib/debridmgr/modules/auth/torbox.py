# -*- coding: utf-8 -*-
import xbmcgui
import os
import json
import urllib.request
import urllib.error

from debridmgr.modules import control

torbox_icon = control.joinPath(control.artPath(), 'torbox.png')
API_BASE = "https://api.torbox.app"
VALIDATE_PATH = "/v1/api/user/me"   # Or another valid authenticated route per the API docs

class Torbox:
    def auth(self):
        api = xbmcgui.Dialog().input('Enter TorBox API Key:')
        api = api.strip()

        if not api:
            control.notification(message="TorBox authorization failed!", icon=torbox_icon)
            return

        url = f"{API_BASE}{VALIDATE_PATH}"
        req = urllib.request.Request(url)
        # Send the token as a header (Bearer or API key)
        req.add_header("Authorization", f"Bearer {api}")

        try:
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read().decode("utf-8"))

            # If success, store key
            control.setSetting("torbox.token", api)
            control.notification_torbox(
                title="TorBox",
                message="TorBox Successfully Authorized",
                icon=torbox_icon
            )

        except urllib.error.HTTPError as e:
            if e.code == 401:
                control.notification(message="TorBox Authorization Failed (Invalid API Key)", icon=torbox_icon)
            elif e.code == 404:
                control.notification(message="TorBox Authorization Failed (Bad Endpoint). Check VALIDATE_PATH", icon=torbox_icon)
            else:
                control.notification(message=f"TorBox Authorization Failed (HTTP {e.code})", icon=torbox_icon)

        except Exception as e:
            control.notification(message=f"TorBox Authorization Failed ({str(e)})", icon=torbox_icon)

    def revoke(self):
        if not control.okDialog("TorBox", "Revoke TorBox Authorization?"):
            return
        control.setSetting("torbox.token", "")
        control.notification("TorBox Authorization Revoked", icon=torbox_icon)



