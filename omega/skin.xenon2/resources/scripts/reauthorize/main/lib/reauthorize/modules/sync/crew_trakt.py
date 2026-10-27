# -*- coding: utf-8 -*-
"""
    ReAuthorize - Trakt in The Crew (1.3.8)

    The Crew (script.module.thecrew 3.x, read from 3.2.9) changed three things that made
    ReAuthorize's old block "sync" Trakt without it ever working (a user's report, 2026-10-04,
    checked against the real code):

    1. Its Trakt app key is no longer written in modules/trakt.py. That file now says
       'CLIENT_ID = keys.trakt_id' / 'CLIENT_SECRET = keys.trakt_secret' and keys.py holds them
       obfuscated, so replacing the old literal key did nothing: Crew sent ReAuthorize's token
       under its own app key, Trakt refused it (401, then invalid_grant on refresh), and Crew
       cleared the tokens and set trakt.revoked itself. The swap is now by line, whatever the
       right-hand side is, and the line remembers what was there so it can be put back.
    2. It is signed in only with trakt.user + trakt.token + trakt.refresh AND trakt.revoked
       false. With the flag still true from an earlier revoke, Crew DELETES whatever is written
       (_purge_stale_credentials_if_revoked). The flag and its window copies are cleared here.
    3. Expiry lives in trakt.expires_at (whole seconds). It is written so Crew does not start
       by renewing the shared, single-use refresh token.

    The old block also compared only the token, so an incomplete sign-in whose token already
    matched was never repaired. Every value is compared now.

    Crew also keeps copies of ALL its settings and can restore sign-ins from them:
    settings.xml.bak and settings.xml.health_backup_<version> beside its settings, and
    thecrew_settings_backup/settings.xml in Kodi's root and (older) in userdata. A wipe that
    only blanks the live settings leaves every sign-in in those files, inside any build made
    from the box. scrub_backups() blanks them there too; link() updates them.
"""

import glob
import os
import re

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from libs.common import var

CREW = 'plugin.video.thecrew'
LOG_TAG = '[ReAuthorize Crew]'
MARK = '# ReAuthorize; was: '

_KEY_LINE = re.compile(r'^(?P<name>CLIENT_ID|CLIENT_SECRET)(?P<eq>\s*=\s*)(?P<value>[^#\r\n]*?)(?P<tail>\s*(?:#.*)?)$',
                       re.M)
_MARKED = re.compile(r'^(CLIENT_ID|CLIENT_SECRET)(\s*=\s*).*?' + re.escape(MARK) + r'(.+?)\s*$', re.M)

# Crew's own names for the Trakt and Simkl sign-in (settings_repair.py), which import_map
# cannot know: it only lists what ReAuthorize writes.
_CREW_SIGNIN_IDS = ('trakt.user', 'trakt.token', 'trakt.refresh', 'trakt.expires_at', 'trakt.expires',
                    'trakt.auth', 'simkl.user', 'simkl.token')
_WINDOW_FLAGS = ('thecrew.trakt_revoked', 'thecrew.trakt_auth_failed', 'thecrew.trakt_auth_notified',
                 'thecrew.trakt_revoked_creds_purged')


def _log(message):
    xbmc.log('%s %s' % (LOG_TAG, message), xbmc.LOGINFO)


def installed():
    return xbmcvfs.exists(var.chk_crew)


def swap_key(text, client, secret):
    """Crew's trakt.py with ReAuthorize's app key on the CLIENT_ID / CLIENT_SECRET lines."""
    ours = {'CLIENT_ID': client, 'CLIENT_SECRET': secret}

    def swap(m):
        if m.group('value').strip().strip('\'"') == ours[m.group('name')]:
            return m.group(0)
        return "%s%s'%s'  %s%s" % (m.group('name'), m.group('eq'), ours[m.group('name')], MARK, m.group('tail').split(MARK, 1)[1].strip() if MARK in m.group('tail') else m.group('value').strip())
    swapped = _KEY_LINE.sub(swap, text)
    # Older Crew versions wrote the key itself in this file.
    return swapped.replace(var.crew_client, client).replace(var.crew_secret, secret)


def restore_key(text):
    """The reverse: every marked line gets back what it said before."""
    return _MARKED.sub(lambda m: '%s%s%s' % (m.group(1), m.group(2), m.group(3)), text)


def ensure_key():
    """Make sure Crew uses ReAuthorize's Trakt app key. True if the file is right (or was made right)."""
    try:
        with open(var.path_crew, encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return False
    swapped = swap_key(text, var.client_am, var.secret_am)
    values = {match.group('name'): match.group('value').strip().strip("'\"") for match in _KEY_LINE.finditer(swapped)}
    if values.get('CLIENT_ID') != var.client_am or values.get('CLIENT_SECRET') != var.secret_am:
        return False
    if swapped == text:
        return True
    try:
        with open(var.path_crew, 'w', encoding='utf-8') as f:
            f.write(swapped)
        _log('Trakt app key set in The Crew')
        return True
    except Exception as e:
        _log('could not set the Trakt app key in The Crew: %s' % e)
        return False


def _expires_at(expires):
    try:
        return str(int(float(expires)))
    except (TypeError, ValueError):
        return ''


def _clear_window_flags():
    try:
        window = xbmcgui.Window(10000)
        for name in _WINDOW_FLAGS:
            window.clearProperty(name)
    except Exception:
        pass


def link(username, token, refresh, expires):
    """Give The Crew ReAuthorize's Trakt sign-in, complete. True if anything was written."""
    if not (installed() and token):
        return False
    if not ensure_key():
        raise RuntimeError('Crew Trakt application identity could not be verified')
    wanted = [('trakt.user', username), ('trakt.token', token), ('trakt.refresh', refresh),
              ('trakt.expires_at', _expires_at(expires)), ('trakt.revoked', 'false')]
    addon = xbmcaddon.Addon(CREW)
    changed = False
    for key, value in wanted:
        if key == 'trakt.expires_at' and not value:
            continue
        if addon.getSetting(key) != value:
            addon.setSetting(key, value)
            changed = True
    _clear_window_flags()
    if changed:
        _patch_backups(dict(wanted))
    return changed


# --- Crew's own copies of its settings ---------------------------------------------------

def backup_files():
    """Every file in which The Crew keeps a copy of its settings, that exists."""
    data = xbmcvfs.translatePath('special://profile/addon_data/%s/' % CREW)
    home = xbmcvfs.translatePath('special://home/').rstrip('\\/')
    profile = xbmcvfs.translatePath('special://profile/').rstrip('\\/')
    paths = [os.path.join(data, 'settings.xml.bak')]
    paths += sorted(glob.glob(os.path.join(data, 'settings.xml.health_backup_*')))
    paths += sorted(glob.glob(os.path.join(data, 'settings*.bak')))
    paths.append(os.path.join(os.path.dirname(home), 'thecrew_settings_backup', 'settings.xml'))
    paths.append(os.path.join(profile, 'thecrew_settings_backup', 'settings.xml'))
    return [p for p in paths if os.path.isfile(p)]


def _set_in_xml(text, values):
    """Kodi settings XML with these ids set to these values, where the ids are present."""
    from xml.sax.saxutils import escape
    changed = False
    for key, value in values.items():
        value = escape(str(value))
        pattern = re.compile(r'(<setting\s+id="%s"[^>]*?)(?:\s*/>|>([^<]*)</setting>)' % re.escape(key))

        def put(m, value=value):
            head = re.sub(r'\s+default="true"', '', m.group(1))
            return '%s>%s</setting>' % (head, value) if value else '%s />' % head
        new = pattern.sub(put, text)
        if new != text:
            text, changed = new, True
    return text, changed


def _patch_backups(values):
    count = 0
    for path in backup_files():
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
            new, changed = _set_in_xml(text, values)
            if changed:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new)
                count += 1
        except Exception as e:
            _log('could not update %s: %s' % (os.path.basename(path), e))
    return count


def _signin_ids():
    ids = set(_CREW_SIGNIN_IDS)
    try:
        from reauthorize.modules import import_map
        ids.update(getattr(import_map, 'SETTINGS', {}).get(CREW, {}))
    except Exception:
        pass
    return ids


def scrub_backups():
    """Blank every sign-in in Crew's copies of its settings. Returns how many files changed."""
    values = dict((key, '') for key in _signin_ids())
    values['trakt.revoked'] = 'true'       # so Crew does not put a sign-in back from anywhere else
    return _patch_backups(values)


def wipe():
    """
    Part of a full wipe (sync/trakt_wipe.py): the live Trakt fields import_map does not list,
    Crew's 'revoked' flag set so it will not restore a sign-in from a copy, and the copies
    themselves. True if anything changed.
    """
    if not installed():
        return False
    changed = False
    try:
        addon = xbmcaddon.Addon(CREW)
        for key in ('trakt.expires_at', 'trakt.expires', 'trakt.auth'):
            if addon.getSetting(key):
                addon.setSetting(key, '')
                changed = True
        if addon.getSetting('trakt.revoked') != 'true':
            addon.setSetting('trakt.revoked', 'true')
            changed = True
    except Exception as e:
        _log('could not clear The Crew: %s' % e)
    scrubbed = scrub_backups()
    if scrubbed:
        _log('sign-ins removed from %d of The Crew\'s settings copies' % scrubbed)
    return changed or bool(scrubbed)
