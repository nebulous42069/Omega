import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import glob
import os
import re
try:  # Python 3
    from urllib.parse import quote_plus
    from urllib.request import urlretrieve
except ImportError:  # Python 2
    from urllib import quote_plus
    from urllib import urlretrieve
from resources.libs.common import directory
from resources.libs.common.config import CONFIG

translatePath = xbmcvfs.translatePath
addons = translatePath('special://home/addons/')

def debrid_menu():
    from resources.libs import debridit_rd
    for debrid in debridit_rd.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_rd.DEBRIDID[debrid]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_rd.DEBRIDID[debrid]['plugin'])) or xbmcvfs.exists(addons + translatePath('plugin.video.NightwingLite/')):
                name = debridit_rd.DEBRIDID[debrid]['name']
                path = debridit_rd.DEBRIDID[debrid]['path']
                saved = debridit_rd.DEBRIDID[debrid]['saved']
                file = debridit_rd.DEBRIDID[debrid]['file']
                user = CONFIG.get_setting(saved)
                auser = debridit_rd.debrid_user(debrid)
                set_user = debridit_rd.settings(debrid)
                icon = debridit_rd.DEBRIDID[debrid]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = debridit_rd.DEBRIDID[debrid]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('Debrid', debrid)
                menu2 = create_save_data_menu('Debrid', debrid)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=debrid)'.format(CONFIG.ADDON_ID, debrid)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]Not Authorized[/COLOR]'.format(name), {'name': debrid}, icon=icon, description='Your Real-Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]Authorized[/COLOR]'.format(name), {'name': debrid}, icon=icon, description='Your Real-Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_rd', 'name': debrid}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()


def premiumize_menu():
    from resources.libs import debridit_pm

    for debrid in debridit_pm.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_pm.DEBRIDID[debrid]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_pm.DEBRIDID[debrid]['plugin'])) or xbmcvfs.exists(addons + translatePath('plugin.video.NightwingLite/')):
                name = debridit_pm.DEBRIDID[debrid]['name']
                path = debridit_pm.DEBRIDID[debrid]['path']
                saved = debridit_pm.DEBRIDID[debrid]['saved']
                file = debridit_pm.DEBRIDID[debrid]['file']
                user = CONFIG.get_setting(saved)
                auser = debridit_pm.debrid_user(debrid)
                set_user = debridit_pm.settings(debrid)
                icon = debridit_pm.DEBRIDID[debrid]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = debridit_pm.DEBRIDID[debrid]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('Debrid', debrid)
                menu2 = create_save_data_menu('Debrid', debrid)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=debrid)'.format(CONFIG.ADDON_ID, debrid)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]Not Authorized[/COLOR]'.format(name), {'name': debrid}, icon=icon, description='Your Premiumize Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]Authorized[/COLOR]'.format(name), {'name': debrid}, icon=icon, description='Your Premiumize Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_pm', 'name': debrid}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()

def alldebrid_menu():
    from resources.libs import debridit_ad

    for debrid in debridit_ad.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_ad.DEBRIDID[debrid]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_ad.DEBRIDID[debrid]['plugin'])) or xbmcvfs.exists(addons + translatePath('plugin.video.NightwingLite/')):
                name = debridit_ad.DEBRIDID[debrid]['name']
                path = debridit_ad.DEBRIDID[debrid]['path']
                saved = debridit_ad.DEBRIDID[debrid]['saved']
                file = debridit_ad.DEBRIDID[debrid]['file']
                user = CONFIG.get_setting(saved)
                auser = debridit_ad.debrid_user(debrid)
                set_user = debridit_ad.settings(debrid)
                icon = debridit_ad.DEBRIDID[debrid]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = debridit_ad.DEBRIDID[debrid]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('Debrid', debrid)
                menu2 = create_save_data_menu('Debrid', debrid)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=debrid)'.format(CONFIG.ADDON_ID, debrid)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]Not Authorized[/COLOR]'.format(name), {'name': debrid}, icon=icon, description='Your All-Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]Authorized[/COLOR]'.format(name), {'name': debrid}, icon=icon, description='Your All-Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_ad', 'name': debrid}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()

def torbox_menu():
    from resources.libs import tbit

    for tb in tbit.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(tbit.TBID[tb]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(tbit.TBID[tb]['plugin'])):
                name = tbit.TBID[tb]['name']
                path = tbit.TBID[tb]['path']
                saved = tbit.TBID[tb]['saved']
                file = tbit.TBID[tb]['file']
                user = CONFIG.get_setting(saved)
                auser = tbit.tb_user(tb)
                set_user = tbit.settings(tb)
                icon = tbit.TBID[tb]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = tbit.TBID[tb]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('TorBox', tb)
                menu2 = create_save_data_menu('TorBox', tb)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=tb)'.format(CONFIG.ADDON_ID, tb)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]Not Authorized[/COLOR]'.format(name), {'name': tb}, icon=icon, description='Your TorBox Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]Authorized[/COLOR]'.format(name), {'name': tb}, icon=icon, description='Your TorBox Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_tb', 'name': tb}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()

def easydebrid_menu():
    from resources.libs import edit

    for ed in edit.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(edit.EDID[ed]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(edit.EDID[ed]['plugin'])):
                name = edit.EDID[ed]['name']
                path = edit.EDID[ed]['path']
                saved = edit.EDID[ed]['saved']
                file = edit.EDID[ed]['file']
                user = CONFIG.get_setting(saved)
                auser = edit.ed_user(ed)
                set_user = edit.settings(ed)
                icon = edit.EDID[ed]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = edit.EDID[ed]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('Easy Debrid', ed)
                menu2 = create_save_data_menu('Easy Debrid', ed)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=ed)'.format(CONFIG.ADDON_ID, ed)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]Not Authorized[/COLOR]'.format(name), {'name': ed}, icon=icon, description='Your Easy Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]Authorized[/COLOR]'.format(name), {'name': ed}, icon=icon, description='Your Easy Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_ed', 'name': ed}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()
                
def offcloud_menu():
    from resources.libs import offit

    for offc in offit.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(offit.OFFCID[offc]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(offit.OFFCID[offc]['plugin'])):
                name = offit.OFFCID[offc]['name']
                path = offit.OFFCID[offc]['path']
                saved = offit.OFFCID[offc]['saved']
                file = offit.OFFCID[offc]['file']
                user = CONFIG.get_setting(saved)
                auser = offit.offc_user(offc)
                set_user = offit.settings(offc)
                icon = offit.OFFCID[offc]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = offit.OFFCID[offc]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('OffCloud', offc)
                menu2 = create_save_data_menu('OffCloud', offc)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=offc)'.format(CONFIG.ADDON_ID, offc)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]Not Authorized[/COLOR]'.format(name), {'name': offc}, icon=icon, description='Your Offcloud Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]Authorized[/COLOR]'.format(name), {'name': offc}, icon=icon, description='Your Offcloud Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_oc', 'name': offc}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()
                
def ext_menu():
    from resources.libs import extit

    for ext in extit.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(extit.EXTID[ext]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(extit.EXTID[ext]['plugin'])):
                name = extit.EXTID[ext]['name']
                path = extit.EXTID[ext]['path']
                saved = extit.EXTID[ext]['saved']
                file = extit.EXTID[ext]['file']
                user = CONFIG.get_setting(saved)
                auser = extit.ext_user(ext)
                set_user = extit.settings(ext)
                icon = extit.EXTID[ext]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = extit.EXTID[ext]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('External Providers', ext)
                menu2 = create_save_data_menu('External Providers', ext)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=ext)'.format(CONFIG.ADDON_ID, ext)))

                if not auser:
                    directory.add_file('{0} - [COLOR red]No Scraper Synced[/COLOR]'.format(name), {'name': ext}, icon=icon, description='Your External Provider Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('{0} - [COLOR springgreen]CocoScrapers Synced[/COLOR]'.format(name), {'name': ext}, icon=icon, description='Your External Provider Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_ext', 'name': ext}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()

def all_accounts_menu():
    from resources.libs import debridit_all

    for debrid in debridit_all.ORDER:
        if not xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_all.DEBRIDID[debrid]['plugin'])):
            pass
        else:
            if xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit_all.DEBRIDID[debrid]['plugin'])):
                name = debridit_all.DEBRIDID[debrid]['name']
                path = debridit_all.DEBRIDID[debrid]['path']
                saved = debridit_all.DEBRIDID[debrid]['saved']
                file = debridit_all.DEBRIDID[debrid]['file']
                user = CONFIG.get_setting(saved)
                user_rd = debridit_all.debrid_user_rd(debrid)
                user_pm = debridit_all.debrid_user_pm(debrid)
                user_ad = debridit_all.debrid_user_ad(debrid)
                set_user = debridit_all.settings(debrid)
                icon = debridit_all.DEBRIDID[debrid]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
                fanart = debridit_all.DEBRIDID[debrid]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
                menu = create_addon_data_menu('Debrid', debrid)
                menu2 = create_save_data_menu('Debrid', debrid)
                menu.append((CONFIG.THEME2.format('{0} Settings'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=debrid)'.format(CONFIG.ADDON_ID, debrid)))

                directory.add_file('{0}'.format(name), {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                
                if not user_rd:
                    directory.add_file('Real-Debrid - [COLOR red]Not Authorized[/COLOR]', {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('Real-Debrid - [COLOR springgreen]Authorized[/COLOR]', {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                
                if not user_pm:
                    directory.add_file('Premiumize - [COLOR red]Not Authorized[/COLOR]', {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('Premiumize - [COLOR springgreen]Authorized[/COLOR]', {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                
                if not user_ad:
                    directory.add_file('All-Debrid - [COLOR red]Not Authorized[/COLOR]', {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                else:
                    directory.add_file('All-Debrid - [COLOR springgreen]Authorized[/COLOR]', {'name': debrid}, icon=icon, description='Your Debrid Authorizations', fanart=fanart, themeit=CONFIG.THEME3)
                if name == 'Fen Light':
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format('Fen Light'), {'mode': 'opensettings_fenlt', 'name': 'Fen Light'}, icon=icon, fanart=fanart, menu=menu)
                else:
                    directory.add_file('[COLOR blue]Open [COLOR dodgerblue]{0}[/COLOR] Settings[/COLOR]'.format(set_user), {'mode': 'opensettings_all', 'name': debrid}, icon=icon, fanart=fanart, menu=menu)
                directory.add_separator_allaccts()
            
def create_addon_data_menu(add='', name=''):
    menu_items = []

    add2 = quote_plus(add.lower().replace(' ', ''))
    add3 = add.replace('Debrid', 'Real Debrid')
    name2 = quote_plus(name.lower().replace(' ', ''))
    name = name.replace('url', 'URL Resolver')
    menu_items.append((CONFIG.THEME2.format(name.title()), ' '))
    menu_items.append((CONFIG.THEME3.format('Save {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=save{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Restore {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=restore{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Clear {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=clear{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))

    menu_items.append((CONFIG.THEME2.format('{0} Settings'.format(CONFIG.ADDONTITLE)), 'RunPlugin(plugin://{0}/?mode=settings)'.format(CONFIG.ADDON_ID)))

    return menu_items


def create_save_data_menu(add='', name=''):
    menu_items = []

    add2 = quote_plus(add.lower().replace(' ', ''))
    add3 = add.replace('Debrid', 'Real Debrid')
    name2 = quote_plus(name.lower().replace(' ', ''))
    name = name.replace('url', 'URL Resolver')
    menu_items.append((CONFIG.THEME2.format(name.title()), ' '))
    menu_items.append((CONFIG.THEME3.format('Register {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=auth{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Save {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=save{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Restore {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=restore{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Import {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=import{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Clear Addon {0} Data'.format(add3)), 'RunPlugin(plugin://{0}/?mode=addon{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))

    menu_items.append((CONFIG.THEME2.format('{0} Settings'.format(CONFIG.ADDONTITLE)), 'RunPlugin(plugin://{0}/?mode=settings)'.format(CONFIG.ADDON_ID)))

    return menu_items
