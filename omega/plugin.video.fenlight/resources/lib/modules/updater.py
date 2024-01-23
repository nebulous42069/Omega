# -*- coding: utf-8 -*-
import shutil
import time
import sqlite3 as database
from zipfile import ZipFile
from modules.utils import string_alphanum_to_num
from modules import kodi_utils 
# logger = kodi_utils.logger

requests, addon_info, unzip, confirm_dialog, ok_dialog = kodi_utils.requests, kodi_utils.addon_info, kodi_utils.unzip, kodi_utils.confirm_dialog, kodi_utils.ok_dialog
translate_path, osPath, delete_file, execute_builtin = kodi_utils.translate_path, kodi_utils.osPath, kodi_utils.delete_file, kodi_utils.execute_builtin
update_local_addons, disable_enable_addon, close_all_dialog = kodi_utils.update_local_addons, kodi_utils.disable_enable_addon, kodi_utils.close_all_dialog
update_kodi_addons_db, notification = kodi_utils.update_kodi_addons_db, kodi_utils.notification

packages_dir = translate_path('special://home/addons/packages/')
home_addons_dir = translate_path('special://home/addons/')
destination_check = translate_path('special://home/addons/plugin.video.fenlight/')

def get_versions():
	try:
		result = requests.get('https://github.com/Tikipeter/tikipeter.github.io/raw/main/packages/fen_light_version')
		if result.status_code != 200: return None, None
		online_version = string_alphanum_to_num(result.text.replace('\n', ''))
		current_version = string_alphanum_to_num(addon_info('version'))
		return current_version, online_version
	except: return None, None

def update_check(action=4):
	if action == 3: return
	current_version, online_version = get_versions()
	if not current_version: return notification('Fen Light Update Error')
	line = 'Installed Version: [B]%s[/B][CR]Online Version: [B]%s[/B][CR][CR] ' % (current_version, online_version)
	if current_version == online_version:
		if action == 4: return ok_dialog(heading='Fen Light Updater', text=line + '[B]No Update Available[/B]')
		return
	if action in (0, 4):
		if not confirm_dialog(heading='Fen Light Updater', text=line + '[B]An Update is Available[/B][CR]Perform Update?'): return
	if action == 1: notification('Fen Light Update Occuring')
	if action == 2: return notification('Fen Light Update Available')
	return update_addon(online_version, action)

def update_addon(new_version, action):
	close_all_dialog()
	execute_builtin('ActivateWindow(Home)', True)
	zip_name = 'plugin.video.fenlight-%s.zip' % new_version
	url = 'https://github.com/Tikipeter/tikipeter.github.io/raw/main/packages/%s' % zip_name
	result = requests.get(url, stream=True)
	if result.status_code != 200: return ok_dialog(heading='Fen Light Updater', text='Error Updating. Please install new update manually')
	zip_location = osPath.join(packages_dir, zip_name)
	with open(zip_location, 'wb') as f: shutil.copyfileobj(result.raw, f)
	shutil.rmtree(osPath.join(home_addons_dir, 'plugin.video.fenlight'))
	success = unzip(zip_location, home_addons_dir, destination_check)
	delete_file(zip_location)
	if not success: return ok_dialog(heading='Fen Light Updater', text='Error Updating.[CR]Please install new update manually')
	if action in (0, 4): ok_dialog(heading='Fen Light Updater', text='Success.[CR]Fen Light updated to version [B]%s[/B]' % new_version)
	update_local_addons()
	disable_enable_addon()
	update_kodi_addons_db()