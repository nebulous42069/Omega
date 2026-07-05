# -*- coding: utf-8 -*-
import xbmc, xbmcaddon
import json
import os
from xbmcgui import Window
from xbmc import sleep, getInfoLabel, executebuiltin
from xbmcvfs import translatePath, exists
from xbmcaddon import Addon
from modules.cpath_maker import remake_all_cpaths
from modules.custom_actions import apply_saved_color
from modules.backup_restore import enable_pre_config_home_menu_toggles

# from modules.logger import logger

window = Window(10000)

PROFILE_PATH = os.path.join(
    translatePath("special://userdata/addon_data/script.fentastic.helperr"),
    "current_profile.json",
)


# Enable Main Menu Toggles
def enable_home_menu_toggles():

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

    for setting in enabled_settings:
        if xbmc.getCondVisibility(f"Skin.HasSetting({setting})"):
            xbmc.executebuiltin(f"Skin.Reset({setting})")
            xbmc.sleep(50)
            
def generated_xml_missing():
    xml_path = translatePath("special://skin/xml/")

    required_files = (
        "script-fentastic-widget_movies.xml",
        "script-fentastic-widget_tvshows.xml",
        "script-fentastic-widget_custom1.xml",
        "script-fentastic-widget_custom2.xml",
        "script-fentastic-widget_custom3.xml",
        "script-fentastic-widget_custom4.xml",
        "script-fentastic-widget_custom5.xml",
        "script-fentastic-widget_custom6.xml",
        "script-fentastic-main_menu_movies.xml",
        "script-fentastic-main_menu_tvshows.xml",
        "script-fentastic-main_menu_custom1.xml",
        "script-fentastic-main_menu_custom2.xml",
        "script-fentastic-main_menu_custom3.xml",
        "script-fentastic-main_menu_custom4.xml",
        "script-fentastic-main_menu_custom5.xml",
        "script-fentastic-main_menu_custom6.xml",
    )

    for file_name in required_files:
        if not exists(os.path.join(xml_path, file_name)):
            return True

    return False


def check_for_update():
    skin_id = "skin.fentasticp"
    skin_addon = xbmcaddon.Addon(skin_id)
    current_version = skin_addon.getAddonInfo("version")
    stored_version = xbmc.getInfoLabel("Skin.String(installed_version)")

    missing_xml = generated_xml_missing()
    version_changed = stored_version != current_version

    if missing_xml:
        #enable_home_menu_toggles() # Enable menus
        remake_all_cpaths(silent=True) # Remake menus/widgets
        
    if version_changed:
        executebuiltin("Skin.SetString(installed_version,%s)" % current_version)
        apply_saved_color(reload_skin=False) # Restore current colour scheme
        #enable_home_menu_toggles() # Enable menus
        remake_all_cpaths(silent=True) # Remake menus/widgets


def set_current_profile(skin_id, current_profile):
    dir_path = os.path.dirname(PROFILE_PATH)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(PROFILE_PATH, "w") as f:
        json.dump(current_profile, f)
    window.setProperty("%s.current_profile" % skin_id, current_profile)


def check_for_profile_change(skin_id):
    current_profile = getInfoLabel("System.ProfileName")
    saved_profile = window.getProperty("%s.current_profile" % skin_id)
    try:
        with open(PROFILE_PATH, "r") as f:
            saved_profile = json.load(f)
    except FileNotFoundError:
        saved_profile = None
    if not saved_profile:
        set_current_profile(skin_id, current_profile)
        return
    if saved_profile == current_profile:
        return
    from modules.cpath_maker import remake_all_cpaths

    set_current_profile(skin_id, current_profile)
    sleep(200)
    remake_all_cpaths(silent=True)
