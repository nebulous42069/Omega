import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

amgr = 'ReAuthorize ERROR'
addon_id = 'script.module.reauthorize'
addon = xbmcaddon.Addon(addon_id)
setting = addon.getSetting

translatePath = xbmcvfs.translatePath
xmls = translatePath('special://home/addons/script.module.reauthorize/resources/xmls/')
addons = translatePath('special://home/addons/')
addon_data = translatePath('special://profile/addon_data/')
user_path = translatePath('special://profile/')
backup_path = setting('backupfolder')

#Account Manager Trakt API Keys
def traktID():
        return '12ab9767aa51f805d963553442c3784b634075ef2868d3e6552c2073fecced5b'
    
def traktSecret():
        return 'dcaa2635dda30ebb76bce44ce00db8842210b1f0271d70d8f3dcdeca8302022e'

#Trakt Sync List Paths
synclist_file = os.path.join(user_path, 'addon_data/script.module.reauthorize/trakt_sync_list.json')
synclist_backup = translatePath(backup_path + 'trakt/trakt_sync_list.json')

#Backup Trakt Sync List
def backup_synclist():
    if os.path.exists(os.path.join(synclist_file)) and os.path.exists(os.path.join(trakt_backup)):
        try:
                xbmcvfs.copy(synclist_file, synclist_backup)
        except:
            pass

#Restore Trakt Sync List
def restore_synclist():
    if os.path.exists(os.path.join(synclist_backup)):
        try:
                xbmcvfs.copy(synclist_backup, synclist_file)
        except:
            pass

#Delete Trakt Sync List
def delete_synclist():
    if os.path.exists(os.path.join(synclist_file)):
        try:
                os.unlink(synclist_file)
        except:
            pass

#Remake Settings Cache (no-op: was Fen Light-only, that addon is no longer supported)
def remake_settings():
        pass

#Account Mananger Trakt API Keys
client_am = traktID()
secret_am = traktSecret()

#Account Mananger Trakt/Debrid Check
chk_api = traktID()
chk_accountmgr_tk = setting("trakt.token")
chk_accountmgr_tk_rd = setting("realdebrid.token")
chk_accountmgr_tk_pm = setting("premiumize.token")
chk_accountmgr_tk_ad = setting("alldebrid.token")

#Account Manager Metadata Check
chk_accountmgr_fanart = setting("fanart.tv.api.key")
chk_accountmgr_omdb = setting("omdb.api.key")
chk_accountmgr_mdb = setting("mdb.api.key")
chk_accountmgr_imdb = setting("imdb.user")
chk_accountmgr_tmdb = setting("tmdb.api.key")
chk_accountmgr_tmdb_user = setting("tmdb.username")
chk_accountmgr_tmdb_pass = setting("tmdb.password")
chk_accountmgr_tmdb_session = setting("tmdb.session_id")
chk_accountmgr_tvdb = setting("tvdb.api.key")
chk_accountmgr_trakt = setting("trakt.api.key")

#Account Manager Non-Debrid Check
chk_accountmgr_tb = setting("torbox.token")
chk_accountmgr_ed = setting("easydebrid.token")
chk_accountmgr_offc = setting("offcloud.token")
chk_accountmgr_easy = setting("easynews.password")
chk_accountmgr_file = setting("filepursuit.api.key")

#Account Manager External Provider Check
chk_accountmgr_ext = setting("ext.provider")

#Account Manager Backup Paths
rd_backup = translatePath(backup_path) + 'realdebrid/'
pm_backup = translatePath(backup_path) + 'premiumize/'
ad_backup = translatePath(backup_path) + 'alldebrid/'
trakt_backup = translatePath(backup_path) + 'trakt/'
tb_backup = translatePath(backup_path) + 'torbox/'
ed_backup = translatePath(backup_path) + 'easydebrid/'
offc_backup = translatePath(backup_path) + 'offcloud/'
easy_backup = translatePath(backup_path) + 'easynews/'
file_backup = translatePath(backup_path) + 'filepursuit/'
meta_backup = translatePath(backup_path) + 'meta/'
ext_backup = translatePath(backup_path) + 'extproviders/'

#Gears Database Paths
gears_path = os.path.join(user_path, 'addon_data/plugin.video.gears/databases/')
gears_settings_db = os.path.join(gears_path,'settings.db')
gears_trakt_db = os.path.join(gears_path,'traktcache.db')

#Red Light Database Paths
redlight_path = os.path.join(user_path, 'addon_data/plugin.video.redlight/databases/')
redlight_settings_db = os.path.join(redlight_path,'settings.db')

#Realizer Paths
realx_path = os.path.join(user_path, 'addon_data/plugin.video.realizerx')
realx_json_path = os.path.join(realx_path,'rdauth.json')
rd_backup_realx = os.path.join(rd_backup,'rdauth.json')

#Youtube Backup Path
backup_youtube = os.path.join(meta_backup,'youtube.json')

#Account Manager Add-on XML's
seren = xmls + translatePath('plugin.video.seren/settings.xml')
coal = xmls + translatePath('plugin.video.coalition/settings.xml')
pov = xmls + translatePath('plugin.video.pov/settings.xml')
umb = xmls + translatePath('plugin.video.umbrella/settings.xml')
infinity = xmls + translatePath('plugin.video.infinity/settings.xml')
shadow = xmls + translatePath('plugin.video.shadow/settings.xml')
ghost = xmls + translatePath('plugin.video.ghost/settings.xml')
blueballs = xmls + translatePath('plugin.video.blueballs/settings.xml')
twisted = xmls + translatePath('plugin.video.twisted/settings.xml')
base = xmls + translatePath('plugin.video.base/settings.xml')
chains = xmls + translatePath('plugin.video.thechains/settings.xml')
asgard = xmls + translatePath('plugin.video.asgard/settings.xml')
patriot = xmls + translatePath('plugin.video.patriot/settings.xml')
blackl = xmls + translatePath('plugin.video.blacklightning/settings.xml')
metv = xmls + translatePath('plugin.video.metv19/settings.xml')
aliunde = xmls + translatePath('plugin.video.aliundek19/settings.xml')
home = xmls + translatePath('plugin.video.homelander/settings.xml')
quick = xmls + translatePath('plugin.video.quicksilver/settings.xml')
genocide = xmls + translatePath('plugin.video.chainsgenocide/settings.xml')
absol = xmls + translatePath('plugin.video.absolution/settings.xml')
shazam = xmls + translatePath('plugin.video.shazam/settings.xml')
crew = xmls + translatePath('plugin.video.thecrew/settings.xml')
moria = xmls + translatePath('plugin.video.moria/settings.xml')
nine = xmls + translatePath('plugin.video.nine/settings.xml')
scrubs = xmls + translatePath('plugin.video.scrubsv2/settings.xml')
salts = xmls + translatePath('plugin.video.salts/settings.xml')
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
chk_coal = addons + translatePath('plugin.video.coalition/')
chk_pov = addons + translatePath('plugin.video.pov/')
chk_umb = addons + translatePath('plugin.video.umbrella/')
chk_infinity = addons + translatePath('plugin.video.infinity/')
chk_shadow = addons + translatePath('plugin.video.shadow/')
chk_ghost = addons + translatePath('plugin.video.ghost/')
chk_blueballs = addons + translatePath('plugin.video.blueballs/')
chk_twisted = addons + translatePath('plugin.video.twisted/')
chk_base = addons + translatePath('plugin.video.base/')
chk_chains = addons + translatePath('plugin.video.thechains/')
chk_asgard = addons + translatePath('plugin.video.asgard/')
chk_patriot = addons + translatePath('plugin.video.patriot/')
chk_blackl = addons + translatePath('plugin.video.blacklightning/')
chk_metv = addons + translatePath('plugin.video.metv19/')
chk_aliunde = addons + translatePath('plugin.video.aliundek19/')
chk_home = addons + translatePath('plugin.video.homelander/')
chk_quick = addons + translatePath('plugin.video.quicksilver/')
chk_genocide = addons + translatePath('plugin.video.chainsgenocide/')
chk_absol = addons + translatePath('plugin.video.absolution/')
chk_shazam = addons + translatePath('plugin.video.shazam/')
chk_crew = addons + translatePath('plugin.video.thecrew/')
chk_moria = addons + translatePath('plugin.video.moria/')
chk_nine = addons + translatePath('plugin.video.nine/')
chk_scrubs = addons + translatePath('plugin.video.scrubsv2/')
chk_otaku = addons + translatePath('plugin.video.otaku/')
chk_realx = addons + translatePath('plugin.video.realizerx/')
chk_premx = addons + translatePath('plugin.video.premiumizerx/')
chk_allaccounts = addons + translatePath('script.module.allaccounts/')
chk_myaccounts = addons + translatePath('script.module.myaccounts/')
chk_amgr = addons + translatePath('script.module.reauthorize/')
chk_rurl= addons + translatePath('script.module.resolveurl/')
chk_tmdbh = addons + translatePath('plugin.video.themoviedb.helper/')
chk_trakt = addons + translatePath('script.trakt/')
chk_simkl = addons + translatePath('script.simkl/')
chk_embuary = addons + translatePath('script.embuary.info/')
chk_meta = addons + translatePath('script.module.metahandler/')
chk_pvr = addons + translatePath('script.module.pvr.artwork/')
chk_coco = addons + translatePath('script.module.cocoscrapers/')
chk_gears = addons + translatePath('script.module.gearsscrapers/')
chk_gears_video = addons + translatePath('plugin.video.gears/')
chk_newgenocide = addons + translatePath('plugin.video.genocide/')
chk_trakt_player = addons + translatePath('plugin.video.trakt_player/')
chk_gratisred = addons + translatePath('plugin.video.gratisred/')
chk_magneto = addons + translatePath('script.module.magneto/')
chk_viper = addons + translatePath('script.module.viperscrapers/')
chk_salts = addons + translatePath('plugin.video.salts/')
chk_fentastic = addons + translatePath('skin.fentastic/')
chk_nimbus = addons + translatePath('skin.nimbus/')
chk_orion = addons + translatePath('plugin.video.orion/')
chk_redlight = addons + translatePath('plugin.video.redlight/')
chk_thearchives = addons + translatePath('plugin.video.thearchives/')
chk_cosmos = addons + translatePath('plugin.video.cosmos/')
chk_fidok19 = addons + translatePath('plugin.video.fidoK19/')
chk_torquelite = addons + translatePath('plugin.video.torquelite/')
chk_torquelive = addons + translatePath('plugin.video.torquelive/')
chk_rdtplayer = addons + translatePath('plugin.program.rdtplayer/')
chk_prism = addons + translatePath('plugin.video.prism/')
chk_tmdbmovies = addons + translatePath('plugin.video.tmdbmovies/')
chk_youtubetheater = addons + translatePath('plugin.video.youtubetheater/')
chk_nightwing = addons + translatePath('plugin.video.nightwing/')
chk_madtitan = addons + translatePath('plugin.video.madtitansports/')

#Add-on Userdata Paths
seren_ud = addon_data + translatePath('plugin.video.seren/')
coal_ud = addon_data + translatePath('plugin.video.coalition/')
pov_ud = addon_data + translatePath('plugin.video.pov/')
umb_ud = addon_data + translatePath('plugin.video.umbrella/')
infinity_ud = addon_data + translatePath('plugin.video.infinity/')
shadow_ud = addon_data + translatePath('plugin.video.shadow/')
ghost_ud = addon_data + translatePath('plugin.video.ghost/')
blueballs_ud = addon_data + translatePath('plugin.video.blueballs/')
twisted_ud = addon_data + translatePath('plugin.video.twisted/')
base_ud = addon_data + translatePath('plugin.video.base/')
chains_ud = addon_data + translatePath('plugin.video.thechains/')
asgard_ud = addon_data + translatePath('plugin.video.asgard/')
patriot_ud = addon_data + translatePath('plugin.video.patriot/')
blackl_ud = addon_data + translatePath('plugin.video.blacklightning/')
metv_ud = addon_data + translatePath('plugin.video.metv19/')
aliunde_ud = addon_data + translatePath('plugin.video.aliundek19/')
home_ud = addon_data + translatePath('plugin.video.homelander/')
quick_ud = addon_data + translatePath('plugin.video.quicksilver/')
genocide_ud = addon_data + translatePath('plugin.video.chainsgenocide/')
absol_ud = addon_data + translatePath('plugin.video.absolution/')
shazam_ud = addon_data + translatePath('plugin.video.shazam/')
crew_ud = addon_data + translatePath('plugin.video.thecrew/')
moria_ud = addon_data + translatePath('plugin.video.moria/')
nine_ud = addon_data + translatePath('plugin.video.nine/')
scrubs_ud = addon_data + translatePath('plugin.video.scrubsv2/')
salts_ud = addon_data + translatePath('plugin.video.salts/')
otaku_ud = addon_data + translatePath('plugin.video.otaku/')
realx_ud = addon_data + translatePath('plugin.video.realizerx/')
premx_ud = addon_data + translatePath('plugin.video.premiumizerx/')
allaccounts_ud = addon_data + translatePath('script.module.allaccounts/')
myaccounts_ud = addon_data + translatePath('script.module.myaccounts/')
amgr_ud = addon_data + translatePath('script.module.reauthorize/')
rurl_ud = addon_data + translatePath('script.module.resolveurl/')
tmdbh_ud = addon_data + translatePath('plugin.video.themoviedb.helper/')
trakt_ud = addon_data + translatePath('script.trakt/')
simkl_ud = addon_data + translatePath('script.simkl/')
embuary_ud = addon_data + translatePath('script.embuary.info/')
meta_ud = addon_data + translatePath('script.module.metahandler/')
pvr_ud = addon_data + translatePath('script.module.pvr.artwork/')
gears_ud = addon_data + translatePath('plugin.video.gears/')
newgenocide_ud = addon_data + translatePath('plugin.video.genocide/')
orion_ud = addon_data + translatePath('plugin.video.orion/')
redlight_ud = addon_data + translatePath('plugin.video.redlight/')
thearchives_ud = addon_data + translatePath('plugin.video.thearchives/')
cosmos_ud = addon_data + translatePath('plugin.video.cosmos/')
fidok19_ud = addon_data + translatePath('plugin.video.fidoK19/')
torquelite_ud = addon_data + translatePath('plugin.video.torquelite/')
torquelive_ud = addon_data + translatePath('plugin.video.torquelive/')

#Add-on settings.xml Paths
chkset_seren = addon_data + translatePath('plugin.video.seren/settings.xml')
chkset_coal = addon_data + translatePath('plugin.video.coalition/settings.xml')
chkset_pov = addon_data + translatePath('plugin.video.pov/settings.xml')
chkset_umb = addon_data + translatePath('plugin.video.umbrella/settings.xml')
chkset_infinity = addon_data + translatePath('plugin.video.infinity/settings.xml')
chkset_shadow = addon_data + translatePath('plugin.video.shadow/settings.xml')
chkset_ghost = addon_data + translatePath('plugin.video.ghost/settings.xml')
chkset_blueballs = addon_data + translatePath('plugin.video.blueballs/settings.xml')
chkset_twisted = addon_data + translatePath('plugin.video.twisted/settings.xml')
chkset_base = addon_data + translatePath('plugin.video.base/settings.xml')
chkset_chains = addon_data + translatePath('plugin.video.thechains/settings.xml')
chkset_asgard = addon_data + translatePath('plugin.video.asgard/settings.xml')
chkset_patriot = addon_data + translatePath('plugin.video.patriot/settings.xml')
chkset_blackl = addon_data + translatePath('plugin.video.blacklightning/settings.xml')
chkset_metv = addon_data + translatePath('plugin.video.metv19/settings.xml')
chkset_aliunde = addon_data + translatePath('plugin.video.aliundek19/settings.xml')
chkset_home = addon_data + translatePath('plugin.video.homelander/settings.xml')
chkset_quick = addon_data + translatePath('plugin.video.quicksilver/settings.xml')
chkset_genocide = addon_data + translatePath('plugin.video.chainsgenocide/settings.xml')
chkset_absol = addon_data + translatePath('plugin.video.absolution/settings.xml')
chkset_shazam = addon_data + translatePath('plugin.video.shazam/settings.xml')
chkset_crew = addon_data + translatePath('plugin.video.thecrew/settings.xml')
chkset_moria = addon_data + translatePath('plugin.video.moria/settings.xml')
chkset_nine = addon_data + translatePath('plugin.video.nine/settings.xml')
chkset_scrubs = addon_data + translatePath('plugin.video.scrubsv2/settings.xml')
chkset_otaku = addon_data + translatePath('plugin.video.otaku/settings.xml')
chkset_realx = addon_data + translatePath('plugin.video.realizerx/settings.xml')
chkset_realx_json = addon_data + translatePath('plugin.video.realizerx/rdauth.json')
chkset_premx = addon_data + translatePath('plugin.video.premiumizerx/settings.xml')
chkset_allaccounts = addon_data + translatePath('script.module.allaccounts/settings.xml')
chkset_myaccounts = addon_data + translatePath('script.module.myaccounts/settings.xml')
chkset_amgr = addon_data + translatePath('script.module.reauthorize/settings.xml')
chkset_rurl = addon_data + translatePath('script.module.resolveurl/settings.xml')
chkset_tmdbh = addon_data + translatePath('plugin.video.themoviedb.helper/settings.xml')
chkset_trakt = addon_data + translatePath('script.trakt/settings.xml')
chkset_simkl = addon_data + translatePath('script.simkl/settings.xml')
chkset_embuary = addon_data + translatePath('script.embuary.info/settings.xml')
chkset_meta = addon_data + translatePath('script.module.metahandler/settings.xml')
chkset_pvr = addon_data + translatePath('script.module.pvr.artwork/settings.xml')
chkset_salts = addon_data + translatePath('plugin.video.salts/settings.xml')
chkset_gears = addon_data + translatePath('plugin.video.gears/databases/settings.db')
chkset_newgenocide = addon_data + translatePath('plugin.video.genocide/settings.xml')
chkset_trakt_player = addon_data + translatePath('plugin.video.trakt_player/settings.xml')
chkset_gratisred = addon_data + translatePath('plugin.video.gratisred/settings.xml')
chkset_fentastic = addon_data + translatePath('skin.fentastic/settings.xml')
chkset_nimbus = addon_data + translatePath('skin.nimbus/settings.xml')
chkset_orion = addon_data + translatePath('plugin.video.orion/settings.xml')
chkset_redlight = addon_data + translatePath('plugin.video.redlight/settings.xml')
chkset_thearchives = addon_data + translatePath('plugin.video.thearchives/settings.xml')
chkset_cosmos = addon_data + translatePath('plugin.video.cosmos/settings.xml')
chkset_fidok19 = addon_data + translatePath('plugin.video.fidoK19/settings.xml')
chkset_torquelite = addon_data + translatePath('plugin.video.torquelite/settings.xml')
chkset_torquelive = addon_data + translatePath('plugin.video.torquelive/settings.xml')
chkset_rdtplayer = addon_data + translatePath('plugin.program.rdtplayer/settings.xml')
chkset_prism = addon_data + translatePath('plugin.video.prism/settings.xml')
chkset_tmdbmovies = addon_data + translatePath('plugin.video.tmdbmovies/settings.xml')
chkset_youtubetheater = addon_data + translatePath('plugin.video.youtubetheater/settings.xml')
chkset_nightwing = addon_data + translatePath('plugin.video.nightwing/settings.xml')
chkset_madtitan = addon_data + translatePath('plugin.video.madtitansports/settings.xml')

#Skin Setting Paths
path_fentastic = addon_data + translatePath('skin.fentastic/settings.xml')
path_nimbus = addon_data + translatePath('skin.nimbus/settings.xml')

#Skin Setting OS Paths
nimbus = os.path.join(addon_data, 'skin.nimbus/settings.xml')
fentastic = os.path.join(addon_data, 'skin.fentastic/settings.xml')

#Trakt API Key Paths
path_seren = addons + translatePath('plugin.video.seren/resources/lib/indexers/trakt.py')
path_coal = addons + translatePath('plugin.video.coalition/resources/lib/apis/trakt_api.py')
path_shadow = addons + translatePath('plugin.video.shadow/resources/modules/general.py')
path_ghost = addons + translatePath('plugin.video.ghost/resources/modules/general.py')
path_blueballs = addons + translatePath('plugin.video.blueballs/resources/lib/modules/trakt.py')
path_twisted = addons + translatePath('plugin.video.twisted/resources/lib/modules/trakt.py')
path_base = addons + translatePath('plugin.video.base/resources/modules/general.py')
path_chains = addons + translatePath('plugin.video.thechains/resources/modules/general.py')
path_asgard = addons + translatePath('plugin.video.asgard/resources/modules/general.py')
path_patriot = addons + translatePath('plugin.video.patriot/resources/modules/general.py')
# Black Lightning 2.4.2 keeps CLIENT_ID / CLIENT_SECRET in resources/menus.py (general.py imports them from there).
# This pointed at general.py, which holds no key, so the swap did nothing (found by tests/audit_addons.py, 2026-10-05).
path_blackl = addons + translatePath('plugin.video.blacklightning/resources/menus.py')
path_aliunde = addons + translatePath('plugin.video.aliundek19/resources/modules/general.py')
path_genocide = addons + translatePath('plugin.video.chainsgenocide/resources/lib/modules/trakt.py')
# Genocide under its new id keeps its Trakt key in a different file (V2_API_KEY / CLIENT_SECRET, the same values as genocide_client/secret).
path_newgenocide = addons + translatePath('plugin.video.genocide/resources/lib/indexers/trakt.py')
path_crew = addons + translatePath('script.module.thecrew/lib/resources/lib/modules/trakt.py')
path_scrubs = addons + translatePath('plugin.video.scrubsv2/resources/lib/modules/trakt.py')
path_allaccounts = addons + translatePath('script.module.allaccounts/lib/allaccounts/modules/trakt.py')
path_myaccounts = addons + translatePath('script.module.myaccounts/lib/myaccounts/modules/trakt.py')
path_tmdbh = addons + translatePath('plugin.video.themoviedb.helper/resources/tmdbhelper/lib/api/api_keys/trakt.py')
path_trakt = addons + translatePath('script.trakt/resources/lib/traktapi.py')
path_gratisred = addons + translatePath('plugin.video.gratisred/resources/lib/modules/trakt.py')
path_tmdbmovies = addons + translatePath('plugin.video.tmdbmovies/resources/lib/config.py')

#Trakt API Keys
seren_client = '0c9a30819e4af6ffaf3b954cbeae9b54499088513863c03c02911de00ac2de79'
seren_secret = 'bf02417f27b514cee6a8d135f2ddc261a15eecfb6ed6289c36239826dcdd1842'
coal_client = '19849909a0f8c9dc632bc5f5c7ccafd19f3e452e2e44fee05b83fd5dc1e77675'
coal_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
pov_client = '6bc29124c3d9466e06a3ed19a7b5976fcb28311008401e1ce04cf08196f8b16a'
pov_secret = '99478842b17d44d7accafef45c6c1bbba235792753c195069ae149595cd3a919'
shadow_client = '8ed545c0b7f92cc26d1ecd6326995c6cf0053bd7596a98e962a472bee63274e6'
shadow_secret = '1ec4f37e5743e3086abace0c83444c25d9b655d1d77b793806b2c8205a510426'
ghost_client = 'a4e716b4b22b62e59b9e09454435c8710b650b3143dcce553d252b6a66ba60c8'
ghost_secret = 'c6d9aba72214a1ca3c6d45d0351e59f21bbe43df9bbac7c5b740089379f8c5cd'
# V2_API_KEY / CLIENT_SECRET in resources/lib/modules/trakt.py (byte-identical to The Crew's).
blueballs_client = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
blueballs_secret = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
# V2_API_KEY / CLIENT_SECRET in resources/lib/modules/trakt.py (byte-identical to Scrubs V2's).
twisted_client = '63c53edc299b7a05cc6ea2272e8a84e13aade067c18a794362ab9a4a84eafb16'
twisted_secret = '9163ebda9d33acd06c74d017e861404b7212ee34675e09e73365d7536b84eab6'
base_client = '76578d23add0005f9b723fd66f97f1eb0e226f3fac55a3127baaa78e6ed5b303'
base_secret = '7110290e5ecf935c1a3ffb3e6410e34cef5d732ef59dbdb141cef2846c8bd227'
chains_client = '19849909a0f8c9dc632bc5f5c7ccafd19f3e452e2e44fee05b83fd5dc1e77675'
chains_secret = '122b7a79437dcf4b657d3af9e92f2d9ff8939ade532e03bc81bfb5ce798b04b'
asgard_client = '54de56f7b90a4cf7227fd70ecf703c6c043ec135c56ad10c9bb90c539bf2749f'
asgard_secret = 'a43aa6bd62eb5afd37ede4a625457fc903f1961b8384178986bf76eebfcd5999'
patriot_client = '5085635871955f48506576375bf736293c4833d491beca8d962c9da45125b63c'
patriot_secret = '2400cb3da2a3cc1f74b53c43793de8f97e6ea867a5639c8f0b0bde606c067e41'
blackl_client = 'cddec5a35d5d39a8b1e189d8f012dc5046880b8f1bbd67fc2e3b14de1b374b5b'
blackl_secret = '1b4b51a3595d03155813a057a566f32c4c37f2a77bd7888c207d85f31687b57f'
# DEFAULT_TRAKT_CLIENT_ID / _SECRET in resources/modules/general.py - the value
# the addon's Trakt code actually falls back on (byte-identical to Shadow's;
# the old constants here matched a key in resources/menus.py that nothing imports).
aliunde_client = '8ed545c0b7f92cc26d1ecd6326995c6cf0053bd7596a98e962a472bee63274e6'
aliunde_secret = '1ec4f37e5743e3086abace0c83444c25d9b655d1d77b793806b2c8205a510426'
genocide_client = '19849909a0f8c9dc632bc5f5c7ccafd19f3e452e2e44fee05b83fd5dc1e77675'
genocide_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
crew_client = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
crew_secret = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
scrubs_client = '63c53edc299b7a05cc6ea2272e8a84e13aade067c18a794362ab9a4a84eafb16'
scrubs_secret = '9163ebda9d33acd06c74d017e861404b7212ee34675e09e73365d7536b84eab6'
allacts_client = '4f2f0e3cf53e5c3b9ed1e2a203ebff1cd9c91205772f48a9bd2e1ba560e5e1f7'
allacts_secret = '2667c9c1ea787ea15029412f3cdaaec7606f78b187de181f45f2f0db8208e37a'
myacts_client = 'e3a8d1c673dfecb7f669b23ecbf77c75fcfd24d3e8c3dbc7f79ed995262fa1db'
myacts_secret = '73bee6aeee29cb75db4d8771458a440017f7cfe842e85f457ed9d81f7910b349'
tmdbh_client = 'e6fde6173adf3c6af8fd1b0694b9b84d7c519cefc24482310e1de06c6abe5467'
tmdbh_secret = '15119384341d9a61c751d8d515acbc0dd801001d4ebe85d3eef9885df80ee4d9'
trakt_client = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'
trakt_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
# V2_API_KEY / CLIENT_SECRET in GratisRed's resources/lib/modules/trakt.py
# (confirmed by its developer, and read from v1.3.3).
gratisred_client = '33ea6bfa2b06c9cfa3e408fc6b4cc30484f31b90733df3508fd09ce512f47982'
gratisred_secret = '4a294afdab95894be977dc79c9715224dc87a4a88d74944507945ca58bf719b2'
# TRAKT_CLIENT_ID / TRAKT_CLIENT_SECRET in resources/lib/config.py, read as
# ADDON.getSetting('trakt_client_id') or <this value> - the addon's own fallback.
tmdbmovies_client = '67149cca60e6dd23f9f56ba45e1187ce0f9cb9c73363364eb24560c7627c3daf'
tmdbmovies_secret = '7a237effa309ecb580cc167985b5df05f04b1dc163edfd6d2000b8536fc44a92'

#Metadata API Keys
coal_fan = '598515b970d81280063107d49d0e2558'
coal_tmdb = '74f3ce931d65ebda1f77ef24eac2625f'
pov_fan = 'fe073550acf157bdb8a4217f215c0882'
pov_tmdb = 'a07324c669cac4d96789197134ce272b'
home_fan = 'c3469c1cc9465b9f1a1a862feea8b76b'
home_tmdb = 'fb981e5ab89415bba616409d5eb5f05e'
crew_fan = '27bef29779bbffe947232dc310a91f0c'
crew_tmdb = '0049795edb57568b95240bc9e61a9dfc'
