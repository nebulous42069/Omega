# -*- coding: utf-8 -*-
import os
import shutil
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import sqlite3
import zipfile
import tempfile
import xml.etree.ElementTree as ET

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
addon_id = xbmcaddon.Addon().getAddonInfo('id')
addon = xbmcaddon.Addon(addon_id)
addon_info = addon.getAddonInfo
addon_path = translatePath(addon_info('path'))
addon_data = translatePath('special://profile/addon_data/')
addon_icon = translatePath('special://home/addons/script.fentastic.helperr/resources/icon.png')

#Skin Backup/Restore Variables
db_dst_dir = xbmcvfs.translatePath("special://profile/addon_data/script.fentastic.helperr/")
home = translatePath('special://home/')
user_path = os.path.join(home, 'userdata/')
data_path = os.path.join(user_path, 'addon_data/')
skin_path = translatePath('special://skin/')
skin = ET.parse(os.path.join(skin_path, 'addon.xml'))
root = skin.getroot()
skin_id = root.attrib['id']

#GUI/FAV Variables
gui_file = 'guisettings.xml'
fav_file = 'favourites.xml'

#Menu/Widget Default Configs
dst_cfg = xbmcvfs.translatePath('special://skin/xml/')
dst_db = os.path.join(addon_data, 'script.fentastic.helperr/')

fen_cfg = os.path.join(skin_path, 'resources/pre_configs/Fen_Light_Basic/menus_widgets/')
fen_db = os.path.join(skin_path, 'resources/pre_configs/Fen_Light_Basic/database/')

fen_tk_cfg = os.path.join(skin_path, 'resources/pre_configs/Fen_Light_Trakt/menus_widgets/')
fen_tk_db = os.path.join(skin_path, 'resources/pre_configs/Fen_Light_Trakt/database/')

fen_anime_cfg = os.path.join(skin_path, 'resources/pre_configs/Fen_Light_Anime/menus_widgets/')
fen_anime_db = os.path.join(skin_path, 'resources/pre_configs/Fen_Light_Anime/database/')

red_cfg = os.path.join(skin_path, 'resources/pre_configs/Red_Light_Basic/menus_widgets/')
red_db = os.path.join(skin_path, 'resources/pre_configs/Red_Light_Basic/database/')

red_tk_cfg = os.path.join(skin_path, 'resources/pre_configs/Red_Light_Trakt/menus_widgets/')
red_tk_db = os.path.join(skin_path, 'resources/pre_configs/Red_Light_Trakt/database/')

red_anime_cfg = os.path.join(skin_path, 'resources/pre_configs/Red_Light_Anime/menus_widgets/')
red_anime_db = os.path.join(skin_path, 'resources/pre_configs/Red_Light_Anime/database/')

pov_cfg = os.path.join(skin_path, 'resources/pre_configs/POV_Basic/menus_widgets/')
pov_db = os.path.join(skin_path, 'resources/pre_configs/POV_Basic/database/')

pov_tk_cfg = os.path.join(skin_path, 'resources/pre_configs/POV_Trakt/menus_widgets/')
pov_tk_db = os.path.join(skin_path, 'resources/pre_configs/POV_Trakt/database/')

pov_anime_cfg = os.path.join(skin_path, 'resources/pre_configs/POV_Anime/menus_widgets/')
pov_anime_db = os.path.join(skin_path, 'resources/pre_configs/POV_Anime/database/')

umb_cfg = os.path.join(skin_path, 'resources/pre_configs/Umbrella_Basic/menus_widgets/')
umb_db = os.path.join(skin_path, 'resources/pre_configs/Umbrella_Basic/database/')

umb_tk_cfg = os.path.join(skin_path, 'resources/pre_configs/Umbrella_Trakt/menus_widgets/')
umb_tk_db = os.path.join(skin_path, 'resources/pre_configs/Umbrella_Trakt/database/')

gears_cfg = os.path.join(skin_path, 'resources/pre_configs/The_Gears_Basic/menus_widgets/')
gears_db = os.path.join(skin_path, 'resources/pre_configs/The_Gears_Basic/database/')

gears_tk_cfg = os.path.join(skin_path, 'resources/pre_configs/The_Gears_Trakt/menus_widgets/')
gears_tk_db = os.path.join(skin_path, 'resources/pre_configs/The_Gears_Trakt/database/')

tmdbh_cfg = os.path.join(skin_path, 'resources/pre_configs/TMDbH/menus_widgets/')
tmdbh_db = os.path.join(skin_path, 'resources/pre_configs/TMDbH/database/')


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
#Open Kodi keyboard and return input
def get_keyboard_text(default=""):
    kb = xbmc.Keyboard(default, "Enter name for your backup")
    kb.doModal()
    if kb.isConfirmed():
        text = kb.getText().strip()
        return text if text else None
    return None

#Create directory if it doesn't exist
def ensure_dir(path):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)

#Copy file
def copy_file(src, dst):
    try:
        ensure_dir(os.path.dirname(dst))
        xbmcvfs.copy(src, dst)
    except Exception as e:
        dialog.notification("Backup Error", str(e), xbmcgui.NOTIFICATION_ERROR, 3000)

# Check if an addon is installed
def addon_installed(addon_id):
    try:
        xbmcaddon.Addon(addon_id)
        return True
    except:
        return False

# Copy all files from source to destination
def copy_all_files(src_dir, dst_dir):
    # Make sure destination exists
    os.makedirs(dst_dir, exist_ok=True)

    # Loop through items in source directory
    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)
        dst_path = os.path.join(dst_dir, item)

        # Copy only files (skip subdirectories)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)
            
# Delete files starting with
def delete_files_starting_with(directory, prefix):
    # Ensure directory ends with slash
    if not directory.endswith(("/", "\\")):
        directory += "/"

    # List the directory contents
    try:
        dirs, files = xbmcvfs.listdir(directory)
    except Exception as e:
        xbmc.log(f"Error reading directory: {e}", xbmc.LOGERROR)
        return

    # Loop through files and delete those starting with prefix
    for file_name in files:
        if file_name.startswith(prefix):
            full_path = os.path.join(directory, file_name)
            xbmcvfs.delete(full_path)

# Apply Default Config XML files
def apply_default_config_xmls():
    src = xbmcvfs.translatePath('special://skin/resources/default_configs/')
    dst = xbmcvfs.translatePath('special://skin/xml/')

    if not src.endswith(("/", "\\")):
        src += "/"

    if not dst.endswith(("/", "\\")):
        dst += "/"

    if not xbmcvfs.exists(src):
        xbmc.log(f"FENtastic Plus: default config path missing: {src}", xbmc.LOGERROR)
        return False

    dirs, files = xbmcvfs.listdir(src)

    for file_name in files:
        if file_name.startswith('script-fentastic') and file_name.endswith('.xml'):
            src_file = src + file_name
            dst_file = dst + file_name
            xbmcvfs.copy(src_file, dst_file)

    return True

# Write Main Menu icons to settings
def write_pre_config_main_menu_icons(cfg_src):
    icon_settings = {
        "script-fentastic-main_menu_movies.xml": "movie.main_menu_icon",
        "script-fentastic-main_menu_tvshows.xml": "tvshow.main_menu_icon",
        "script-fentastic-main_menu_custom1.xml": "custom1.main_menu_icon",
        "script-fentastic-main_menu_custom2.xml": "custom2.main_menu_icon",
        "script-fentastic-main_menu_custom3.xml": "custom3.main_menu_icon",
        "script-fentastic-main_menu_custom4.xml": "custom4.main_menu_icon",
        "script-fentastic-main_menu_custom5.xml": "custom5.main_menu_icon",
        "script-fentastic-main_menu_custom6.xml": "custom6.main_menu_icon",
    }

    for file_name, skin_key in icon_settings.items():
        xml_path = os.path.join(cfg_src, file_name)

        if not os.path.exists(xml_path):
            continue

        try:
            with open(xml_path, "r", encoding="utf-8") as f:
                data = f.read()

            start = data.find("<thumb>")
            end = data.find("</thumb>", start)

            if start == -1 or end == -1:
                continue

            icon = data[start + len("<thumb>"):end].strip().replace('"', "'")

            if icon:
                xbmc.executebuiltin(f'Skin.SetString({skin_key},"{icon}")')
                xbmc.sleep(50)

        except Exception as e:
            xbmc.log(f"FENtastic Plus: failed to read pre-config icon from {xml_path}. Reason: {e}",xbmc.LOGERROR)

# Apply Pre-Config XML files
def apply_pre_config(cfg_src, db_src, search_provider):
    apply_default_config_xmls()
    enable_pre_config_home_menu_toggles()
    xbmc.executebuiltin(f'Skin.SetString(current_search_provider,"{search_provider}")')
    copy_all_files(cfg_src, dst_cfg)
    write_pre_config_main_menu_icons(dst_cfg)
    copy_all_files(db_src, dst_db)

	
# -------------------------------------------------
# SET BACKUP DIRECTORY
# -------------------------------------------------
def choose_backup_directory():
    default_path = xbmcvfs.translatePath("special://home/backups/FENtastic_Plus/")
    current_path = xbmc.getInfoLabel("Skin.String(backup_directory)")

    if not current_path:
        current_path = default_path

    path = xbmcgui.Dialog().browseSingle(3,"Choose Backup Directory","files",defaultt=current_path)

    if not path:
        return

    xbmc.executebuiltin('Skin.SetString(backup_directory,"%s")' % path)

    dialog.ok("FENtastic Plus","Backup directory saved.[CR][CR]""Location:[CR][COLOR=gold]%s[/COLOR]" % os.path.normpath(path))


def get_backup_directory():
    path = xbmc.getInfoLabel("Skin.String(backup_directory)")

    if path:
        return xbmcvfs.translatePath(path)

    return xbmcvfs.translatePath("special://home/backups/FENtastic_Plus/")


def get_backup_subdir(folder_name):
    path = os.path.join(get_backup_directory(), folder_name)
    ensure_dir(path)
    return path


# -------------------------------------------------
# GUI & FAVS BACKUP/RESTORE FUNCTIONS
# -------------------------------------------------
#Backup GUI settings
def backup_gui():
    gui_save = get_backup_subdir("gui_bkup")
    selection = xbmcgui.Dialog().yesno("FENtastic Plus","Are you sure?")
    if selection == 1:
        ensure_dir(gui_save)
        if os.path.exists(os.path.join(user_path, gui_file)) and os.path.exists(os.path.join(gui_save)):
            try:
                xbmcvfs.copy(os.path.join(user_path, gui_file), os.path.join(gui_save, gui_file))
            except Exception as e:
                xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(gui_save, gui_file), e), xbmc.LOGINFO)
        dialog.notification("FENtastic Plus", "Backup Complete", addon_icon, 3000)
    elif selection == 0:
        return

#Restore GUI settings              
def restore_gui():
    gui_save = get_backup_subdir("gui_bkup")
    selection = xbmcgui.Dialog().yesno("FENtastic Plus","Are you sure?")
    if selection == 1:
        if os.path.exists(os.path.join(gui_save, gui_file)):
            try:
                xbmcvfs.copy(os.path.join(gui_save, gui_file), os.path.join(user_path, gui_file))
            except Exception as e:
                xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(user_path, gui_file), e), xbmc.LOGINFO)
        dialog.ok('FENtastic Plus', 'To save changes you now need to force close Kodi.\n\nPress OK to force close Kodi.')
        os._exit(1)
    elif selection == 0:
        return

#Backup Favourites
def backup_favs():
    fav_save = get_backup_subdir("favs_bkup")
    selection = xbmcgui.Dialog().yesno("FENtastic Plus","Are you sure?")
    if selection == 1:
        ensure_dir(fav_save)
        if os.path.exists(os.path.join(user_path, fav_file)) and os.path.exists(os.path.join(fav_save)):
            try:
                xbmcvfs.copy(os.path.join(user_path, fav_file), os.path.join(fav_save, fav_file))
            except Exception as e:
                xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(fav_save, fav_file), e), xbmc.LOGINFO)
        dialog.notification("FENtastic Plus", "Backup Complete", addon_icon, 3000)
    elif selection == 0:
        return

#Restore Favourites              
def restore_favs():
    fav_save = get_backup_subdir("favs_bkup")
    selection = xbmcgui.Dialog().yesno("FENtastic Plus","Are you sure?")
    if selection == 1:
        if os.path.exists(os.path.join(fav_save, fav_file)):
            try:
                xbmcvfs.copy(os.path.join(fav_save, fav_file), os.path.join(user_path, fav_file))
            except Exception as e:
                xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(user_path, fav_file), e), xbmc.LOGINFO)
        dialog.ok('FENtastic Plus', 'To save changes you now need to force close Kodi.\n\nPress OK to force close Kodi.')
        os._exit(1)
    elif selection == 0:
        return

#Restore skin settings
def restore_skin(skin_save):
    selection = xbmcgui.Dialog().yesno("FENtastic Plus", "Restore the default skin settings.\nAre you sure?")
    if selection == 1:
        if os.path.exists(os.path.join(data_path, skin_id)):
            base_path = translatePath('special://home/addons/skin.fentasticp/')
            src = os.path.join(base_path,'resources','default_colors','fentastic_plus','defaults.xml')
            dst = os.path.join(base_path,'colors','defaults.xml')
            try:
                shutil.copytree(skin_save,os.path.join(data_path, skin_id),dirs_exist_ok=True)
                copy_file(src, dst)
            except Exception as e:
                xbmc.log('Failed to restore %s. Reason: %s' %(os.path.join(data_path, skin_id), e),xbmc.LOGINFO)
        dialog.notification("FENtastic Plus", "Restore Complete", addon_icon, 3000)
        dialog.ok('FENtastic Plus', 'To save changes you now need to force close Kodi.\n\nPress OK to force close Kodi.')
        os._exit(1)
    elif selection == 0:
            return


# -------------------------------------------------
# USER-CONFIG BACKUP FUNCTION
# -------------------------------------------------
def backup_config():
    backup_name = get_keyboard_text()
    if not backup_name:
        dialog.ok("Backup Canceled", "No backup name was entered.")
        return

    base_backup_dir = get_backup_subdir("User_Configs")
    backup_dir = os.path.join(base_backup_dir, backup_name)
    zip_path = backup_dir + ".zip"

    skin_backup_dir = os.path.join(backup_dir, "skin_files")
    skin_settings_backup_dir = os.path.join(backup_dir, "skin_settings")

    for d in (skin_backup_dir, skin_settings_backup_dir):
        ensure_dir(d)

    # Paths
    xml_dir = xbmcvfs.translatePath("special://skin/xml/")
    db_src = xbmcvfs.translatePath("special://profile/addon_data/script.fentastic.helperr/cpath_cache.db")

    # Backup Menus/Widgets
    for file in xbmcvfs.listdir(xml_dir)[1]:
        if "script-fentastic" in file.lower():
            src = os.path.join(xml_dir, file)
            dst = os.path.join(skin_backup_dir, file)
            copy_file(src, dst)

    # Backup database
    if xbmcvfs.exists(db_src):
        copy_file(db_src, os.path.join(backup_dir, "cpath_cache.db"))

    # Backup skin settings   
    if os.path.exists(os.path.join(data_path, skin_id)) and os.path.exists(os.path.join(skin_settings_backup_dir)):
        try:
            shutil.copytree(os.path.join(data_path, skin_id),os.path.join(skin_settings_backup_dir, skin_id),dirs_exist_ok=True)
        except Exception as e:
            xbmc.log('Failed to backup %s. Reason: %s' % (os.path.join(skin_settings_backup_dir, skin_id), e),xbmc.LOGINFO)

    # Create zip
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zipf.write(file_path, arcname)

        shutil.rmtree(backup_dir, ignore_errors=True)

    except Exception as e:
        xbmc.log('Failed to create backup zip %s. Reason: %s' % (zip_path, e), xbmc.LOGINFO)
        dialog.ok("Backup Failed", "Failed to create backup zip.")
        return

    display_path = os.path.normpath(zip_path)

    dialog.ok("Backup Completed",f"Backup saved as: [COLOR=gold]{backup_name}.zip[/COLOR][CR]"f"Location:[CR][COLOR=gold]{display_path}[/COLOR]")


# -------------------------------------------------
# USER-CONFIG RESTORE FUNCTION
# -------------------------------------------------
def restore_config():
    base_backup_dir = get_backup_subdir("User_Configs")

    # List backup zip files
    backups = [f for f in xbmcvfs.listdir(base_backup_dir)[1] if f.lower().endswith(".zip")]

    if not backups:
        dialog.ok("Restore Error", "No backups available.")
        return

    # User selects a backup
    index = dialog.select("Choose Backup To Restore", backups)
    if index < 0:
        return

    selected_backup = backups[index]
    zip_path = os.path.join(base_backup_dir, selected_backup)
    extract_path = os.path.join(base_backup_dir, "_restore_temp")

    try:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path, ignore_errors=True)

        ensure_dir(extract_path)

        with zipfile.ZipFile(zip_path, "r") as zipf:
            zipf.extractall(extract_path)

        backup_path = extract_path
        skin_backup_path = os.path.join(backup_path, "skin_files/")
        skin_settings_backup_path = os.path.join(backup_path, "skin_settings/")

        # Restore skin XML files
        xml_dir = xbmcvfs.translatePath("special://skin/xml/")

        delete_files_starting_with(dst_cfg, 'script-fentastic')
        
        if xbmcvfs.exists(skin_backup_path):
            for file in xbmcvfs.listdir(skin_backup_path)[1]:
                src = os.path.join(skin_backup_path, file)
                dst = os.path.join(xml_dir, file)
                copy_file(src, dst)

        #Restore skin settings            
        if os.path.exists(os.path.join(data_path, skin_id)):
            try:
                shutil.copytree(os.path.join(skin_settings_backup_path, skin_id), os.path.join(data_path, skin_id), dirs_exist_ok=True)
            except Exception as e:
                xbmc.log('Failed to restore %s. Reason: %s' % (os.path.join(data_path, skin_id), e), xbmc.LOGINFO)

        #Restore database
        ensure_dir(db_dst_dir)
        db_src = os.path.join(backup_path, "cpath_cache.db")
        if xbmcvfs.exists(db_src):
            copy_file(db_src, os.path.join(db_dst_dir, "cpath_cache.db"))

    except Exception as e:
        xbmc.log('Failed to restore backup zip %s. Reason: %s' % (zip_path, e), xbmc.LOGINFO)
        dialog.ok("Restore Failed", "Failed to restore backup zip.")
        return

    finally:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path, ignore_errors=True)
    
    dialog.ok("Restore Complete", f"Restored backup:   [COLOR=gold]{selected_backup}[/COLOR]")
    xbmc.executebuiltin("ReloadSkin()")


# -------------------------------------------------
# USER-CONFIG EXPORT FUNCTION
# -------------------------------------------------
def export_config():
    base_backup_dir = get_backup_subdir("User_Configs")

    backups = [f for f in xbmcvfs.listdir(base_backup_dir)[1] if f.lower().endswith(".zip")]
    if not backups:
        dialog.ok("Export Error", "No backups available to export.")
        return

    index = dialog.select("Select Backup To Export", backups)
    if index < 0:
        return

    backup_name = backups[index]
    backup_path = os.path.join(base_backup_dir, backup_name)

    dest_dir = dialog.browse(3,"Choose Export Location","files","",False,False) # Select directory

    if not dest_dir:
        return

    if not dest_dir.endswith(("/", "\\")):
        dest_dir += "/"

    export_path = os.path.join(dest_dir, backup_name)

    try:
        if os.path.exists(export_path):
            os.remove(export_path)

        copy_file(backup_path, export_path)

    except Exception as e:
        dialog.ok("Export Error", f"Failed to export backup:\n{e}")
        return

    dialog.notification("FENtastic Plus",f"Backup exported as:\n{backup_name}",addon_icon,3000)

    
# -------------------------------------------------
# USER-CONFIG IMPORT FUNCTION
# -------------------------------------------------
def import_config():
    zip_path = dialog.browseSingle(1,"Select FENtastic Plus Backup ZIP","local",".zip",False,False)

    if not zip_path:
        return

    if not zip_path.lower().endswith(".zip"):
        dialog.ok("Import Error", "Selected file is not a ZIP archive.")
        return

    base_backup_dir = get_backup_subdir("User_Configs")
    ensure_dir(base_backup_dir)

    backup_name = os.path.basename(zip_path)
    final_dst = os.path.join(base_backup_dir, backup_name)

    if os.path.exists(final_dst):
        overwrite = dialog.yesno("Backup Exists",f"A backup named '{backup_name}' already exists.\n\nOverwrite it?")
        if not overwrite:
            return
        os.remove(final_dst)

    try:
        copy_file(zip_path, final_dst)
    except Exception as e:
        dialog.ok("Import Error", f"Failed to import backup:\n{e}")
        return

    # Ask to restore
    if dialog.yesno("Import Complete",f"Backup '{backup_name}' imported successfully.\n\nRestore it now?"):
        restore_config()


# -------------------------------------------------
# Enable Pre-Config Main Menu Toggles
# -------------------------------------------------
def enable_pre_config_home_menu_toggles():
    """
    Enables Movies, TV Shows, and Custom1-6
    Disables the default Kodi menu items not used by pre-configs
    """
    enabled_settings = [
        "HomeMenuNoMoviesButton",
        "HomeMenuNoTVShowsButton",
        "HomeMenuNoCustom1Button",
        "HomeMenuNoCustom2Button",
        "HomeMenuNoCustom3Button",
        "HomeMenuNoCustom4Button",
        "HomeMenuNoCustom5Button",
        "HomeMenuNoCustom6Button",
        "HomeMenuNoProgramsButton",
        "HomeMenuNoFavButton",
    ]

    disabled_settings = [
        "HomeMenuNoMusicButton",
        "HomeMenuNoMusicVideoButton",
        "HomeMenuNoTVButton",
        "HomeMenuNoRadioButton",
        "HomeMenuNoPicturesButton",
        "HomeMenuNoVideosButton",
        "HomeMenuNoGamesButton",
        "HomeMenuNoWeatherButton",
    ]

    for setting in enabled_settings:
        if xbmc.getCondVisibility(f"Skin.HasSetting({setting})"):
            xbmc.executebuiltin(f"Skin.Reset({setting})")
            xbmc.sleep(50)

    for setting in disabled_settings:
        if not xbmc.getCondVisibility(f"Skin.HasSetting({setting})"):
            xbmc.executebuiltin(f"Skin.SetBool({setting})")
            xbmc.sleep(50)


# -------------------------------------------------
# Main Menu Labels
# -------------------------------------------------
def load_all_menu_labels():
    """
    Reads all main menu labels from cpath_cache.db and assigns them
    to Skin.String() values for use in XML.
    """
    db_path = translatePath("special://profile/addon_data/script.fentastic.helperr/cpath_cache.db")

    if not xbmcvfs.exists(db_path):
        return

    # DB main-menu key - Skin.String key - default label
    MENU_MAP = {
        "movie":   ("MenuMovieLabelDB",   "Movies"),
        "tvshow":  ("MenuTVShowLabelDB",  "TV Shows"),
        "custom1": ("MenuCustom1LabelDB", "Custom 1"),
        "custom2": ("MenuCustom2LabelDB", "Custom 2"),
        "custom3": ("MenuCustom3LabelDB", "Custom 3"),
        "custom4": ("MenuCustom4LabelDB", "Custom 4"),
        "custom5": ("MenuCustom5LabelDB", "Custom 5"),
        "custom6": ("MenuCustom6LabelDB", "Custom 6"),
    }

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        for key, (skin_key, default_label) in MENU_MAP.items():
            # This matches rows like "movie.main_menu", "tvshow.main_menu", "custom1.main_menu", etc.
            setting_key = f"{key}.main_menu"

            cur.execute("SELECT cpath_header FROM custom_paths WHERE cpath_setting = ? LIMIT 1",(setting_key,))
            row = cur.fetchone()

            if row and row[0]:
                label = row[0]
                source = "DB"
            else:
                label = default_label
                source = "DEFAULT"

            safe = label.replace('"', "'")
            xbmc.executebuiltin(f'Skin.SetString({skin_key},"{safe}")')

        conn.close()

    except Exception as e:
        xbmc.log(f"DB Error loading menu labels: {e}", xbmc.LOGERROR)

        
# -------------------------------------------------
# Select Pre-Made Configurations
# -------------------------------------------------
def pre_config_dialog():
    """
    Shows only config modes for addons actually installed
    """
    menu = []
    modes = []

    def add_separator(title):
        menu.append(f"[COLOR dimgray]──────── {title} ────────[/COLOR]")
        modes.append(None)
        
    # TMDb Helper
    if addon_installed("plugin.video.themoviedb.helper"):
        add_separator("TMDb Helper (Free Or Debrid)")
        menu.append("TMDb Helper")
        modes.append("TMDb Helper")
        
    # Red Light
    if addon_installed("plugin.video.themoviedb.helper"):
        add_separator("Red Light (Debrid Only")
        for config in ("Basic", "Trakt"):
            label = f"Red Light {config}"
            menu.append(label)
            modes.append(label)

    # POV
    if addon_installed("plugin.video.themoviedb.helper"):
        add_separator("POV (Debrid Only)")
        for config in ("Basic", "Trakt"):
            label = f"POV {config}"
            menu.append(label)
            modes.append(label)

    # Umbrella
    if addon_installed("plugin.video.themoviedb.helper"):
        add_separator("Umbrella (Debrid Only)")
        for config in ("Basic", "Trakt"):
            label = f"Umbrella {config}"
            menu.append(label)
            modes.append(label)

    # The Gears
    if addon_installed("plugin.video.themoviedb.helper"):
        add_separator("The Gears (Debrid Only)")
        for config in ("Basic", "Trakt"):
            label = f"The Gears {config}"
            menu.append(label)
            modes.append(label)

    # Nothing installed
    if not menu:
        xbmcgui.Dialog().ok("FENtastic Plus","No supported addons are installed.\nNothing to configure.")
        return

    # Let user choose
    while True:
        choice = xbmcgui.Dialog().select("Choose Your Flavor",menu)

        if choice == -1:
            return

        # Ignore separators
        if modes[choice] is None:
            continue

        run_pre_config_mode(modes[choice])
        break

def run_pre_config_mode(mode):
    # Ask the user to confirm before applying
    confirm = xbmcgui.Dialog().yesno(
        "FENtastic Plus",
        f"Are you sure you want to apply the '[COLOR gold]{mode}[/COLOR]' pre-configuration?\n\n"
        "This will overwrite your current menu/widgets configuration.",
        nolabel="No",
        yeslabel="Yes"
    )

    if not confirm:
        return
    
    if mode == "Fen Light Basic":
        apply_pre_config(fen_cfg, fen_db, "1")

    elif mode == "Fen Light Trakt":
        apply_pre_config(fen_tk_cfg, fen_tk_db, "1")

    elif mode == "Fen Light Anime":
        apply_pre_config(fen_anime_cfg, fen_anime_db, "1")

    elif mode == "Red Light Basic":
        apply_pre_config(red_cfg, red_db, "5")

    elif mode == "Red Light Trakt":
        apply_pre_config(red_tk_cfg, red_tk_db, "5")

    elif mode == "Red Light Anime":
        apply_pre_config(red_anime_cfg, red_anime_db, "5")

    elif mode == "POV Basic":
        apply_pre_config(pov_cfg, pov_db, "3")

    elif mode == "POV Trakt":
        apply_pre_config(pov_tk_cfg, pov_tk_db, "3")

    elif mode == "POV Anime":
        apply_pre_config(pov_anime_cfg, pov_anime_db, "3")

    elif mode == "Umbrella Basic":
        apply_pre_config(umb_cfg, umb_db, "2")

    elif mode == "Umbrella Trakt":
        apply_pre_config(umb_tk_cfg, umb_tk_db, "2")

    elif mode == "The Gears Basic":
        apply_pre_config(gears_cfg, gears_db, "4")

    elif mode == "The Gears Trakt":
        apply_pre_config(gears_tk_cfg, gears_tk_db, "4")

    elif mode == "TMDb Helper":
        apply_pre_config(tmdbh_cfg, tmdbh_db, "0")

    load_all_menu_labels()
    xbmc.executebuiltin('Skin.SetBool(noiconsilhouettes)')
    xbmc.executebuiltin("ReloadSkin()")
    xbmcgui.Dialog().notification("FENtastic Plus", f"{mode} config applied!", addon_icon, 3000)
