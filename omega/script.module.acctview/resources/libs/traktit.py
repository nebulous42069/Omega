import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import xbmcvfs
import sqlite3

from sqlite3 import Error
from xml.etree import ElementTree
from resources.libs.common.config import CONFIG
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common import var

ORDER = ['seren',
         'fen',
         'fenlt',
         'affen',
         'ezra',
         'coal',
         'pov',
         'umbrella',
         'dradis',
         'taz',
         'shadow',
         'ghost',
         'base19',
         'unleashed',
         'chains',
         'md',
         'asgard',
         'patriot',
         'blackl',
         'aliunde',
         'homelander',
         'quicksilver',
         'genocide',
         'absolution',
         'shazam',
         'thecrew',
         'nightwing',
         'thelab',
         'alvin',
         'moria',
         'nine',
         'scrubs',
         'thelabjr',
         'tmdbhelper',
         'trakt',
         'acctmgr',
         'allact',
         'myact']

TRAKTID = {
   'seren': {
        'name'     : 'Seren',
        'plugin'   : 'plugin.video.seren',
        'saved'    : 'seren',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.seren'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.seren/resources/images', 'ico-seren-3.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.seren/resources/images', 'fanart-seren-3.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'seren_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.seren', 'settings.xml'),
        'default'  : 'trakt.username',
        'data'     : ['trakt.auth', 'trakt.clientid', 'trakt.refresh', 'trakt.secret', 'trakt.username', 'trakt.expires'],
        'activate' : 'Addon.OpenSettings(plugin.video.seren)'},
    'fen': {
        'name'     : 'Fen',
        'plugin'   : 'plugin.video.fen',
        'saved'    : 'fen',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fen'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fen/resources/media/', 'fen_icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.fen/resources/media/', 'fen_fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'fen_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.fen', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.refresh', 'trakt.expires', 'trakt.token', 'trakt.user', 'trakt.indicators_active','watched_indicators'],
        'activate' : 'Addon.OpenSettings(plugin.video.fen)'},
    'fenlt': {
        'name'     : 'Fen Light',
        'plugin'   : 'plugin.video.fenlight',
        'saved'    : 'fenlt',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fenlight'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.fenlight/resources/media/', 'fenlight_icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.fenlight/resources/media/', 'fenlight_fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'fenlt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.fenlight/databases', 'settings.db'),
        'fenlt'    : '',
        'data'     : [],
        'activate' : 'Addon.OpenSettings(plugin.video.fenlight)'},
    'affen': {
        'name'     : 'afFENity',
        'plugin'   : 'plugin.video.affenity',
        'saved'    : 'affen',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.affenity'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.affenity/resources/media/', 'affenity_icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.affenity/resources/media/', 'affenity_fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'affen'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.affenity/databases', 'settings.db'),
        'fenlt'    : '',
        'data'     : [],
        'activate' : 'Addon.OpenSettings(plugin.video.affenity)'},
    'ezra': {
        'name'     : 'Ezra',
        'plugin'   : 'plugin.video.ezra',
        'saved'    : 'ezra',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.ezra'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.ezra', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.ezra', 'fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'ezra_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.ezra', 'settings.xml'),
        'default'  : 'trakt_user',
        'data'     : ['trakt.expires', 'trakt.token', 'trakt_user', 'trakt.indicators_active','watched_indicators'],
        'activate' : 'Addon.OpenSettings(plugin.video.ezra)'},
    'coal': {
        'name'     : 'The Coalition',
        'plugin'   : 'plugin.video.coalition',
        'saved'    : 'coal',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.coalition', 'fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'coal_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.coalition', 'settings.xml'),
        'default'  : 'trakt_user',
        'data'     : ['trakt.refresh', 'trakt.expires', 'trakt.token', 'trakt_user', 'trakt.indicators_active','watched_indicators'],
        'activate' : 'Addon.OpenSettings(plugin.video.coalition)'},
    'pov': {
        'name'     : 'POV',
        'plugin'   : 'plugin.video.pov',
        'saved'    : 'pov',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.pov', 'fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'pov_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.pov', 'settings.xml'),
        'default'  : 'trakt_user',
        'data'     : ['trakt.refresh', 'trakt.expires', 'trakt.token', 'trakt_user', 'trakt.indicators_active','watched_indicators'],
        'activate' : 'Addon.OpenSettings(plugin.video.pov)'},
    'umbrella': {
        'name'     : 'Umbrella',
        'plugin'   : 'plugin.video.umbrella',
        'saved'    : 'umbrella',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.umbrella', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'umbrella_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.umbrella', 'settings.xml'),
        'default'  : 'trakt.user.name',
        'data'     : ['trakt.clientid', 'trakt.clientsecret', 'trakt.user.token', 'trakt.user.name', 'trakt.token.expires', 'trakt.refreshtoken', 'traktuserkey.customenabled'],
        'activate' : 'Addon.OpenSettings(plugin.video.umbrella)'},
    'dradis': {
        'name'     : 'Dradis',
        'plugin'   : 'plugin.video.dradis',
        'saved'    : 'dradis',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dradis'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.dradis', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.dradis', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'dradis_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.dradis', 'settings.xml'),
        'default'  : 'trakt.username',
        'data'     : ['trakt.token', 'trakt.username', 'trakt.expires', 'trakt.refresh', 'trakt.isauthed'],
        'activate' : 'Addon.OpenSettings(plugin.video.dradis)'},
    'taz': {
        'name'     : 'Taz19',
        'plugin'   : 'plugin.video.taz19',
        'saved'    : 'taz',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.taz19'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.taz19', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.taz19', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'taz_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.taz19', 'settings.xml'),
        'default'  : 'trakt_user',
        'data'     : ['trakt.token', 'trakt_user', 'trakt.expires', 'trakt_indicators_active', 'watched_indicators'],
        'activate' : 'Addon.OpenSettings(plugin.video.taz19)'},
    'shadow': {
        'name'     : 'Shadow',
        'plugin'   : 'plugin.video.shadow',
        'saved'    : 'shadow',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.shadow'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.shadow', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.shadow', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'shadow_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.shadow', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.shadow)'},
    'ghost': {
        'name'     : 'Ghost',
        'plugin'   : 'plugin.video.ghost',
        'saved'    : 'ghost',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.ghost'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.ghost', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.ghost', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'ghost_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.ghost', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.ghost)'},
    'base19': {
        'name'     : 'Base 19',
        'plugin'   : 'plugin.video.base19',
        'saved'    : 'base19',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.base19'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.base19', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.base19', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'base19_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.base19', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.base19)'},
    'unleashed': {
        'name'     : 'Unleashed',
        'plugin'   : 'plugin.video.unleashed',
        'saved'    : 'unleashed',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.unleashed'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.unleashed', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.unleashed', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'unleashed_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.unleashed', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.unleashed)'},
    'chains': {
        'name'     : 'Chains Reaction',
        'plugin'   : 'plugin.video.thechains',
        'saved'    : 'chains',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thechains'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thechains', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.thechains', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'chains_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.thechains', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.thechains)'},
    'md': {
        'name'     : 'Magic Dragon',
        'plugin'   : 'plugin.video.magicdragon',
        'saved'    : 'md',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.magicdragon'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.magicdragon', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.magicdragon', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'md_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.magicdragon', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.magicdragon)'},
    'asgard': {
        'name'     : 'Asgard',
        'plugin'   : 'plugin.video.asgard',
        'saved'    : 'asgard',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.asgard'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.asgard', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.asgard', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'asgard_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.asgard', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.asgard)'},
    'patriot': {
        'name'     : 'Patriot',
        'plugin'   : 'plugin.video.patriot',
        'saved'    : 'patriot',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.patriot'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.patriot', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.patriot', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'patriot_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.patriot', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.patriot)'},
    'blackl': {
        'name'     : 'Black Lightning',
        'plugin'   : 'plugin.video.blacklightning',
        'saved'    : 'blackl',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.blacklightning'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.blacklightning', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.blacklightning', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'blackl_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.blacklightning', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.blacklightning)'},
    'aliunde': {
        'name'     : 'Aliunde K19',
        'plugin'   : 'plugin.video.aliundek19',
        'saved'    : 'aliunde',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.aliundek19'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.aliundek19', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.aliundek19', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'aliunde_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.aliundek19', 'settings.xml'),
        'default'  : 'trakt_access_token',
        'data'     : ['trakt_expires_at', 'trakt_refresh_token', 'trakt_access_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.aliundek19)'},
   'homelander': {
        'name'     : 'Homelander',
        'plugin'   : 'plugin.video.homelander',
        'saved'    : 'homelander',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.homelander'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.homelander', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.homelander', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'homelander_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.homelander', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.homelander)'},
   'quicksilver': {
        'name'     : 'Quicksilver',
        'plugin'   : 'plugin.video.quicksilver',
        'saved'    : 'quicksilver',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.quicksilver'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.quicksilver', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.quicksilver', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'quicksilver_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.quicksilver', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.quicksilver)'},
   'genocide': {
        'name'     : 'Chains Genocide',
        'plugin'   : 'plugin.video.chainsgenocide',
        'saved'    : 'genocide',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.chainsgenocide'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.chainsgenocide', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.chainsgenocide', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'genocide_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.chainsgenocide', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.chainsgenocide)'},
   'absolution': {
        'name'     : 'Absolution',
        'plugin'   : 'plugin.video.absolution',
        'saved'    : 'absolution',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.absolution'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.absolution', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.absolution', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'absolution_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.absolution', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.absolution)'},
   'shazam': {
        'name'     : 'Shazam',
        'plugin'   : 'plugin.video.shazam',
        'saved'    : 'shazam',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.shazam'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.shazam', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.shazam', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'shazam_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.shazam', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.shazam)'},
   'thecrew': {
        'name'     : 'The Crew',
        'plugin'   : 'plugin.video.thecrew',
        'saved'    : 'thecrew',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thecrew'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thecrew', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.thecrew', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'thecrew_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.thecrew', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.refresh', 'trakt.token', 'trakt.user'],
        'activate' : 'Addon.OpenSettings(plugin.video.thecrew)'},
   'nightwing': {
        'name'     : 'Nightwing',
        'plugin'   : 'plugin.video.nightwing',
        'saved'    : 'nightwing',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.nightwing'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.nightwing', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.nightwing', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'nightwing_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.nightwing', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.client_id', 'trakt.client_secret', 'trakt.refresh', 'trakt.token', 'trakt.user'],
        'activate' : 'Addon.OpenSettings(plugin.video.nightwing)'},
   'thelab': {
        'name'     : 'TheLab',
        'plugin'   : 'plugin.video.thelab',
        'saved'    : 'thelab',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thelab'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thelab', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.thelab', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'thelab_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.thelab', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.thelab)'},
   'alvin': {
        'name'     : 'Alvin',
        'plugin'   : 'plugin.video.alvin',
        'saved'    : 'alvin',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.alvin'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.alvin', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.alvin', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'alvin_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.alvin', 'settings.xml'),
        'default'  : 'trakt.token',
        'data'     : ['trakt.client_id', 'trakt.client_secret', 'trakt.refresh', 'trakt.token', 'trakt.user'],
        'activate' : 'Addon.OpenSettings(plugin.video.alvin)'},
   'moria': {
        'name'     : 'Moria',
        'plugin'   : 'plugin.video.moria',
        'saved'    : 'moria',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.moria'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.moria', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.moria', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'moria_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.moria', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.moria)'},
   'nine': {
        'name'     : '9 Lives',
        'plugin'   : 'plugin.video.nine',
        'saved'    : 'nine',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.nine'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.nine', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.nine', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'nine_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.nine', 'settings.xml'),
        'default'  : 'trakt.token',
        'data'     : ['trakt.authed', 'trakt.user', 'trakt.token' 'trakt.refresh', 'trakt.client_id', 'trakt.client_secret'],
        'activate' : 'Addon.OpenSettings(plugin.video.nine)'},
   'scrubs': {
        'name'     : 'Scrubs V2',
        'plugin'   : 'plugin.video.scrubsv2',
        'saved'    : 'scrubsv2',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.scrubsv2'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.scrubsv2/resources/images', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.scrubsv2/resources/images', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'scrubsv2_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.scrubsv2', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.refresh', 'trakt.token', 'trakt.user'],
        'activate' : 'Addon.OpenSettings(plugin.video.scrubsv2)'},
   'thelabjr': {
        'name'     : 'TheLabjr',
        'plugin'   : 'plugin.video.thelabjr',
        'saved'    : 'thelabjr',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thelabjr'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.thelabjr/resources/images', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.thelabjr/resources/images', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'thelabjr_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.thelabjr', 'settings.xml'),
        'default'  : 'trakt.user',
        'data'     : ['trakt.refresh', 'trakt.token', 'trakt.user'],
        'activate' : 'Addon.OpenSettings(plugin.video.thelabjr)'},
   'tmdbhelper': {
        'name'     : 'TMDB Helper',
        'plugin'   : 'plugin.video.themoviedb.helper',
        'saved'    : 'tmdbhelper',
        'path'     : os.path.join(CONFIG.ADDONS, 'plugin.video.themoviedb.helper'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'plugin.video.themoviedb.helper', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'plugin.video.themoviedb.helper', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'tmdbhelper_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'plugin.video.themoviedb.helper', 'settings.xml'),
        'default'  : 'trakt_token',
        'data'     : ['trakt_token'],
        'activate' : 'Addon.OpenSettings(plugin.video.themoviedb.helper)'},
   'trakt': {
        'name'     : 'Trakt Add-on',
        'plugin'   : 'script.trakt',
        'saved'    : 'trakt',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.trakt'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.trakt', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.trakt', 'fanart.jpg'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'trakt_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.trakt', 'settings.xml'),
        'default'  : 'user',
        'data'     : ['authorization', 'user'],
        'activate' : 'Addon.OpenSettings(script.trakt)'},
   'acctmgr': {
        'name'     : 'Account Manager',
        'plugin'   : 'script.module.accountmgr',
        'saved'    : 'acctmgr',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.accountmgr'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.accountmgr', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.accountmgr', 'fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'acctmgr_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.accountmgr', 'settings.xml'),
        'default'  : 'trakt.username',
        'data'     : ['trakt.client.id','trakt.client.secret', 'traktuserkey.enabled', 'trakt.expires', 'trakt.refresh', 'trakt.token', 'trakt.username'],
        'activate' : 'Addon.OpenSettings(script.module.accountmgr)'},
   'allact': {
        'name'     : 'All Accounts',
        'plugin'   : 'script.module.allaccounts',
        'saved'    : 'allact',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.allaccounts', 'fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'allact_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.allaccounts', 'settings.xml'),
        'default'  : 'trakt.username',
        'data'     : ['trakt.client.id', 'trakt.client.secret', 'trakt.expires', 'trakt.refresh', 'trakt.token', 'trakt.username'],
        'activate' : 'Addon.OpenSettings(script.module.allaccounts)'},
   'myact': {
        'name'     : 'My Accounts',
        'plugin'   : 'script.module.myaccounts',
        'saved'    : 'myact',
        'path'     : os.path.join(CONFIG.ADDONS, 'script.module.myaccounts'),
        'icon'     : os.path.join(CONFIG.ADDONS, 'script.module.myaccounts', 'icon.png'),
        'fanart'   : os.path.join(CONFIG.ADDONS, 'script.module.myaccounts', 'fanart.png'),
        'file'     : os.path.join(CONFIG.TRAKTFOLD, 'myact_trakt'),
        'settings' : os.path.join(CONFIG.ADDON_DATA, 'script.module.myaccounts', 'settings.xml'),
        'default'  : 'trakt.username',
        'data'     : ['trakt.client.id', 'trakt.client.secret', 'trakt.expires', 'trakt.refresh', 'trakt.token', 'trakt.username'],
        'activate' : 'Addon.OpenSettings(script.module.myaccounts)'}
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
        xbmc.log('%s: Traktit.py Failed!' % var.amgr, xbmc.LOGINFO)
        pass
    
def trakt_user(who):
    user = None
    if TRAKTID[who]:
        name = TRAKTID[who]['name']
        if os.path.exists(TRAKTID[who]['path']) and name == 'Fen Light':
            try:
                # Create database connection
                conn = create_conn(var.fenlt_settings_db)
                with conn:
                    cur = conn.cursor()
                    cur.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('trakt.token',)) #Get setting to compare
                    auth = cur.fetchone()
                    user_data = str(auth)

                    if user_data == "('empty_setting',)" or user_data == "('',)" or user_data == '' or user_data == None: #Check if addon is authorized
                        user = None #Return if not authorized
                    else:
                        user = user_data #Return if authorized
                    cur.close()
            except:
                xbmc.log('%s: Traktit Fen Light Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        elif os.path.exists(TRAKTID[who]['path']) and name == 'afFENity':
            try:
                conn = create_conn(var.affen_settings_db)
                with conn:
                    cur = conn.cursor()
                    cur.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('trakt.token',))
                    auth = cur.fetchone()
                    user_data = str(auth)

                    if user_data == "('empty_setting',)" or user_data == "('',)" or user_data == '' or user_data == None:
                        user = None
                    else:
                        user = user_data
                    cur.close()
            except:
                xbmc.log('%s: Traktit afFENity Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        else:
            if os.path.exists(TRAKTID[who]['path']):
                try:
                    add = tools.get_addon_by_id(TRAKTID[who]['plugin'])
                    user = add.getSetting(TRAKTID[who]['default'])
                except:
                    pass
    return user

def trakt_it(do, who):
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.TRAKTFOLD):
        os.makedirs(CONFIG.TRAKTFOLD)
    if who == 'all':
        for log in ORDER:
            if os.path.exists(TRAKTID[log]['path']):
                try:
                    addonid = tools.get_addon_by_id(TRAKTID[log]['plugin'])
                    default = TRAKTID[log]['default']
                    user = addonid.getSetting(default)

                    update_trakt(do, log)
                except:
                    pass
            else:
                logging.log('[Trakt Data] {0}({1}) is not installed'.format(TRAKTID[log]['name'], TRAKTID[log]['plugin']), level=xbmc.LOGERROR)
        CONFIG.set_setting('traktnextsave', tools.get_date(days=3, formatted=True))
    else:
        if TRAKTID[who]:
            if os.path.exists(TRAKTID[who]['path']):
                update_trakt(do, who)
        else:
            logging.log('[Trakt Data] Invalid Entry: {0}'.format(who), level=xbmc.LOGERROR)

def trakt_it_revoke(do, who):
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.TRAKTFOLD):
        os.makedirs(CONFIG.TRAKTFOLD)
    if who == 'all':
        for log in ORDER:
            if os.path.exists(TRAKTID[log]['path']):
                try:
                    addonid = tools.get_addon_by_id(TRAKTID[log]['plugin'])
                    default = TRAKTID[log]['default']
                    user = addonid.getSetting(default)

                    update_trakt(do, log)
                except:
                    pass
            else:
                logging.log('[Trakt Data] {0}({1}) is not installed'.format(TRAKTID[log]['name'], TRAKTID[log]['plugin']), level=xbmc.LOGERROR)
        CONFIG.set_setting('traktnextsave', tools.get_date(days=3, formatted=True))
    else:
        if TRAKTID[who]:
            if os.path.exists(TRAKTID[who]['path']):
                update_trakt(do, who)
        else:
            logging.log('[Trakt Data] Invalid Entry: {0}'.format(who), level=xbmc.LOGERROR)

def trakt_it_restore(do, who):
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.TRAKTFOLD):
        os.makedirs(CONFIG.TRAKTFOLD)
    if who == 'all':
        for log in ORDER:
            if os.path.exists(TRAKTID[log]['path']):
                try:
                    addonid = tools.get_addon_by_id(TRAKTID[log]['plugin'])
                    default = TRAKTID[log]['default']
                    user = addonid.getSetting(default)

                    update_trakt(do, log)
                except:
                    pass
            else:
                logging.log('[Trakt Data] {0}({1}) is not installed'.format(TRAKTID[log]['name'], TRAKTID[log]['plugin']), level=xbmc.LOGERROR)
        CONFIG.set_setting('traktnextsave', tools.get_date(days=3, formatted=True))
    else:
        if TRAKTID[who]:
            if os.path.exists(TRAKTID[who]['path']):
                update_trakt(do, who)
        else:
            logging.log('[Trakt Data] Invalid Entry: {0}'.format(who), level=xbmc.LOGERROR)
    restore_trakt() #Restore API keys for all add-ons


def clear_saved(who, over=False):
    if who == 'all':
        for trakt in TRAKTID:
            clear_saved(trakt,  True)
    elif TRAKTID[who]:
        file = TRAKTID[who]['file']
        if os.path.exists(file):
            os.remove(file)
    if not over:
        xbmc.executebuiltin('Container.Refresh()')


def update_trakt(do, who):
    file = TRAKTID[who]['file']
    settings = TRAKTID[who]['settings']
    data = TRAKTID[who]['data']
    addonid = tools.get_addon_by_id(TRAKTID[who]['plugin'])
    saved = TRAKTID[who]['saved']
    default = TRAKTID[who]['default']
    user = addonid.getSetting(default)
    suser = CONFIG.get_setting(saved)
    name = TRAKTID[who]['name']
    icon = TRAKTID[who]['icon']

    if do == 'update':
        if not user == '':
            try:
                root = ElementTree.Element(saved)

                for setting in data:
                    trakt = ElementTree.SubElement(root, 'trakt')
                    id = ElementTree.SubElement(trakt, 'id')
                    id.text = setting
                    value = ElementTree.SubElement(trakt, 'value')
                    value.text = addonid.getSetting(setting)

                tree = ElementTree.ElementTree(root)
                tree.write(file)

                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)
                logging.log('Trakt Data Saved for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Trakt Data] Unable to Update {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('Trakt Data Not Registered for {0}'.format(name))
    elif do == 'restore':
        if os.path.exists(file):
            tree = ElementTree.parse(file)
            root = tree.getroot()

            try:
                for setting in root.findall('trakt'):
                    id = setting.find('id').text
                    value = setting.find('value').text
                    addonid.setSetting(id, value)

                user = addonid.getSetting(default)
                CONFIG.set_setting(saved, user)
                logging.log('Trakt Data Restored for {0}'.format(name), level=xbmc.LOGINFO)
            except Exception as e:
                logging.log("[Trakt Data] Unable to Restore {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        else:
            logging.log('Trakt Data Not Found for {0}'.format(name))
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
                logging.log("[Trakt Data] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
    elif do == 'wipeaddon':
        logging.log('{0} SETTINGS: {1}'.format(name, settings))
        revoke_trakt() #Restore default API keys for all add-ons
        if name == 'Fen Light':
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
                    logging.log("[Trakt Data] Unable to Clear Addon {0} ({1})".format(who, str(e)), level=xbmc.LOGERROR)
        xbmc.executebuiltin('Container.Refresh()')


def auto_update(who):
    if who == 'all':
        for log in TRAKTID:
            if os.path.exists(TRAKTID[log]['path']):
                auto_update(log)
    elif TRAKTID[who]:
        if os.path.exists(TRAKTID[who]['path']):
            u = trakt_user(who)
            su = CONFIG.get_setting(TRAKTID[who]['saved'])
            n = TRAKTID[who]['name']
            if not u or u == '':
                return
            elif su == '':
                trakt_it('update', who)
            elif not u == su:
                dialog = xbmcgui.Dialog()

                if dialog.yesno(CONFIG.ADDONTITLE,
                                    "Would you like to save the [COLOR {0}]Trakt Data[/COLOR] for [COLOR {1}]{2}[/COLOR]?".format(CONFIG.COLOR2, CONFIG.COLOR1, n),
                                    "Addon: [COLOR springgreen][B]{0}[/B][/COLOR]".format(u),
                                    "Saved:[/COLOR] [COLOR red][B]{0}[/B][/COLOR]".format(su) if not su == '' else 'Saved:[/COLOR] [COLOR red][B]None[/B][/COLOR]',
                                    yeslabel="[B][COLOR springgreen]Save Data[/COLOR][/B]",
                                    nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
                    trakt_it('update', who)
            else:
                trakt_it('update', who)


def import_list(who):
    if who == 'all':
        for log in TRAKTID:
            if os.path.exists(TRAKTID[log]['file']):
                import_list(log)
    elif TRAKTID[who]:
        if os.path.exists(TRAKTID[who]['file']):
            file = TRAKTID[who]['file']
            addonid = tools.get_addon_by_id(TRAKTID[who]['plugin'])
            saved = TRAKTID[who]['saved']
            default = TRAKTID[who]['default']
            suser = CONFIG.get_setting(saved)
            name = TRAKTID[who]['name']

            tree = ElementTree.parse(file)
            root = tree.getroot()

            for setting in root.findall('trakt'):
                id = setting.find('id').text
                value = setting.find('value').text

                addonid.setSetting(id, value)

            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, name),
                       '[COLOR {0}]Trakt Data: Imported![/COLOR]'.format(CONFIG.COLOR2))


def open_settings_trakt(who):
    addonid = tools.get_addon_by_id(TRAKTID[who]['plugin'])
    addonid.openSettings()

def revoke_trakt(): #Restore default API keys for all add-ons

        if xbmcvfs.exists(var.chk_seren) and var.setting('traktuserkey.enabled') == 'true': #Check if add-on is installed
            try:
                #Remove Account Mananger API keys from add-on
                with open(var.path_seren,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.seren_client).replace(var.secret_am,var.seren_secret)

                with open(var.path_seren,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Seren Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_fen):
            try:
                with open(var.path_fen,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.fen_client).replace(var.secret_am,var.fen_secret)

                with open(var.path_fen,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Fen Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_fenlt):
            try:
                with open(var.path_fenlt,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.fenlt_client).replace(var.secret_am,var.fenlt_secret)

                with open(var.path_fenlt,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Fen Light Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_coal):
            try:
                with open(var.path_coal,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.coal_client).replace(var.secret_am,var.coal_secret)

                with open(var.path_coal,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Coalition Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_pov):
            try:
                with open(var.path_pov,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.pov_client).replace(var.secret_am,var.pov_secret)

                with open(var.path_pov,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API POV Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_dradis):
            try:
                with open(var.path_dradis,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.dradis_client).replace(var.secret_am,var.dradis_secret)

                with open(var.path_dradis,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Dradis Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_taz):
            try:
                with open(var.path_taz,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.taz_client)

                with open(var.path_taz,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Taz Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_shadow):
            try:
                with open(var.path_shadow,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.shadow_client).replace(var.secret_am,var.shadow_secret)

                with open(var.path_shadow,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Shadow Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_ghost):
            try:
                with open(var.path_ghost,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.ghost_client).replace(var.secret_am,var.ghost_secret)

                with open(var.path_ghost,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Ghost Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_base):
            try:
                with open(var.path_base,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.base_client).replace(var.secret_am,var.base_secret)

                with open(var.path_base,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Base Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_unleashed):
            try:
                with open(var.path_unleashed,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.unleashed_client).replace(var.secret_am,var.unleashed_secret)

                with open(var.path_unleashed,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Unleashed Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_chains):
            try:
                with open(var.path_chains,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.chains_client).replace(var.secret_am,var.chains_secret)

                with open(var.path_chains,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Chain Reaction Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_md):
            try:
                with open(var.path_md,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.md_client).replace(var.secret_am,var.md_secret)

                with open(var.path_md,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Magic Dragon Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_asgard):
            try:
                with open(var.path_asgard,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.asgard_client).replace(var.secret_am,var.asgard_secret)

                with open(var.path_asgard,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Asgard Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_patriot):
            try:
                with open(var.path_patriot,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.patriot_client).replace(var.secret_am,var.patriot_secret)

                with open(var.path_patriot,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Patriot Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_blackl):
            try:
                with open(var.path_blackl,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.blackl_client).replace(var.secret_am,var.blackl_secret)

                with open(var.path_blackl,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Black Lightning Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_aliunde):
            try:
                with open(var.path_aliunde,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.aliunde_client).replace(var.secret_am,var.aliunde_secret)

                with open(var.path_aliunde,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Aliunde Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_crew):
            try:
                with open(var.path_crew,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.crew_client).replace(var.secret_am,var.crew_secret)

                with open(var.path_crew,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API The Crew Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_scrubs):
            try:
                with open(var.path_scrubs,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.scrubs_client).replace(var.secret_am,var.scrubs_secret)

                with open(var.path_scrubs,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Scrubs V2 Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_labjr):
            try:
                with open(var.path_labjr,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.labjr_client).replace(var.secret_am,var.labjr_secret)

                with open(var.path_labjr,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API TheLabjr Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_tmdbh):
            try:
                with open(var.path_tmdbh,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.tmdbh_client).replace(var.secret_am,var.tmdbh_secret)

                with open(var.path_tm,dbh,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API TMDbH Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_trakt):
            try:
                with open(var.path_trakt,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.trakt_client).replace(var.secret_am,var.trakt_secret)

                with open(var.path_trakt,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API Trakt Addon Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_allaccounts):
            try:
                with open(var.path_allaccounts,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.allacts_client).replace(var.secret_am,var.allacts_secret)

                with open(var.path_allaccounts,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API All Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_myaccounts):
            try:
                with open(var.path_myaccounts,'r') as f:
                    data = f.read()

                client = data.replace(var.client_am,var.myacts_client).replace(var.secret_am,var.myacts_secret)

                with open(var.path_myaccounts,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Revoke API My Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                pass

def restore_trakt(): #Restore API Keys to all add-ons

        if xbmcvfs.exists(var.chk_seren) and var.setting('traktuserkey.enabled') == 'true': #Check if add-on is installed
    
            try:
                #Insert Account Mananger API keys into add-on
                with open(var.path_seren,'r') as f:
                    data = f.read()

                client = data.replace(var.seren_client,var.client_am).replace(var.seren_secret,var.secret_am)

                with open(var.path_seren,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Seren Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_fen):
            try:
                with open(var.path_fen,'r') as f:
                    data = f.read()

                client = data.replace(var.fen_client,var.client_am).replace(var.fen_secret,var.secret_am)

                with open(var.path_fen,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Fen Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_fenlt):
            try:
                with open(var.path_fenlt,'r') as f:
                    data = f.read()

                client = data.replace(var.fenlt_client,var.client_am).replace(var.fenlt_secret,var.secret_am)

                with open(var.path_fenlt,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Fen Light Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_coal):
            try:
                with open(var.path_coal,'r') as f:
                    data = f.read()

                client = data.replace(var.coal_client,var.client_am).replace(var.coal_secret,var.secret_am)

                with open(var.path_coal,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Coalition Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_pov):
            try:
                with open(var.path_pov,'r') as f:
                    data = f.read()

                client = data.replace(var.pov_client,var.client_am).replace(var.pov_secret,var.secret_am)

                with open(var.path_pov,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API POV Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_dradis):
            try:
                with open(var.path_dradis,'r') as f:
                    data = f.read()

                client = data.replace(var.dradis_client,var.client_am).replace(var.dradis_secret,var.secret_am)

                with open(var.path_dradis,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Dradis Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_taz):
            try:
                with open(var.path_taz,'r') as f:
                    data = f.read()

                client = data.replace(var.taz_client,var.client_am)

                with open(var.path_taz,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Taz Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_shadow):
            try:
                with open(var.path_shadow,'r') as f:
                    data = f.read()

                client = data.replace(var.shadow_client,var.client_am).replace(var.shadow_secret,var.secret_am)

                with open(var.path_shadow,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Shadow Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_ghost):
            try:
                with open(var.path_ghost,'r') as f:
                    data = f.read()

                client = data.replace(var.ghost_client,var.client_am).replace(var.ghost_secret,var.secret_am)

                with open(var.path_ghost,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Ghost Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_base):
            try:
                with open(var.path_base,'r') as f:
                    data = f.read()

                client = data.replace(var.base_client,var.client_am).replace(var.base_secret,var.secret_am)

                with open(var.path_base,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Base Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_unleashed):
            try:
                with open(var.path_unleashed,'r') as f:
                    data = f.read()

                client = data.replace(var.unleashed_client,var.client_am).replace(var.unleashed_secret,var.secret_am)

                with open(var.path_unleashed,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Unleashed Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_chains):
            try:
                with open(var.path_chains,'r') as f:
                    data = f.read()

                client = data.replace(var.chains_client,var.client_am).replace(var.chains_secret,var.secret_am)

                with open(var.path_chains,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Chain Reaction Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_md):
            try:
                with open(var.path_md,'r') as f:
                    data = f.read()

                client = data.replace(var.md_client,var.client_am).replace(var.md_secret,var.secret_am)

                with open(var.path_md,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Magic Dragon Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        if xbmcvfs.exists(var.chk_asgard):
            try:
                with open(var.path_asgard,'r') as f:
                    data = f.read()

                client = data.replace(var.asgard_client,var.client_am).replace(var.asgard_secret,var.secret_am)

                with open(var.path_asgard,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Asgard Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_patriot):
            try:
                with open(var.path_patriot,'r') as f:
                    data = f.read()

                client = data.replace(var.patriot_client,var.client_am).replace(var.patriot_secret,var.secret_am)

                with open(var.path_patriot,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Patriot Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_blackl):
            try:
                with open(var.path_blackl,'r') as f:
                    data = f.read()

                client = data.replace(var.blackl_client,var.client_am).replace(var.blackl_secret,var.secret_am)

                with open(var.path_blackl,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Black Lightning Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_aliunde):
            try:
                with open(var.path_aliunde,'r') as f:
                    data = f.read()

                client = data.replace(var.aliunde_client,var.client_am).replace(var.aliunde_secret,var.secret_am)

                with open(var.path_aliunde,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Aliunde Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_crew):
            try:
                with open(var.path_crew,'r') as f:
                    data = f.read()

                client = data.replace(var.crew_client,var.client_am).replace(var.crew_secret,var.secret_am)

                with open(var.path_crew,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API The Crew Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_scrubs):
            try:
                with open(var.path_scrubs,'r') as f:
                    data = f.read()

                client = data.replace(var.scrubs_client,var.client_am).replace(var.scrubs_secret,var.secret_am)

                with open(var.path_scrubs,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Scrubs V2 Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_labjr):
            try:
                with open(var.path_labjr,'r') as f:
                    data = f.read()

                client = data.replace(var.labjr_client,var.client_am).replace(var.labjr_secret,var.secret_am)

                with open(var.path_labjr,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API TheLabjr Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_tmdbh):
            try:
                with open(var.path_tmdbh,'r') as f:
                    data = f.read()

                client = data.replace(var.tmdbh_client,var.client_am).replace(var.tmdbh_secret,var.secret_am)

                with open(var.path_tmdbh,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API TMDbH Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_trakt):
            try:
                with open(var.path_trakt,'r') as f:
                    data = f.read()

                client = data.replace(var.trakt_client,var.client_am).replace(var.trakt_secret,var.secret_am)

                with open(var.path_trakt,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API Trakt Addon Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_allaccounts):
            try:
                with open(var.path_allaccounts,'r') as f:
                    data = f.read()

                client = data.replace(var.allacts_client,var.client_am).replace(var.allacts_secret,var.secret_am)

                with open(var.path_allaccounts,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API All Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                pass

        if xbmcvfs.exists(var.chk_myaccounts):
            try:
                with open(var.path_myaccounts,'r') as f:
                    data = f.read()

                client = data.replace(var.myacts_client,var.client_am).replace(var.myacts_secret,var.secret_am)

                with open(var.path_myaccounts,'w') as f:
                    f.write(client)
            except:
                xbmc.log('%s: Traktit.py Restore API My Accounts Failed!' % var.amgr, xbmc.LOGINFO)
                pass
