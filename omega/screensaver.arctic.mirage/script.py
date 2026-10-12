# -*- coding: utf-8 -*-
import sys

import xbmc
import xbmcaddon

from resources.lib import utils

_addon = xbmcaddon.Addon()
_id = _addon.getAddonInfo('id')


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


def run_and_sync(call):
    before_path = utils.get_skin_string(utils.SKIN_PATH_STRING)
    before_name = utils.get_skin_string(utils.SKIN_NAME_STRING)

    xbmc.executebuiltin(call, wait=True)

    # In normal Kodi builds, wait=True returns after Skin Shortcuts / Skin.SetString
    # finishes. The short poll below covers builds where the skin string is
    # updated slightly after the called script returns.
    for _ in range(20):
        path = utils.get_skin_string(utils.SKIN_PATH_STRING)
        name = utils.get_skin_string(utils.SKIN_NAME_STRING)
        if path != before_path or name != before_name or path or name:
            break
        xbmc.sleep(250)

    return utils.sync_addon_settings_from_skinstrings()


def change_label():
    return 'Skin.SetString({})'.format(utils.SKIN_NAME_STRING)


def choose_path():
    return ('RunScript(script.skinshortcuts,'
            'type=widgets'
            '&showNone=False'
            '&skinWidgetName={0}'
            '&skinWidgetPath={1})'.format(utils.SKIN_NAME_STRING, utils.SKIN_PATH_STRING))


if __name__ == '__main__':
    params = get_params()
    mode = params.get('mode')

    call = None
    if mode == 'label':
        call = change_label()
    elif mode == 'choose':
        call = choose_path()

    if call:
        run_and_sync(call)
    elif mode == 'installfonts':
        utils.install_mirage_fonts_into_active_skin()
    elif mode == 'restorefonts':
        utils.restore_active_skin_fontxml_backup()
    else:
        utils.log('No valid mode supplied to settings script: {}'.format(sys.argv))
