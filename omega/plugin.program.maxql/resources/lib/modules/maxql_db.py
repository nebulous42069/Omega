import xbmc, xbmcaddon
import sqlite3
import xbmcvfs
import os
from sqlite3 import Error

translatePath = xbmcvfs.translatePath
home = translatePath('special://home/')
user_path = os.path.join(home, 'userdata/')
fen_lt_path = os.path.join(user_path, 'addon_data/plugin.video.fenlight/databases')
fenlt_settings_db = os.path.join(fen_lt_path,'settings.db')
affen_lt_path = os.path.join(user_path, 'addon_data/plugin.video.affenity/databases')
affen_settings_db = os.path.join(affen_lt_path,'settings.db')

#Connect to database
def create_conn(db_file):
    try:
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            print(e)

        return conn
    except:
        pass


#One Setting
def connect_one(conn, setting):
    try:
        # Update settings database
        setting_enable = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''

        cur = conn.cursor()
        cur.execute(setting_enable, setting)
        conn.commit()
        cur.close()
    except:
        pass
    
#Two Settings
def connect_two(conn, setting):
    try:
        # Update settings database
        setting_one = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        setting_two = ''' UPDATE settings
                  SET setting_value = ?
                  WHERE setting_id = ?'''
        
        cur = conn.cursor()
        cur.execute(setting_one, setting)
        cur.execute(setting_two, setting)
        conn.commit()
        cur.close()
    except:
        pass


###############################################################
###############################################################   
###############################################################
########################## Fen Light ##########################   
#Enable 4K
def enable_fenlt_4k():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_two(conn, ('SD, 720p, 1080p, 4K', 'results_quality_movie'))
            connect_two(conn, ('SD, 720p, 1080p, 4K', 'results_quality_episode'))
    except:
        pass
    
#Disable 3D
def enable_fenlt_1080p():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_two(conn, ('SD, 720p, 1080p', 'results_quality_movie'))
            connect_two(conn, ('SD, 720p, 1080p', 'results_quality_episode'))
    except:
        pass
    
#Enable DV
def enable_fenlt_dv():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_two(conn, ('0', 'filter_dv'))
            connect_two(conn, ('include', 'filter_dv_name'))
    except:
        pass
    
#Disable DV
def disable_fenlt_dv():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_two(conn, ('1', 'filter_dv'))
            connect_two(conn, ('exclude', 'filter_dv_name'))
    except:
        pass
    
#Enable 3D
def enable_fenlt_3d():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_one(conn, ('true', 'include_3d_results'))
    except:
        pass
    
#Disable 3D
def disable_fenlt_3d():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_one(conn, ('false', 'include_3d_results'))
    except:
        pass

#Enable Auto-Play
def enable_fenlt_ap():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_two(conn, ('true', 'auto_play_movie'))
            connect_two(conn, ('true', 'auto_play_episode'))
    except:
        pass
    
#Disable Auto-Play
def disable_fenlt_ap():
    try:
        # Create database connection
        conn = create_conn(fenlt_settings_db)
        with conn:
            connect_two(conn, ('false', 'auto_play_movie'))
            connect_two(conn, ('false', 'auto_play_episode'))
    except:
        pass

###############################################################
###############################################################   
###############################################################
########################## afFENity ###########################
#Enable 4K
def enable_affen_4k():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_two(conn, ('SD, 720p, 1080p, 4K', 'results_quality_movie'))
            connect_two(conn, ('SD, 720p, 1080p, 4K', 'results_quality_episode'))
    except:
        pass
    
#Disable 3D
def enable_affen_1080p():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_two(conn, ('SD, 720p, 1080p', 'results_quality_movie'))
            connect_two(conn, ('SD, 720p, 1080p', 'results_quality_episode'))
    except:
        pass
    
#Enable DV
def enable_affen_dv():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_two(conn, ('0', 'filter_dv'))
            connect_two(conn, ('include', 'filter_dv_name'))
    except:
        pass
    
#Disable DV
def disable_affen_dv():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_two(conn, ('1', 'filter_dv'))
            connect_two(conn, ('exclude', 'filter_dv_name'))
    except:
        pass
    
#Enable 3D
def enable_affen_3d():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_one(conn, ('true', 'include_3d_results'))
    except:
        pass
    
#Disable 3D
def disable_affen_3d():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_one(conn, ('false', 'include_3d_results'))
    except:
        pass

#Enable Auto-Play
def enable_affen_ap():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_two(conn, ('true', 'auto_play_movie'))
            connect_two(conn, ('true', 'auto_play_episode'))
    except:
        pass
    
#Disable Auto-Play
def disable_affen_ap():
    try:
        # Create database connection
        conn = create_conn(affen_settings_db)
        with conn:
            connect_two(conn, ('false', 'auto_play_movie'))
            connect_two(conn, ('false', 'auto_play_episode'))
    except:
        pass
