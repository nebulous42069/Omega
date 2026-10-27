# -*- coding: utf-8 -*-
"""
    ReAuthorize - Last.fm Sync
    Pushes Last.fm credentials to service.scrobbler.lastfm when installed.

    service.scrobbler.lastfm (4.0.3, the one in Kodi's repo) uses:
    - lastfmuser : username
    - lastfmpass : password
    - lastfmkey  : session key, which it makes ITSELF from the two above with its own built-in
                   key (lib/utils.py read_settings, auth.getMobileSession), and again whenever the
                   username or password change; with a username and password but no key it signs in
                   at its next start. It scrobbles only with all three, and shows Last.fm's own
                   error when a sign-in is refused.

    1.4.1: ReAuthorize keeps the username and password (no Last.fm API key needed anywhere) and
    sends those; a changed pair also blanks lastfmkey so the Scrobbler signs in afresh. A sign-in
    from before 1.4.1 (a session key made with the user's own API key, no password) is still sent
    as it was. A wipe (control.wiping()) blanks all three.
"""

import time

import xbmc
import xbmcaddon
import xbmcvfs

from libs.common import var
from reauthorize.modules import control
from reauthorize.modules.control import accountmgr

LASTFM_ADDON_ID = 'service.scrobbler.lastfm'
SIGN_IN_IDS = ('lastfmuser', 'lastfmpass', 'lastfmkey')



from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
def installed():
    return xbmcvfs.exists('special://home/addons/%s/' % LASTFM_ADDON_ID)


def pick_up_from_scrobbler():
    """ReAuthorize holds no Last.fm sign-in and the Scrobbler has a username and password: take them. True if taken."""
    if accountmgr.getSetting('lastfm.password') or accountmgr.getSetting('lastfm.session.key') or not installed():
        return False
    try:
        scrobbler = xbmcaddon.Addon(LASTFM_ADDON_ID)
        user, pwd = scrobbler.getSetting('lastfmuser'), scrobbler.getSetting('lastfmpass')
    except Exception:
        sync_support.failed()
        return False
    if not (user and pwd):
        return False
    accountmgr.setSetting('lastfm.username', user)
    accountmgr.setSetting('lastfm.password', pwd)
    return True


def scrobbler_session():
    """The session key the Scrobbler holds now ('' if none or not installed)."""
    try:
        return xbmcaddon.Addon(LASTFM_ADDON_ID).getSetting('lastfmkey') if installed() else ''
    except Exception:
        sync_support.failed()
        return ''


def wait_for_session(seconds=15):
    """After a new username/password: True once the Scrobbler holds a session key again."""
    end = time.time() + seconds
    while time.time() < end:
        if scrobbler_session():
            return True
        if control.monitor.waitForAbort(1):
            break
    return bool(scrobbler_session())


def clear_scrobbler(user=None, pwd=None):
    """Sign the Scrobbler out. With user/pwd given, only when it holds that same sign-in. True if cleared."""
    if not installed():
        return False
    try:
        scrobbler = xbmcaddon.Addon(LASTFM_ADDON_ID)
        if user is not None and (scrobbler.getSetting('lastfmuser') != user or scrobbler.getSetting('lastfmpass') != pwd):
            return False
        changed = False
        for sid in SIGN_IN_IDS:
            if scrobbler.getSetting(sid):
                scrobbler.setSetting(sid, '')
                changed = True
        return changed
    except Exception:
        sync_support.failed()
        return False


class Auth:

    def lastfm_auth(self):
        if not installed():
            return
        if control.wiping():
            clear_scrobbler()
            return
        pick_up_from_scrobbler()
        username = accountmgr.getSetting('lastfm.username')
        password = accountmgr.getSetting('lastfm.password')
        session_key = accountmgr.getSetting('lastfm.session.key')
        if not (password or session_key):
            return
        try:
            lastfm = xbmcaddon.Addon(LASTFM_ADDON_ID)
            if password:
                if lastfm.getSetting('lastfmuser') != username or lastfm.getSetting('lastfmpass') != password:
                    lastfm.setSetting('lastfmkey', '')          # it signs in afresh with the new pair
                    lastfm.setSetting('lastfmuser', username)
                    lastfm.setSetting('lastfmpass', password)
            else:                                               # a sign-in from before 1.4.1
                if username:
                    lastfm.setSetting('lastfmuser', username)
                lastfm.setSetting('lastfmkey', session_key)
            # Keep scrobbling toggles enabled when syncing credentials.
        except Exception:
            sync_support.failed()
            xbmc.log('%s: Last.fm sync failed!' % var.amgr, xbmc.LOGINFO)
