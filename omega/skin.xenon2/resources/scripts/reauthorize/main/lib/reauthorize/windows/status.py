# -*- coding: utf-8 -*-
"""
	ReAuthorize - Build Status Dashboard
	Addon-centric view: shows each installed addon and which services
	have been configured in it by ReAuthorize.
"""

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from reauthorize.modules import addon_service_view

ADDON_ID   = 'script.module.reauthorize'

# Rows that fit in the list viewport at once. Derived from status.xml:
# list height 748 / itemlayout height 72 = 10. Keep in sync if either changes.
VISIBLE_ROWS = 10
COUNT_LABEL_ID = 300
_SERVICES = addon_service_view.status_services()
_SERVICE_ADDONS = addon_service_view.SERVICE_ADDONS
_DEBRID_SERVICE_IDS = addon_service_view.DEBRID_SERVICE_IDS


# ── Window class ──────────────────────────────────────────────────────────────

class StatusDashboard(xbmcgui.WindowXMLDialog):

	def onInit(self):
		self._addons_base = xbmcvfs.translatePath('special://home/addons/')
		self._populate()

	# ── Helpers ───────────────────────────────────────────────────────────────

	def _addon_label(self, addon_id):
		"""Return a friendly display name for an addon ID."""
		return addon_service_view.get_addon_label(addon_id)

	def _populate(self):
		_addon    = xbmcaddon.Addon(ADDON_ID)
		list_ctrl = self.getControl(100)
		list_ctrl.reset()

		# Pre-compute credential + sync state for every service
		svc_state = {}
		for svc in _SERVICES:
			keys = svc.get('token_keys') or [svc['token_key']]
			authed = any(bool(_addon.getSetting(k)) for k in keys)
			sync_flag = svc.get('sync_flag')
			synced    = (_addon.getSetting(sync_flag) == 'true') if sync_flag else authed
			svc_state[svc['id']] = (authed, synced)

		# Build the per-addon list from _SERVICE_ADDONS (deduplicated, sorted by label)
		seen     = {}  # addon_id -> list of service IDs it supports
		for svc in _SERVICES:
			for aid in _SERVICE_ADDONS.get(svc['id'], []):
				if aid in addon_service_view.STATUS_HIDDEN:
					continue
				if xbmcvfs.exists(self._addons_base + aid + '/'):
					seen.setdefault(aid, []).append(svc['id'])

		# If an addon supports any debrid service, show all debrid services for it
		for aid in seen:
			if any(s in _DEBRID_SERVICE_IDS for s in seen[aid]):
				for svc_id in _DEBRID_SERVICE_IDS:
					if svc_id not in seen[aid]:
						seen[aid].append(svc_id)

		if not seen:
			item = xbmcgui.ListItem(label='No supported addons found in this build')
			item.setLabel2('[COLOR FFFFFFFF]Install addons that use the services above[/COLOR]')
			list_ctrl.addItem(item)
			self.setFocusId(200)
			return

		# Sort alphabetically by friendly label
		addon_rows = sorted(seen.items(), key=lambda x: self._addon_label(x[0]).lower())

		for aid, services in addon_rows:
			label = self._addon_label(aid)

			addon_icon = addon_service_view.get_addon_icon_path(aid, self._addons_base)

			item = xbmcgui.ListItem(label=label)
			art = {
				'icon': addon_icon,
				'thumb': addon_icon,
			}
			for svc in _SERVICES:
				art['icon_%s' % svc['id']] = svc['icon']
			item.setArt(art)

			for svc in _SERVICES:
				svc_id = svc['id']
				if svc_id not in services:
					col = '00000000'
				else:
					authed, synced = svc_state[svc_id]
					if authed and synced:
						col = 'FFFFFFFF'
					elif authed:
						col = 'FFFFBB33'
					else:
						col = '44FFFFFF'
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
				if aid:
					xbmc.executebuiltin('Addon.OpenSettings(%s)' % aid)

	def onAction(self, action):
		if action.getId() in (9, 10, 92):  # Back / Escape / Nav-Back
			self.close()


# ── Entry point ───────────────────────────────────────────────────────────────

def open_status():
	addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')
	w = StatusDashboard('status.xml', addon_path, 'default', '1080i')
	w.doModal()
	del w
