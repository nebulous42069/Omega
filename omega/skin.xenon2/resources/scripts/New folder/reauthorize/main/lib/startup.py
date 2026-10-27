import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import os
import os.path
import time
import sqlite3
import _strptime
import threading

try:
    from libs.common import var
except ImportError:
    class _FallbackVar:
        amgr = '[ReAuthorize]'
    var = _FallbackVar()
from reauthorize.modules import control
from reauthorize.modules import log_utils
from reauthorize.modules import settings_display
from reauthorize.modules import vault
from reauthorize.modules import server
from reauthorize.modules import owner
from reauthorize.modules import reset
from reauthorize.modules.sync_all import run_all_syncs


def _sync_settings_display_values():
    try:
        settings_display.sync_authorized_display_values()
    except:
        xbmc.log('%s: Startup settings display sync failed!' % var.amgr, xbmc.LOGINFO)

# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
accountmgr = control.accountmgr
dialog = xbmcgui.Dialog()
LOGINFO = 1


def _step(name):
    """
    One line per step of the start-up sequence. Kodi froze about 11 seconds into a start twice
    (MQ9 2026-10-05, the bench 2026-10-06), each time about a second after this service's last
    log line, and the log could not say what the service was doing: a step that is entered and
    never left is now the last '[ReAuthorize Start]' line. About 15 short lines per Kodi start.
    """
    xbmc.log('[ReAuthorize Start] %s' % name, LOGINFO)


def _refresh_trakt():
    """
    Renew the Trakt token while there is plenty of time left, before any add-on
    (their services start alongside this one) gets the chance. The refresh token
    is shared and rotates on use, so whoever refreshes first leaves everyone else
    holding a dead copy. When that is always ReAuthorize, and it re-sends the
    result, ReAuthorize stays the one app Trakt sees and every add-on keeps working.
    """
    if not (accountmgr.getSetting('trakt.token') and accountmgr.getSetting('trakt.refresh')):
        return
    try:
        from reauthorize.modules.auth import trakt
        trakt.Trakt().refresh_if_due(quiet=True)
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Trakt renewal check failed: %s' % e, LOGINFO)


def _refresh_mdblist():
    """Renew the MDBList sign-in well before its 30 days run out, and re-send it (mdblist_oauth.py)."""
    if not accountmgr.getSetting('mdblist.oauth.token'):
        return
    try:
        from reauthorize.modules.auth import mdblist_oauth
        mdblist_oauth.refresh_if_due(quiet=True)
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  MDBList renewal check failed: %s' % e, LOGINFO)


# How often a running Kodi checks whether a sign-in is due for renewal. Each check is a
# local comparison; Trakt or MDBList is only called when a renewal is actually due.
def _refresh_punchplay():
    """
    PunchPlay sign-ins last one hour and only ReAuthorize renews them (auth/punchplay.py): renew
    when under 25 minutes remain and hand the new one to the add-ons at once. Looked at every
    five minutes, not every six hours like the others.
    """
    if not (accountmgr.getSetting('punchplay.token') or accountmgr.getSetting('punchplay.refresh')):
        return
    try:
        from reauthorize.modules.auth import punchplay
        punchplay.refresh_if_due(quiet=True)
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  PunchPlay renewal check failed: %s' % e, LOGINFO)


def _adopt_trakt():
    """Every five minutes: another Kodi on this device may have renewed Trakt; take its newer pair from the
    vault (auth/trakt.py adopt_newer_from_vault). No call to Trakt."""
    if not (accountmgr.getSetting('trakt.token') and accountmgr.getSetting('trakt.refresh')):
        return
    try:
        from reauthorize.modules.auth import trakt
        trakt.Trakt().adopt_and_send()
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Trakt backup check failed: %s' % e, LOGINFO)


RENEW_CHECK_SECONDS = 6 * 60 * 60

# How often a running Kodi looks for an add-on that has become ready since the last look
# (installed, or opened for the first time). A handful of file checks.
NEW_ADDON_CHECK_SECONDS = 5 * 60


def _link_new_addons(at_start):
    """
    An add-on installed or first opened after the last sync has no sign-ins, and nobody knows to
    press Sync (modules/new_addons.py). When one appears, run the normal full sync once.
    At start a changed key file asks about a restart; while Kodi runs it only leaves the note,
    and nothing is done during playback (the next look catches it).
    """
    try:
        from reauthorize.modules import new_addons, restart_hint
        if not at_start and xbmc.Player().isPlaying():
            return
        new_ids = new_addons.appeared()
        if not new_ids:
            return
        before = restart_hint.key_files()
        new_addons.link(new_ids)
        restart_hint.note_for_next_start(before, 'new add-ons')
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  New add-on check failed: %s' % e, LOGINFO)


def _resend_after_settings_repair(addon_ids):
    """
    An add-on whose settings file was repaired at this start (settings_health.repair_addons)
    lost every sign-in Kodi had been ignoring: send them again. Trakt only with consent.
    """
    if not addon_ids:
        return
    try:
        include_trakt = bool(control.setting('trakt.token')) and control.setting('trakt.auto_push.consent') != 'false'
        xbmc.log('[ReAuthorize Settings] sending the sign-ins again to %s' % ', '.join(addon_ids), LOGINFO)
        failed = run_all_syncs(include_trakt=include_trakt)
        if failed:
            xbmc.log('[ReAuthorize Settings] sync failed for: %s' % ', '.join(failed), LOGINFO)
    except Exception as e:
        xbmc.log('[ReAuthorize Settings] sending the sign-ins again failed: %s' % e, LOGINFO)


def _keep_signed_in():
    # control.monitor, never a new xbmc.Monitor(): one made AFTER Kodi asked the script to stop
    # never hears about it and waits the full six hours. 1.3.7 made a new one here, so closing
    # Kodi in its first five minutes (while check_api was still looping) left this script to
    # be killed ("script didn't stop in 5 seconds", found on the bench 2026-10-04).
    monitor = control.monitor
    since_renew_check = 0
    while not monitor.waitForAbort(NEW_ADDON_CHECK_SECONDS):
        _refresh_punchplay()
        _adopt_trakt()
        _link_new_addons(at_start=False)
        since_renew_check += NEW_ADDON_CHECK_SECONDS
        if since_renew_check >= RENEW_CHECK_SECONDS:
            since_renew_check = 0
            _refresh_trakt()
            _refresh_mdblist()


def _confirm_owner():
    """Make sure this device's ID is its own and not one it shares (server.confirm_owner)."""
    try:
        server.confirm_owner()
        owner.leak_notice(server.claim_leaks())
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Device ID check failed: %s' % e, LOGINFO)


def _guard_identity():
    """
    First thing at every start, before anything is restored, pushed or backed up:
    obey the server's reset switch (reset.py - delete that call and import in
    1.3.6), then remove sign-ins that arrived with a build (owner.py). The reset
    goes first so that, while it is armed, every box is told in its plain-words
    popup and not by the smaller notice below. Neither may ever stop the service
    from starting.
    """
    new_box = False
    try:
        new_box = owner.is_new_box()   # before anything can create this device's ID
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Sign-in ownership check failed: %s' % e, LOGINFO)
    try:
        reset.check()
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Reset check failed: %s' % e, LOGINFO)
    try:
        owner.startup_check(new_box)
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Sign-in ownership check failed: %s' % e, LOGINFO)


# Sign-ins checked when a device finds it was sharing its backup: the name, the
# setting prefix, and the setting that means "signed in". Purely informational
# to the user - see _shared_backup_notice's dialog text for why no cause is given.
_SIGNINS = (
    ('Real-Debrid', 'realdebrid.', 'realdebrid.token'),
    ('Premiumize',  'premiumize.', 'premiumize.token'),
    ('AllDebrid',   'alldebrid.',  'alldebrid.token'),
    ('TorBox',      'torbox.',     'torbox.token'),
    ('Easy Debrid', 'easydebrid.', 'easydebrid.token'),
    ('OffCloud',    'offcloud.',   'offcloud.token'),
    ('Debrid-Link', 'debridlink.', 'debridlink.token'),
    ('Linksnappy',  'linksnappy.', 'linksnappy.username'),
    ('Easynews',    'easynews.',   'easynews.username'),
    ('Trakt',       'trakt.',      'trakt.token'),
    ('Simkl',       'simkl.',      'simkl.token'),
    ('Last.fm',     'lastfm.',     'lastfm.session.key'),
    ('TMDb',        'tmdb.',       'tmdb.session_id'),
    ('YouTube',     'youtube.',    'youtube.tokens'),
)

# Which _SIGNINS prefixes can be force-pushed (blank) to every addon that
# already has them, via sync_all.run_all_syncs(wipe=...). Left out on purpose:
#   trakt.   - handled directly below by revoking the token itself.
#   lastfm.  - lastfm_sync re-imports from the scrobbler addon when ReAuthorize's
#              own copy is blank, so pushing through it would undo the clear;
#              handled directly below instead.
#   tmdb.    - session-based sign-in, no addon it gets pushed to.
#   youtube. - its own JSON sign-in file, not a settings push; too easy to
#              corrupt blind, and untested in a real Kodi (see AGENTS.md).
_WIPE_TAG = {
    'realdebrid.': 'rd', 'premiumize.': 'pm', 'alldebrid.': 'ad',
    'torbox.': 'torbox', 'easydebrid.': 'easyd', 'offcloud.': 'offc',
    'debridlink.': 'debridlink', 'linksnappy.': 'linksnappy',
    'easynews.': 'easy', 'simkl.': 'simkl',
}


def _shared_backup_notice():
    """
    This device's ID had been claimed by another device (see device.py), so it
    now has its own. Whatever it was signed into may not belong to this box -
    ask once, in the vaguest honest terms, whether to clear it and re-authorize.

    Deliberately vague about why: this is almost always a non-technical user
    who will uninstall rather than worry about what "shared with other boxes"
    means. But it still has to ask, not just act - a box that lands here
    because *it* is the one that got moved to a new ID (see
    case_a_build_no_longer_shares_its_makers_backup's "builder" case in
    tests/test_device_identity.py) is signed into its own real accounts, and
    only the person in front of it can tell the two situations apart.
    """
    if accountmgr.getSetting('server.shared.notice') != 'true':
        return
    accountmgr.setSetting('server.shared.notice', '')

    shown = [(label, prefix) for label, prefix, token_key in _SIGNINS
             if accountmgr.getSetting(token_key)]
    if not shown:
        return

    fix = dialog.yesno(
        'ReAuthorize',
        'Sorry for the inconvenience - an internal issue reset the sign-in '
        'details for:[CR][CR]%s[CR][CR]Re-authorize them now?'
        % '[CR]'.join('  - %s' % label for label, _ in shown),
        nolabel='Not now', yeslabel='Re-authorize')
    if not fix:
        return

    # Trakt: kill the token itself, not just ReAuthorize's copy of it. A local
    # clear would leave it live in every addon it was already pushed to, and
    # in the actual owner's hands elsewhere. oauth/revoke kills it everywhere
    # at once (free Trakt accounts allow only one connected app).
    if any(prefix == 'trakt.' for _, prefix in shown):
        try:
            from reauthorize.modules.auth.trakt import Trakt
            Trakt().call('oauth/revoke', data={'token': accountmgr.getSetting('trakt.token')},
                         with_auth=False)
        except Exception as e:
            xbmc.log('[ script.module.reauthorize ]  Trakt revoke during shared-backup '
                     'cleanup failed: %s' % e, LOGINFO)

    # Last.fm: clear the scrobbler addon's own copy directly, since
    # lastfm_sync would otherwise just re-import it from there once
    # ReAuthorize's own setting goes blank.
    if any(prefix == 'lastfm.' for _, prefix in shown):
        try:
            scrobbler = xbmcaddon.Addon('service.scrobbler.lastfm')
            scrobbler.setSetting('lastfmkey', '')
            scrobbler.setSetting('lastfmuser', '')
        except Exception:
            pass

    prefixes = tuple(prefix for _, prefix in shown)
    for key in vault.CREDENTIAL_KEYS:
        if key.startswith(prefixes) and vault.is_credential_key(key):
            accountmgr.setSetting(key, '')

    # Push the now-blank credentials out to every addon that already has the
    # old ones - a normal sync skips a blank setting as "nothing to do", so
    # without this the stale sign-in would sit in Umbrella, Red Light, etc.
    # forever, until it quietly breaks once the real owner resets it.
    wipe_tags = {_WIPE_TAG[prefix] for _, prefix in shown if prefix in _WIPE_TAG}
    if wipe_tags:
        run_all_syncs(include_trakt=False, wipe=wipe_tags)

    # Both backups still hold them. Start both again from what is left.
    vault.clear()
    server.clear()
    vault.backup()
    server.backup()
    _sync_settings_display_values()
    xbmc.log('[ script.module.reauthorize ]  Cleared sign-ins after a device ID conflict.', LOGINFO)


def _push_trakt_once():
    """
    Before 1.3.1 Trakt only reached an addon once the user had found the hidden
    "Choose Primary Kodi Trakt Add-on" button, so people who signed in have it saved
    in ReAuthorize and sent nowhere. Send it once, on the first start after updating.
    An explicit "No" to the auto-link question is respected.

    Done here, not in a thread: the service may end right after, which would cut a
    background push off half way through the addons.
    """
    if accountmgr.getSetting('trakt.all_push.done') == 'true' or not accountmgr.getSetting('trakt.token'):
        return
    if accountmgr.getSetting('trakt.auto_push.consent') == 'false':
        return
    try:
        from reauthorize.modules.sync import trakt_sync, trakt_select
        trakt_sync.Auth().trakt_auth()
        if trakt_select.installed_addons():
            accountmgr.setSetting('sync.tk.service', 'true')
            accountmgr.setSetting('api.service', 'true')
        accountmgr.setSetting('trakt.all_push.done', 'true')
        xbmc.log('[ script.module.reauthorize ]  Trakt sent to every installed add-on (first start after updating).', LOGINFO)
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Sending Trakt to add-ons failed: %s' % e, LOGINFO)

def _resend_after_key_swap():
    """
    A key ReAuthorize swapped while Kodi ran is used by that add-on from this start on. Until now
    it may have sent a sign-in under its old key and dropped it, so send everything once more
    (restart_hint.note_for_next_start, 1.4.0: replaces a 'Restart Kodi?' question that came up
    after nearly every add-on update).
    """
    from reauthorize.modules import restart_hint
    if accountmgr.getSetting(restart_hint.RESEND_SETTING) != 'true':
        return
    accountmgr.setSetting(restart_hint.RESEND_SETTING, '')
    try:
        from reauthorize.modules.sync_all import run_all_syncs
        include_trakt = bool(accountmgr.getSetting('trakt.token')) and accountmgr.getSetting('trakt.auto_push.consent') != 'false'
        failed = run_all_syncs(include_trakt=include_trakt)
        xbmc.log('[ script.module.reauthorize ]  Sign-ins sent again after an add-on key change%s.'
                 % (' (failed: %s)' % ', '.join(failed) if failed else ''), LOGINFO)
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Re-send after a key change failed: %s' % e, LOGINFO)


def _link_simkl():
    """
    Simkl ties a sign-in to an app, and until 1.3.9 the add-ons got the token without ReAuthorize's
    app key (or nothing at all), so it never worked in them. Send it properly once, on the first
    start after updating. At every start, put the key back in an add-on whose update restored its
    own. A changed key file is only read when Kodi starts, so ask about a restart.
    """
    if not accountmgr.getSetting('simkl.token'):
        return
    try:
        from reauthorize.modules import restart_hint
        from reauthorize.modules.sync import simkl_sync
        before = restart_hint.key_files()
        if accountmgr.getSetting('simkl.all_push.done') != 'true':
            simkl_sync.Auth().simkl_auth()
            accountmgr.setSetting('simkl.all_push.done', 'true')
            xbmc.log('[ script.module.reauthorize ]  Simkl sent to every installed add-on (first start after updating).', LOGINFO)
        else:
            simkl_sync.ensure_keys()
        restart_hint.note_for_next_start(before, 'Simkl')
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  Sending Simkl to add-ons failed: %s' % e, LOGINFO)


timeout_start = time.time()
timeout = 60*5


def genocide_sync():
    try:
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.chainsgenocide/?action=tools_forceTraktSync)')
        xbmc.sleep(1000)
        if xbmc.getCondVisibility('Window.IsTopMost(yesnodialog)'):
            xbmc.executebuiltin('SendClick(yesnodialog, 11)')
        accountmgr.setSetting("genocide_traktsync", 'false')
    except:
        xbmc.log('%s: Startup Chains Genocide Trakt Sync Failed!' % var.amgr, xbmc.LOGINFO)


class PremAccntNotification:
    def run(self):
        from datetime import datetime
        from reauthorize.modules.auth import alldebrid
        from reauthorize.modules.auth import premiumize
        from reauthorize.modules.auth import realdebrid
        xbmc.log('[ script.module.reauthorize ]  Debrid Account Expiry Notification Service Starting...', LOGINFO)
        self.duration = [(15, 10), (11, 7), (8, 4), (5, 2), (3, 0)]
        if control.setting('alldebrid.username') != '' and control.setting('alldebrid.expiry.notice') == 'true':
            account_info = alldebrid.AllDebrid().account_info()['user']
            if account_info:
                if not account_info['isSubscribed']:
                    expires = datetime.fromtimestamp(account_info['premiumUntil'])
                    days_remaining = (expires - datetime.today()).days
                    if days_remaining < 15:
                        control.notification(message='AllDebrid Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'alldebrid.png'))

        if control.setting('premiumize.username') != '' and control.setting('premiumize.expiry.notice') == 'true':
            account_info = premiumize.Premiumize().account_info()
            if account_info:
                expires = datetime.fromtimestamp(account_info['premium_until'])
                days_remaining = (expires - datetime.today()).days
                if days_remaining < 15:
                    control.notification(message='Premiumize.me Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'premiumize.png'))

        if control.setting('realdebrid.username') != '' and control.setting('realdebrid.expiry.notice') == 'true':
            account_info = realdebrid.RealDebrid().account_info()
            if account_info:
                import time
                FormatDateTime = "%Y-%m-%dT%H:%M:%S.%fZ"
                try: expires = datetime.strptime(account_info['expiration'], FormatDateTime)
                except: expires = datetime(*(time.strptime(account_info['expiration'], FormatDateTime)[0:6]))
                days_remaining = (expires - datetime.today()).days
                if days_remaining < 15:
                    control.notification(message='Real-Debrid Account expires in %s days' % days_remaining, icon=control.joinPath(control.artPath(), 'realdebrid.png'))


# ─── API Key Service ──────────────────────────────────────────────────────────
#
# File-based addons store their Trakt client/secret in a .py source file.
# check_api() monitors every 10 seconds and replaces the old keys with
# Account Manager's keys if Trakt is authorised and the addon is installed.
# restore_api() does the same thing once, triggered by the UI setting.
#
# Settings-based addons (Umbrella, POV, Infinity) use xbmcaddon.setSetting()
# instead and are handled explicitly below the loop.

_api_addons_cache = None

def _api_addons():
    """Return the file-based addon table, computed once and cached."""
    global _api_addons_cache
    if _api_addons_cache is None:
        _api_addons_cache = [
            # (chk_addon_path, chkset_path, trakt_file, old_client, old_secret, label)
            (var.chk_seren,       var.chkset_seren,       var.path_seren,       var.seren_client,    var.seren_secret,    'Seren'),
            (var.chk_coal,        var.chkset_coal,        var.path_coal,        var.coal_client,     var.coal_secret,     'Coalition'),
            (var.chk_shadow,      var.chkset_shadow,      var.path_shadow,      var.shadow_client,   var.shadow_secret,   'Shadow'),
            (var.chk_ghost,       var.chkset_ghost,       var.path_ghost,       var.ghost_client,    var.ghost_secret,    'Ghost'),
            (var.chk_blueballs,   var.chkset_blueballs,   var.path_blueballs,   var.blueballs_client, var.blueballs_secret, 'Blue Balls'),
            (var.chk_twisted,     var.chkset_twisted,     var.path_twisted,     var.twisted_client,  var.twisted_secret,  'Twisted'),
            (var.chk_base,        var.chkset_base,        var.path_base,        var.base_client,     var.base_secret,     'Base'),
            (var.chk_chains,      var.chkset_chains,      var.path_chains,      var.chains_client,   var.chains_secret,   'Chain Reaction'),
            (var.chk_patriot,     var.chkset_patriot,     var.path_patriot,     var.patriot_client,  var.patriot_secret,  'Patriot'),
            (var.chk_blackl,      var.chkset_blackl,      var.path_blackl,      var.blackl_client,   var.blackl_secret,   'Black Lightning'),
            (var.chk_aliunde,     var.chkset_aliunde,     var.path_aliunde,     var.aliunde_client,  var.aliunde_secret,  'Aliunde'),
            (var.chk_genocide,    var.chkset_genocide,    var.path_genocide,    var.genocide_client, var.genocide_secret, 'Chains Genocide'),
            (var.chk_newgenocide, var.chkset_newgenocide, var.path_newgenocide, var.genocide_client, var.genocide_secret, 'Genocide'),
            (var.chk_crew,        var.chkset_crew,        var.path_crew,        var.crew_client,     var.crew_secret,     'The Crew'),
            (var.chk_scrubs,      var.chkset_scrubs,      var.path_scrubs,      var.scrubs_client,   var.scrubs_secret,   'Scrubs V2'),
            (var.chk_tmdbh,       var.chkset_tmdbh,       var.path_tmdbh,       var.tmdbh_client,    var.tmdbh_secret,    'TMDb Helper'),
            (var.chk_trakt,       var.chkset_trakt,       var.path_trakt,       var.trakt_client,    var.trakt_secret,    'Trakt Addon'),
            (var.chk_allaccounts, var.chkset_allaccounts, var.path_allaccounts, var.allacts_client,  var.allacts_secret,  'All Accounts'),
            (var.chk_myaccounts,  var.chkset_myaccounts,  var.path_myaccounts,  var.myacts_client,   var.myacts_secret,   'My Accounts'),
            (var.chk_gratisred,   var.chkset_gratisred,   var.path_gratisred,   var.gratisred_client, var.gratisred_secret, 'GratisRed'),
        ]
    return _api_addons_cache


def _inject_file_keys(path, old_client, old_secret, label):
    """Replace old Trakt API keys in a file with Account Manager's keys if not already present."""
    try:
        with open(path) as f:
            data = f.read()
        if var.chk_api not in data:
            swapped = data.replace(old_client, var.client_am).replace(old_secret, var.secret_am)
            if swapped != data:        # a file with neither key was rewritten unchanged every 10 seconds
                with open(path, 'w') as f:
                    f.write(swapped)
    except Exception:
        xbmc.log('%s: %s API Failed!' % (var.amgr, label), xbmc.LOGINFO)


# Add-ons the key check could not open (disabled in Kodi: the folder is there, but Kodi answers 'Unknown addon id').
# Skipped for the rest of the check instead of failing, and logging it, every 10 seconds (bench, 2026-10-18).
_UNAVAILABLE = set()


def _usable(addon_id):
    if addon_id in _UNAVAILABLE:
        return False
    try:
        xbmcaddon.Addon(addon_id)
        return True
    except Exception:
        _UNAVAILABLE.add(addon_id)
        xbmc.log('[ReAuthorize Start] %s is installed but cannot be opened (disabled?) - the key check skips it'
                 % addon_id, LOGINFO)
        return False


def check_api():
    monitor = control.monitor
    first_pass = True
    while not monitor.abortRequested():
        if time.time() > timeout_start + timeout:
            break

        if control.setting('api.service') == 'true' and control.setting('trakt.token'):
            from reauthorize.modules import restart_hint
            if first_pass: _step('key check: reading key files')
            key_files_before = restart_hint.key_files()
            for chk, chkset, path, old_client, old_secret, label in _api_addons():
                if xbmcvfs.exists(chk) and xbmcvfs.exists(chkset):
                    _inject_file_keys(path, old_client, old_secret, label)

            # The Crew 3.x - its key lines are swapped by pattern (sync/crew_trakt.py), which the
            # plain search-and-replace above cannot do; an update of Crew puts its own key back.
            try:
                from reauthorize.modules.sync import crew_trakt
                if crew_trakt.installed():
                    crew_trakt.ensure_key()
            except Exception:
                xbmc.log('%s: The Crew API Failed!' % var.amgr, xbmc.LOGINFO)

            # The Trakt add-on 3.9.0 keeps its key as a list of numbers: the same kind of line swap.
            try:
                from reauthorize.modules.sync import traktaddon_key
                if traktaddon_key.installed():
                    traktaddon_key.ensure_key()
            except Exception:
                xbmc.log('%s: Trakt Addon API Failed!' % var.amgr, xbmc.LOGINFO)

            # A key swapped now (an update of the add-on put its own back) is read by that add-on
            # from the next Kodi start. No question (1.4.0, restart_hint.py): logged, and the
            # sign-ins are sent once more at the next start.
            restart_hint.note_for_next_start(key_files_before, 'Trakt key check')

            if first_pass: _step('key check: Umbrella, POV, Infinity settings')
            # Umbrella - settings-based
            if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb) and _usable('plugin.video.umbrella'):
                try:
                    umb = xbmcaddon.Addon('plugin.video.umbrella')
                    chk_client = umb.getSetting('trakt.clientid')
                    chk_auth   = umb.getSetting('trakt.user.token')
                    if str(chk_client) != str(var.chk_api) and control.setting('trakt.token') == str(chk_auth):
                        umb.setSetting('traktuserkey.customenabled', 'true')
                        umb.setSetting('trakt.clientid', var.client_am)
                        umb.setSetting('trakt.clientsecret', var.secret_am)
                except Exception:
                    xbmc.log('%s: Umbrella API Failed!' % var.amgr, xbmc.LOGINFO)

            # POV - settings-based
            if xbmcvfs.exists(var.chk_pov) and xbmcvfs.exists(var.chkset_pov) and _usable('plugin.video.pov'):
                try:
                    pov = xbmcaddon.Addon('plugin.video.pov')
                    chk_client = pov.getSetting('trakt.client_id')
                    chk_auth   = pov.getSetting('trakt.token')
                    if str(chk_client) != str(var.chk_api) and control.setting('trakt.token') == str(chk_auth):
                        pov.setSetting('trakt.client_id', var.client_am)
                        pov.setSetting('trakt.client_secret', var.secret_am)
                except Exception:
                    xbmc.log('%s: POV API Failed!' % var.amgr, xbmc.LOGINFO)

            # Infinity - settings-based
            if xbmcvfs.exists(var.chk_infinity) and xbmcvfs.exists(var.chkset_infinity) and _usable('plugin.video.infinity'):
                try:
                    inf = xbmcaddon.Addon('plugin.video.infinity')
                    chk_client = inf.getSetting('trakt.clientid')
                    chk_auth   = inf.getSetting('trakt.user.token')
                    if str(chk_client) != str(var.chk_api) and control.setting('trakt.token') == str(chk_auth):
                        inf.setSetting('traktuserkey.customenabled', 'true')
                        inf.setSetting('trakt.clientid', var.client_am)
                        inf.setSetting('trakt.clientsecret', var.secret_am)
                except Exception:
                    xbmc.log('%s: Infinity API Failed!' % var.amgr, xbmc.LOGINFO)

            # GratisRed - settings-based since 2.0.4 (its file lines are swapped above as well):
            # the settings survive an update of GratisRed and need no restart.
            if xbmcvfs.exists(var.chk_gratisred) and xbmcvfs.exists(var.chkset_gratisred) and _usable('plugin.video.gratisred'):
                try:
                    gratis = xbmcaddon.Addon('plugin.video.gratisred')
                    ours = control.setting('trakt.token')
                    if (ours and ours == str(gratis.getSetting('trakt.token'))
                            and str(gratis.getSetting('trakt.client_id')) != str(var.client_am)):
                        with open(var.path_gratisred, 'r') as f:
                            reads_setting = 'trakt.client_id' in f.read()
                        if reads_setting:
                            gratis.setSetting('trakt.client_id', var.client_am)
                            gratis.setSetting('trakt.client_secret', var.secret_am)
                except Exception:
                    xbmc.log('%s: GratisRed API Failed!' % var.amgr, xbmc.LOGINFO)

        if first_pass:
            _step('key check: first pass done')
            first_pass = False
        if monitor.waitForAbort(10):
            break


def restore_api():
    accountmgr.setSetting('api_restore', 'false')

    for chk, _chkset, path, old_client, old_secret, label in _api_addons():
        if xbmcvfs.exists(chk):
            try:
                with open(path, 'r') as f:
                    data = f.read()
                data = data.replace(old_client, var.client_am).replace(old_secret, var.secret_am)
                with open(path, 'w') as f:
                    f.write(data)
            except Exception:
                xbmc.log('%s: Restore API %s Failed!' % (var.amgr, label), xbmc.LOGINFO)

    # POV - settings-based
    if xbmcvfs.exists(var.chk_pov):
        try:
            pov = xbmcaddon.Addon('plugin.video.pov')
            pov.setSetting('trakt.client_id', var.client_am)
            pov.setSetting('trakt.client_secret', var.secret_am)
        except Exception:
            xbmc.log('%s: Restore API POV Failed!' % var.amgr, xbmc.LOGINFO)

    # Umbrella - settings-based
    if xbmcvfs.exists(var.chk_umb):
        try:
            umb = xbmcaddon.Addon('plugin.video.umbrella')
            umb.setSetting('traktuserkey.customenabled', 'true')
            umb.setSetting('trakt.clientid', var.client_am)
            umb.setSetting('trakt.clientsecret', var.secret_am)
        except Exception:
            xbmc.log('%s: Restore API Umbrella Failed!' % var.amgr, xbmc.LOGINFO)

    # Infinity - settings-based
    if xbmcvfs.exists(var.chk_infinity):
        try:
            inf = xbmcaddon.Addon('plugin.video.infinity')
            inf.setSetting('traktuserkey.customenabled', 'true')
            inf.setSetting('trakt.clientid', var.client_am)
            inf.setSetting('trakt.clientsecret', var.secret_am)
        except Exception:
            xbmc.log('%s: Restore API Infinity Failed!' % var.amgr, xbmc.LOGINFO)


if os.environ.get('REAUTHORIZE_LOCAL_DEBUG') == '1':
    xbmc.log('[ script.module.reauthorize ]  Local debug mode: startup service boot skipped.', LOGINFO)
else:
    # AUTO-RESTORE - recover credentials from cloud or local vault on first boot of a new build,
    # then immediately push them out to every installed addon so nothing needs re-authorizing by hand.
    # Only runs when no credentials are present (new install or builder-wiped build).
    _CRED_KEYS = [
        'trakt.token', 'realdebrid.token', 'premiumize.token', 'alldebrid.token',
        'torbox.token', 'easydebrid.token', 'offcloud.token',
        'linksnappy.username', 'debridlink.token',
        'easynews.username', 'filepursuit.api.key',
        'simkl.token', 'lastfm.session.key',
        'youtube.api.key',
        'fanart.tv.api.key', 'tmdb.api.key', 'mdb.api.key',
    ]
    def _run_auto_restore():
        import embedded as _engine
        with _engine.file_lock(os.path.join(_engine.profile(), 'embedded-recovery.lock')):
            _run_auto_restore_unlocked()

    def _run_auto_restore_unlocked():
        if not any(accountmgr.getSetting(k) for k in vault.CREDENTIAL_KEYS if vault.is_credential_key(k)):
            server.auto_restore()
        vault.restore_missing_keys()  # fill in anything the server backup didn't have
        _sync_settings_display_values()
        _refresh_trakt()  # a restored token may be old; renew before it is pushed out
        _refresh_punchplay()  # a restored PunchPlay token is always old: they last an hour

        # Trakt is a single device-wide login shared by every addon it's pushed to.
        # Ask once per device before auto-linking it; every other service pushes silently.
        include_trakt = True
        if control.setting('trakt.token'):
            consent = control.setting('trakt.auto_push.consent')
            if consent == '':
                answer = dialog.yesno(
                    'ReAuthorize',
                    # The question goes FIRST: some skins show only the first line (MQ9, 2026-10-02).
                    'Send Trakt to your add-ons after a new build?[CR][CR]'
                    'Trakt is one login shared by all your add-ons. You are asked only once.',
                    nolabel='No', yeslabel='Yes')
                control.setSetting('trakt.auto_push.consent', 'true' if answer else 'false')
                include_trakt = answer
            else:
                include_trakt = (consent == 'true')

        try:
            failed = run_all_syncs(include_trakt=include_trakt)  # push restored credentials into every installed addon
            if failed:
                xbmc.log('[ script.module.reauthorize ]  Auto-restore: sync failed for: %s' % ', '.join(failed), LOGINFO)
        except Exception as e:
            xbmc.log('[ script.module.reauthorize ]  Auto-restore: push to addons failed: %s' % e, LOGINFO)

        if include_trakt and accountmgr.getSetting('trakt.token'):
            accountmgr.setSetting('trakt.all_push.done', 'true')  # the push above covered it
            accountmgr.setSetting('api.service', 'true')  # keeps the Trakt keys patched after add-on updates
        vault.backup()
        server.backup()
        xbmc.log('[ script.module.reauthorize ]  Auto-restore complete (new build detected).', LOGINFO)

    # First of all: Kodi shows an EMPTY settings window and saves nothing while it cannot load
    # ReAuthorize's settings file. Set such a file aside before anything reads or writes a
    # setting; the restore below then brings the sign-ins back (settings_health.py, 1.4.3).
    _step('settings file check')
    repaired_addons = []
    try:
        from reauthorize.modules import settings_health
        settings_health.ensure_loadable()
        # The add-ons it sends to fall into the same trap (log 1004): repair theirs too, before
        # anything is sent to them.
        _step('add-on settings file check')
        repaired_addons = settings_health.repair_addons()
    except Exception as e:
        xbmc.log('[ReAuthorize Settings] check failed: %s' % e, xbmc.LOGWARNING)

    _guard_identity()

    if not any(accountmgr.getSetting(k) for k in _CRED_KEYS):
        restore_thread = threading.Thread(target=_run_auto_restore, daemon=True)
        restore_thread.start()
    else:
        xbmc.log('[ script.module.reauthorize ]  Credentials present - auto-restore skipped.', LOGINFO)
        _step('renewal checks')
        _refresh_trakt()
        _refresh_mdblist()
        _refresh_punchplay()
        _step('re-send after a key swap')
        _resend_after_key_swap()
        _step('one-time pushes')
        _push_trakt_once()
        _link_simkl()
        _step('new add-ons')
        _link_new_addons(at_start=True)
        _resend_after_settings_repair(repaired_addons)   # with no sign-ins, the restore's sync does it
        _step('device check (server)')
        _confirm_owner()
        _shared_backup_notice()

    _step('status lines')
    _sync_settings_display_values()

    # YOUTUBE SIGN-IN - keep a copy of the one on this device, or put a stored
    # one back if a build install wiped it. Restoring never overwrites a live
    # sign-in; the one on the device always wins.
    _step('YouTube sign-in copy')
    try:
        from reauthorize.modules.sync import youtube_sync
        if not youtube_sync.capture_tokens():
            youtube_sync.restore_tokens()
    except Exception as e:
        xbmc.log('[ script.module.reauthorize ]  YouTube sign-in check failed: %s' % e, LOGINFO)

    # RESTORE API SERVICE
    if hasattr(var, 'chk_api') and control.setting('api_restore') == 'true':
        restore_api()

    # Embedded ReAuthorize is maintained through Xenon skin updates.
    # Do not query or advertise standalone add-on releases.

    # ACCOUNT EXPIRES NOTIFICATION
    _step('account expiry check')
    PremAccntNotification().run()
    _step('account expiry check done')

    # GENOCIDE TRAKT SYNC
    if control.setting('genocide_traktsync') == 'true':
        genocide_sync()

    # RESET TO DEFAULT SERVICE
    if control.setting('reset_settings') == 'true':
        # Consume the one-shot request before any dialog or reset action can
        # fail. A failed action must not become a prompt on every restart.
        control.setSetting('reset_settings', 'false')
        yes = dialog.yesno('ReAuthorize', 'Choose proceed to remove all settings applied by ReAuthorize or cancel to quit.', 'Cancel', 'Proceed')
        if yes:
            try:
                xbmc.executebuiltin('PlayMedia(plugin://script.module.reauthorize-core/?mode=wipeclean&name=all)')
            except Exception as exc:
                xbmc.log('[ReAuthorize Reset] Pending reset failed: ' + type(exc).__name__, xbmc.LOGERROR)
                dialog.ok('ReAuthorize', 'The reset could not finish. The pending request has been cleared. Check kodi.log before retrying the reset manually.')
        if not yes and control.setting('trakt.token') != '':
            control.setSetting('api.service', 'true')

    # RUN API CHECK SERVICE
    if hasattr(var, 'chk_api') and control.setting('api.service') == 'true' and control.setting('trakt.token') != '':
        _step('add-on key check (first 5 minutes)')
        check_api()

    # Then stay up and keep the sign-ins renewed. Trakt's tokens last 7 days now, so a Kodi
    # left running for a week used to outlive its token and leave the add-ons to scramble
    # for it themselves (each renewal kills the other copies).
    _step('start-up finished; staying up for renewals and new add-ons')
    _keep_signed_in()
