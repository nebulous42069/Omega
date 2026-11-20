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
                                enable_easy = ("false" if control.wiping() else "true")
                         
                                if sync_support.needs('plugin.video.coalition', [('easynews_user',your_easy_user),('easynews_password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.coalition")
                                        addon.setSetting("provider.easynews", enable_easy)
                                        addon.setSetting("easynews_user", your_easy_user)
                                        addon.setSetting("easynews_password", your_easy_pass)
                except:
                        sync_support.failed('plugin.video.coalition')
                        xbmc.log('%s: Coalition Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #POV
                try:
                        if xbmcvfs.exists(var.chk_pov) and (accountmgr.getSetting("easynews.password") != '' or control.wiping()):

                                chk_easy = xbmcaddon.Addon('plugin.video.pov').getSetting("easynews_password")
                                enable_easy = ("false" if control.wiping() else "true")
                                     
                                if sync_support.needs('plugin.video.pov', [('easynews_user',your_easy_user),('easynews_password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.pov")
                                        addon.setSetting("provider.easynews", enable_easy)
                                        addon.setSetting("easynews_user", your_easy_user)
                                        addon.setSetting("easynews_password", your_easy_pass)
                except:
                        sync_support.failed('plugin.video.pov')
                        xbmc.log('%s: POV Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Umbrella
                try:
                    if xbmcvfs.exists(var.chk_umb) and ((your_easy_user and your_easy_pass) or control.wiping()):
                        sync_support.put('plugin.video.umbrella', [('easynews.user', '' if control.wiping() else your_easy_user), ('easynews.password', '' if control.wiping() else your_easy_pass), ('easynews.enable', 'true' if your_easy_user and your_easy_pass and not control.wiping() else 'false')], wipe=control.wiping())
                except:
                        sync_support.failed('plugin.video.umbrella')
                        xbmc.log('%s: Umbrella Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Infinity
                try:
                        if xbmcvfs.exists(var.chk_infinity):

                                chk_easy = xbmcaddon.Addon('plugin.video.infinity').getSetting("easynews.password")
                                enable_easy = ("false" if control.wiping() else "true")
                                     
                                if sync_support.needs('plugin.video.infinity', [('easynews.user',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("easynews.enable", enable_easy)
                                        addon.setSetting("easynews.user", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed('plugin.video.infinity')
                        xbmc.log('%s: Infinity Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #The Crew
                try:
                                

                        if xbmcvfs.exists(var.chk_crew):
                                chk_easy = xbmcaddon.Addon('plugin.video.thecrew').getSetting("easynews.password")

                                     
                                if sync_support.needs('plugin.video.thecrew', [('easynews.user',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("plugin.video.thecrew")
                                        addon.setSetting("easynews.user", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed('plugin.video.thecrew')
                        xbmc.log('%s: The Crew Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #All Accounts
                try:
                                

                        if xbmcvfs.exists(var.chk_allaccounts):

                                chk_easy = xbmcaddon.Addon('script.module.allaccounts').getSetting("easynews.password")

                                if sync_support.needs('script.module.allaccounts', [('easynews.username',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("easynews.username", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed('script.module.allaccounts')
                        xbmc.log('%s: All Accounts Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #My Accounts
                try:
                                

                        if xbmcvfs.exists(var.chk_myaccounts):

                                chk_easy = xbmcaddon.Addon('script.module.myaccounts').getSetting("easynews.password")

                                if sync_support.needs('script.module.myaccounts', [('easynews.username',your_easy_user),('easynews.password',your_easy_pass)]):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("easynews.username", your_easy_user)
                                        addon.setSetting("easynews.password", your_easy_pass)
                except:
                        sync_support.failed('script.module.myaccounts')
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
                sync_support.failed('plugin.video.genocide')
                xbmc.log('%s: Genocide Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light Easynews
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('easynews_password', your_easy_pass),
                                  ('easynews_user', your_easy_user),
                                  ('provider.easynews', ('false' if control.wiping() else 'true'))])
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
                                addon.setSetting("provider.easynews", ('false' if control.wiping() else 'true'))
        except:
                sync_support.failed('plugin.video.thearchives')
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
                                addon.setSetting("easynews_enabled", ('false' if control.wiping() else 'true'))
        except:
                sync_support.failed('plugin.video.cosmos')
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
                                addon.setSetting("enable_easynews", ('false' if control.wiping() else 'true'))
        except:
                sync_support.failed('plugin.program.rdtplayer')
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
                                addon.setSetting("provider.easy", ('false' if control.wiping() else 'true'))
        except:
                sync_support.failed('plugin.video.youtubetheater')
                xbmc.log('%s: Youtube Theater Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass

