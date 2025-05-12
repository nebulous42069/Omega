import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import shutil
import urllib.request

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = ADDON.getAddonInfo('path')
USERDATA_PATH = xbmcvfs.translatePath("special://userdata/")
PLAYERCORE_FACTORY = os.path.join(USERDATA_PATH, "playercorefactory.xml")
VLC_ANDROID_XML = os.path.join(ADDON_PATH, "playercorefactory-vlc-android.xml")
VLC_LINUX_XML = os.path.join(ADDON_PATH, "playercorefactory-vlc-linux.xml")
VLC_WINDOWS_XML = os.path.join(ADDON_PATH, "playercorefactory-vlc-windows.xml")
VLC_MACOS_XML = os.path.join(ADDON_PATH, "playercorefactory-vlc-macos.xml")
CUSTOM_XML = os.path.join(ADDON_PATH, "custom_playercorefactory.xml")

# Funzione per semplificare la traduzione
def getLocalizedString(id):
    return ADDON.getLocalizedString(id)

def is_kodi_sandboxed():
    """
    Verifica se Kodi è in esecuzione in un ambiente sandbox (Flatpak o Snap)
    """
    # Verifica se Kodi è in esecuzione come Flatpak
    if os.path.exists("/.flatpak-info"):
        # Verifica se questo file è accessibile dal processo Kodi
        try:
            with open("/.flatpak-info", "r") as f:
                content = f.read()
                if "Application" in content:
                    return True, "Flatpak"
        except:
            pass
    
    # Verifica se Kodi è in esecuzione come Snap
    if os.environ.get("SNAP"):
        # Se la variabile SNAP è definita, siamo in un'applicazione Snap
        if "kodi" in os.environ.get("SNAP", "").lower():
            return True, "Snap"
    
    # Altro modo per verificare Snap (se la variabile SNAP_NAME è definita)
    if os.environ.get("SNAP_NAME"):
        if "kodi" in os.environ.get("SNAP_NAME", "").lower():
            return True, "Snap"
    
    return False, None

def is_app_installed_android(package_name):
    """
    Verifica se un'app è installata su Android utilizzando un Intent.
    """
    try:
        # Prova ad avviare l'app tramite Intent
        intent = f"android.intent.action.MAIN;android.intent.category.LAUNCHER;package={package_name}"
        xbmc.executebuiltin(f"StartAndroidActivity({intent})")
        # Se l'Intent ha successo, l'app è installata
        return True
    except:
        # Se l'Intent fallisce, l'app non è installata
        return False

def is_player_installed(player):
    """
    Verifica se il player specificato è installato sul dispositivo.
    """
    if player == "VLC":
        # Prima verifica se Kodi è in un ambiente sandbox
        is_sandbox, sandbox_type = is_kodi_sandboxed()
        
        if is_sandbox:
            xbmc.log(f"Kodi è in esecuzione in un ambiente {sandbox_type}, impossibile verificare VLC con certezza", xbmc.LOGINFO)
            # In ambiente sandbox, assumiamo che VLC sia installato
            return True
        
        # Se non siamo in un ambiente sandbox, procediamo con la verifica normale
        if xbmc.getCondVisibility("System.Platform.Android"):
            # Verifica se VLC è installata su Android
            return is_app_installed_android("org.videolan.vlc")
        elif xbmc.getCondVisibility("System.Platform.Windows"):
            # Verifica se VLC è installato su Windows
            vlc_paths = [
                "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
                "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe"
            ]
            return any(os.path.isfile(path) for path in vlc_paths)
        elif xbmc.getCondVisibility("System.Platform.OSX") or xbmc.getCondVisibility("System.Platform.Darwin"):
            # Percorsi comuni di VLC su macOS
            macos_vlc_paths = [
                "/Applications/VLC.app/Contents/MacOS/VLC",
                os.path.expanduser("~/Applications/VLC.app/Contents/MacOS/VLC")
            ]
            return any(os.path.isfile(path) for path in macos_vlc_paths)
        elif xbmc.getCondVisibility("System.Platform.Linux"):
            # Verifica se VLC è installato su Linux
            linux_vlc_paths = [
                "/usr/bin/vlc",
                "/usr/local/bin/vlc",
                "/snap/bin/vlc",
                "/var/lib/flatpak/exports/bin/vlc",
                "/var/lib/flatpak/exports/bin/org.videolan.VLC",
                os.path.expanduser("~/.local/share/flatpak/exports/bin/org.videolan.VLC"),
                os.path.expanduser("~/.local/bin/vlc"),
                os.path.expanduser("~/bin/vlc"),
                "/opt/vlc/bin/vlc"
            ]
            return any(os.path.isfile(path) for path in linux_vlc_paths)
    return False

def get_actual_player():
    if not os.path.exists(PLAYERCORE_FACTORY):
        return "Kodi"
    
    with open(PLAYERCORE_FACTORY, "r") as f:
        content = f.read()
        if "org.videolan.vlc" in content:
            return "VLC (Android)"
        elif "vlc.exe" in content:
            return "VLC (Windows)"
        elif "/usr/bin/vlc" in content or "/snap/bin/vlc" in content or "/var/lib/flatpak/exports/bin/vlc" in content:
            return "VLC (Linux)"
        elif "/Applications/VLC.app" in content:
            return "VLC (macOS)"
        else:
            return getLocalizedString(30034)
    
    return "Kodi"

def set_player(player):
    if player == "VLC":
        if not is_player_installed("VLC"):
            xbmcgui.Dialog().ok(getLocalizedString(30001), getLocalizedString(30002))
            return
        
        # Determine the OS and select the appropriate XML file
        if xbmc.getCondVisibility("System.Platform.Android"):
            src = VLC_ANDROID_XML
        elif xbmc.getCondVisibility("System.Platform.Windows"):
            src = VLC_WINDOWS_XML
        elif xbmc.getCondVisibility("System.Platform.OSX") or xbmc.getCondVisibility("System.Platform.Darwin"):
            src = VLC_MACOS_XML
        elif xbmc.getCondVisibility("System.Platform.Linux"):
            src = VLC_LINUX_XML
        else:
            xbmcgui.Dialog().ok(getLocalizedString(30001), getLocalizedString(30003))
            return
    elif player == "Custom Player":
        # Se l'utente ha scelto un player personalizzato, usa il file custom
        src = CUSTOM_XML
    elif player == "Local Custom Player":
        # Se l'utente ha scelto un player personalizzato locale, usa il file selezionato
        src = CUSTOM_XML
    else:
        if os.path.exists(PLAYERCORE_FACTORY):
            os.remove(PLAYERCORE_FACTORY)
        xbmcgui.Dialog().notification(getLocalizedString(30000), getLocalizedString(30004), xbmcgui.NOTIFICATION_INFO)
        xbmcgui.Dialog().ok(getLocalizedString(30005), getLocalizedString(30006))
        return

    if os.path.exists(PLAYERCORE_FACTORY):
        os.remove(PLAYERCORE_FACTORY)
    shutil.copy(src, PLAYERCORE_FACTORY)
    xbmcgui.Dialog().notification(getLocalizedString(30000), getLocalizedString(30007) % player, xbmcgui.NOTIFICATION_INFO)
    xbmcgui.Dialog().ok(getLocalizedString(30005), getLocalizedString(30006))

def download_xml_from_url(url):
    """
    Downloads an XML file from the specified URL and saves it to the custom playercorefactory.xml file.
    
    Returns:
        bool: True if download and save was successful, False otherwise
    """
    dialog = xbmcgui.Dialog()
    try:
        # Show progress dialog
        dp = xbmcgui.DialogProgress()
        dp.create(getLocalizedString(30008), getLocalizedString(30009) % url)
        
        # Create a request with a standard User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        
        # Download the file with proper headers
        response = urllib.request.urlopen(req)
        xml_content = response.read().decode('utf-8')
        
        dp.close()
        
        # Validate that the content looks like XML
        if not xml_content.strip().startswith("<"):
            dialog.ok(getLocalizedString(30010), getLocalizedString(30011))
            return False
        
        # Save the XML to custom file
        with open(CUSTOM_XML, "w") as f:
            f.write(xml_content)
        
        dialog.notification(getLocalizedString(30000), getLocalizedString(30012), xbmcgui.NOTIFICATION_INFO)
        return True
        
    except urllib.error.HTTPError as e:
        error_message = getLocalizedString(30013) % (e.code, e.reason)
        if e.code == 403:
            error_message += "\n" + getLocalizedString(30014)
        dialog.ok(getLocalizedString(30015), error_message)
        return False
    except urllib.error.URLError as e:
        dialog.ok(getLocalizedString(30015), getLocalizedString(30016) % str(e.reason))
        return False
    except Exception as e:
        dialog.ok(getLocalizedString(30015), getLocalizedString(30017) % str(e))
        return False

def browse_for_local_xml():
    """
    Opens a file browser to select a local playercorefactory.xml file.
    """
    dialog = xbmcgui.Dialog()
    
    # Browse for the XML file
    xml_file = dialog.browse(1, getLocalizedString(30029), 'files', '.xml', False, False)
    
    if xml_file and xml_file != "":
        try:
            # Validate that the file exists and is an XML
            if not os.path.isfile(xml_file):
                dialog.ok(getLocalizedString(30001), getLocalizedString(30030))
                return False
            
            # Read the content of the file
            with open(xml_file, "r") as f:
                xml_content = f.read()
            
            # Validate that the content looks like XML
            if not xml_content.strip().startswith("<"):
                dialog.ok(getLocalizedString(30010), getLocalizedString(30011))
                return False
            
            # Save the XML to custom file
            with open(CUSTOM_XML, "w") as f:
                f.write(xml_content)
            
            dialog.notification(getLocalizedString(30000), getLocalizedString(30031), xbmcgui.NOTIFICATION_INFO)
            
            # Ask user if they want to apply it immediately
            if dialog.yesno(getLocalizedString(30021), getLocalizedString(30022)):
                set_player("Local Custom Player")
            else:
                dialog.notification(getLocalizedString(30000), getLocalizedString(30023), xbmcgui.NOTIFICATION_INFO)
            
            return True
        except Exception as e:
            dialog.ok(getLocalizedString(30001), getLocalizedString(30032) % str(e))
            return False
    
    return False

def show_custom_xml_dialog():
    """
    Shows a dialog for entering URL to download a custom playercorefactory.xml file.
    """
    dialog = xbmcgui.Dialog()
    
    # Ask user for URL
    keyboard = xbmc.Keyboard("https://", getLocalizedString(30018))
    keyboard.doModal()
    
    if keyboard.isConfirmed():
        url = keyboard.getText()
        
        # Validate URL
        if not url.startswith("http"):
            dialog.ok(getLocalizedString(30019), getLocalizedString(30020))
            return
        
        # Try to download the XML
        if download_xml_from_url(url):
            # Ask user if they want to apply it immediately
            if dialog.yesno(getLocalizedString(30021), getLocalizedString(30022)):
                set_player("Custom Player")
            else:
                dialog.notification(getLocalizedString(30000), getLocalizedString(30023), xbmcgui.NOTIFICATION_INFO)

def show_menu():
    # Debug per verificare l'ambiente
    is_sandbox, sandbox_type = is_kodi_sandboxed()
    if is_sandbox:
        xbmc.log(f"Kodi è in esecuzione in un ambiente {sandbox_type}", xbmc.LOGINFO)
    
    actual_player = get_actual_player()
    dialog = xbmcgui.Dialog()
    options = [
        getLocalizedString(30024),  # "Use VLC external player"
        getLocalizedString(30025),  # "Remote custom playercorefactory.xml"
        getLocalizedString(30033),  # "Local custom playercorefactory.xml"
        getLocalizedString(30026),  # "Use Kodi internal player"
        "",
        getLocalizedString(30027) % actual_player,  # "Actual player: %s"
        "",  # Riga vuota
        getLocalizedString(30028)  # "Telegram: @ItalianSpaghettiGeeks"
    ]
    choice = dialog.select(getLocalizedString(30000), options)
    if choice == 0:
        set_player("VLC")
    elif choice == 1:
        show_custom_xml_dialog()
    elif choice == 2:
        browse_for_local_xml()
    elif choice == 3:
        set_player("Kodi")

if __name__ == "__main__":
    show_menu()