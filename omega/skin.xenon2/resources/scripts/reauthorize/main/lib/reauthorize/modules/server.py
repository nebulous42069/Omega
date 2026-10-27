# -*- coding: utf-8 -*-
"""
    ReAuthorize - Server Sync
    Communicates with the ReAuthorize API at reauthorize.the-hermit.com.

    Startup sequence (called from startup.py):
        1. server.auto_restore() - if credentials are empty, fetch from server
        2. (all syncs run)
        3. server.backup()       - push fresh credentials to server
       With credentials present, server.confirm_owner() instead.

    One device per ID: every request carries the device key (see device.py).
    The server remembers the first key it sees for an ID and answers any other
    with 409 not_owner; this device then takes a new ID of its own.

    Builder workflow:
        server.builder_on()  - before zipping a build
        server.builder_off() - after zipping, to re-enable restore on this device
"""

import base64
import json
import xbmc
import xbmcaddon
from reauthorize.modules import own_settings  # one read or write of our settings at a time

# Imported at module scope, not inside _post(): the except clauses below name
# HTTPError, and a failure raised before an in-function import would make the
# handler itself throw NameError.
try:
    from urllib.request import urlopen, Request
    from urllib.error   import URLError, HTTPError
except ImportError:  # Kodi 18 / Python 2
    from urllib2 import urlopen, Request, URLError, HTTPError  # noqa: F401
from reauthorize.modules import device
from reauthorize.modules.device import get_device_id
from reauthorize.modules.crypto import encrypt_data, decrypt_data
# vault owns the credential-vs-preference distinction both backup channels need.
# Safe at module scope: vault imports storage/device/crypto, never server.
from reauthorize.modules import vault
from reauthorize.modules import owner

ADDON_ID  = 'script.module.reauthorize'
LOG_TAG   = '[ReAuthorize Server]'
API_URL   = 'https://reauthorize.the-hermit.com/api.php'
TIMEOUT   = 10  # seconds - keeps startup fast even if server is slow

# The single list lives in vault.py so the two backup channels can never
# drift apart again. See the note beside it for what that drift cost.
CREDENTIAL_KEYS = vault.CREDENTIAL_KEYS

PRIMARY_KEYS = [
    'realdebrid.token', 'premiumize.token', 'alldebrid.token',
    'trakt.token', 'torbox.token', 'easydebrid.token', 'simkl.token',
]


# ── HTTP helper ───────────────────────────────────────────────────────────────

# Why the most recent server call failed. None = the call succeeded.
#   'unreachable'  - DNS/TLS/timeout; we never got an answer from the server
#   'no_secret'    - api.secret is blank, so sync is effectively switched off
#   'no_backup'    - the server answered, but holds nothing for this device yet
#   'rejected'     - the server answered with an error (bad secret, 5xx, etc.)
#   'not_owner'    - another device owns this ID; this one has just been given its own
#   'failed'       - reached the server, but its reply made no sense
# Callers use this to tell "couldn't reach the server" apart from "server has no
# backup for this device" - those look identical otherwise, which is how a dead
# endpoint stayed invisible for months.
#
# A 404 in particular is a normal answer, not a fault: it means this device has
# never pushed a backup. Filing it as 'unreachable' logged a warning identical
# to a dead host, which is exactly the ambiguity that hid four months of NXDOMAIN.
_LAST_ERROR = None
# The HTTP status of the last refused request (e.g. 429 for "too many logs"), or None.
_LAST_CODE = None


def last_error():
    """Reason the most recent server call failed, or None if it succeeded."""
    return _LAST_ERROR


def unreachable():
    """
    True only if the last call never reached the server at all.
    A server that answered 404 is reachable - see no_backup().
    """
    return _LAST_ERROR == 'unreachable'


def no_backup():
    """True if the server answered but has nothing stored for this device."""
    return _LAST_ERROR == 'no_backup'


def _error_of(http_error):
    """The 'error' field of an error reply's JSON body, or '' if there is none."""
    try:
        return json.loads(http_error.read().decode('utf-8')).get('error', '')
    except Exception:
        return ''


def _after_new_identity():
    """
    The vault left with the old ID. Save what this device is signed in to now
    under the new one, so a build wipe straight after does not lose it.

    Some of those sign-ins may have come from the shared backup, so the next
    start asks whether to keep them (startup._shared_backup_notice).
    """
    try:
        vault.backup()
        addon = own_settings.addon()
        if vault.count_credentials({k: addon.getSetting(k) for k in CREDENTIAL_KEYS}):
            addon.setSetting('server.shared.notice', 'true')
    except Exception as e:
        xbmc.log('%s Vault backup after new device ID failed: %s' % (LOG_TAG, e),
                 xbmc.LOGWARNING)


def _post(action, extra=None, timeout=TIMEOUT):
    """
    POST a JSON request to the API. Returns the parsed response dict or None on failure.
    Uses only stdlib - no external dependencies.
    """
    global _LAST_ERROR, _LAST_CODE
    if action == 'log':
        _LAST_ERROR, _LAST_CODE = 'disabled', None
        return None
    _LAST_ERROR = None
    _LAST_CODE = None
    device_id = ''
    try:
        import json as _json
        addon  = own_settings.addon()
        secret = addon.getSetting('server.api.secret')
        if not secret:
            _LAST_ERROR = 'no_secret'
            xbmc.log('%s api.secret not set - server sync disabled.' % LOG_TAG, xbmc.LOGWARNING)
            return None

        device_id = get_device_id()
        payload = {
            'action':    action,
            'secret':    secret,
            'device_id': device_id,
        }
        device_key = device.get_device_key()
        if device_key:
            payload['device_key'] = device_key
        if extra:
            payload.update(extra)

        data = _json.dumps(payload).encode('utf-8')

        req = Request(API_URL, data=data, headers={
            'Content-Type': 'application/json',
            'User-Agent':   'ReAuthorize/1.0 Kodi',
        })
        response = urlopen(req, timeout=timeout)
        return _json.loads(response.read().decode('utf-8'))

    except HTTPError as e:
        _LAST_CODE = e.code
        # The server answered. 404 on a fetch is the normal "nothing stored for
        # this device yet" reply, so it is logged as information, not a fault.
        if e.code == 404:
            _LAST_ERROR = 'no_backup'
            xbmc.log('%s No backup stored for this device yet (%s).'
                     % (LOG_TAG, action), xbmc.LOGINFO)
        elif e.code == 409 and _error_of(e) == 'not_owner':
            _LAST_ERROR = 'not_owner'
            xbmc.log('%s Another device owns this device ID (%s) - making this one its own.'
                     % (LOG_TAG, action), xbmc.LOGWARNING)
            if device.replace_identity(device_id):
                _after_new_identity()
        else:
            _LAST_ERROR = 'rejected'
            xbmc.log('%s Server refused the request (%s): HTTP %s'
                     % (LOG_TAG, action, e.code), xbmc.LOGWARNING)
        return None

    except URLError as e:
        # Never got an answer: DNS, TLS, timeout, connection refused.
        # HTTPError subclasses this, so it must be caught above, not here.
        _LAST_ERROR = 'unreachable'
        xbmc.log('%s Could not reach the server (%s): %s'
                 % (LOG_TAG, action, getattr(e, 'reason', e)), xbmc.LOGWARNING)
        return None

    except Exception as e:
        # Reached the server but could not make sense of the reply.
        _LAST_ERROR = 'failed'
        xbmc.log('%s Unexpected error talking to the server (%s): %s'
                 % (LOG_TAG, action, str(e)), xbmc.LOGWARNING)
        return None


# ── Credential helpers ────────────────────────────────────────────────────────

def _encode(credentials):
    wrapper = json.dumps({'v': 2, 'd': encrypt_data(credentials, get_device_id())})
    return base64.b64encode(wrapper.encode('utf-8')).decode()


def _decode(encoded):
    raw = json.loads(base64.b64decode(encoded.encode('utf-8')).decode('utf-8'))
    if isinstance(raw, dict) and raw.get('v') == 2:
        return decrypt_data(raw['d'], get_device_id())
    # Old format: the decoded blob is the credentials dict directly
    return raw


def credentials_are_empty():
    addon = own_settings.addon()
    return all(addon.getSetting(k) == '' for k in PRIMARY_KEYS)


def _server_enabled():
    return own_settings.addon().getSetting('server.enabled') == 'true'


# ── Public API ────────────────────────────────────────────────────────────────

def backup():
    """
    Push all credentials to the server.
    Called after every successful startup sync so the server always has fresh data.
    Returns True on success.
    """
    if not _server_enabled():
        return False
    try:
        addon = own_settings.addon()
        credentials = {k: addon.getSetting(k) for k in CREDENTIAL_KEYS if addon.getSetting(k)}
        # Never send an older Trakt / PunchPlay pair than the one the local backup holds (vault.keep_newer_pairs).
        try:
            vault.keep_newer_pairs(credentials)
        except Exception as e:
            xbmc.log('%s could not compare with the local backup: %s' % (LOG_TAG, e), xbmc.LOGINFO)

        # Count real credentials, not config flags. Kodi returns booleans as the
        # string 'false', which is truthy, so a plain "is the dict empty" test
        # always passed and a restore that recovered nothing was immediately
        # followed by a push that overwrote the good server copy with five
        # preference flags. See vault.is_credential_key().
        if not vault.count_credentials(credentials):
            xbmc.log('%s Nothing but preferences to send - refusing to overwrite '
                     'the stored backup.' % LOG_TAG, xbmc.LOGINFO)
            return False

        result = _post('store', {'vault_data': _encode(credentials)})
        if result is None and _LAST_ERROR == 'not_owner':
            # This device has just been given its own ID; send the backup there.
            result = _post('store', {'vault_data': _encode(credentials)})
        if result and result.get('status') == 200:
            xbmc.log('%s Credentials pushed to server.' % LOG_TAG, xbmc.LOGINFO)
            return True
        xbmc.log('%s Server backup failed: %s' % (LOG_TAG, result), xbmc.LOGWARNING)
        return False
    except Exception as e:
        xbmc.log('%s backup() error: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def restore():
    """
    Fetch credentials from the server and write them into addon settings.
    Returns True on success, False if server has no data or builder mode is active.
    """
    if not _server_enabled():
        return False
    try:
        result = _post('fetch')
        if not result:
            return False

        if result.get('builder_mode'):
            xbmc.log('%s Server reports builder mode ON - skipping restore.' % LOG_TAG, xbmc.LOGINFO)
            return False

        if result.get('status') == 404:
            xbmc.log('%s No server vault found for this device.' % LOG_TAG, xbmc.LOGINFO)
            return False

        vault_data = result.get('vault_data')
        if not vault_data:
            return False

        credentials = _decode(vault_data)
        addon = own_settings.addon()
        for key, val in credentials.items():
            addon.setSetting(key, val)
        owner.claim()   # a restore is this device putting its own sign-ins back

        xbmc.log('%s Credentials restored from server.' % LOG_TAG, xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log('%s restore() error: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def auto_restore():
    """
    Called at startup before syncing.
    If credentials are missing, tries server first, then falls back to local vault.
    Returns True if a restore was performed.
    """
    if not credentials_are_empty():
        return False

    xbmc.log('%s Credential wipe detected \u2014 attempting server restore...' % LOG_TAG, xbmc.LOGINFO)

    # Primary: server
    if _server_enabled() and restore():
        return True

    # Fallback: local vault. Name which of the three cases this is \u2014 a device
    # with no server copy yet is normal, a dead endpoint is not, and logging
    # both as "failed or disabled" is what made a four-month outage invisible.
    if not _server_enabled():
        reason = 'server sync is switched off'
    elif no_backup():
        reason = 'server has no copy for this device yet'
    elif unreachable():
        reason = 'server could not be reached'
    else:
        reason = 'server restore failed'
    xbmc.log('%s %s \u2014 trying local vault...' % (LOG_TAG, reason.capitalize()),
             xbmc.LOGINFO)
    try:
        return vault.auto_restore()
    except Exception as e:
        xbmc.log('%s Local vault fallback error: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def has_backup():
    """
    Check whether the server has a credential record for this device UUID.
    Does NOT apply any data. Returns True/False.
    Used by the UI to decide whether to offer 'Restore & Sync' vs first-time setup.
    """
    if not _server_enabled():
        return False
    try:
        result = _post('fetch')
        if not result:
            return False
        if result.get('status') == 404:
            return False
        return bool(result.get('vault_data'))
    except Exception as e:
        xbmc.log('%s has_backup() error: %s' % (LOG_TAG, str(e)), xbmc.LOGWARNING)
        return False


def confirm_owner():
    """
    Ask the server whether this device's ID is its own. Run at every start.

    Before 1.3.3 a build carried its maker's ID to every box it went on, and all
    of them shared one backup. The first device to show its key claims the ID;
    when a second one shows up, the server retires the ID and deletes that backup,
    and every device holding it is moved to a new ID of its own (see _post).

    Returns True if this device owns its ID or has no backup yet.
    """
    global _CLAIM_LEAKS
    _CLAIM_LEAKS = 0
    if not _server_enabled():
        return False
    result = _post('claim', timeout=5)
    if result is None and _LAST_ERROR == 'not_owner':
        backup()  # the new ID has no backup on the server yet
        return False
    if result and result.get('status') == 200:
        try:
            _CLAIM_LEAKS = int(result.get('leaks', 0))
        except (TypeError, ValueError):
            pass
        return True
    return False


# How many devices have reported finding this device's sign-ins in a build, as
# of the last confirm_owner(). See owner.leak_notice.
_CLAIM_LEAKS = 0


def claim_leaks():
    return _CLAIM_LEAKS


def report_leak(source_fp):
    """Tell the server a device found sign-ins stamped by source_fp. Best effort."""
    if not _server_enabled() or len(source_fp or '') != 8:
        return False
    result = _post('leak', {'source': source_fp}, timeout=5)
    return bool(result and result.get('status') == 200)


def reset_status(obeyed=None):
    """
    The server's reset switch: {'reset': int, 'message': str}, or None if it could
    not be read. An older api.php answers 400 and reads as None, so nothing happens.
    See reset.py. The same call tells the server this device's addon version and the
    number it last obeyed (None = none yet), which is all the uptake count is made of.

    Deliberately NOT gated on 'Enable Server Sync': it sends no sign-ins (only the device ID,
    version and a number), and in 1.3.5 a box with sync switched off, including every box of
    a build shipped that way, never reset and never showed up in the count.
    """
    extra ={'version': own_settings.addon().getAddonInfo('version')}
    if obeyed is not None:
        extra['obeyed'] = int(obeyed)
    result = _post('status', extra, timeout=5)
    if not result or result.get('status') != 200:
        return None
    try:
        return {'reset': int(result.get('reset', 0)), 'message': result.get('message', '')}
    except (TypeError, ValueError):
        return None


def reset_done():
    """This device's current ID is about to be retired by a reset: drop its uptake row.
    Not gated on 'Enable Server Sync', for the same reason as reset_status."""
    result = _post('reset_done', timeout=5)
    return bool(result and result.get('status') == 200)


def send_log(text):
    """Compatibility stub: log submissions are disabled in the embedded copy."""
    return None, 'disabled'


def clear():
    """Delete this device's vault from the server. Returns True on success."""
    if not _server_enabled():
        return False
    result = _post('clear')
    if result and result.get('status') == 200:
        xbmc.log('%s Server vault cleared.' % LOG_TAG, xbmc.LOGINFO)
        return True
    return False
