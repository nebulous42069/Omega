# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon

properties = [
	'context.trailer.autoplay',
	'context.trailer.selectplay']

def getKodiVersion():
	return int(xbmc.getInfoLabel("System.BuildVersion")[:2])
LOGNOTICE = xbmc.LOGNOTICE if getKodiVersion() < 19 else xbmc.LOGINFO # (2 in 18, deprecated in 19 use LOGINFO(1))


class PropertiesUpdater(xbmc.Monitor):
	def __init__(self):
		for id in properties:
			if xbmcaddon.Addon().getSetting(id) == 'true':
				xbmc.executebuiltin('SetProperty({0},true,home)'.format(id))
				xbmc.log('[ context.trailer.play ]  Context menu item enabled: {0}'.format(id), LOGNOTICE)

	def onSettingsChanged(self):
		for id in properties:
			if xbmcaddon.Addon().getSetting(id) == 'true':
				xbmc.executebuiltin('SetProperty({0},true,home)'.format(id))
				xbmc.log('[ context.trailer.play ]  Context menu item enabled: {0}'.format(id), LOGNOTICE)
			else:
				xbmc.executebuiltin('ClearProperty({0},home)'.format(id))
				xbmc.log('[ context.trailer.play ]  Context menu item disabled: {0}'.format(id), LOGNOTICE)

# start monitoring settings changes events
xbmc.log('[ context.trailer.play ]  Service Started', LOGNOTICE)
properties_monitor = PropertiesUpdater()

# wait until abort is requested
properties_monitor.waitForAbort()
xbmc.log('[ context.trailer.play ]  Service Stopped', LOGNOTICE)