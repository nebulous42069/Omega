# -*- coding: utf-8 -*-
"""Reset Home rows only when the selected main-menu item changes."""
import os
import re
import time
import xml.etree.ElementTree as ET
import xbmc
import xbmcgui
import xbmcvfs
from x2_selector_state import sync as sync_selector


class HomeRowFocus:
    def __init__(self):
        self.menu = None
        self.ids = {9010}
        self.pending = set()
        self.stamp = None
        self.scan_at = 0

    def refresh_ids(self, now):
        if now < self.scan_at:
            return
        self.scan_at = now + 1
        path = xbmcvfs.translatePath('special://skin/16x9/script-skinshortcuts-includes.xml')
        try:
            stamp = os.stat(path).st_mtime_ns
            if stamp == self.stamp:
                return
            ids = {9010}
            for include in ET.parse(path).getroot().findall('include'):
                # Includes both wrappers and per-profile generated templates.
                if not re.match(r'^skinshortcuts-template-widget[12](?:X2S(?:10|[2-9]))?(?:-|$)', include.get('name', '')):
                    continue
                for control in include.iter('control'):
                    cid = control.get('id', '')
                    if control.get('type') in ('list','panel','fixedlist','wraplist') and cid.isdigit():
                        ids.add(int(cid))
            if self.menu is not None:
                self.pending.update(ids - self.ids)
            self.ids, self.stamp = ids, stamp
        except (OSError, ValueError, ET.ParseError):
            pass

    def tick(self, now):
        if not xbmc.getCondVisibility('Window.IsActive(home)'):
            return
        sync_selector()
        self.refresh_ids(now)
        key = (xbmc.getInfoLabel('System.ProfileName'),
               xbmc.getInfoLabel('Container(9000).ListItem.Property(submenuVisibility)'),
               xbmc.getInfoLabel('Container(9000).CurrentItem'))
        if not (key[1] or key[2]):
            return
        if self.menu is None:
            # Do not disturb the current Home visit when the watcher starts.
            self.menu = key
        elif key != self.menu:
            self.menu = key
            self.pending = set(self.ids)
        try:
            focused = xbmcgui.Window(10000).getFocusId()
        except RuntimeError:
            return
        for cid in list(self.pending):
            if focused != cid and not xbmc.getCondVisibility('Control.IsVisible(%d)' % cid):
                continue
            try:
                current = int(xbmc.getInfoLabel('Container(%d).CurrentItem' % cid) or 0)
                count = int(xbmc.getInfoLabel('Container(%d).NumItems' % cid) or 0)
            except (TypeError, ValueError):
                continue
            if count <= 0 or current <= 0:
                continue
            if current > 1:
                # Exact displacement avoids wrapping through the list.
                xbmc.executebuiltin('Control.Move(%d,%d)' % (cid, 1-current))
            if focused == cid:
                # Reset once on entry; subsequent browsing retains its position.
                self.pending.discard(cid)


def watch(stop):
    monitor = xbmc.Monitor()
    state = HomeRowFocus()
    while not stop.is_set() and not monitor.abortRequested():
        try:
            state.tick(time.monotonic())
        except Exception as exc:
            xbmc.log('[X2 Home focus] Reset skipped: %s' % type(exc).__name__, xbmc.LOGDEBUG)
        if monitor.waitForAbort(0.1):
            break
