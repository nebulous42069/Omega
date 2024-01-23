import time
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json
import requests
import re
from urllib.parse import unquote

ADDON = xbmcaddon.Addon(id='script.module.pvr.artwork')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
LOC = ADDON.getLocalizedString
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
MEDIA_LOCAL = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('path')), 'media', 'defaultnas.png')

LANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
if not LANGUAGE: LANGUAGE = "en"
DB_VERSION = '1.0.9'
DB_PREFIX = '%s.%s' % (ADDON_ID, DB_VERSION)


def jsonrpc(query):
    """
        perform a JSON-RPC query
    """
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(querystring)))
        if 'result' in response: return response['result']
    except TypeError as e:
        xbmc.log('Error executing JSON RPC: %s' % e, xbmc.LOGERROR)
    return None


def get_json(url, params, prefix=None):
    """
        get info from a rest api
    """
    log('Query database %s with parameters' % url, pretty_print=params)

    try:
        response = requests.get(url, params=params, timeout=20, headers={'content-type': 'application/json'})
        response.raise_for_status()
        if response and response.content:
            data = json.loads(response.content)
            js_data = data.get(prefix, data) if prefix else data
            if ADDON.getSetting('log_results') == 'true': log('Result of database query', pretty_print=js_data)
            return js_data

    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        xbmc.log(str(e), xbmc.LOGERROR)

    return None


def log(message, pretty_print=False, type=xbmc.LOGDEBUG):
    xbmc.log('[%s] %s' % (ADDON_ID, message), type)
    if pretty_print: print(json.dumps(pretty_print, sort_keys=True, indent=4, ensure_ascii=False))


def normalize_string(fname):
    """
        normalize string, strip all special chars
    """
    fname = fname.replace(':', ' -')
    fname = re.sub(r'[\\/*?"<>|]', '', fname).strip().rstrip('.')
    return ' '.join(fname.split())


def split_addonsetting(setting, separator):
    item = ADDON.getSetting(setting)
    if item == '':
        return []
    else:
        return item.split(separator)


def pure_channelname(channel):
    """
        reduce channel name to SD channels only
    """
    for item in [' HD', ' FHD', ' UHD', ' hd', ' fhd', ' uhd']:
        if item in channel: return channel.replace(item, '')
    return channel


def extend_dict(org_dict, new_dict, allow_overwrite=None):
    """
        Create a new dictionary with a's properties extended by b, without overwriting existing values.
    """
    return {**org_dict, **new_dict}


def parse_int(string):
    """
        helper to parse int from string without erroring on empty or misformed string
    """
    try:
        return int(string)
    except ValueError:
        return 0


def get_compare_string(text):
    """
        strip all special chars in a string for better comparing of searchresults
    """
    text = text.lower()
    text = ''.join(e for e in text if e.isalnum())
    return text


def url_unquote(url):
    """
        unquote urls, remove image scheme and trailing slashes
    """
    return unquote(url.replace('image://', '')).rstrip('/')


def convert_date(date, date_format='%Y-%m-%d'):
    try:
        dt = time.strptime(date, date_format)
        return time.strftime(xbmc.getRegion('dateshort'), dt)
    except ValueError:
        log('Could not convert date with wrong format: %s' % date, type=xbmc.LOGERROR)
        return date


def rmdirs(folder, count, force=True):
    process_bg = xbmcgui.DialogProgressBG()
    dirs, files = xbmcvfs.listdir(folder)
    if len(dirs) > 0: steps = 100 // len(dirs)
    pcnt = 0
    steps = 0
    if len(dirs) > 0: steps = 100 // len(dirs)
    process_bg.create(ADDON_NAME, LOC(32071))
    for file in files: xbmcvfs.delete(os.path.join(folder, file))
    for dir in dirs:
        rmdirs(os.path.join(folder, dir), count, force=force)
        process_bg.update(pcnt, ADDON_NAME, LOC(32071))
        pcnt = pcnt + steps
        if xbmcvfs.rmdir(os.path.join(folder, dir), force=force): count += 1
    process_bg.close()
    return count

