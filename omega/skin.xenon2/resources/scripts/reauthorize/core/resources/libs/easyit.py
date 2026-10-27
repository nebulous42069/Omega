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

ORDER = ['coal',
         'pov',
         'umb',
         'dyn',
         'infinity',
         'thecrew',
         'acctmgr',
         'allact',
         'myact']

EASYID = {
    'coal': {
        'name'     : 'The Coalition',
        'plugin'   : 'plugin.video.coalition',
        'saved'    : 'coal',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition/icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition/fanart.jpg'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'coal_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.coalition', 'settings.xml'),
        'default'  : 'easynews_user',
        'data'     : ['provider.easynews', 'easynews_user', 'easynews_password', 'easynews.use_custom_farm', 'easynews.server_name', 'easynews.title_filter', 'easynews.filter_lang', 'en.priority', 'easynews.lang_filters', 'check.easynews'],
        'activate' : 'Addon.OpenSettings(plugin.video.coalition)'},
    'pov': {
        'name'     : 'POV',
        'plugin'   : 'plugin.video.pov',
        'saved'    : 'pov',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'pov_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.pov', 'settings.xml'),
        'default'  : 'easynews_user',
        'data'     : ['provider.easynews', 'easynews_user', 'easynews_password', 'easynews.title_filter', 'easynews.filter_lang', 'en.priority', 'easynews.lang_filters', 'easynews_moderation', 'check.easynews'],
        'activate' : 'Addon.OpenSettings(plugin.video.pov)'},
    'umb': {
        'name'     : 'Umbrella',
        'plugin'   : 'plugin.video.umbrella',
        'saved'    : 'umb',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'umb_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.umbrella', 'settings.xml'),
        'default'  : 'easynews.user',
        'data'     : ['easynews.enable', 'easynews.user', 'easynews.password', 'easynews.priority'],
        'activate' : 'Addon.OpenSettings(plugin.video.umbrella)'},
    'dyn': {
        'name'     : 'Dynasty',
        'plugin'   : 'plugin.video.dynasty',
        'saved'    : 'dyn',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dynasty'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dynasty', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.dynasty', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'dyn_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.dynasty', 'settings.xml'),
        'default'  : 'easynews.user',
        'data'     : ['easynews.enable', 'easynews.user', 'easynews.password', 'easynews.priority'],
        'activate' : 'Addon.OpenSettings(plugin.video.dynasty)'},
    'infinity': {
        'name'     : 'Infinity',
        'plugin'   : 'plugin.video.infinity',
        'saved'    : 'infinity',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.infinity'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.infinity/resources/media/', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.infinity/resources/media', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'infinity_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.infinity', 'settings.xml'),
        'default'  : 'easynews.user',
        'data'     : ['easynews.enable', 'easynews.user', 'easynews.password', 'easynews.priority'],
        'activate' : 'Addon.OpenSettings(plugin.video.infinity)'},
   'thecrew': {
        'name'     : 'The Crew',
        'plugin'   : 'plugin.video.thecrew',
        'saved'    : 'thecrew',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thecrew'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thecrew', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.thecrew', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'thecrew_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.thecrew', 'settings.xml'),
        'default'  : 'easynews.user',
        'data'     : ['easynews.user', 'easynews.password'],
        'activate' : 'Addon.OpenSettings(plugin.video.thecrew)'},
    'acctmgr': {
        'name'     : 'ReAuthorize',
        'plugin'   : 'script.module.reauthorize',
        'saved'    : 'acctmgr',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.reauthorize'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.reauthorize', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.reauthorize', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'acctmgr_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.reauthorize', 'settings.xml'),
        'default'  : 'easynews.username',
        'data'     : ['easynews.username', 'easynews.password'],
        'activate' : 'Addon.OpenSettings(script.module.reauthorize)'},
    'allact': {
        'name'     : 'All Accounts',
        'plugin'   : 'script.module.allaccounts',
        'saved'    : 'allact',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'allact_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.allaccounts', 'settings.xml'),
        'default'  : 'easynews.username',
        'data'     : ['easynews.username', 'easynews.password'],
        'activate' : 'Addon.OpenSettings(script.module.allaccounts)'},
    'myact': {
        'name'     : 'My Accounts',
        'plugin'   : 'script.module.myaccounts',
        'saved'    : 'myact',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.myaccounts'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.myaccounts', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.myaccounts', 'fanart.png'),
        'file'     : os.path.join(CONFIG.EASYFOLD, 'myact_easy'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.myaccounts', 'settings.xml'),
        'default'  : 'easynews.username',
        'data'     : ['easynews.username', 'easynews.password'],
        'activate' : 'Addon.OpenSettings(script.module.myaccounts)'}
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
        xbmc.log('%s: easyit.py Failed!' % var.amgr, xbmc.LOGINFO)
        pass
    
def easy_user(who):
    user_easy = None
    if EASYID[who]:
        name = EASYID[who]['name']
        if os.path.exists(EASYID[who]['path']):
            try:
                add = tools.get_addon_by_id(EASYID[who]['plugin'])
                user_easy = add.getSetting(EASYID[who]['default'])
            except:
                pass
    return user_easy

def easy_it(do, who):
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.EASYFOLD):
        os.makedirs(CONFIG.EASYFOLD)
    if who == 'all':
        for log in ORDER:
            if os.path.exists(EASYID[log]['path']):
                try:
                    addonid = tools.get_addon_by_id(EASYID[log]['plugin'])
                    default = EASYID[log]['default']
                    user = addonid.getSetting(default)
                    
                    update_easy(do, log)
                except:
                    pass
            else:
                logging.log('[Easynews Info] {0}({1}) is not installed'.format(EASYID[log]['name'], EASYID[log]['plugin']), level=xbmc.LOGERROR)
        CONFIG.set_setting('easynextsave', tools.get_date(days=3, formatted=True))
    else:
        if EASYID[who]:
            if os.path.exists(EASYID[who]['path']):
                update_easy(do, who)
        else:
            logging.log('[Easynews Info] Invalid Entry: {0}'.format(who), level=xbmc.LOGERROR)

def clear_saved(who, over=False):
    if who == 'all':
        for easy in EASYID:
            clear_saved(easy,  True)
    elif EASYID[who]:
        file = EASYID[who]['file']
        if os.path.exists(file):
            os.remove(file)
    if not over:
        xbmc.executebuiltin('Container.Refresh()')

def update_easy(do, who):
    file = EASYID[who]['file']
    settings = EASYID[who]['settings']
    data = EASYID[who]['data']
    addonid = tools.get_addon_by_id(EASYID[who]['plugin'])
    saved = EASYID[who]['saved']
    default = EASYID[who]['default']
    user = addonid.getSetting(default)
    suser = CONFIG.get_setting(saved)
    name = EASYID[who]['name']
    icon = EASYID[who]['icon']

    if do == 'update':
        if not user == '':
            try:
                root = ElementTree.Element(saved)

                for setting in data:
                    easy = ElementTree.SubElement(root, 'easy')
                    id = ElementTree.SubElement(easy, 'id')
                    id.text = setting
                    value = ElementTree.SubElement(easy, 'value')
                    value.text = addonid.getSetting(setting)

                tree = ElementTree.ElementTree(root)
                tree.write(file)

                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)

                logging.log('Easynews Info Saved for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Easynews Info] Unable to Update {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('OffCloud Info Not Registered for {0}'.format(name))
    elif do == 'restore':
        if os.path.exists(file):
            tree = ElementTree.parse(file)
            root = tree.getroot()
            
            try:
                for setting in root.findall('easy'):
                    id = setting.find('id').text
                    value = setting.find('value').text
                    addonid.setSetting(id, value)
                
                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)
                
                logging.log('Easynews Info Restored for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Easynews Info] Unable to Restore {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('Easynews Info Not Found for {0}'.format(name))
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

            except Exception as e:
                logging.log("[Easynews Info] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
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
                logging.log("[Easynews Info] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        xbmc.executebuiltin('Container.Refresh()')
    
def auto_update(who):
    if who == 'all':
        for log in EASYID:
            if os.path.exists(EASYID[log]['path']):
                auto_update(log)
    elif EASYID[who]:
        if os.path.exists(EASYID[who]['path']):
            u = easy_user(who)
            su = CONFIG.get_setting(EASYID[who]['saved'])
            n = EASYID[who]['name']
            if not u or u == '':
                return
            elif su == '':
                easy_it('update', who)
            elif not u == su:
                dialog = xbmcgui.Dialog()

                if dialog.yesno(CONFIG.ADDONTITLE,
                                    "Would you like to save the [COLOR {0}]Easynews Info[/COLOR] for [COLOR {1}]{2}[/COLOR]?".format(CONFIG.COLOR2, CONFIG.COLOR1, n),
                                    "Addon: [COLOR springgreen][B]{0}[/B][/COLOR]".format(u),
                                    "Saved:[/COLOR] [COLOR red][B]{0}[/B][/COLOR]".format(su) if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]',
                                    yeslabel="[B][COLOR springreen]Save Easynews[/COLOR][/B]",
                                    nolabel="[B][COLOR red]No, Cancel[/COLOR][/B]"):
                    easy_it('update', who)
            else:
                easy_it('update', who)

def import_list(who):
    if who == 'all':
        for log in EASYID:
            if os.path.exists(EASYID[log]['file']):
                import_list(log)
    elif EASYID[who]:
        if os.path.exists(EASYID[who]['file']):
            file = EASYID[who]['file']
            addonid = tools.get_addon_by_id(EASYID[who]['plugin'])
            saved = EASYID[who]['saved']
            default = EASYID[who]['default']
            suser = CONFIG.get_setting(saved)
            name = EASYID[who]['name']
            
            tree = ElementTree.parse(file)
            root = tree.getroot()
            
            for setting in root.findall('easy'):
                id = setting.find('id').text
                value = setting.find('value').text
            
                addonid.setSetting(id, value)

            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, name),
                       '[COLOR {0}]Easynews Info: Imported![/COLOR]'.format(CONFIG.COLOR2))

def settings(who):
    user = None
    user = EASYID[who]['name']
    return user

def open_settings(who):
    addonid = tools.get_addon_by_id(EASYID[who]['plugin'])
    addonid.openSettings()

