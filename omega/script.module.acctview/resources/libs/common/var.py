import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os

amgr = 'Account Manager ERROR'
addon_id = 'script.module.accountmgr'
addon = xbmcaddon.Addon(addon_id)
setting = addon.getSetting

translatePath = xbmcvfs.translatePath
home = translatePath('special://home/')
xmls = translatePath('special://home/addons/script.module.accountmgr/resources/xmls/')
addons = translatePath('special://home/addons/')
addon_data = translatePath('special://userdata/addon_data/')

user_path = os.path.join(home, 'userdata/')
backup_path = setting('backupfolder')

#Account Manager Custom Trakt API Check
def traktID():
        traktId = '4a479b95c8224999eef8d418cfe6c7a4389e2837441672c48c9c8168ea42a407'
        if setting('trakt.client.id') != '' and setting('traktuserkey.enabled') == 'true':
                traktId = str(setting('trakt.client.id'))
        if setting('dev.client.id') != '' and setting('devuserkey.enabled') == 'true':
                traktId = str(setting('dev.client.id'))
        return traktId
    
def traktSecret():
        traktSecret = '89d8f8f71b312985a9e1f91e9eb426e23050102734bb1fa36ec76cdc74452ab6'
        if setting('trakt.client.secret') != '' and setting('traktuserkey.enabled') == 'true':
                traktSecret = str(setting('trakt.client.secret'))
        if setting('dev.client.secret') != '' and setting('devuserkey.enabled') == 'true':
                traktSecret = str(setting('dev.client.secret'))
        return traktSecret

def rm_traktcache():
        if setting('rm_traktcache')=='true':
                if os.path.exists(os.path.join(fenlt_trakt_db)):
                        try:
                                os.unlink(os.path.join(fenlt_trakt_db))
                        except OSError:
                                pass
                if os.path.exists(os.path.join(affen_trakt_db)):
                        try:
                                os.unlink(os.path.join(affen_trakt_db))
                        except OSError:
                                pass
                addon.setSetting("rm_traktcache", 'false')
                
#Account Mananger Trakt API Keys
client_am = traktID()
secret_am = traktSecret()

#Account Mananger Trakt & Debrid Check
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
chk_accountmgr_furk = setting("furk.password")
chk_accountmgr_easy = setting("easynews.password")
chk_accountmgr_file = setting("filepursuit.api.key")

#Account Manager Backup Paths
rd_backup = translatePath(backup_path) + 'realdebrid/'
pm_backup = translatePath(backup_path) + 'premiumize/'
ad_backup = translatePath(backup_path) + 'alldebrid/'
trakt_backup = translatePath(backup_path) + 'trakt/'
non_backup = translatePath(backup_path) + 'nondebrid/'
meta_backup = translatePath(backup_path) + 'meta/'

#Fen Light Database Paths
fen_lt_path = os.path.join(user_path, 'addon_data/plugin.video.fenlight/databases')
fenlt_settings_db = os.path.join(fen_lt_path,'settings.db')
fenlt_traktcache = os.path.join(user_path, 'addon_data/plugin.video.fenlight/databases')
fenlt_trakt_db = os.path.join(fenlt_traktcache,'traktcache.db')

#Fen Light Backup Paths
rd_backup_fenlt = os.path.join(rd_backup,'fenlt_rd.db')
pm_backup_fenlt = os.path.join(pm_backup,'fenlt_pm.db')
ad_backup_fenlt = os.path.join(ad_backup,'fenlt_ad.db')
trakt_backup_fenlt = os.path.join(trakt_backup,'fenlt_trakt.db')
meta_backup_fenlt = os.path.join(meta_backup,'fenlt_meta.db')
easy_backup_fenlt = os.path.join(non_backup,'fenlt_nondebrid.db')

#afFEnity Database Paths
affen_lt_path = os.path.join(user_path, 'addon_data/plugin.video.affenity/databases')
affen_settings_db = os.path.join(affen_lt_path,'settings.db')
affen_traktcache = addon_data + translatePath('plugin.video.affenity/databases')
affen_trakt_db = os.path.join(affen_traktcache,'traktcache.db')

#afFENity Backup Paths
rd_backup_affen = os.path.join(rd_backup,'affen_rd.db')
pm_backup_affen = os.path.join(pm_backup,'affen_pm.db')
ad_backup_affen = os.path.join(ad_backup,'affen_ad.db')
trakt_backup_affen = os.path.join(trakt_backup,'affen_trakt.db')
meta_backup_affen = os.path.join(meta_backup,'affen_meta.db')
easy_backup_affen = os.path.join(non_backup,'affen_nondebrid.db')

#Realizer Paths
realx_path = os.path.join(user_path, 'addon_data/plugin.video.realizerx')
realx_json_path = os.path.join(realx_path,'rdauth.json')
rd_backup_realx = os.path.join(rd_backup,'rdauth.json')

#Youtube Backup Path
backup_youtube = os.path.join(meta_backup,'youtube.json')

#Account Manager Add-on XML's
seren = xmls + translatePath('plugin.video.seren/settings.xml')
fen = xmls + translatePath('plugin.video.fen/settings.xml')
ezra = xmls + translatePath('plugin.video.ezra/settings.xml')
coal = xmls + translatePath('plugin.video.coalition/settings.xml')
pov = xmls + translatePath('plugin.video.pov/settings.xml')
umb = xmls + translatePath('plugin.video.umbrella/settings.xml')
dradis = xmls + translatePath('plugin.video.dradis/settings.xml')
taz = xmls + translatePath('plugin.video.taz19/settings.xml')
shadow = xmls + translatePath('plugin.video.shadow/settings.xml')
ghost = xmls + translatePath('plugin.video.ghost/settings.xml')
base = xmls + translatePath('plugin.video.base/settings.xml')
unleashed = xmls + translatePath('plugin.video.unleashed/settings.xml')
chains = xmls + translatePath('plugin.video.thechains/settings.xml')
twisted = xmls + translatePath('plugin.video.twisted/settings.xml')
md = xmls + translatePath('plugin.video.magicdragon/settings.xml')
asgard = xmls + translatePath('plugin.video.asgard/settings.xml')
patriot = xmls + translatePath('plugin.video.patriot/settings.xml')
blackl = xmls + translatePath('plugin.video.blacklightning/settings.xml')
metv = xmls + translatePath('plugin.video.metv19/settings.xml')
aliunde = xmls + translatePath('plugin.video.aliundek19/settings.xml')
home = xmls + translatePath('plugin.video.homelander/settings.xml')
lab = xmls + translatePath('plugin.video.thelab/settings.xml')
quick = xmls + translatePath('plugin.video.quicksilver/settings.xml')
genocide = xmls + translatePath('plugin.video.chainsgenocide/settings.xml')
absol = xmls + translatePath('plugin.video.absolution/settings.xml')
shazam = xmls + translatePath('plugin.video.shazam/settings.xml')
crew = xmls + translatePath('plugin.video.thecrew/settings.xml')
night = xmls + translatePath('plugin.video.nightwing/settings.xml')
alvin = xmls + translatePath('plugin.video.alvin/settings.xml')
moria = xmls + translatePath('plugin.video.moria/settings.xml')
nine = xmls + translatePath('plugin.video.nine/settings.xml')
scrubs = xmls + translatePath('plugin.video.scrubsv2/settings.xml')
labjr = xmls + translatePath('plugin.video.thelabjr/settings.xml')
otaku = xmls + translatePath('plugin.video.otaku/settings.xml')
realx = xmls + translatePath('plugin.video.realizerx/settings.xml')
realx_json = xmls + translatePath('plugin.video.realizerx/rdauth.json')
premx = xmls + translatePath('plugin.video.premiumizerx/settings.xml')
allaccounts = xmls + translatePath('script.module.allaccounts/settings.xml')
myaccounts = xmls + translatePath('script.module.myaccounts/settings.xml')
rurl = xmls + translatePath('script.module.resolveurl/settings.xml')
tmdbh = xmls + translatePath('plugin.video.themoviedb.helper/settings.xml')
trakt = xmls + translatePath('script.trakt/settings.xml')
embuary = xmls + translatePath('script.embuary.info/settings.xml')
meta = xmls + translatePath('script.module.metahandler/settings.xml')
pvr = xmls + translatePath('script.module.pvr.artwork/settings.xml')

#Add-on Paths
chk_seren = addons + translatePath('plugin.video.seren/')
chk_fen = addons + translatePath('plugin.video.fen/')
chk_fenlt = addons + translatePath('plugin.video.fenlight/')
chk_affen = addons + translatePath('plugin.video.affenity/')
chk_ezra = addons + translatePath('plugin.video.ezra/')
chk_coal = addons + translatePath('plugin.video.coalition/')
chk_pov = addons + translatePath('plugin.video.pov/')
chk_umb = addons + translatePath('plugin.video.umbrella/')
chk_dradis = addons + translatePath('plugin.video.dradis/')
chk_taz = addons + translatePath('plugin.video.taz19/')
chk_shadow = addons + translatePath('plugin.video.shadow/')
chk_ghost = addons + translatePath('plugin.video.ghost/')
chk_base = addons + translatePath('plugin.video.base/')
chk_unleashed = addons + translatePath('plugin.video.unleashed/')
chk_chains = addons + translatePath('plugin.video.thechains/')
chk_twisted = addons + translatePath('plugin.video.twisted/')
chk_md = addons + translatePath('plugin.video.magicdragon/')
chk_asgard = addons + translatePath('plugin.video.asgard/')
chk_patriot = addons + translatePath('plugin.video.patriot/')
chk_blackl = addons + translatePath('plugin.video.blacklightning/')
chk_metv = addons + translatePath('plugin.video.metv19/')
chk_aliunde = addons + translatePath('plugin.video.aliundek19/')
chk_home = addons + translatePath('plugin.video.homelander/')
chk_lab = addons + translatePath('plugin.video.thelab/')
chk_quick = addons + translatePath('plugin.video.quicksilver/')
chk_genocide = addons + translatePath('plugin.video.chainsgenocide/')
chk_absol = addons + translatePath('plugin.video.absolution/')
chk_shazam = addons + translatePath('plugin.video.shazam/')
chk_crew = addons + translatePath('plugin.video.thecrew/')
chk_night = addons + translatePath('plugin.video.nightwing/')
chk_alvin = addons + translatePath('plugin.video.alvin/')
chk_moria = addons + translatePath('plugin.video.moria/')
chk_nine = addons + translatePath('plugin.video.nine/')
chk_scrubs = addons + translatePath('plugin.video.scrubsv2/')
chk_labjr = addons + translatePath('plugin.video.thelabjr/')
chk_otaku = addons + translatePath('plugin.video.otaku/')
chk_realx = addons + translatePath('plugin.video.realizerx/')
chk_premx = addons + translatePath('plugin.video.premiumizerx/')
chk_allaccounts = addons + translatePath('script.module.allaccounts/')
chk_myaccounts = addons + translatePath('script.module.myaccounts/')
chk_rurl= addons + translatePath('script.module.resolveurl/')
chk_tmdbh = addons + translatePath('plugin.video.themoviedb.helper/')
chk_trakt = addons + translatePath('script.trakt/')
chk_embuary = addons + translatePath('script.embuary.info/')
chk_meta = addons + translatePath('script.module.metahandler/')
chk_pvr = addons + translatePath('script.module.pvr.artwork/')

#Add-on Userdata Paths
seren_ud = addon_data + translatePath('plugin.video.seren/')
fen_ud = addon_data + translatePath('plugin.video.fen/')
ezra_ud = addon_data + translatePath('plugin.video.ezra/')
coal_ud = addon_data + translatePath('plugin.video.coalition/')
pov_ud = addon_data + translatePath('plugin.video.pov/')
umb_ud = addon_data + translatePath('plugin.video.umbrella/')
dradis_ud = addon_data + translatePath('plugin.video.dradis/')
taz_ud = addon_data + translatePath('plugin.video.taz19/')
shadow_ud = addon_data + translatePath('plugin.video.shadow/')
ghost_ud = addon_data + translatePath('plugin.video.ghost/')
base_ud = addon_data + translatePath('plugin.video.base/')
unleashed_ud = addon_data + translatePath('plugin.video.unleashed/')
chains_ud = addon_data + translatePath('plugin.video.thechains/')
twisted_ud = addon_data + translatePath('plugin.video.twisted/')
md_ud = addon_data + translatePath('plugin.video.magicdragon/')
asgard_ud = addon_data + translatePath('plugin.video.asgard/')
patriot_ud = addon_data + translatePath('plugin.video.patriot/')
blackl_ud = addon_data + translatePath('plugin.video.blacklightning/')
metv_ud = addon_data + translatePath('plugin.video.metv19/')
aliunde_ud = addon_data + translatePath('plugin.video.aliundek19/')
home_ud = addon_data + translatePath('plugin.video.homelander/')
lab_ud = addon_data + translatePath('plugin.video.thelab/')
quick_ud = addon_data + translatePath('plugin.video.quicksilver/')
genocide_ud = addon_data + translatePath('plugin.video.chainsgenocide/')
absol_ud = addon_data + translatePath('plugin.video.absolution/')
shazam_ud = addon_data + translatePath('plugin.video.shazam/')
crew_ud = addon_data + translatePath('plugin.video.thecrew/')
night_ud = addon_data + translatePath('plugin.video.nightwing/')
alvin_ud = addon_data + translatePath('plugin.video.alvin/')
moria_ud = addon_data + translatePath('plugin.video.moria/')
nine_ud = addon_data + translatePath('plugin.video.nine/')
scrubs_ud = addon_data + translatePath('plugin.video.scrubsv2/')
labjr_ud = addon_data + translatePath('plugin.video.thelabjr/')
otaku_ud = addon_data + translatePath('plugin.video.otaku/')
realx_ud = addon_data + translatePath('plugin.video.realizerx/')
premx_ud = addon_data + translatePath('plugin.video.premiumizerx/')
allaccounts_ud = addon_data + translatePath('script.module.allaccounts/')
myaccounts_ud = addon_data + translatePath('script.module.myaccounts/')
rurl_ud = addon_data + translatePath('script.module.resolveurl/')
tmdbh_ud = addon_data + translatePath('plugin.video.themoviedb.helper/')
trakt_ud = addon_data + translatePath('script.trakt/')
embuary_ud = addon_data + translatePath('script.embuary.info/')
meta_ud = addon_data + translatePath('script.module.metahandler/')
pvr_ud = addon_data + translatePath('script.module.pvr.artwork/')

#Add-on settings.xml Paths
chkset_seren = addon_data + translatePath('plugin.video.seren/settings.xml')
chkset_fen = addon_data + translatePath('plugin.video.fen/settings.xml')
chkset_fenlt = addon_data + translatePath('plugin.video.fenlight/databases/settings.db')
chkset_affen = addon_data + translatePath('plugin.video.affenity/databases/settings.db')
chkset_ezra = addon_data + translatePath('plugin.video.ezra/settings.xml')
chkset_coal = addon_data + translatePath('plugin.video.coalition/settings.xml')
chkset_pov = addon_data + translatePath('plugin.video.pov/settings.xml')
chkset_umb = addon_data + translatePath('plugin.video.umbrella/settings.xml')
chkset_dradis = addon_data + translatePath('plugin.video.dradis/settings.xml')
chkset_taz = addon_data + translatePath('plugin.video.taz19/settings.xml')
chkset_shadow = addon_data + translatePath('plugin.video.shadow/settings.xml')
chkset_ghost = addon_data + translatePath('plugin.video.ghost/settings.xml')
chkset_base = addon_data + translatePath('plugin.video.base/settings.xml')
chkset_unleashed = addon_data + translatePath('plugin.video.unleashed/settings.xml')
chkset_chains = addon_data + translatePath('plugin.video.thechains/settings.xml')
chkset_twisted = addon_data + translatePath('plugin.video.twisted/settings.xml')
chkset_md = addon_data + translatePath('plugin.video.magicdragon/settings.xml')
chkset_asgard = addon_data + translatePath('plugin.video.asgard/settings.xml')
chkset_patriot = addon_data + translatePath('plugin.video.patriot/settings.xml')
chkset_blackl = addon_data + translatePath('plugin.video.blacklightning/settings.xml')
chkset_metv = addon_data + translatePath('plugin.video.metv19/settings.xml')
chkset_aliunde = addon_data + translatePath('plugin.video.aliundek19/settings.xml')
chkset_home = addon_data + translatePath('plugin.video.homelander/settings.xml')
chkset_lab = addon_data + translatePath('plugin.video.thelab/settings.xml')
chkset_quick = addon_data + translatePath('plugin.video.quicksilver/settings.xml')
chkset_genocide = addon_data + translatePath('plugin.video.chainsgenocide/settings.xml')
chkset_absol = addon_data + translatePath('plugin.video.absolution/settings.xml')
chkset_shazam = addon_data + translatePath('plugin.video.shazam/settings.xml')
chkset_crew = addon_data + translatePath('plugin.video.thecrew/settings.xml')
chkset_night = addon_data + translatePath('plugin.video.nightwing/settings.xml')
chkset_alvin = addon_data + translatePath('plugin.video.alvin/settings.xml')
chkset_moria = addon_data + translatePath('plugin.video.moria/settings.xml')
chkset_nine = addon_data + translatePath('plugin.video.nine/settings.xml')
chkset_scrubs = addon_data + translatePath('plugin.video.scrubsv2/settings.xml')
chkset_labjr = addon_data + translatePath('plugin.video.thelabjr/settings.xml')
chkset_otaku = addon_data + translatePath('plugin.video.otaku/settings.xml')
chkset_realx = addon_data + translatePath('plugin.video.realizerx/settings.xml')
chkset_realx_json = addon_data + translatePath('plugin.video.realizerx/rdauth.json')
chkset_premx = addon_data + translatePath('plugin.video.premiumizerx/settings.xml')
chkset_allaccounts = addon_data + translatePath('script.module.allaccounts/settings.xml')
chkset_myaccounts = addon_data + translatePath('script.module.myaccounts/settings.xml')
chkset_rurl = addon_data + translatePath('script.module.resolveurl/settings.xml')
chkset_tmdbh = addon_data + translatePath('plugin.video.themoviedb.helper/settings.xml')
chkset_trakt = addon_data + translatePath('script.trakt/settings.xml')
chkset_embuary = addon_data + translatePath('script.embuary.info/settings.xml')
chkset_meta = addon_data + translatePath('script.module.metahandler/settings.xml')
chkset_pvr = addon_data + translatePath('script.module.pvr.artwork/settings.xml')

#Trakt API Key Paths
path_seren = addons + translatePath('plugin.video.seren/resources/lib/indexers/trakt.py')
path_fen = addons + translatePath('plugin.video.fen/resources/lib/apis/trakt_api.py')
path_fenlt = addons + translatePath('plugin.video.fenlight/resources/lib/apis/trakt_api.py')
path_affen = addons + translatePath('plugin.video.affenity/resources/lib/apis/trakt_api.py')
path_coal = addons + translatePath('plugin.video.coalition/resources/lib/apis/trakt_api.py')
path_pov = addons + translatePath('plugin.video.pov/resources/lib/apis/trakt_api.py')
path_dradis = addons + translatePath('plugin.video.dradis/resources/lib/modules/trakt.py')
path_taz = addons + translatePath('plugin.video.taz19/resources/lib/apis/trakt_api.py')
path_shadow = addons + translatePath('plugin.video.shadow/resources/modules/general.py')
path_ghost = addons + translatePath('plugin.video.ghost/resources/modules/general.py')
path_base = addons + translatePath('plugin.video.base/resources/modules/general.py')
path_unleashed = addons + translatePath('plugin.video.unleashed/resources/modules/general.py')
path_chains = addons + translatePath('plugin.video.thechains/resources/modules/general.py')
path_md = addons + translatePath('plugin.video.magicdragon/resources/modules/general.py')
path_asgard = addons + translatePath('plugin.video.asgard/resources/modules/general.py')
path_patriot = addons + translatePath('plugin.video.patriot/resources/modules/general.py')
path_blackl = addons + translatePath('plugin.video.blacklightning/resources/modules/general.py')
path_aliunde = addons + translatePath('plugin.video.aliundek19/resources/modules/general.py')
path_crew = addons + translatePath('script.module.thecrew/lib/resources/lib/modules/trakt.py')
path_scrubs = addons + translatePath('plugin.video.scrubsv2/resources/lib/modules/trakt.py')
path_labjr = addons + translatePath('plugin.video.thelabjr/resources/lib/modules/trakt.py')
path_allaccounts = addons + translatePath('script.module.allaccounts/lib/allaccounts/modules/trakt.py')
path_myaccounts = addons + translatePath('script.module.myaccounts/lib/myaccounts/modules/trakt.py')
path_tmdbh = addons + translatePath('plugin.video.themoviedb.helper/resources/tmdbhelper/lib/api/api_keys/trakt.py')
path_trakt = addons + translatePath('script.trakt/resources/lib/traktapi.py')

#Trakt API Keys
seren_client = '0c9a30819e4af6ffaf3b954cbeae9b54499088513863c03c02911de00ac2de79'
seren_secret = 'bf02417f27b514cee6a8d135f2ddc261a15eecfb6ed6289c36239826dcdd1842'
fen_client = '645b0f46df29d27e63c4a8d5fff158edd0bef0a6a5d32fc12c1b82388be351af'
fen_secret = '422a282ef5fe4b5c47bc60425c009ac3047ebd10a7f6af790303875419f18f98'
fenlt_client = '1038ef327e86e7f6d39d80d2eb5479bff66dd8394e813c5e0e387af0f84d89fb'
fenlt_secret = '8d27a92e1d17334dae4a0590083a4f26401cb8f721f477a79fd3f218f8534fd1'
affen_client = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'
affen_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
coal_client = '19849909a0f8c9dc632bc5f5c7ccafd19f3e452e2e44fee05b83fd5dc1e77675'
coal_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
pov_client = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'
pov_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
dradis_client = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'
dradis_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'
taz_client = '4f2f0e3cf53e5c3b9ed1e2a203ebff1cd9c91205772f48a9bd2e1ba560e5e1f7'
shadow_client = '8ed545c0b7f92cc26d1ecd6326995c6cf0053bd7596a98e962a472bee63274e6'
shadow_secret = '1ec4f37e5743e3086abace0c83444c25d9b655d1d77b793806b2c8205a510426'
ghost_client = 'a4e716b4b22b62e59b9e09454435c8710b650b3143dcce553d252b6a66ba60c8'
ghost_secret = 'c6d9aba72214a1ca3c6d45d0351e59f21bbe43df9bbac7c5b740089379f8c5cd'
base_client = '76578d23add0005f9b723fd66f97f1eb0e226f3fac55a3127baaa78e6ed5b303'
base_secret = '7110290e5ecf935c1a3ffb3e6410e34cef5d732ef59dbdb141cef2846c8bd227'
unleashed_client = '19849909a0f8c9dc632bc5f5c7ccafd19f3e452e2e44fee05b83fd5dc1e77675'
unleashed_secret = '122b7a79437dcf4b657d3af9e92f2d9ff8939ade532e03bc81bfb5ce798b04b'
chains_client = '19849909a0f8c9dc632bc5f5c7ccafd19f3e452e2e44fee05b83fd5dc1e77675'
chains_secret = '122b7a79437dcf4b657d3af9e92f2d9ff8939ade532e03bc81bfb5ce798b04b'
md_client = '8ed545c0b7f92cc26d1ecd6326995c6cf0053bd7596a98e962a472bee63274e6'
md_secret = '1ec4f37e5743e3086abace0c83444c25d9b655d1d77b793806b2c8205a510426'
asgard_client = '54de56f7b90a4cf7227fd70ecf703c6c043ec135c56ad10c9bb90c539bf2749f'
asgard_secret = 'a43aa6bd62eb5afd37ede4a625457fc903f1961b8384178986bf76eebfcd5999'
patriot_client = '5085635871955f48506576375bf736293c4833d491beca8d962c9da45125b63c'
patriot_secret = '2400cb3da2a3cc1f74b53c43793de8f97e6ea867a5639c8f0b0bde606c067e41'
blackl_client = 'cddec5a35d5d39a8b1e189d8f012dc5046880b8f1bbd67fc2e3b14de1b374b5b'
blackl_secret = '1b4b51a3595d03155813a057a566f32c4c37f2a77bd7888c207d85f31687b57f'
aliunde_client = '4d6fbe175e32115ca9117c3b7c55bf46b53f69f90c232d79869ec32f0dd470a6'
aliunde_secret = '6c27014354629b345dbe4b4028ff5956489ee5cb7e7e5857454bcd24430c91ac'
crew_client = '482f9db52ee2611099ce3aa1abf9b0f7ed893c6d3c6b5face95164eac7b01f71'
crew_secret = '80a2729728b53ba1cc38137b22f21f34d590edd35454466c4b8920956513d967'
scrubs_client = '63c53edc299b7a05cc6ea2272e8a84e13aade067c18a794362ab9a4a84eafb16'
scrubs_secret = '9163ebda9d33acd06c74d017e861404b7212ee34675e09e73365d7536b84eab6'
labjr_client = 'c0f8e1164003c7117d60713756a1812250e13f64d194d432057246e6867adf8f'
labjr_secret = 'cf70a427f74b8ed7349717405e723f021be6d67aa709207ad7242c4d1740830c'
allacts_client = '4f2f0e3cf53e5c3b9ed1e2a203ebff1cd9c91205772f48a9bd2e1ba560e5e1f7'
allacts_secret = '2667c9c1ea787ea15029412f3cdaaec7606f78b187de181f45f2f0db8208e37a'
myacts_client = 'e3a8d1c673dfecb7f669b23ecbf77c75fcfd24d3e8c3dbc7f79ed995262fa1db'
myacts_secret = '73bee6aeee29cb75db4d8771458a440017f7cfe842e85f457ed9d81f7910b349'
tmdbh_client = 'e6fde6173adf3c6af8fd1b0694b9b84d7c519cefc24482310e1de06c6abe5467'
tmdbh_secret = '15119384341d9a61c751d8d515acbc0dd801001d4ebe85d3eef9885df80ee4d9'
trakt_client = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'
trakt_secret = 'b5fcd7cb5d9bb963784d11bbf8535bc0d25d46225016191eb48e50792d2155c0'

#Metadata API Keys
ezra_fan = 'fe073550acf157bdb8a4217f215c0882'
ezra_tmdb = '05a454b451f2f9003fbca293744e4a85'
fen_fan = 'fa836e1c874ba95ab08a14ee88e05565'
fen_tmdb = 'b370b60447737762ca38457bd77579b3'
coal_fan = '598515b970d81280063107d49d0e2558"'
coal_tmdb = '74f3ce931d65ebda1f77ef24eac2625f'
pov_fan = 'fe073550acf157bdb8a4217f215c0882'
pov_tmdb = 'a07324c669cac4d96789197134ce272b'
taz_fan = 'fe073550acf157bdb8a4217f215c0882'
taz_tmdb = '05a454b451f2f9003fbca293744e4a85'
home_fan = 'c3469c1cc9465b9f1a1a862feea8b76b'
home_tmdb = 'fb981e5ab89415bba616409d5eb5f05e'
crew_fan = '27bef29779bbffe947232dc310a91f0c'
crew_tmdb = '0049795edb57568b95240bc9e61a9dfc'
