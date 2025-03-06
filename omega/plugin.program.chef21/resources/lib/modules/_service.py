import json
import base64
import xbmc
import xbmcgui
from uservar import notify_url, changelog_dir
from .maintenance import clear_packages_startup
from .addonvar import setting, setting_set, addon_name, addon_icon, isBase64, headers, dialog, local_string, addon_id, gui_save_default, UPDATE_VERSION, CURRENT_BUILD, CURRENT_VERSION, BUILD_URL
from .build_install import restore_binary, binaries_path, build_install
from .addons_enable import enable_addons
from .save_data import backup_gui_skin
from . import  notify

class Startup:
    def check_updates(self):
           if CURRENT_BUILD == 'No Build Installed':
               nobuild = dialog.yesnocustom(
                   addon_name,
                   'There is currently no build installed.\nWould you like to install one now?',
                   'Remind Later'
               )
               if nobuild == 1:
                   xbmc.executebuiltin(
                       f'ActivateWindow(10001, "plugin://{addon_id}/?mode=1",return)'
                   )
               elif nobuild == 0:
                   setting_set('buildname', 'No Build')
               return
           if UPDATE_VERSION is None:
               pass
           else:
               if UPDATE_VERSION > CURRENT_VERSION and setting('update_passed') != 'true':
                   update_available = xbmcgui.Dialog().yesnocustom(
                       addon_name,
                       f'{local_string(30047)} {CURRENT_BUILD} {local_string(30048)}\n{local_string(30049)} {CURRENT_VERSION}\n{local_string(30050)} {UPDATE_VERSION}\n{local_string(30051)}',
                       yeslabel='Update Now', nolabel='Not Now', customlabel='View Changelog', defaultbutton=xbmcgui.DLG_YESNO_CUSTOM_BTN
                   )
                   
                   if update_available == 1:
                       name = CURRENT_BUILD
                       name2 = name
                       if BUILD_URL.startswith('https://www.dropbox.com'):
                           url = BUILD_URL.replace('dl=0', 'dl=1')
                       else:
                           url = BUILD_URL
                       build_install(name, name2, UPDATE_VERSION, url) 
                       
                   elif update_available == 0:
                       remind_later = xbmcgui.Dialog().yesno(addon_name, 'Would you like to be reminded later?', yeslabel='Remind Later', nolabel='Ignore', defaultbutton=xbmcgui.DLG_YESNO_YES_BTN)
                       if remind_later:
                           setting_set('update_passed', 'false')
                       else:
                           setting_set('update_passed', 'true')
                       
                   elif update_available == 2:
                       if changelog_dir == 'http://CHANGEME' or '':
                           xbmcgui.Dialog().notification(addon_name, 'No Changelog to Display!!', addon_icon, 3000)
                           Startup().check_updates()
                       else:
                           message = notify.get_changelog()
                           notify.notification_clog(message)
                       
               elif UPDATE_VERSION == CURRENT_VERSION and setting('update_passed') == 'true':
                   setting_set('update_passed', 'false')
                   
    def save_menu(self):
        choices = []
        preselect = []
        if setting('savedata') == 'true':
            choices.append('[I]Trakt & Debrid Data[/I][TABS]5[/TABS][Preselected]')
            preselect.append(0)
        else:
            choices.append('Trakt & Debrid Data')
        if setting('saveyoutube') == 'true':
            choices.append('[I]YouTube API Keys[/I][TABS]5[/TABS][Preselected]')
            preselect.append(1)
        else:
            choices.append('YouTube API Keys')
        if setting('saveadvanced') == 'true':
            choices.append('[I]Advanced Settings[/I][TABS]5[/TABS][Preselected]')
            preselect.append(2)
        else:
            choices.append('Advanced Settings')
        if setting('savefavs') == 'true':
            choices.append('[I]Favourites[/I][TABS]7[/TABS][Preselected]')
            preselect.append(4)
        else:
            choices.append('Favourites')
        save_select = dialog.multiselect(
            f'{addon_name} - {local_string(30052)}',
            choices,
            preselect=preselect
        )
        # Select Save Items
        if save_select is None:
            return
        save_items = [choices[index] for index in save_select]
                
        if 'Trakt & Debrid Data' in save_items:
            setting_set('savedata', 'true')
        elif '[I]Trakt & Debrid Data[/I][TABS]5[/TABS][Preselected]' in save_items:
            setting_set('savedata', 'true')
        else:
            setting_set('savedata', 'false')
            
        if 'YouTube API Keys' in save_items:
            setting_set('saveyoutube', 'true')
        elif '[I]YouTube API Keys[/I][TABS]5[/TABS][Preselected]' in save_items:
            setting_set('saveyoutube', 'true')
        else:
            setting_set('saveyoutube', 'false')

        if 'Advanced Settings' in save_items:
            setting_set('saveadvanced', 'true')
        elif '[I]Advanced Settings[/I][TABS]5[/TABS][Preselected]' in save_items:
            setting_set('saveadvanced', 'true')
        else:
            setting_set('saveadvanced', 'false')
            
        if 'Favourites' in save_items:
            setting_set('savefavs', 'true')
        elif '[I]Favourites[/I][TABS]7[/TABS][Preselected]' in save_items:
            setting_set('savefavs', 'true')
        else:
            setting_set('savefavs', 'false')
  
        setting_set('firstrunSave', 'true')

    def notify_check(self):
        if notify_url in ('http://CHANGEME', 'http://slamiousproject.com/wzrd/notify19.txt', '', 'http://'):
            return
        
        info = notify.get_notify()
        current_notify = int(setting('notifyversion'))
        notify_version = info[0]
        message = info[1]
        if setting('firstrunNotify') != 'true' or notify_version > current_notify:
            notify.notification(message)
            setting_set('firstrunNotify', 'true')
            setting_set('notifyversion', str(notify_version))
    
    def run_startup(self):
        if setting('firstrun') == 'true':
            enable_addons()
            backup_gui_skin(gui_save_default)
            setting_set('firstrun', 'false')
        else:
            if setting('autoclearpackages') == 'true':
                clear_packages_startup()
            xbmc.sleep(1000)
            self.notify_check()
            xbmc.sleep(3000)  # Delay Build Update Notification
            self.check_updates()
        if binaries_path.exists():
            restore_binary()
