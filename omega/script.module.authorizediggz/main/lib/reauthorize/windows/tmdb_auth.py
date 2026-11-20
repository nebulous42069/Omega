"""TMDB browser-approval QR window. Polling never writes account settings."""
import os
import threading
import time
import webbrowser
import xbmc
import xbmcaddon
import xbmcgui
from reauthorize.modules.qr_local import qr_rectangles
from .device_auth import DeviceAuthDialog, ADDON_ID


class TMDBAuthDialog(DeviceAuthDialog):
    def onInit(self):
        self.getControl(101).setLabel('Authorize TMDB')
        self.getControl(102).setLabel('Scan the QR code with your phone')
        self.getControl(103).setLabel('Sign in to TMDB and approve access')
        # The embedded addon path already ends in 'main'. Resolve the
        # packaged black texture relative to this module, not the launcher.
        try:
            main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            texture = os.path.join(main_path, 'resources', 'skins', 'default', 'media', 'common', 'qr_black.png')
            if not os.path.isfile(texture):
                raise FileNotFoundError('Packaged QR texture missing')
            self.qr_controls = [xbmcgui.ControlImage(x, y, w, h, texture, 0, '0xFFFFFFFF')
                                for x, y, w, h in qr_rectangles(self.verification_url, 780, 270, 360)]
            self.addControls(self.qr_controls)
            xbmc.log('[Diggz Account Manager] TMDB QR texture verified; controls added: %d' % len(self.qr_controls), xbmc.LOGINFO)
        except Exception as exc:
            xbmc.log('[Diggz Account Manager] TMDB QR control rendering failed: %s' % type(exc).__name__, xbmc.LOGERROR)
            self.getControl(102).setLabel('QR unavailable - select Open in Browser')
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        deadline = self.deadline
        next_poll = time.monotonic() + 3
        monitor = xbmc.Monitor()
        while not self.cancelled and not monitor.abortRequested():
            now = time.monotonic()
            remaining = max(0, int(deadline - now + 0.999))
            if not remaining:
                break
            try:
                self.getControl(104).setLabel('Waiting for approval... %02d:%02d' % divmod(remaining, 60))
            except Exception:
                pass
            if now >= next_poll:
                try:
                    result = self.poll_func()
                except Exception:
                    result = False
                if self.cancelled or monitor.abortRequested():
                    return
                if result is True:
                    self.success = True
                    self._finish('Approved!')
                    return
                if result is False:
                    self._finish('Authorization failed or was denied.')
                    return
                if result == 'slow_down':
                    self.interval = min(30, self.interval + 5)
                next_poll = time.monotonic() + self.interval
            if monitor.waitForAbort(1):
                break
        if not self.cancelled:
            self._finish('Authorization expired - please try again.')

    def onClick(self, control_id):
        if control_id == 201:
            try:
                webbrowser.open(self.verification_url)
            except Exception:
                pass  # QR remains available on devices without a browser.
        else:
            super().onClick(control_id)


def run(url, poll_func, deadline):
    addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
    w = TMDBAuthDialog('tmdb_auth.xml', addon_path, 'default', '1080i')
    w.addon_path = addon_path
    w.verification_url = url
    w.poll_func = poll_func
    w.deadline = deadline
    try:
        w.doModal()
    finally:
        # Kodi may close the dialog directly; do not commit a late result.
        approved = w.success and not w.cancelled
        w.cancelled = True
        if w._thread is not None:
            w._thread.join(16)
    return approved
