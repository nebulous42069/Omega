import xbmc, xbmcaddon
import xbmcvfs
import os

from pathlib import Path
from debridmgr.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Debrid Manager All-Debrid
debridmgr = xbmcaddon.Addon("script.module.debridmgr")
your_ad_username = debridmgr.getSetting("alldebrid.username")
your_ad_token = debridmgr.getSetting("alldebrid.token")

class Auth:
    def alldebrid_auth(self):
    #Fen Light AD
        try:
                if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt): #Check that the addon is installed and settings.db exists
                        
                        #Create database connection
                        from debridmgr.modules.db import debrid_db
                        conn = debrid_db.create_conn(var.fenlt_settings_db)
                        
                        #Get add-on settings to compare
                        with conn:
                            cursor = conn.cursor()
                            cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('ad.token',))
                            auth_ad = cursor.fetchone()
                            chk_auth_fenlt = str(auth_ad)

                            cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('pm.token',))
                            auth_pm = cursor.fetchone()
                            chk_auth_fenlt_pm = str(auth_pm)

                            cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('rd.token',))
                            auth_rd = cursor.fetchone()
                            chk_auth_fenlt_rd = str(auth_rd)
                            cursor.close()
                            
                            #Clean up database results
                            for char in char_remov:
                                chk_auth_fenlt = chk_auth_fenlt.replace(char, "")
                            
                            if not str(var.chk_debridmgr_tk_ad) == chk_auth_fenlt: #Compare Account Mananger token to Add-on token. If they match, authorization is skipped
                                
                                #Write settings to database
                                from debridmgr.modules.db import debrid_db
                                debrid_db.auth_fenlt_ad()
                                
                                #Enable authorized debrid services
                                for char in char_remov:
                                    chk_auth_fenlt_pm = chk_auth_fenlt_pm.replace(char, "")
                                
                                if chk_auth_fenlt_pm != 'empty_setting' or chk_auth_fenlt_pm != '' or chk_auth_fenlt_pm != None:
                                    from debridmgr.modules.db import debrid_db
                                    debrid_db.enable_fenlt_pm()
                                else:
                                    from debridmgr.modules.db import debrid_db
                                    debrid_db.disable_fenlt_pm()
                                    
                                for char in char_remov:
                                    chk_auth_fenlt_rd = chk_auth_fenlt_rd.replace(char, "")

                                if chk_auth_fenlt_rd != 'empty_setting' or chk_auth_fenlt_rd != '' or chk_auth_fenlt_rd != None:
                                    from debridmgr.modules.db import debrid_db
                                    debrid_db.enable_fenlt_rd()
                                else:
                                    from debridmgr.modules.db import debrid_db
                                    debrid_db.disable_fenlt_rd()
                                var.remkae_settings()
        except:
                xbmc.log('%s: Fen Light All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Fen AD
        try:
                if xbmcvfs.exists(var.chk_fen) and xbmcvfs.exists(var.chkset_fen):
                        chk_auth_fen = xbmcaddon.Addon('plugin.video.fen').getSetting("ad.token")
                        chk_auth_fen_rd = xbmcaddon.Addon('plugin.video.fen').getSetting("rd.token")
                        chk_auth_fen_pm = xbmcaddon.Addon('plugin.video.fen').getSetting("pm.token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_fen) or str(chk_auth_fen) == '':

                                addon = xbmcaddon.Addon("plugin.video.fen")
                                addon.setSetting("ad.account_id", your_ad_username)
                                addon.setSetting("ad.token", your_ad_token)

                                enabled_ad = ("true")
                                addon.setSetting("ad.enabled", enabled_ad)

                                if str(chk_auth_fen_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)
                        
                                if str(chk_auth_fen_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
        except:
                xbmc.log('%s: Fen All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Umbrella AD
        try:
                if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("alldebridtoken")
                        chk_auth_umb_rd = xbmcaddon.Addon('plugin.video.umbrella').getSetting("realdebridtoken")
                        chk_auth_umb_pm = xbmcaddon.Addon('plugin.video.umbrella').getSetting("premiumizetoken")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_umb) or str(chk_auth_umb) == '':

                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("alldebridusername", your_ad_username)
                                addon.setSetting("alldebridtoken", your_ad_token)

                                enabled_ad = ("true")
                                addon.setSetting("alldebrid.enable", enabled_ad)

                                if str(chk_auth_umb_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("realdebrid.enable", enabled_rd)
                        
                                if str(chk_auth_umb_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("premiumize.enable", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("premiumize.enable", enabled_pm)
        except:
                xbmc.log('%s: Umbrella All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #POV AD
        try:
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("ad.token")
                        chk_auth_pov_rd = xbmcaddon.Addon('plugin.video.pov').getSetting("rd.token")
                        chk_auth_pov_pm = xbmcaddon.Addon('plugin.video.pov').getSetting("pm.token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_pov) or str(chk_auth_pov) == '':

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("ad.account_id", your_ad_username)
                                addon.setSetting("ad.token", your_ad_token)

                                enabled_ad = ("true")
                                addon.setSetting("ad.enabled", enabled_ad)

                                if str(chk_auth_pov_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)
                        
                                if str(chk_auth_pov_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
        except:
                xbmc.log('%s: POV All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass                
            
     #Dradis AD
        try:
                if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis):
                        chk_auth_dradis = xbmcaddon.Addon('plugin.video.dradis').getSetting("alldebrid.token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_dradis) or str(chk_auth_dradis) == '':

                                addon = xbmcaddon.Addon("plugin.video.dradis")
                                addon.setSetting("alldebrid.username", your_ad_username)
                                addon.setSetting("alldebrid.token", your_ad_token)

                                enabled_ad = ("true")
                                addon.setSetting("alldebrid.enable", enabled_ad)
        except:
                xbmc.log('%s: Dradis All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Coalition AD
        try:
                if xbmcvfs.exists(var.chk_coal) and xbmcvfs.exists(var.chkset_coal):
                        chk_auth_coal = xbmcaddon.Addon('plugin.video.coalition').getSetting("ad.token")
                        chk_auth_coal_rd = xbmcaddon.Addon('plugin.video.coalition').getSetting("rd.token")
                        chk_auth_coal_pm = xbmcaddon.Addon('plugin.video.coalition').getSetting("pm.token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_coal) or str(chk_auth_coal) == '':

                                addon = xbmcaddon.Addon("plugin.video.coalition")
                                addon.setSetting("ad.account_id", your_ad_username)
                                addon.setSetting("ad.token", your_ad_token)

                                enabled_ad = ("true")
                                addon.setSetting("ad.enabled", enabled_ad)

                                if str(chk_auth_coal_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)
                        
                                if str(chk_auth_coal_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
        except:
                xbmc.log('%s: Coalition All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Seren AD
        try:
                if xbmcvfs.exists(var.chk_seren) and xbmcvfs.exists(var.chkset_seren): #Check that the addon is installed and settings.xml exists
                        
                        #Get add-on setting to compare
                        chk_auth_seren = xbmcaddon.Addon('plugin.video.seren').getSetting("alldebrid.apikey")
                        chk_auth_seren_rd = xbmcaddon.Addon('plugin.video.seren').getSetting("rd.auth")
                        chk_auth_seren_pm = xbmcaddon.Addon('plugin.video.seren').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_seren) or str(chk_auth_seren) == '': #Compare Account Mananger token to Add-on token. If they match authorization is skipped

                                #Write data to settings.xml
                                addon = xbmcaddon.Addon("plugin.video.seren")
                                addon.setSetting("alldebrid.username", your_ad_username)
                                addon.setSetting("alldebrid.apikey", your_ad_token)

                                premium_stat = ("Premium")
                                addon.setSetting("alldebrid.premiumstatus", premium_stat)
                                
                                #Enable authorized debrid services
                                enabled_ad = ("true")
                                addon.setSetting("alldebrid.enabled", enabled_ad)

                                if str(chk_auth_seren_rd) != '': #Check if Real-Debrid is authorized
                                        enabled_rd = ("true")
                                        addon.setSetting("realdebrid.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("realdebrid.enabled", enabled_rd)
                        
                                if str(chk_auth_seren_pm) != '': #Check if Premiumize is authorized
                                        enabled_pm = ("true")
                                        addon.setSetting("premiumize.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("premiumize.enabled", enabled_pm)
        except:
                xbmc.log('%s: Seren All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #All Accounts AD
        try:
                if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.allaccounts_ud):
                        os.mkdir(var.allaccounts_ud)
                        xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                        
                if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.chkset_allaccounts):
                        xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                        
                if xbmcvfs.exists(var.chk_allaccounts) and xbmcvfs.exists(var.chkset_allaccounts):
                        chk_auth_allaccounts = xbmcaddon.Addon('script.module.allaccounts').getSetting("alldebrid.token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_allaccounts) or str(chk_auth_allaccounts) == '':
                        
                                addon = xbmcaddon.Addon("script.module.allaccounts")
                                addon.setSetting("alldebrid.username", your_ad_username)
                                addon.setSetting("alldebrid.token", your_ad_token)
        except:
                xbmc.log('%s: All Accounts All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #ResolveURL AD
        try:
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.rurl_ud):
                        os.mkdir(var.rurl_ud)
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))
                        
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.chkset_rurl):
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))
                        
                if xbmcvfs.exists(var.chk_rurl) and xbmcvfs.exists(var.chkset_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("AllDebridResolver_token")
                        if not str(var.chk_debridmgr_tk_ad) == str(chk_auth_rurl) or str(chk_auth_rurl) == '':

                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("AllDebridResolver_client_id", your_ad_username)
                                addon.setSetting("AllDebridResolver_token", your_ad_token)

                                cache_only = ("true")
                                addon.setSetting("AllDebridResolver_cached_only", cache_only)
        except:
                xbmc.log('%s: ResolveURL All-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
