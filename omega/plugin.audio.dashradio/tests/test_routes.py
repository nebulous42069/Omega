from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import MagicMock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'resources' / 'lib'))
import catalog

class RouteTests(unittest.TestCase):
    def run_route(self, query):
        modules = {name: MagicMock() for name in ('xbmc', 'xbmcaddon', 'xbmcgui', 'xbmcplugin', 'xbmcvfs')}
        info = {'path': str(ROOT), 'profile': str(ROOT / 'profile'),
                'icon': str(ROOT / 'icon.png'), 'fanart': str(ROOT / 'fanart.jpg')}
        modules['xbmcaddon'].Addon.return_value.getAddonInfo.side_effect = info.get
        modules['xbmcvfs'].translatePath.side_effect = lambda p: p
        stations = catalog.read_file(str(ROOT / 'resources' / 'stations.json'))
        with patch.dict(sys.modules, modules), patch.object(sys, 'argv', ['plugin://plugin.audio.dashradio', '1', query]):
            with patch.object(catalog, 'load', return_value=(stations, 'live')):
                runpy.run_path(str(ROOT / 'main.py'), run_name='__main__')
        return modules

    def test_root_and_all_stations(self):
        self.assertEqual(self.run_route('')['xbmcplugin'].addDirectoryItem.call_count, 17)
        self.assertEqual(self.run_route('?action=all')['xbmcplugin'].addDirectoryItem.call_count, 39)

    def test_genre_and_resolve(self):
        self.assertEqual(self.run_route('?action=listing&genre=Pop')['xbmcplugin'].addDirectoryItem.call_count, 4)
        m = self.run_route('?action=play&station=237')
        self.assertTrue(m['xbmcplugin'].setResolvedUrl.call_args.args[1])
        self.assertIn('/shaqfu', m['xbmcgui'].ListItem.return_value.setPath.call_args.args[0])

    def test_legacy_and_missing_favourites(self):
        self.assertTrue(self.run_route('?action=play&video=https://old.example/5587_128')['xbmcplugin'].setResolvedUrl.call_args.args[1])
        self.assertFalse(self.run_route('?action=play&station=missing')['xbmcplugin'].setResolvedUrl.call_args.args[1])

    def test_manual_refresh(self):
        m = self.run_route('?action=refresh')
        m['xbmc'].executebuiltin.assert_called_once_with('Container.Refresh')
