import xbmcaddon

import os

ADDON_ID = xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('id')
PATH = xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path')
ART = os.path.join(PATH, 'resources', 'media')

ADDONTITLE = 'ReAuthorize-Viewer'
HIDESPACERS = 'No'
SPACER = '<>'
COLOR1 = 'gray'
COLOR2 = 'white'
THEME2 = u'[COLOR {color1}]{{}}[/COLOR]'.format(color1=COLOR1)
THEME3 = u'[COLOR {color1}]{{}}[/COLOR]'.format(color1=COLOR2)
