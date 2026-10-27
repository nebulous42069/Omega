# -*- coding: utf-8 -*-
"""
    ReAuthorize - "restart Kodi" after a Trakt app key was swapped in an add-on's file (1.3.8)

    Add-ons whose Trakt app key lives in a source file (The Crew, the Trakt add-on, Genocide,
    Seren, ...) read that file once, when Kodi starts. After ReAuthorize swaps the key they
    keep using their own until Kodi is restarted, and Trakt refuses ReAuthorize's sign-in
    under it. "Sync Add-ons" used to end with "Sync Complete!" and nothing else, and users
    would never know to restart (the user's point, 2026-10-04). Both places that swap a key
    now ask, and only when a key file really changed: "Sync Add-ons", and the start-up check
    (after an update of an add-on put its own key back). If the start-up question cannot be
    shown, a note on the home window makes the next "Sync Add-ons" ask instead.

    1.4.0: no question at start or in the background any more. Every update of such an add-on
    (The Crew updated twice in one week) put its own key back, ReAuthorize swapped it again and
    asked, so users saw it after nearly every update (the user, 2026-10-10). Nobody needs to be
    asked: the swap is logged, the add-on uses the key from the next Kodi start, and at that start
    note_for_next_start() makes ReAuthorize send the sign-ins once more, in case the add-on dropped
    one meanwhile. The question stays after an action the user takes (Sync Add-ons, signing in).
"""

import hashlib
import os
import re

import xbmc
import xbmcgui

from libs.common import var

_PROPERTY = 'reauthorize.restart_needed'
# Hidden setting: a key was swapped while Kodi ran; send the sign-ins again at the next start.
RESEND_SETTING = 'sync.resend.next_start'


def key_files():
    """{path: digest} for every add-on key file ReAuthorize may patch that exists right now."""
    state = {}
    for name, path in vars(var).items():
        if not name.startswith('path_') or not isinstance(path, str):
            continue
        candidates = [path]
        if name == 'path_tmdbmovies':            # 1.1.308 moved it (see trakt_sync)
            candidates.append(os.path.join(os.path.dirname(path), 'core', 'config.py'))
        for candidate in candidates:
            try:
                with open(candidate, 'rb') as f:
                    state[candidate] = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass
    try:                                              # Simkl app keys in add-on files (1.3.9)
        from reauthorize.modules.sync import simkl_appkey
        for candidate in simkl_appkey.paths():
            try:
                with open(candidate, 'rb') as f:
                    state[candidate] = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass
    except Exception:
        pass
    return state


def _addon_of(path):
    m = re.search(r'[\\/]addons[\\/]([^\\/]+)', path)
    return m.group(1) if m else path


def note_for_next_start(before, where):
    """
    For the start-up and background checks, in place of asking: if a key file changed since
    `before`, log which add-ons and leave RESEND_SETTING for the next start. True if one changed.
    """
    after = key_files()
    changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
    if not changed:
        return False
    names = ', '.join(sorted({_addon_of(p) for p in changed}))
    xbmc.log('[ReAuthorize] app key set in %s (%s); used from the next Kodi start, '
             'when the sign-ins are sent once more' % (names, where), xbmc.LOGINFO)
    from reauthorize.modules.control import accountmgr
    accountmgr.setSetting(RESEND_SETTING, 'true')
    return True


def mark():
    xbmcgui.Window(10000).setProperty(_PROPERTY, 'true')


def pending():
    return xbmcgui.Window(10000).getProperty(_PROPERTY) == 'true'


def clear():
    xbmcgui.Window(10000).clearProperty(_PROPERTY)


def ask(before):
    """After a sync: True if the user chose to restart now. Asks only when a key file changed."""
    if key_files() == before and not pending():
        return False
    return ask_now()


def ask_now():
    """The question itself. True = restart now."""
    clear()                                       # asked once; "Later" is an answer
    return xbmcgui.Dialog().yesno(
        'ReAuthorize',
        'Restart Kodi to finish linking your add-ons?[CR][CR]A sign-in was set up inside one or more add-ons. '
        'They only pick that up when Kodi starts.',
        nolabel='Later', yeslabel='Restart Now',
        # Nobody may be at the box. At start-up this runs in the service, and an unanswered question
        # would hold up everything after it, the 6-hourly renewals included. Two minutes, then "Later".
        autoclose=120000)
