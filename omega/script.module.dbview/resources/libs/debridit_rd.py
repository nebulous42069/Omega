import xbmc
import xbmcaddon
import xbmcgui
import os.path
import xbmcvfs
import json
import os
import time
import sqlite3

from sqlite3 import Error
from xml.etree import ElementTree
from resources.libs.common.config import CONFIG
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common import var
translatePath = xbmcvfs.translatePath
addons = translatePath('special://home/addons/')

ORDER = ['fenltrd',
         'fenrd',
         'umbrd',
         'povrd',
         'dradisrd',
         'serenrd',
         'coalrd',
         'realxrd',
         'rurlrd',
         'allactrd',
         'acctmgrrd']

DEBRIDID = {
    'fenltrd': {
        'name'     : 'Fen Light',
        'plugin'   : 'plugin.video.fenlight',
        'saved'    : 'fenltrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fenlight'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fenlight/resources/media/', 'fenlight_icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.fenlight/resources/media/', 'fenlight_fanart2.jpg'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'fenlt_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.fenlight/databases', 'settings.db'),
        'default'  : '',
        'data'     : [],
        'activate' : 'Addon.OpenSettings(plugin.video.fenlight)'},
    'fenrd': {
        'name'     : 'Fen',
        'plugin'   : 'plugin.video.fen',
        'saved'    : 'fenrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fen'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fen/resources/media/', 'fen_icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.fen/resources/media/', 'fen_fanart.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'fen_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.fen', 'settings.xml'),
        'default'  : 'rd.account_id',
        'data'     : ['rd.client_id', 'rd.refresh', 'rd.secret', 'rd.token', 'rd.account_id', 'rd.enabled'],
        'activate' : 'Addon.OpenSettings(plugin.video.fen)'},
    'umbrd': {
        'name'     : 'Umbrella',
        'plugin'   : 'plugin.video.umbrella',
        'saved'    : 'umbrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'umb_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.umbrella', 'settings.xml'),
        'default'  : 'realdebridusername',
        'data'     : ['realdebridusername', 'realdebridtoken', 'realdebrid.clientid', 'realdebridsecret', 'realdebridrefresh', 'realdebrid.enable'],
        'activate' : 'Addon.OpenSettings(plugin.video.umbrella)'},
    'povrd': {
        'name'     : 'POV',
        'plugin'   : 'plugin.video.pov',
        'saved'    : 'povrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'fanart.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'pov_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.pov', 'settings.xml'),
        'default'  : 'rd.username',
        'data'     : ['rd.username', 'rd.token', 'rd.client_id', 'rd.refresh', 'rd.secret','rd.enabled'],
        'activate' : 'Addon.OpenSettings(plugin.video.pov)'},
    'dradisrd': {
        'name'     : 'Dradis',
        'plugin'   : 'plugin.video.dradis',
        'saved'    : 'dradisrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dradis'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dradis', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.dradis', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'dradis_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.dradis', 'settings.xml'),
        'default'  : 'realdebrid.username',
        'data'     : ['realdebrid.username', 'realdebrid.token', 'realdebrid.client_id', 'realdebrid.secret', 'realdebrid.refresh', 'realdebrid.enable'],
        'activate' : 'Addon.OpenSettings(plugin.video.dradis)'},
    'coalrd': {
        'name'     : 'The Coalition',
        'plugin'   : 'plugin.video.coalition',
        'saved'    : 'coalrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition', 'fanart.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'coal_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.coalition', 'settings.xml'),
        'default'  : 'rd.username',
        'data'     : ['rd.username', 'rd.token', 'rd.client_id', 'rd.refresh', 'rd.secret','rd.enabled'],
        'activate' : 'Addon.OpenSettings(plugin.video.coalition)'},
    'serenrd': {
        'name'     : 'Seren',
        'plugin'   : 'plugin.video.seren',
        'saved'    : 'serenrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.seren'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.seren/resources/images', 'ico-seren-3.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.seren/resources/images', 'fanart-seren-3.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'seren_rd'), #Backup location
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.seren', 'settings.xml'),
        'default'  : 'rd.username',
        'data'     : ['rd.auth', 'rd.client_id', 'rd.expiry', 'rd.refresh', 'rd.secret', 'rd.username', 'realdebrid.enabled'],
        'activate' : 'Addon.OpenSettings(plugin.video.seren)'},
    'realxrd': {
        'name'     : 'Realizer',
        'plugin'   : 'plugin.video.realizerx',
        'saved'    : 'realxrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.realizerx'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.realizerx', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.realizerx', 'fanart.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'realx_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.realizerx', 'rdauth.json'),
        'default'  : '',
        'data'     : [],
        'activate' : 'Addon.OpenSettings(plugin.video.realizerx)'},
    'rurlrd': {
        'name'     : 'ResolveURL',
        'plugin'   : 'script.module.resolveurl',
        'saved'    : 'rurlrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.resolveurl'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.resolveurl', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.resolveurl', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'rurl_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.resolveurl', 'settings.xml'),
        'default'  : 'RealDebridResolver_client_id',
        'data'     : ['RealDebridResolver_client_id', 'RealDebridResolver_client_secret', 'RealDebridResolver_enabled', 'RealDebridResolver_refresh', 'RealDebridResolver_token', 'RealDebridResolver_cached_only'],
        'activate' : 'Addon.OpenSettings(script.module.resolveurl)'},
    'allactrd': {
        'name'     : 'All Accounts',
        'plugin'   : 'script.module.allaccounts',
        'saved'    : 'allactrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts', 'fanart.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'allact_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.allaccounts', 'settings.xml'),
        'default'  : 'realdebrid.username',
        'data'     : ['realdebrid.client_id', 'realdebrid.refresh', 'realdebrid.secret', 'realdebrid.token', 'realdebrid.username'],
        'activate' : 'Addon.OpenSettings(script.module.allaccounts)'},
    'acctmgrrd': {
        'name'     : 'Debrid Manager',
        'plugin'   : 'script.module.debridmgr',
        'saved'    : 'acctmgrrd',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.debridmgr'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.debridmgr', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.debridmgr', 'fanart.png'),
        'file'     : os.path.join(CONFIG.DEBRIDFOLD_RD, 'acctmgr_rd'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.debridmgr', 'settings.xml'),
        'default'  : 'realdebrid.username',
        'data'     : ['realdebrid.client_id', 'realdebrid.refresh', 'realdebrid.secret', 'realdebrid.token', 'realdebrid.username'],
        'activate' : 'Addon.OpenSettings(script.module.debridmgr)'},
}

def create_conn(db_file):
    try:
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            print(e)

        return conn
    except:
        xbmc.log('%s: Debridit_rd Failed!' % var.amgr, xbmc.LOGINFO)
        pass
    
def debrid_user(who):
    user = None
    if DEBRIDID[who]:
        name = DEBRIDID[who]['name']
        if os.path.exists(DEBRIDID[who]['path']) and name == 'Fen Light':
            try:
                # Create database connection
                conn = create_conn(var.fenlt_settings_db)
                with conn:
                    cur = conn.cursor()
                    cur.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('rd.token',)) #Get setting to compare
                    auth = cur.fetchone()
                    user_data = str(auth)

                    if user_data == "('empty_setting',)" or user_data == "('',)" or user_data == '' or user_data == None: #Check if addon is authorized
                        user = None #Return if not authorized
                    else:
                        user = user_data #Return if authorized
                    cur.close()
            except:
                xbmc.log('%s: Debridit_rd Fen Light Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            '''elif os.path.exists(DEBRIDID[who]['path']) and name == 'afFENity':
            try:
                conn = create_conn(var.affen_settings_db)
                with conn:
                    cur = conn.cursor()
                    cur.execute(''''''SELECT setting_value FROM settings WHERE setting_id = ?'''''', ('rd.token',))
                    auth = cur.fetchone()
                    user_data = str(auth)

                    if user_data == "('empty_setting',)" or user_data == "('',)" or user_data == '' or user_data == None:
                        user = None
                    else:
                        user = user_data
                    cur.close()
            except:
                xbmc.log('%s: Debridit_rd afFENity Failed!' % var.amgr, xbmc.LOGINFO)
                pass'''
        elif os.path.exists(DEBRIDID[who]['path']) and name == 'Realizer':
            try:
                with open(var.chkset_realx_json) as r:
                    data = json.load(r)
                    chk_auth_realx = data['token']
                    if not str(var.chk_debridmgr_tk_rd) == str(chk_auth_realx) or str(chk_auth_realx) == '':
                        user = None
                    else:
                        user = str(chk_auth_realx)
            except:
                xbmc.log('%s: Debridit_rd Realizer Failed!' % var.amgr, xbmc.LOGINFO)
                pass              
        else:
            if os.path.exists(DEBRIDID[who]['path']):
                try:
                    add = tools.get_addon_by_id(DEBRIDID[who]['plugin'])
                    user = add.getSetting(DEBRIDID[who]['default'])
                except:
                    pass
    return user

def debrid_it(do, who):
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.DEBRIDFOLD_RD):
        os.makedirs(CONFIG.DEBRIDFOLD_RD)
    if who == 'all':
        for log in ORDER:
            if os.path.exists(DEBRIDID[log]['path']):
                try:
                    addonid = tools.get_addon_by_id(DEBRIDID[log]['plugin'])
                    default = DEBRIDID[log]['default']
                    user = addonid.getSetting(default)
                    
                    update_debrid(do, log)
                except:
                    pass
            else:
                logging.log('[Debrid Info] {0}({1}) is not installed'.format(DEBRIDID[log]['name'], DEBRIDID[log]['plugin']), level=xbmc.LOGERROR)
    else:
        if DEBRIDID[who]:
            if os.path.exists(DEBRIDID[who]['path']):
                update_debrid(do, who)
        else:
            logging.log('[Debrid Info] Invalid Entry: {0}'.format(who), level=xbmc.LOGERROR)

def clear_saved(who, over=False):
    if who == 'all':
        for debrid in DEBRIDID:
            clear_saved(debrid,  True)
    elif DEBRIDID[who]:
        file = DEBRIDID[who]['file']
        if os.path.exists(file):
            os.remove(file)
    if not over:
        xbmc.executebuiltin('Container.Refresh()')

def update_debrid(do, who):
    file = DEBRIDID[who]['file']
    settings = DEBRIDID[who]['settings']
    data = DEBRIDID[who]['data']
    addonid = tools.get_addon_by_id(DEBRIDID[who]['plugin'])
    saved = DEBRIDID[who]['saved']
    default = DEBRIDID[who]['default']
    user = addonid.getSetting(default)
    suser = CONFIG.get_setting(saved)
    name = DEBRIDID[who]['name']
    icon = DEBRIDID[who]['icon']

    if do == 'update':
        if name == 'Fen Light':
            pass
        else:
            if not user == '':
                try:
                    root = ElementTree.Element(saved)
                    
                    for setting in data:
                        debrid = ElementTree.SubElement(root, 'debrid')
                        id = ElementTree.SubElement(debrid, 'id')
                        id.text = setting
                        value = ElementTree.SubElement(debrid, 'value')
                        value.text = addonid.getSetting(setting)
                      
                    tree = ElementTree.ElementTree(root)
                    tree.write(file)
                    
                    user = addonid.getSetting(default)
                    CONFIG.set_setting(saved, user)
                    
                    logging.log('Debrid Info Saved for {0}'.format(name), level=xbmc.LOGINFO)
                except Exception as e:
                    logging.log("[Debrid Info] Unable to Update {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
            else:
                logging.log('Debrid Info Not Registered for {0}'.format(name))
    elif do == 'restore':
        if os.path.exists(file):
            tree = ElementTree.parse(file)
            root = tree.getroot()
            
            try:
                for setting in root.findall('debrid'):
                    id = setting.find('id').text
                    value = setting.find('value').text
                    addonid.setSetting(id, value)
                
                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)
                logging.log('Debrid Info Restored for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Debrid Info] Unable to Restore {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('Debrid Info Not Found for {0}'.format(name))
    elif do == 'clearaddon':
        logging.log('{0} SETTINGS: {1}'.format(name, settings))
        if os.path.exists(settings):
            try:
                tree = ElementTree.parse(settings)
                root = tree.getroot()
                
                for setting in root.findall('setting'):
                    if setting.attrib['id'] in data:
                        logging.log('Removing Setting: {0}'.format(setting.attrib))
                        root.remove(setting)
                            
                tree.write(settings)
                
                logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, name),
                                   '[COLOR {0}]Addon Data: Cleared![/COLOR]'.format(CONFIG.COLOR2),
                                   2000,
                                   icon)
            except Exception as e:
                logging.log("[Debrid Info] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        xbmc.executebuiltin('Container.Refresh()')
    elif do == 'wipeaddon':
        logging.log('{0} SETTINGS: {1}'.format(name, settings))
        if name == 'Fen Light':
        #if name == 'Fen Light' or name == 'afFENity':
            pass
        else:
            if os.path.exists(settings):
                try:
                    tree = ElementTree.parse(settings)
                    root = tree.getroot()
                    
                    for setting in root.findall('setting'):
                        if setting.attrib['id'] in data:
                            logging.log('Removing Setting: {0}'.format(setting.attrib))
                            root.remove(setting)
                                
                    tree.write(settings)
                    
                except Exception as e:
                    logging.log("[Debrid Info] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
            xbmc.executebuiltin('Container.Refresh()')

def auto_update(who):
    if who == 'all':
        for log in DEBRIDID:
            if os.path.exists(DEBRIDID[log]['path']):
                auto_update(log)
    elif DEBRIDID[who]:
        if os.path.exists(DEBRIDID[who]['path']):
            u = debrid_user(who)
            su = CONFIG.get_setting(DEBRIDID[who]['saved'])
            n = DEBRIDID[who]['name']
            if not u or u == '':
                return
            elif su == '':
                debrid_it('update', who)
            elif not u == su:
                dialog = xbmcgui.Dialog()

                if dialog.yesno(CONFIG.ADDONTITLE,
                                    "Would you like to save the [COLOR {0}]Debrid Info[/COLOR] for [COLOR {1}]{2}[/COLOR]?".format(CONFIG.COLOR2, CONFIG.COLOR1, n),
                                    "Addon: [COLOR springgreen][B]{0}[/B][/COLOR]".format(u),
                                    "Saved:[/COLOR] [COLOR red][B]{0}[/B][/COLOR]".format(su) if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]',
                                    yeslabel="[B][COLOR springreen]Save Debrid[/COLOR][/B]",
                                    nolabel="[B][COLOR red]No, Cancel[/COLOR][/B]"):
                    debrid_it('update', who)
            else:
                debrid_it('update', who)

def import_list(who):
    if who == 'all':
        for log in DEBRIDID:
            if os.path.exists(DEBRIDID[log]['file']):
                import_list(log)
    elif DEBRIDID[who]:
        if os.path.exists(DEBRIDID[who]['file']):
            file = DEBRIDID[who]['file']
            addonid = tools.get_addon_by_id(DEBRIDID[who]['plugin'])
            saved = DEBRIDID[who]['saved']
            default = DEBRIDID[who]['default']
            suser = CONFIG.get_setting(saved)
            name = DEBRIDID[who]['name']
            
            tree = ElementTree.parse(file)
            root = tree.getroot()
            
            for setting in root.findall('debrid'):
                id = setting.find('id').text
                value = setting.find('value').text
            
                addonid.setSetting(id, value)

            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, name),
                       '[COLOR {0}]Debrid Info: Imported![/COLOR]'.format(CONFIG.COLOR2))

def settings(who):
    user = None
    user = DEBRIDID[who]['name']
    return user

def open_settings(who):
    addonid = tools.get_addon_by_id(DEBRIDID[who]['plugin'])
    addonid.openSettings()

