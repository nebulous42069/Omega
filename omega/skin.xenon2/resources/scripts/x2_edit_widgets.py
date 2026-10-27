# -*- coding: utf-8 -*-
"""Open Xenon 2's widget settings for the currently selected Home menu."""
import re
import time
import xbmc
import xbmcgui


def plain(value):
    value = value or ''
    value = re.sub(r'\[(?:/?(?:B|I|UPPERCASE|LOWERCASE|CAPITALIZE)|/?COLOR(?: [^\]]*)?)\]', '', value, flags=re.I)
    return value.strip().casefold()


def home_target():
    def prop(name):
        return xbmc.getInfoLabel('Container(9000).ListItem.Property(%s)' % name).strip()
    return {'key':prop('submenuVisibility'),
            'label':xbmc.getInfoLabel('Container(9000).ListItem.Label').strip(),
            'path':prop('translatedPath') or prop('path')}


def match_menu(target, items):
    """Use a stable shortcut identity, then the resolved label/action pair.

    Do not use the Home position as the editor can include hidden/disabled items.
    Return None rather than selecting a different menu in an ambiguous case.
    """
    key = target.get('key', '')
    if key:
        matches = [i for i, item in enumerate(items)
                   if key in (item.getProperty('labelID'), item.getProperty('submenuVisibility'))]
        if len(matches) == 1:
            return matches[0]
    label = plain(target.get('label'))
    path = target.get('path', '')
    matches = [i for i, item in enumerate(items) if label and plain(item.getLabel()) == label]
    if len(matches) == 1:
        return matches[0]
    def same_path(item):
        return path and path in (item.getProperty('translatedPath'), item.getProperty('path'), item.getPath())
    narrowed = [i for i in matches if same_path(items[i])]
    if len(narrowed) == 1:
        return narrowed[0]
    path_matches = [i for i, item in enumerate(items) if same_path(item)]
    if len(path_matches) == 1:
        return path_matches[0]
    return None


class LiveMenuItem:
    """Read the actual GUI item, not a new ControlList wrapper's item cache."""
    def __init__(self, index):
        self.prefix = 'Container(211).ListItemAbsolute(%d).' % index
    def getLabel(self):
        return xbmc.getInfoLabel(self.prefix + 'Label')
    def getProperty(self, name):
        return xbmc.getInfoLabel(self.prefix + 'Property(%s)' % name)
    def getPath(self):
        return self.getProperty('path')


def live_count():
    try:
        return int(xbmc.getInfoLabel('Container(211).NumItems') or 0)
    except ValueError:
        return 0


def current_index():
    try:
        return int(xbmc.getInfoLabel('Container(211).CurrentItem') or 0) - 1
    except ValueError:
        return -1


def editor_window():
    visible = xbmc.getCondVisibility('Window.IsVisible(script-skinshortcuts.xml)')
    for wid in (xbmcgui.getCurrentWindowDialogId(), xbmcgui.getCurrentWindowId()):
        try:
            window = xbmcgui.Window(wid)
            group = window.getProperty('groupname')
            if group == 'mainmenu' or (visible and not group and wid > 10000):
                return window
        except RuntimeError:
            pass
    return None


def notify(message):
    xbmcgui.Dialog().notification('Edit Widgets', message, xbmcgui.NOTIFICATION_INFO, 5000)


def open_editor(monitor, session):
    target = home_target()
    if not target['key'] and not target['label']:
        return
    xbmc.executebuiltin('RunScript(script.skinshortcuts,type=manage&group=mainmenu)')
    deadline = time.monotonic() + 20
    entered = False
    while time.monotonic() < deadline and not monitor.abortRequested():
        window = editor_window()
        if window is None:
            if entered:
                return
        else:
            entered = True
            session[:] = [window]
            count = live_count()
            items = [LiveMenuItem(i) for i in range(count)]
            if items and any(item.getLabel() for item in items):
                index = match_menu(target, items)
                if index is None:
                    notify('Select the Home menu to edit; no unique match was found.')
                    return
                xbmc.executebuiltin('Control.SetFocus(211,%d,absolute)' % index)
                selected_deadline = time.monotonic() + 4
                while time.monotonic() < selected_deadline:
                    if monitor.waitForAbort(.1) or editor_window() is None:
                        return
                    if current_index() == index:
                        break
                else:
                    notify('The requested menu could not be selected. Please select it manually.')
                    return
                # Verify the menu, then leave the full settings list open.
                if match_menu(target, [LiveMenuItem(current_index())]) != 0:
                    notify('The menu selection changed. Please select the menu manually.')
                    return
                xbmcgui.Window(10000).clearProperty('skinshortcuts-management-widget')
                if monitor.waitForAbort(.15) or editor_window() is None:
                    return
                xbmc.executebuiltin('Control.SetFocus(800)')
                xbmc.log('[X2 Edit Widgets] Selected menu index %d; focused Widget 1 button.' % index, xbmc.LOGINFO)
                return
        if monitor.waitForAbort(.1):
            return
    if not monitor.abortRequested():
        notify('The menu customizer did not become ready. Please try again.')
        xbmc.log('[X2 Edit Widgets] Live list did not become available.', xbmc.LOGWARNING)


def main():
    # Open/select/focus, then exit. Never retain an editor window while the
    # user browses nested pickers or Kodi destroys/rebuilds the skin.
    open_editor(xbmc.Monitor(), [])


if __name__ == '__main__':
    main()
