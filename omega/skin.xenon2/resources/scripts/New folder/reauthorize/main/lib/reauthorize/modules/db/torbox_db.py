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

def auth_gears_tb():
    try:
        conn = create_conn(_GEARS_DB)
        with conn:
            connect_tb(conn, ('true', 'tb.enabled'))
            connect_tb(conn, (your_tb_token, 'tb.token'))
    except:
        xbmc.log('%s: TorBox_db Gears Failed!' % var.amgr, xbmc.LOGINFO)
        pass
