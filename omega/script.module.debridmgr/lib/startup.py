import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import os.path
import time
import sqlite3
import _strptime

from libs.common import var
from debridmgr.modules import control
from debridmgr.modules import log_utils

debridmgr = xbmcaddon.Addon("script.module.debridmgr")
dialog = xbmcgui.Dialog()
LOGINFO = 1

timeout_start = time.time()
timeout = 60*5
        
def startup_rd_sync():
        try:
                if str(var.chk_debridmgr_tk_rd) != '': #Skip sync if Real-Debrid is not authorized
                        from debridmgr.modules.sync import debrid_rd
                        debrid_rd.Auth().realdebrid_auth() #Sync Real-Debrid
        except:
                xbmc.log('%s: Startup Real-Debrid Sync Failed!' % var.amgr, xbmc.LOGINFO)
        
def startup_pm_sync():
        try:
                if str(var.chk_debridmgr_tk_pm) != '': #Skip sync if Premiumize is not authorized
                        from debridmgr.modules.sync import debrid_pm
                        debrid_pm.Auth().premiumize_auth() #Sync Premiumize
        except:
                xbmc.log('%s: Startup Premiumize Sync Failed!' % var.amgr, xbmc.LOGINFO)

def startup_ad_sync():
        try:
                if str(var.chk_debridmgr_tk_ad) != '': #Skip sync if All-Debrid is not authorized
                        from debridmgr.modules.sync import debrid_ad 
                        debrid_ad.Auth().alldebrid_auth() #Sync All-Debrid
        except:
                xbmc.log('%s: Startup All-Debrid Sync Failed!' % var.amgr, xbmc.LOGINFO)

def startup_torbox_sync():
        try:    
                if str(var.chk_debridmgr_tb) != '': #Skip sync if no data is available to sync
                        from debridmgr.modules.sync import torbox_sync
                        torbox_sync.Auth().torbox.auth() #Sync Torbox Data
        except:
                xbmc.log('%s: Startup Torbox Sync Failed!' % var.amgr, xbmc.LOGINFO)

def startup_easyd_sync():
        try:    
                if str(var.chk_debridmgr_ed) != '': #Skip sync if no data is available to sync
                        from debridmgr.modules.sync import easydebrid_sync
                        easydebrid_sync.Auth().easydebrid.auth() #Sync Easy Debrid Data
        except:
                xbmc.log('%s: Startup Easy Debrid Sync Failed!' % var.amgr, xbmc.LOGINFO)

def startup_offc_sync():
        try:    
                if str(var.chk_debridmgr_offc) != '': #Skip sync if no data is available to sync
                        from debridmgr.modules.sync import offcloud_sync
                        offcloud_sync.Auth().offcloud.auth() #Sync OffCloud Data
        except:
                xbmc.log('%s: Startup OffCloud Sync Failed!' % var.amgr, xbmc.LOGINFO)

def startup_extp_sync():
        try:    
                if xbmcvfs.exists(var.chk_coco):
                        from debridmgr.modules.sync import ext_sync
                        ext_sync.Auth().ext_auth() #Sync External Provider Data
                        debridmgr.setSetting("ext.provider", "CocoScrapers")
        except:
                xbmc.log('%s: Startup External Provider Sync Failed!' % var.amgr, xbmc.LOGINFO)
                
class AddonCheckUpdate:
        def run(self):
            xbmc.log('[ script.module.debridmgr ]  Addon checking available updates', LOGINFO)
            try:
                import re
                import requests
                repo_xml = requests.get('https://raw.githubusercontent.com/Zaxxon709/zaxxon/main/zips/script.module.debridmgr/addon.xml')
                if repo_xml.status_code != 200:
                    return xbmc.log('[ script.module.debridmgr ]  Could not connect to remote repo XML: status code = %s' % repo_xml.status_code, LOGINFO)
                repo_version = re.search(r'<addon id=\"script.module.debridmgr\".*version=\"(\d*.\d*.\d*)\"', repo_xml.text, re.I).group(1)
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
                    xbmc.log('[ script.module.debridmgr ]  A newer version is available. Installed Version: v%s' % (local_version), LOGINFO)
                    control.notification(message=control.lang(32072) % repo_version, time=5000)
                return xbmc.log('[ script.module.debridmgr ]  Addon update check complete', LOGINFO)
            except:
                import traceback
                traceback.print_exc()

class PremAccntNotification:
	def run(self):
		from datetime import datetime
		from debridmgr.modules.auth import alldebrid
		from debridmgr.modules.auth import premiumize
		from debridmgr.modules.auth import realdebrid
		xbmc.log('[ script.module.debridmgr ]  Debrid Account Expiry Notification Service Starting...', LOGINFO)
		self.duration = [(15, 10), (11, 7), (8, 4), (5, 2), (3, 0)]
		if control.setting('alldebrid.username') != '' and control.setting('alldebrid.expiry.notice') == 'true':
			account_info = alldebrid.AllDebrid().account_info()['user']
			if account_info:
				if not account_info['isSubscribed']:
					expires = datetime.fromtimestamp(account_info['premiumUntil'])
					days_remaining = (expires - datetime.today()).days # int
					if days_remaining < 15:
						control.notification(message='AllDebrid Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'alldebrid.png'))

		if control.setting('premiumize.username') != '' and control.setting('premiumize.expiry.notice') == 'true':
			account_info = premiumize.Premiumize().account_info()
			if account_info:
				expires = datetime.fromtimestamp(account_info['premium_until'])
				days_remaining = (expires - datetime.today()).days # int
				if days_remaining < 15:
					control.notification(message='Premiumize.me Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'premiumize.png'))

		if control.setting('realdebrid.username') != '' and control.setting('realdebrid.expiry.notice') == 'true':
			account_info = realdebrid.RealDebrid().account_info()
			if account_info:
				import time
				FormatDateTime = "%Y-%m-%dT%H:%M:%S.%fZ"
				try: expires = datetime.strptime(account_info['expiration'], FormatDateTime)
				except: expires = datetime(*(time.strptime(account_info['expiration'], FormatDateTime)[0:6]))
				days_remaining = (expires - datetime.today()).days # int
				if days_remaining < 15:
					control.notification(message='Real-Debrid Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'realdebrid.png'))

# AUTO-SYNC STARTUP SERVICES        
if control.setting('sync.rd.service')=='true':
        startup_rd_sync()

if control.setting('sync.pm.service')=='true':
        startup_pm_sync()

if control.setting('sync.ad.service')=='true':
        startup_ad_sync()

if control.setting('sync.torbox.service')=='true':
        startup_torbox_sync()

if control.setting('sync.easyd.service')=='true':
        startup_easyd_sync()

if control.setting('sync.offc.service')=='true':
        startup_offc_sync()

if control.setting('sync.ext.service')=='true':
        startup_extp_sync()

# AM UPDATE NOTIFICATION SERVICE
if control.setting('checkAddonUpdates')=='true':
	AddonCheckUpdate().run()

# ACCOUNT EXPIRES NOTIFICATION
PremAccntNotification().run()

# RESET TO DEFAULT SERVICE
if control.setting('reset_settings')=='true': #Check if reset settings is enabled
        yes = dialog.yesno('Debrid Manager', 'Choose proceed to remove all settings applied by Debrid Manager or cancel to quit.', 'Cancel', 'Proceed') # Ask user for permission
        if yes:
                xbmc.executebuiltin('PlayMedia(plugin://script.module.dbview/?mode=wipeclean&name=all)') #Reset settings
                control.setSetting("reset_settings", "false")
        else:
                if str(var.chk_debridmgr_tk) != '':
                        control.setSetting("api.service", "true") #Re-enable service
                        control.setSetting("reset_settings", "false") #Disable reset settings
