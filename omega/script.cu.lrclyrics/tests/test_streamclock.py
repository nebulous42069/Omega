import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path('work/script.cu.lrclyrics').resolve()))
from lib.playbackclock import StreamClock

class StreamClockTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.clock = StreamClock(lambda: self.now)

    def tick(self, wall, player=None, blocked=False):
        self.now = wall
        return self.clock.sample(player, blocked)

    def test_station_uptime_is_not_song_time(self):
        self.clock.reset(5400)
        self.assertEqual(self.tick(1, 5401), 1)
        self.assertEqual(self.tick(2, 5402), 2)

    def test_player_stall_freezes(self):
        self.clock.reset(100)
        self.assertEqual(self.tick(1, 101), 1)
        self.assertEqual(self.tick(20, 101), 1)
        self.assertEqual(self.tick(21, 102), 2)

    def test_pause_excludes_elapsed_wall_time(self):
        self.assertEqual(self.tick(1, 0), 1)
        self.tick(2, 0, True)
        self.tick(30, 0, True)
        self.assertEqual(self.tick(31, 0), 1)
        self.assertEqual(self.tick(32, 0), 2)

    def test_buffering_excludes_elapsed_player_time(self):
        self.clock.reset(100)
        self.tick(1, 101)
        self.tick(2, 102, True)
        self.tick(20, 120, True)
        self.assertEqual(self.tick(21, 121), 1)
        self.assertEqual(self.tick(22, 122), 2)

    def test_new_song_resets_without_station_uptime(self):
        self.clock.reset(500)
        self.tick(10, 510)
        self.clock.reset(510)
        self.assertEqual(self.tick(11, 511), 1)

    def test_station_clock_restart_does_not_jump(self):
        self.clock.reset(500)
        self.tick(1, 501)
        self.assertEqual(self.tick(2, 0), 1)
        self.assertEqual(self.tick(3, 1), 2)

    def test_missing_clock_uses_monotonic_elapsed(self):
        self.assertEqual(self.tick(5), 5)
        self.assertEqual(self.tick(12), 12)

    def test_missing_established_clock_freezes_until_rebased(self):
        self.clock.reset(100)
        self.tick(1, 101)
        self.assertEqual(self.tick(10), 1)
        self.assertEqual(self.tick(11, 111), 1)
        self.assertEqual(self.tick(12, 112), 2)
