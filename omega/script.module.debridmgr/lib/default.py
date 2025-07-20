# -*- coding: utf-8 -*-

'''
	Debrid Manager
'''

import sys
import os
import xbmcgui
import xbmcaddon
import xbmcvfs
import shutil
import time
import json
from urllib.parse import parse_qsl
from debridmgr.modules import control
from libs.common import var

joinPath = os.path.join
dialog = xbmcgui.Dialog()
addon = xbmcaddon.Addon
translatePath = xbmcvfs.translatePath
addonObject = addon('script.module.debridmgr')
addonInfo = addonObject.getAddonInfo
debridmgr = xbmcaddon.Addon('script.module.debridmgr')
xmls = translatePath('special://home/addons/script.module.debridmgr/resources/xmls/')
addon_path = xbmcvfs.translatePath('special://home/addons/')
coco = 'repository.cocoscrapers'
plugin_id = 'script.module.cocoscrapers'

amgr_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'debridmgr.png')
rd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'realdebrid.png')
pm_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'premiumize.png')
ad_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'alldebrid.png')
torbox_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'torbox.png')
easyd_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'easydebrid.png')
offcloud_icon = joinPath(os.path.join(xbmcaddon.Addon('script.module.debridmgr').getAddonInfo('path'), 'resources', 'icons'), 'offcloud.png')

def install_addon(plugin_id):
        if xbmc.getCondVisibility(f'System.HasAddon({plugin_id})'):
            return True
        xbmc.executebuiltin(f'InstallAddon({plugin_id})')
        clicked = False
        start = time.time()
        timeout = 20
        while not isinstalled(plugin_id):
            if time.time() >= start + timeout:
                return False
            xbmc.sleep(500)
            if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)') and not clicked:
                xbmc.executebuiltin('SendClick(yesnodialog, 11)')
                clicked = True
        return True

def isinstalled(addonid):
        query = '{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": { "addonid": "%s", "properties" : ["name", "thumbnail", "fanart", "enabled", "installed", "path", "dependencies"] } }' % addonid
        addonDetails = xbmc.executeJSONRPC(query)
        details_result = json.loads(addonDetails)
        if "error" in details_result:
            return False
        elif details_result['result']['addon']['installed'] == True:
            return True
        else:
            return False
        
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
	control.openSettings(query, "script.module.debridmgr")
	
#Real-Debrid
elif action == 'realdebridAcct':
	from debridmgr.modules.auth import realdebrid
	realdebrid.RealDebrid().account_info_to_dialog()

elif action == 'realdebridAuth':
	from debridmgr.modules.auth import realdebrid
	control.function_monitor(realdebrid.RealDebrid().auth)
	control.setSetting('sync.rd.service', 'true')

elif action == 'realdebridReSync': #Sync Real-Debrid with installed add-ons
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=rd_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import debrid_rd
        control.function_monitor(debrid_rd.Auth().realdebrid_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=rd_icon)
                
elif action == 'realdebridRevoke':
	from debridmgr.modules.auth import realdebrid
	control.function_monitor(realdebrid.RealDebrid().revoke)

#Premiumize
elif action == 'premiumizeAcct':
	from debridmgr.modules.auth import premiumize
	premiumize.Premiumize().account_info_to_dialog()

elif action == 'premiumizeAuth':
	from debridmgr.modules.auth import premiumize
	control.function_monitor(premiumize.Premiumize().auth)
	control.setSetting('sync.pm.service', 'true')

elif action == 'premiumizeReSync': #Sync Premiumize with installed add-ons
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=pm_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import debrid_pm
        control.function_monitor(debrid_pm.Auth().premiumize_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=pm_icon)
	
elif action == 'premiumizeRevoke':
	from debridmgr.modules.auth import premiumize
	control.function_monitor(premiumize.Premiumize().revoke)

#All-Debrid
elif action == 'alldebridAcct':
	from debridmgr.modules.auth import alldebrid
	alldebrid.AllDebrid().account_info_to_dialog()

elif action == 'alldebridAuth':
	from debridmgr.modules.auth import alldebrid
	control.function_monitor(alldebrid.AllDebrid().auth)
	control.setSetting('sync.ad.service', 'true')

elif action == 'alldebridReSync': #Sync All-Debrid with installed add-ons
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=rd_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import debrid_ad
        control.function_monitor(debrid_ad.Auth().alldebrid_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=ad_icon)

elif action == 'alldebridRevoke':
	from debridmgr.modules.auth import alldebrid
	control.function_monitor(alldebrid.AllDebrid().revoke)

#TorBox
elif action == 'torboxAuth':
	from debridmgr.modules.auth import torbox
	control.function_monitor(torbox.Torbox().auth)
	control.setSetting('sync.torbox.service', 'true')
elif action == 'torboxRevoke':
	from debridmgr.modules.auth import torbox
	control.function_monitor(torbox.Torbox().revoke)
elif action == 'torboxReSync':
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=torbox_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import torbox_sync
        control.function_monitor(torbox_sync.Auth().torbox_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=torbox_icon)

#Easy Debrid
elif action == 'easydebridAuth':
	from debridmgr.modules.auth import easydebrid
	control.function_monitor(easydebrid.Easydebrid().auth)
	control.setSetting('sync.easyd.service', 'true')
elif action == 'easydebridRevoke':
	from debridmgr.modules.auth import easydebrid
	control.function_monitor(easydebrid.Easydebrid().revoke)
elif action == 'easydebridReSync':
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=easyd_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import easydebrid_sync
        control.function_monitor(easydebrid_sync.Auth().easydebrid_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=easyd_icon)
                
#Offcloud
elif action == 'offcloudAuth':
	from debridmgr.modules.auth import offcloud
	control.function_monitor(offcloud.Offcloud().auth)
	control.setSetting('sync.offc.service', 'true')
elif action == 'offcloudRevoke':
	from debridmgr.modules.auth import offcloud
	control.function_monitor(offcloud.Offcloud().revoke)
elif action == 'offcloudReSync':
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=offcloud_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import offcloud_sync
        control.function_monitor(offcloud_sync.Auth().offcloud_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=offcloud_icon)

#External Providers
elif action == 'extAuth': #Sync external providers with installed add-ons
        if not os.path.exists(var.chk_coco):
                scrapers = control.yesnoDialog('No external scrapers are installed!\nWould you like to install the package now?', heading=addonInfo('name'), nolabel='No', yeslabel='Yes' )
                if scrapers:
                        shutil.copytree(os.path.join(xmls, coco), os.path.join(addon_path, coco), dirs_exist_ok=True)
                        xbmc.executebuiltin('UpdateLocalAddons')
                        clicked = False
                        xbmc.executebuiltin('EnableAddon(repository.cocoscrapers)')
                        if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)') and not clicked:
                                xbmc.executebuiltin('SendClick(yesnodialog, 11)')
                                clicked = True
                        xbmc.sleep(1000)
                        install_addon(plugin_id)
                        notification('Debrid Manager', 'CocoScrapers Installed!', icon=amgr_icon)
                        from debridmgr.modules.sync import ext_sync
                        debridmgr.setSetting("ext.provider", "CocoScrapers")
                        notification('Debrid Manager', 'Sync in progress, please wait!', icon=amgr_icon)
                        xbmc.sleep(3000)
                        control.function_monitor(ext_sync.Auth().ext_auth)
                        control.setSetting('sync.ext.service', 'true')
                        xbmc.sleep(1000)
                        notification('Debrid Manager', 'Sync Complete!', icon=amgr_icon)
                else:
                        xbmc.executebuiltin('Dialog.Close(all,true)')
                        xbmc.executebuiltin("Addon.openSettings(script.module.debridmgr)")
        else:
                from debridmgr.modules.sync import ext_sync
                debridmgr.setSetting("ext.provider", "CocoScrapers")
                notification('Debrid Manager', 'Sync in progress, please wait!', icon=amgr_icon)
                xbmc.sleep(3000)
                control.function_monitor(ext_sync.Auth().ext_auth)
                control.setSetting('sync.ext.service', 'true')
                xbmc.sleep(1000)
                notification('Debrid Manager', 'Sync Complete!', icon=amgr_icon)
elif action == 'extReSync':                              
        notification('Debrid Manager', 'Sync in progress, please wait!', icon=amgr_icon)
        xbmc.sleep(3000)
        from debridmgr.modules.sync import ext_sync
        control.function_monitor(ext_sync.Auth().ext_auth)
        xbmc.sleep(1000)
        notification('Debrid Manager', 'Sync Complete!', icon=amgr_icon)
        
#Sync Multiple Debrid Accounts
elif action == 'ReSyncAll': #Sync RD/PM/AD with installed add-ons
        #Real-Debrid
	if str(var.chk_debridmgr_tk_rd) != '': #Skip sync if Debrid Manager is not authorized
                from debridmgr.modules.sync import debrid_rd
                control.function_monitor(debrid_rd.Auth().realdebrid_auth)
                xbmc.sleep(1000)
                notification('Debrid Manager', 'Real-Debrid Sync Complete!', icon=rd_icon)
	if str(var.chk_debridmgr_tk_rd) == '': #If Debrid Manager is not Authorized notify user
                notification('Debrid Manager', 'Real-Debrid NOT Authorized!', icon=rd_icon)

        #Premiumize
	if str(var.chk_debridmgr_tk_pm) != '': #Skip sync if Debrid Manager is not authorized
                from debridmgr.modules.sync import debrid_pm
                control.function_monitor(debrid_pm.Auth().premiumize_auth)
                xbmc.sleep(1000)
                notification('Debrid Manager', 'Premiumize Sync Complete!', icon=pm_icon)
	if str(var.chk_debridmgr_tk_pm) == '': #If Debrid Manager is not Authorized notify user
                notification('Debrid Manager', 'Premiumize NOT Authorized!', icon=pm_icon)

        #All-Debrid
	if str(var.chk_debridmgr_tk_ad) != '': #Skip sync if Debrid Manager is not authorized
                from debridmgr.modules.sync import debrid_ad
                control.function_monitor(debrid_ad.Auth().alldebrid_auth)
                xbmc.sleep(1000)
                notification('Debrid Manager', 'All-Debrid Sync Complete!', icon=ad_icon)
	if str(var.chk_debridmgr_tk_ad) == '': #If Debrid Manager is not Authorized notify user
                notification('Debrid Manager', 'All-Debrid NOT Authorized!', icon=ad_icon)

#View Supported Add-ons              
elif action == 'ShowSupported_Debrid':
	from debridmgr.modules import changelog
	changelog.get_supported_debrid()

elif action == 'ShowSupported_Torbox':
	from debridmgr.modules import changelog
	changelog.get_supported_torbox()

elif action == 'ShowSupported_Easydebrid':
	from debridmgr.modules import changelog
	changelog.get_supported_easydebrid()
	
elif action == 'ShowSupported_Offcloud':
	from debridmgr.modules import changelog
	changelog.get_supported_offcloud()

elif action == 'ShowSupported_Ext':
	from debridmgr.modules import changelog
	changelog.get_supported_ext()

elif action == 'ShowSupported_Ext_Addons':
	from debridmgr.modules import changelog
	changelog.get_supported_ext_addons()

#View Changelog	
elif action == 'ShowChangelog':
	from debridmgr.modules import changelog
	changelog.get()

#Other
elif action == 'ShowHelp':
	from debridmgr.help import help
	help.get(params.get('name'))

elif action == 'ShowHelpServiceSync':
	from debridmgr.help import help
	help.get_service_sync()
	
elif action == 'ShowHelpCustom':
	from debridmgr.help import help
	help.get_custom()

elif action == 'ShowHelpRestore':
	from debridmgr.help import help
	help.get_restore()

elif action == 'ShowHelpReadme':
	from debridmgr.help import help
	help.get_readme()
	
elif action == 'ShowHelpIssues':
	from debridmgr.help import help
	help.get_issues()
	
elif action == 'ShowOKDialog':
	control.okDialog(params.get('title', 'default'), int(params.get('message', '')))

elif action == 'tools_clearLogFile':
	from debridmgr.modules import log_utils
	cleared = log_utils.clear_logFile()
	if cleared == 'canceled': pass
	elif cleared: control.notification(message='My Accounts Log File Successfully Cleared')
	else: control.notification(message='Error clearing Debrid Manager Log File, see kodi.log for more info')

elif action == 'tools_viewLogFile':
	from debridmgr.modules import log_utils
	log_utils.view_LogFile(params.get('name'))

elif action == 'tools_uploadLogFile':
	from debridmgr.modules import log_utils
	log_utils.upload_LogFile()

elif action == 'SetBackupFolder':
	from debridmgr.modules import control
	control.set_backup_folder()

elif action == 'ResetBackupFolder':
	from debridmgr.modules import control
	control.reset_backup_folder()
             
elif action == 'resetSettings':
        yes = dialog.yesno('Debrid Manager', 'WARNING! This will completely wipe all your saved data and remove all settings applied to add-ons via Debrid Manager. Click proceed to continue or cancel to quit.', 'Cancel', 'Proceed') # Ask user for permission
        if yes:
                control.setSetting('reset_settings', 'true') #Enable reset at startup
                xbmcgui.Dialog().ok('Debrid Manager', 'Press OK to force close Kodi. You will be prompted at next startup to begin removal.')
                os._exit(1) #Force close Kodi

