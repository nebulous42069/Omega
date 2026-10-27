# -*- coding: utf-8 -*-
"""
    ReAuthorize - give a newly installed (or newly opened) add-on the sign-ins by itself (1.3.9)

    ReAuthorize only writes to an add-on that has created its settings, which an add-on does
    the first time it runs. So an add-on installed, or first opened, AFTER the last sync had
    nothing until somebody pressed a Sync button - and nobody knows to (the user's example,
    2026-10-06: he works nights, she opens her favourite add-on and it does not work).

    The start-up service now keeps the list of add-ons it has already seen ready, and when one
    more appears it runs the normal full sync once. It checks at every start and every few
    minutes while Kodi runs.

    "Ready" = an add-on ReAuthorize knows how to write to (import_map) whose settings file or
    database exists. The list lives in the hidden setting 'sync.known_addons'.

    The first look after updating counts EVERY ready add-on as new, once ('sync.catchup.done').
    It was first written to only record them, so an update would not push to every box - and
    on the bench the same night POV and nine other add-ons installed since the last sync
    stayed empty, which is exactly the case this exists for (the user: "pov has nothing").
    A full sync is the same compare-then-write a Sync button does.
"""

import xbmc
import xbmcvfs

from reauthorize.modules import control

SETTING = 'sync.known_addons'
CATCHUP = 'sync.catchup.done'
LOG_TAG = '[ReAuthorize New add-ons]'

# Written without needing a settings file of their own (simkl_sync creates the scrobbler's).
_FOLDER_ONLY = ('script.simkl',)


def ready():
    """The add-ons ReAuthorize can write to right now."""
    from reauthorize.modules import import_map
    found = set()
    for addon_id in import_map.SETTINGS:
        if xbmcvfs.exists('special://profile/addon_data/%s/settings.xml' % addon_id) \
                and xbmcvfs.exists('special://home/addons/%s/' % addon_id):
            found.add(addon_id)
    for addon_id, spec in import_map.DATABASES.items():
        if xbmcvfs.exists('special://profile/addon_data/%s/%s' % (addon_id, spec['file'])) \
                and xbmcvfs.exists('special://home/addons/%s/' % addon_id):
            found.add(addon_id)
    for addon_id in _FOLDER_ONLY:
        if xbmcvfs.exists('special://home/addons/%s/' % addon_id):
            found.add(addon_id)
    return found


def _stored():
    raw = control.setting(SETTING) or ''
    return set(part for part in raw.split(',') if part), bool(raw)


def _store(addon_ids):
    # '-' keeps an empty list different from "never recorded"
    control.setSetting(SETTING, ','.join(sorted(addon_ids)) or '-')


def appeared():
    """
    Add-ons that are ready now and were not at the last look. The list is brought up to date
    either way. The first look after updating returns every ready add-on, once: the catch-up.
    """
    now = ready()
    known, recorded = _stored()
    known.discard('-')
    if now != known or not recorded:
        _store(now)
    if control.setting(CATCHUP) != 'true':
        control.setSetting(CATCHUP, 'true')
        return now
    return now - known


def link(new_ids):
    """Run the normal full sync because of new_ids. Returns the services that failed (a list)."""
    from reauthorize.modules.sync_all import run_all_syncs
    include_trakt = bool(control.setting('trakt.token')) and control.setting('trakt.auto_push.consent') != 'false'
    if len(new_ids) > 3:
        xbmc.log('%s %d add-ons to bring up to date - sending the sign-ins' % (LOG_TAG, len(new_ids)), xbmc.LOGINFO)
    else:
        xbmc.log('%s %s ready for the first time - sending the sign-ins' % (LOG_TAG, ', '.join(sorted(new_ids))), xbmc.LOGINFO)
    failed = run_all_syncs(include_trakt=include_trakt)
    if failed:
        xbmc.log('%s sync failed for: %s' % (LOG_TAG, ', '.join(failed)), xbmc.LOGINFO)
    return failed
