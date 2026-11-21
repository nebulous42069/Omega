from resources.lib.drive_api import DriveError
from resources.lib.kodi_compat import (
    get_addon,
    get_monitor,
    get_setting_string,
    log,
    notify,
    offer_first_import_restart,
    show_ok_dialog,
)
from resources.lib.oauth_bridge import OAuthBridgeClient
from resources.lib.pairing_dialog import create_pairing_dialog
from resources.lib.sync_engine import persist_oauth_tokens, perform_sync


def _update_pairing_dialog(dialog, percent, line1, line2="", line3=""):
    dialog.update(percent, line1, line2, line3)


def pair_google_drive(addon=None):
    addon = addon or get_addon()
    bridge_url = get_setting_string(addon, "oauth_bridge_url", "")
    client = OAuthBridgeClient(bridge_url)
    monitor = get_monitor()

    try:
        pairing = client.create_pairing()
        log(
            "Pairing created: pairing_id_present=%s poll_token_present=%s code=%s expires_in=%s interval=%s"
            % (
                bool(pairing.get("pairing_id")),
                bool(pairing.get("poll_token")),
                pairing.get("user_code", ""),
                pairing.get("expires_in", ""),
                pairing.get("interval", ""),
            ),
            addon=addon,
        )
    except Exception as exc:  # pylint: disable=broad-except
        message = "Could not start browser pairing: %s" % exc
        log(message, level="error", addon=addon)
        show_ok_dialog("Kodi Favourites Sync", message)
        return False

    verification_uri = pairing.get("verification_uri_complete") or pairing.get("verification_url") or bridge_url
    user_code = pairing.get("user_code", "")
    pairing_id = pairing.get("pairing_id", "")
    poll_token = pairing.get("poll_token", "")
    interval = max(2, int(pairing.get("interval", 5)))
    expires_in = max(interval, int(pairing.get("expires_in", 600)))

    paired = False
    dialog = create_pairing_dialog(
        addon,
        "Kodi Favourites Sync",
        verification_uri,
        user_code,
    )
    try:
        for elapsed in range(0, expires_in + interval, interval):
            percent = min(100, int((elapsed * 100) / max(1, expires_in)))
            remaining = max(0, expires_in - elapsed)
            _update_pairing_dialog(
                dialog,
                percent,
                "Scan QR code to authorize Google Drive.",
                "URL: %s" % verification_uri,
                "Code: %s | %ss remaining" % (user_code or "-", remaining),
            )
            if dialog.iscanceled():
                notify(addon, "Kodi Favourites Sync", "Google Drive pairing cancelled")
                return False

            status = client.pairing_status(pairing_id, poll_token)
            state = status.get("status")
            log(
                "Pairing poll: elapsed=%ss remaining=%ss state=%s authorized_at_present=%s last_error_present=%s"
                % (
                    elapsed,
                    remaining,
                    state or "",
                    bool(status.get("authorized_at")),
                    bool(status.get("last_error")),
                ),
                addon=addon,
            )
            if state == "authorized":
                log("Pairing authorized; claiming tokens from bridge", addon=addon)
                tokens = client.claim_pairing(pairing_id, poll_token)
                log(
                    "Claim returned: refresh_token_present=%s access_token_present=%s expires_in=%s scope_present=%s"
                    % (
                        bool(tokens.get("refresh_token")),
                        bool(tokens.get("access_token")),
                        tokens.get("expires_in", ""),
                        bool(tokens.get("scope")),
                    ),
                    addon=addon,
                )
                persist_oauth_tokens(addon, tokens)
                log("Token persistence returned successfully", addon=addon)
                paired = True
                break
            if state == "failed":
                raise DriveError(status.get("last_error") or "Browser pairing failed")
            if monitor.waitForAbort(interval):
                return False
    except Exception as exc:  # pylint: disable=broad-except
        message = "Google Drive pairing failed: %s" % exc
        log(message, level="error", addon=addon)
        show_ok_dialog("Kodi Favourites Sync", message)
        return False
    finally:
        dialog.close()

    if paired:
        # Run the first merge using the SAME Kodi add-on settings instance that
        # just stored OAuth tokens. On some Kodi builds the settings screen
        # temporarily exposes stale values to another launched plugin process.
        # This also makes a freshly paired, empty Kodi profile join immediately.
        result = perform_sync(addon=addon, reason="pairing")
        if result["status"] == "ok":
            if not offer_first_import_restart(addon, result):
                notify(addon, "Kodi Favourites Sync", result["message"])
        else:
            log("Drive paired, but initial sync failed: %s" % result["message"], level="warning", addon=addon)
            show_ok_dialog(
                "Kodi Favourites Sync",
                "Google Drive connected, but the first favourites sync failed: %s. "
                "Use Sync favourites now to retry." % result["message"],
            )
        return True

    show_ok_dialog(
        "Kodi Favourites Sync",
        "The Google sign-in code expired before authorization finished. Start pairing again.",
    )
    return False


def pairing_entrypoint():
    pair_google_drive(get_addon())
