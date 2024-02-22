# -*- coding: utf-8 -*-

'''
	Account Manager
'''

import sys
import os
import xbmcgui
import xbmcaddon
from urllib.parse import parse_qsl
from accountmgr.modules import control
from libs.common import var

joinPath = os.path.join
dialog = xbmcgui.Dialog()
addon = xbmcaddon.Addon
addonObject = addon('script.module.accountmgr')
addonInfo = addonObject.getAddonInfo

amgr_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.acctview').getAddonInfo('path'), 'resources', 'icons'), 'accountmgr.png')
rd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'realdebrid.png')
pm_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'premiumize.png')
ad_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'alldebrid.png')
trakt_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'trakt.png')
tmdb_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'tmdb.png')
furk_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'furk.png')
easy_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'easynews.png')
file_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.accountmgr').getAddonInfo('path'), 'resources', 'icons'), 'filepursuit.png')

def notification(title=None, message=None, icon=None, time=3000, sound=False):
	if title == 'default' or title is None: title = addonName()
	if isinstance(title, int): heading = lang(title)
	else: heading = str(title)
	if isinstance(message, int): body = lang(message)
	else: body = str(message)
	if icon is None or icon == '' or icon == 'default': icon = addonIcon()
	elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
	elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
	elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
	dialog.notification(heading, body, icon, time, sound=sound)

def addonIcon():
	return addonInfo('icon')

def addonName():
	return addonInfo('name')

control.set_active_monitor()

params = {}
for param in sys.argv[1:]:
	param = param.split('=')
	param_dict = dict([param])
	params = dict(params, **param_dict)

action = params.get('action')
query = params.get('query')
addon_id = params.get('addon_id')

if action and not any(i in action for i in ['Auth', 'Revoke']):
	control.release_active_monitor()

if action is None:
	control.openSettings(query, "script.module.accountmgr")

#Trakt
elif action == 'traktAcct':
	from accountmgr.modules import trakt
	trakt.Trakt().account_info_to_dialog()

elif action == 'traktAuth':
	from accountmgr.modules import trakt
	control.function_monitor(trakt.Trakt().auth)

elif action == 'traktReSync': #Sync Trakt with installed add-ons
        from accountmgr.modules import trakt_sync
        control.function_monitor(trakt_sync.Auth().trakt_auth)
        xbmc.sleep(1000)
        notification('Account Manager', 'Sync Complete!', icon=trakt_icon)
        xbmc.sleep(3000)
        xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
        os._exit(1)
        
elif action == 'traktRevoke':
	from accountmgr.modules import trakt
	control.function_monitor(trakt.Trakt().revoke)

#Real-Debrid
elif action == 'realdebridAcct':
	from accountmgr.modules import realdebrid
	realdebrid.RealDebrid().account_info_to_dialog()

elif action == 'realdebridAuth':
	from accountmgr.modules import realdebrid
	control.function_monitor(realdebrid.RealDebrid().auth)

elif action == 'realdebridReSync': #Sync Real-Debrid with installed add-ons
        from accountmgr.modules import debrid_rd
        control.function_monitor(debrid_rd.Auth().realdebrid_auth)
        notification('Account Manager', 'Sync Complete!', icon=rd_icon)
                
elif action == 'realdebridRevoke':
	from accountmgr.modules import realdebrid
	control.function_monitor(realdebrid.RealDebrid().revoke)

#Premiumize
elif action == 'premiumizeAcct':
	from accountmgr.modules import premiumize
	premiumize.Premiumize().account_info_to_dialog()

elif action == 'premiumizeAuth':
	from accountmgr.modules import premiumize
	control.function_monitor(premiumize.Premiumize().auth)

elif action == 'premiumizeReSync': #Sync Premiumize with installed add-ons
        from accountmgr.modules import debrid_pm
        control.function_monitor(debrid_pm.Auth().premiumize_auth)
        notification('Account Manager', 'Sync Complete!', icon=pm_icon)
	
elif action == 'premiumizeRevoke':
	from accountmgr.modules import premiumize
	control.function_monitor(premiumize.Premiumize().revoke)

#All-Debrid
elif action == 'alldebridAcct':
	from accountmgr.modules import alldebrid
	alldebrid.AllDebrid().account_info_to_dialog()

elif action == 'alldebridAuth':
	from accountmgr.modules import alldebrid
	control.function_monitor(alldebrid.AllDebrid().auth)

elif action == 'alldebridReSync': #Sync All-Debrid with installed add-ons
        from accountmgr.modules import debrid_ad
        control.function_monitor(debrid_ad.Auth().alldebrid_auth)
        notification('Account Manager', 'Sync Complete!', icon=ad_icon)

elif action == 'alldebridRevoke':
	from accountmgr.modules import alldebrid
	control.function_monitor(alldebrid.AllDebrid().revoke)

#Sync Multiple Debrid Accounts
elif action == 'ReSyncAll': #Sync RD/PM?AD with installed add-ons
        #Real-Debrid
	if str(var.chk_accountmgr_tk_rd) != '': #Skip sync if Account Mananger is not authorized
                from accountmgr.modules import debrid_rd
                debrid_rd.Auth().realdebrid_auth()
                notification('Account Manager', 'Real-Debrid Sync Complete!', icon=rd_icon)
	if str(var.chk_accountmgr_tk_rd) == '': #If Account Mananger is not Authorized notify user
                notification('Account Manager', 'Real-Debrid NOT Authorized!', icon=rd_icon)

        #Premiumize
	if str(var.chk_accountmgr_tk_pm) != '': #Skip sync if Account Mananger is not authorized
                from accountmgr.modules import debrid_pm
                debrid_pm.Auth().premiumize_auth()
                notification('Account Manager', 'Premiumize Sync Complete!', icon=pm_icon)
	if str(var.chk_accountmgr_tk_pm) == '': #If Account Mananger is not Authorized notify user
                notification('Account Manager', 'Premiumize NOT Authorized!', icon=pm_icon)

        #All-Debrid
	if str(var.chk_accountmgr_tk_ad) != '': #Skip sync if Account Mananger is not authorized
                from accountmgr.modules import debrid_ad
                debrid_ad.Auth().alldebrid_auth()
                notification('Account Manager', 'All-Debrid Sync Complete!', icon=ad_icon)
	if str(var.chk_accountmgr_tk_ad) == '': #If Account Mananger is not Authorized notify user
                notification('Account Manager', 'All-Debrid NOT Authorized!', icon=ad_icon)

#Sync Meta Accounts
elif action == 'tmdbAuth':
	from accountmgr.modules import tmdb
	control.function_monitor(tmdb.Auth().create_session_id)

elif action == 'tmdbRevoke':
	from accountmgr.modules import tmdb
	control.function_monitor(tmdb.Auth().revoke_session_id)

elif action == 'metaReSync':
	if str(var.chk_accountmgr_fanart) != '' or str(var.chk_accountmgr_omdb) != '' or str(var.chk_accountmgr_mdb) != '' or str(var.chk_accountmgr_imdb) != '' or str(var.chk_accountmgr_tmdb) != '' or str(var.chk_accountmgr_tmdb_user) != '' or str(var.chk_accountmgr_tvdb) != '': #Skip sync if no meta account data in Account Manager
                notification('Account Manager', 'Sync in progress, please wait!', icon=amgr_icon)
                from accountmgr.modules import meta_sync
                meta_sync.Auth().meta_auth()
                if var.setting('backupenable') == 'true': #Check if backup service is enabled
                        xbmc.executebuiltin('PlayMedia(plugin://script.module.acctview/?mode=savemeta&name=all)') #Save Metadata               
                        xbmc.sleep(3000)
                notification('Account Manager', 'Sync Complete!', icon=amgr_icon)
                xbmc.sleep(3000)
                xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
	else: #If Account Mananger is not Authorized notify user
                notification('Account Manager', 'No Meta Data to Sync!', icon=amgr_icon)

#Sync Furk/Easynews/FilePursuit
elif action == 'SyncAll':
        if str(var.chk_accountmgr_furk) != '' or str(var.chk_accountmgr_easy) != '' or str(var.chk_accountmgr_file) != '':
                
                notification('Account Manager', 'Sync in progress, please wait!', icon=amgr_icon)
                
                if str(var.chk_accountmgr_furk) != '': #Skip sync if no Furk data in Account Manager
                        from accountmgr.modules import furk_sync
                        furk_sync.Auth().furk_auth()
                else: #If Account Mananger is not Authorized notify user
                        notification('Account Manager', 'No Furk Data to Sync!', icon=furk_icon)
                        
                if str(var.chk_accountmgr_easy) != '': #Skip sync if no Easynews data in Account Manager
                        from accountmgr.modules import easy_sync
                        easy_sync.Auth().easy_auth()
                else: #If Account Mananger is not Authorized notify user
                        notification('Account Manager', 'No Easynews Data to Sync!', icon=easy_icon)

                if str(var.chk_accountmgr_file) != '': #Skip sync if no Filepursuit data in Account Manager
                        from accountmgr.modules import filepursuit_sync
                        filepursuit_sync.Auth().file_auth()
                else: #If Account Mananger is not Authorized notify user
                        notification('Account Manager', 'No FilePursuit Data to Sync!', icon=file_icon)
                if var.setting('backupenable') == 'true': #Check if backup service is enabled
                        xbmc.executebuiltin('PlayMedia(plugin://script.module.acctview/?mode=save_nondebrid&name=all)') #Save Non-Debrid Data
                        xbmc.sleep(3000)
                notification('Account Manager', 'Sync Complete!', icon=amgr_icon)
                xbmc.sleep(3000)
                xbmcgui.Dialog().ok('Account Manager', 'To save changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                notification('Account Manager', 'No Data to Sync!', icon=amgr_icon)
                
#View Supported Add-ons              
elif action == 'ShowSupported_Trakt':
	from accountmgr.modules import changelog
	changelog.get_supported_trakt()

elif action == 'ShowSupported_Debrid':
	from accountmgr.modules import changelog
	changelog.get_supported_debrid()

elif action == 'ShowSupported_Furk':
	from accountmgr.modules import changelog
	changelog.get_supported_furk()

elif action == 'ShowSupported_Easy':
	from accountmgr.modules import changelog
	changelog.get_supported_easy()

elif action == 'ShowSupported_File':
	from accountmgr.modules import changelog
	changelog.get_supported_filepursuit()

elif action == 'ShowSupported_Meta':
	from accountmgr.modules import changelog
	changelog.get_supported_meta()

#View Changelog	
elif action == 'ShowChangelog':
	from accountmgr.modules import changelog
	changelog.get()

#Other
elif action == 'ShowHelp':
	from accountmgr.help import help
	help.get(params.get('name'))

elif action == 'ShowHelpTMDb':
	from accountmgr.help import help
	help.get_tmdb()

elif action == 'ShowHelpMeta':
	from accountmgr.help import help
	help.get_meta()

elif action == 'ShowHelpNonDebrid':
	from accountmgr.help import help
	help.get_nondebrid()

elif action == 'ShowHelpCustom':
	from accountmgr.help import help
	help.get_custom()

elif action == 'ShowHelpRestore':
	from accountmgr.help import help
	help.get_restore()

elif action == 'ShowHelpReadme':
	from accountmgr.help import help
	help.get_readme()
	
elif action == 'ShowHelpIssues':
	from accountmgr.help import help
	help.get_issues()
	
elif action == 'ShowOKDialog':
	control.okDialog(params.get('title', 'default'), int(params.get('message', '')))

elif action == 'tools_clearLogFile':
	from accountmgr.modules import log_utils
	cleared = log_utils.clear_logFile()
	if cleared == 'canceled': pass
	elif cleared: control.notification(message='My Accounts Log File Successfully Cleared')
	else: control.notification(message='Error clearing My Accounts Log File, see kodi.log for more info')

elif action == 'tools_viewLogFile':
	from accountmgr.modules import log_utils
	log_utils.view_LogFile(params.get('name'))

elif action == 'tools_uploadLogFile':
	from accountmgr.modules import log_utils
	log_utils.upload_LogFile()

elif action == 'SetBackupFolder':
	from accountmgr.modules import control
	control.set_backup_folder()

elif action == 'ResetBackupFolder':
	from accountmgr.modules import control
	control.reset_backup_folder()
