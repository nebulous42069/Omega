import xbmc, xbmcaddon
import sqlite3
import xbmcvfs
import os
from libs.common import var
from sqlite3 import Error

#Account Manager TorBox
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_tb_token = accountmgr.getSetting("torbox.token")

###################### Connect to Database ######################
def create_conn(db_file):
    try:
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            xbmc.log(str(e), xbmc.LOGINFO)

        return conn
    except:
        xbmc.log('%s: TorBox_db Connect Failed!' % var.amgr, xbmc.LOGINFO)
        pass

######################### TorBox #########################
def connect_tb(conn, setting):
    try:
        # Update settings database
        tb_enabled = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        tb_token = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''

        cur = conn.cursor()
        cur.execute(tb_enabled, setting)
        cur.execute(tb_token, setting)
        conn.commit()
        cur.close()
    except:
        xbmc.log('%s: TorBox_db Auth Failed!' % var.amgr, xbmc.LOGINFO)
        pass

_GEARS_DB = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.gears/databases/settings.db')

def auth_gears_tb(token=None):
    from reauthorize.modules import sync_support
    token = your_tb_token if token is None else token
    pairs = [('tb.token', token), ('tb.enabled', 'true' if token else 'false')]
    conn = sqlite3.connect(_GEARS_DB, timeout=3)
    try:
        with conn:
            for key, value in pairs:
                if conn.execute('SELECT setting_value FROM settings WHERE setting_id=?', (key,)).fetchone() is None:
                    sync_support.warning('plugin.video.gears', 'incompatible; missing database setting: ' + key)
                    return False
            changed = False
            for key, value in pairs:
                cur = conn.execute('UPDATE settings SET setting_value=? WHERE setting_id=? AND setting_value IS NOT ?', (value, key, value))
                changed = changed or bool(cur.rowcount)
                if conn.execute('SELECT setting_value FROM settings WHERE setting_id=?', (key,)).fetchone() != (value,):
                    raise RuntimeError('Setting readback did not match')
            return changed
    finally:
        conn.close()
