import os
import json
import shutil
import sqlite3
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import xml.etree.ElementTree as ET
from xml.dom import minidom

KEYMAP_LOCATION = "special://userdata/keymaps/"
POSSIBLE_KEYMAP_NAMES = ["gen.xml", "keyboard.xml", "keymap.xml"]


translatePath   = xbmcvfs.translatePath
dialog          = xbmcgui.Dialog()
addon_id        = xbmcaddon.Addon().getAddonInfo('id')
addon           = xbmcaddon.Addon(addon_id)
addon_info      = addon.getAddonInfo
addon_icon      = translatePath('special://home/addons/script.fentastic.helperr/resources/icon.png')
addon_path      = translatePath(addon_info('path'))
home            = translatePath('special://home/')
addon_data      = translatePath('special://profile/addon_data/')
addons_path     = os.path.join(home, 'addons/')
user_path       = os.path.join(home, 'userdata/')
resources       = os.path.join(addon_path, 'resources/')
packages        = os.path.join(addons_path, 'packages/')
db_path         = translatePath('special://database/')
packages        = os.path.join(addons_path, 'packages/')
thumbnails      = os.path.join(user_path, 'Thumbnails')
skin_path       = translatePath('special://skin/')

#Advanced Settings
advancedsettings_blank = os.path.join(resources, 'advancedsettings/advancedsettings.xml')
advancedsettings_xml =  os.path.join(user_path, 'advancedsettings.xml')

#Backup/Restore Variables
data_path = os.path.join(user_path, 'addon_data/')
skin_path = translatePath('special://skin/')
skin = ET.parse(os.path.join(skin_path, 'addon.xml'))
root = skin.getroot()
skin_id = root.attrib['id']


# -------------------------------------------------
# Helpers
# -------------------------------------------------  
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

        
# -------------------------------------------------
# Set background image
# -------------------------------------------------
def set_image():
    default_background_dir = "special://skin/extras/backgrounds/"

    # Retrieve last-used directory
    last_dir = xbmc.getInfoLabel("Skin.String(LastBackgroundDir)")

    # Fallback default
    if not last_dir:
        last_dir = default_background_dir

    # Ensure trailing slash
    if not last_dir.endswith(("/", "\\")):
        last_dir += "/"

    # Start browser in last_dir
    image_file = xbmcgui.Dialog().browse(
        2,
        "Choose Custom Background Image",
        "files",
        ".jpg|.jpeg|.png|.bmp",
        False,
        False,
        last_dir,
        False
    )

    if image_file and image_file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):

        translated_file = xbmcvfs.translatePath(image_file)
        translated_default_dir = xbmcvfs.translatePath(default_background_dir)

        # If chosen from the skin backgrounds folder, store special:// path
        # If chosen outside Kodi, store the OS path
        if translated_file.startswith(translated_default_dir):
            stored_path = image_file
            folder = image_file.rsplit("/", 1)[0] + "/"
            xbmc.executebuiltin(f"Skin.SetString(LastBackgroundDir,{folder})")
        else:
            stored_path = translated_file

        xbmc.executebuiltin(f"Skin.SetString(CustomBackground,{stored_path})")


# -------------------------------------------------
# Set home screen logo
# -------------------------------------------------
def set_image_logo():
    default_logo_dir = "special://skin/extras/logos/"

    # Retrieve last-used directory
    last_dir = xbmc.getInfoLabel("Skin.String(LastLogoDir)")

    # Fallback default
    if not last_dir:
        last_dir = default_logo_dir

    # Ensure trailing slash
    if not last_dir.endswith(("/", "\\")):
        last_dir += "/"

    # Start browser IN last_dir
    image_file = xbmcgui.Dialog().browse(
        2,
        "Choose Custom Home Screen Logo",
        "files",
        ".jpg|.jpeg|.png|.bmp",
        False,
        False,
        last_dir,
        False
    )

    if image_file and image_file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):

        translated_file = xbmcvfs.translatePath(image_file)
        translated_default_dir = xbmcvfs.translatePath(default_logo_dir)

        # If chosen from the skin logo folder, store special:// path
        # If chosen outside Kodi, store the OS path
        if translated_file.startswith(translated_default_dir):
            stored_path = image_file
            folder = image_file.rsplit("/", 1)[0] + "/"
            xbmc.executebuiltin(f"Skin.SetString(LastLogoDir,{folder})")
        else:
            stored_path = translated_file

        xbmc.executebuiltin(f"Skin.SetString(Customlogo,{stored_path})")


# -------------------------------------------------
# Fix black screen
# -------------------------------------------------           
def fix_black_screen():
    if xbmc.getCondVisibility("Skin.HasSetting(TrailerPlaying)"):
        xbmc.executebuiltin("Skin.ToggleSetting(TrailerPlaying)")


# -------------------------------------------------
# Force close Kodi
# -------------------------------------------------
def force_close():
    os._exit(1)

        
# -------------------------------------------------
# Keymap Backup Helpers
# -------------------------------------------------
def make_backup(keymap_path):
    backup_path = f"{keymap_path}.backup"
    if not xbmcvfs.exists(backup_path):
        xbmcvfs.copy(keymap_path, backup_path)

def restore_from_backup(keymap_path):
    backup_path = f"{keymap_path}.backup"
    if xbmcvfs.exists(backup_path):
        xbmcvfs.delete(keymap_path)
        xbmcvfs.rename(backup_path, keymap_path)


# -------------------------------------------------
# Keymaps
# -------------------------------------------------
def get_all_existing_keymap_paths():
    existing_paths = []
    for name in POSSIBLE_KEYMAP_NAMES:
        path = xbmcvfs.translatePath(f"special://profile/keymaps/{name}")
        if xbmcvfs.exists(path):
            existing_paths.append(path)
    return existing_paths

def create_new_keymap_file():
    default_keymap_name = "gen.xml"
    new_keymap_path = xbmcvfs.translatePath(f"{KEYMAP_LOCATION}{default_keymap_name}")
    root = ET.Element("keymap")
    tree = ET.ElementTree(root)
    tree.write(new_keymap_path)
    return new_keymap_path

def modify_keymap():
    keymap_paths = get_all_existing_keymap_paths()
    if not keymap_paths:
        new_keymap_path = create_new_keymap_file()
        keymap_paths = [new_keymap_path]
    setting_value = xbmc.getCondVisibility("Skin.HasSetting(Enable.OneClickTrailers)")
    for keymap_path in keymap_paths:
        if not setting_value:
            restore_from_backup(keymap_path)
            continue
        make_backup(keymap_path)
        tree = ET.parse(keymap_path)
        root = tree.getroot()

        def has_play_trailer_tag(tag):
            return tag.text == "RunScript(script.fentastic.helperr, mode=play_trailer)"

        play_pause_tags = root.findall(".//play_pause[@mod='longpress']")
        t_key_tags = root.findall(".//t")
        global_tag = root.find("global")
        if global_tag is None:
            global_tag = ET.SubElement(root, "global")
        keyboard_tag = global_tag.find("keyboard")
        if keyboard_tag is None:
            keyboard_tag = ET.SubElement(global_tag, "keyboard")
        if setting_value:
            if t_key_tags:
                t_key_tags[
                    0
                ].text = "RunScript(script.fentastic.helperr, mode=play_trailer)"
                for tag in t_key_tags[1:]:
                    keyboard_tag.remove(tag)
            else:
                t_key_tag = ET.SubElement(keyboard_tag, "t")
                t_key_tag.text = "RunScript(script.fentastic.helperr, mode=play_trailer)"
            if play_pause_tags:
                play_pause_tags[
                    0
                ].text = "RunScript(script.fentastic.helperr, mode=play_trailer)"
                for tag in play_pause_tags[1:]:
                    keyboard_tag.remove(tag)
            else:
                play_pause_tag = ET.SubElement(
                    keyboard_tag, "play_pause", mod="longpress"
                )
                play_pause_tag.text = (
                    "RunScript(script.fentastic.helperr, mode=play_trailer)"
                )
        else:
            for tag_list in [play_pause_tags, t_key_tags]:
                for tag in tag_list:
                    if has_play_trailer_tag(tag):
                        keyboard_tag.remove(tag)
        xml_string = ET.tostring(root, encoding="utf-8").decode("utf-8")
        pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")
        pretty_xml = "\n".join(
            [line for line in pretty_xml.split("\n") if line.strip()]
        )
        with xbmcvfs.File(keymap_path, "w") as xml_file:
            xml_file.write(pretty_xml)
    xbmc.executebuiltin("Action(reloadkeymaps)")


# -------------------------------------------------
# Color Map
# -------------------------------------------------
COLOR_OPTIONS = [
    ('Classic FENtastic', 'fentastic_classic'),
    ('FENtastic Plus', 'fentastic_plus'),
    ('Brown', 'brown'),
    ('Charcoal', 'charcoal'),
    ('Chartreuse', 'chartreuse'),
    ('Concrete', 'concrete'),
    ('Estuary', 'estuary'),
    ('Gold', 'gold'),
    ('Green', 'green'),
    ('Midnight', 'midnight'),
    ('Orange', 'orange'),
    ('Pink', 'pink'),
    ('Purple', 'purple'),
    ('Rose', 'rose'),
    ('Teal', 'teal'),
    ('Violet', 'violet')
]


def apply_saved_color(color_label=None, reload_skin=False):
    try:
        base_path = translatePath('special://home/addons/skin.fentasticp/')

        if not color_label:
            color_label = xbmc.getInfoLabel('Skin.String(currentskincolor)')

        if not color_label:
            return False

        color_folder = None

        for label, folder in COLOR_OPTIONS:
            if label == color_label:
                color_folder = folder
                break

        if not color_folder:
            xbmc.log(f'FENtastic: Saved colour not found -> {color_label}', xbmc.LOGERROR)
            return False

        src = os.path.join(base_path,'resources','optional_colors',color_folder,'defaults.xml')
        dst = os.path.join(base_path,'colors','defaults.xml')

        if not xbmcvfs.exists(src):
            xbmc.log(f'FENtastic: Saved colour file not found -> {src}',xbmc.LOGERROR)
            return False

        shutil.copyfile(src, dst)

        if reload_skin:
            xbmc.executebuiltin("ReloadSkin()")

        return True

    except Exception as e:
        xbmc.log(f'FENtastic: Failed to apply saved colour -> {e}',xbmc.LOGERROR)
        return False

    
# -------------------------------------------------
# Copy Colors
# -------------------------------------------------
def copy_colors():
    try:
        labels = [item[0] for item in COLOR_OPTIONS]
        index = dialog.select("Choose Colour Preset", labels)

        if index < 0:
                return False

        color_label, color_folder = COLOR_OPTIONS[index]

        xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,"%s")' % color_label)

        if not apply_saved_color(color_label=color_label, reload_skin=True):
                return False

        dialog.notification("FENtastic Plus",f"{color_label} colour applied",addon_icon,3000)
        return True

    except Exception as e:
            xbmc.log(f'FENtastic: Failed to copy optional colours -> {e}',xbmc.LOGERROR)
            return False


# -------------------------------------------------
# Copy Color Defaults
# -------------------------------------------------
def copy_fentastic_defaults(mode='fen'):
    try:
        if mode == 'fen':
                xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,Classic FENtastic)')
        elif mode == 'fenplus':
                xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,FENtastic Plus)')

        if not apply_saved_color(reload_skin=True):
                return False

        return True

    except Exception as e:
        xbmc.log(f'FENtastic: Failed to copy defaults -> {e}',xbmc.LOGERROR)
        return False


# ----------------------------------------------------------
# Classic FENtastic & FENtastic PLus Look & Feel Experience
# ----------------------------------------------------------
def choose_lookfeel():

    options = [
        '[COLOR gray]── Classic FENtastic ──[/COLOR]',
        'Classic FENtastic  -  [Keep Current Artwork]',
        'Classic FENtastic  -  [Default Artwork]',
        '',
        '[COLOR gray]── FENtastic Plus ──[/COLOR]',
        'FENtastic Plus  -  [Keep Current Artwork]',
        'FENtastic Plus  -  [Default Artwork]'
    ]

    # Map actual choices to indexes
    choice_map = {
        1: 0,  # Classic Custom
        2: 1,  # Classic Default
        5: 2,  # Plus Custom
        6: 3   # Plus Default
    }

    current = 1 if xbmc.getCondVisibility('Skin.HasSetting(ClassicFENtastic)') else 5

    while True:
        choice = xbmcgui.Dialog().select('Choose Look & Feel',options,preselect=current)

        if choice == -1:
            return

        if choice not in choice_map:
            continue

        choice = choice_map[choice]
        break

    if choice == 0:  # Classic Custom Artwork
        xbmc.executebuiltin('Skin.Reset(noiconmainmenu)')
        xbmc.executebuiltin('Skin.SetBool(NoHighlightMainMenu)')
        xbmc.executebuiltin('Skin.SetBool(noiconsilhouettes)')
        xbmc.executebuiltin('Skin.SetBool(no_slide_animations)')
        xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,Classic FENtastic)')
        xbmc.executebuiltin('RunScript(script.fentastic.helperr,mode=set_fen_dflts)')
        xbmc.executebuiltin('Skin.SetBool(ClassicFENtastic)')

    elif choice == 1:  # Classic Default Artwork
        xbmc.executebuiltin('Skin.SetString(custombackground,special://skin/extras/backgrounds/redblur.jpg)')
        xbmc.executebuiltin('Skin.Reset(customlogo)')
        xbmc.executebuiltin('Skin.Reset(noiconmainmenu)')
        xbmc.executebuiltin('Skin.SetBool(NoHighlightMainMenu)')
        xbmc.executebuiltin('Skin.SetBool(noiconsilhouettes)')
        xbmc.executebuiltin('Skin.SetBool(no_slide_animations)')
        xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,Classic FENtastic)')
        xbmc.executebuiltin('RunScript(script.fentastic.helperr,mode=set_fen_dflts)')
        xbmc.executebuiltin('Skin.SetBool(ClassicFENtastic)')

    elif choice == 2:  # Plus Custom Artwork
        xbmc.executebuiltin('Skin.SetBool(noiconmainmenu)')
        xbmc.executebuiltin('Skin.Reset(NoHighlightMainMenu)')
        xbmc.executebuiltin('Skin.Reset(no_slide_animations)')
        xbmc.executebuiltin('Skin.SetBool(noiconsilhouettes)')
        xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,FENtastic Plus)')
        xbmc.executebuiltin('RunScript(script.fentastic.helperr,mode=set_fenplus_dflts)')
        xbmc.executebuiltin('Skin.Reset(ClassicFENtastic)')

    elif choice == 3:  # Plus Default Artwork
        xbmc.executebuiltin('Skin.SetString(custombackground,special://skin/extras/backgrounds/redblur.jpg)')
        xbmc.executebuiltin('Skin.SetString(customlogo,special://skin/extras/logos/fentastic.png)')
        xbmc.executebuiltin('Skin.Reset(no_slide_animations)')
        xbmc.executebuiltin('Skin.Reset(NoHighlightMainMenu)')
        xbmc.executebuiltin('Skin.SetBool(noiconmainmenu)')
        xbmc.executebuiltin('Skin.SetBool(noiconsilhouettes)')
        xbmc.executebuiltin('Skin.SetString(CurrentSkinColor,FENtastic Plus)')
        xbmc.executebuiltin('RunScript(script.fentastic.helperr,mode=set_fenplus_dflts)')
        xbmc.executebuiltin('Skin.Reset(ClassicFENtastic)')

        
# -------------------------------------------------
# Tools Menu
# -------------------------------------------------
def get_latest_db(db_type: str) -> str:
    highest_number = -1
    highest_file = None
    for file in os.listdir(db_path):
        if file.startswith(db_type) and file.endswith('.db'):
            try:
                number = int(file[len(db_type):file.index('.db')])
                if number > highest_number:
                    highest_number = number
                    highest_file = file
            except ValueError:
                pass
    if highest_file is not None:
        return os.path.join(db_path, highest_file)

textures_db = get_latest_db('Textures')

#Purge database
def purge_db(db):
    if os.path.exists(db):
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
        except Exception as e:
            xbmc.log("DB Connection Error: %s" % str(e), xbmc.LOGDEBUG)
            return False
    else: 
        xbmc.log('%s not found.' % db, xbmc.LOGINFO)
        return False
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    for table in cur.fetchall():
        if table[0] == 'version': 
            xbmc.log('Data from table `%s` skipped.' % table[0], xbmc.LOGDEBUG)
        else:
            try:
                cur.execute("DELETE FROM %s" % table[0])
                conn.commit()
                xbmc.log('Data from table `%s` cleared.' % table[0], xbmc.LOGDEBUG)
            except Exception as e:
                xbmc.log("DB Remove Table `%s` Error: %s" % (table[0], str(e)), xbmc.LOGERROR)
    conn.execute('VACUUM')
    conn.close()
    xbmc.log('%s DB Purging Complete.' % db, xbmc.LOGINFO)

#Get size of directory
def get_dir_size(dir_path):
    
    # Get the uncompressed size of a directory
    size = 0
    size_mb = 0
    for path, dirs, files in os.walk(dir_path):
        for name in dirs:
            if name in ['cache', 'temp']:
                pass
        for f in files:
            fp = os.path.join(path, f)
            try:
                size += os.path.getsize(fp)
            except OSError as e:
                xbmc.log(f'Error reading file while getting directory size - {e}', xbmc.LOGINFO)
    size_mb = f"{int(size) / float(1 << 20):.2f}"
    return size_mb

#Kodi Maintenance Stats
packagesize = get_dir_size(packages)
thumbnailsize = get_dir_size(thumbnails)
thumbs = round(float(get_dir_size(thumbnails)), 2)
cleanup = round(float(packagesize) + float(thumbnailsize), 2)

#Clear thumbnails
def clear_thumbnails():
    yes_clear = dialog.yesno('Clear Thumbnails', f'Total Size: [COLOR gold]{thumbnailsize}[/COLOR]\n\nWould you like to clear thumbnails?', nolabel='No', yeslabel='Yes')  # Are you sure?
    if not yes_clear:
        quit()
    else:
        try:
            if os.path.exists(os.path.join(user_path, 'Thumbnails')):
                shutil.rmtree(os.path.join(user_path, 'Thumbnails'))
        except Exception as e:
                xbmc.log('Failed to delete %s. Reason: %s' % (os.path.join(user_path, 'Thumbnails'), e), xbmc.LOGINFO)
                return
        try:
            purge_db(textures_db)
        except:
            xbmc.log('%s DB Purging Failed.' % textures_db, xbmc.LOGINFO)
        xbmc.sleep(1000)
        xbmcgui.Dialog().ok('FENtastic Plus', 'Thumbnails Cleared!\n\nTo refresh thumbs, Kodi will now force close.')  # Thumbnails Deleted
        os._exit(1)

#Clear packages
def clear_packages():
    yes_clear = dialog.yesno('Clear Packages', f'Total Size: [COLOR gold]{packagesize}[/COLOR]\n\nWould you like to clear packages?', nolabel='No', yeslabel='Yes')  # Are you sure?
    if not yes_clear:
        quit()
    else:
        file_count = len([name for name in os.listdir(packages)])
        for filename in os.listdir(packages):
            file_path = os.path.join(packages, filename)
            try:
                   if os.path.isfile(file_path) or os.path.islink(file_path):
                       os.unlink(file_path)
                   elif os.path.isdir(file_path):
                       shutil.rmtree(file_path)
            except Exception as e:
                xbmc.log('Failed to delete %s. Reason: %s' % (file_path, e), xbmc.LOGINFO)
        xbmcgui.Dialog().ok('FENtastic Plus', f'[COLOR gold]{str(file_count)}[/COLOR] Packages Cleared!')  # Packages Deleted

#Set video cache settings    
def advanced_set(buffer, ram, read):
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"filecache.buffermode","value":%s},"id":1}' %(buffer))
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"filecache.memorysize","value":%s},"id":1}' %(ram))
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"filecache.readfactor","value":%s},"id":1}' %(read))
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"filecache.chunksize","value":131072},"id":1}')
    xbmc.executebuiltin('ActivateWindowAndFocus(servicesettings), True')
    xbmc.executebuiltin('Action(Back)')

def advanced_settings():
    selection = xbmcgui.Dialog().select('Select the Ram Size of your device', ['1GB Devices (E.g. 1st-3rd gen Firestick/Firestick Lite)','1.5GB Devices (E.g. 4k Firestick)','2GB+ Devices (E.g. Shield Pro/Shield Tube/FireTV Cube)','Default (Reset to Default)'])  # Select Ram Size
    if selection==0:
        advanced_set('2', '128', '0')
    elif selection==1:
        advanced_set('2', '192', '0')
    elif selection==2:
        advanced_set('2', '256', '0')
    elif selection==3:
        advanced_set('4', '20', '400')
    else:
        return
    xbmc.sleep(1000)
    xbmcgui.Dialog().notification('FENtastic Plus', 'Video Cache Settings updated!', addon_icon, 3000)

#Pretty print for xml files
def _pretty_print(current, parent=None, index=-1, depth=0):
    for i, node in enumerate(current):
        _pretty_print(node, current, i, depth + 1)
    if parent is not None:
        if index == 0:
            parent.text = '\n' + ('\t' * depth)
        else:
            parent[index - 1].tail = '\n' + ('\t' * depth)
        if index == len(parent) - 1:
            current.tail = '\n' + ('\t' * (depth - 1))

#Enable/Disable kodi splash            
def splash(on_off):
    if not xbmcvfs.exists(advancedsettings_xml): #If advacnedsettings.xml does not exist copy blank file
        shutil.copyfile(advancedsettings_blank, advancedsettings_xml)
    if xbmcvfs.exists(advancedsettings_xml):
        tree = ET.parse(advancedsettings_xml) #Parse Advancedsettings.xml
        root = tree.getroot()
        item = root.find('splash')
        if item is None: #If splash does not exist create element
            element = ET.Element('advancedsettings')
            sub_element = ET.SubElement(element, 'splash')
            sub_element.text = on_off
            root.insert(0, sub_element)
            _pretty_print(root)
            tree = ET.ElementTree(root)
            tree.write(advancedsettings_xml) #Write settings to advancedsettings.xml
        else:
            for splash in root.iter('splash'): #If splash element exists write setting
                    splash.text = on_off
                    tree = ET.ElementTree(root)
                    tree.write(advancedsettings_xml)
    
#Focus addon settings
def openAddonSettings(addonId, id1=None, id2=None):
    xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonId)
    if id1 != None and id2 != None:
        xbmc.executebuiltin('SetFocus(%i)' % (id1))
    if id2 != None:
        xbmc.executebuiltin('SetFocus(%i)' % (id2)) 

def tmdbh_mdblist_api():
        openAddonSettings('plugin.video.themoviedb.helper', -196, -175)
        
def rurl_settings_rd():
        openAddonSettings('script.module.resolveurl', -198, -162)

def rurl_settings_pm():
        openAddonSettings('script.module.resolveurl', -198, -173)

def rurl_settings_ad():
        openAddonSettings('script.module.resolveurl', -199, -174)
