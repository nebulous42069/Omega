# SPDX-License-Identifier: GPL-2.0-or-later
"""Open the flavor picker once in a new Kodi process, after Home is ready."""
import json
import os
import sys
import time
import xbmc
import xbmcvfs

SETTING = 'Xenon.FlavorFirstRun'


def session_id():
    pid = os.getpid()
    started = ''
    if sys.platform == 'win32':
        # Include process birth time so reused Windows PIDs do not suppress a boot.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        times = [wintypes.FILETIME() for _ in range(4)]
        if kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ctypes.byref(t) for t in times)):
            started = str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
    else:
        try:
            with open('/proc/self/stat') as stream:
                fields = stream.read().rsplit(')', 1)[1].split()
            started = fields[19]  # field 22, process start ticks
        except (OSError, IndexError):
            pass
    return '%s:%s' % (pid, started)


def first_home_this_session(profile):
    path = os.path.join(profile, 'first-run-session.json')
    current = session_id()
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as stream:
            if json.load(stream).get('session') == current:
                return False
    os.makedirs(profile, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as stream:
        json.dump({'session': current}, stream)
    os.replace(path + '.tmp', path)
    return True


def main():
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/')
    # Record every session, even with the toggle off, so enabling it later
    # waits for the next boot rather than the next Home/skin reload.
    if not first_home_this_session(profile):
        return
    if not xbmc.getCondVisibility('Skin.HasSetting(%s)' % SETTING):
        return
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 60
    while not xbmc.getCondVisibility('Window.IsVisible(home)'):
        if time.monotonic() >= deadline or monitor.waitForAbort(0.1):
            return
    if monitor.waitForAbort(1.0):
        return
    # Consume before launching to prevent repeated popups during flavor reloads.
    xbmc.executebuiltin('Skin.Reset(%s)' % SETTING, True)
    xbmc.executebuiltin('RunScript(special://home/addons/skin.xenon/resources/scripts/flavors.py)')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        xbmc.log('Xenon first run: ' + type(error).__name__, xbmc.LOGERROR)
