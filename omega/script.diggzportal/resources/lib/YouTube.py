from resources.lib import Utils
import xbmc

PROVIDER = "tmdbm.trailers"


def play_video(video_id, windowed=False, dialog=None):
	import re
	from urllib.parse import urlencode
	import xbmcgui
	if not re.fullmatch(r'[A-Za-z0-9_-]{11}', str(video_id or '')):
		Utils.notify('Diggz Portal', 'Invalid YouTube video ID', sound=False)
		return
	provider = PROVIDER
	if not xbmc.getCondVisibility('System.HasAddon(%s)' % provider):
		Utils.notify('Diggz Portal', 'Install or enable TMDbM Trailers', sound=False)
		return
	url = 'plugin://%s/play/?%s' % (provider, urlencode({'video_id': video_id, 'dbtype': 'video'}))
	item = xbmcgui.ListItem(path=url)
	item.setProperty('IsPlayable', 'true')
	xbmc.log('Diggz Portal: trailer handoff ' + url, xbmc.LOGINFO)
	# Netflix information windows contain an embedded video control.
	windowed = windowed or bool(getattr(dialog, "windowed_trailers", False))
	try:
		if not windowed and dialog is not None:
			# Let the modal owner suspend and restore this exact dialog.
			if getattr(dialog, '_pending_trailer', None) is None:
				focus = dialog.getFocusId()
				try:
					position = dialog.getControl(focus).getSelectedPosition()
				except (AttributeError, RuntimeError):
					position = None
				dialog._pending_trailer = (url, item, focus, position)
				dialog.close()
			return
		xbmc.Player().play(url, item, windowed=windowed)
	except Exception as exc:
		xbmc.log('Diggz Portal: trailer handoff failed: ' + str(exc), xbmc.LOGERROR)
		Utils.notify('Diggz Portal', 'Trailer playback failed; check Kodi log', sound=False)



def play_fullscreen_and_wait(url, item):
	"""Keep the owning script alive until playback ends, stops or fails."""
	import time
	import threading

	class TrailerPlayer(xbmc.Player):
		def __init__(self):
			super().__init__()
			self.started = threading.Event()
			self.finished = threading.Event()

		def onAVStarted(self):
			self.started.set()

		def onPlayBackEnded(self):
			self.finished.set()

		def onPlayBackStopped(self):
			if self.started.is_set():
				self.finished.set()

		def onPlayBackError(self):
			self.finished.set()

	monitor = xbmc.Monitor()
	# Stop an embedded preview before registering the new player's callbacks.
	if xbmc.Player().isPlaying():
		xbmc.Player().stop()
		deadline = time.monotonic() + 5
		while xbmc.Player().isPlaying() and time.monotonic() < deadline:
			if monitor.waitForAbort(0.1):
				return False
	player = TrailerPlayer()
	try:
		player.play(url, item, windowed=False)
		deadline = time.monotonic() + 90
		while not player.finished.is_set() and not player.started.is_set():
			if monitor.waitForAbort(0.1):
				return False
			if player.isPlayingVideo():
				player.started.set()
			if time.monotonic() >= deadline:
				Utils.notify('Diggz Portal', 'Trailer did not start; check Kodi log', sound=False)
				break
		# A brief false isPlayingVideo value during startup/transition is not EOF.
		idle_since = None
		while player.started.is_set() and not player.finished.is_set():
			if monitor.waitForAbort(0.1):
				return False
			if player.isPlayingVideo():
				idle_since = None
			elif idle_since is None:
				idle_since = time.monotonic()
			elif time.monotonic() - idle_since >= 2:
				break
		# Allow Kodi to finish leaving the fullscreen video window.
		deadline = time.monotonic() + 3
		while xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)') and time.monotonic() < deadline:
			if monitor.waitForAbort(0.1):
				return False
	except Exception as exc:
		xbmc.log('Diggz Portal: trailer playback failed: ' + str(exc), xbmc.LOGERROR)
	return not monitor.abortRequested()

def browse_videos(search_str='', prev_window=None):
	from urllib.parse import urlencode
	if not xbmc.getCondVisibility('System.HasAddon(%s)' % PROVIDER):
		Utils.hide_busy()
		Utils.notify('Diggz Portal', 'Install or enable TMDbM Trailers', sound=False)
		return
	query = str(search_str or '').strip()
	params = {'mode': 'search_types', 'q': query} if query else {'mode': 'search'}
	url = 'plugin://%s/?%s' % (PROVIDER, urlencode(params))
	Utils.hide_busy()
	if prev_window is not None:
		prev_window.close()
	xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % url)
