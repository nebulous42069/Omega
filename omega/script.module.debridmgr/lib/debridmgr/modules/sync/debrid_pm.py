import xbmc, xbmcaddon
import xbmcvfs
import os

from pathlib import Path
from debridmgr.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Debrid Manager Premiumize
debridmgr = xbmcaddon.Addon("script.module.debridmgr")
your_pm_username = debridmgr.getSetting("premiumize.username")
your_pm_token = debridmgr.getSetting("premiumize.token")

class Auth:
    def premiumize_auth(self):
    #Fen Light PM        
        try:
                if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        
                        from debridmgr.modules.db import debrid_db
                        conn = debrid_db.create_conn(var.fenlt_settings_db)
                        
                        with conn:
                            cursor = conn.cursor()
                            cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('pm.token',))
                            auth_pm = cursor.fetchone()
                            chk_auth_fenlt = str(auth_pm)

                            cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('rd.token',))
                            auth_rd = cursor.fetchone()
                            chk_auth_fenlt_rd = str(auth_pm)

                            cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('ad.token',))
                            auth_ad = cursor.fetchone()
                            chk_auth_fenlt_ad = str(auth_ad)
                            cursor.close()
                            
                            for char in char_remov:
                                chk_auth_fenlt = chk_auth_fenlt.replace(char, "")
                                
                            if not str(var.chk_debridmgr_tk_pm) == chk_auth_fenlt:
                                
                                from debridmgr.modules.db import debrid_db
                                debrid_db.auth_fenlt_pm()
                                
                                for char in char_remov:
                                    chk_auth_fenlt_rd = chk_auth_fenlt_rd.replace(char, "")
                                
                                if chk_auth_fenlt_rd != 'empty_setting' or chk_auth_fenlt_rd != '' or chk_auth_fenlt_rd != None:
                                    from debridmgr.modules.db import debrid_db
                                    debrid_db.enable_fenlt_rd()
                                else:
                                    from debridmgr.modules.db import debrid_db
                                    debrid_db.disable_fenlt_rd()
                                    
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
                xbmc.log('%s: Fen Light Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Fen PM
        try:
                if xbmcvfs.exists(var.chk_fen) and xbmcvfs.exists(var.chkset_fen):
                        chk_auth_fen = xbmcaddon.Addon('plugin.video.fen').getSetting("pm.token")
                        chk_auth_fen_rd = xbmcaddon.Addon('plugin.video.fen').getSetting("rd.token")
                        chk_auth_fen_ad = xbmcaddon.Addon('plugin.video.fen').getSetting("ad.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_fen) or str(chk_auth_fen) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.fen")
                                addon.setSetting("pm.account_id", your_pm_username)
                                addon.setSetting("pm.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("pm.enabled", enabled_pm)

                                if str(chk_auth_fen_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_fen_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                xbmc.log('%s: Fen Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Umbrella PM
        try:
                if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("premiumizetoken")
                        chk_auth_umb_rd = xbmcaddon.Addon('plugin.video.umbrella').getSetting("realdebridtoken")
                        chk_auth_umb_ad = xbmcaddon.Addon('plugin.video.umbrella').getSetting("alldebridtoken")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_umb) or str(chk_auth_umb) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("premiumizeusername", your_pm_username)
                                addon.setSetting("premiumizetoken", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enable", enabled_pm)

                                if str(chk_auth_umb_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("realdebrid.enable", enabled_rd)

                                if str(chk_auth_umb_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
        except:
                xbmc.log('%s: Umbrella Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #POV PM
        try:
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("pm.token")
                        chk_auth_pov_rd = xbmcaddon.Addon('plugin.video.pov').getSetting("rd.token")
                        chk_auth_pov_ad = xbmcaddon.Addon('plugin.video.pov').getSetting("ad.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_pov) or str(chk_auth_pov) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("pm.account_id", your_pm_username)
                                addon.setSetting("pm.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("pm.enabled", enabled_pm)

                                if str(chk_auth_pov_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_pov_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                xbmc.log('%s: POV Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass                

     #The Gears PM
        try:
                if xbmcvfs.exists(var.chk_gears) and xbmcvfs.exists(var.chkset_gears):
                        chk_auth_gears = xbmcaddon.Addon('plugin.video.gears').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_gears) or str(chk_auth_gears) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.gears")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enable", enabled_pm)
        except:
                xbmc.log('%s: The Gears Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Chains Genocide PM
        try:
                if xbmcvfs.exists(var.chk_genocide) and xbmcvfs.exists(var.chkset_genocide):
                        chk_auth_genocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_genocide) or str(chk_auth_genocide) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enable", enabled_pm)
        except:
                xbmc.log('%s: Genocide Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
     #Dradis PM
        try:
                if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis):
                        chk_auth_dradis = xbmcaddon.Addon('plugin.video.dradis').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_dradis) or str(chk_auth_dradis) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.dradis")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enable", enabled_pm)
        except:
                xbmc.log('%s: Dradis Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Coalition PM
        try:
                if xbmcvfs.exists(var.chk_coal) and xbmcvfs.exists(var.chkset_coal):
                        chk_auth_coal = xbmcaddon.Addon('plugin.video.coalition').getSetting("pm.token")
                        chk_auth_coal_rd = xbmcaddon.Addon('plugin.video.coalition').getSetting("rd.token")
                        chk_auth_coal_ad = xbmcaddon.Addon('plugin.video.coalition').getSetting("ad.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_coal) or str(chk_auth_coal) == '':

                                addon = xbmcaddon.Addon("plugin.video.coalition")
                                addon.setSetting("pm.account_id", your_pm_username)
                                addon.setSetting("pm.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("pm.enabled", enabled_pm)

                                if str(chk_auth_coal_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_coal_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                xbmc.log('%s: Coalition Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Seren PM
        try:
                if xbmcvfs.exists(var.chk_seren) and xbmcvfs.exists(var.chkset_seren): #Check that the addon is installed and settings.xml exists
                        
                        #Get add-on setting to compare
                        chk_auth_seren = xbmcaddon.Addon('plugin.video.seren').getSetting("premiumize.token")
                        chk_auth_seren_rd = xbmcaddon.Addon('plugin.video.seren').getSetting("rd.auth")
                        chk_auth_seren_ad = xbmcaddon.Addon('plugin.video.seren').getSetting("alldebrid.apikey")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_seren) or str(chk_auth_seren) == '': #Compare Account Mananger token to Add-on token. If they match authorization is skipped
                                
                                #Write data to settings.xml
                                addon = xbmcaddon.Addon("plugin.video.seren")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                premium_stat = ("Premium")
                                addon.setSetting("premiumize.premiumstatus", premium_stat)
                                
                                #Enable authorized debrid services
                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enabled", enabled_pm)

                                if str(chk_auth_seren_rd) != '': #Check if Real-Debrid is authorized
                                        enabled_rd = ("true")
                                        addon.setSetting("realdebrid.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("realdebrid.enabled", enabled_rd)
                        
                                if str(chk_auth_seren_ad) != '': #Check if Premiumize is authorized
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enabled", enabled_ad)
        except:
                xbmc.log('%s: Seren Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku PM
        try:
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.otaku_ud):
                        os.mkdir(var.otaku_ud)
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))
                        
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.chkset_otaku):
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))

                if xbmcvfs.exists(var.chk_otaku) and xbmcvfs.exists(var.chkset_otaku):
                        chk_auth_otaku = xbmcaddon.Addon('plugin.video.otaku').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_otaku) or str(chk_auth_otaku) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.otaku")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enabled", enabled_pm)
        except:
                xbmc.log('%s: Otaku Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku Testing PM
        try:
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.otakut_ud):
                        os.mkdir(var.otakut_ud)
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))
                        
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.chkset_otakut):
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))

                if xbmcvfs.exists(var.chk_otakut) and xbmcvfs.exists(var.chkset_otakut):
                        chk_auth_otakut = xbmcaddon.Addon('plugin.video.otaku.testing').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_otakut) or str(chk_auth_otakut) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.otaku.testing")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("premiumize.enabled", enabled_pm)
        except:
                xbmc.log('%s: Otaku Testing Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Premiumizer PM
        try:
                if xbmcvfs.exists(var.chk_premx) and not xbmcvfs.exists(var.premx_ud):
                        os.mkdir(var.premx_ud)
                        xbmcvfs.copy(os.path.join(var.premx), os.path.join(var.chkset_premx))
                        
                if xbmcvfs.exists(var.chk_premx) and not xbmcvfs.exists(var.chkset_premx):
                        xbmcvfs.copy(os.path.join(var.premx), os.path.join(var.chkset_premx))

                if xbmcvfs.exists(var.chk_premx) and xbmcvfs.exists(var.chkset_premx):
                        chk_auth_premx = xbmcaddon.Addon('plugin.video.premiumizerx').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_premx) or str(chk_auth_premx) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.premiumizerx")
                                addon.setSetting("premiumize.status", 'Authorized')
                                addon.setSetting("premiumize.token", your_pm_token)
                                addon.setSetting("premiumize.refresh", '315360000')
        except:
                xbmc.log('%s: Premiumizer Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #All Accounts PM
        try:
                if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.allaccounts_ud):
                        os.mkdir(var.allaccounts_ud)
                        xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                        
                if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.chkset_allaccounts):
                        xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                        
                if xbmcvfs.exists(var.chk_allaccounts) and xbmcvfs.exists(var.chkset_allaccounts):
                        chk_auth_allaccounts = xbmcaddon.Addon('script.module.allaccounts').getSetting("premiumize.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_allaccounts) or str(chk_auth_allaccounts) == '':
                        
                                addon = xbmcaddon.Addon("script.module.allaccounts")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)
        except:
                xbmc.log('%s: All Accounts Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
     
    #ResolveURL PM
        try:
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.rurl_ud):
                        os.mkdir(var.rurl_ud)
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))
                        
                if xbmcvfs.exists(var.chk_rurl) and not xbmcvfs.exists(var.chkset_rurl):
                        xbmcvfs.copy(os.path.join(var.rurl), os.path.join(var.chkset_rurl))
                        
                if xbmcvfs.exists(var.chk_rurl) and xbmcvfs.exists(var.chkset_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("PremiumizeMeResolver_token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_rurl) or str(chk_auth_rurl) == '':
                        
                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("PremiumizeMeResolver_token", your_pm_token)

                                cache_only = ("true")
                                addon.setSetting("PremiumizeMeResolver_cached_only", cache_only)
        except:
                xbmc.log('%s: ResolveURL Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
