# SPDX-License-Identifier: GPL-2.0-or-later
"""Skip the parent entry once per newly loaded video directory."""
import os
import time
import uuid
import xbmc
import xbmcvfs

VIEWS = (50, 51, 52, 53, 55, 56, 57, 58, 59, 500, 501, 502, 503, 504, 505, 506, 507, 509, 591, 592, 602, 609)


class ListingState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.path = None
        self.busy = False
        self.handled = False
        self.ready_since = None

    def check(self, path, busy, ready, now):
        if path != self.path or (busy and not self.busy):
            self.path = path
            self.handled = False
            self.ready_since = None
        self.busy = busy
        if self.handled or busy or not ready:
            self.ready_since = None
            return False
        if self.ready_since is None:
            self.ready_since = now
            return False
        if now - self.ready_since < 0.4:
            return False
        self.handled = True
        return True


def run():
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon2/')
    os.makedirs(profile, exist_ok=True)
    lock = os.path.join(profile, 'video-nav-focus.lock')
    token = uuid.uuid4().hex
    try:
        with open(lock, 'x') as stream:
            stream.write(token)
    except FileExistsError:
        if time.time() - os.path.getmtime(lock) < 60:
            return
        os.unlink(lock)
        try:
            with open(lock, 'x') as stream:
                stream.write(token)
        except FileExistsError:
            return
    state = ListingState()
    monitor = xbmc.Monitor()
    heartbeat = 0
    try:
        while not monitor.abortRequested():
            if xbmc.getSkinDir() != 'skin.xenon2':
                break
            now = time.monotonic()
            if now - heartbeat >= 5:
                os.utime(lock, None)
                heartbeat = now
            if not xbmc.getCondVisibility('Window.IsActive(videos)'):
                state.reset()
            else:
                view = next((v for v in VIEWS if xbmc.getCondVisibility('Control.IsVisible(%d)' % v)), None)
                ready = view is not None and xbmc.getCondVisibility('Control.HasFocus(%d)' % view)
                path = xbmc.getInfoLabel('Container.FolderPath')
                busy = xbmc.getCondVisibility('Container.IsUpdating')
                if state.check(path, busy, ready, now):
                    if xbmc.getCondVisibility('ListItem.IsParentFolder'):
                        count = xbmc.getInfoLabel('Container(%d).NumItems' % view)
                        if count.isdigit() and int(count) > 0:
                            xbmc.executebuiltin('SetFocus(%d,1,absolute)' % view)
            if monitor.waitForAbort(0.1 if xbmc.getCondVisibility('Window.IsActive(videos)') else 0.5):
                break
    finally:
        try:
            with open(lock) as stream:
                owned = stream.read() == token
            if owned:
                os.unlink(lock)
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        xbmc.log('Xenon2 video directory focus: ' + type(error).__name__, xbmc.LOGERROR)
