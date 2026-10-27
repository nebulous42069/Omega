import ast
import re
import unittest
from bisect import bisect_right
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

source = Path('work/script.cu.lrclyrics/lib/gui.py').read_text()
tree = ast.parse(source)
methods = {}
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name in ('GUI', 'MAIN'):
        methods[node.name] = node
ns = {'re': re, 'bisect_right': bisect_right}
for name, names in {'GUI': ['parser_lyrics', 'match_pattern', 'refresh', 'save_sync'],
                    'MAIN': ['save_lyrics_to_file', 'monitor_stream_metadata', 'myPlayerChanged']}.items():
    node = methods[name]
    node.bases = []
    node.body = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<addon>', 'exec'), ns)

class TimingTests(unittest.TestCase):
    def gui(self, text, strip=False):
        g = ns['GUI']()
        g.matchlist = []
        g.SETTING_OFFSET = 0
        g.SETTING_STRIP = strip
        g.parser_lyrics(text)
        return g

    def test_fraction_precision(self):
        g = self.gui('[00:01.5]a\n[00:02.25]b\n[00:03.125]c\n[00:04:750]d\n[00:05]e')
        self.assertEqual(g.overlay_times[1:], [1.5, 2.25, 3.125, 4.75, 5])

    def test_multiple_mixed_tags(self):
        g = self.gui('[00:01.125][00:04][00:07.5]same')
        self.assertEqual(g.pOverlay[1:], [(1.125, 'same'), (4, 'same'), (7.5, 'same')])

    def test_signed_offset_and_sorted_negative_times(self):
        g = self.gui('[offset: +1500]\n[00:01]a\n[00:02]b')
        self.assertEqual(g.overlay_times[1:], [-0.5, 0.5])
        self.assertEqual(sorted(g.overlay_times), g.overlay_times)
        self.assertEqual(self.gui('[offset:-250]\n[00:01]a').overlay_times[1], 1.25)

    def test_clock_seeks_pause_last_line_and_offsets(self):
        g = self.gui('[00:10]a\n[00:20]b\n[00:30]c')
        g.allowtimer = True
        g.syncadjust = 0
        g.scroll_line = 2
        g.text = Mock()
        g.text.size.return_value = 4
        selected = [0]
        g.text.getSelectedPosition.side_effect = lambda: selected[0]
        g.text.selectItem.side_effect = lambda p: selected.__setitem__(0, p)
        ns['ADDON'] = SimpleNamespace(getSettingNumber=lambda _: g.SETTING_OFFSET)
        for clock, offset, adjust, expected in [(20,0,0,2),(15,0,0,1),(35,0,0,3),
              (0,0,0,0),(10,0,0,1),(10,0,0,1),(10,2,0,0),(10,0,10,2)]:
            g.playback_time = lambda: clock
            g.SETTING_OFFSET, g.syncadjust = offset, adjust
            g.refresh()
            self.assertEqual(selected[0], expected)

    def test_transient_player_failure_recovers(self):
        g = self.gui('[00:01]a')
        g.allowtimer = True
        g.playback_time = Mock(side_effect=RuntimeError('stopped'))
        ns['ADDON'] = SimpleNamespace(getSettingNumber=lambda _: 0)
        g.refresh()

    def test_saved_adjustments_are_deltas(self):
        g = self.gui('')
        g.saved_syncadjust = 0
        g.save = Mock()
        lyric = object()
        g.lyrics = lyric
        for val in [2, 3, 3, 0]:
            g.save_sync(lyric, val)
        self.assertEqual([c.args[1] for c in g.save.call_args_list], [2, 1, -3])

    def test_metadata_polling_selects_continuous_streams(self):
        m = ns['MAIN']()
        m.SETTING_INTERNETRADIO = False
        m.MyPlayer = Mock()
        ns['xbmc'] = SimpleNamespace(getCondVisibility=lambda _: True)
        for duration, expected in [(0, True), (180, False)]:
            m.MyPlayer.getTotalTime.return_value = duration
            self.assertEqual(m.monitor_stream_metadata(), expected)
        m.SETTING_INTERNETRADIO = True
        self.assertTrue(m.monitor_stream_metadata())
        ns['xbmc'] = SimpleNamespace(getCondVisibility=lambda _: False)
        self.assertFalse(m.monitor_stream_metadata())

    def test_radio_anchor_survives_redisplay_and_resets_on_new_song(self):
        m = ns['MAIN']()
        m.CULRC_FIRSTRUN = True
        m.lyricssettings = {}
        m.DEBUG = False
        m.timing_key = None
        m.streamclock = Mock()
        m.MyPlayer = Mock()
        m.MyPlayer.getTotalTime.return_value = 0
        m.MyPlayer.getTime.return_value = 500
        song = SimpleNamespace(filepath='https://station/stream', artist='Artist', title='One')
        ns['Song'] = SimpleNamespace(current=lambda **kw: song)
        ns['xbmc'] = SimpleNamespace(getCondVisibility=lambda _: True)
        ns['log'] = lambda *a, **kw: None
        m.proceed = lambda: False
        m.get_lyrics = lambda *args: SimpleNamespace(song=song, lyrics='[00:01]words')
        for title in ['One', 'One', 'Two']:
            song.title = title
            m.current_lyrics = SimpleNamespace(song=None)
            m.myPlayerChanged()
        self.assertEqual(m.streamclock.reset.call_count, 2)
        self.assertEqual(m.timing_key[-1], 'Two')

    def test_offset_tag_save_without_newline(self):
        m = ns['MAIN']()
        m.SETTING_SAVE_LYRICS1LRC = True
        m.SETTING_SAVE_LYRICS1TXT = m.SETTING_SAVE_LYRICS2LRC = m.SETTING_SAVE_LYRICS2TXT = False
        m.write_lyrics_file = Mock()
        lyric = SimpleNamespace(lyrics='[offset:500][00:01]a', lrc=True,
                                song=SimpleNamespace(path1=lambda _: 'test.lrc'))
        m.save_lyrics_to_file(lyric, 0.25)
        self.assertEqual(m.write_lyrics_file.call_args.args[1], '[offset:750]\n[00:01]a')

if __name__ == '__main__':
    unittest.main()
