# -*- coding: utf-8 -*-
"""
	Auth Station
"""

from reauthorize.windows.base import BaseDialog

ACTION_MOVE_UP   = 3
ACTION_MOVE_DOWN = 4
SCROLL_LINES     = 10

class TextViewerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		super(TextViewerXML, self).__init__(*args, **kwargs)
		self.window_id  = 2000
		self.heading    = kwargs.get('heading')
		self.text       = kwargs.get('text')
		self._scroll_pos = 0

	def onInit(self):
		super(TextViewerXML, self).onInit()
		self._scroll_pos = 0
		self.set_properties()

	def run(self):
		import xbmc
		xbmc.sleep(300)
		self.doModal()

	def onAction(self, action):
		action_id = action.getId()
		if action_id in self.closing_actions or action_id in self.selection_actions:
			self.close()
		elif action_id == ACTION_MOVE_UP:
			self._scroll_pos = max(0, self._scroll_pos - SCROLL_LINES)
			self.getControl(self.window_id).scroll(self._scroll_pos)
		elif action_id == ACTION_MOVE_DOWN:
			self._scroll_pos += SCROLL_LINES
			self.getControl(self.window_id).scroll(self._scroll_pos)

	def onClick(self, control_id):
		if control_id == 2001:
			self.close()

	def set_properties(self):
		self.setProperty('accountmgr.text', self.text)
		self.setProperty('accountmgr.heading', self.heading)
