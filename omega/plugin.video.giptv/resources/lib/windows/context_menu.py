# -*- coding: utf-8 -*-
import xbmcgui
from resources.lib.windows.base_window import BaseDialog


class GIPTVContextMenu(BaseDialog):
    LIST_ID = 1000

    def __init__(self, *args, **kwargs):
        super(GIPTVContextMenu, self).__init__(*args, **kwargs)
        self.title = kwargs.get("title", "Menu")
        self.items = kwargs.get("items", [])
        self._closing = False

    def onInit(self):
        self.set_prop("menu_title", self.title)

        list_control = self.getControl(self.LIST_ID)
        list_control.reset()

        for item in self.items:
            li = xbmcgui.ListItem(label=item.get("label", ""))
            li.setProperty("action_key", item.get("key", ""))
            li.setProperty("description", item.get("description", ""))

            icon = item.get("icon", "")
            if icon:
                li.setArt({"icon": icon, "thumb": icon})

            list_control.addItem(li)

        if self.items:
            self.setFocusId(self.LIST_ID)

    def _finish(self, result=None):
        if self._closing:
            return
        self._closing = True
        self.result = result
        self.close()

    def onClick(self, controlId):
        if controlId != self.LIST_ID:
            return

        item = self.getControl(self.LIST_ID).getSelectedItem()
        self._finish(item.getProperty("action_key") if item else None)

    def onAction(self, action):
        try:
            action_id = action.getId()
        except Exception:
            action_id = action

        if action_id in self.closing_actions:
            self._finish(None)
            return

        super(GIPTVContextMenu, self).onAction(action)
