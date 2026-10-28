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
from dlhd.media_check import validate_media, validate_mp4


class Relay(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, port, base, automatic=False, log_path=None):
        self.base = base
        self.automatic = automatic
        self.log_path = log_path
        self.selected = {}
        self.failures = {}
        self.blocked = {}
        self.selection_locks = {}
        self.sessions = {}
        self.resources = OrderedDict()
        self.lock = threading.RLock()
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = 'http://127.0.0.1:{}'.format(self.server_port)
    def resource(self, url, referer, context=None, role="media", encrypted=False):
        key = secrets.token_urlsafe(18)
        with self.lock:
            self.resources[key] = (url, referer, context, role, encrypted)
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
            passed = 0
            for uri in media[:3]:
                segment, kind, _ = resolver.fetch(urljoin(target, uri), session['referer'])
                try:
                    validate_media(unwrap(segment) if not encrypted else segment, encrypted)
                    passed += 1
                except ValueError as error:
                    LOG.info('probe sample rejected: %s', reason(error))
                if passed >= 2:
                    break
            if passed < 2:
                raise ValueError('Source did not provide two usable media samples')
            init = re.search(r'#EXT-X-MAP:[^\n]*URI="([^"]+)"', text)
            if init:
                initdata, _, _ = resolver.fetch(urljoin(target, init.group(1)), session['referer'])
                validate_mp4(initdata, initialization=True)
            return
        raise ValueError('Too many nested HLS playlists')

    def media_failure(self, context):
        if not context or not context[2]:return
        channel, player, automatic = context
        key = (channel, player)
        with self.lock:
            count = self.failures.get(key, 0) + 1
            self.failures[key] = count
            if count < 2:return
            self.blocked[key] = time.time() + 120
            cached = self.selected.get(channel)
            if cached and cached[0] == player:self.selected.pop(channel, None)
            self.sessions.pop(key, None)
        LOG.warning('source excluded channel=%s player=%s failures=%s; next playlist request will try alternatives', channel, player, count)

    def media_success(self, context):
        if context:
            with self.lock:self.failures.pop(context[:2], None)

    def is_blocked(self, context):
        if not context or not context[2]:return False
        with self.lock:return time.time() < self.blocked.get(context[:2], 0)

    def choose(self, channel):
        # Kodi may request the same playlist concurrently while probing it.
        with self.lock:
            lock = self.selection_locks.setdefault(channel, threading.Lock())
        with lock:return self._choose(channel)

    def _choose(self, channel):
        with self.lock:
            cached = self.selected.get(channel)
            if cached and time.time() < cached[1] and time.time() >= self.blocked.get((channel, cached[0]), 0):
                LOG.info('auto channel=%s cached_player=%s', channel, cached[0])
                return cached[0]
        for player in resolver.SERVERS:
            with self.lock:
                if time.time() < self.blocked.get((channel, player), 0):continue
            started = time.monotonic()
            LOG.info('test channel=%s player=%s started', channel, player)
            resolver.REQUEST.deadline = time.monotonic() + 12
            try:
                session = self.session(channel, player)
                self.probe(session)
                with self.lock:
                    self.selected[channel] = (player, min(session['until'], time.time() + 120))
                LOG.info('test channel=%s player=%s result=PASS elapsed=%.2fs', channel, player, time.monotonic() - started)
                return player
            except Exception as error:
                with self.lock:self.blocked[(channel, player)] = time.time() + 30
                LOG.warning('test channel=%s player=%s result=FAIL reason=%s elapsed=%.2fs', channel, player, reason(error), time.monotonic() - started)
            finally:
                del resolver.REQUEST.deadline
        raise ValueError('No available source passed the media checks; failing sources are temporarily excluded. See debugging log.')


def rewrite(text, target, referer, relay, context=None):
    encrypted = False
    master = '#EXT-X-STREAM-INF' in text
    def local(uri, role='media'):
        return relay.resource(urljoin(target, uri), referer, context, role, encrypted)
    rows = []
    for line in text.splitlines():
        if line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
            continue
        if line.startswith('#'):
            if line.startswith('#EXT-X-KEY:'):
                encrypted = 'METHOD=NONE' not in line
            role = 'key' if line.startswith('#EXT-X-KEY:') else 'init' if line.startswith('#EXT-X-MAP:') else 'other'
            line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + local(m.group(1), role) + '"', line)
        elif line.strip():
            line = local(line.strip(), 'playlist' if master else 'media')
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
            try:self.reply(502, message, 'text/plain; charset=utf-8')
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                LOG.info('playback client disconnected before error reply')
        finally:
            self.server.slots.release()
    def handle_get(self):
        context = None
        role = 'playlist'
        encrypted = False
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
            automatic = self.server.automatic or player == 'auto'
            if automatic:
                player = self.server.choose(channel)
            context = (channel, player, automatic)
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
            target, ref, context, role, encrypted = entry
            if self.server.is_blocked(context):
                channel = context[0]
                player = self.server.choose(channel)
                if role == 'media':
                    raise ValueError('Source changed; reload the channel to continue')
                if role not in ('key', 'init', 'other'):
                    session = self.server.session(channel, player)
                    data, kind, final = self.server.playlist_fetch(session)
                    ref = session['referer']
                    context = (channel, player, True)
                else:
                    raise ValueError('Source changed; reload the channel to continue')
            else:
                try:data, kind, final = resolver.fetch(target, ref)
                except Exception:
                    if role not in ('key','init','other'):self.server.media_failure(context)
                    raise
        else:
            self.reply(404, 'Not found', 'text/plain')
            return
        if data.lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'#EXTM3U'):
            data = rewrite(data.decode('utf-8-sig'), final, ref, self.server, context)
            kind = 'application/vnd.apple.mpegurl'
        else:
            original = data
            data = unwrap(data) if not encrypted else data
            if role == 'media':
                try:validate_media(data, encrypted)
                except ValueError:
                    self.server.media_failure(context)
                    raise
                self.server.media_success(context)
            if data is not original or (len(data) > 188 and data[0] == 71 and data[188] == 71):
                LOG.info('segment format=mpeg-ts wrapped=%s input_bytes=%s output_bytes=%s', data is not original, len(original), len(data))
                kind = 'video/mp2t'
        self.reply(200, data, kind or 'application/octet-stream')
