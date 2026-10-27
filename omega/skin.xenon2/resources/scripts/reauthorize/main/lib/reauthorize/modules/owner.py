# -*- coding: utf-8 -*-
"""
    ReAuthorize - Ownership stamp (the leak failsafe)

    A build carries ReAuthorize's settings, so a builder's sign-ins used to arrive
    on every box the build went on (2026-09-27). Prepare for Distribution cleans
    them, but only if the builder remembers. This is the net under it.

    Whenever this device holds sign-ins, settings also holds a stamp made from this
    device's ID: '<first 8 chars of the ID>.<HMAC of the ID>'. The ID never leaves
    the device (device.py), so a stamp copied into a build cannot verify anywhere
    else. At every start, before anything is pushed or backed up:

        no sign-ins                       -> nothing to do
        stamp verifies                    -> the sign-ins are this device's own
        no stamp, device already had an   -> a version before the stamp existed:
          ID before this start               adopt them (stamp them now)
        no stamp and no ID yet, or a      -> they came with a build or a copy of
          stamp that does not verify         another device: FOREIGN

    Foreign sign-ins are cleared before they can reach an addon or a backup, the
    user is told in one plain sentence, and the server is told which device the
    stamp names, so the builder finds out from the leak itself (server.py, claim).

    Known limits: a build made by a version older than this carries no stamp and,
    on a box that already has an ID, is adopted as if it were the user's own;
    the kill switch (reset.py) is what covers those. Addons' own copies of tokens
    inside a build are only blanked for the services sync_all.run_all_syncs knows.
"""

import hashlib
import hmac
import os
import xbmc
import xbmcaddon
from reauthorize.modules import own_settings  # one read or write of our settings at a time
from reauthorize.modules import storage, device, vault

ADDON_ID = 'script.module.reauthorize'
LOG_TAG  = '[ReAuthorize Owner]'

# How long a wipe waits before checking it again (see wipe_local). The tests set it to 0.
SETTLE_SECONDS = float(os.environ.get('REAUTHORIZE_SETTLE_SECONDS', '20'))

STAMP      = 'owner.stamp'
LEAKS_SEEN = 'owner.leaks.seen'

NONE, OWN, ADOPT, FOREIGN = 'none', 'own', 'adopt', 'foreign'

# Everything ReAuthorize clears when it removes every sign-in from a device,
# beyond vault.CREDENTIAL_KEYS: the markers that would make a fresh start behave
# like an old one.
_EXTRA_KEYS = ('trakt.all_push.done', 'import.declined', 'server.shared.notice', STAMP,
               'mdblist.oauth.username.display')

# Service tags for sync_all.run_all_syncs(wipe=...): push a blank to every
# addon that already holds the old value.
WIPE_TAGS = {'rd', 'pm', 'ad', 'torbox', 'easyd', 'offc', 'linksnappy',
             'easy', 'debridlink', 'simkl', 'filep', 'meta', 'mdbo', 'lastfm', 'punchplay',
             'torrentclaw'}


def _get(key):
    return own_settings.addon().getSetting(key)


def _set(key, value):
    own_settings.addon().setSetting(key, value)


def make_stamp():
    device_id = device.get_device_id()
    mac = hmac.new(device_id.encode('utf-8'), b'reauthorize-owner-stamp',
                   hashlib.sha256).hexdigest()[:32]
    return '%s.%s' % (device_id[:8], mac)


def source_of(stamp):
    """The 8-character device fingerprint a stamp names, or ''."""
    head = (stamp or '').split('.')[0]
    return head if len(head) == 8 else ''


def holds_credentials():
    addon = own_settings.addon()
    return vault.count_credentials({k: addon.getSetting(k) for k in vault.CREDENTIAL_KEYS}) > 0


def is_new_box():
    """
    True if this device has never had an ID. Call it before anything can make
    one: the ID file appears the first time device.get_device_id() runs.
    A device with nowhere to write outside Kodi cannot tell, so it is never new.
    """
    path = storage.device_id_path()
    return bool(path) and not os.path.isfile(path)


def assess(new_box):
    if not holds_credentials():
        return NONE
    stamp = _get(STAMP)
    if stamp:
        return OWN if hmac.compare_digest(stamp, make_stamp()) else FOREIGN
    return FOREIGN if new_box else ADOPT


def claim(force=False):
    """
    Stamp the sign-ins now in settings as this device's own. Leaves an existing
    stamp alone (never blesses what is already marked as someone else's) unless
    force. With no sign-ins it removes the stamp. Returns True if it wrote one.
    """
    try:
        if not holds_credentials():
            if _get(STAMP):
                _set(STAMP, '')
            return False
        if _get(STAMP) and not force:
            return False
        _set(STAMP, make_stamp())
        return True
    except Exception as e:
        xbmc.log('%s claim failed: %s' % (LOG_TAG, e), xbmc.LOGWARNING)
        return False


def wipe_mapped_settings():
    """Clear only credential fields recorded in ReAuthorize's own send map.

    Covers obsolete fields that a newer sync adapter no longer writes, while
    preserving unrelated settings and built-in application constants.
    """
    from reauthorize.modules import import_map, sync_support
    from reauthorize.modules.sync import trakt_wipe
    targets = {}
    for addon_id, fields in import_map.SETTINGS.items():
        targets[addon_id] = {field for field, key in fields.items()
                             if key in vault.CREDENTIAL_KEYS and vault.is_credential_key(key)}
    for extras in (trakt_wipe._JSON_SETTINGS, getattr(trakt_wipe, '_ALSO_BLANK', {})):
        for addon_id, fields in extras.items():
            targets.setdefault(addon_id, set()).update(fields)
    failed = []
    for addon_id, fields in targets.items():
        if not fields:
            continue
        for field in sorted(fields):
            try:
                sync_support.clear_setting(addon_id, field, import_map.SETTINGS.get(addon_id, {}).get(field))
            except Exception as exc:
                if addon_id not in failed:
                    failed.append(addon_id)
                # Names and exception type only, never the old value or the
                # exception message (which may contain credentials).
                xbmc.log('[ReAuthorize Wipe] Could not clear %s / %s (%s)' %
                         (addon_id, field, type(exc).__name__), xbmc.LOGWARNING)
    from reauthorize.modules.retained_wipe import wipe_retained_data
    failed.extend(wipe_retained_data())
    return sorted(set(failed))


def wipe_local(revoke_trakt=False, progress=None):
    """
    Remove every sign-in and marker from ReAuthorize's settings, then push the
    blanks to the addons that already hold the old values.

    revoke_trakt kills the Trakt token itself, everywhere at once. Only for
    sign-ins that are this device's own to end: a build's Trakt belongs to its
    maker, who revokes it himself.

    progress(percent, text), when given, is told each step (Prepare for Distribution's
    progress window, 1.4.3: about 40 seconds passed with only a corner notice, and the
    user nearly took the wait for the end).
    """
    report = progress or (lambda percent, text: None)
    report(5, 'Removing the sign-ins from ReAuthorize...')
    if revoke_trakt and _get('trakt.token'):
        try:
            from reauthorize.modules.auth.trakt import Trakt
            Trakt().call('oauth/revoke', data={'token': _get('trakt.token')}, with_auth=False)
        except Exception as e:
            xbmc.log('%s Trakt revoke failed: %s' % (LOG_TAG, e), xbmc.LOGWARNING)

    for key in list(vault.CREDENTIAL_KEYS) + list(_EXTRA_KEYS):
        if _get(key):
            _set(key, '')

    from reauthorize.modules.sync_all import run_all_syncs
    from reauthorize.modules.sync import youtube_sync, trakt_wipe

    def clear_addons():
        failed = []
        # Independent steps: failure of one service must not prevent the
        # remaining services, YouTube or Trakt from being cleared.
        try:
            failed.extend(run_all_syncs(include_trakt=False, wipe=WIPE_TAGS) or [])
        except Exception as exc:
            failed.append('service sync')
            xbmc.log('%s Service wipe failed: %s' % (LOG_TAG, type(exc).__name__), xbmc.LOGWARNING)
        for name, action in (('YouTube', youtube_sync.wipe), ('Trakt', trakt_wipe.wipe_addons)):
            try:
                action()
            except Exception as exc:
                failed.append(name)
                xbmc.log('%s %s wipe failed: %s' % (LOG_TAG, name, type(exc).__name__), xbmc.LOGWARNING)
        try:
            failed.extend(wipe_mapped_settings())
        except Exception as exc:
            failed.append('mapped settings')
            xbmc.log('%s Mapped wipe failed: %s' % (LOG_TAG, type(exc).__name__), xbmc.LOGWARNING)
        return failed

    report(10, 'Removing logins from supported installed add-ons...')
    clear_addons()
    monitor = xbmc.Monitor()
    # Add-ons may persist a cached copy after our first write. Give them time
    # to settle, then send blanks again and report final-pass failures.
    for waited in range(int(SETTLE_SECONDS)):
        report(30 + 40 * waited // max(int(SETTLE_SECONDS), 1),
               'Checking for cached logins in %d s' % (int(SETTLE_SECONDS) - waited))
        if monitor.waitForAbort(1):
            return ['interrupted']
    report(75, 'Checking your add-ons once more...')
    failed = clear_addons()
    report(90, 'Add-on login removal checked')
    return sorted(set(failed))


def handle_foreign(source_fp):
    """Sign-ins that came with a build or copy: remove them and say so."""
    xbmc.log('%s Sign-ins came from another device (%s...) - removing them.'
             % (LOG_TAG, source_fp or '?'), xbmc.LOGWARNING)
    wipe_local(revoke_trakt=False)
    try:
        from reauthorize.modules import server
        server.report_leak(source_fp)
    except Exception as e:
        xbmc.log('%s Leak report failed: %s' % (LOG_TAG, e), xbmc.LOGWARNING)
    # No commas in the text: the builtin splits its arguments on them. Worded to be
    # true for a build's sign-ins and for an old box whose own sign-ins cannot be told apart.
    xbmc.executebuiltin('Notification(ReAuthorize, Sign-ins that could not be confirmed as '
                        'yours were removed. Please sign in to your services again., 8000)')


def startup_check(new_box):
    """First thing at every start. Returns the verdict."""
    verdict = assess(new_box)
    if verdict == ADOPT:
        claim()
    elif verdict == FOREIGN:
        handle_foreign(source_of(_get(STAMP)))
    return verdict


def leak_notice(count):
    """
    The server counted `count` boxes that found this device's sign-ins in a build.
    Tell the builder once per new count, in words that say what to do.
    """
    try:
        count = int(count)
        seen = int(_get(LEAKS_SEEN) or 0)
    except (TypeError, ValueError):
        return False
    if count <= seen:
        return False
    _set(LEAKS_SEEN, str(count))
    import xbmcgui
    xbmcgui.Dialog().ok(
        'ReAuthorize',
        'Sign-ins from this device were found on %d other device%s, and were removed there.[CR][CR]'
        'If you share builds, run Prepare for Distribution first, and sign out or revoke the '
        'services you used on this device.' % (count, '' if count == 1 else 's'))
    return True
