# -*- coding: utf-8 -*-

'''
    Auth Station
'''

import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
from reauthorize.modules import control

joinPath = os.path.join
dialog = xbmcgui.Dialog()
addon = xbmcaddon.Addon
addonObject = addon('script.module.authorizediggz')
addonInfo = addonObject.getAddonInfo
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
accountmgr = control.accountmgr

_ICON_DIR       = os.path.join(addonInfo('path'), 'resources', 'icons')
amgr_icon       = addonInfo('icon')
rd_icon         = joinPath(_ICON_DIR, 'realdebrid.png')
pm_icon         = joinPath(_ICON_DIR, 'premiumize.png')
ad_icon         = joinPath(_ICON_DIR, 'alldebrid.png')
trakt_icon      = joinPath(_ICON_DIR, 'trakt.png')
tmdb_icon       = joinPath(_ICON_DIR, 'tmdb.png')
torbox_icon     = joinPath(_ICON_DIR, 'torbox.png')
easyd_icon      = joinPath(_ICON_DIR, 'easydebrid.png')
offcloud_icon   = joinPath(_ICON_DIR, 'offcloud.png')
easy_icon       = joinPath(_ICON_DIR, 'easynews.png')
file_icon       = joinPath(_ICON_DIR, 'filepursuit.png')
simkl_icon      = joinPath(_ICON_DIR, 'simkl.png')
lastfm_icon     = joinPath(_ICON_DIR, 'lastfm.png')
youtube_icon    = joinPath(_ICON_DIR, 'youtube.png')
linksnappy_icon = joinPath(_ICON_DIR, 'linksnappy.png')
debridlink_icon = joinPath(_ICON_DIR, 'debridlink.png')

_DATE_MAP = {
    'trakt':       'tk_backup_date',
    'realdebrid':  'rd_backup_date',
    'premiumize':  'pm_backup_date',
    'alldebrid':   'ad_backup_date',
    'torbox':      'tb_backup_date',
    'easydebrid':  'ed_backup_date',
    'offcloud':    'oc_backup_date',
    'easynews':    'en_backup_date',
    'filepursuit': 'fp_backup_date',
    'meta':        'md_backup_date',
}

def notification(title=None, message=None, icon=None, time=3000, sound=False):
    if title == 'default' or title is None: title = addonName()
    if isinstance(title, int): heading = lang(title)
    else: heading = str(title)
    if isinstance(message, int): body = lang(message)
    else: body = str(message)
    if icon is None or icon == '' or icon == 'default': icon = addonIcon()
    elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
    dialog.notification(heading, body, icon, time, sound=sound)

def addonIcon():
    return addonInfo('icon')

def addonName():
    return addonInfo('name')

# Actions that already ran a full backup/sync themselves, or that never changed a
# credential (view-only dialogs, help text, log tools) - no reminder needed for these.
_NO_REMINDER_ACTIONS = {
    'openSettings', 'statusDashboard',
    'traktAcct', 'realdebridAcct', 'premiumizeAcct', 'alldebridAcct', 'simklAcct', 'lastfmAcct', 'punchplayAcct',
    'ShowChangelog', 'ShowHelp', 'ShowHelpTMDb', 'ShowHelpMeta', 'ShowHelpRestore',
    'ShowHelpIssues', 'ShowCompatibleAddons', 'ShowOKDialog', 'storageReport', 'sendLog',
    'tools_clearLogFile', 'tools_viewLogFile', 'tools_uploadLogFile', 'resetSettings',
    'vaultBackup', 'vaultRestore', 'vaultClear', 'serverBackup', 'serverRestore', 'serverClear',
    'backupAll', 'backupService', 'restoreService', 'deviceReset', 'prepareDistribution',
    'readMeFirst', 'silentReAuthorize', 'quickAuthorize',
    'youtubeSignIn', 'youtubeSignOut',
}

def _backup_if_signins_changed():
    """
    Back up by itself when this action changed a sign-in (modules/autosave.py). This replaced a
    reminder to press "Save & Backup Now" that was shown after nearly every action, changed or
    not. The actions in _NO_REMINDER_ACTIONS manage the backups themselves and are left alone.
    """
    if not action or action in _NO_REMINDER_ACTIONS:
        return
    try:
        from reauthorize.modules import autosave
        note = autosave.save_if_changed(_signins_at_start)
        if note:
            notification('Diggz Account Manager', note, icon=amgr_icon, time=4000)
            xbmc.sleep(1500)
    except Exception as e:
        xbmc.log('[Diggz Account Manager] automatic backup failed: %s' % e, xbmc.LOGINFO)


def _send_new_signin():
    """
    A sign-in just made is sent to the add-ons by itself (modules/autosend.py, 1.4.1). Until then
    these buttons only saved it, and the add-ons had nothing until "Sync Add-ons" was pressed.
    """
    try:
        from reauthorize.modules import autosend
        sent = autosend.send_if_changed(
            action, _signins_at_start,
            notify=lambda label: notification('Diggz Account Manager', 'Sending %s to your add-ons...' % label, icon=amgr_icon))
        if sent and getattr(sent[1], 'has_issues', bool(sent[1])):
            _show_sync_result(sent[1], amgr_icon)
    except Exception as e:
        xbmc.log('[Diggz Account Manager] sending the new sign-in failed: %s' % e, xbmc.LOGINFO)


def _reload_and_open_settings(query=None):
    from reauthorize.modules import settings_display
    settings_display.sync_authorized_display_values()
    from reauthorize.modules import sync_support
    sync_support.after_action(action, _signins_at_start)
    _send_new_signin()
    _backup_if_signins_changed()
    xbmc.sleep(500)
    control.openSettings(query, 'script.module.authorizediggz')

from reauthorize.modules.sync_all import run_all_syncs as _run_all_syncs, META_KEYS as _META_KEYS, show_result as _show_sync_result

# What the backup set holds as this action starts; _backup_if_signins_changed() compares against it.
try:
    from reauthorize.modules import autosave as _autosave
    _signins_at_start = _autosave.snapshot()
except Exception:
    _signins_at_start = None

def _run_meta_sync():
    if any(control.setting(k) for k in _META_KEYS):
        _show_sync_result(_run_all_syncs(include_trakt=False, only=('meta',)), amgr_icon)
    else:
        notification('Diggz Account Manager', 'No Meta Data to Sync!', icon=amgr_icon)
    _reload_and_open_settings()

def _sync_restored_credentials():
    """Explicit restore already has user consent; retain the existing Trakt auto-link choice."""
    from startup import _refresh_trakt, _refresh_mdblist, _refresh_simkl, _refresh_punchplay
    include_trakt = control.setting('trakt.auto_push.consent') != 'false'
    if include_trakt:
        _refresh_trakt()
    _refresh_mdblist()
    _refresh_simkl()
    _refresh_punchplay()
    _show_sync_result(_run_all_syncs(include_trakt=include_trakt, portal_explicit=False), amgr_icon)


control.set_active_monitor()

params = {}
for param in sys.argv[1:]:
    # RunScript(addon, action=X&mode=Y) has no comma, so Kodi passes the whole
    # thing as one sys.argv element - splitting only on '=' left 'mode' folded
    # into action's own value ('X&mode=Y'), matching no elif branch below.
    # Every serviceRevoke/backupService/restoreService row
    # depends on this second param; split each element on '&' first.
    for piece in param.split('&'):
        if '=' in piece:
            key, _, value = piece.partition('=')
            params[key] = value

_NO_DIALOG = (-1, 9999)  # 9999 = WINDOW_INVALID, Kodi's own "no dialog" sentinel

def _wait_for_modal_close(timeout=2.0, interval=0.05):
    # The settings row's own option="close" only closes the settings dialog
    # (10140) itself. Diagnostic logging on a real box (2026-09-29) showed that
    # waiting for *that* dialog to clear isn't the real fix: when ReAuthorize
    # is opened via the addon info page's "Configure" button, the Addon Info
    # dialog (10146 - confirmed against Kodi's own WindowIDs.h) is still open
    # underneath and becomes the new active dialog the instant settings closes.
    # It's not mid-animation, it's just still there, so no amount of waiting
    # helps; force-close every dialog instead of guessing which one to wait
    # for. A second live test showed Dialog.Close(all,true) clears this
    # instantly but getCurrentWindowDialogId() then reports 9999, not -1, so
    # checking only for -1 burned the full timeout on every single use.
    xbmc.executebuiltin('Dialog.Close(all,true)')
    monitor = xbmc.Monitor()
    waited = 0.0
    dialog_id = xbmcgui.getCurrentWindowDialogId()
    while dialog_id not in _NO_DIALOG and waited < timeout:
        if monitor.waitForAbort(interval):
            return
        waited += interval
        dialog_id = xbmcgui.getCurrentWindowDialogId()
    if dialog_id not in _NO_DIALOG:
        xbmc.log('Diggz Account Manager: still blocked by dialog id=%d after force-close + %.2fs wait' % (dialog_id, waited), xbmc.LOGINFO)

action = params.get('action')
query = params.get('query')
addon_id = params.get('addon_id')

if action and not any(i in action for i in ['Auth', 'Revoke']):
    control.release_active_monitor()

# Every settings row closes the settings dialog and then starts this script, while
# that dialog is still animating shut (or, via Configure, with the Addon Info dialog
# still underneath). On skins with a slower close (Confluence/Xonfluence) the account
# dialog, status window or re-opened settings then collide with it: the row "just
# exits settings" or settings comes back blank. Clear the stack first, once, for all
# actions; serviceRevoke does its own below.
if action and action != 'serviceRevoke':
    _wait_for_modal_close()

if action is None:
    # After a reset (reset.py, removed in 1.3.6), say once what to do next.
    try:
        from reauthorize.modules import reset
        reset.show_followup()
    except Exception as e:
        xbmc.log('[Diggz Account Manager] reset follow-up failed: %s' % e, xbmc.LOGERROR)
    # Opening ReAuthorize: first check whether the user already signed into
    # anything inside their addons. Quiet unless there is something new.
    try:
        from reauthorize.modules import importer
        importer.run(explicit=False)
    except Exception as e:
        xbmc.log('[Diggz Account Manager] sign-in check failed: %s' % e, xbmc.LOGERROR)
    _reload_and_open_settings()

elif action == 'findSignins':
    from reauthorize.modules import importer
    importer.run(explicit=True)
    _reload_and_open_settings()

elif action == 'openSettings':
    _reload_and_open_settings(query)

elif action in ('statusDashboard', 'viewAuthorizations'):
    from reauthorize.windows.status import open_status
    open_status()
    _reload_and_open_settings()

elif action == 'traktAcct':
    from reauthorize.modules.auth import trakt
    trakt.Trakt().account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'trackingPreference':
    from reauthorize.modules import tracking_preference
    tracking_preference.choose_and_apply()
    _reload_and_open_settings()

elif action == 'traktAuth':
    from reauthorize.modules.auth import trakt
    result = trakt.Trakt().auth()
    if result:
        # Signing in is only half of it: send Trakt to every installed add-on now,
        # so the user is not left holding a login that nothing is using.
        from reauthorize.modules.sync import trakt_sync, trakt_select
        notification('Diggz Account Manager', 'Sending Trakt to your add-ons...', icon=trakt_icon)
        result = _run_all_syncs(only=('trakt',))
        if result.has_issues:
            _show_sync_result(result, trakt_icon)
        targets = trakt_select.installed_addons()
        control.setSetting('trakt.all_push.done', 'true' if not result else '')
        control.setSetting('sync.tk.service', 'true' if targets and not result else 'false')
        if targets:
            accountmgr.setSetting('api.service', 'true')
        from reauthorize.modules import vault, server
        vault.backup()
        server.backup()
        xbmc.sleep(1000)
        if targets:
            restart = xbmcgui.Dialog().yesno(
                'Diggz Account Manager',
                'Trakt linked; %d installed add-on%s considered for synchronization.[CR][CR]Restart Kodi to load any changed keys.[CR][CR]Restart now, or finish setting up other services first?' 
                % (len(targets), '' if len(targets) == 1 else 's'),
                nolabel='Later', yeslabel='Restart Now')
            if restart:
                os._exit(1)
        else:
            xbmcgui.Dialog().ok(
                'Diggz Account Manager',
                'Trakt linked![CR][CR]No add-ons that use Trakt are installed yet. Install one, then press "Sync Add-ons" on this tab.')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'traktReSync':
    from reauthorize.modules.sync import trakt_sync
    from reauthorize.modules import restart_hint
    notification('Diggz Account Manager', 'Sync in progress, please wait!', icon=trakt_icon)
    xbmc.sleep(3000)
    key_files_before = restart_hint.key_files()
    _show_sync_result(_run_all_syncs(only=('trakt',)), trakt_icon)
    accountmgr.setSetting("api.service", "true")
    # An add-on whose key file was just swapped only reads it when Kodi starts.
    if control.setting('trakt.token') and restart_hint.ask(key_files_before):
        os._exit(1)
    _reload_and_open_settings()

elif action == 'realdebridAcct':
    from reauthorize.modules.auth import realdebrid
    realdebrid.RealDebrid().account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'realdebridAuth':
    from reauthorize.modules.auth import realdebrid
    realdebrid.RealDebrid().auth()
    if control.setting('realdebrid.token'):
        control.setSetting('sync.rd.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'realdebridReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('rd',)), rd_icon)
    _reload_and_open_settings()

elif action == 'realdebridRevoke':
    from reauthorize.modules.auth import realdebrid
    realdebrid.RealDebrid().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'premiumizeAcct':
    from reauthorize.modules.auth import premiumize
    premiumize.Premiumize().account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'premiumizeAuth':
    from reauthorize.modules.auth import premiumize
    premiumize.Premiumize().auth()
    if control.setting('premiumize.token'):
        control.setSetting('sync.pm.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'premiumizeReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('pm',)), pm_icon)
    _reload_and_open_settings()

elif action == 'premiumizeRevoke':
    from reauthorize.modules.auth import premiumize
    premiumize.Premiumize().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'alldebridAcct':
    from reauthorize.modules.auth import alldebrid
    alldebrid.AllDebrid().account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'alldebridAuth':
    from reauthorize.modules.auth import alldebrid
    alldebrid.AllDebrid().auth()
    if control.setting('alldebrid.token'):
        control.setSetting('sync.ad.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'alldebridReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('ad',)), ad_icon)
    _reload_and_open_settings()

elif action == 'alldebridRevoke':
    from reauthorize.modules.auth import alldebrid
    alldebrid.AllDebrid().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'torboxAuth':
    from reauthorize.modules.auth import torbox
    torbox.Torbox().auth()
    if control.setting('torbox.token'):
        control.setSetting('sync.torbox.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'torboxRevoke':
    from reauthorize.modules.auth import torbox
    torbox.Torbox().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'torboxReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('torbox',)), torbox_icon)
    _reload_and_open_settings()

elif action == 'easydebridAuth':
    from reauthorize.modules.auth import easydebrid
    easydebrid.Easydebrid().auth()
    if control.setting('easydebrid.token'):
        control.setSetting('sync.easyd.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'easydebridRevoke':
    from reauthorize.modules.auth import easydebrid
    easydebrid.Easydebrid().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'easydebridReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('easyd',)), easyd_icon)
    _reload_and_open_settings()

elif action == 'offcloudAuth':
    from reauthorize.modules.auth import offcloud
    offcloud.Offcloud().auth()
    if control.setting('offcloud.token'):
        control.setSetting('sync.offc.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'offcloudRevoke':
    from reauthorize.modules.auth import offcloud
    offcloud.Offcloud().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'offcloudReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('offc',)), offcloud_icon)
    _reload_and_open_settings()

elif action == 'easynewsAuth':
    from reauthorize.modules.auth import easynews
    easynews.Easynews().auth()
    if control.setting('easynews.username') and control.setting('easynews.password'):
        control.setSetting('sync.easy.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'easynewsReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('easy',)), easy_icon)
    _reload_and_open_settings()

elif action == 'filepursuitAuth':
    from reauthorize.modules.auth import filepursuit
    filepursuit.Filepursuit().auth()
    if control.setting('filepursuit.api.key'):
        control.setSetting('sync.filep.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'filepursuitReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('filep',)), file_icon)
    _reload_and_open_settings()

elif action == 'linksnappyAuth':
    from reauthorize.modules.auth import linksnappy
    linksnappy.Linksnappy().auth()
    if control.setting('linksnappy.username'):
        control.setSetting('sync.linksnappy.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'linksnappyRevoke':
    from reauthorize.modules.auth import linksnappy
    linksnappy.Linksnappy().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'linksnappyReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('linksnappy',)), linksnappy_icon)
    _reload_and_open_settings()

elif action == 'debridlinkAuth':
    from reauthorize.modules.auth import debridlink
    debridlink.Debridlink().auth()
    if control.setting('debridlink.token'):
        control.setSetting('sync.debridlink.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'debridlinkRevoke':
    from reauthorize.modules.auth import debridlink
    debridlink.Debridlink().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'debridlinkReSync':
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('debridlink',)), debridlink_icon)
    _reload_and_open_settings()

elif action == 'tmdbAuth':
    from reauthorize.modules.auth import tmdb
    tmdb.Auth().create_session_id()
    if control.setting('tmdb.api.key') or control.setting('tmdb.session_id') or control.setting('tmdb.authorization'):
        control.setSetting('sync.meta.service', 'true')
    xbmc.sleep(2000)
    _reload_and_open_settings()

elif action == 'tmdbSync':
    from reauthorize.modules.sync_all import run_all_syncs
    _show_sync_result(run_all_syncs(include_trakt=False, only=('meta',)), tmdb_icon)
    _reload_and_open_settings()

elif action == 'tmdbRevoke':
    from reauthorize.modules.auth import tmdb
    tmdb.Auth().revoke_session_id()
    _reload_and_open_settings()

elif action == 'fanartAuth':
    from reauthorize.modules.auth import fanart
    fanart.Fanart().auth()
    if control.setting('fanart.tv.api.key'):
        control.setSetting('sync.meta.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'fanartRevoke':
    from reauthorize.modules.auth import fanart
    fanart.Fanart().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'torrentclawAuth':
    from reauthorize.modules.auth import torrentclaw
    torrentclaw.TorrentClaw().auth()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'torrentclawRevoke':
    from reauthorize.modules.auth import torrentclaw
    torrentclaw.TorrentClaw().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'audiodbAuth':
    from reauthorize.modules.auth import audiodb
    audiodb.AudioDB().auth()
    if control.setting('audiodb.api.key'):
        control.setSetting('sync.meta.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'audiodbRevoke':
    from reauthorize.modules.auth import audiodb
    audiodb.AudioDB().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action in ('tvdbSync', 'tvdbRevoke'):
    from reauthorize.modules import tmdbh_compat
    if action == 'tvdbRevoke':
        control.setSetting('tvdb.api.key', '')
    tmdbh_compat.sync_tvdb(control.setting('tvdb.api.key'), wipe=action == 'tvdbRevoke')
    if control.setting('tvdb.api.key'):
        control.setSetting('sync.meta.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'omdbAuth':
    from reauthorize.modules.auth import omdb
    omdb.OMDb().auth()
    if control.setting('omdb.api.key'):
        control.setSetting('sync.meta.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'omdbRevoke':
    from reauthorize.modules.auth import omdb
    omdb.OMDb().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'imdbAuth':
    from reauthorize.modules.auth import imdb
    imdb.IMDb().auth()
    if control.setting('imdb.user'):
        control.setSetting('sync.meta.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'imdbRevoke':
    from reauthorize.modules.auth import imdb
    imdb.IMDb().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'serviceRevoke':
    # This row used to only fire router.py's legacy 'addon<svc>' mode, which
    # wipes a fixed ~21-addon list in reauthorize-core's debridit_*.py that
    # predates most addons this project has wired since (Prism, Diamond Media
    # Player, TMDb Movies, Youtube Theater, and more) -- confirmed live,
    # 2026-09-29: Prism kept a dead Premiumize token straight through a Revoke
    # click. Now: clear ReAuthorize's own copy the same way the standalone
    # {service}Revoke actions elsewhere in this file already do, then push
    # that blank out through every currently-wired addon via the same wipe
    # mechanism the shared-backup notice already uses. torbox/easydebrid/
    # offcloud's revoke() asks for confirmation first and does nothing if
    # declined, so the wipe only fires once the setting is actually blank --
    # otherwise a cancelled confirmation would still wipe the addons.
    # Trakt's 'addontrakt' route is untouched below -- it un-patches
    # source-patched client keys, a different job, already kept current per
    # AGENTS.md's "both revoke routes" instruction.
    mode = params.get('mode', '')
    # FIRST, before any popup: let the settings dialog this row was pressed in finish closing.
    # Kodi writes that dialog's settings to disk once more when its window loop ends, and the
    # loop cannot end while another dialog (the "signed out" popup, the settings reopened below)
    # has been opened inside it. It then ends only when THAT dialog closes, and writes the
    # values the old dialog was opened with: the sign-in just revoked comes back. Seen on the
    # bench 2026-10-13: Premiumize revoked at 07:19:38, blank on disk, and back at 07:20:21, the
    # moment the reopened settings were left, with no add-on holding it. Every other action gets
    # this from the call near the top of this file; this one was left out of it when it still
    # only handed over to core (which waited itself), and the branches rewritten since never did.
    _wait_for_modal_close()
    if mode == 'addondebrid_rd':
        from reauthorize.modules.auth import realdebrid
        realdebrid.RealDebrid().revoke()
        if not control.setting('realdebrid.token'):
            _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'rd'}, only=('rd',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addondebrid_pm':
        from reauthorize.modules.auth import premiumize
        premiumize.Premiumize().revoke()
        if not control.setting('premiumize.token'):
            _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'pm'}, only=('pm',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addondebrid_ad':
        from reauthorize.modules.auth import alldebrid
        alldebrid.AllDebrid().revoke()
        if not control.setting('alldebrid.token'):
            _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'ad'}, only=('ad',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addontb':
        from reauthorize.modules.auth import torbox
        torbox.Torbox().revoke()
        if not control.setting('torbox.token'):
            _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'torbox'}, only=('torbox',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addoned':
        from reauthorize.modules.auth import easydebrid
        easydebrid.Easydebrid().revoke()
        if not control.setting('easydebrid.token'):
            _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'easyd'}, only=('easyd',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addonoffc':
        from reauthorize.modules.auth import offcloud
        offcloud.Offcloud().revoke()
        if not control.setting('offcloud.token'):
            _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'offc'}, only=('offc',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addoneasy':
        control.setSetting('easynews.username', '')
        control.setSetting('easynews.password', '')
        _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'easy'}, only=('easy',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addonfile':
        control.setSetting('filepursuit.api.key', '')
        _show_sync_result(_run_all_syncs(include_trakt=False, wipe={'filep'}, only=('filep',)), amgr_icon)
        control.release_active_monitor()
        _reload_and_open_settings()
    elif mode == 'addontrakt':
        # Sign ReAuthorize itself out too (it used to stay signed in, with Authorize hidden),
        # then let core give the add-ons their own Trakt keys back, as before.
        from reauthorize.modules.auth import trakt
        trakt.Trakt().sign_out_everywhere()
        control.release_active_monitor()
        _wait_for_modal_close()
        xbmc.executebuiltin('PlayMedia(plugin://script.module.authorizediggz-core/?mode=addontrakt&name=all)')
    elif mode:
        # Trakt's addontrakt (and anything else not covered above) keeps going
        # through router.py directly; wait for settings to finish closing.
        _wait_for_modal_close()
        xbmc.executebuiltin('PlayMedia(plugin://script.module.authorizediggz-core/?mode=%s&name=all)' % mode)

elif action == 'mdblistOAuthAuth':
    # The one MDBList button (1.4.0): the account sign-in, then the API key if the user wants it.
    from reauthorize.modules.auth import mdblist_oauth
    mdblist_oauth.sign_in()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'mdblistOAuthReSync':
    if control.setting('mdblist.oauth.token') or control.setting('mdb.api.key'):
        _show_sync_result(_run_all_syncs(include_trakt=False, only=('mdbo', 'meta')), amgr_icon)
    else:
        notification('Diggz Account Manager', 'Authorize MDBList first.', icon=amgr_icon)
    _reload_and_open_settings()

elif action == 'mdblistOAuthRevoke':
    from reauthorize.modules.auth import mdblist_oauth
    mdblist_oauth.sign_out()
    _reload_and_open_settings()

elif action == 'punchplayAuth':
    # Sends to the add-ons itself; the automatic backup follows as the settings reopen.
    from reauthorize.modules.auth import punchplay
    punchplay.sign_in()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'punchplayAcct':
    from reauthorize.modules.auth import punchplay
    punchplay.account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'punchplayReSync':
    from reauthorize.modules.auth import punchplay
    from reauthorize.modules.sync import punchplay_sync
    if punchplay.signed_in() and punchplay.seconds_left() < 120:
        punchplay.refresh_if_due(force=True)        # a token that has run out is no use to an add-on
    punchplay_sync.push(force=True)
    held = len(punchplay_sync.holding())
    if held:
        notification('Diggz Account Manager', 'PunchPlay sent to %d add-on%s.' % (held, '' if held == 1 else 's'), icon=amgr_icon)
    else:
        notification('Diggz Account Manager', 'No PunchPlay add-on to send it to.', icon=amgr_icon)
    _reload_and_open_settings()

elif action == 'punchplayRevoke':
    from reauthorize.modules.auth import punchplay
    punchplay.sign_out()
    _reload_and_open_settings()

elif action == 'mdblistAuth':
    from reauthorize.modules.auth import mdblist
    mdblist.MDBListAuth().authorize()
    if control.setting('mdb.api.key'):
        control.setSetting('sync.meta.service', 'true')
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'mdblistRevoke':
    from reauthorize.modules.auth import mdblist
    mdblist.MDBListAuth().revoke()
    control.release_active_monitor()
    _reload_and_open_settings()

elif action == 'simklAcct':
    from reauthorize.modules.auth import simkl
    simkl.Simkl().account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'simklAuth':
    from reauthorize.modules.auth import simkl
    # Waiting for Kodi's native addonsettings window here never completes.
    try:
        simkl_authorized = simkl.Simkl().auth()
    finally:
        control.release_active_monitor()
    if simkl_authorized and control.setting('simkl.token'):
        from reauthorize.modules.sync import simkl_sync
        from reauthorize.modules import restart_hint
        notification('Diggz Account Manager', 'Simkl sync in progress...', icon=simkl_icon)
        key_files_before = restart_hint.key_files()
        result = _run_all_syncs(include_trakt=False, only=('simkl',))
        control.setSetting('simkl.all_push.done', 'true' if not result else '')
        _show_sync_result(result, simkl_icon)
        if restart_hint.pending() or restart_hint.key_files() != key_files_before:
            _backup_if_signins_changed()          # "Restart Now" leaves before the settings reopen
        if restart_hint.ask(key_files_before):
            os._exit(1)
    _reload_and_open_settings()

elif action == 'simklRevoke':
    from reauthorize.modules.auth import simkl
    # Waiting for Kodi's native addonsettings window here never completes.
    try:
        simkl.Simkl().revoke()
    finally:
        control.release_active_monitor()
    # Take it out of the add-ons too, and give them their own Simkl app key back. Until 1.3.9
    # a Simkl Revoke only cleared ReAuthorize's copy and every add-on kept the sign-in.
    if not control.setting('simkl.token'):
        from reauthorize.modules.sync import simkl_sync
        simkl_sync.sign_out_addons()
    _reload_and_open_settings()

elif action == 'simklReSync':
    from reauthorize.modules.sync import simkl_sync
    from reauthorize.modules import restart_hint
    notification('Diggz Account Manager', 'Simkl sync in progress...', icon=simkl_icon)
    key_files_before = restart_hint.key_files()
    _show_sync_result(_run_all_syncs(include_trakt=False, only=('simkl',)), simkl_icon)
    if control.setting('simkl.token') and restart_hint.ask(key_files_before):
        os._exit(1)
    _reload_and_open_settings()

elif action == 'youtubeReSync':
    if control.setting('youtube.api.key') and control.setting('youtube.api.id') and control.setting('youtube.api.secret'):
        notification('Diggz Account Manager', 'YouTube sync in progress...', icon=youtube_icon)
        from reauthorize.modules.sync import youtube_sync
        _show_sync_result(_run_all_syncs(include_trakt=False, only=('yt',)), youtube_icon)
    else:
        notification('Diggz Account Manager', 'YouTube: Enter all three API credentials first.', icon=youtube_icon)
    _reload_and_open_settings()

elif action == 'youtubeSignIn':
    from reauthorize.modules.sync import youtube_sync
    if not (control.setting('youtube.api.key') and control.setting('youtube.api.id') and control.setting('youtube.api.secret')):
        notification('Diggz Account Manager', 'YouTube: enter all three API keys first (step 1).', icon=youtube_icon)
    elif not youtube_sync.is_installed():
        notification('Diggz Account Manager', 'YouTube for Kodi is not installed.', icon=youtube_icon)
    elif xbmcgui.Dialog().yesno(
            'Diggz Account Manager',
            'YouTube will show up to 3 codes, one after another.[CR][CR]'
            'On your phone or computer: the first code goes in at youtube.com/activate, the next ones at google.com/device. '
            'Approve every one with the account you use for YouTube; wait for each new code. '
            'This lets you see your own subscriptions, playlists and Watch Later. Diggz Account Manager never sees your password.',
            nolabel='Cancel', yeslabel='Continue'):
        # A sign-in only works with the keys it was issued against, so YouTube for
        # Kodi gets them first, then its own sign-in takes over.
        youtube_sync.Auth().youtube_auth()
        control.setSetting('sync.yt.service', 'true')
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.youtube/sign/in/)')
        # The sign-in is several codes in a row, done outside this script. Follow
        # along, so it is saved with the backup without the user having to remember.
        if youtube_sync.wait_for_signin(minutes=8):
            from reauthorize.modules import vault, server
            vault.backup()
            server.backup()
            notification('Diggz Account Manager', 'YouTube sign-in saved with your backup.', icon=youtube_icon)
    _reload_and_open_settings()

elif action == 'youtubeSignOut':
    from reauthorize.modules.sync import youtube_sync
    # YouTube for Kodi asks its own "sign out?" question. Only once it really is
    # signed out is ReAuthorize's saved copy dropped too; otherwise the next start
    # would find YouTube signed out and put the old sign-in straight back.
    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.youtube/sign/out/)')
    monitor = xbmc.Monitor()
    for _ in range(20):
        if monitor.waitForAbort(1.5) or not youtube_sync.signed_in():
            break
    if not youtube_sync.signed_in():
        youtube_sync.forget_saved_signin()
        notification('Diggz Account Manager', 'YouTube: signed out.', icon=youtube_icon)
    _reload_and_open_settings()

elif action == 'lastfmAcct':
    from reauthorize.modules.auth import lastfm
    lastfm.LastFM().account_info_to_dialog()
    _reload_and_open_settings()

elif action == 'lastfmAuth':
    from reauthorize.modules.auth import lastfm
    lastfm.LastFM().auth()                     # 1.4.1: username + password, sent to the Scrobbler itself
    _reload_and_open_settings()

elif action == 'lastfmReSync':
    if control.setting('lastfm.password') or control.setting('lastfm.session.key'):
        notification('Diggz Account Manager', 'Last.fm sync in progress...', icon=lastfm_icon)
        from reauthorize.modules.sync import lastfm_sync
        lastfm_sync.Auth().lastfm_auth()
        control.setSetting('sync.lastfm.service', 'true')
        notification('Diggz Account Manager', 'Last.fm sync complete!', icon=lastfm_icon)
    else:
        notification('Diggz Account Manager', 'Last.fm: Authorize first before syncing.', icon=lastfm_icon)
    _reload_and_open_settings()

elif action == 'lastfmRevoke':
    from reauthorize.modules.auth import lastfm
    lastfm.LastFM().revoke()
    control.setSetting('sync.lastfm.service', 'false')
    _reload_and_open_settings()

elif action == 'metaReSync':
    _run_meta_sync()

elif action == 'ReSyncAll':
    failed = _run_all_syncs()
    _show_sync_result(failed, amgr_icon)
    _reload_and_open_settings()

elif action == 'ShowChangelog':
    from reauthorize.modules import changelog
    changelog.get()
    _reload_and_open_settings()

elif action == 'ShowHelp':
    from reauthorize.help import help
    help.get(params.get('name'))

elif action == 'ShowHelpTMDb':
    from reauthorize.help import help
    help.get_tmdb()
    _reload_and_open_settings()

elif action == 'ShowHelpMeta':
    from reauthorize.help import help
    help.get_meta()
    _reload_and_open_settings()

elif action == 'ShowHelpRestore':
    from reauthorize.help import help
    help.get_restore()
    _reload_and_open_settings()

elif action == 'ShowHelpIssues':
    from reauthorize.help import help
    help.get_issues()
    _reload_and_open_settings()

elif action == 'ShowCompatibleAddons':
    from reauthorize.help import help
    help.get_compatible()
    _reload_and_open_settings()

elif action == 'storageReport':
    from reauthorize.modules import storage
    from reauthorize.help import help
    # ReAuthorize's own viewer, as Help uses: it scrolls with the remote on every
    # skin. Kodi's built-in one only scrolls where the skin allows it.
    help._show_text('Diggz Account Manager - Storage Report', storage.diagnostic_report())
    _reload_and_open_settings()

elif action == 'sendLog':
    dialog.ok('Diggz Account Manager', 'Log uploading has been removed from this embedded version.')

elif action == 'ShowOKDialog':
    control.okDialog(params.get('title', 'default'), int(params.get('message', '')))

elif action == 'tools_clearLogFile':
    from reauthorize.modules import log_utils
    cleared = log_utils.clear_logFile()
    if cleared == 'canceled': pass
    elif cleared: control.notification(message='Auth Station Log File Successfully Cleared')
    else: control.notification(message='Error clearing Auth Station Log File, see kodi.log for more info')

elif action == 'tools_viewLogFile':
    from reauthorize.modules import log_utils
    log_utils.view_LogFile(params.get('name'))

elif action == 'tools_uploadLogFile':
    dialog.ok('Diggz Account Manager', 'Log uploading has been removed from this embedded version.')

elif action == 'resetSettings':
    xbmc.sleep(500)
    yes = dialog.yesno('Diggz Account Manager', 'WARNING! This will completely wipe all your saved data and remove all settings applied to add-ons via Auth Station. Click proceed to continue or cancel to quit.', 'Cancel', 'Proceed')
    if yes:
        control.setSetting("api.service", "false")
        control.setSetting('reset_settings', 'true')
        # Back or the X means "not yet": the removal is offered at the next start either way.
        if xbmcgui.Dialog().yesno('Diggz Account Manager', 'Close Kodi now to start the removal?[CR][CR]You will be asked at the next '
                                  'Kodi start before anything is removed.', nolabel='Not yet', yeslabel='Close Kodi'):
            os._exit(1)

elif action == 'vaultBackup':
    from reauthorize.modules import vault
    # vault.backup() stamps vault.last_backup itself, and only once the file is
    # genuinely written - don't stamp a date here on top of it.
    if vault.backup():
        warning = vault.warning_message()
        notification('Diggz Account Manager', warning or 'Vault: Credentials backed up successfully.',
                     time=6000 if warning else 3000)
    else:
        notification('Diggz Account Manager', 'Vault: %s' % vault.failure_message(), time=6000)
    _reload_and_open_settings()

elif action == 'vaultRestore':
    from reauthorize.modules import vault
    xbmc.sleep(500)
    if not vault.vault_has_data():
        notification('Diggz Account Manager', 'Vault: No backup found.')
    else:
        yes = dialog.yesno('Diggz Account Manager', 'Restore credentials from vault and sync them to your linked add-ons? This will overwrite your current settings.', 'Cancel', 'Restore')
        if yes:
            if vault.restore():
                notification('Diggz Account Manager', 'Vault: Credentials restored.')
                _sync_restored_credentials()
            else:
                notification('Diggz Account Manager', 'Vault: Restore failed. See kodi.log.')
    _reload_and_open_settings()

elif action == 'vaultClear':
    from reauthorize.modules import vault
    xbmc.sleep(500)
    yes = dialog.yesno('Diggz Account Manager', 'Clear the credential vault? Your authorizations in Kodi will NOT be removed - only the vault backup.', 'Cancel', 'Clear')
    if yes:
        vault.clear()
        notification('Diggz Account Manager', 'Vault: Backup cleared.')
    _reload_and_open_settings()

elif action == 'serverBackup':
    from reauthorize.modules import server
    if server.backup(): notification('Diggz Account Manager', 'Server: Credentials backed up.')
    else: notification('Diggz Account Manager', 'Server: Backup failed or nothing to back up.')
    _reload_and_open_settings()

elif action == 'serverRestore':
    from reauthorize.modules import server
    xbmc.sleep(500)
    yes = dialog.yesno('Diggz Account Manager', 'Restore credentials from server and sync them to your linked add-ons? This will overwrite your current settings.', 'Cancel', 'Restore')
    if yes:
        if server.restore():
            notification('Diggz Account Manager', 'Server: Credentials restored.')
            _sync_restored_credentials()
        else: notification('Diggz Account Manager', 'Server: No backup found or restore failed.')
    _reload_and_open_settings()

elif action == 'serverClear':
    from reauthorize.modules import server
    xbmc.sleep(500)
    yes = dialog.yesno('Diggz Account Manager', 'Delete this device\'s credentials from the server? This cannot be undone.', 'Cancel', 'Delete')
    if yes:
        if server.clear(): notification('Diggz Account Manager', 'Server: Device vault deleted.')
        else: notification('Diggz Account Manager', 'Server: Delete failed.')
    _reload_and_open_settings()

elif action == 'backupAll':
    from reauthorize.modules import vault, server
    try:
        # Pick up a YouTube sign-in made since the last save, so it goes into
        # this backup rather than being lost with the next build install.
        try:
            from reauthorize.modules.sync import youtube_sync
            youtube_sync.capture_tokens()
        except Exception as e:
            xbmc.log('[Diggz Account Manager] YouTube sign-in capture failed: %s' % e, xbmc.LOGINFO)

        vault_ok = vault.backup()
        if vault_ok:
            server.backup()

        if vault.last_error() == 'no_credentials':
            # Genuinely nothing to do - no service has been authorized yet.
            notification('Diggz Account Manager', vault.failure_message(), icon=amgr_icon, time=5000)
        else:
            # Syncing runs even when the vault could not be written. Pushing
            # credentials out to the addons is the half of this button that
            # still works on a device with blocked storage, and it used to be
            # skipped entirely - so the button appeared to do nothing at all.
            notification('Diggz Account Manager', 'Saving and syncing services, please wait...', icon=amgr_icon)
            failed = _run_all_syncs()

            problems = []
            if not vault_ok:
                problems.append(vault.failure_message())
            if failed.has_issues:
                _show_sync_result(failed, amgr_icon)
                problems.append('See synchronization report for details.')

            if problems:
                notification('Diggz Account Manager', '  '.join(problems), icon=amgr_icon, time=7000)
            else:
                notification('Diggz Account Manager',
                             vault.warning_message() or 'Done! Credentials saved and all services synced.',
                             icon=amgr_icon, time=6000)
    except Exception as e:
        xbmc.log('[Diggz Account Manager] backupAll failed: %s' % e, xbmc.LOGERROR)
        notification('Diggz Account Manager', 'Backup failed - see kodi.log for details.', icon=amgr_icon, time=6000)
    xbmc.sleep(2500)
    _reload_and_open_settings()

elif action == 'backupService':
    import datetime
    from reauthorize.modules import vault, server
    svc = params.get('service', '')
    vault_ok  = vault.backup()
    server_ok = server.backup()

    # Only stamp a backup date if something was actually written - the date drives
    # the Restore button's visibility, so claiming a backup that doesn't exist
    # offers the user a restore that can only fail.
    if vault_ok or server_ok:
        date_str = datetime.datetime.now().strftime('Date: %Y-%m-%d  Time: %H:%M')
        if svc in _DATE_MAP:
            accountmgr.setSetting(_DATE_MAP[svc], date_str)

    # Report what really happened. The local vault is the one that matters most -
    # it lives outside Kodi and survives a build wipe - so say so plainly when the
    # server is unavailable, rather than a blanket "backup complete".
    warning = vault.warning_message()
    if vault_ok and warning:
        notification('Diggz Account Manager', warning, time=7000)
    elif vault_ok and server_ok:
        notification('Diggz Account Manager', 'Backup complete - saved locally and to the server.')
    elif vault_ok and server.unreachable():
        notification('Diggz Account Manager', 'Saved to local vault. Server unreachable - try Backup again later.')
    elif vault_ok:
        notification('Diggz Account Manager', 'Saved to local vault. Server backup did not complete.')
    elif server_ok:
        notification('Diggz Account Manager', 'Saved to the server, but the local vault could not be written.', time=6000)
    else:
        # Say which failure this is - a blocked device and an empty profile are
        # not the same problem and never had the same fix.
        notification('Diggz Account Manager', vault.failure_message(), time=7000)
    xbmc.sleep(2500)
    _reload_and_open_settings()

elif action == 'restoreService':
    from reauthorize.modules import vault, server
    xbmc.sleep(500)
    yes = dialog.yesno(
        'Diggz Account Manager - Restore',
        'Restore credentials from backup and sync them to your linked add-ons? This will overwrite your current settings.',
        'Cancel', 'Restore')
    if yes:
        ok = server.restore()
        source = 'server'
        if not ok:
            # Remember whether the server was actually unreachable before falling
            # back, so we don't report "no backup found" for a network failure.
            server_down = server.unreachable()
            ok = vault.restore()
            source = 'local vault'
        else:
            server_down = False

        if ok:
            notification('Diggz Account Manager', 'Credentials restored from %s.' % source)
            _sync_restored_credentials()
        elif server_down:
            notification('Diggz Account Manager', 'Could not reach the server, and no local vault backup exists.')
        else:
            notification('Diggz Account Manager', 'No backup found. Use the Auto-Vault or Server Sync section to create one.')
    _reload_and_open_settings()

elif action == 'deviceReset':
    xbmc.sleep(500)
    yes = dialog.yesno(
        'Nuke This Device',
        'This will:[CR]  - Wipe all saved credentials from this device[CR]  - Remove your profile from the server[CR]  - Delete the local vault backup[CR][CR]You will need to start over from scratch.[CR][CR]Are you sure?',
        'Cancel', 'Nuke It')
    if yes:
        # A nuke supersedes any older queued reset-to-default request.
        control.setSetting('reset_settings', 'false')
        from reauthorize.modules import owner
        import embedded as _embedded
        _reset_home = xbmcgui.Window(10000)
        _reset_home.setProperty('Xenon.ReAuthorize.Resetting', 'true')
        _progress = xbmcgui.DialogProgressBG()
        _progress.create('Nuke This Device', 'Removing logins from your add-ons...')
        try:
            # Wait for any startup/wizard recovery to finish before blanking.
            with _embedded.file_lock(os.path.join(_embedded.profile(), 'embedded-recovery.lock')):
                _wipe_failures = owner.wipe_local(
                    revoke_trakt=False,
                    progress=lambda percent, text: _progress.update(percent, 'Nuke This Device', text)) or []
        except Exception as exc:
            _wipe_failures = ['add-on wipe']
            xbmc.log('[Diggz Account Manager Nuke] Add-on wipe failed: ' + type(exc).__name__, xbmc.LOGERROR)
        finally:
            _progress.close()
            _reset_home.clearProperty('Xenon.ReAuthorize.Resetting')
        _ALL_KEYS = [
            'realdebrid.token', 'realdebrid.refresh', 'realdebrid.secret',
            'realdebrid.client_id', 'realdebrid.username',
            'premiumize.token', 'premiumize.username',
            'alldebrid.token', 'alldebrid.username',
            'trakt.token', 'trakt.refresh', 'trakt.expires', 'trakt.username', 'trakt.synclist',
            'torbox.token', 'torbox.enabled',
            'easydebrid.token', 'easydebrid.enabled',
            'offcloud.token', 'offcloud.enabled',
            'easynews.username', 'easynews.password', 'easynews.enabled',
            'filepursuit.api.key', 'filepursuit.enabled', 'torrentclaw.api.key',
            'linksnappy.username', 'linksnappy.password', 'linksnappy.enabled',
            'debridlink.token', 'debridlink.enabled',
            'simkl.token', 'simkl.username', 'simkl.client.id', 'simkl.authorization',
            'lastfm.api.key', 'lastfm.api.secret', 'lastfm.session.key', 'lastfm.username',
            'fanart.tv.api.key', 'omdb.api.key', 'mdb.api.key', 'mdb.username', 'imdb.user',
            'mdblist.oauth.token', 'mdblist.oauth.refresh', 'mdblist.oauth.expires', 'mdblist.oauth.username',
            'tmdb.api.key', 'tmdb.username', 'tmdb.password', 'tmdb.session_id', 'tmdb.authorization', 'tmdb.portal.authorization',
            'audiodb.api.key',
            'youtube.api.key', 'youtube.api.id', 'youtube.api.secret',
            'sync.tk.service', 'sync.rd.service', 'sync.pm.service', 'sync.ad.service',
            'sync.torbox.service', 'sync.easyd.service', 'sync.offc.service',
            'sync.easy.service', 'sync.filep.service', 'sync.meta.service',
            'sync.yt.service', 'sync.lastfm.service', 'sync.linksnappy.service', 'sync.debridlink.service', 'api.service',
            'owner.stamp', 'owner.leaks.seen',
        ]
        for k in _ALL_KEYS:
            accountmgr.setSetting(k, '')
        from reauthorize.modules import device, server, vault
        # Server first: clearing needs this device's ID and key. Removing the ID
        # file before this call used to let the server call read the ID back out
        # of settings and write the file again, so the "reset" kept the old ID.
        try:
            server.clear()
        except Exception:
            pass
        vault.clear()
        device.forget()
        from reauthorize.modules import storage
        storage.purge_all()   # a copy left in another location would come back at the next start
        if _wipe_failures:
            dialog.ok('Diggz Account Manager - Wipe incomplete',
                      'Some add-on logins could not be cleared: ' + ', '.join(_wipe_failures) +
                      '.[CR][CR]Diggz Account Manager backups have been removed. Check kodi.log and the affected add-ons before sharing this setup.')
        else:
            notification('Diggz Account Manager', 'Device reset and supported add-on login removal complete.')
        restart = xbmcgui.Dialog().yesno(
            'Diggz Account Manager - Device Reset',
            ('Some add-on logins may remain.[CR][CR]' if _wipe_failures else 'Saved logins were cleared from Diggz Account Manager and supported add-ons.[CR][CR]') +
            'Kodi must restart before you set your services up again.[CR][CR]'
            'Close Kodi now?',
            nolabel='Later', yeslabel='Close Kodi')
        if restart:
            import os as _os2
            _os2._exit(1)
        else:
            _reload_and_open_settings()

elif action == 'clearServiceDate':
    svc = params.get('service', '')
    if svc in _DATE_MAP:
        accountmgr.setSetting(_DATE_MAP[svc], 'Date: 0000-00-00  Time: 00:00')
    notification('Diggz Account Manager', 'Backup record cleared.')
    _reload_and_open_settings()

elif action == 'prepareDistribution':
    xbmc.sleep(500)
    # Every dialog here puts its point in the first line and stays short: some skins scroll a
    # long text slowly in one line, and the user nearly pressed on before reading it (1.4.3).
    confirmed = xbmcgui.Dialog().yesno(
        'Prepare This Build for Distribution',
        'Remove every sign-in, then close Kodi?[CR][CR]'
        'Do this LAST, after any clean-up inside Kodi. It takes about a minute: please let it finish, '
        'Kodi force closes when done. Then zip the build before opening Kodi again.',
        nolabel='Cancel', yeslabel='Remove and close')
    # 1.4.3: truncate tables, which builders otherwise ran from a wizard (build_clean.py). Both
    # need Kodi closed straight after, so they can only run together, from this one button.
    # Asked here, before anything is cleared, so a Back leaves it out.
    clean_build = confirmed and xbmcgui.Dialog().yesno(
        'Prepare This Build for Distribution',
        'Also truncate the database tables?[CR][CR]'
        'Empties watched history, TV guide, music and views. Add-ons and their settings stay.',
        nolabel='Sign-ins only', yeslabel='Truncate too')
    if confirmed:
        _DIST_KEYS = [
            'realdebrid.token', 'realdebrid.refresh', 'realdebrid.secret',
            'realdebrid.client_id', 'realdebrid.username',
            'premiumize.token', 'premiumize.username',
            'alldebrid.token', 'alldebrid.username',
            'trakt.token', 'trakt.refresh', 'trakt.expires', 'trakt.username', 'trakt.synclist',
            'torbox.token', 'easydebrid.token',
            'offcloud.token', 'offcloud.userid', 'offcloud.user', 'offcloud.pass',
            'easynews.username', 'easynews.password',
            'filepursuit.api.key', 'torrentclaw.api.key',
            'linksnappy.username', 'linksnappy.password',
            'debridlink.token',
            'simkl.token', 'simkl.username', 'simkl.client.id', 'simkl.authorization',
            'lastfm.api.key', 'lastfm.api.secret', 'lastfm.session.key', 'lastfm.username',
            'fanart.tv.api.key', 'omdb.api.key', 'mdb.api.key', 'mdb.username', 'imdb.user',
            'mdblist.oauth.token', 'mdblist.oauth.refresh', 'mdblist.oauth.expires', 'mdblist.oauth.username',
            'tmdb.api.key', 'tmdb.username', 'tmdb.password', 'tmdb.session_id', 'tmdb.authorization', 'tmdb.portal.authorization',
            'audiodb.api.key',
            'youtube.api.key', 'youtube.api.id', 'youtube.api.secret',
            'sync.tk.service', 'sync.rd.service', 'sync.pm.service', 'sync.ad.service',
            'sync.torbox.service', 'sync.easyd.service', 'sync.offc.service',
            'sync.easy.service', 'sync.filep.service', 'sync.meta.service', 'sync.yt.service',
            'sync.lastfm.service', 'sync.linksnappy.service', 'sync.debridlink.service',
            'api.service',
            # This device's ID. device.py no longer keeps it in settings, but an
            # older version did, and every box the build went on took it and
            # shared this device's cloud backup.
            'server.device.id', 'server.shared.notice',
            # Ownership stamp (owner.py): made from this device's ID, harmless on
            # another box, but no reason to ship it.
            'owner.stamp', 'owner.leaks.seen',
            # settings_display.py mirrors these into disabled *.display rows for
            # the UI. Most mirror masked or generic-status text and are harmless,
            # but the ones below are the real value verbatim -- confirmed live,
            # 2026-09-29, on the first real test of this button: imdb.user.display
            # still held the profile ID after imdb.user itself was cleared. A
            # hidden row's visibility check keeps it off screen once the real
            # value is blank, but the raw string was still sitting in the
            # distributed build's settings.xml.
            'realdebrid.username.display', 'premiumize.username.display',
            'alldebrid.username.display', 'easynews.username.display',
            'linksnappy.username.display', 'trakt.username.display',
            'simkl.username.display', 'lastfm.username.display',
            'tmdb.api.key.display', 'tmdb.username.display',
            'fanart.tv.api.key.display', 'audiodb.api.key.display',
            'mdb.username.display', 'mdb.api.key.display', 'omdb.api.key.display', 'mdblist.oauth.username.display',
            'imdb.user.display', 'youtube.api.key.display', 'youtube.api.id.display',
            'torrentclaw.authorized.display',
        ]
        # A progress window for the whole run (about 40 seconds: two passes through the add-ons
        # with a pause between, then the tables). With only a corner notice the user took the
        # pause for the end and nearly pressed on (1.4.3). Cancel is ignored: stopping halfway
        # would ship a build with some sign-ins still in it.
        busy = xbmcgui.DialogProgress()
        busy.create('Cleaning, please wait - do not close Kodi', 'Removing the sign-ins from Diggz Account Manager...')

        def _step(percent, text):
            try:
                busy.update(int(percent * (0.85 if clean_build else 1)), text)
            except Exception:
                pass

        for k in _DIST_KEYS:
            accountmgr.setSetting(k, '')
        # A build also carries every sign-in ReAuthorize had already pushed into the
        # add-ons' own settings and databases, so blank those too. Until 1.3.5 only
        # ReAuthorize's own copy was cleared and the rest shipped with the build.
        try:
            from reauthorize.modules import owner
            wipe_failures = owner.wipe_local(progress=_step)
        except Exception as e:
            wipe_failures = ['add-on sign-in wipe']
            xbmc.log('[Diggz Account Manager] Prepare for Distribution: clearing the add-ons failed (%s).' % type(e).__name__, xbmc.LOGERROR)
        problem = ''
        if clean_build:
            busy.update(88, 'Truncating the database tables...')
            try:
                from reauthorize.modules import build_clean
                report = build_clean.clean()
                if report['problems']:
                    problem = '[CR]' + build_clean.summary(report)
            except Exception as e:
                xbmc.log('[Diggz Account Manager] Prepare for Distribution: truncating the tables failed: %s' % e, xbmc.LOGERROR)
                problem = '[CR][COLOR FFFF6666]Truncating the tables failed. Check kodi.log.[/COLOR]'
        if wipe_failures:
            busy.close()
            xbmcgui.Dialog().ok(
                'Distribution wipe incomplete',
                'Some sign-ins may still be stored. Do not share this build yet.[CR][CR]'
                'Could not clear %s. Check kodi.log and the affected add-ons.[CR][CR]'
                'Kodi will close after you dismiss this message.' % ', '.join(wipe_failures) + problem)
        else:
            message = ('Tables and sign-ins are clean.' if clean_build and not problem
                       else 'Sign-ins are clean.')
            busy.update(100, message + ' Kodi will now force close.' + problem)
            xbmc.sleep(8000 if problem else 4000)
            busy.close()
        # A FORCE close (the user, 2026-10-18), not Quit: a normal Quit hung Kodi 21 after 'Unloaded skin' on
        # every bench run (each time after an add-on's service, Umbrella's, had been force-stopped in that
        # session), and the builder was left with a frozen screen. Everything ReAuthorize writes is on disk by
        # now (setSetting saves at once, the databases are closed); the pause lets anything another add-on was
        # writing finish. What a force close skips is Kodi's own save of its last-minute changes at exit.
        xbmc.sleep(2000)
        xbmc.log('[Diggz Account Manager] Prepare for Distribution: done - force closing Kodi', xbmc.LOGINFO)
        control.force_close()

elif action == 'readMeFirst':
    from reauthorize.help import help
    help.get_readmefirst()
    _reload_and_open_settings()

elif action == 'silentReAuthorize':
    notification('Diggz Account Manager', 'Re-authorizing your services, please wait...', icon=amgr_icon)
    xbmc.sleep(1000)
    try:
        failed = _run_all_syncs()
        _show_sync_result(failed, amgr_icon)
    except Exception as e:
        xbmc.log('[Diggz Account Manager] silentReAuthorize failed: %s' % e, xbmc.LOGERROR)
        notification('Diggz Account Manager', 'Re-authorize failed - see kodi.log for details.', icon=amgr_icon, time=6000)
    _reload_and_open_settings()

elif action == 'quickAuthorize':
    from reauthorize.windows.authorize_quick import open_quick_authorize
    open_quick_authorize()
    _reload_and_open_settings()

elif action == 'removeService':
    _categories = [
        ('Debrid Services', [
            ('realdebrid.token',    [],                    'Real-Debrid'),
            ('premiumize.token',    [],                    'Premiumize'),
            ('alldebrid.token',     [],                    'All-Debrid'),
            ('torbox.token',        [],                    'TorBox'),
            ('easydebrid.token',    [],                    'Easy Debrid'),
            ('offcloud.token',      [],                    'OffCloud'),
        ]),
        ('Trakt & Scrobble', [
            ('trakt.token',         ['trakt.username', 'trakt.refresh', 'trakt.expires'], 'Trakt'),
            ('simkl.token',         ['simkl.username'],    'Simkl'),
            ('lastfm.session.key',  ['lastfm.username', 'lastfm.api.key', 'lastfm.api.secret'], 'Last.fm'),
        ]),
        ('Streaming & Other', [
            ('easynews.username',   ['easynews.password'], 'Easynews'),
            ('filepursuit.api.key', [],                    'FilePursuit'),
            ('youtube.api.key',     ['youtube.api.id', 'youtube.api.secret'], 'YouTube for Kodi'),
        ]),
        ('Metadata', [
            ('tmdb.session_id',     ['tmdb.username', 'tmdb.password', 'tmdb.authorization', 'tmdb.portal.authorization'], 'TMDB Account'),
            ('tmdb.api.key',        [], 'TMDB API Key'),
            ('fanart.tv.api.key',   [],                    'Fanart.TV'),
            ('mdb.api.key',         [],                    'MDBList'),
        ]),
    ]
    any_configured = any(
        accountmgr.getSetting(key)
        for _, services in _categories
        for key, _, __ in services
    )
    if not any_configured:
        dialog.ok('Diggz Account Manager', 'No services are currently configured.')
    else:
        cat_choice = dialog.select('Remove a Service - Choose Category',
                                   [cat_label for cat_label, _ in _categories])
        if cat_choice >= 0:
            cat_label, cat_services = _categories[cat_choice]
            svc_choice = dialog.select('Remove - %s' % cat_label,
                                       [lbl for _, __, lbl in cat_services])
            if svc_choice >= 0:
                key, extra, label = cat_services[svc_choice]
                if not accountmgr.getSetting(key):
                    dialog.ok('Diggz Account Manager', '%s is not currently configured.' % label)
                elif dialog.yesno('Diggz Account Manager', 'Remove %s from your profile?' % label,
                                  nolabel='Cancel', yeslabel='Remove'):
                    accountmgr.setSetting(key, '')
                    for extra_key in extra:
                        accountmgr.setSetting(extra_key, '')
                    from reauthorize.modules import vault, server
                    vault.backup()
                    server.backup()
                    dialog.notification('Diggz Account Manager', '%s removed.' % label, time=3000)
    _reload_and_open_settings()
