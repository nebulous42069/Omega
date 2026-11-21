"""Persistent per-device OAuth credentials for Google Drive.

Some Kodi builds accept an OAuth callback yet reject the legacy settings API's
setSettingString() without raising. Never rely on that API for the only copy of
refresh credentials. Store a restricted file in the add-on's *userdata* (not the
install directory) and accept older Kodi settings as a read-only upgrade path.

This file is local to the device. It is never included in Drive favourites
journals. Like Kodi's normal add-on settings, it is not encrypted at rest.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

from resources.lib.kodi_compat import get_setting_string, profile_dir

CREDENTIAL_FILE = "google-drive-credentials.json"
CREDENTIAL_SCHEMA = 1
MAX_FILE_BYTES = 16384
FIELDS = (
    "oauth_refresh_token",
    "oauth_refresh_secret",
    "oauth_access_token",
    "oauth_access_token_expires_at",
    "oauth_scope",
)


class CredentialStoreError(Exception):
    pass


def _path(addon):
    return os.path.join(profile_dir(addon), CREDENTIAL_FILE)


def _validate_record(record):
    if not isinstance(record, dict) or record.get("schema") != CREDENTIAL_SCHEMA:
        raise CredentialStoreError("Unrecognized Google Drive credential file format")
    result = {}
    for key in FIELDS:
        value = record.get(key, "")
        if not isinstance(value, str):
            raise CredentialStoreError("Invalid Google Drive credential field: %s" % key)
        result[key] = value
    if not result["oauth_refresh_token"]:
        raise CredentialStoreError("Google Drive credentials are missing a refresh token")
    return result


def load_credentials(addon):
    """Load the verified local store, or legacy Kodi settings if absent.

    Corrupt local credentials cause an explicit error, never a silent fallback
    to potentially unrelated Kodi settings from a different Google account.
    """
    path = _path(addon)
    if os.path.isfile(path):
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                raise CredentialStoreError("Google Drive credential file is unexpectedly large")
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except CredentialStoreError:
            raise
        except (ValueError, OSError, UnicodeError) as exc:
            raise CredentialStoreError("Cannot read Google Drive credentials: %s" % type(exc).__name__) from exc
        return _validate_record(record)
    return {key: get_setting_string(addon, key, "") for key in FIELDS}


def has_credentials(addon):
    creds = load_credentials(addon)
    return bool(creds["oauth_refresh_token"] or creds["oauth_access_token"])


def save_credentials(addon, token_payload):
    """Atomically save a complete new authorization and verify its contents.

    We intentionally replace the record rather than merging: credentials from
    another Google account must never be combined with this new authorization.
    """
    refresh = token_payload.get("refresh_token") or ""
    if not isinstance(refresh, str) or not refresh:
        raise CredentialStoreError("Google authorization did not return a renewable token")
    expires_at = ""
    if token_payload.get("expires_in") is not None:
        try:
            seconds = int(token_payload["expires_in"])
            if seconds < 1:
                raise ValueError("Nonpositive expiry")
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
        except (ValueError, TypeError, OverflowError) as exc:
            raise CredentialStoreError("Google authorization returned an invalid expiration") from exc

    record = {
        "schema": CREDENTIAL_SCHEMA,
        "oauth_refresh_token": refresh,
        "oauth_refresh_secret": token_payload.get("refresh_secret") or "",
        "oauth_access_token": token_payload.get("access_token") or "",
        "oauth_access_token_expires_at": expires_at,
        "oauth_scope": token_payload.get("scope") or "",
    }
    values = _validate_record(record)
    encoded = json.dumps(record, ensure_ascii=True, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES:
        raise CredentialStoreError("Google authorization credentials are unexpectedly large")

    path = _path(addon)
    directory = os.path.dirname(path)
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".google-drive-credentials-", suffix=".tmp", dir=directory)
        try:
            os.fchmod(fd, 0o600)
        except (OSError, AttributeError):
            pass  # Some Android emulated filesystems ignore POSIX modes.
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except OSError as exc:
        raise CredentialStoreError("Unable to save Google Drive credentials in add-on userdata: %s" % type(exc).__name__) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    saved = load_credentials(addon)
    if saved != values:
        raise CredentialStoreError("Google Drive credentials failed save verification")
    return True
