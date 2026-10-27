# -*- coding: utf-8 -*-
"""
    ReAuthorize - send a new sign-in to the add-ons by itself (1.4.1)

    Until 1.4.1 only Trakt, Simkl, Last.fm and the MDBList account were sent to the add-ons when
    the user signed in. Authorizing Real-Debrid, Premiumize, AllDebrid, TorBox, EasyDebrid,
    OffCloud, Easynews, FilePursuit, Linksnappy, Debrid-Link or entering a metadata key only
    SAVED it: the add-ons had nothing until "Sync Add-ons" was pressed, and nothing said so (the
    user took the short refresh after the sign-in for the sync, 2026-10-13 on the bench).

    default.py takes autosave.snapshot() when an action starts and calls send_if_changed() when
    it ends, just before the automatic backup. A sign-in that was cancelled changes nothing, so
    nothing is sent. Only the one service is sent, not a full sync.
"""

import xbmc

from reauthorize.modules import control

LOG_TAG = '[ReAuthorize Autosend]'

# Authorize action -> the service tag sync_all.run_all_syncs knows it by. Actions that send for
# themselves (Trakt, Simkl, Last.fm, the MDBList account, YouTube) are not here.
TAG_FOR_ACTION = {
    'realdebridAuth': 'rd', 'premiumizeAuth': 'pm', 'alldebridAuth': 'ad', 'torboxAuth': 'torbox',
    'easydebridAuth': 'easyd', 'offcloudAuth': 'offc', 'easynewsAuth': 'easy',
    'filepursuitAuth': 'filep', 'linksnappyAuth': 'linksnappy', 'debridlinkAuth': 'debridlink',
    'tmdbAuth': 'meta', 'fanartAuth': 'meta', 'audiodbAuth': 'meta', 'omdbAuth': 'meta',
    'imdbAuth': 'meta', 'mdblistAuth': 'meta', 'torrentclawAuth': 'torrentclaw',
}

_META_LABEL = 'your key'


def send_if_changed(action, before, notify=None):
    """
    Send the service this action signs in to, if the action changed a sign-in since 'before'.
    notify(label) is called just before sending, so the user sees what the pause is for.
    Returns (label, failed services) when something was sent, None when there was nothing to do.
    """
    tag = TAG_FOR_ACTION.get(action)
    if not tag or before is None:
        return None
    from reauthorize.modules import autosave, sync_all
    if autosave.snapshot() == before:
        return None
    label = _META_LABEL if tag == 'meta' else sync_all._SERVICE_LABELS.get(tag, tag)
    if notify:
        try:
            notify(label)
        except Exception:
            pass
    failed = sync_all.run_all_syncs(include_trakt=False, only=(tag,))
    xbmc.log('%s %s sent to the add-ons after the sign-in%s' % (
        LOG_TAG, tag, ' (failed: %s)' % ', '.join(failed) if failed else ''), xbmc.LOGINFO)
    return label, failed
