from reauthorize.modules import sync_support
import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

from pathlib import Path
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager OffCloud
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_token = accountmgr.getSetting("offcloud.token")
          

from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def offcloud_auth(self):
    #Umbrella
        try:
                if xbmcvfs.exists(var.chk_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("offcloudtoken")
                        if sync_support.needs('plugin.video.umbrella', [('offcloudtoken',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("offcloudtoken", your_token)
                                addon.setSetting("offcloud.enable", "true")
        except:
                sync_support.failed()
                xbmc.log('%s: Umbrella OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #POV
        try:
                if xbmcvfs.exists(var.chk_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("oc.token")
                        if sync_support.needs('plugin.video.pov', [('oc.token',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("oc.token", your_token)
                                addon.setSetting("oc.enabled", "true")
        except:
                sync_support.failed()
                xbmc.log('%s: POV OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Infinity
        try:
                if xbmcvfs.exists(var.chk_infinity):
                        chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("offcloudtoken")
                        if sync_support.needs('plugin.video.infinity', [('offcloudtoken',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                addon.setSetting("offcloudtoken", your_token)
                                addon.setSetting("offcloud.enable", "true")
        except:
                sync_support.failed()
                xbmc.log('%s: Infinity OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Cosmos
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("oc_api_key")
                        if sync_support.needs('plugin.video.cosmos', [('oc_api_key',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("oc_api_key", your_token)
                                addon.setSetting("oc_enabled", "true")
                                addon.setSetting("oc_auth_done", "true")
        except:
                sync_support.failed()
                xbmc.log('%s: Cosmos OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #ResolveURL
    #ResolveURL's OffCloud plugin is usable when it is enabled and has an apikey;
    #OffCloudResolver_user is only a display label. OffCloud gives one account
    #the same key wherever it signs in, so this is the value Umbrella holds too.
        try:
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.rurl_ud):
                        os.mkdir(var.rurl_ud)
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))

                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.chkset_rurl):
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))

                if xbmcvfs.exists(var.chk_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("OffCloudResolver_apikey")
                        if sync_support.needs('script.module.resolveurl', [('OffCloudResolver_apikey',your_token)]):

                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("OffCloudResolver_apikey", your_token)
                                addon.setSetting("OffCloudResolver_enabled", "true")
        except:
                sync_support.failed()
                xbmc.log('%s: ResolveURL OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('oc.token', your_token),
                                  ('oc.enabled', 'true')])
        except:
                sync_support.failed()
                xbmc.log('%s: Red Light OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Diamond Media Player OffCloud
        try:
                if xbmcvfs.exists(var.chk_rdtplayer):
                        chk_auth_rdtplayer = xbmcaddon.Addon('plugin.program.rdtplayer').getSetting("offcloud_api_key")
                        if sync_support.needs('plugin.program.rdtplayer', [('offcloud_api_key',your_token)]):
                                addon = xbmcaddon.Addon("plugin.program.rdtplayer")
                                addon.setSetting("offcloud_api_key", your_token)
        except:
                sync_support.failed()
                xbmc.log('%s: Diamond Media Player OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Prism OffCloud
    #oc.token isn't in settings.xml either; confirmed from Prism's own
    #resources/lib/debrid/offcloud.py: OC_TOKEN_KEY = "oc.token".
        try:
                if xbmcvfs.exists(var.chk_prism):
                        chk_auth_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("oc.token")
                        if sync_support.needs('plugin.video.prism', [('oc.token',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.prism")
                                addon.setSetting("oc.token", your_token)
                                addon.setSetting("offcloud.enabled", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Prism OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #TMDb Movies OffCloud
        try:
                if xbmcvfs.exists(var.chk_tmdbmovies):
                        chk_auth_tmdbmovies = xbmcaddon.Addon('plugin.video.tmdbmovies').getSetting("oc_api_key")
                        if sync_support.needs('plugin.video.tmdbmovies', [('oc_api_key',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.tmdbmovies")
                                addon.setSetting("oc_api_key", your_token)
        except:
                sync_support.failed()
                xbmc.log('%s: TMDb Movies OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass
