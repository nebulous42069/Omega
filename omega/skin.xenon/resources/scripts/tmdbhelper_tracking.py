"""Choose all four TMDb Helper tracking sources, then clear and rebuild sync data."""
import xbmc
import xbmcaddon
import xbmcgui
import os
import sys
import xml.etree.ElementTree as ET

SETTING_IDS = (
    'sync_source_watched',
    'sync_source_watchlist',
    'sync_source_collection',
    'sync_source_playback',
)


def clear_sync_and_reload():
    # Load TMDb Helper and its Python dependencies in this script so that
    # ReloadSkin runs only after the sync operation and completion dialog finish.
    visited = set()

    def load_paths(addon_id):
        if addon_id in visited or addon_id.startswith('xbmc.'):
            return
        visited.add(addon_id)
        addon = xbmcaddon.Addon(addon_id)
        path = addon.getAddonInfo('path')
        root = ET.parse(os.path.join(path, 'addon.xml')).getroot()
        for dependency in root.findall('./requires/import'):
            if dependency.get('optional') != 'true':
                load_paths(dependency.get('addon'))
        for extension in root.findall('./extension'):
            if extension.get('point') == 'xbmc.python.module':
                library_path = os.path.join(path, extension.get('library', ''))
                if library_path not in sys.path:
                    sys.path.insert(0, library_path)
        resources = os.path.join(path, 'resources')
        if resources not in sys.path:
            sys.path.insert(0, resources)

    load_paths('plugin.video.themoviedb.helper')
    # TMDb Helper's libraries use Addon() without an ID. A standalone skin
    # script has no default add-on context, so supply it within this interpreter.
    original_addon = xbmcaddon.Addon

    def contextual_addon(id=None):
        return original_addon(id or 'plugin.video.themoviedb.helper')

    xbmcaddon.Addon = contextual_addon
    try:
        from tmdbhelper.lib.script.method.trakt import invalidate_sync
        invalidate_sync('all')
    finally:
        xbmcaddon.Addon = original_addon
    xbmc.executebuiltin('ReloadSkin()')


def main():
    dialog = xbmcgui.Dialog()
    choice = dialog.yesnocustom(
        'TMDb Helper Tracking',
        'Would you like to use Trakt Or Mdblist Tracking?',
        customlabel='',
        nolabel='Trakt',
        yeslabel='MdbList',
    )
    if choice not in (0, 1):
        return
    source = 'Trakt' if choice == 0 else 'MDbList'
    previous = {}
    addon = None
    try:
        addon = xbmcaddon.Addon('plugin.video.themoviedb.helper')
        previous = {key: addon.getSetting(key) for key in SETTING_IDS}
        for key in SETTING_IDS:
            addon.setSetting(key, source)
        if any(addon.getSetting(key) != source for key in SETTING_IDS):
            raise RuntimeError('Unable to verify all four source settings')
    except Exception as error:
        if addon is not None:
            for key, value in previous.items():
                try:
                    addon.setSetting(key, value)
                except Exception:
                    pass
        xbmc.log('TMDb Helper tracking shortcut: %s' % error, xbmc.LOGERROR)
        dialog.ok('TMDb Helper Tracking', 'Could not update the tracking sources. See the Kodi log for details.')
        return
    dialog.notification('TMDb Helper Tracking', 'All four sources set to %s' % source)
    try:
        clear_sync_and_reload()
    except Exception as error:
        xbmc.log('TMDb Helper sync/skin refresh: %s' % error, xbmc.LOGERROR)
        dialog.ok('TMDb Helper Tracking',
                  'Sources were switched, but sync or skin refresh failed. See the Kodi log for details.')


if __name__ == '__main__':
    main()
