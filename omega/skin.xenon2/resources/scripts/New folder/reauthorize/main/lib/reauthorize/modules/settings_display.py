# -*- coding: utf-8 -*-

import re

from reauthorize.modules import control

_MASK = '**************'

# The values are written plain: a read-only row is drawn in Kodi's own dim grey, which the user prefers
# (2026-10-18: 'it breaks things up visually; it isn't a book'). plain() takes off the colour a 1.4.4 test
# build put on them. Each row is written only when its value changed.
_WRAPPED = re.compile(r'^\[COLOR [^\]]+\](.*)\[/COLOR\]$', re.S)


def plain(value):
    """The value without a colour tag around it."""
    value = value or ''
    m = _WRAPPED.match(value)
    return m.group(1) if m else value


def _put(display_key, value):
    value = plain(value)
    if control.setting(display_key) != value:
        control.setSetting(display_key, value)


def _set_display(raw_key, display_key, mask=False):
    value = control.setting(raw_key)
    if mask and value:
        value = _MASK
    _put(display_key, value)


def sync_authorized_display_values():
    """Populate display-only fields for authorized services."""
    # The version that is running, first row of the first tab (asked for by the user, 2026-10-13).
    # Embedded copy: show its version without standalone repository status.
    try:
        line = control.addonVersion()
        if line:
            _put('version.display', line)
    except Exception:
        pass
    # Debrid + account services
    if control.setting('realdebrid.token'):
        _set_display('realdebrid.username', 'realdebrid.username.display')
    else:
        _put('realdebrid.username.display', '')

    if control.setting('premiumize.token'):
        _set_display('premiumize.username', 'premiumize.username.display')
    else:
        _put('premiumize.username.display', '')

    if control.setting('alldebrid.token'):
        _set_display('alldebrid.username', 'alldebrid.username.display')
    else:
        _put('alldebrid.username.display', '')

    if control.setting('offcloud.token'):
        _put('offcloud.authorized.display', 'Authorized')
    else:
        _put('offcloud.authorized.display', '')

    if control.setting('easynews.password'):
        _set_display('easynews.username', 'easynews.username.display')
        _set_display('easynews.password', 'easynews.password.display', mask=True)
    else:
        _put('easynews.username.display', '')
        _put('easynews.password.display', '')

    if control.setting('torbox.token'):
        _put('torbox.authorized.display', 'Authorized')
    else:
        _put('torbox.authorized.display', '')

    if control.setting('easydebrid.token'):
        _put('easydebrid.authorized.display', 'Authorized')
    else:
        _put('easydebrid.authorized.display', '')

    if control.setting('filepursuit.api.key'):
        _put('filepursuit.authorized.display', 'Authorized')
    else:
        _put('filepursuit.authorized.display', '')

    if control.setting('debridlink.token'):
        _put('debridlink.authorized.display', 'Authorized')
    else:
        _put('debridlink.authorized.display', '')

    if control.setting('linksnappy.username'):
        _set_display('linksnappy.username', 'linksnappy.username.display')
    else:
        _put('linksnappy.username.display', '')

    if control.setting('trakt.token'):
        _set_display('trakt.username', 'trakt.username.display')
    else:
        _put('trakt.username.display', '')

    if control.setting('simkl.token'):
        _set_display('simkl.username', 'simkl.username.display')
    else:
        _put('simkl.username.display', '')

    if control.setting('mdblist.oauth.token'):
        if control.setting('mdblist.oauth.username'):
            _set_display('mdblist.oauth.username', 'mdblist.oauth.username.display')
        else:
            _put('mdblist.oauth.username.display', 'Signed in')
    else:
        _put('mdblist.oauth.username.display', '')

    if control.setting('punchplay.token'):
        if control.setting('punchplay.username'):
            _set_display('punchplay.username', 'punchplay.username.display')
        else:
            _put('punchplay.username.display', 'Signed in')
    else:
        _put('punchplay.username.display', '')

    if control.setting('lastfm.password') or control.setting('lastfm.session.key'):
        if control.setting('lastfm.username'):
            _set_display('lastfm.username', 'lastfm.username.display')
        else:
            _put('lastfm.username.display', 'Authorized')
    else:
        _put('lastfm.username.display', '')

    _put('torrentclaw.authorized.display', 'Connected' if control.setting('torrentclaw.api.key') else '')

    # Metadata / API keys
    if control.setting('tmdb.session_id'):
        _set_display('tmdb.api.key', 'tmdb.api.key.display')
        _set_display('tmdb.username', 'tmdb.username.display')
        _set_display('tmdb.password', 'tmdb.password.display', mask=True)
    else:
        _put('tmdb.api.key.display', '')
        _put('tmdb.username.display', '')
        _put('tmdb.password.display', '')

    _set_display('fanart.tv.api.key', 'fanart.tv.api.key.display')
    _set_display('audiodb.api.key', 'audiodb.api.key.display')
    _set_display('mdb.username', 'mdb.username.display')
    _set_display('mdb.api.key', 'mdb.api.key.display')
    _set_display('omdb.api.key', 'omdb.api.key.display')
    _set_display('imdb.user', 'imdb.user.display')
    if control.setting('youtube.api.key'):
        _set_display('youtube.api.key', 'youtube.api.key.display')
        _set_display('youtube.api.id', 'youtube.api.id.display')
        _set_display('youtube.api.secret', 'youtube.api.secret.display', mask=True)
    else:
        _put('youtube.api.key.display', '')
        _put('youtube.api.id.display', '')
        _put('youtube.api.secret.display', '')

    # The API keys only identify the app. The Google sign-in is a separate step,
    # and the one that decides whether the user sees their own subscriptions.
    signed_in = installed = False
    try:
        from reauthorize.modules.sync import youtube_sync
        installed = youtube_sync.is_installed()
        signed_in = youtube_sync.signed_in()
    except Exception:
        pass
    have_keys = all(control.setting(k) for k in ('youtube.api.key', 'youtube.api.id', 'youtube.api.secret'))
    if signed_in:
        status = 'Signed in'
    elif not installed:
        status = 'YouTube for Kodi is not installed'
    elif not have_keys:
        status = 'Enter the API keys first'
    else:
        status = 'Not signed in'
    control.setSetting('youtube.signedin', 'true' if signed_in else 'false')
    _put('youtube.signin.display', status)
