import xbmc, xbmcaddon
import xbmcvfs
import os
import json

from pathlib import Path
from debridmgr.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Debrid Manager Real-Debrid
debridmgr = xbmcaddon.Addon("script.module.debridmgr")
your_rd_username = debridmgr.getSetting("realdebrid.username")
your_rd_token = debridmgr.getSetting("realdebrid.token")
your_rd_client_id = debridmgr.getSetting("realdebrid.client_id")
your_rd_refresh = debridmgr.getSetting("realdebrid.refresh")
your_rd_secret = debridmgr.getSetting("realdebrid.secret")

class Auth:
    def realdebrid_auth(self):
    #Fen Light RD        
        try:
                if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt): #Check that the addon is installed and settings.db exists
                    
                    #Create database connection
                    from debridmgr.modules.db import debrid_db
                    conn = debrid_db.create_conn(var.fenlt_settings_db)
                    
                    #Get add-on settings to compare
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('rd.token',))
                        auth_rd = cursor.fetchone()
                        chk_auth_fenlt = str(auth_rd)

                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('pm.token',))
                        auth_pm = cursor.fetchone()
                        chk_auth_fenlt_pm = str(auth_pm)

                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('ad.token',))
                        auth_ad = cursor.fetchone()
                        chk_auth_fenlt_ad = str(auth_ad)
                        cursor.close()
                        
                        #Clean up database results
                        for char in char_remov:
                            chk_auth_fenlt = chk_auth_fenlt.replace(char, "")
                        
                        if not str(var.chk_debridmgr_tk_rd) == chk_auth_fenlt: #Compare Account Mananger token to Add-on token. If they match, authorization is skipped
                            
                            #Write settings to database
                            from debridmgr.modules.db import debrid_db
                            debrid_db.auth_fenlt_rd()
                            
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
                                chk_auth_fenlt_ad = chk_auth_fenlt_ad.replace(char, "")

                            if chk_auth_fenlt_ad != 'empty_setting' or chk_auth_fenlt_ad != '' or chk_auth_fenlt_ad != None:
                                from debridmgr.modules.db import debrid_db
                                debrid_db.enable_fenlt_ad()
                            else:
                                from debridmgr.modules.db import debrid_db
                                debrid_db.disable_fenlt_ad()
                            var.remake_settings()
        except:
                xbmc.log('%s: Fen Light Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Fen RD
        try:
                if xbmcvfs.exists(var.chk_fen) and xbmcvfs.exists(var.chkset_fen):
                        chk_auth_fen = xbmcaddon.Addon('plugin.video.fen').getSetting("rd.token")
                        chk_auth_fen_pm = xbmcaddon.Addon('plugin.video.fen').getSetting("pm.token")
                        chk_auth_fen_ad = xbmcaddon.Addon('plugin.video.fen').getSetting("ad.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_fen) or str(chk_auth_fen) == '':

                                addon = xbmcaddon.Addon("plugin.video.fen")
                                addon.setSetting("rd.account_id", your_rd_username)
                                addon.setSetting("rd.token", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                enabled_rd = ("true")
                                addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_fen_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
                        
                                if str(chk_auth_fen_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                xbmc.log('%s: Fen Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Umbrella RD
        try:
                if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("realdebridtoken")
                        chk_auth_umb_pm = xbmcaddon.Addon('plugin.video.umbrella').getSetting("premiumizetoken")
                        chk_auth_umb_ad = xbmcaddon.Addon('plugin.video.umbrella').getSetting("alldebridtoken")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_umb) or str(chk_auth_umb) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("realdebridusername", your_rd_username)
                                addon.setSetting("realdebridtoken", your_rd_token)
                                addon.setSetting("realdebrid.clientid", your_rd_client_id)
                                addon.setSetting("realdebridrefresh", your_rd_refresh)
                                addon.setSetting("realdebridsecret", your_rd_secret)

                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enable", enabled_rd)

                 
                                if str(chk_auth_umb_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("premiumize.enable", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("premiumize.enable", enabled_pm)

                                if str(chk_auth_umb_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
        except:
                xbmc.log('%s: Umbrella Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #POV RD
        try:
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("rd.token")
                        chk_auth_pov_pm = xbmcaddon.Addon('plugin.video.pov').getSetting("pm.token")
                        chk_auth_pov_ad = xbmcaddon.Addon('plugin.video.pov').getSetting("ad.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_pov) or str(chk_auth_pov) == '':

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("rd.username", your_rd_username)
                                addon.setSetting("rd.token", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                enabled_rd = ("true")
                                addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_pov_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
                        
                                if str(chk_auth_pov_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                xbmc.log('%s: POV Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #The Gears RD
        try:
                if xbmcvfs.exists(var.chk_gears) and xbmcvfs.exists(var.chkset_gears):
                        chk_auth_gears = xbmcaddon.Addon('plugin.video.gears').getSetting("realdebrid.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_gears) or str(chk_auth_gears) == '':

                                addon = xbmcaddon.Addon("plugin.video.gears")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
                                
                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enable", enabled_rd)
        except:
                xbmc.log('%s: The Gears Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Chains Genocide RD
        try:
                if xbmcvfs.exists(var.chk_genocide) and xbmcvfs.exists(var.chkset_genocide):
                        chk_auth_genocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("realdebrid.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_genocide) or str(chk_auth_genocide) == '':

                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
                                
                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enable", enabled_rd)
        except:
                xbmc.log('%s: Genocide Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
     #Dradis RD
        try:
                if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis):
                        chk_auth_dradis = xbmcaddon.Addon('plugin.video.dradis').getSetting("realdebrid.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_dradis) or str(chk_auth_dradis) == '':

                                addon = xbmcaddon.Addon("plugin.video.dradis")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
                                
                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enable", enabled_rd)
        except:
                xbmc.log('%s: Dradis Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Coalition RD
        try:
                if xbmcvfs.exists(var.chk_coal) and xbmcvfs.exists(var.chkset_coal):
                        chk_auth_coal = xbmcaddon.Addon('plugin.video.coalition').getSetting("rd.token")
                        chk_auth_coal_pm = xbmcaddon.Addon('plugin.video.coalition').getSetting("pm.token")
                        chk_auth_coal_ad = xbmcaddon.Addon('plugin.video.coalition').getSetting("ad.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_coal) or str(chk_auth_coal) == '':

                                addon = xbmcaddon.Addon("plugin.video.coalition")
                                addon.setSetting("rd.username", your_rd_username)
                                addon.setSetting("rd.token", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                enabled_rd = ("true")
                                addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_coal_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
                        
                                if str(chk_auth_coal_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                xbmc.log('%s: Coalition Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Seren RD
        try:
                if xbmcvfs.exists(var.chk_seren) and xbmcvfs.exists(var.chkset_seren): #Check that the addon is installed and settings.xml exists
                        
                        #Get add-on setting to compare
                        chk_auth_seren = xbmcaddon.Addon('plugin.video.seren').getSetting("rd.auth")
                        chk_auth_seren_pm = xbmcaddon.Addon('plugin.video.seren').getSetting("premiumize.token")
                        chk_auth_seren_ad = xbmcaddon.Addon('plugin.video.seren').getSetting("alldebrid.apikey")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_seren) or str(chk_auth_seren) == '': #Compare Account Mananger token to Add-on token. If they match authorization is skipped

                                #Write data to settings.xml
                                addon = xbmcaddon.Addon("plugin.video.seren")
                                addon.setSetting("rd.username", your_rd_username)
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                premium_stat = ("Premium")
                                addon.setSetting("realdebrid.premiumstatus", premium_stat)
                                
                                #Enable authorized debrid services
                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enabled", enabled_rd)
                        
                                if str(chk_auth_seren_pm) != '': #Check if Premiumize is authorized
                                        enabled_pm = ("true")
                                        addon.setSetting("premiumize.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("premiumize.enabled", enabled_pm)

                                if str(chk_auth_seren_ad) != '': #Check if Real-Debrid is authorized
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enabled", enabled_ad)
        except:
                xbmc.log('%s: Seren Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku RD
        try:
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.otaku_ud):
                        os.mkdir(var.otaku_ud)
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))
                        
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.chkset_otaku):
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))

                if xbmcvfs.exists(var.chk_otaku) and xbmcvfs.exists(var.chkset_otaku):
                        chk_auth_otaku = xbmcaddon.Addon('plugin.video.otaku').getSetting("rd.auth")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_otaku) or str(chk_auth_otaku) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.otaku")
                                addon.setSetting("rd.username", your_rd_username)
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)
                                
                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enabled", enabled_rd)
        except:
                xbmc.log('%s: Otaku Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku Testing RD
        try:
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.otakut_ud):
                        os.mkdir(var.otakut_ud)
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))
                        
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.chkset_otakut):
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))

                if xbmcvfs.exists(var.chk_otakut) and xbmcvfs.exists(var.chkset_otakut):
                        chk_auth_otakut = xbmcaddon.Addon('plugin.video.otaku.testing').getSetting("realdebrid.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_otakut) or str(chk_auth_otakut) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.otaku.testing")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
                                
                                enabled_rd = ("true")
                                addon.setSetting("realdebrid.enabled", enabled_rd)
        except:
                xbmc.log('%s: Otaku Testing Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
     #Realizer RD
        try:

                if xbmcvfs.exists(var.chk_realx) and not xbmcvfs.exists(var.realx_ud):
                        os.mkdir(var.realx_ud)
                        xbmcvfs.copy(os.path.join(var.realx), os.path.join(var.chkset_realx))
                        
                if xbmcvfs.exists(var.chk_realx) and not xbmcvfs.exists(var.chkset_realx):
                        xbmcvfs.copy(os.path.join(var.realx), os.path.join(var.chkset_realx))

                if xbmcvfs.exists(var.chk_realx) and not xbmcvfs.exists(var.chkset_realx_json):
                        xbmcvfs.copy(os.path.join(var.realx_json), os.path.join(var.chkset_realx_json))

                if xbmcvfs.exists(var.chk_realx) and xbmcvfs.exists(var.chkset_realx) and xbmcvfs.exists(var.chkset_realx_json):
                        
                        with open(var.chkset_realx_json) as r:
                            data = json.load(r)
                            chk_auth_realx = data['token']

                            if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_realx) or str(chk_auth_realx) == '':
                                
                                rdauth = {}
                                rdauth = {'client_id': debridmgr.getSetting('realdebrid.client_id'), 'client_secret': debridmgr.getSetting('realdebrid.secret'), 'token': debridmgr.getSetting('realdebrid.token'), 'refresh_token': debridmgr.getSetting('realdebrid.refresh'), 'added': '202312010243'}

                                with open(var.chkset_realx_json, 'w') as w:
                                        json.dump(rdauth, w)
                        
        except:
                xbmc.log('%s: Realizer Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #All Accounts RD
        try:
                if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.allaccounts_ud):
                        os.mkdir(var.allaccounts_ud)
                        xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                        
                if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.chkset_allaccounts):
                        xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                        
                if xbmcvfs.exists(var.chk_allaccounts) and xbmcvfs.exists(var.chkset_allaccounts):
                        chk_auth_allaccounts = xbmcaddon.Addon('script.module.allaccounts').getSetting("realdebrid.token")
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_allaccounts) or str(chk_auth_allaccounts) == '':

                                addon = xbmcaddon.Addon("script.module.allaccounts")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
        except:
                xbmc.log('%s: All Accounts Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
                     
    #ResolveURL RD
        try:
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.rurl_ud):
                        os.mkdir(var.rurl_ud)
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))
                        
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.chkset_rurl):
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))
                    
                if xbmcvfs.exists(var.chk_rurl) and xbmcvfs.exists(var.chkset_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("RealDebridResolver_token")
                        
                        if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_rurl) or str(chk_auth_rurl) == '':
                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("RealDebridResolver_login", your_rd_username)
                                addon.setSetting("RealDebridResolver_token", your_rd_token)
                                addon.setSetting("RealDebridResolver_client_id", your_rd_client_id)
                                addon.setSetting("RealDebridResolver_refresh", your_rd_refresh)
                                addon.setSetting("RealDebridResolver_client_secret", your_rd_secret)

                                cache_only = ("true")
                                addon.setSetting("RealDebridResolver_cached_only", cache_only)
        except:
                xbmc.log('%s: ResolveURL Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
