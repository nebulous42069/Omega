# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file sources.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import os
import sys

import urllib

from urllib.parse import urlencode
from resources.lib.modules.crewruntime import c

import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs
import time
import json

import six

lang = xbmcaddon.Addon().getLocalizedString

lang2 = xbmc.getLocalizedString

setting = xbmcaddon.Addon().getSetting

setSetting = xbmcaddon.Addon().setSetting

addon = xbmcaddon.Addon

addItem = xbmcplugin.addDirectoryItem

addItems = xbmcplugin.addDirectoryItems

item = xbmcgui.ListItem

directory = xbmcplugin.endOfDirectory

content = xbmcplugin.setContent

sortMethod = xbmcplugin.addSortMethod

property = xbmcplugin.setProperty

addonInfo = xbmcaddon.Addon().getAddonInfo

infoLabel = xbmc.getInfoLabel

condVisibility = xbmc.getCondVisibility

jsonrpc = xbmc.executeJSONRPC

window = xbmcgui.Window(10000)

dialog = xbmcgui.Dialog()

progressDialog = xbmcgui.DialogProgress()

progressDialogBG = xbmcgui.DialogProgressBG()

windowDialog = xbmcgui.WindowDialog()

button = xbmcgui.ControlButton

image = xbmcgui.ControlImage

getCurrentDialogId = xbmcgui.getCurrentWindowDialogId()

keyboard = xbmc.Keyboard

monitor = xbmc.Monitor()

execute = xbmc.executebuiltin

skin = xbmc.getSkinDir()

player = xbmc.Player()

playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

resolve = xbmcplugin.setResolvedUrl

legalFilename = xbmcvfs.makeLegalFilename

openFile = xbmcvfs.File

makeFile = xbmcvfs.mkdir

deleteFile = xbmcvfs.delete

deleteDir = xbmcvfs.rmdir

listDir = xbmcvfs.listdir

transPath = xbmcvfs.translatePath

skinPath = transPath('special://skin/')

addonPath = transPath(addonInfo('path'))

dataPath = transPath(addonInfo('profile'))

settingsFile = os.path.join(dataPath, 'settings.xml')

viewsFile = os.path.join(dataPath, 'views.db')

bookmarksFile = os.path.join(dataPath, 'bookmarks.db')

providercacheFile = os.path.join(dataPath, 'providers.13.db')

metacacheFile = os.path.join(dataPath, 'meta.5.db')

searchFile = os.path.join(dataPath, 'search.1.db')

libcacheFile = os.path.join(dataPath, 'library.db')

cacheFile = os.path.join(dataPath, 'cache.db')

dbFile = os.path.join(dataPath, 'debridcache.db')

dbSettings = os.path.join(dataPath, 'settings.db')

#key = "RgUkXp2s5v8x/A?D(G+KbPeShVmYq3t6"

#iv = "p2s5v8y/B?E(H+Mb"

integer = 1000


def six_encode(txt, char='utf-8', errors='replace'):
    if six.PY2 and isinstance(txt, six.text_type):
        txt = txt.encode(char, errors=errors)
    return txt

def six_decode(txt, char='utf-8', errors='replace'):
    if six.PY3 and isinstance(txt, six.binary_type):
        txt = txt.decode(char, errors=errors)
    return txt


# Modified `sleep` command that honors a user exit request
def sleep(time):
    while time > 0 and not monitor.abortRequested():
        xbmc.sleep(min(100, time))
        time = time - 100


def getKodiVersion(as_string = False, as_full = False):

    main_version = xbmc.getInfoLabel("System.BuildVersion")
    version = xbmc.getInfoLabel("System.BuildVersion").split(".")[0]
    v_major = str(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
    v_minor = str(xbmc.getInfoLabel("System.BuildVersion").split(".")[1])
    v_debug = str(xbmc.getInfoLabel("System.BuildVersion").split(".")[2])
    if(as_string == True):
        if (as_full == False):
            return version
        else:
            return (v_major + '.' + v_minor + '.' +  v_debug)
    return int(version)


def metadataClean(metadata): # Filter out non-existing/custom keys. Otherise there are tons of errors in Kodi 18 log.
    if metadata == None: return metadata
    allowed = ['genre', 'country', 'year', 'episode', 'season', 'sortepisode', 'sortseason', 'episodeguide', 'showlink', 'top250', 'setid', 'tracknumber', 'rating', 'userrating', 'watched', 'playcount', 'overlay', 'cast', 'castandrole', 'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle', 'sorttitle', 'duration', 'studio', 'tagline', 'writer', 'tvshowtitle', 'premiered', 'status', 'set', 'setoverview', 'tag', 'imdbnumber', 'code', 'aired', 'credits', 'lastplayed', 'album', 'artist', 'votes', 'path', 'trailer', 'dateadded', 'mediatype', 'dbid']
    return {k: v for k, v in six.iteritems(metadata) if k in allowed}

def addonIcon():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'icon.png')
    return addonInfo('icon')


def addonThumb():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'poster.png')
    elif theme == '-':
        return 'DefaultFolder.png'
    return addonInfo('icon')


def addonPoster():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'poster.png')
    return 'DefaultVideo.png'


def addonBanner():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'banner.png')
    return 'DefaultVideo.png'


def addonFanart():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'fanart.jpg')
    return addonInfo('fanart')


def addonClearart():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'clearart.png')
    return ''

def addonDiscart():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'discart.png')
    return ''

def addonClearlogo():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'clearlogo.png')
    return ''


def addonNext():
    theme = appearance()
    art = artPath()
    if not (art is None and theme in ['-', '']):
        return os.path.join(art, 'next.png')
    return 'DefaultVideo.png'


def addonId():
    return addonInfo('id')


def addonName():
    return addonInfo('name')


def get_plugin_url(queries):
    try:
        query = urllib.parse.urlencode(queries)
    except UnicodeEncodeError:
        for k in queries:
            if isinstance(queries[k], six.text_type):
                queries[k] = six_encode(queries[k])
        query = urllib.parse.urlencode(queries)
    addon_id = sys.argv[0]
    if not addon_id:
        addon_id = addonId()
    return addon_id + '?' + query


def artPath():
    theme = appearance()
    if theme in ['-', '']:
        return
    elif condVisibility('System.HasAddon(script.thecrew.artwork)'):
        return os.path.join(xbmcaddon.Addon('script.thecrew.artwork').getAddonInfo('path'), 'resources', 'media', theme)

def appearance():
    appearance = setting('appearance.1').lower() if condVisibility('System.HasAddon(script.thecrew.artwork)') else setting('appearance.alt').lower()
    return appearance


def artwork():
    execute('RunPlugin(plugin://script.thecrew.artwork)')


def infoDialog(message, heading=addonInfo('name'), icon='', time=3000, sound=False):
    if icon == '':
        icon = addonIcon()
    elif icon == 'INFO':
        icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING':
        icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR':
        icon = xbmcgui.NOTIFICATION_ERROR
    dialog.notification(heading, message, icon, time, sound=sound)

def startupMaintenance():

    import requests
    from resources.lib.modules import keys

    from sqlite3 import dbapi2 as db

    try:

        tmdb_session = requests.Session()
        days = 7
        diff_time = (86400 * days)

        tmdb_user = setting('tm.personal_user') or setting('tm.user')
        if not tmdb_user: tmdb_user = keys.tmdb_key

        settings_table = 'settings'
        makeFile(dataPath)
        dbcon = db.connect(dbSettings)
        dbcur = dbcon.cursor()

        now = int(time.time())
        dbcur.execute("CREATE TABLE IF NOT EXISTS {} (""id INTEGER, secure_base_url TEXT, ""backdrop_sizes TEXT, ""logo_sizes TEXT, ""poster_sizes TEXT, ""profile_sizes TEXT, ""still_sizes TEXT, ""added TEXT, UNIQUE(id)"")".format(settings_table))

        dbcur.execute(f"SELECT * FROM {settings_table} WHERE added < ({now} - {diff_time}) AND id = 1")
        row = dbcur.fetchone()

        if(row == None):
            url = "https://api.themoviedb.org/3/configuration?api_key=%s" % tmdb_user
            result = tmdb_session.get(url, timeout=16).json()

            result = result['images']
            s_base_url = result['secure_base_url']
            b_sizes = result['backdrop_sizes'] if len(result['backdrop_sizes']) == 4 else result['backdrop_sizes'][-4:]
            l_sizes = result['logo_sizes'] if len(result['logo_sizes']) == 4 else result['logo_sizes'][-4:]
            p_sizes = result['poster_sizes'] if len(result['poster_sizes']) == 4 else result['poster_sizes'][-4:]
            pr_sizes = result['profile_sizes'] if len(result['profile_sizes']) == 4 else result['profile_sizes'][-4:]
            s_sizes = result['still_sizes'] if len(result['still_sizes']) == 4 else result['still_sizes'][-4:]


            _id = 1
            b_size = json.dumps(b_sizes)
            l_size = json.dumps(l_sizes)
            p_size = json.dumps(p_sizes)
            pr_size = json.dumps(pr_sizes)
            s_size = json.dumps(s_sizes)

            dbcur.execute(f"INSERT INTO settings_table VALUES ({_id}, {s_base_url}, {b_size}, {l_size}, {p_size}, {pr_size}, {s_size}, {now}) ON CONFLICT ({_id}) UPDATE secure_base_url = {s_base_url}, backdrop_sizes = {b_size}, " % settings_table, (_id, s_base_url, json.dumps(b_sizes), json.dumps(l_sizes), json.dumps(p_sizes), json.dumps(pr_sizes), json.dumps(s_sizes), now))

        dbcur.execute(f"SELECT * FROM {settings_table} WHERE id = 2")
        row = dbcur.fetchone()
        if(row == None):
            dbcur.execute("REPLACE INTO %s VALUES (?, ?, ?, ?, ?, ?, ?, ?)" % settings_table, (2, setting('fanart.quality'), b_sizes[int(setting('fanart.quality'))], l_sizes[int(setting('fanart.quality'))], p_sizes[int(setting('fanart.quality'))], pr_sizes[int(setting('fanart.quality'))], s_sizes[int(setting('fanart.quality'))], now))

        dbcon.commit()


    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        xbmc.log('[CM Debug @ 341 in control.py]Traceback:: ' + str(failure))
        xbmc.log('[CM Debug @ 341 in control.py]Exception raised. Error = ' + str(e))
        #xbmc.log('[ script.module.thecrew ] Exception raised in. Error =' + str(e))   
        pass

#    finally:
#        db.close()

def setSizes():
    from sqlite3 import dbapi2 as db

    settings_table = 'settings'
    makeFile(dataPath)
    dbcon = db.connect(dbSettings)
    dbcur = dbcon.cursor()

    dbcur.execute(f"SELECT * FROM {settings_table} WHERE id = 2")
    row = dbcur.fetchone()

    dbcon.commit()


def updateSizes():
    try:
        from sqlite3 import dbapi2 as db

        settings_table = 'settings'
        makeFile(dataPath)
        dbcon = db.connect(dbSettings)
        dbcur = dbcon.cursor()


        dbcur.execute(f"SELECT * FROM {settings_table} WHERE id = 2")


        row = dbcur.fetchone()

        xbmc.log('[debug @ 395 in control.py]row = ' + repr(row))

        dbcon.commit()
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        xbmc.log('[CM Debug @ 402 in control.py]Traceback:: ' + str(failure))
        xbmc.log('[CM Debug @ 403 in control.py]Exception raised. Error = ' + str(e))
        #xbmc.log('[ script.module.thecrew ] Exception raised in. Error =' + str(e))   
        pass



def setFanartQuality():
    from sqlite3 import dbapi2 as db
    try:
        settings_table = 'settings'
        makeFile(dataPath)
        dbcon = db.connect(dbSettings)
        dbcur = dbcon.cursor()

        dbcur.execute(f"SELECT * FROM {settings_table} WHERE id = 1")
        row = dbcur.fetchone()
        c.log('[CM Debug @ 384 in control.py] row =' + repr(row))   
        dbcon.commit()
    except Exception as e:
        import traceback
        failure = traceback.format_exc()
        c.log('[CM Debug @ 390 in control.py]Traceback:: ' + str(failure))
        c.log('[CM Debug @ 391 in control.py]Exception raised. Error = ' + str(e))
        pass




def yesnoDialog(message, heading=addonInfo('name'), nolabel='', yeslabel=''):
    return dialog.yesno(heading, message, nolabel, yeslabel)
#TC 2/01/19 started

def selectDialog(list, heading=addonInfo('name'), useDetails=False):
    return dialog.select(heading, list, useDetails=useDetails)

def metaFile():
         return os.path.join(dataPath, 'meta.db')

def metaFile_old():
    if condVisibility('System.HasAddon(script.thecrew.metadata)'):
        return os.path.join( xbmcaddon.Addon('script.thecrew.metadata').getAddonInfo('path'), 'resources', 'data', 'meta.db')

def apiLanguage(ret_name=None):
    langDict = {
        'Bulgarian': 'bg', 'Chinese': 'zh', 'Croatian': 'hr', 'Czech': 'cs', 'Danish': 'da', 'Dutch': 'nl',
        'English': 'en', 'Finnish': 'fi', 'French': 'fr', 'German': 'de', 'Greek': 'el', 'Hebrew': 'he',
        'Hungarian': 'hu', 'Italian': 'it', 'Japanese': 'ja', 'Korean': 'ko', 'Norwegian': 'no', 'Polish': 'pl',
        'Portuguese': 'pt', 'Romanian': 'ro', 'Russian': 'ru', 'Serbian': 'sr', 'Slovak': 'sk', 'Slovenian': 'sl',
        'Spanish': 'es', 'Swedish': 'sv', 'Thai': 'th', 'Turkish': 'tr', 'Ukrainian': 'uk'}


    trakt = ['bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'he', 'hr', 'hu', 'it', 'ja',
             'ko', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sr', 'sv', 'th', 'tr', 'uk', 'zh']
    tvdb = ['en', 'sv', 'no', 'da', 'fi', 'nl', 'de', 'it', 'es', 'fr', 'pl',
            'hu', 'el', 'tr', 'ru', 'he', 'ja', 'pt', 'zh', 'cs', 'sl', 'hr', 'ko']

    youtube = ['gv', 'gu', 'gd', 'ga', 'gn', 'gl', 'ty', 'tw', 'tt', 'tr', 'ts', 'tn', 'to', 'tl', 'tk', 'th', 'ti',
               'tg', 'te', 'ta', 'de', 'da', 'dz', 'dv', 'qu', 'zh', 'za', 'zu', 'wa', 'wo', 'jv', 'ja', 'ch', 'co',
               'ca', 'ce', 'cy', 'cs', 'cr', 'cv', 'cu', 'ps', 'pt', 'pa', 'pi', 'pl', 'mg', 'ml', 'mn', 'mi', 'mh',
               'mk', 'mt', 'ms', 'mr', 'my', 've', 'vi', 'is', 'iu', 'it', 'vo', 'ii', 'ik', 'io', 'ia', 'ie', 'id',
               'ig', 'fr', 'fy', 'fa', 'ff', 'fi', 'fj', 'fo', 'ss', 'sr', 'sq', 'sw', 'sv', 'su', 'st', 'sk', 'si',
               'so', 'sn', 'sm', 'sl', 'sc', 'sa', 'sg', 'se', 'sd', 'lg', 'lb', 'la', 'ln', 'lo', 'li', 'lv', 'lt',
               'lu', 'yi', 'yo', 'el', 'eo', 'en', 'ee', 'eu', 'et', 'es', 'ru', 'rw', 'rm', 'rn', 'ro', 'be', 'bg',
               'ba', 'bm', 'bn', 'bo', 'bh', 'bi', 'br', 'bs', 'om', 'oj', 'oc', 'os', 'or', 'xh', 'hz', 'hy', 'hr',
               'ht', 'hu', 'hi', 'ho', 'ha', 'he', 'uz', 'ur', 'uk', 'ug', 'aa', 'ab', 'ae', 'af', 'ak', 'am', 'an',
               'as', 'ar', 'av', 'ay', 'az', 'nl', 'nn', 'no', 'na', 'nb', 'nd', 'ne', 'ng', 'ny', 'nr', 'nv', 'ka',
               'kg', 'kk', 'kj', 'ki', 'ko', 'kn', 'km', 'kl', 'ks', 'kr', 'kw', 'kv', 'ku', 'ky']


    #CM - As of 2022/12/08 these are the official supported TMDB languages
    langDictTMDB = {'Abkhazian':'ab', 'Afar':'aa', 'Afrikaans':'af', 'Akan':'ak', 'Albanian':'sq',
                    'Amharic':'am', 'Arabic':'ar', 'Aragonese':'an', 'Armenian':'hy', 'Assamese':'as',
                    'Avaric':'av', 'Avestan':'ae', 'Aymara':'ay', 'Azerbaijani':'az', 'Bambara':'bm',
                    'Bashkir':'ba', 'Basque':'eu', 'Belarusian':'be', 'Bengali':'bn', 'Bislama':'bi',
                    'Bosnian':'bs', 'Breton':'br', 'Bulgarian':'bg', 'Burmese':'my', 'Cantonese':'cn',
                    'Catalan':'ca', 'Chamorro':'ch', 'Chechen':'ce', 'Chichewa Nyanja':'ny',
                    'Chuvash':'cv', 'Cornish':'kw', 'Corsican':'co', 'Cree':'cr', 'Croatian':'hr',
                    'Czech':'cs', 'Danish':'da', 'Divehi':'dv', 'Dutch':'nl', 'Dzongkha':'dz',
                    'English':'en', 'Esperanto':'eo', 'Estonian':'et', 'Ewe':'ee', 'Faroese':'fo',
                    'Fijian':'fj', 'Finnish':'fi', 'French':'fr', 'Frisian':'fy', 'Fulah':'ff',
                    'Gaelic':'gd', 'Galician':'gl', 'Ganda':'lg', 'Georgian':'ka', 'German':'de',
                    'Greek':'el', 'Guarani':'gn', 'Gujarati':'gu', 'Haitian':'ht', 'Hausa':'ha',
                    'Hebrew':'he', 'Herero':'hz', 'Hindi':'hi', 'Hiri Motu':'ho', 'Hungarian':'hu',
                    'Icelandic':'is', 'Ido':'io', 'Igbo':'ig', 'Indonesian':'id', 'Interlingua':'ia',
                    'Interlingue':'ie', 'Inuktitut':'iu', 'Inupiaq':'ik', 'Irish':'ga', 'Italian':'it',
                    'Japanese':'ja', 'Javanese':'jv', 'Kalaallisut':'kl', 'Kannada':'kn', 'Kanuri':'kr',
                    'Kashmiri':'ks', 'Kazakh':'kk', 'Khmer':'km', 'Kikuyu':'ki', 'Kinyarwanda':'rw',
                    'Kirghiz':'ky', 'Komi':'kv', 'Kongo':'kg', 'Korean':'ko', 'Kuanyama':'kj',
                    'Kurdish':'ku', 'Lao':'lo', 'Latin':'la', 'Latvian':'lv', 'Letzeburgesch':'lb',
                    'Limburgish':'li', 'Lingala':'ln', 'Lithuanian':'lt', 'Luba-Katanga':'lu',
                    'Macedonian':'mk', 'Malagasy':'mg', 'Malay':'ms', 'Malayalam':'ml', 'Maltese':'mt',
                    'Mandarin':'zh', 'Manx':'gv', 'Maori':'mi', 'Marathi':'mr', 'Marshall':'mh',
                    'Moldavian':'mo', 'Mongolian':'mn', 'Nauru':'na', 'Navajo':'nv', 'Ndebele':'nr',
                    'Ndebele':'nd', 'Ndonga':'ng', 'Nepali':'ne', 'No Language':'xx',
                    'Northern Sami':'se', 'Norwegian':'no', 'Norwegian Bokmal':'nb',
                    'Norwegian Nynorsk':'nn', 'Occitan':'oc', 'Ojibwa':'oj', 'Oriya':'or', 'Oromo':'om',
                    'Ossetian':'os', 'Pali':'pi', 'Persian':'fa', 'Polish':'pl', 'Portuguese':'pt',
                    'Punjabi':'pa', 'Pushto':'ps', 'Quechua':'qu', 'Raeto-Romance':'rm',
                    'Romanian':'ro', 'Rundi':'rn', 'Russian':'ru', 'Samoan':'sm', 'Sango':'sg',
                    'Sanskrit':'sa', 'Sardinian':'sc', 'Serbian':'sr', 'Serbo-Croatian':'sh',
                    'Shona':'sn', 'Sindhi':'sd', 'Sinhalese':'si', 'Slavic':'cu', 'Slovak':'sk',
                    'Slovenian':'sl', 'Somali':'so', 'Sotho':'st', 'Spanish':'es', 'Sundanese':'su',
                    'Swahili':'sw', 'Swati':'ss', 'Swedish':'sv', 'Tagalog':'tl', 'Tahitian':'ty',
                    'Tajik':'tg', 'Tamil':'ta', 'Tatar':'tt', 'Telugu':'te', 'Thai':'th', 'Tibetan':'bo',
                    'Tigrinya':'ti', 'Tonga':'to', 'Tsonga':'ts', 'Tswana':'tn', 'Turkish':'tr',
                    'Turkmen':'tk', 'Twi':'tw', 'Uighur':'ug', 'Ukrainian':'uk', 'Urdu':'ur',
                    'Uzbek':'uz', 'Venda':'ve', 'Vietnamese':'vi', 'Volapuk':'vo', 'Walloon':'wa',
                    'Welsh':'cy', 'Wolof':'wo', 'Xhosa':'xh', 'Yi':'ii', 'Yiddish':'yi', 'Yoruba':'yo',
                    'Zhuang':'za', 'Zulu':'zu'}

    tmdb = ['aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bi',
            'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch', 'cn', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da',
            'de', 'dv', 'dz', 'ee', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr',
            'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz',
            'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj',
            'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln',
            'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my', 'na',
            'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa',
            'pi', 'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'sh',
            'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg',
            'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've',
            'vi', 'vo', 'wa', 'wo', 'xh', 'xx', 'yi', 'yo', 'za', 'zh', 'zu']


    name = setting('api.language')
    if not name: name = 'AUTO'

    if name[-1].isupper():
        try:
            name = xbmc.getLanguage(xbmc.ENGLISH_NAME).split(' ')[0]
        except:
            pass
    try:
        name = langDict[name]
    except:
        name = 'en'

    lang = {'trakt': name} if name in trakt else {'trakt': 'en'}
    lang['tvdb'] = name if name in tvdb else 'en'
    lang['tmdb'] = name if name in tmdb else 'en'
    lang['youtube'] = name if name in youtube else 'en'

    if ret_name:
        lang['trakt'] = [i[0] for i in list(langDict.items()) if i[1] == lang['trakt']][0]
        lang['tvdb'] = [i[0] for i in list(langDict.items()) if i[1] == lang['tvdb']][0]
        lang['tmdb'] = [i[0] for i in list(langDictTMDB.items()) if i[1] == lang['tmdb']][0]
        lang['youtube'] = [i[0] for i in list(langDict.items()) if i[1] == lang['youtube']][0]

    return lang


def version():
    num = ''
    try:
        version = addon('xbmc.addon').getAddonInfo('version')
    except:
        version = '999'

    num = int(''.join(filter(str.isdigit, version)))

    return int(num)


def cdnImport(uri, name):
    import imp
    from resources.lib.modules import client

    path = os.path.join(dataPath, 'py' + name)
    path = six_decode(path)

    deleteDir(os.path.join(path, ''), force=True)
    makeFile(dataPath)
    makeFile(path)

    r = client.request(uri)
    p = os.path.join(path, name + '.py')
    f = openFile(p, 'w')
    f.write(r)
    f.close()
    m = imp.load_source(name, p)

    deleteDir(os.path.join(path, ''), force=True)
    return m

#cm - 
def openSettings(query='', id=addonInfo('id')):
    try:
        idle()
        execute('Addon.OpenSettings(%s)' % id)
        if not query:
            raise Exception()
        c, f = query.split('.')

        execute('SetFocus(%i)' % (int(c) - 100))
        execute('SetFocus(%i)' % (int(f) - 80))

    except:
        return


def getCurrentViewId():
    win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    return str(win.getFocusId())


def refresh():
    return execute('Container.Refresh')


def busy():
    return execute('ActivateWindow(busydialognocancel)')


def idle():
    return execute('Dialog.Close(busydialognocancel)')


def queueItem():
    return execute('Action(Queue)')


def installAddon(addon_id):
    addon_path = os.path.join(transPath('special://home/addons'), addon_id)
    if not os.path.exists(addon_path) == True:
        xbmc.executebuiltin('InstallAddon(%s)' % (addon_id))
    else:
        infoDialog(f"{addon_id} is already installed", sound=True)