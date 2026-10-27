import xbmcvfs
from libs.common import var

# Every add-on trakt_sync.py knows how to hand Trakt to: the label its block is
# gated on, and the var.py path that says whether the add-on is installed.
# A new add-on with a Trakt block in trakt_sync.py needs a line here too.
TARGETS = [
    ('Seren',           'chk_seren'),
    ('The Coalition',   'chk_coal'),
    ('POV',             'chk_pov'),
    ('Umbrella',        'chk_umb'),
    ('Infinity',        'chk_infinity'),
    ('Shadow',          'chk_shadow'),
    ('Ghost',           'chk_ghost'),
    ('Blue Balls',      'chk_blueballs'),
    ('Twisted',         'chk_twisted'),
    ('Base',            'chk_base'),
    ('Chain Reaction',  'chk_chains'),
    ('Patriot',         'chk_patriot'),
    ('Black Lightning', 'chk_blackl'),
    ('Aliunde K19',     'chk_aliunde'),
    ('Homelander',      'chk_home'),
    ('Quicksilver',     'chk_quick'),
    ('Chains Genocide', 'chk_genocide'),
    ('Genocide',        'chk_newgenocide'),
    ('Absolution',      'chk_absol'),
    ('Shazam',          'chk_shazam'),
    ('The Crew',        'chk_crew'),
    ('Nightwing',       'chk_nightwing'),
    ('Scrubs V2',       'chk_scrubs'),
    ('TMDb Helper',     'chk_tmdbh'),
    ('Trakt Addon',     'chk_trakt'),
    ('All Accounts',    'chk_allaccounts'),
    ('My Accounts',     'chk_myaccounts'),
    ('Gears',           'chk_gears_video'),
    ('GratisRed',       'chk_gratisred'),
    ('Orion',           'chk_orion'),
    ('Red Light',       'chk_redlight'),
    ('Cosmos',          'chk_cosmos'),
    ('The Archives',    'chk_thearchives'),
    ('FidoK19',         'chk_fidok19'),
    ('TorqueLite',      'chk_torquelite'),
    ('TorqueLive',      'chk_torquelive'),
    ('Diamond Media Player', 'chk_rdtplayer'),
    ('TMDb Movies',     'chk_tmdbmovies'),
    ('Youtube Theater', 'chk_youtubetheater'),
    ('Mad Titan Sports', 'chk_madtitan'),
]


def installed_addons():
    """Labels of the installed add-ons that receive Trakt - all of them.

    Trakt used to go only to one "primary" add-on the user picked into
    trakt_sync_list.json. The reason was the shared refresh token: every add-on
    that refreshed its own copy spent it for the rest. ReAuthorize now renews the
    token itself, long before any add-on would (Trakt.refresh_if_due), so every
    add-on can hold it. It also means a build wipe, which took that file with
    it, no longer leaves Trakt pushed nowhere.
    """
    installed = []
    for label, chk in TARGETS:
        path = getattr(var, chk, None)
        if path and xbmcvfs.exists(path):
            installed.append(label)
    return installed
