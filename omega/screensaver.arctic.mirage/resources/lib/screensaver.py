# -*- coding: utf-8 -*-
import threading

import xbmc
import xbmcgui

from resources.lib import utils


WIDGET_LIST_ID = 1297
HIDDEN_IMAGE_ID = 1298
INFO_BUTTON_ID = 1299

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_STOP = 13
ACTION_MOVE_DOWN = 4

OPEN_INFO_ON_WAKE_SETTING = 'open_info_on_wake'
RESTORE_PAUSED_VIDEO_OSD_SETTING = 'restore_paused_video_osd'

ART_KEYS = (
    'clearlogo',
    'tvshow.clearlogo',
    'fanart',
    'tvshow.fanart',
    'thumb',
    'poster',
    'tvshow.poster',
    'landscape',
    'banner',
    'icon',
    'clearart',
    'logo',
)

PROPERTY_KEYS = (
    'IsPlayable',
    'tmdb_id',
    'tvdb_id',
    'imdb_id',
    'dbid',
    'dbtype',
)

INFO_FIELDS = (
    'Title',
    'OriginalTitle',
    'TVShowTitle',
    'Plot',
    'Year',
    'Rating',
    'Votes',
    'Genre',
    'MPAA',
    'Duration',
    'Premiered',
    'Studio',
    'Director',
    'Writer',
    'Season',
    'Episode',
    'DBID',
    'DBTYPE',
    'IMDBNumber',
)


def _as_int(value):
    try:
        if value in (None, ''):
            return None
        return int(float(value))
    except Exception:
        return None


def _as_float(value):
    try:
        if value in (None, ''):
            return None
        return float(value)
    except Exception:
        return None


class Screensaver(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, deactivated_callback):
            self.deactivated_callback = deactivated_callback

        def onScreensaverActivated(self):
            utils.log('Screensaver Activated')

        def onScreensaverDeactivated(self):
            utils.log('Screensaver Deactivated')

            try:
                self.deactivated_callback()
            except AttributeError:
                utils.log('Callback method not yet available.')
            except Exception as exc:
                utils.log('Screensaver deactivation callback failed: {}'.format(exc), xbmc.LOGERROR)

    def __init__(self, *args, **kwargs):
        self.exit_monitor = self.ExitMonitor(self.onScreensaverDeactivated)
        self.path = utils.get_saved_widget_path()
        self.name = utils.get_saved_widget_name()
        self.open_info_on_wake = utils.get_bool_setting(OPEN_INFO_ON_WAKE_SETTING, True)
        self.restore_paused_video_osd = utils.get_bool_setting(RESTORE_PAUSED_VIDEO_OSD_SETTING, True)
        self._paused_video_on_start = self._video_is_paused()
        self._paused_video_wake_requested = False
        self._exit_requested = False
        self._info_requested = False
        self._ready = False
        self._capture_stop = False
        self._last_item = {}
        self._capture_thread = None
        self._lifecycle_lock = threading.RLock()
        self._handoff_pending = False
        self._handoff_complete = threading.Event()
        self._screensaver_inhibited = False
        self._screensaver_was_inhibited = False
        utils.log('Widget path: {}'.format(self.path))
        utils.log('Open info on wake: {}'.format(self.open_info_on_wake))
        utils.log('Restore paused video OSD: {}'.format(self.restore_paused_video_osd))
        utils.log('Paused video on screensaver start: {}'.format(self._paused_video_on_start))

    def onInit(self):
        self.character = self.getControl(HIDDEN_IMAGE_ID)
        self._ready = True
        self.setProperty('screensaver.arctic.mirage.info_enabled', 'true' if self.open_info_on_wake else '')

        if self.path:
            self.setProperty('screensaver.arctic.mirage.path', self.path)
        if self.name:
            self.setProperty('screensaver.arctic.mirage.name', self.name)

        self._start_capture_thread()

    def on_screensaver_deactivated(self):
        # Compatibility alias for the 1.9.6 callback-name typo.
        return self.onScreensaverDeactivated()

    def _video_is_paused(self):
        try:
            return bool(
                xbmc.getCondVisibility('Player.HasVideo')
                and xbmc.getCondVisibility('Player.Paused')
            )
        except Exception:
            return False

    def _paused_video_should_take_priority(self):
        return bool(
            self.restore_paused_video_osd
            and (self._paused_video_on_start or self._video_is_paused())
        )

    def onScreensaverDeactivated(self):
        if self._handoff_pending:
            # InhibitScreensaver wakes Kodi's core screensaver once at startup.
            # Keep our modal dialog visible so subsequent keys reach onAction.
            self._handoff_pending = False
            self._handoff_complete.set()
            return

        # A real deactivation still cannot identify a button.
        self.close_screensaver()

    def onAction(self, action):
        action_id = action.getId()

        if action_id in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_STOP):
            self._exit_requested = True
        elif action_id == ACTION_MOVE_DOWN:
            if self.open_info_on_wake and not self._paused_video_should_take_priority():
                self.capture_selected_item()
                self._info_requested = True

        # Every other action wakes normally, without opening Video Info.
        self.close_screensaver()

    def onClick(self, control_id):
        # Mouse/touch and OK are ordinary wake actions, never info requests.
        self.close_screensaver()

    def _start_capture_thread(self):
        if self._capture_thread:
            return

        self._capture_thread = threading.Thread(target=self._capture_loop)
        self._capture_thread.daemon = True
        self._capture_thread.start()

    def _take_input_control(self):
        if not self.open_info_on_wake:
            return True

        # Core screensaver wake consumes the first physical key. Release that
        # core state now, while retaining our modal WindowXMLDialog. Inhibition
        # also prevents Kodi from launching a second screensaver over this one.
        with self._lifecycle_lock:
            if self._capture_stop:
                return False
            self._handoff_pending = bool(xbmc.getCondVisibility('System.ScreenSaverActive'))
            if not self._handoff_pending:
                self._handoff_complete.set()
            self._screensaver_was_inhibited = bool(xbmc.getCondVisibility('System.IsScreensaverInhibited'))
            self._screensaver_inhibited = True
            xbmc.executebuiltin('InhibitScreensaver(true)', wait=True)

        for unused in range(50):
            if self._capture_stop or self.exit_monitor.abortRequested():
                return False
            if self._handoff_complete.wait(0.1):
                break
        else:
            utils.log('Screensaver input handoff timed out', xbmc.LOGERROR)
            return False

        with self._lifecycle_lock:
            if self._capture_stop:
                return False
            # Kodi schedules StopScript for a Python screensaver on wake. The
            # modal dialog now owns its lifetime, so cancel that shutdown alarm.
            xbmc.executebuiltin('CancelAlarm(sssssscreensaver,true)', wait=True)
        utils.log('Screensaver dialog now owns input; DOWN opens Video Info')
        return True

    def _capture_loop(self):
        try:
            if not self._take_input_control():
                self.close_screensaver()
                return
            while not self._capture_stop:
                if self.exit_monitor.abortRequested():
                    self.close_screensaver()
                    return
                if self._ready:
                    self.capture_selected_item(log_failures=False)
                self.exit_monitor.waitForAbort(1.0)
        except Exception as exc:
            utils.log('Screensaver input worker failed: {}'.format(exc), xbmc.LOGERROR)
            self.close_screensaver()

    def release_input_control(self):
        with self._lifecycle_lock:
            if self._screensaver_inhibited:
                restore = 'true' if self._screensaver_was_inhibited else 'false'
                xbmc.executebuiltin('InhibitScreensaver({})'.format(restore), wait=True)
                self._screensaver_inhibited = False

    def _get_container_label(self, field):
        return xbmc.getInfoLabel('Container({}).ListItem.{}'.format(WIDGET_LIST_ID, field)) or ''

    def _get_container_property(self, key):
        return xbmc.getInfoLabel('Container({}).ListItem.Property({})'.format(WIDGET_LIST_ID, key)) or ''

    def _get_selected_item(self, log_failures=True):
        try:
            list_control = self.getControl(WIDGET_LIST_ID)
            return list_control.getSelectedItem()
        except Exception as exc:
            if log_failures:
                utils.log('Unable to read selected item from control: {}'.format(exc), xbmc.LOGWARNING)
            return None

    def _get_selected_item_path(self, item=None):
        path = ''

        try:
            if item:
                path = item.getPath() or ''
        except Exception as exc:
            utils.log('Unable to read selected item path from ListItem: {}'.format(exc), xbmc.LOGWARNING)

        if not path:
            path = self._get_container_label('FileNameAndPath')
        if not path:
            path = self._get_container_label('Path')
        if not path:
            path = self._get_container_label('FolderPath')

        return path

    def capture_selected_item(self, log_failures=True):
        item = self._get_selected_item(log_failures=log_failures)
        path = self._get_selected_item_path(item)

        label = ''
        label2 = ''
        try:
            if item:
                label = item.getLabel() or ''
                label2 = item.getLabel2() or ''
        except Exception:
            pass

        info = {}
        for field in INFO_FIELDS:
            value = self._get_container_label(field)
            if value:
                info[field.lower()] = value

        art = {}
        for key in ART_KEYS:
            value = ''
            try:
                if item:
                    value = item.getArt(key) or ''
            except Exception:
                value = ''
            if not value:
                value = xbmc.getInfoLabel('Container({}).ListItem.Art({})'.format(WIDGET_LIST_ID, key)) or ''
            if value:
                art[key] = value

        props = {}
        for key in PROPERTY_KEYS:
            value = self._get_container_property(key)
            if value:
                props[key] = value

        title = info.get('title') or label or path
        if not title and not path:
            return self._last_item

        snapshot = {
            'label': label or title,
            'label2': label2,
            'path': path,
            'info': info,
            'art': art,
            'properties': props,
        }
        self._last_item = snapshot
        return snapshot

    def should_restore_paused_video_osd_after_close(self):
        # Enter/OK usually just dismisses the screensaver. If it was launched
        # over a paused video, restore fullscreen playback UI instead of opening
        # widget Video Info.
        return bool(
            self.restore_paused_video_osd
            and not self._exit_requested
            and (self._paused_video_wake_requested or self._paused_video_on_start or self._video_is_paused())
        )

    def restore_paused_video_osd(self):
        utils.log('Restoring paused video OSD after screensaver close')
        try:
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)', wait=True)
            xbmc.sleep(250)

            if not xbmc.getCondVisibility('Window.IsActive(videoosd)'):
                xbmc.executebuiltin('Action(OSD)', wait=True)
                xbmc.sleep(150)

            if not xbmc.getCondVisibility('Window.IsActive(videoosd)'):
                xbmc.executebuiltin('ActivateWindow(videoosd)', wait=True)

            return True
        except Exception as exc:
            utils.log('Unable to restore paused video OSD: {}'.format(exc), xbmc.LOGERROR)
            return False

    def should_open_info_after_close(self):
        # Require an explicit DOWN request. A captured item or a generic
        # screensaver wake must never open info. Paused video OSD takes priority.
        return bool(
            self.open_info_on_wake
            and not self._exit_requested
            and not self.should_restore_paused_video_osd_after_close()
            and self._info_requested
            and self._last_item
        )

    def _make_info_listitem(self, snapshot):
        snapshot = snapshot or {}
        info = snapshot.get('info') or {}
        art = snapshot.get('art') or {}
        props = snapshot.get('properties') or {}
        path = snapshot.get('path') or ''
        label = snapshot.get('label') or info.get('title') or path or 'Selected item'

        listitem = xbmcgui.ListItem(label=label)

        try:
            if path:
                listitem.setPath(path)
        except Exception:
            pass

        try:
            if art:
                listitem.setArt(art)
        except Exception as exc:
            utils.log('Unable to set art on info ListItem: {}'.format(exc), xbmc.LOGWARNING)

        for key, value in props.items():
            try:
                listitem.setProperty(key, value)
            except Exception:
                pass

        video_info = {}
        text_map = {
            'title': 'title',
            'originaltitle': 'originaltitle',
            'tvshowtitle': 'tvshowtitle',
            'plot': 'plot',
            'genre': 'genre',
            'mpaa': 'mpaa',
            'premiered': 'premiered',
            'studio': 'studio',
            'director': 'director',
            'writer': 'writer',
            'imdbnumber': 'imdbnumber',
        }
        for src, dst in text_map.items():
            if info.get(src):
                video_info[dst] = info[src]

        for src, dst in (('year', 'year'), ('duration', 'duration'), ('season', 'season'), ('episode', 'episode'), ('dbid', 'dbid')):
            value = _as_int(info.get(src))
            if value is not None:
                video_info[dst] = value

        rating = _as_float(info.get('rating'))
        if rating is not None:
            video_info['rating'] = rating

        if info.get('votes'):
            video_info['votes'] = info['votes']

        mediatype = info.get('dbtype') or props.get('dbtype') or ''
        if not mediatype:
            if info.get('season') or info.get('episode'):
                mediatype = 'episode'
            elif info.get('tvshowtitle'):
                mediatype = 'tvshow'
            else:
                mediatype = 'movie'
        video_info['mediatype'] = mediatype

        try:
            listitem.setInfo('video', video_info)
        except Exception as exc:
            utils.log('Unable to set video info on ListItem: {}'.format(exc), xbmc.LOGWARNING)

        return listitem

    def open_last_item_info(self):
        snapshot = self._last_item or {}
        if not snapshot:
            utils.log('No captured widget item available for Video Info dialog', xbmc.LOGWARNING)
            return False

        label = snapshot.get('label') or (snapshot.get('info') or {}).get('title') or snapshot.get('path') or 'selected item'
        utils.log('Opening Video Info dialog after screensaver close: {}'.format(label))

        try:
            listitem = self._make_info_listitem(snapshot)
            xbmcgui.Dialog().info(listitem)
            return True
        except Exception as exc:
            utils.log('Video Info dialog failed after screensaver close: {}'.format(exc), xbmc.LOGERROR)
            return False

    def close_screensaver(self):
        self._capture_stop = True
        try:
            self.release_input_control()
        finally:
            self.close()

    def exit(self):
        self._exit_requested = True
        self.close_screensaver()
        if self.exit_monitor:
            del self.exit_monitor
