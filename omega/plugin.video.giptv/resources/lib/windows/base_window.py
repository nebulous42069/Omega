# -*- coding: utf-8 -*-
import xbmc
import xbmcgui


class BaseDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(BaseDialog, self).__init__(*args, **kwargs)
        self.result = None
        self._closing = False
        self.closing_actions = (9, 10, 13, 92)

    def run(self):
        self.doModal()
        return self.result

    def _finish(self, result=None):
        if self._closing:
            return
        self._closing = True
        self.result = result
        xbmc.sleep(50)
        self.close()

    def onAction(self, action):
        try:
            action_id = action.getId()
        except Exception:
            action_id = action

        if action_id in self.closing_actions:
            self._finish(None)

    def set_prop(self, key, value):
        self.setProperty(key, "" if value is None else str(value))

    def log(self, msg, level=xbmc.LOGINFO):
        xbmc.log("[GIPTV][WINDOW] {}".format(msg), level)
