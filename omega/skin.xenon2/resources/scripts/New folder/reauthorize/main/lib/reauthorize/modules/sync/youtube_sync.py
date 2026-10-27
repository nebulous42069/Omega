# -*- coding: utf-8 -*-
"""
    ReAuthorize - YouTube for Kodi Sync

    Pushes saved YouTube API credentials to plugin.video.youtube settings.
    YouTube stores its own api_keys.json by syncing from its settings on startup.

    It also carries the YouTube sign-in itself. The API keys only identify the
    app; seeing your own subscriptions, history and playlists needs a sign-in to
    your Google account, and YouTube for Kodi asks for it several times in a row
    (one device code per part of the account it links). All of it lands in one
    file, access_manager.json, so a build install wipes it and the user has to
    sit through every prompt again. Keeping a copy means they do not.

    The tokens belong to the API keys they were issued against, and ReAuthorize
    restores those keys alongside them, so a restored sign-in keeps working.
"""

import json
import os
import re
import time

import xbmc
import xbmcaddon
import xbmcvfs

ACCOUNTMGR_ID = 'script.module.reauthorize'
YT_ADDON_ID   = 'plugin.video.youtube'

# Same ids on both sides: ReAuthorize stores them under the names YouTube uses.
API_KEYS    = ('youtube.api.key', 'youtube.api.id', 'youtube.api.secret')

TOKENS_KEY  = 'youtube.tokens'
TOKENS_FILE = 'special://profile/addon_data/%s/access_manager.json' % YT_ADDON_ID

# The server refuses a payload over 50KB, and a sign-in file is normally 1-3KB.
# Anything wildly bigger is not what we think it is, so leave it alone.
MAX_TOKENS_BYTES = 32768


def _log(message):
    xbmc.log('[ReAuthorize YouTube] %s' % message, xbmc.LOGINFO)


# A Google client ID: '<digits>-<letters and digits>.apps.googleusercontent.com'.
_CLIENT_ID = re.compile(r'[0-9]+-[0-9a-z]+\.apps\.googleusercontent\.com', re.I)


def clean_value(key, value):
    """
    What the user meant to paste. People copy more than the field: found 2026-10-01, a
    364-character Client ID holding part of Google's client file and ending in '...certs',
    which made YouTube's second sign-in fail ('The OAuth client was not found'). For the
    Client ID keep only the ID itself; for every key drop spaces, quotes and line breaks
    around it. Anything that does not look like an ID is left as typed, minus that padding.
    """
    value = (value or '').strip().strip('"\',;').strip()
    if key == 'youtube.api.id':
        found = _CLIENT_ID.search(value)
        if found:
            return found.group(0)
    return value


def _installed():
    base = xbmcvfs.translatePath('special://home/addons/').replace('\\', '/')
    return xbmcvfs.exists(base + YT_ADDON_ID + '/')


def _signed_in(text):
    """True if this access_manager.json actually holds a usable sign-in."""
    try:
        users = (json.loads(text).get('access_manager') or {}).get('users') or {}
    except Exception:
        return False
    return any(isinstance(u, dict) and u.get('refresh_token') for u in users.values())


def _read_tokens_file():
    path = xbmcvfs.translatePath(TOKENS_FILE)
    if not xbmcvfs.exists(path):
        return ''
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        _log('could not read the sign-in file: %s' % e)
        return ''


def is_installed():
    return _installed()


def signed_in():
    """True if YouTube for Kodi holds a usable Google sign-in right now."""
    return _installed() and _signed_in(_read_tokens_file())


def forget_saved_signin():
    """
    Drop the copy ReAuthorize keeps. Needed after a sign-out: YouTube would be
    found signed out at the next start and the old sign-in put straight back.
    """
    xbmcaddon.Addon(ACCOUNTMGR_ID).setSetting(TOKENS_KEY, '')


def wipe():
    """
    Sign YouTube for Kodi out without asking: blank the tokens in its own sign-in file
    (empty tokens, expiry -1, the way a signed-out user looks) and the API keys ReAuthorize
    put in its settings. Part of a full wipe (owner.wipe_local). Until 1.3.5 this was left
    alone, so the bench still held its Google sign-in after a reset, and the service then
    picked it up again as ReAuthorize's own and backed it up. Only ever blanks what is
    there; the user row, names and ids stay. Returns True if anything changed.
    """
    if not _installed():
        return False
    changed = False
    text = _read_tokens_file()
    if text:
        try:
            data = json.loads(text)
        except Exception:
            data = None
        if data is not None:
            touched = []

            def blank(node):
                if isinstance(node, dict):
                    if 'access_token' in node or 'refresh_token' in node:
                        for key, value in (('access_token', ''), ('refresh_token', ''), ('token_expires', -1)):
                            if key in node and node[key] != value:
                                node[key] = value
                                touched.append(key)
                    for child in node.values():
                        blank(child)
                elif isinstance(node, list):
                    for child in node:
                        blank(child)

            blank(data)
            if touched:
                try:
                    with open(xbmcvfs.translatePath(TOKENS_FILE), 'w', encoding='utf-8') as f:
                        f.write(json.dumps(data, indent=4))
                    changed = True
                except Exception as e:
                    _log('could not sign YouTube out: %s' % e)
    try:
        yt = xbmcaddon.Addon(YT_ADDON_ID)
        for key in API_KEYS:
            if yt.getSetting(key):
                yt.setSetting(key, '')
                changed = True
    except Exception as e:
        _log('could not blank the API keys: %s' % e)
    if changed:
        _log('YouTube sign-in removed')
    return changed


# A dialog is on screen (YouTube's code window, or its 'sign in again?' question): no id, or 9999 = none.
_NO_DIALOG = (-1, 9999)


def _dialog_open():
    try:
        import xbmcgui
        return xbmcgui.getCurrentWindowDialogId() not in _NO_DIALOG
    except Exception:
        return False


def wait_for_signin(minutes=10):
    """
    Follow a sign-in being made in YouTube for Kodi and keep a copy of it. Its sign-in is up to three
    codes in a row, done outside this script, so this watches the file until it has been quiet for a
    while WITH NO DIALOG ON SCREEN. True if anything was saved.

    Until 1.4.4 'quiet' counted while YouTube's next code window was still open: 45 s after the second
    approval this returned, the settings reopened on top and YouTube's third code window vanished half
    way through the user typing google.com/device, its request left waiting (the user, 2026-10-18).
    """
    monitor = xbmc.Monitor()
    deadline = time.time() + minutes * 60
    saved_at = None
    quiet_since = None
    while time.time() < deadline and not monitor.abortRequested():
        if capture_tokens():
            saved_at = time.time()
            quiet_since = None
        elif saved_at:
            if _dialog_open():
                quiet_since = None            # a code still being entered: keep waiting
            elif quiet_since is None:
                quiet_since = time.time()
            elif time.time() - quiet_since > 45:
                break
        if monitor.waitForAbort(3):
            break
    return saved_at is not None


def _capture_keys(accountmgr):
    """
    Store the API keys the sign-in was issued against, if we do not have them.

    A sign-in is only valid for those keys, so keeping one without the other is
    worse than keeping neither: after a build install we would restore a sign-in
    whose keys no longer exist. They are captured together, always.

    Never overwrites keys already in ReAuthorize - those are the ones it syncs
    out to other addons, and the user chose them.
    """
    try:
        yt = xbmcaddon.Addon(YT_ADDON_ID)
        values = [clean_value(k, yt.getSetting(k)) for k in API_KEYS]
    except Exception as e:
        _log('could not read the API keys: %s' % e)
        return False
    if any(values) and not all(values):
        return False  # An incomplete client bundle must not replace a complete one.
    if all(accountmgr.getSetting(k) == v for k, v in zip(API_KEYS, values)):
        return False
    for key, value in zip(API_KEYS, values):
        accountmgr.setSetting(key, value)
    _log('YouTube API keys stored alongside the sign-in')
    return True


def capture_tokens():
    """
    Copy YouTube's sign-in into ReAuthorize so a build install cannot lose it,
    together with the API keys it belongs to. Only ever reads from YouTube;
    returns True when something new was stored.
    """
    if not _installed():
        return False
    text = _read_tokens_file()
    if not text or not _signed_in(text):
        return False
    if len(text.encode('utf-8')) > MAX_TOKENS_BYTES:
        _log('sign-in file is unexpectedly large - not stored')
        return False
    accountmgr = xbmcaddon.Addon(ACCOUNTMGR_ID)
    keys_stored = _capture_keys(accountmgr)
    if accountmgr.getSetting(TOKENS_KEY) == text:
        return keys_stored
    accountmgr.setSetting(TOKENS_KEY, text)
    _log('YouTube sign-in stored, ready for the next build')
    return True


def restore_tokens():
    """
    Put a stored sign-in back after a build install. Never overwrites a
    sign-in that is already there - the one on the device is the live one.
    """
    if not _installed():
        return False
    stored = xbmcaddon.Addon(ACCOUNTMGR_ID).getSetting(TOKENS_KEY)
    if not stored or not _signed_in(stored):
        return False
    if _signed_in(_read_tokens_file()):
        return False
    path = xbmcvfs.translatePath(TOKENS_FILE)
    try:
        xbmcvfs.mkdirs(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(stored)
    except Exception as e:
        _log('could not restore the sign-in: %s' % e)
        return False
    _log('YouTube sign-in restored')
    return True


class Auth:

    def youtube_auth(self):
        if signed_in():
            # Adopt the active client's credentials before any push can change them.
            capture_tokens()
        # The sign-in is worth restoring even when no personal API keys are set,
        # so it is not behind the key check below.
        restore_tokens()

        accountmgr = xbmcaddon.Addon(ACCOUNTMGR_ID)
        stored = [accountmgr.getSetting(key) for key in API_KEYS]
        values = [clean_value(key, value) for key, value in zip(API_KEYS, stored)]

        if not all(values):
            return

        # Repair ReAuthorize's own copy too, or the bad paste would be pushed out again.
        for key, old, new in zip(API_KEYS, stored, values):
            if old != new:
                accountmgr.setSetting(key, new)
                _log('%s tidied (extra text around the pasted value removed)' % key)

        if not _installed():
            return

        try:
            yt = xbmcaddon.Addon(YT_ADDON_ID)
            for key, value in zip(API_KEYS, values):
                yt.setSetting(key, value)
        except Exception:
            pass
