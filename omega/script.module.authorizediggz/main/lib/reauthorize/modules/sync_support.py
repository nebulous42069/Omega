"""Audit-build sync helpers. No network requests or global Kodi monkey patches."""
import os
import ast
import tempfile
import threading
import sys
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

_state = threading.local()
_real_addon = xbmcaddon.Addon

# These versions use the legacy action ID as their stored Trakt username.
# Their own sign-in code saves it with Kodi's settings API.
_TRAKT_ACTION_USERNAME_ADDONS = frozenset({
    'plugin.video.absolution',
    'plugin.video.homelander',
    'plugin.video.nightwing',
    'plugin.video.quicksilver',
    'plugin.video.scrubsv2',
})


class IncompatibleSetting(RuntimeError):
    pass


def begin():
    _state.errors = set()
    _state.reached = set()
    _state.warnings = set()
    _state.last_addon = None


def _ensure():
    if not hasattr(_state, 'errors'):
        begin()


def warning(addon_id, reason):
    _ensure()
    item = (addon_id, reason)
    if item not in _state.warnings:
        _state.warnings.add(item)
        xbmc.log('[Diggz Account Manager] Skipped %s: %s' % item, xbmc.LOGWARNING)


def warnings():
    return sorted(getattr(_state, 'warnings', ()))


def failed(addon_id=None):
    _ensure()
    if isinstance(sys.exc_info()[1], IncompatibleSetting):
        return
    if addon_id is None and _state.last_addon in _state.errors:
        return
    addon_id = addon_id or 'adapter'
    _state.errors.add(addon_id)


def errors():
    return sorted(getattr(_state, 'errors', ()))


def reached():
    return sorted(getattr(_state, 'reached', ()))


def declared_settings(addon):
    """Read the installed add-on's setting definitions without copying them."""
    path = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('path')), 'resources', 'settings.xml')
    try:
        return {node.get('id'): node.get('type', '').lower()
                for node in ET.parse(path).getroot().iter('setting') if node.get('id')}
    except (OSError, ET.ParseError):
        return None


def profile_ready(addon_id, path):
    """Custom storage must be initialized by its owning add-on."""
    if not installed(addon_id):
        return False
    if xbmcvfs.exists(path):
        return True
    warning(addon_id, 'not initialized; open the add-on once and retry')
    return False


class _Addon:
    def __init__(self, addon_id):
        _ensure()
        _state.last_addon = addon_id
        self.id = addon_id
        self.raw = _real_addon(addon_id)
        self.schema = declared_settings(self.raw)

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def _writable(self, key):
        legacy = key == 'trakt.user' and self.id in _TRAKT_ACTION_USERNAME_ADDONS
        return self.schema is None or (key in self.schema and (self.schema[key] != 'action' or legacy))

    def _value(self, key, value):
        value = str(value)
        kind = (self.schema or {}).get(key, '')
        if value == '' and kind in ('integer', 'number', 'float'):
            return '0'
        if value == '' and kind in ('bool', 'boolean'):
            return 'false'
        return value

    def preflight(self, pairs):
        missing = sorted({key for key, value in pairs if not self._writable(key)
                          and (value != '' or self.getSetting(key) != '')})
        if missing:
            warning(self.id, 'incompatible; missing writable setting(s): ' + ', '.join(missing))
            return False
        return True

    def getSetting(self, key):
        _state.last_addon = self.id
        try:
            return _real_addon(self.id).getSetting(key)
        except Exception:
            failed(self.id)
            raise

    def setSetting(self, key, value):
        _state.last_addon = self.id
        try:
            value = self._value(key, value)
            if not self._writable(key):
                if value == '' and self.getSetting(key) == '':
                    return
                warning(self.id, 'incompatible; missing writable setting: ' + key)
                raise IncompatibleSetting('Target setting is missing or read-only')
            # Avoid Kodi's onSettingsChanged broadcast for unchanged values.
            if self.getSetting(key) != value:
                raw = _real_addon(self.id)
                kind = (self.schema or {}).get(key, '')
                # Otaku uses Kodi's typed schema. Use the matching native setter.
                if self.id == 'plugin.video.otaku' and kind in ('boolean', 'integer', 'number', 'string'):
                    settings = raw.getSettings()
                    methods = {'boolean': ('setBool', value.lower() == 'true'),
                               'string': ('setString', value)}
                    if kind == 'integer':
                        methods[kind] = ('setInt', int(value))
                    elif kind == 'number':
                        methods[kind] = ('setNumber', float(value))
                    method, typed = methods[kind]
                    getattr(settings, method)(key, typed)
                else:
                    raw.setSetting(key, value)
            if self.getSetting(key) != value:
                xbmc.log('[Diggz Account Manager] %s did not save %s. Open the add-on once and retry.' %
                         (self.id, key), xbmc.LOGWARNING)
                raise RuntimeError('Setting readback did not match')
            _state.reached.add(self.id)
        except IncompatibleSetting:
            raise
        except Exception:
            failed(self.id)
            raise

    setSettingString = setSetting

    def set_optional(self, key, value):
        if self._writable(key):
            self.setSetting(key, value)


def addon_api(api):
    class LocalAPI:
        def __getattr__(self, name):
            return getattr(api, name)

        def Addon(self, addon_id=None, **kwargs):
            if not addon_id or addon_id == 'script.module.authorizediggz':
                return api.Addon(addon_id, **kwargs) if addon_id else api.Addon(**kwargs)
            return _Addon(addon_id)
    return LocalAPI()


def needs(addon_id, pairs):
    from reauthorize.modules import control
    addon = _Addon(addon_id)
    values = [(key, addon._value(key, value)) for key, value in pairs if value or control.wiping()]
    enable = {'rd.token': 'rd.enabled', 'rd.auth': 'realdebrid.enabled',
              'realdebridtoken': 'realdebrid.enable', 'pm.token': 'pm.enabled',
              'premiumize.token': 'premiumize.enabled', 'premiumizetoken': 'premiumize.enable',
              'ad.token': 'ad.enabled', 'alldebrid.apikey': 'alldebrid.enabled',
              'alldebridtoken': 'alldebrid.enable', 'tb.token': 'tb.enabled',
              'torboxtoken': 'torbox.enable', 'ed.token': 'ed.enabled',
              'easydebridtoken': 'easydebrid.enable', 'oc.token': 'oc.enabled',
              'offcloudtoken': 'offcloud.enable', 'filepursuittoken': 'filepursuit.enable',
              'filepursuit.api': 'filepursuit.enable'}
    if addon_id == 'plugin.video.prism':
        enable['tb.token'] = 'torbox.enabled'
    elif addon_id not in ('plugin.video.seren', 'plugin.video.pov', 'plugin.video.umbrella'):
        enable = {}
    flags = [(enable[key], 'true' if value else 'false') for key, value in values
             if key in enable and addon._writable(enable[key])]
    if not addon.preflight(values):
        return False
    if any(addon.getSetting(key) != value for key, value in values + flags):
        return True
    if values:
        _state.reached.add(addon_id)
    return False


def installed(addon_id):
    return xbmcvfs.exists('special://home/addons/%s/' % addon_id)


def put(addon_id, pairs, wipe=False):
    if not installed(addon_id):
        return False
    try:
        addon = _Addon(addon_id)
        pairs = [(key, addon._value(key, value)) for key, value in pairs if value or wipe]
        if not addon.preflight(pairs):
            return False
        for key, value in pairs:
            addon.setSetting(key, value)
        return True
    except IncompatibleSetting:
        return False
    except Exception as exc:
        failed(addon_id)
        xbmc.log('[Diggz Account Manager] Follow-up sync failed for %s (%s).' %
                 (addon_id, type(exc).__name__), xbmc.LOGWARNING)
        return False


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
    legacy_username = key == 'trakt.user' and addon_id in _TRAKT_ACTION_USERNAME_ADDONS
    if kind == 'action' and not legacy_username:
        xbmc.log('[Diggz Account Manager Wipe] Skipped action control %s / %s' %
                 (addon_id, key), xbmc.LOGINFO)
        return True
    numeric = kind in ('integer', 'number', 'float') or credential_key == 'trakt.expires'
    boolean = kind in ('bool', 'boolean')
    wanted = '0' if numeric else ('false' if boolean else '')
    if addon.getSetting(key) != wanted:
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
    if tag in ('rd', 'torbox'):
        from reauthorize.modules.sync import aniverse_sync
        try:
            aniverse_sync.send(tag)
        except OSError as exc:
            failed(aniverse_sync.ADDON_ID)
            xbmc.log('[Diggz Account Manager] AniVerse %s sync failed (%s).' %
                     (tag, type(exc).__name__), xbmc.LOGWARNING)
    if tag not in ('easyd', 'debridlink'):
        from reauthorize.modules.sync import salts_sync
        salts_sync.send(tag)
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
    elif tag in ('rd', 'pm'):
        # AllDebrid's adapter verifies the token before enabling the resolver.
        prefix = {'rd': 'RealDebridResolver', 'pm': 'PremiumizeMeResolver'}[tag]
        put('script.module.resolveurl', [(prefix + '_enabled', 'false' if wipe else 'true')], wipe)
    elif tag == 'meta':
        value = get('mdb.api.key')
        if value or wipe:
            put('plugin.video.seren', [('mdblist.apikey', value), ('mdblist.username', get('mdb.username'))], wipe)
        value = get('tmdb.api.key')
        if value or wipe:
            put('plugin.video.prism', [('tmdb.apikey', value)], wipe)


def _disable_matching(addon, sid, key):
    if not key.endswith('.token') and key not in ('easynews.password', 'linksnappy.password', 'filepursuit.api.key'):
        return
    service = key.split('.')[0]
    short = {'torbox': 'tb', 'realdebrid': 'rd', 'premiumize': 'pm',
             'alldebrid': 'ad', 'easydebrid': 'ed', 'offcloud': 'oc'}.get(service, service)
    candidates = (service + '.enabled', service + '.enable', short + '.enabled',
                  service + '_enabled', short + '_enabled', short + '_auth_done',
                  'debrid_use_' + ('tr' if service == 'torbox' else short),
                  'provider.easynews' if service == 'easynews' else '',
                  'provider.easy' if service == 'easynews' else '',
                  'enable_easynews' if service == 'easynews' else '',
                  'RealDebridResolver_login' if service == 'realdebrid' else '',
                  {'torbox': 'TorBoxResolver_enabled', 'realdebrid': 'RealDebridResolver_enabled',
                   'premiumize': 'PremiumizeMeResolver_enabled', 'alldebrid': 'AllDebridResolver_enabled',
                   'offcloud': 'OffCloudResolver_enabled'}.get(service, ''))
    for flag in set(candidates):
        if flag and addon.schema and addon.schema.get(flag) in ('bool', 'boolean'):
            addon.setSetting(flag, 'false')
    if addon.id == 'plugin.video.otaku':
        addon.set_optional(service + '.auth.status', '')
        addon.set_optional(service + '.username', '')
        if service == 'realdebrid':
            addon.set_optional('realdebrid.expiry', '0')


def clear_matching(before, source_keys):
    """Remove only values matching the credential snapshot being signed out."""
    from reauthorize.modules import import_map
    from reauthorize.modules.sync import tmdbmovies_sync
    if 'tmdb.authorization' in source_keys:
        from reauthorize.modules.auth.tmdb import clear_helper_matching, clear_umbrella_matching
        clear_helper_matching(before.get('tmdb.authorization'))
        clear_umbrella_matching(before.get('tmdb.authorization'), before.get('tmdb.session_id'))
        from reauthorize.modules.auth.tmdb import bundle, portal_bundle, PORTAL_FIELD
        from reauthorize.modules.sync import portal_sync
        converted = portal_bundle(before.get(PORTAL_FIELD), bundle(before.get('tmdb.authorization')))
        if converted:
            portal_sync.revoke_tmdb(converted['session_id'])
    for addon_id, mapping in import_map.SETTINGS.items():
        if not installed(addon_id) or not source_keys.intersection(mapping.values()):
            continue
        try:
            addon = _Addon(addon_id)
            for sid, key in mapping.items():
                if key not in source_keys or not before.get(key) or not addon._writable(sid):
                    continue
                if addon.getSetting(sid) != before[key]:
                    continue
                addon.setSetting(sid, '')
                _disable_matching(addon, sid, key)
                if addon_id == tmdbmovies_sync.ADDON_ID and sid in tmdbmovies_sync.CLOUD_STATUS:
                    tmdbmovies_sync.status(tmdbmovies_sync.CLOUD_STATUS[sid], 'Disconnected')
        except IncompatibleSetting:
            continue
        except Exception:
            failed(addon_id)
    if 'realdebrid.token' in source_keys and before.get('realdebrid.token'):
        from reauthorize.modules.sync import aniverse_sync
        try:
            aniverse_sync.clear_matching_rd(before)
        except OSError:
            failed(aniverse_sync.ADDON_ID)
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
        if not source_keys.intersection(spec['keys'].values()):
            continue
        conn = None
        changed = False
        try:
            conn = sqlite3.connect(path, timeout=3)
            with conn:
                for sid, key in spec['keys'].items():
                    if key in source_keys and before.get(key):
                        cur = conn.execute("UPDATE settings SET setting_value='' WHERE setting_id=? AND setting_value=?", (sid, before[key]))
                        if cur.rowcount:
                            changed = True
                            if conn.execute('SELECT setting_value FROM settings WHERE setting_id=?', (sid,)).fetchone() != ('',):
                                raise RuntimeError('Credential wipe readback did not match')
                            if sid in ('tb.token', 'rd.token', 'pm.token', 'ad.token', 'oc.token', 'ed.token'):
                                flag = sid.split('.')[0] + '.enabled'
                                conn.execute("UPDATE settings SET setting_value='false' WHERE setting_id=?", (flag,))
                                row = conn.execute('SELECT setting_value FROM settings WHERE setting_id=?', (flag,)).fetchone()
                                if row is not None and row != ('false',):
                                    raise RuntimeError('Enable flag wipe readback did not match')
        except Exception:
            failed(aid)
        finally:
            if conn is not None:
                conn.close()
        if changed and aid == 'plugin.video.redlight':
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.redlight/?mode=sync_settings&silent=true&load_properties=false&force=true)')


def after_action(action, before):
    from reauthorize.modules import control, autosend
    if not before:
        return
    if action in autosend.TAG_FOR_ACTION:
        return  # autosend uses the runner, which invokes extra()
    revoked = {'realdebridRevoke': 'realdebrid.', 'premiumizeRevoke': 'premiumize.',
               'alldebridRevoke': 'alldebrid.', 'torboxRevoke': 'torbox.',
               'easydebridRevoke': 'easydebrid.', 'debridlinkRevoke': 'debridlink.', 'offcloudRevoke': 'offcloud.',
               'easynewsRevoke': 'easynews.', 'linksnappyRevoke': 'linksnappy.',
               'filepursuitRevoke': 'filepursuit.', 'fanartRevoke': 'fanart.tv.',
               'omdbRevoke': 'omdb.', 'imdbRevoke': 'imdb.', 'tmdbRevoke': 'tmdb.'}
    prefix = revoked.get(action)
    if prefix:
        begin()
        keys = {k for k, value in before.items() if k.startswith(prefix) and value and not control.setting(k)}
        if keys:
            clear_matching(before, keys)
    elif action == 'removeService':
        keys = {k for k, value in before.items() if value and not control.setting(k)}
        clear_matching(before, keys)
    if prefix or action == 'removeService':
        if errors() or warnings():
            details = ['%s: %s' % item for item in warnings()]
            details += ['%s: credential removal could not be verified' % aid for aid in errors()]
            control.dialog.ok('Diggz Account Manager', '[CR]'.join(details))


def scrub_crew_simkl():
    from reauthorize.modules.sync import crew_trakt
    crew_trakt._patch_backups({'simkl.token': '', 'simkl.user': '', 'simkl.client_id': ''})
