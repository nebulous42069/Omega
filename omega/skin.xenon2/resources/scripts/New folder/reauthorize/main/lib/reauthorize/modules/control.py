# -*- coding: utf-8 -*-
"""
	Auth Station
"""

import os.path
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import datetime
from libs.common import var

addon = xbmcaddon.Addon
addonObject = addon('script.module.reauthorize')
addonInfo = addonObject.getAddonInfo
getLangString = xbmcaddon.Addon().getLocalizedString
condVisibility = xbmc.getCondVisibility
execute = xbmc.executebuiltin
monitor = xbmc.Monitor()
transPath = xbmcvfs.translatePath
joinPath = os.path.join
date = str(datetime.date.today())

ADDON_ID = 'script.module.reauthorize'

# One read or write of ReAuthorize's own settings at a time in this process (1.4.3). Every
# setSetting makes Kodi rewrite the whole settings.xml, and every fresh handle reads it back.
# On a first start the restore thread and the start-up steps did both at once: on the Kodi 22
# copy (2026-10-13 21:38:36) a handle read the file half-written ('failed to load addon
# settings from ...'), and a handle that loaded nothing cannot save anything. A file left
# unreadable makes Kodi show an empty settings window for good (settings_health.py).
from reauthorize.modules.own_settings import LOCK as _settings_lock  # the same lock as every other handle


class _Settings(object):
	"""
	Settings accessor that never holds on to a stale Addon handle.

	Kodi gives every xbmcaddon.Addon() object its own view of the addon's
	settings. Holding one instance for the life of the process and writing
	through it lets it revert values written through a different instance: the
	stale handle persists the snapshot it was created with.

	That is exactly what defeated a server restore on 2026-09-20. This module
	is imported at startup, before any restore, so its handle held blank
	credentials. server.restore() then wrote twelve real credentials through
	its own fresh handle - restore_missing_keys() confirmed they were there -
	and 0.4s later sync_authorized_display_values() wrote a few .display fields
	through THIS stale handle, reverting every credential. The log said
	"Credentials restored from server" and the profile was empty.

	Reads go through a fresh handle too: a cached one can serve values that
	another instance has already replaced.

	Everything that is not a setting - getAddonInfo, getLocalizedString - is
	read-only metadata and is served from one handle, since creating an Addon
	object per call inside the sync loops would be wasteful for no benefit.
	"""

	def getSetting(self, key):
		with _settings_lock:
			return xbmcaddon.Addon(ADDON_ID).getSetting(key)

	def setSetting(self, key, value):
		with _settings_lock:
			xbmcaddon.Addon(ADDON_ID).setSetting(key, value)
		# A sign-in written here is this device's own: stamp it (owner.py), so a
		# copy of it in a build is recognised as foreign on any other device.
		if value and str(value).lower() not in ('true', 'false'):
			try:
				from reauthorize.modules import vault, owner
				if key in vault.CREDENTIAL_KEYS and vault.is_credential_key(key):
					owner.claim()
			except Exception:
				pass

	def __getattr__(self, name):
		return getattr(addonObject, name)


accountmgr = _Settings()
dialog = xbmcgui.Dialog()
window = xbmcgui.Window(10000)
progressDialog = xbmcgui.DialogProgress()

existsPath = xbmcvfs.exists
openFile = xbmcvfs.File
makeFile = xbmcvfs.mkdir

progress_line = '%s[CR]%s[CR]%s'

char_remov = ["'", ",", ")","("]

pm_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'premiumize.png')
ad_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'alldebrid.png')
trakt_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'trakt.png')
tmdb_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'tmdb.png')
torbox_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'torbox.png')
easyd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'easydebrid.png')
offcloud_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'offcloud.png')
easy_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'easynews.png')
file_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'filepursuit.png')
rd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize').getAddonInfo('path'), 'resources', 'icons'), 'realdebrid.png')
	
def getKodiVersion():
	return int(xbmc.getInfoLabel("System.BuildVersion")[:2])

def setting(id):
	return accountmgr.getSetting(id)

def setSetting(id, value):
	return accountmgr.setSetting(id, value)

def lang(language_id):
	text = getLangString(language_id)
	return text

def sleep(time):  # Modified `sleep` command that honors a user exit request
	while time > 0 and not monitor.abortRequested():
		xbmc.sleep(min(100, time))
		time = time - 100

def addonId():
	return addonInfo('id')

def addonName():
	return addonInfo('name')

def addonVersion():
	return addonInfo('version')

def addonIcon():
	return addonInfo('icon')

def addonPath():
	try: return transPath(addonInfo('path').decode('utf-8'))
	except: return transPath(addonInfo('path'))

def artPath():
	return os.path.join(addonObject.getAddonInfo('path'), 'resources', 'icons')

def openSettings(query=None, id=addonInfo('id')):
	try:
		from reauthorize.modules import settings_display
		settings_display.sync_authorized_display_values()
	except Exception as e:
		xbmc.log('[ReAuthorize] openSettings: display sync error: %s' % str(e), xbmc.LOGERROR)
	idle()
	xbmc.sleep(500)
	execute('Addon.OpenSettings(%s)' % id)
	if query is None: return
	try:
		c, f = query.split('.')
		execute('SetFocus(%i)' % (int(c) - 100))
		execute('SetFocus(%i)' % (int(f) - 80))
	except Exception:
		pass

def idle():
	if condVisibility('Window.IsActive(busydialognocancel)'):
		return execute('Dialog.Close(busydialognocancel)')

def notification(title=None, message=None, icon=None, time=3000, sound=False):
	if title == 'default' or title is None: title = addonName()
	if isinstance(title, int): heading = lang(title)
	else: heading = str(title)
	if isinstance(message, int): body = lang(message)
	else: body = str(message)
	if icon is None or icon == '' or icon == 'default': icon = addonIcon()
	elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
	elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
	elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
	dialog.notification(heading, body, icon, time, sound=sound)

def yesnoDialog(line, heading=addonInfo('name'), nolabel='', yeslabel=''):
	return dialog.yesno(heading, line, nolabel, yeslabel)

def selectDialog(list, heading=addonInfo('name')):
	return dialog.select(heading, list)

def confirm_remove(service):
	"""The question before a sign-out. Until 1.4.4 these sign-outs called okDialog() with no text, and the skin
	showed an OK box saying 'None' (the user, 2026-10-18). True = remove."""
	return dialog.yesno(addonName(), 'Remove your %s sign-in?[CR][CR]It is also taken out of your add-ons.' % service,
	                    nolabel='Cancel', yeslabel='Remove')


def okDialog(title=None, message=None):
	if title == 'default' or title is None: title = addonName()
	if isinstance(title, int): heading = lang(title)
	else: heading = str(title)
	if isinstance(message, int): body = lang(message)
	else: body = str(message)
	return dialog.ok(heading, body)

def closeAll():
	return execute('Dialog.Close(all, true)')

def jsondate_to_datetime(jsondate_object, resformat, remove_time=False):
	import _strptime  # fix bug in python import
	from datetime import datetime
	import time
	if remove_time:
		try: datetime_object = datetime.strptime(jsondate_object, resformat).date()
		except TypeError: datetime_object = datetime(*(time.strptime(jsondate_object, resformat)[0:6])).date()
	else:
		try: datetime_object = datetime.strptime(jsondate_object, resformat)
		except TypeError: datetime_object = datetime(*(time.strptime(jsondate_object, resformat)[0:6]))
	return datetime_object

def set_active_monitor():
	window.setProperty('accountmgr.active', 'true')

def release_active_monitor():
	window.clearProperty('accountmgr.active')

# Set by sync_all.run_all_syncs around each service it is wiping, so the few sync
# blocks that skip a blank value (Red Light's database, POV's Easynews, Infinity's
# Simkl client id, Gears' metadata) write the blank this time instead of leaving
# the old value in the addon.
_wiping = False

def force_close():
    """
    End Kodi at once (os._exit), for Prepare for Distribution (1.4.4: a normal Quit kept hanging Kodi 21).
    The test sandbox sets REAUTHORIZE_TEST_NO_EXIT so a test can see it happen without being ended by it.
    """
    if os.environ.get('REAUTHORIZE_TEST_NO_EXIT'):
        xbmc.executebuiltin('ReAuthorizeForceClose')
        return
    os._exit(1)


def set_wiping(on):
	global _wiping
	_wiping = bool(on)

def wiping():
	return _wiping

def function_monitor(func, query='0.0'):
	func()
	sleep(100)
	openSettings(query)
	while not condVisibility('Window.IsVisible(addonsettings)'):
		sleep(250)
	sleep(100)
	release_active_monitor()

def refresh_debugReversed(): # called from service "onSettingsChanged" to clear accountmgr.log if setting to reverse has been changed
	if window.getProperty('accountmgr.debug.reversed') != setting('debug.reversed'):
		window.setProperty('accountmgr.debug.reversed', setting('debug.reversed'))
		execute('RunScript(script.module.reauthorize, action=tools_clearLogFile)')


