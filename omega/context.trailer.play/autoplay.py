# -*- coding: utf-8 -*-

import sys
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()


if __name__ == '__main__':
	windowed = ADDON.getSetting("windowed") == "true"
	info = sys.listitem.getVideoInfoTag()
	trailer = info.getTrailer()
	if windowed:
		xbmc.executebuiltin("PlayMedia(%s,1)" % (trailer))
	else:
		xbmc.executebuiltin("PlayMedia(%s)" % (trailer))