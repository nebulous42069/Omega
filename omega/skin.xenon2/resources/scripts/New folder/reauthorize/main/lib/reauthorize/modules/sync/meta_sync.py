import xbmc, xbmcaddon
import xbmcvfs
import json
import os

from pathlib import Path
from reauthorize.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Metadata
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_tmdb_user = accountmgr.getSetting("tmdb.username")
your_tmdb_pass = accountmgr.getSetting("tmdb.password")
your_tmdb_session = accountmgr.getSetting("tmdb.session_id")
your_tmdb_api = accountmgr.getSetting("tmdb.api.key")
your_imdb_api = accountmgr.getSetting("imdb.user")
your_fanart_api = accountmgr.getSetting("fanart.tv.api.key")
your_mdb_api = accountmgr.getSetting("mdb.api.key")
your_mdb_user = accountmgr.getSetting("mdb.username")
your_omdb_api = accountmgr.getSetting("omdb.api.key")
your_audiodb_api = accountmgr.getSetting("audiodb.api.key")


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
        def meta_auth(self):
        #Seren
                try:
                        if xbmcvfs.exists(var.chk_seren): #Check that the addon is installed and settings.xml exists
                            
                                #Get add-on setting to compare
                                chk_fanart_api = xbmcaddon.Addon('plugin.video.seren').getSetting("fanart.apikey")
                                chk_omdb_api = xbmcaddon.Addon('plugin.video.seren').getSetting("omdb.apikey")
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.seren').getSetting("tmdb.apikey")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''): #Compare Account Mananger API to Add-on API. If they match authorization is skipped
                                        #Write Meta API to settings.xml
                                        addon = xbmcaddon.Addon("plugin.video.seren")
                                        addon.setSetting("fanart.apikey", your_fanart_api)
                                        
                                if (your_omdb_api or control.wiping()) and (not str(your_omdb_api) == str(chk_omdb_api) or str(chk_omdb_api) == ''): #Compare Account Mananger API to Add-on API. If they match authorization is skipped
                                        #Write Meta API to settings.xml
                                        addon = xbmcaddon.Addon("plugin.video.seren")
                                        addon.setSetting("omdb.apikey", your_omdb_api)

                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''): #Compare Account Mananger API to Add-on API. If they match authorization is skipped
                                        #Write Meta API to settings.xml
                                        addon = xbmcaddon.Addon("plugin.video.seren")
                                        addon.setSetting("tmdb.apikey", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Seren Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #Gears
                try:
                        if xbmcvfs.exists(var.chk_gears_video) and xbmcvfs.exists(var.chkset_gears):

                            from reauthorize.modules.db import meta_db
                            conn = meta_db.create_conn(var.gears_settings_db)

                            with conn:
                                cursor = conn.cursor()
                                cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('omdb_api',))
                                auth_omdb = cursor.fetchone()
                                chk_auth_gears_omdb = str(auth_omdb)

                                cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('tmdb_api',))
                                auth_tmdb = cursor.fetchone()
                                chk_auth_gears_tmdb = str(auth_tmdb)
                                cursor.close()

                                for char in char_remov:
                                    chk_auth_gears_omdb = chk_auth_gears_omdb.replace(char, "")

                                for char in char_remov:
                                    chk_auth_gears_tmdb = chk_auth_gears_tmdb.replace(char, "")

                                if str(your_omdb_api) == '' and not control.wiping():
                                        pass
                                else:
                                        if str(your_omdb_api) != chk_auth_gears_omdb:
                                                from reauthorize.modules.db import meta_db
                                                meta_db.auth_gears_omdb()

                                if str(your_tmdb_api) == '' and not control.wiping():
                                        pass
                                else:
                                        if str(your_tmdb_api) != chk_auth_gears_tmdb:
                                                from reauthorize.modules.db import meta_db
                                                meta_db.auth_gears_tmdb()
                except:
                        sync_support.failed()
                        xbmc.log('%s: Gears Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass


        #Coalition
                try:
                        if xbmcvfs.exists(var.chk_coal):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.coalition').getSetting("fanart_client_key")
                                chk_omdb_api = xbmcaddon.Addon('plugin.video.coalition').getSetting("omdb_api")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.coalition').getSetting("imdb_user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.coalition').getSetting("tmdb_api")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.coalition")
                                        addon.setSetting("fanart_client_key", your_fanart_api)

                                if (your_omdb_api or control.wiping()) and (not str(your_omdb_api) == str(chk_omdb_api) or str(chk_omdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.coalition")
                                        addon.setSetting("omdb_api", your_omdb_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.coalition")
                                        addon.setSetting("imdb_user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.coalition")
                                        addon.setSetting("tmdb_api", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Coalition Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

                
        #Umbrella
                try:
                        if xbmcvfs.exists(var.chk_umb):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.umbrella').getSetting("fanart_tv.api_key")
                                chk_mdb_api = xbmcaddon.Addon('plugin.video.umbrella').getSetting("mdblist.api")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.umbrella').getSetting("imdbuser")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.umbrella').getSetting("tmdb.apikey")
                                chk_tmdb_user = xbmcaddon.Addon('plugin.video.umbrella').getSetting("tmdbusername")
                                chk_tmdb_pass = xbmcaddon.Addon('plugin.video.umbrella').getSetting("tmdbpassword")
                                chk_tmdb_session = xbmcaddon.Addon('plugin.video.umbrella').getSetting("tmdb.sessionid")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("fanart_tv.api_key", your_fanart_api)

                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(chk_mdb_api) or str(chk_mdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        pass  # This Umbrella uses MDBList OAuth, not this obsolete field.

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("imdbuser", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("tmdb.apikey", your_tmdb_api)

                                if (your_tmdb_user or control.wiping()) and (not str(your_tmdb_user) == str(chk_tmdb_user) or str(chk_tmdb_user) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("tmdbusername", your_tmdb_user)

                                if (your_tmdb_pass or control.wiping()) and (not str(your_tmdb_pass) == str(chk_tmdb_pass) or str(chk_tmdb_pass) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("tmdbpassword", your_tmdb_pass)

                                if (your_tmdb_session or control.wiping()) and (not str(your_tmdb_session) == str(chk_tmdb_session) or str(chk_tmdb_session) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("tmdb.sessionid", your_tmdb_session)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Umbrella Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Infinity
                try:
                        if xbmcvfs.exists(var.chk_infinity):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.infinity').getSetting("fanart_tv.api_key")
                                chk_mdb_api = xbmcaddon.Addon('plugin.video.infinity').getSetting("mdblist.api")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.infinity').getSetting("imdbuser")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.infinity').getSetting("tmdb.apikey")
                                chk_tmdb_user = xbmcaddon.Addon('plugin.video.infinity').getSetting("tmdbusername")
                                chk_tmdb_pass = xbmcaddon.Addon('plugin.video.infinity').getSetting("tmdbpassword")
                                chk_tmdb_session = xbmcaddon.Addon('plugin.video.infinity').getSetting("tmdb.sessionid")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("fanart_tv.api_key", your_fanart_api)

                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(chk_mdb_api) or str(chk_mdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        pass  # This Umbrella uses MDBList OAuth, not this obsolete field.

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("imdbuser", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("tmdb.apikey", your_tmdb_api)

                                if (your_tmdb_user or control.wiping()) and (not str(your_tmdb_user) == str(chk_tmdb_user) or str(chk_tmdb_user) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("tmdbusername", your_tmdb_user)

                                if (your_tmdb_pass or control.wiping()) and (not str(your_tmdb_pass) == str(chk_tmdb_pass) or str(chk_tmdb_pass) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("tmdbpassword", your_tmdb_pass)

                                if (your_tmdb_session or control.wiping()) and (not str(your_tmdb_session) == str(chk_tmdb_session) or str(chk_tmdb_session) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("tmdb.sessionid", your_tmdb_session)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Infinity Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #The Crew
                try:
                        if xbmcvfs.exists(var.chk_crew) and not xbmcvfs.exists(var.crew_ud):
                                os.mkdir(var.crew_ud)
                                xbmcvfs.copy(os.path.join(var.crew), os.path.join(var.chkset_crew))
                                
                        if xbmcvfs.exists(var.chk_crew) and not xbmcvfs.exists(var.chkset_crew):
                                xbmcvfs.copy(os.path.join(var.crew), os.path.join(var.chkset_crew))

                        if xbmcvfs.exists(var.chk_crew):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.thecrew').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.thecrew').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.thecrew').getSetting("tm.user")
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.thecrew")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.thecrew")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.thecrew")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: The Crew Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #Homelander
                try:
                        if xbmcvfs.exists(var.chk_home) and not xbmcvfs.exists(var.home_ud):
                                os.mkdir(var.home_ud)
                                xbmcvfs.copy(os.path.join(var.home), os.path.join(var.chkset_home))
                                
                        if xbmcvfs.exists(var.chk_home) and not xbmcvfs.exists(var.chkset_home):
                                xbmcvfs.copy(os.path.join(var.home), os.path.join(var.chkset_home))

                        if xbmcvfs.exists(var.chk_home):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.homelander').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.homelander').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.homelander').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.homelander")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.homelander")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.homelander")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Homelander Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #Quicksilver
                try:
                        if xbmcvfs.exists(var.chk_quick) and not xbmcvfs.exists(var.quick_ud):
                                os.mkdir(var.quick_ud)
                                xbmcvfs.copy(os.path.join(var.quick), os.path.join(var.chkset_quick))
                                
                        if xbmcvfs.exists(var.chk_quick) and not xbmcvfs.exists(var.chkset_quick):
                                xbmcvfs.copy(os.path.join(var.quick), os.path.join(var.chkset_quick))

                        if xbmcvfs.exists(var.chk_quick):
                                
                                chk_fanart_api = xbmcaddon.Addon('plugin.video.quicksilver').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.quicksilver').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.quicksilver').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.quicksilver")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.quicksilver")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.quicksilver")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Quicksilver Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Chains Genocide
                try:
                        if xbmcvfs.exists(var.chk_genocide) and not xbmcvfs.exists(var.genocide_ud):
                                os.mkdir(var.genocide_ud)
                                xbmcvfs.copy(os.path.join(var.genocide), os.path.join(var.chkset_genocide))
                                
                        if xbmcvfs.exists(var.chk_genocide) and not xbmcvfs.exists(var.chkset_genocide):
                                xbmcvfs.copy(os.path.join(var.genocide), os.path.join(var.chkset_genocide))

                        if xbmcvfs.exists(var.chk_genocide):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.chainsgenocide').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.chainsgenocide').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.chainsgenocide').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Chains Genocide Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Genocide (plugin.video.genocide) Metadata
        # "Chains Genocide" (plugin.video.chainsgenocide) was renamed to "Genocide"
        # (plugin.video.genocide) at some point before this was found (2026-09-27,
        # on a real Kodi 21 box). RD/PM/AD/Trakt/TorBox/Simkl already had a matching
        # var.chk_newgenocide block; Metadata was the one left behind, so every field
        # here had always been going to an addon id that no longer exists. The real,
        # current addon's own settings.xml also uses different field names than the
        # old block assumed (fanart_tv.api_key, not fanart.tv.user; tmdb.api.key and
        # a separate tmdb.username, not one merged tm.user) - confirmed by reading
        # the installed addon's shipped resources/settings.xml, not guessed.
                try:
                        if xbmcvfs.exists(var.chk_newgenocide):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.genocide').getSetting("fanart_tv.api_key")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.genocide').getSetting("imdb.user")
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.genocide').getSetting("tmdb.api.key")
                                chk_tmdb_user = xbmcaddon.Addon('plugin.video.genocide').getSetting("tmdb.username")

                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.genocide")
                                        addon.setSetting("fanart_tv.api_key", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.genocide")
                                        addon.setSetting("imdb.user", your_imdb_api)

                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.genocide")
                                        addon.setSetting("tmdb.api.key", your_tmdb_api)

                                if (your_tmdb_user or control.wiping()) and (not str(your_tmdb_user) == str(chk_tmdb_user) or str(chk_tmdb_user) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.genocide")
                                        addon.setSetting("tmdb.username", your_tmdb_user)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Genocide Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Shazam
                try:
                        if xbmcvfs.exists(var.chk_shazam) and not xbmcvfs.exists(var.shazam_ud):
                                os.mkdir(var.shazam_ud)
                                xbmcvfs.copy(os.path.join(var.shazam), os.path.join(var.chkset_shazam))
                                
                        if xbmcvfs.exists(var.chk_shazam) and not xbmcvfs.exists(var.chkset_shazam):
                                xbmcvfs.copy(os.path.join(var.shazam), os.path.join(var.chkset_shazam))

                        if xbmcvfs.exists(var.chk_shazam):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.shazam').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.shazam').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.shazam').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.shazam")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.shazam")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.shazam")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Shazam Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Moria: retired 1.4.0 (unmaintained). Sent nothing any more; a wipe still blanks what earlier versions sent.
                try:

                        if control.wiping() and xbmcvfs.exists(var.chk_moria):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.moria').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.moria').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.moria').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.moria")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.moria")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.moria")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Moria Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Nightwing (plugin.video.nightwing, 1.4.0): Moria's setting names
                try:

                        if xbmcvfs.exists(var.chk_nightwing):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.nightwing').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.nightwing').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.nightwing').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.nightwing")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.nightwing")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.nightwing")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Nightwing Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Absolution
                try:
                        if xbmcvfs.exists(var.chk_absol) and not xbmcvfs.exists(var.absol_ud):
                                os.mkdir(var.absol_ud)
                                xbmcvfs.copy(os.path.join(var.absol), os.path.join(var.chkset_absol))
                                
                        if xbmcvfs.exists(var.chk_absol) and not xbmcvfs.exists(var.chkset_absol):
                                xbmcvfs.copy(os.path.join(var.absol), os.path.join(var.chkset_absol))

                        if xbmcvfs.exists(var.chk_absol):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.absolution').getSetting("fanart.tv.user")
                                chk_imdb_api = xbmcaddon.Addon('plugin.video.absolution').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('plugin.video.absolution').getSetting("tm.user")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.absolution")
                                        addon.setSetting("fanart.tv.user", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.absolution")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.absolution")
                                        addon.setSetting("tm.user", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Absolution Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #TMDB Helper
                try:
                        if xbmcvfs.exists(var.chk_tmdbh) and not xbmcvfs.exists(var.tmdbh_ud):
                                os.mkdir(var.tmdbh_ud)
                                xbmcvfs.copy(os.path.join(var.tmdbh), os.path.join(var.chkset_tmdbh))
                                
                        if xbmcvfs.exists(var.chk_tmdbh) and not xbmcvfs.exists(var.chkset_tmdbh):
                                xbmcvfs.copy(os.path.join(var.tmdbh), os.path.join(var.chkset_tmdbh))

                        if xbmcvfs.exists(var.chk_tmdbh):

                                chk_fanart_api = xbmcaddon.Addon('plugin.video.themoviedb.helper').getSetting("fanarttv_clientkey")
                                chk_omdb_api = xbmcaddon.Addon('plugin.video.themoviedb.helper').getSetting("omdb_apikey")    
                                chk_mdb_api = xbmcaddon.Addon('plugin.video.themoviedb.helper').getSetting("mdblist_apikey")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.themoviedb.helper")
                                        addon.setSetting("fanarttv_clientkey", your_fanart_api)

                                if (your_omdb_api or control.wiping()) and (not str(your_omdb_api) == str(chk_omdb_api) or str(chk_omdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.themoviedb.helper")
                                        addon.setSetting("omdb_apikey", your_omdb_api)
                                        
                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(chk_mdb_api) or str(chk_mdb_api) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.themoviedb.helper")
                                        addon.setSetting("mdblist_apikey", your_mdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: TMDBh Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Metahandler
                try:
                        if xbmcvfs.exists(var.chk_meta) and not xbmcvfs.exists(var.meta_ud):
                                os.mkdir(var.meta_ud)
                                xbmcvfs.copy(os.path.join(var.meta), os.path.join(var.chkset_meta))
                                
                        if xbmcvfs.exists(var.chk_meta) and not xbmcvfs.exists(var.chkset_meta):
                                xbmcvfs.copy(os.path.join(var.meta), os.path.join(var.chkset_meta))

                        if xbmcvfs.exists(var.chk_meta):
                                
                                chk_omdb_api = xbmcaddon.Addon('script.module.metahandler').getSetting("omdb_api_key")
                                chk_tmdb_api = xbmcaddon.Addon('script.module.metahandler').getSetting("tmdb_api_key")
                                enable_omdb_fallback = ("true")
                                enable_omdb_override = ("true")
                                enable_tmdb = ("true")

                                if (your_omdb_api or control.wiping()) and (not str(your_omdb_api) == str(chk_omdb_api) or str(chk_omdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.metahandler")
                                        addon.setSetting("omdb_api_key", your_omdb_api)
                                       
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.metahandler")
                                        addon.setSetting("tmdb_api_key", your_tmdb_api)
                                        
                                if str(your_omdb_api) != '':
                                        addon = xbmcaddon.Addon("script.module.metahandler")
                                        addon.setSetting("omdbapi_fallback", enable_omdb_fallback)
                                        
                                        addon = xbmcaddon.Addon("script.module.metahandler")
                                        addon.setSetting("override_omdb_key", enable_omdb_override)

                                if str(your_tmdb_api) != '':
                                        addon = xbmcaddon.Addon("script.module.metahandler")
                                        addon.setSetting("override_tmdb_key", enable_tmdb)
                                        
                except:
                        sync_support.failed()
                        xbmc.log('%s: Metahandler Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #PVR Artwork Module
                try:
                        if xbmcvfs.exists(var.chk_pvr) and not xbmcvfs.exists(var.pvr_ud):
                                os.mkdir(var.pvr_ud)
                                xbmcvfs.copy(os.path.join(var.pvr), os.path.join(var.chkset_pvr))
                                
                        if xbmcvfs.exists(var.chk_pvr):

                                chk_fanart_api = xbmcaddon.Addon('script.module.pvr.artwork').getSetting("fanart_apikey")
                                chk_tmdb_api = xbmcaddon.Addon('script.module.pvr.artwork').getSetting("tmdb_apikey")
                                enable_fanart = ("true")
                                enable_fanart_prefer = ("true")
                                enable_tmdb = ("true")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.pvr.artwork")
                                        addon.setSetting("fanart_apikey", your_fanart_api)
                                       
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.pvr.artwork")
                                        addon.setSetting("tmdb_apikey", your_tmdb_api)

                                if str(your_fanart_api) != '':
                                        addon = xbmcaddon.Addon("script.module.pvr.artwork")
                                        addon.setSetting("use_fanart_tv", enable_fanart)

                                        addon = xbmcaddon.Addon("script.module.pvr.artwork")
                                        addon.setSetting("prefer_fanart_tv", enable_fanart_prefer)

                                if str(your_tmdb_api) != '':
                                        addon = xbmcaddon.Addon("script.module.pvr.artwork")
                                        addon.setSetting("use_tmdb", enable_tmdb)
                except:
                        sync_support.failed()
                        xbmc.log('%s: PVR Artwork Module Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #All Accounts
                try:
                        if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.allaccounts_ud):
                                os.mkdir(var.allaccounts_ud)
                                xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                                
                        if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.chkset_allaccounts):
                                xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))

                        if xbmcvfs.exists(var.chk_allaccounts):
                                #Check Add-on API Keys
                                chk_fanart_api = xbmcaddon.Addon('script.module.allaccounts').getSetting("fanart.tv.api.key")
                                chk_imdb_api = xbmcaddon.Addon('script.module.allaccounts').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('script.module.allaccounts').getSetting("tmdb.api.key")
                                chk_tmdb_user = xbmcaddon.Addon('script.module.allaccounts').getSetting("tmdb.username")
                                chk_tmdb_pass = xbmcaddon.Addon('script.module.allaccounts').getSetting("tmdb.password")
                                chk_tmdb_session = xbmcaddon.Addon('script.module.allaccounts').getSetting("tmdb.session_id")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        #Write Meta API to settings.xml
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("fanart.tv.api.key", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("tmdb.api.key", your_tmdb_api)

                                if (your_tmdb_user or control.wiping()) and (not str(your_tmdb_user) == str(chk_tmdb_user) or str(chk_tmdb_user) == ''):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("tmdb.username", your_tmdb_user)

                                if (your_tmdb_pass or control.wiping()) and (not str(your_tmdb_pass) == str(chk_tmdb_pass) or str(chk_tmdb_pass) == ''):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("tmdb.password", your_tmdb_pass)
                                        
                                if (your_tmdb_session or control.wiping()) and (not str(your_tmdb_session) == str(chk_tmdb_session) or str(chk_tmdb_session) == ''):
                                        addon = xbmcaddon.Addon("script.module.allaccounts")
                                        addon.setSetting("tmdb.session_id", your_tmdb_session)
                except:
                        sync_support.failed()
                        xbmc.log('%s: All Accounts Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
                
        #My Accounts
                try:
                        if xbmcvfs.exists(var.chk_myaccounts) and not xbmcvfs.exists(var.myaccounts_ud):
                                os.mkdir(var.myaccounts_ud)
                                xbmcvfs.copy(os.path.join(var.myaccounts), os.path.join(var.chkset_myaccounts))
                                
                        if xbmcvfs.exists(var.chk_myaccounts) and not xbmcvfs.exists(var.chkset_myaccounts):
                                xbmcvfs.copy(os.path.join(var.myaccounts), os.path.join(var.chkset_myaccounts))
                        
                        if xbmcvfs.exists(var.chk_myaccounts):

                                chk_fanart_api = xbmcaddon.Addon('script.module.myaccounts').getSetting("fanart.tv.api.key")
                                chk_imdb_api = xbmcaddon.Addon('script.module.myaccounts').getSetting("imdb.user")    
                                chk_tmdb_api = xbmcaddon.Addon('script.module.myaccounts').getSetting("tmdb.api.key")
                                chk_tmdb_user = xbmcaddon.Addon('script.module.myaccounts').getSetting("tmdb.username")
                                chk_tmdb_pass = xbmcaddon.Addon('script.module.myaccounts').getSetting("tmdb.password")
                                chk_tmdb_session = xbmcaddon.Addon('script.module.myaccounts').getSetting("tmdb.session_id")
                                
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_api) or str(chk_fanart_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("fanart.tv.api.key", your_fanart_api)

                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_api) or str(chk_imdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("imdb.user", your_imdb_api)
                                        
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb_api) or str(chk_tmdb_api) == ''):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("tmdb.api.key", your_tmdb_api)

                                if (your_tmdb_user or control.wiping()) and (not str(your_tmdb_user) == str(chk_tmdb_user) or str(chk_tmdb_user) == ''):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("tmdb.username", your_tmdb_user)

                                if (your_tmdb_pass or control.wiping()) and (not str(your_tmdb_pass) == str(chk_tmdb_pass) or str(chk_tmdb_pass) == ''):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("tmdb.password", your_tmdb_pass)
                                        
                                if (your_tmdb_session or control.wiping()) and (not str(your_tmdb_session) == str(chk_tmdb_session) or str(chk_tmdb_session) == ''):
                                        addon = xbmcaddon.Addon("script.module.myaccounts")
                                        addon.setSetting("tmdb.session_id", your_tmdb_session)
                except:
                        sync_support.failed()
                        xbmc.log('%s: My Accounts Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Fentastic & Nimbus Skin
                try:
                        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"lookandfeel.skin"}, "id":1}')
                        json_query = json.loads(json_query)
                        skin = ''
                        if 'result' in json_query and 'value' in json_query['result']:
                                skin_chk = json_query['result']['value']
                                #xbmc.log(str(skin), xbmc.LOGINFO)
                        if xbmcvfs.exists(var.chk_fentastic) and skin_chk == 'skin.fentastic':
                                with open(var.path_fentastic) as f:
                                        if your_mdb_api in f.read():
                                                pass
                                        else:  
                                                xbmc.executebuiltin("Skin.SetString(mdblist_api_key, %s)" % your_mdb_api)
                        if xbmcvfs.exists(var.chk_nimbus) and skin_chk == 'skin.nimbus':
                                with open(var.path_nimbus) as f:
                                        if your_mdb_api in f.read():
                                                pass
                                        else:
                                                xbmc.executebuiltin("Skin.SetString(mdblist_api_key, %s)" % your_mdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Skin Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Red Light
        #No tmdb.token: Red Light sends it as a Bearer token for TMDb lists, and a
        #v3 API key there makes those calls fail. No tmdb.session_id: Red Light
        #pairs it with tmdb.account_id, which ReAuthorize has no value for.
                try:
                        from reauthorize.modules.db import redlight_db
                        redlight_db.push([('tmdb_api', your_tmdb_api),
                                          ('omdb_api', your_omdb_api),
                                          ('fanarttv_api', your_fanart_api)], require_first=False)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Red Light Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #The Archives MDBList (1.4.0): signed in = mdblist.api_key (plugins/mdblist.py __check_auth);
        #mdblist.username is what it shows as the account.
                try:
                        if xbmcvfs.exists(var.chk_thearchives):
                                addon = xbmcaddon.Addon("plugin.video.thearchives")
                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(addon.getSetting("mdblist.api_key")) or str(addon.getSetting("mdblist.api_key")) == ''):
                                        addon.setSetting("mdblist.api_key", your_mdb_api)
                                        addon.setSetting("mdblist.username", your_mdb_user if your_mdb_api else '')
                except:
                        sync_support.failed()
                        xbmc.log('%s: The Archives MDBList Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #GratisRed
                try:
                        if xbmcvfs.exists(var.chk_gratisred):
                                chk_tmdb = xbmcaddon.Addon('plugin.video.gratisred').getSetting("tmdb.api")
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb) or str(chk_tmdb) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.gratisred")
                                        addon.setSetting("tmdb.api", your_tmdb_api)
                                        addon.setSetting("tmdb.id", your_tmdb_user)
                                        addon.setSetting("tmdb.session", your_tmdb_session)
                                chk_fanart = xbmcaddon.Addon('plugin.video.gratisred').getSetting("fanart.api")
                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart) or str(chk_fanart) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.gratisred")
                                        addon.setSetting("fanart.api", your_fanart_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: GratisRed Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Cosmos
                try:
                        if xbmcvfs.exists(var.chk_cosmos):
                                chk_tmdb = xbmcaddon.Addon('plugin.video.cosmos').getSetting("tmdb_api_key")
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb) or str(chk_tmdb) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.cosmos")
                                        addon.setSetting("tmdb_api_key", your_tmdb_api)
                                # 1.4.0: its MDBList API key, used when it holds no account sign-in
                                chk_mdb = xbmcaddon.Addon('plugin.video.cosmos').getSetting("mdblist_api_key")
                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(chk_mdb) or str(chk_mdb) == ''):
                                        xbmcaddon.Addon("plugin.video.cosmos").setSetting("mdblist_api_key", your_mdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Cosmos Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #The Loop and Mad Titan Sports (1.4.0): tmdb.api_key ships with a working key of their own and a
        #blank breaks them (no fallback in tmdb_plugin.py), so it is written only when the user has a key,
        #and a wipe puts their own default back.
                for loop_id in ('plugin.video.the-loop', 'plugin.video.madtitansports'):
                        try:
                                if xbmcvfs.exists('special://home/addons/%s/' % loop_id) and xbmcvfs.exists('special://profile/addon_data/%s/settings.xml' % loop_id):
                                        addon = xbmcaddon.Addon(loop_id)
                                        if your_tmdb_api and not control.wiping():
                                                if addon.getSetting("tmdb.api_key") != your_tmdb_api:
                                                        addon.setSetting("tmdb.api_key", your_tmdb_api)
                                        elif control.wiping():
                                                from reauthorize.modules.sync.mdblist_oauth_sync import _shipped_default
                                                # its own key back; blank only if that cannot be read (a personal key
                                                # left in a build is worse than a menu that needs the add-on reset)
                                                shipped = _shipped_default(loop_id, 'tmdb.api_key')
                                                if addon.getSetting("tmdb.api_key") != shipped:
                                                        addon.setSetting("tmdb.api_key", shipped)
                        except:
                                sync_support.failed()
                                xbmc.log('%s: %s TMDb Failed!' % (var.amgr, loop_id), xbmc.LOGINFO)

        #FidoK19
                try:
                        if xbmcvfs.exists(var.chk_fidok19):
                                chk_tmdb = xbmcaddon.Addon('plugin.video.fidoK19').getSetting("tmdb.api_key")
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb) or str(chk_tmdb) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.fidoK19")
                                        addon.setSetting("tmdb.api_key", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: FidoK19 Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Aliunde K19
                try:
                        if xbmcvfs.exists(var.chk_aliunde):
                                chk_tmdb = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("tmdb_api")
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb) or str(chk_tmdb) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.aliundek19")
                                        addon.setSetting("tmdb_api", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Aliunde K19 Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #TorqueLite
                try:
                        if xbmcvfs.exists(var.chk_torquelite):
                                chk_tmdb = xbmcaddon.Addon('plugin.video.torquelite').getSetting("tmdb.api_key")
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb) or str(chk_tmdb) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.torquelite")
                                        addon.setSetting("tmdb.api_key", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: TorqueLite Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #TorqueLive
                try:
                        if xbmcvfs.exists(var.chk_torquelive):
                                chk_tmdb = xbmcaddon.Addon('plugin.video.torquelive').getSetting("tmdb.api_key")
                                if (your_tmdb_api or control.wiping()) and (not str(your_tmdb_api) == str(chk_tmdb) or str(chk_tmdb) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.torquelive")
                                        addon.setSetting("tmdb.api_key", your_tmdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: TorqueLive Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Prism
                try:
                        if xbmcvfs.exists(var.chk_prism):
                                chk_fanart_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("fanart.apikey")
                                chk_mdblist_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("mdblist.apikey")

                                if (your_fanart_api or control.wiping()) and (not str(your_fanart_api) == str(chk_fanart_prism) or str(chk_fanart_prism) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.prism")
                                        addon.setSetting("fanart.apikey", your_fanart_api)

                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(chk_mdblist_prism) or str(chk_mdblist_prism) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.prism")
                                        addon.setSetting("mdblist.apikey", your_mdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Prism Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #TMDb Movies
        #mdblist_access_token/mdblist_refresh_token are its own full OAuth flow -
        #ReAuthorize only holds a plain MDBList API key, so this pushes into
        #mdblist_api, the field its own settings.xml labels "MDBList API Key
        #(fallback)". Also has fanart.tv? No - confirmed absent, no fanart field
        #found in its settings.xml or source; only MDBList/Trakt/Simkl for lists.
                try:
                        if xbmcvfs.exists(var.chk_tmdbmovies):
                                chk_mdblist_tmdbmovies = xbmcaddon.Addon('plugin.video.tmdbmovies').getSetting("mdblist_api")
                                if (your_mdb_api or control.wiping()) and (not str(your_mdb_api) == str(chk_mdblist_tmdbmovies) or str(chk_mdblist_tmdbmovies) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.tmdbmovies")
                                        addon.setSetting("mdblist_api", your_mdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: TMDb Movies Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Youtube Theater
        #imdb_user is a single field read by imdb_menu() to build imdb.com/user/ur<id>
        #URLs - separate from its imdb_user_0..9 slots, which are a distinct
        #multi-profile feature (aggregating several different people's IMDb ids),
        #confirmed from source, not guessed from the field name alone.
                try:
                        if xbmcvfs.exists(var.chk_youtubetheater):
                                chk_imdb_ytheater = xbmcaddon.Addon('plugin.video.youtubetheater').getSetting("imdb_user")
                                if (your_imdb_api or control.wiping()) and (not str(your_imdb_api) == str(chk_imdb_ytheater) or str(chk_imdb_ytheater) == ''):
                                        addon = xbmcaddon.Addon("plugin.video.youtubetheater")
                                        addon.setSetting("imdb_user", your_imdb_api)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Youtube Theater Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

