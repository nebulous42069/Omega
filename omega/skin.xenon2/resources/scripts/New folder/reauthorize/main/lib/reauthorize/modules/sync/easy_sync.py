from reauthorize.modules import sync_support
import xbmc, xbmcaddon
import xbmcvfs
import os

from pathlib import Path
from reauthorize.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Easynews
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_easy_user = accountmgr.getSetting("easynews.username")
your_easy_pass = accountmgr.getSetting("easynews.password")


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
        def easy_auth(self):

        #Coalition
                try:
                        if xbmcvfs.exists(var.chk_coal):

                                chk_easy = xbmcaddon.Addon('plugin.video.coalition').getSetting("easynews_password")
                                enable_easy = ("true")
                         
                                if sync_support.needs('plugin.video.coalition', [('easynews_user',your_easy_user),('easynews_password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.coalition")
                                        addon.setSetting("provider.easynews", enable_easy)
                                        addon.setSetting("easynews_user", your_easy_user)
                                        addon.setSetting("easynews_password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Coalition Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #POV
                try:
                        if xbmcvfs.exists(var.chk_pov) and (accountmgr.getSetting("easynews.password") != '' or control.wiping()):

                                chk_easy = xbmcaddon.Addon('plugin.video.pov').getSetting("easynews_password")
                                enable_easy = ("true")
                                     
                                if sync_support.needs('plugin.video.pov', [('easynews_user',your_easy_user),('easynews_password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.pov")
                                        addon.setSetting("provider.easynews", enable_easy)
                                        addon.setSetting("easynews_user", your_easy_user)
                                        addon.setSetting("easynews_password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: POV Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Umbrella
                try:
                        if xbmcvfs.exists(var.chk_umb):

                                chk_easy = xbmcaddon.Addon('plugin.video.umbrella').getSetting("easynews.password")
                                enable_easy = ("true")
                                     
                                if sync_support.needs('plugin.video.umbrella', [('easynews.user',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("easynews.enable", enable_easy)
                                        addon.setSetting("easynews.user", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Umbrella Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Infinity
                try:
                        if xbmcvfs.exists(var.chk_infinity):

                                chk_easy = xbmcaddon.Addon('plugin.video.infinity').getSetting("easynews.password")
                                enable_easy = ("true")
                                     
                                if sync_support.needs('plugin.video.infinity', [('easynews.user',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("easynews.enable", enable_easy)
                                        addon.setSetting("easynews.user", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Infinity Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #The Crew
                try:
                        if xbmcvfs.exists(var.chk_crew) and not xbmcvfs.exists(var.crew_ud):
                                os.mkdir(var.crew_ud)
                                xbmcvfs.copy(os.path.join(var.crew), os.path.join(var.chkset_crew))
                                
                        if xbmcvfs.exists(var.chk_crew) and not xbmcvfs.exists(var.chkset_crew):
                                xbmcvfs.copy(os.path.join(var.crew), os.path.join(var.chkset_crew))

                        if xbmcvfs.exists(var.chk_crew):
                                chk_easy = xbmcaddon.Addon('plugin.video.thecrew').getSetting("easynews.password")

                                     
                                if sync_support.needs('plugin.video.thecrew', [('easynews.user',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.thecrew")
                                        addon.setSetting("easynews.user", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: The Crew Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #All Accounts
                try:
                        if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.allaccounts_ud):
                                os.mkdir(var.allaccounts_ud)
                                xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                                
                        if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.chkset_allaccounts):
                                xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))

                        if xbmcvfs.exists(var.chk_allaccounts):

                                chk_easy = xbmcaddon.Addon('script.module.allaccounts').getSetting("easynews.password")

                                if sync_support.needs('script.module.allaccounts', [('easynews.username',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("easynews.username", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: All Accounts Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #My Accounts
                try:
                        if xbmcvfs.exists(var.chk_myaccounts) and not xbmcvfs.exists(var.myaccounts_ud):
                                os.mkdir(var.myaccounts_ud)
                                xbmcvfs.copy(os.path.join(var.myaccounts), os.path.join(var.chkset_myaccounts))
                                
                        if xbmcvfs.exists(var.chk_myaccounts) and not xbmcvfs.exists(var.chkset_myaccounts):
                                xbmcvfs.copy(os.path.join(var.myaccounts), os.path.join(var.chkset_myaccounts))

                        if xbmcvfs.exists(var.chk_myaccounts):

                                chk_easy = xbmcaddon.Addon('script.module.myaccounts').getSetting("easynews.password")

                                if sync_support.needs('script.module.myaccounts', [('easynews.username',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("easynews.username", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed()
                        xbmc.log('%s: My Accounts Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Genocide (plugin.video.genocide) Easynews
        try:
                if xbmcvfs.exists(var.chk_newgenocide):
                        chk_auth_newgenocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("easynews.password")
                        if sync_support.needs('plugin.video.genocide', [('easynews.username',your_easy_user),('easynews.password',your_easy_pass)]):
                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("easynews.username", your_easy_user)
                                addon.setSetting("easynews.password", your_easy_pass)
        except:
                sync_support.failed()
                xbmc.log('%s: Genocide Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light Easynews
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('easynews_password', your_easy_pass),
                                  ('easynews_user', your_easy_user),
                                  ('provider.easynews', 'true')])
        except:
                sync_support.failed()
                xbmc.log('%s: Red Light Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #The Archives Easynews
        try:
                if xbmcvfs.exists(var.chk_thearchives):
                        chk_easy = xbmcaddon.Addon('plugin.video.thearchives').getSetting("easynews.password")
                        if sync_support.needs('plugin.video.thearchives', [('easynews.username',your_easy_user),('easynews.password',your_easy_pass)]):
                                addon = xbmcaddon.Addon("plugin.video.thearchives")
                                addon.setSetting("easynews.username", your_easy_user)
                                addon.setSetting("easynews.password", your_easy_pass)
                                addon.setSetting("provider.easynews", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: The Archives Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Cosmos Easynews
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_easy = xbmcaddon.Addon('plugin.video.cosmos').getSetting("easynews_password")
                        if sync_support.needs('plugin.video.cosmos', [('easynews_username',your_easy_user),('easynews_password',your_easy_pass)]):
                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("easynews_username", your_easy_user)
                                addon.setSetting("easynews_password", your_easy_pass)
                                addon.setSetting("easynews_enabled", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Cosmos Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        #Diamond Media Player
        try:
                if xbmcvfs.exists(var.chk_rdtplayer):
                        chk_easy = xbmcaddon.Addon('plugin.program.rdtplayer').getSetting("easynews_password")
                        if sync_support.needs('plugin.program.rdtplayer', [('easynews_user',your_easy_user),('easynews_password',your_easy_pass)]):
                                addon = xbmcaddon.Addon("plugin.program.rdtplayer")
                                addon.setSetting("easynews_user", your_easy_user)
                                addon.setSetting("easynews_password", your_easy_pass)
                                addon.setSetting("enable_easynews", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Diamond Media Player Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        #Youtube Theater
        try:
                if xbmcvfs.exists(var.chk_youtubetheater):
                        chk_easy = xbmcaddon.Addon('plugin.video.youtubetheater').getSetting("easynews.password")
                        if sync_support.needs('plugin.video.youtubetheater', [('easynews.user',your_easy_user),('easynews.password',your_easy_pass)]):
                                addon = xbmcaddon.Addon("plugin.video.youtubetheater")
                                addon.setSetting("easynews.user", your_easy_user)
                                addon.setSetting("easynews.password", your_easy_pass)
                                addon.setSetting("provider.easy", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Youtube Theater Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

