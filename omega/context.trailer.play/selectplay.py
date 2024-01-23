# -*- coding: utf-8 -*-

import sys
import xbmc
import xbmcaddon

from resources.lib.modules import trailer

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
	windowed = ADDON.getSetting("windowed") == "true"

	info = sys.listitem.getVideoInfoTag()
	type = info.getMediaType()
	name = info.getTitle()
	tvshowtitle = info.getTVShowTitle()
	if tvshowtitle:
		name = tvshowtitle
	# season = info.getSeason() # may utilize for season specific trailer search
	year = info.getYear()

	trailer.Trailer().play(type, name, year, windowedtrailer=1 if windowed else 0)