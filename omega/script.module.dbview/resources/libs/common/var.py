import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

amgr = 'Debrid Manager ERROR'
addon_id = 'script.module.debridmgr'
addon = xbmcaddon.Addon(addon_id)
setting = addon.getSetting

translatePath = xbmcvfs.translatePath
xmls = translatePath('special://home/addons/script.module.debridmgr/resources/xmls/')
addons = translatePath('special://home/addons/')
addon_data = translatePath('special://profile/addon_data/')
user_path = translatePath('special://profile/')
backup_path = setting('backupfolder')

#dbview Open Add-on Settings
def open_settings(who):
    addonid = tools.get_addon_by_id(script.module.debridmgr)
    addonid.openSettings()
    xbmc.executebuiltin('Container.Refresh()')
    
def open_settings_fenlt():
    xbmc.executebuiltin('PlayMedia(plugin://plugin.video.fenlight/?mode=open_settings)')
        
#Remake Settings Cache
def remake_settings():
        if not xbmcvfs.exists(chk_fenlt):
        #if not xbmcvfs.exists(chk_fenlt) or xbmcvfs.exists(chk_affen):
                pass
        else:
                if xbmcvfs.exists(chk_fenlt):
                        xbmc.executebuiltin('PlayMedia(plugin://plugin.video.fenlight/?mode=sync_settings&silent=true)')
                        xbmc.sleep(1000)
                #if xbmcvfs.exists(chk_affen):
                        #xbmc.executebuiltin('PlayMedia(plugin://plugin.video.affenity/?mode=sync_settings&silent=true)')
                        #xbmc.sleep(1000)
        
#Account Mananger Trakt/Debrid Check
chk_debridmgr_tk_rd = setting("realdebrid.token")
chk_debridmgr_tk_pm = setting("premiumize.token")
chk_debridmgr_tk_ad = setting("alldebrid.token")

#Debrid Manager Non-Debrid Check
chk_debridmgr_tb = setting("torbox.token")
chk_debridmgr_ed = setting("easydebrid.token")
chk_debridmgr_offc = setting("offcloud.token")

#Debrid Manager External Provider Check
chk_debridmgr_ext = setting("ext.provider")

#Debrid Manager Backup Paths
rd_backup = translatePath(backup_path) + 'realdebrid/'
pm_backup = translatePath(backup_path) + 'premiumize/'
ad_backup = translatePath(backup_path) + 'alldebrid/'
tb_backup = translatePath(backup_path) + 'torbox/'
ed_backup = translatePath(backup_path) + 'easydebrid/'
offc_backup = translatePath(backup_path) + 'offcloud/'
ext_backup = translatePath(backup_path) + 'extproviders/'

#Fen Light Database Paths
fen_lt_path = os.path.join(user_path, 'addon_data/plugin.video.fenlight/databases/')
fenlt_settings_db = os.path.join(fen_lt_path,'settings.db')

#Fen Light Backup Paths
rd_backup_fenlt = os.path.join(rd_backup,'fenlt_rd.db')
pm_backup_fenlt = os.path.join(pm_backup,'fenlt_pm.db')
ad_backup_fenlt = os.path.join(ad_backup,'fenlt_ad.db')
tb_backup_fenlt = os.path.join(tb_backup,'fenlt_tb.db')
ed_backup_fenlt = os.path.join(ed_backup,'fenlt_ed.db')
offc_backup_fenlt = os.path.join(offc_backup,'fenlt_offc.db')
ext_backup_fenlt = os.path.join(ext_backup,'fenlt_ext.db')

#Realizer Paths
realx_path = os.path.join(user_path, 'addon_data/plugin.video.realizerx')
realx_json_path = os.path.join(realx_path,'rdauth.json')
rd_backup_realx = os.path.join(rd_backup,'rdauth.json')

#Debrid Manager Add-on XML's
seren = xmls + translatePath('plugin.video.seren/settings.xml')
fen = xmls + translatePath('plugin.video.fen/settings.xml')
coal = xmls + translatePath('plugin.video.coalition/settings.xml')
pov = xmls + translatePath('plugin.video.pov/settings.xml')
umb = xmls + translatePath('plugin.video.umbrella/settings.xml')
gears = xmls + translatePath('plugin.video.gears/settings.xml')
genocide = xmls + translatePath('plugin.video.genocide/settings.xml')
dradis = xmls + translatePath('plugin.video.dradis/settings.xml')
otaku = xmls + translatePath('plugin.video.otaku/settings.xml')
otakut = xmls + translatePath('plugin.video.otaku.testing/settings.xml')
realx = xmls + translatePath('plugin.video.realizerx/settings.xml')
realx_json = xmls + translatePath('plugin.video.realizerx/rdauth.json')
premx = xmls + translatePath('plugin.video.premiumizerx/settings.xml')
allaccounts = xmls + translatePath('script.module.allaccounts/settings.xml')
rurl = xmls + translatePath('script.module.resolveurl/settings.xml')

#Add-on Paths
chk_seren = addons + translatePath('plugin.video.seren/')
chk_fen = addons + translatePath('plugin.video.fen/')
chk_fenlt = addons + translatePath('plugin.video.fenlight/')
chk_coal = addons + translatePath('plugin.video.coalition/')
chk_pov = addons + translatePath('plugin.video.pov/')
chk_umb = addons + translatePath('plugin.video.umbrella/')
chk_gears = addons + translatePath('plugin.video.gears/')
chk_genocide = addons + translatePath('plugin.video.genocide/')
chk_dradis = addons + translatePath('plugin.video.dradis/')
chk_otaku = addons + translatePath('plugin.video.otaku/')
chk_otakut = addons + translatePath('plugin.video.otaku.testing/')
chk_realx = addons + translatePath('plugin.video.realizerx/')
chk_premx = addons + translatePath('plugin.video.premiumizerx/')
chk_allaccounts = addons + translatePath('script.module.allaccounts/')
chk_amgr = addons + translatePath('script.module.debridmgr/')
chk_rurl= addons + translatePath('script.module.resolveurl/')
chk_coco = addons + translatePath('script.module.cocoscrapers/')
chk_mag = addons + translatePath('script.module.magneto/')

#Add-on Userdata Paths
seren_ud = addon_data + translatePath('plugin.video.seren/')
fen_ud = addon_data + translatePath('plugin.video.fen/')
coal_ud = addon_data + translatePath('plugin.video.coalition/')
pov_ud = addon_data + translatePath('plugin.video.pov/')
umb_ud = addon_data + translatePath('plugin.video.umbrella/')
gears_ud = addon_data + translatePath('plugin.video.gears/')
genocide_ud = addon_data + translatePath('plugin.video.genocide/')
dradis_ud = addon_data + translatePath('plugin.video.dradis/')
otaku_ud = addon_data + translatePath('plugin.video.otaku/')
otakut_ud = addon_data + translatePath('plugin.video.otaku.testing/')
realx_ud = addon_data + translatePath('plugin.video.realizerx/')
premx_ud = addon_data + translatePath('plugin.video.premiumizerx/')
allaccounts_ud = addon_data + translatePath('script.module.allaccounts/')
amgr_ud = addon_data + translatePath('script.module.debridmgr/')
rurl_ud = addon_data + translatePath('script.module.resolveurl/')

#Add-on settings.xml Paths
chkset_seren = addon_data + translatePath('plugin.video.seren/settings.xml')
chkset_fen = addon_data + translatePath('plugin.video.fen/settings.xml')
chkset_fenlt = addon_data + translatePath('plugin.video.fenlight/databases/settings.db')
chkset_coal = addon_data + translatePath('plugin.video.coalition/settings.xml')
chkset_pov = addon_data + translatePath('plugin.video.pov/settings.xml')
chkset_umb = addon_data + translatePath('plugin.video.umbrella/settings.xml')
chkset_gears = addon_data + translatePath('plugin.video.gears/settings.xml')
chkset_genocide = addon_data + translatePath('plugin.video.genocide/settings.xml')
chkset_dradis = addon_data + translatePath('plugin.video.dradis/settings.xml')
chkset_otaku = addon_data + translatePath('plugin.video.otaku/settings.xml')
chkset_otakut = addon_data + translatePath('plugin.video.otaku.testing/settings.xml')
chkset_realx = addon_data + translatePath('plugin.video.realizerx/settings.xml')
chkset_realx_json = addon_data + translatePath('plugin.video.realizerx/rdauth.json')
chkset_premx = addon_data + translatePath('plugin.video.premiumizerx/settings.xml')
chkset_allaccounts = addon_data + translatePath('script.module.allaccounts/settings.xml')
chkset_amgr = addon_data + translatePath('script.module.debridmgr/settings.xml')
chkset_rurl = addon_data + translatePath('script.module.resolveurl/settings.xml')
