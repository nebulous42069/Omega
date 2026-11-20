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
SIMKL = 'script.module.tmdbhelper.sync.simkl'
TVDB = 'script.module.tmdbhelper.sync.tvdb'
HELPER = 'plugin.video.themoviedb.helper'


def installed(addon_id):
    return xbmcvfs.exists('special://home/addons/%s/' % addon_id)


def clear_trakt_session():
    """Clear TMDb Helper's cached authorization if its utility is available."""
    import sys
    import xml.etree.ElementTree as ET
    import xbmc

    if not (installed(TRAKT) or installed('plugin.video.themoviedb.helper')):
        return
    added = []
    try:
        dependency = xbmcaddon.Addon('script.module.jurialmunkey')
        base = xbmcvfs.translatePath(dependency.getAddonInfo('path'))
        manifest = ET.parse(os.path.join(base, 'addon.xml'))
        for extension in manifest.findall("extension[@point='xbmc.python.module']"):
            for library in extension.get('library', '').split('|'):
                path = os.path.join(base, library)
                if library and path not in sys.path:
                    sys.path.insert(0, path)
                    added.append(path)
        from jurialmunkey.window import get_property
        for name in ('TraktUserToken', 'TraktIsAuth', 'TraktRefreshAttempts',
                     'TraktRefreshTimeStamp', 'TraktAttemptedLogin'):
            get_property(name, clear_property=True)
    except Exception as exc:
        xbmc.log('[Diggz Account Manager] TMDb Helper Trakt cache could not be cleared (%s). '
                 'Restart Kodi to discard cached authorization.' % type(exc).__name__, xbmc.LOGWARNING)
    finally:
        for path in added:
            sys.path.remove(path)


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
    tree = ast.parse(api)
    requests = [n for n in ast.walk(tree) if isinstance(n, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == 'client_id' and isinstance(v, ast.Attribute) and v.attr == 'client_id' for k, v in zip(n.keys, n.values))]
    if not requests or len(requests) != api.count(marker):
        raise ValueError('Unsupported TMDb Helper Trakt OAuth request layout')
    api = api.replace(marker, replacement)
    ast.parse(keys)
    ast.parse(api)
    changed = False
    for path, content in ((keys_path, keys), (api_path, api)):
        with open(path, encoding='utf-8') as stream:
            original = stream.read()
        if original != content:
            changed = True
            temporary = path + '.reauthorize-tmp'
            try:
                with open(temporary, 'w', encoding='utf-8') as stream:
                    stream.write(content)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)

    return changed


def sync_trakt(token_json, client_id, client_secret):
    changed = configure_trakt_client(client_id, client_secret)
    addon = xbmcaddon.Addon(TRAKT)
    incoming = json.loads(token_json)
    existing = read_bundle(TRAKT, 'token')
    # Never replace a newer provider grant during routine sync. Recovery may
    # adopt that grant after confirming the account identity.
    if not changed and existing.get('refresh_token') and bundle_expiry(existing) > bundle_expiry(incoming):
        return False
    if existing == incoming and not changed:
        return True
    addon.setSetting('token', token_json)
    if addon.getSetting('token') != token_json:
        raise IOError('TMDb Helper Trakt token did not save')
    addon.setSetting('credentials_migrated', 'true')
    clear_trakt_session()
    return True


def sync_mdblist(api_key):
    addon = xbmcaddon.Addon(MDBLIST)
    addon.setSetting('apikey', api_key)
    if addon.getSetting('apikey') != api_key:
        raise IOError('TMDb Helper MDbList API key did not save')
    # Prevent migration from restoring an old key after an intentional wipe.
    if installed('plugin.video.themoviedb.helper'):
        xbmcaddon.Addon('plugin.video.themoviedb.helper').setSetting('mdblist_apikey', '')


def key_paths():
    base = xbmcvfs.translatePath('special://home/addons/%s/resources/lib/tmdbhelper_sync_trakt/api/' % TRAKT)
    return [os.path.join(base, name) for name in ('keys.py', 'api.py')]


def repair_provider(account):
    """Reapply client compatibility after provider updates, without repeated token resets."""
    from libs.common import var
    if not installed(TRAKT):
        return False
    access = account.getSetting('trakt.token')
    if not access or account.getSetting('trakt.auto_push.consent') == 'false':
        return False
    changed = configure_trakt_client(var.client_am, var.secret_am)
    destination = xbmcaddon.Addon(TRAKT)
    if changed or not destination.getSetting('token'):
        lifetime = int(float(account.getSetting('trakt.lifetime') or 604800))
        expires = int(float(account.getSetting('trakt.expires') or 0))
        if not expires or not account.getSetting('trakt.refresh'):
            raise ValueError('Diggz Account Manager Trakt sign-in needs a refresh token and expiry before provider recovery')
        bundle = json.dumps({
            'access_token': access, 'refresh_token': account.getSetting('trakt.refresh'),
            'token_type': 'bearer', 'expires_in': lifetime,
            'created_at': expires - lifetime, 'scope': 'public'})
        sync_trakt(bundle, var.client_am, var.secret_am)
    return changed


def read_bundle(addon_id, key):
    try:
        value = json.loads(xbmcaddon.Addon(addon_id).getSetting(key) or '{}')
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError, RuntimeError):
        return {}


def bundle_expiry(bundle):
    try:
        return int(float(bundle.get('created_at', 0))) + int(float(bundle.get('expires_in', 0)))
    except (ValueError, TypeError, OverflowError):
        return 0


def newer_trakt(account, client_id):
    """Only adopt a newer provider token after verifying the same Trakt account."""
    if not installed(TRAKT) or not account.getSetting('trakt.refresh'):
        return None
    bundle = read_bundle(TRAKT, 'token')
    if not bundle.get('access_token') or not bundle.get('refresh_token'):
        return None
    try:
        if bundle_expiry(bundle) <= float(account.getSetting('trakt.expires') or 0):
            return None
        if bundle['refresh_token'] == account.getSetting('trakt.refresh'):
            return None
        import requests
        response = requests.get('https://api.trakt.tv/users/settings', headers={
            'Authorization': 'Bearer ' + bundle['access_token'],
            'trakt-api-key': client_id, 'trakt-api-version': '2'}, timeout=10)
        if response.status_code != 200:
            return None
        user = response.json().get('user', {})
        expected = account.getSetting('trakt.username').strip().casefold()
        names = (str(user.get('username') or '').casefold(), str(user.get('ids', {}).get('slug') or '').casefold())
        if expected and expected in names:
            return bundle
    except Exception:
        return None
    return None


def simkl_present():
    auth = read_bundle(SIMKL, 'authorization')
    try:
        path = xbmcvfs.translatePath('special://home/addons/%s/resources/lib/tmdbhelper_sync_simkl/keys.py' % SIMKL)
        with open(path, encoding='utf-8') as stream:
            tree = ast.parse(stream.read())
        client = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CLIENT_ID' for t in n.targets))
        return bool(auth.get('client_id') == client and auth.get('session_id') and auth.get('access_token') and auth.get('refresh_token') and 'media:read' in auth.get('scope', '').split() and float(auth.get('expires_at', 0)) > 0)
    except Exception:
        return False


def sync_tvdb(key, wipe=False):
    if installed(TVDB) and (key or wipe):
        addon = xbmcaddon.Addon(TVDB)
        addon.setSetting('apikey', key)
        if addon.getSetting('apikey') != key:
            raise IOError('TVDb API key did not save')


def sync_simkl(bundle):
    if not installed(SIMKL):
        return False
    from reauthorize.modules.auth.simkl import valid_bundle
    from reauthorize.modules.sync import simkl_appkey
    if not valid_bundle(bundle):
        return False
    addon = xbmcaddon.Addon(SIMKL)
    held = read_bundle(SIMKL, 'authorization')
    if held.get('session_id') == bundle['session_id'] and valid_bundle(held) and float(held['expires_at']) > float(bundle['expires_at']):
        return False  # background renewal will adopt it, never overwrite it
    simkl_appkey.ensure(SIMKL, bundle['client_id'])
    path = simkl_appkey.path_of(SIMKL, 'resources/lib/tmdbhelper_sync_simkl/keys.py')
    with open(path, encoding='utf-8') as stream:
        tree = ast.parse(stream.read())
    client = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CLIENT_ID' for t in n.targets))
    if client != bundle['client_id']:
        raise ValueError('Unsupported SIMKL provider key layout')
    if held != bundle:
        addon.setSetting('authorization', json.dumps(bundle))
        if read_bundle(SIMKL, 'authorization') != bundle:
            raise IOError('SIMKL authorization did not save')
    return True


def clear_simkl():
    # Local wipe only: do not revoke a builder's grant on the server.
    if installed(SIMKL):
        xbmcaddon.Addon(SIMKL).setSetting('authorization', '')
        from reauthorize.modules.sync import simkl_appkey
        simkl_appkey.restore(SIMKL)
