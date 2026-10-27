"""Post-install recovery and read-only status entry points for the skin wizard."""
import os
import embedded as engine

def restore_and_sync():
    from reauthorize.modules import server, vault, sync_all, settings_display
    addon = engine.Addon()
    with engine.file_lock(os.path.join(engine.profile(), 'embedded-recovery.lock')):
        # The skin service may already have recovered the account. Always send
        # current credentials to the add-ons just installed by this wizard.
        existing = any(addon.getSetting(k) for k in vault.CREDENTIAL_KEYS if vault.is_credential_key(k))
        restored = server.auto_restore() if not existing else False
        filled = vault.restore_missing_keys()
        has_credentials = any(addon.getSetting(k) for k in vault.CREDENTIAL_KEYS if vault.is_credential_key(k))
        include_trakt = False
        if addon.getSetting('trakt.token'):
            consent = addon.getSetting('trakt.auto_push.consent')
            if not consent:
                answer = engine.GUI.Dialog().yesno('ReAuthorize',
                    'Send your saved Trakt login to supported installed add-ons?',
                    nolabel='No', yeslabel='Yes')
                consent = 'true' if answer else 'false'
                addon.setSetting('trakt.auto_push.consent', consent)
            include_trakt = consent == 'true'
        if addon.getSetting('trakt.token') and addon.getSetting('trakt.refresh'):
            from reauthorize.modules.auth import trakt
            trakt.Trakt().refresh_if_due(quiet=True)
        if addon.getSetting('mdblist.oauth.token'):
            from reauthorize.modules.auth import mdblist_oauth
            mdblist_oauth.refresh_if_due(quiet=True)
        failed = sync_all.run_all_syncs(include_trakt=include_trakt) if has_credentials else []
        settings_display.sync_authorized_display_values()
        if has_credentials:
            vault.backup()
            server.backup()
        if not has_credentials:
            message = 'No saved logins could be recovered. You can authorize your services manually.'
        elif failed:
            message = 'Saved logins are available, but some add-ons could not be synced. Use View Status to review them.'
        else:
            message = 'Saved logins were restored and sent to supported installed add-ons.' if restored or filled else 'Your existing saved logins were sent to supported installed add-ons.'
        engine.GUI.Dialog().ok('Saved login check', message)

def show_status():
    from reauthorize.windows.status import open_status
    open_status()
