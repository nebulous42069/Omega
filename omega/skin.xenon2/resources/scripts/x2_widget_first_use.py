# SPDX-License-Identifier: GPL-2.0-or-later
"""Remember widget first-use gates for the current Kodi session, not on disk."""
import os
import time
import uuid
import xml.etree.ElementTree as ET
import xbmc
import xbmcgui
import xbmcvfs

MARKER = '] | String.IsEqual(Window(Home).Property(X2WidgetLoaded.'


def read_triggers(path):
    tree = ET.parse(path)
    triggers = {}
    for variable in tree.getroot().iter('variable'):
        name = variable.get('name', '')
        if not name.startswith('X2OnDemand'):
            continue
        value = variable.find('value')
        condition = value.get('condition', '') if value is not None else ''
        if condition.startswith('[') and MARKER in condition:
            triggers[name] = condition[1:].split(MARKER, 1)[0]
    return triggers


def run():
    profile = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon2/')
    os.makedirs(profile, exist_ok=True)
    lock = os.path.join(profile, 'widget-first-use.lock')
    token = uuid.uuid4().hex
    try:
        with open(lock, 'x') as stream:
            stream.write(token)
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(lock) < 60:
                return
            os.unlink(lock)
            with open(lock, 'x') as stream:
                stream.write(token)
        except (FileExistsError, FileNotFoundError):
            return
    window = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()
    path = xbmcvfs.translatePath('special://skin/16x9/script-skinshortcuts-includes.xml')
    triggers = {}
    stamp = None
    scan_at = heartbeat = 0
    profile_name = xbmc.getInfoLabel('System.ProfileName')
    try:
        while not monitor.abortRequested() and xbmc.getSkinDir() == 'skin.xenon2':
            now = time.monotonic()
            if now - heartbeat >= 5:
                os.utime(lock, None)
                heartbeat = now
            current_profile = xbmc.getInfoLabel('System.ProfileName')
            if current_profile != profile_name:
                # Profile changes must not pre-load another profile's widget slots.
                for name in triggers:
                    window.clearProperty('X2WidgetLoaded.' + name)
                profile_name = current_profile
                stamp = None
            if now >= scan_at:
                scan_at = now + 2
                try:
                    stat = os.stat(path)
                    changed = (stat.st_mtime_ns, stat.st_size)
                    if changed != stamp:
                        # Re-read after the skinshortcuts builder finishes replacing its XML.
                        updated = read_triggers(path)
                        if updated:
                            triggers = updated
                            stamp = changed
                except (OSError, ET.ParseError):
                    pass
            active = xbmc.getCondVisibility('Window.IsActive(home)')
            if active:
                for name, condition in triggers.items():
                    key = 'X2WidgetLoaded.' + name
                    if window.getProperty(key) != 'true' and xbmc.getCondVisibility(condition):
                        window.setProperty(key, 'true')
            if monitor.waitForAbort(0.1 if active else 0.5):
                break
    finally:
        try:
            with open(lock) as stream:
                owned = stream.read() == token
            if owned:
                os.unlink(lock)
        except OSError:
            pass


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        xbmc.log('[Xenon2 widget first use] ' + type(error).__name__ + ': ' + str(error), xbmc.LOGERROR)
