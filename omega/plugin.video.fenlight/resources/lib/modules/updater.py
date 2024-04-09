# -*- coding: utf-8 -*-
import shutil
import time
import sqlite3 as database
from zipfile import ZipFile
from caches.settings_cache import set_setting
from modules.utils import string_alphanum_to_num
from modules.settings import update_use_test_repo
from modules import kodi_utils 
# logger = kodi_utils.logger

translate_path, osPath, delete_file, execute_builtin, get_icon = kodi_utils.translate_path, kodi_utils.osPath, kodi_utils.delete_file, kodi_utils.execute_builtin, kodi_utils.get_icon
update_kodi_addons_db, notification, show_text, confirm_dialog = kodi_utils.update_kodi_addons_db, kodi_utils.notification, kodi_utils.show_text, kodi_utils.confirm_dialog
requests, addon_info, unzip, confirm_dialog, ok_dialog = kodi_utils.requests, kodi_utils.addon_info, kodi_utils.unzip, kodi_utils.confirm_dialog, kodi_utils.ok_dialog
update_local_addons, disable_enable_addon, close_all_dialog = kodi_utils.update_local_addons, kodi_utils.disable_enable_addon, kodi_utils.close_all_dialog
json, select_dialog = kodi_utils.json, kodi_utils.select_dialog

packages_dir = translate_path('special://home/addons/packages/')
home_addons_dir = translate_path('special://home/addons/')
destination_check = translate_path('special://home/addons/plugin.video.fenlight/')
changelog_location = translate_path('special://home/addons/plugin.video.fenlight/resources/text/changelog.txt')
github_icon = get_icon('github')
addon_dir = 'plugin.video.fenlight'
repo_location = {True: 'tikipeter.test', False: 'tikipeter.github.io'}
zipfile_name = 'plugin.video.fenlight-%s.zip'
versions_url = 'https://github.com/Tikipeter/%s/raw/main/packages/fen_light_version'
location_url = 'https://github.com/Tikipeter/%s/raw/main/packages/%s'
contents_url = 'https://api.github.com/repos/Tikipeter/%s/contents/packages'
heading_str = 'Fen Light Updater'
notification_error_str = 'Fen Light Update Error'
notification_occuring_str = 'Fen Light Update Occuring'
notification_available_str = 'Fen Light Update Available'
notification_updating_str = 'Fen Light Performing Update'
notification_rollback_str = 'Fen Light Performing Rollback'
result_str = 'Installed Version: [B]%s[/B][CR]Online%s Version: [B]%s[/B][CR][CR] %s'
no_update_str = '[B]No Update Available[/B]'
update_available_str = '[B]An Update is Available[/B][CR]Perform Update?'
success_str = '[CR]Success.[CR]Fen Light updated to version [B]%s[/B]'
rollback_heading_str = 'Choose Rollback Version'
success_rollback_str = '[CR]Success.[CR]Fen Light rolled back to version [B]%s[/B]'
confirm_rollback_str = 'Are you sure?[CR]Version [B]%s[/B] will overwrite your current installed version.' \
						'[CR]Fen Light will set your update action to [B]OFF[/B] if rollback is successful'
no_rollback_str = 'No previous versions found.[CR]Please install rollback manually'
error_str = 'Error Updating.[CR]Please install new update manually'
error_rollback_str = 'Error rolling back.[CR]Please install rollback manually'

def get_versions(use_test_repo):
	try:
		result = requests.get(versions_url % repo_location[use_test_repo])
		if result.status_code != 200: return None, None
		online_version = result.text.replace('\n', '')
		current_version = addon_info('version')
		return current_version, online_version
	except: return None, None

def perform_update(current_version, online_version, use_test_repo):
	if use_test_repo: return current_version != online_version
	else: return string_alphanum_to_num(current_version) != string_alphanum_to_num(online_version)

def update_check(action=4):
	use_test_repo = update_use_test_repo()
	if action == 3: return
	online_type = ' [B]Test[/B]' if use_test_repo else ''
	current_version, online_version = get_versions(use_test_repo)
	if not current_version: return notification(notification_error_str, icon=github_icon)
	if not perform_update(current_version, online_version, use_test_repo):
		if action == 4: return ok_dialog(heading=heading_str, text=result_str % (current_version, online_type, online_version, no_update_str))
		return
	if action in (0, 4):
		if not confirm_dialog(heading=heading_str, text=result_str % (current_version, online_type, online_version, update_available_str)): return
	if action == 1: notification(notification_occuring_str, icon=github_icon)
	if action == 2: return notification(notification_available_str, icon=github_icon)
	return update_addon(online_version, action, use_test_repo)

def update_addon(new_version, action, use_test_repo):
	close_all_dialog()
	execute_builtin('ActivateWindow(Home)', True)
	notification_str = notification_rollback_str if action == 5 else notification_updating_str
	notification(notification_str, icon=github_icon)
	zip_name = zipfile_name % new_version
	url = location_url % (repo_location[use_test_repo], zip_name)
	result = requests.get(url, stream=True)
	if result.status_code != 200: return ok_dialog(heading=heading_str, text=error_str)
	zip_location = osPath.join(packages_dir, zip_name)
	with open(zip_location, 'wb') as f: shutil.copyfileobj(result.raw, f)
	shutil.rmtree(osPath.join(home_addons_dir, addon_dir))
	success = unzip(zip_location, home_addons_dir, destination_check)
	delete_file(zip_location)
	if not success: return ok_dialog(heading=heading_str, text=error_str)
	if action == 5:
		set_setting('update.action', '3')
		ok_dialog(heading=heading_str, text=success_rollback_str % new_version)
	elif action in (0, 4) and confirm_dialog(heading=heading_str, text=success_str % new_version, ok_label='Changelog', cancel_label='Exit', default_control=10) != False:
			show_text('Changelog', file=changelog_location, font_size='large')
	update_local_addons()
	disable_enable_addon()
	update_kodi_addons_db()

def rollback_check():
	use_test_repo = update_use_test_repo()
	current_version = get_versions(use_test_repo)[0]
	url = contents_url % repo_location[use_test_repo]
	results = requests.get(url)
	if results.status_code != 200: return ok_dialog(heading=heading_str, text=error_rollback_str)
	results = [i['name'].split('-')[1].replace('.zip', '') for i in results.json() if 'plugin.video.fenlight' in i['name'] \
				and not i['name'].split('-')[1].replace('.zip', '') == current_version]
	if not results: return ok_dialog(heading=heading_str, text=no_rollback_str)
	list_items = [{'line1': item, 'icon': github_icon} for item in results]
	kwargs = {'items': json.dumps(list_items), 'heading': rollback_heading_str}
	rollback_version = select_dialog(results, **kwargs)
	if rollback_version == None: return
	if not confirm_dialog(heading=heading_str, text=confirm_rollback_str % rollback_version): return
	update_addon(rollback_version, 5, use_test_repo)
