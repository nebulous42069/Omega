"""Compatibility with TMDb Helper's separate Trakt and MDbList providers."""
import ast
import json
import os
import re
import xbmcaddon
import xbmcgui
import xbmcvfs

TRAKT = 'script.module.tmdbhelper.sync.trakt'
MDBLIST = 'script.module.tmdbhelper.sync.mdblist'


def installed(addon_id):
    return xbmcvfs.exists('special://home/addons/%s/' % addon_id)


def clear_trakt_session():
    import sys
    library = xbmcvfs.translatePath('special://home/addons/script.module.jurialmunkey/lib/')
    added = library not in sys.path
    if added:
        sys.path.insert(0, library)
    try:
        from jurialmunkey.window import get_property
        for name in ('TraktUserToken', 'TraktIsAuth', 'TraktRefreshAttempts',
                     'TraktRefreshTimeStamp', 'TraktAttemptedLogin'):
            get_property(name, clear_property=True)
    finally:
        if added:
            sys.path.remove(library)


def configure_trakt_client(client_id, client_secret):
    """Keep copied refresh tokens paired with their issuing OAuth client."""
    base = xbmcvfs.translatePath('special://home/addons/%s/resources/lib/tmdbhelper_sync_trakt/api/' % TRAKT)
    keys_path, api_path = os.path.join(base, 'keys.py'), os.path.join(base, 'api.py')
    with open(keys_path, encoding='utf-8') as stream:
        keys = stream.read()
    with open(api_path, encoding='utf-8') as stream:
        api = stream.read()
    keys, count = re.subn(r"(?m)^CLIENT_ID\s*=.*$", 'CLIENT_ID = ' + repr(client_id), keys)
    if count != 1:
        raise ValueError('Unsupported TMDb Helper Trakt client layout')
    # Provider 1.2.5 is a public OAuth client. ReAuthorize uses a confidential
    # client, so its token exchange, refresh and revoke also need the secret.
    marker = "'client_id': self.client_id"
    replacement = marker + ", 'client_secret': " + repr(client_secret)
    # Repeated syncs update the existing compatibility injection in place.
    api = re.sub(r"'client_id': self.client_id, 'client_secret': '[^']*'", marker, api)
    if api.count(marker) != 4:
        raise ValueError('Unsupported TMDb Helper Trakt OAuth request layout')
    api = api.replace(marker, replacement)
    ast.parse(keys)
    ast.parse(api)
    for path, content in ((keys_path, keys), (api_path, api)):
        with open(path, encoding='utf-8') as stream:
            original = stream.read()
        if original != content:
            temporary = path + '.reauthorize-tmp'
            try:
                with open(temporary, 'w', encoding='utf-8') as stream:
                    stream.write(content)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)


def sync_trakt(token_json, client_id, client_secret):
    configure_trakt_client(client_id, client_secret)
    addon = xbmcaddon.Addon(TRAKT)
    addon.setSetting('token', token_json)
    if addon.getSetting('token') != token_json:
        raise IOError('TMDb Helper Trakt token did not save')
    addon.setSetting('credentials_migrated', 'true')
    clear_trakt_session()


def sync_mdblist(api_key):
    addon = xbmcaddon.Addon(MDBLIST)
    addon.setSetting('apikey', api_key)
    if addon.getSetting('apikey') != api_key:
        raise IOError('TMDb Helper MDbList API key did not save')
    # Prevent migration from restoring an old key after an intentional wipe.
    if installed('plugin.video.themoviedb.helper'):
        xbmcaddon.Addon('plugin.video.themoviedb.helper').setSetting('mdblist_apikey', '')
