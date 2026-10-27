# -*- coding: utf-8 -*-
"""
    ReAuthorize - keep its own settings file loadable (1.4.3)

    When Kodi cannot load an add-on's saved settings.xml (cut short because Kodi was closed or
    killed in the middle of a write, edited outside Kodi, ...), it does three things, all read
    from Kodi 21's own code (Addon.cpp, GUIDialogAddonSettings.cpp):
      - the add-on runs on its defaults, so every sign-in looks gone;
      - the settings window opens EMPTY: no heading, no tabs, '?0?' where the page counter is;
      - it refuses to save over the file (CAddon::SaveSettings saves only settings it loaded),
        so nothing written afterwards sticks, not by ReAuthorize and not by Kodi.
    Nothing inside Kodi can repair it. Changing versions keeps the file; only uninstalling with
    the add-on's data removed helped (the Diggz forum, 2026-10-15: Shields on Kodi 21.2, a fresh
    build whose maker had deleted ReAuthorize's addon_data before zipping it).

    So at every start, before anything else reads or writes a setting: write a probe value and
    read it back through a fresh handle. If it does not stick, move the file aside
    (settings.xml.broken, the last one only) so Kodi starts again from defaults, and check
    once more. The start-up then finds no sign-ins and restores them from the backup like after
    any new build. No popup: the user gets back a working ReAuthorize with their sign-ins.
"""

import html
import os
import re
import time
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

ADDON_ID = 'script.module.reauthorize'
PROBE = 'settings.probe'            # a hidden setting (settings.xml, first tab) that only this writes
BROKEN_SUFFIX = '.broken'
LOG_TAG = '[ReAuthorize Settings]'


def _log(message, level=xbmc.LOGINFO):
    xbmc.log('%s %s' % (LOG_TAG, message), level)


def settings_path():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/settings.xml' % ADDON_ID)


def _sticks():
    """Does a value written now come back through a fresh handle (= Kodi loaded and saved the file)?"""
    value = '%d' % int(time.time() * 1000)
    xbmcaddon.Addon(ADDON_ID).setSetting(PROBE, value)
    return xbmcaddon.Addon(ADDON_ID).getSetting(PROBE) == value


def ensure_loadable(retry_wait_ms=1000):
    """
    'ok' (nothing to do), 'repaired' (a file Kodi could not load was moved aside) or 'broken'
    (it could not be moved, or the fresh start did not help either). Never raises.
    """
    path = settings_path()
    try:
        if not os.path.isfile(path):
            return 'ok'                 # Kodi starts from defaults and saves normally
        if _sticks():
            return 'ok'
        # Once more after a moment, in case another process was writing the file just then.
        xbmc.sleep(retry_wait_ms)
        if _sticks():
            return 'ok'
    except Exception as e:
        _log('could not check the settings file: %s' % e, xbmc.LOGWARNING)
        return 'ok'

    size = os.path.getsize(path) if os.path.isfile(path) else 0
    aside = path + BROKEN_SUFFIX
    try:
        if os.path.exists(aside):
            os.remove(aside)
        os.replace(path, aside)
    except Exception as e:
        _log('Kodi cannot load ReAuthorize\'s settings file (%d bytes) and it could not be moved aside: %s'
             % (size, e), xbmc.LOGERROR)
        return 'broken'
    _log('Kodi could not load ReAuthorize\'s settings file (%d bytes); moved it aside as settings.xml%s '
         'and started fresh - sign-ins come back from the backup' % (size, BROKEN_SUFFIX), xbmc.LOGWARNING)
    try:
        if _sticks():
            return 'repaired'
    except Exception as e:
        _log('the fresh settings file could not be checked: %s' % e, xbmc.LOGWARNING)
        return 'repaired'
    _log('settings still do not save after starting fresh', xbmc.LOGERROR)
    return 'broken'


# ---------------------------------------------------------------------------------------------
# The add-ons ReAuthorize sends sign-ins to (1.4.3)
#
# The same trap catches them: log 1004 (2026-10-15, an onn 4K Pro on Kodi 21.3) showed 'failed
# to load user settings' about 240 times for Umbrella, POV, GratisRed, TMDb Helper, ResolveURL,
# TMDb Movies and The Loop. Each ran on its defaults - no debrid, no scrapers - and two plays
# ended 'skipping unplayable item'. Their windows were empty and Kodi would not save, so neither
# the user nor ReAuthorize's sync could put anything back.
#
# Another add-on's file is never written to just to test it. It is READ, and a few of the values
# it holds are compared with what Kodi reports for that add-on: when Kodi answers with its
# defaults for every one, it did not load the file. A file that is not even XML is damaged
# outright. Then the file is moved aside (settings.xml.broken), every value that can still be
# read from it is written back in Kodi's own format, and Kodi is asked again; if it still will
# not take them, the add-on starts from its defaults. Either way the start-up re-sends the
# sign-ins. The add-on's own choices are kept whenever they can be read.
# ---------------------------------------------------------------------------------------------

EXTRA_ADDONS = ('script.module.resolveurl', 'plugin.video.youtube', 'service.scrobbler.lastfm',
                'service.mdblist-scrobbler', 'script.trakt', 'plugin.video.the-loop')
MIN_CHECKS = 3                  # fewer comparable values than this: cannot tell, leave the file alone
MAX_CHECKS = 8
_ROW = re.compile(r'<setting\s+id="([^"]+)"([^>]*?)(?:/>|>(.*?)</setting>)', re.S)
_VALUE_ATTR = re.compile(r'\bvalue="([^"]*)"')
_FILE_VERSION = re.compile(r'<settings\b[^>]*\bversion="(\d+)"')

# The cause Jay found (2026-10-15): a build made on Kodi 22 and backported to Kodi 21. Kodi 22
# writes settings files as version 4, Kodi 19 to 21 as version 2, and Kodi 21 refuses anything
# newer whatever it holds ('unable to read setting values from version 4 (current version: 2)').
# Such a file is damaged on this Kodi even when it holds too few values to compare; its values are
# fine and go back in version 2. Kodi 22 and later read version 2, and their own files are never
# judged by number (their limit is not known here), only by comparison.
NEWEST_VERSION_READ = {19: 2, 20: 2, 21: 2}


def _kodi_major():
    try:
        return int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    except Exception:
        return 0


def _too_new(text):
    """A settings file written by a newer Kodi than this one, which this one will not load."""
    found = _FILE_VERSION.search(text[:500])
    limit = NEWEST_VERSION_READ.get(_kodi_major())
    return bool(found and limit is not None and int(found.group(1)) > limit)


def _read_values(text):
    """
    ('ok' | 'unparsable' | 'refused', {id: value}, ids marked default="true").
    'refused' = XML that Kodi will not load whatever it holds: no <settings> root, or an
    old-format file with no values. An unparsable file's values are read line by line.
    """
    try:
        root = ET.fromstring(text)
    except Exception:
        values = {}
        for sid, attrs, body in _ROW.findall(text):
            attr = _VALUE_ATTR.search(attrs)
            values[html.unescape(sid)] = html.unescape(attr.group(1) if attr else (body or ''))
        return 'unparsable', values, set()
    if root.tag.lower() != 'settings':
        return 'refused', {}, set()
    rows = root.findall('setting')
    new_format = root.get('version') is not None
    if not new_format and not rows:
        return 'refused', {}, set()
    values, defaults = {}, set()
    for row in rows:
        sid = row.get('id')
        if not sid:
            continue
        values[sid] = (row.text or '') if new_format else (row.get('value') or '')
        if row.get('default') == 'true':
            defaults.add(sid)
    return 'ok', values, defaults


def _defined(addon_id):
    """The setting ids an add-on declares in its own resources/settings.xml (both formats)."""
    path = xbmcvfs.translatePath('special://home/addons/%s/resources/settings.xml' % addon_id)
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return set()
    return set(e.get('id') for e in root.iter('setting')
               if e.get('id') and e.get('type') not in ('action', 'lsep', 'sep'))


def _verdict(addon_id, values, defaults, defined):
    """True: Kodi loaded the file. False: it did not. None: not enough values to tell."""
    checks = [(k, v) for k, v in sorted(values.items()) if v and k not in defaults and k in defined][:MAX_CHECKS]
    if len(checks) < MIN_CHECKS:
        return None
    addon = xbmcaddon.Addon(addon_id)
    return any(addon.getSetting(k) == v for k, v in checks)


def _write_new_format(path, values):
    root = ET.Element('settings', version='2')
    for key in sorted(values):
        ET.SubElement(root, 'setting', id=key).text = values[key]
    tmp = path + '.tmp'
    ET.ElementTree(root).write(tmp, encoding='utf-8')
    os.replace(tmp, path)


def _start_from_defaults(addon_id, defined):
    """No file: Kodi loads the defaults and saves again. One write through Kodi makes the file the sync needs."""
    key = sorted(defined)[0]
    addon = xbmcaddon.Addon(addon_id)
    addon.setSetting(key, addon.getSetting(key))


def repair_addon(addon_id):
    """None (healthy, or nothing to judge by), 'repaired' (values kept) or 'reset' (defaults)."""
    if not os.path.isdir(xbmcvfs.translatePath('special://home/addons/%s/' % addon_id)):
        return None
    path = xbmcvfs.translatePath('special://profile/addon_data/%s/settings.xml' % addon_id)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    shape, values, defaults = _read_values(text)
    defined = _defined(addon_id)
    if not defined:
        return None                         # its own definition cannot be read: never guess
    if shape == 'refused' or _too_new(text):
        verdict = False
    else:
        verdict = _verdict(addon_id, values, defaults, defined)
    if verdict or (shape == 'ok' and verdict is None):
        return None

    aside = path + BROKEN_SUFFIX
    if os.path.exists(aside):
        os.remove(aside)
    os.replace(path, aside)
    keep = dict((k, v) for k, v in values.items() if k in defined)
    outcome = 'reset'
    if keep:
        _write_new_format(path, keep)
        check = [(k, v) for k, v in sorted(keep.items()) if v][:MAX_CHECKS]
        addon = xbmcaddon.Addon(addon_id)
        if not check or any(addon.getSetting(k) == v for k, v in check):
            outcome = 'repaired'
        else:
            os.remove(path)                 # Kodi will not take the rebuilt file either
    if outcome == 'reset':
        _start_from_defaults(addon_id, defined)
    _log('%s: Kodi could not load its settings file (%d bytes); moved it aside as settings.xml%s and %s'
         % (addon_id, len(text), BROKEN_SUFFIX,
            'kept %d of its settings' % len(keep) if outcome == 'repaired' else 'started it from its defaults'),
         xbmc.LOGWARNING)
    return outcome


def repair_addons():
    """Check every installed add-on ReAuthorize sends sign-ins to. The ids repaired or reset."""
    try:
        from reauthorize.modules import import_map
        ids = set(import_map.SETTINGS) | set(EXTRA_ADDONS)
    except Exception:
        ids = set(EXTRA_ADDONS)
    fixed = []
    for addon_id in sorted(ids):
        try:
            if repair_addon(addon_id):
                fixed.append(addon_id)
        except Exception as e:
            _log('%s: could not check its settings file: %s' % (addon_id, e), xbmc.LOGWARNING)
    return fixed
