# -*- coding: utf-8 -*-
"""Keep selector choices per profile/menu; expose the current choice to skin XML."""
import hashlib
import json
import os
import uuid
import sys

import xbmc
import xbmcgui
import xbmcvfs

ACTIVE = 'X2Selector.Active'
OWNER = 'X2Selector.Owner'


VALUES = frozenset(['hide'] + [str(n) for n in range(1, 16)])


def state_path(key):
    # A file per menu avoids read/modify/write races between different menus.
    folder = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon2/widget_selector/')
    return os.path.join(folder, key + '.json')


def load_choice(key):
    try:
        with open(state_path(key), encoding='utf-8') as handle:
            value = json.load(handle).get('selected')
        return value if isinstance(value, str) and value in VALUES else ''
    except (OSError, ValueError, TypeError, AttributeError):
        return ''


def save_choice(key, value):
    if value not in VALUES:
        return
    temporary = None
    try:
        path = state_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temporary = path + '.' + uuid.uuid4().hex + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as handle:
            json.dump({'selected': value}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        # The live selector must remain usable even if the profile cannot be written.
        xbmc.log('Xenon widget selector: could not save menu selection', xbmc.LOGWARNING)
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.remove(temporary)
            except OSError:
                pass


def saved_choice(home, key):
    value = home.getProperty(key)
    return value if value in VALUES else load_choice(key)


def menu_key():
    profile = xbmc.getInfoLabel('System.ProfileName')
    menu = (xbmc.getInfoLabel('Container(9000).ListItem.Property(submenuVisibility)')
            or xbmc.getInfoLabel('Container(9000).ListItem.Property(id)')
            or xbmc.getInfoLabel('Container(9000).CurrentItem'))
    if not menu:
        return None
    payload = json.dumps([profile, menu], ensure_ascii=True).encode('utf-8')
    return 'X2Selector.Menu.' + hashlib.sha256(payload).hexdigest()


def sync():
    """Called by the existing Home watcher, including on its first tick."""
    key = menu_key()
    if key is None:
        return
    home = xbmcgui.Window(10000)
    if home.getProperty(OWNER) != key:
        # An unset menu uses the skin's existing first-configured-widget fallback.
        # Never migrate the old global value: it may be the buggy global 'hide'.
        value = saved_choice(home, key)
        home.setProperty(key, value)
        home.setProperty(ACTIVE, value)
        home.setProperty(OWNER, key)


def select(value):
    if value not in VALUES:
        return
    key = menu_key()
    if key is None:
        return
    home = xbmcgui.Window(10000)
    home.setProperty(key, value)
    home.setProperty(ACTIVE, value)
    home.setProperty(OWNER, key)
    save_choice(key, value)


def swap(source, target):
    """Keep the saved choice with its widget when the editor swaps slots."""
    key = menu_key()
    if key is None:
        return
    home = xbmcgui.Window(10000)
    if str(source) not in VALUES or str(target) not in VALUES:
        return
    active = saved_choice(home, key)
    value = str(target) if active == str(source) else str(source) if active == str(target) else active
    if value:
        home.setProperty(key, value)
        save_choice(key, value)
        if home.getProperty(OWNER) == key:
            home.setProperty(ACTIVE, value)


if __name__ == '__main__' and len(sys.argv) == 2:
    select(sys.argv[1])
