# -*- coding: utf-8 -*-
"""Keep selector choices per profile/menu; expose the current choice to skin XML."""
import hashlib
import json
import sys

import xbmc
import xbmcgui

ACTIVE = 'X2Selector.Active'
OWNER = 'X2Selector.Owner'


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
        home.setProperty(ACTIVE, home.getProperty(key))
        home.setProperty(OWNER, key)


def select(value):
    if value not in ['hide'] + [str(n) for n in range(1, 16)]:
        return
    key = menu_key()
    if key is None:
        return
    home = xbmcgui.Window(10000)
    home.setProperty(key, value)
    home.setProperty(ACTIVE, value)
    home.setProperty(OWNER, key)


def swap(source, target):
    """Keep the saved choice with its widget when the editor swaps slots."""
    key = menu_key()
    if key is None:
        return
    home = xbmcgui.Window(10000)
    active = home.getProperty(key)
    value = str(target) if active == str(source) else str(source) if active == str(target) else active
    if value:
        home.setProperty(key, value)
        if home.getProperty(OWNER) == key:
            home.setProperty(ACTIVE, value)


if __name__ == '__main__' and len(sys.argv) == 2:
    select(sys.argv[1])
