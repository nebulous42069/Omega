# -*- coding: utf-8 -*-
"""
    ReAuthorize - Addon/Service Visualization Helpers
    Reusable functions for displaying addon names with their associated service icons.
    Used by quick-authorize, the status dashboard and troubleshooting tabs.
"""

import os
import xbmcvfs
import xbmcaddon

ADDON_ID         = 'script.module.reauthorize'
ICONS_PATH       = os.path.join(xbmcaddon.Addon(ADDON_ID).getAddonInfo('path'), 'resources', 'icons')

# Service-to-addons mapping - the single list every screen reads from
_SERVICE_ADDONS = {
    'trakt': [
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.pov', 'plugin.video.umbrella',
        'plugin.video.infinity', 'plugin.video.shadow', 'plugin.video.ghost',
        'plugin.video.base', 'plugin.video.thechains',
        'plugin.video.patriot', 'plugin.video.blacklightning', 'plugin.video.homelander',
        'plugin.video.quicksilver', 'plugin.video.chainsgenocide', 'plugin.video.absolution',
        'plugin.video.shazam', 'plugin.video.thecrew',
        'plugin.video.nine', 'plugin.video.scrubsv2',
        'plugin.video.salts',
        'plugin.video.gears', 'plugin.video.genocide',
        'plugin.video.gratisred', 'plugin.video.orion',
        'plugin.video.otaku', 'plugin.video.syncher',
        'plugin.video.redlight', 'plugin.video.cosmos', 'plugin.video.thearchives',
        'plugin.video.aliunde', 'plugin.video.aliundek19', 'plugin.video.cumination',
        'plugin.video.lookmovietomb', 'plugin.video.blueballs', 'plugin.video.twisted',
        'script.trakt', 'script.module.trakt',
        'script.module.myaccounts', 'script.module.allaccounts',
        'plugin.video.fidoK19', 'plugin.video.torquelite', 'plugin.video.torquelive',
        'plugin.video.themoviedb.helper', 'plugin.program.rdtplayer', 'plugin.video.tmdbmovies',
        'plugin.video.youtubetheater',
        'plugin.video.nightwing', 'plugin.video.madtitansports',
    ],
    'realdebrid': [
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.pov', 'plugin.video.umbrella',
        'plugin.video.infinity', 'plugin.video.shadow', 'plugin.video.ghost',
        'plugin.video.base', 'plugin.video.thechains',
        'plugin.video.patriot', 'plugin.video.blacklightning', 'plugin.video.homelander',
        'plugin.video.quicksilver', 'plugin.video.chainsgenocide', 'plugin.video.absolution',
        'plugin.video.shazam', 'plugin.video.thecrew',
        'plugin.video.nine', 'plugin.video.scrubsv2',
        'plugin.video.salts',
        'plugin.video.realizerx',
        'plugin.video.gears', 'plugin.video.genocide',
        'plugin.video.gratisred', 'plugin.video.otaku',
        'plugin.video.syncher', 'plugin.video.redlight',
        'plugin.video.aliunde', 'plugin.video.aliundek19', 'plugin.video.cumination',
        'plugin.video.lookmovietomb', 'plugin.video.thearchives',
        'plugin.video.blueballs', 'plugin.video.twisted',
        'script.module.resolveurl', 'script.module.myaccounts', 'script.module.allaccounts',
        'plugin.program.rdtplayer', 'plugin.video.prism', 'plugin.video.tmdbmovies',
        'plugin.video.youtubetheater',
        'plugin.video.nightwing',
    ],
    'premiumize': [
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.pov', 'plugin.video.umbrella',
        'plugin.video.infinity', 'plugin.video.shadow', 'plugin.video.ghost',
        'plugin.video.base', 'plugin.video.thechains',
        'plugin.video.patriot', 'plugin.video.premiumizerx',
        'plugin.video.gears', 'plugin.video.genocide',
        'plugin.video.gratisred', 'plugin.video.syncher',
        'plugin.video.redlight', 'plugin.video.thearchives',
        'plugin.video.aliunde', 'plugin.video.aliundek19', 'plugin.video.cumination',
        'plugin.video.lookmovietomb', 'plugin.video.blueballs', 'plugin.video.twisted',
        'script.module.resolveurl', 'script.module.myaccounts', 'script.module.allaccounts',
        'plugin.program.rdtplayer', 'plugin.video.prism',
    ],
    'alldebrid': [
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.pov', 'plugin.video.umbrella',
        'plugin.video.infinity', 'plugin.video.shadow', 'plugin.video.ghost',
        'plugin.video.base', 'plugin.video.thechains',
        'plugin.video.gears', 'plugin.video.genocide',
        'plugin.video.gratisred', 'plugin.video.syncher',
        'plugin.video.redlight', 'plugin.video.thearchives',
        'plugin.video.aliunde', 'plugin.video.aliundek19', 'plugin.video.cumination',
        'plugin.video.lookmovietomb', 'plugin.video.blueballs', 'plugin.video.twisted',
        'script.module.resolveurl', 'script.module.myaccounts', 'script.module.allaccounts',
        'plugin.video.prism', 'plugin.video.youtubetheater',
    ],
    'torbox': [
        'plugin.video.seren',
        'plugin.video.umbrella', 'plugin.video.infinity',
        'plugin.video.gears', 
        'plugin.video.genocide', 'plugin.video.redlight', 'plugin.video.thearchives',
        'plugin.video.aliunde', 'plugin.video.aliundek19', 'plugin.video.cumination',
        'plugin.video.lookmovietomb',
        'script.module.resolveurl', 'plugin.program.rdtplayer', 'plugin.video.prism', 'plugin.video.tmdbmovies',
        'plugin.video.youtubetheater',
    ],
    'easydebrid': [
        'plugin.video.coalition', 'plugin.video.umbrella',
        'script.module.resolveurl',
    ],
    'offcloud': [
        'plugin.video.coalition', 'plugin.video.umbrella',
        'plugin.video.cosmos',
        'script.module.resolveurl', 'plugin.program.rdtplayer', 'plugin.video.prism', 'plugin.video.tmdbmovies',
    ],
    'easynews': [
        'plugin.video.seren', 'plugin.video.umbrella',
        'plugin.video.coalition', 'plugin.video.infinity',
        'plugin.video.orion',
        'plugin.video.genocide', 'plugin.video.redlight', 'plugin.video.cosmos', 'plugin.video.thearchives',
        'plugin.program.rdtplayer', 'plugin.video.youtubetheater',
        'script.module.myaccounts',
    ],
    'filepursuit': [
        'plugin.video.coalition', 'plugin.video.umbrella',
        'script.module.myaccounts',
    ],
    'tmdb': [
        'plugin.video.seren',
        'plugin.video.umbrella', 'plugin.video.infinity',
        'plugin.video.orion', 'plugin.video.otaku', 'plugin.video.redlight',
        'plugin.video.thearchives',
        'script.module.metahandler', 'script.module.pvr.artwork',
        'service.luc_kodi.mdblist', 'service.luc_kodi.tmdbextendedinfo',
        'metadata.common.fanart.tv',
        'plugin.video.fidoK19', 'plugin.video.torquelite', 'plugin.video.torquelive',
        'plugin.video.genocide',
        'plugin.video.nightwing', 'script.module.myaccounts',
        'plugin.video.the-loop', 'plugin.video.madtitansports',
    ],
    # Every add-on simkl_sync.py writes (1.3.9 added Red Light, Gears, TMDb Movies, The Crew and
    # the scrobbler for real; Seren was listed here but never written, so it is gone).
    'simkl': [
        'script.simkl',
        'plugin.video.umbrella', 'plugin.video.redlight', 'plugin.video.gears',
        'plugin.video.tmdbmovies', 'plugin.video.thecrew', 'plugin.video.gratisred', 'plugin.video.cosmos',
        'plugin.video.genocide', 'plugin.video.infinity', 'plugin.video.otaku',
        'plugin.video.thearchives', 'plugin.video.prism',
    ],
    # The add-ons punchplay_sync.py writes (1.4.1). The official PunchPlay scrobbler signs in
    # another way and is not fed.
    'punchplay': [
        'plugin.video.umbrella', 'plugin.video.redlight', 'plugin.video.cosmos',
        'plugin.video.tmdbmovies', 'plugin.video.thearchives',
    ],
    'lastfm': [
        'service.scrobbler.lastfm',
    ],
    # ONE MDBList, however the user signs in: the API key (Metadata tab) or the account (Trakt &
    # Scrobble tab). The user, 2026-10-09: 'treat it like it was one program no matter which way
    # they log in'. The MDBList Scrobbler is not listed on purpose: a separate 'Scrobbler' row
    # confused people; it still receives the account sign-in.
    'mdblist': [
        'plugin.video.umbrella', 'plugin.video.pov', 'plugin.video.redlight', 'plugin.video.cosmos',
        'plugin.video.thearchives',
        'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.infinity',
        'plugin.video.themoviedb.helper', 'plugin.video.prism', 'plugin.video.tmdbmovies',
    ],
    'fanarttv': [
        'metadata.common.fanart.tv',
        'plugin.video.umbrella', 'plugin.video.seren',
        'plugin.video.coalition', 'plugin.video.infinity',
        'plugin.video.themoviedb.helper', 'plugin.video.genocide',
        'plugin.video.prism',
        'plugin.video.nightwing', 'script.module.myaccounts',
    ],
    'youtube': [
        'plugin.video.youtube',
    ],
    # The add-ons torrentclaw_sync.py writes (1.4.4).
    'torrentclaw': [
        'plugin.video.cosmos',
    ],
}

# Addon ID -> friendly display name mapping
_ADDON_LABELS = {
    'plugin.video.absolution':              'Absolution',
    'plugin.video.aliunde':                 'Aliunde',
    'plugin.video.aliundek19':              'Aliunde K19',
    'plugin.video.base':                    'Base',
    'plugin.video.blacklightning':          'Black Lightning',
    'plugin.video.blueballs':               'Blue Balls',
    'plugin.video.chainsgenocide':          'Chains Genocide',
    'plugin.video.coalition':               'Coalition',
    'plugin.video.cosmos':                  'Cosmos',
    'plugin.video.cumination':              'Cumination',
    'plugin.video.fidoK19':                 'FidoK19',
    'plugin.video.gears':                   'Gears',
    'plugin.video.genesis':                 'Genesis',
    'plugin.video.genocide':                'Genocide',
    'plugin.video.ghost':                   'Ghost',
    'plugin.video.gratisred':               'GratisRed',
    'plugin.video.homelander':              'Homelander',
    'plugin.video.infinity':                'Infinity',
    'plugin.video.lookmovietomb':           'LookMovie',
    'plugin.video.the-loop':                'The Loop',
    'plugin.video.madtitansports':          'Mad Titan Sports',
    'plugin.video.nine':                    'Nine',
    'plugin.video.nightwing':               'Nightwing',
    'plugin.video.orion':                   'Orion',
    'plugin.video.otaku':                   'Otaku',
    'plugin.video.patriot':                 'Patriot',
    'plugin.video.pov':                     'POV',
    'plugin.video.premiumizerx':            'PremiumizerX',
    'plugin.video.quicksilver':             'Quicksilver',
    'plugin.video.realizerx':               'RealizerX',
    'plugin.video.redlight':                'Red Light',
    'plugin.video.salts':                   'Salts',
    'plugin.video.scrubsv2':                'Scrubs V2',
    'plugin.video.seren':                   'Seren',
    'plugin.video.shadow':                  'Shadow',
    'plugin.video.shazam':                  'Shazam',
    'plugin.video.syncher':                 'Syncher',
    'plugin.video.thearchives':             'The Archives',
    'plugin.program.rdtplayer':             'Diamond Media Player',
    'plugin.video.prism':                   'Prism',
    'plugin.video.tmdbmovies':               'TMDb Movies',
    'plugin.video.youtubetheater':          'Youtube Theater',
    'plugin.video.thechains':               'Chains',
    'plugin.video.thecrew':                 'The Crew',
    'plugin.video.twisted':                 'Twisted',
    'plugin.video.torquelite':              'TorqueLite',
    'plugin.video.torquelive':              'TorqueLive',
    'plugin.video.umbrella':                'Umbrella',
    'plugin.video.youtube':                 'YouTube for Kodi',
    'script.module.allaccounts':            'All Accounts',
    'script.module.metahandler':            'MetaHandler',
    'script.module.myaccounts':             'My Accounts',
    'script.module.pvr.artwork':            'PVR Artwork',
    'script.module.reauthorize':            'ReAuthorize',
    'plugin.video.themoviedb.helper':      'TMDb Helper',
    'script.module.resolveurl':             'ResolveURL',
    'script.module.trakt':                  'Trakt (module)',
    'script.simkl':                         'Simkl (addon)',
    'script.trakt':                         'Trakt (addon)',
    'service.luc_kodi.mdblist':             'MDB List',
    'service.luc_kodi.tmdbextendedinfo':    'TMDB Extended Info',
    'service.scrobbler.lastfm':             'Last.fm Scrobbler',
    'metadata.common.fanart.tv':            'Fanart.tv',
}

# Service ID -> icon path (relative to addon resources)
_SERVICE_ICONS = {
    'trakt': 'trakt.png',
    'realdebrid': 'realdebrid.png',
    'premiumize': 'premiumize.png',
    'alldebrid': 'alldebrid.png',
    'torbox': 'torbox.png',
    'easydebrid': 'easydebrid.png',
    'offcloud': 'offcloud.png',
    'easynews': 'easynews.png',
    'filepursuit': 'filepursuit.png',
    'tmdb': 'tmdb.png',
    'simkl': 'simkl.png',
    'punchplay': 'punchplay.png',
    'lastfm': 'lastfm.png',
    'mdblist': 'mdblist.png',
    'fanarttv': 'fanarttv.png',
    'youtube': 'youtube.png',
    'torrentclaw': 'torrent-claw.png',
    'linksnappy': 'linksnappy.png',
    'debridlink': 'debridlink.png',
}

# Service auth-state metadata used by Build Status and related views.
_SERVICE_STATE_META = {
    'trakt': {'label': 'Trakt', 'token_key': 'trakt.token', 'sync_flag': 'sync.tk.service'},
    'realdebrid': {'label': 'Real-Debrid', 'token_key': 'realdebrid.token', 'sync_flag': 'sync.rd.service'},
    'premiumize': {'label': 'Premiumize', 'token_key': 'premiumize.token', 'sync_flag': 'sync.pm.service'},
    'alldebrid': {'label': 'All-Debrid', 'token_key': 'alldebrid.token', 'sync_flag': 'sync.ad.service'},
    'torbox': {'label': 'TorBox', 'token_key': 'torbox.token', 'sync_flag': 'sync.torbox.service'},
    'easydebrid': {'label': 'Easy Debrid', 'token_key': 'easydebrid.token', 'sync_flag': 'sync.easyd.service'},
    'offcloud': {'label': 'OffCloud', 'token_key': 'offcloud.token', 'sync_flag': 'sync.offc.service'},
    'easynews': {'label': 'Easynews', 'token_key': 'easynews.username', 'sync_flag': 'sync.easy.service'},
    'filepursuit': {'label': 'FilePursuit', 'token_key': 'filepursuit.api.key', 'sync_flag': 'sync.filep.service'},
    'tmdb': {'label': 'TMDB', 'token_keys': ['tmdb.api.key', 'tmdb.session_id'], 'sync_flag': None},
    'simkl': {'label': 'Simkl', 'token_key': 'simkl.token', 'sync_flag': None},
    'punchplay': {'label': 'PunchPlay', 'token_key': 'punchplay.token', 'sync_flag': None},
    'lastfm': {'label': 'Last.fm', 'token_keys': ['lastfm.password', 'lastfm.session.key'], 'sync_flag': 'sync.lastfm.service'},
    'mdblist': {'label': 'MDBList', 'token_keys': ['mdb.api.key', 'mdblist.oauth.token'], 'sync_flag': None},
    'fanarttv': {'label': 'Fanart.TV', 'token_key': 'fanart.tv.api.key', 'sync_flag': None},
    'youtube': {'label': 'YouTube', 'token_key': 'youtube.api.key', 'sync_flag': 'sync.yt.service'},
    'torrentclaw': {'label': 'TorrentClaw', 'token_key': 'torrentclaw.api.key', 'sync_flag': None},
}

_SERVICE_ORDER = [
    'trakt',
    'realdebrid',
    'premiumize',
    'alldebrid',
    'torbox',
    'easydebrid',
    'offcloud',
    'easynews',
    'filepursuit',
    'tmdb',
    'simkl',
    'punchplay',
    'lastfm',
    'mdblist',
    'fanarttv',
    'youtube',
    'torrentclaw',
]

# Any addon that supports one debrid service should display all debrid columns.
DEBRID_SERVICE_IDS = ['realdebrid', 'premiumize', 'alldebrid', 'torbox', 'easydebrid', 'offcloud']

# Add-ons that only ever hold their own one sign-in are left off Build Status (the user, 2026-10-18:
# 'things that only log in to itself do not need a row'); a service whose only add-on is one of these
# loses its column there (Last.fm). They stay in every list above, so Compatible Add-ons and the
# sync still know them. YouTube for Kodi keeps its row: it is a whole add-on of its own, and the only
# place the YouTube sign-in shows.
STATUS_HIDDEN = ('service.scrobbler.lastfm', 'script.simkl', 'script.trakt', 'script.module.trakt')


def status_services():
    """The Build Status columns: every service at least one shown add-on receives."""
    return [svc for svc in get_service_definitions()
            if any(a not in STATUS_HIDDEN for a in _SERVICE_ADDONS.get(svc['id'], []))]


# Public aliases consumed by windows.
SERVICE_ADDONS = _SERVICE_ADDONS
ADDON_LABELS = _ADDON_LABELS

def get_addon_icon_path(addon_id, addons_base_path):
    """
    The add-on's own icon: the one its addon.xml names, which is what Kodi itself shows (POV's is
    pov.png, Red Light's sits in resources/media/addon_icons/), else an icon.png in its folder.
    Until 1.4.0 only that icon.png was tried and ReAuthorize shipped 2 MB of copies for the rest;
    every add-on on the bench and the MQ9 build has an icon of its own, and it stays current when
    the add-on changes it.
    """
    try:
        icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
        if icon and xbmcvfs.exists(icon):
            return icon.replace('\\', '/')
    except Exception:
        pass                              # not installed, or disabled
    installed = os.path.join(addons_base_path, addon_id, 'icon.png').replace('\\', '/')
    if xbmcvfs.exists(installed):
        return installed
    return ''


def get_addon_label(addon_id):
    """Return a friendly display name for an addon ID."""
    return _ADDON_LABELS.get(addon_id, addon_id.replace('plugin.video.', '').title())


def get_services_for_addon(addon_id):
    """Return list of service IDs that use this addon."""
    services = []
    for service_id, addon_list in _SERVICE_ADDONS.items():
        if addon_id in addon_list:
            services.append(service_id)
    return services


def get_addons_with_services(addons_base_path):
    """
    Scan installed addons and return list of dicts with addon info and service icons.
    [
        {'id': 'plugin.video.thechains', 'label': 'Chains', 'services': ['trakt', 'realdebrid']},
        {'id': 'plugin.video.umbrella', 'label': 'Umbrella', 'services': ['trakt']},
    ]
    """
    installed = []
    for service_id, addon_list in _SERVICE_ADDONS.items():
        for addon_id in addon_list:
            if xbmcvfs.exists(addons_base_path + addon_id + '/'):
                addon_entry = next((a for a in installed if a['id'] == addon_id), None)
                if addon_entry:
                    addon_entry['services'].append(service_id)
                else:
                    installed.append({
                        'id': addon_id,
                        'label': get_addon_label(addon_id),
                        'services': [service_id],
                    })
    return sorted(installed, key=lambda x: x['label'])


def get_service_icon_path(service_id):
    """Return full path to service icon."""
    icon_name = _SERVICE_ICONS.get(service_id)
    path = os.path.join(ICONS_PATH, icon_name if icon_name else 'icon.png')
    return path.replace('\\', '/')


def get_service_definitions():
    """Return canonical ordered service definitions for status-style dashboards."""
    defs = []
    for service_id in _SERVICE_ORDER:
        meta = _SERVICE_STATE_META[service_id]
        row = {
            'id': service_id,
            'label': meta['label'],
            'icon': get_service_icon_path(service_id),
            'sync_flag': meta.get('sync_flag'),
        }
        if 'token_keys' in meta:
            row['token_keys'] = list(meta['token_keys'])
        else:
            row['token_key'] = meta['token_key']
        defs.append(row)
    return defs


def build_service_icons_row(services):
    """
    Return comma-separated paths for service icons.
    Input: ['trakt', 'realdebrid', 'tmdb']
    Output: '/path/trakt.png,/path/realdebrid.png,/path/tmdb.png'
    """
    icon_paths = [get_service_icon_path(svc) for svc in services]
    return ','.join(icon_paths)
