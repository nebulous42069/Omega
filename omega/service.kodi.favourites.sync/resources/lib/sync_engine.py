import hashlib
import os
import traceback
from datetime import datetime, timedelta, timezone

from resources.lib.drive_api import (
    APPDATA_SCOPE,
    DRIVE_FILE_SCOPE,
    DriveClient,
    DriveError,
    OAuthTokenProvider,
)
from resources.lib.kodi_compat import (
    get_addon,
    get_monitor,
    get_setting_bool,
    get_setting_string,
    log,
    notify,
    now_iso,
    profile_dir,
    set_setting_string,
    translate_path,
)
from resources.lib.state import load_state, save_state


LOCAL_FAVOURITES_PATH = "special://profile/favourites.xml"


def _mtime_to_datetime(timestamp):
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_file_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def _write_file_bytes(path, content):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(content)


def _local_metadata(path):
    if not os.path.exists(path):
        return None
    stat_result = os.stat(path)
    return {
        "path": path,
        "modified_time": _mtime_to_datetime(stat_result.st_mtime),
        "size": stat_result.st_size,
        "sha256": _file_sha256(path),
    }


def decide_sync_direction(local_meta, remote_meta, upload_local_changes):
    if local_meta and remote_meta:
        local_time = local_meta["modified_time"]
        remote_time = remote_meta["modified_time"]

        if local_meta.get("sha256") == remote_meta.get("sha256"):
            return "noop"
        if remote_time and local_time and remote_time > local_time:
            return "download"
        if local_time and remote_time and local_time > remote_time:
            return "upload" if upload_local_changes else "noop"
        if remote_time and not local_time:
            return "download"
        if local_time and not remote_time:
            return "upload" if upload_local_changes else "noop"
        return "noop"

    if remote_meta and not local_meta:
        return "download"
    if local_meta and not remote_meta:
        return "upload" if upload_local_changes else "noop"
    return "noop"


def _sync_result(status, direction, message, local_meta=None, remote_meta=None):
    return {
        "status": status,
        "direction": direction,
        "message": message,
        "local_modified_time": to_iso(local_meta["modified_time"]) if local_meta else None,
        "remote_modified_time": to_iso(remote_meta["modified_time"]) if remote_meta else None,
        "completed_at": now_iso(),
    }


def to_iso(value):
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def selected_scopes(remote_mode):
    scopes = [APPDATA_SCOPE]
    if remote_mode in ("drive_file", "file_id"):
        scopes.append(DRIVE_FILE_SCOPE)
    return scopes


def _scope_contains(granted_scope, expected_scope):
    if not granted_scope or not expected_scope:
        return False
    return expected_scope in granted_scope.split()


def parse_expiry(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def build_drive_client(addon):
    remote_mode = get_setting_string(addon, "remote_mode", "appdata") or "appdata"
    client = OAuthTokenProvider(
        client_id="",
        client_secret="",
        refresh_token=get_setting_string(addon, "oauth_refresh_token", ""),
        refresh_secret=get_setting_string(addon, "oauth_refresh_secret", ""),
        scopes=selected_scopes(remote_mode),
        access_token=get_setting_string(addon, "oauth_access_token", ""),
        access_token_expiry=parse_expiry(get_setting_string(addon, "oauth_access_token_expires_at", "")),
        refresh_bridge_url=get_setting_string(addon, "oauth_bridge_url", ""),
    )
    return DriveClient(client), remote_mode


def persist_oauth_tokens(addon, token_payload):
    refresh_token = token_payload.get("refresh_token")
    refresh_secret = token_payload.get("refresh_secret")
    access_token = token_payload.get("access_token")
    expires_in = token_payload.get("expires_in")
    granted_scope = token_payload.get("scope")
    log(
        "Persisting OAuth tokens: refresh_token_present=%s refresh_secret_present=%s access_token_present=%s expires_in=%s scope_present=%s"
        % (
            bool(refresh_token),
            bool(refresh_secret),
            bool(access_token),
            expires_in if expires_in is not None else "",
            bool(granted_scope),
        ),
        addon=addon,
    )

    if refresh_token:
        set_setting_string(addon, "oauth_refresh_token", refresh_token)
        stored_refresh_token = get_setting_string(addon, "oauth_refresh_token", "")
        log(
            "Stored oauth_refresh_token: persisted=%s length=%s"
            % (bool(stored_refresh_token), len(stored_refresh_token)),
            addon=addon,
        )
    if refresh_secret:
        set_setting_string(addon, "oauth_refresh_secret", refresh_secret)
        stored_refresh_secret = get_setting_string(addon, "oauth_refresh_secret", "")
        log(
            "Stored oauth_refresh_secret: persisted=%s length=%s"
            % (bool(stored_refresh_secret), len(stored_refresh_secret)),
            addon=addon,
        )
    if access_token:
        set_setting_string(addon, "oauth_access_token", access_token)
        stored_access_token = get_setting_string(addon, "oauth_access_token", "")
        log(
            "Stored oauth_access_token: persisted=%s length=%s"
            % (bool(stored_access_token), len(stored_access_token)),
            addon=addon,
        )
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        set_setting_string(addon, "oauth_access_token_expires_at", expires_at.isoformat())
        stored_expiry = get_setting_string(addon, "oauth_access_token_expires_at", "")
        log(
            "Stored oauth_access_token_expires_at: persisted=%s value=%s"
            % (bool(stored_expiry), stored_expiry),
            addon=addon,
        )
    if granted_scope:
        set_setting_string(addon, "oauth_scope", granted_scope)
        stored_scope = get_setting_string(addon, "oauth_scope", "")
        log(
            "Stored oauth_scope: persisted=%s length=%s"
            % (bool(stored_scope), len(stored_scope)),
            addon=addon,
        )


def perform_sync(addon=None, reason="manual"):
    addon = addon or get_addon()
    local_path = translate_path(LOCAL_FAVOURITES_PATH)
    addon_profile = profile_dir(addon)
    state = load_state(addon_profile)

    log("Starting sync (%s)" % reason, addon=addon)
    drive_file_id = get_setting_string(addon, "drive_file_id", "")
    drive_folder_id = get_setting_string(addon, "drive_folder_id", "")
    remote_filename = get_setting_string(addon, "remote_filename", "favourites.xml")
    upload_local_changes = get_setting_bool(addon, "upload_local_changes", True)
    oauth_refresh_token = get_setting_string(addon, "oauth_refresh_token", "")
    oauth_access_token = get_setting_string(addon, "oauth_access_token", "")
    oauth_scope = get_setting_string(addon, "oauth_scope", "")
    oauth_bridge_url = get_setting_string(addon, "oauth_bridge_url", "")
    log("Setting check: upload_local_changes=%s" % upload_local_changes, addon=addon)

    if not oauth_refresh_token and not oauth_access_token:
        if oauth_bridge_url:
            result = _sync_result(
                "ok",
                "noop",
                "Google Drive is not paired yet. Run the pairing action before startup sync can use OAuth.",
            )
            persist_result(addon_profile, state, result, None)
            return result
        result = _sync_result(
            "error",
            "noop",
            "OAuth bridge URL is not configured and no OAuth token is available",
        )
        persist_result(addon_profile, state, result, None)
        return result

    client, remote_mode = build_drive_client(addon)
    log(
        "OAuth scope check: remote_mode=%s appdata_granted=%s drive_file_granted=%s scope=%s"
        % (
            remote_mode,
            _scope_contains(oauth_scope, APPDATA_SCOPE),
            _scope_contains(oauth_scope, DRIVE_FILE_SCOPE),
            oauth_scope or "",
        ),
        addon=addon,
    )

    try:
        remote_meta = client.resolve_remote(drive_file_id, drive_folder_id, remote_filename, remote_mode=remote_mode)
        local_meta = _local_metadata(local_path)
        remote_bytes = None

        if remote_meta and os.path.exists(local_path):
            remote_bytes = client.download_file(remote_meta["id"])
            remote_meta["sha256"] = hashlib.sha256(remote_bytes).hexdigest()
        elif remote_meta:
            remote_meta["sha256"] = None

        direction = decide_sync_direction(local_meta, remote_meta, upload_local_changes)
        log("Sync decision: %s" % direction, verbose_only=True, addon=addon)

        if direction == "download":
            if not remote_meta:
                raise DriveError("Remote file metadata is missing for download")
            content = remote_bytes if remote_bytes is not None else client.download_file(remote_meta["id"])
            _write_file_bytes(local_path, content)
            if remote_meta["modified_time"] is not None:
                timestamp = remote_meta["modified_time"].timestamp()
                os.utime(local_path, (timestamp, timestamp))
            local_meta = _local_metadata(local_path)
            result = _sync_result("ok", "download", "Downloaded newer remote favourites.xml", local_meta, remote_meta)
            persist_result(addon_profile, state, result, remote_meta)
            return result

        if direction == "upload":
            if not local_meta:
                raise DriveError("Local favourites.xml is missing for upload")
            content = _read_file_bytes(local_path)
            if remote_meta:
                remote_meta = client.update_file(remote_meta["id"], remote_filename, content)
            else:
                remote_meta = client.create_file(drive_folder_id, remote_filename, content, remote_mode=remote_mode)
            result = _sync_result("ok", "upload", "Uploaded newer local favourites.xml", local_meta, remote_meta)
            persist_result(addon_profile, state, result, remote_meta)
            return result

        result = _sync_result("ok", "noop", "Local and remote favourites.xml are already in sync", local_meta, remote_meta)
        persist_result(addon_profile, state, result, remote_meta)
        return result
    except Exception as exc:  # pylint: disable=broad-except
        log("Sync failed: %s" % exc, level="error", addon=addon)
        log("Sync traceback:\n%s" % traceback.format_exc(), level="error", addon=addon)
        result = _sync_result("error", "noop", str(exc))
        persist_result(addon_profile, state, result, None)
        return result


def persist_result(addon_profile, state, result, remote_meta):
    new_state = dict(state)
    new_state["last_sync"] = result["completed_at"]
    new_state["last_direction"] = result["direction"]
    new_state["last_status"] = result["status"]
    new_state["last_error"] = result["message"] if result["status"] == "error" else ""
    if remote_meta:
        new_state["last_remote_file_id"] = remote_meta.get("id")
        new_state["last_remote_modified_time"] = to_iso(remote_meta.get("modified_time"))
        new_state["last_remote_version"] = remote_meta.get("version")
    save_state(addon_profile, new_state)


def service_main():
    addon = get_addon()
    monitor = get_monitor()
    if get_setting_bool(addon, "pair_on_next_startup", False):
        log("Launching Google Drive pairing from startup fallback toggle", addon=addon)
        set_setting_string(addon, "pair_on_next_startup", "false")
        from resources.lib.pairing_flow import pair_google_drive

        pair_google_drive(addon=addon)
    if get_setting_bool(addon, "sync_on_startup", True):
        result = perform_sync(addon=addon, reason="startup")
        _notify_if_needed(addon, result, manual=False)
    else:
        log("Startup sync is disabled", addon=addon)

    while not monitor.abortRequested():
        if monitor.waitForAbort(30):
            break


def manual_sync_entrypoint():
    addon = get_addon()
    result = perform_sync(addon=addon, reason="manual")
    _notify_if_needed(addon, result, manual=True)


def _notify_if_needed(addon, result, manual):
    direction = result["direction"]
    message = result["message"]
    log("%s: %s" % (direction, message), addon=addon)
    if manual or result["status"] == "error":
        heading = "Kodi Favourites Sync"
        notify(addon, heading, message)
