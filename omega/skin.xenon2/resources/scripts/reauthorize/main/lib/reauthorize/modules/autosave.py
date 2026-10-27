# -*- coding: utf-8 -*-
"""
    ReAuthorize - back up by itself when a sign-in changes (1.3.9)

    Until 1.3.9 only Trakt, the MDBList account, YouTube and the importer backed up after a
    sign-in. Authorizing Real-Debrid, Premiumize, AllDebrid, TorBox, OffCloud, EasyDebrid,
    Simkl, Last.fm or entering a metadata key wrote NO backup: the sign-in worked on that box
    and was gone at the next build install unless the user pressed "Save & Backup Now". The
    only guard was a reminder shown after nearly every action, which people stopped reading
    (a user asked why it keeps saying it; "can't closing just do that?" - it could not).

    default.py takes snapshot() when an action starts and calls save_if_changed() when it ends.
    Nothing changed -> nothing happens and nothing is said.
"""

import xbmc

from reauthorize.modules import control

LOG_TAG = '[ReAuthorize Autosave]'
SAVED = 'Saved and backed up.'


def snapshot():
    """Every setting that goes into a backup, as it is now."""
    from reauthorize.modules import vault
    return {key: control.setting(key) or '' for key in vault.CREDENTIAL_KEYS}


def save_if_changed(before):
    """
    Back up to the vault and the server if anything in the backup set changed since 'before'.
    Returns the line to show the user, or None when there is nothing to say:
      - nothing changed, or a sign-in was only removed and there was nothing new to save
      - the backup was written                      -> 'Saved and backed up.'
      - a sign-in was ADDED and no backup was made  -> why not (vault.failure_message())
    """
    if before is None:
        return None
    from reauthorize.modules import vault, server
    now = snapshot()
    if now == before:
        return None
    vault_ok = server_ok = False
    try:
        vault_ok = bool(vault.backup())
    except Exception as e:
        xbmc.log('%s vault backup failed: %s' % (LOG_TAG, e), xbmc.LOGINFO)
    try:
        server_ok = bool(server.backup())
    except Exception as e:
        xbmc.log('%s server backup failed: %s' % (LOG_TAG, e), xbmc.LOGINFO)
    xbmc.log('%s a sign-in changed: vault %s, server %s' % (LOG_TAG, 'saved' if vault_ok else 'not saved',
                                                          'saved' if server_ok else 'not saved'), xbmc.LOGINFO)
    if vault_ok or server_ok:
        return SAVED
    added = vault.count_credentials(now) > vault.count_credentials(before)
    if added:
        try:
            return 'Not backed up: %s' % vault.failure_message()
        except Exception:
            return 'Not backed up. Open Backup & Device and press "Save & Backup Now".'
    return None
