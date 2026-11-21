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
    get_enum_index,
    get_setting_bool,
    get_setting_string,
    log,
    notify,
    offer_first_import_restart,
    offer_manual_sync_close,
    show_ok_dialog,
    xbmcgui,
    now_iso,
    profile_dir,
    set_setting_string,
    translate_path,
)
from resources.lib.state import load_state, save_state
from resources.lib.oauth_store import load_credentials, has_credentials, save_credentials, CredentialStoreError


LOCAL_FAVOURITES_PATH = "special://profile/favourites.xml"


def _sync_result(status, direction, message):
    return {
        "status": status,
        "direction": direction,
        "message": message,
        "completed_at": now_iso(),
    }


def selected_scopes(remote_mode):
    scopes = [APPDATA_SCOPE]
    if remote_mode in ("drive_file", "file_id"):
        scopes.append(DRIVE_FILE_SCOPE)
    return scopes


def parse_expiry(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def build_drive_client(addon):
    remote_mode = get_setting_string(addon, "remote_mode", "appdata") or "appdata"
    credentials = load_credentials(addon)
    client = OAuthTokenProvider(
        client_id="",
        client_secret="",
        refresh_token=credentials["oauth_refresh_token"],
        refresh_secret=credentials["oauth_refresh_secret"],
        scopes=selected_scopes(remote_mode),
        access_token=credentials["oauth_access_token"],
        access_token_expiry=parse_expiry(credentials["oauth_access_token_expires_at"]),
        refresh_bridge_url=get_setting_string(addon, "oauth_bridge_url", ""),
    )
    return DriveClient(client), remote_mode


def persist_oauth_tokens(addon, token_payload):
    """Save and verify credentials before announcing a successful pairing.

    Kodi settings can report success yet reject string writes on some builds.
    Use an atomic add-on userdata file instead; legacy settings remain a
    read-only fallback for already authorized installations.
    """
    save_credentials(addon, token_payload)
    log("Google Drive authorization saved and verified in add-on userdata", addon=addon)
    return True


def perform_sync(addon=None, reason="manual"):
    """Perform non-destructive household sync via independent device journals."""
    from resources.lib.sync_v2 import perform_household_sync

    addon = addon or get_addon()
    addon_profile = profile_dir(addon)
    state = load_state(addon_profile)
    try:
        if not has_credentials(addon):
            result = _sync_result("error", "noop", "Pair Google Drive before synchronizing")
            persist_result(addon_profile, state, result, None)
            return result
        client, mode = build_drive_client(addon)
        if mode != "appdata":
            raise DriveError("Two-way sync requires Google Drive appdata mode; change remote_mode to appdata")
        log("Starting two-way sync (%s)" % reason, addon=addon)
        result = perform_household_sync(
            client, addon, addon_profile, translate_path(LOCAL_FAVOURITES_PATH), reason=reason)
        persist_result(addon_profile, state, result, None)
        return result
    except Exception as exc:  # pylint: disable=broad-except
        log("Two-way sync failed: %s" % exc, level="error", addon=addon)
        log("Sync traceback:\n%s" % traceback.format_exc(), level="error", addon=addon)
        result = _sync_result("error", "noop", str(exc))
        persist_result(addon_profile, state, result, None)
        return result


def _refresh_pending_for_this_session(state):
    """An XML write needs a *Kodi process* restart to refresh its UI cache.

    Remember pending writes after a declined prompt or a background sync, but
    discard the marker when Kodi has actually started a new process. This
    keeps manual Sync Now useful even when an earlier background sync already
    downloaded everything and the next network sync is a no-op.
    """
    try:
        return int(state.get("ui_refresh_pending_pid", -1)) == os.getpid()
    except (TypeError, ValueError):
        return False


def pending_ui_refresh(addon):
    return _refresh_pending_for_this_session(load_state(profile_dir(addon)))


def persist_result(addon_profile, state, result, remote_meta):
    new_state = dict(state)
    # A full Kodi restart starts a new OS process, unlike a slow profile reload.
    # Do not keep prompting based on changes written during a previous launch.
    if not _refresh_pending_for_this_session(new_state):
        new_state.pop("ui_refresh_pending_pid", None)
        new_state.pop("ui_refresh_pending_count", None)
    if result.get("status") == "ok" and result.get("changed_local_file"):
        new_state["ui_refresh_pending_pid"] = os.getpid()
        new_state["ui_refresh_pending_count"] = int(result.get("count", 0))
    new_state["last_sync"] = result["completed_at"]
    new_state["last_direction"] = result["direction"]
    new_state["last_status"] = result["status"]
    new_state["last_message"] = result["message"]
    new_state["last_error"] = result["message"] if result["status"] == "error" else ""
    if "count" in result:
        new_state["last_count"] = result["count"]
    save_state(addon_profile, new_state)


def poll_interval_minutes(base_minutes, idle_checks, adaptive=True):
    """Back off idle polls without changing the explicit sync interval setting.

    At 5 minutes, six quiet checks (~30 minutes) increase to 15 minutes;
    24 quiet checks eventually increase to 30 minutes. Activity/errors reset
    the timer to the user's base interval; manual sync always runs instantly.
    """
    if not adaptive:
        return base_minutes
    if idle_checks >= 24:
        return max(base_minutes, 30)
    if idle_checks >= 6:
        return max(base_minutes, 15)
    return base_minutes


def service_main():
    addon = get_addon()
    monitor = get_monitor()
    if get_setting_bool(addon, "pair_on_next_startup", False):
        set_setting_string(addon, "pair_on_next_startup", "false")
        from resources.lib.pairing_flow import pair_google_drive
        pair_google_drive(addon=addon)

    if get_setting_bool(addon, "sync_on_startup", True):
        try:
            paired = has_credentials(addon)
        except CredentialStoreError as exc:
            log("Google Drive credentials cannot be read: %s" % exc, level="error", addon=addon)
            paired = False
        if paired:
            result = perform_sync(addon=addon, reason="startup")
            if not offer_first_import_restart(addon, result):
                _notify_if_needed(addon, result, manual=False)
        else:
            log("Google Drive is not paired; skipping startup sync", addon=addon)

    # A quiet household needs fewer network requests. A manual sync is never
    # delayed, and new local/cloud activity resets to the chosen base interval.
    intervals = [1, 5, 15, 30]
    idle_checks = 0
    while not monitor.abortRequested():
        choice = get_enum_index(addon, "sync_interval", 1)
        base_minutes = intervals[choice] if 0 <= choice < len(intervals) else 5
        adaptive = get_setting_bool(addon, "reduce_idle_sync", True)
        minutes = poll_interval_minutes(base_minutes, idle_checks, adaptive)
        if monitor.waitForAbort(minutes * 60):
            break
        if not get_setting_bool(addon, "sync_periodically", True):
            idle_checks = 0
            continue
        try:
            paired = has_credentials(addon)
        except CredentialStoreError as exc:
            log("Google Drive credentials cannot be read: %s" % exc, level="error", addon=addon)
            idle_checks = 0
            continue
        if not paired:
            idle_checks = 0
            continue
        result = perform_sync(addon=addon, reason="periodic")
        if (result.get("status") == "ok" and result.get("direction") == "noop"
                and not result.get("cloud_changed", True)
                and not result.get("uploaded_journal", True)):
            idle_checks += 1
        else:
            idle_checks = 0
        if not offer_first_import_restart(addon, result):
            _notify_if_needed(addon, result, manual=False)


def manual_sync_entrypoint():
    """Manual Sync Now always gives visible feedback, unlike the background job."""
    addon = get_addon()
    progress = None
    try:
        # A small non-modal indicator makes slow Drive network calls visible.
        if xbmcgui is not None and hasattr(xbmcgui, "DialogProgressBG"):
            progress = xbmcgui.DialogProgressBG()
            progress.create("Kodi Favourites Sync", "Checking Google Drive...")
    except Exception as exc:
        log("Could not display manual sync progress: %s" % exc,
            level="warning", addon=addon)
        progress = None
    try:
        result = perform_sync(addon=addon, reason="manual")
    finally:
        if progress is not None:
            try:
                progress.close()
            except Exception:
                pass

    if result["status"] != "ok":
        show_ok_dialog("Kodi Favourites Sync", "Sync failed: %s" % result["message"])
        return
    # Preserve the existing first-import wording, but also offer the same
    # close/reopen action for *later* manual downloads or files written by an
    # earlier background sync in this Kodi process.
    if offer_first_import_restart(addon, result):
        return
    if result.get("changed_local_file") or pending_ui_refresh(addon):
        offer_manual_sync_close(addon, result)
        return
    show_ok_dialog(
        "Kodi Favourites Sync",
        "Sync completed successfully. %d favourite(s) in the shared collection. "
        "No newly downloaded favourites need a Kodi restart." % int(result.get("count", 0)),
    )


def reload_favourites_entrypoint():
    """Optional, user-initiated profile reload for a background sync result."""
    from resources.lib.kodi_compat import reload_current_profile, show_ok_dialog, show_yesno_dialog
    if show_yesno_dialog(
        "Kodi Favourites Sync",
        "Reload the active Kodi profile to display newly synced favourites? "
        "This may close open windows or interrupt playback.",
        yeslabel="Reload now", nolabel="Cancel",
    ):
        try:
            reload_current_profile()
        except Exception as exc:
            log("Manual Kodi profile reload failed: %s" % exc, level="warning", addon=get_addon())
            show_ok_dialog("Kodi Favourites Sync", "Profile reload failed: %s. Restart Kodi instead." % exc)


def show_sync_status_entrypoint():
    from resources.lib.kodi_compat import show_ok_dialog
    addon = get_addon()
    state = load_state(profile_dir(addon))
    show_ok_dialog("Kodi Favourites Sync", "Last sync: %s\nResult: %s\nFavourites: %s\n%s" % (
        state.get("last_sync", "Never"),
        state.get("last_status", "Not paired"),
        state.get("last_count", "-"),
        state.get("last_message", ""),
    ))


def _notify_if_needed(addon, result, manual):
    log("%s: %s" % (result["direction"], result["message"]), addon=addon)
    # Background downloads are deliberately silent. Kodi's in-memory
    # favourites are not automatically reread when XML changes on disk.
    if manual or result["status"] == "error":
        notify(addon, "Kodi Favourites Sync", result["message"])
