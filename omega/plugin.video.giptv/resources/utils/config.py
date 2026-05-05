# -*- coding: utf-8 -*-
"""
config.py

Central configuration module for GIPTV.

- Non-credential flags live here
- Credentials are ALWAYS read from Kodi settings.xml
- This module syncs credentials into xtream_api.STATE
"""

import xbmc
import xbmcaddon

import resources.utils.settings as settings
import resources.utils.giptv as giptv
from resources.utils.xtream import STATE
from urllib.parse import urlparse, urlunparse

ADDON = xbmcaddon.Addon()


def setup_api_config():
    """
    Load credentials from Kodi settings.xml and populate STATE.
    """
    try:
        server, username, password = settings.get_api_credentials(ADDON)

        if not server or not username or not password:
            return False

        if not server.startswith(("http://", "https://")):
            giptv.notification(
                "Configuration Error",
                "Please configure your IPTV credentials in the add-on settings.",
                icon="ERROR",
            )
            xbmc.Monitor().waitForAbort(5)
            giptv.open_settings()
            return False

        if "@" in server:
            giptv.log(
                msg="WARNING: credentials detected in server URL — sanitizing",
                level=xbmc.LOGWARNING,
            )

        parsed = urlparse(server)

        # Remove accidental username/password in server field
        netloc = parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"

        clean_server = urlunparse((parsed.scheme, netloc, "", "", "", ""))

        STATE.server = clean_server.rstrip("/")
        STATE.username = username
        STATE.password = password

        giptv.log(f"Xtream credentials loaded: {STATE.server}", xbmc.LOGINFO)
        return True

    except Exception as e:
        giptv.notification(
            ADDON.getAddonInfo("name"),
            f"Configuration Setup Error: {e}",
            icon="ERROR",
        )
        giptv.open_settings()
        return False


def ensure_api_ready():
    """
    Ensure STATE is populated.
    Safe to call from any module at any time.
    """
    if not STATE.is_ready():
        return setup_api_config()
    return True
