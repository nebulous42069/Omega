# -*- coding: utf-8 -*-
"""
    ReAuthorize - Simkl app key in add-ons that keep theirs in a source file (1.3.9)

    Simkl ties a sign-in to the app that made it. ReAuthorize's sign-in under another
    add-on's Simkl app key is refused with 401 "user_token_failed" (checked against Simkl
    2026-10-05 with Umbrella's, TMDb Movies' and the Simkl scrobbler's keys). Until 1.3.9
    ReAuthorize only wrote the token, so every add-on that uses its own key "had" Simkl and
    could not use it (a user's report: Red Light, TMDb Movies, The Crew).

    Most add-ons read their key from a setting, and simkl_sync writes it there. These three
    keep it as one line in a source file, so that line is swapped, the same way as The Crew's
    Trakt key (crew_trakt.py): the line remembers what it said and restore puts it back.

        Umbrella          resources/lib/modules/simkl.py   simklclientid = '...'
        Simkl scrobbler   resources/lib/api_simkl.py       APIKEY = '...'
        The Archives      resources/lib/util/dev_api.py    SIMKL_CLIENT_ID = "..."
        GratisRed         resources/lib/modules/simkl.py   SIMKL_CLIENT_ID = '...'
"""

import os
import re

import xbmc

from libs.common import var

LOG_TAG = '[ReAuthorize Simkl]'
MARK = '# ReAuthorize; was: '

# (label, add-on folder, file inside it, the name on the left of the '=')
TARGETS = (
    ('Umbrella', 'plugin.video.umbrella', 'resources/lib/modules/simkl.py', 'simklclientid'),
    ('Simkl scrobbler', 'script.simkl', 'resources/lib/api_simkl.py', 'APIKEY'),
    ('The Archives', 'plugin.video.thearchives', 'resources/lib/util/dev_api.py', 'SIMKL_CLIENT_ID'),
    # GratisRed has two keys; SIMKL_CLIENT_ID is the one it uses for a sign-in with no refresh token
    # (auth_version 1). SIMKL_CLIENT_ID_V2, for its own newer sign-ins, is a different line and is left alone.
    ('GratisRed', 'plugin.video.gratisred', 'resources/lib/modules/simkl.py', 'SIMKL_CLIENT_ID'),
)


def path_of(addon_id, relative):
    return os.path.join(var.addons, addon_id, *relative.split('/'))


def paths():
    """Every key file this module may change (restart_hint watches them)."""
    return [path_of(addon_id, relative) for _, addon_id, relative, _ in TARGETS]


def _line(name):
    return re.compile(r'^(?P<head>[ \t]*' + re.escape(name) + r'[ \t]*=[ \t]*)(?P<quote>[\'"])(?P<value>[^\'"\r\n]*)(?P=quote)'
                      r'(?P<tail>[ \t]*(?:#.*)?)$', re.M)


def _marked(name):
    return re.compile(r'^([ \t]*' + re.escape(name) + r'[ \t]*=[ \t]*)[\'"][^\'"\r\n]*[\'"][ \t]*' + re.escape(MARK)
                      + r'([\'"][^\'"\r\n]*[\'"])[ \t]*$', re.M)


def swap_key(text, name, client):
    """The file's text with ReAuthorize's Simkl app key on the 'name = ...' line."""
    def swap(m):
        if MARK in m.group('tail') or m.group('value') == client:
            return m.group(0)
        return "%s'%s'  %s%s%s%s" % (m.group('head'), client, MARK, m.group('quote'), m.group('value'), m.group('quote'))
    return _line(name).sub(swap, text, count=1)


def restore_key(text, name):
    """The reverse: the marked line gets back what it said before."""
    return _marked(name).sub(lambda m: m.group(1) + m.group(2), text)


def _rewrite(label, addon_id, relative, change, done):
    path = path_of(addon_id, relative)
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return False                                  # not installed, or a version without this file
    changed = change(text)
    if changed == text:
        return False
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(changed)
        xbmc.log('%s %s %s' % (LOG_TAG, done, label), xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log('%s could not change the Simkl app key in %s: %s' % (LOG_TAG, label, e), xbmc.LOGINFO)
        return False


def ensure(addon_id, client):
    """Put ReAuthorize's key into one add-on's file. True if the file was changed."""
    if not client:
        return False
    for label, target, relative, name in TARGETS:
        if target == addon_id:
            return _rewrite(label, target, relative, lambda text: swap_key(text, name, client), 'Simkl app key set in')
    return False


def ensure_all(client):
    """The same for every add-on in TARGETS (start-up: an update of the add-on puts its own key back)."""
    return sum(1 for _, addon_id, _, _ in TARGETS if ensure(addon_id, client))


def restore(addon_id):
    """Give one add-on its own key back (sign-out, wipe). True if the file was changed."""
    for label, target, relative, name in TARGETS:
        if target == addon_id:
            return _rewrite(label, target, relative, lambda text: restore_key(text, name), 'own Simkl app key put back in')
    return False


def restore_all():
    return sum(1 for _, addon_id, _, _ in TARGETS if restore(addon_id))
