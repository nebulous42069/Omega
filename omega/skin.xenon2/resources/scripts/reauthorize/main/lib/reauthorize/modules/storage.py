# -*- coding: utf-8 -*-
"""
    ReAuthorize - Persistent Storage Location

    Single source of truth for where ReAuthorize keeps the two files that must
    outlive a build install: the credential vault and the device ID.

    Why this module exists
    ----------------------
    The location used to be hardcoded in three places as::

        base = '/sdcard' if android else os.path.expanduser('~')

    That is correct on Windows, Linux and Android 10 or older, but it is wrong
    on Android 11+ (API 30). Under scoped storage the WRITE_EXTERNAL_STORAGE
    permission no longer grants raw writes to the /sdcard root - that needs
    MANAGE_EXTERNAL_STORAGE, which Kodi does not request. So every write threw
    PermissionError on Fire OS 8, Google TV, current Shield firmware and any
    modern phone or tablet. The vault was never written, the device ID was
    regenerated on every build wipe, and because the server keys its rows by
    device ID and the payload is encrypted with it, cloud restore broke too.

    Rather than hardcode a new guess, we probe. Locations are tried in
    descending order of durability and the first one that genuinely accepts a
    write is used. Whatever we pick is cached for the Kodi session.

    Durability, best first
    ----------------------
    1. Shared storage (Android ``/sdcard``, desktop home folder)
       Outlives a Kodi reinstall entirely. Works on desktop always, and on
       Android 10 and older.
    2. Kodi's own app storage - the folder holding ``special://home``
       On Android this is ``.../Android/data/<kodi package>/files/``, which is
       app-specific external storage: always writable, no permission needed, on
       every API level. It sits beside ``.kodi/`` rather than inside it, so a
       build install - which clears ``.kodi/addons`` and
       ``.kodi/userdata/addon_data`` - leaves it untouched. Lost only if the
       user uninstalls Kodi or clears its data.
    3. Addon data - last resort, NOT durable
       Always writable, but a build install wipes it. Better than losing the
       credentials mid-session, and :func:`is_durable` reports False so callers
       can warn instead of promising a backup that will not survive.

    Existing installs are never moved. If a location already holds data and is
    still writable, it wins outright - so an Android 9 box or a Windows PC that
    has been working keeps using the exact path it always has. Migration only
    happens when the location holding the data can no longer be written to.
"""

import os
import shutil
import xbmc
import xbmcvfs

ADDON_ID = 'script.module.reauthorize'
LOG_TAG  = '[ReAuthorize Storage]'

DIR_NAME    = '.reauthorize'
VAULT_FILE  = 'vault.json'
DEVICE_FILE = 'device_id'
KEY_FILE    = 'device_key'

# Files that make up the store. Migration moves these and nothing else.
PAYLOAD_FILES = (VAULT_FILE, DEVICE_FILE, KEY_FILE)

# Resolved once per Kodi session - probing touches the filesystem.
_resolved = None


class _Location(object):
    """One candidate directory, with how well it survives a build install."""

    __slots__ = ('path', 'durable', 'label')

    def __init__(self, path, durable, label):
        self.path    = path
        self.durable = durable
        self.label   = label


def _kodi_app_dir():
    """
    The folder that contains ``special://home``.

    Android : /storage/emulated/0/Android/data/<kodi package>/files
    Windows : C:\\Users\\<user>\\AppData\\Roaming
    Linux   : /home/<user>

    Derived from Kodi rather than hardcoded, so Kodi forks and non-standard
    package names resolve correctly instead of pointing at a folder that does
    not exist.
    """
    home = xbmcvfs.translatePath('special://home/')
    return os.path.dirname(home.rstrip('/\\'))


def _candidates():
    """Candidate directories, most durable first, de-duplicated."""
    found = []

    if xbmc.getCondVisibility('system.platform.android'):
        found.append(_Location(os.path.join('/sdcard', DIR_NAME),
                               True, 'shared storage'))
    else:
        found.append(_Location(os.path.join(os.path.expanduser('~'), DIR_NAME),
                               True, 'home folder'))

    try:
        found.append(_Location(os.path.join(_kodi_app_dir(), DIR_NAME),
                               True, 'Kodi app storage'))
    except Exception as e:
        xbmc.log('%s Could not resolve Kodi app storage: %s' % (LOG_TAG, e),
                 xbmc.LOGWARNING)

    try:
        addon_data = xbmcvfs.translatePath(
            'special://profile/addon_data/%s/' % ADDON_ID)
        found.append(_Location(os.path.join(addon_data, DIR_NAME),
                               False, 'addon data'))
    except Exception as e:
        xbmc.log('%s Could not resolve addon data: %s' % (LOG_TAG, e),
                 xbmc.LOGWARNING)

    # On Linux the home folder and the Kodi app folder are the same place.
    unique, seen = [], set()
    for loc in found:
        key = os.path.normcase(os.path.normpath(loc.path))
        if key not in seen:
            seen.add(key)
            unique.append(loc)
    return unique


def _is_writable(path):
    """
    True only if a file written here can be read back.

    A plain makedirs() is not proof: some Android storage layers accept the
    call and quietly discard the contents. Round-tripping a probe file is the
    only answer we can trust.

    Leaves no trace. Testing a location needs a directory, but a candidate we
    do not end up using must not be left behind - an empty .reauthorize folder
    sitting in Kodi's app storage looks exactly like a real backup to anyone
    browsing their device, and invites them to delete the wrong thing. The
    chosen location gets its directory back from ensure_dir() before any write.
    """
    probe = os.path.join(path, '.probe')
    created = not os.path.isdir(path)
    try:
        os.makedirs(path, exist_ok=True)
        with open(probe, 'w', encoding='utf-8') as f:
            f.write('ok')
        with open(probe, 'r', encoding='utf-8') as f:
            return f.read() == 'ok'
    except Exception:
        return False
    finally:
        try:
            os.remove(probe)
        except Exception:
            pass
        if created:
            try:
                os.rmdir(path)  # only succeeds while still empty
            except Exception:
                pass


def _has_payload(path):
    """True if this directory already holds a vault or a device ID."""
    try:
        return any(os.path.isfile(os.path.join(path, name))
                   for name in PAYLOAD_FILES)
    except Exception:
        return False


def _migrate(src, dst):
    """
    Copy vault and device ID from an unwritable location into the new one.

    The device ID is the decryption key for the vault, so the two must travel
    together or the recovered vault would be undecryptable. Existing files at
    the destination are never overwritten - the destination is already live.
    """
    # The probe cleans up after itself, so the destination may not exist yet.
    try:
        os.makedirs(dst.path, exist_ok=True)
    except Exception as e:
        xbmc.log('%s Could not create %s for migration: %s'
                 % (LOG_TAG, dst.path, e), xbmc.LOGWARNING)
        return []

    moved = []
    for name in PAYLOAD_FILES:
        source = os.path.join(src.path, name)
        target = os.path.join(dst.path, name)
        if not os.path.isfile(source) or os.path.isfile(target):
            continue
        try:
            shutil.copyfile(source, target)
            moved.append(name)
        except Exception as e:
            xbmc.log('%s Could not migrate %s: %s' % (LOG_TAG, name, e),
                     xbmc.LOGWARNING)
    if moved:
        xbmc.log('%s Migrated %s from %s to %s.'
                 % (LOG_TAG, ' + '.join(moved), src.label, dst.label),
                 xbmc.LOGINFO)
    return moved


def _resolve():
    """Pick the directory to use for this session, migrating if needed."""
    candidates = _candidates()

    # Probing writes a file, so remember the answer rather than asking twice.
    probed = {}

    def writable(loc):
        if loc.path not in probed:
            probed[loc.path] = _is_writable(loc.path)
        return probed[loc.path]

    # An install that already works keeps the exact path it has always used.
    for loc in candidates:
        if _has_payload(loc.path) and writable(loc):
            xbmc.log('%s Using existing store in %s (%s).'
                     % (LOG_TAG, loc.label, loc.path), xbmc.LOGINFO)
            return loc

    target = next((loc for loc in candidates if writable(loc)), None)
    if target is None:
        xbmc.log('%s No writable location found - checked: %s'
                 % (LOG_TAG, ', '.join(loc.path for loc in candidates)),
                 xbmc.LOGERROR)
        return None

    # Rescue data stranded in a location that has become read-only. On
    # Android 11+ the old /sdcard store is usually unreadable as well, in which
    # case there is nothing to rescue and we simply start clean.
    for loc in candidates:
        if loc is not target and _has_payload(loc.path):
            _migrate(loc, target)
            break

    xbmc.log('%s Store location: %s (%s, %s).'
             % (LOG_TAG, target.path, target.label,
                'survives build installs' if target.durable
                else 'wiped by build installs'),
             xbmc.LOGINFO)
    return target


def _location():
    global _resolved
    if _resolved is None:
        _resolved = _resolve()
    return _resolved


def data_dir():
    """
    The directory ReAuthorize stores persistent files in, or None if every
    candidate refused a write. Callers must handle None rather than assume a
    path exists.
    """
    loc = _location()
    return loc.path if loc else None


def is_durable():
    """
    True if the chosen location survives a build install.

    False means credentials are being kept somewhere a build wipe will clear,
    so the UI should say that plainly instead of reporting a successful backup.
    """
    loc = _location()
    return bool(loc and loc.durable)


def location_label():
    """Short human-readable name of the chosen location, for UI and logs."""
    loc = _location()
    return loc.label if loc else 'unavailable'


def _path_for(name):
    base = data_dir()
    return os.path.join(base, name) if base else None


def vault_path():
    """Full path to vault.json, or None if there is nowhere to write."""
    return _path_for(VAULT_FILE)


def device_id_path():
    """Full path to the device ID file, or None if there is nowhere to write."""
    return _path_for(DEVICE_FILE)


def device_key_path():
    """Full path to the device key file, or None if there is nowhere to write."""
    return _path_for(KEY_FILE)


def ensure_dir():
    """
    Create the store directory and return its path, or None if unavailable.
    Call before writing.
    """
    base = data_dir()
    if not base:
        return None
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except Exception as e:
        xbmc.log('%s Could not create %s: %s' % (LOG_TAG, base, e),
                 xbmc.LOGWARNING)
        return None


def purge_all():
    """
    Delete the vault, device ID and device key from EVERY candidate location,
    not just the one in use. Migration copies rather than moves, and a store
    that was once elsewhere leaves its files behind; _resolve() picks the first
    location holding any payload, so a stray copy there came back to life at the
    next start after a Nuke (reported 2026-09-29: a builder nuked and his old
    vault.json was still there). Returns how many files were removed.
    """
    removed = 0
    for loc in _candidates():
        for name in PAYLOAD_FILES + (VAULT_FILE + '.bak',):
            path = os.path.join(loc.path, name)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    removed += 1
            except Exception as e:
                xbmc.log('%s Could not remove %s: %s' % (LOG_TAG, path, e), xbmc.LOGWARNING)
    reset_cache()
    if removed:
        xbmc.log('%s Removed %d stored file(s) from every location.' % (LOG_TAG, removed),
                 xbmc.LOGINFO)
    return removed


def reset_cache():
    """Forget the resolved location so the next call probes again."""
    global _resolved
    _resolved = None


def _info_label(name, attempts=5, wait_ms=120):
    """
    Read a Kodi InfoLabel, waiting out its "Busy" placeholder.

    Some labels - System.OSVersionInfo in particular - are resolved
    asynchronously, and Kodi returns the literal string "Busy" until the answer
    is ready. Printing that in a diagnostic is worse than printing nothing,
    because the OS version is one of the two fields that explains a device's
    storage behaviour. Retry briefly, then give up quietly.
    """
    for attempt in range(attempts):
        try:
            value = (xbmc.getInfoLabel(name) or '').strip()
        except Exception:
            return ''
        if value and not value.lower().startswith('busy'):
            return value
        if attempt < attempts - 1:
            xbmc.sleep(wait_ms)
    return ''


def diagnostic_report():
    """
    Plain-English report of what storage this device actually allows.

    Exists so a user can answer 'is your backup working?' with a screenshot
    instead of a guess, and so support can tell a permission failure apart from
    an empty profile without asking anyone to find kodi.log on a TV box.

    The device ID is the key the vault and the server payload are encrypted
    with, so only a short fingerprint is shown - never the whole thing.

    The answers come first. Many skins' text viewers cannot scroll with a remote,
    and a report that opened on a list of folder paths answered nothing: the
    result was below the bottom of the screen.
    """
    from reauthorize.modules import device, own_settings

    addon   = own_settings.addon()
    android = xbmc.getCondVisibility('system.platform.android')
    chosen  = _location()
    vault   = vault_path()

    lines = ['[B]Backup status[/B]']
    if chosen is None:
        lines.append('Working:  %s, this device blocks every storage location.' % _no())
    elif addon.getSetting('vault.enabled') == 'false':
        lines.append('Working:  %s, Auto-Vault is switched off (turn it on under Backup & Device).' % _no())
    else:
        lines.append('Working:  %s, saving to the %s' % (_yes(), chosen.label))
    if chosen is not None:
        lines.append('Survives a new build:  %s' % (_yes() if chosen.durable else _no()))
    if vault and os.path.isfile(vault):
        lines.append('Backup file:  present, last saved %s'
                     % (addon.getSetting('vault.last_backup') or 'at an unknown time'))
    else:
        lines.append('Backup file:  none yet')
    lines.append('Device fingerprint:  %s' % (device.fingerprint() or 'not set yet'))

    # Whether a device can write to /sdcard is decided by the Android version
    # AND which SDK the installed Kodi targets - an older Kodi keeps legacy
    # storage access on Android 11. Capturing both turns a user's screenshot
    # into something that explains itself.
    about = ['Android' if android else sys_platform()]
    for label, info in (('Kodi ', 'System.BuildVersion'),
                        ('',      'System.OSVersionInfo')):
        value = _info_label(info)
        if value:
            about.append(label + value.split('(')[0].strip())
    lines += ['', '[B]This device[/B]', '  -  '.join(about)]

    lines += ['', '[B]Folders checked, best first[/B]']
    for loc in _candidates():
        if _is_writable(loc.path):
            state = 'writable'
        elif _has_payload(loc.path):
            state = 'readable, cannot write'
        else:
            state = 'blocked'
        mark = '>> ' if chosen and loc.path == chosen.path else '     '
        lines.append('%s%s  -  %s' % (mark, loc.label, state))
        lines.append('       %s' % loc.path)

    if android and chosen and chosen.label != 'shared storage':
        lines.append('')
        lines.append('Note: Android 11 and newer block add-ons from writing to')
        lines.append('/sdcard. That is normal and is not a fault with your box.')
        lines.append('Plugging in an SD card, USB drive or SSD does not change it.')
        lines.append('ReAuthorize uses Kodi\'s own storage instead, which works.')

    return '\n'.join(lines)


def _yes():
    return '[COLOR FF4CAF50][B]YES[/B][/COLOR]'


def _no():
    return '[COLOR FFE53935][B]NO[/B][/COLOR]'


def sys_platform():
    """Human-readable desktop platform name for the report."""
    for cond, name in (('system.platform.windows', 'Windows'),
                       ('system.platform.linux',   'Linux'),
                       ('system.platform.osx',     'macOS')):
        if xbmc.getCondVisibility(cond):
            return name
    return 'Unknown'
