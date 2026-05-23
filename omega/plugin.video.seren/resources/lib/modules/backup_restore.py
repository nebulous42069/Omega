"""
Backup/Restore Module

Exports and imports Seren settings and user-configurable databases
to/from a user-selected folder. Backs up:
  - settings.xml (all addon settings including debrid auth tokens)
  - undesirables.db (user keyword blocklist)
  - titleSubs.db (title substitution mappings)
  - providers/ folder (installed scraper packages)

The backup is a single .zip file with a timestamp filename.
Restore unpacks the zip back into the addon userdata folder.
"""

import datetime
import os
import shutil
import zipfile

import xbmcgui
import xbmcvfs

from resources.lib.modules.globals import g


# Files relative to ADDON_USERDATA_PATH to include in backup
BACKUP_FILES = [
    "settings.xml",
    "undesirables.db",
    "providerPerf.db",
    "titleSubs.db",
]

# Folders relative to ADDON_USERDATA_PATH to include in backup
BACKUP_FOLDERS = [
    "providers",
]


def backup_settings():
    """
    Export settings and databases to a user-selected folder as a timestamped zip.
    """
    # Ask user for destination folder
    dest_folder = xbmcgui.Dialog().browseSingle(
        0,  # ShowAndGetDirectory
        f"{g.ADDON_NAME}: Select Backup Location",
        "files",
        "",
        False,
        False,
    )
    if not dest_folder:
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"seren_backup_{timestamp}.zip"
    zip_path = os.path.join(xbmcvfs.translatePath(dest_folder), zip_name)
    userdata = xbmcvfs.translatePath(g.ADDON_USERDATA_PATH)

    try:
        file_count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Backup individual files
            for filename in BACKUP_FILES:
                filepath = os.path.join(userdata, filename)
                if os.path.isfile(filepath):
                    zf.write(filepath, filename)
                    file_count += 1
                    g.log(f"Backup: Added {filename}", "info")

            # Backup folders recursively
            for folder_name in BACKUP_FOLDERS:
                folder_path = os.path.join(userdata, folder_name)
                if os.path.isdir(folder_path):
                    for root, dirs, files in os.walk(folder_path):
                        for f in files:
                            abs_path = os.path.join(root, f)
                            arc_name = os.path.relpath(abs_path, userdata)
                            zf.write(abs_path, arc_name)
                            file_count += 1
                    g.log(f"Backup: Added folder {folder_name}/", "info")

        g.log(f"Backup: Created {zip_path} ({file_count} files)", "info")
        xbmcgui.Dialog().notification(
            g.ADDON_NAME,
            f"Backup saved ({file_count} files)",
            time=4000,
        )
    except Exception as e:
        g.log(f"Backup failed: {e}", "error")
        xbmcgui.Dialog().notification(
            g.ADDON_NAME,
            "Backup failed — check log",
            time=4000,
        )


def restore_settings():
    """
    Import settings and databases from a previously created backup zip.
    """
    # Ask user to select the backup zip file
    zip_path = xbmcgui.Dialog().browseSingle(
        1,  # ShowAndGetFile
        f"{g.ADDON_NAME}: Select Backup File",
        "files",
        ".zip",
        False,
        False,
    )
    if not zip_path:
        return

    zip_path = xbmcvfs.translatePath(zip_path)

    if not os.path.isfile(zip_path) or not zipfile.is_zipfile(zip_path):
        xbmcgui.Dialog().notification(
            g.ADDON_NAME,
            "Invalid backup file",
            time=4000,
        )
        return

    # Confirm with user
    confirm = xbmcgui.Dialog().yesno(
        g.ADDON_NAME,
        "Restore will overwrite current settings and databases. Continue?",
    )
    if not confirm:
        return

    userdata = xbmcvfs.translatePath(g.ADDON_USERDATA_PATH)

    try:
        file_count = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Validate zip contents — only extract known safe paths
            for member in zf.namelist():
                # Security: prevent path traversal
                if member.startswith("/") or ".." in member:
                    g.log(f"Restore: Skipping unsafe path '{member}'", "warning")
                    continue

                # Only restore files we know about
                is_valid = False
                if member in BACKUP_FILES:
                    is_valid = True
                else:
                    for folder in BACKUP_FOLDERS:
                        if member.startswith(f"{folder}/"):
                            is_valid = True
                            break

                if is_valid:
                    dest_path = os.path.join(userdata, member)
                    dest_dir = os.path.dirname(dest_path)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    file_count += 1
                    g.log(f"Restore: Extracted {member}", "info")
                else:
                    g.log(f"Restore: Skipping unknown file '{member}'", "info")

        g.log(f"Restore: Completed ({file_count} files)", "info")

        # Reload settings cache so changes take effect
        g._init_cache()
        g.SETTINGS_CACHE = None
        g.__init__()

        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            f"Restore complete ({file_count} files). Please restart Kodi for all changes to take effect.",
        )
    except Exception as e:
        g.log(f"Restore failed: {e}", "error")
        xbmcgui.Dialog().notification(
            g.ADDON_NAME,
            "Restore failed — check log",
            time=4000,
        )
