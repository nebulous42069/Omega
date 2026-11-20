from reauthorize.modules import sync_support
import xbmc, xbmcaddon
import xbmcvfs
import json
from pathlib import Path
from reauthorize.modules import control
from libs.common import var

#Account Manager FilePursuit
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_file_api = accountmgr.getSetting("filepursuit.api.key")


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
        def file_auth(self):
               
        #Umbrella
                try:
                        if xbmcvfs.exists(var.chk_umb): #Check that the addon is installed and settings.xml exists
                                
                                #Get add-on setting to compare
                                chk_file = xbmcaddon.Addon('plugin.video.umbrella').getSetting("filepursuittoken")
                                enable_file = ("true")
                                
                                #Write data to settings.xml
                                if sync_support.needs('plugin.video.umbrella', [('filepursuittoken',your_file_api)]):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("filepursuit.enable", enable_file)
                                        addon.setSetting("filepursuittoken", your_file_api)
                except:
                        sync_support.failed('plugin.video.umbrella')
                        xbmc.log('%s: Umbrella FilePursuit Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Infinity
                try:
                        if xbmcvfs.exists(var.chk_infinity):
                                
                                chk_file = xbmcaddon.Addon('plugin.video.infinity').getSetting("filepursuit.api")
                                enable_file = ("true")
                                
                                if sync_support.needs('plugin.video.infinity', [('filepursuit.api',your_file_api)]):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("filepursuit.enable", enable_file)
                                        addon.setSetting("filepursuit.api", your_file_api)
                except:
                        sync_support.failed('plugin.video.infinity')
                        xbmc.log('%s: Infinity FilePursuit Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #All Accounts
                try:
                                
                        
                        if xbmcvfs.exists(var.chk_allaccounts):
                                
                                chk_file = xbmcaddon.Addon('script.module.allaccounts').getSetting("filepursuit.api.key")
                                
                                if sync_support.needs('script.module.allaccounts', [('filepursuit.api.key',your_file_api)]):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("filepursuit.api.key", your_file_api)
                except:
                        sync_support.failed('script.module.allaccounts')
                        xbmc.log('%s: All Accounts FilePursuit Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #My Accounts
                try:
                                
                        
                        if xbmcvfs.exists(var.chk_myaccounts):
                                
                                chk_file = xbmcaddon.Addon('script.module.myaccounts').getSetting("filepursuit.api.key")
                                
                                if sync_support.needs('script.module.myaccounts', [('filepursuit.api.key',your_file_api)]):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("filepursuit.api.key", your_file_api)
                except:
                        sync_support.failed('script.module.myaccounts')
                        xbmc.log('%s: My Accounts FilePursuit Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
