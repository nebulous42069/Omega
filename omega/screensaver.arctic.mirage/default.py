# -*- coding: utf-8 -*-
import sys

import xbmc
import xbmcaddon

from resources.lib import utils
from resources.lib.screensaver import Screensaver

_addon = xbmcaddon.Addon()
_path = _addon.getAddonInfo('path')
_xml = 'screensaver-arctic-mirage-addon.xml'


if __name__ == '__main__':
    try:
        utils.sync_pending_widget_selection()
    except Exception as exc:
        utils.log('Could not recover widget selection: {}'.format(exc), xbmc.LOGWARNING)

    screensaver_gui = Screensaver(_xml, _path, 'Default', '1080i')
    try:
        screensaver_gui.doModal()
    finally:
        # Restore normal idle screensaver activation on every exit path.
        screensaver_gui._capture_stop = True
        screensaver_gui.release_input_control()

    # Launch the captured item only after the modal dialog has closed.
    try:
        if screensaver_gui.should_open_info_after_close():
            xbmc.sleep(250)
            screensaver_gui.open_last_item_info()
    except Exception as exc:
        utils.log('Post-screensaver action failed: {}'.format(exc), xbmc.LOGERROR)

    del screensaver_gui
    sys.modules.clear()
