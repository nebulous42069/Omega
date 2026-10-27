import json
import re
import secrets
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from dlhd import resolver
from dlhd.debuglog import LOG, reason


from dlhd.segments import unwrap


class Relay(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, port, base, automatic=False, log_path=None):
        self.base = base
        self.automatic = automatic
        self.log_path = log_path
        self.selected = {}
        self.sessions = {}
        self.resources = OrderedDict()
        self.lock = threading.RLock()
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = 'http://127.0.0.1:{}'.format(self.server_port)
    def resource(self, url, referer):
        key = secrets.token_urlsafe(18)
        with self.lock:
            self.resources[key] = (url, referer)
            while len(self.resources) > 10000:
                self.resources.popitem(last=False)
        return self.origin + '/resource/' + key
    def session(self, channel, player, force=False):
        with self.lock:
            key = (channel, player)
            entry = self.sessions.get(key)
            if force or not entry or time.time() >= entry['until']:
                entry = resolver.resolve(self.base, channel, player)
                self.sessions[key] = entry
            return entry

    def playlist_fetch(self, session, target=None):
        target = target or session['url']
        meta, ref = session['meta'], session['referer']
        if meta.get('edge') and urlsplit(target).netloc == urlsplit(meta['edge']).netloc:
            token_data, _, _ = resolver.fetch(meta['edge'].rstrip('/') + '/api/playlist-token?' + urlencode({'slug': meta['slug']}), ref)
            token = json.loads(token_data)['token']
            parts = urlsplit(target)
            query = parse_qs(parts.query)
            query.update({'t': [token], '_': [str(int(time.time() * 1000))]})
            target = urlunsplit(parts._replace(query=urlencode(query, doseq=True)))
        return resolver.fetch(target, ref)

    def probe(self, session):
        data, _, target = self.playlist_fetch(session)
        for depth in range(4):
            text = data.decode('utf-8-sig', 'replace').strip()
            if not text.startswith('#EXTM3U'):
                raise ValueError('Source did not return an HLS playlist')
            media = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith('#')]
            if not media:
                raise ValueError('HLS playlist contains no media')
            if '#EXT-X-STREAM-INF' in text:
                data, _, target = self.playlist_fetch(session, urljoin(target, media[0]))
                continue
            keys = re.findall(r'#EXT-X-KEY:([^\n]+)', text)
            encrypted = False
            for key in keys:
                method = re.search(r'(?:^|,)METHOD=([^,]+)', key)
                if not method or method.group(1) == 'NONE':
                    continue
                if method.group(1) != 'AES-128':
                    raise ValueError('Unsupported encrypted HLS method')
                uri = re.search(r'URI="([^"]+)"', key)
                if not uri:
                    raise ValueError('HLS encryption key URI missing')
                keydata, _, _ = resolver.fetch(urljoin(target, uri.group(1)), session['referer'])
                if len(keydata) != 16:
                    raise ValueError('HLS AES key has invalid length')
                encrypted = True
            segment, kind, _ = resolver.fetch(urljoin(target, media[0]), session['referer'])
            if not segment:
                raise ValueError('Media segment is empty')
            if encrypted:
                if len(segment) < 188 or len(segment) % 16 or segment.lstrip().startswith(b'<'):
                    raise ValueError('Encrypted media segment has invalid length')
            else:
                segment = unwrap(segment)
                ts = len(segment) > 188 and segment[0] == 71 and segment[188] == 71
                mp4 = len(segment) >= 8 and segment[4:8] in (b'ftyp', b'styp', b'moof', b'sidx')
                if not ts and not mp4:
                    raise ValueError('Media segment is not recognized as MPEG-TS or fragmented MP4')
            init = re.search(r'#EXT-X-MAP:[^\n]*URI="([^"]+)"', text)
            if init:
                initdata, _, _ = resolver.fetch(urljoin(target, init.group(1)), session['referer'])
                if len(initdata) < 8 or initdata[4:8] not in (b'ftyp', b'moov'):
                    raise ValueError('Invalid MP4 initialization segment')
            return
        raise ValueError('Too many nested HLS playlists')

    def choose(self, channel):
        with self.lock:
            cached = self.selected.get(channel)
            if cached and time.time() < cached[1]:
                LOG.info('auto channel=%s cached_player=%s', channel, cached[0])
                return cached[0]
        for player in resolver.SERVERS:
            started = time.monotonic()
            LOG.info('test channel=%s player=%s started', channel, player)
            resolver.REQUEST.deadline = time.monotonic() + 4
            try:
                session = self.session(channel, player)
                self.probe(session)
                with self.lock:
                    self.selected[channel] = (player, min(session['until'], time.time() + 120))
                LOG.info('test channel=%s player=%s result=PASS elapsed=%.2fs', channel, player, time.monotonic() - started)
                return player
            except Exception as error:
                LOG.warning('test channel=%s player=%s result=FAIL reason=%s elapsed=%.2fs', channel, player, reason(error), time.monotonic() - started)
            finally:
                del resolver.REQUEST.deadline
        raise ValueError('All six players failed the source check. Open View debugging log for details.')


def rewrite(text, target, referer, relay):
    def local(uri):
        return relay.resource(urljoin(target, uri), referer)
    rows = []
    for line in text.splitlines():
        if line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
            continue
        if line.startswith('#'):
            line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + local(m.group(1)) + '"', line)
        elif line.strip():
            line = local(line.strip())
        rows.append(line)
    return '\n'.join(rows) + '\n'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def reply(self, status, data, kind):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if not self.server.slots.acquire(False):
            self.reply(503, 'Too many requests', 'text/plain')
            return
        try:
            self.handle_get()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            LOG.info('playback client disconnected')
        except Exception as error:
            # Avoid exposing signed URLs or token-bearing upstream errors.
            message = reason(error)
            LOG.warning('relay request failed: %s', message)
            self.reply(502, message, 'text/plain; charset=utf-8')
        finally:
            self.server.slots.release()
    def handle_get(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/health':
            self.reply(200, 'ok', 'text/plain')
            return
        if parsed.path == '/debug-log':
            if self.server.log_path:
                with open(self.server.log_path, 'rb') as stream:
                    stream.seek(0, 2)
                    stream.seek(max(0, stream.tell() - 128 * 1024))
                    self.reply(200, stream.read(), 'text/plain; charset=utf-8')
            else:
                self.reply(200, 'Debug log is not configured', 'text/plain')
            return
        match = re.fullmatch(r'/stream/([1-9]\d*)\.m3u8', parsed.path)
        if match:
            channel = match.group(1)
            player = parse_qs(parsed.query).get('server', ['stream'])[0]
            if self.server.automatic or player == 'auto':
                player = self.server.choose(channel)
            LOG.info('play channel=%s player=%s', channel, player)
            session = self.server.session(channel, player)
            for attempt in range(2):
                ref = session['referer']
                try:
                    data, kind, final = self.server.playlist_fetch(session)
                    break
                except HTTPError as error:
                    if error.code not in (401, 403) or attempt:
                        raise
                    session = self.server.session(channel, player, True)
        elif parsed.path.startswith('/resource/'):
            with self.server.lock:
                entry = self.server.resources.get(parsed.path.rsplit('/', 1)[-1])
            if not entry:
                self.reply(410, 'Resource expired; reopen the channel', 'text/plain')
                return
            target, ref = entry
            data, kind, final = resolver.fetch(target, ref)
        else:
            self.reply(404, 'Not found', 'text/plain')
            return
        if data.lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'#EXTM3U'):
            data = rewrite(data.decode('utf-8-sig'), final, ref, self.server)
            kind = 'application/vnd.apple.mpegurl'
        else:
            original = data
            data = unwrap(data)
            if data is not original or (len(data) > 188 and data[0] == 71 and data[188] == 71):
                LOG.info('segment format=mpeg-ts wrapped=%s input_bytes=%s output_bytes=%s', data is not original, len(original), len(data))
                kind = 'video/mp2t'
        self.reply(200, data, kind or 'application/octet-stream')
