# -*- coding: utf-8 -*-
"""
	Diggz Account Manager - Device Authorization (QR)
	Generic modal dialog for OAuth device-code flows: shows a scannable
	QR code alongside the verification URL and code, and polls in a
	background thread until poll_func() reports success/failure or the
	code expires or the user cancels.

	doModal() is used deliberately, not show() - a modeless window isn't
	guaranteed to reliably deliver the Cancel click back to the script
	when opened from a background script invocation, which let the poll
	loop keep running invisibly after Cancel and blocked every other
	Diggz Account Manager action (Kodi won't launch a second instance of the same
	script addon while one is still alive). doModal() is Kodi's properly
	input-responsive dialog mode, so the background thread here owns the
	polling and calls close() itself when done.
"""

import os
import threading
import time
import xbmc
import xbmcgui
import xbmcaddon

ADDON_ID = 'script.module.authorizediggz'


class DeviceAuthDialog(xbmcgui.WindowXMLDialog):

	def __init__(self, *args, **kwargs):
		super(DeviceAuthDialog, self).__init__(*args)  # positional only - Kodi C extension ignores extra kwargs
		self.service_name = ''
		self.qr_url = ''
		self.local_qr_data = None
		self.qr_controls = []
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
		self._render_qr()
		self._thread = threading.Thread(target=self._poll_loop)
		self._thread.daemon = True
		self._thread.start()

	def _render_qr(self):
		if self.local_qr_data:
			try:
				# Match the existing TMDB local QR renderer. In this XML the
				# 360px white backing is at (510+270, 160+110).
				from reauthorize.modules.qr_local import qr_rectangles
				main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
				texture = os.path.join(main_path, 'resources', 'skins', 'default', 'media', 'common', 'qr_black.png')
				if not os.path.isfile(texture):
					raise FileNotFoundError('Packaged QR texture missing')
				self.qr_controls = [xbmcgui.ControlImage(x, y, w, h, texture, 0, '0xFFFFFFFF')
				                    for x, y, w, h in qr_rectangles(self.local_qr_data, 780, 270, 360)]
				self.addControls(self.qr_controls)
				xbmc.log('[Diggz Account Manager] Local device QR controls added: %d' % len(self.qr_controls), xbmc.LOGINFO)
				return
			except Exception as exc:
				# Keep private verification parameters out of logs and the
				# public QR service: the caller supplies a public fallback URL.
				for c in self.qr_controls:
					try:
						self.removeControl(c)
					except Exception:
						pass
				self.qr_controls = []
				xbmc.log('[Diggz Account Manager] Local device QR rendering failed: %s' % type(exc).__name__, xbmc.LOGERROR)
		try:
			self.getControl(100).setImage(self.qr_url)
		except Exception:
			pass

	def _poll_loop(self):
		deadline = time.monotonic() + self.expires_in
		while not self.cancelled:
			remaining = deadline - time.monotonic()
			if remaining <= 0:
				break
			xbmc.sleep(int(min(max(self.interval, 1), remaining) * 1000))
			if self.cancelled:
				return
			if time.monotonic() >= deadline:
				break
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
			if result == 'slow_down':
				self.interval += 5
			elif result == 'expired_token':
				break
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


def run(service_name, qr_url, verification_url, user_code, poll_func, interval=5, expires_in=900, local_qr_data=None):
	"""
	Shows the QR/code device-authorization dialog and blocks (doModal)
	until the flow ends. poll_func() is called roughly every `interval`
	seconds on a background thread - it should return True (approved,
	stop polling), False (denied/failed, stop polling), or None (still
	pending), 'slow_down' (add five seconds), or 'expired_token' (end polling).
	Returns True if authorization succeeded.
	"""
	addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
	w = DeviceAuthDialog('device_auth.xml', addon_path, 'default', '1080i')
	w.service_name = service_name
	w.qr_url = qr_url
	w.local_qr_data = local_qr_data
	w.verification_url = verification_url
	w.user_code = user_code
	w.poll_func = poll_func
	w.interval = interval
	w.expires_in = expires_in
	w.doModal()
	success = w.success
	del w
	return success
