#       Copyright (C) 2013-2014
#       Sean Poyser (seanpoyser@gmail.com)
#       Portions Copyright (c) 2020 John Moore
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

# This script is to allow the excellent XBMC GlobalSearch script by Ronie to be
# used without the need for manual entry via the on-screen keyboard.
# It should be called like this:
#
# xbmc.executebuiltin('RunScript('FULLPATHTOSCRIPT/globalsearch.py', searchstring:SEARCHTERM)')
#


import os, sys
import xbmc, xbmcaddon, xbmcvfs


ADDON        = xbmcaddon.Addon('script.globalsearch')
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE     = ADDON.getLocalizedString
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
RESOURCE     = xbmcvfs.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.insert(0, RESOURCE)

def doSearch():
	searchstring = None
	if len(sys.argv) > 1:
		try:
			param = sys.argv[1]
			if param.startswith('searchstring:'):
				from urllib.parse import unquote_plus
				searchstring = param.split(':', 1)[-1]
				searchstring = unquote_plus(searchstring)
				searchstring = searchstring.replace('\'', '')
				searchstring = searchstring.replace('"',  '')
		except:
			searchstring = None
            
	if not searchstring:     
		keyboard = xbmc.Keyboard( '', LANGUAGE(32101), False )
		keyboard.doModal()
		if ( keyboard.isConfirmed() ):
			searchstring = keyboard.getText()

	if searchstring:
		params = {}
		#TODO Fix import gui reference

		ui = launch_global_search()
		ui.doModal()
		del ui
		sys.modules.clear()

doSearch()
# --- Injected patch: use external Global Search add-on ---
def launch_global_search(query=None):
    import xbmc
    addon_id = 'script.globalsearch'
    if query:
        xbmc.executebuiltin('RunScript(%s,search=%s)' % (addon_id, query))
    else:
        xbmc.executebuiltin('RunAddon(%s)' % addon_id)
    return True
# --- End patch ---
