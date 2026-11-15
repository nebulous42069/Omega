"""Apply the playback presets from Account Manager Lite (GPL-3.0)."""
from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from reauthorize.modules import sync_support


ACTIONS = {
    'setUHD': ('resolution', 0, '4K Max'),
    'setHD': ('resolution', 1, '1080p Max'),
    'setSD': ('resolution', 2, '720p Max'),
    'setDIR': ('playback', 0, 'Source Select'),
    'setAUTO': ('playback', 1, 'Autoplay'),
}
TITLE = 'Diggz Account Manager'
STANDARD_QUALITY = ('0', '1', '2')
QUALITY_LISTS = ('SD, 720p, 1080p, 4K', 'SD, 720p, 1080p', 'SD, 720p')
BOOLEAN_PLAYBACK = ('false', 'true')
RESULT_QUALITY = ('results_quality_movie', 'results_quality_episode')
AUTO_QUALITY = ('autoplay_quality_movie', 'autoplay_quality_episode')
AUTOPLAY = ('auto_play_movie', 'auto_play_episode')
SEREN_PLAYBACK = ('general.playstyleMovie', 'general.playstyleEpisodes')
HOST_MODE_ADDONS = ('homelander', 'nightwing', 'absolution', 'thecrew', 'scrubsv2', 'gratisred')
DATABASE_ADDONS = ('fenlight', 'gears', 'redlight')
SHADOW_FAMILY = ('shadow', 'ghost', 'thechains')
SHADOW_QUALITY = ('max_q', 'max_q_tv', 'max_quality', 'max_quality_tv')

RESOLUTION = {
    **{name: (('hosts.quality',), STANDARD_QUALITY)
       for name in ('umbrella', 'genocide', 'luc_kodi', 'homelander', 'nightwing', 'absolution')},
    **{name: (('general.maxResolution',), STANDARD_QUALITY) for name in ('seren', 'prism')},
    **{name: (SHADOW_QUALITY, ('2', '1', '0')) for name in SHADOW_FAMILY},
    **{name: (('quality.max',), STANDARD_QUALITY) for name in ('scrubsv2', 'gratisred')},
    **{name: (RESULT_QUALITY + AUTO_QUALITY, QUALITY_LISTS)
       for name in DATABASE_ADDONS},
    'pov': (RESULT_QUALITY + AUTO_QUALITY, QUALITY_LISTS),
    'thecrew': (('hosts.quality',), ('0', '2', '3')),
    'otaku': (('general.maxResolution',), ('4', '3', '2')),
    'a4kstreaming': (('general.max_quality',), ('3', '2', '1')),
}
PLAYBACK = {
    **{name: (('hosts.mode',), ('1', '2')) for name in HOST_MODE_ADDONS},
    **{name: (SEREN_PLAYBACK, ('1', '0')) for name in ('seren', 'prism')},
    **{name: (AUTOPLAY, BOOLEAN_PLAYBACK) for name in (*DATABASE_ADDONS, 'pov')},
    'umbrella': (('play.mode.movie', 'play.mode.tv'), ('0', '1')),
    'luc_kodi': (('play.mode',), ('0', '1')),
    'a4kstreaming': (('general.autoplay',), BOOLEAN_PLAYBACK),
    'salts': (('auto_play',), BOOLEAN_PLAYBACK),
    'tmdbmovies': (('auto_play',), BOOLEAN_PLAYBACK),
    '9movies': (('autoplay',), BOOLEAN_PLAYBACK),
    **{name: (('one_click', 'one_click_tv'), BOOLEAN_PLAYBACK) for name in SHADOW_FAMILY},
    'otaku': (('general.playstyle.movie',), ('1', '0')),
}


def _write_database(addon, addon_id, keys, value):
    profile = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    path = os.path.join(profile, 'databases', 'settings.db')
    if not os.path.isfile(path):
        raise ValueError('Open the add-on once to initialize its settings')
    uri = Path(path).resolve().as_uri() + '?mode=rw'
    with closing(sqlite3.connect(uri, uri=True, timeout=3)) as conn, conn:
        for key in keys:
            cursor = conn.execute('UPDATE settings SET setting_value = ? WHERE setting_id = ?', (value, key))
            if cursor.rowcount != 1:
                raise ValueError('Missing or duplicate setting: ' + key)
    options = '&load_properties=false&force=true' if addon_id == 'plugin.video.redlight' else '&isFolder=false'
    xbmc.executebuiltin('RunPlugin(plugin://%s/?mode=sync_settings&silent=true%s)' % (addon_id, options))


def _shadow_schema(addon):
    path = Path(xbmcvfs.translatePath(addon.getAddonInfo('path'))) / 'resources' / 'settings.xml'
    # Some releases ship raw ampersands inside the action URLs. Normalize
    # them for validation in memory while leaving the installed file alone.
    xml = re.sub(rb'&(?!amp;|lt;|gt;|quot;|apos;|#[0-9]+;|#x[0-9a-fA-F]+;)',
                 b'&amp;', path.read_bytes())
    return {node.get('id'): node.get('type') for node in ET.fromstring(xml).iter('setting')}


def _write_kodi_settings(addon, addon_id, name, kind, keys, value):
    schema = addon.schema
    if schema is None and name in SHADOW_FAMILY:
        schema = _shadow_schema(addon)
    if name == 'thecrew' and kind == 'resolution' and schema and 'hosts.quality' not in schema:
        keys = ('quality.max',)
    pov_quality = name == 'pov' and kind == 'resolution'
    if not schema or any(key not in schema or (schema[key] == 'action' and not pov_quality)
                         for key in keys):
        raise ValueError('Expected playback fields are missing from the settings schema')
    for key in keys:
        # The One Click quality menu uses the opposite enum order.
        desired = str(2 - int(value)) if name in SHADOW_FAMILY and key in SHADOW_QUALITY[2:] else value
        raw = xbmcaddon.Addon(addon_id)
        if raw.getSetting(key) == desired:
            continue
        if pov_quality:
            # POV itself saves these action-backed string fields with setSetting.
            raw.setSetting(key, desired)
            if xbmcaddon.Addon(addon_id).getSetting(key) != desired:
                raise ValueError('Setting readback did not match: ' + key)
        else:
            addon.setSetting(key, desired)


def apply(action):
    kind, index, label = ACTIONS[action]
    mappings = RESOLUTION if kind == 'resolution' else PLAYBACK
    updated, failed = [], []
    addon_api = sync_support.addon_api(xbmcaddon)
    sync_support.begin()
    for name, (keys, values) in mappings.items():
        addon_id = 'plugin.video.' + name
        if not sync_support.installed(addon_id):
            continue
        display_name = addon_id
        try:
            addon = addon_api.Addon(addon_id)
            display_name = addon.getAddonInfo('name') or addon_id
            if name in DATABASE_ADDONS:
                _write_database(addon, addon_id, keys, values[index])
            else:
                _write_kodi_settings(addon, addon_id, name, kind, keys, values[index])
            updated.append(display_name)
        except Exception as exc:
            failed.append(display_name)
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            xbmc.log('[%s] %s: %s: %s' % (TITLE, addon_id, label, reason), xbmc.LOGWARNING)
    if not updated and not failed:
        xbmcgui.Dialog().ok(TITLE, 'No supported add-ons are installed for %s.' % label)
        return
    lines = [label]
    if updated:
        lines.append('Applied to ' + ', '.join(updated) + '.')
    if failed:
        lines.append('Could not verify all settings for ' + ', '.join(failed) + '. See kodi.log.')
    xbmcgui.Dialog().ok(TITLE, '[CR][CR]'.join(lines))
