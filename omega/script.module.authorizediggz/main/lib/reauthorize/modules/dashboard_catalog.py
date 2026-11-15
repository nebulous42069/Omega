"""Dashboard-only capabilities verified against the supplied add-on versions."""
from reauthorize.modules import addon_service_view, importer, tmdbh_compat

RESOLVEURL = 'script.module.resolveurl'
RESOLVER_ONLY = frozenset({
    'plugin.video.absolution', 'plugin.video.homelander', 'plugin.video.nightwing',
    'plugin.video.quicksilver', 'plugin.video.scrubsv2', 'plugin.video.cumination',
    'plugin.video.thecrew',
})
RESOLVER_BADGE = RESOLVER_ONLY | {
    'plugin.video.blacklightning', 'plugin.video.thechains', 'plugin.video.ghost',
    'plugin.video.salts', 'plugin.video.gratisred',
}
CREW_FALLBACK = {
    'realdebrid': ('realdebridtoken',),
    'alldebrid': ('alldebridtoken',),
    'premiumize': ('premiumizetoken',),
}
DIRECT_FIELDS = {
    'plugin.video.tmdbmovies': {'trakt': ('trakt_access_token', 'trakt_refresh_token')},
    'plugin.video.thecrew': CREW_FALLBACK,
    # The Archives stores its own TMDB account session. The metadata sender
    # has no TMDB write for this add-on, so this is a status-only indicator.
    'plugin.video.thearchives': {'tmdb': ('tmdb.session_id',)},
    'plugin.video.blacklightning': {
        'premiumize': ('premiumize.token',), 'alldebrid': ('alldebrid.token',),
        'torbox': ('tb.token',),
    },
    'plugin.video.thechains': {'torbox': ('tb.token',)},
    'plugin.video.ghost': {'torbox': ('tb.token',)},
    'plugin.video.genocide': {'mdblist': ('mdblist.user',), 'offcloud': ('offcloud.token',)},
    'plugin.video.gratisred': {'mdblist': ('mdblist.token',)},
    'plugin.video.otaku': {
        'alldebrid': ('alldebrid.token',), 'debridlink': ('debridlink.token',),
        'torbox': ('torbox.token',), 'easydebrid': ('easydebrid.token',),
        'easynews': ('easynews.user', 'easynews.password'), 'simkl': ('simkl.token',),
    },
    'plugin.video.pov': {
        'offcloud': ('oc.token',), 'torbox': ('tb.token',),
        'tmdb': ('tmdb.token', 'tmdb.session_id'),
    },
    'plugin.video.salts': {
        'trakt': ('trakt_access_token',), 'realdebrid': ('realdebrid_token',),
        'premiumize': ('premiumize_token',), 'alldebrid': ('alldebrid_token',),
        'torbox': ('torbox_token',), 'easydebrid': ('easydebrid_token',),
        'debridlink': ('debridlink_token',), 'offcloud': ('offcloud_token',),
        'easynews': ('easynews_username', 'easynews_password'),
    },
    'plugin.video.seren': {
        'offcloud': ('offcloud.apikey',), 'debridlink': ('debridlink.token',),
    },
}
# These indicators are read-only until there is a verified ReAuthorize sender.
# Existing senders may still be used for the specific pairs listed here.
DIRECT_SYNC = {
    ('plugin.video.tmdbmovies', 'trakt'),
    ('plugin.video.otaku', 'alldebrid'), ('plugin.video.otaku', 'torbox'),
    ('plugin.video.pov', 'offcloud'), ('plugin.video.pov', 'torbox'),
    ('plugin.video.seren', 'offcloud'),
} | {('plugin.video.salts', service)
     for service in DIRECT_FIELDS['plugin.video.salts'] if service != 'premiumize'}
UNKNOWN = {
    ('plugin.video.genocide', 'simkl'),  # API client ID only
    ('plugin.video.seren', 'simkl'),     # Toggle with no account token field
}


def services():
    definitions = addon_service_view.status_services()
    definitions.append({'id': 'debridlink', 'label': 'Debrid-Link',
                        'token_key': 'debridlink.token',
                        'icon': addon_service_view.get_service_icon_path('debridlink')})
    return definitions


def rows(installed):
    result = {}
    for service, addons in addon_service_view.SERVICE_ADDONS.items():
        for addon_id in addons:
            if (addon_id not in addon_service_view.STATUS_HIDDEN
                    and addon_id != 'plugin.video.lookmovietomb' and installed(addon_id)):
                result.setdefault(addon_id, set()).add(service)
    for addon_id in RESOLVER_BADGE:
        if installed(addon_id):
            result.setdefault(addon_id, set())
    for addon_id in RESOLVER_ONLY.intersection(result):
        result[addon_id].difference_update(addon_service_view.DEBRID_SERVICE_IDS)
    if 'plugin.video.cumination' in result:
        result['plugin.video.cumination'].discard('trakt')
    for addon_id, fields in DIRECT_FIELDS.items():
        if not installed(addon_id):
            continue
        if addon_id == 'plugin.video.thecrew':
            fallback = importer._read_settings(addon_id, [keys[0] for keys in fields.values()])
            fields = {service for service, keys in fields.items() if keys[0] in fallback}
        result.setdefault(addon_id, set()).update(fields)
    for addon_id, service in UNKNOWN:
        if installed(addon_id):
            result.setdefault(addon_id, set()).add(service)
    if installed('plugin.video.redlight'):
        result.setdefault('plugin.video.redlight', set()).add('offcloud')
    # Provider rows own the credentials once these modules are installed.
    core = result.get('plugin.video.themoviedb.helper', set())
    if installed(tmdbh_compat.TRAKT):
        core.discard('trakt')
    if installed(tmdbh_compat.MDBLIST):
        core.discard('mdblist')
    return result
