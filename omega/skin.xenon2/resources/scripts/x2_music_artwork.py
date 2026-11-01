# -*- coding: utf-8 -*-
"""Shared streaming artwork lookup, started by MusicVisualisation.xml (Kodi 19+).
No third-party Python modules required. Fanart.tv discart requires an API key. See X2_MUSIC_ARTWORK.md.
"""
import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from difflib import SequenceMatcher
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcvfs

PREFIX = 'X2.MusicArtwork.'
USER_AGENT = 'XenonMusicArtwork/1.0 (Kodi skin.xenon2)'

def fanart_api_key():
    return 'ad7eccc1dd67f889f7f5c2e9ebb810ae'



def normal(value):
    value = unicodedata.normalize('NFKD', value).casefold()
    return ' '.join(re.findall(r'\w+', value))


def similarity(left, right):
    return SequenceMatcher(None, normal(left), normal(right)).ratio()


def metadata():
    artist = xbmc.getInfoLabel('MusicPlayer.Artist').strip()
    title = xbmc.getInfoLabel('MusicPlayer.Title').strip()
    album = xbmc.getInfoLabel('MusicPlayer.Album').strip()
    # ICY stations commonly put both fields into the title.
    if not artist:
        combined = title or xbmc.getInfoLabel('Player.Title').strip()
        parts = re.split(r'\s+[-–—]\s+', combined, maxsplit=1)
        if len(parts) == 2:
            artist, title = (part.strip() for part in parts)
    return artist, title, album


def quote(value):
    # Strip Lucene operators from user-supplied stream tags.
    return '"' + ' '.join(re.findall(r'\w+', value, re.UNICODE)) + '"'


class Lookup:
    def __init__(self, monitor, cache_dir=None):
        self.monitor = monitor
        self.cache_dir = cache_dir
        self.last_mb = 0
        self.album_covers = {}
        self.fanart_covers = {}

    @staticmethod
    def album_key(tags):
        artist, title, album = tags
        if not artist or not album:
            return None
        return normal(artist), normal(album)

    def remember_cover(self, tags, url):
        key = self.album_key(tags)
        if key and url:
            self.album_covers[key] = url

    def known_cover(self, tags):
        return self.album_covers.get(self.album_key(tags), '')

    def get_json(self, url):
        if url.startswith('https://musicbrainz.org/'):
            delay = max(0, 1.1 - (time.monotonic() - self.last_mb))
            if delay and self.monitor.waitForAbort(delay):
                raise RuntimeError('Stopping')
            self.last_mb = time.monotonic()
        request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read(2 * 1024 * 1024).decode('utf-8'))

    def search(self, entity, query):
        return self.get_json('https://musicbrainz.org/ws/2/' + entity + '/?' +
                             urlencode({'query': query, 'fmt': 'json', 'limit': 5}))

    def download_cover(self, url):
        """Publish a local image only after the download succeeds."""
        if not url.startswith(('http://', 'https://')) or not self.cache_dir:
            return ''
        url = 'https://' + url.split('://', 1)[1]
        stem = os.path.join(self.cache_dir, 'cover-' + hashlib.sha256(url.encode('utf-8')).hexdigest())
        for extension in ('.jpg', '.png', '.webp'):
            existing = stem + extension
            if os.path.isfile(existing) and os.path.getsize(existing) > 32:
                return existing
        try:
            request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'image/*'})
            with urlopen(request, timeout=12) as response:
                data = response.read(12 * 1024 * 1024 + 1)
            if len(data) > 12 * 1024 * 1024 or len(data) < 32:
                return ''
            if data.startswith(b'\xff\xd8\xff') and data.rstrip().endswith(b'\xff\xd9'):
                extension = '.jpg'
            elif data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data[-16:]:
                extension = '.png'
            elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
                extension = '.webp'
            else:
                return ''  # Reject HTML error pages, empty replies and unknown formats.
            path = stem + extension
            with open(path + '.tmp', 'wb') as handle:
                handle.write(data)
            os.replace(path + '.tmp', path)
            return path
        except Exception as exc:
            xbmc.log('Xenon cover download unavailable (' + type(exc).__name__ + ')', xbmc.LOGDEBUG)
            return ''

    def cover(self, entity, mbid):
        data = self.get_json('https://coverartarchive.org/' + entity + '/' + mbid)
        for image in data.get('images', []):
            if image.get('front'):
                thumbs = image.get('thumbnails', {})
                urls = (thumbs.get('1200'), thumbs.get('500'), thumbs.get('250'), image.get('image'))
                for url in dict.fromkeys(url for url in urls if url):
                    path = self.download_cover(url)
                    if path:
                        return path
        return ''

    def discart(self, entity, mbid, api_key, disc_number, need_cover=False):
        candidate = (entity, mbid)
        if not api_key:
            return ''
        if entity == 'release':
            release = self.get_json('https://musicbrainz.org/ws/2/release/' + mbid +
                                    '?inc=release-groups&fmt=json')
            mbid = release.get('release-group', {}).get('id', '')
        if not mbid:
            return ''
        data = self.get_json('https://webservice.fanart.tv/v3/music/albums/' + mbid +
                             '?' + urlencode({'api_key': api_key}))
        albums = data.get('albums', {})
        album = albums.get(mbid, {}) if isinstance(albums, dict) else next(
            (a for a in albums if a.get('release_group_id') == mbid), {})
        if need_cover:
            # Fanart.tv can supply the front cover even if Cover Art Archive fails.
            for image in album.get('albumcover', [])[:2]:
                path = self.download_cover(image.get('url', ''))
                if path:
                    self.fanart_covers[candidate] = path
                    break
        images = album.get('cdart', [])
        # Never substitute a different disc when its number is known.
        if disc_number:
            images = [i for i in images if str(i.get('disc', '')) == disc_number]
        else:
            first = [i for i in images if str(i.get('disc', '1')) == '1']
            images = first or images
        def likes(image):
            try:
                return int(image.get('likes', 0))
            except (TypeError, ValueError):
                return 0
        for image in sorted(images, key=likes, reverse=True):
            url = image.get('url', '')
            if url.startswith(('http://', 'https://')):
                return 'https://' + url.split('://', 1)[1]
        return ''

    def find(self, artist, title, album, api_key='', disc_number=''):
        candidates = []
        if album:
            data = self.search('release-group', 'artist:' + quote(artist) +
                               ' AND releasegroup:' + quote(album))
            for item in data.get('release-groups', []):
                credit = ''.join(c.get('name', '') + c.get('joinphrase', '')
                                 for c in item.get('artist-credit', []))
                if similarity(artist, credit) >= .85 and similarity(album, item.get('title', '')) >= .85:
                    candidates.append(('release-group', item['id']))
        if not candidates and title:
            data = self.search('recording', 'artist:' + quote(artist) +
                               ' AND recording:' + quote(title))
            for item in data.get('recordings', []):
                credit = ''.join(c.get('name', '') + c.get('joinphrase', '')
                                 for c in item.get('artist-credit', []))
                if similarity(artist, credit) < .85 or similarity(title, item.get('title', '')) < .85:
                    continue
                for release in item.get('releases', []):
                    if album and similarity(album, release.get('title', '')) < .85:
                        continue
                    candidates.append(('release', release['id']))
        result = {'cover': self.known_cover((artist, title, album)), 'discart': ''}
        # Use one matched album for both kinds of artwork.
        for entity, mbid in list(dict.fromkeys(candidates))[:3]:
            try:
                if not result['cover']:
                    result['cover'] = self.cover(entity, mbid)
            except Exception:
                pass
            try:
                result['discart'] = self.discart(entity, mbid, api_key, disc_number, need_cover=not result['cover'])
                if not result['cover']:
                    result['cover'] = self.fanart_covers.get((entity, mbid), '')
            except Exception:
                pass
            if result['cover'] or result['discart']:
                break
        self.remember_cover((artist, title, album), result['cover'])
        return result



class NextArtwork:
    """Independent queued-track cover; never borrow the playing track's image."""
    def __init__(self, home, lookup, cache_dir):
        self.home, self.lookup, self.cache_dir = home, lookup, cache_dir
        self.previous = None
        self.stable_since = 0
        self.attempted = False

    @staticmethod
    def snapshot():
        enabled = (xbmc.getCondVisibility('Window.IsVisible(visualisation)') and
                   xbmc.getCondVisibility('Player.HasAudio') and
                   xbmc.getCondVisibility('MusicPlayer.Offset(1).Exists') and
                   xbmc.getCondVisibility('String.IsEqual(Skin.String(MusicVizLayout),1)') and
                   not xbmc.getCondVisibility('Skin.HasSetting(Disable.MusicPlayerNextTrack)') and
                   not xbmc.getCondVisibility('Skin.HasSetting(Disable.StreamMusicArtwork)'))
        if not enabled:
            return None
        return tuple(xbmc.getInfoLabel('MusicPlayer.Offset(1).' + field).strip()
                     for field in ('Artist', 'Title', 'Album'))

    def update(self, last_search, allow_network=True):
        tags = self.snapshot()
        if tags != self.previous:
            self.home.clearProperty(PREFIX + 'NextCover')
            self.previous = tags
            self.stable_since = time.monotonic()
            self.attempted = False
        if tags is None or not tags[0] or not (tags[1] or tags[2]) or self.attempted:
            return last_search
        if time.monotonic() - self.stable_since < 2:
            return last_search
        key = hashlib.sha256(json.dumps(('v5-next-local',) + tags,
                                      ensure_ascii=False).encode('utf-8')).hexdigest()
        path = os.path.join(self.cache_dir, key + '.json')
        result = None
        try:
            with open(path, encoding='utf-8') as handle:
                cached = json.load(handle)
            ttl = 30 * 86400 if cached.get('cover') else 300
            if time.time() - cached['time'] < ttl:
                result = cached['cover']
                if result and not os.path.isfile(result):
                    result = None
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if result is None:
            if not allow_network or time.monotonic() - last_search < 15:
                return last_search
            last_search = time.monotonic()
            try:
                # No discart request for the queued-track widget.
                result = self.lookup.find(*tags).get('cover', '')
            except Exception as exc:
                xbmc.log('Xenon next artwork: lookup unavailable (' +
                         type(exc).__name__ + ')', xbmc.LOGDEBUG)
                result = ''
            try:
                with open(path + '.tmp', 'w', encoding='utf-8') as handle:
                    json.dump({'time': time.time(), 'cover': result}, handle)
                os.replace(path + '.tmp', path)
            except OSError:
                pass
        self.attempted = True
        # Queue edits, shuffle, skips, or stopping may occur during a request.
        if self.snapshot() == tags:
            self.lookup.remember_cover(tags, result)
            self.home.setProperty(PREFIX + 'NextCover', result)
        else:
            self.home.clearProperty(PREFIX + 'NextCover')
        return last_search


def run():
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(10000)
    owner = PREFIX + 'Owner'
    heartbeat = PREFIX + 'Heartbeat'
    now = time.time()
    try:
        if home.getProperty(owner) and now - float(home.getProperty(heartbeat) or 0) < 300:
            return
    except ValueError:
        pass
    token = uuid.uuid4().hex
    home.setProperty(owner, token)
    home.setProperty(heartbeat, str(now))
    cache_dir = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon2/music_artwork/')
    xbmcvfs.mkdirs(cache_dir)
    lookup = Lookup(monitor, cache_dir)
    next_art = NextArtwork(home, lookup, cache_dir)
    home.clearProperty(PREFIX + 'NextCover')
    previous = None
    stable_since = time.monotonic()
    attempted = False
    last_search = 0
    try:
        while not monitor.abortRequested() and home.getProperty(owner) == token:
            home.setProperty(heartbeat, str(time.time()))
            if not (xbmc.getCondVisibility('Player.HasAudio') or
                    xbmc.getCondVisibility('Window.IsVisible(home)') or
                    xbmc.getCondVisibility('Window.IsVisible(visualisation)')):
                break
            active = xbmc.getCondVisibility('Player.HasAudio')
            tags = metadata() if active else ('', '', '')
            api_key = fanart_api_key()
            disc_number = xbmc.getInfoLabel('MusicPlayer.DiscNumber').strip()
            disabled = xbmc.getCondVisibility('Skin.HasSetting(Disable.StreamMusicArtwork)')
            # Include path so two plugins with identical tags do not inherit art.
            identity = (xbmc.getInfoLabel('Player.Filenameandpath'), api_key, disc_number, disabled) + tags
            if identity != previous:
                home.clearProperty(PREFIX + 'Cover')
                home.clearProperty(PREFIX + 'Discart')
                previous = identity
                stable_since = time.monotonic()
                attempted = False
            disabled = xbmc.getCondVisibility('Skin.HasSetting(Disable.StreamMusicArtwork)')
            if disabled:
                home.clearProperty(PREFIX + 'Cover')
                home.clearProperty(PREFIX + 'Discart')
            # Clear/reuse queued artwork before a potentially slow current lookup.
            last_search = next_art.update(last_search, allow_network=False)
            artist, title, album = tags
            if (not disabled and active and artist and (title or album)
                    and not attempted and time.monotonic() - stable_since >= 2):
                key = hashlib.sha256(json.dumps(('v5-local', hashlib.sha256(api_key.encode('utf-8')).hexdigest(), disc_number) + tags, ensure_ascii=False).encode('utf-8')).hexdigest()
                path = os.path.join(cache_dir, key + '.json')
                result = None
                try:
                    with open(path, encoding='utf-8') as handle:
                        cached = json.load(handle)
                    ttl = 30 * 86400 if cached.get('art', {}).get('cover') else 300
                    if time.time() - cached['time'] < ttl:
                        result = cached['art']
                        if result.get('cover') and not os.path.isfile(result['cover']):
                            result = None
                except (OSError, ValueError, KeyError, TypeError):
                    pass
                if result is None and time.monotonic() - last_search < 15:
                    if monitor.waitForAbort(.5):
                        break
                    continue
                if result is None:
                    last_search = time.monotonic()
                    try:
                        result = lookup.find(*tags, api_key=api_key, disc_number=disc_number)
                    except Exception as exc:
                        # Do not log track names, stream URLs or credentials.
                        xbmc.log('Xenon music artwork: lookup unavailable (' + type(exc).__name__ + ')', xbmc.LOGDEBUG)
                        result = {'cover': '', 'discart': ''}
                    try:
                        with open(path + '.tmp', 'w', encoding='utf-8') as handle:
                            json.dump({'time': time.time(), 'art': result}, handle)
                        os.replace(path + '.tmp', path)
                    except OSError:
                        pass  # Read-only/full profile must not prevent displaying art.
                attempted = True
                # Never publish a completed request for the previous song.
                current = (xbmc.getInfoLabel('Player.Filenameandpath'),
                           fanart_api_key(),
                           xbmc.getInfoLabel('MusicPlayer.DiscNumber').strip(),
                           xbmc.getCondVisibility('Skin.HasSetting(Disable.StreamMusicArtwork)')) + metadata()
                if (current == identity and xbmc.getCondVisibility('Player.HasAudio')
                        and not xbmc.getCondVisibility('Skin.HasSetting(Disable.StreamMusicArtwork)')):
                    lookup.remember_cover(tags, result.get('cover', ''))
                    home.setProperty(PREFIX + 'Cover', lookup.known_cover(tags) or result.get('cover', ''))
                    home.setProperty(PREFIX + 'Discart', result.get('discart', ''))
            last_search = next_art.update(last_search)
            # A queued song may identify the same album more successfully.
            # Reuse only an exact normalized artist+album match, never its discart.
            if (xbmc.getCondVisibility('Player.HasAudio') and
                    not xbmc.getCondVisibility('Skin.HasSetting(Disable.StreamMusicArtwork)')):
                shared_cover = lookup.known_cover(metadata())
                if shared_cover:
                    home.setProperty(PREFIX + 'Cover', shared_cover)
            if monitor.waitForAbort(.5):
                break
    finally:
        if home.getProperty(owner) == token:
            home.clearProperty(PREFIX + 'Cover')
            home.clearProperty(PREFIX + 'Discart')
            home.clearProperty(PREFIX + 'NextCover')
            home.clearProperty(owner)
            home.clearProperty(heartbeat)


if __name__ == '__main__':
    run()
