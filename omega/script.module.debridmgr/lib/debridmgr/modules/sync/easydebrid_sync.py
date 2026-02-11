import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

from pathlib import Path
from libs.common import var

char_remov = ["'", ",", ")","("]

#Debrid Manager Easy Debrid
debridmgr = xbmcaddon.Addon("script.module.debridmgr")
your_token = debridmgr.getSetting("easydebrid.token")
your_acct_id = debridmgr.getSetting("easydebrid.acct_id")
          
class Auth:
    def easydebrid_auth(self):
    #Fen Light
        try:
                if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt): #Check that the addon is installed and settings.db exists
                    
                    #Create database connection
                    from debridmgr.modules.db import easydebrid_db
                    conn = easydebrid_db.create_conn(var.fenlt_settings_db)
                    
                    #Get add-on settings to compare
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('ed.token',))
                        auth_ed = cursor.fetchone()
                        chk_auth_fenlt = str(auth_ed)
                        cursor.close()
                        
                        #Clean up database results
                        for char in char_remov:
                            chk_auth_fenlt = chk_auth_fenlt.replace(char, "")
                            
                        if not str(var.chk_debridmgr_ed) == chk_auth_fenlt: #Compare Account Mananger data to Add-on data. If they match, authorization is skipped
                            
                            #Write settings to database
                            from debridmgr.modules.db import easydebrid_db
                            easydebrid_db.auth_fenlt_ed()
                            var.remake_settings()
        except:
                xbmc.log('%s: Fen Light Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass


    #Umbrella
        try:
                if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("easydebridtoken")
                        if not str(var.chk_debridmgr_ed) == str(chk_auth_umb) or str(chk_auth_umb) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("easydebridtoken", your_token)
                                addon.setSetting("easydebrid.enable", 'true')

        except:
                xbmc.log('%s: Umbrella Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass


    #POV
        try:
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("ed.token")
                        if not str(var.chk_debridmgr_ed) == str(chk_auth_pov) or str(chk_auth_pov) == '':

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("ed.token", your_token)
                                addon.setSetting("ed.account_id", your_acct_id)
                                addon.setSetting("ed.enabled", 'true')

        except:
                xbmc.log('%s: POV Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #The Gears
        try:
                if xbmcvfs.exists(var.chk_gears) and xbmcvfs.exists(var.chkset_gears):
                        chk_auth_gears = xbmcaddon.Addon('plugin.video.gears').getSetting("easydebrid.token")
                        if not str(var.chk_debridmgr_ed) == str(chk_auth_gears) or str(chk_auth_gears) == '':

                                addon = xbmcaddon.Addon("plugin.video.gears")
                                addon.setSetting("easydebrid.token", your_token)
                                addon.setSetting("easydebrid.username", your_acct_id)
                                addon.setSetting("easydebrid.enable", 'true')
                                addon.setSetting("easydebrid.expires", '0')

        except:
                xbmc.log('%s: The Gears Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Chains Genocide
        try:
                if xbmcvfs.exists(var.chk_genocide) and xbmcvfs.exists(var.chkset_genocide):
                        chk_auth_genocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("easydebrid.token")
                        if not str(var.chk_debridmgr_ed) == str(chk_auth_genocide) or str(chk_auth_genocide) == '':

                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("easydebrid.token", your_token)
                                addon.setSetting("easydebrid.username", your_acct_id)
                                addon.setSetting("easydebrid.enable", 'true')
                                addon.setSetting("easydebrid.expires", '0')

        except:
                xbmc.log('%s: Genocide Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Dradis
        try:
                if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis):
                        chk_auth_dradis = xbmcaddon.Addon('plugin.video.dradis').getSetting("easydebrid.token")
                        if not str(var.chk_debridmgr_ed) == str(chk_auth_dradis) or str(chk_auth_dradis) == '':

                                addon = xbmcaddon.Addon("plugin.video.dradis")
                                addon.setSetting("easydebrid.token", your_token)
                                addon.setSetting("easydebrid.username", your_acct_id)
                                addon.setSetting("easydebrid.enable", 'true')
                                addon.setSetting("easydebrid.expires", '0')

        except:
                xbmc.log('%s: Dradis Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku
        try:
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.otaku_ud):
                        os.mkdir(var.otaku_ud)
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))
                        
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.chkset_otaku):
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))

                if xbmcvfs.exists(var.chk_otaku) and xbmcvfs.exists(var.chkset_otaku):
                        chk_auth_otaku = xbmcaddon.Addon('plugin.video.otaku').getSetting("easydebrid.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_otaku) or str(chk_auth_otaku) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.otaku")
                                addon.setSetting("easydebrid.username", your_pm_username)
                                addon.setSetting("easydebrid.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("easydebrid.enabled", enabled_pm)
        except:
                xbmc.log('%s: Otaku Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku Testing
        try:
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.otakut_ud):
                        os.mkdir(var.otakut_ud)
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))
                        
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.chkset_otakut):
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))

                if xbmcvfs.exists(var.chk_otakut) and xbmcvfs.exists(var.chkset_otakut):
                        chk_auth_otakut = xbmcaddon.Addon('plugin.video.otaku.testing').getSetting("easydebrid.token")
                        if not str(var.chk_debridmgr_tk_pm) == str(chk_auth_otakut) or str(chk_auth_otakut) == '':
                                
                                addon = xbmcaddon.Addon("plugin.video.otaku.testing")
                                addon.setSetting("easydebrid.username", your_pm_username)
                                addon.setSetting("easydebrid.token", your_pm_token)

                                enabled_pm = ("true")
                                addon.setSetting("easydebrid.enabled", enabled_pm)
        except:
                xbmc.log('%s: Otaku Testing Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

