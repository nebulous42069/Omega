import xbmc, xbmcaddon
import sqlite3
import xbmcvfs
import os
from libs.common import var
from sqlite3 import Error

#Account Manager Easynews
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_easy_user = accountmgr.getSetting("easynews.username")
your_easy_pass = accountmgr.getSetting("easynews.password")

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
        xbmc.log('%s: Ext_db Connect Failed!' % var.amgr, xbmc.LOGINFO)
        pass

######################### External Provider #########################
def connect_ext(conn, setting):
    try:
        # Update settings database
        ext_enable = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        ext_user = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        ext_pass = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''

        cur = conn.cursor()
        cur.execute(ext_enable, setting)
        cur.execute(ext_user, setting)
        cur.execute(ext_pass, setting)
        conn.commit()
        cur.close()
    except:
        xbmc.log('%s: Ext_db Auth Failed!' % var.amgr, xbmc.LOGINFO)
        pass

