import collections, re, socket, sys, threading, time, os
import traceback
import urllib, urllib3
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs

import mypithos
from musicbrainzngs import set_useragent, search_recordings

_addon	= xbmcaddon.Addon()
_base	= sys.argv[0]
_id	= _addon.getAddonInfo('id')
_version	= _addon.getAddonInfo('version')
_stamp	= str(time.time())
_debug = _addon.getSetting('debug') == 'true'
_notification = _addon.getSetting('notification') == 'true'
 
# xbmc.LOGDEBUG = 0
# xbmc.LOGERROR = 4
# xbmc.LOGFATAL = 6
# xbmc.LOGINFO = 1
# xbmc.LOGNONE = 7
# xbmc.LOGNOTICE = 2
# xbmc.LOGSEVERE = 5
# xbmc.LOGWARNING = 3

KODIMONITOR = xbmc.Monitor()
CA_CERTS = xbmcvfs.translatePath('special://system/certs/cacert.pem')


# setup the ability to provide notification to the Kodi GUI
iconart = xbmcvfs.translatePath(os.path.join('special://home/addons/plugin.audio.pandoki',  'icon.png'))


def log(msg, s = None, level = xbmc.LOGDEBUG):
    if _debug == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    if s and s.get('artist'): xbmc.log("%s-%s %s %s '%s - %s'" % (_id, _version, msg, s['token'][-4:], s['artist'], s['title']), level) # song
    elif s:                   xbmc.log("%s-%s %s %s '%s'"      % (_id, _version, msg, s['token'][-4:], s['title']), level)              # station
    else:                     xbmc.log("%s-%s %s"              % (_id, _version, msg), level)


def notification(title, message, ms, nart):
    if _notification == False: return
    xbmc.executebuiltin("Notification(" + title + "," + message + "," + ms + "," + nart + ")")


def Val(key, val = None):
    if key in [ 'author', 'changelog', 'description', 'disclaimer', 'fanart', 'icon', 'id', 'name', 'path', 'profile', 'stars', 'summary', 'type', 'version' ]:
        return _addon.getAddonInfo(key)

    if val:      _addon.setSetting(key, val)
    else: return _addon.getSetting(key)


def Prop(key, val = 'get'):
    if val == 'get':
        retVal = xbmcgui.Window(10000).getProperty("%s.%s" % (_id, key))
        log('def Prop %s=%s value=%s' % (key, val, retVal), None, xbmc.LOGDEBUG)
        return retVal
    else:
        log('def Prop %s=%s ' % (key, val), None, xbmc.LOGDEBUG)
        xbmcgui.Window(10000).setProperty("%s.%s" % (_id, key), val)


_maxdownloads=int(Val('maxdownload'))

class Pandoki(object):
    def __init__(self):
        run = Prop('run')
        if run and time.time() < float(run) + 3: return

        Prop('run', str(time.time()))
        Prop('stamp', _stamp)

        self.once	= True
        self.downloading = 0  # reserved fetch workers, including connection setup
        self.fetch_lock = threading.Lock()
        self.generation = 0
        self.pending_station = None
        self.open_player = False
        self.abort	= False
        self.mesg	= None
        self.station	= None
        self.stations	= None
        self.songs	= { }
        self.pithos	= mypithos.Pithos()
        self.player	= xbmc.Player()
        self.playlist	= xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        self.ahead	= { }
        self.queue	= collections.deque()
        self.prof	= Val('prof')
        self.wait	= { 'auth' : 0, 'stations' : 0, 'flush' : 0, 'scan' : 0, 'next' : 0 }
        self.silent	= xbmcvfs.translatePath("special://home/addons/%s/resources/media/silent.m4a" % _id)

        set_useragent("kodi.%s" % _id, Val('version'))
        xbmcvfs.mkdirs(xbmcvfs.translatePath(Val('cache')))
        xbmcvfs.mkdirs(xbmcvfs.translatePath(Val('library')))
        self.Flush()

    def Proxy(self):
        log('def Proxy')
        proxy = Val('proxy')

        if proxy == '1':	# None
            hand = urllib.request.ProxyHandler({})
            return urllib.request.build_opener(hand)

        elif proxy == '0':	# Global
            if Val('sni') == 'true':
                return urllib3.PoolManager(
                    cert_reqs='CERT_REQUIRED',
                    ca_certs=CA_CERTS
                )
            else:
                return urllib.request.build_opener()

        elif proxy == '2':	# Custom
            if Val('sni') == 'true':
                auth_header = urllib3.make_headers(proxy_basic_auth='%s:%s' % (Val('proxy_user'), Val('proxy_pass')))
                return urllib3.ProxyManager('http://%s:%s/' % (Val('proxy_host'), Val('proxy_port')), proxy_headers=auth_header)
            else:
                http = 'http://%s:%s@%s:%s' % (Val('proxy_user'), Val('proxy_pass'), Val('proxy_host'), Val('proxy_port'))
                hand = urllib.request.ProxyHandler({ 'http' : http, 'https' : http })
                return urllib.request.build_opener(hand)


    def Auth(self):
        log('def Auth')
        p = Val('prof')
        if self.prof != p:
            self.wait['auth'] = 0
            self.stations = None
            self.prof = p

        if time.time() < self.wait['auth']: return True

        self.pithos.set_url_opener(self.Proxy(), (Val('sni') == 'true'))

        try: self.pithos.connect(Val('one' + p), Val('username' + p), Val('password' + p))
        except mypithos.PithosError:
            log('Auth  Failed')
            return False

        self.wait['auth'] = time.time() + (60 * 60)	# Auth every hour
        log('Auth  OK')
        return True


    def Login(self):
        log('def Login')
        # if (Val('sni') == 'true') and (not _urllib3):
        #     if xbmcgui.Dialog().yesno(Val('name'), 'SNI Support not found', 'Please install: pyOpenSSL/ndg-httpsclient/pyasn1', 'Check Settings?'):
        #         xbmcaddon.Addon().openSettings()
        #     else:
        #         exit()

        while not self.Auth():
            if xbmcgui.Dialog().yesno(Val('name'), '          Login Failed', 'Bad User/Pass/Proxy', '       Check Settings?'):
                xbmcaddon.Addon().openSettings()
            else:
                exit()


    def Stations(self):
        log('def Stations')
        if (self.stations) and (time.time() < self.wait['stations']):
            return self.stations

        if not self.Auth(): return None
        self.stations = self.pithos.get_stations()

        self.wait['stations'] = time.time() + (60 * 5)				# Valid for 5 mins
        return self.stations


    def Sorted(self):
        log('def Sorted')
        sort = Val('sort')
        stations = list(self.Stations())
        quickmix = stations.pop(0)						# Quickmix

        if   sort == '0': stations = stations					# Normal
        elif sort == '2': stations = stations[::-1]				# Reverse
        elif sort == '1': stations = sorted(stations, key=lambda s: s['title'])	# A-Z

        stations.insert(0, quickmix)						# Quickmix back on top
        return stations


    def Dir(self, handle):
        log('def Dir')
        self.Login()

        ic = Val('icon')
        li = xbmcgui.ListItem('New Station ...')
        li.setArt({'icon': ic, 'thumb': ic})
        xbmcplugin.addDirectoryItem(int(handle), "%s?search=hcraes" % _base, li, True)

        for s in self.Sorted():
            li = xbmcgui.ListItem(s['title'], s['token'])
            if self.station == s: li.select(True)

            art = Val("art-%s" % s['token'])
            if not art: art = s.get('art', ic)

            li.setArt({'icon': art, 'thumb': art})

            title = s['title']
            rurl = "RunPlugin(plugin://%s/?%s)" % (_id, urllib.parse.urlencode({ 'rename' : s['token'], 'title' : title }))
            durl = "RunPlugin(plugin://%s/?%s)" % (_id, urllib.parse.urlencode({ 'delete' : s['token'], 'title' : title }))
            surl = "RunPlugin(plugin://%s/?%s)" % (_id, urllib.parse.urlencode({  'thumb' : s['token'], 'title' : title }))

            li.addContextMenuItems([('Rename Station', rurl),
                                    ('Delete Station', durl),
                                    ('Select Thumb',   surl), ])

            burl = "%s?%s" % (_base, urllib.parse.urlencode({ 'play' : s['token'] }))
            xbmcplugin.addDirectoryItem(int(handle), burl, li)

        xbmcplugin.endOfDirectory(int(handle), cacheToDisc = False)
        # wait for the window to appear in Kodi before continuing
        KODIMONITOR.waitForAbort(0.1)
        log("Dir   OK %4s" % handle)


    def Search(self, handle, query):
        log('def Search %s ' % query)
        self.Login()

        for s in self.pithos.search(query, True):
            title = s['artist']
            title += (' - %s' % s['title']) if s.get('title') else ''

            li = xbmcgui.ListItem(title, s['token'])
            xbmcplugin.addDirectoryItem(int(handle), "%s?create=%s" % (_base, s['token']), li)

        xbmcplugin.endOfDirectory(int(handle), cacheToDisc = False)
        log("Search   %4s '%s'" % (handle, query))


    def Info(self, s):
        log('def Info')
        info = { 'artist' : s['artist'], 'album' : s['album'], 'title' : s['title'], 'rating' : s['rating'], 'mediatype':'song' }

        if s.get('duration'):
            info['duration'] = s['duration']

        return info


    def Add(self, song):
        log('def Add ', song)
        if song['token'] != 'mesg':
            self.songs[song['token']] = song

        # This line adds the line in the playlist on Kodi GUI
        li = xbmcgui.ListItem(song['artist'], song['title'])
        li.setArt({'icon': song['art'], 'thumb': song['art']})
        li.setProperty("%s.token" % _id, song['token'])
        li.setInfo('music', self.Info(song))

        if song.get('encoding') == 'm4a': li.setProperty('mimetype', 'audio/aac')
        if song.get('encoding') == 'mp3': li.setProperty('mimetype', 'audio/mpeg')

        log('def Add  adding %s' % song['path'], song)
        self.playlist.add(song['path'], li)
        self.Scan(False)
        log('Add   OK', song)


    def Queue(self, song):
        log('def Queue ', song)
        if song.get('_generation', self.generation) == self.generation:
            self.queue.append(song)


    def Msg(self, msg):
        log('def Msg %s ' % msg, None, xbmc.LOGDEBUG)
        if self.mesg == msg: return
        else: self.mesg = msg
        
        # added ready (true if file is ready to play and starttime to know how
        # long it has been taking to download file
        song = { 'starttime' : time.time(), 'ready' : False, 'token' : 'mesg', 'title' : msg, 'path' : self.silent, 'artist' : Val('name'),  'album' : Val('description'), 'art' : Val('icon'), 'rating' : '' }
        self.Queue(song)


    def Tag(self, song):
        log('def Tag', song)
        try:
            res = search_recordings(limit = 1, query = song['title'], artist = song['artist'], release = song['album'], qdur = str(song['duration'] * 1000))['recording-list'][0]
            song['number'] = int(res['release-list'][0]['medium-list'][1]['track-list'][0]['number'])
            song['count']  =     res['release-list'][0]['medium-list'][1]['track-count']
            song['score']  =     res['ext:score']
            song['brain']  =     res['id']

        except:
            song['score']  = '0'

        log("Tag%4s%%" % song['score'], song, xbmc.LOGINFO)
        return song['score'] == '100'


    def Save(self, song):
        log('def Save ', song)
        if song['title'] == 'Advertisement' or song.get('saved') or not song.get('cached', False): return
        if Val('mode') in ('0', '1') or (Val('mode') == '3' and song.get('voted') != 'up'): return
        if not self.Tag(song): return

        tmp = "%s.%s" % (song['path'], song['encoding'])
        if not xbmcvfs.copy(song['path_cch'], tmp):
            log('Save Failed', song, xbmc.LOGINFO)
            return

        if   song['encoding'] == 'm4a': tag = EasyMP4(tmp)
        elif song['encoding'] == 'mp3': tag = MP3(tmp, ID3 = EasyID3)

        if tag == None:
            log('Save Failed', song, xbmc.LOGINFO)
            xbmcvfs.delete(tmp)
            return

        tag['tracknumber']         = "%d/%d" % (song['number'], song['count'])
        tag['musicbrainz_trackid'] = song['brain']
        tag['artist']              = song['artist']
        tag['album']               = song['album']
        tag['title']               = song['title']
        log("Save: metadata %s %s %s %s %s" % (song['brain'], song['artist'], song['album'], song['title']), song)

        if song['encoding'] == 'mp3':
            tag.save(v2_version = 3)
        else:
            tag.save()

        xbmcvfs.mkdirs(song['path_dir'])
        xbmcvfs.copy(tmp, song['path_lib'])
        xbmcvfs.delete(tmp)
        log('Save: Song Cached ', song)

        song['saved'] = True

        if song.get('art', False) and not xbmcvfs.exists(song['path_alb']) or not xbmcvfs.exists(song['path_art']):
            try:
                strm = self.Proxy().open(song['art'])
                data = strm.read()
            except ValueError:
                log("Save ART      '%s'" % song['art'], None, xbmc.LOGINFO)
                return

            for jpg in [ song['path_alb'], song['path_art'] ]:
                if not xbmcvfs.exists(jpg):
                    file = xbmcvfs.File(jpg, 'wb')
                    file.write(data)
                    file.close()

        log('Save  OK', song)


    def Hook(self, song, size, totl):
        log('def Hook ', song)
        if totl in (341980, 340554, 173310):	# empty song cause requesting to fast
            self.Msg('Too Many Songs Requested')
            log('Cache MT', song, xbmc.LOGINFO)
            return False

        if song['title'] != 'Advertisement' and totl <= int(Val('adsize')) * 1024:
            log('Cache AD', song, xbmc.LOGINFO)

            song['artist'] = Val('name')
            song['album']  = Val('description')
            song['art']    = Val('icon')
            song['title']  = 'Advertisement'

            if Val('skip') == 'true':
                song['qued'] = True
                self.Msg('Skipping Small Songs')

        log('Cache QU: ready=%s size=%8d bitrate:%8d' % (song.get('ready'), size, song['bitrate']), song)
        if song.get('ready',False) and not song.get('qued') and size >= (song['bitrate'] / 8 * 1024 * int(Val('delay'))):
            song['qued'] = True
            self.Queue(song)

        return True


    def Cache(self, song):
        log('def Cache ', song)
        strm, file = None, None
        size, totl, complete = 0, 0, False
        partial = song['path_cch'] + '.part.%s.%s' % (song.get('_generation', 0), threading.get_ident())
        try:
            # Audio failures are not authentication failures. Retrying login
            # here stalled other work and did not refresh this signed audio URL.
            opener = self.Proxy()
            if hasattr(opener, 'open'):
                strm = opener.open(song['url'], timeout=10)
            else:
                strm = opener.urlopen('GET', song['url'], preload_content=False,
                                      timeout=10, retries=False)
            totl = int(strm.headers['Content-Length'])
            if totl <= 0 or not self.Hook(song, 0, totl):
                return
            file = xbmcvfs.File(partial, 'wb')
            song['starttime'] = time.time()
            notification('Caching', '[COLOR lime]' + song['title'] + ' [/COLOR]', '3000', iconart)
            while (size < totl and not KODIMONITOR.abortRequested() and not self.abort
                   and song.get('_generation', self.generation) == self.generation):
                data = strm.read(min(65536, totl - size))
                if not data:
                    # EOF before Content-Length is a failed download, not a
                    # reason to spin on empty reads for another minute.
                    break
                file.write(data)
                size += len(data)
            complete = (size == totl)
        except Exception:
            log('Audio cache download failed', song, xbmc.LOGERROR)
        finally:
            if file is not None:
                file.close()
            if strm is not None:
                strm.close()
            if not complete and file is not None:
                xbmcvfs.delete(partial)
        if complete and song.get('_generation', self.generation) == self.generation:
            if xbmcvfs.exists(song['path_cch']):
                xbmcvfs.delete(partial)
            elif not xbmcvfs.rename(partial, song['path_cch']):
                xbmcvfs.delete(partial)
                log('Could not finalize cached song', song, xbmc.LOGERROR)
                return
            song['ready'] = True
            song['cached'] = True
            # Queue only after close, so Kodi sees a complete file. Small files
            # below the old buffer threshold must not get stuck forever.
            if self.Hook(song, size, totl) and not song.get('qued'):
                song['qued'] = True
                self.Queue(song)
            self.Save(song)
        elif complete:
            xbmcvfs.delete(partial)

    def Fetch(self, song):
        log('def Fetch ', song)
        if xbmcvfs.exists(song['path_mp3']):	# Found MP3 in Library
            log('Song MP3', song, xbmc.LOGINFO)
            song['path_lib'] = song['path_mp3']
            song['path'] = song['path_lib']
            song['saved'] = True

        elif xbmcvfs.exists(song['path_m4a']):	# Found M4A in Library
            log('Song M4A', song, xbmc.LOGINFO)
            song['path_lib'] = song['path_m4a']
            song['path'] = song['path_lib']
            song['saved'] = True

        elif xbmcvfs.exists(song['path_cch']):	# Found in Cache
            log('Song CCH', song, xbmc.LOGINFO)
            song['path'] = song['path_cch']

        elif Val('mode') == '0':		# Stream Only
            log('Song PAN', song, xbmc.LOGINFO)
            song['path'] = song['url']

        else:					# Cache / Save
            log('Song GET', song, xbmc.LOGINFO)
            song['path'] = song['path_cch']
            self.Cache(song)
            return

        self.Queue(song)



    def Seed(self, song):
        log('def Seed')
        if not self.Stations(): return
        result = self.pithos.search("%s by %s" % (song['title'], song['artist']))[0]

        if result['title'] == song['title'] and result['artist'] == song['artist']:
            self.pithos.seed_station(song['station'], result['token'])
        else:
            log('Seed BAD', song)


    def Branch(self, song):
        log('def Branch')
        if not self.Stations(): return
        station = self.pithos.branch_station(song['token'])

        Prop('play', station['token'])
        Prop('action', 'play')

        log('Branch  ', song, xbmc.LOGINFO)


#    def Del(self, song):
#        xbmcvfs.delete(song['path_lib'])


    def Rate(self, mode):
        log('def Rate')
        pos  = self.playlist.getposition()
        item = self.playlist[pos]
        tokn = item.getProperty("%s.token" % _id)
        song = self.songs.get(tokn)

        if not song:
            return

        elif mode == 'branch':
            self.Branch(song)
            return

        elif mode == 'seed':
            self.Seed(song)

        elif mode == 'up':
            song['voted'] = 'up'
            Prop('voted', 'up')
            self.pithos.add_feedback(song['token'], True)
            notification('Thumb UP', song['title'], '3000', iconart)
            self.Save(song)

        elif mode == 'tired':
            self.player.playnext()
            self.pithos.set_tired(song['token'])

        elif mode == 'down':
            song['voted'] = 'down'
            Prop('voted', 'down')
            self.player.playnext()
            self.pithos.add_feedback(song['token'], False)
            notification('Thumb DOWN', song['title'], '3000', iconart)

        elif mode == 'clear':
            song['voted'] = ''
            Prop('voted', '')
            feedback = self.pithos.add_feedback(song['token'], True)
            self.pithos.del_feedback(song['station'], feedback)
            notification('Thumb CLEARED', song['title'], '3000', iconart)

        else: return

        log("%-8s" % mode.title(), song, xbmc.LOGINFO)


    def Rated(self, song, rating):
        log("Rate %1s>%1s" % (song['rating'], rating), song, xbmc.LOGINFO)

        expert = (Val('rating') == '1')
        song['rating'] = rating
        song['rated'] = rating

        if rating == '5':
            if expert:
                self.Branch(song)
            else:
                self.pithos.add_feedback(song['token'], True)
                notification('Thumb UP', song['title'], '3000', iconart)
            self.Save(song)

        elif rating == '4':
            if expert:
                self.Seed(song)
            else:
                self.pithos.add_feedback(song['token'], True)
                notification('Thumb UP', song['title'], '3000', iconart)
            self.Save(song)

        elif rating == '3':
            self.pithos.add_feedback(song['token'], True)
            notification('Thumb UP', song['title'], '3000', iconart)
            self.Save(song)

        elif rating == '2':
            if expert:
                self.pithos.set_tired(song['token'])
            else:
                self.pithos.add_feedback(song['token'], False)
                notification('Thumb DOWN', song['title'], '3000', iconart)
            self.player.playnext()

        elif rating == '1':
            self.pithos.add_feedback(song['token'], False)
            notification('Thumb DOWN', song['title'], '3000', iconart)
            self.player.playnext()

        elif rating == '':
            feedback = self.pithos.add_feedback(song['token'], True)
            self.pithos.del_feedback(song['station'], feedback)
            notification('Thumb CLEARED', song['title'], '3000', iconart)


    def Scan(self, rate = False):
        log('def Scan')
        if (rate and time.time() < self.wait['scan']) or xbmcgui.getCurrentWindowDialogId() == 10135: return
        self.wait['scan'] = time.time() + 15

        songs = dict()
        for pos in range(0, self.playlist.size()):
            tk = self.playlist[pos].getProperty("%s.token" % _id)
            rt = xbmc.getInfoLabel("MusicPlayer.Position(%d).Rating" % pos)
            if rt == '': rt = '0'

            if tk in self.songs:
                song = self.songs[tk]
                del self.songs[tk]
                songs[tk] = song

                if rate and song.get('rating', rt) != rt:
                    self.Rated(song, rt)
                elif not song.get('rating'):
                    song['rating'] = rt

        for s in self.songs:
            if not self.songs[s].get('keep', False) and xbmcvfs.exists(self.songs[s].get('path_cch')):
                xbmcvfs.delete(self.songs[s]['path_cch'])
                log('Scan  RM', self.songs[s], xbmc.LOGINFO)

        self.songs = songs


    def Path(self, s):
        log('def Path')
        lib  = Val('library')
        badc = '\\/?%*:|"<>.'		# remove bad filename chars

        s['artist'] = ''.join(c for c in s['artist'] if c not in badc)
        s['album']  = ''.join(c for c in s['album']  if c not in badc)
        s['title']  = ''.join(c for c in s['title']  if c not in badc)

        s['path_cch'] = xbmcvfs.translatePath("%s/%s - %s.%s"            % (Val('cache'), s['artist'], s['title'],  s['encoding']))
        s['path_dir'] = xbmcvfs.translatePath("%s/%s/%s - %s"            % (lib,          s['artist'], s['artist'], s['album']))
        s['path_m4a'] = xbmcvfs.translatePath("%s/%s/%s - %s/%s - %s.%s" % (lib,          s['artist'], s['artist'], s['album'], s['artist'], s['title'], 'm4a')) #s['encoding']))
        s['path_mp3'] = xbmcvfs.translatePath("%s/%s/%s - %s/%s - %s.%s" % (lib,          s['artist'], s['artist'], s['album'], s['artist'], s['title'], 'mp3')) #s['encoding']))
        s['path_lib'] = xbmcvfs.translatePath("%s/%s/%s - %s/%s - %s.%s" % (lib,          s['artist'], s['artist'], s['album'], s['artist'], s['title'], s['encoding']))
        s['path_alb'] = xbmcvfs.translatePath("%s/%s/%s - %s/folder.jpg" % (lib,          s['artist'], s['artist'], s['album']))
        s['path_art'] = xbmcvfs.translatePath("%s/%s/folder.jpg"         % (lib,          s['artist'])) #.decode("utf-8"

        title = ''.join(c for c in self.station['title'] if c not in badc)
        s['path_m3u'] = xbmcvfs.translatePath("%s/%s.m3u"                % (lib, title))
        s['path_rel'] = xbmcvfs.translatePath(   "%s/%s - %s/%s - %s.%s" % (     s['artist'], s['artist'], s['album'], s['artist'], s['title'], s['encoding']))


    def Fill(self):
        log('def Fill')
        token = self.station['token']
        if len(self.ahead.get(token, '')) > 0: return

        if not self.Auth():
            self.Msg('Login Failed. Check Settings')
            self.abort = True
            return

        try: songs = self.pithos.get_playlist(token, int(Val('quality')))
        except (mypithos.PithosTimeout, mypithos.PithosNetError):
            log('Playlist request failed; will retry', self.station, xbmc.LOGERROR)
            return False
        except (mypithos.PithosAuthTokenInvalid, mypithos.PithosAPIVersionError, mypithos.PithosError) as e:
            log("%s, %s" % (e.message, e.submsg))
            self.Msg(e.message)
            self.abort = True
            return

        for song in songs:
            self.Path(song)

        self.ahead[token] = collections.deque(songs)

        log('Fill  OK', self.station, xbmc.LOGINFO)


    def FetchWorker(self, song):
        try:
            if song.get('_generation') == self.generation:
                self.Fetch(song)
        except Exception:
            log('Song fetch failed', song, xbmc.LOGERROR)
        finally:
            with self.fetch_lock:
                self.downloading -= 1

    def Next(self):
        if time.time() < self.wait['next']:
            return
        with self.fetch_lock:
            if self.downloading >= _maxdownloads:
                return
        # Retain pacing for subsequent requests; Play resets this for a new
        # station so it does not inherit the previous station's countdown.
        self.wait['next'] = time.time() + float(Val('delay')) + 1
        self.Fill()
        token = self.station['token']
        if self.ahead.get(token):
            song = self.ahead[token].popleft()
            song['_generation'] = self.generation
            with self.fetch_lock:
                self.downloading += 1
            worker = threading.Thread(target=self.FetchWorker, args=(song,))
            worker.daemon = True
            try:
                worker.start()
            except Exception:
                with self.fetch_lock:
                    self.downloading -= 1
                self.ahead[token].appendleft(song)
                raise


    def List(self):
        log('def List')
        if not self.station or not self.player.isPlayingAudio(): return

        len1  = self.playlist.size()
        pos  = self.playlist.getposition()
        item = self.playlist[pos]
        tokn = item.getProperty("%s.token" % _id)

        if tokn in self.songs:
            Prop('voted', self.songs[tokn].get('voted', ''))

#        skip = xbmc.getInfoLabel("MusicPlayer.Position(%d).Rating" % pos)
#        skip = ((tokn == 'mesg') or (skip == '1') or (skip == '2')) and (xbmcgui.getCurrentWindowDialogId() != 10135)
        
        # keep adding until number of max downloads is in list not played
        if (len1 - pos) < 2 or (len1 - pos + self.downloading) < (_maxdownloads + 1):
            self.Next()

        log('###################22222222 PLAYLIST INFO: %s %s %s' % ( len1, pos, tokn))
        if ((len1 - pos) > 1) and (tokn == 'mesg'):
            self.player.playnext()


    def Deque(self):
        log('def Deque %2d' % len(self.queue))
        if len(self.queue) == 0: return
        elif self.once:
            self.playlist.clear()

        startpos = None
        while len(self.queue) > 0:
            song = self.queue.popleft()
            if song.get('_generation', self.generation) != self.generation:
                continue
            self.Add(song)
            if (startpos is None and song['token'] != 'mesg'
                    and self.pending_station == self.generation):
                startpos = self.playlist.size() - 1
                self.pending_station = None

        if startpos is not None:
            # Switching stations must not wait for the old song to finish.
            self.player.play(self.playlist, startpos=startpos)
            self.once = False
        elif self.once:
            # this will start the playlist playing (possibly a status item).
            self.player.play(self.playlist)
            log('def Deque setting once to False')
            self.once = False

        max = int(Val('history'))
        while self.playlist.size() > max and self.playlist.getposition() > 0:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Playlist.Remove", "params":{"playlistid":' + str(xbmc.PLAYLIST_MUSIC) + ', "position":0}}')
            KODIMONITOR.waitForAbort(0.1)

        if xbmcgui.getCurrentWindowId() == 10500:
            xbmc.executebuiltin("Container.Refresh")


    def Tune(self, token):
        log('def Tune %s' % token)
        for s in self.Stations():
            if token == s['token'] or token == s['token'][-4:]:
                if self.station == s: return False

                self.station = s
                Val('station' + self.prof, token)
                return True

        return False


    def Play(self, token):
        log('Play  ??', self.station, xbmc.LOGINFO)
        last = self.station
        self.open_player = True

        if self.Tune(token):
            self.generation += 1
            self.pending_station = self.generation
            self.queue.clear()
            self.wait['next'] = 0

            while True:
                len = self.playlist.size() - 1
                pos = self.playlist.getposition()
                if len > pos:
                    item = self.playlist[len]
                    tokn = item.getProperty("%s.token" % _id)

                    if last and tokn in self.songs:
                        self.songs[tokn]['keep'] = True
                        self.ahead.setdefault(last['token'], collections.deque()).appendleft(self.songs[tokn])

                    xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Playlist.Remove", "params":{"playlistid":' + str(xbmc.PLAYLIST_MUSIC) + ', "position":' + str(len) + '}}')
                else: break

            self.mesg = None
            self.Msg("%s" % self.station['title'])
            self.Next()
            log('Play  OK', self.station)



    def Create(self, token):
        log('%s' % token, None, xbmc.LOGINFO)
        self.Stations()
#        self.Auth()
        station = self.pithos.create_station(token)

        log('Create  ', station, xbmc.LOGINFO)
        self.Play(station['token'])


    def Delete(self, token):
        if self.station and self.station['token'] == token: self.station = None

        self.Stations()
        station = self.pithos.delete_station(token)

        log('Delete  ', station, xbmc.LOGINFO)
        xbmc.executebuiltin("Container.Refresh")


    def Rename(self, token, title):
        self.Stations()
        station = self.pithos.rename_station(token, title)

        log('Rename  ', station, xbmc.LOGINFO)
        xbmc.executebuiltin("Container.Refresh")


    def Action(self):
        act = Prop('action')
        log('def Action action=%s' % act, None, level = xbmc.LOGDEBUG)

        if _stamp != Prop('stamp'):
            self.abort = True
            self.station = None
            return

        elif act == '':
            Prop('run', str(time.time()))
            return

        elif act == 'search':
            self.Search(Prop('handle'), Prop('search'))
 
        elif act == 'create':
            self.Create(Prop('create'))

        elif act == 'rename':
            self.Rename(Prop('rename'), Prop('title'))

        elif act == 'delete':
            self.Delete(Prop('delete'))

        elif act == 'rate':
            self.Rate(Prop('rate'))

        act = Prop('action')

        if   act == 'play':
            self.Play(Prop('play'))

        elif act == 'dir':
            self.Dir(Prop('handle'))
            if (self.once or not self.player.isPlayingAudio()) and Val('autoplay') == 'true' and Val('station' + self.prof):
                self.Play(Val('station' + self.prof))

        Prop('action', '')
        Prop('run', str(time.time()))


    def Flush(self):
        log('def Flush')
        cch = xbmcvfs.translatePath(Val('cache'))
        reg = re.compile(r'^.*\.(m4a|mp3)(?:\.part\.\d+\.\d+)?$')

        (dirs, list) = xbmcvfs.listdir(cch)

        for file in list:
            if reg.match(file):
                xbmcvfs.delete("%s/%s" % (cch, file))
                log("Flush OK      '%s'" % file)


    def ShowPlayer(self):
        if (self.open_player and self.pending_station is None
                and self.player.isPlayingAudio()):
            xbmc.executebuiltin('ActivateWindow(12006)')
            self.open_player = False

    def Loop(self):
        log('def Loop')
        while not KODIMONITOR.abortRequested() and not self.abort and (self.once or self.player.isPlayingAudio()):

            self.Action()
            self.Deque()
            self.List()
            self.Scan()
            self.ShowPlayer()

            KODIMONITOR.waitForAbort(0.2)
                
        if self.player.isPlayingAudio():
            notification('Exiting', '[COLOR lime]No longer queuing new songs[/COLOR]' , '5000', iconart)
        log('Pankodi Exiting XBMCAbort?=%s PandokiAbort?=%s ' % (KODIMONITOR.abortRequested(), self.abort), None, level = xbmc.LOGINFO)
        Prop('run', '0')

