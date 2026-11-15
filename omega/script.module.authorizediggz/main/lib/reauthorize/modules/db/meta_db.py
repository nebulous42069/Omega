import xbmc, xbmcaddon
import sqlite3
import xbmcvfs
import os
from libs.common import var
from sqlite3 import Error

#Account Manager Metadata
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_omdb_api = accountmgr.getSetting("omdb.api.key")
your_tmdb_api = accountmgr.getSetting("tmdb.api.key")

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
        xbmc.log('%s: Meta_db Connect Failed!' % var.amgr, xbmc.LOGINFO)
        pass

########################## Write OMDb Metadata Setting #########################
def connect_omdb(conn, setting):
    try:
        # Update settings database
        omdb_api = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        
        cur = conn.cursor()
        cur.execute(omdb_api, setting)
        conn.commit()
        cur.close()
    except:
        xbmc.log('%s: Meta_db OMDb Auth Failed!' % var.amgr, xbmc.LOGINFO)
        pass

########################## Write TMDb Metadata Setting #########################
def connect_tmdb(conn, setting):
    try:
        # Update settings database
        tmdb_api = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        
        cur = conn.cursor()
        cur.execute(tmdb_api, setting)
        conn.commit()
        cur.close()
    except:
        xbmc.log('%s: Meta_db TMDb Auth Failed!' % var.amgr, xbmc.LOGINFO)
        pass
    
    
#################### Auth Gears OMDb Metadata ###################
def auth_gears_omdb():
    try:
        conn = create_conn(var.gears_settings_db)
        with conn:
            connect_omdb(conn, (your_omdb_api, 'omdb_api'))
    except:
        xbmc.log('%s: Meta_db OMDb Gears Failed!' % var.amgr, xbmc.LOGINFO)
        pass

#################### Auth Gears TMDb Metadata ###################
def auth_gears_tmdb():
    try:
        conn = create_conn(var.gears_settings_db)
        with conn:
            connect_tmdb(conn, (your_tmdb_api, 'tmdb_api'))
    except:
        xbmc.log('%s: Meta_db TMDb Gears Failed!' % var.amgr, xbmc.LOGINFO)
        pass


#################### Auth Affenity Metadata ###################
def auth_affen_meta():
    try:
        conn = create_conn(var.affen_settings_db)
        with conn:
            connect_omdb(conn, (your_omdb_api, 'omdb_api'))
    except:
        xbmc.log('%s: Meta_db Affenity Failed!' % var.amgr, xbmc.LOGINFO)
        pass


