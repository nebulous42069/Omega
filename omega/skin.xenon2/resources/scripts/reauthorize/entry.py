"""Forward existing Xenon shortcuts to the standalone ReAuthorize add-on."""
import json
import sys
import xbmc
import xbmcgui

ADDON_ID = 'script.module.authorizediggz'


def run(arguments):
    # Older skins still invoke this on startup. Kodi starts the add-on service.
    if any('service=true' in arg.split('&') for arg in arguments):
        return
    if not xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % ADDON_ID):
        xbmcgui.Dialog().ok('Diggz Account Manager required', 'Install and enable the standalone Diggz Account Manager.')
        return
    encoded = ''.join(',' + json.dumps(arg, ensure_ascii=False) for arg in arguments)
    xbmc.executebuiltin('RunScript(%s%s)' % (ADDON_ID, encoded))


if __name__ == '__main__':
    run(sys.argv[1:])
