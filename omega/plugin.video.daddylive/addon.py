# -*- coding: utf-8 -*- 
'''
***********************************************************
*
* @file addon.py
* @package script.module.thecrew
*
* Created on 2024-03-08.
* Copyright 2024 by The Crew. All rights reserved.
*
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import re
import os
import sys
import json
import html
import gzip
import base64
import hashlib
import hmac as _hmac
import socket
import struct
import random
import requests
import threading
import tempfile
import concurrent.futures
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, unquote, parse_qsl, quote_plus, urlparse, urljoin
from datetime import datetime, timezone
import time
import calendar
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon

_KODI_TEMP = xbmcvfs.translatePath('special://temp/')
os.makedirs(_KODI_TEMP, exist_ok=True)

DADDYLIVE_PROXY_CACHE = {} 

addon_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.daddylive')

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
FANART = addon.getAddonInfo('fanart')
ICON = addon.getAddonInfo('icon')

_seed_setting = addon.getSetting('seed_baseurl').strip()
SEED_BASEURL = _seed_setting if _seed_setting else 'https://dlhd.link/'

_CUSTOM_DNS = addon.getSetting('custom_dns').strip()
EXTRA_M3U8_URL = 'http://drewlive2423.duckdns.org:8081/DrewLive/MergedPlaylist.m3u8'


CHEVY_PROXY = 'https://chevy.soyspace.cyou'
CHEVY_LOOKUP = 'https://chevy.vovlacosa.sbs'
PLAYER_REFERER = 'https://www.ksohls.ru/'

M3U8_PROXY_PORT = 19876
_actual_proxy_port = None  # resolved at runtime by _ensure_m3u8_proxy
try:
    _PROXY_ADDON_MTIME = str(int(os.path.getmtime(__file__)))
except Exception:
    _PROXY_ADDON_MTIME = '0'

IPTV_ORG_API = 'https://iptv-org.github.io/api/channels.json'
IPTV_ORG_INDEX_CACHE = os.path.join(_KODI_TEMP, 'daddylive_iptv_org_idx2.json')
IPTV_ORG_TVG_CACHE = os.path.join(_KODI_TEMP, 'daddylive_iptv_org_tvg.json')
IPTV_ORG_TTL = 7 * 24 * 3600  # refresh index every 7 days
_EPG_BEST_CACHE_FILE = os.path.join(_KODI_TEMP, 'daddylive_epg_best.json')
_EPG_BEST_TTL = 1800  # 30 minutes
_XMLTV_FR_URL = 'https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz'
_XMLTV_FR_CACHE_FILE = os.path.join(_KODI_TEMP, 'daddylive_xmltv_fr.xml.gz')
_XMLTV_FR_TTL = 4 * 3600   # re-download every 4 hours
_XMLTV_PROG_CACHE = os.path.join(_KODI_TEMP, 'daddylive_xmltv_programs.json')
_XMLTV_PROG_TTL = 1800     # re-parse every 30 minutes

_CDN_CACHE_FILE = os.path.join(_KODI_TEMP, 'daddylive_cdn_map.json')
_CDN_CACHE_TTL = 3600  # 1 hour
_CDN_STATUS_CACHE_FILE = os.path.join(_KODI_TEMP, 'daddylive_cdn_status.json')
_CDN_STATUS_TTL = 300  # 5 minutes
_FAILED_CHANNELS_FILE = os.path.join(_KODI_TEMP, 'daddylive_failed_channels.json')
_FAILED_CHANNEL_TTL = 600  # 10 minutes — channels with no valid content
# CDN domains that serve image placeholders (not video) when a channel has no source stream.
# tempfileb.aiquickdraw.com and liftstory.com are intentionally NOT here — they serve real video.
_IMAGE_PLACEHOLDER_DOMAINS = ('fluxpro.ai', 'iuimg.com')
_PREMIUM_KEY_RX = re.compile(r'^premium(\d+)$')
_M3U8_ENDLIST = b'#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXT-X-ENDLIST\n'
_SEQ_RX = re.compile(r'#EXT-X-MEDIA-SEQUENCE:(\d+)')
_MEDIA_SEQ_RX = re.compile(r'MEDIA-SEQUENCE:(\d+)')
_FAV_PROBE_TS_FILE = os.path.join(_KODI_TEMP, 'daddylive_fav_probe_ts')
_PAGE_CACHE_FILE = os.path.join(_KODI_TEMP, 'daddylive_page_cache.json')


def _is_placeholder(url):
    """Return True if segment URL is from a known image-placeholder CDN (not real video)."""
    try:
        host = url.split('/')[2].lower()
        return any(host == d or host.endswith('.' + d) for d in _IMAGE_PLACEHOLDER_DOMAINS)
    except Exception:
        return False


def _apply_m3u8_filter(content):
    """Filter placeholder image segments from an M3U8 playlist.
    Returns (filtered_content, remaining_count, total_count) or (None, 0, total) if all filtered."""
    raw_lines = content.splitlines(keepends=True)
    filtered = []
    prev_removed = found_first = False
    removed_before_first = total = 0
    orig_seq_m = _SEQ_RX.search(content)
    orig_seq = int(orig_seq_m.group(1)) if orig_seq_m else 0
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            total += 1
            if _is_placeholder(stripped):
                if filtered and filtered[-1].strip().startswith('#EXTINF'):
                    filtered.pop()
                if not found_first:
                    removed_before_first += 1
                prev_removed = True
                continue
            else:
                if prev_removed and found_first:
                    filtered.append('#EXT-X-DISCONTINUITY\n')
                found_first = True
                prev_removed = False
        filtered.append(line)
    remaining = sum(1 for l in filtered if l.strip() and not l.strip().startswith('#'))
    if not remaining:
        return None, 0, total
    result = ''.join(filtered)
    if removed_before_first > 0 and orig_seq_m:
        result = result.replace(
            orig_seq_m.group(0),
            f'#EXT-X-MEDIA-SEQUENCE:{orig_seq + removed_before_first}',
            1
        )
    return result, remaining, total


_FAV_PROBE_COOLDOWN = 120  # seconds between background probes (persisted across processes)
_FAV_REFRESH_TS_FILE = os.path.join(_KODI_TEMP, 'daddylive_fav_refresh_ts')
_FAV_REFRESH_DEBOUNCE = 10  # min seconds between Container.Refresh calls from mark_failed

# ISO 3166-1 alpha-2 country → ISO 639-3 primary language
COUNTRY_LANG = {
    'AE': 'ara', 'AF': 'pus', 'AL': 'sqi', 'AM': 'hye', 'AO': 'por',
    'AR': 'spa', 'AT': 'deu', 'AU': 'eng', 'AZ': 'aze', 'BA': 'bos',
    'BD': 'ben', 'BE': 'fra', 'BG': 'bul', 'BH': 'ara', 'BO': 'spa',
    'BR': 'por', 'CA': 'eng', 'CH': 'deu', 'CL': 'spa', 'CM': 'fra',
    'CN': 'zho', 'CO': 'spa', 'CR': 'spa', 'CU': 'spa', 'CY': 'ell',
    'CZ': 'ces', 'DE': 'deu', 'DK': 'dan', 'DO': 'spa', 'DZ': 'ara',
    'EC': 'spa', 'EE': 'est', 'EG': 'ara', 'ES': 'spa', 'FI': 'fin',
    'FR': 'fra', 'GB': 'eng', 'GE': 'kat', 'GH': 'eng', 'GR': 'ell',
    'GT': 'spa', 'HK': 'zho', 'HN': 'spa', 'HR': 'hrv', 'HU': 'hun',
    'ID': 'ind', 'IE': 'eng', 'IL': 'heb', 'IN': 'hin', 'IQ': 'ara',
    'IR': 'fas', 'IS': 'isl', 'IT': 'ita', 'JM': 'eng', 'JO': 'ara',
    'JP': 'jpn', 'KE': 'eng', 'KR': 'kor', 'KW': 'ara', 'KZ': 'kaz',
    'LB': 'ara', 'LT': 'lit', 'LU': 'fra', 'LV': 'lav', 'LY': 'ara',
    'MA': 'ara', 'MD': 'ron', 'ME': 'srp', 'MK': 'mkd', 'MN': 'mon',
    'MO': 'zho', 'MR': 'ara', 'MX': 'spa', 'MY': 'msa', 'MZ': 'por',
    'NG': 'eng', 'NI': 'spa', 'NL': 'nld', 'NO': 'nor', 'NP': 'nep',
    'NZ': 'eng', 'OM': 'ara', 'PA': 'spa', 'PE': 'spa', 'PH': 'fil',
    'PK': 'urd', 'PL': 'pol', 'PS': 'ara', 'PT': 'por', 'PY': 'spa',
    'QA': 'ara', 'RO': 'ron', 'RS': 'srp', 'RU': 'rus', 'SA': 'ara',
    'SD': 'ara', 'SE': 'swe', 'SG': 'eng', 'SI': 'slv', 'SK': 'slk',
    'SV': 'spa', 'SY': 'ara', 'TH': 'tha', 'TN': 'ara', 'TR': 'tur',
    'TT': 'eng', 'TW': 'zho', 'UA': 'ukr', 'US': 'eng', 'UY': 'spa',
    'UZ': 'uzb', 'VE': 'spa', 'VN': 'vie', 'YE': 'ara', 'ZA': 'eng',
}

LANG_NAMES = {
    'eng': 'English', 'fra': 'Français', 'deu': 'Allemand', 'spa': 'Espagnol',
    'ita': 'Italien', 'por': 'Portugais', 'ara': 'Arabe', 'nld': 'Néerlandais',
    'tur': 'Turc', 'rus': 'Russe', 'pol': 'Polonais', 'ron': 'Roumain',
    'swe': 'Suédois', 'nor': 'Norvégien', 'dan': 'Danois', 'fin': 'Finnois',
    'ces': 'Tchèque', 'hrv': 'Croate', 'srp': 'Serbe', 'bul': 'Bulgare',
    'hun': 'Hongrois', 'ell': 'Grec', 'heb': 'Hébreu', 'fas': 'Persan',
    'urd': 'Ourdou', 'msa': 'Malais', 'hin': 'Hindi', 'ben': 'Bengalî',
    'tam': 'Tamoul', 'ind': 'Indonésien', 'zho': 'Chinois', 'tha': 'Thaï',
    'vie': 'Vietnamien', 'jpn': 'Japonais', 'kor': 'Coréen',
}

# EPlayer auth — UA/screen/tz/lang values used for fingerprint computation
_AUTH_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

# Thread-safe state store: channel_key → {auth_token, channel_salt, m3u8_url, fetched_at}
_proxy_lock = threading.Lock()
_channel_creds = {}
# Stall tracker: channel_key → {seq: last_seq, count: consecutive_same_seq}
_m3u8_stall = {}
_m3u8_timeouts = {}  # channel_key → consecutive timeout count
_stall_lock = threading.Lock()
_seg_semaphore = threading.Semaphore(2)  # max 2 concurrent segment downloads
_proxy_abort = threading.Event()  # set on Kodi shutdown to unblock sleeping handler threads
_probe_lock = threading.Lock()


def _cleanup_caches():
    """Background thread: purge stale entries every 5 minutes. Exits on Kodi abort."""
    monitor = xbmc.Monitor()
    while not monitor.waitForAbort(300):
        now = time.time()
        # DNS cache: TTL 30 min
        with _dns_cache_lock:
            stale = [h for h, (_, ts) in list(_dns_cache.items()) if now - ts > 1800]
            for h in stale:
                del _dns_cache[h]
        # Channel creds: purge entries older than 10 min
        with _proxy_lock:
            stale = [k for k, v in list(_channel_creds.items()) if now - v.get('fetched_at', 0) > 600]
            for k in stale:
                del _channel_creds[k]
                _m3u8_stall.pop(k, None)


def _dns_resolve(hostname, dns_server, port=53, timeout=2):
    """Resolve a hostname via UDP to a custom DNS server. Returns IP string or None."""
    try:
        txid = random.randint(1, 65535)
        # Header with RD flag, 1 question, 0 answers, 0 authority, 1 additional (EDNS0)
        header = struct.pack('>HHHHHH', txid, 0x0100, 1, 0, 0, 1)
        question = b''
        for label in hostname.split('.'):
            enc = label.encode('ascii')
            question += bytes([len(enc)]) + enc
        question += b'\x00' + struct.pack('>HH', 1, 1)  # Type A, Class IN
        # EDNS0 OPT record: allows up to 4096 byte UDP responses
        edns0 = b'\x00' + struct.pack('>HHIH', 41, 4096, 0, 0)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(header + question + edns0, (dns_server, port))
            resp = sock.recv(4096)
        ancount = struct.unpack('>H', resp[6:8])[0]
        if ancount == 0:
            return None
        # Skip question section
        offset = 12
        while resp[offset] != 0:
            if resp[offset] & 0xC0 == 0xC0:
                offset += 2
                break
            offset += resp[offset] + 1
        else:
            offset += 1
        offset += 4  # QTYPE + QCLASS
        # Parse answer records
        for _ in range(ancount):
            if resp[offset] & 0xC0 == 0xC0:
                offset += 2
            else:
                while resp[offset] != 0:
                    offset += resp[offset] + 1
                offset += 1
            rtype, _rc, _ttl, rdlen = struct.unpack('>HHIH', resp[offset:offset + 10])
            offset += 10
            if rtype == 1 and rdlen == 4:
                return '.'.join(str(b) for b in resp[offset:offset + 4])
            offset += rdlen
        return None
    except Exception:
        return None


_dns_cache = {}  # host -> (ip, timestamp)
_dns_cache_lock = threading.Lock()
_original_getaddrinfo = socket.getaddrinfo
_active_dns = None  # set by _apply_custom_dns after reachability check
_DNS_FALLBACK = '8.8.8.8'


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if not _active_dns or not host:
        return _original_getaddrinfo(host, port, family, type, proto, flags)
    # Don't intercept IP literals or localhost
    try:
        socket.inet_aton(host)
        return _original_getaddrinfo(host, port, family, type, proto, flags)
    except OSError:
        pass
    if host == 'localhost' or host.endswith('.local'):
        return _original_getaddrinfo(host, port, family, type, proto, flags)
    with _dns_cache_lock:
        entry = _dns_cache.get(host)
    ip = None
    if entry:
        cached_ip, cached_ts = entry
        if time.time() - cached_ts < 1800:  # 30 min TTL
            ip = cached_ip
    if ip is None:
        ip = _dns_resolve(host, _active_dns)
        if ip:
            with _dns_cache_lock:
                _dns_cache[host] = (ip, time.time())
        else:
            # Active DNS failed — try the other server
            _fallback = _DNS_FALLBACK if _active_dns != _DNS_FALLBACK else _CUSTOM_DNS
            log(f'[CustomDNS] resolve failed via {_active_dns} for {host}, trying {_fallback}')
            ip = _dns_resolve(host, _fallback)
            if ip:
                with _dns_cache_lock:
                    _dns_cache[host] = (ip, time.time())
                log(f'[CustomDNS] {host} → {ip} (via {_fallback} fallback)')
            else:
                log(f'[CustomDNS] resolve failed for {host}, fallback to system DNS')
                return _original_getaddrinfo(host, port, family, type, proto, flags)
    results = []
    for socktype in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        results.append((socket.AF_INET, socktype, 0, '', (ip, port or 0)))
    return results


def _apply_custom_dns():
    global _active_dns
    if not _CUSTOM_DNS:
        return
    # Quick reachability check: resolve a known hostname via the configured DNS server
    _test_ip = _dns_resolve('www.google.com', _CUSTOM_DNS, timeout=2)
    if _test_ip:
        _active_dns = _CUSTOM_DNS
        xbmc.log(f'[DaddyLive][CustomDNS] Active — using {_CUSTOM_DNS}', xbmc.LOGINFO)
    else:
        _active_dns = _DNS_FALLBACK
        xbmc.log(f'[DaddyLive][CustomDNS] {_CUSTOM_DNS} unreachable — using {_DNS_FALLBACK} as primary', xbmc.LOGWARNING)
    socket.getaddrinfo = _patched_getaddrinfo


_apply_custom_dns()
threading.Thread(target=_cleanup_caches, daemon=True).start()


def _compute_fingerprint():
    combined = _AUTH_UA + '1920x1080' + 'UTC' + 'en'
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _compute_pow_nonce(channel_key, channel_salt, key_id, ts):
    hmac_base = _hmac.new(channel_salt.encode(), channel_key.encode(), hashlib.sha256).hexdigest()
    for nonce in range(100000):
        combined = hmac_base + channel_key + key_id + str(ts) + str(nonce)
        h = hashlib.md5(combined.encode()).hexdigest()
        if int(h[:4], 16) < 0x1000:
            return nonce
    return 99999


def _compute_auth_sig(channel_key, channel_salt, key_id, ts, fp):
    msg = f'{channel_key}|{key_id}|{ts}|{fp}'
    return _hmac.new(channel_salt.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]


def _xor_decode(arr, key):
    return ''.join(chr(b ^ key) for b in arr)


def _extract_credential(page, field):
    """Extract a credential value supporting plain string or XOR-encoded formats."""
    # Format 1: field: 'value'
    m = re.search(rf"{field}\s*:\s*'([^']+)'", page)
    if m:
        return m.group(1)
    # Format 2: field: _dec_XXXX(_init_YYYY, key)
    m = re.search(rf"{field}\s*:\s*_dec_\w+\((_init_\w+),\s*(\d+)\)", page)
    if m:
        init_name, key = m.group(1), int(m.group(2))
        arr_m = re.search(rf"{init_name}\s*=\s*\[([^\]]+)\]", page)
        if arr_m:
            arr = list(map(int, arr_m.group(1).split(',')))
            return _xor_decode(arr, key)
    return None


def _fetch_auth_credentials(channel_id, max_attempts=3):
    """Fetch fresh authToken and channelSalt from the ksohls.ru player page."""
    url = f'https://www.ksohls.ru/premiumtv/daddyhd.php?id={channel_id}'
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, headers={
                'User-Agent': _AUTH_UA,
                'Referer': get_active_base(),
            }, timeout=4)
            auth_token = _extract_credential(r.text, 'authToken')
            channel_salt = _extract_credential(r.text, 'channelSalt')
            if auth_token and channel_salt:
                return auth_token, channel_salt
            log(f'[EPlayerAuth] Credentials not found (attempt {attempt+1}/3), page snippet: {r.text[:200]}')
        except Exception as e:
            log(f'[EPlayerAuth] fetch error (attempt {attempt+1}/3): {e}')
        if attempt < max_attempts - 1:
            time.sleep(1)
    return None, None


def _state_file(channel_key):
    return os.path.join(_KODI_TEMP, f'daddylive_{channel_key}.json')


def _set_channel_state(channel_key, auth_token, channel_salt, m3u8_url):
    state = {
        'auth_token': auth_token,
        'channel_salt': channel_salt,
        'm3u8_url': m3u8_url,
        'fetched_at': time.time(),
    }
    with _proxy_lock:
        _channel_creds[channel_key] = state
    # Reset stall/timeout counters — fresh session, stale counts must not carry over
    _m3u8_stall.pop(channel_key, None)
    _m3u8_timeouts.pop(channel_key, None)
    # Persist to temp file so other plugin processes can read the state
    try:
        with open(_state_file(channel_key), 'w') as f:
            json.dump(state, f)
    except Exception:
        pass


def _get_channel_state(channel_key):
    with _proxy_lock:
        state = _channel_creds.get(channel_key)
    # Always check if the file has been updated by another process
    try:
        path = _state_file(channel_key)
        if os.path.exists(path):
            file_mtime = os.path.getmtime(path)
            in_memory_time = state.get('fetched_at', 0) if state else 0
            if file_mtime > in_memory_time and (time.time() - file_mtime) < 300:
                with open(path) as f:
                    file_state = json.load(f)
                with _proxy_lock:
                    _channel_creds[channel_key] = file_state
                return dict(file_state)
    except Exception:
        pass
    if state:
        return dict(state)
    return {}


class _EPlayerProxyHandler(BaseHTTPRequestHandler):
    """Local HTTP proxy that:
    - GET /m3u8/<channel_key>  → fetches live m3u8, rewrites key URIs to /key/...
    - GET /key/<channel_key>/<key_id> → computes auth headers, fetches real AES key
    """

    def do_GET(self):
        if self.path == '/health':
            body = b'daddylive-proxy'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/version':
            body = _PROXY_ADDON_MTIME.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        m = re.match(r'^/m3u8/([^/?]+)', self.path)
        if m:
            self._handle_m3u8(m.group(1))
            return
        m = re.match(r'^/key/([^/]+)/(\d+)', self.path)
        if m:
            self._handle_key(m.group(1), m.group(2))
            return
        m = re.match(r'^/seg/(.+)', self.path)
        if m:
            self._handle_segment(m.group(1))
            return
        m = re.match(r'^/raw/([^/]+)/(.+)', self.path)
        if m:
            self._handle_raw(m.group(1), m.group(2))
            return
        self.send_response(404)
        self.end_headers()

    def _handle_m3u8(self, channel_key):
        state = _get_channel_state(channel_key)
        if not state or not state.get('m3u8_url'):
            # Proxy runs in old process — fetch credentials on demand
            m = _PREMIUM_KEY_RX.match(channel_key)
            if m:
                cid = m.group(1)
                log(f'[EPlayerProxy] No state for {channel_key}, fetching credentials for id={cid}')
                auth_token, channel_salt = _fetch_auth_credentials(cid)
                if auth_token and channel_salt:
                    m3u8_url = resolve_stream_url(cid)
                    _set_channel_state(channel_key, auth_token, channel_salt, m3u8_url)
                    state = _get_channel_state(channel_key)
        if not state or not state.get('m3u8_url'):
            self.send_response(503)
            self.end_headers()
            return
        try:
            m3u8_hdrs = {
                'User-Agent': _AUTH_UA,
                'Referer': PLAYER_REFERER,
                'Authorization': f'Bearer {state["auth_token"]}',
                'X-Channel-Key': channel_key,
                'X-User-Agent': _AUTH_UA,
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
            for _m3u8_attempt in range(2):
                try:
                    _tout = 5 if _m3u8_attempt > 0 else 3
                    r = requests.get(state['m3u8_url'], headers=m3u8_hdrs, timeout=_tout)
                    with _stall_lock:
                        _m3u8_timeouts.pop(channel_key, None)  # reset on success
                    break
                except requests.exceptions.Timeout:
                    if _m3u8_attempt == 0:
                        log(f'[EPlayerProxy] m3u8 timeout for {channel_key}, retrying')
                        time.sleep(1)
                    else:
                        # Count consecutive timeouts; give up gracefully after 5
                        with _stall_lock:
                            _tc = _m3u8_timeouts.get(channel_key, 0) + 1
                            _m3u8_timeouts[channel_key] = _tc
                        log(f'[EPlayerProxy] m3u8 timeout #{_tc} for {channel_key}')
                        if _tc >= 5:
                            log(f'[EPlayerProxy] {channel_key}: CDN unresponsive ({_tc} timeouts) — ending stream')
                            _mark_channel_failed(channel_key)
                            with _stall_lock:
                                _m3u8_timeouts.pop(channel_key, None)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                            self.send_header('Content-Length', str(len(_M3U8_ENDLIST)))
                            self.end_headers()
                            self.wfile.write(_M3U8_ENDLIST)
                            return
                        raise
                except Exception as _e:
                    log(f'[EPlayerProxy] m3u8 conn error (attempt {_m3u8_attempt+1}): {_e}')
                    if _m3u8_attempt == 0:
                        time.sleep(0.1)
                    else:
                        raise

            # On 403/404, re-auth and retry once (403 = token expired or wrong CDN server key)
            if r.status_code in (403, 404):
                log(f'[EPlayerProxy] m3u8 {r.status_code} for {channel_key}, re-fetching credentials')
                m = _PREMIUM_KEY_RX.match(channel_key)
                if m:
                    cid = m.group(1)
                    auth_token, channel_salt = _fetch_auth_credentials(cid)
                    if auth_token and channel_salt:
                        m3u8_url = resolve_stream_url(cid)
                        _set_channel_state(channel_key, auth_token, channel_salt, m3u8_url)
                        state = _get_channel_state(channel_key)
                        m3u8_hdrs['Authorization'] = f'Bearer {state["auth_token"]}'
                        r = requests.get(state['m3u8_url'], headers=m3u8_hdrs, timeout=3)
                        log(f'[EPlayerProxy] m3u8 after re-auth: status={r.status_code}')
                    if r.status_code != 200:
                        log(f'[EPlayerProxy] {channel_key}: CDN {r.status_code} after re-auth — ending stream')
                        _mark_channel_failed(channel_key)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                        self.send_header('Content-Length', str(len(_M3U8_ENDLIST)))
                        self.end_headers()
                        self.wfile.write(_M3U8_ENDLIST)
                        return

            # On 502/503, retry once after a short delay
            if r.status_code in (502, 503):
                log(f'[EPlayerProxy] m3u8 {r.status_code} for {channel_key}, retrying')
                time.sleep(1)
                r = requests.get(state['m3u8_url'], headers=m3u8_hdrs, timeout=3)

            content = r.text
            if r.status_code == 200:
                # Finite playlist = channel offline — end gracefully (not 503, avoids restart loop)
                if '#EXT-X-ENDLIST' in content:
                    log(f'[EPlayerProxy] {channel_key}: offline playlist (EXT-X-ENDLIST) — ending stream')
                    _mark_channel_failed(channel_key)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                    self.send_header('Content-Length', str(len(_M3U8_ENDLIST)))
                    self.end_headers()
                    self.wfile.write(_M3U8_ENDLIST)
                    return
                # Strip image placeholder segments served by known image CDNs.
                # NOTE: tempfileb.aiquickdraw.com is a real video CDN that obfuscates segments as .png — keep those.
                _content_filt, _remaining, _all_seg_count = _apply_m3u8_filter(content)
                if _remaining == 0:
                    _all_segs_raw = [l.strip() for l in content.splitlines()
                                     if l.strip() and not l.strip().startswith('#')]
                    log(f'[EPlayerProxy] {channel_key}: all {_all_seg_count} segments are images — samples: {_all_segs_raw[:2]}')
                    # Wait 3s for CDN to produce real segments (transient state), then re-fetch
                    _proxy_abort.wait(timeout=3)
                    if _proxy_abort.is_set():
                        return
                    _png_reauth_ok = False
                    try:
                        _refetch = requests.get(state['m3u8_url'], headers=m3u8_hdrs, timeout=5)
                        if _refetch.status_code == 200 and '#EXTM3U' in _refetch.text:
                            _rf_segs = [l.strip() for l in _refetch.text.splitlines()
                                        if l.strip() and not l.strip().startswith('#')]
                            if any(not _is_placeholder(s) for s in _rf_segs):
                                log(f'[EPlayerProxy] {channel_key}: CDN recovered after 3s wait — continuing')
                                content = _refetch.text
                                _png_reauth_ok = True
                    except Exception:
                        pass
                    # Try re-auth with a fresh CDN URL if 3s wait didn't help
                    _png_cid_m = _PREMIUM_KEY_RX.match(channel_key)
                    if not _png_reauth_ok and _png_cid_m:
                        _png_cid = _png_cid_m.group(1)
                        log(f'[EPlayerProxy] {channel_key}: re-authing to get fresh CDN')
                        _pat, _pcs = _fetch_auth_credentials(_png_cid, max_attempts=1)
                        if _pat and _pcs:
                            _purl = resolve_stream_url(_png_cid)
                            _set_channel_state(channel_key, _pat, _pcs, _purl)
                            state = _get_channel_state(channel_key)
                            m3u8_hdrs['Authorization'] = f'Bearer {state["auth_token"]}'
                            try:
                                _pr = requests.get(state['m3u8_url'], headers=m3u8_hdrs, timeout=5)
                                if _pr.status_code == 200 and '#EXTM3U' in _pr.text:
                                    _pr_segs = [l.strip() for l in _pr.text.splitlines()
                                                if l.strip() and not l.strip().startswith('#')]
                                    _pr_video = [s for s in _pr_segs if not _is_placeholder(s)]
                                    if _pr_video:
                                        log(f'[EPlayerProxy] {channel_key}: re-auth got real video segments — continuing')
                                        content = _pr.text
                                        _png_reauth_ok = True
                                    else:
                                        log(f'[EPlayerProxy] {channel_key}: re-auth still all images — channel offline')
                            except Exception as _pe:
                                log(f'[EPlayerProxy] {channel_key}: re-auth fetch failed: {_pe}')
                    if not _png_reauth_ok:
                        log(f'[EPlayerProxy] {channel_key}: no video segments after filtering — ending stream')
                        _mark_channel_failed(channel_key)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                        self.send_header('Content-Length', str(len(_M3U8_ENDLIST)))
                        self.end_headers()
                        self.wfile.write(_M3U8_ENDLIST)
                        return
                    # Re-apply filter on fresh content
                    _content_filt, _remaining, _all_seg_count = _apply_m3u8_filter(content)
                if _content_filt is not None and _remaining < _all_seg_count:
                    log(f'[EPlayerProxy] {channel_key}: filtered image segments, {_remaining} video segs remain')
                    content = _content_filt
            seq_m = _MEDIA_SEQ_RX.search(content)
            seq = seq_m.group(1) if seq_m else '?'
            log(f'[EPlayerProxy] m3u8 fetched seq={seq} status={r.status_code}')

            # Stall detection: sequence unchanged for 20+ seconds → re-auth
            # Time-based (not count-based) to be immune to parallel request bursts
            _STALL_TIMEOUT = 20  # seconds without sequence advance = stall
            if r.status_code == 200 and seq != '?':
                _now = time.time()
                with _stall_lock:
                    stall = _m3u8_stall.get(channel_key, {'seq': None, 'first_seen': _now})
                    if seq != stall['seq']:
                        stall = {'seq': seq, 'first_seen': _now}
                    _m3u8_stall[channel_key] = stall
                if _now - stall['first_seen'] >= _STALL_TIMEOUT:
                    same_retries = stall.get('same_url_retries', 0)
                    _stall_age = int(_now - stall['first_seen'])
                    log(f'[EPlayerProxy] stall detected (seq={seq} frozen {_stall_age}s), re-auth (same_url_retries={same_retries})')
                    cm = _PREMIUM_KEY_RX.match(channel_key)
                    if cm:
                        cid = cm.group(1)
                        at, cs = _fetch_auth_credentials(cid)
                        if at and cs:
                            old_url = (state or {}).get('m3u8_url', '')
                            new_url = resolve_stream_url(cid)
                            _set_channel_state(channel_key, at, cs, new_url)
                            if new_url != old_url:
                                # New CDN endpoint — reset stall tracker
                                with _stall_lock:
                                    _m3u8_stall[channel_key] = {'seq': None, 'first_seen': time.time(), 'same_url_retries': 0}
                                log(f'[EPlayerProxy] stall: new CDN URL obtained')
                            else:
                                # Same URL after re-auth — wait for CDN to produce new segments
                                same_retries += 1
                                if same_retries >= 3:
                                    # CDN genuinely frozen after 3 attempts — end stream
                                    log(f'[EPlayerProxy] stall: CDN frozen after {same_retries} retries — ending stream')
                                    with _stall_lock:
                                        _m3u8_stall.pop(channel_key, None)
                                    _mark_channel_failed(channel_key)
                                    self.send_response(200)
                                    self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                                    self.send_header('Content-Length', str(len(_M3U8_ENDLIST)))
                                    self.end_headers()
                                    self.wfile.write(_M3U8_ENDLIST)
                                    return
                                # Not yet giving up — wait 6s then re-fetch CDN playlist
                                log(f'[EPlayerProxy] stall: same URL (retry {same_retries}/2), waiting 6s for CDN')
                                with _stall_lock:
                                    _m3u8_stall[channel_key] = {'seq': seq, 'first_seen': time.time(), 'same_url_retries': same_retries}
                                _proxy_abort.wait(timeout=6)
                                if _proxy_abort.is_set():
                                    return
                                try:
                                    _r2 = requests.get(state['m3u8_url'], headers=m3u8_hdrs, timeout=5)
                                    if _r2.status_code == 200:
                                        content = _r2.text
                                        log(f'[EPlayerProxy] stall: CDN re-fetched after wait')
                                except Exception:
                                    pass

            port = _actual_proxy_port or M3U8_PROXY_PORT

            def _rewrite_key(mo):
                uri = mo.group(1)
                km = re.search(r'/key/[^/]+/(\d+)', uri)
                if km:
                    return f'URI="http://127.0.0.1:{port}/key/{channel_key}/{km.group(1)}"'
                return mo.group(0)

            content = re.sub(r'URI="([^"]+)"', _rewrite_key, content)

            # Rewrite segment URLs so Kodi fetches them via the proxy
            # (segments need Origin/Referer headers that Kodi doesn't send)
            # Also handle relative segment URLs using m3u8_url as base
            _m3u8_base = state['m3u8_url'].split('?')[0].rsplit('/', 1)[0] + '/'
            seg_lines = []
            for line in content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    if stripped.startswith('http://') or stripped.startswith('https://'):
                        abs_seg = stripped
                    else:
                        abs_seg = urljoin(_m3u8_base, stripped)
                    encoded = quote_plus(abs_seg)
                    seg_lines.append(f'http://127.0.0.1:{port}/seg/{encoded}')
                else:
                    seg_lines.append(line)
            content = '\n'.join(seg_lines)

            body = content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            log(f'[EPlayerProxy] m3u8 error for {channel_key}: {e}')
            self.send_response(502)
            self.end_headers()

    def _handle_key(self, channel_key, key_id):
        state = _get_channel_state(channel_key)
        if not state or not state.get('channel_salt'):
            # Proxy runs in old process — fetch credentials on demand
            m = _PREMIUM_KEY_RX.match(channel_key)
            if m:
                cid = m.group(1)
                auth_token, channel_salt = _fetch_auth_credentials(cid)
                if auth_token and channel_salt:
                    m3u8_url = resolve_stream_url(cid)
                    _set_channel_state(channel_key, auth_token, channel_salt, m3u8_url)
                    state = _get_channel_state(channel_key)
        if not state or not state.get('channel_salt'):
            self.send_response(503)
            self.end_headers()
            return
        try:
            ts = int(time.time())
            fp = _compute_fingerprint()
            nonce = _compute_pow_nonce(channel_key, state['channel_salt'], key_id, ts)
            auth_sig = _compute_auth_sig(channel_key, state['channel_salt'], key_id, ts, fp)
            key_url = f'{CHEVY_LOOKUP}/key/{channel_key}/{key_id}'
            r = requests.get(key_url, headers={
                'User-Agent': _AUTH_UA,
                'Referer': PLAYER_REFERER,
                'Authorization': f'Bearer {state["auth_token"]}',
                'X-Key-Timestamp': str(ts),
                'X-Key-Nonce': str(nonce),
                'X-Key-Path': auth_sig,
                'X-Fingerprint': fp,
            }, timeout=3)
            body = r.content
            log(f'[EPlayerProxy] key {key_id}: {len(body)}B status={r.status_code} nonce={nonce}')
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            log(f'[EPlayerProxy] key error for {channel_key}/{key_id}: {e}')
            self.send_response(502)
            self.end_headers()

    def _handle_raw(self, encoded_origin, encoded_url):
        """Proxy a URL with a specific Origin/Referer.
        - m3u8/playlist: rewrites relative segment URLs to absolute and routes through /raw/
        - segments (.ts): buffered and forwarded (stream=False for retry on conn errors)
        """
        try:
            origin = unquote(encoded_origin)
            raw_url = unquote(encoded_url)

            # Guard: reject clearly relative URLs (Kodi resolved them incorrectly)
            if not raw_url.startswith('http'):
                log(f'[EPlayerProxy] raw: relative URL rejected: {raw_url}')
                self.send_response(400)
                self.end_headers()
                return

            referer = origin.rstrip('/') + '/'
            hdrs = {'User-Agent': UA, 'Origin': origin, 'Referer': referer}

            # Fetch without streaming so we can inspect Content-Type / content prefix
            r = requests.get(raw_url, headers=hdrs, timeout=5)
            ct = r.headers.get('Content-Type', '')

            # Detect M3U8 by URL extension OR Content-Type OR content starting with #EXTM3U
            is_manifest = (
                '.m3u8' in raw_url.split('?')[0]
                or 'mpegurl' in ct.lower()
                or r.content[:7] == b'#EXTM3U'
            )

            if is_manifest:
                port = _actual_proxy_port or M3U8_PROXY_PORT
                base = raw_url.split('?')[0].rsplit('/', 1)[0] + '/'
                enc_orig = quote_plus(origin)
                seg_lines = []
                for line in r.text.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        abs_seg = stripped if stripped.startswith('http') else urljoin(base, stripped)
                        seg_lines.append(f'http://127.0.0.1:{port}/raw/{enc_orig}/{quote_plus(abs_seg)}')
                    else:
                        seg_lines.append(line)
                body = '\n'.join(seg_lines).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                # Segment — already buffered by stream=False above
                body = r.content
                self.send_response(r.status_code)
                self.send_header('Content-Type', ct or 'video/mp2t')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except Exception as e:
            log(f'[EPlayerProxy] raw error: {e}')
            try:
                self.send_response(502)
                self.end_headers()
            except Exception:
                pass

    def _handle_segment(self, encoded_url):
        seg_url = unquote(encoded_url)
        log(f'[EPlayerProxy] seg req: {seg_url[8:70]}')
        seg_hdrs = {
            'User-Agent': _AUTH_UA,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.ksohls.ru',
            'Referer': PLAYER_REFERER,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        body = None
        seg_proxy_url = addon.getSetting('seg_proxy').strip()
        proxies = {'http': seg_proxy_url, 'https': seg_proxy_url} if seg_proxy_url else None
        with _seg_semaphore:
            for attempt in range(2):
                current_proxies = proxies if attempt == 1 else None
                try:
                    r = requests.get(seg_url, headers=seg_hdrs, timeout=(3, 5),
                                     proxies=current_proxies)
                    ct = r.headers.get('Content-Type', '')
                    if r.status_code == 200 and 'html' not in ct.lower():
                        body = r.content
                        if current_proxies:
                            log(f'[EPlayerProxy] seg ok via proxy: {len(body)}B')
                        break
                    elif r.status_code == 429:
                        if attempt == 0 and proxies:
                            log(f'[EPlayerProxy] seg 429, retrying via proxy')
                            # continue to attempt 1 with proxy
                        else:
                            log(f'[EPlayerProxy] seg 429: CDN rate-limit')
                            break
                    else:
                        log(f'[EPlayerProxy] seg bad: status={r.status_code} ct={ct} size={len(r.content)}B')
                        break
                except requests.exceptions.Timeout:
                    log(f'[EPlayerProxy] seg timeout: {seg_url[:70]}')
                    break
                except Exception as e:
                    err_str = str(e)
                    if '407' in err_str or 'Proxy Authentication Required' in err_str:
                        log(f'[EPlayerProxy] seg proxy 407: identifiants proxy incorrects — vérifiez le paramètre "Proxy segments" dans les réglages')
                        break
                    log(f'[EPlayerProxy] seg error (attempt {attempt + 1}): {e}')
                    if attempt == 0:
                        time.sleep(0.1)
        try:
            if body is not None:
                log(f'[EPlayerProxy] seg ok: {len(body)}B')
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                log(f'[EPlayerProxy] seg fail 502: {seg_url[8:70]}')
                self.send_response(502)
                self.end_headers()
        except Exception:
            pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


class _M3U8ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        target = unquote(self.path.lstrip('/'))
        try:
            r = requests.get(target, headers={'User-Agent': UA}, timeout=15)
            body = r.content
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()
    def log_message(self, fmt, *args):
        pass

def _serve_until_abort(server):
    """Run the HTTP server until Kodi signals shutdown. Exits within ~0.5s of abort."""
    monitor = xbmc.Monitor()
    server.timeout = 0.5
    while not monitor.abortRequested():
        server.handle_request()
    _proxy_abort.set()  # unblock any handler threads sleeping in stall retry
    log('[EPlayerProxy] Kodi abort — proxy server stopped')
    server.server_close()


def _ensure_m3u8_proxy():
    global _actual_proxy_port
    if _actual_proxy_port is not None:
        return
    for port in range(M3U8_PROXY_PORT, M3U8_PROXY_PORT + 20):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), _EPlayerProxyHandler)
            server.daemon_threads = True  # request threads die with the process
            t = threading.Thread(target=_serve_until_abort, args=(server,), daemon=True)
            t.start()
            _actual_proxy_port = port
            log(f'[EPlayerProxy] Started on port {port} (mtime={_PROXY_ADDON_MTIME})')
            return
        except OSError as e:
            if e.errno in (98, 10048):
                # Port busy — check if it's our proxy with current code
                try:
                    rh = requests.get(f'http://127.0.0.1:{port}/health', timeout=1)
                    if rh.status_code == 200 and rh.text == 'daddylive-proxy':
                        try:
                            rv = requests.get(f'http://127.0.0.1:{port}/version', timeout=1)
                            proxy_mtime = rv.text.strip() if rv.status_code == 200 else ''
                        except Exception:
                            proxy_mtime = ''
                        if proxy_mtime == _PROXY_ADDON_MTIME:
                            _actual_proxy_port = port
                            log(f'[EPlayerProxy] Already running on port {port} (up-to-date)')
                            return
                        else:
                            log(f'[EPlayerProxy] Port {port} has stale proxy (mtime {proxy_mtime} != {_PROXY_ADDON_MTIME}), trying next port')
                except Exception:
                    pass
                log(f'[EPlayerProxy] Port {port} busy (not ours), trying {port + 1}')
            else:
                log(f'[EPlayerProxy] Failed to start on port {port}: {e}')
                break
    _actual_proxy_port = None
    log(f'[EPlayerProxy] Could not bind any port — proxy unavailable')

EXTRA_CHANNELS_DATA = {}

def log(msg):
    logpath = xbmcvfs.translatePath('special://logpath/')
    filename = 'daddylive.log'
    log_file = os.path.join(logpath, filename)
    try:
        if isinstance(msg, str):
            _msg = f'\n    {msg}'
        else:
            _msg = f'\n    {repr(msg)}'
        if not os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8'):
                pass
        with open(log_file, 'a', encoding='utf-8') as f:
            line = '[{} {}]: {}'.format(datetime.now().date(), str(datetime.now().time())[:8], _msg)
            f.write(line.rstrip('\r\n') + '\n')
    except Exception as e:
        try:
            xbmc.log(f'[ Daddylive ] Logging Failure: {e}', 2)
        except:
            pass

def should_cache_url(url: str) -> bool:
    """
    Determine if this URL is cacheable.
    Cache:
        - index.php pages (category, schedule, etc.)
        - 24-7-channels.php
    Do NOT cache:
        - watch.php (stream URLs)
    """
    if 'watch.php' in url:
        return False
    if 'index.php' in url or '24-7-channels.php' in url:
        return True
    return False


_CACHE_TTL_VALUES = [1800, 3600, 7200, 21600, 43200]  # 30min, 1h, 2h, 6h, 12h

def get_cache_expiry():
    try:
        return _CACHE_TTL_VALUES[int(addon.getSetting('cache_ttl'))]
    except Exception:
        return 7200  # default 2h

CACHE_EXPIRY = get_cache_expiry()

def _is_error_response(text, url=''):
    if not text:
        return True
    if '24-7-channels.php' in url and 'class="card"' not in text:
        return True
    return False

def _load_page_cache():
    try:
        with open(_PAGE_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_page_cache(cache):
    try:
        with open(_PAGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
    except Exception as e:
        log(f"[fetch_via_proxy] Failed to save page cache: {e}")

def fetch_via_proxy(url, headers=None, use_cache=True):
    headers = headers or {}
    should_cache = should_cache_url(url)

    if should_cache:
        cached = _load_page_cache()
        entry = cached.get(url)
        if isinstance(entry, dict) and 'data' in entry and 'timestamp' in entry:
            if time.time() - entry['timestamp'] < get_cache_expiry() and not _is_error_response(entry['data'], url):
                log(f"[fetch_via_proxy] Returning cached data for {url}")
                return entry['data']

    resp_text = ''
    for attempt in range(2):
        for verify_ssl in ([True, False] if attempt == 0 else [False]):
            try:
                resp_text = requests.get(url, headers=headers, timeout=8,
                                         verify=verify_ssl, allow_redirects=True).text
                if not _is_error_response(resp_text, url):
                    log(f"[fetch_via_proxy] ok attempt={attempt} verify={verify_ssl} for {url}")
                    break
                log(f"[fetch_via_proxy] bad response verify={verify_ssl}: {resp_text[:80]}")
            except Exception as e:
                log(f"[fetch_via_proxy] failed attempt={attempt} verify={verify_ssl} for {url}: {type(e).__name__}: {e}")
        if not _is_error_response(resp_text, url):
            break
        if attempt == 0:
            time.sleep(1)
    if _is_error_response(resp_text, url):
        return ''

    if should_cache:
        cached = _load_page_cache()
        cached[url] = {'timestamp': int(time.time()), 'data': resp_text}
        _save_page_cache(cached)

    return resp_text




def normalize_origin(url):
    try:
        u = urlparse(url)
        return f'{u.scheme}://{u.netloc}/'
    except:
        return SEED_BASEURL

def resolve_active_baseurl(seed):
    try:
        _ = fetch_via_proxy(seed, headers={'User-Agent': UA})
        return normalize_origin(seed)
    except Exception as e:
        log(f'Active base resolve failed, using seed. Error: {e}')
        return normalize_origin(seed)

_active_base_cache = None

def get_active_base():
    global _active_base_cache
    if _active_base_cache:
        return _active_base_cache
    base = addon.getSetting('active_baseurl')
    if base:
        # Validate once per process — if unreachable, fall back to seed
        try:
            r = requests.get(base, headers={'User-Agent': UA}, timeout=5,
                             verify=False, allow_redirects=True)
            if r.status_code >= 400:
                raise Exception(f'HTTP {r.status_code}')
        except Exception as e:
            log(f'[get_active_base] {base} invalide ({e}), reset vers seed')
            base = ''
            addon.setSetting('active_baseurl', '')
    if not base:
        base = normalize_origin(SEED_BASEURL)
        addon.setSetting('active_baseurl', base)
    if not base.endswith('/'):
        base += '/'
    _active_base_cache = base
    return base

def set_active_base(new_base: str):
    if not new_base.endswith('/'):
        new_base += '/'
    addon.setSetting('active_baseurl', new_base)

def abs_url(path: str) -> str:
    return urljoin(get_active_base(), path.lstrip('/'))

def get_local_time(utc_time_str):
    if not utc_time_str:
        return ''
    try:
        # Parse manually — datetime.strptime is None in some Kodi/Python envs (_strptime lazy import bug)
        h, m = map(int, utc_time_str.strip().split(':'))
        utc_now = time.gmtime()
        utc_ts = calendar.timegm((utc_now.tm_year, utc_now.tm_mon, utc_now.tm_mday, h, m, 0, 0, 0, 0))
        local = time.localtime(utc_ts)
        use_24h = addon.getSetting('time_format') == '1'
        if use_24h:
            return f'{local.tm_hour:02d}:{local.tm_min:02d}'
        else:
            period = 'AM' if local.tm_hour < 12 else 'PM'
            h12 = local.tm_hour % 12 or 12
            return f'{h12}:{local.tm_min:02d} {period}'
    except Exception as e:
        log(f"Failed to convert time: {e}")
        return utc_time_str or ''


def _build_current_events_map():
    """Return {channel_id: 'LocalTime  EventTitle'} for events currently airing (started < 4h ago)."""
    try:
        url = abs_url('index.php')
        html_text = fetch_via_proxy(url, headers={'User-Agent': UA, 'Referer': get_active_base()})
        if not html_text:
            return {}
        now_ts = time.time()
        utc_now = time.gmtime()
        today_midnight = calendar.timegm((utc_now.tm_year, utc_now.tm_mon, utc_now.tm_mday, 0, 0, 0, 0, 0, 0))
        ev_map = {}
        for time_str, event_title, channels_block in re.findall(
            r'<div\s+class="schedule__event">.*?'
            r'<div\s+class="schedule__eventHeader"[^>]*?>\s*'
            r'(?:<[^>]+>)*?'
            r'<span\s+class="schedule__time"[^>]*data-time="([^"]+)"[^>]*>.*?</span>\s*'
            r'<span\s+class="schedule__eventTitle">\s*([^<]+)\s*</span>.*?'
            r'</div>\s*'
            r'<div\s+class="schedule__channels">(.*?)</div>',
            html_text, re.IGNORECASE | re.DOTALL
        ):
            try:
                h, m = map(int, time_str.strip().split(':'))
            except Exception:
                continue
            # Check today and yesterday to handle midnight crossover
            is_current = False
            for midnight in (today_midnight, today_midnight - 86400):
                event_ts = midnight + h * 3600 + m * 60
                if event_ts <= now_ts < event_ts + 4 * 3600:
                    is_current = True
                    break
            if not is_current:
                continue
            local_time = get_local_time(time_str.strip())
            title = html.unescape(event_title.strip())
            display = f'{local_time}  {title}'
            for href, title_attr, link_text in re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>',
                channels_block, re.IGNORECASE | re.DOTALL
            ):
                try:
                    cid = dict(parse_qsl(urlparse(href).query)).get('id') or ''
                except Exception:
                    cid = ''
                if cid and cid not in ev_map:
                    ev_map[cid] = display
        return ev_map
    except Exception as e:
        log(f'[_build_current_events_map] error: {e}')
        return {}


def build_url(query):
    return addon_url + '?' + urlencode(query)

def addDir(title, dir_url, is_folder=True, logo=None, context_menu=None, plot=None):
    li = xbmcgui.ListItem(title)
    clean_title = re.sub(r'<[^>]+>', '', title)
    clean_plot = plot if plot else clean_title
    labels = {'title': clean_title, 'plot': clean_plot, 'mediatype': 'video'}
    if getKodiversion() < 20:
        li.setInfo("video", labels)
    else:
        infotag = li.getVideoInfoTag()
        infotag.setMediaType('video')
        infotag.setTitle(clean_title)
        infotag.setPlot(clean_plot)

    logo = logo or ICON
    li.setArt({'thumb': logo, 'poster': logo, 'banner': logo, 'icon': logo, 'fanart': FANART})
    li.setProperty("IsPlayable", 'false' if is_folder else 'true')
    if context_menu:
        li.addContextMenuItems(context_menu)
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=dir_url, listitem=li, isFolder=is_folder)


def closeDir():
    xbmcplugin.endOfDirectory(addon_handle)

def getKodiversion():
    try:
        return int(xbmc.getInfoLabel("System.BuildVersion")[:2])
    except:
        return 18

def Main_Menu():
    menu = [
        ['[B][COLOR gold]LIVE SPORTS SCHEDULE[/COLOR][/B]', 'sched', None],
        ['[B][COLOR gold]LIVE TV CHANNELS[/COLOR][/B]', 'live_tv', None],
        ['[B][COLOR gold]LIVE TV PAR LANGUE[/COLOR][/B]', 'lang_menu', None],
        ['[B][COLOR gold]FAVORITE LIVE TV CHANNELS[/COLOR][/B]', 'favorites', None],
        ['[B][COLOR gold]EXTRA CHANNELS / VODS[/COLOR][/B]', 'extra_channels',
         'https://images-ext-1.discordapp.net/external/fUzDq2SD022-veHyDJTHKdYTBzD9371EnrUscXXrf0c/%3Fsize%3D4096/https/cdn.discordapp.com/icons/1373713080206495756/1fe97e658bc7fb0e8b9b6df62259c148.png?format=webp&quality=lossless'],
        ['[B][COLOR gold]SEARCH EVENTS SCHEDULE[/COLOR][/B]', 'search', None],
        ['[B][COLOR gold]SEARCH LIVE TV CHANNELS[/COLOR][/B]', 'search_channels', None],
        ['[B][COLOR lime]EXPORT M3U / CONFIGURE PVR[/COLOR][/B]', 'export_m3u', None],
        ['[B][COLOR red]DIAGNOSTICS[/COLOR][/B]', 'diagnostics', None],
        ['[B][COLOR cyan]DADDYLIVE CHAT[/COLOR][/B]', 'chat', None],
    ]

    for title, mode_name, logo in menu:
        addDir(title, build_url({'mode': 'menu', 'serv_type': mode_name}), True, logo=logo)

    closeDir()


def run_diagnostics():
    def ok(text):
        return f'[COLOR lime][OK][/COLOR] {text}'
    def ko(text):
        return f'[COLOR red][KO][/COLOR] {text}'
    def info(text):
        return f'[COLOR cyan][INFO][/COLOR] {text}'

    version = addon.getAddonInfo('version')
    lines = [f'[B]DaddyLive v3 — v{version} — Diagnostics[/B]', '']

    # 0. Configuration summary
    lines.append('[B]0. Configuration[/B]')
    lines.append(info(f'Base active : {get_active_base()}'))
    lines.append(info(f'Seed URL    : {SEED_BASEURL}'))
    dns = addon.getSetting('custom_dns').strip()
    lines.append(info(f'DNS custom  : {dns or "(non configuré)"}'))
    seg_proxy = addon.getSetting('seg_proxy').strip()
    lines.append(info(f'Proxy segs  : {seg_proxy or "(non configuré)"}'))
    lines.append(info(f'ffmpegdirect: {addon.getSetting("use_ffmpegdirect")}'))
    if os.path.exists(IPTV_ORG_INDEX_CACHE):
        age_h = int((time.time() - os.path.getmtime(IPTV_ORG_INDEX_CACHE)) / 3600)
        try:
            with open(IPTV_ORG_INDEX_CACHE, 'r', encoding='utf-8') as _f:
                _idx = json.load(_f)
            lines.append(info(f'iptv-org    : {len(_idx)} entrées, mis à jour il y a {age_h}h'))
        except Exception:
            lines.append(info('iptv-org    : cache corrompu'))
    else:
        lines.append(info('iptv-org    : pas encore téléchargé'))
    lines.append('')

    # 1. Channel list
    url = abs_url('24-7-channels.php')
    lines.append(f'[B]1. Liste des chaînes[/B]  ({url})')
    fetched = False
    for verify_ssl in [True, False]:
        try:
            r = requests.get(url, headers={'User-Agent': UA}, timeout=10,
                             verify=verify_ssl, allow_redirects=True)
            cards = len(re.findall(r'class="card"', r.text))
            if cards > 0:
                lines.append(ok(f'HTTP {r.status_code} — {cards} chaînes trouvées'))
                fetched = True
                break
            else:
                lines.append(ko(f'HTTP {r.status_code} — 0 chaînes (verify={verify_ssl})'))
        except Exception as e:
            lines.append(ko(f'verify={verify_ssl}: {type(e).__name__}: {str(e)[:80]}'))
    if not fetched:
        lines.append(ko('Échec du chargement des chaînes'))
    lines.append('')

    # 2. Auth credentials
    lines.append('[B]2. Credentials auth[/B]')
    auth_token, channel_salt = None, None
    try:
        r2 = requests.get('https://www.ksohls.ru/premiumtv/daddyhd.php?id=51',
                          headers={'User-Agent': _AUTH_UA, 'Referer': get_active_base()},
                          timeout=10, verify=False)
        auth_token = _extract_credential(r2.text, 'authToken')
        channel_salt = _extract_credential(r2.text, 'channelSalt')
        if auth_token and channel_salt:
            lines.append(ok(f'HTTP {r2.status_code} — authToken + channelSalt OK'))
        else:
            lines.append(ko(f'HTTP {r2.status_code} — authToken={bool(auth_token)} channelSalt={bool(channel_salt)}'))
    except Exception as e:
        lines.append(ko(f'{type(e).__name__}: {str(e)[:80]}'))
    lines.append('')

    # 3. CDN m3u8 (avec auth)
    lines.append('[B]3. CDN m3u8[/B]')
    m3u8_url = resolve_stream_url('51')
    lines.append(info(f'URL : {m3u8_url}'))
    cdn_segs = []
    m3u8_content = ''
    try:
        m3u8_hdrs = {
            'User-Agent': _AUTH_UA,
            'Referer': PLAYER_REFERER,
        }
        if auth_token:
            m3u8_hdrs['Authorization'] = f'Bearer {auth_token}'
            m3u8_hdrs['X-Channel-Key'] = 'premium51'
        r3 = requests.get(m3u8_url, headers=m3u8_hdrs, timeout=10, verify=False)
        m3u8_content = r3.text
        cdn_segs = [l for l in m3u8_content.splitlines() if l and not l.startswith('#')]
        ct3 = r3.headers.get('Content-Type', '')
        if r3.status_code == 200 and cdn_segs:
            lines.append(ok(f'HTTP {r3.status_code} — {len(cdn_segs)} segments — CT: {ct3[:50]}'))
        else:
            lines.append(ko(f'HTTP {r3.status_code} — {len(cdn_segs)} segments — CT: {ct3[:50]}'))
            if not cdn_segs:
                lines.append(ko(f'Réponse: {m3u8_content[:120]}'))
    except Exception as e:
        lines.append(ko(f'{type(e).__name__}: {str(e)[:80]}'))
    lines.append('')

    # 4. CDN clé AES-128
    lines.append('[B]4. CDN clé AES[/B]')
    try:
        if auth_token and channel_salt:
            channel_key = 'premium51'
            # Extract real key_id from fetched m3u8 content
            km = re.search(r'/key/[^/]+/(\d+)', m3u8_content)
            key_id = km.group(1) if km else '5906764'
            lines.append(info(f'key_id : {key_id}'))
            ts = int(time.time())
            fp = _compute_fingerprint()
            nonce = _compute_pow_nonce(channel_key, channel_salt, key_id, ts)
            auth_sig = _compute_auth_sig(channel_key, channel_salt, key_id, ts, fp)
            r4 = requests.get(f'{CHEVY_LOOKUP}/key/{channel_key}/{key_id}',
                              headers={'User-Agent': _AUTH_UA, 'Referer': PLAYER_REFERER,
                                       'Authorization': f'Bearer {auth_token}',
                                       'X-Key-Timestamp': str(ts), 'X-Key-Nonce': str(nonce),
                                       'X-Key-Path': auth_sig, 'X-Fingerprint': fp},
                              timeout=10)
            if r4.status_code == 200 and len(r4.content) == 16:
                lines.append(ok('HTTP 200 — clé AES 16B OK'))
            else:
                lines.append(ko(f'HTTP {r4.status_code} — {len(r4.content)} octets'))
        else:
            lines.append(ko('Credentials manquants (étape 2 échouée)'))
    except Exception as e:
        lines.append(ko(f'{type(e).__name__}: {str(e)[:80]}'))
    lines.append('')

    # 5. Proxy local + m3u8 + segment
    lines.append('[B]5. Proxy local[/B]')
    try:
        _ensure_m3u8_proxy()
        port = _actual_proxy_port or M3U8_PROXY_PORT
        rh = requests.get(f'http://127.0.0.1:{port}/health', timeout=2)
        if rh.status_code == 200 and rh.text == 'daddylive-proxy':
            lines.append(ok(f'Proxy actif — port {port}'))
            if auth_token and channel_salt and m3u8_url:
                _set_channel_state('premium51', auth_token, channel_salt, m3u8_url)
                rm = requests.get(f'http://127.0.0.1:{port}/m3u8/premium51', timeout=12)
                proxy_segs = [l for l in rm.text.splitlines() if l and not l.startswith('#')]
                if rm.status_code == 200 and proxy_segs:
                    lines.append(ok(f'Proxy m3u8 : HTTP 200 — {len(proxy_segs)} segments réécrits'))
                    # Download first segment through proxy
                    first_seg = proxy_segs[0]
                    if '/seg/' in first_seg:
                        try:
                            rs = requests.get(first_seg, timeout=20)
                            ct_s = rs.headers.get('Content-Type', '')
                            if rs.status_code == 200 and 'html' not in ct_s.lower():
                                lines.append(ok(f'Segment test : HTTP 200 — {len(rs.content)}B — CT: {ct_s[:30]}'))
                            else:
                                lines.append(ko(f'Segment test : HTTP {rs.status_code} — CT: {ct_s[:40]}'))
                        except Exception as es:
                            lines.append(ko(f'Segment test : {type(es).__name__}: {str(es)[:60]}'))
                else:
                    lines.append(ko(f'Proxy m3u8 : HTTP {rm.status_code} — {len(proxy_segs)} segments'))
        else:
            lines.append(ko(f'Proxy ne répond pas (HTTP {rh.status_code})'))
    except Exception as e:
        lines.append(ko(f'Proxy : {type(e).__name__}: {str(e)[:80]}'))
    lines.append('')

    # 6. État stall (debug freezes)
    lines.append('[B]6. État stall[/B]')
    stall_keys = list(_m3u8_stall.keys())
    with _proxy_lock:
        cred_keys = list(_channel_creds.keys())
    if stall_keys:
        for k in stall_keys:
            st = _m3u8_stall.get(k, {})
            _age = int(time.time() - st.get('first_seen', time.time()))
            lines.append(info(f'{k}: seq={st.get("seq")} frozen={_age}s same_retries={st.get("same_url_retries", 0)}'))
    else:
        lines.append(ok('Aucun stall actif'))
    lines.append(info(f'Chaînes en cache : {", ".join(cred_keys) if cred_keys else "aucune"}'))

    # 7. CDN — état des serveurs chevy
    lines.append('')
    lines.append(f'[B]7. CDN — Serveurs {CHEVY_LOOKUP}[/B]')
    try:
        rh = requests.get(f'{CHEVY_LOOKUP}/health',
                          headers={'User-Agent': UA, 'Referer': PLAYER_REFERER},
                          timeout=6)
        if rh.status_code == 200:
            hdata = rh.json()
            top_status = hdata.get('status', 'ok')
            workers = hdata.get('workers', {})
            pool_ex = workers.get('poolExhausted', False)
            pending = workers.get('pendingHeirs', 0)
            daemon = hdata.get('daemon', {})
            using_fb = daemon.get('using_fallback', False)
            connected = daemon.get('connected', False)
            favorites_count = daemon.get('favorites_count', 0)
            # Pool exhausted but favorites worker present = still serving traffic
            globally_ko = (top_status != 'ok') or (pool_ex and favorites_count == 0 and not connected)
            pool_label = 'EXHAUSTED' if pool_ex else 'OK'
            fav_label_str = f'favorites:{favorites_count}'
            if globally_ko:
                lines.append(ko(f'Pool {pool_label} — {fav_label_str} — CDN KO'))
            elif pool_ex:
                lines.append(info(f'Pool {pool_label} (fallback via {fav_label_str}) — pendingHeirs:{pending}'))
            else:
                lines.append(ok(f'Pool {pool_label} — {fav_label_str} — pendingHeirs:{pending}'))
            lines.append(info(f'Daemon connecté : {connected} — using_fallback:{using_fb}'))
            # Per-server status: KO only if globally down
            servers = workers.get('servers', {})
            for sk, sdata in sorted(servers.items()):
                deaths = sdata.get('deaths', 0)
                avg_life = sdata.get('avgLife', '?')
                if globally_ko:
                    lines.append(ko(f'  {sk:<12} deaths:{deaths} — avgLife:{avg_life}s'))
                else:
                    lines.append(ok(f'  {sk:<12} deaths:{deaths} — avgLife:{avg_life}s (via favorites)'))
            # Honeypot & rate limits
            hp = hdata.get('honeypot', {})
            bans = hp.get('active_bans', 0)
            banned_sample = hp.get('banned_ips_sample', [])
            lines.append(info(f'Honeypot bans : {bans}' + (f' — {banned_sample[:3]}' if banned_sample else '')))
            rl = hdata.get('rate_limits', {})
            lines.append(info(f'Rate limits   : auth={rl.get("auth_tracked_ips",0)} ch={rl.get("channel_tracked_ips",0)}'))
            sl = hdata.get('server_locator', {})
            lines.append(info(f'Locator cache : {sl.get("cache_size",0)} entrées — hit rate {sl.get("hit_rate_percent","?")}%'))
            sess = hdata.get('sessions', {}).get('active', 0)
            lines.append(info(f'Sessions actives : {sess}'))
        else:
            lines.append(ko(f'Health endpoint : HTTP {rh.status_code}'))
    except Exception as e:
        lines.append(ko(f'{type(e).__name__}: {str(e)[:80]}'))

    # Local CDN cache summary
    lines.append('')
    if os.path.exists(_CDN_CACHE_FILE):
        age_m = int((time.time() - os.path.getmtime(_CDN_CACHE_FILE)) / 60)
        try:
            with open(_CDN_CACHE_FILE, 'r') as _f:
                _cdn = json.load(_f)
            _sk_counts = {}
            for _sk in _cdn.values():
                _sk_counts[_sk] = _sk_counts.get(_sk, 0) + 1
            _summary = ', '.join(f'{k}:{v}' for k, v in sorted(_sk_counts.items(), key=lambda x: -x[1]))
            lines.append(info(f'Cache CDN local : {len(_cdn)} ch, âge {age_m}min — {_summary}'))
        except Exception:
            lines.append(info('Cache CDN local : corrompu'))
    else:
        lines.append(info('Cache CDN local : non généré (ouvrir "LIVE TV PAR CDN" d\'abord)'))

    msg = '\n'.join(lines)
    log(f'[Diagnostics]\n{msg}')
    xbmcgui.Dialog().textviewer(f'DaddyLive v3 v{version} — Diagnostics', msg)

def getCategTrans():
    schedule_url = abs_url('index.php')
    try:
        html_text = fetch_via_proxy(schedule_url, headers={'User-Agent': UA, 'Referer': get_active_base()})
        m = re.search(r'<div[^>]+class="filters"[^>]*>(.*?)</div>', html_text, re.IGNORECASE | re.DOTALL)
        if not m:
            log("getCategTrans(): filters block not found")
            return []

        block = m.group(1)
        anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
        if not anchors:
            log("getCategTrans(): no <a> items in filters block")
            return []

        categs = []
        seen = set()
        for href, text_content in anchors:
            name = html.unescape(re.sub(r'\s+', ' ', text_content)).strip()
            if not name or name.lower() == 'all':
                continue
            if name in seen:
                continue
            seen.add(name)
            categs.append((name, '[]'))

        return categs
    except Exception as e:
        xbmcgui.Dialog().ok("Error", f"Error fetching category data: {e}")
        log(f'index parse fail: url={schedule_url} err={e}')
        return []

def Menu_Trans():
    categs = getCategTrans()
    if not categs:
        return
    for categ_name, _ in categs:
        addDir(categ_name, build_url({'mode': 'showChannels', 'trType': categ_name}))
    closeDir()

def ShowChannels(categ, channels_list):
    for item in channels_list:
        title = item.get('title')
        addDir(title, build_url({'mode': 'trList', 'trType': categ, 'channels': json.dumps(item.get('channels'))}), True)
    closeDir()

def getTransData(categ):
    try:
        url = abs_url('index.php?cat=' + quote_plus(categ))
        html_text = fetch_via_proxy(url, headers={'User-Agent': UA, 'Referer': get_active_base()})
        cut = re.search(r'<h2\s+class="collapsible-header\b', html_text, re.IGNORECASE)
        if cut:
            html_text = html_text[:cut.start()]

        events = re.findall(
            r'<div\s+class="schedule__event">.*?'
            r'<div\s+class="schedule__eventHeader"[^>]*?>\s*'
            r'(?:<[^>]+>)*?'
            r'<span\s+class="schedule__time"[^>]*data-time="([^"]+)"[^>]*>.*?</span>\s*'
            r'<span\s+class="schedule__eventTitle">\s*([^<]+)\s*</span>.*?'
            r'</div>\s*'
            r'<div\s+class="schedule__channels">(.*?)</div>',
            html_text, re.IGNORECASE | re.DOTALL
        )

        trns = []
        for time_str, event_title, channels_block in events:
            event_time_local = get_local_time(time_str.strip())
            title = f'[COLOR gold]{event_time_local}[/COLOR] {html.unescape(event_title.strip())}'

            chans = []
            for href, title_attr, link_text in re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>',
                channels_block, re.IGNORECASE | re.DOTALL
            ):
                try:
                    u = urlparse(href)
                    qs = dict(parse_qsl(u.query))
                    cid = qs.get('id') or ''
                except Exception:
                    cid = ''
                name = html.unescape((title_attr or link_text).strip())
                if cid:
                    chans.append({'channel_name': name, 'channel_id': cid})

            if chans:
                trns.append({'title': title, 'channels': chans})

        return trns
    except Exception as e:
        log(f'getTransData error for categ={categ}: {e}')
        return []

def TransList(categ, channels):
    dead_cids = _get_dead_cids()
    fav_ids = {f['id'] for f in get_favorites()}
    for channel in channels:
        channel_title = html.unescape(channel.get('channel_name'))
        channel_id = str(channel.get('channel_id', '')).strip()
        if not channel_id:
            continue
        label = _ch_label(channel_title, channel_id, dead_cids)
        fav_label = '★ Retirer des favoris' if channel_id in fav_ids else '☆ Ajouter aux favoris'
        ctx = [(fav_label, 'RunPlugin(%s)' % build_url({'mode': 'toggle_fav', 'cid': channel_id, 'name': channel_title}))]
        addDir(label, build_url({'mode': 'trLinks', 'trData': json.dumps({'channels': [{'channel_name': channel_title, 'channel_id': channel_id}]})}), False, context_menu=ctx)
    closeDir()

def getSource(trData):
    try:
        data = json.loads(unquote(trData))
        channels_data = data.get('channels')
        if channels_data and isinstance(channels_data, list):
            cid = str(channels_data[0].get('channel_id', '')).strip()
            if not cid:
                return
            if '%7C' in cid or '|' in cid:
                url_stream = abs_url('watchs2watch.php?id=' + cid)
            else:
                url_stream = abs_url('watch.php?id=' + cid)
            xbmcplugin.setContent(addon_handle, 'videos')
            PlayStream(url_stream)
    except Exception as e:
        log(f'getSource failed: {e}')

def get_favorites():
    try:
        return json.loads(addon.getSetting('favorites') or '[]')
    except:
        return []

def save_favorites(favs):
    addon.setSetting('favorites', json.dumps(favs))

def toggle_favorite(cid, name):
    favs = get_favorites()
    ids = [f['id'] for f in favs]
    if cid in ids:
        favs = [f for f in favs if f['id'] != cid]
        save_favorites(favs)
        xbmcgui.Dialog().notification('DaddyLive v3', f'Retiré des favoris : {name}', ICON, 2000)
    else:
        favs.append({'id': cid, 'name': name})
        save_favorites(favs)
        xbmcgui.Dialog().notification('DaddyLive v3', f'Ajouté aux favoris : {name}', ICON, 2000)
    xbmc.executebuiltin('Container.Refresh')

def list_favorites():
    favs = get_favorites()
    if not favs:
        xbmcgui.Dialog().notification('DaddyLive v3', 'Aucun favori. Appui long sur une chaîne pour ajouter.', ICON, 3000)
        closeDir()
        return
    # Auto-probe on first open (cooldown of 120s prevents re-running on every open)
    _probe_favorites_background(favs)
    fav_ids = {f['id'] for f in favs}
    dead_cids = _get_dead_cids()
    # Load CDN map from cache to show CDN name on red channels
    _fav_cdn_map = {}
    try:
        if os.path.exists(_CDN_CACHE_FILE):
            with open(_CDN_CACHE_FILE, 'r') as _f:
                _fav_cdn_map = json.load(_f)
    except Exception:
        pass
    ev_map = _build_current_events_map()
    # EPG (epgshare01 XMLTV) has priority over the DaddyLive sports schedule
    xmltv_programs = _fetch_xmltv_fr_epg([(f['id'], f['name']) for f in favs])
    ev_map.update(xmltv_programs)
    addDir('[B][COLOR cyan]Vérifier les chaînes[/COLOR][/B]', build_url({'mode': 'probe_favorites'}), False)
    for fav in sorted(favs, key=lambda x: x['name'].lower()):
        cid = fav['id']
        name = fav['name']
        cdn_name = _fav_cdn_map.get(cid) if cid in dead_cids else None
        ctx = [('Retirer des favoris', 'RunPlugin(%s)' % build_url({'mode': 'toggle_fav', 'cid': cid, 'name': name}))]
        ev = ev_map.get(cid)
        label = f'{_ch_label(name, cid, dead_cids, cdn_name)} ({cid})'
        if ev:
            label += f'  [COLOR gold]{ev}[/COLOR]'
        addDir(label, build_url({'mode': 'play', 'url': abs_url('watch.php?id=' + cid)}), False, context_menu=ctx, plot=ev)
    closeDir()

def _normalize_ch_name(name):
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'([a-z])(\d)', r'\1 \2', name)  # "sport360" → "sport 360"
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# Pass 1 — mots de langue/pays (≥3 car.) présents n'importe où dans le nom
_NAME_TO_LANG = {
    'arabic': 'ara', 'arab': 'ara',
    'english': 'eng', 'british': 'eng',
    'french': 'fra',
    'german': 'deu', 'deutsch': 'deu',
    'spanish': 'spa',
    'italian': 'ita',
    'portuguese': 'por',
    'turkish': 'tur',
    'russian': 'rus',
    'polish': 'pol',
    'romanian': 'ron',
    'dutch': 'nld',
    'greek': 'ell',
    'hebrew': 'heb',
    'persian': 'fas', 'farsi': 'fas',
    'hindi': 'hin', 'indian': 'hin',
    'urdu': 'urd',
    'swedish': 'swe',
    'norwegian': 'nor',
    'danish': 'dan',
    'finnish': 'fin',
    'czech': 'ces',
    'slovak': 'slk',
    'croatian': 'hrv',
    'serbian': 'srp',
    'bulgarian': 'bul',
    'hungarian': 'hun',
    'malay': 'msa', 'malaysian': 'msa',
    'indonesian': 'ind',
    'chinese': 'zho',
    'japanese': 'jpn',
    'korean': 'kor',
    'thai': 'tha',
    'vietnamese': 'vie',
    # Noms de pays
    'france': 'fra',
    'usa': 'eng', 'america': 'eng', 'american': 'eng',
    'germany': 'deu',
    'spain': 'spa',
    'italy': 'ita',
    'portugal': 'por',
    'netherlands': 'nld',
    'turkey': 'tur',
    'russia': 'rus',
    'poland': 'pol',
    'romania': 'ron',
    'greece': 'ell',
    'israel': 'heb',
    'iran': 'fas',
    'india': 'hin',
    'pakistan': 'urd',
    'malaysia': 'msa',
    'indonesia': 'ind',
    'china': 'zho',
    'japan': 'jpn',
    'korea': 'kor',
    'thailand': 'tha',
    'vietnam': 'vie',
    'brazil': 'por', 'brasil': 'por',
    'mexico': 'spa',
    'argentina': 'spa',
    'colombia': 'spa',
    'belgium': 'fra',
    'switzerland': 'deu',
    'austria': 'deu',
    'sweden': 'swe',
    'norway': 'nor',
    'denmark': 'dan',
    'finland': 'fin',
}

# Pass 1 — codes ISO 2 lettres, vérifiés UNIQUEMENT comme dernier mot du nom
_CODE_TO_LANG = {
    'fr': 'fra', 'de': 'deu', 'es': 'spa', 'it': 'ita', 'pt': 'por',
    'nl': 'nld', 'tr': 'tur', 'ru': 'rus', 'pl': 'pol', 'ro': 'ron',
    'gr': 'ell', 'il': 'heb', 'ae': 'ara', 'sa': 'ara', 'ar': 'ara',
    'uk': 'eng', 'us': 'eng', 'gb': 'eng', 'au': 'eng', 'ca': 'eng',
    'be': 'fra', 'ch': 'deu', 'at': 'deu',
    'se': 'swe', 'no': 'nor', 'dk': 'dan', 'fi': 'fin',
    'hr': 'hrv', 'rs': 'srp', 'bg': 'bul', 'hu': 'hun',
    'sk': 'slk', 'cz': 'ces',
    'pk': 'urd', 'mx': 'spa', 'br': 'por',
    'my': 'msa', 'cn': 'zho', 'jp': 'jpn', 'kr': 'kor',
    'th': 'tha', 'vn': 'vie',
}


def _lang_from_name(name):
    """Pass 1 : détecte la langue depuis les mots explicites du nom de chaîne.
    - Dernier mot : vérifié dans _NAME_TO_LANG ET _CODE_TO_LANG.
    - Autres mots (droite→gauche) : _NAME_TO_LANG uniquement (pas de codes 2 lettres).
    Retourne un code langue ou None."""
    words = re.findall(r'[a-z]+', name.lower())
    if not words:
        return None
    last = words[-1]
    if last in _NAME_TO_LANG:
        return _NAME_TO_LANG[last]
    if last in _CODE_TO_LANG:
        return _CODE_TO_LANG[last]
    for word in reversed(words[:-1]):
        if word in _NAME_TO_LANG:
            return _NAME_TO_LANG[word]
    return None

def _get_iptv_org_index():
    """Fetch/cache iptv-org channels.json, return normalized_name→lang_code index."""
    if os.path.exists(IPTV_ORG_INDEX_CACHE):
        if time.time() - os.path.getmtime(IPTV_ORG_INDEX_CACHE) < IPTV_ORG_TTL:
            try:
                with open(IPTV_ORG_INDEX_CACHE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    try:
        log('[iptv-org] Fetching channels database...')
        r = requests.get(IPTV_ORG_API, timeout=30)
        index = {}
        tvg_index = {}  # normalized_name → tvg_id (e.g. "BBCOne.uk")
        for ch in r.json():
            tvg_id = ch.get('id', '')
            country = ch.get('country', '')
            lang = COUNTRY_LANG.get(country)
            candidates = [ch.get('name', '')] + ch.get('alt_names', [])
            for candidate in candidates:
                norm = _normalize_ch_name(candidate)
                if norm and tvg_id and norm not in tvg_index:
                    tvg_index[norm] = tvg_id
            if not lang:
                continue
            for candidate in candidates:
                norm = _normalize_ch_name(candidate)
                if norm and norm not in index:
                    index[norm] = lang
        with open(IPTV_ORG_INDEX_CACHE, 'w', encoding='utf-8') as f:
            json.dump(index, f)
        with open(IPTV_ORG_TVG_CACHE, 'w', encoding='utf-8') as f:
            json.dump(tvg_index, f)
        log(f'[iptv-org] Index built: {len(index)} entries, {len(tvg_index)} tvg IDs')
        return index
    except Exception as e:
        log(f'[iptv-org] Fetch error: {e}')
        return {}

def _lookup_lang(name, index):
    """Retourne le code langue d'une chaîne.
    Pass 1 : détection depuis les mots du nom (pays/langue explicites).
    Pass 2 : recherche dans l'index iptv-org, avec plusieurs normalisations."""
    # Pass 1 — nom seul, sans index
    lang = _lang_from_name(name)
    if lang:
        return lang

    # Pass 2 — index iptv-org
    # Normalise le nom, puis retire progressivement les suffixes pays/langue
    # pour améliorer les chances de correspondance dans la base.
    norm = _normalize_ch_name(name)

    # 2a. Correspondance exacte
    if norm in index:
        return index[norm]

    # 2b. Retire le numéro final ("Sky Sports 1" → "Sky Sports")
    no_num = re.sub(r'\s+\d+$', '', norm).strip()
    if no_num != norm and no_num in index:
        return index[no_num]

    # 2c. Retire le dernier mot s'il est un indicateur pays/langue,
    #     puis recherche à nouveau (avec et sans numéro final)
    parts = norm.split()
    if len(parts) > 1:
        last_word = parts[-1]
        if last_word in _NAME_TO_LANG or last_word in _CODE_TO_LANG:
            stripped = ' '.join(parts[:-1]).strip()
            if stripped in index:
                return index[stripped]
            no_num2 = re.sub(r'\s+\d+$', '', stripped).strip()
            if no_num2 != stripped and no_num2 in index:
                return index[no_num2]

    return None


def _get_iptv_org_tvg_index():
    """Return normalized_name → iptv-org tvg_id (e.g. 'BBCOne.uk'). Built alongside lang index."""
    if os.path.exists(IPTV_ORG_TVG_CACHE):
        try:
            with open(IPTV_ORG_TVG_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Trigger rebuild (downloads channels.json and saves both caches)
    _get_iptv_org_index()
    try:
        with open(IPTV_ORG_TVG_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _channel_name_to_tvg_id(name, tvg_index):
    """Map a DaddyLive channel name to an iptv-org tvg_id using progressive name stripping."""
    norm = _normalize_ch_name(name)
    if norm in tvg_index:
        return tvg_index[norm]
    # Remove trailing quality/number suffix: HD, SD, FHD, UHD, 4K, +1, digits
    stripped = re.sub(r'\s+(?:hd|sd|fhd|uhd|4k|\+\d+|\d+)$', '', norm).strip()
    if stripped != norm and stripped in tvg_index:
        return tvg_index[stripped]
    # Remove trailing number only
    no_num = re.sub(r'\s+\d+$', '', stripped or norm).strip()
    if no_num not in (norm, stripped) and no_num in tvg_index:
        return tvg_index[no_num]
    # Remove trailing country/lang word
    parts = (stripped or norm).split()
    if len(parts) > 1 and parts[-1] in _NAME_TO_LANG:
        base = ' '.join(parts[:-1]).strip()
        if base in tvg_index:
            return tvg_index[base]
        base_no_num = re.sub(r'\s+\d+$', '', base).strip()
        if base_no_num != base and base_no_num in tvg_index:
            return tvg_index[base_no_num]
    return None


def _fetch_epg_best_programs(tvg_ids):
    """Return {tvg_id: current_program_title} for the given tvg_ids, cached 30 min."""
    if not tvg_ids:
        return {}
    now_ts = time.time()
    # Load per-channel cache
    cached = {}
    try:
        if os.path.exists(_EPG_BEST_CACHE_FILE):
            with open(_EPG_BEST_CACHE_FILE, 'r', encoding='utf-8') as f:
                cached = json.load(f)
    except Exception:
        pass
    to_fetch = [tid for tid in tvg_ids if now_ts - cached.get(tid, {}).get('ts', 0) > _EPG_BEST_TTL]
    if to_fetch:
        today = time.strftime('%Y-%m-%d', time.gmtime())
        params = '&'.join('channels[]=' + quote_plus(tid) for tid in to_fetch)
        url = f'https://epg.best/api/programmes?date={today}&{params}&per_page=200'
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': UA})
            data = resp.json()
            for tvg_id, programs in data.get('data', {}).items():
                prog_now = ''
                for prog in programs:
                    if prog.get('start_utc', 0) <= now_ts <= prog.get('stop_utc', 0):
                        prog_now = prog.get('title', '')
                        break
                cached[tvg_id] = {'ts': now_ts, 'program': prog_now}
            # Mark IDs that returned no data (avoid re-fetching)
            for tid in to_fetch:
                if tid not in cached:
                    cached[tid] = {'ts': now_ts, 'program': ''}
        except Exception as e:
            log(f'[epg.best] error: {e}')
        try:
            with open(_EPG_BEST_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cached, f)
        except Exception:
            pass
    return {tid: cached[tid]['program'] for tid in tvg_ids if cached.get(tid, {}).get('program')}


def _fetch_xmltv_fr_epg(cid_name_pairs):
    """Return {cid: current_program_title} from epgshare01 French XMLTV (free, no auth).

    Downloads epg_ripper_FR1.xml.gz once every 4h, parses in ~0.2s, caches results 30min.
    cid_name_pairs: list of (daddylive_channel_id, channel_name)
    """
    if not cid_name_pairs:
        return {}
    now_ts = time.time()

    # Load 30-min program cache
    prog_cache = {}
    try:
        if os.path.exists(_XMLTV_PROG_CACHE) and now_ts - os.path.getmtime(_XMLTV_PROG_CACHE) < _XMLTV_PROG_TTL:
            with open(_XMLTV_PROG_CACHE, 'r', encoding='utf-8') as f:
                prog_cache = json.load(f)
    except Exception:
        pass

    need_lookup = [p for p in cid_name_pairs if p[0] not in prog_cache]
    if not need_lookup:
        return {cid: prog_cache[cid] for cid, _ in cid_name_pairs if prog_cache.get(cid)}

    # Ensure XMLTV file is fresh (4h TTL)
    xml_gz = None
    if os.path.exists(_XMLTV_FR_CACHE_FILE) and now_ts - os.path.getmtime(_XMLTV_FR_CACHE_FILE) < _XMLTV_FR_TTL:
        try:
            with open(_XMLTV_FR_CACHE_FILE, 'rb') as f:
                xml_gz = f.read()
        except Exception:
            pass
    if xml_gz is None:
        try:
            log('[xmltv-fr] Downloading EPG...')
            resp = requests.get(_XMLTV_FR_URL, timeout=20, headers={'User-Agent': UA})
            xml_gz = resp.content
            with open(_XMLTV_FR_CACHE_FILE, 'wb') as f:
                f.write(xml_gz)
            log(f'[xmltv-fr] Downloaded {len(xml_gz)//1024}KB')
        except Exception as e:
            log(f'[xmltv-fr] Download error: {e}')
            for cid, _ in need_lookup:
                prog_cache[cid] = ''
            return {}

    try:
        xml_str = gzip.decompress(xml_gz).decode('utf-8', errors='replace')
    except Exception as e:
        log(f'[xmltv-fr] Decompress error: {e}')
        return {}

    # Collect channel IDs that actually have programme entries (some IDs are defined but empty)
    active_channels = set(re.findall(r'<programme channel="([^"]+)"', xml_str))

    # Build display_name → xmltv_id index, preferring IDs that have programme data
    xmltv_idx = {}
    for xmltv_id, display_name in re.findall(
        r'<channel id="([^"]+)"[^>]*>.*?<display-name[^>]*>([^<]+)</display-name>',
        xml_str, re.DOTALL
    ):
        norm = _normalize_ch_name(display_name)
        if not norm:
            continue
        if norm not in xmltv_idx:
            xmltv_idx[norm] = xmltv_id
        elif xmltv_id in active_channels and xmltv_idx[norm] not in active_channels:
            # Replace inactive ID with one that actually has programmes
            xmltv_idx[norm] = xmltv_id

    # Match each DaddyLive channel name to an XMLTV ID
    cid_to_xmltv = {}
    for cid, name in need_lookup:
        xmltv_id = _channel_name_to_tvg_id(name, xmltv_idx)
        if xmltv_id:
            cid_to_xmltv[cid] = xmltv_id
        else:
            prog_cache[cid] = ''  # no match, don't retry until cache expires

    if not cid_to_xmltv:
        try:
            with open(_XMLTV_PROG_CACHE, 'w', encoding='utf-8') as f:
                json.dump(prog_cache, f)
        except Exception:
            pass
        return {}

    # Parse timestamps helper
    def _parse_xmltv_ts(s):
        s = s.strip()
        main = s[:14]
        tz = s[15:] if len(s) > 14 else '+0000'
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        dt = _dt.strptime(main, '%Y%m%d%H%M%S')
        sign = 1 if tz[0] == '+' else -1
        h, m = int(tz[1:3]), int(tz[3:5])
        return (_dt(*dt.timetuple()[:6]) - _td(hours=h*sign, minutes=m*sign)).replace(tzinfo=_tz.utc).timestamp()

    # Scan programmes for matching XMLTV IDs
    target_xmltv = set(cid_to_xmltv.values())
    xmltv_to_program = {}
    for m in re.finditer(
        r'<programme channel="([^"]+)" start="([^"]+)" stop="([^"]+)"[^>]*>.*?<title[^>]*>([^<]+)</title>',
        xml_str, re.DOTALL
    ):
        xmltv_id, start_str, stop_str, title = m.groups()
        if xmltv_id not in target_xmltv or xmltv_id in xmltv_to_program:
            continue
        try:
            if _parse_xmltv_ts(start_str) <= now_ts <= _parse_xmltv_ts(stop_str):
                xmltv_to_program[xmltv_id] = html.unescape(title)
        except Exception:
            pass

    for cid, xmltv_id in cid_to_xmltv.items():
        prog_cache[cid] = xmltv_to_program.get(xmltv_id, '')

    try:
        with open(_XMLTV_PROG_CACHE, 'w', encoding='utf-8') as f:
            json.dump(prog_cache, f)
    except Exception:
        pass

    return {cid: prog_cache[cid] for cid, _ in cid_name_pairs if prog_cache.get(cid)}


def list_by_language():
    """Show language folders for all 24/7 channels."""
    xbmcgui.Dialog().notification('DaddyLive', 'Chargement base langue...', ICON, 2000)
    ch_list = channels()
    if not ch_list:
        closeDir()
        return
    index = _get_iptv_org_index()
    if not index:
        xbmcgui.Dialog().notification('DaddyLive', 'Base iptv-org indisponible', ICON, 4000)
        closeDir()
        return
    lang_counts = {}
    unclassified = 0
    for href, name in ch_list:
        lang = _lookup_lang(name, index)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        else:
            unclassified += 1
    for lang_code, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        lang_name = LANG_NAMES.get(lang_code, lang_code.upper())
        addDir(f'[B]{lang_name}[/B]  ({count})', build_url({'mode': 'lang_channels', 'lang': lang_code}), True)
    if unclassified:
        addDir(f'[Non classé]  ({unclassified})', build_url({'mode': 'lang_channels', 'lang': '__none__'}), True)
    closeDir()

def list_lang_channels(lang_code):
    """Show channels matching a language code (or unclassified if lang_code='__none__')."""
    xbmcplugin.setContent(addon_handle, 'videos')
    ch_list = channels()
    index = _get_iptv_org_index()
    fav_ids = {f['id'] for f in get_favorites()}
    dead_cids = _get_dead_cids()
    for href, name in ch_list:
        cid_m = re.search(r'id=(\d+)', href)
        cid = cid_m.group(1) if cid_m else ''
        ch_lang = _lookup_lang(name, index) if index else None
        if lang_code == '__none__':
            if ch_lang is not None:
                continue
        else:
            if ch_lang != lang_code:
                continue
        fav_label = '★ Retirer des favoris' if cid in fav_ids else '☆ Ajouter aux favoris'
        ctx = [(fav_label, 'RunPlugin(%s)' % build_url({'mode': 'toggle_fav', 'cid': cid, 'name': name}))] if cid else []
        label = f'{_ch_label(name, cid, dead_cids)} ({cid})' if cid else name
        addDir(label, build_url({'mode': 'play', 'url': abs_url(href)}), False, context_menu=ctx)
    closeDir()

def _get_cdn_dead_servers():
    """Return frozenset of server_keys currently KO. Cached 5 min to file."""
    try:
        if os.path.exists(_CDN_STATUS_CACHE_FILE) and \
                time.time() - os.path.getmtime(_CDN_STATUS_CACHE_FILE) < _CDN_STATUS_TTL:
            with open(_CDN_STATUS_CACHE_FILE, 'r') as f:
                return frozenset(json.load(f))
    except Exception:
        pass
    dead = set()
    try:
        resp = requests.get(f'{CHEVY_LOOKUP}/health',
                            headers={'User-Agent': UA, 'Referer': PLAYER_REFERER},
                            timeout=3)
        if resp.status_code == 200:
            hdata = resp.json()
            top_status = hdata.get('status', 'ok')
            workers = hdata.get('workers', {})
            daemon = hdata.get('daemon', {})
            pool_ex = workers.get('poolExhausted', False)
            # favorites workers can serve traffic even when pool is exhausted
            favorites_count = daemon.get('favorites_count', 0)
            connected = daemon.get('connected', True)
            # CDN is truly KO only if status is not ok, OR pool exhausted with no fallback at all
            globally_ko = (top_status != 'ok') or (pool_ex and favorites_count == 0 and not connected)
            if globally_ko:
                for sk in workers.get('servers', {}):
                    dead.add(sk)
    except Exception:
        pass
    try:
        with open(_CDN_STATUS_CACHE_FILE, 'w') as f:
            json.dump(list(dead), f)
    except Exception:
        pass
    return frozenset(dead)

def _refresh_favorites_debounced():
    """Trigger Container.Refresh at most once every _FAV_REFRESH_DEBOUNCE seconds."""
    try:
        try:
            last_ts = float(open(_FAV_REFRESH_TS_FILE).read().strip())
        except Exception:
            last_ts = 0
        now = time.time()
        if now - last_ts < _FAV_REFRESH_DEBOUNCE:
            return
        open(_FAV_REFRESH_TS_FILE, 'w').write(str(now))
        xbmc.executebuiltin('Container.Refresh')
        log('[FailedCache] Container.Refresh triggered (channel marked KO)')
    except Exception:
        pass


def _mark_channel_failed(channel_key):
    """Record a channel content failure (no valid video segments) for red-label coloring."""
    try:
        failed = {}
        if os.path.exists(_FAILED_CHANNELS_FILE):
            with open(_FAILED_CHANNELS_FILE, 'r') as f:
                failed = json.load(f)
        now = time.time()
        failed[channel_key] = now
        # Prune expired entries while we have the file open
        failed = {k: v for k, v in failed.items() if now - v < _FAILED_CHANNEL_TTL}
        _dir = os.path.dirname(_FAILED_CHANNELS_FILE)
        fd, tmp_path = tempfile.mkstemp(dir=_dir)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(failed, f)
            os.replace(tmp_path, _FAILED_CHANNELS_FILE)
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            raise
    except Exception:
        pass
    # Debounced Container.Refresh so favorites list updates when user returns to it
    _refresh_favorites_debounced()


def _clear_channel_failed(channel_key):
    """Remove a channel from the failed cache (probe confirmed it's working again)."""
    try:
        if not os.path.exists(_FAILED_CHANNELS_FILE):
            return False
        with open(_FAILED_CHANNELS_FILE, 'r') as f:
            failed = json.load(f)
        if channel_key in failed:
            del failed[channel_key]
            _dir = os.path.dirname(_FAILED_CHANNELS_FILE)
            fd, tmp_path = tempfile.mkstemp(dir=_dir)
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(failed, f)
                os.replace(tmp_path, _FAILED_CHANNELS_FILE)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise
            return True
    except Exception:
        pass
    return False


def _probe_favorites_background(favs, force=False):
    """Probe each favorite channel's m3u8 in background; update failed cache and refresh list."""
    log(f'[ProbeBackground] Called with {len(favs)} favorites (force={force})')
    with _probe_lock:
        now = time.time()
        if not force:
            # Cooldown persisted in a file so it survives across Kodi plugin invocations
            try:
                last_ts = float(open(_FAV_PROBE_TS_FILE).read().strip())
            except Exception:
                last_ts = 0
            elapsed = now - last_ts
            if elapsed < _FAV_PROBE_COOLDOWN:
                log(f'[ProbeBackground] Skipped — cooldown ({int(_FAV_PROBE_COOLDOWN - elapsed)}s remaining)')
                return
        # Mark probe as started immediately to avoid race between concurrent addon invocations
        try:
            open(_FAV_PROBE_TS_FILE, 'w').write(str(now))
        except Exception:
            pass

    log(f'[ProbeBackground] Launching background thread')

    def _run():
        try:
            log(f'[ProbeBackground] Thread started — probing {len(favs)} favorites')
            # Load CDN map for server keys (from cache — no blocking rebuild)
            cdn_map = {}
            try:
                if os.path.exists(_CDN_CACHE_FILE):
                    with open(_CDN_CACHE_FILE, 'r') as f:
                        cdn_map = json.load(f)
                log(f'[ProbeBackground] CDN cache loaded ({len(cdn_map)} entries)')
            except Exception as e:
                log(f'[ProbeBackground] CDN cache load failed: {e}')

            def probe_one(fav):
                cid = fav['id']
                channel_key = f'premium{cid}'
                sk = cdn_map.get(cid)
                if not sk or sk == 'unknown':
                    # Try live lookup — quick, already cached by chevy
                    try:
                        resp = requests.get(
                            f'{CHEVY_LOOKUP}/server_lookup?channel_id={channel_key}',
                            headers={'User-Agent': UA, 'Referer': PLAYER_REFERER},
                            timeout=3
                        )
                        sk = resp.json().get('server_key', 'unknown')
                    except Exception:
                        sk = 'unknown'
                if sk == 'unknown':
                    log(f'[ProbeBackground] {channel_key}: no server key — skipped')
                    return cid, None  # skip — no server key
                url = f'{CHEVY_PROXY}/proxy/{sk}/{channel_key}/mono.css'
                ok = _probe_hls_url(url)
                log(f'[ProbeBackground] {channel_key} ({sk}): {"OK" if ok else "KO" if ok is False else "skip"}')
                return cid, ok

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(probe_one, favs))

            n_ok = sum(1 for _, ok in results if ok is True)
            n_ko = sum(1 for _, ok in results if ok is False)
            n_skip = sum(1 for _, ok in results if ok is None)
            changed = False
            for cid, ok in results:
                channel_key = f'premium{cid}'
                if ok is False:
                    _mark_channel_failed(channel_key)
                    changed = True
                    log(f'[ProbeBackground] {channel_key}: KO → marked red')
                elif ok is True:
                    if _clear_channel_failed(channel_key):
                        changed = True
                        log(f'[ProbeBackground] {channel_key}: OK → cleared red')

            if changed:
                xbmc.executebuiltin('Container.Refresh')
            log(f'[ProbeBackground] Done — {n_ok} OK / {n_ko} KO / {n_skip} skip — {"refreshed" if changed else "no change"}')
        except Exception as e:
            log(f'[ProbeBackground] Error: {e}')
            import traceback
            log(f'[ProbeBackground] Traceback: {traceback.format_exc()}')

    threading.Thread(target=_run, daemon=True).start()


def _get_dead_cids():
    """Return frozenset of channel IDs: CDN KO servers + recently failed content."""
    dead = set()
    # CDN server health
    dead_servers = _get_cdn_dead_servers()
    if dead_servers:
        try:
            if os.path.exists(_CDN_CACHE_FILE):
                with open(_CDN_CACHE_FILE, 'r') as f:
                    cdn_map = json.load(f)
                dead.update(cid for cid, sk in cdn_map.items() if sk in dead_servers)
        except Exception:
            pass
    # Proxy-level content failures (no valid video segments served)
    try:
        if os.path.exists(_FAILED_CHANNELS_FILE):
            with open(_FAILED_CHANNELS_FILE, 'r') as f:
                failed = json.load(f)
            now = time.time()
            for k, t in failed.items():
                if now - t < _FAILED_CHANNEL_TTL:
                    m = re.match(r'^premium(\d+)$', k)
                    if m:
                        dead.add(m.group(1))
    except Exception:
        pass
    return frozenset(dead)

def _ch_label(name, cid, dead_cids, cdn_name=None):
    """Wrap label in red if channel is KO. Optionally append CDN name."""
    if cid and cid in dead_cids:
        suffix = f' ({cdn_name})' if cdn_name else ''
        return f'[COLOR red]{name}{suffix}[/COLOR]'
    return name

def _get_cdn_map(ch_list):
    """Return {channel_id: server_key} for all channels, using a 1-hour file cache."""
    try:
        if os.path.exists(_CDN_CACHE_FILE) and time.time() - os.path.getmtime(_CDN_CACHE_FILE) < _CDN_CACHE_TTL:
            with open(_CDN_CACHE_FILE, 'r') as f:
                cached = json.load(f)
            log(f'[CDN] Loaded cdn_map from cache ({len(cached)} channels)')
            return cached
    except Exception:
        pass

    cid_list = []
    for href, name in ch_list:
        cid_m = re.search(r'id=(\d+)', href)
        cid = cid_m.group(1) if cid_m else None
        if cid:
            cid_list.append((cid, href, name))

    def fetch_sk(item):
        cid, href, name = item
        channel_key = f'premium{cid}'
        try:
            resp = requests.get(
                f'{CHEVY_LOOKUP}/server_lookup?channel_id={channel_key}',
                headers={'User-Agent': UA, 'Referer': PLAYER_REFERER},
                timeout=4
            )
            return cid, resp.json().get('server_key', 'unknown')
        except Exception:
            return cid, 'unknown'

    cdn_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        for cid, sk in executor.map(fetch_sk, cid_list):
            cdn_map[cid] = sk

    try:
        with open(_CDN_CACHE_FILE, 'w') as f:
            json.dump(cdn_map, f)
    except Exception:
        pass

    log(f'[CDN] Built fresh cdn_map ({len(cdn_map)} channels)')
    return cdn_map


def list_gen():
    chData = channels()
    if not chData:
        xbmcgui.Dialog().notification('DaddyLive v3', 'Impossible de charger les chaînes. Vérifiez votre connexion.', ICON, 5000)
        log('[list_gen] channels() returned empty list')
    fav_ids = {f['id'] for f in get_favorites()}
    dead_cids = _get_dead_cids()
    ev_map = _build_current_events_map()
    for href, name in chData:
        cid_m = re.search(r'id=(\d+)', href)
        cid = cid_m.group(1) if cid_m else ''
        fav_label = '★ Retirer des favoris' if cid in fav_ids else '☆ Ajouter aux favoris'
        ctx = [(fav_label, 'RunPlugin(%s)' % build_url({'mode': 'toggle_fav', 'cid': cid, 'name': name}))] if cid else []
        label = f'{_ch_label(name, cid, dead_cids)} ({cid})' if cid else name
        ev = ev_map.get(cid) if cid else None
        if ev:
            label += f'  [COLOR gold]{ev}[/COLOR]'
        addDir(label, build_url({'mode': 'play', 'url': abs_url(href)}), False, context_menu=ctx, plot=ev)
    closeDir()

def channels():
    url = abs_url('24-7-channels.php')
    headers = {'Referer': get_active_base(), 'User-Agent': UA}

    try:
        resp = fetch_via_proxy(url, headers=headers)
    except Exception as e:
        log(f"[DADDYLIVE] channels(): request failed: {e}")
        return []

    card_rx = re.compile(
        r'<a\s+class="card"[^>]*?href="(?P<href>[^"]+)"[^>]*?data-title="(?P<data_title>[^"]*)"[^>]*>'
        r'.*?<div\s+class="card__title">\s*(?P<title>.*?)\s*</div>'
        r'.*?ID:\s*(?P<id>\d+)\s*</div>'
        r'.*?</a>',
        re.IGNORECASE | re.DOTALL
    )

    items = []
    for m in card_rx.finditer(resp):
        href_rel = m.group('href').strip()
        title_dom = html.unescape(m.group('title').strip())
        title_attr = html.unescape(m.group('data_title').strip())
        name = title_dom or title_attr

        is_adult = (
            '18+' in name.upper() or
            'XXX' in name.upper() or
            name.strip().startswith('18+')
        )

        if is_adult:
            continue

        name = re.sub(r'^\s*\d+(?=[A-Za-z])', '', name).strip()
        items.append([href_rel, name])

    return items


def _channel_group(name):
    """Assign a group/category to a channel based on its name."""
    n = name.upper()
    if any(k in n for k in ['SPORT', 'ESPN', 'BEIN', 'DAZN', 'RACING', 'GOLF', 'BOXING',
                              'FIGHT', 'WWE', 'NBA ', 'NFL ', 'MLB ', 'NHL ', 'MOTOGP',
                              'EUROSPORT', 'SKY SPORTS', 'BT SPORT', 'PREMIER', 'CHAMPIONS',
                              'FORMULA', 'ARENA SPORT', 'MATCH TV', 'SETANTA', 'SPORTV']):
        return 'Sports'
    if any(k in n for k in ['NEWS', 'CNN', 'SKY NEWS', 'FOX NEWS', 'AL JAZEERA', 'ALJAZEERA',
                              'FRANCE 24', 'EURONEWS', 'BFMTV', 'BFM TV', 'LCI', 'CNBC',
                              'BLOOMBERG', 'TRT ', 'NHK', 'DW ']):
        return 'News'
    if any(k in n for k in [' UK', 'BBC ', 'ITV ', 'CHANNEL 4', 'CHANNEL 5', 'SKY ONE',
                              'SKY CINEMA', 'SKY ATLANTIC', 'SKY MAX', 'DAVE ', 'E4 ',
                              'MORE4', 'COMEDY CENTRAL UK']):
        return 'United Kingdom'
    if any(k in n for k in ['FRANCE', 'TF1', 'M6 ', 'ARTE', 'CANAL+', 'CNEWS', 'C NEWS',
                              'TMC ', 'TFX', 'W9 ', 'C8 ', 'CSTAR', 'GULLI', 'RMC ', 'NRJ ',
                              'BFM', 'RTL ']):
        return 'France'
    if any(k in n for k in [' US ', 'NBC ', 'CBS ', 'ABC ', 'AMC ', 'HBO ', 'SHOWTIME',
                              'STARZ', ' FX ', 'TBS ', 'BRAVO', 'HISTORY', 'DISCOVERY',
                              'NAT GEO', 'ANIMAL PLANET', 'LIFETIME', 'A&E ']):
        return 'USA'
    if any(k in n for k in ['ARABIC', 'ARAB', 'MBC ', 'OSN ', 'ROTANA', 'AL ARABIYA',
                              'AL MAYADEEN', 'BAHRAIN', 'KUWAIT', 'SAUDI', 'QATAR', ' UAE',
                              'KSA ', 'NILE ']):
        return 'Arabic'
    if any(k in n for k in ['INDIA', 'STAR PLUS', 'ZEE ', 'SONY LIV', 'COLORS', 'HIND']):
        return 'India'
    return 'International'


def generate_m3u():
    """Parse channel list and write M3U to special://userdata/daddylive.m3u.
    Returns the file path on success, None on error."""
    url = abs_url('24-7-channels.php')
    try:
        resp = fetch_via_proxy(url, headers={'Referer': get_active_base(), 'User-Agent': UA})
    except Exception as e:
        log(f'[generate_m3u] fetch error: {e}')
        return None

    # Extended regex capturing logo in addition to existing fields
    card_rx = re.compile(
        r'<a\s+class="card"[^>]*?href="(?P<href>[^"]+)"[^>]*?data-title="(?P<data_title>[^"]*)"[^>]*>'
        r'(?:.*?<img[^>]+src="(?P<logo>[^"]*)"[^>]*>)?'
        r'.*?<div\s+class="card__title">\s*(?P<title>.*?)\s*</div>'
        r'.*?ID:\s*(?P<id>\d+)',
        re.IGNORECASE | re.DOTALL
    )

    lines = ['#EXTM3U']
    count = 0
    base = get_active_base().rstrip('/')

    for m in card_rx.finditer(resp):
        href_rel = m.group('href').strip()
        name_raw = html.unescape(m.group('title').strip()) or html.unescape(m.group('data_title').strip())
        logo = m.group('logo') or ''
        cid_m = re.search(r'id=(\d+)', href_rel)
        if not cid_m:
            continue
        cid = cid_m.group(1)
        # Skip adult
        nu = name_raw.upper()
        if '18+' in nu or 'XXX' in nu:
            continue
        name = re.sub(r'^\s*\d+(?=[A-Za-z])', '', name_raw).strip()
        group = _channel_group(name)
        play_url = ('plugin://plugin.video.daddylive/?' +
                    urlencode({'mode': 'play', 'url': f'{base}/watch.php?id={cid}'}))
        lines.append(f'#EXTINF:-1 tvg-id="{cid}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
        lines.append(play_url)
        count += 1

    if count == 0:
        log('[generate_m3u] No channels found')
        return None

    out_path = xbmcvfs.translatePath('special://userdata/daddylive.m3u')
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        log(f'[generate_m3u] Written {count} channels to {out_path}')
        return out_path
    except Exception as e:
        log(f'[generate_m3u] Write error: {e}')
        return None


def pvr_setup():
    """Generate M3U and guide user to configure PVR IPTV Simple Client."""
    xbmcgui.Dialog().notification('DaddyLive', 'Génération du fichier M3U…', ICON, 2000)
    out_path = generate_m3u()
    if not out_path:
        xbmcgui.Dialog().ok('DaddyLive — Export M3U',
                             'Erreur lors de la génération.\nVérifiez votre connexion.')
        return

    pvr_installed = False
    try:
        xbmcaddon.Addon('pvr.iptvsimple')
        pvr_installed = True
    except Exception:
        pass

    pvr_status = ('PVR IPTV Simple Client détecté !' if pvr_installed
                  else "PVR IPTV Simple Client non installé.\nInstallez-le depuis Extensions → Dépôt Kodi.")
    msg = (f'[B]{pvr_status}[/B]\n\n'
           f'Fichier M3U généré :\n[I]{out_path}[/I]\n\n'
           f'Configuration :\n'
           f'1. Paramètres → PVR IPTV Simple Client\n'
           f'2. M3U Play List URL → Fichier local\n'
           f'3. Chemin → {out_path}\n'
           f'4. OK → Kodi redémarre le PVR')
    if pvr_installed:
        if xbmcgui.Dialog().yesno('DaddyLive — Export M3U', msg,
                                   nolabel='Fermer', yeslabel='Ouvrir paramètres PVR'):
            xbmc.executebuiltin('Addon.OpenSettings(pvr.iptvsimple)')
    else:
        xbmcgui.Dialog().ok('DaddyLive — Export M3U', msg)


def show_adult():
    """Return True if adult content is enabled in settings"""
    return addon.getSettingBool('show_adult')

def _probe_hls_url(url):
    """Quick check: returns True if CDN responds with a live HLS playlist (any segments).
    Returns None (inconclusive) for auth errors (403/407) — CDN reachable but requires auth.
    Returns False for definitive failures (404, 5xx, HTML content, no segments)."""
    try:
        r = requests.get(url, headers={'User-Agent': UA, 'Referer': PLAYER_REFERER}, timeout=3)
        if r.status_code in (403, 407):
            return None  # CDN requires auth — inconclusive, don't mark as KO
        if r.status_code != 200:
            return False
        content = r.text
        if content[:5] in ('<!DOC', '<html', '<!doc'):
            return False
        # Finite playlist = channel offline
        if '#EXT-X-ENDLIST' in content:
            return False
        if '#EXTM3U' not in content:
            return len(content) > 0 and '<' not in content[:20]
        _segs = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        return len(_segs) > 0  # CDN is reachable and serving a playlist
    except Exception:
        return False


def get_player6_stream(channel_id):
    """Fetch fallback stream URL from Player 6 (tv-bu1.blogspot.com).
    Returns a direct HLS URL or None if unavailable."""
    try:
        blogspot_url = f'https://tv-bu1.blogspot.com/p/e1.html?id={channel_id}a'
        log(f'[Player6] Fetching: {blogspot_url}')
        r = requests.get(blogspot_url, headers={'User-Agent': UA}, timeout=4)
        if r.status_code != 200:
            log(f'[Player6] HTTP {r.status_code}')
            return None
        html_page = r.text

        # Find the iframe src injected for this channel id
        m = re.search(
            r'id\s*===\s*"' + re.escape(str(channel_id)) + r'a"[^<]{0,600}'
            r'<iframe[^>]+src="([^"]+)"',
            html_page, re.DOTALL
        )
        if not m:
            log(f'[Player6] No entry for channel {channel_id}a')
            return None

        iframe_src = m.group(1)
        log(f'[Player6] iframe src: {iframe_src}')

        # Case 1: r-strm.blogspot.com with ?s=<direct_url> parameter
        ms = re.search(r'[?&]s=(https?://[^&"\'>\s]+)', iframe_src)
        if ms:
            stream_url = ms.group(1)
            log(f'[Player6] Direct URL from ?s= param: {stream_url}')
            return stream_url

        # Case 2: hoofoot.ru — JW Player page with file: "..." URL
        if 'hoofoot.ru' in iframe_src:
            r2 = requests.get(iframe_src, headers={'User-Agent': UA}, timeout=8)
            mf = re.search(r'["\']?file["\']?\s*:\s*["\']([^"\']+)["\']', r2.text)
            if mf:
                stream_url = mf.group(1)
                log(f'[Player6] hoofoot.ru stream: {stream_url}')
                return stream_url

        # Case 3: r-strm.blogspot.com sub-page — fetch and extract JW Player or iframe
        if 'r-strm.blogspot.com' in iframe_src:
            r2 = requests.get(iframe_src, headers={'User-Agent': UA}, timeout=8)
            # JW Player file
            mf = re.search(r'["\']?file["\']?\s*:\s*["\']([^"\']+)["\']', r2.text)
            if mf:
                return mf.group(1)
            # Inner iframe with ?s= param
            mi = re.search(r'<iframe[^>]+src="([^"]*[?&]s=https?://[^"]+)"', r2.text)
            if mi:
                ms2 = re.search(r'[?&]s=(https?://[^&"\'>\s]+)', mi.group(1))
                if ms2:
                    return ms2.group(1)

        log(f'[Player6] Could not extract direct URL from {iframe_src}')
        return None

    except Exception as e:
        log(f'[Player6] Error for channel {channel_id}: {e}')
        return None


def get_stream_page_url(channel_id):
    """For channels not in the chevy CDN, extract m3u8 via stellarthread player chain.
    Chain: stream-{id}.php → wikisport.club/court/{fid} → stellarthread.com/wiki.php?live={fid}
    The md5 token in the URL is IP-based, so it will work from Kodi (same IP as this request).
    """
    try:
        watch_url = abs_url(f'watch.php?id={channel_id}')
        stream_url_page = abs_url(f'stream/stream-{channel_id}.php')

        # Step 1: fetch the stream page with the correct Referer
        r = requests.get(stream_url_page, headers={
            'User-Agent': UA,
            'Referer': watch_url,
        }, timeout=12)
        if r.status_code != 200:
            log(f'[StreamPage] stream page HTTP {r.status_code} for id={channel_id}')
            return None

        # Step 2: find wikisport.club iframe src
        mw = re.search(r'src="(https://wikisport\.club/[^"]+)"', r.text)
        if not mw:
            log(f'[StreamPage] no wikisport iframe for id={channel_id}')
            return None
        wikisport_url = mw.group(1)

        # Step 3: fetch wikisport page to get fid
        r2 = requests.get(wikisport_url, headers={
            'User-Agent': UA,
            'Referer': stream_url_page,
        }, timeout=8)
        mf = re.search(r'fid\s*=\s*"([^"]+)"', r2.text)
        if not mf:
            log(f'[StreamPage] no fid in wikisport page')
            return None
        fid = mf.group(1)

        # Step 4: fetch stellarthread wiki.php to get the URL
        stellar_url = f'https://stellarthread.com/wiki.php?player=desktop&live={fid}'
        r3 = requests.get(stellar_url, headers={
            'User-Agent': UA,
            'Referer': wikisport_url,
        }, timeout=8)
        if r3.status_code != 200:
            log(f'[StreamPage] stellarthread HTTP {r3.status_code}')
            return None

        # Step 5: extract URL from char array in ettgHtplrU() function
        m3 = re.search(r'return\(\[(.+?)\]\.join\(', r3.text)
        if not m3:
            log(f'[StreamPage] no char array found in stellarthread page')
            return None
        chars = re.findall(r'"(.*?)"', m3.group(1))
        m3u8_url = ''.join(chars).replace('\\/', '/')

        if 'm3u8' in m3u8_url and m3u8_url.startswith('https://'):
            log(f'[StreamPage] Got URL for channel {channel_id}: {m3u8_url[:70]}')
            return m3u8_url
        return None
    except Exception as e:
        log(f'[StreamPage] Error for channel {channel_id}: {e}')
        return None


def resolve_stream_url(channel_id):
    channel_key = f'premium{channel_id}'
    server_key = 'zeko'
    for attempt in range(2):
        try:
            resp = requests.get(
                f'{CHEVY_LOOKUP}/server_lookup?channel_id={channel_key}',
                headers={'User-Agent': UA, 'Referer': PLAYER_REFERER},
                timeout=4
            )
            server_key = resp.json().get('server_key', 'zeko')
            break
        except Exception as e:
            log(f'[resolve_stream_url] server_lookup failed (attempt {attempt+1}): {e}')
            if attempt == 0:
                time.sleep(0.5)
    if server_key == 'top1/cdn':
        return f'{CHEVY_PROXY}/proxy/top1/cdn/{channel_key}/mono.css'
    return f'{CHEVY_PROXY}/proxy/{server_key}/{channel_key}/mono.css'

def PlayStream(link):
    try:
        log(f'[PlayStream] Starting: {link}')

        parsed = urlparse(link)
        qs = dict(parse_qsl(parsed.query))
        channel_id = qs.get('id', '').split('|')[0].strip()

        if not channel_id:
            log('[PlayStream] No channel ID found')
            xbmcgui.Dialog().notification('DaddyLive', 'Chaîne introuvable (ID manquant)', ICON, 4000)
            xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
            return

        log(f'[PlayStream] Channel ID: {channel_id}')
        channel_key = f'premium{channel_id}'

        # Reuse cached credentials if fresh (< 5 min), otherwise resolve CDN URL and
        # fetch auth in parallel to minimise spinner time before setResolvedUrl.
        cached = _get_channel_state(channel_key)
        auth_is_fresh = (cached and cached.get('auth_token')
                         and (time.time() - cached.get('fetched_at', 0)) < 300)
        use_player6 = False
        if auth_is_fresh:
            real_m3u8_url = resolve_stream_url(channel_id)
            auth_token = cached['auth_token']
            channel_salt = cached['channel_salt']
            log(f'[PlayStream] Reusing cached credentials for {channel_key}')
        else:
            # Resolve CDN URL and fetch auth simultaneously
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as _ex:
                _fut_resolve = _ex.submit(resolve_stream_url, channel_id)
                _fut_auth = _ex.submit(_fetch_auth_credentials, channel_id)
                real_m3u8_url = _fut_resolve.result()
                auth_token, channel_salt = _fut_auth.result()
        log(f'[PlayStream] Primary M3U8 URL: {real_m3u8_url}')

        # Probe primary CDN — if it's down (returns HTML), try Player 6 fallback
        if not _probe_hls_url(real_m3u8_url):
            log('[PlayStream] Primary CDN probe failed, trying Player 6 fallback')
            player6_url = get_player6_stream(channel_id)
            if player6_url:
                log(f'[PlayStream] Player 6 fallback URL: {player6_url}')
                real_m3u8_url = player6_url
                use_player6 = True
            else:
                log('[PlayStream] Player 6 unavailable, using primary CDN anyway')
                _mark_channel_failed(channel_key)
                xbmcgui.Dialog().notification('DaddyLive', f'CDN indisponible (ch.{channel_id}) — tentative en cours…', ICON, 4000)

        if use_player6:
            # stellarthread/sanwalyaarpya streams require Origin header — proxy via /raw/
            if 'sanwalyaarpya.com' in real_m3u8_url:
                _ensure_m3u8_proxy()
                encoded_origin = quote_plus('https://stellarthread.com')
                encoded_url = quote_plus(real_m3u8_url)
                m3u8_url = f'http://127.0.0.1:{_actual_proxy_port or M3U8_PROXY_PORT}/raw/{encoded_origin}/{encoded_url}'
                log(f'[PlayStream] Using raw proxy for stellarthread stream')
            else:
                m3u8_url = real_m3u8_url
            log('[PlayStream] Using Player 6 stream directly')
        else:
            if auth_token and channel_salt:
                log(f'[PlayStream] Got auth credentials for {channel_key}')
                _set_channel_state(channel_key, auth_token, channel_salt, real_m3u8_url)
                _ensure_m3u8_proxy()
                m3u8_url = f'http://127.0.0.1:{_actual_proxy_port or M3U8_PROXY_PORT}/m3u8/{channel_key}'
                log(f'[PlayStream] Using auth proxy: {m3u8_url}')
            else:
                log('[PlayStream] Auth credentials unavailable, falling back to direct URL')
                xbmcgui.Dialog().notification('DaddyLive', f'Authentification impossible (ch.{channel_id})', ICON, 4000)
                m3u8_url = real_m3u8_url

        liz = xbmcgui.ListItem(f'Channel {channel_id}', path=m3u8_url)
        liz.setContentLookup(False)
        liz.setMimeType('application/vnd.apple.mpegurl')
        if addon.getSetting('use_ffmpegdirect') != 'false':
            liz.setProperty('inputstream', 'inputstream.ffmpegdirect')
            liz.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
            liz.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
        liz.setProperty('IsPlayable', 'true')

        xbmcplugin.setResolvedUrl(addon_handle, True, liz)
        log(f'[PlayStream] Stream started ({"Player6" if use_player6 else "primary CDN"})')

    except Exception as e:
        log(f'[PlayStream] Error: {e}')
        xbmcgui.Dialog().notification('DaddyLive', f'Erreur : {str(e)[:80]}', ICON, 6000)
        xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())

def Search_Events():
    keyboard = xbmcgui.Dialog().input("Enter search term", type=xbmcgui.INPUT_ALPHANUM)
    if not keyboard or keyboard.strip() == '':
        closeDir()
        return
    term = keyboard.lower().strip()

    try:
        html_text = fetch_via_proxy(abs_url('index.php'), headers={'User-Agent': UA, 'Referer': get_active_base()})
        events = re.findall(
            r"<div\s+class=\"schedule__event\">.*?"
            r"<div\s+class=\"schedule__eventHeader\"[^>]*?>\s*"
            r"(?:<[^>]+>)*?"
            r"<span\s+class=\"schedule__time\"[^>]*data-time=\"([^\"]+)\"[^>]*>.*?</span>\s*"
            r"<span\s+class=\"schedule__eventTitle\">\s*([^<]+)\s*</span>.*?"
            r"</div>\s*"
            r"<div\s+class=\"schedule__channels\">(.*?)</div>",
            html_text, re.IGNORECASE | re.DOTALL
        )

        rows = {}
        seen = set()
        for time_str, raw_title, channels_block in events:
            title_clean = html.unescape(raw_title.strip())
            if term not in title_clean.lower():
                continue
            if title_clean in seen:
                continue
            seen.add(title_clean)
            event_time_local = get_local_time(time_str.strip())
            rows[title_clean] = channels_block

        for title, chblock in rows.items():
            links = []
            for href, title_attr, link_text in re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*title="([^"]*)".*?>(.*?)</a>',
                chblock, re.IGNORECASE | re.DOTALL
            ):
                name = html.unescape(title_attr or link_text)
                links.append({'channel_name': name, 'channel_id': href})
            addDir(title, build_url({'mode': 'trLinks', 'trData': json.dumps({'channels': links})}), False)

    except Exception as e:
        log(f'Search_Events error: {e}')
    closeDir()

def Search_Channels():
    keyboard = xbmcgui.Dialog().input("Enter channel name", type=xbmcgui.INPUT_ALPHANUM)
    if not keyboard or keyboard.strip() == '':
        closeDir()
        return
    term = keyboard.lower().strip()
    chData = channels()
    for href, title in chData:
        if term in title.lower():
            addDir(title, build_url({'mode': 'play', 'url': abs_url(href)}), False)
    closeDir()

def load_extra_channels(force_reload=False):
    global EXTRA_CHANNELS_DATA
    CACHE_EXPIRY = 24 * 60 * 60

    saved = addon.getSetting('extra_channels_cache')
    if saved and not force_reload:
        try:
            saved_data = json.loads(saved)
            if time.time() - saved_data.get('timestamp', 0) < CACHE_EXPIRY:
                EXTRA_CHANNELS_DATA = saved_data.get('channels', {})
                if EXTRA_CHANNELS_DATA:
                    return EXTRA_CHANNELS_DATA
        except:
            pass

    try:
        resp = requests.get(EXTRA_M3U8_URL, headers={'User-Agent': UA}, timeout=10).text
    except Exception as e:
        xbmcgui.Dialog().ok("Error", f"Failed to fetch extra channels: {e}")
        return {}

    categories = {}
    lines = resp.splitlines()

    for i, line in enumerate(lines):
        if not line.startswith('#EXTINF:'):
            continue

        title_match = re.search(r',(.+)$', line)
        cat_match = re.search(r'group-title="([^"]+)"', line)
        logo_match = re.search(r'tvg-logo="([^"]+)"', line)

        if not title_match:
            continue

        title = title_match.group(1).strip()
        category = cat_match.group(1).strip() if cat_match else 'Uncategorized'
        logo = logo_match.group(1) if logo_match else ICON

        is_adult = (
            '18+' in category.upper() or
            'XXX' in category.upper() or
            '18+' in title.upper() or
            'XXX' in title.upper()
        )

        if is_adult:
            continue

        stream_url = lines[i + 1].strip() if i + 1 < len(lines) else ''
        if not stream_url:
            continue

        categories.setdefault(category, []).append({
            'title': title,
            'url': stream_url,
            'logo': logo
        })

    EXTRA_CHANNELS_DATA = categories

    addon.setSetting(
        'extra_channels_cache',
        json.dumps({'timestamp': int(time.time()), 'channels': EXTRA_CHANNELS_DATA})
    )

    return EXTRA_CHANNELS_DATA

def ExtraChannels_Main():
    global EXTRA_CHANNELS_DATA
    if not EXTRA_CHANNELS_DATA:
        load_extra_channels() 
        if not EXTRA_CHANNELS_DATA:
            xbmcgui.Dialog().ok("Error", "Extra channels could not be loaded.")
            return

    addDir('[B][COLOR gold]Search Extra Channels / VODs[/COLOR][/B]',
           build_url({'mode': 'extra_search'}), True)

    for cat in sorted(EXTRA_CHANNELS_DATA.keys()):
        is_adult_cat = (
            '18+' in cat.upper() or
            'XXX' in cat.upper()
        )

        if is_adult_cat:
            continue
    
        addDir(cat, build_url({'mode': 'extra_list', 'category': cat}), True, logo="https://images-ext-1.discordapp.net/external/fUzDq2SD022-veHyDJTHKdYTBzD9371EnrUscXXrf0c/%3Fsize%3D4096/https/cdn.discordapp.com/icons/1373713080206495756/1fe97e658bc7fb0e8b9b6df62259c148.png?format=webp&quality=lossless")

    
    closeDir()



def ExtraChannels_Search():
    """
    Open a dialog to search for a channel or VOD in the extra list.
    """
    keyboard = xbmcgui.Dialog().input("Search Extra Channels / VODs", type=xbmcgui.INPUT_ALPHANUM)
    if not keyboard or keyboard.strip() == '':
        closeDir()
        return
    search_term = keyboard.strip()
    ExtraChannels_List(None, search_term) 


def ExtraChannels_List(category=None, search=None):
    """
    List ExtraChannels, optionally filtering by category or search term,
    enforcing adult access where needed.
    """
    global EXTRA_CHANNELS_DATA
    if not EXTRA_CHANNELS_DATA:
        load_extra_channels()  
        if not EXTRA_CHANNELS_DATA:
            xbmcgui.Dialog().ok("Error", "Extra channels could not be loaded.")
            return

    items_to_show = []

    for cat, streams in EXTRA_CHANNELS_DATA.items():
        if category and cat != category:
            continue

        is_adult_cat = (
            '18+' in cat.upper() or
            'XXX' in cat.upper()
        )
        if is_adult_cat:
            continue

        for item in streams:
            if category and cat != category:
                continue
            if search and search.lower() not in item['title'].lower():
                continue

            is_adult = (
                '18+' in item['title'].upper() or
                'XXX' in item['title'].upper()
            )
            if is_adult:
                continue

            items_to_show.append({
                'title': item['title'],
                'url': item['url'],
                'logo': item.get('logo', ICON)
            })

    for item in items_to_show:
        addDir(
            item['title'],
            build_url({'mode': 'extra_play', 'url': item['url'], 'logo': item.get('logo', ICON), 'name': item['title']}),
            False,
            logo=item.get('logo', ICON)
        )

    closeDir()


def ExtraChannels_Play(url, name='Extra Channel', logo=ICON):
    """
    Play a channel or VOD from ExtraChannels, enforcing adult access.
    """
    try:

        log(f'[ExtraChannels_Play] Original URL: {url}')

        if 'a1xmedia' in url.lower() or 'a1xs.vip' in url.lower():
            headers = {
                'User-Agent': UA,
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://a1xs.vip/'
            }
            try:
                response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
                url = response.url
                log(f'[ExtraChannels_Play] Resolved A1XMedia URL: {url}')
            except Exception as e:
                log(f'[ExtraChannels_Play] Failed to resolve A1XMedia URL, using original: {e}')

        elif 'daddylive' in url.lower() or 'dlhd' in url.lower():
            parsed_url = urlparse(url)
            qs_url = dict(parse_qsl(parsed_url.query))
            channel_id = qs_url.get('id', '').split('|')[0].strip()
            if not channel_id:
                m = re.search(r'(?:id=|premium)(\d+)', url)
                if m:
                    channel_id = m.group(1)
            if channel_id:
                PlayStream(abs_url('watch.php?id=' + channel_id))
                return
            log(f'[ExtraChannels_Play] Could not extract channel ID from: {url}')

        logo = logo or ICON
        liz = xbmcgui.ListItem(name, path=url)
        liz.setArt({'thumb': logo, 'icon': logo, 'fanart': FANART})
        liz.setInfo('video', {'title': name, 'plot': name})

        if '.m3u8' in url.lower():
            liz.setProperty('inputstream', 'inputstream.adaptive')
            liz.setProperty('inputstream.adaptive.manifest_type', 'hls')
            liz.setMimeType('application/vnd.apple.mpegurl')
            log('[ExtraChannels_Play] HLS stream detected')
        elif url.lower().endswith('.mp4'):
            liz.setMimeType('video/mp4')
            log('[ExtraChannels_Play] MP4 stream detected')
        else:
            liz.setMimeType('video')
            log('[ExtraChannels_Play] Generic video stream')

        liz.setProperty('IsPlayable', 'true')
        xbmcplugin.setResolvedUrl(addon_handle, True, liz)
        log(f'[ExtraChannels_Play] Stream started for: {name}')

    except Exception as e:
        log(f'[ExtraChannels_Play] Error: {e}')
        import traceback
        log(f'Traceback: {traceback.format_exc()}')
        xbmcgui.Dialog().notification("Daddylive", "Failed to play channel", ICON, 3000)


if not params.get('mode'): 
    load_extra_channels()
    Main_Menu()
else:
    mode = params.get('mode')

    if mode == 'menu':
        servType = params.get('serv_type')
        if servType == 'sched':
            Menu_Trans()
        elif servType == 'live_tv':
            list_gen()
        elif servType == 'lang_menu':
            list_by_language()
        elif servType == 'favorites':
            list_favorites()
        elif servType == 'extra_channels':
            ExtraChannels_Main()
        elif servType == 'search':
            Search_Events()
        elif servType == 'search_channels':
            Search_Channels()
        elif servType == 'diagnostics':
            run_diagnostics()
            xbmcplugin.endOfDirectory(addon_handle, False)
        elif servType == 'export_m3u':
            pvr_setup()
            xbmcplugin.endOfDirectory(addon_handle, False)
        elif servType == 'chat':
            import webbrowser
            webbrowser.open('https://daddylivehd.chatango.com/')
            xbmcplugin.endOfDirectory(addon_handle, False)

    elif mode == 'showChannels':
        transType = params.get('trType')
        channels_list = getTransData(transType)
        ShowChannels(transType, channels_list)

    elif mode == 'trList':
        transType = params.get('trType')
        channels_list = json.loads(params.get('channels'))
        TransList(transType, channels_list)

    elif mode == 'trLinks':
        trData = params.get('trData')
        getSource(trData)

    elif mode == 'play':
        link = params.get('url')
        PlayStream(link)

    elif mode == 'diagnostics':
        run_diagnostics()

    elif mode == 'toggle_fav':
        toggle_favorite(params.get('cid', ''), params.get('name', ''))

    elif mode == 'probe_favorites':
        favs = get_favorites()
        if favs:
            xbmcgui.Dialog().notification('DaddyLive', f'Vérification de {len(favs)} chaînes…', ICON, 2000)
            _probe_favorites_background(favs, force=True)
        xbmcplugin.endOfDirectory(addon_handle, False)

    elif mode == 'lang_channels':
        list_lang_channels(params.get('lang', 'eng'))

    elif mode == 'extra_channels':
        ExtraChannels_Main()

    elif mode == 'extra_search':
        ExtraChannels_Search()

    elif mode == 'extra_list':  
        cat = params.get('category')
        search_term = params.get('search')
        ExtraChannels_List(cat, search_term)

    elif mode == 'extra_play':
        url = params.get('url')
        logo = params.get('logo', ICON)
        name = params.get('name', 'Extra Channel')
        ExtraChannels_Play(url, name=name, logo=logo)

