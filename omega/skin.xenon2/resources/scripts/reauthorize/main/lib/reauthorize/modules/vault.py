# -*- coding: utf-8 -*-
"""
    ReAuthorize - Credential Vault
    Stores a backup of all credentials in a location outside Kodi's addon_data/
    so credentials survive build installs that wipe portable_data/ or addon_data/.

    The storage location is chosen at runtime by reauthorize.modules.storage,
    which probes each candidate directory and uses the most durable one that
    genuinely accepts a write. See that module for the ordering and for why a
    hardcoded path could not work on Android 11+.

    On startup, if credentials are missing but a vault backup exists,
    credentials are silently restored before syncing begins.
"""

import os
import json
import base64
import datetime
import xbmc
import xbmcaddon
from reauthorize.modules import own_settings  # one read or write of our settings at a time
from reauthorize.modules import storage
from reauthorize.modules.device import get_device_id
from reauthorize.modules.crypto import encrypt_data, decrypt_data

ADDON_ID = 'script.module.reauthorize'
LOG_TAG  = '[ReAuthorize Vault]'


# All credential and service settings to include in the backup
CREDENTIAL_KEYS = [
    # Real-Debrid
    'realdebrid.token', 'realdebrid.refresh', 'realdebrid.secret',
    'realdebrid.client_id', 'realdebrid.username',
    # Premiumize
    'premiumize.token', 'premiumize.username',
    # All-Debrid
    'alldebrid.token', 'alldebrid.username',
    # Trakt
    'trakt.token', 'trakt.refresh', 'trakt.expires', 'trakt.username',
    'trakt.synclist',
    'trakt.auto_push.consent',
    # TorBox
    'torbox.token', 'torbox.enabled',
    # Easy Debrid
    'easydebrid.token', 'easydebrid.enabled',
    # OffCloud
    'offcloud.token', 'offcloud.enabled',
    # Debrid-Link
    'debridlink.token', 'debridlink.enabled',
    # Linksnappy
    'linksnappy.username', 'linksnappy.password', 'linksnappy.enabled',
    # Easynews
    'easynews.username', 'easynews.password', 'easynews.enabled',
    # FilePursuit
    'filepursuit.api.key', 'filepursuit.enabled',
    # TorrentClaw (1.4.4): the user's own free key
    'torrentclaw.api.key',
    # Metadata
    'fanart.tv.api.key', 'omdb.api.key', 'mdb.api.key', 'mdb.username', 'imdb.user',
    'audiodb.api.key', 'tmdb.api.key', 'tmdb.username', 'tmdb.password',
    'tmdb.session_id',
    # YouTube - the keys, plus the sign-in itself (access_manager.json), which
    # a build install would otherwise wipe and make the user redo several times
    'youtube.api.key', 'youtube.api.id', 'youtube.api.secret', 'youtube.tokens',
    # Service / sync flags
    'sync.tk.service', 'sync.rd.service', 'sync.pm.service', 'sync.ad.service',
    'sync.torbox.service', 'sync.easyd.service', 'sync.offc.service',
    'sync.easy.service', 'sync.filep.service', 'sync.meta.service',
    'sync.yt.service', 'sync.ext.service', 'api.service',
    'sync.linksnappy.service', 'sync.debridlink.service', 'sync.lastfm.service',
    # Simkl
    'simkl.token', 'simkl.username', 'simkl.client.id',
    # MDBList account sign-in (1.3.7; the API key under Metadata is mdb.api.key)
    'mdblist.oauth.token', 'mdblist.oauth.refresh', 'mdblist.oauth.expires', 'mdblist.oauth.username',
    # PunchPlay (1.4.1). The refresh token changes at every renewal: auth/punchplay.py.
    'punchplay.token', 'punchplay.refresh', 'punchplay.expires', 'punchplay.username', 'punchplay.user.id',
    # Last.fm
    'lastfm.api.key', 'lastfm.api.secret', 'lastfm.session.key', 'lastfm.username', 'lastfm.password',
    # Debrid multi-account flag
    'debridall.enabled', 'meta.enabled',
]

# server.py backs up the same set. It used to keep its own copy, and the two
# drifted: YouTube's three keys and mdb.username lived only in the vault list,
# so they survived locally but were silently dropped from every cloud backup -
# invisible until someone restored onto a new device and found YouTube gone.
# Debrid-Link, Linksnappy and simkl.client.id were missing from BOTH lists, so
# those two services were never backed up by anything and were lost on every
# build install. One list, two consumers, so they cannot diverge again.
#
# server.api.secret is deliberately absent: it ships as a constant in
# settings.xml and is not a user credential.

# If ALL of these are empty we treat it as a credential wipe (e.g. after a build install)
PRIMARY_KEYS = [
    'realdebrid.token', 'premiumize.token', 'alldebrid.token',
    'trakt.token', 'torbox.token', 'easydebrid.token', 'simkl.token',
]


# Why the most recent backup() failed. None = it succeeded.
#   'no_credentials' - nothing authorized yet, so there is genuinely nothing to save
#   'no_location'    - the device refused every storage location we tried
#   'write_failed'   - we had a location but the write itself failed
# Callers use this to tell an empty profile apart from a blocked device. Those
# two reported identically as "Nothing to back up - no credentials found",
# which told users with a full profile that their credentials had vanished.
_LAST_ERROR = None


def last_error():
    """Reason the most recent backup() failed, or None if it succeeded."""
    return _LAST_ERROR


def blocked():
    """True if the last backup failed because the device would not let us write."""
    return _LAST_ERROR in ('no_location', 'write_failed')


def failure_message():
    """
    One plain sentence explaining the last failure, for showing to the user.
    Empty string if the last backup succeeded.

    Kept beside the reasons themselves so every screen reports a failure the
    same way, and so no caller has to guess what a False return meant.
    """
    if _LAST_ERROR == 'disabled':
        return 'Auto-Vault is switched off - turn it on under Backup & Device.'
    if _LAST_ERROR == 'no_credentials':
        return 'Nothing to back up yet - authorize a service first.'
    if _LAST_ERROR in ('no_location', 'write_failed'):
        return ('Could not save - this device is blocking storage access. '
                'See About -> Storage Report.')
    return ''


def warning_message():
    """
    Warning to show after a backup that worked but landed somewhere a build
    install will wipe. Empty string when the backup is properly durable.
    """
    if _LAST_ERROR is None and not storage.is_durable():
        return ('Saved, but only inside Kodi - a new build will erase it. '
                'See About -> Storage Report.')
    return ''


# Keys in CREDENTIAL_KEYS that are configuration, not credentials. These are
# stored so a restore brings your preferences back too, but a "backup" holding
# only these is empty in every sense that matters.
#
# This distinction is not cosmetic. Kodi returns booleans as the STRING
# 'false', which is truthy in Python, so the old emptiness check -
#     for key in CREDENTIAL_KEYS:
#         val = addon.getSetting(key)
#         if val: credentials[key] = val
#     if not credentials: return False
# could never fire: the five *.enabled flags are always present. A restore that
# recovered nothing was therefore followed by a "successful" backup that wrote
# those five flags over a perfectly good vault, destroying it permanently - and
# the same call then pushed the same wreckage to the server, taking out both
# copies at once.
_CONFIG_PREFIXES = ('sync.', 'api.', 'debridall.', 'meta.')
_CONFIG_SUFFIXES = ('.enabled', '.service')


def is_credential_key(key):
    """True if this setting is an actual credential rather than a preference."""
    return not (key.startswith(_CONFIG_PREFIXES) or key.endswith(_CONFIG_SUFFIXES))


# No real credential is ever the word "true" or "false". Checking the value as
# well as the name catches settings that are booleans in disguise: trakt.synclist
# is declared type="text" with default="false", so a name-only rule counted it as
# a credential and let a brand-new profile with nothing in it write a "backup".
_BOOLEAN_VALUES = ('', 'true', 'false')


def count_credentials(mapping):
    """
    How many real credentials (not configuration) a mapping holds.

    Judged by name AND value, because settings.xml does not reliably declare
    which is which.
    """
    return sum(1 for k, v in mapping.items()
               if is_credential_key(k)
               and str(v).strip().lower() not in _BOOLEAN_VALUES)


def _vault_file():
    """
    Current vault file path, or '' when no writable location exists.
    '' is safe to hand to os.path.isfile(), which keeps the read paths simple.
    """
    return storage.vault_path() or ''


def _legacy_decode(encoded):
    return json.loads(base64.b64decode(encoded.encode('utf-8')).decode('utf-8'))


def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d  %H:%M')


def _keep_previous(path, new_credentials):
    """
    Keep one rolling copy of the outgoing vault as vault.json.bak.

    Only kept when the outgoing file holds MORE credentials than the one
    replacing it - that is the shape of an accidental loss, and it is the copy
    worth being able to fall back on. A normal backup that adds a service
    overwrites the .bak harmlessly.

    Never allowed to fail the backup itself: a missing safety net is a smaller
    problem than not saving the credentials at all.
    """
    try:
        if not os.path.isfile(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            existing = json.loads(f.read())
        version = existing.get('version', 1)
        if version >= 2:
            old = decrypt_data(existing['data'], get_device_id())
        else:
            old = _legacy_decode(existing['data'])
        if count_credentials(old) > count_credentials(new_credentials):
            import shutil
            shutil.copyfile(path, path + '.bak')
            xbmc.log('%s Previous vault held more credentials - kept a copy as '
                     'vault.json.bak.' % LOG_TAG, xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log('%s Could not preserve previous vault: %s' % (LOG_TAG, e),
                 xbmc.LOGDEBUG)


# Sign-ins whose refresh token works only once (1.4.4). Every Kodi on a device shares this vault; one that
# renewed leaves the others holding a spent pair, and a backup made from one of those used to write the dead
# pair over the live one (the MQ9 build, 2026-10-17: every Kodi on the PC then got a dead Trakt sign-in).
# (name, the pair: token, refresh token, expiry, what goes with it)
PAIRED = (
    ('Trakt', ('trakt.token', 'trakt.refresh', 'trakt.expires'), ('trakt.username',)),
    ('PunchPlay', ('punchplay.token', 'punchplay.refresh', 'punchplay.expires'),
     ('punchplay.username', 'punchplay.user.id')),
)


def keep_newer_pairs(credentials, backed_up=None):
    """
    Where the vault already holds a pair that runs out LATER than the one about to be backed up (and has a
    different refresh token), keep the vault's: the outgoing one is spent. A sign-out (no pair in
    `credentials`) is left alone, so a Revoke still takes the sign-in out of the backup. Changes
    `credentials` in place; returns the names of the pairs kept.
    """
    if backed_up is None:
        backed_up = stored()
    kept = []
    for name, (token, refresh, expires), extra in PAIRED:
        mine, theirs = credentials.get(refresh), backed_up.get(refresh)
        if not (mine and credentials.get(token) and theirs and backed_up.get(token)) or mine == theirs:
            continue
        try:
            newer = float(backed_up.get(expires) or 0) > float(credentials.get(expires) or 0)
        except (TypeError, ValueError):
            continue
        if newer:
            for key in (token, refresh, expires) + extra:
                if backed_up.get(key):
                    credentials[key] = backed_up[key]
            kept.append(name)
    return kept


def backup():
    """
    Write all credential settings to the vault file.
    Called after a successful auth and periodically by the startup service.
    Returns True on success; on failure see last_error() for why.
    """
    global _LAST_ERROR
    _LAST_ERROR = None
    try:
        addon = own_settings.addon()
        credentials = {}
        for key in CREDENTIAL_KEYS:
            val = addon.getSetting(key)
            if val:
                credentials[key] = val

        # "Enable Auto-Vault" in settings. Gates new backups only, never a
        # restore of data already saved. Absent or blank counts as enabled, so
        # a fresh profile is protected before the user has touched anything.
        if addon.getSetting('vault.enabled') == 'false':
            _LAST_ERROR = 'disabled'
            xbmc.log('%s Auto-Vault is switched off - not saving.' % LOG_TAG,
                     xbmc.LOGINFO)
            return False

        # Count real credentials, not config flags - see is_credential_key().
        # Writing a flags-only backup over a good one is silent data loss.
        if not count_credentials(credentials):
            _LAST_ERROR = 'no_credentials'
            xbmc.log('%s Nothing but preferences to save - refusing to overwrite '
                     'the existing backup.' % LOG_TAG, xbmc.LOGINFO)
            return False

        for name in keep_newer_pairs(credentials):
            xbmc.log('%s The backup already holds a newer %s sign-in than this Kodi - kept that one.'
                     % (LOG_TAG, name), xbmc.LOGWARNING)
        vault_data = {
            'version': 2,
            'timestamp': _now(),
            'data': encrypt_data(credentials, get_device_id()),
        }
        if not storage.ensure_dir():
            _LAST_ERROR = 'no_location'
            xbmc.log('%s No writable storage location - nothing was saved.'
                     % LOG_TAG, xbmc.LOGWARNING)
            return False

        path = _vault_file()
        _keep_previous(path, credentials)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(vault_data))

        # Only stamp the date once the file is actually on disk - this is what
        # the settings screen shows as "Last Backup", and a date next to a
        # backup that never happened is worse than no date at all.
        addon.setSetting('vault.last_backup', _now())
        xbmc.log('%s Credentials backed up to %s.'
                 % (LOG_TAG, storage.location_label()), xbmc.LOGINFO)
        return True
    except Exception as e:
        _LAST_ERROR = 'write_failed'
        xbmc.log('%s Backup failed: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def stored():
    """
    The sign-ins in the vault file as a dict, without writing anything ({} when there is no vault
    or it cannot be read). For a caller that wants one value from the backup, not a restore.
    """
    try:
        path = _vault_file()
        if not os.path.isfile(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            vault_data = json.loads(f.read())
        if vault_data.get('version', 1) >= 2:
            credentials = decrypt_data(vault_data['data'], get_device_id())
        else:
            credentials = _legacy_decode(vault_data['data'])
        return credentials if isinstance(credentials, dict) else {}
    except Exception as e:
        xbmc.log('%s Could not read the vault: %s' % (LOG_TAG, str(e)), xbmc.LOGINFO)
        return {}


def restore():
    """
    Read vault file and write all stored credentials back into addon settings.
    Returns True on success.
    """
    try:
        path = _vault_file()
        if not os.path.isfile(path):
            xbmc.log('%s No vault file found - nothing to restore.' % LOG_TAG, xbmc.LOGINFO)
            return False

        with open(path, 'r', encoding='utf-8') as f:
            vault_data = json.loads(f.read())

        version = vault_data.get('version', 1)
        if version >= 2:
            credentials = decrypt_data(vault_data['data'], get_device_id())
        else:
            credentials = _legacy_decode(vault_data['data'])
        addon = own_settings.addon()
        for key, val in credentials.items():
            addon.setSetting(key, val)
        from reauthorize.modules import owner   # owner imports vault, so not at the top
        owner.claim()

        xbmc.log('%s Credentials restored from vault (backed up: %s).'
                 % (LOG_TAG, vault_data.get('timestamp', 'unknown')), xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log('%s Restore failed: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def clear():
    """Delete the vault file. Returns True on success."""
    try:
        path = _vault_file()
        if os.path.isfile(path):
            os.remove(path)
            own_settings.addon().setSetting('vault.last_backup', '')
            xbmc.log('%s Vault cleared.' % LOG_TAG, xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log('%s Clear failed: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def vault_has_data():
    """Returns True if a vault backup file exists and is readable."""
    path = _vault_file()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        return bool(data.get('data'))
    except Exception:
        return False


def credentials_are_empty():
    """
    Returns True if all primary credential keys are blank.
    This indicates the addon_data was wiped (e.g. by a build install).
    """
    addon = own_settings.addon()
    return all(addon.getSetting(k) == '' for k in PRIMARY_KEYS)


def restore_missing_keys():
    """
    Restore only keys from vault that are currently empty in addon settings.
    Called after server auto-restore to fill in any keys the server didn't have
    (e.g. Simkl authorized after the last server backup).
    Returns True if at least one key was filled in.
    """
    path = _vault_file()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            vault_data = json.loads(f.read())
        version = vault_data.get('version', 1)
        if version >= 2:
            credentials = decrypt_data(vault_data['data'], get_device_id())
        else:
            credentials = _legacy_decode(vault_data['data'])
        addon = own_settings.addon()
        filled = 0
        for key, val in credentials.items():
            if val and not addon.getSetting(key):
                addon.setSetting(key, val)
                filled += 1
        if filled:
            from reauthorize.modules import owner
            owner.claim()
            xbmc.log('%s Filled in %d missing key(s) from vault.' % (LOG_TAG, filled), xbmc.LOGINFO)
        return filled > 0
    except Exception as e:
        xbmc.log('%s restore_missing_keys failed: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def auto_restore():
    """
    Called at startup before syncing.
    If credentials are missing but a vault backup exists, restore silently.
    Returns True if a restore was performed.
    Note: vault.enabled only gates new backups, not restore of existing data.
    """
    if credentials_are_empty() and vault_has_data():
        xbmc.log('%s Credential wipe detected \u2014 auto-restoring from vault...' % LOG_TAG, xbmc.LOGINFO)
        return restore()
    return False
