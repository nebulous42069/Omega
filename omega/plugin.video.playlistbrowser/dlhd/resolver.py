"""Experimental, standard-library Python implementation of selected upstream formats."""
import base64
import html
import json
import re
import time
import threading
from dlhd.debuglog import LOG, reason
from dlhd.groups import group_for, sort_key, display_name
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from html.parser import HTMLParser

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'
REQUEST = threading.local()

SERVERS = ('stream', 'cast', 'watch', 'plus', 'casting', 'player')


def b64(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)).decode('utf-8')


def fetch(url, referer='', limit=32 * 1024 * 1024):
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('Only HTTP(S) URLs are supported')
    headers = {'User-Agent': UA, 'Accept': '*/*', 'Accept-Encoding': 'identity'}
    if referer and not re.search(r'bluetier|wideiptv|cdnlivetv|tiktokcdn', urlsplit(url).hostname or '', re.I):
        headers['Referer'] = referer
        p = urlsplit(referer)
        headers['Origin'] = p.scheme + '://' + p.netloc
    remaining = getattr(REQUEST, 'deadline', time.monotonic() + 20) - time.monotonic()
    if remaining <= 0:
        raise ValueError('Source test time budget exceeded')
    started = time.monotonic()
    host = urlsplit(url).hostname or 'unknown'
    try:
        response = urlopen(Request(url, headers=headers), timeout=min(20, remaining))
    except Exception as error:
        LOG.warning('fetch host=%s failed=%s elapsed=%.2fs', host, reason(error), time.monotonic() - started)
        raise
    with response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Upstream response exceeds size limit')
        LOG.info('fetch host=%s status=%s bytes=%s elapsed=%.2fs', host, response.status, len(data), time.monotonic() - started)
        return data, response.headers.get('Content-Type', ''), response.geturl()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.frames, self.channels = [], []
        self.anchor = None
        self.text = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'iframe' and a.get('src'):
            self.frames.append(a)
        if tag == 'a':
            self.anchor = a
            self.text = []
    def handle_data(self, data):
        if self.anchor is not None:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            href = self.anchor.get('href', '')
            match = re.search(r'(?:[?&]id=|stream-)(\d+)|/(\d+)/?$', href)
            name = ' '.join(' '.join(self.text).split()) or self.anchor.get('title', '')
            if match and name:
                self.channels.append((int(match.group(1) or match.group(2)), name))
            self.anchor = None


def channels(base):
    data, _, _ = fetch(base.rstrip('/') + '/24-7-channels.php')
    parser = Links()
    parser.feed(data.decode('utf-8', 'replace'))
    found = dict(parser.channels)
    if not found:
        raise ValueError('No channels found; upstream may have changed or blocked the request')
    return sorted(found.items(), key=lambda item: item[1].casefold())


def extract(source):
    source = html.unescape(source).replace('\\/', '/')
    match = re.search(r'window\._econfig\s*=\s*[\'"]([^\'"]+)', source)
    if match:
        raw = base64.b64decode(match.group(1)).decode('latin1')
        size = (len(raw) + 3) // 4
        pieces = [''] * 4
        for i, target in enumerate((2, 0, 3, 1)):
            chunk = raw[i * size:(i + 1) * size]
            pieces[target] = b64(chunk[:3] + chunk[4:])
        config = json.loads(b64(''.join(pieces)))
        key = 'stream_url_nop2p' if config.get('p2p') is False or config.get('url_nop2p') else 'stream_url'
        return config.get(key) or config.get('stream_url') or config.get('stream_url_nop2p'), {}
    match = re.search(r'var\s+_\w+\s*=\s*\[([\d,\s]+)\]\s*,\s*_\w+\s*=\s*(\d+)\s*,\s*_\w+\s*=\s*(\d+)', source)
    if match:
        source = ''.join(chr(((int(n) ^ int(match.group(2))) - int(match.group(3))) & 255) for n in match.group(1).split(',') if n.strip())
    src = re.search(r'const\s+SRC\s*=\s*"([^"]+)"', source)
    edge = re.search(r'const\s+EDGE\s*=\s*"([^"]+)"', source)
    slug = re.search(r'const\s+CHANNEL\s*=\s*"([^"]+)"', source)
    if src and edge and slug and urlsplit(src.group(1)).netloc == urlsplit(edge.group(1)).netloc:
        return src.group(1), {'edge': edge.group(1), 'slug': slug.group(1)}
    decoder = re.search(r'function (\w+)\(s\)\{[^}]*atob', source)
    if decoder:
        variables = dict(re.findall(r"var (\w+)='([A-Za-z0-9+/=_-]+)'", source))
        assign = re.search(r'var \w+=((?:' + re.escape(decoder.group(1)) + r'\(\w+\)\+?)+);\s*var _p2pMode', source)
        if assign:
            candidate = ''.join(b64(variables[name]) for name in re.findall(re.escape(decoder.group(1)) + r'\((\w+)\)', assign.group(1)))
            if '.m3u8' in candidate:
                return candidate, {}
    for encoded in re.findall(r'atob\([\'"]([^\'"]+)[\'"]\)', source):
        try:
            candidate = b64(encoded)
            if candidate.startswith(('https://', 'http://')) and '.m3u8' in candidate:
                return candidate, {}
        except (ValueError, UnicodeError):
            pass
    for pattern in (r'SIGNED_URL\s*=\s*[\'"]([^\'"]+)', r'streamUrl\s*:\s*[\'"]([^\'"]+)', r'https?://[^\s\'"<>`\\]+\.m3u8[^\s\'"<>`\\]*'):
        m = re.search(pattern, source)
        if m:
            return m.group(1) if m.lastindex else m.group(0), {}
    return None


def resolve(base, channel, server):
    if server not in SERVERS or not str(channel).isdigit() or int(channel) < 1:
        raise ValueError('Invalid channel or player')
    page = base.rstrip('/') + '/{}/stream-{}.php'.format(server, channel)
    referer = base.rstrip('/') + '/watch.php?id=' + str(channel)
    visited = set()
    for depth in range(8):
        if page in visited:
            break
        visited.add(page)
        data, _, page = fetch(page, referer)
        source = data.decode('utf-8', 'replace')
        LOG.info('resolve channel=%s player=%s hop=%s host=%s', channel, server, depth, urlsplit(page).hostname)
        result = extract(source) if depth else None
        if result:
            target, meta = result
            expiry = re.search(r'[?&]e=(\d+)', target)
            return {'url': target, 'referer': page, 'meta': meta, 'until': min(float(expiry.group(1)) - 45, time.time() + 240) if expiry else time.time() + 240}
        parser = Links()
        parser.feed(source)
        preferred = [f for f in parser.frames if f.get('id') == 'thatframe'] or [f for f in parser.frames if 'video' in f.get('class', '')] or parser.frames
        next_page = preferred[-1]['src'] if preferred else None
        if not next_page and 'wikisport' in page:
            fid = re.search(r'fid\s*=\s*[\'"]([^\'"]+)', source)
            if fid:
                from urllib.parse import quote
                next_page = 'https://igniteandship.com/wiki.php?player=desktop&live=' + quote(fid.group(1))
        if not next_page:
            raise ValueError('Unsupported embed or no stream found. Try a different player.')
        referer, page = page, urljoin(page, html.unescape(next_page))
    raise ValueError('Embed chain exceeded limit')


def playlist(items, origin, server, logos=None, epg=None, epg_url=None):
    rows = ['#EXTM3U' + (' x-tvg-url="{}"'.format(epg_url) if epg_url else '')]
    for channel, name in sorted(items, key=sort_key):
        name = display_name(name)
        name = ' '.join(name.replace('"', "'").split())
        logo = (logos or {}).get(int(channel), '')
        from dlhd.logo_paths import portable_logo
        logo = portable_logo(logo)
        from dlhd.logos import safe_logo_reference
        logo_attr = ' tvg-logo="{}"'.format(logo) if safe_logo_reference(logo) else ''
        mapping=(epg or {}).get(int(channel), {})
        epg_id=' '.join(str(mapping.get('id',int(channel))).replace('"', "'").split())
        epg_name=' '.join(str(mapping.get('name','')).replace('"', "'").split())
        epg_attr=' tvg-name="{}"'.format(epg_name) if epg_name else ''
        rows.extend(['#EXTINF:-1 tvg-id="{}"{} group-title="{}"{},{}'.format(epg_id, epg_attr, group_for(name), logo_attr, name), '{}/stream/{}.m3u8?server={}'.format(origin.rstrip('/'), int(channel), server)])
    return '\n'.join(rows) + '\n'
