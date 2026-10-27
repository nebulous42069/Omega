import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import os
import os.path
import sys
from datetime import datetime
try:  # Python 3
    from urllib.parse import parse_qsl
except ImportError:  # Python 2
    from urlparse import parse_qsl
from libs.common import logging
from libs.common import tools
from libs.common import var
from libs.gui import menu


def _close_kodi_or_later():
    # The change is already made; closing Kodi only makes the add-ons read it. Back or the X
    # means "not yet" (the user's rule, 2026-10-04): this used to be an OK box that closed Kodi
    # whichever way it was dismissed.
    if xbmcgui.Dialog().yesno('ReAuthorize', 'Close Kodi now to finish?[CR][CR]The change is saved. '
                              'Add-ons pick it up the next time Kodi starts.',
                              nolabel='Not yet', yeslabel='Close Kodi'):
        os._exit(1)
    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')


import re as _re

# The Crew 3.x reads its Trakt key from keys.py, so ReAuthorize (1.3.8) swaps the whole
# CLIENT_ID / CLIENT_SECRET lines and leaves what they said in a comment. Put that back.
_CREW_MARKED = _re.compile(r'^(CLIENT_ID|CLIENT_SECRET)(\s*=\s*).*?# ReAuthorize; was: (.+?)\s*$', _re.M)

def _crew_restore(data):
    return _CREW_MARKED.sub(lambda m: m.group(1) + m.group(2) + m.group(3), data)


# The Trakt add-on 3.9.0 keeps its key as a list of numbers; ReAuthorize (1.3.8) swaps those
# two lines the same way. Put back what they said.
_TRAKTADDON_MARKED = _re.compile(r'^([ \t]*__client_(?:id|secret)[^=\r\n]*=[ \t]*)\[[^\]\r\n]*\][ \t]*# ReAuthorize; was: '
                                 r'(\[[^\]\r\n]*\])[ \t]*$', _re.M)

def _traktaddon_restore(data):
    return _TRAKTADDON_MARKED.sub(lambda m: m.group(1) + m.group(2), data)


def _tmdbmovies_config():
    # TMDb Movies 1.1.308 moved config.py from resources/lib/ to resources/lib/core/.
    # Both places are looked at, the same way the Trakt sync does.
    path = var.path_tmdbmovies
    return path if os.path.isfile(path) else os.path.join(os.path.dirname(path), 'core', 'config.py')

accountmgr = xbmcaddon.Addon("script.module.reauthorize")
addon = xbmcaddon.Addon
addonObject = addon('script.module.reauthorize-core')
addonInfo = addonObject.getAddonInfo
getLangString = xbmcaddon.Addon('script.module.reauthorize-core').getLocalizedString
condVisibility = xbmc.getCondVisibility
execute = xbmc.executebuiltin
monitor = xbmc.Monitor()
joinPath = os.path.join
dialog = xbmcgui.Dialog()
date_time = datetime.now()
date = date_time.strftime('Date: %Y-%m-%d  Time: %H:%M')

amgr_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'accountmgr.png')
rd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'realdebrid.png')
pm_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'premiumize.png')
ad_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'alldebrid.png')
trakt_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'trakt.png')
torbox_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'torbox.png')
easyd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'easydebrid.png')
offcloud_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'offcloud.png')
easy_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'easynews.png')
file_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.reauthorize-core').getAddonInfo('path'), 'resources', 'icons'), 'filepursuit.png')
                      
class Router:
    def __init__(self):
        self.route = None
        self.params = {}

    def _log_params(self, paramstring):
        _url = sys.argv[0]

        self.params = dict(parse_qsl(paramstring))

        logstring = '{0}: '.format(_url)
        for param in self.params:
            logstring += '[ {0}: {1} ] '.format(param, self.params[param])

        logging.log(logstring, level=xbmc.LOGDEBUG)

        return self.params

    def dispatch(self, handle, paramstring):
        self._log_params(paramstring)

        mode = self.params['mode'] if 'mode' in self.params else None
        url = self.params['url'] if 'url' in self.params else None
        name = self.params['name'] if 'name' in self.params else None
        action = self.params['action'] if 'action' in self.params else None
        
        from libs import traktit, debridit_rd, debridit_pm, debridit_ad, tbit, edit, offit, easyit, fileit, extit, metait_all, databit, jsonit
        
        # MAIN MENU - opened from Video add-ons, where core is listed and people look first.
        # Core on its own does nothing useful, so send them to ReAuthorize itself: open it, or
        # offer to install it from the repository (people kept installing only core, 2026-10-02).
        if mode is None:
            if xbmc.getCondVisibility('System.HasAddon(script.module.reauthorize)'):
                xbmc.executebuiltin('RunScript(script.module.reauthorize)')
            elif xbmcgui.Dialog().yesno('ReAuthorize',
                                        'Install ReAuthorize now?[CR][CR]This is only its helper. '
                                        'ReAuthorize itself is what you open and sign in with.'):
                xbmc.executebuiltin('InstallAddon(script.module.reauthorize)')
            self._finish(handle)
                 
        elif mode == 'trakt':  # Trakt Account Viewer
            menu.trakt_menu()
            self._finish(handle)
            
        elif mode == 'realdebrid':  # Real-Debrid Account Viewer
            menu.debrid_menu()
            self._finish(handle)

        elif mode == 'premiumize':  # Premiumize Account Viewer
            menu.premiumize_menu()
            self._finish(handle)

        elif mode == 'alldebrid':  # All-Debird Account Viewer
            menu.alldebrid_menu()
            self._finish(handle)

        elif mode == 'torbox':  # TorBox Account Viewer
            menu.torbox_menu()
            self._finish(handle)

        elif mode == 'easydebrid':  # Easy Debrid Account Viewer
            menu.easydebrid_menu()
            self._finish(handle)
            
        elif mode == 'offcloud':  # OffCloud Account Viewer
            menu.offcloud_menu()
            self._finish(handle)

        elif mode == 'easynews':  # Easynews Account Viewer
            menu.easynews_menu()
            self._finish(handle)
            
        elif mode == 'filepursuit':  # Filepursuit Account Viewer
            menu.filepursuit_menu()
            self._finish(handle)

        elif mode == 'extproviders':  # External Providers Account Viewer
            menu.ext_menu()
            self._finish(handle)

        elif mode == 'metadata':  # Metadata Account Viewer
            menu.meta_accounts_menu()
            self._finish(handle)

        elif mode == 'allaccts':  # All Account Viewer
            menu.all_accounts_menu()
            self._finish(handle)

        # OPEN ADDON SETTINGS
        elif mode == 'opensettings_tk':  # Trakt
            from libs import traktit
            traktit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')
            
        elif mode == 'opensettings_rd':  # Real Debrid
            from libs import debridit_rd
            debridit_rd.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_pm':  # Premiumize
            from libs import debridit_pm
            debridit_pm.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_ad':  # All-Debrid
            from libs import debridit_ad
            debridit_ad.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_all':  # Debrid All
            from libs import debridit_all
            debridit_all.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_tb':  # TorBox
            from libs import tbit
            tbit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_ed':  # Easy Debrid
            from libs import edit
            edit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_oc':  # OffCloud
            from libs import offit
            offit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_en':  # Easynews
            from libs import easyit
            easyit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_fp':  # Filepursuit
            from libs import fileit
            fileit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_md':  # Metadata
            from libs import metait_all
            metait_all.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_ext':  # External Providers
            from libs import extit
            extit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        # TRAKT MANAGER
        elif mode == 'savetrakt':  # Save Trakt Data
            traktit.trakt_it('update', name)
        elif mode == 'savetrakt_acctmgr':  # Save Trakt Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('trakt.token') != '':
                    traktit.trakt_it('update', name)
                    var.backup_synclist()
                    accountmgr.setSetting('tk_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'Trakt Backup Complete!', trakt_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Trakt Data to Backup!', trakt_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoretrakt':  # Recover All Saved Trakt Data
            try:
                if xbmcvfs.exists(var.trakt_backup): # Skip restore if no trakt folder present in backup folder
                    path = os.listdir(var.trakt_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        var.restore_synclist()
                        traktit.trakt_it_restore('restore', name)
                        accountmgr.setSetting("trakt.synclist", 'true')
                        accountmgr.setSetting("sync.tk.service", "true")
                        if xbmcvfs.exists(var.chk_genocide):
                            # Every installed add-on is a Trakt target now; there is no list file to look in.
                            accountmgr.setSetting("genocide_traktsync", 'true')
                        else:
                            pass
                        accountmgr.setSetting("api.service", "true") #Enable API Check Service
                        xbmcgui.Dialog().notification('ReAuthorize', 'Trakt Data Restored!', trakt_icon, 3000)
                        xbmc.sleep(3000)
                        _close_kodi_or_later()
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Trakt Data to Restore!', trakt_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Trakt Data to Restore!', trakt_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addontrakt':  # Clear All Addon Trakt Data
            #Revoke Account Manager/Custom API keys for all add-ons
            if accountmgr.getSetting('trakt.token') != '':
                pass
            else:
                accountmgr.setSetting("api.service", "false") #Disable API Check Service
            if xbmcvfs.exists(var.chk_seren): #Check if add-on is installed
                try:
                    with open(var.path_seren,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.seren_client).replace(var.secret_am,var.seren_secret)

                    with open(var.path_seren,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Seren Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_coal):
                try:
                    with open(var.path_coal,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.coal_client).replace(var.secret_am,var.coal_secret)

                    with open(var.path_coal,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Coalition Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_pov):
                try:
                    addon = xbmcaddon.Addon("plugin.video.pov")
                    addon.setSetting("trakt.client_id", var.pov_client)
                    addon.setSetting("trakt.client_secret", var.pov_secret)
                except:
                    xbmc.log('%s: Traktit.py Revoke API POV Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_shadow):
                try:
                    with open(var.path_shadow,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.shadow_client).replace(var.secret_am,var.shadow_secret)

                    with open(var.path_shadow,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Shadow Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_ghost):
                try:
                    with open(var.path_ghost,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.ghost_client).replace(var.secret_am,var.ghost_secret)

                    with open(var.path_ghost,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Ghost Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_blueballs):
                try:
                    with open(var.path_blueballs,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.blueballs_client).replace(var.secret_am,var.blueballs_secret)

                    with open(var.path_blueballs,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Blue Balls Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_twisted):
                try:
                    with open(var.path_twisted,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.twisted_client).replace(var.secret_am,var.twisted_secret)

                    with open(var.path_twisted,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Twisted Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_base):
                try:
                    with open(var.path_base,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.base_client).replace(var.secret_am,var.base_secret)

                    with open(var.path_base,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Base Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_chains):
                try:
                    with open(var.path_chains,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.chains_client).replace(var.secret_am,var.chains_secret)

                    with open(var.path_chains,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Chain Reaction Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_asgard):
                try:
                    with open(var.path_asgard,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.asgard_client).replace(var.secret_am,var.asgard_secret)

                    with open(var.path_asgard,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Asgard Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_patriot):
                try:
                    with open(var.path_patriot,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.patriot_client).replace(var.secret_am,var.patriot_secret)

                    with open(var.path_patriot,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Patriot Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_blackl):
                try:
                    with open(var.path_blackl,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.blackl_client).replace(var.secret_am,var.blackl_secret)

                    with open(var.path_blackl,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Black Lightning Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_tmdbmovies):
                try:
                    with open(_tmdbmovies_config(),'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.tmdbmovies_client).replace(var.secret_am,var.tmdbmovies_secret)

                    with open(_tmdbmovies_config(),'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API TMDb Movies Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_aliunde):
                try:
                    with open(var.path_aliunde,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.aliunde_client).replace(var.secret_am,var.aliunde_secret)

                    with open(var.path_aliunde,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Aliunde Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_gratisred):
                try:
                    with open(var.path_gratisred,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.gratisred_client).replace(var.secret_am,var.gratisred_secret)

                    with open(var.path_gratisred,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API GratisRed Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_genocide):
                try:
                    with open(var.path_genocide,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.genocide_client).replace(var.secret_am,var.genocide_secret)

                    with open(var.path_genocide,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Chains Genocide Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_newgenocide):
                try:
                    with open(var.path_newgenocide,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.genocide_client).replace(var.secret_am,var.genocide_secret)

                    with open(var.path_newgenocide,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Genocide Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_crew):
                try:
                    with open(var.path_crew,'r') as f:
                        data = f.read()

                    client = _crew_restore(data).replace(var.client_am,var.crew_client).replace(var.secret_am,var.crew_secret)

                    with open(var.path_crew,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API The Crew Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_scrubs):
                try:
                    with open(var.path_scrubs,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.scrubs_client).replace(var.secret_am,var.scrubs_secret)

                    with open(var.path_scrubs,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Scrubs V2 Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_tmdbh):
                try:
                    with open(var.path_tmdbh,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.tmdbh_client).replace(var.secret_am,var.tmdbh_secret)

                    with open(var.path_tmdbh,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API TMDbH Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_trakt):
                try:
                    with open(var.path_trakt,'r') as f:
                        data = f.read()

                    client = _traktaddon_restore(data).replace(var.client_am,var.trakt_client).replace(var.secret_am,var.trakt_secret)

                    with open(var.path_trakt,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API Trakt Addon Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_allaccounts):
                try:
                    with open(var.path_allaccounts,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.allacts_client).replace(var.secret_am,var.allacts_secret)

                    with open(var.path_allaccounts,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API All Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass

            if xbmcvfs.exists(var.chk_myaccounts):
                try:
                    with open(var.path_myaccounts,'r') as f:
                        data = f.read()

                    client = data.replace(var.client_am,var.myacts_client).replace(var.secret_am,var.myacts_secret)

                    with open(var.path_myaccounts,'w') as f:
                        f.write(client)
                except:
                    xbmc.log('%s: Traktit.py Revoke API My Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
                
            traktit.trakt_it_revoke('clearaddon', name)
            var.delete_synclist()
            accountmgr.setSetting("trakt.synclist", 'false')
            accountmgr.setSetting("sync.tk.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', trakt_icon, 3000)
            xbmc.sleep(3000)
            _close_kodi_or_later()
        elif mode == 'cleartrakt':  # Clear All Saved Trakt Data
            try:
                if xbmcvfs.exists(var.trakt_backup): # Skip clearing data if no Trakt folder present in backup folder
                    path = os.listdir(var.trakt_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('tk_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.trakt_backup)
                        for file in data:
                                files = os.path.join(var.trakt_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Trakt Data Cleared!', trakt_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Trakt Data to Clear!', trakt_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Trakt Data to Clear!', trakt_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'opentraktsettings':  # Authorize Trakt
            traktit.open_settings_trakt(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatetrakt':  # Update Saved Trakt Data
            traktit.auto_update('all')
            
        # DEBRID MANAGER RD
        elif mode == 'savedebrid_rd':  # Save Debrid Data
            debridit_rd.debrid_it('update', name)
            jsonit.realizer_bk()
        elif mode == 'savedebrid_acctmgr_rd':  # Save Debrid Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('realdebrid.token') != '':
                    debridit_rd.debrid_it('update', name)
                    jsonit.realizer_bk()
                    accountmgr.setSetting('rd_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'RealDebrid Backup Complete!', rd_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No RealDebrid Data to Backup!', rd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoredebrid_rd':  # Recover All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.rd_backup): # Skip restore if no debrid folder present in backup folder
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        debridit_rd.debrid_it('restore', name)
                        accountmgr.setSetting("sync.rd.service", "true")
                        jsonit.realizer_rst()
                        xbmcgui.Dialog().notification('ReAuthorize', 'Real-Debrid Data Restored!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data to Restore!', rd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data to Restore!', rd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore RD Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addondebrid_rd':  # Clear All Addon Debrid Data
            debridit_rd.debrid_it('wipeaddon', name)
            accountmgr.setSetting("sync.rd.service", "false")
            jsonit.realizer_rvk()
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', rd_icon, 3000)           
        elif mode == 'cleardebrid_rd':  # Clear All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.rd_backup): # Skip clearing data if no debrid folder present in backup folder
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('rd_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.rd_backup)
                        for file in data:
                                files = os.path.join(var.rd_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Real-Debrid Data Cleared!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear RD Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'opendebridsettings_rd':  # Authorize Debrid
            debridit_rd.open_settings_debrid(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatedebrid_rd':  # Update Saved Debrid Data
            debridit_rd.auto_update('all')

        # DEBRID MANAGER PM
        elif mode == 'savedebrid_pm':  # Save Debrid Data
            debridit_pm.debrid_it('update', name)
        elif mode == 'savedebrid_acctmgr_pm':  # Save Debrid Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('premiumize.token') != '':
                    debridit_pm.debrid_it('update', name)
                    accountmgr.setSetting('pm_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'Premiumize Backup Complete!', pm_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Backup!', pm_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoredebrid_pm':  # Recover All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.pm_backup): # Skip restore if no debrid folder present in backup folder
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        debridit_pm.debrid_it('restore', name)
                        accountmgr.setSetting("sync.pm.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'Premiumize Data Restored!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Restore!', pm_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Restore!', pm_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore PM Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addondebrid_pm':  # Clear All Addon Debrid Data
            debridit_pm.debrid_it('wipeaddon', name)
            accountmgr.setSetting("sync.pm.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', pm_icon, 3000)
        elif mode == 'cleardebrid_pm':  # Clear All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.pm_backup): # Skip clearing data if no debrid folder present in backup folder
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('pm_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.pm_backup)
                        for file in data:
                                files = os.path.join(var.pm_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Premiumize Data Cleared!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Clear!', pm_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Clear!', pm_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear PM Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'opendebridsettings_pm':  # Authorize Debrid
            debridit_pm.open_settings_debrid(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatedebrid_pm':  # Update Saved Debrid Data
            debridit_pm.auto_update('all')

        # DEBRID MANAGER AD
        elif mode == 'savedebrid_ad':  # Save Debrid Data
            debridit_ad.debrid_it('update', name)
        elif mode == 'savedebrid_acctmgr_ad':  # Save Debrid Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('alldebrid.token') != '':
                    debridit_ad.debrid_it('update', name)
                    accountmgr.setSetting('ad_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'AllDebrid Backup Complete!', ad_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No AllDebrid Data to Backup!', ad_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoredebrid_ad':  # Recover All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.ad_backup): # Skip restore if no debrid folder present in backup folder
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        debridit_ad.debrid_it('restore', name)
                        accountmgr.setSetting("sync.ad.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'All-Debrid Data Restored!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data to Restore!', ad_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data to Restore!', ad_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore AD Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addondebrid_ad':  # Clear All Addon Debrid Data
            debridit_ad.debrid_it('wipeaddon', name)
            accountmgr.setSetting("sync.ad.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', ad_icon, 3000)
        elif mode == 'cleardebrid_ad':  # Clear All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.ad_backup): # Skip clearing data if no debrid folder present in backup folder
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('ad_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.ad_backup)
                        for file in data:
                                files = os.path.join(var.ad_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'All-Debrid Data Cleared!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear AD Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'opendebridsettings_ad':  # Authorize Debrid
            debridit_ad.open_settings_debrid(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatedebrid_ad':  # Update Saved Debrid Data
            debridit_ad.auto_update('all')

        # TORBOX MANAGER
        elif mode == 'savetorbox':  # Save Data
            tbit.tb_it('update', name)
        elif mode == 'save_tb_acctmgr':  # Save Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('torbox.token') != '':
                    tbit.tb_it('update', name)
                    accountmgr.setSetting('tb_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'TorBox Backup Complete!', torbox_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No TorBox Data to Backup!', torbox_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoretb':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.tb_backup): # Skip restore if no TorBox folder present in backup folder
                    path = os.listdir(var.tb_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        tbit.tb_it('restore', name)
                        accountmgr.setSetting("sync.torbox.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'TorBox Data Restored!', torbox_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No TorBox Data to Restore!', torbox_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No TorBox Data to Restore!', torbox_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addontb':  # Clear All Addon OffCloud Data
            tbit.tb_it('wipeaddon', name)
            accountmgr.setSetting("sync.torbox.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', torbox_icon, 3000)
        elif mode == 'cleartb':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.tb_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.tb_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('tb_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.tb_backup)
                        for file in data:
                                files = os.path.join(var.tb_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'TorBox Data Cleared!', torbox_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No TorBox Data to Clear!', torbox_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No TorBox Data to Clear!', torbox_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updatetb':  # Update Saved Data
            tbit.auto_update('all')

        # EASY DEBRID MANAGER
        elif mode == 'saveeasydebrid':  # Save Data
            edit.ed_it('update', name)
        elif mode == 'save_ed_acctmgr':  # Save Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('easydebrid.token') != '':
                    edit.ed_it('update', name)
                    accountmgr.setSetting('ed_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'Easy Debrid Backup Complete!', easyd_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Easy Debrid  Data to Backup!', easyd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoreed':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.ed_backup): # Skip restore if no Easy Debrid folder present in backup folder
                    path = os.listdir(var.ed_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        edit.ed_it('restore', name)
                        accountmgr.setSetting("sync.easyd.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'Easy Debrid  Data Restored!', easyd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Easy Debrid  Data to Restore!', easyd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Easy Debrid  Data to Restore!', easyd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addoned':  # Clear All Addon OffCloud Data
            edit.ed_it('wipeaddon', name)
            accountmgr.setSetting("sync.eastd.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', easyd_icon, 3000)
        elif mode == 'cleared':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.ed_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.ed_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('ed_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.ed_backup)
                        for file in data:
                                files = os.path.join(var.ed_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Easy Debrid  Data Cleared!', easyd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Easy Debrid Data to Clear!', easyd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Easy Debrid Data to Clear!', easyd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateed':  # Update Saved Data
            edit.auto_update('all')
            
        # OFFCLOUD MANAGER
        elif mode == 'saveoffcloud':  # Save Data
            offit.offc_it('update', name)
        elif mode == 'save_offc_acctmgr':  # Save Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('offcloud.token') != '':
                    offit.offc_it('update', name)
                    accountmgr.setSetting('oc_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'OffCloud Backup Complete!', offcloud_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No OffCloud Data to Backup!', offcloud_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoreoffc':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.offc_backup): # Skip restore if no offcloud folder present in backup folder
                    path = os.listdir(var.offc_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        offit.offc_it('restore', name)
                        accountmgr.setSetting("sync.offc.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'OffCloud Data Restored!', offcloud_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No OffCloud Data to Restore!', offcloud_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No OffCloud Data to Restore!', offcloud_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addonoffc':  # Clear All Addon OffCloud Data
            offit.offc_it('wipeaddon', name)
            accountmgr.setSetting("sync.offc.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', offcloud_icon, 3000)
        elif mode == 'clearoffc':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.offc_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.offc_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('oc_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.offc_backup)
                        for file in data:
                                files = os.path.join(var.offc_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'OffCloud Data Cleared!', offcloud_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No OffCloud Data to Clear!', offcloud_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No OffCloud Data to Clear!', offcloud_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateoffc':  # Update Saved Data
            offit.auto_update('all')
            
        # EASYNEWS MANAGER
        elif mode == 'saveeasy':  # Save Data
            easyit.easy_it('update', name)
        elif mode == 'save_easy_acctmgr':  # Save Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('easynews.password') != '':
                    easyit.easy_it('update', name)
                    accountmgr.setSetting('en_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'Easynews Backup Complete!', easy_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Easynews Data to Backup!', easy_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoreeasy':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.easy_backup): # Skip restore if no easynews folder present in backup folder
                    path = os.listdir(var.easy_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        easyit.easy_it('restore', name)
                        accountmgr.setSetting("sync.easy.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'Easynews Data Restored!', easy_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Easynews Data to Restore!', easy_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Easynews  Data to Restore!', easy_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addoneasy':  # Clear All Addon Easynews Data
            easyit.easy_it('wipeaddon', name)
            accountmgr.setSetting("sync.easy.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', easy_icon, 3000)
        elif mode == 'cleareasy':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.easy_backup): # Skip clearing data if no easynews folder present in backup folder
                    path = os.listdir(var.easy_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('en_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.easy_backup)
                        for file in data:
                                files = os.path.join(var.easy_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Easynews Data Cleared!', easy_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Easynews Data to Clear!', easy_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Easynews Data to Clear!', easy_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear Easynews Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateeasy':  # Update Saved Data
            easyit.auto_update('all')

        # FILEPURSUIT MANAGER
        elif mode == 'savefile':  # Save Data
            fileit.filep_it('update', name)
        elif mode == 'save_file_acctmgr':  # Save Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('filepursuit.api.key') != '':
                    fileit.filep_it('update', name)
                    accountmgr.setSetting('fp_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'Filepursuit Backup Complete!', file_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Filepursuit Data to Backup!', file_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restorefile':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.file_backup): # Skip restore if no fileloud folder present in backup folder
                    path = os.listdir(var.file_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        fileit.filep_it('restore', name)
                        accountmgr.setSetting("sync.filep.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'Filepursuit Data Restored!', file_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Filepursuit Data to Restore!', file_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Filepursuit Data to Restore!', file_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore Filepursuit Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addonfile':  # Clear All Addon Filepursuit Data
            fileit.filep_it('wipeaddon', name)
            accountmgr.setSetting("sync.filep.service", "false")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', file_icon, 3000)
        elif mode == 'clearfile':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.file_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.file_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('fp_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.file_backup)
                        for file in data:
                                files = os.path.join(var.file_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Filepursuit Data Cleared!', file_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Filepursuit Data to Clear!', file_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Filepursuit Data to Clear!', file_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear Filepursuit Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updatefile':  # Update Saved Data
            fileit.auto_update('all')

        #EXTERNAL PROVIDERS MANAGER
        elif mode == 'saveext':  # Save Data
            extit.ext_it('update', name)
        elif mode == 'save_ext_acctmgr':  # Save Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('sync.ext.service') == 'true':
                    extit.ext_it('update', name)
                    accountmgr.setSetting('ext_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'External Providers Backup Complete!', amgr_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No External Providers Data to Backup!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoreext':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.ext_backup): # Skip restore if no extprovider folder present in backup folder
                    path = os.listdir(var.ext_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        extit.ext_it('restore', name)
                        accountmgr.setSetting("sync.ext.service", "true")
                        accountmgr.setSetting("ext.provider", 'CocoScrapers')
                        xbmcgui.Dialog().notification('ReAuthorize', 'External Providers Data Restored!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No External Providers Data to Restore!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No External Providers  Data to Restore!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.lLose(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore External Providers Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addonext':  # Clear All Addon External Providers Data
            extit.ext_it('wipeaddon', name)
            accountmgr.setSetting("sync.ext.service", "false")
            accountmgr.setSetting("ext.provider", '')
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', amgr_icon, 3000)
        elif mode == 'clearext':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.ext_backup): # Skip clearing data if no extprovider folder present in backup folder
                    path = os.listdir(var.ext_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('ext_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.ext_backup)
                        for file in data:
                                files = os.path.join(var.ext_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'External Providers Data Cleared!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No External Providers Data to Clear!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No External Providers Data to Clear!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear External Providers Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateext':  # Update Saved Data
            extit.auto_update('all')
            
        #META DATA MANAGER
        elif mode == 'savemeta':  # Save Meta Data
            metait_all.debrid_it('update', name)
        elif mode == 'savemeta_acctmgr':  # Save Meta Data via Account Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('ReAuthorize', 'No backup path set! Please set a backup path in Account Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.reauthorize)")
            else:
                if accountmgr.getSetting('fanart.tv.api.key') != '' or accountmgr.getSetting('omdb.api.key') != '' or accountmgr.getSetting('mdb.api.key') != '' or accountmgr.getSetting('imdb.user') != '' or accountmgr.getSetting('tmdb.api.key') != '' or accountmgr.getSetting('tmdb.username') != '' or accountmgr.getSetting('tvdb.api.key') != '':
                    metait_all.debrid_it('update', name)
                    accountmgr.setSetting('md_backup_date', date)
                    xbmcgui.Dialog().notification('ReAuthorize', 'Metadata Backup Complete!', amgr_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Metadata to Backup!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
        elif mode == 'restoremeta':  # Recover All Saved Meta Data
            try:
                if xbmcvfs.exists(var.meta_backup): # Skip restore if no meta folder present in backup folder
                    path = os.listdir(var.meta_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        metait_all.debrid_it('restore', name)
                        accountmgr.setSetting("sync.meta.service", "true")
                        xbmcgui.Dialog().notification('ReAuthorize', 'Metadata Restored!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        _close_kodi_or_later()
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Metadata to Restore!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Metadata to Restore!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Restore Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addonmeta':  # Clear All Addon Meta Data
            metait_all.debrid_it('wipeaddon', name)
            accountmgr.setSetting("sync.meta.service", "false")
            xbmc.executebuiltin("Skin.Reset(mdblist_api_key)")
            xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', amgr_icon, 3000)
            xbmc.sleep(3000)
            _close_kodi_or_later()
        elif mode == 'clearmeta':  # Clear All Saved Meta Data
            try:
                if xbmcvfs.exists(var.meta_backup): # Skip clearing data if no meta folder present in backup folder
                    path = os.listdir(var.meta_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        accountmgr.setSetting('md_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.meta_backup)
                        for file in data:
                                files = os.path.join(var.meta_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('ReAuthorize', 'Metadata Cleared!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Metadata to Clear!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                else:
                    xbmcgui.Dialog().notification('ReAuthorize', 'No Metadata to Clear!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
            except:
                xbmc.log('%s: Router.py Clear Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updatemeta':  # Update Saved Meta Data
            metait_all.auto_update('all')
            
        #REVOKE ALL DEBRID ACCOUNTS
        elif mode == 'revokeall':  # Clear Addon Data for all Debrid services
            if accountmgr.getSetting('realdebrid.token') == '' and accountmgr.getSetting('premiumize.token') == '' and accountmgr.getSetting('alldebrid.token') == '': # If no accounts are authorized notify user
                xbmcgui.Dialog().notification('ReAuthorize', 'No Active Debrid Accounts!', amgr_icon, 3000) # If Accounts authorized notify user
            else:
                if accountmgr.getSetting('realdebrid.token') != '':
                    debridit_rd.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.rd.service", "false")
                    jsonit.realizer_rvk()

                if accountmgr.getSetting('premiumize.token') != '':
                    debridit_pm.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.pm.service", "false")

                if accountmgr.getSetting('alldebrid.token') != '':
                    debridit_ad.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.ad.service", "false")
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database     
                xbmcgui.Dialog().notification('ReAuthorize', 'All Add-ons Revoked!', amgr_icon, 3000)
                
        #BACKUP ALL DEBRID ACCOUNTS
        elif mode == 'backupall':  # Save Debrid Data for all Debrid services
            if accountmgr.getSetting('realdebrid.token') == '' and accountmgr.getSetting('premiumize.token') == '' and accountmgr.getSetting('alldebrid.token') != '': # If no accounts are authorized notify user
                xbmcgui.Dialog().notification('ReAuthorize', 'No Active Debrid Accounts!', amgr_icon, 3000)
            else:
                if accountmgr.getSetting('realdebrid.token') != '': # Skip backup if Debrid account not authorized
                    #Real-Debrid
                    debridit_rd.debrid_it('update', name)
                    jsonit.realizer_bk()
                    accountmgr.setSetting('rd_backup_date', date)
                    
                if accountmgr.getSetting('premiumize.token') != '':
                    #Premiumize
                    debridit_pm.debrid_it('update', name)
                    accountmgr.setSetting('pm_backup_date', date)

                if accountmgr.getSetting('alldebrid.token') != '':
                    #All-Debrid
                    debridit_ad.debrid_it('update', name)
                    accountmgr.setSetting('ad_backup_date', date)
                        
                xbmcgui.Dialog().notification('ReAuthorize', 'Backup Complete!', amgr_icon, 3000)
            
        #RESTORE ALL DEBRID ACCOUNTS
        elif mode == 'restoreall':  # Recover All Saved Debrid Data for all Accounts
            if xbmcvfs.exists(var.rd_backup) or xbmcvfs.exists(var.pm_backup) or xbmcvfs.exists(var.ad_backup): # Skip restore if no debrid folder present in backup folder
                try:
                    if xbmcvfs.exists(var.rd_backup): # Skip restore if no backup folder exists or it's empty
                        path_rd = os.listdir(var.rd_backup)
                        if len(path_rd) != 0: # Skip if backup directory is empty
                            debridit_rd.debrid_it('restore', name)
                            accountmgr.setSetting("sync.rd.service", "true")
                            jsonit.realizer_rst()
                            xbmcgui.Dialog().notification('ReAuthorize', 'Real-Debrid Data Restored!', rd_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data Found!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data Found!', rd_icon, 3000)
                    if xbmcvfs.exists(var.pm_backup): # Skip restore if no backup folder exists or it's empty
                        path_pm = os.listdir(var.pm_backup)
                        if len(path_pm) != 0: # Skip if backup directory is empty
                            debridit_pm.debrid_it('restore', name)
                            accountmgr.setSetting("sync.pm.service", "true")
                            xbmcgui.Dialog().notification('ReAuthorize', 'Premiumize Data Restored!', pm_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data Found!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data Found!', pm_icon, 3000)
                    if xbmcvfs.exists(var.ad_backup): # Skip restore if no backup folder exists or it's empty
                        path_ad = os.listdir(var.ad_backup)
                        if len(path_ad) != 0: # Skip if backup directory is empty
                            debridit_ad.debrid_it('restore', name)
                            accountmgr.setSetting("sync.ad.service", "true")
                            xbmcgui.Dialog().notification('ReAuthorize', 'All-Debrid Data Restored!', ad_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data Found!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data Found!', ad_icon, 3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.sleep(1000)
                    var.remake_settings() #Refresh settings database
                except:
                    xbmc.log('%s: Router.py Restore All Debrid Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('ReAuthorize', 'Restore Failed! No Saved Data Found!', amgr_icon, 3000)
                xbmc.sleep(3000)
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                 
        #CLEAR ALL SAVED DATA FOR DEBRID ACCOUNTS
        elif mode == 'clearall':  # Clear All Saved Debrid Data
            if xbmcvfs.exists(var.rd_backup) or xbmcvfs.exists(var.pm_backup) or xbmcvfs.exists(var.ad_backup): # Skip clearing data if no debrid folder present in backup folder
                try:
                    #Clear Real-Debrid Saved Data
                    if xbmcvfs.exists(var.rd_backup): # Skip clearing data if no folder present in backup folder
                        path = os.listdir(var.rd_backup)
                        if len(path) != 0: # Skip clearing data if no saved data in backup folder
                            data = os.listdir(var.rd_backup)
                            for file in data:
                                    files = os.path.join(var.rd_backup, file)
                                    if os.path.isfile(files):
                                            os.remove(files) 
                            xbmcgui.Dialog().notification('ReAuthorize', 'Real-Debrid Data Cleared!', rd_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    
                    #Clear Premiumize Saved Data
                    if xbmcvfs.exists(var.pm_backup): # Skip clearing data if no folder present in backup folder
                        path = os.listdir(var.pm_backup)
                        if len(path) != 0: # Skip clearing data if no saved data in backup folder
                            data = os.listdir(var.pm_backup)
                            for file in data:
                                    files = os.path.join(var.pm_backup, file)
                                    if os.path.isfile(files):
                                            os.remove(files)
                            xbmcgui.Dialog().notification('ReAuthorize', 'Premiumize Data Cleared!', pm_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Clear!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No Premiumize Data to Clear!', pm_icon, 3000)
                        
                    #Clear All-Debrid Saved Data
                    if xbmcvfs.exists(var.ad_backup): # Skip clearing data if no folder present in backup folder
                        path = os.listdir(var.ad_backup)
                        if len(path) != 0: # Skip clearing data if no saved data in backup folder
                            data = os.listdir(var.ad_backup)
                            for file in data:
                                    files = os.path.join(var.ad_backup, file)
                                    if os.path.isfile(files):
                                            os.remove(files)
                            xbmcgui.Dialog().notification('ReAuthorize', 'All-Debrid Data Cleared!', ad_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('ReAuthorize', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear All Debrid Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('ReAuthorize', 'No Data to Clear!', amgr_icon, 3000)
                xbmc.sleep(3000)
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin('Addon.OpenSettings(script.module.reauthorize)')
                 
        # REVOKE/WIPE/CLEAN ALL ADD-ONS
        elif mode == 'wipeclean':  # Revoke all Add-ons, Clear all saved data, and restore stock API Keys for all add-ons
            xbmcgui.Dialog().notification('ReAuthorize', 'Restoring default settings, please wait!', amgr_icon, 3000)
            try:
                #Revoke Trakt
                if accountmgr.getSetting('trakt.token') != '':
                    #Revoke Account Manager/Custom API keys for all add-ons
                    if xbmcvfs.exists(var.chk_seren): #Check if add-on is installed
                        try:
                            with open(var.path_seren,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.seren_client).replace(var.secret_am,var.seren_secret)

                            with open(var.path_seren,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Seren Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_coal):
                        try:
                            with open(var.path_coal,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.coal_client).replace(var.secret_am,var.coal_secret)

                            with open(var.path_coal,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Coalition Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_pov):
                        try:
                            addon = xbmcaddon.Addon("plugin.video.pov")
                            addon.setSetting("trakt.client_id", var.pov_client)
                            addon.setSetting("trakt.client_secret", var.pov_secret)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API POV Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_shadow):
                        try:
                            with open(var.path_shadow,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.shadow_client).replace(var.secret_am,var.shadow_secret)

                            with open(var.path_shadow,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Shadow Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_ghost):
                        try:
                            with open(var.path_ghost,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.ghost_client).replace(var.secret_am,var.ghost_secret)

                            with open(var.path_ghost,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Ghost Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_blueballs):
                        try:
                            with open(var.path_blueballs,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.blueballs_client).replace(var.secret_am,var.blueballs_secret)

                            with open(var.path_blueballs,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Blue Balls Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_twisted):
                        try:
                            with open(var.path_twisted,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.twisted_client).replace(var.secret_am,var.twisted_secret)

                            with open(var.path_twisted,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Twisted Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_base):
                        try:
                            with open(var.path_base,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.base_client).replace(var.secret_am,var.base_secret)

                            with open(var.path_base,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Base Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_chains):
                        try:
                            with open(var.path_chains,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.chains_client).replace(var.secret_am,var.chains_secret)

                            with open(var.path_chains,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Chain Reaction Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_asgard):
                        try:
                            with open(var.path_asgard,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.asgard_client).replace(var.secret_am,var.asgard_secret)

                            with open(var.path_asgard,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Asgard Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_patriot):
                        try:
                            with open(var.path_patriot,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.patriot_client).replace(var.secret_am,var.patriot_secret)

                            with open(var.path_patriot,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Patriot Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_blackl):
                        try:
                            with open(var.path_blackl,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.blackl_client).replace(var.secret_am,var.blackl_secret)

                            with open(var.path_blackl,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Black Lightning Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_tmdbmovies):
                        try:
                            with open(_tmdbmovies_config(),'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.tmdbmovies_client).replace(var.secret_am,var.tmdbmovies_secret)

                            with open(_tmdbmovies_config(),'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API TMDb Movies Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_newgenocide):
                        try:
                            with open(var.path_newgenocide,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.genocide_client).replace(var.secret_am,var.genocide_secret)

                            with open(var.path_newgenocide,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Genocide Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_aliunde):
                        try:
                            with open(var.path_aliunde,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.aliunde_client).replace(var.secret_am,var.aliunde_secret)

                            with open(var.path_aliunde,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Aliunde Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_gratisred):
                        try:
                            with open(var.path_gratisred,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.gratisred_client).replace(var.secret_am,var.gratisred_secret)

                            with open(var.path_gratisred,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API GratisRed Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_crew):
                        try:
                            with open(var.path_crew,'r') as f:
                                data = f.read()

                            client = _crew_restore(data).replace(var.client_am,var.crew_client).replace(var.secret_am,var.crew_secret)

                            with open(var.path_crew,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API The Crew Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_scrubs):
                        try:
                            with open(var.path_scrubs,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.scrubs_client).replace(var.secret_am,var.scrubs_secret)

                            with open(var.path_scrubs,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Scrubs V2 Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_tmdbh):
                        try:
                            with open(var.path_tmdbh,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.tmdbh_client).replace(var.secret_am,var.tmdbh_secret)

                            with open(var.path_tmdbh,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API TMDbH Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_trakt):
                        try:
                            with open(var.path_trakt,'r') as f:
                                data = f.read()

                            client = _traktaddon_restore(data).replace(var.client_am,var.trakt_client).replace(var.secret_am,var.trakt_secret)

                            with open(var.path_trakt,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API Trakt Addon Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_allaccounts):
                        try:
                            with open(var.path_allaccounts,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.allacts_client).replace(var.secret_am,var.allacts_secret)

                            with open(var.path_allaccounts,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API All Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                            pass

                    if xbmcvfs.exists(var.chk_myaccounts):
                        try:
                            with open(var.path_myaccounts,'r') as f:
                                data = f.read()

                            client = data.replace(var.client_am,var.myacts_client).replace(var.secret_am,var.myacts_secret)

                            with open(var.path_myaccounts,'w') as f:
                                f.write(client)
                        except:
                            xbmc.log('%s: Traktit.py Revoke API My Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                            pass
                        
                    traktit.trakt_it_revoke('wipeaddon', name)
                    accountmgr.setSetting("sync.tk.service", "false")
                    
                #Revoke Real-Debrid
                if accountmgr.getSetting('realdebrid.token') != '':
                    debridit_rd.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.rd.service", "false")
                    jsonit.realizer_rvk()

                #Revoke Premiumize
                if accountmgr.getSetting('premiumize.token') != '':
                    debridit_pm.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.pm.service", "false")

                #Revoke All-Debrid
                if accountmgr.getSetting('alldebrid.token') != '':
                    debridit_ad.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.ad.service", "false")

                #Revoke TorBox
                if not str(var.setting('torbox.token')) == '':
                    tbit.tb_it('wipeaddon', name)
                    accountmgr.setSetting("sync.torbox.service", "false")
                    accountmgr.setSetting("torbox.enabled", 'false')

                #Revoke Easy Debrid
                if not str(var.setting('easydebrid.token')) == '':
                    edit.ed_it('wipeaddon', name)
                    accountmgr.setSetting("sync.easyd.service", "false")
                    accountmgr.setSetting("easydebrid.enabled", 'false')
                    
                #Revoke OffCloud
                if not str(var.setting('offcloud.token')) == '':
                    offit.offc_it('wipeaddon', name)
                    accountmgr.setSetting("sync.offc.service", "false")
                    accountmgr.setSetting("offcloud.enabled", 'false')
                    
                #Revoke Easynews
                if not str(var.setting('easynews.password')) == '':
                    easyit.easy_it('wipeaddon', name)
                    accountmgr.setSetting("sync.easy.service", "false")
                    accountmgr.setSetting("easynews.enabled", 'false')

                #Revoke Filepursuit
                if not str(var.setting('filepursuit.api.key')) == '':
                    fileit.filep_it('wipeaddon', name)
                    accountmgr.setSetting("sync.filep.service", "false")
                    accountmgr.setSetting("filepursuit.enabled", 'false')

                #Revoke External Providers
                if not str(var.setting('ext.provider')) == '':
                    extit.ext_it('wipeaddon', name)
                    accountmgr.setSetting("sync.ext.service", "false")
                    accountmgr.setSetting("ext.provider", '')

                #Revoke Metadata
                if str(var.setting('fanart.tv.api.key')) != '' or str(var.setting('omdb.api.key')) != '' or str(var.setting('mdb.api.key')) != '' or str(var.setting('imdb.user')) != '' or str(var.setting('tvdb.api.key')) != '' or str(var.setting('tmdb.api.key')) != '' or str(var.setting('tmdb.username')) != '' or str(var.setting('tmdb.password')) != '' or str(var.setting('tmdb.session_id')) != '':
                    metait_all.debrid_it('wipeaddon', name)
                    accountmgr.setSetting("sync.meta.service", "false")
                    xbmc.executebuiltin("Skin.Reset(mdblist_api_key)")
                    accountmgr.setSetting("meta.enabled", 'false')
                    
                
                #Clear Trakt Saved Data
                if xbmcvfs.exists(var.trakt_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.trakt_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.trakt_backup)
                        for file in data:
                                files = os.path.join(var.trakt_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                
                #Clear Real-Debrid Saved Data
                if xbmcvfs.exists(var.rd_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.rd_backup)
                        for file in data:
                                files = os.path.join(var.rd_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        
                #Clear Premiumize Saved Data
                if xbmcvfs.exists(var.pm_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.pm_backup)
                        for file in data:
                                files = os.path.join(var.pm_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                    
                #Clear All-Debrid Saved Data
                if xbmcvfs.exists(var.ad_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.ad_backup)
                        for file in data:
                                files = os.path.join(var.ad_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                                        
                #Clear TorBox Saved Data
                if xbmcvfs.exists(var.tb_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.tb_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.tb_backup)
                        for file in data:
                                files = os.path.join(var.tb_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)

                #Clear Easy Debrid Saved Data
                if xbmcvfs.exists(var.ed_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.ed_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.ed_backup)
                        for file in data:
                                files = os.path.join(var.ed_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)

                #Clear OffCloud Saved Data
                if xbmcvfs.exists(var.offc_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.offc_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.offc_backup)
                        for file in data:
                                files = os.path.join(var.offc_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)

                #Clear Easynews Saved Data
                if xbmcvfs.exists(var.easy_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.easy_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.easy_backup)
                        for file in data:
                                files = os.path.join(var.easy_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)

                #Clear Filepursuit Saved Data
                if xbmcvfs.exists(var.file_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.file_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.file_backup)
                        for file in data:
                                files = os.path.join(var.file_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)

                #Clear External Providers Saved Data
                if xbmcvfs.exists(var.ext_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.ext_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.ext_backup)
                        for file in data:
                                files = os.path.join(var.ext_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                                        
                #Clear Metadata Saved Data
                if xbmcvfs.exists(var.meta_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.meta_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.meta_backup)
                        for file in data:
                                files = os.path.join(var.meta_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
                
            except:
                xbmc.log('%s: Router.py Revoke/Wipe/Clean Account Manager Failed!' % var.amgr, xbmc.LOGINFO)
                pass

            xbmcgui.Dialog().ok('ReAuthorize', 'All settings have been restored to default.')
                    
    def _finish(self, handle):
        from libs.common import directory
        
        directory.set_view()
        
        xbmcplugin.setContent(handle, 'files')
        xbmcplugin.endOfDirectory(handle)
