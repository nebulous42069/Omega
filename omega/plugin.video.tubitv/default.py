# -*- coding: utf-8 -*-
# KodiAddon
#
from resources.lib.scraper import myAddon
import re
import sys
import xbmcaddon

__settings__ = xbmcaddon.Addon('plugin.video.tubitv')

# Start of Module
addonName = re.search('plugin\://plugin.video.(.+?)/',str(sys.argv[0])).group(1)
ma = myAddon(addonName)

did = __settings__.getSetting("did")
sid = __settings__.getSetting("sid")

if not did or not sid:
    xbmcaddon.Addon().openSettings()
    sys.exit()

ma.defaultHeaders.update({'Cookie':'deviceId='+did+'; connect.sid='+sid+''})
ma.processAddonEvent()
