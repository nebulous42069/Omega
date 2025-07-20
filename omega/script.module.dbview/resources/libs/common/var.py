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

#afFEnity Database Paths
#affen_lt_path = os.path.join(user_path, 'addon_data/plugin.video.affenity/databases')
#affen_settings_db = os.path.join(affen_lt_path,'settings.db')
#affen_traktcache = addon_data + translatePath('plugin.video.affenity/databases')
#affen_trakt_db = os.path.join(affen_traktcache,'traktcache.db')

#afFENity Backup Paths
#rd_backup_affen = os.path.join(rd_backup,'affen_rd.db')
#pm_backup_affen = os.path.join(pm_backup,'affen_pm.db')
#ad_backup_affen = os.path.join(ad_backup,'affen_ad.db')
#trakt_backup_affen = os.path.join(trakt_backup,'affen_trakt.db')
#easy_backup_affen = os.path.join(easy_backup,'affen_easy.db')
#meta_backup_affen = os.path.join(meta_backup,'affen_meta.db')

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
infinity = xmls + translatePath('plugin.video.infinity/settings.xml')
dradis = xmls + translatePath('plugin.video.dradis/settings.xml')
shadow = xmls + translatePath('plugin.video.shadow/settings.xml')
ghost = xmls + translatePath('plugin.video.ghost/settings.xml')
base = xmls + translatePath('plugin.video.base/settings.xml')
chains = xmls + translatePath('plugin.video.thechains/settings.xml')
asgard = xmls + translatePath('plugin.video.asgard/settings.xml')
patriot = xmls + translatePath('plugin.video.patriot/settings.xml')
blackl = xmls + translatePath('plugin.video.blacklightning/settings.xml')
metv = xmls + translatePath('plugin.video.metv19/settings.xml')
aliunde = xmls + translatePath('plugin.video.aliundek19/settings.xml')
night = xmls + translatePath('plugin.video.NightwingLite/settings.xml')
home = xmls + translatePath('plugin.video.homelander/settings.xml')
quick = xmls + translatePath('plugin.video.quicksilver/settings.xml')
genocide = xmls + translatePath('plugin.video.chainsgenocide/settings.xml')
absol = xmls + translatePath('plugin.video.absolution/settings.xml')
shazam = xmls + translatePath('plugin.video.shazam/settings.xml')
crew = xmls + translatePath('plugin.video.thecrew/settings.xml')
alvin = xmls + translatePath('plugin.video.alvin/settings.xml')
moria = xmls + translatePath('plugin.video.moria/settings.xml')
nine = xmls + translatePath('plugin.video.nine/settings.xml')
scrubs = xmls + translatePath('plugin.video.scrubsv2/settings.xml')
otaku = xmls + translatePath('plugin.video.otaku/settings.xml')
realx = xmls + translatePath('plugin.video.realizerx/settings.xml')
realx_json = xmls + translatePath('plugin.video.realizerx/rdauth.json')
premx = xmls + translatePath('plugin.video.premiumizerx/settings.xml')
allaccounts = xmls + translatePath('script.module.allaccounts/settings.xml')
myaccounts = xmls + translatePath('script.module.myaccounts/settings.xml')
rurl = xmls + translatePath('script.module.resolveurl/settings.xml')
tmdbh = xmls + translatePath('plugin.video.themoviedb.helper/settings.xml')
trakt = xmls + translatePath('script.trakt/settings.xml')
simkl = xmls + translatePath('script.simkl/settings.xml')
embuary = xmls + translatePath('script.embuary.info/settings.xml')
meta = xmls + translatePath('script.module.metahandler/settings.xml')
pvr = xmls + translatePath('script.module.pvr.artwork/settings.xml')

#Add-on Paths
chk_seren = addons + translatePath('plugin.video.seren/')
chk_fen = addons + translatePath('plugin.video.fen/')
chk_fenlt = addons + translatePath('plugin.video.fenlight/')
#chk_affen = addons + translatePath('plugin.video.affenity/')
chk_coal = addons + translatePath('plugin.video.coalition/')
chk_pov = addons + translatePath('plugin.video.pov/')
chk_umb = addons + translatePath('plugin.video.umbrella/')
chk_infinity = addons + translatePath('plugin.video.infinity/')
chk_dradis = addons + translatePath('plugin.video.dradis/')
chk_shadow = addons + translatePath('plugin.video.shadow/')
chk_ghost = addons + translatePath('plugin.video.ghost/')
chk_base = addons + translatePath('plugin.video.base/')
chk_chains = addons + translatePath('plugin.video.thechains/')
chk_asgard = addons + translatePath('plugin.video.asgard/')
chk_patriot = addons + translatePath('plugin.video.patriot/')
chk_blackl = addons + translatePath('plugin.video.blacklightning/')
chk_metv = addons + translatePath('plugin.video.metv19/')
chk_aliunde = addons + translatePath('plugin.video.aliundek19/')
chk_night = addons + translatePath('plugin.video.NightwingLite/')
chk_home = addons + translatePath('plugin.video.homelander/')
chk_quick = addons + translatePath('plugin.video.quicksilver/')
chk_genocide = addons + translatePath('plugin.video.chainsgenocide/')
chk_absol = addons + translatePath('plugin.video.absolution/')
chk_shazam = addons + translatePath('plugin.video.shazam/')
chk_crew = addons + translatePath('plugin.video.thecrew/')
chk_alvin = addons + translatePath('plugin.video.alvin/')
chk_moria = addons + translatePath('plugin.video.moria/')
chk_nine = addons + translatePath('plugin.video.nine/')
chk_scrubs = addons + translatePath('plugin.video.scrubsv2/')
chk_otaku = addons + translatePath('plugin.video.otaku/')
chk_realx = addons + translatePath('plugin.video.realizerx/')
chk_premx = addons + translatePath('plugin.video.premiumizerx/')
chk_allaccounts = addons + translatePath('script.module.allaccounts/')
chk_myaccounts = addons + translatePath('script.module.myaccounts/')
chk_amgr = addons + translatePath('script.module.debridmgr/')
chk_rurl= addons + translatePath('script.module.resolveurl/')
chk_tmdbh = addons + translatePath('plugin.video.themoviedb.helper/')
chk_trakt = addons + translatePath('script.trakt/')
chk_simkl = addons + translatePath('script.simkl/')
chk_embuary = addons + translatePath('script.embuary.info/')
chk_meta = addons + translatePath('script.module.metahandler/')
chk_pvr = addons + translatePath('script.module.pvr.artwork/')
chk_coco = addons + translatePath('script.module.cocoscrapers/')
chk_fentastic = addons + translatePath('skin.fentastic/')
chk_nimbus = addons + translatePath('skin.nimbus/')

#Add-on Userdata Paths
seren_ud = addon_data + translatePath('plugin.video.seren/')
fen_ud = addon_data + translatePath('plugin.video.fen/')
coal_ud = addon_data + translatePath('plugin.video.coalition/')
pov_ud = addon_data + translatePath('plugin.video.pov/')
umb_ud = addon_data + translatePath('plugin.video.umbrella/')
infinity_ud = addon_data + translatePath('plugin.video.infinity/')
dradis_ud = addon_data + translatePath('plugin.video.dradis/')
shadow_ud = addon_data + translatePath('plugin.video.shadow/')
ghost_ud = addon_data + translatePath('plugin.video.ghost/')
base_ud = addon_data + translatePath('plugin.video.base/')
chains_ud = addon_data + translatePath('plugin.video.thechains/')
asgard_ud = addon_data + translatePath('plugin.video.asgard/')
patriot_ud = addon_data + translatePath('plugin.video.patriot/')
blackl_ud = addon_data + translatePath('plugin.video.blacklightning/')
metv_ud = addon_data + translatePath('plugin.video.metv19/')
aliunde_ud = addon_data + translatePath('plugin.video.aliundek19/')
night_ud = addon_data + translatePath('plugin.video.NightwingLite/')
home_ud = addon_data + translatePath('plugin.video.homelander/')
quick_ud = addon_data + translatePath('plugin.video.quicksilver/')
genocide_ud = addon_data + translatePath('plugin.video.chainsgenocide/')
absol_ud = addon_data + translatePath('plugin.video.absolution/')
shazam_ud = addon_data + translatePath('plugin.video.shazam/')
crew_ud = addon_data + translatePath('plugin.video.thecrew/')
alvin_ud = addon_data + translatePath('plugin.video.alvin/')
moria_ud = addon_data + translatePath('plugin.video.moria/')
nine_ud = addon_data + translatePath('plugin.video.nine/')
scrubs_ud = addon_data + translatePath('plugin.video.scrubsv2/')
otaku_ud = addon_data + translatePath('plugin.video.otaku/')
realx_ud = addon_data + translatePath('plugin.video.realizerx/')
premx_ud = addon_data + translatePath('plugin.video.premiumizerx/')
allaccounts_ud = addon_data + translatePath('script.module.allaccounts/')
myaccounts_ud = addon_data + translatePath('script.module.myaccounts/')
amgr_ud = addon_data + translatePath('script.module.debridmgr/')
rurl_ud = addon_data + translatePath('script.module.resolveurl/')
tmdbh_ud = addon_data + translatePath('plugin.video.themoviedb.helper/')
trakt_ud = addon_data + translatePath('script.trakt/')
simkl_ud = addon_data + translatePath('script.simkl/')
embuary_ud = addon_data + translatePath('script.embuary.info/')
meta_ud = addon_data + translatePath('script.module.metahandler/')
pvr_ud = addon_data + translatePath('script.module.pvr.artwork/')

#Add-on settings.xml Paths
chkset_seren = addon_data + translatePath('plugin.video.seren/settings.xml')
chkset_fen = addon_data + translatePath('plugin.video.fen/settings.xml')
chkset_fenlt = addon_data + translatePath('plugin.video.fenlight/databases/settings.db')
#chkset_affen = addon_data + translatePath('plugin.video.affenity/databases/settings.db')
chkset_coal = addon_data + translatePath('plugin.video.coalition/settings.xml')
chkset_pov = addon_data + translatePath('plugin.video.pov/settings.xml')
chkset_umb = addon_data + translatePath('plugin.video.umbrella/settings.xml')
chkset_infinity = addon_data + translatePath('plugin.video.infinity/settings.xml')
chkset_dradis = addon_data + translatePath('plugin.video.dradis/settings.xml')
chkset_shadow = addon_data + translatePath('plugin.video.shadow/settings.xml')
chkset_ghost = addon_data + translatePath('plugin.video.ghost/settings.xml')
chkset_base = addon_data + translatePath('plugin.video.base/settings.xml')
chkset_chains = addon_data + translatePath('plugin.video.thechains/settings.xml')
chkset_asgard = addon_data + translatePath('plugin.video.asgard/settings.xml')
chkset_patriot = addon_data + translatePath('plugin.video.patriot/settings.xml')
chkset_blackl = addon_data + translatePath('plugin.video.blacklightning/settings.xml')
chkset_metv = addon_data + translatePath('plugin.video.metv19/settings.xml')
chkset_aliunde = addon_data + translatePath('plugin.video.aliundek19/settings.xml')
chkset_night = addon_data + translatePath('plugin.video.NightwingLite/settings.xml')
chkset_home = addon_data + translatePath('plugin.video.homelander/settings.xml')
chkset_quick = addon_data + translatePath('plugin.video.quicksilver/settings.xml')
chkset_genocide = addon_data + translatePath('plugin.video.chainsgenocide/settings.xml')
chkset_absol = addon_data + translatePath('plugin.video.absolution/settings.xml')
chkset_shazam = addon_data + translatePath('plugin.video.shazam/settings.xml')
chkset_crew = addon_data + translatePath('plugin.video.thecrew/settings.xml')
chkset_alvin = addon_data + translatePath('plugin.video.alvin/settings.xml')
chkset_moria = addon_data + translatePath('plugin.video.moria/settings.xml')
chkset_nine = addon_data + translatePath('plugin.video.nine/settings.xml')
chkset_scrubs = addon_data + translatePath('plugin.video.scrubsv2/settings.xml')
chkset_otaku = addon_data + translatePath('plugin.video.otaku/settings.xml')
chkset_realx = addon_data + translatePath('plugin.video.realizerx/settings.xml')
chkset_realx_json = addon_data + translatePath('plugin.video.realizerx/rdauth.json')
chkset_premx = addon_data + translatePath('plugin.video.premiumizerx/settings.xml')
chkset_allaccounts = addon_data + translatePath('script.module.allaccounts/settings.xml')
chkset_myaccounts = addon_data + translatePath('script.module.myaccounts/settings.xml')
chkset_amgr = addon_data + translatePath('script.module.debridmgr/settings.xml')
chkset_rurl = addon_data + translatePath('script.module.resolveurl/settings.xml')
chkset_tmdbh = addon_data + translatePath('plugin.video.themoviedb.helper/settings.xml')
chkset_trakt = addon_data + translatePath('script.trakt/settings.xml')
chkset_simkl = addon_data + translatePath('script.simkl/settings.xml')
chkset_embuary = addon_data + translatePath('script.embuary.info/settings.xml')
chkset_meta = addon_data + translatePath('script.module.metahandler/settings.xml')
chkset_pvr = addon_data + translatePath('script.module.pvr.artwork/settings.xml')
chkset_fentastic = addon_data + translatePath('skin.fentastic/settings.xml')
chkset_nimbus = addon_data + translatePath('skin.nimbus/settings.xml')

#Skin Setting Paths
path_fentastic = addon_data + translatePath('skin.fentastic/settings.xml')
path_nimbus = addon_data + translatePath('skin.nimbus/settings.xml')

#Skin Setting OS Paths
nimbus = os.path.join(addon_data, 'skin.nimbus/settings.xml')
fentastic = os.path.join(addon_data, 'skin.fentastic/settings.xml')
