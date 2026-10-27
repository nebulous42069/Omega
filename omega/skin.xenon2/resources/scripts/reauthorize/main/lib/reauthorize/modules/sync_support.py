"""Audit-build sync helpers. No network requests or global Kodi monkey patches."""
import os
import ast
import tempfile
import threading
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

_state = threading.local()
_real_addon = xbmcaddon.Addon


def begin():
    _state.errors = set()
    _state.reached = set()


def failed(addon_id='adapter'):
    if not hasattr(_state, 'errors'):
        begin()
    _state.errors.add(addon_id)


def errors():
    return sorted(getattr(_state, 'errors', ()))


class _Addon:
    def __init__(self, addon_id):
        self.id = addon_id
        self.raw = _real_addon(addon_id)

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def getSetting(self, key):
        try:
            return _real_addon(self.id).getSetting(key)
        except Exception:
            failed(self.id)
            raise

    def setSetting(self, key, value):
        try:
            value = str(value)
            # A fresh handle avoids reverting a concurrent setting snapshot.
            _real_addon(self.id).setSetting(key, value)
            if _real_addon(self.id).getSetting(key) != value:
                raise RuntimeError('Setting readback did not match')
            if not hasattr(_state, 'reached'):
                begin()
            _state.reached.add(self.id)
        except Exception:
            failed(self.id)
            raise

    setSettingString = setSetting


def addon_api(api):
    class LocalAPI:
        def __getattr__(self, name):
            return getattr(api, name)

        def Addon(self, addon_id=None, **kwargs):
            if not addon_id or addon_id == 'script.module.reauthorize':
                return api.Addon(addon_id, **kwargs) if addon_id else api.Addon(**kwargs)
            return _Addon(addon_id)
    return LocalAPI()


def needs(addon_id, pairs):
    from reauthorize.modules import control
    addon = _Addon(addon_id)
    values = [(key, str(value)) for key, value in pairs if value or control.wiping()]
    enable = {'rd.token': 'rd.enabled', 'rd.auth': 'realdebrid.enabled',
              'realdebridtoken': 'realdebrid.enable', 'pm.token': 'pm.enabled',
              'premiumize.token': 'premiumize.enabled', 'premiumizetoken': 'premiumize.enable',
              'ad.token': 'ad.enabled', 'alldebrid.apikey': 'alldebrid.enabled',
              'alldebridtoken': 'alldebrid.enable', 'tb.token': 'tb.enabled',
              'torboxtoken': 'torbox.enable', 'ed.token': 'ed.enabled',
              'easydebridtoken': 'easydebrid.enable'}
    # Apply only verified naming conventions; do not invent a missing field.
    if addon_id == 'plugin.video.prism':
        enable['tb.token'] = 'torbox.enabled'
    elif addon_id not in ('plugin.video.seren', 'plugin.video.pov', 'plugin.video.umbrella'):
        enable = {}
    if any(value and key in enable and addon.getSetting(enable[key]) != 'true' for key, value in values):
        return True
    return any(addon.getSetting(key) != value for key, value in values)


def installed(addon_id):
    return xbmcvfs.exists('special://home/addons/%s/' % addon_id)


def put(addon_id, pairs, wipe=False):
    if not installed(addon_id):
        return False
    addon = _Addon(addon_id)
    for key, value in pairs:
        if value or wipe:
            if addon.getSetting(key) != str(value):
                addon.setSetting(key, str(value))
    return True


def clear_setting(addon_id, key, credential_key=None):
    """Clear a mapped field using the receiving add-on's declared setting type.

    Action controls are not credentials. Expiry counters use zero, not an
    empty string. Text credentials must still read back as exactly empty.
    """
    if not installed(addon_id):
        return False
    addon = _real_addon(addon_id)
    kind = ''
    try:
        schema = os.path.join(addon.getAddonInfo('path'), 'resources', 'settings.xml')
        for node in ET.parse(schema).getroot().iter('setting'):
            if node.get('id') == key:
                kind = node.get('type', '').lower()
                break
    except (OSError, ET.ParseError, AttributeError, TypeError):
        pass
    if kind == 'action':
        xbmc.log('[ReAuthorize Wipe] Skipped action control %s / %s' %
                 (addon_id, key), xbmc.LOGINFO)
        return True
    numeric = kind in ('integer', 'number', 'float') or credential_key == 'trakt.expires'
    boolean = kind in ('bool', 'boolean')
    wanted = '0' if numeric else ('false' if boolean else '')
    addon.setSetting(key, wanted)
    actual = _real_addon(addon_id).getSetting(key)
    if numeric:
        try:
            cleared = float(actual) == 0
        except (ValueError, TypeError):
            cleared = False
    elif boolean:
        cleared = str(actual).lower() == 'false'
    else:
        cleared = actual == ''
    if not cleared:
        failed(addon_id)
        raise RuntimeError('Mapped wipe readback did not match the cleared state')
    return True


def patch_constants(path, wanted):
    """Replace only named string assignments; refuse unrecognized source layouts."""
    with open(path, encoding='utf-8') as stream:
        text = stream.read()
    lines = text.splitlines(True)
    found = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in wanted and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                found[name] = node
    if set(found) != set(wanted):
        raise RuntimeError('Unrecognized application-key layout')
    for name, node in found.items():
        if node.lineno != node.end_lineno:
            raise RuntimeError('Multiline application key is not supported')
        line = lines[node.lineno - 1]
        marker = '# ReAuthorize; was: '
        original = line.split(marker, 1)[1].strip() if marker in line else repr(node.value.value)
        lines[node.lineno - 1] = '%s = %r  %s%s\n' % (name, wanted[name], marker, original)
    result = ''.join(lines)
    if result == text:
        return False
    fd, temporary = tempfile.mkstemp(prefix='.reauthorize-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(result)
        os.chmod(temporary, os.stat(path).st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return True


def extra(tag):
    """Additional mappings verified in the supplied consumer source."""
    from reauthorize.modules import control
    get = control.setting
    wipe = control.wiping()
    if tag == 'trakt' and get('trakt.token'):
        from libs.common import var
        # These supplied forks support explicit client settings. They override
        # fallback constants and avoid brittle source-secret replacement.
        for aid in ('plugin.video.homelander', 'plugin.video.quicksilver', 'plugin.video.absolution', 'plugin.video.moria'):
            put(aid, [('trakt.client_id', var.client_am), ('trakt.client_secret', var.secret_am),
                      ('trakt.user', get('trakt.username')), ('trakt.token', get('trakt.token')),
                      ('trakt.refresh', get('trakt.refresh'))])
        put('plugin.video.thechains', [('trakt_client_id', var.client_am), ('trakt_client_secret', var.secret_am)])
        if installed('plugin.video.thearchives'):
            path = xbmcvfs.translatePath('special://home/addons/plugin.video.thearchives/resources/lib/util/dev_api.py')
            patch_constants(path, {'TRAKT_CLIENT_ID': var.client_am, 'TRAKT_CLIENT_SECRET': var.secret_am})
            put('plugin.video.thearchives', [('trakt.access_token', get('trakt.token')),
                ('trakt.refresh_token', get('trakt.refresh')), ('trakt.expires', get('trakt.expires')),
                ('trakt.user_id', get('trakt.username'))])
    token = {'torbox': 'torbox.token', 'offc': 'offcloud.token', 'meta': 'mdb.api.key'}.get(tag)
    if tag == 'torbox':
        value = get(token)
        if value or wipe:
            put('plugin.video.seren', [('torbox.token', value), ('torbox.enabled', 'false' if wipe else 'true')], wipe)
            put('script.module.resolveurl', [('TorBoxResolver_apikey', value), ('TorBoxResolver_enabled', 'false' if wipe else 'true')], wipe)
    elif tag == 'offc':
        value = get(token)
        if value or wipe:
            put('plugin.video.seren', [('offcloud.apikey', value), ('offcloud.enabled', 'false' if wipe else 'true')], wipe)
            put('script.module.resolveurl', [('OffCloudResolver_apikey', value), ('OffCloudResolver_enabled', 'false' if wipe else 'true')], wipe)
    elif tag in ('rd', 'pm', 'ad'):
        prefix = {'rd': 'RealDebridResolver', 'pm': 'PremiumizeMeResolver', 'ad': 'AllDebridResolver'}[tag]
        put('script.module.resolveurl', [(prefix + '_enabled', 'false' if wipe else 'true')], wipe)
    elif tag == 'meta':
        value = get('mdb.api.key')
        if value or wipe:
            put('plugin.video.seren', [('mdblist.apikey', value), ('mdblist.username', get('mdb.username'))], wipe)
        value = get('tmdb.api.key')
        if value or wipe:
            put('plugin.video.prism', [('tmdb.apikey', value)], wipe)


def clear_matching(before, source_keys):
    """Remove only values matching the credential snapshot being signed out."""
    from reauthorize.modules import import_map
    for addon_id, mapping in import_map.SETTINGS.items():
        if not installed(addon_id):
            continue
        addon = _Addon(addon_id)
        for sid, key in mapping.items():
            if key in source_keys and before.get(key) and addon.getSetting(sid) == before[key]:
                addon.setSetting(sid, '')
    # Supplemental integrations are not present in the original generated map.
    pairs = [('plugin.video.seren', 'torbox.token', 'torbox.token'),
             ('script.module.resolveurl', 'TorBoxResolver_apikey', 'torbox.token'),
             ('plugin.video.seren', 'offcloud.apikey', 'offcloud.token'),
             ('plugin.video.seren', 'mdblist.apikey', 'mdb.api.key'),
             ('plugin.video.prism', 'tmdb.apikey', 'tmdb.api.key')]
    for aid, sid, key in pairs:
        if key in source_keys and before.get(key) and installed(aid):
            addon = _Addon(aid)
            if addon.getSetting(sid) == before[key]:
                addon.setSetting(sid, '')
    if 'realdebrid.token' in source_keys and before.get('realdebrid.token'):
        import json
        path = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.realizerx/rdauth.json')
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as stream:
                data = json.load(stream)
            if data.get('token') == before['realdebrid.token']:
                for key in ('token', 'refresh', 'client_id', 'secret'):
                    if key in data:
                        data[key] = ''
                fd, temporary = tempfile.mkstemp(prefix='.reauthorize-', dir=os.path.dirname(path))
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                        json.dump(data, stream)
                    os.replace(temporary, path)
                finally:
                    if os.path.exists(temporary):
                        os.remove(temporary)
    # Database-backed consumers: remove matching values, then request reload.
    import sqlite3
    for aid, spec in import_map.DATABASES.items():
        path = xbmcvfs.translatePath('special://profile/addon_data/%s/%s' % (aid, spec['file']))
        if not os.path.isfile(path):
            continue
        conn = sqlite3.connect(path, timeout=10)
        try:
            with conn:
                for sid, key in spec['keys'].items():
                    if key in source_keys and before.get(key):
                        conn.execute("UPDATE settings SET setting_value='' WHERE setting_id=? AND setting_value=?", (sid, before[key]))
        finally:
            conn.close()
        if aid == 'plugin.video.redlight':
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.redlight/?mode=sync_settings&silent=true&load_properties=false&force=true)')


def after_action(action, before):
    from reauthorize.modules import control, autosend
    if not before:
        return
    if action in autosend.TAG_FOR_ACTION:
        return  # autosend uses the runner, which invokes extra()
    resync = {'realdebridReSync': 'rd', 'premiumizeReSync': 'pm', 'alldebridReSync': 'ad',
              'torboxReSync': 'torbox', 'offcloudReSync': 'offc', 'traktAuth': 'trakt', 'traktReSync': 'trakt'}
    if action in resync:
        extra(resync[action])
    revoked = {'realdebridRevoke': 'realdebrid.', 'premiumizeRevoke': 'premiumize.',
               'alldebridRevoke': 'alldebrid.', 'torboxRevoke': 'torbox.',
               'easydebridRevoke': 'easydebrid.', 'offcloudRevoke': 'offcloud.',
               'easynewsRevoke': 'easynews.', 'linksnappyRevoke': 'linksnappy.',
               'filepursuitRevoke': 'filepursuit.', 'fanartRevoke': 'fanart.tv.',
               'omdbRevoke': 'omdb.', 'imdbRevoke': 'imdb.', 'tmdbRevoke': 'tmdb.'}
    prefix = revoked.get(action)
    if prefix:
        keys = {k for k, value in before.items() if k.startswith(prefix) and value and not control.setting(k)}
        if keys:
            clear_matching(before, keys)
    elif action == 'removeService':
        keys = {k for k, value in before.items() if value and not control.setting(k)}
        clear_matching(before, keys)
    if errors():
        control.notification(title='ReAuthorize', message='Some add-on settings could not be verified: ' + ', '.join(errors()), time=7000)


def scrub_crew_simkl():
    from reauthorize.modules.sync import crew_trakt
    crew_trakt._patch_backups({'simkl.token': '', 'simkl.user': '', 'simkl.client_id': ''})
