import os
import threading
import xbmc
import xbmcaddon
from reauthorize.modules import own_settings  # one read or write of our settings at a time
from reauthorize.modules import storage

ADDON_ID = 'script.module.reauthorize'
LOG_TAG  = '[ReAuthorize Device]'

ID_LENGTH = 64

# The setting the ID used to be cached in. Kept only for a device with nowhere
# to write outside Kodi, and scrubbed everywhere else (see get_device_id).
SETTING = 'server.device.id'

# Minting and replacing happen under one lock, so two threads that both find no
# key, or both hear "not yours" from the server, cannot each write a different one.
_lock = threading.RLock()

# An ID made in this process. Keeps the ID steady for the rest of the session
# if the store took the probe but then refused the write.
_session_id = None


def _read_file_id(path):
    if not path:
        return ''
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                file_id = f.read().strip()
            if len(file_id) == ID_LENGTH:
                return file_id
    except Exception as e:
        xbmc.log('%s Could not read device ID: %s' % (LOG_TAG, e), xbmc.LOGWARNING)
    return ''


def _write_file_id(path, device_id):
    """Persist the device ID outside Kodi. Returns True if it was written."""
    if not path or not storage.ensure_dir():
        return False
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(device_id)
        return True
    except Exception as e:
        xbmc.log('%s Could not write device ID: %s' % (LOG_TAG, e), xbmc.LOGWARNING)
        return False


def _remove(path):
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        xbmc.log('%s Could not remove %s: %s' % (LOG_TAG, path, e), xbmc.LOGWARNING)


def _new_value():
    return os.urandom(32).hex()


def get_device_id():
    """
    Return a stable 64-char hex string that uniquely identifies this Kodi
    installation.

    It lives in <store>/device_id, outside Kodi, so it survives build wipes.
    See reauthorize.modules.storage for how that location is chosen.

    Never in Kodi's settings. It used to be cached in 'server.device.id', and an
    ID found only there was adopted. But a build carries ReAuthorize's settings,
    so every box the build went on adopted its maker's ID, and all of them shared
    one cloud backup: the maker's sign-ins went to strangers, and strangers'
    sign-ins came back. An ID found only in settings now means it came from
    somewhere else, and this device starts its own. The one exception is a
    device with nowhere to write outside Kodi, where settings are all there is.

    This ID is also the key the vault and the server payload are encrypted
    with, so losing it means losing both backups. That is exactly what used to
    happen on Android 11+, where the old hardcoded /sdcard path could not be
    written: every build wipe minted a brand-new ID and orphaned the backup.
    """
    global _session_id
    with _lock:
        addon = own_settings.addon()
        path  = storage.device_id_path()
        cached = addon.getSetting(SETTING)

        file_id = _read_file_id(path)
        if file_id:
            if cached:
                addon.setSetting(SETTING, '')
            return file_id

        if cached and len(cached) == ID_LENGTH:
            if not path or cached == _session_id:
                return cached
            xbmc.log('%s Found a device ID in settings with no copy outside Kodi. It came '
                     'with a build or a copied Kodi, so it belongs to another device - '
                     'not using it.' % LOG_TAG, xbmc.LOGWARNING)

        device_id = _new_value()
        _session_id = device_id
        if _write_file_id(path, device_id):
            addon.setSetting(SETTING, '')
        else:
            addon.setSetting(SETTING, device_id)
            xbmc.log('%s New device ID could not be saved outside Kodi - it will '
                     'not survive a build install.' % LOG_TAG, xbmc.LOGWARNING)
        xbmc.log('%s Generated new device ID for this installation.' % LOG_TAG,
                 xbmc.LOGINFO)
        return device_id


def get_device_key():
    """
    The private half of this device's identity. Sent with every server request,
    it proves the request comes from the device that owns the ID and not from a
    copy of it. The server remembers the first key it sees for an ID and refuses
    any other.

    Kept only beside device_id, never in settings, so a build cannot carry it.
    Returns '' when there is nowhere to write it; the server then treats the
    request as coming from a version older than 1.3.3.
    """
    with _lock:
        get_device_id()
        path = storage.device_key_path()
        key = _read_file_id(path)
        if key:
            return key
        key = _new_value()
        return key if _write_file_id(path, key) else ''


def fingerprint():
    """First 8 characters of the device ID, for display. Never creates one."""
    device_id = (_read_file_id(storage.device_id_path())
                 or own_settings.addon().getSetting(SETTING))
    return device_id[:8]


def replace_identity(rejected_id):
    """
    Start over with a new ID and key, because the server says rejected_id
    belongs to another device. Returns True if this call replaced it.

    Only acts while rejected_id is still this device's ID, so two threads that
    both hear "not yours" replace it once.

    The vault goes with the old ID. It is encrypted with that ID, and on a box
    that got the ID from a build, what it holds are the builder's sign-ins.
    Whatever this device is signed in to now stays in settings; the caller backs
    that up again under the new ID.
    """
    with _lock:
        if get_device_id() != rejected_id:
            return False
        vault = storage.vault_path()
        _remove(vault)
        _remove(vault + '.bak' if vault else None)
        addon = own_settings.addon()
        addon.setSetting('vault.last_backup', '')

        new_id = _new_value()
        global _session_id
        _session_id = new_id
        _write_file_id(storage.device_key_path(), _new_value())
        if _write_file_id(storage.device_id_path(), new_id):
            addon.setSetting(SETTING, '')
        else:
            addon.setSetting(SETTING, new_id)
        xbmc.log('%s Device ID %s... is in use by another device. This device now has '
                 'its own: %s...' % (LOG_TAG, rejected_id[:8], new_id[:8]), xbmc.LOGWARNING)
        # The stamp on whatever this device is signed in to was made from the old
        # ID. Whether those sign-ins are its own is the shared-backup question's
        # to settle (startup._shared_backup_notice); until then they must not be
        # cleared as foreign just because the ID changed.
        from reauthorize.modules import owner
        owner.claim(force=True)
        return True


def forget():
    """
    Remove this device's ID and key (NUKE THIS DEVICE). The next call to
    get_device_id() makes a new pair.
    """
    global _session_id
    with _lock:
        _remove(storage.device_id_path())
        _remove(storage.device_key_path())
        own_settings.addon().setSetting(SETTING, '')
        _session_id = None
