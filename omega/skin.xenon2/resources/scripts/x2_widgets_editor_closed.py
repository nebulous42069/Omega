# -*- coding: utf-8 -*-
"""Rebuild after the complete customizer session closes, not nested editors."""
import time
import uuid
import xbmc
import xbmcgui

PENDING = 'X2Widgets.PendingEditorBuild'
CLOSE_GRACE = 2.0
BUILD = 'RunScript(script.skinshortcuts,type=buildxml&mainmenuID=9000&levels=2&group=mainmenu|buttonmenu)'


def main():
    home = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()
    token = uuid.uuid4().hex
    # A newer unload supersedes an earlier pending request. This also combines
    # rapid nested-dialog transitions into one eventual build.
    home.setProperty(PENDING, token)
    closed_since = None
    try:
        while not monitor.abortRequested():
            if home.getProperty(PENDING) != token:
                return
            now = time.monotonic()
            if xbmc.getCondVisibility('Window.IsVisible(script-skinshortcuts.xml)'):
                closed_since = None
            elif closed_since is None:
                closed_since = now
            elif now - closed_since >= CLOSE_GRACE:
                # Check ownership and visibility again immediately before building.
                if home.getProperty(PENDING) != token:
                    return
                if xbmc.getCondVisibility('Window.IsVisible(script-skinshortcuts.xml)'):
                    closed_since = None
                    continue
                xbmc.log('[X2 Edit Widgets] Customizer session closed; requesting normal menu build.', xbmc.LOGINFO)
                xbmc.executebuiltin(BUILD)
                return
            if monitor.waitForAbort(0.2):
                return
    finally:
        if home.getProperty(PENDING) == token:
            home.clearProperty(PENDING)


if __name__ == '__main__':
    main()
