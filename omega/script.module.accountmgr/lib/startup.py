import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import os.path
import time
import sqlite3
import _strptime

from libs.common import var
from accountmgr.modules import control
from accountmgr.modules import log_utils

var.rm_traktcache()
accountmgr = xbmcaddon.Addon("script.module.accountmgr")

LOGINFO = 1

timeout_start = time.time()
timeout = 60*5
                                
def startup_sync():
        try:
                if str(var.chk_accountmgr_tk) != '': #Skip sync if Trakt is not authorized
                        from accountmgr.modules import trakt_sync
                        trakt_sync.Auth().trakt_auth() #Sync Trakt
        except:
                xbmc.log('%s: Startup Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        try:
                if str(var.chk_accountmgr_tk_rd) != '': #Skip sync if Real-Debrid is not authorized
                        from accountmgr.modules import debrid_rd
                        debrid_rd.Auth().realdebrid_auth() #Sync Real-Debrid
        except:
                xbmc.log('%s: Startup Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        try:
                if str(var.chk_accountmgr_tk_pm) != '': #Skip sync if Premiumize is not authorized
                        from accountmgr.modules import debrid_pm
                        debrid_pm.Auth().premiumize_auth() #Sync Premiumize
        except:
                xbmc.log('%s: Startup Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        try:
                if str(var.chk_accountmgr_tk_ad) != '': #Skip sync if All-Debrid is not authorized
                        from accountmgr.modules import debrid_ad 
                        debrid_ad.Auth().alldebrid_auth() #Sync All-Debrid
        except:
                xbmc.log('%s: Startup Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass

def startup_nondebrid_sync():
        try:    #Skip sync if no data is available to sync
                if str(var.chk_accountmgr_furk) != '':
                        from accountmgr.modules import furk_sync
                        furk_sync.Auth().furk_auth() #Sync Data
        except:
                xbmc.log('%s: Startup Non-Debrid Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        
        try:    #Skip sync if no data is available to sync
                if str(var.chk_accountmgr_easy) != '':
                        from accountmgr.modules import easy_sync
                        easy_sync.Auth().easy_auth() #Sync Data
        except:
                xbmc.log('%s: Startup Non-Debrid Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        
        try:    #Skip sync if no data is available to sync
                if str(var.chk_accountmgr_file) != '':
                        from accountmgr.modules import filepursuit_sync
                        filepursuit_sync.Auth().file_auth() #Sync Data
        except:
                xbmc.log('%s: Startup Non-Debrid Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        
def startup_meta_sync():
        try:    #Skip sync if no Metadata is available to sync
                if str(var.chk_accountmgr_fanart) != '' or str(var.chk_accountmgr_omdb) != '' or str(var.chk_accountmgr_mdb) != '' or str(var.chk_accountmgr_imdb) != '' or str(var.chk_accountmgr_tmdb) != '' or str(var.chk_accountmgr_tmdb_user) != '' or str(var.chk_accountmgr_tvdb) != '':
                        from accountmgr.modules import meta_sync
                        meta_sync.Auth().meta_auth() #Sync Metadata
        except:
                xbmc.log('%s: Startup Meta Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        
def dradis_sync():
        try:
                xbmc.executebuiltin('RunPlugin(plugin://plugin.video.dradis/?action=tools_forceTraktSync)') #Start Trakt Sync
                accountmgr.setSetting("dradis_traktsync", 'false')
        except:
                xbmc.log('%s: Startup Dradis Sync Failed!' % var.amgr, xbmc.LOGINFO)
                pass
                
class AddonCheckUpdate:
        def run(self):
            xbmc.log('[ script.module.accountmgr ]  Addon checking available updates', LOGINFO)
            try:
                import re
                import requests
                repo_xml = requests.get('https://raw.githubusercontent.com/Zaxxon709/nexus/main/zips/script.module.accountmgr/addon.xml')
                if repo_xml.status_code != 200:
                    return xbmc.log('[ script.module.accountmgr ]  Could not connect to remote repo XML: status code = %s' % repo_xml.status_code, LOGINFO)
                repo_version = re.search(r'<addon id=\"script.module.accountmgr\".*version=\"(\d*.\d*.\d*)\"', repo_xml.text, re.I).group(1)
                local_version = control.addonVersion()[:5] # 5 char max so pre-releases do try to compare more chars than github version
                def check_version_numbers(current, new): # Compares version numbers and return True if github version is newer
                    current = current.split('.')
                    new = new.split('.')
                    step = 0
                    for i in current:
                        if int(new[step]) > int(i): return True
                        if int(i) > int(new[step]): return False
                        if int(i) == int(new[step]):
                            step += 1
                            continue
                    return False
                if check_version_numbers(local_version, repo_version):
                    while control.condVisibility('Library.IsScanningVideo'):
                        control.sleep(10000)
                    xbmc.log('[ script.module.accountmgr ]  A newer version is available. Installed Version: v%s' % (local_version), LOGINFO)
                    control.notification(message=control.lang(32072) % repo_version, time=5000)
                return xbmc.log('[ script.module.accountmgr ]  Addon update check complete', LOGINFO)
            except:
                import traceback
                traceback.print_exc()
                
def api_check():
        while True:
                if time.time() > timeout_start + timeout: #Time out after 5min
                        break

                if xbmcvfs.exists(var.chk_seren) and xbmcvfs.exists(var.chkset_seren) and str(var.chk_accountmgr_tk) != '' and var.setting('traktuserkey.enabled') == 'true': #Check that the addon is installed, settings.xml exists and Account Manager is authorized
                        try:
                                with open(var.path_seren) as f: #Check add-on for Account Manager API keys. If found, move on to next add-on
                                        if var.chk_api in f.read():
                                                pass
                                        else:   #Insert Account Mananger API keys into add-on
                                                with open(var.path_seren,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.seren_client,var.client_am).replace(var.seren_secret,var.secret_am)

                                                with open(var.path_seren,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Seren API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                                                
                                
                if xbmcvfs.exists(var.chk_fen) and xbmcvfs.exists(var.chkset_fen) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_fen) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:   
                                                with open(var.path_fen,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.fen_client,var.client_am).replace(var.fen_secret,var.secret_am)

                                                with open(var.path_fen,'w') as f:
                                                    f.write(client) 
                                                continue
                        except:
                                xbmc.log('%s: Fen API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_fenlt) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:   
                                                with open(var.path_fenlt,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.fenlt_client,var.client_am).replace(var.fenlt_secret,var.secret_am)

                                                with open(var.path_fenlt,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Fen Light API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass

                if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_affen) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:   
                                                with open(var.path_affen,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.affen_client,var.client_am).replace(var.affen_secret,var.secret_am)

                                                with open(var.path_affen,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: afFENity API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_coal) and xbmcvfs.exists(var.chkset_coal) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_coal) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:   
                                                with open(var.path_coal,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.coal_client,var.client_am).replace(var.coal_secret,var.secret_am)

                                                with open(var.path_coal,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Coalition API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_pov) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_pov,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.pov_client,var.client_am).replace(var.pov_secret,var.secret_am)

                                                with open(var.path_pov,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: POV API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_dradis) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_dradis,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.dradis_client,var.client_am).replace(var.dradis_secret,var.secret_am)

                                                with open(var.path_dradis,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Dradis API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_taz) and xbmcvfs.exists(var.chkset_taz) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_taz) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_taz,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.taz_client,var.client_am)

                                                with open(var.path_taz,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Taz API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_shadow) and xbmcvfs.exists(var.chkset_shadow) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_shadow) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_shadow,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.shadow_client,var.client_am).replace(var.shadow_secret,var.secret_am)

                                                with open(var.path_shadow,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Shadow API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_ghost) and xbmcvfs.exists(var.chkset_ghost) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_ghost) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_ghost,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.ghost_client,var.client_am).replace(var.ghost_secret,var.secret_am)

                                                with open(var.path_ghost,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Ghost API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_base) and xbmcvfs.exists(var.chkset_base) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_base) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_base,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.base_client,var.client_am).replace(var.base_secret,var.secret_am)

                                                with open(var.path_base,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Base API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_unleashed) and xbmcvfs.exists(var.chkset_unleashed) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_unleashed) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_unleashed,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.unleashed_client,var.client_am).replace(var.unleashed_secret,var.secret_am)

                                                with open(var.path_unleashed,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Unleashed API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_chains) and xbmcvfs.exists(var.chkset_chains) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_chains) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_chains,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.chains_client,var.client_am).replace(var.chains_secret,var.secret_am)

                                                with open(var.path_chains,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Chain Reaction API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_md) and xbmcvfs.exists(var.chkset_md) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_md) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_md,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.md_client,var.client_am).replace(var.md_secret,var.secret_am)

                                                with open(var.path_md,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Magic Dragon API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_asgard) and xbmcvfs.exists(var.chkset_asgard) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_asgard) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_asgard,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.asgard_client,var.client_am).replace(var.asgard_secret,var.secret_am)

                                                with open(var.path_asgard,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Asgard API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_patriot) and xbmcvfs.exists(var.chkset_patriot) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_patriot) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_patriot,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.patriot_client,var.client_am).replace(var.patriot_secret,var.secret_am)

                                                with open(var.path_patriot,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Patriot API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_blackl) and xbmcvfs.exists(var.chkset_blackl) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_blackl) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_blackl,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.blackl_client,var.client_am).replace(var.blackl_secret,var.secret_am)

                                                with open(var.path_blackl,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Black Lightning API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_aliunde) and xbmcvfs.exists(var.chkset_aliunde) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_aliunde) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_aliunde,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.aliunde_client,var.client_am).replace(var.aliunde_secret,var.secret_am)

                                                with open(var.path_aliunde,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Aliunde API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_crew) and xbmcvfs.exists(var.chkset_crew) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_crew) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_crew,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.crew_client,var.client_am).replace(var.crew_secret,var.secret_am)

                                                with open(var.path_crew,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: The Crew API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_scrubs) and xbmcvfs.exists(var.chkset_scrubs) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_scrubs) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_scrubs,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.scrubs_client,var.client_am).replace(var.scrubs_secret,var.secret_am)

                                                with open(var.path_scrubs,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Scrubs V2 API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_labjr) and xbmcvfs.exists(var.chkset_labjr) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_labjr) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_labjr,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.labjr_client,var.client_am).replace(var.labjr_secret,var.secret_am)

                                                with open(var.path_labjr,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: TheLabjr API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass

                if xbmcvfs.exists(var.chk_tmdbh) and xbmcvfs.exists(var.chkset_tmdbh) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_tmdbh) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_tmdbh,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.tmdbh_client,var.client_am).replace(var.tmdbh_secret,var.secret_am)

                                                with open(var.path_tmdbh,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: TMDbH API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_trakt) and xbmcvfs.exists(var.chkset_trakt) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_trakt) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_trakt,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.trakt_client,var.client_am).replace(var.trakt_secret,var.secret_am)

                                                with open(var.path_trakt,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: Trakt Addon API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_allaccounts) and xbmcvfs.exists(var.chkset_allaccounts) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_allaccounts) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_allaccounts,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.allacts_client,var.client_am).replace(var.allacts_secret,var.secret_am)

                                                with open(var.path_allaccounts,'w') as f:
                                                    f.write(client)
                                                continue
                        except:
                                xbmc.log('%s: All Accounts API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass
                        
                if xbmcvfs.exists(var.chk_myaccounts) and xbmcvfs.exists(var.chkset_myaccounts) and str(var.chk_accountmgr_tk) != '':
                        try:
                                with open(var.path_myaccounts) as f:
                                        if var.chk_api in f.read():
                                                pass
                                        else:
                                                with open(var.path_myaccounts,'r') as f:
                                                    data = f.read()

                                                client = data.replace(var.myacts_client,var.client_am).replace(var.myacts_secret,var.secret_am)

                                                with open(var.path_myaccounts,'w') as f:
                                                    f.write(client)
                                                xbmc.log('%s: Startup Sync Failed!' % var.amgr, xbmc.LOGINFO)
                        except:
                                xbmc.log('%s: My Accounts API Failed!' % var.amgr, xbmc.LOGINFO)
                                pass

                xbmc.sleep(10000) #Pause for 10 seconds

if var.setting('sync.service')=='true': #Check if service is enabled
        startup_sync() #Start service
else:
        pass

if var.setting('sync.nondebrid.service')=='true': #Check if service is enabled
        startup_nondebrid_sync() #Start service
else:
        pass

if var.setting('sync.metaservice')=='true': #Check if service is enabled
        startup_meta_sync() #Start service
else:
        pass

if var.setting('checkAddonUpdates')=='true': #Check if service is enabled
	AddonCheckUpdate().run() #Start service
else:
        pass

if var.setting('dradis_traktsync')=='true': #Check if Trakt Sync is enabled
        dradis_sync()
else:
        pass

if var.setting('trakt.service')=='true': #Check if service is enabled
        api_check() #Start service
else:
        quit()
