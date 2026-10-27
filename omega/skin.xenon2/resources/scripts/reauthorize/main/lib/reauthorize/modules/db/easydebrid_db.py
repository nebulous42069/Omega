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
your_ed_token = accountmgr.getSetting("easydebrid.token")

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
        xbmc.log('%s: Easydebrid_db Connect Failed!' % var.amgr, xbmc.LOGINFO)
        pass

######################### Easy Debrid #########################
def connect_ed(conn, setting):
    try:
        # Update settings database
        ed_enabled = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        ed_token = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''

        cur = conn.cursor()
        cur.execute(ed_enabled, setting)
        cur.execute(ed_token, setting)
        conn.commit()
        cur.close()
    except:
        xbmc.log('%s: Easydebrid_db Auth Failed!' % var.amgr, xbmc.LOGINFO)
        pass
