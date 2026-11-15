import xbmc, xbmcaddon
import sqlite3
import xbmcvfs
import os
from libs.common import var
from sqlite3 import Error

#Account Manager Trakt
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_clientid = var.client_am
your_secret = var.secret_am
your_token = accountmgr.getSetting("trakt.token")
your_username = accountmgr.getSetting("trakt.username")           
your_refresh = accountmgr.getSetting("trakt.refresh")
your_expires = accountmgr.getSetting("trakt.expires")

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
        xbmc.log('%s: Trakt_db Connect Failed!' % var.amgr, xbmc.LOGINFO)
        pass


######################### Trakt #########################
def connect_trakt(conn, setting):
    try:
        # Update settings database
        trakt_client = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_secret = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_token = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_user = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_refresh = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_expires = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_watched_indicators = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        trakt_watched_indicators_name = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''

        cur = conn.cursor()
        cur.execute(trakt_client, setting)
        cur.execute(trakt_secret, setting)
        cur.execute(trakt_token, setting)
        cur.execute(trakt_user, setting)
        cur.execute(trakt_refresh, setting)
        cur.execute(trakt_expires, setting)
        cur.execute(trakt_watched_indicators, setting)
        cur.execute(trakt_watched_indicators_name, setting)
        conn.commit()
        cur.close()
    except:
        xbmc.log('%s: Trakt_db Failed!' % var.amgr, xbmc.LOGINFO)
        pass


_GEARS_DB = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.gears/databases/settings.db')

def auth_gears_trakt():
    try:
        conn = create_conn(_GEARS_DB)
        with conn:
            connect_trakt(conn, (your_clientid, 'trakt.client'))
            connect_trakt(conn, (your_secret, 'trakt.secret'))
            connect_trakt(conn, (your_token, 'trakt.token'))
            connect_trakt(conn, (your_username, 'trakt.user'))
            connect_trakt(conn, (your_refresh, 'trakt.refresh'))
            connect_trakt(conn, (your_expires, 'trakt.expires'))
            connect_trakt(conn, (1, 'watched_indicators'))
            connect_trakt(conn, ('Trakt', 'watched_indicators_name'))
    except:
        xbmc.log('%s: Trakt_db Gears Failed!' % var.amgr, xbmc.LOGINFO)
        pass



