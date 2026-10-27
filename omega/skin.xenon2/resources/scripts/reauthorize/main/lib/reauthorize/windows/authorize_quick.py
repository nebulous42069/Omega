# -*- coding: utf-8 -*-
"""
    ReAuthorize - Quick Authorize (Welcome Back)
    For returning users: one button pushes all saved credentials to every
    installed addon. Shows a backdrop of installed addon icons, a progress
    bar during sync, then a results list with per-addon service icon rows.
"""

import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from reauthorize.modules import control
from reauthorize.modules import vault
from reauthorize.modules import server
from reauthorize.modules import addon_service_view

ADDON_ID   = 'script.module.reauthorize'
ICONS_PATH = os.path.join(xbmcaddon.Addon(ADDON_ID).getAddonInfo('path'), 'resources', 'icons')

_TICKER_DEFS = [
    ('trakt.token',         'sync.tk.service',          'Trakt'),
    ('realdebrid.token',    'sync.rd.service',           'Real-Debrid'),
    ('premiumize.token',    'sync.pm.service',           'Premiumize'),
    ('alldebrid.token',     'sync.ad.service',           'All-Debrid'),
    ('torbox.token',        'sync.torbox.service',       'TorBox'),
    ('easydebrid.token',    'sync.easyd.service',        'Easy Debrid'),
    ('offcloud.token',      'sync.offc.service',         'OffCloud'),
    ('linksnappy.username', 'sync.linksnappy.service',   'Linksnappy'),
    ('debridlink.token',    'sync.debridlink.service',   'Debrid-Link'),
    ('easynews.username',   'sync.easy.service',         'Easynews'),
    ('filepursuit.api.key', 'sync.filep.service',        'FilePursuit'),
    ('simkl.token',         None,                        'Simkl'),
    ('lastfm.session.key',  'sync.lastfm.service',       'Last.fm'),
    ('youtube.api.key',     'sync.yt.service',           'YouTube'),
]

_SYNC_STEPS = [
    ('trakt.token',           'trakt',       'reauthorize.modules.sync.trakt_sync',       'Auth', 'trakt_auth',       'sync.tk.service'),
    ('realdebrid.token',      'realdebrid',  'reauthorize.modules.sync.debrid_rd',        'Auth', 'realdebrid_auth',  'sync.rd.service'),
    ('premiumize.token',      'premiumize',  'reauthorize.modules.sync.debrid_pm',        'Auth', 'premiumize_auth',  'sync.pm.service'),
    ('alldebrid.token',       'alldebrid',   'reauthorize.modules.sync.debrid_ad',        'Auth', 'alldebrid_auth',   'sync.ad.service'),
    ('torbox.token',          'torbox',      'reauthorize.modules.sync.torbox_sync',      'Auth', 'torbox_auth',      'sync.torbox.service'),
    ('easydebrid.token',      'easydebrid',  'reauthorize.modules.sync.easydebrid_sync',  'Auth', 'easydebrid_auth',  'sync.easyd.service'),
    ('offcloud.token',        'offcloud',    'reauthorize.modules.sync.offcloud_sync',    'Auth', 'offcloud_auth',    'sync.offc.service'),
    ('linksnappy.username',   'linksnappy',  'reauthorize.modules.sync.linksnappy_sync',  'Auth', 'linksnappy_auth',  'sync.linksnappy.service'),
    ('debridlink.token',      'debridlink',  'reauthorize.modules.sync.debridlink_sync',  'Auth', 'debridlink_auth',  'sync.debridlink.service'),
    ('easynews.username',     'easynews',    'reauthorize.modules.sync.easy_sync',        'Auth', 'easy_auth',        'sync.easy.service'),
    ('filepursuit.api.key',   'filepursuit', 'reauthorize.modules.sync.filepursuit_sync', 'Auth', 'file_auth',        'sync.filep.service'),
    ('simkl.token',           'simkl',       'reauthorize.modules.sync.simkl_sync',      'Auth', 'simkl_auth',       None),
    ('lastfm.session.key',    'lastfm',      'reauthorize.modules.sync.lastfm_sync',      'Auth', 'lastfm_auth',      'sync.lastfm.service'),
    ('youtube.api.key',       'youtube',     'reauthorize.modules.sync.youtube_sync',    'Auth', 'youtube_auth',     'sync.yt.service'),
]

_SERVICE_LABELS = {
    'trakt': 'Trakt', 'realdebrid': 'Real-Debrid', 'premiumize': 'Premiumize',
    'alldebrid': 'All-Debrid', 'torbox': 'TorBox', 'easydebrid': 'Easy Debrid',
    'offcloud': 'OffCloud', 'easynews': 'Easynews', 'filepursuit': 'FilePursuit',
    'simkl': 'Simkl', 'tmdb': 'TMDB', 'lastfm': 'Last.fm', 'youtube': 'YouTube',
    'linksnappy': 'Linksnappy', 'debridlink': 'Debrid-Link',
}

_RESULT_SERVICES  = ['trakt', 'realdebrid', 'premiumize', 'alldebrid', 'torbox', 'simkl', 'easynews', 'tmdb', 'youtube']
_PROGRESS_BAR_MAX = 1200

_META_KEYS = ('fanart.tv.api.key', 'tmdb.api.key', 'tmdb.username',
              'audiodb.api.key', 'omdb.api.key', 'mdb.api.key', 'imdb.user')


class QuickAuthorize(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super(QuickAuthorize, self).__init__(*args, **kwargs)
        self._addon         = xbmcaddon.Addon(ADDON_ID)
        self._synced        = []
        self._did_full_sync = False
        self._sync_running  = False

    def onInit(self):
        self._addons_base = xbmcvfs.translatePath('special://home/addons/')
        active = [s for s in _SYNC_STEPS if self._addon.getSetting(s[0])]
        if active:
            msg = '%d service%s ready - click Re-Auth All to push to your addons.' % (
                len(active), 's' if len(active) != 1 else '')
        else:
            msg = 'No services set up yet - open the Debrid Services tab to add one.'
        self._update_progress(0, msg)
        self._show_current_status()

    def _silent_backup(self):
        """Silently backup credentials if any exist and we haven't just done a full sync."""
        if self._did_full_sync:
            return  # _run_authorize_all already backed up
        has_creds = any(self._addon.getSetting(s[0]) for s in _SYNC_STEPS)
        if not has_creds:
            return
        try:
            vault.backup()
            server.backup()
        except Exception:
            pass

    def onClick(self, control_id):
        if control_id == 201:
            if not self._sync_running:
                self._run_authorize_all()
        elif control_id == 200:
            self._silent_backup()
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self._silent_backup()
            self.close()

    # ── Progress ──────────────────────────────────────────────────────────────

    def _update_progress(self, pct, message):
        self.getControl(500).setLabel(message)
        self.getControl(511).setWidth(int(_PROGRESS_BAR_MAX * pct / 100.0))

    # ── Results ───────────────────────────────────────────────────────────────

    def _show_current_status(self):
        """Pre-populate results list from current settings - no sync needed."""
        authorized = set()
        for (token_key, svc_id, *_) in _SYNC_STEPS:
            if self._addon.getSetting(token_key):
                authorized.add(svc_id)
        if any(self._addon.getSetting(k) for k in _META_KEYS):
            authorized.add('tmdb')
        self._fill_results_list(authorized)
        try:
            self.getControl(520).setLabel(self._build_ticker())
        except Exception:
            pass

    def _fill_results_list(self, authorized_set):
        list_ctrl = self.getControl(100)
        list_ctrl.reset()

        addons_with_services = addon_service_view.get_addons_with_services(self._addons_base)
        _EXCLUDE = {'script.module.trakt'}
        addons_with_services = [a for a in addons_with_services if a['id'] not in _EXCLUDE]
        for addon_info in addons_with_services:
            active = [s for s in addon_info['services'] if s in authorized_set]
            item = xbmcgui.ListItem(label=addon_info['label'])
            icon_path = addon_service_view.get_addon_icon_path(addon_info['id'], self._addons_base)
            art = {
                'icon':  icon_path,
                'thumb': icon_path,
            }
            for svc_id in _RESULT_SERVICES:
                art['icon_%s' % svc_id] = addon_service_view.get_service_icon_path(svc_id)
            item.setArt(art)
            for svc_id in _RESULT_SERVICES:
                if svc_id in addon_info['services']:
                    col = 'FFFFFFFF' if svc_id in active else '44FFFFFF'
                else:
                    col = '00000000'
                item.setProperty('col_%s' % svc_id, col)
            list_ctrl.addItem(item)

        if list_ctrl.size() == 0:
            list_ctrl.addItem(xbmcgui.ListItem(
                label='No supported add-ons found in this build.'))

    # ── Sync ──────────────────────────────────────────────────────────────────

    def _run_authorize_all(self):
        self._sync_running = True
        self.getControl(201).setLabel('Syncing...')

        active_steps = [s for s in _SYNC_STEPS if self._addon.getSetting(s[0])]
        if not active_steps:
            self._update_progress(0, 'No services set up yet - open the Debrid Services tab to add one.')
            self._sync_running = False
            self.getControl(201).setLabel('Re-Auth All')
            return

        total        = len(active_steps)
        self._synced = []

        for i, (token_key, svc_id, module_path, cls_name, method_name, flag) in enumerate(active_steps):
            self._update_progress(
                int(100 * i / total),
                'Syncing %s...' % _SERVICE_LABELS.get(svc_id, svc_id)
            )
            xbmc.sleep(200)
            try:
                mod = __import__(module_path, fromlist=[cls_name])
                getattr(getattr(mod, cls_name)(), method_name)()
                if flag:
                    control.setSetting(flag, 'true')
                if svc_id == 'trakt':
                    control.setSetting('api.service', 'true')
                self._synced.append(svc_id)
            except Exception as e:
                xbmc.log('[ReAuthorize QuickAuth] Sync error (%s): %s' % (svc_id, str(e)), xbmc.LOGWARNING)

        if any(self._addon.getSetting(k) for k in _META_KEYS):
            self._update_progress(95, 'Syncing metadata services...')
            xbmc.sleep(200)
            try:
                __import__('reauthorize.modules.sync.meta_sync', fromlist=['Auth']).Auth().meta_auth()
                control.setSetting('sync.meta.service', 'true')
                if 'tmdb' not in self._synced:
                    self._synced.append('tmdb')
            except Exception as e:
                xbmc.log('[ReAuthorize QuickAuth] Meta sync error: %s' % str(e), xbmc.LOGWARNING)

        v_ok = vault.backup()
        s_ok = server.backup()
        self._did_full_sync = True
        if v_ok or s_ok:
            backed = ' + '.join((['local'] if v_ok else []) + (['cloud'] if s_ok else []))
            backup_line = 'Authorization complete - backed up: %s' % backed
            if v_ok and vault.warning_message():
                backup_line = 'Authorized, but the backup will not survive a new build.'
        else:
            # Name the actual reason instead of "check settings" - the user has
            # no way to tell a blocked device from an empty profile otherwise.
            backup_line = 'Authorized, but not backed up. %s' % vault.failure_message()
        self._update_progress(100, backup_line)
        self._fill_results_list(set(self._synced))

        self._sync_running = False
        self.getControl(201).setLabel('Re-Auth All')
        try:
            self.getControl(520).setLabel(self._build_ticker())
        except Exception:
            pass

        # Offer restart so all addons reload with new credentials
        if self._synced:
            restart = xbmcgui.Dialog().yesno(
                'ReAuthorize',
                'All services synced successfully.[CR][CR]'
                'A Kodi restart is recommended so all addons fully load the new credentials.[CR][CR]'
                'Close Kodi now?',
                nolabel='Later', yeslabel='Close Kodi'
            )
            if restart:
                xbmc.executebuiltin('Quit')
            else:
                self.setFocusId(200)
        else:
            xbmcgui.Dialog().notification('ReAuthorize', backup_line, time=5000)
            self.setFocusId(200)


    # ── Status ticker ─────────────────────────────────────────────────────────

    def _build_ticker(self):
        parts = []
        for token_key, flag_key, label in _TICKER_DEFS:
            has_token = bool(self._addon.getSetting(token_key))
            synced = flag_key and self._addon.getSetting(flag_key) == 'true'
            if has_token and synced:
                parts.append('[COLOR FF00C851]%s: Active[/COLOR]' % label)
            elif has_token:
                parts.append('[COLOR FFFFBB33]%s: Pending Sync[/COLOR]' % label)
            else:
                parts.append('[COLOR FFFF4444]%s: Not Set Up[/COLOR]' % label)
        has_meta = any(self._addon.getSetting(k) for k in _META_KEYS)
        meta_synced = self._addon.getSetting('sync.meta.service') == 'true'
        if has_meta and meta_synced:
            parts.append('[COLOR FF00C851]TMDB: Active[/COLOR]')
        elif has_meta:
            parts.append('[COLOR FFFFBB33]TMDB: Pending Sync[/COLOR]')
        else:
            parts.append('[COLOR FFFF4444]TMDB: Not Set Up[/COLOR]')
        # Use fadelabel-compatible separators so Kodi shows one clean item at a time.
        return '|'.join(parts)


# ── Entry point ───────────────────────────────────────────────────────────────

def open_quick_authorize():
    addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
    w = QuickAuthorize('authorize_quick.xml', addon_path, 'default', '1080i')
    w.doModal()
    del w
