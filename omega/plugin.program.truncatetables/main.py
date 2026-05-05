import sys
import os
import sqlite3
import xbmc
from xbmcaddon import Addon
from xbmcvfs import translatePath
from xbmcgui import Dialog

ADDON_NAME = Addon().getAddonInfo('name')
DB_FOLDER = translatePath('special://database')
ADDONS_DB = os.path.join(DB_FOLDER, 'Addons33.db')
OK_DIALOG = Dialog().ok
YES_NO_DIALOG = Dialog().yesno

def truncate_tables():
    success = False
    OK_DIALOG(ADDON_NAME, 'Make sure you backup Addons33.db before proceeding in case something gets screwed up,')
    verify = YES_NO_DIALOG(ADDON_NAME, 'Are you sure you wish to truncate tables?')
    if not verify:
        OK_DIALOG(ADDON_NAME, 'Cancelled')
        sys.exit()
    try:
        con = sqlite3.connect(ADDONS_DB)
        cursor = con.cursor()
        cursor.execute('DELETE FROM addonlinkrepo;',)
        cursor.execute('DELETE FROM addons;',)
        cursor.execute('DELETE FROM package;',)
        cursor.execute('DELETE FROM repo;',)
        cursor.execute('DELETE FROM update_rules;',)
        cursor.execute('DELETE FROM version;',)
        con.commit()
        OK_DIALOG(ADDON_NAME, 'Tables truncated succesfully!')
        success = True
    except sqlite3.Error as e:
        xbmc.log(f'{ADDON_NAME}: There was an error reading the database - {e}', xbmc.LOGINFO)
        OK_DIALOG(ADDON_NAME, 'Unable to truncate tables.  Check log.')
        return ''
    finally:
        try:
            if con:
                con.close()
        except UnboundLocalError as e:
            xbmc.log(f'{ADDON_NAME}: There was an error connecting to the database - {e}', xbmc.LOGINFO)
    try:
        con = sqlite3.connect(ADDONS_DB)
        cursor = con.cursor()
        cursor.execute('VACUUM;',)
        con.commit()
    except sqlite3.Error as e:
        xbmc.log(f"Failed to vacuum data from the sqlite table: {e}", xbmc.LOGINFO)
    finally:
        try:
            if con:
                con.close()
        except sqlite3.Error:
            pass
    if success is True:
        OK_DIALOG(ADDON_NAME, 'Kodi will now force close')
        os._exit(1)

if __name__ == '__main__':
    truncate_tables()
    