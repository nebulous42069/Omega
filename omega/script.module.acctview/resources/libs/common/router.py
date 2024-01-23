import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import os.path
import os
import xbmcvfs
import sys
try:  # Python 3
    from urllib.parse import parse_qsl
except ImportError:  # Python 2
    from urlparse import parse_qsl
from resources.libs.common.config import CONFIG
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common import var
from resources.libs.gui import menu

accountmgr = xbmcaddon.Addon("script.module.accountmgr")
addon = xbmcaddon.Addon
addonObject = addon('script.module.acctview')
addonInfo = addonObject.getAddonInfo
getLangString = xbmcaddon.Addon().getLocalizedString
condVisibility = xbmc.getCondVisibility
execute = xbmc.executebuiltin
monitor = xbmc.Monitor()
joinPath = os.path.join
dialog = xbmcgui.Dialog()


amgr_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.acctview').getAddonInfo('path'), 'resources', 'icons'), 'accountmgr.png')
rd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.acctview').getAddonInfo('path'), 'resources', 'icons'), 'realdebrid.png')
pm_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.acctview').getAddonInfo('path'), 'resources', 'icons'), 'premiumize.png')
ad_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.acctview').getAddonInfo('path'), 'resources', 'icons'), 'alldebrid.png')
trakt_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.acctview').getAddonInfo('path'), 'resources', 'icons'), 'trakt.png')

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

        # MAIN MENU
        if mode is None:
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

        elif mode == 'nondebrid':  # Non-Debrid Account Viewer
            menu.nondebrid_accounts_menu()
            self._finish(handle)

        elif mode == 'metadata':  # Metadata Account Viewer
            menu.meta_accounts_menu()
            self._finish(handle)

        elif mode == 'allaccts':  # All Account Viewer
            menu.all_accounts_menu()
            self._finish(handle)
            
        # TRAKT MANAGER
        elif mode == 'savetrakt':  # Save Trakt Data
            from resources.libs import traktit
            traktit.trakt_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_trakt()
            databit.backup_affen_trakt()
        elif mode == 'savetrakt_acctmgr':  # Save Trakt Data via Account Manager settings menu
            from resources.libs import traktit
            traktit.trakt_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_trakt()
            databit.backup_affen_trakt()
            xbmcgui.Dialog().notification('Account Manager', 'Trakt Backup Complete!', trakt_icon, 3000)
        elif mode == 'restoretrakt':  # Recover All Saved Trakt Data
            if xbmcvfs.exists(var.trakt_backup): # Skip restore if no trakt folder present in backup folder
                try:
                    path = os.listdir(var.trakt_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        from resources.libs import traktit
                        traktit.trakt_it_restore('restore', name)
                        from resources.libs import databit
                        databit.restore_fenlt_trakt()
                        databit.restore_affen_trakt()
                        if xbmcvfs.exists(var.chk_dradis) and xbmcvfs.exists(var.chkset_dradis):
                            accountmgr.setSetting("dradis_traktsync", 'true')
                        xbmcgui.Dialog().notification('Account Manager', 'Trakt Data Restored!', trakt_icon, 3000)
                        xbmc.sleep(2000)
                        xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
                        os._exit(1)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Trakt Data to Restore!', trakt_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Trakt Data to Restore!', trakt_icon, 3000)
        elif mode == 'addontrakt':  # Clear All Addon Trakt Data
            from resources.libs import traktit
            traktit.trakt_it_revoke('wipeaddon', name)
            from resources.libs import databit
            databit.revoke_fenlt_trakt()
            databit.revoke_affen_trakt()
            xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', trakt_icon, 3000)
            xbmc.sleep(2000)
            xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
            os._exit(1)
        elif mode == 'cleartrakt':  # Clear All Saved Trakt Data
            if xbmcvfs.exists(var.trakt_backup): # Skip clearing data if no Trakt folder present in backup folder
                try:
                    path = os.listdir(var.trakt_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder           
                        from resources.libs import traktit
                        traktit.clear_saved(name)
                        from resources.libs import databit
                        databit.delete_fenlt_trakt()
                        databit.delete_affen_trakt()
                        xbmcgui.Dialog().notification('Account Manager', 'Trakt Data Cleared!', trakt_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Trakt Data to Clear!', trakt_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Trakt Data to Clear!', trakt_icon, 3000)
        elif mode == 'opentraktsettings':  # Authorize Trakt
            from resources.libs import traktit
            traktit.open_settings_trakt(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatetrakt':  # Update Saved Trakt Data
            from resources.libs import traktit
            traktit.auto_update('all')
            
        # DEBRID MANAGER RD
        elif mode == 'savedebrid_rd':  # Save Debrid Data
            from resources.libs import debridit_rd
            debridit_rd.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_rd()
            databit.backup_affen_rd()
            from resources.libs import jsonit
            jsonit.realizer_bk()
        elif mode == 'savedebrid_acctmgr_rd':  # Save Debrid Data via Account Manager settings menu
            from resources.libs import debridit_rd
            debridit_rd.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_rd()
            databit.backup_affen_rd()
            from resources.libs import jsonit
            jsonit.realizer_bk()
            xbmcgui.Dialog().notification('Account Manager', 'Real-Debrid Backup Complete!', rd_icon, 3000)
        elif mode == 'restoredebrid_rd':  # Recover All Saved Debrid Data
            if xbmcvfs.exists(var.rd_backup): # Skip restore if no debrid folder present in backup folder
                try:
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        from resources.libs import debridit_rd
                        debridit_rd.debrid_it('restore', name)
                        from resources.libs import databit
                        databit.restore_fenlt_rd()
                        databit.restore_affen_rd()
                        from resources.libs import jsonit
                        jsonit.realizer_rst()
                        xbmcgui.Dialog().notification('Account Manager', 'Real-Debrid Data Restored!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data to Restore!', rd_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore RD Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data to Restore!', rd_icon, 3000)           
        elif mode == 'addondebrid_rd':  # Clear All Addon Debrid Data
            from resources.libs import debridit_rd
            debridit_rd.debrid_it('wipeaddon', name)
            from resources.libs import databit
            databit.revoke_fenlt_rd()
            databit.revoke_affen_rd()
            from resources.libs import jsonit
            jsonit.realizer_rvk()
            xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', rd_icon, 3000)
        elif mode == 'cleardebrid_rd':  # Clear All Saved Debrid Data
            if xbmcvfs.exists(var.rd_backup): # Skip clearing data if no debrid folder present in backup folder
                try:
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder           
                        from resources.libs import debridit_rd
                        debridit_rd.clear_saved(name)
                        from resources.libs import databit
                        databit.delete_fenlt_rd()
                        databit.delete_affen_rd()
                        from resources.libs import jsonit
                        jsonit.realizer_rm()
                        xbmcgui.Dialog().notification('Account Manager', 'Real-Debrid Data Cleared!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear RD Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
        elif mode == 'opendebridsettings_rd':  # Authorize Debrid
            from resources.libs import debridit_rd
            debridit_rd.open_settings_debrid(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatedebrid_rd':  # Update Saved Debrid Data
            from resources.libs import debridit_rd
            debridit_rd.auto_update('all')

        # DEBRID MANAGER PM
        elif mode == 'savedebrid_pm':  # Save Debrid Data
            from resources.libs import debridit_pm
            debridit_pm.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_pm()
            databit.backup_affen_pm()
        elif mode == 'savedebrid_acctmgr_pm':  # Save Debrid Data via Account Manager settings menu
            from resources.libs import debridit_pm
            debridit_pm.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_pm()
            databit.backup_affen_pm()
            xbmcgui.Dialog().notification('Account Manager', 'Premiumize Backup Complete!', pm_icon, 3000)
        elif mode == 'restoredebrid_pm':  # Recover All Saved Debrid Data
            if xbmcvfs.exists(var.pm_backup): # Skip restore if no debrid folder present in backup folder
                try:
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        from resources.libs import debridit_pm
                        debridit_pm.debrid_it('restore', name)
                        from resources.libs import databit
                        databit.restore_fenlt_pm()
                        databit.restore_affen_pm()
                        xbmcgui.Dialog().notification('Account Manager', 'Premiumize Data Restored!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data to Restore!', pm_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore PM Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data to Restore!', pm_icon, 3000)
        elif mode == 'addondebrid_pm':  # Clear All Addon Debrid Data
            from resources.libs import debridit_pm
            debridit_pm.debrid_it('wipeaddon', name)
            from resources.libs import databit
            databit.revoke_fenlt_pm()
            databit.revoke_affen_pm()
            xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', pm_icon, 3000)
        elif mode == 'cleardebrid_pm':  # Clear All Saved Debrid Data
            if xbmcvfs.exists(var.pm_backup): # Skip clearing data if no debrid folder present in backup folder
                try:
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder           
                        from resources.libs import debridit_pm
                        debridit_pm.clear_saved(name)
                        from resources.libs import databit
                        databit.delete_fenlt_pm()
                        databit.delete_affen_pm()
                        xbmcgui.Dialog().notification('Account Manager', 'Premiumize Data Cleared!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear PM Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
        elif mode == 'opendebridsettings_pm':  # Authorize Debrid
            from resources.libs import debridit_pm
            debridit_pm.open_settings_debrid(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatedebrid_pm':  # Update Saved Debrid Data
            from resources.libs import debridit_pm
            debridit_pm.auto_update('all')

        # DEBRID MANAGER AD
        elif mode == 'savedebrid_ad':  # Save Debrid Data
            from resources.libs import debridit_ad
            debridit_ad.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_ad()
            databit.backup_affen_ad()
        elif mode == 'savedebrid_acctmgr_ad':  # Save Debrid Data via Account Manager settings menu
            from resources.libs import debridit_ad
            debridit_ad.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_ad()
            databit.backup_affen_ad()
            xbmcgui.Dialog().notification('Account Manager', 'All-Debrid Backup Complete!', ad_icon, 3000)
        elif mode == 'restoredebrid_ad':  # Recover All Saved Debrid Data
            if xbmcvfs.exists(var.ad_backup): # Skip restore if no debrid folder present in backup folder
                try:
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        from resources.libs import debridit_ad
                        debridit_ad.debrid_it('restore', name)
                        from resources.libs import databit
                        databit.restore_fenlt_ad()
                        databit.restore_affen_ad()
                        xbmcgui.Dialog().notification('Account Manager', 'All-Debrid Data Restored!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data to Restore!', ad_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore AD Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data to Restore!', ad_icon, 3000)
        elif mode == 'addondebrid_ad':  # Clear All Addon Debrid Data
            from resources.libs import debridit_ad
            debridit_ad.debrid_it('wipeaddon', name)
            from resources.libs import databit
            databit.revoke_fenlt_ad()
            databit.revoke_affen_ad()
            xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', ad_icon, 3000)
        elif mode == 'cleardebrid_ad':  # Clear All Saved Debrid Data
            if xbmcvfs.exists(var.ad_backup): # Skip clearing data if no debrid folder present in backup folder
                try:
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder           
                        from resources.libs import debridit_ad
                        debridit_ad.clear_saved(name)
                        from resources.libs import databit
                        databit.delete_fenlt_ad()
                        databit.delete_affen_ad()
                        xbmcgui.Dialog().notification('Account Manager', 'All-Debrid Data Cleared!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear AD Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
        elif mode == 'opendebridsettings_ad':  # Authorize Debrid
            from resources.libs import debridit_ad
            debridit_ad.open_settings_debrid(name)
            xbmc.executebuiltin('Container.Refresh()')
        elif mode == 'updatedebrid_ad':  # Update Saved Debrid Data
            from resources.libs import debridit_ad
            debridit_ad.auto_update('all')

        #FURK/EASYNEWS/FILEPURSUIT MANAGER
        elif mode == 'save_nondebrid':  # Save Data
            from resources.libs import non_debrid_all
            non_debrid_all.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_easy()
            databit.backup_affen_easy()
        elif mode == 'save_non_acctmgr':  # Save Data via Account Manager settings menu
            if str(var.chk_accountmgr_furk) != '' or str(var.chk_accountmgr_easy) != '' or str(var.chk_accountmgr_file) != '':
                from resources.libs import non_debrid_all
                non_debrid_all.debrid_it('update', name)
                from resources.libs import databit
                databit.backup_fenlt_easy()
                databit.backup_affen_easy()
                xbmcgui.Dialog().notification('Account Manager', 'Backup Complete!', amgr_icon, 3000)
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Data to Backup!', amgr_icon, 3000)
        elif mode == 'restore_non':  # Recover All Saved Data
            if xbmcvfs.exists(var.non_backup): # Skip restore if no nondebrid folder present in backup folder
                try:
                    path = os.listdir(var.non_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        from resources.libs import non_debrid_all
                        non_debrid_all.debrid_it('restore', name)
                        from resources.libs import databit
                        databit.restore_fenlt_easy()
                        databit.restore_affen_easy()
                        xbmcgui.Dialog().notification('Account Manager', 'Data Restored!', amgr_icon, 3000)
                        xbmc.sleep(2000)
                        xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
                        os._exit(1)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Data to Restore!', amgr_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore Non-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Data to Restore!', amgr_icon, 3000)
        elif mode == 'addon_non':  # Clear All Addon Debrid Data
            from resources.libs import non_debrid_all
            non_debrid_all.debrid_it('clearaddon', name)
            from resources.libs import databit
            databit.revoke_fenlt_easy()
            databit.revoke_affen_easy()
            xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', amgr_icon, 3000)
            xbmc.sleep(2000)
            xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
            os._exit(1)
        elif mode == 'clear_non':  # Clear All Saved Data
            if xbmcvfs.exists(var.non_backup): # Skip clearing data if no nondebrid folder present in backup folder
                try:
                    path = os.listdir(var.non_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder           
                        from resources.libs import non_debrid_all
                        non_debrid_all.clear_saved(name)
                        from resources.libs import databit
                        databit.delete_fenlt_easy()
                        databit.delete_affen_easy()
                        xbmcgui.Dialog().notification('Account Manager', 'Data Cleared!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Data to Clear!', amgr_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear Non-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Data to Clear!', amgr_icon, 3000)
        elif mode == 'update_non':  # Update Saved Data
            from resources.libs import non_debrid_all
            non_debrid_all.auto_update('all')

        #META DATA MANAGER
        elif mode == 'savemeta':  # Save Meta Data
            from resources.libs import metait_all
            metait_all.debrid_it('update', name)
            from resources.libs import databit
            databit.backup_fenlt_meta()
            databit.backup_affen_meta()
        elif mode == 'savemeta_acctmgr':  # Save Meta Data via Account Manager settings menu
            if str(var.chk_accountmgr_fanart) != '' or str(var.chk_accountmgr_omdb) != '' or str(var.chk_accountmgr_mdb) != '' or str(var.chk_accountmgr_imdb) != '' or str(var.chk_accountmgr_tmdb) != '' or str(var.chk_accountmgr_tmdb_user) != '' or str(var.chk_accountmgr_tvdb) != '':
                from resources.libs import metait_all
                metait_all.debrid_it('update', name)
                from resources.libs import databit
                databit.backup_fenlt_meta()
                databit.backup_affen_meta()
                xbmcgui.Dialog().notification('Account Manager', 'Metadata Backup Complete!', amgr_icon, 3000)
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Metadata to Backup!', amgr_icon, 3000)
        elif mode == 'restoremeta':  # Recover All Saved Meta Data
            if xbmcvfs.exists(var.meta_backup): # Skip restore if no meta folder present in backup folder
                try:
                    path = os.listdir(var.meta_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        from resources.libs import metait_all
                        metait_all.debrid_it('restore', name)
                        from resources.libs import databit
                        databit.restore_fenlt_meta()
                        databit.restore_affen_meta()
                        xbmcgui.Dialog().notification('Account Manager', 'Metadata Restored!', amgr_icon, 3000)
                        xbmc.sleep(2000)
                        xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
                        os._exit(1)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Metadata to Restore!', amgr_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Metadata to Restore!', amgr_icon, 3000)
        elif mode == 'addonmeta':  # Clear All Addon Debrid Data
            from resources.libs import metait_all
            metait_all.debrid_it('clearaddon', name)
            from resources.libs import databit
            databit.revoke_fenlt_meta()
            databit.revoke_affen_meta()
            xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', amgr_icon, 3000)
            xbmc.sleep(2000)
            xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
            os._exit(1)
        elif mode == 'clearmeta':  # Clear All Saved Meta Data
            if xbmcvfs.exists(var.meta_backup): # Skip clearing data if no meta folder present in backup folder
                try:
                    path = os.listdir(var.meta_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder           
                        from resources.libs import metait_all
                        metait_all.clear_saved(name)
                        from resources.libs import databit
                        databit.delete_fenlt_meta()
                        databit.delete_affen_meta()
                        xbmcgui.Dialog().notification('Account Manager', 'Metadata Cleared!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Metadata to Clear!', amgr_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear Metadata Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Metadata to Clear!', amgr_icon, 3000)
        elif mode == 'updatemeta':  # Update Saved Meta Data
            from resources.libs import metait_all
            metait_all.auto_update('all')
            
        #REVOKE ALL DEBRID ACCOUNTS
        elif mode == 'revokeall':  # Clear Addon Data for all Debrid services
            if str(var.chk_accountmgr_tk_rd) != '' or str(var.chk_accountmgr_tk_pm) != '' or str(var.chk_accountmgr_tk_ad) != '': #Skip revoke if no Debrid accounts authorized
                from resources.libs import debridit_rd, debridit_pm, debridit_ad 
                debridit_rd.debrid_it('wipeaddon', name)
                debridit_pm.debrid_it('wipeaddon', name)
                debridit_ad.debrid_it('wipeaddon', name)
                from resources.libs import databit
                databit.revoke_fenlt_rd()
                databit.revoke_affen_rd()
                databit.revoke_fenlt_pm()
                databit.revoke_affen_pm()
                databit.revoke_fenlt_ad()
                databit.revoke_affen_ad()
                from resources.libs import jsonit
                jsonit.realizer_rvk()
                xbmcgui.Dialog().notification('Account Manager', 'All Add-ons Revoked!', amgr_icon, 3000)
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Active Debrid Accounts!', amgr_icon, 3000) # If Accounts authorized notify user
                
        #BACKUP ALL DEBRID ACCOUNTS
        elif mode == 'backupall':  # Save Debrid Data for all Debrid services
            if str(var.chk_accountmgr_tk_rd) != '' or str(var.chk_accountmgr_tk_pm) != '' or str(var.chk_accountmgr_tk_ad) != '': # Skip backup if no Debrid accounts authorized
                from resources.libs import debridit_rd, debridit_pm, debridit_ad
                debridit_rd.debrid_it('update', name)
                debridit_pm.debrid_it('update', name)
                debridit_ad.debrid_it('update', name)
                from resources.libs import databit
                databit.backup_fenlt_rd()
                databit.backup_fenlt_pm()
                databit.backup_fenlt_ad()
                databit.backup_affen_rd()
                databit.backup_affen_pm()
                databit.backup_affen_ad()
                from resources.libs import jsonit
                jsonit.realizer_bk()
                xbmcgui.Dialog().notification('Account Manager', 'Backup Complete!', amgr_icon, 3000)
            if str(var.chk_accountmgr_tk_rd) == '': # If Account Mananger is not Authorized notify user
                xbmcgui.Dialog().notification('Account Manager', 'No Active Debrid Accounts!', amgr_icon, 3000)
            
        #RESTORE ALL DEBRID ACCOUNTS
        elif mode == 'restoreall':  # Recover All Saved Debrid Data for all Accounts
            if xbmcvfs.exists(var.rd_backup) or xbmcvfs.exists(var.pm_backup) or xbmcvfs.exists(var.ad_backup): # Skip restore if no debrid folder present in backup folder
                try:
                    if xbmcvfs.exists(var.rd_backup): # Skip restore if no backup folder exists or it's empty
                        path_rd = os.listdir(var.rd_backup)
                        if len(path_rd) != 0: # Skip if backup directory is empty
                            from resources.libs import debridit_rd
                            debridit_rd.debrid_it('restore', name)
                            from resources.libs import databit
                            databit.restore_fenlt_rd()
                            databit.restore_affen_rd()
                            from resources.libs import jsonit
                            jsonit.realizer_rst()
                            xbmcgui.Dialog().notification('Account Manager', 'Real-Debrid Data Restored!', rd_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data Found!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data Found!', rd_icon, 3000)
                    if xbmcvfs.exists(var.pm_backup): # Skip restore if no backup folder exists or it's empty
                        path_pm = os.listdir(var.pm_backup)
                        if len(path_pm) != 0: # Skip if backup directory is empty
                            from resources.libs import debridit_pm
                            debridit_pm.debrid_it('restore', name)
                            from resources.libs import databit
                            databit.restore_fenlt_pm()
                            databit.restore_affen_pm()
                            xbmcgui.Dialog().notification('Account Manager', 'Premiumize Data Restored!', pm_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data Found!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data Found!', pm_icon, 3000)
                    if xbmcvfs.exists(var.ad_backup): # Skip restore if no backup folder exists or it's empty
                        path_ad = os.listdir(var.ad_backup)
                        if len(path_ad) != 0: # Skip if backup directory is empty
                            from resources.libs import debridit_ad
                            debridit_ad.debrid_it('restore', name)
                            from resources.libs import databit
                            databit.restore_fenlt_ad()
                            databit.restore_affen_ad()
                            xbmcgui.Dialog().notification('Account Manager', 'All-Debrid Data Restored!', ad_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data Found!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data Found!', ad_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Restore All Debrid Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'Restore Failed! No Saved Data Found!', amgr_icon, 3000)
                 
        #CLEAR ALL SAVED DATA FOR DEBRID ACCOUNTS
        elif mode == 'clearall':  # Clear All Saved Debrid Data
            if xbmcvfs.exists(var.rd_backup) or xbmcvfs.exists(var.pm_backup) or xbmcvfs.exists(var.ad_backup): # Skip clearing data if no debrid folder present in backup folder
                try:     
                    if xbmcvfs.exists(var.rd_backup): # Skip clear data if no backup folder exists or it's empty
                        path_rd = os.listdir(var.rd_backup)
                        if len(path_rd) != 0: # Skip if backup directory is empty
                            from resources.libs import debridit_rd
                            debridit_rd.clear_saved(name)
                            from resources.libs import databit
                            databit.delete_fenlt_rd()
                            databit.delete_affen_rd()
                            from resources.libs import jsonit
                            jsonit.realizer_rm()
                            xbmcgui.Dialog().notification('Account Manager', 'Real-Debrid Data Cleared!', rd_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    if xbmcvfs.exists(var.pm_backup): # Skip clear data if no backup folder exists or it's empty
                        path_pm = os.listdir(var.pm_backup)
                        if len(path_pm) != 0: # Skip if backup directory is empty
                            from resources.libs import debridit_pm
                            debridit_pm.clear_saved(name)
                            from resources.libs import databit
                            databit.delete_fenlt_pm()
                            databit.delete_affen_pm()
                            xbmcgui.Dialog().notification('Account Manager', 'Premiumize Data Cleared!', pm_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                    if xbmcvfs.exists(var.ad_backup): # Skip clear data if no backup folder exists or it's empty
                        path_ad = os.listdir(var.ad_backup)
                        if len(path_ad) != 0: # Skip if backup directory is empty
                            from resources.libs import debridit_ad
                            debridit_ad.clear_saved(name)
                            from resources.libs import databit
                            databit.delete_fenlt_ad()
                            databit.delete_affen_ad()
                            xbmcgui.Dialog().notification('Account Manager', 'All-Debrid Data Cleared!', ad_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Account Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear All Debrid Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Account Manager', 'No Data to Clear!', amgr_icon, 3000)
                 
        # REVOKE/WIPE CLEAN ALL ADD-ONS
        elif mode == 'wipeclean':  # Clear data and restore stock API Keys for all add-ons
            yes = dialog.yesno('Account Manager', 'WARNING! This will completely wipe all data and restore add-ons to default settings. Click proceed to continue or cancel to quit.', 'Cancel', 'Proceed') # Ask user for permission
            if yes:
                try:
                    from resources.libs import traktit, metait_all, non_debrid_all, debridit_rd, debridit_pm, debridit_ad, databit, jsonit
                    #Revoke Trakt
                    traktit.trakt_it_revoke('wipeaddon', name)
                    databit.revoke_fenlt_trakt()
                    databit.revoke_affen_trakt()
                    xbmcgui.Dialog().notification('Account Manager', 'Trakt Revoked!', amgr_icon, 3000)
                    xbmc.sleep(3000)

                    #Revoke Debrid
                    debridit_rd.debrid_it('wipeaddon', name)
                    debridit_pm.debrid_it('wipeaddon', name)
                    debridit_ad.debrid_it('wipeaddon', name)
                    databit.revoke_fenlt_rd()
                    databit.revoke_fenlt_pm()
                    databit.revoke_fenlt_ad()
                    databit.revoke_affen_rd()
                    databit.revoke_affen_pm()
                    databit.revoke_affen_ad()
                    jsonit.realizer_rvk()
                    xbmcgui.Dialog().notification('Account Manager', 'Debrid Revoked!', amgr_icon, 3000)

                    #Revoke Metadata & Non-Debrid
                    metait_all.debrid_it('clearaddon', name)
                    non_debrid_all.debrid_it('clearaddon', name)
                    databit.revoke_fenlt_easy()
                    databit.revoke_fenlt_meta()
                    databit.revoke_affen_easy()
                    databit.revoke_affen_meta()
                    xbmcgui.Dialog().notification('Account Manager', 'Metadata & Non-Debrid Revoked!', amgr_icon, 3000)
                    xbmc.sleep(1000)

                    #Clear all saved data
                    traktit.clear_saved(name)
                    metait_all.clear_saved(name)
                    non_debrid_all.clear_saved(name)
                    debridit_rd.clear_saved(name)
                    debridit_pm.clear_saved(name)
                    debridit_ad.clear_saved(name)
                    xbmc.sleep(1000)
                    databit.delete_fenlt_rd()
                    databit.delete_fenlt_pm()
                    databit.delete_fenlt_ad()
                    databit.delete_fenlt_trakt()
                    databit.delete_fenlt_easy()
                    databit.delete_fenlt_meta()
                    databit.delete_affen_rd()
                    databit.delete_affen_pm()
                    databit.delete_affen_ad()
                    jsonit.realizer_rm()
                    databit.delete_affen_trakt()
                    databit.delete_fenlt_easy()
                    databit.delete_fenlt_meta()
                    xbmcgui.Dialog().notification('Account Manager', 'All Saved Data Cleared!', amgr_icon, 3000)
                    xbmc.sleep(3000)

                    #Force close Kodi
                    xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
                    os._exit(1)
                except:
                    xbmc.log('%s: Router.py Revoke/Wipe/Clean Account Manager Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            
    def _finish(self, handle):
        from resources.libs.common import directory
        
        directory.set_view()
        
        xbmcplugin.setContent(handle, 'files')
        xbmcplugin.endOfDirectory(handle)                       
