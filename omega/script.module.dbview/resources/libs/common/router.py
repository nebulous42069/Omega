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
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common import var
from resources.libs.gui import menu

debridmgr = xbmcaddon.Addon("script.module.debridmgr")
addon = xbmcaddon.Addon
addonObject = addon('script.module.dbview')
addonInfo = addonObject.getAddonInfo
getLangString = xbmcaddon.Addon().getLocalizedString
condVisibility = xbmc.getCondVisibility
execute = xbmc.executebuiltin
monitor = xbmc.Monitor()
joinPath = os.path.join
dialog = xbmcgui.Dialog()
date_time = datetime.now()
date = date_time.strftime('Date: %Y-%m-%d  Time: %H:%M')

amgr_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'debridmgr.png')
rd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'realdebrid.png')
pm_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'premiumize.png')
ad_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'alldebrid.png')
torbox_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'torbox.png')
easyd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'easydebrid.png')
offcloud_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.dbview').getAddonInfo('path'), 'resources', 'icons'), 'offcloud.png')
                      
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
        
        from resources.libs import debridit_rd, debridit_pm, debridit_ad, tbit, edit, offit, extit, databit, jsonit
        
        # MAIN MENU
        if mode is None:
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

        elif mode == 'extproviders':  # External Providers Account Viewer
            menu.ext_menu()
            self._finish(handle)

        elif mode == 'allaccts':  # All Account Viewer
            menu.all_accounts_menu()
            self._finish(handle)

        # OPEN ADDON SETTINGS           
        elif mode == 'opensettings_rd':  # Real Debrid
            from resources.libs import debridit_rd
            debridit_rd.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_pm':  # Premiumize
            from resources.libs import debridit_pm
            debridit_pm.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_ad':  # All-Debrid
            from resources.libs import debridit_ad
            debridit_ad.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_all':  # Debrid All
            from resources.libs import debridit_all
            debridit_all.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_tb':  # TorBox
            from resources.libs import tbit
            tbit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_ed':  # Easy Debrid
            from resources.libs import edit
            edit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_oc':  # OffCloud
            from resources.libs import offit
            offit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_ext':  # External Providers
            from resources.libs import extit
            extit.open_settings(name)
            xbmc.executebuiltin('Container.Refresh()')

        elif mode == 'opensettings_fenlt':  # Open Fen Light settings
            var.open_settings_fenlt()
            xbmc.executebuiltin('Container.Refresh()')
            
        # DEBRID MANAGER RD
        elif mode == 'savedebrid_rd':  # Save Debrid Data
            debridit_rd.debrid_it('update', name)
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_rd()
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.backup_affen_rd()
            jsonit.realizer_bk()
        elif mode == 'savedebrid_acctmgr_rd':  # Save Debrid Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_tk_rd) != '':
                    debridit_rd.debrid_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_rd()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_rd()
                    jsonit.realizer_bk()
                    debridmgr.setSetting('rd_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'RealDebrid Backup Complete!', rd_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No RealDebrid Data to Backup!', rd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoredebrid_rd':  # Recover All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.rd_backup): # Skip restore if no debrid folder present in backup folder
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        debridit_rd.debrid_it('restore', name)
                        debridmgr.setSetting("sync.rd.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_rd()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                            #databit.restore_affen_rd()
                            #var.remake_settings() #Refresh settings database
                        jsonit.realizer_rst()
                        xbmcgui.Dialog().notification('Debrid Manager', 'Real-Debrid Data Restored!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data to Restore!', rd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data to Restore!', rd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore RD Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addondebrid_rd':  # Clear All Addon Debrid Data
            debridit_rd.debrid_it('wipeaddon', name)
            debridmgr.setSetting("sync.rd.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_rd()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.revoke_affen_rd()
                #var.remake_settings() #Refresh settings database
            jsonit.realizer_rvk()
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', rd_icon, 3000)           
        elif mode == 'cleardebrid_rd':  # Clear All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.rd_backup): # Skip clearing data if no debrid folder present in backup folder
                    path = os.listdir(var.rd_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('rd_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.rd_backup)
                        for file in data:
                                files = os.path.join(var.rd_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'Real-Debrid Data Cleared!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
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
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_pm()
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.backup_affen_pm()
        elif mode == 'savedebrid_acctmgr_pm':  # Save Debrid Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_tk_pm) != '':
                    debridit_pm.debrid_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_pm()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_pm()
                    debridmgr.setSetting('pm_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'Premiumize Backup Complete!', pm_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Backup!', pm_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoredebrid_pm':  # Recover All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.pm_backup): # Skip restore if no debrid folder present in backup folder
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        debridit_pm.debrid_it('restore', name)
                        debridmgr.setSetting("sync.pm.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_pm()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                            #databit.restore_affen_pm()
                            #var.remake_settings() #Refresh settings database
                        xbmcgui.Dialog().notification('Debrid Manager', 'Premiumize Data Restored!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Restore!', pm_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Restore!', pm_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore PM Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addondebrid_pm':  # Clear All Addon Debrid Data
            debridit_pm.debrid_it('wipeaddon', name)
            debridmgr.setSetting("sync.pm.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_pm()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.revoke_affen_pm()
                #var.remake_settings() #Refresh settings database
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', pm_icon, 3000)
        elif mode == 'cleardebrid_pm':  # Clear All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.pm_backup): # Skip clearing data if no debrid folder present in backup folder
                    path = os.listdir(var.pm_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('pm_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.pm_backup)
                        for file in data:
                                files = os.path.join(var.pm_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'Premiumize Data Cleared!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
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
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_ad()
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.backup_affen_ad()
        elif mode == 'savedebrid_acctmgr_ad':  # Save Debrid Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_tk_ad) != '':
                    debridit_ad.debrid_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_ad()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_ad()
                    debridmgr.setSetting('ad_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'AllDebrid Backup Complete!', ad_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No AllDebrid Data to Backup!', ad_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoredebrid_ad':  # Recover All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.ad_backup): # Skip restore if no debrid folder present in backup folder
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        debridit_ad.debrid_it('restore', name)
                        debridmgr.setSetting("sync.ad.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_ad()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                            #databit.restore_affen_ad()
                            #var.remake_settings() #Refresh settings database
                        xbmcgui.Dialog().notification('Debrid Manager', 'All-Debrid Data Restored!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data to Restore!', ad_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data to Restore!', ad_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore AD Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addondebrid_ad':  # Clear All Addon Debrid Data
            debridit_ad.debrid_it('wipeaddon', name)
            debridmgr.setSetting("sync.ad.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_ad()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.revoke_affen_ad()
                #var.remake_settings() #Refresh settings database
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', ad_icon, 3000)
        elif mode == 'cleardebrid_ad':  # Clear All Saved Debrid Data
            try:
                if xbmcvfs.exists(var.ad_backup): # Skip clearing data if no debrid folder present in backup folder
                    path = os.listdir(var.ad_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('ad_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.ad_backup)
                        for file in data:
                                files = os.path.join(var.ad_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'All-Debrid Data Cleared!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
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
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_tb()
        elif mode == 'save_tb_acctmgr':  # Save Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_tb) != '':
                    tbit.tb_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_tb()
                    debridmgr.setSetting('tb_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'TorBox Backup Complete!', torbox_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No TorBox Data to Backup!', torbox_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoretb':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.tb_backup): # Skip restore if no TorBox folder present in backup folder
                    path = os.listdir(var.tb_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        tbit.tb_it('restore', name)
                        debridmgr.setSetting("sync.torbox.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_tb()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        xbmcgui.Dialog().notification('Debrid Manager', 'TorBox Data Restored!', torbox_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No TorBox Data to Restore!', torbox_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No TorBox Data to Restore!', torbox_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addontb':  # Clear All Addon OffCloud Data
            tbit.tb_it('wipeaddon', name)
            debridmgr.setSetting("sync.torbox.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_tb()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', torbox_icon, 3000)
        elif mode == 'cleartb':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.tb_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.tb_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('tb_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.tb_backup)
                        for file in data:
                                files = os.path.join(var.tb_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'TorBox Data Cleared!', torbox_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No TorBox Data to Clear!', torbox_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No TorBox Data to Clear!', torbox_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Clear TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updatetb':  # Update Saved Data
            tbit.auto_update('all')

        # EASY DEBRID MANAGER
        elif mode == 'saveeasydebrid':  # Save Data
            edit.ed_it('update', name)
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_ed()
        elif mode == 'save_ed_acctmgr':  # Save Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_ed) != '':
                    edit.ed_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_ed()
                    debridmgr.setSetting('ed_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'Easy Debrid Backup Complete!', easyd_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Easy Debrid  Data to Backup!', easyd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoreed':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.ed_backup): # Skip restore if no Easy Debrid folder present in backup folder
                    path = os.listdir(var.ed_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        edit.ed_it('restore', name)
                        debridmgr.setSetting("sync.easyd.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_ed()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        xbmcgui.Dialog().notification('Debrid Manager', 'Easy Debrid  Data Restored!', easyd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Easy Debrid  Data to Restore!', easyd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Easy Debrid  Data to Restore!', easyd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addoned':  # Clear All Addon OffCloud Data
            edit.ed_it('wipeaddon', name)
            debridmgr.setSetting("sync.eastd.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_ed()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', easyd_icon, 3000)
        elif mode == 'cleared':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.ed_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.ed_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('ed_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.ed_backup)
                        for file in data:
                                files = os.path.join(var.ed_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'Easy Debrid  Data Cleared!', easyd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Easy Debrid Data to Clear!', easyd_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No Easy Debrid Data to Clear!', easyd_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Clear Easy Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateed':  # Update Saved Data
            edit.auto_update('all')
            
        # OFFCLOUD MANAGER
        elif mode == 'saveoffcloud':  # Save Data
            offit.offc_it('update', name)
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_oc()
        elif mode == 'save_offc_acctmgr':  # Save Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_offc) != '':
                    offit.offc_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_oc()
                    debridmgr.setSetting('oc_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'OffCloud Backup Complete!', offcloud_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No OffCloud Data to Backup!', offcloud_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoreoffc':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.offc_backup): # Skip restore if no offcloud folder present in backup folder
                    path = os.listdir(var.offc_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        offit.offc_it('restore', name)
                        debridmgr.setSetting("sync.offc.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_oc()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        xbmcgui.Dialog().notification('Debrid Manager', 'OffCloud Data Restored!', offcloud_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No OffCloud Data to Restore!', offcloud_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No OffCloud Data to Restore!', offcloud_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addonoffc':  # Clear All Addon OffCloud Data
            offit.offc_it('wipeaddon', name)
            debridmgr.setSetting("sync.offc.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_oc()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', offcloud_icon, 3000)
        elif mode == 'clearoffc':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.offc_backup): # Skip clearing data if no nondebrid folder present in backup folder
                    path = os.listdir(var.offc_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('oc_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.offc_backup)
                        for file in data:
                                files = os.path.join(var.offc_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'OffCloud Data Cleared!', offcloud_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No OffCloud Data to Clear!', offcloud_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No OffCloud Data to Clear!', offcloud_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Clear OffCloud Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateoffc':  # Update Saved Data
            offit.auto_update('all')

        #EXTERNAL PROVIDERS MANAGER
        elif mode == 'saveext':  # Save Data
            extit.ext_it('update', name)
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.backup_fenlt_ext()
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.backup_affen_ext()
        elif mode == 'save_ext_acctmgr':  # Save Data via Debrid Manager settings menu
            if not var.backup_path:
                xbmcgui.Dialog().ok('Debrid Manager', 'No backup path set! Please set a backup path in Debrid Manager settings.')
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
            else:
                if str(var.chk_debridmgr_ext) != '':
                    extit.ext_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_ext()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_ext()
                    debridmgr.setSetting('ext_backup_date', date)
                    xbmcgui.Dialog().notification('Debrid Manager', 'External Providers Backup Complete!', amgr_icon, 3000)
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No External Providers Data to Backup!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
        elif mode == 'restoreext':  # Recover All Saved Data
            try:
                if xbmcvfs.exists(var.ext_backup): # Skip restore if no extprovider folder present in backup folder
                    path = os.listdir(var.ext_backup)
                    if len(path) != 0: # Skip restore if no saved data in backup folder
                        extit.ext_it('restore', name)
                        debridmgr.setSetting("sync.ext.service", "true")
                        if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                            databit.restore_fenlt_ext()
                            xbmc.executebuiltin('Dialog.Close(all,true)')
                            xbmc.sleep(1000)
                            var.remake_settings() #Refresh settings database
                        #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                            #databit.restore_affen_ext()
                            #var.remake_settings() #Refresh settings database
                        debridmgr.setSetting("ext.provider", 'CocoScrapers')
                        xbmcgui.Dialog().notification('Debrid Manager', 'External Providers Data Restored!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No External Providers Data to Restore!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No External Providers  Data to Restore!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.lLose(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Restore External Providers Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'addonext':  # Clear All Addon External Providers Data
            extit.ext_it('wipeaddon', name)
            debridmgr.setSetting("sync.ext.service", "false")
            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                databit.revoke_fenlt_ext()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                #databit.revoke_affen_ext()
                #var.remake_settings() #Refresh settings database
            debridmgr.setSetting("ext.provider", '')
            xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', amgr_icon, 3000)
        elif mode == 'clearext':  # Clear All Saved Data
            try:
                if xbmcvfs.exists(var.ext_backup): # Skip clearing data if no extprovider folder present in backup folder
                    path = os.listdir(var.ext_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        debridmgr.setSetting('ext_backup_date', 'Date: 0000-00-00   Time: 00:00')
                        data = os.listdir(var.ext_backup)
                        for file in data:
                                files = os.path.join(var.ext_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                        xbmcgui.Dialog().notification('Debrid Manager', 'External Providers Data Cleared!', amgr_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No External Providers Data to Clear!', amgr_icon, 3000)
                        xbmc.sleep(3000)
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                else:
                    xbmcgui.Dialog().notification('Debrid Manager', 'No External Providers Data to Clear!', amgr_icon, 3000)
                    xbmc.sleep(3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
            except:
                xbmc.log('%s: Router.py Clear External Providers Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif mode == 'updateext':  # Update Saved Data
            extit.auto_update('all')
            
        #REVOKE ALL DEBRID ACCOUNTS
        elif mode == 'revokeall':  # Clear Addon Data for all Debrid services
            if str(var.chk_debridmgr_tk_rd) == '' and str(var.chk_debridmgr_tk_pm) == '' and str(var.chk_debridmgr_tk_ad) == '': # If no accounts are authorized notify user
                xbmcgui.Dialog().notification('Debrid Manager', 'No Active Debrid Accounts!', amgr_icon, 3000) # If Accounts authorized notify user
            else:
                if not str(var.chk_debridmgr_tk_rd) == '':
                    debridit_rd.debrid_it('wipeaddon', name)
                    debridmgr.setSetting("sync.rd.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_rd()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_rd()
                    jsonit.realizer_rvk()
                    
                if not str(var.chk_debridmgr_tk_pm) == '':
                    debridit_pm.debrid_it('wipeaddon', name)
                    debridmgr.setSetting("sync.pm.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_pm()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_pm()
                    
                if not str(var.chk_debridmgr_tk_ad) == '':
                    debridit_ad.debrid_it('wipeaddon', name)
                    debridmgr.setSetting("sync.ad.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_ad()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_ad()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database     
                xbmcgui.Dialog().notification('Debrid Manager', 'All Add-ons Revoked!', amgr_icon, 3000)
                
        #BACKUP ALL DEBRID ACCOUNTS
        elif mode == 'backupall':  # Save Debrid Data for all Debrid services
            if str(var.chk_debridmgr_tk_rd) == '' and str(var.chk_debridmgr_tk_pm) == '' and str(var.chk_debridmgr_tk_ad) != '': # If no accounts are authorized notify user
                xbmcgui.Dialog().notification('Debrid Manager', 'No Active Debrid Accounts!', amgr_icon, 3000)
            else:
                if not str(var.chk_debridmgr_tk_rd) == '': # Skip backup if Debrid account not authorized
                    #Real-Debrid
                    debridit_rd.debrid_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_rd()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_rd()
                    jsonit.realizer_bk()
                    debridmgr.setSetting('rd_backup_date', date)
                    
                if not str(var.chk_debridmgr_tk_pm) == '':
                    #Premiumize
                    debridit_pm.debrid_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_pm()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_pm()
                    debridmgr.setSetting('pm_backup_date', date)

                if not str(var.chk_debridmgr_tk_ad) == '':
                    #All-Debrid
                    debridit_ad.debrid_it('update', name)
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.backup_fenlt_ad()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.backup_affen_ad()
                    debridmgr.setSetting('ad_backup_date', date)
                        
                xbmcgui.Dialog().notification('Debrid Manager', 'Backup Complete!', amgr_icon, 3000)
            
        #RESTORE ALL DEBRID ACCOUNTS
        elif mode == 'restoreall':  # Recover All Saved Debrid Data for all Accounts
            if xbmcvfs.exists(var.rd_backup) or xbmcvfs.exists(var.pm_backup) or xbmcvfs.exists(var.ad_backup): # Skip restore if no debrid folder present in backup folder
                try:
                    if xbmcvfs.exists(var.rd_backup): # Skip restore if no backup folder exists or it's empty
                        path_rd = os.listdir(var.rd_backup)
                        if len(path_rd) != 0: # Skip if backup directory is empty
                            debridit_rd.debrid_it('restore', name)
                            debridmgr.setSetting("sync.rd.service", "true")
                            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                                databit.restore_fenlt_rd()
                            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                                #databit.restore_affen_rd()
                            jsonit.realizer_rst()
                            xbmcgui.Dialog().notification('Debrid Manager', 'Real-Debrid Data Restored!', rd_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data Found!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data Found!', rd_icon, 3000)
                    if xbmcvfs.exists(var.pm_backup): # Skip restore if no backup folder exists or it's empty
                        path_pm = os.listdir(var.pm_backup)
                        if len(path_pm) != 0: # Skip if backup directory is empty
                            debridit_pm.debrid_it('restore', name)
                            debridmgr.setSetting("sync.pm.service", "true")
                            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                                databit.restore_fenlt_pm()
                            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                                #databit.restore_affen_pm()
                            xbmcgui.Dialog().notification('Debrid Manager', 'Premiumize Data Restored!', pm_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data Found!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data Found!', pm_icon, 3000)
                    if xbmcvfs.exists(var.ad_backup): # Skip restore if no backup folder exists or it's empty
                        path_ad = os.listdir(var.ad_backup)
                        if len(path_ad) != 0: # Skip if backup directory is empty
                            debridit_ad.debrid_it('restore', name)
                            debridmgr.setSetting("sync.ad.service", "true")
                            if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                                databit.restore_fenlt_ad()
                            #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                                #databit.restore_affen_ad()
                            xbmcgui.Dialog().notification('Debrid Manager', 'All-Debrid Data Restored!', ad_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data Found!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data Found!', ad_icon, 3000)
                    xbmc.executebuiltin('Dialog.Close(all,true)')
                    xbmc.sleep(1000)
                    var.remake_settings() #Refresh settings database
                except:
                    xbmc.log('%s: Router.py Restore All Debrid Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Debrid Manager', 'Restore Failed! No Saved Data Found!', amgr_icon, 3000)
                xbmc.sleep(3000)
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                 
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
                            xbmcgui.Dialog().notification('Debrid Manager', 'Real-Debrid Data Cleared!', rd_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Real-Debrid Data to Clear!', rd_icon, 3000)
                    
                    #Clear Premiumize Saved Data
                    if xbmcvfs.exists(var.pm_backup): # Skip clearing data if no folder present in backup folder
                        path = os.listdir(var.pm_backup)
                        if len(path) != 0: # Skip clearing data if no saved data in backup folder
                            data = os.listdir(var.pm_backup)
                            for file in data:
                                    files = os.path.join(var.pm_backup, file)
                                    if os.path.isfile(files):
                                            os.remove(files)
                            xbmcgui.Dialog().notification('Debrid Manager', 'Premiumize Data Cleared!', pm_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No Premiumize Data to Clear!', pm_icon, 3000)
                        
                    #Clear All-Debrid Saved Data
                    if xbmcvfs.exists(var.ad_backup): # Skip clearing data if no folder present in backup folder
                        path = os.listdir(var.ad_backup)
                        if len(path) != 0: # Skip clearing data if no saved data in backup folder
                            data = os.listdir(var.ad_backup)
                            for file in data:
                                    files = os.path.join(var.ad_backup, file)
                                    if os.path.isfile(files):
                                            os.remove(files)
                            xbmcgui.Dialog().notification('Debrid Manager', 'All-Debrid Data Cleared!', ad_icon, 3000)
                        else:
                            xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                    else:
                        xbmcgui.Dialog().notification('Debrid Manager', 'No All-Debrid Data to Clear!', ad_icon, 3000)
                except:
                    xbmc.log('%s: Router.py Clear All Debrid Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                    pass
            else:
                xbmcgui.Dialog().notification('Debrid Manager', 'No Data to Clear!', amgr_icon, 3000)
                xbmc.sleep(3000)
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.executebuiltin('Addon.OpenSettings(script.module.debridmgr)')
                 
        # REVOKE/WIPE/CLEAN ALL ADD-ONS
        elif mode == 'wipeclean':  # Revoke all Add-ons, Clear all saved data, and restore stock API Keys for all add-ons
            xbmcgui.Dialog().notification('Debrid Manager', 'Restoring default settings, please wait!', amgr_icon, 3000)
            try:                   
                #Revoke Real-Debrid
                if not str(var.chk_debridmgr_tk_rd) == '':
                    debridit_rd.debrid_it('wipeaddon', name)
                    debridmgr.setSetting("sync.rd.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_rd()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_rd()
                    jsonit.realizer_rvk()
                
                #Revoke Premiumize
                if not str(var.chk_debridmgr_tk_pm) == '':
                    debridit_pm.debrid_it('wipeaddon', name)
                    debridmgr.setSetting("sync.pm.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_pm()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_pm()
                
                #Revoke All-Debrid
                if not str(var.chk_debridmgr_tk_ad) == '':
                    debridit_ad.debrid_it('wipeaddon', name)
                    debridmgr.setSetting("sync.ad.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_ad()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_ad()
                        
                #Revoke TorBox
                if not str(var.setting('torbox.token')) == '':
                    tbit.tb_it('wipeaddon', name)
                    debridmgr.setSetting("sync.torbox.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_tb()
                    debridmgr.setSetting("torbox.enabled", 'false')

                #Revoke Easy Debrid
                if not str(var.setting('easydebrid.token')) == '':
                    edit.ed_it('wipeaddon', name)
                    debridmgr.setSetting("sync.easyd.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_ed()
                    debridmgr.setSetting("easydebrid.enabled", 'false')
                    
                #Revoke OffCloud
                if not str(var.setting('offcloud.token')) == '':
                    offit.offc_it('wipeaddon', name)
                    debridmgr.setSetting("sync.offc.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_oc()
                    debridmgr.setSetting("offcloud.enabled", 'false')

                #Revoke External Providers
                if not str(var.setting('ext.provider')) == '':
                    extit.ext_it('wipeaddon', name)
                    debridmgr.setSetting("sync.ext.service", "false")
                    if xbmcvfs.exists(var.chk_fenlt) and xbmcvfs.exists(var.chkset_fenlt):
                        databit.revoke_fenlt_ext()
                    #if xbmcvfs.exists(var.chk_affen) and xbmcvfs.exists(var.chkset_affen):
                        #databit.revoke_affen_ext()
                    debridmgr.setSetting("ext.provider", '')
                    

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

                #Clear External Providers Saved Data
                if xbmcvfs.exists(var.ext_backup): # Skip clearing data if no folder present in backup folder
                    path = os.listdir(var.ext_backup)
                    if len(path) != 0: # Skip clearing data if no saved data in backup folder
                        data = os.listdir(var.ext_backup)
                        for file in data:
                                files = os.path.join(var.ext_backup, file)
                                if os.path.isfile(files):
                                        os.remove(files)
                xbmc.executebuiltin('Dialog.Close(all,true)')
                xbmc.sleep(1000)
                var.remake_settings() #Refresh settings database
                
            except:
                xbmc.log('%s: Router.py Revoke/Wipe/Clean Debrid Manager Failed!' % var.amgr, xbmc.LOGINFO)
                pass

            xbmcgui.Dialog().ok('Debrid Manager', 'All settings have been restored to default.')
                    
    def _finish(self, handle):
        from resources.libs.common import directory
        
        directory.set_view()
        
        xbmcplugin.setContent(handle, 'files')
        xbmcplugin.endOfDirectory(handle)
