"""Read stored add-on credentials for the status dashboard."""
import json

import xbmc
import xbmcaddon

from reauthorize.modules import dashboard_catalog, importer, import_map, tmdbh_compat

TMDB_HELPER = 'plugin.video.themoviedb.helper'
SYNC_TAGS = {
    'trakt': 'trakt', 'realdebrid': 'rd', 'premiumize': 'pm', 'alldebrid': 'ad',
    'easydebrid': 'easyd', 'debridlink': 'debridlink',
    'torbox': 'torbox', 'offcloud': 'offc', 'easynews': 'easy',
    'filepursuit': 'filep', 'tmdb': 'meta', 'fanarttv': 'meta',
    'simkl': 'simkl', 'punchplay': 'punchplay', 'lastfm': 'lastfm',
    'mdblist': 'meta', 'torrentclaw': 'torrentclaw', 'youtube': 'yt',
}


def target(addon_id, service_id):
    if addon_id == TMDB_HELPER:
        provider = {'trakt': tmdbh_compat.TRAKT, 'mdblist': tmdbh_compat.MDBLIST}.get(service_id)
        if provider and tmdbh_compat.installed(provider):
            return provider
    return addon_id


def scan(rows, services, account):
    """Return local credential state and sync candidates, indexed by add-on and service."""
    stored = importer._collect()
    states = {}
    pending = {}
    for addon_id, supported in rows.items():
        for service in services:
            sid = service['id']
            if sid not in supported:
                continue
            receiver = target(addon_id, sid)
            pair = (addon_id, sid)
            keys = tuple(service.get('token_keys') or (service['token_key'],))
            if sid == 'easynews':
                keys = ('easynews.username', 'easynews.password')
            if not xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % receiver):
                states[pair] = 'unknown'
                continue
            try:
                state = read_state(receiver, sid, keys, stored.get(receiver, {}))
            except Exception:
                state = 'unknown'
            states[pair] = state
            if state != 'missing' or sid not in SYNC_TAGS:
                continue
            if sid in dashboard_catalog.DIRECT_FIELDS.get(receiver, {}) and pair not in dashboard_catalog.DIRECT_SYNC:
                continue
            source_keys = ('mdb.api.key',) if sid == 'mdblist' else keys
            if pair == ('plugin.video.tmdbmovies', 'trakt') and not importer._is_value(account.getSetting('trakt.refresh')):
                continue
            if sid == 'tmdb':
                # A personal account session cannot fill a metadata API-key field.
                source_keys = tuple(key for key in keys if key in mapped_credentials(receiver))
            if sid == 'youtube':
                source_keys = ('youtube.tokens',)
                if all(importer._is_value(account.getSetting(k)) for k in
                       ('youtube.api.key', 'youtube.api.id', 'youtube.api.secret')):
                    pending[pair] = SYNC_TAGS[sid]
                    continue
            if receiver == 'plugin.video.aniverse' and sid == 'realdebrid':
                from reauthorize.modules.sync import aniverse_sync
                if all(importer._is_value(account.getSetting(key)) for key in aniverse_sync.RD_FIELDS.values()):
                    pending[pair] = SYNC_TAGS[sid]
                continue
            configured = [importer._is_value(account.getSetting(k)) for k in source_keys]
            if (all(configured) if sid == 'easynews' else any(configured)):
                pending[pair] = SYNC_TAGS[sid]
    return states, pending


def read_state(addon_id, service_id, keys, held):
    if (addon_id, service_id) in dashboard_catalog.UNKNOWN:
        return 'unknown'
    if addon_id == 'plugin.video.prism' and service_id == 'offcloud':
        from reauthorize.modules import sync_support
        schema = sync_support.declared_settings(xbmcaddon.Addon(addon_id))
        if schema is not None and schema.get('oc.token', 'action') == 'action':
            return 'unknown'
    if addon_id == 'plugin.video.aniverse' and service_id == 'realdebrid':
        from reauthorize.modules.sync import aniverse_sync
        return 'present' if aniverse_sync.rd_configured(aniverse_sync.read_rd()) else 'missing'
    if addon_id == 'plugin.video.salts' and service_id == 'trakt':
        from reauthorize.modules.sync import salts_sync
        has_token = salts_sync.trakt_file_has_token()
        if has_token is not None:
            return 'present' if has_token else 'missing'
    direct = dashboard_catalog.DIRECT_FIELDS.get(addon_id, {}).get(service_id)
    if direct:
        values = importer._read_settings(addon_id, direct)
        return 'present' if all(key in values for key in direct) else 'missing'
    if service_id == 'trakt' and addon_id in (TMDB_HELPER, tmdbh_compat.TRAKT):
        field = 'token' if addon_id == tmdbh_compat.TRAKT else 'trakt_token'
        raw = xbmcaddon.Addon(addon_id).getSetting(field)
        bundle = json.loads(raw) if raw else {}
        if not isinstance(bundle, dict):
            return 'unknown'
        return 'present' if importer._is_value(bundle.get('access_token') or '') else 'missing'
    if service_id == 'punchplay':
        from reauthorize.modules.sync import punchplay_sync
        if addon_id in punchplay_sync.ADDONS:
            return 'present' if importer._is_value(punchplay_sync._held(addon_id)[0]) else 'missing'
    if service_id == 'youtube' and addon_id == 'plugin.video.youtube':
        from reauthorize.modules.sync import youtube_sync
        if youtube_sync.signed_in():
            return 'present'
        if all(held.get(key) for key in youtube_sync.API_KEYS):
            return 'present'
        return 'missing'
    if not mapped_credentials(addon_id).intersection(keys):
        return 'unknown'
    if service_id == 'easynews':
        present = all(held.get(key) for key in keys)
    else:
        present = any(held.get(key) for key in keys)
    return 'present' if present else 'missing'


def mapped_credentials(addon_id):
    settings = import_map.SETTINGS.get(addon_id, {})
    database = import_map.DATABASES.get(addon_id, {})
    return set(settings.values()) | set(database.get('keys', {}).values())


_RESOLVER_CREDENTIALS = (
    ('RealDebridResolver_token',),
    ('PremiumizeMeResolver_token',),
    ('AllDebridResolver_token',),
    ('TorBoxResolver_apikey',),
    ('OffCloudResolver_apikey',),
    ('DebridLinkResolver_token',),
    ('CocoLeechResolver_apikey',),
    ('BoxbitResolver_token',),
    ('LinkSnappyResolver_username', 'LinkSnappyResolver_password'),
    ('MegaDebridResolver_username', 'MegaDebridResolver_password'),
    ('RPnetResolver_username', 'RPnetResolver_password'),
    ('SimplyDebridResolver_username', 'SimplyDebridResolver_password'),
)


def resolver_badge_color():
    if not xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % dashboard_catalog.RESOLVEURL):
        return '18FFFFFF'
    keys = [key for group in _RESOLVER_CREDENTIALS for key in group]
    saved = importer._read_settings(dashboard_catalog.RESOLVEURL, keys)
    return 'FFFFFFFF' if any(all(key in saved for key in group)
                             for group in _RESOLVER_CREDENTIALS) else '18FFFFFF'
