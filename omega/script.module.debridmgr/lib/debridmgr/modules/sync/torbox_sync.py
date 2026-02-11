import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

from pathlib import Path
from libs.common import var

char_remov = ["'", ",", ")","("]

#Debrid Manager Torbox
debridmgr = xbmcaddon.Addon("script.module.debridmgr")
your_token = debridmgr.getSetting("torbox.token")
your_acct_id = debridmgr.getSetting("torbox.acct_id")
          
class Auth:
    def torbox_auth(self):
    #Fen Light
        try:
                if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt): #Check that the addon is installed and settings.db exists
                    
                    #Create database connection
                    from debridmgr.modules.db import torbox_db
                    conn = torbox_db.create_conn(var.fenlt_settings_db)
                    
                    #Get add-on settings to compare
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('tb.token',))
                        auth_tb = cursor.fetchone()
                        chk_auth_fenlt = str(auth_tb)
                        cursor.close()
                        
                        #Clean up database results
                        for char in char_remov:
                            chk_auth_fenlt = chk_auth_fenlt.replace(char, "")
                            
                        if not str(var.chk_debridmgr_tb) == chk_auth_fenlt: #Compare Account Mananger data to Add-on data. If they match, authorization is skipped
                            
                            #Write settings to database
                            from debridmgr.modules.db import torbox_db
                            torbox_db.auth_fenlt_tb()
                            var.remake_settings()
        except:
                xbmc.log('%s: Fen Light Torbox Failed!' % var.amgr, xbmc.LOGINFO)
                pass


    #Umbrella
        try:
                if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("torboxtoken")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_umb) or str(chk_auth_umb) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("torboxtoken", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
                                addon.setSetting("torbox.enable", 'true')

        except:
                xbmc.log('%s: Umbrella TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass


    #POV
        try:
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("tb.token")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_pov) or str(chk_auth_pov) == '':

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("tb.token", your_token)
                                addon.setSetting("tb.account_id", your_acct_id)
                                addon.setSetting("tb.enabled", 'true')
                                addon.setSetting("tb.expires", '0')

        except:
                xbmc.log('%s: POV TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #The Gears
        try:
                if xbmcvfs.exists(var.chk_gears) and xbmcvfs.exists(var.chkset_gears):
                        chk_auth_gears = xbmcaddon.Addon('plugin.video.gears').getSetting("torbox.token")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_gears) or str(chk_auth_gears) == '':

                                addon = xbmcaddon.Addon("plugin.video.gears")
                                addon.setSetting("torbox.token", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
                                addon.setSetting("torbox.enable", 'true')
                                addon.setSetting("torbox.expires", '0')

        except:
                xbmc.log('%s: The Gears TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Chains Genocide
        try:
                if xbmcvfs.exists(var.chk_genocide) and xbmcvfs.exists(var.chkset_genocide):
                        chk_auth_genocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("torbox.token")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_genocide) or str(chk_auth_genocide) == '':

                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("torbox.token", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
                                addon.setSetting("torbox.enable", 'true')
                                addon.setSetting("torbox.expires", '0')

        except:
                xbmc.log('%s: Genocide TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Dradis
        try:
                if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis):
                        chk_auth_dradis = xbmcaddon.Addon('plugin.video.dradis').getSetting("torbox.token")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_dradis) or str(chk_auth_dradis) == '':

                                addon = xbmcaddon.Addon("plugin.video.dradis")
                                addon.setSetting("torbox.token", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
                                addon.setSetting("torbox.enable", 'true')
                                addon.setSetting("torbox.expires", '0')

        except:
                xbmc.log('%s: Dradis TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
     #Otaku
        try:
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.otaku_ud):
                        os.mkdir(var.otaku_ud)
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))
                        
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.chkset_otaku):
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))

                if xbmcvfs.exists(var.chk_otaku) and xbmcvfs.exists(var.chkset_otaku):
                        chk_auth_otaku = xbmcaddon.Addon('plugin.video.otaku').getSetting("tb.apikey")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_otaku) or str(chk_auth_otaku) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.otaku")
                                addon.setSetting("tb.apikey", your_token)
                                addon.setSetting("tb.enabled", 'true')
        except:
                xbmc.log('%s: Otaku TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku Testing
        try:
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.otakut_ud):
                        os.mkdir(var.otakut_ud)
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))
                        
                if xbmcvfs.exists(var.chk_otakut) and not xbmcvfs.exists(var.chkset_otakut):
                        xbmcvfs.copy(os.path.join(var.otakut), os.path.join(var.chkset_otakut))

                if xbmcvfs.exists(var.chk_otakut) and xbmcvfs.exists(var.chkset_otakut):
                        chk_auth_otakut = xbmcaddon.Addon('plugin.video.otaku.testing').getSetting("torbox.token")
                        if not str(var.chk_debridmgr_tb) == str(chk_auth_otakut) or str(chk_auth_otakut) == '':
                        
                                addon = xbmcaddon.Addon("plugin.video.otaku.testing")
                                addon.setSetting("torbox.token", your_token)
                                addon.setSetting("torbox.enabled", 'true')
        except:
                xbmc.log('%s: Otaku Testing TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

