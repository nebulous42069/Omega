from reauthorize.modules import sync_support
import xbmc, xbmcaddon
import xbmcvfs
import os
from libs.common import var

# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_username = accountmgr.getSetting("linksnappy.username")
your_password = accountmgr.getSetting("linksnappy.password")


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def linksnappy_auth(self):

    #Cosmos
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("ls_username")
                        if sync_support.needs('plugin.video.cosmos', [('ls_username',your_username),('ls_password',your_password)]):
                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("ls_username", your_username)
                                addon.setSetting("ls_password", your_password)
        except:
                sync_support.failed()
                xbmc.log('%s: Cosmos Linksnappy Failed!' % var.amgr, xbmc.LOGINFO)
                pass
