# -*- coding: utf-8 -*-
"""
    ReAuthorize - Run every service sync
    Shared by default.py (manual sync buttons/actions) and startup.py
    (automatic sync right after a silent credential restore on boot).
"""

import xbmc
from reauthorize.modules import control

META_KEYS = [
    'fanart.tv.api.key', 'omdb.api.key', 'mdb.api.key', 'imdb.user',
    'tmdb.api.key', 'tmdb.username', 'audiodb.api.key',
]

_SERVICE_LABELS = {
    'trakt': 'Trakt', 'rd': 'Real-Debrid', 'pm': 'Premiumize', 'ad': 'AllDebrid',
    'torbox': 'TorBox', 'easyd': 'Easy Debrid', 'offc': 'OffCloud',
    'easy': 'Easynews', 'filep': 'FilePursuit', 'linksnappy': 'Linksnappy',
    'debridlink': 'Debrid-Link', 'simkl': 'Simkl', 'lastfm': 'Last.fm',
    'meta': 'Metadata', 'yt': 'YouTube', 'mdbo': 'MDBList', 'punchplay': 'PunchPlay',
    'torrentclaw': 'TorrentClaw',
}


# The tags of the services run_all_syncs is wiping right now; empty otherwise.
_wipe_tags = ()
# When set, the only services this run sends (modules/autosend.py: one service, right after its sign-in).
_only_tags = ()


def _try(label, failed, fn):
    """
    Run one service's sync in isolation - a single failure must never block the rest.
    A service being wiped runs with control.wiping() on, so blocks that would skip a
    blank value write it instead.
    """
    if _only_tags and label not in _only_tags:
        return
    from reauthorize.modules import sync_support
    sync_support.begin()
    control.set_wiping(label in _wipe_tags)
    try:
        fn()
        sync_support.extra(label)
        if sync_support.errors():
            flag = {'trakt':'tk','meta':'meta','rd':'rd','pm':'pm','ad':'ad','torbox':'torbox','easyd':'easyd','offc':'offc','easy':'easy','filep':'filep','linksnappy':'linksnappy','lastfm':'lastfm'}.get(label)
            if flag:
                control.setSetting('sync.%s.service' % flag, '')
            failed.append(_SERVICE_LABELS.get(label, label))
    except Exception as e:
        xbmc.log('[ReAuthorize] run_all_syncs: %s sync failed: %s' % (label, e), xbmc.LOGERROR)
        failed.append(_SERVICE_LABELS.get(label, label))
    finally:
        if _SERVICE_LABELS.get(label, label) in failed:
            flag = {'trakt':'tk','meta':'meta','rd':'rd','pm':'pm','ad':'ad','torbox':'torbox','easyd':'easyd','offc':'offc','easy':'easy','filep':'filep','linksnappy':'linksnappy','lastfm':'lastfm'}.get(label)
            if flag:
                control.setSetting('sync.%s.service' % flag, '')
        control.set_wiping(False)


def refresh_sync_modules():
    """
    Most sync and db modules read ReAuthorize's sign-ins ONCE, when they are first imported
    (module-level 'your_token = ...'). A button press is a new process, so that was always
    current. The start-up service is one process that now lives as long as Kodi (1.3.7), and
    a sync it runs hours later would send what those modules read at the start: a Trakt token
    since renewed, or a blank for a service signed in to meanwhile. Reload the ones already
    imported, so every sync in a long-lived process reads the sign-ins as they are now.
    """
    import importlib
    import sys
    for name in sorted(sys.modules):
        if name.startswith(('reauthorize.modules.sync.', 'reauthorize.modules.db.')):
            module = sys.modules.get(name)
            if module is None:
                continue
            try:
                importlib.reload(module)
            except Exception as e:
                xbmc.log('[ script.module.reauthorize ]  could not reload %s: %s' % (name, e), xbmc.LOGINFO)


def run_all_syncs(include_trakt=True, wipe=(), only=()):
    """
    Push every authorized service's credentials to its installed addons.
    include_trakt=False skips the Trakt push only - used when the user hasn't
    (yet) consented to Trakt being auto-linked on every fresh build boot.

    wipe: service tags ('rd', 'pm', 'ad', 'torbox', 'easyd', 'offc',
    'linksnappy', 'easy', 'debridlink', 'simkl', 'filep', 'meta') to push even though
    ReAuthorize's own setting for them is blank. Normally a blank setting
    means "nothing to sync" and the service is skipped; a caller that just
    cleared a credential ReAuthorize itself doesn't own (see
    startup._shared_backup_notice) passes its tag here so the blank value
    still reaches every addon that already has the old one - otherwise the
    addon keeps the stale credential forever, since nothing else will ever
    push over it. Trakt is not covered here: clearing it means revoking the
    token, which the caller does directly.

    only: service tags to send and nothing else (the same tags as 'wipe', plus 'lastfm', 'mdbo',
    'yt'); empty means every service. Used right after one sign-in, so a single service does not
    cost a full sync.

    Returns a list of friendly service names that failed (empty if all succeeded),
    so callers can tell the user exactly what needs another look instead of a
    blanket "Done!" that may not be true.

    Red Light is told to reload its settings once, after every service has
    written, instead of once per service. See db/redlight_db.py.
    """
    refresh_sync_modules()
    from reauthorize.modules.db import redlight_db
    global _wipe_tags, _only_tags
    _wipe_tags = set(wipe)
    _only_tags = set(only)
    redlight_db.begin_batch()
    try:
        return _sync_each(include_trakt, wipe)
    finally:
        _wipe_tags = ()
        _only_tags = ()
        redlight_db.end_batch()


def _sync_each(include_trakt, wipe=()):
    failed = []

    if include_trakt and control.setting('trakt.token'):
        def _tk():
            from reauthorize.modules.sync import trakt_sync
            trakt_sync.Auth().trakt_auth()
            control.setSetting('sync.tk.service', 'true')
        _try('trakt', failed, _tk)

    if control.setting('realdebrid.token') or 'rd' in wipe:
        def _rd():
            from reauthorize.modules.sync import debrid_rd
            debrid_rd.Auth().realdebrid_auth()
            control.setSetting('sync.rd.service', '' if 'rd' in wipe else 'true')
        _try('rd', failed, _rd)

    if control.setting('premiumize.token') or 'pm' in wipe:
        def _pm():
            from reauthorize.modules.sync import debrid_pm
            debrid_pm.Auth().premiumize_auth()
            control.setSetting('sync.pm.service', '' if 'pm' in wipe else 'true')
        _try('pm', failed, _pm)

    if control.setting('alldebrid.token') or 'ad' in wipe:
        def _ad():
            from reauthorize.modules.sync import debrid_ad
            debrid_ad.Auth().alldebrid_auth()
            control.setSetting('sync.ad.service', '' if 'ad' in wipe else 'true')
        _try('ad', failed, _ad)

    if control.setting('torbox.token') or 'torbox' in wipe:
        def _torbox():
            from reauthorize.modules.sync import torbox_sync
            torbox_sync.Auth().torbox_auth()
            control.setSetting('sync.torbox.service', '' if 'torbox' in wipe else 'true')
        _try('torbox', failed, _torbox)

    if control.setting('easydebrid.token') or 'easyd' in wipe:
        def _easyd():
            from reauthorize.modules.sync import easydebrid_sync
            easydebrid_sync.Auth().easydebrid_auth()
            control.setSetting('sync.easyd.service', '')
            if 'easyd' not in wipe:
                raise RuntimeError('EasyDebrid has no verified active target in supplied POV/Umbrella')
        _try('easyd', failed, _easyd)

    if control.setting('offcloud.token') or 'offc' in wipe:
        def _offc():
            from reauthorize.modules.sync import offcloud_sync
            offcloud_sync.Auth().offcloud_auth()
            control.setSetting('sync.offc.service', '' if 'offc' in wipe else 'true')
        _try('offc', failed, _offc)

    if control.setting('easynews.password') or 'easy' in wipe:
        def _easy():
            from reauthorize.modules.sync import easy_sync
            easy_sync.Auth().easy_auth()
            control.setSetting('sync.easy.service', '' if 'easy' in wipe else 'true')
        _try('easy', failed, _easy)

    if control.setting('filepursuit.api.key') or 'filep' in wipe:
        def _filep():
            from reauthorize.modules.sync import filepursuit_sync
            filepursuit_sync.Auth().file_auth()
            control.setSetting('sync.filep.service', '' if 'filep' in wipe else 'true')
        _try('filep', failed, _filep)

    if control.setting('linksnappy.username') or 'linksnappy' in wipe:
        def _linksnappy():
            from reauthorize.modules.sync import linksnappy_sync
            linksnappy_sync.Auth().linksnappy_auth()
            control.setSetting('sync.linksnappy.service', '' if 'linksnappy' in wipe else 'true')
        _try('linksnappy', failed, _linksnappy)

    if control.setting('debridlink.token') or 'debridlink' in wipe:
        def _debridlink():
            from reauthorize.modules.sync import debridlink_sync
            # Only claim the service is synced if it actually reached an addon.
            # Debrid-Link currently reaches none - Salts was its only target
            # and Salts is retired - so this flag stays off and the UI stops
            # showing a green light for something that did nothing.
            control.setSetting('sync.debridlink.service', '')
            if 'debridlink' not in wipe:
                raise RuntimeError('Debrid-Link has no verified compatible credential sender')
        _try('debridlink', failed, _debridlink)

    if control.setting('simkl.token') or 'simkl' in wipe:
        def _simkl():
            from reauthorize.modules.sync import simkl_sync
            simkl_sync.Auth().simkl_auth()
        _try('simkl', failed, _simkl)

    if control.setting('lastfm.password') or control.setting('lastfm.session.key') or 'lastfm' in wipe:
        def _lastfm():
            from reauthorize.modules.sync import lastfm_sync
            lastfm_sync.Auth().lastfm_auth()
            control.setSetting('sync.lastfm.service', '' if 'lastfm' in wipe else 'true')
        _try('lastfm', failed, _lastfm)

    # MDBList account sign-in (1.3.7) into the MDBList Scrobbler; a wipe takes it out again.
    if control.setting('mdblist.oauth.token') or 'mdbo' in wipe:
        def _mdbo():
            from reauthorize.modules.sync import mdblist_oauth_sync
            if 'mdbo' in wipe:
                mdblist_oauth_sync.wipe()
            else:
                mdblist_oauth_sync.push()
        _try('mdbo', failed, _mdbo)

    # PunchPlay (1.4.1): the access token only; ReAuthorize alone renews it (auth/punchplay.py).
    if control.setting('punchplay.token') or 'punchplay' in wipe:
        def _punchplay():
            from reauthorize.modules.sync import punchplay_sync
            if 'punchplay' in wipe:
                punchplay_sync.wipe()
            else:
                punchplay_sync.push()
        _try('punchplay', failed, _punchplay)

    # TorrentClaw (1.4.4): the user's own key, typed once (auth/torrentclaw.py); a wipe blanks it.
    if control.setting('torrentclaw.api.key') or 'torrentclaw' in wipe:
        def _torrentclaw():
            from reauthorize.modules.sync import torrentclaw_sync
            torrentclaw_sync.push()
        _try('torrentclaw', failed, _torrentclaw)

    if any(control.setting(k) for k in META_KEYS) or 'meta' in wipe:
        def _meta():
            if 'meta' not in wipe and not any(control.setting(k) for k in META_KEYS if k != 'audiodb.api.key'):
                raise RuntimeError('TheAudioDB has no configured receiving integration')
            from reauthorize.modules.sync import meta_sync
            meta_sync.Auth().meta_auth()
            control.setSetting('sync.meta.service', '' if 'meta' in wipe else 'true')
        _try('meta', failed, _meta)

    # Also runs for a stored sign-in with no personal API keys: someone using
    # YouTube's shipped keys still wants their sign-in back after a build.
    if (control.setting('youtube.tokens')
            or (control.setting('youtube.api.key') and control.setting('youtube.api.id')
                and control.setting('youtube.api.secret'))):
        def _yt():
            from reauthorize.modules.sync import youtube_sync
            youtube_sync.Auth().youtube_auth()
            control.setSetting('sync.yt.service', 'true')
        _try('yt', failed, _yt)

    return failed
