# -*- coding: utf-8 -*-
"""
	Debrid Manager
"""

from debridmgr.windows.base import BaseDialog

class TextViewerXML(BaseDialog):
	def __init__(self, *args, **kwargs):
		super(TextViewerXML, self).__init__(self, args)
		self.window_id = 2060
		self.heading = kwargs.get('heading')
		self.text = kwargs.get('text')

	def onInit(self):
		super(TextViewerXML, self).onInit()
		self.set_properties()
		self.setFocusId(self.window_id)

	def run(self):
		self.doModal()

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.close()

	def set_properties(self):
		self.setProperty('debridmgr.text', self.text)
		self.setProperty('debridmgr.heading', self.heading)
