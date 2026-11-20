# -*- coding: utf-8 -*-
"""
	Diggz Account Manager - Build Status Dashboard
	Addon-centric view: shows each installed addon and the credentials found in its local settings.
"""

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from reauthorize.modules import addon_service_view, credential_status, dashboard_catalog

ADDON_ID   = 'script.module.authorizediggz'

# Rows that fit in the list viewport at once. Derived from status.xml:
# list height 748 / itemlayout height 72 = 10. Keep in sync if either changes.
VISIBLE_ROWS = 10
COUNT_LABEL_ID = 300
_SERVICES = dashboard_catalog.services()


# ── Window class ──────────────────────────────────────────────────────────────

class StatusDashboard(xbmcgui.WindowXMLDialog):

	def onInit(self):
		self._addons_base = xbmcvfs.translatePath('special://home/addons/')
		self._populate()

	# ── Helpers ───────────────────────────────────────────────────────────────

	def _addon_label(self, addon_id):
		"""Return a friendly display name for an addon ID."""
		return addon_service_view.get_addon_label(addon_id)

	def _installed_rows(self):
		return dashboard_catalog.rows(lambda aid: xbmcvfs.exists(self._addons_base + aid + '/'))

	def _populate(self):
		_addon    = xbmcaddon.Addon(ADDON_ID)
		list_ctrl = self.getControl(100)
		list_ctrl.reset()

		seen = self._installed_rows()
		states, _ = credential_status.scan(seen, _SERVICES, _addon)

		# Show the other debrid columns as unsupported for this add-on.
		colors = {'present': 'FFFFFFFF', 'unknown': '45FFFFFF', 'missing': '18FFFFFF'}

		if not seen:
			item = xbmcgui.ListItem(label='No supported addons found in this build')
			item.setLabel2('[COLOR FFFFFFFF]Install addons that use the services above[/COLOR]')
			list_ctrl.addItem(item)
			self.setFocusId(200)
			return

		# Sort alphabetically by friendly label
		addon_rows = sorted(seen.items(), key=lambda x: self._addon_label(x[0]).lower())

		resolver_color = credential_status.resolver_badge_color()
		for aid, _ in addon_rows:
			label = self._addon_label(aid)

			addon_icon = addon_service_view.get_addon_icon_path(aid, self._addons_base)

			item = xbmcgui.ListItem(label=label)
			art = {
				'icon': addon_icon,
				'thumb': addon_icon,
			}
			if aid in dashboard_catalog.RESOLVER_BADGE:
				item.setProperty('resolver_color', resolver_color)
				art['resolver'] = addon_service_view.get_addon_icon_path(
					dashboard_catalog.RESOLVEURL, self._addons_base)
			for svc in _SERVICES:
				art['icon_%s' % svc['id']] = svc['icon']
			item.setArt(art)

			for svc in _SERVICES:
				svc_id = svc['id']
				state = states.get((aid, svc_id))
				col = colors.get(state, '00000000')
				if state == 'unknown':
					item.setProperty('unknown_' + svc_id, 'true')
				item.setProperty('col_%s' % svc_id, col)

			item.setProperty('addon_id', aid)
			list_ctrl.addItem(item)

		self._set_count_label(len(addon_rows))

		list_ctrl.selectItem(0)  # Always open on the first row, never a restored position
		self.setFocusId(100)     # Focus the list itself so the highlight is visible at the top

	def _set_count_label(self, total):
		"""Show '10 of 15 shown' when the list scrolls, plain total when it doesn't."""
		if total > VISIBLE_ROWS:
			text = '%d of %d shown  -  scroll for more' % (VISIBLE_ROWS, total)
		elif total == 1:
			text = '1 addon'
		else:
			text = '%d addons' % total
		try:
			self.getControl(COUNT_LABEL_ID).setLabel(text)
		except Exception:
			pass  # label is optional - skin may not define it

	# ── Actions ───────────────────────────────────────────────────────────────

	def onClick(self, control_id):
		if control_id == 200:
			# Close
			self.close()
		elif control_id == 100:
			# Addon row clicked - open that addon's settings
			item = self.getControl(100).getSelectedItem()
			if item:
				aid = item.getProperty('addon_id')
				if aid == 'plugin.video.themoviedb.helper':
					from reauthorize.modules import tmdbh_compat
					choices = [('TMDb Helper', aid)] + [(label, provider) for label, provider in [('Trakt', tmdbh_compat.TRAKT), ('MDBList', tmdbh_compat.MDBLIST), ('SIMKL', tmdbh_compat.SIMKL), ('TVDb', tmdbh_compat.TVDB)] if tmdbh_compat.installed(provider)]
					selected = xbmcgui.Dialog().select('TMDb Helper settings', [label for label, provider in choices])
					if selected >= 0:
						xbmc.executebuiltin('Addon.OpenSettings(%s)' % choices[selected][1])
				elif aid:
					xbmc.executebuiltin('Addon.OpenSettings(%s)' % aid)

	def onAction(self, action):
		if action.getId() in (9, 10, 92):  # Back / Escape / Nav-Back
			self.close()


# ── Entry point ───────────────────────────────────────────────────────────────

def open_status():
    from reauthorize.modules import own_settings, restart_hint

    account = own_settings.addon()
    addon_path = account.getAddonInfo('path')
    window = StatusDashboard('status.xml', addon_path, 'default', '1080i')
    window._addons_base = xbmcvfs.translatePath('special://home/addons/')
    _, pending = credential_status.scan(window._installed_rows(), _SERVICES, account)
    if pending:
        dialog = xbmcgui.Dialog()
        labels = {service['id']: service['label'] for service in _SERVICES}
        names = sorted('%s (%s)' % (addon_service_view.get_addon_label(aid), labels[sid])
                       for aid, sid in pending)
        preview = ', '.join(names[:5])
        if len(names) > 5:
            preview += ' and %d more' % (len(names) - 5)
        message = (
            'Saved sign-ins are available for add-ons with missing credentials.[CR][CR]'
            '%s[CR][CR]Sync the affected services now? This runs the normal sync for '
            'those services and may replace their existing sign-ins in other linked add-ons.'
        ) % preview
        if dialog.yesno('Diggz Account Manager View Status', message, nolabel='Later', yeslabel='Sync now'):
            from reauthorize.modules.sync_all import run_all_syncs
            before = restart_hint.key_files()
            tags = set(pending.values())
            failed = run_all_syncs(include_trakt='trakt' in tags, only=tags)
            if restart_hint.note_for_next_start(before, 'View Status sync'):
                restart_hint.mark()
                dialog.ok('Diggz Account Manager', 'Restart Kodi to load the updated app keys.')
            if failed.has_issues:
                dialog.ok('Diggz Account Manager', failed.message())
    window.doModal()
