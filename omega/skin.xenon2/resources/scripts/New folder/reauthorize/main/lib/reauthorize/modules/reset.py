# -*- coding: utf-8 -*-
"""
    ReAuthorize - Reset switch (temporary; remove in 1.3.6)

    One number on the server ('reset_epoch', see server/api.php). Shipped at 0,
    which does nothing. Raise it and every device that updates to this version
    removes all of its sign-ins at its next start, tells the user in plain words,
    and starts as a first install with a new device ID.

    Removing it later means deleting this file and startup._guard_identity's one
    call to reset.check(). The server side can stay: at 0 it is inert.

    The number this device has already obeyed is kept beside the device ID, outside
    Kodi, so a build cannot carry it in (a build carrying its maker's number would
    make its boxes think the reset had already happened).
"""

import os
import threading
import xbmc
import xbmcaddon
from reauthorize.modules import own_settings  # one read or write of our settings at a time
import xbmcgui
from reauthorize.modules import storage, device, vault, server, owner

ADDON_ID = 'script.module.reauthorize'
LOG_TAG  = '[ReAuthorize Reset]'
FILE     = 'reset_epoch'
FALLBACK = 'reset.epoch'   # only where there is nowhere to write outside Kodi

FOLLOWUP_FILE = 'reset_followup'
FOLLOWUP_MESSAGE = ('This device has been cleared.[CR][CR]'
                    'To complete the reset, sign in to your services again through ReAuthorize: '
                    'open each tab and choose Authorize (Real-Debrid, Premiumize, Trakt and any '
                    'others you use).')

# Shown when the wipe has FINISHED (people will not think to open ReAuthorize on their own,
# and a message that goes away reads as "fixed"). The server can replace the first part with a
# 'reset_message' row; the line after it is always added, because OK opens ReAuthorize.
# The action goes FIRST: some skins show only the first line, about 45 characters (MQ9, 2026-10-02).
DEFAULT_MESSAGE = ('Update done. Sign in to your services again.[CR][CR]'
                   'Every sign-in on this device was reset by the ReAuthorize update, '
                   'so please sign in to your services again to finish.')
OPEN_LINE = '[CR][CR]Press OK to open ReAuthorize.'

# While the wipe runs (about a minute). No commas in the text: the builtin splits on them.
START_NOTICE = 'Notification(ReAuthorize, Resetting sign-ins. This takes about a minute., 8000)'


def _path():
    base = storage.data_dir()
    return os.path.join(base, FILE) if base else None


def _read():
    """The number this device has obeyed, or None if it has never recorded one."""
    path = _path()
    try:
        if path:
            if os.path.isfile(path):
                return int(open(path).read().strip())
            return None
        value = own_settings.addon().getSetting(FALLBACK)
        return int(value) if value != '' else None
    except (ValueError, OSError):
        return None


def _write(number):
    path = _path()
    try:
        if path and storage.ensure_dir():
            with open(path, 'w') as f:
                f.write(str(number))
            return
    except OSError as e:
        xbmc.log('%s Could not record epoch: %s' % (LOG_TAG, e), xbmc.LOGWARNING)
    own_settings.addon().setSetting(FALLBACK, str(number))


def _followup_path():
    base = storage.data_dir()
    return os.path.join(base, FOLLOWUP_FILE) if base else None


def _set_followup():
    """Note that the next time ReAuthorize is opened it should say what to do now."""
    path = _followup_path()
    try:
        if path and storage.ensure_dir():
            with open(path, 'w') as f:
                f.write('1')
    except OSError as e:
        xbmc.log('%s Could not note the follow-up: %s' % (LOG_TAG, e), xbmc.LOGWARNING)


def _clear_followup():
    path = _followup_path()
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


def show_followup():
    """
    Called when ReAuthorize is opened (default.py). Once after a reset, say that the device
    was cleared and how to finish. The popup and notice at the reset can be missed, and this
    is the screen people actually read. Returns True if it showed.
    """
    path = _followup_path()
    try:
        if not (path and os.path.isfile(path)):
            return False
        os.remove(path)
    except OSError:
        return False
    xbmcgui.Dialog().ok('ReAuthorize', FOLLOWUP_MESSAGE)
    return True


def _clean(message):
    text = ''.join(ch for ch in str(message or '') if ch >= ' ')[:400].strip()
    return text or DEFAULT_MESSAGE


# The thread showing the message, kept so a test can wait for it.
_popup = None


def _announce(message):
    """
    Once the wipe has finished, say so and keep saying it until OK is pressed, in a thread of
    its own so that nothing waits on it. OK opens ReAuthorize, because people who are merely
    told to will not, and will think it is fixed. Seen live on the Shield (2026-09-30): another
    addon's long notice covered the message, and because the wipe waited for it to be closed,
    the reset sat idle for three minutes. A dialog closed with Back or Cancel comes straight
    back; it stops only for OK or when Kodi is closing.
    """
    text = _clean(message) + OPEN_LINE

    def show():
        monitor = xbmc.Monitor()
        while True:
            try:
                if xbmcgui.Dialog().ok('ReAuthorize', text):
                    _clear_followup()        # they are being taken there now
                    xbmc.executebuiltin('RunScript(script.module.reauthorize)')
                    return
            except Exception as e:
                xbmc.log('%s Could not show the reset message: %s' % (LOG_TAG, e), xbmc.LOGWARNING)
                return
            if monitor.waitForAbort(1):
                return

    thread = threading.Thread(target=show)
    thread.start()
    return thread


def perform(message):
    global _popup
    xbmc.executebuiltin(START_NOTICE)
    # This device's own sign-ins, so end Trakt at Trakt too: one revoke kills every
    # copy that ever left, and Trakt allows free accounts one connected app anyway.
    owner.wipe_local(revoke_trakt=True)
    for step in (server.reset_done, server.clear):   # both need the old ID, so before it is replaced
        try:
            step()
        except Exception:
            pass
    vault.clear()
    device.forget()
    storage.purge_all()     # and any stray copy in the locations not in use
    xbmc.log('%s All sign-ins removed; device starts fresh.' % LOG_TAG, xbmc.LOGINFO)
    _set_followup()         # if the popup below is never answered, ReAuthorize says it on its first open
    _popup = _announce(message)


def check():
    """
    Compare the server's number with the one this device last obeyed. Returns True
    if it reset the device. Silent and harmless when the server is unreachable.
    """
    seen = _read()
    status = server.reset_status(obeyed=seen)
    if not status:
        return False
    target = status['reset']
    if seen is None:
        if not owner.holds_credentials():
            _write(target)      # a fresh box: nothing to reset, and nothing after this
            return False
        seen = 0                # an existing box: it has obeyed nothing yet
    if target <= seen:
        if _read() is None:
            _write(seen)
        return False
    perform(status.get('message'))
    _write(target)
    try:
        server.reset_status(obeyed=target)   # count this device under its new ID straight away
    except Exception:
        pass
    return True
