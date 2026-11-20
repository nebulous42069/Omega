from reauthorize.modules import control, sync_support
import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

from pathlib import Path
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Torbox
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_token = accountmgr.getSetting("torbox.token")
your_acct_id = accountmgr.getSetting("torbox.acct_id")
          

from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def torbox_auth(self):
        wipe = control.wiping()
        token = '' if wipe else your_token
        account_id = '' if wipe else your_acct_id
        enabled = 'true' if token else 'false'
        if not token and not wipe:
            return
        targets = {
            'plugin.video.umbrella': [('torboxtoken', token), ('torbox.username', account_id), ('torbox.enable', enabled)],
            'plugin.video.pov': [('tb.token', token), ('tb.account_id', account_id), ('tb.enabled', enabled), ('tb.expires', '0')],
            'plugin.video.infinity': [('torboxtoken', token), ('torbox.username', account_id), ('torbox.enable', enabled), ('torbox.expirynotice', '0')],
            'plugin.video.genocide': [('torbox.token', token), ('torbox.username', account_id)],
            'plugin.video.orion': [('tb_token', token), ('tb_enabled', enabled)],
            'plugin.video.thearchives': [('tb.token', token), ('tb.enabled', enabled)],
            'plugin.video.cosmos': [('tb_api_key', token), ('tb_auth_done', enabled)],
            'plugin.program.rdtplayer': [('torbox_token', token)],
            'plugin.video.prism': [('tb.token', token), ('torbox.enabled', enabled)],
            'plugin.video.youtubetheater': [('tb.token', token), ('debrid_use_tr', enabled)],
        }
        # Expiry metadata was previously reset only on a token change.
        for aid, pairs in targets.items():
            if not sync_support.installed(aid):
                continue
            try:
                addon = xbmcaddon.Addon(aid)
                if not addon._writable(pairs[0][0]):
                    sync_support.warning(aid, 'incompatible; missing writable setting: ' + pairs[0][0])
                    continue
                if not wipe and addon.getSetting(pairs[0][0]) == token:
                    pairs = [(k, v) for k, v in pairs if k not in ('tb.expires', 'torbox.expirynotice')]
                sync_support.put(aid, pairs, wipe=wipe)
            except Exception:
                sync_support.failed(aid)
        try:
            if sync_support.installed('plugin.video.otaku'):
                addon = xbmcaddon.Addon('plugin.video.otaku')
                current = 'torbox.token' in (addon.schema or {})
                pairs = [('torbox.token' if current else 'tb.apikey', token),
                         ('torbox.enabled' if current else 'tb.enabled', enabled)]
                if wipe and current:
                    pairs.extend([('torbox.username', ''), ('torbox.auth.status', '')])
                sync_support.put('plugin.video.otaku', pairs, wipe=wipe)
        except Exception:
            sync_support.failed('plugin.video.otaku')
        try:
            if sync_support.profile_ready('plugin.video.gears', var.gears_settings_db):
                from reauthorize.modules.db import torbox_db
                if torbox_db.auth_gears_tb(token):
                    var.remake_settings()
        except Exception:
            sync_support.failed('plugin.video.gears')
        try:
            from reauthorize.modules.db import redlight_db
            redlight_db.push([('tb.token', token), ('tb.enabled', enabled)])
        except Exception:
            sync_support.failed('plugin.video.redlight')
        try:
            from reauthorize.modules.sync import tmdbmovies_sync
            tmdbmovies_sync.cloud('torbox_api_key', token, wipe=wipe)
        except Exception:
            sync_support.failed('plugin.video.tmdbmovies')
