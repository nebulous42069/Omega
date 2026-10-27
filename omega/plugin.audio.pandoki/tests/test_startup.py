import ast
import collections
import io
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'resources/lib/pandoki/pandoki.py').read_text())
node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Pandoki')
settings = {'delay': '7', 'quality': '2', 'adsize': '1', 'skip': 'false'}
class ApiTimeout(Exception): pass
class ApiError(Exception): pass
ns = {'collections':collections, 'threading':threading, 'time':time,
      'log':lambda *a,**k:None, 'notification':lambda *a:None,
      'Val':lambda k,*a:settings.get(k,''), '_maxdownloads':3,
      'KODIMONITOR':SimpleNamespace(abortRequested=lambda:False),
      'iconart':'icon', '_id':'plugin.audio.pandoki',
      'xbmc':SimpleNamespace(LOGDEBUG=0,LOGINFO=1,LOGERROR=4,executebuiltin=Mock()),
      'mypithos':SimpleNamespace(PithosTimeout=ApiTimeout,PithosNetError=ApiTimeout,
          PithosAuthTokenInvalid=ApiError,PithosAPIVersionError=ApiError,PithosError=ApiError)}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<addon>','exec'),ns)

class StartupTests(unittest.TestCase):
    def setUp(self):
        self.p = ns['Pandoki'].__new__(ns['Pandoki'])
        p=self.p
        p.generation=0;p.pending_station=None;p.downloading=0;p.fetch_lock=threading.Lock()
        p.wait={'next':time.time()+100,'auth':0};p.queue=collections.deque()
        p.ahead={};p.station={'token':'old','title':'Old'};p.songs={};p.abort=False
        p.playlist=Mock();p.playlist.size.return_value=0;p.playlist.getposition.return_value=0
        p.Msg=Mock();p.Fill=Mock();p.mesg=None

    def test_station_switch_dispatches_immediately(self):
        p=self.p
        def tune(token):
            p.station={'token':'new','title':'New'};return True
        p.Tune=tune
        p.Next=Mock()
        p.Play('new')
        self.assertEqual(p.wait['next'],0)
        p.Next.assert_called_once()
        self.assertEqual(p.generation,1)

    def test_old_station_queue_is_discarded(self):
        p=self.p;p.queue.append({'_generation':0})
        p.Tune=lambda _:True;p.Next=Mock()
        p.Play('new');self.assertEqual(len(p.queue),0)
        p.Queue({'_generation':0});self.assertEqual(len(p.queue),0)
        p.Queue({'_generation':1});self.assertEqual(len(p.queue),1)

    def test_fetch_failure_releases_slot(self):
        p=self.p;p.downloading=1;p.Fetch=Mock(side_effect=OSError('offline'))
        p.FetchWorker({'_generation':0})
        self.assertEqual(p.downloading,0)

    def test_stale_worker_skips_fetch_and_releases_slot(self):
        p=self.p;p.downloading=1;p.Fetch=Mock()
        p.FetchWorker({'_generation':-1});p.Fetch.assert_not_called()
        self.assertEqual(p.downloading,0)

    def test_limit_prevents_dispatch(self):
        p=self.p;p.wait['next']=0;p.downloading=3
        p.Next();p.Fill.assert_not_called()

    def test_slot_reserved_before_thread_start(self):
        p=self.p;p.wait['next']=0;p.ahead={'old':collections.deque([{}])}
        class Worker:
            def __init__(self,**kw):pass
            def start(self):
                if p.downloading!=1:raise AssertionError('slot not reserved')
        original=ns['threading'];ns['threading']=SimpleNamespace(Thread=Worker)
        try:p.Next()
        finally:ns['threading']=original
        self.assertEqual(p.downloading,1)

    def test_failed_playlist_request_returns_without_unbound_songs(self):
        p=self.p;del p.Fill;p.Auth=lambda:True;p.pithos=Mock()
        p.pithos.get_playlist.side_effect=ApiTimeout('timeout')
        self.assertFalse(p.Fill())
        self.assertEqual(p.ahead,{})

    def test_new_station_plays_first_ready_song_immediately(self):
        p=self.p;p.once=False;p.pending_station=0;p.player=Mock()
        entries=['old song'];p.playlist.size.side_effect=lambda:len(entries)
        p.playlist.getposition.return_value=0
        p.Add=lambda song:entries.append(song['token'])
        p.queue.append({'token':'new song','_generation':0})
        oldval=ns['Val'];ns['Val']=lambda k,*a:'20'
        ns['xbmcgui']=SimpleNamespace(getCurrentWindowId=lambda:0)
        try:p.Deque()
        finally:ns['Val']=oldval
        p.player.play.assert_called_once_with(p.playlist,startpos=1)
        self.assertIsNone(p.pending_station)

    def test_fullscreen_opens_once_when_station_ready(self):
        p=self.p;p.open_player=True;p.pending_station=0;p.player=Mock()
        p.player.isPlayingAudio.return_value=True
        builtin=ns['xbmc'].executebuiltin;builtin.reset_mock()
        p.ShowPlayer();builtin.assert_not_called()
        p.pending_station=None
        p.ShowPlayer();p.ShowPlayer()
        builtin.assert_called_once_with('ActivateWindow(12006)')
        self.assertFalse(p.open_player)

    def test_fullscreen_waits_for_audio(self):
        p=self.p;p.open_player=True;p.player=Mock()
        p.player.isPlayingAudio.return_value=False
        builtin=ns['xbmc'].executebuiltin;builtin.reset_mock()
        p.ShowPlayer();builtin.assert_not_called()
        self.assertTrue(p.open_player)

    def cache(self, data, expected, error=False):
        p=self.p
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        path=os.path.join(self.temp.name,'song.mp3')
        class Response(io.BytesIO):
            headers={'Content-Length':str(expected)}
            def read(self,n):
                if error:raise socket.timeout('slow')
                return super().read(n)
        response=Response(data)
        p.Proxy=lambda:SimpleNamespace(open=lambda *a,**k:response)
        def rename(a,b):os.replace(a,b);return True
        ns['xbmcvfs']=SimpleNamespace(File=lambda p,m:open(p,m),exists=os.path.exists,
            rename=rename,delete=lambda p:os.remove(p) if os.path.exists(p) else None)
        song={'path_cch':path,'path':path,'url':'https://audio','_generation':0,
              'title':'Song','artist':'Artist','token':'tok','bitrate':128}
        p.Hook=Mock(return_value=True);p.Save=Mock()
        p.Cache(song)
        return song,path,response

    def test_complete_cache_file_is_closed_before_queue(self):
        song,path,response=self.cache(b'abc',3)
        self.assertTrue(response.closed)
        self.assertEqual(Path(path).read_bytes(),b'abc')
        self.assertTrue(song['cached']);self.assertEqual(len(self.p.queue),1)
        self.assertEqual(os.listdir(self.temp.name),['song.mp3'])

    def test_early_eof_is_cleaned_without_queuing(self):
        song,path,response=self.cache(b'a',100)
        self.assertTrue(response.closed);self.assertFalse(os.path.exists(path))
        self.assertEqual(len(self.p.queue),0)
        self.assertEqual(os.listdir(self.temp.name),[])

    def test_timeout_is_cleaned_without_queuing(self):
        song,path,response=self.cache(b'abc',3,True)
        self.assertTrue(response.closed);self.assertEqual(len(self.p.queue),0)
        self.assertEqual(os.listdir(self.temp.name),[])

if __name__=='__main__':unittest.main()
