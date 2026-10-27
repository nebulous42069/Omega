# -*- coding: utf-8 -*-
"""
	ReAuthorize - Device Authorization (QR)
	Generic modal dialog for OAuth device-code flows: shows a scannable
	QR code alongside the verification URL and code, and polls in a
	background thread until poll_func() reports success/failure or the
	code expires or the user cancels.

	doModal() is used deliberately, not show() - a modeless window isn't
	guaranteed to reliably deliver the Cancel click back to the script
	when opened from a background script invocation, which let the poll
	loop keep running invisibly after Cancel and blocked every other
	ReAuthorize action (Kodi won't launch a second instance of the same
	script addon while one is still alive). doModal() is Kodi's properly
	input-responsive dialog mode, so the background thread here owns the
	polling and calls close() itself when done.
"""

import threading
import xbmc
import xbmcgui
import xbmcaddon

ADDON_ID = 'script.module.reauthorize'


class DeviceAuthDialog(xbmcgui.WindowXMLDialog):

	def __init__(self, *args, **kwargs):
		super(DeviceAuthDialog, self).__init__(*args)  # positional only - Kodi C extension ignores extra kwargs
		self.service_name = ''
		self.qr_url = ''
		self.verification_url = ''
		self.user_code = ''
		self.poll_func = None
		self.interval = 5
		self.expires_in = 900
		self.cancelled = False
		self.success = False
		self._closed = False
		self._thread = None

	def onInit(self):
		self.getControl(101).setLabel('Authorize %s' % self.service_name)
		self.getControl(102).setLabel('Go to: %s' % self.verification_url)
		self.getControl(103).setLabel(self.user_code)
		self.getControl(104).setLabel('Waiting for you to approve on your phone or browser...')
		try:
			self.getControl(100).setImage(self.qr_url)
		except Exception:
			pass
		self._thread = threading.Thread(target=self._poll_loop)
		self._thread.daemon = True
		self._thread.start()

	def _poll_loop(self):
		elapsed = 0
		while elapsed < self.expires_in and not self.cancelled:
			xbmc.sleep(max(self.interval, 1) * 1000)
			if self.cancelled:
				return
			elapsed += self.interval
			try:
				result = self.poll_func()
			except Exception:
				result = None
			if result is True:
				self.success = True
				self._finish('Authorized!')
				return
			if result is False:
				self._finish('Authorization failed or was denied.')
				return
			# result is None - still pending, keep polling
		if not self.cancelled:
			self._finish('Code expired - please try again.')

	def _finish(self, message):
		if self.cancelled:
			return
		try:
			self.getControl(104).setLabel(message)
		except Exception:
			pass
		xbmc.sleep(900)
		self.close()

	def close(self):
		# The Cancel button and the poll thread can both decide to close
		# at nearly the same time - make it safe to call more than once.
		if self._closed:
			return
		self._closed = True
		super(DeviceAuthDialog, self).close()

	def onClick(self, control_id):
		if control_id == 200:
			self.cancelled = True
			self.close()

	def onAction(self, action):
		if action.getId() in (9, 10, 92):
			self.cancelled = True
			self.close()


def run(service_name, qr_url, verification_url, user_code, poll_func, interval=5, expires_in=900):
	"""
	Shows the QR/code device-authorization dialog and blocks (doModal)
	until the flow ends. poll_func() is called roughly every `interval`
	seconds on a background thread - it should return True (approved,
	stop polling), False (denied/failed, stop polling), or None (still
	pending, keep polling). Returns True if authorization succeeded.
	"""
	addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
	w = DeviceAuthDialog('device_auth.xml', addon_path, 'default', '1080i')
	w.service_name = service_name
	w.qr_url = qr_url
	w.verification_url = verification_url
	w.user_code = user_code
	w.poll_func = poll_func
	w.interval = interval
	w.expires_in = expires_in
	w.doModal()
	success = w.success
	del w
	return success
