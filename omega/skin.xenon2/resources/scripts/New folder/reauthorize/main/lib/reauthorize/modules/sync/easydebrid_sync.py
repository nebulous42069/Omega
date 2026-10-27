from reauthorize.modules import sync_support
import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

from pathlib import Path
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Easy Debrid
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_token = accountmgr.getSetting("easydebrid.token")
your_acct_id = accountmgr.getSetting("easydebrid.acct_id")
          

from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def easydebrid_auth(self):
        from reauthorize.modules import control
        if not control.wiping():
            raise RuntimeError("EasyDebrid playback targets are disabled or unverified")

    #Umbrella
        try:
                if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("easydebridtoken")
                        if sync_support.needs('plugin.video.umbrella', [('easydebridtoken',your_token)]):
                        
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("easydebridtoken", your_token)
                                addon.setSetting("easydebrid.enable", 'true')

        except:
                sync_support.failed()
                xbmc.log('%s: Umbrella Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #POV
        try:
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("ed.token")
                        if sync_support.needs('plugin.video.pov', [('ed.token',your_token),('ed.account_id',your_acct_id)]):

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("ed.token", your_token)
                                addon.setSetting("ed.account_id", your_acct_id)
                                addon.setSetting("ed.enabled", 'true')

        except:
                sync_support.failed()
                xbmc.log('%s: POV Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Infinity
        try:
                if xbmcvfs.exists(var.chk_infinity) and xbmcvfs.exists(var.chkset_infinity):
                        chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("easydebridtoken")
                        if sync_support.needs('plugin.video.infinity', [('easydebridtoken',your_token),('easydebrid.username',your_acct_id)]):

                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                addon.setSetting("easydebridtoken", your_token)
                                addon.setSetting("easydebrid.username", your_acct_id)
                                addon.setSetting("easydebrid.enable", 'true')
                                addon.setSetting("easydebrid.expirynotice", '0')

        except:
                sync_support.failed()
                xbmc.log('%s: Infinity Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

