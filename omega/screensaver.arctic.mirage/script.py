# -*- coding: utf-8 -*-
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import utils

_addon = xbmcaddon.Addon()


def get_params():
    params = {}
    for arg in sys.argv[1:]:
        if not arg:
            continue
        arg = arg.lstrip('?')
        for part in arg.split('&'):
            if '=' not in part:
                continue
            key, value = part.split('=', 1)
            if key:
                params[key] = value
    return params


def pick_widget():
    utils.prepare_widget_picker()
    xbmc.executebuiltin(choose_path(), wait=True)

    # RunScript may return while Skin Shortcuts is still loading or showing
    # its picker. Leave the baseline in the skin so startup can collect any
    # selection that arrives after this script exits.
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 10
    while not monitor.abortRequested():
        if xbmc.getCondVisibility('System.HasActiveModalDialog'):
            deadline = time.monotonic() + 2
        elif time.monotonic() >= deadline:
            break
        if utils.sync_pending_widget_selection():
            show_widget_path()
            return
        if monitor.waitForAbort(0.25):
            return
    if not monitor.abortRequested() and utils.sync_pending_widget_selection():
        show_widget_path()


def show_widget_path():
    path = utils.get_active_widget_path()
    xbmcgui.Dialog().textviewer(_addon.getLocalizedString(32012),
                               path or _addon.getLocalizedString(32013))


def edit_widget_path():
    keyboard = xbmc.Keyboard(utils.get_active_widget_path(), _addon.getLocalizedString(32010))
    keyboard.doModal()
    if keyboard.isConfirmed():
        utils.save_manual_widget_path(keyboard.getText())
        show_widget_path()


def choose_path():
    return ('RunScript(script.skinshortcuts,'
            'type=widgets'
            '&showNone=False'
            '&skinWidgetName={0}'
            '&skinWidgetPath={1})'.format(utils.SKIN_NAME_STRING, utils.SKIN_PICKER_PATH))


if __name__ == '__main__':
    params = get_params()
    mode = params.get('mode')

    if mode == 'showpath':
        show_widget_path()
    elif mode in ('choose', 'editpath'):
        try:
            if mode == 'choose':
                pick_widget()
            else:
                edit_widget_path()
        except OSError as exc:
            utils.log('Could not save widget path in the add-on folder: {}'.format(exc),
                      xbmc.LOGERROR)
            xbmcgui.Dialog().ok(_addon.getAddonInfo('name'), _addon.getLocalizedString(32011))
    elif mode == 'installfonts':
        utils.install_mirage_fonts_into_active_skin()
    elif mode == 'restorefonts':
        utils.restore_active_skin_fontxml_backup()
    else:
        utils.log('No valid mode supplied to settings script: {}'.format(sys.argv))
