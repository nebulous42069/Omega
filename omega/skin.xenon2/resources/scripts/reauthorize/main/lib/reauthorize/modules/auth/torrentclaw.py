# -*- coding: utf-8 -*-
"""
	Auth Station - TorrentClaw (1.4.4)

	TorrentClaw has no sign-in with a code: its API knows only a personal key (free account, profile ->
	API Keys tab), sent as 'Authorization: Bearer <key>' or ?api_key=. Its terms allow one free key per
	person and forbid one key across many users, so ReAuthorize has no key of its own and never proxies:
	each user types their key here ONCE, and from then on it is backed up and sent to their add-ons like
	any other sign-in (sync/torrentclaw_sync.py). Cosmos is the add-on that uses it.

	The key is checked with one Torznab 'caps' request, which TorrentClaw answers 401 'API key
	required' for no key and for a key it does not know.
"""

import xbmc
import xbmcgui
from reauthorize.modules import control

KEY = 'torrentclaw.api.key'
CHECK_URL = 'https://torrentclaw.com/api/v1/torznab?t=caps'
USER_AGENT = 'ReAuthorize/1.4 (+https://the-hermit.com)'
LOG_TAG = '[ReAuthorize TorrentClaw]'

ACCEPTED, REFUSED, UNKNOWN = 'accepted', 'refused', 'unknown'


def _status(url, key=None):
	"""One GET; the HTTP status, or None when TorrentClaw could not be reached."""
	try:
		from urllib.request import Request, urlopen
		from urllib.error import HTTPError
	except ImportError:
		return None
	headers = {'User-Agent': USER_AGENT, 'Accept': 'application/xml'}
	if key:
		headers['Authorization'] = 'Bearer ' + key
	try:
		return urlopen(Request(url, headers=headers), timeout=15).getcode()
	except HTTPError as e:
		return e.code
	except Exception:
		return None


def check_key(key, status=_status):
	"""ACCEPTED, REFUSED (TorrentClaw does not know the key) or UNKNOWN (no answer, busy, down)."""
	from urllib.parse import quote
	first = status(CHECK_URL, key)
	if first == 200:
		return ACCEPTED
	if first == 401:
		# Torznab clients send the key in the address; try that way once before calling it wrong.
		second = status(CHECK_URL + '&apikey=' + quote(key, safe=''))
		if second == 200:
			return ACCEPTED
		if second in (401, 403):
			return REFUSED
	if first == 403:
		return REFUSED
	return UNKNOWN


def clean(key):
	"""The key as typed, without spaces or line breaks around it; '' if anything odd is inside."""
	key = (key or '').strip().strip('"\'')
	if not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
		return ''
	return key


class TorrentClaw:

	def auth(self, dialog=None, check=check_key):
		dialog = dialog or xbmcgui.Dialog()
		# The first line carries the message: some skins show only that line (AGENTS.md, Dialog text).
		dialog.ok('TorrentClaw',
				  'Type your TorrentClaw key on the next screen.[CR][CR]'
				  'Get it free: sign in at torrentclaw.com, open your profile, API Keys tab, and copy the key. '
				  'You only do this once: ReAuthorize keeps it and gives it to your add-ons.')
		typed = dialog.input('TorrentClaw API key')
		if not typed:
			return False
		key = clean(typed)
		if not key:
			dialog.ok('TorrentClaw', 'Type the key only, no spaces.[CR][CR]Nothing was saved. Try again.')
			return False
		result = check(key)
		xbmc.log('%s key check: %s' % (LOG_TAG, result), xbmc.LOGINFO)
		if result == REFUSED:
			dialog.ok('TorrentClaw', 'TorrentClaw did not accept that key.[CR][CR]'
					  'Check it on your TorrentClaw profile (API Keys tab) and try again. Nothing was saved.')
			return False
		control.setSetting(KEY, key)
		if result == UNKNOWN:
			dialog.ok('TorrentClaw', 'Key saved, but not checked.[CR][CR]'
					  'TorrentClaw could not be reached just now. Your add-ons get the key anyway.')
		return True

	def revoke(self):
		"""Out of ReAuthorize and out of every add-on that holds this key (one typed inside an add-on
		itself is left alone). The key itself stays valid at TorrentClaw: it is reset on the website."""
		key = control.setting(KEY)
		control.setSetting(KEY, '')
		if key:
			try:
				from reauthorize.modules.sync import torrentclaw_sync
				torrentclaw_sync.sign_out(key)
			except Exception as e:
				xbmc.log('%s sign-out from the add-ons failed: %s' % (LOG_TAG, e), xbmc.LOGERROR)
		control.notification(title='TorrentClaw', message='Key removed')
