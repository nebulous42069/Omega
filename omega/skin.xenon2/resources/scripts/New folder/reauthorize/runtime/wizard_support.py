"""Post-install recovery and read-only status entry points for the skin wizard."""
import os
import embedded as engine

# Presence checks, not live account validation. Names, expiry timestamps, client
# IDs, boolean preferences and consent flags cannot authorize an account.
LOGIN_GROUPS = (
    ('realdebrid.token',), ('premiumize.token',), ('alldebrid.token',),
    ('trakt.token',), ('torbox.token',), ('easydebrid.token',),
    ('offcloud.token',), ('debridlink.token',), ('simkl.token',),
    ('mdblist.oauth.token',), ('punchplay.token',), ('lastfm.session.key',),
    ('linksnappy.username', 'linksnappy.password'),
    ('easynews.username', 'easynews.password'),
    ('filepursuit.api.key',), ('torrentclaw.api.key',),
    ('fanart.tv.api.key',), ('omdb.api.key',), ('mdb.api.key',),
    ('audiodb.api.key',), ('tmdb.api.key',), ('tmdb.session_id',),
    ('tmdb.username', 'tmdb.password'),
    ('youtube.tokens',), ('youtube.api.key',),
)


def has_saved_credentials(addon):
    def present(key):
        value = str(addon.getSetting(key) or '').strip()
        return value.casefold() not in ('', 'true', 'false', 'none', 'null', '0', '{}', '[]')
    return any(all(present(key) for key in group) for group in LOGIN_GROUPS)


def restore_and_sync():
    from reauthorize.modules import server, vault, sync_all, settings_display
    addon = engine.Addon()
    with engine.file_lock(os.path.join(engine.profile(), 'embedded-recovery.lock')):
        # The skin service may already have recovered the account. Always send
        # current credentials to the add-ons just installed by this wizard.
        existing = has_saved_credentials(addon)
        restored = server.auto_restore() if not existing else False
        filled = vault.restore_missing_keys()
        has_credentials = has_saved_credentials(addon)
        if not has_credentials:
            settings_display.sync_authorized_display_values()
            engine.REAL_XBMC.log('Xenon Setup: no saved login credentials or API keys found after backup check; nothing to sync.', engine.REAL_XBMC.LOGINFO)
            return
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
        if failed:
            message = 'Saved logins are available, but some add-ons could not be synced. Use View Status to review them.'
        else:
            message = ('Saved credentials were recovered. The synchronization check is complete. Use View Status to review supported add-ons.'
                       if not existing else
                       'Saved credentials are available. The synchronization check is complete. Use View Status to review supported add-ons.')
        engine.GUI.Dialog().ok('Saved login check', message)

def show_status():
    from reauthorize.windows.status import open_status
    open_status()
