import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import xbmcvfs
import sqlite3

from sqlite3 import Error
from xml.etree import ElementTree
from libs.common.config import CONFIG
from libs.common import logging
from libs.common import tools
from libs.common import var

ORDER = ['umb',
         'dyn',
         'pov',
         'infin',
         'acctmgr']

EDID = {
    'umb': {
        'name'     : 'Umbrella',
        'plugin'   : 'plugin.video.umbrella',
        'saved'    : 'umb',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EDFOLD, 'umb_ed'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.umbrella', 'settings.xml'),
        'default'  : 'easydebridtoken',
        'data'     : ['easydebridtoken', 'easydebrid.priority', 'easydebrid.enable'],
        'activate' : 'Addon.OpenSettings(plugin.video.umbrella)'},
    'dyn': {
        'name'     : 'Dynasty',
        'plugin'   : 'plugin.video.dynasty',
        'saved'    : 'dyn',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dynasty'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dynasty', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.dynasty', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EDFOLD, 'dyn_ed'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.dynasty', 'settings.xml'),
        'default'  : 'easydebridtoken',
        'data'     : ['easydebridtoken', 'easydebrid.priority', 'easydebrid.enable'],
        'activate' : 'Addon.OpenSettings(plugin.video.dynasty)'},
    'pov': {
        'name'     : 'POV',
        'plugin'   : 'plugin.video.pov',
        'saved'    : 'pov',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EDFOLD, 'pov_ed'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.pov', 'settings.xml'),
        'default'  : 'ed.token',
        'data'     : ['ed.token', 'ed.account_id', 'ed.expires', 'ed.enabled', 'ed.torrent.enabled', 'ed.priority'],
        'activate' : 'Addon.OpenSettings(plugin.video.pov)'},
    'infin': {
        'name'     : 'Infinity',
        'plugin'   : 'plugin.video.infinity',
        'saved'    : 'infin',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.infinity'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.infinity/resources/media', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.infinity/resources/media', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EDFOLD, 'infinity_ed'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.infinity', 'settings.xml'),
        'default'  : 'easydebridtoken',
        'data'     : ['easydebridtoken', 'easydebrid.username', 'easydebrid.expirynotice', 'easydebrid.priority', 'easydebrid.enable', 'ed_cloud.enabled'],
        'activate' : 'Addon.OpenSettings(plugin.video.infinity)'},
   'acctmgr': {
        'name'     : 'ReAuthorize',
        'plugin'   : 'script.module.reauthorize',
        'saved'    : 'acctmgr',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.reauthorize'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.reauthorize', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.reauthorize', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EDFOLD, 'acctmgr_ed'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.reauthorize', 'settings.xml'),
        'default'  : 'easydebrid.token',
        'data'     : ['easydebrid.token', 'easydebrid.acct_id', 'easydebrid.enabled'],
        'activate' : 'Addon.OpenSettings(script.module.reauthorize)'}
}

def create_conn(db_file):
    try:
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            xbmc.log(str(e), xbmc.LOGINFO)

        return conn
    except:
        xbmc.log('%s: edit.py Failed!' % var.amgr, xbmc.LOGINFO)
        pass
    
def ed_user(who):
    user_ed = None
    if EDID[who]:
       name = EDID[who]['name']
       if os.path.exists(EDID[who]['path']):
           try:
               add = tools.get_addon_by_id(EDID[who]['plugin'])
               user_ed = add.getSetting(EDID[who]['default'])
           except:
               pass
    return user_ed
    
def ed_it(do, who):
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.EDFOLD):
        os.makedirs(CONFIG.EDFOLD)
    if who == 'all':
        for log in ORDER:
            if os.path.exists(EDID[log]['path']):
                try:
                    addonid = tools.get_addon_by_id(EDID[log]['plugin'])
                    default = EDID[log]['default']
                    user = addonid.getSetting(default)
                    
                    update_ed(do, log)
                except:
                    pass
            else:
                logging.log('[Easy Debrid Info] {0}({1}) is not installed'.format(EDID[log]['name'], EDID[log]['plugin']), level=xbmc.LOGERROR)
    else:
        if EDID[who]:
            if os.path.exists(EDID[who]['path']):
                update_ed(do, who)
        else:
            logging.log('[Easy Debrid Info] Invalid Entry: {0}'.format(who), level=xbmc.LOGERROR)

def clear_saved(who, over=False):
    if who == 'all':
        for ed in EDID:
            clear_saved(ed,  True)
    elif EDID[who]:
        file = EDID[who]['file']
        if os.path.exists(file):
            os.remove(file)
    if not over:
        xbmc.executebuiltin('Container.Refresh()')

def update_ed(do, who):
    file = EDID[who]['file']
    settings = EDID[who]['settings']
    data = EDID[who]['data']
    addonid = tools.get_addon_by_id(EDID[who]['plugin'])
    saved = EDID[who]['saved']
    default = EDID[who]['default']
    user = addonid.getSetting(default)
    suser = CONFIG.get_setting(saved)
    name = EDID[who]['name']
    icon = EDID[who]['icon']

    if do == 'update':
        if not user == '':
            try:
                root = ElementTree.Element(saved)
                for setting in data:
                    ed = ElementTree.SubElement(root, 'ed')
                    id = ElementTree.SubElement(ed, 'id')
                    id.text = setting
                    value = ElementTree.SubElement(ed, 'value')
                    value.text = addonid.getSetting(setting)

                tree = ElementTree.ElementTree(root)
                tree.write(file)
                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)

                logging.log('Easy Debrid Info Saved for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Easy Debrid Info] Unable to Update {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('Easy Debrid Info Not Registered for {0}'.format(name))
    elif do == 'restore':
        if os.path.exists(file):
            tree = ElementTree.parse(file)
            root = tree.getroot()
            
            try:
                for setting in root.findall('ed'):
                    id = setting.find('id').text
                    value = setting.find('value').text
                    addonid.setSetting(id, value)
                
                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)
                logging.log('Easy Debrid Info Restored for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Easy Debrid Info] Unable to Restore {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('Easy Debrid Info Not Found for {0}'.format(name))
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
                logging.log("[Easy Debrid Info] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        xbmc.executebuiltin('Container.Refresh()')
    elif do == 'wipeaddon':
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

            except Exception as e:
                logging.log("[TorBox Info] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        xbmc.executebuiltin('Container.Refresh()')

def auto_update(who):
    if who == 'all':
        for log in EDID:
            if os.path.exists(EDID[log]['path']):
                auto_update(log)
    elif EDID[who]:
        if os.path.exists(EDID[who]['path']):
            u = ed_user(who)
            su = CONFIG.get_setting(EDID[who]['saved'])
            n = EDID[who]['name']
            if not u or u == '':
                return
            elif su == '':
                ed_it('update', who)
            elif not u == su:
                dialog = xbmcgui.Dialog()

                if dialog.yesno(CONFIG.ADDONTITLE,
                                    "Would you like to save the [COLOR {0}]OffCloud Info[/COLOR] for [COLOR {1}]{2}[/COLOR]?".format(CONFIG.COLOR2, CONFIG.COLOR1, n),
                                    "Addon: [COLOR springgreen][B]{0}[/B][/COLOR]".format(u),
                                    "Saved:[/COLOR] [COLOR red][B]{0}[/B][/COLOR]".format(su) if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]',
                                    yeslabel="[B][COLOR springreen]Save OffCloud[/COLOR][/B]",
                                    nolabel="[B][COLOR red]No, Cancel[/COLOR][/B]"):
                    ed_it('update', who)
            else:
                ed_it('update', who)

def import_list(who):
    if who == 'all':
        for log in EDID:
            if os.path.exists(EDID[log]['file']):
                import_list(log)
    elif EDID[who]:
        if os.path.exists(EDID[who]['file']):
            file = EDID[who]['file']
            addonid = tools.get_addon_by_id(EDID[who]['plugin'])
            saved = EDID[who]['saved']
            default = EDID[who]['default']
            suser = CONFIG.get_setting(saved)
            name = EDID[who]['name']
            
            tree = ElementTree.parse(file)
            root = tree.getroot()
            
            for setting in root.findall('ed'):
                id = setting.find('id').text
                value = setting.find('value').text
            
                addonid.setSetting(id, value)

            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, name),
                       '[COLOR {0}]Easy Debrid Info: Imported![/COLOR]'.format(CONFIG.COLOR2))

def settings(who):
    user = None
    user = EDID[who]['name']
    return user

def open_settings(who):
    addonid = tools.get_addon_by_id(EDID[who]['plugin'])
    addonid.openSettings()
