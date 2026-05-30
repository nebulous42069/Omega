import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import os
import json
import time
import threading


class DependencyStatusWindow(xbmcgui.WindowDialog):
    """Persistent dependency status overlay.

    This is intentionally not DialogProgress. Kodi's startup ecosystem is full of add-ons
    opening/closing dialogs and stealing focus, so the installer owns this custom window and
    a watchdog keeps re-showing it when another startup task knocks it away.
    """

    ACTION_PREVIOUS_MENU = 10
    ACTION_NAV_BACK = 92
    ACTION_CLOSE_DIALOG = 117

    def __init__(self, heading, background_image=''):
        xbmcgui.WindowDialog.__init__(self)
        self.heading_text = heading
        self.background_image = background_image
        self.allow_close = False
        self._built = False
        self._build_controls()

    def _build_controls(self):
        if self._built:
            return

        # Use 1280x720 coordinates. Kodi scales these for the active skin/resolution.
        # This is a custom top banner, not Kodi's DialogProgressBG notification.
        # Keep it nearly full-width so long dependency/status text is readable.
        left = 20
        top = 20
        width = 1240
        height = 300

        try:
            if self.background_image and xbmcvfs.exists(self.background_image):
                self.addControl(xbmcgui.ControlImage(left, top, width, height, self.background_image))
        except Exception:
            pass

        self.heading = xbmcgui.ControlLabel(
            left + 35, top + 22, width - 70, 42,
            self.heading_text,
            font='font14',
            textColor='0xFFFFFFFF',
            alignment=2
        )
        self.line1 = xbmcgui.ControlLabel(left + 45, top + 75, width - 90, 34, '', font='font13', textColor='0xFFFFFFFF')
        self.line2 = xbmcgui.ControlLabel(left + 45, top + 115, width - 90, 34, '', font='font12', textColor='0xFFFFFFFF')
        # line3 is a textbox so long missing-dependency lists can wrap instead of disappearing.
        self.line3 = xbmcgui.ControlTextBox(left + 45, top + 155, width - 90, 64, font='font12', textColor='0xFFFFFFFF')
        self.progress = xbmcgui.ControlProgress(left + 45, top + 230, width - 90, 28)
        self.percent_label = xbmcgui.ControlLabel(left + 45, top + 262, width - 90, 25, '0%', font='font12', textColor='0xFFFFFFFF', alignment=2)

        for control in (self.heading, self.line1, self.line2, self.line3, self.progress, self.percent_label):
            self.addControl(control)

        self._built = True

    def onAction(self, action):
        # Keep this visible while the installer is active. Back/Escape should not dismiss it.
        if self.allow_close:
            return
        try:
            action_id = action.getId()
        except Exception:
            return
        if action_id in (self.ACTION_PREVIOUS_MENU, self.ACTION_NAV_BACK, self.ACTION_CLOSE_DIALOG):
            return

    def update_status(self, percent, line1='', line2='', line3=''):
        percent = max(0, min(100, int(percent)))
        try:
            self.line1.setLabel(line1 or '')
            self.line2.setLabel(line2 or '')
            try:
                self.line3.setText(line3 or '')
            except Exception:
                self.line3.setLabel(line3 or '')
            self.progress.setPercent(percent)
            self.percent_label.setLabel('%s%%' % percent)
        except Exception:
            pass

    def close_window(self):
        self.allow_close = True
        try:
            self.close()
        except Exception:
            pass


class Installer:
    """Install all addon ids listed in resources/addons.json and keep retrying until done."""

    ADDON_ID = 'service.multistaller'
    BOOT_DELAY_MS = 15000
    INSTALL_TIMEOUT = 90
    RETRY_SLEEP = 30
    REPO_REFRESH_INTERVAL = 300
    WATCHDOG_INTERVAL = 1.0
    FORCE_RESHOW_INTERVAL = 2.0
    REBUILD_IF_HIDDEN_SECONDS = 4.0
    # Kodi skins control DialogProgressBG size, so keep this short enough to fit.
    BG_HEADING = 'Installing Dependencies'
    DIALOG_HEADING = 'Please wait for Dependencies to install before continuing'
    USE_CUSTOM_WINDOW = False

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.monitor = xbmc.Monitor()
        self.dialog = None
        self.bg_progress = None
        self.addon_data = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.addon_path = addon_path
        self.addon_json = os.path.join(addon_path, 'resources', 'addons.json')
        self.dialog_bg = os.path.join(addon_path, 'resources', 'media', 'dependency_status_bg.png')

        self._status_lock = threading.RLock()
        self._ui_lock = threading.RLock()
        self._current_status = (0, 'Starting dependency installer...', '', '')
        self._progress_active = False
        self._watchdog_stop = threading.Event()
        self._watchdog_thread = None
        self._last_show = 0
        self._hidden_since = 0
        self._last_rebuild = 0

    def log(self, message, level=xbmc.LOGINFO):
        xbmc.log('[%s] %s' % (self.ADDON_ID, message), level)

    def get_setting(self, setting_id):
        return self.addon.getSetting(setting_id)

    def set_setting(self, setting_id, value):
        self.addon.setSetting(setting_id, value)

    def create_folder(self, folder_path):
        if not xbmcvfs.exists(folder_path):
            return xbmcvfs.mkdir(folder_path)
        return True

    def load_required_addons(self):
        with open(self.addon_json, 'r', encoding='utf-8', errors='ignore') as f:
            addon_data = json.loads(f.read())

        required = []
        seen = set()
        for item in addon_data.values():
            plugin_id = item.get('plugin_id') if isinstance(item, dict) else None
            if plugin_id and plugin_id not in seen:
                required.append(plugin_id)
                seen.add(plugin_id)
        return required

    def installer(self):
        self.start_progress_watchdog()
        self.update_progress(0, 'Starting dependency installer...', 'Waiting for Kodi to finish startup.', '')
        xbmc.sleep(self.BOOT_DELAY_MS)

        required_addons = self.load_required_addons()
        if not required_addons:
            self.log('No addon ids found in addons.json', xbmc.LOGWARNING)
            self.update_progress(100, 'No dependencies were found in addons.json.', '', '')
            self.set_setting('activate_installer', 'false')
            xbmc.sleep(1200)
            self.close_progress()
            return

        # Keep this on until every required addon is confirmed installed.
        self.set_setting('activate_installer', 'true')

        total = len(required_addons)
        last_repo_refresh = 0
        while not self.monitor.abortRequested():
            missing = self.get_missing_addons(required_addons)
            installed_count = total - len(missing)
            self.update_progress(
                self.percent(installed_count, total),
                'Checking required dependencies...',
                'Installed: %s of %s' % (installed_count, total),
                'Missing: %s' % self.format_addon_list(missing)
            )

            if not missing:
                self.finish_success()
                return

            now = time.time()
            if now - last_repo_refresh >= self.REPO_REFRESH_INTERVAL:
                self.refresh_repositories(installed_count, total, missing)
                last_repo_refresh = now

            for plugin_id in missing:
                if self.monitor.abortRequested():
                    break
                self.install_addon(plugin_id, required_addons)

            still_missing = self.get_missing_addons(required_addons)
            installed_count = total - len(still_missing)
            if not still_missing:
                self.finish_success()
                return

            self.set_setting('activate_installer', 'true')
            self.log('Still missing addons: %s. Will retry.' % ', '.join(still_missing), xbmc.LOGWARNING)
            self.retry_wait(installed_count, total, still_missing)

        # Kodi is shutting down/rebooting. Leave the toggle enabled so next boot retries.
        self.set_setting('activate_installer', 'true')
        self.close_progress()

    def refresh_repositories(self, installed_count=0, total=1, missing=None):
        self.log('Refreshing local addons and addon repositories before install attempts.')
        self.update_progress(
            self.percent(installed_count, total),
            'Refreshing Kodi repositories...',
            'Kodi repository metadata may not be ready yet.',
            'Still missing: %s' % self.format_addon_list(missing or [])
        )
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.executebuiltin('UpdateAddonRepos')
        self.wait_with_progress(10, installed_count, total, missing or [], 'Waiting for Kodi repositories to become available...')

    def get_missing_addons(self, addon_ids):
        return [addon_id for addon_id in addon_ids if not self.isinstalled(addon_id)]

    def install_addon(self, plugin_id, required_addons=None):
        if self.isinstalled(plugin_id):
            return True

        required_addons = required_addons or []
        total = len(required_addons) if required_addons else 1
        installed_count = total - len(self.get_missing_addons(required_addons)) if required_addons else 0

        self.log('Attempting install: %s' % plugin_id)
        self.update_progress(
            self.percent(installed_count, total),
            'Installing dependency...',
            plugin_id,
            'Installed: %s of %s' % (installed_count, total)
        )

        # Kodi's installer may briefly open its own dialog and steal focus. The watchdog will
        # keep re-showing our status window while this runs, because apparently one window was
        # too emotionally fragile for startup.
        xbmc.executebuiltin('InstallAddon(%s)' % plugin_id)

        clicked = False
        start = time.time()
        while not self.monitor.abortRequested() and time.time() - start < self.INSTALL_TIMEOUT:
            if self.isinstalled(plugin_id):
                self.log('Installed: %s' % plugin_id)
                installed_count = total - len(self.get_missing_addons(required_addons)) if required_addons else 1
                self.update_progress(
                    self.percent(installed_count, total),
                    'Installed dependency:',
                    plugin_id,
                    'Installed: %s of %s' % (installed_count, total)
                )
                return True

            elapsed = int(time.time() - start)
            remaining = max(0, int(self.INSTALL_TIMEOUT - elapsed))
            self.update_progress(
                self.percent(installed_count, total),
                'Installing dependency...',
                plugin_id,
                'Waiting up to %s seconds for Kodi to finish.' % remaining
            )

            if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)') and not clicked:
                xbmc.executebuiltin('SendClick(yesnodialog, 11)')
                clicked = True
                xbmc.sleep(500)
                self.update_progress(
                    self.percent(installed_count, total),
                    'Installing dependency...',
                    plugin_id,
                    'Confirmed Kodi install prompt.'
                )

            if self.monitor.waitForAbort(0.5):
                break

        installed = self.isinstalled(plugin_id)
        if not installed:
            self.log('Install attempt timed out or failed: %s' % plugin_id, xbmc.LOGWARNING)
            self.update_progress(
                self.percent(installed_count, total),
                'Dependency install did not complete. It will retry.',
                plugin_id,
                'Kodi repo may still be unavailable.'
            )
        return installed

    def retry_wait(self, installed_count, total, still_missing):
        self.wait_with_progress(
            self.RETRY_SLEEP,
            installed_count,
            total,
            still_missing,
            'Retrying failed dependencies shortly...'
        )

    def wait_with_progress(self, seconds, installed_count, total, missing, message):
        end_time = time.time() + seconds
        while not self.monitor.abortRequested() and time.time() < end_time:
            remaining = max(0, int(end_time - time.time()))
            self.update_progress(
                self.percent(installed_count, total),
                message,
                'Installed: %s of %s' % (installed_count, total),
                'Retry in %s sec. Missing: %s' % (remaining, self.format_addon_list(missing))
            )
            if self.monitor.waitForAbort(1):
                break

    def finish_success(self):
        self.log('All required addons are installed. Disabling startup installer.')
        self.set_setting('activate_installer', 'false')
        self.update_progress(100, 'All dependencies installed.', 'Complete.', '')
        xbmc.sleep(1800)
        self.close_progress()
        xbmcgui.Dialog().notification('Dependencies Installed', 'Complete', xbmcgui.NOTIFICATION_INFO, 5000)

    def start_progress_watchdog(self):
        self._progress_active = True
        self._watchdog_stop.clear()
        self.ensure_background_progress()
        if self.USE_CUSTOM_WINDOW:
            self.ensure_progress(force=True)
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._watchdog_thread = threading.Thread(target=self._progress_watchdog, name='DependencyStatusWatchdog')
        self._watchdog_thread.daemon = True
        self._watchdog_thread.start()

    def _progress_watchdog(self):
        self.log('Dependency status window watchdog started.')
        while not self.monitor.abortRequested() and not self._watchdog_stop.is_set():
            try:
                percent, line1, line2, line3 = self.get_current_status()
                self.ensure_background_progress(percent, line1, line2, line3)
                if self.USE_CUSTOM_WINDOW:
                    self.keep_progress_visible(percent, line1, line2, line3)
            except Exception as exc:
                self.log('Progress watchdog error: %s' % exc, xbmc.LOGWARNING)

            # Sleep in small pieces so Kodi shutdown is handled quickly.
            for _ in range(int(self.WATCHDOG_INTERVAL * 10)):
                if self._watchdog_stop.is_set() or self.monitor.abortRequested():
                    break
                xbmc.sleep(100)

        self.log('Dependency status window watchdog stopped.')

    def get_current_status(self):
        with self._status_lock:
            return self._current_status

    def set_current_status(self, percent, line1='', line2='', line3=''):
        percent = max(0, min(100, int(percent)))
        with self._status_lock:
            self._current_status = (percent, line1 or '', line2 or '', line3 or '')

    def ensure_background_progress(self, percent=None, line1='', line2='', line3=''):
        # DialogProgressBG is skin-controlled and cannot be resized by an addon. It *does*,
        # however, survive Kodi startup focus changes much better than custom windows, so keep
        # the text short and let Kodi own the always-visible top progress slot.
        try:
            if self.bg_progress is None:
                self.bg_progress = xbmcgui.DialogProgressBG()
                self.bg_progress.create(self.BG_HEADING, 'Please wait')
            if percent is not None:
                self.bg_progress.update(int(percent), self.BG_HEADING, self.compact_status(percent, line1, line2, line3))
        except Exception as exc:
            self.log('Could not update background dependency progress: %s' % exc, xbmc.LOGWARNING)
            self.bg_progress = None

    def compact_status(self, percent, line1='', line2='', line3=''):
        # Keep under the width used by most Kodi skins for DialogProgressBG. Long strings are
        # what made the top box unreadable in the previous build.
        def clean(text):
            return (text or '').replace('Installing dependency...', 'Installing').replace('Checking required dependencies...', 'Checking')

        def shorten(text, limit=34):
            text = clean(text).strip()
            if len(text) <= limit:
                return text
            if '.' in text and len(text) > limit:
                parts = text.split('.')
                # script.module.requests -> s.m.requests, plugin.video.foo -> p.v.foo
                text = '.'.join([(part[:1] if i < len(parts) - 1 else part) for i, part in enumerate(parts)])
                if len(text) <= limit:
                    return text
            if limit <= 3:
                return text[:limit]
            return text[:limit - 3] + '...'

        line1 = clean(line1)
        line2 = clean(line2)
        line3 = clean(line3)

        # Prefer the useful changing detail: current addon, installed count, retry countdown.
        if line2.startswith('Installed:'):
            count = line2.replace('Installed:', '').strip()
            if 'Retry in' in line3:
                retry = line3.split('.')[0].replace('Retry in', 'retry').strip()
                return '%s | %s' % (count, shorten(retry, 18))
            if 'Missing:' in line3:
                return '%s | missing deps' % count
            return count

        if line2 and (line2.startswith('plugin.') or line2.startswith('script.') or line2.startswith('service.') or line2.startswith('repository.') or line2.startswith('resource.')):
            if line1:
                return '%s: %s' % (shorten(line1, 12), shorten(line2, 34))
            return shorten(line2, 42)

        if line1:
            if line2:
                return '%s | %s' % (shorten(line1, 24), shorten(line2, 24))
            return shorten(line1, 48)

        return 'Please wait'

    def close_background_progress(self):
        if self.bg_progress:
            try:
                self.bg_progress.close()
            except Exception:
                pass
            self.bg_progress = None

    def keep_progress_visible(self, percent, line1='', line2='', line3=''):
        now = time.time()
        visible = self.progress_window_visible()

        if visible is True:
            self._hidden_since = 0
        elif visible is False:
            if not self._hidden_since:
                self._hidden_since = now
                self.log('Dependency status window is not visible. Forcing it back on screen.', xbmc.LOGWARNING)
        else:
            # Some Kodi builds do not expose a reliable visibility state for WindowDialog.
            # In that case we still re-show periodically, but we do not rebuild constantly.
            self._hidden_since = 0

        force = (visible is not True) or (now - self._last_show >= self.FORCE_RESHOW_INTERVAL)

        # If Kodi actually destroyed the dialog instead of merely hiding it, rebuild after a
        # few seconds. Rebuilding every heartbeat would flicker, because naturally there must be
        # a new way to annoy everyone.
        if (visible is False and self._hidden_since and
                now - self._hidden_since >= self.REBUILD_IF_HIDDEN_SECONDS and
                now - self._last_rebuild >= self.REBUILD_IF_HIDDEN_SECONDS):
            self.rebuild_progress_window()
            self._last_rebuild = now
            force = True

        self.ensure_progress(force=force)
        if self.dialog:
            try:
                self.dialog.update_status(percent, line1, line2, line3)
            except Exception as exc:
                self.log('Could not update dependency status window from watchdog: %s' % exc, xbmc.LOGWARNING)
                self.rebuild_progress_window()

    def progress_window_visible(self):
        if self.dialog is None:
            return False
        try:
            window_id = self.dialog.getId()
            if window_id:
                return bool(
                    xbmc.getCondVisibility('Window.IsActive(%s)' % window_id) or
                    xbmc.getCondVisibility('Window.IsVisible(%s)' % window_id)
                )
        except Exception:
            pass

        # If Kodi cannot report visibility for this custom dialog, report unknown.
        # The watchdog will still call show() periodically without constantly rebuilding it.
        return None

    def rebuild_progress_window(self):
        with self._ui_lock:
            try:
                if self.dialog:
                    self.dialog.close_window()
            except Exception:
                pass
            self.dialog = None
            self.ensure_progress(force=True)

    def ensure_progress(self, force=False):
        with self._ui_lock:
            try:
                if self.dialog is None:
                    self.dialog = DependencyStatusWindow(self.DIALOG_HEADING, self.dialog_bg)

                now = time.time()
                if force or now - self._last_show >= self.FORCE_RESHOW_INTERVAL:
                    self.dialog.show()
                    self._last_show = now
            except Exception as exc:
                self.log('Could not create/show dependency status window: %s' % exc, xbmc.LOGWARNING)
                try:
                    self.dialog = DependencyStatusWindow(self.DIALOG_HEADING, self.dialog_bg)
                    self.dialog.show()
                    self._last_show = time.time()
                except Exception as second_exc:
                    self.log('Could not recreate dependency status window: %s' % second_exc, xbmc.LOGWARNING)
                    self.dialog = None

    def update_progress(self, percent, line1='', line2='', line3=''):
        self.set_current_status(percent, line1, line2, line3)
        self.ensure_background_progress(percent, line1, line2, line3)
        if not self.USE_CUSTOM_WINDOW:
            return
        self.ensure_progress(force=False)
        if self.dialog is None:
            return

        try:
            self.dialog.update_status(percent, line1, line2, line3)
        except Exception as exc:
            self.log('Could not update dependency status window: %s' % exc, xbmc.LOGWARNING)
            self.rebuild_progress_window()

    def close_progress(self):
        self._progress_active = False
        self._watchdog_stop.set()
        try:
            if (self._watchdog_thread and self._watchdog_thread.is_alive() and
                    threading.current_thread() is not self._watchdog_thread):
                self._watchdog_thread.join(2.0)
        except Exception:
            pass
        self._watchdog_thread = None

        with self._ui_lock:
            if self.dialog:
                try:
                    self.dialog.close_window()
                except Exception:
                    pass
                self.dialog = None
        self.close_background_progress()

    def join_status_lines(self, line1='', line2='', line3=''):
        lines = [line for line in (line1, line2, line3) if line]
        return ' | '.join(lines)

    def percent(self, installed_count, total):
        if total <= 0:
            return 0
        return int((float(installed_count) / float(total)) * 100)

    def format_addon_list(self, addon_ids, max_items=3):
        if not addon_ids:
            return 'None'
        visible = addon_ids[:max_items]
        extra = len(addon_ids) - len(visible)
        text = ', '.join(visible)
        if extra > 0:
            text += ' +%s more' % extra
        return text

    def isinstalled(self, addonid):
        if xbmc.getCondVisibility('System.HasAddon(%s)' % addonid):
            return True

        query = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': addonid,
                'properties': ['installed']
            }
        }

        try:
            response = xbmc.executeJSONRPC(json.dumps(query))
            details = json.loads(response)
            return bool(details.get('result', {}).get('addon', {}).get('installed'))
        except Exception as exc:
            self.log('Could not check install status for %s: %s' % (addonid, exc), xbmc.LOGWARNING)
            return False
