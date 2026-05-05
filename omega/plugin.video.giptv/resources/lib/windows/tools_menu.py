# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
from resources.lib.windows.base_window import BaseDialog


class GIPTVToolsMenu(BaseDialog):
    LIST_ID = 1000

    def __init__(self, *args, **kwargs):
        super(GIPTVToolsMenu, self).__init__(*args, **kwargs)
        self.items = kwargs.get("items", [])
        self._closing = False

    def onInit(self):
        self.set_prop("menu_title", "GIPTV Tools")

        list_control = self.getControl(self.LIST_ID)
        list_control.reset()

        for item in self.items:
            li = xbmcgui.ListItem(label=item.get("label", ""))
            li.setProperty("action_key", item.get("key", ""))
            list_control.addItem(li)

        if self.items:
            self.setFocusId(self.LIST_ID)

    def _finish(self, result=None):
        if self._closing:
            return
        self._closing = True
        self.result = result
        xbmc.sleep(50)
        self.close()

    def onClick(self, controlId):
        if controlId != self.LIST_ID:
            return

        item = self.getControl(self.LIST_ID).getSelectedItem()
        action_key = item.getProperty("action_key") if item else None
        self._finish(action_key)

    def onAction(self, action):
        try:
            action_id = action.getId()
        except Exception:
            action_id = action

        if action_id in self.closing_actions:
            self._finish(None)
            return

        super(GIPTVToolsMenu, self).onAction(action)
