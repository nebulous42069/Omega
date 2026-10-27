import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'resources' / 'lib'))
import catalog

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.bundle = str(ROOT / 'resources' / 'stations.json')
        self.stations = catalog.read_file(self.bundle)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = os.path.join(self.temp.name, 'cache', 'stations.json')

    def test_catalog_integrity_and_genres(self):
        self.assertEqual(len(self.stations), 39)
        self.assertEqual(len(catalog.groups(self.stations)), 15)
        self.assertEqual(len({s['station_id'] for s in self.stations}), 39)
        for s in self.stations:
            self.assertTrue(s['logo_url'].startswith('https://'))
            self.assertNotIn('premium_stream_url', s)

    def test_sse_snapshot_and_heartbeat(self):
        data = b':heartbeat\n\nevent: snapshot\ndata: ' + json.dumps({'stations': self.stations}).encode() + b'\n\n'
        self.assertEqual(catalog.read_snapshot(io.BytesIO(data)), self.stations)

    def test_sse_missing_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            catalog.read_snapshot(io.BytesIO(b'event: song-changed\ndata: {}\n\n'))

    def test_fresh_fetch_is_cached(self):
        with patch.object(catalog, 'fetch', return_value=self.stations) as fetch:
            self.assertEqual(catalog.load(self.cache, self.bundle)[1], 'live')
            self.assertEqual(catalog.load(self.cache, self.bundle)[1], 'cache')
            self.assertEqual(fetch.call_count, 1)

    def test_refresh_bypasses_cache(self):
        with patch.object(catalog, 'fetch', return_value=self.stations) as fetch:
            catalog.load(self.cache, self.bundle)
            self.assertEqual(catalog.load(self.cache, self.bundle, force=True)[1], 'live')
            self.assertEqual(fetch.call_count, 2)

    def test_offline_fallback_and_stale_cache(self):
        with patch.object(catalog, 'fetch', side_effect=OSError('offline')):
            self.assertEqual(catalog.load(self.cache, self.bundle)[1], 'bundled')
        with patch.object(catalog, 'fetch', return_value=self.stations):
            catalog.load(self.cache, self.bundle)
        with patch.object(catalog, 'fetch', side_effect=OSError('offline')):
            self.assertEqual(catalog.load(self.cache, self.bundle, force=True)[1], 'stale cache')

    def test_bad_and_duplicate_catalog_rejected(self):
        for payload in [{}, {'stations': []}, {'stations': self.stations * 2},
                        {'stations': [dict(self.stations[0], stream_url='file:///etc/passwd')]}]:
            with self.assertRaises(ValueError):
                catalog.validate(payload)

    def test_failed_cache_write_preserves_live_result(self):
        with patch.object(catalog, 'fetch', return_value=self.stations):
            with patch.object(catalog.os, 'makedirs', side_effect=OSError('read-only')):
                self.assertEqual(catalog.load(self.cache, self.bundle)[1], 'live')

if __name__ == '__main__':
    unittest.main()
