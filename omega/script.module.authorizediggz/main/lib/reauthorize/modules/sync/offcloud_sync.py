from reauthorize.modules import control
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
            if xbmcvfs.exists(var.chk_umb) and ((your_token) or control.wiping()):
                username = accountmgr.getSetting('offcloud.userid') or accountmgr.getSetting('offcloud.user')
                pairs = [('offcloudtoken', '' if control.wiping() else your_token), ('offcloud.enable', 'true' if your_token and not control.wiping() else 'false')]
                if username or control.wiping():
                    pairs.append(('offcloud.username', '' if control.wiping() else username))
                sync_support.put('plugin.video.umbrella', pairs, wipe=control.wiping())
        except:
                sync_support.failed('plugin.video.umbrella')
                xbmc.log('%s: Umbrella OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #POV
        try:
                if xbmcvfs.exists(var.chk_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("oc.token")
                        if sync_support.needs('plugin.video.pov', [('oc.token',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("oc.token", your_token)
                                addon.setSetting("oc.enabled", ('true' if your_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.pov')
                xbmc.log('%s: POV OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Infinity
        try:
                if xbmcvfs.exists(var.chk_infinity):
                        chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("offcloudtoken")
                        if sync_support.needs('plugin.video.infinity', [('offcloudtoken',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                addon.setSetting("offcloudtoken", your_token)
                                addon.setSetting("offcloud.enable", ('true' if your_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.infinity')
                xbmc.log('%s: Infinity OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Cosmos
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("oc_api_key")
                        if sync_support.needs('plugin.video.cosmos', [('oc_api_key',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("oc_api_key", your_token)
                                addon.setSetting("oc_enabled", ('true' if your_token and not control.wiping() else 'false'))
                                addon.setSetting("oc_auth_done", ('true' if your_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.cosmos')
                xbmc.log('%s: Cosmos OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #ResolveURL
    #ResolveURL's OffCloud plugin is usable when it is enabled and has an apikey;
    #OffCloudResolver_user is only a display label. OffCloud gives one account
    #the same key wherever it signs in, so this is the value Umbrella holds too.
        try:


                if xbmcvfs.exists(var.chk_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("OffCloudResolver_apikey")
                        if sync_support.needs('script.module.resolveurl', [('OffCloudResolver_apikey',your_token)]):

                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("OffCloudResolver_apikey", your_token)
                                addon.setSetting("OffCloudResolver_enabled", ('true' if your_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('script.module.resolveurl')
                xbmc.log('%s: ResolveURL OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('oc.token', your_token),
                                  ('oc.enabled', ('true' if your_token and not control.wiping() else 'false'))])
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
                sync_support.failed('plugin.program.rdtplayer')
                xbmc.log('%s: Diamond Media Player OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    # Prism versions without a writable OffCloud setting cannot receive a key.
        try:
            if xbmcvfs.exists(var.chk_prism):
                addon = xbmcaddon.Addon('plugin.video.prism')
                if addon.schema is None or addon.schema.get('oc.token', 'action') != 'action':
                    if sync_support.needs('plugin.video.prism', [('oc.token', your_token)]):
                        addon.setSetting('oc.token', your_token)
                        addon.set_optional('offcloud.enabled', 'true' if your_token else 'false')
        except Exception:
            sync_support.failed('plugin.video.prism')
            xbmc.log('%s: Prism OffCloud Failed!' % var.amgr, xbmc.LOGINFO)

    # TMDb Movies cloud account
        try:
            from reauthorize.modules.sync import tmdbmovies_sync
            tmdbmovies_sync.cloud('oc_api_key', your_token, wipe=control.wiping())
        except Exception:
            sync_support.failed('plugin.video.tmdbmovies')
            xbmc.log('%s: TMDb Movies cloud status could not be saved.' % var.amgr, xbmc.LOGWARNING)
