from urllib.parse import parse_qs, urlencode, urlsplit
import threading
import time
import xbmc
import xbmcgui
from resources.lib import Utils

# A selected external player can take time to search and resolve a video.
# Keep the watcher scoped to the initiating Portal dialog, not a global service.
START_TIMEOUT = 300


def cancel_pending_playback(dialog):
    request = getattr(dialog, '_portal_playback_request', None)
    if request is not None:
        request.cancelled.set()
        dialog._portal_playback_request = None


def cancel_on_portal_input(dialog, action=None):
    """After a cancelled player chooser, a new Portal interaction ends the old request."""
    if getattr(dialog, '_portal_playback_request', None) is None:
        return
    # Ignore passive mouse movement and playback/volume events. A click is
    # supplied without an action, and navigation keys have standard Kodi IDs.
    if action is not None and action.getId() not in (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 92, 100, 101, 102, 104, 105, 117, 401):
        return
    if xbmcgui.getCurrentWindowDialogId() == getattr(dialog, 'window_id', None):
        cancel_pending_playback(dialog)


class PlaybackRequest(xbmc.Player):
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.cancelled = threading.Event()
        self.av_started = threading.Event()
        self.initial_video, self.initial_file = self.video_state()
        self.saw_idle = not self.initial_video

    def video_state(self):
        if not self.isPlayingVideo():
            return False, ''
        try:
            return True, self.getPlayingFile()
        except RuntimeError:
            return True, ''

    def onAVStarted(self):
        self.av_started.set()

    def is_new_video(self):
        playing, filename = self.video_state()
        if not playing:
            self.saw_idle = True
            return False
        # Do not close Portal merely because an embedded preview or another
        # movie was already playing when the chooser was opened.
        if filename and self.initial_file and filename != self.initial_file:
            return True
        if self.saw_idle and (filename or self.av_started.is_set()):
            return True
        # A replay of the same file is a new AV session, except for an existing
        # embedded preview, whose AV events must not close its information page.
        return self.av_started.is_set() and not getattr(self.dialog, 'windowed_trailers', False)

    def active(self):
        return (not self.cancelled.is_set()
                and getattr(self.dialog, '_portal_modal_active', False)
                and getattr(self.dialog, '_portal_playback_request', None) is self)

    def watch(self):
        monitor = xbmc.Monitor()
        deadline = time.monotonic() + START_TIMEOUT
        try:
            while self.active() and not monitor.abortRequested() and time.monotonic() < deadline:
                if self.is_new_video() and self.active():
                    self.dialog._portal_feature_started = True
                    try:
                        self.dialog.close()
                    except Exception:
                        self.dialog._portal_feature_started = False
                        raise
                    return
                if monitor.waitForAbort(0.2):
                    return
        except Exception as exc:
            # Player paths and provider URLs can contain credentials. Log only
            # the exception class, not the path or full exception string.
            xbmc.log('Diggz Portal: playback handoff monitor: ' + type(exc).__name__, xbmc.LOGWARNING)
        finally:
            if getattr(self.dialog, '_portal_playback_request', None) is self:
                cancel_pending_playback(self.dialog)


def choose_player(url):
    Utils.hide_busy()
    if not url:
        return
    target = urlsplit(url.replace('&amp;', '&'))
    if target.scheme != 'plugin' or target.netloc != 'plugin.video.themoviedb.helper':
        return
    params = parse_qs(target.query)
    if params.get('info') != ['play'] or params.get('type') not in (['movie'], ['episode']):
        return
    params['ignore_default'] = ['true']
    url = 'plugin://plugin.video.themoviedb.helper/?' + urlencode(params, doseq=True)
    # Import lazily to avoid a cycle with the dialog modules. Both catalog and
    # information windows register their actual modal owner with WindowManager.
    from resources.lib.WindowManager import wm
    dialog = getattr(wm, '_modal_owner', None)
    request = None
    if dialog is not None and getattr(dialog, '_portal_modal_active', False):
        cancel_pending_playback(dialog)
        request = PlaybackRequest(dialog)
        dialog._portal_playback_request = request
    try:
        xbmc.executebuiltin('PlayMedia(%s)' % url)
        if request is not None:
            threading.Thread(target=request.watch, name='PortalPlaybackHandoff', daemon=True).start()
    except Exception:
        if request is not None and getattr(dialog, '_portal_playback_request', None) is request:
            cancel_pending_playback(dialog)
        raise
