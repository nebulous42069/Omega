# -*- coding: utf-8 -*-
import os
import sys
import xbmc, xbmcgui, xbmcvfs
from urllib.parse import parse_qsl

dialog = xbmcgui.Dialog()
translatePath = xbmcvfs.translatePath
home = translatePath('special://home/')

#GUI Backup/restore paths
gui_save_path = os.path.join(home, 'backups/')
gui_save_user = os.path.join(gui_save_path, 'gui_bkup/')

#FAVS Backup/restore paths
fav_save_path = os.path.join(home, 'backups/')
fav_save_user = os.path.join(fav_save_path, 'favs_bkup/')

    
def routing():
    params = dict(parse_qsl(sys.argv[1], keep_blank_values=True))
    _get = params.get
    mode = _get("mode", "check_for_update")

    # -------------------------------------------------
    # Default modes
    # -------------------------------------------------
    if mode == "widget_monitor":
        from modules.widget_utils import widget_monitor

        return widget_monitor(params.get("list_id"))

    if "actions" in mode:
        from modules import actions

        return exec("actions.%s(params)" % mode.split(".")[1])

    if mode == "check_for_update":
        from modules.version_monitor import check_for_update

        return check_for_update()

    if mode == "check_for_profile_change":
        from modules.version_monitor import check_for_profile_change

        return check_for_profile_change(_get("skin_id"))

    if mode == "manage_widgets":
        from modules.cpath_maker import CPaths

        return CPaths(_get("cpath_setting")).manage_widgets()

    if mode == "manage_main_menu_path":
        from modules.cpath_maker import CPaths

        return CPaths(_get("cpath_setting")).manage_main_menu_path()

    if mode == "manage_main_menu_icon":
        from modules.cpath_maker import manage_main_menu_icon

        return manage_main_menu_icon(_get("cpath_setting"))

    if mode == "starting_widgets":
        from modules.cpath_maker import starting_widgets

        return starting_widgets()

    if mode == "remake_all_cpaths":
        silent = params.get("silent", "false").lower() == "true"
        from modules.cpath_maker import remake_all_cpaths

        return remake_all_cpaths(silent=silent)

    if mode == "search_input":
        from modules.search_utils import SPaths

        return SPaths().search_input()

    if mode == "remove_all_spaths":
        from modules.search_utils import SPaths

        return SPaths().remove_all_spaths()

    if mode == "re_search":
        from modules.search_utils import SPaths

        return SPaths().re_search()

    if mode == "open_search_window":
        from modules.search_utils import SPaths

        return SPaths().open_search_window()

    if mode == "set_api_key":
        from modules.MDbList import set_api_key

        return set_api_key()

    if mode == "delete_all_ratings":
        from modules.MDbList import MDbListAPI

        return MDbListAPI().delete_all_ratings()

    if mode == "modify_keymap":
        from modules.custom_actions import modify_keymap

        return modify_keymap()

    if mode == "play_trailer":
        from modules.MDbList import play_trailer

        return play_trailer()

    if mode == "fix_black_screen":
        from modules.custom_actions import fix_black_screen

        return fix_black_screen()


    # -------------------------------------------------
    # Change Search Provider in Search Results Window
    # -------------------------------------------------
    if mode == 'select_search_provider':
        from modules.search_utils import SPaths

        return SPaths().change_search_provider()


    # -------------------------------------------------
    # Search From History
    # -------------------------------------------------
    if mode == 'search_from_history':
        from modules.search_utils import SPaths

        return SPaths().search_from_history()


    # -------------------------------------------------
    # Set Backup Directory
    # -------------------------------------------------
    if mode == "set_backup_directory":
        from modules.backup_restore import choose_backup_directory

        return choose_backup_directory()


    # -------------------------------------------------
    # Set Skin Colors
    # -------------------------------------------------
    if mode == "set_color":
        from modules.custom_actions import copy_colors

        return copy_colors()

    
    # -------------------------------------------------
    # Set Skin Default Colors
    # -------------------------------------------------
    if mode == "set_fen_dflts":
        from modules.custom_actions import copy_fentastic_defaults

        return copy_fentastic_defaults('fen')

    if mode == "set_fenplus_dflts":
        from modules.custom_actions import copy_fentastic_defaults

        return copy_fentastic_defaults('fenplus')


    # -------------------------------------------------
    # Set Background and Logo
    # -------------------------------------------------
    if mode == "set_image":
        from modules.custom_actions import set_image

        return set_image()

    if mode == "set_image_logo":
        from modules.custom_actions import set_image_logo

        return set_image_logo()


    # ----------------------------------------------------------
    # Classic FENtastic & FENtastic PLus Look & Feel Experience
    # ----------------------------------------------------------
    if mode == 'choose_lookfeel':
        from modules.custom_actions  import choose_lookfeel

        return choose_lookfeel()

    
    # -------------------------------------------------
    # Power Mode Select
    # -------------------------------------------------
    if mode == "power_mode_select":
        choices = ["Force Close", "Quit Kodi", "Show Shutdown Menu"]

        ret = dialog.select("Power Button Mode", choices)

        if ret >= 0:
            value = choices[ret]
            xbmc.executebuiltin(f"Skin.SetString(PowerButtonMode,{value})")
        return

    # -------------------------------------------------
    # OSD Audio Button Select
    # -------------------------------------------------
    if mode == "osd_audio_button_select":
            choices = ["Next audio stream", "Audio settings", "Disabled"]

            ret = dialog.select("Audio Button Behavior", choices)

            if ret >= 0:
                    value = choices[ret]
                    xbmc.executebuiltin(f"Skin.SetString(OSDAudioButtonMode,{value})")
            return

    # -------------------------------------------------
    # OSD Subtitle Button Select
    # -------------------------------------------------
    if mode == "osd_subtitle_button_select":
            choices = ["Next subtitle", "Subtitle settings", "Disabled"]

            ret = dialog.select("Subtitle Button Behavior", choices)

            if ret >= 0:
                    value = choices[ret]
                    xbmc.executebuiltin(f"Skin.SetString(OSDSubtitleButtonMode,{value})")
            return

    # -------------------------------------------------
    # Force Close Kodi
    # -------------------------------------------------
    if mode == "force_close":
        from modules.custom_actions import force_close

        return force_close()


    # -------------------------------------------------
    # Tools Menu
    # -------------------------------------------------
    if mode == "clear_thumbnails":
        from modules.custom_actions import clear_thumbnails

        return clear_thumbnails()

    if mode == "clear_pkgs":
        from modules.custom_actions import clear_packages

        return clear_packages()

    if mode == "advanced_set":
        from modules.custom_actions import advanced_settings

        return advanced_settings()

    #Enable/Disable kodi splash
    if mode == "splash_on":
        from modules.custom_actions import splash, addon_icon
        dialog.notification('FENtastic Plus', 'Splash Enabled!', addon_icon, 3000)
        return splash('true')

    if mode == "splash_off":
        from modules.custom_actions import splash, addon_icon
        dialog.notification('FENtastic Plus', 'Splash Disabled!', addon_icon, 3000)
        return splash('false')

    #Backup & Restore Custom Configs
    if mode == "backup_config":
        from modules.backup_restore import backup_config

        return backup_config()

    if mode == "restore_config":
        from modules.backup_restore import restore_config

        return restore_config()

    #Import & Export Custom Configs
    if mode == "import_config":
        from modules.backup_restore import import_config

        return import_config()

    if mode == "export_config":
        from modules.backup_restore import export_config

        return export_config()
    
    #Backup & Restore GUI settings
    if mode == "backup_gui":
        from modules.backup_restore import backup_gui

        return backup_gui(gui_save_user)

    if mode == "restore_gui":
        from modules.backup_restore import restore_gui

        return restore_gui(gui_save_user)

    #Restore default GUI & Skin settings
    if mode == "restore_gui_dflt":
        from modules.backup_restore import restore_gui

        kodi_version = xbmc.getInfoLabel('System.BuildVersion')

        if kodi_version.startswith('22'):
            saved_defaults = translatePath('special://skin/resources/gui_skin_dflt/K22/')
        elif kodi_version.startswith('21'):
            saved_defaults = translatePath('special://skin/resources/gui_skin_dflt/K21/')

        return restore_gui(saved_defaults)

    if mode == "restore_skin_dflt":
        from modules.backup_restore import restore_skin

        saved_defaults = translatePath('special://skin/resources/gui_skin_dflt/skin.fentasticp/')

        return restore_skin(saved_defaults)

    #Backup & Restore Favourites
    if mode == "backup_favs":
        from modules.backup_restore import backup_favs

        return backup_favs(fav_save_user)

    if mode == "restore_favs":
        from modules.backup_restore import restore_favs

        return restore_favs(fav_save_user)

    # Set Pre-Made Configurations
    if mode == "pre_config":
        from modules.backup_restore import pre_config_dialog
        
        return pre_config_dialog()

    #Focus settings
    if mode == "tmdbh_mdblist_api":
        from modules.custom_actions import tmdbh_mdblist_api

        return tmdbh_mdblist_api()

    if mode == "rurl_settings_rd":
        from modules.custom_actions import rurl_settings_rd

        return rurl_settings_rd()

    if mode == "rurl_settings_pm":
        from modules.custom_actions import rurl_settings_pm

        return rurl_settings_pm()

    if mode == "rurl_settings_ad":
        from modules.custom_actions import rurl_settings_ad

        return rurl_settings_ad()
