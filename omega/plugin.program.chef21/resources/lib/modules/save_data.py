import xbmc
import xbmcgui
import xbmcvfs	
import xbmcaddon
import os
import shutil
import json
import xml.etree.ElementTree as ET 
from .addonvar import user_path, data_path, setting, addon_id, packages, addon_name, dialog

user_path = xbmcvfs.translatePath('special://userdata/')	
data_path = os.path.join(user_path, 'addon_data/')
skin_path = xbmcvfs.translatePath('special://skin/')
text_path = os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')), 'resources/', 'texts/')
skin = ET.parse(os.path.join(skin_path, 'addon.xml'))
root = skin.getroot()
skin_id = root.attrib['id']
gui_save = os.path.join(user_path, 'gui_settings/')
gui_file = 'guisettings.xml'
skinsc = 'script.skinshortcuts'

def backup(path, file):
    if os.path.exists(os.path.join(path, file)):
        try:
            if os.path.isfile(os.path.join(path, file)):
                xbmcvfs.copy(os.path.join(path, file), os.path.join(packages, file))   #Backup your Kodi specifics (advancedsettings, favs etc...)
            elif os.path.isdir(os.path.join(path, file)):
                shutil.copytree(os.path.join(path, file), os.path.join(packages, file), dirs_exist_ok=True)   #Backup your Trakt & Debrid data
        except Exception as e:
            xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(packages, file), e), xbmc.LOGINFO)

def backup_gui_skin():
    if not os.path.exists(gui_save):
        os.mkdir(gui_save)
    if os.path.exists(os.path.join(user_path, gui_file)) and os.path.exists(os.path.join(gui_save)):
        try:
            xbmcvfs.copy(os.path.join(user_path, gui_file), os.path.join(gui_save, gui_file))   #Backup gui settings
        except Exception as e:
            xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(gui_save, gui_file), e), xbmc.LOGINFO)     
    if os.path.exists(os.path.join(data_path, skin_id)) and os.path.exists(os.path.join(gui_save)):
        try:
            shutil.copytree(os.path.join(data_path, skin_id), os.path.join(gui_save, skin_id), dirs_exist_ok=True)   #Backup skin settings
        except Exception as e:
                xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(gui_save, skin_id), e), xbmc.LOGINFO)
    if os.path.exists(os.path.join(data_path, skinsc)) and os.path.exists(os.path.join(gui_save)):
        try:
            shutil.copytree(os.path.join(data_path, skinsc), os.path.join(gui_save, skinsc), dirs_exist_ok=True)   #Backup skinshortcut settings
        except Exception as e:
            xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(gui_save, skinsc), e), xbmc.LOGINFO)        
           
def restore(path, file):
    if os.path.exists(os.path.join(packages, file)):
        try:
            if os.path.isfile(os.path.join(packages, file)):
                if os.path.exists(os.path.join(user_path, file)):
                    os.unlink(os.path.join(path, file))   #Remove Kodi specifics (advancedsettings, favs etc...) included with new install
                shutil.move(os.path.join(packages, file), os.path.join(path, file))   #Restore your backed up Kodi specifics (advancedsettings, favs etc...)
            elif os.path.isdir(os.path.join(packages, file)):
                shutil.copytree(os.path.join(packages, file), os.path.join(path, file), dirs_exist_ok=True)   #Restore your backed up Trakt & Debrid data
        except Exception as e:
            xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(path, file), e), xbmc.LOGINFO)

def restore_gui():
    if os.path.exists(os.path.join(gui_save, gui_file)):
        try:
            xbmcvfs.copy(os.path.join(gui_save, gui_file), os.path.join(user_path, gui_file))   #Restore you backed up gui settings
        except Exception as e:
            xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(user_path, gui_file), e), xbmc.LOGINFO)
    dialog.ok(addon_name, 'To save changes you now need to force close Kodi, Press OK to force close Kodi')
    os._exit(1)
    
def restore_skin():
    if os.path.exists(os.path.join(data_path, skin_id)):
        try:
            shutil.copytree(os.path.join(gui_save, skin_id), os.path.join(data_path, skin_id), dirs_exist_ok=True)   #Restore your backed up skin settings
        except Exception as e:
            xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(data_path, skin_id), e), xbmc.LOGINFO)
    if os.path.exists(os.path.join(data_path, skinsc)) and os.path.exists(os.path.join(gui_save, skinsc)):
        try:
            shutil.copytree(os.path.join(gui_save, skinsc), os.path.join(data_path, skinsc), dirs_exist_ok=True)   #Restore your backed up skinshortcuts settings
        except Exception as e:
            xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(data_path, skinsc), e), xbmc.LOGINFO)
    dialog.ok(addon_name, 'To save changes you now need to force close Kodi, Press OK to force close Kodi')
    os._exit(1)

def save_backup_restore(_type: str) -> None:
    with open(os.path.join(text_path, 'backup_restore.json'), 'r', encoding='utf-8', errors='ignore') as f:
        item_list = json.loads(f.read())
        for item in item_list.keys():
            setting_id = item_list[item]['setting']
            path = item_list[item]['path']
            data = item + '/settings.xml'             #Addon settings
            realizer = item + '/rdauth.json'          #Realizer debrid data
            youtube = item + '/api_keys.json'         #Youtube API Keys
            if path == 'user_path':
                path = user_path
            elif path == 'data_path':
                path = data_path
            try:
                if setting(setting_id)=='true':
                    if _type == 'backup':
                        backup(path, data)            #Backup all addon data
                        backup(user_path, item)       #Backup Kodi specifics
                        backup(path, realizer)        #Backup Realizer data
                        backup(path, youtube)         #Backup Youtube data
                    elif _type == 'restore':
                        restore(path, item)           #Restore all addon data and Kodi specifics
            except Exception as e:
                xbmc.log(f'Error= {e}', xbmc.LOGINFO)
                continue
