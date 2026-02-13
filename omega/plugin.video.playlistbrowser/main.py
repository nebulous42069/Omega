# -*- coding: utf-8 -*-
import sys, os, json, time, gzip, re, io, urllib.parse
from urllib.request import urlopen, Request
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
VERSION = "2.6.9"
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def _normalize_hex(color: str) -> str:
    # Normalize to Kodi [COLOR] tag value:
    # Accepts '#RRGGBB', 'RRGGBB', '#AARRGGBB', 'AARRGGBB', or a named color like 'red'.
    # Returns AARRGGBB (alpha first) for hex; named colors pass through.
    try:
        if not color:
            return ''
        s = str(color).strip()
        if s.startswith('#'):
            s = s[1:]
        # named color allowed
        if re.fullmatch(r'[A-Za-z]+', s or ''):
            return s
        # 6-digit hex -> prepend FF
        if re.fullmatch(r'[0-9A-Fa-f]{6}', s or ''):
            return ('FF' + s).upper()
        # 8-digit hex already AARRGGBB
        if re.fullmatch(r'[0-9A-Fa-f]{8}', s or ''):
            return s.upper()
        return ''
    except Exception:
        return ''

    c = color.strip().lstrip('#')
    if len(c) == 8:  # AARRGGBB -> RRGGBB
        return c[2:].upper()
    if len(c) == 6:
        return c.upper()
    return ''
    c = color.strip().lstrip('#')
    if len(c) == 6:
        return 'FF' + c.upper()
    if len(c) == 8:
        return c.upper()
    return ''

def _apply_color(text: str, setting_id: str) -> str:
    try:
        col = _normalize_hex(get_string_setting(setting_id))
    except Exception:
        col = ''
    if not col or not text:
        return text
    return f"[COLOR {col}]{text}[/COLOR]"


def _profile_dir():
    try:
        return xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    except Exception:
        return xbmc.translatePath(ADDON.getAddonInfo('profile'))
PROFILE = _profile_dir()
if not os.path.isdir(PROFILE):
    os.makedirs(PROFILE, exist_ok=True)

ADDON_PATH = ADDON.getAddonInfo('path')
FALLBACK_ICON = os.path.join(ADDON_PATH, 'resources', 'media', 'icon.png')
FALLBACK_FANART = os.path.join(ADDON_PATH, 'resources', 'media', 'fanart.png')

# ---------- Settings helpers ----------
def get_string_setting(key, default=""):
    try:
        val = ADDON.getSetting(key)
        return val if val is not None else default
    except Exception:
        return default
def get_int_setting(key, default=0):
    try:
        return ADDON.getSettingInt(key)
    except Exception:
        try:
            s = get_string_setting(key, "")
            return int(s) if s.strip() != "" else default
        except Exception:
            return default
def get_bool_setting(key, default=True):
    try:
        return ADDON.getSettingBool(key)
    except Exception:
        s = get_string_setting(key, "").strip().lower()
        if s == "":
            return default
        return s in ("true","1","yes","on")

# ---------- Utils ----------
def log(msg):
    xbmc.log(f"[{ADDON_ID} v{VERSION}] {msg}", xbmc.LOGINFO)
def notify(heading, message, level=xbmcgui.NOTIFICATION_INFO, time_ms=2500):
    try:
        xbmcgui.Dialog().notification(heading, message, level, time_ms)
    except Exception:
        pass
def build_url(query: dict) -> str:
    return BASE_URL + '?' + urllib.parse.urlencode(query)
def _is_url(s: str) -> bool:
    return s and s.startswith(('http://','https://'))
def _ensure_dir(path):
    d = os.path.dirname(path)
    try: xbmcvfs.mkdirs(d)
    except Exception:
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
def _write_bytes(path, data_bytes):
    _ensure_dir(path)
    with open(path, 'wb') as fh: fh.write(data_bytes)
    return True
def _write_text(path, text):
    _ensure_dir(path)
    with open(path, 'w', encoding='utf-8', errors='ignore') as fh: fh.write(text or '')
    return True
def _write_json(path, obj): return _write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def read_text(path_or_url: str) -> str:
    if not path_or_url:
        return ''
    try:
        if _is_url(path_or_url):
            # 1) Try Kodi VFS first (handles tricky redirects better than urllib)
            try:
                f = xbmcvfs.File(path_or_url); data = f.read(); f.close()
                if isinstance(data, bytes):
                    try: return data.decode('utf-8', errors='ignore')
                    except Exception: return data.decode('latin-1', errors='ignore')
                else:
                    s = str(data)
                    if (s or '').strip():
                        return s
            except Exception:
                pass

            # 2) Manual HTTP follow (up to 8 hops); never raise on loops—fall through
            import urllib.request as _uw
            import urllib.parse as _up
            max_hops = 8
            visited = set()
            url = path_or_url
            last_url = url
            def _referer(u: str) -> str:
                try:
                    pu = _up.urlparse(u)
                    return f"{pu.scheme}://{pu.netloc}/" if pu.scheme and pu.netloc else ""
                except Exception:
                    return ""
            for _ in range(max_hops):
                if url in visited:  # loop -> stop manual attempts
                    break
                visited.add(url)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Kodi Addon)',
                    'Accept': '*/*',
                    'Referer': _referer(url) or _referer(path_or_url),
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Connection': 'close',
                }
                req = _uw.Request(url, headers=headers, method='GET')
                try:
                    with _uw.urlopen(req, timeout=25) as resp:
                        status = getattr(resp, 'status', None) or getattr(resp, 'code', 200)
                        if 300 <= int(status) < 400:
                            loc = resp.getheader('Location') or resp.headers.get('Location')
                            if not loc:
                                break
                            url = _up.urljoin(url, loc)
                            last_url = url
                            continue
                        data = resp.read()
                        try:
                            return data.decode('utf-8', errors='ignore')
                        except Exception:
                            try:
                                return data.decode('latin-1', errors='ignore')
                            except Exception:
                                pass  # fall through to VFS fallback
                except _uw.HTTPError as he:
                    if he.code in (301, 302, 303, 307, 308):
                        loc = he.headers.get('Location')
                        if loc:
                            url = _up.urljoin(url, loc)
                            last_url = url
                            continue
                    break  # other HTTPError -> VFS fallback
                except Exception:
                    break  # network hiccup -> VFS fallback

            # 3) VFS fallbacks: last URL, original URL, and cache-busted URL
            def _vfs_try(u: str) -> str:
                try:
                    f = xbmcvfs.File(u); data = f.read(); f.close()
                    if isinstance(data, bytes):
                        try: return data.decode('utf-8', errors='ignore')
                        except Exception: return data.decode('latin-1', errors='ignore')
                    else:
                        return str(data)
                except Exception:
                    return ''
            try:
                import time as _t
                candidates = (last_url, path_or_url, f"{path_or_url}{'&' if '?' in path_or_url else '?'}_ts={int(_t.time())}")
            except Exception:
                candidates = (last_url, path_or_url)
            for candidate in candidates:
                txt = _vfs_try(candidate)
                if (txt or '').strip():
                    return txt

            return ''  # nothing worked
        else:
            # Local file path
            try:
                f = xbmcvfs.File(path_or_url); data = f.read(); f.close()
                return data.decode('utf-8', errors='ignore') if isinstance(data, bytes) else data
            except Exception:
                with open(path_or_url, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
    except Exception as e:
        log(f"Failed to read: {e}")
        return ''

def parse_m3u(text: str):
    chans = []
    if not text: return chans
    lines = [ln.rstrip('\n') for ln in text.splitlines()]
    if not lines: return chans
    if not lines[0].lstrip().startswith('#EXTM3U'): log('Not an extended M3U or header missing.')
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if not ln: i += 1; continue
        if ln.startswith('#EXTINF:'):
            try: header, name_part = ln.split(',', 1)
            except ValueError: header, name_part = ln, ''
            attrs_part = header.split(':',1)[1] if ':' in header else header
            attrs_part = attrs_part.strip()
            if attrs_part and (attrs_part[0].isdigit() or attrs_part[0]=='-'):
                sp = attrs_part.split(' ', 1); attrs_part = sp[1] if len(sp) > 1 else ''
            attrs = {}
            for k, v in re.findall(r'([A-Za-z0-9_-]+)="([^"]*)"', attrs_part): attrs[k] = v
            for k, v in re.findall(r'([A-Za-z0-9_-]+)=([^"\\s,]+)', attrs_part):
                if k not in attrs: attrs[k] = v
            name = (name_part or '').strip() or attrs.get('tvg-name') or 'Channel'
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('#'): j += 1
            if j < len(lines):
                url = lines[j].strip()
                chans.append({'name': name, 'url': url, 'logo': attrs.get('tvg-logo',''),
                              'group': attrs.get('group-title',''), 'tvg_id': attrs.get('tvg-id',''),
                              'tvg_name': attrs.get('tvg-name','')})
                i = j + 1; continue
        i += 1
    log(f"M3U parsed: {len(chans)} channels"); return chans

def parse_json(text: str):
    try:
        data = json.loads(text); chans = []
        for item in data:
            if isinstance(item, dict) and 'url' in item:
                chans.append({'name': item.get('name') or 'Channel','url': item['url'],
                              'logo': item.get('logo',''),'group': item.get('group',''),
                              'tvg_id': item.get('tvg_id',''),'tvg_name': item.get('tvg_name','')})
        return chans
    except Exception as e:
        log(f"JSON parse error: {e}"); return []

# ---------- XMLTV helpers ----------
def _tag_name(el):
    t = el.tag; return t.split('}',1)[-1] if '}' in t else t
def _iter_all(node, tag_name):
    for el in node.iter():
        if _tag_name(el) == tag_name: yield el
def _find_child(node, tag_name):
    for el in list(node):
        if _tag_name(el) == tag_name: return el
    return None
def _find_children(node, tag_name):
    return [el for el in list(node) if _tag_name(el) == tag_name]

def _normalize_xmltv_ts(s: str) -> str:
    if not isinstance(s, str):
        try: s = s.decode('utf-8', 'ignore')
        except Exception: s = str(s)
    for ch in ('\ufeff','\u200e','\u200f','\u2060','\u200c','\u200d'): s = s.replace(ch, '')
    s = s.replace('\xa0',' ')  # NBSP -> space
    return s.strip()

def _xmltv_parse_time_strict_or_none(s: str):
    s = _normalize_xmltv_ts(s)
    for fmt in ("%Y%m%d%H%M%S %z", "%Y%m%d%H%M%S%z"):
        try: return datetime.strptime(s, fmt)
        except Exception: pass
    m = re.match(r"^(\d{14})\s*([+-])\s*(\d{2}):(\d{2})$", s)
    if m:
        base, sign, hh, mm = m.groups()
        dt = datetime.strptime(base, "%Y%m%d%H%M%S")
        offset = (1 if sign == "+" else -1) * timedelta(hours=int(hh), minutes=int(mm))
        return dt.replace(tzinfo=timezone(offset))
    m = re.match(r"^(\d{14})$", s)
    if m: return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return None

def _xmltv_parse_time_ultra_lenient(s: str):
    s = _normalize_xmltv_ts(s)
    digits = re.findall(r"\d", s)
    if len(digits) < 14: return None
    base = "".join(digits[:14])
    try: dt = datetime.strptime(base, "%Y%m%d%H%M%S")
    except Exception: return None
    mo = re.search(r"([+-])\s*(\d{2})[:\s]?(\d{2})", s)
    if mo:
        sign, hh, mm = mo.groups()
        offset = (1 if sign == "+" else -1) * timedelta(hours=int(hh), minutes=int(mm))
        return dt.replace(tzinfo=timezone(offset))
    return dt.replace(tzinfo=timezone.utc)


def _xmltv_guess_times(s_start: str, s_stop: str):
    def _grab14(s):
        ds = re.findall(r"\d", s or "")
        return "".join(ds[:14]) if len(ds) >= 14 else None
    base = _grab14(s_start)
    if not base:
        return None, None
    try:
        y,m,d,hh,mm,ss = int(base[0:4]), int(base[4:6]), int(base[6:8]), int(base[8:10]), int(base[10:12]), int(base[12:14])
        start = datetime(y,m,d,hh,mm,ss, tzinfo=timezone.utc)
    except Exception:
        return None, None
    # Try to read a second 14-digit block from stop; else fallback +30min
    stop_base = _grab14(s_stop)
    if stop_base and len(stop_base) == 14:
        try:
            y2,m2,d2,H2,M2,S2 = int(stop_base[0:4]), int(stop_base[4:6]), int(stop_base[6:8]), int(stop_base[8:10]), int(stop_base[10:12]), int(stop_base[12:14])
            stop = datetime(y2,m2,d2,H2,M2,S2, tzinfo=timezone.utc)
            return start, stop
        except Exception:
            pass
    return start, start + timedelta(minutes=30)


def _norm(s):
    s = (s or '').lower(); return ''.join(c for c in s if c.isalnum())

class Source:
    def __init__(self, idx, name, m3u, js, epg):
        self.idx = idx; self.name = name or f"Playlist {idx}"
        self.m3u = m3u or ''; self.js = js or ''; self.epg = epg or ''
        self.channels = None; self.epg_channels = {}; self.progs = {}
    def _cache_paths(self):
        base = os.path.join(PROFILE, f'epg_{self.idx}.xml'); return base, base + '.gz'
    def load_channels(self):
        if self.channels is not None: return self.channels
        # Prefer cached channels JSON (written by 'Refresh channels now')
        try:
            raw_path, ch_json_path = _playlist_cache_paths(self.idx, self)
            data = read_text(ch_json_path)
            if (data or '').strip():
                try:
                    self.channels = json.loads(data)
                    return self.channels
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback: fetch once and cache for subsequent runs
        if self.js:
            raw = read_text(self.js)
            self.channels = parse_json(raw)
        elif self.m3u:
            raw = read_text(self.m3u)
            self.channels = parse_m3u(raw)
        else:
            self.channels = []
        try:
            _, ch_json_path = _playlist_cache_paths(self.idx, self)
            _write_json(ch_json_path, self.channels)
        except Exception:
            pass
        return self.channels
    
    def load_epg(self):
        if not self.epg: return {}, {}
        cache_xml, cache_gz = self._cache_paths()
        ttl_hours = max(1, get_int_setting('EPG_TTL_HOURS', 24))
        need_refresh = not os.path.isfile(cache_xml)
        if not need_refresh:
            try:
                age = time.time() - os.path.getmtime(cache_xml)
                if age > (ttl_hours * 3600):
                    need_refresh = True
            except Exception:
                pass
        try:
            xml_bytes = None
            if need_refresh:
                if self.epg.startswith(('http://','https://')):
                    req = Request(self.epg, headers={'User-Agent':'Mozilla/5.0 (Kodi Addon)'})
                    with urlopen(req, timeout=90) as resp: data = resp.read()
                else:
                    try:
                        f = xbmcvfs.File(self.epg); data = f.read(); f.close()
                        if not isinstance(data, bytes): data = str(data).encode('utf-8','ignore')
                    except Exception:
                        with open(self.epg, 'rb') as fh: data = fh.read()
                is_gz_ext = self.epg.lower().endswith('.gz')
                is_gz_sig = len(data)>=2 and data[:2]==b'\x1f\x8b'
                looks_xml = data.strip()[:1] == b'<'
                if is_gz_ext or is_gz_sig: _write_bytes(cache_gz, data)
                if is_gz_ext or is_gz_sig:
                    try: xml_bytes = gzip.decompress(data)
                    except Exception:
                        try:
                            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gf: xml_bytes = gf.read()
                        except Exception as de: log(f"EPG gzip decompress failed (src {self.idx}): {de}"); xml_bytes = None
                if xml_bytes is None and looks_xml: xml_bytes = data
                if xml_bytes is not None: _write_bytes(cache_xml, xml_bytes)
            else:
                if os.path.isfile(cache_gz):
                    try:
                        with open(cache_gz, 'rb') as gh: gz_bytes = gh.read()
                        xml_bytes = gzip.decompress(gz_bytes)
                    except Exception as ge: log(f"EPG cache gz decompress failed (src {self.idx}): {ge}"); xml_bytes = None
                if xml_bytes is None and os.path.isfile(cache_xml):
                    with open(cache_xml, 'rb') as fh: xml_bytes = fh.read()
        except Exception as e:
            log(f"EPG fetch failed (src {self.idx}): {e}"); xml_bytes = None
        if not xml_bytes: return {}, {}

        try:
            root = ET.fromstring(xml_bytes)
            epg_channels = {}
            for ch in _iter_all(root, 'channel'):
                cid = ch.get('id') or ''
                name_node = _find_child(ch, 'display-name')
                if name_node is None:
                    names = _find_children(ch, 'display-name'); name_text = names[0].text if names else cid
                else: name_text = name_node.text
                icon_node = _find_child(ch, 'icon')
                logo_src = icon_node.get('src') if icon_node is not None else ''
                epg_channels[cid] = {'name': name_text or cid, 'logo': logo_src}

            progs_by_ch = {}; raw_prog = 0; added_count = 0; strict_ok = 0; strict_fail_samples = []
            for pr in _iter_all(root, 'programme'):
                raw_prog += 1
                cid = pr.get('channel') or ''
                s_raw = pr.get('start',''); e_raw = pr.get('stop','')
                start = _xmltv_parse_time_strict_or_none(s_raw); stop = _xmltv_parse_time_strict_or_none(e_raw)
                if not (start and stop):
                    ls = _xmltv_parse_time_ultra_lenient(s_raw); le = _xmltv_parse_time_ultra_lenient(e_raw)
                    if ls and le:
                        start, stop = ls, le
                    else:
                        gs, ge = _xmltv_guess_times(s_raw, e_raw)
                        if gs and ge:
                            start, stop = gs, ge
                        else:
                            if len(strict_fail_samples) < 5: strict_fail_samples.append(repr(s_raw) + " | " + repr(e_raw))
                            continue
                else: strict_ok += 1
                title_node = _find_child(pr, 'title'); sub_node = _find_child(pr, 'sub-title'); desc_node = _find_child(pr, 'desc')
                title = title_node.text if title_node is not None else 'Program'
                if sub_node is not None and sub_node.text: title = f"{title} - {sub_node.text}"
                desc = desc_node.text if desc_node is not None else ''
                progs_by_ch.setdefault(cid, []).append({'start':start,'stop':stop,'title':title,'desc':desc}); added_count += 1
            for cid in progs_by_ch: progs_by_ch[cid].sort(key=lambda x: x['start'])
            if raw_prog and strict_ok == 0 and strict_fail_samples:
                log("EPG note: strict time parse failed for samples: " + " || ".join(strict_fail_samples))
            log(f"EPG parse stats (primary): programmes seen={raw_prog}, added={added_count}, strict_ok={strict_ok}")

            # If still 0 programmes, retry from gz cache
            counts_tmp = (len(epg_channels), sum(len(v) for v in progs_by_ch.values()))
            if counts_tmp[1] == 0:
                cache_xml, cache_gz = self._cache_paths()
                if os.path.isfile(cache_gz):
                    try:
                        with open(cache_gz, 'rb') as gh: gz_bytes2 = gh.read()
                        xml_bytes2 = gzip.decompress(gz_bytes2)
                        root2 = ET.fromstring(xml_bytes2)
                        epg_channels2 = {}
                        for ch in _iter_all(root2, 'channel'):
                            cid = ch.get('id') or ''
                            name_node = _find_child(ch, 'display-name')
                            if name_node is None:
                                names = _find_children(ch, 'display-name'); name_text = names[0].text if names else cid
                            else: name_text = name_node.text
                            icon_node = _find_child(ch, 'icon')
                            logo_src = icon_node.get('src') if icon_node is not None else ''
                            epg_channels2[cid] = {'name': name_text or cid, 'logo': logo_src}
                        progs_by_ch2 = {}; raw_prog2 = 0; added_count2 = 0; strict_ok2 = 0
                        for pr in _iter_all(root2, 'programme'):
                            raw_prog2 += 1
                            cid = pr.get('channel') or ''
                            s_raw = pr.get('start',''); e_raw = pr.get('stop','')
                            start = _xmltv_parse_time_strict_or_none(s_raw) or _xmltv_parse_time_ultra_lenient(s_raw)
                            stop  = _xmltv_parse_time_strict_or_none(e_raw) or _xmltv_parse_time_ultra_lenient(e_raw)
                            if not (start and stop):
                                gs, ge = _xmltv_guess_times(s_raw, e_raw)
                                if not (gs and ge):
                                    continue
                                start, stop = gs, ge
                            else: strict_ok2 += 1
                            title_node = _find_child(pr, 'title'); sub_node = _find_child(pr, 'sub-title'); desc_node = _find_child(pr, 'desc')
                            title = title_node.text if title_node is not None else 'Program'
                            if sub_node is not None and sub_node.text: title = f"{title} - {sub_node.text}"
                            desc = desc_node.text if desc_node is not None else ''
                            progs_by_ch2.setdefault(cid, []).append({'start':start,'stop':stop,'title':title,'desc':desc}); added_count2 += 1
                        for cid in progs_by_ch2: progs_by_ch2[cid].sort(key=lambda x: x['start'])
                        epg_channels, progs_by_ch = epg_channels2, progs_by_ch2
                        log(f"EPG fallback parse from gz succeeded: {len(epg_channels)} channels, {sum(len(v) for v in progs_by_ch.values())} programmes (src {self.idx}); stats: seen={raw_prog2}, added={added_count2}, strict_ok={strict_ok2}")
                    except Exception as fe:
                        log(f"EPG fallback parse from gz failed (src {self.idx}): {fe}")

            self.epg_channels, self.progs = epg_channels, progs_by_ch
            counts = (len(self.epg_channels), sum(len(v) for v in self.progs.values()))
            log(f"EPG loaded: {counts[0]} channels, {counts[1]} programmes (src {self.idx})")
            if need_refresh:
                try:
                    xbmcgui.Dialog().notification(
                        'Playlist Browser',
                        f'EPG loaded: {counts[0]} ch / {counts[1]} programs',
                        xbmcgui.NOTIFICATION_INFO,
                        2500
                    )
                except Exception:
                    pass
            return self.epg_channels, self.progs
        except Exception as e:
            log(f"EPG parse failed (src {self.idx}): {e}"); return {}, {}

    def match_epg_key(self, channel):
        tvg_id = channel.get('tvg_id')
        if tvg_id and tvg_id in self.epg_channels: return tvg_id
        cname = _norm(channel.get('tvg_name') or channel.get('name'))
        for cid, meta in self.epg_channels.items():
            if _norm(meta.get('name')) == cname: return cid
        for cid, meta in self.epg_channels.items():
            n = _norm(meta.get('name'))
            if cname and (cname in n or n in cname): return cid
        return None

# ---------- Source registry ----------

def load_baked_in_sources(base_idx_start: int = 100):
    """
    Load baked-in sources from addons\plugin.video.playlistbrowser\resources\baked_in.json.
    The JSON should be a list of objects with keys like:
      - name (str)
      - m3u or m3u_url (str)  [optional if 'json' provided]
      - json or json_url (str) [optional if 'm3u' provided]
      - epg or epg_xml or epg_url (str) [optional]
    Only additive: if file is missing or invalid, returns [].
    """
    try:
        # Resolve baked-in path inside the addon folder
        path = os.path.join(ADDON_PATH, 'resources', 'baked_in.json')
        raw = read_text(path)
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []

        def pick(d, *keys):
            for k in keys:
                if k in d and d.get(k):
                    return d.get(k)
            return ""

        out = []
        idx = base_idx_start
        for item in data:
            if not isinstance(item, dict):
                continue
            name = pick(item, 'name', 'Name', 'display_name') or f"Baked {idx}"
            m3u = pick(item, 'm3u', 'm3u_url', 'M3U', 'M3U_URL')
            js  = pick(item, 'json', 'json_url', 'JSON', 'JSON_URL')
            epg = pick(item, 'epg', 'epg_xml', 'epg_url', 'EPG', 'EPG_XML', 'EPG_URL')
            # Require at least one of m3u/json
            if not (m3u or js):
                continue
            s = Source(idx, name, m3u, js, epg)
            try:
                s.src_icon = pick(item, 'icon','Icon','icon_url','IconUrl')
                s.src_fanart = pick(item, 'fanart','Fanart','fanart_url','FanartUrl')
            except Exception:
                pass
            out.append(s)
            idx += 1
        return out
    except Exception as e:
        try:
            log(f"baked_in.json load error: {e}")
        except Exception:
            pass
        return []
# ---------- Source registry ----------
def load_sources():
    sources = []
    for i in (1,2,3):
        name = get_string_setting(f"SRC{i}_NAME", f"Playlist {i}")
        m3u = get_string_setting(f"SRC{i}_M3U_URL", "")
        js  = get_string_setting(f"SRC{i}_JSON_URL", "")
        epg = get_string_setting(f"SRC{i}_EPG_XML_URL", "")
        if any([m3u, js]): sources.append(Source(i, name, m3u, js, epg))
    # Append baked-in sources (if any)
    sources.extend(load_baked_in_sources(base_idx_start=100))

    return sources

# ---------- Artwork helpers ----------
def _extract_logo_from_url(url: str) -> str:
    try:
        if not url or '://' not in url: return ''
        parsed = urllib.parse.urlparse(url); q = urllib.parse.parse_qs(parsed.query)
        for key in ('Icon', 'icon', 'logo', 'Logo', 'art', 'image'):
            if key in q and q[key] and q[key][0]: return q[key][0]
        if 'Icon=' in url:
            part = url.split('Icon=',1)[1]; part = part.split('&',1)[0]
            return urllib.parse.unquote(part)
        return ''
    except Exception: return ''

def set_art(li, logo_url=None):
    use_logos = get_bool_setting('USE_LOGOS', True)
    if use_logos and logo_url:
        li.setArt({'thumb': logo_url, 'icon': logo_url, 'fanart': FALLBACK_FANART, 'poster': logo_url, 'landscape': logo_url, 'banner': logo_url})
    else:
        li.setArt({'thumb': FALLBACK_ICON, 'icon': FALLBACK_ICON, 'fanart': FALLBACK_FANART, 'poster': FALLBACK_ICON, 'landscape': FALLBACK_ICON, 'banner': FALLBACK_ICON})

def channel_logo(ch, src: 'Source'):
    logo = ch.get('logo') or _extract_logo_from_url(ch.get('url','')) or ''
    if (not logo) and get_bool_setting('USE_EPG_LOGO_FALLBACK', True):
        epg_key = src.match_epg_key(ch)
        if epg_key and src.epg_channels.get(epg_key, {}).get('logo'):
            logo = src.epg_channels[epg_key]['logo']
    return logo or ''

def nice_time(dt):
    try:
        s = dt.astimezone().strftime('%I:%M %p')
        if s.startswith('0'):
            s = s[1:]
        return s
    except Exception:
        return ''



def _fmt_ampm_range_start(dt):
    """Return 'm/d/yy h[:mm]am/pm' (lowercase am/pm, drop :00)."""
    try:
        local = dt.astimezone()
        m, d, yy = local.month, local.day, local.year % 100
        hour24 = local.hour
        h = hour24 % 12
        if h == 0: h = 12
        minute = local.minute
        ampm = 'am' if hour24 < 12 else 'pm'
        if minute == 0:
            t = f"{h}{ampm}"
        else:
            t = f"{h}:{minute:02d}{ampm}"
        return f"{m}/{d}/{yy} {t}"
    except Exception:
        return ''

def _fmt_ampm_time(dt):
    """Return 'h:mmam/pm' (always include minutes)."""
    try:
        local = dt.astimezone()
        hour24 = local.hour
        h = hour24 % 12
        if h == 0: h = 12
        ampm = 'am' if hour24 < 12 else 'pm'
        return f"{h}:{local.minute:02d}{ampm}"
    except Exception:
        return ''
# ---------- Extra actions ----------
def _epg_cache_path_for(idx: int):
    try: prof = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    except Exception: prof = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    return os.path.join(prof, f'epg_{idx}.xml')
def _epg_cache_gz_for(idx: int): return _epg_cache_path_for(idx) + '.gz'


def _maybe_run_iptv_merge_for_source(src_idx: int):
    """If this source uses IPTV Merge's output playlist, trigger IPTV Merge 'Run Merge'."""
    try:
        src = next((x for x in load_sources() if x.idx==src_idx), None)
        if not src:
            return
        target_special = 'special://home/userdata/addon_data/plugin.program.iptv.merge/playlist.m3u8'
        playlist_path = (src.m3u or src.js or '').strip()

        # Normalize: compare both the special:// form and the translated local paths
        try:
            target_local = xbmcvfs.translatePath(target_special)
        except Exception:
            try:
                target_local = xbmc.translatePath(target_special)
            except Exception:
                target_local = target_special

        try:
            playlist_local = xbmcvfs.translatePath(playlist_path) if playlist_path.startswith('special://') else playlist_path
        except Exception:
            playlist_local = playlist_path

        match = False
        if playlist_path and playlist_path.lower() == target_special.lower():
            match = True
        elif playlist_local and target_local and playlist_local.replace('\\','/').lower() == target_local.replace('\\','/').lower():
            match = True

        if match:
            # Wait for Busy dialog to close to avoid blocked builtins
            try:
                for _ in range(80):  # ~8s max
                    if not xbmc.getCondVisibility('Window.IsActive(DialogBusy.xml)'):
                        break
                    xbmc.sleep(100)
            except Exception:
                pass

            log(f"IPTV Merge: triggering Run Merge via RunPlugin for src {src_idx}")
            xbmc.executebuiltin('RunPlugin("plugin://plugin.program.iptv.merge/?_=merge")')

            # Brief pause so Merge begins writing, then clear ONLY this source's EPG cache
            try:
                xbmc.sleep(800)
            except Exception:
                pass
            try:
                path_xml = _epg_cache_path_for(src_idx); path_gz = _epg_cache_gz_for(src_idx)
                for fp in (path_xml, path_gz):
                    try:
                        if os.path.exists(fp): os.remove(fp)
                    except Exception as ee:
                        log(f"IPTV Merge: failed clearing {fp}: {ee}")
                log(f"IPTV Merge: cleared EPG cache for src {src_idx} after merge trigger")
            except Exception as ce:
                log(f"IPTV Merge: error clearing EPG cache (src {src_idx}): {ce}")
    except Exception as e:
        log(f"IPTV Merge trigger error (src {src_idx}): {e}")

def refresh_epg(src_idx: int):
    path_xml = _epg_cache_path_for(src_idx); path_gz = _epg_cache_gz_for(src_idx)
    try:
        if os.path.exists(path_xml): os.remove(path_xml)
        if os.path.exists(path_gz): os.remove(path_gz)
        notify('Playlist Browser', 'EPG cache cleared. Reloading…')
    except Exception as e:
        notify('Playlist Browser', f'EPG refresh failed: {e}', xbmcgui.NOTIFICATION_ERROR, 4000); log(f"EPG refresh cleanup failed: {e}")
    show_guide_now(src_idx)

def _playlist_cache_paths(idx: int, src: 'Source'):
    base = os.path.join(PROFILE, f'playlist_{idx}')
    if src.js: return base + '.json', os.path.join(PROFILE, f'channels_{idx}.json')
    else: return base + '.m3u', os.path.join(PROFILE, f'channels_{idx}.json')

def refresh_channels(src_idx: int):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src: xbmcgui.Dialog().ok('Playlist Browser', 'Source not found.'); return
    raw = read_text(src.js or src.m3u); raw_path, ch_json_path = _playlist_cache_paths(src.idx, src)
    _write_text(raw_path, raw or ''); chans = parse_json(raw) if src.js else parse_m3u(raw)
    src.channels = chans; _write_json(ch_json_path, chans); src.load_epg()
    matched = sum(1 for ch in chans if src.match_epg_key(ch))
    try: xbmcgui.Dialog().notification('Playlist Browser', f'Channels: {len(chans)} (matched {matched})', xbmcgui.NOTIFICATION_INFO, 3000)
    except Exception: pass
    log(f"Channels refreshed: {len(chans)} parsed; {matched} matched to EPG (src {src.idx})")
def refresh_all_sources():
    """Refresh ALL sources: clear cached EPG/XML(.gz) and playlist/channels caches for each source,
    then rebuild channels and EPG for each source without changing navigation."""
    try:
        sources = load_sources()
        if not sources:
            notify('Playlist Browser', 'No sources to refresh.')
            return
        notify('Playlist Browser', 'Refreshing all sources…')
        # Clear caches for each source
        for s in sources:
            try:
                # EPG caches
                path_xml = _epg_cache_path_for(s.idx); path_gz = _epg_cache_gz_for(s.idx)
                for fp in (path_xml, path_gz):
                    try:
                        if os.path.exists(fp): os.remove(fp)
                    except Exception as e:
                        log(f"Failed removing {fp}: {e}")
                # Playlist + parsed channels caches
                raw_path, ch_json_path = _playlist_cache_paths(s.idx, s)
                for fp in (raw_path, ch_json_path):
                    try:
                        if os.path.exists(fp): os.remove(fp)
                    except Exception as e:
                        log(f"Failed removing {fp}: {e}")
            except Exception as e:
                log(f"Refresh-all cleanup error (src {s.idx}): {e}")
        # Rebuild for each source
        for s in sources:
            try:
                refresh_channels(s.idx)
            except Exception as e:
                log(f"Refresh-all rebuild error (src {s.idx}): {e}")
        notify('Playlist Browser', 'All sources refreshed.')
    except Exception as e:
        notify('Playlist Browser', f'Refresh all failed: {e}', xbmcgui.NOTIFICATION_ERROR, 4000)
        log(f"Refresh all sources failed: {e}")


def write_match_report(src_idx: int):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src: xbmcgui.Dialog().ok('Playlist Browser', 'Source not found.'); return
    chans = src.load_channels(); src.load_epg()
    lines = ['name\\ttvg-id\\tmatched_epg_id\\tmethod']
    for ch in chans:
        mid = None; method = ''
        tvg_id = (ch.get('tvg_id') or '').strip()
        if tvg_id and tvg_id in src.epg_channels: mid = tvg_id; method = 'tvg-id'
        else:
            cname = _norm(ch.get('tvg_name') or ch.get('name'))
            for cid, meta in src.epg_channels.items():
                if _norm(meta.get('name')) == cname: mid = cid; method = 'name-exact'; break
            if not mid:
                for cid, meta in src.epg_channels.items():
                    n = _norm(meta.get('name'))
                    if cname and (cname in n or n in cname): mid = cid; method = 'name-fuzzy'; break
        lines.append(f"{ch.get('name','')}\\t{tvg_id}\\t{mid or ''}\\t{method}")
    path = os.path.join(PROFILE, f'match_report_{src.idx}.tsv'); _write_text(path, '\\n'.join(lines))
    try: xbmcgui.Dialog().notification('Playlist Browser', f'Match report written (match_report_{src.idx}.tsv)', xbmcgui.NOTIFICATION_INFO, 3000)
    except Exception: pass
    log(f"Match report written: {path}")



# ---------- Favorites (additive-only) ----------
def _fav_file():
    try:
        prof = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    except Exception:
        prof = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    return os.path.join(prof, 'favorites.json')

def _load_favs():
    try:
        data = read_text(_fav_file())
        arr = json.loads(data) if (data or '').strip() else []
        return arr if isinstance(arr, list) else []
    except Exception:
        return []

def _save_favs(arr):
    try:
        _write_json(_fav_file(), arr or [])
    except Exception:
        pass

def _fav_key(name, url, tvg):
    return f"{(name or '').strip()}|{(url or '').strip()}|{(tvg or '').strip()}"

def fav_add(src_idx: int, cname: str, tvg: str, url: str, logo: str = ''):
    if not (cname or url):
        notify('Playlist Browser', 'Cannot add favorite: missing channel info', xbmcgui.NOTIFICATION_ERROR, 3000); return
    favs = _load_favs(); key = _fav_key(cname, url, tvg)
    for it in favs:
        if _fav_key(it.get('name'), it.get('url'), it.get('tvg_id')) == key:
            notify('Playlist Browser', 'Already in Live TV Favorites'); return
    favs.append({'name': cname or 'Channel', 'url': url or '', 'tvg_id': tvg or '', 'logo': logo or '', 'src': int(src_idx or 0)})
    _save_favs(favs); notify('Playlist Browser', 'Added to Live TV Favorites')

def fav_remove(cname: str, tvg: str, url: str):
    favs = _load_favs(); key = _fav_key(cname, url, tvg)
    new = [it for it in favs if _fav_key(it.get('name'), it.get('url'), it.get('tvg_id')) != key]
    _save_favs(new); notify('Playlist Browser', 'Removed from Live TV Favorites')


def list_favorites():
    favs = _load_favs()
    if not favs:
        li = xbmcgui.ListItem(label='(No favorites yet)'); set_art(li)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'noop'}), li, isFolder=False)
        xbmcplugin.endOfDirectory(HANDLE); return

    xbmcplugin.setContent(HANDLE, 'videos')
    sources = load_sources()
    now_utc = datetime.now(timezone.utc)

    for it in favs:
        name = it.get('name','Channel'); url = it.get('url',''); tvg = it.get('tvg_id',''); logo = it.get('logo',''); src_idx = int(it.get('src') or 0)
        src_obj = next((x for x in sources if x.idx == src_idx), None)

        title_plain = name
        title_col = _apply_color(title_plain, 'COLOR_CHANNEL')

        current = None
        if src_obj:
            try:
                src_obj.load_epg()
                ch = {'name': name, 'tvg_id': tvg, 'url': url, 'tvg_name': name}
                epg_key = src_obj.match_epg_key(ch)
                if epg_key and src_obj.progs.get(epg_key):
                    for pr in src_obj.progs[epg_key]:
                        if pr['start'] <= now_utc < pr['stop']:
                            current = pr; break
            except Exception:
                current = None

        if current:
            tstart = nice_time(current['start']); tstop = nice_time(current['stop'])
            epg_title = current.get('title','') or ''
            epg_col = _apply_color(epg_title, 'COLOR_EPG')
            time_col = _apply_color(f"({tstart}-{tstop})", 'COLOR_TIME')
            label_epg = f"{epg_col}  {time_col}"
            label = f"{title_col}  {label_epg}"
            label2 = label_epg
            desc = current.get('desc','') or ''
            plot = f"{epg_title}  ({tstart}-{tstop})\n{desc}"
        else:
            # No current EPG: show only the channel name (no extra '(No current EPG)' text)
            label = f"{title_col}"
            label2 = ''
            plot = ''

        li = xbmcgui.ListItem(label=label)
        li.setLabel2(label2)
        li.setInfo('video', {'title': title_col, 'plot': plot, 'mediatype': 'video'})
        if logo:
            set_art(li, logo)
        elif src_obj:
            set_art(li, channel_logo({'logo': logo, 'url': url}, src_obj))
        else:
            set_art(li)
        li.setProperty('IsPlayable','true')

        li.addContextMenuItems([('Remove from Live TV Favorites', f"RunPlugin({build_url({'action':'fav_remove','cname':name,'tvg':tvg,'url':url})})")], replaceItems=True)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'play','url': url}), li, isFolder=False)

# ---------- UI ----------
    xbmcplugin.endOfDirectory(HANDLE)

def list_root():
    log("Addon entry")
    sources = load_sources()

    # Favorites at top
    li_fav = xbmcgui.ListItem(label='Your Live TV Favorites')
    try:
        fav_icon = os.path.join(ADDON_PATH, 'resources', 'media', 'live_tv_favorites.png')
        li_fav.setArt({'thumb': fav_icon, 'icon': fav_icon, 'poster': fav_icon, 'fanart': FALLBACK_FANART})
    except Exception:
        set_art(li_fav)
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'favorites'}), li_fav, isFolder=True)

    # Optional auto-start behavior (unchanged)
    start_mode = get_int_setting('START_MODE', 0)
    if start_mode != 0 and sources:
        src = sources[0]
        if start_mode == 1:
            return list_channels(src.idx)
        elif start_mode == 2:
            return show_guide_now(src.idx)
        elif start_mode == 3:
            return list_guide_channels(src.idx)

    if not sources:
        li = xbmcgui.ListItem(label='No sources configured. Use Settings to add playlists/EPG.')
        set_art(li)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'settings'}), li, isFolder=False)

        return

    # List sources
    for s in sources:
        li = xbmcgui.ListItem(label=s.name)
        set_art(li)
        try:
            if hasattr(s, 'src_icon') and s.src_icon:
                li.setArt({'icon': s.src_icon, 'thumb': s.src_icon, 'poster': s.src_icon})
            if hasattr(s, 'src_fanart') and s.src_fanart:
                li.setArt({'fanart': s.src_fanart})
        except Exception:
            pass
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'source', 'src': s.idx}), li, isFolder=True)

    
    # Refresh All Sources button (clears caches & rebuilds all)
    li_all = xbmcgui.ListItem(label='Refresh All Sources')
    try:
        icon_all = os.path.join(ADDON_PATH, 'resources', 'media', 'refresh_all.png')
        li_all.setArt({'thumb': icon_all, 'icon': icon_all, 'poster': icon_all, 'fanart': FALLBACK_FANART})
    except Exception:
        set_art(li_all)
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'refresh_all'}), li_all, isFolder=False)
# Settings at bottom
    li_set = xbmcgui.ListItem(label='Settings')
    set_art(li_set)
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'settings'}), li_set, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def list_source_home(src_idx: int):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src: xbmcgui.Dialog().ok('Playlist Browser', 'Source not found. Configure in Settings.'); return
    _maybe_run_iptv_merge_for_source(src_idx)
    for label, action in [('Live TV Guide','guide_now'), ('Channel Groups','channel_groups'), ('Up Next TV Guide','guide_channels'), ('Refresh EPG now','refresh_epg'), ('Refresh channels now','refresh_channels'), ('Write diagnostics (match report)','write_match_report')]:
        li = xbmcgui.ListItem(label=label); set_art(li)
        # Attach custom thumbs for specific menus (case-insensitive match; no filesystem checks on special:// paths)
        try:
            media_dir = os.path.join(ADDON_PATH, 'resources', 'media')
            _menu_map = {
                'live tv guide': 'live_tv_guide.png',
                'channel groups': 'channel_groups.png',
                'up next tv guide': 'up_next_tv_guide.png',
                'refresh epg now': 'refresh_epg.png',
                'refresh channels now': 'refresh_channels.png',
                'write diagnostics (match report)': 'write_diagnostics.png',
                'refresh epg now': 'refresh_epg.png',
            }
            key = (label or '').strip().lower()
            fname = _menu_map.get(key)
            if fname:
                icon_path = os.path.join(media_dir, fname)
                li.setArt({'thumb': icon_path, 'icon': icon_path, 'poster': icon_path})
        except Exception:
            pass
        is_folder = action not in ('refresh_epg','refresh_channels','write_match_report')
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':action,'src':src.idx}), li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(HANDLE)

def list_channels(src_idx: int):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src: xbmcgui.Dialog().ok('Channels', 'Source not found.'); xbmcplugin.endOfDirectory(HANDLE); return
    channels = src.load_channels(); src.load_epg()
    xbmcplugin.setContent(HANDLE, 'videos')
    for ch in channels:
        title = ch.get('name','Channel'); li = xbmcgui.ListItem(label=_apply_color(title, 'COLOR_CHANNEL'))
        info = {'title': _apply_color(title, 'COLOR_CHANNEL'), 'genre': ch.get('group','Live'), 'mediatype':'video'}; li.setInfo('video', info)
        set_art(li, channel_logo(ch, src)); li.setProperty('IsPlayable','true')
        epg_key = src.match_epg_key(ch); now_utc = datetime.now(timezone.utc)
        if epg_key and src.progs.get(epg_key):
            current = next((p for p in src.progs[epg_key] if p['start']<=now_utc<p['stop']), None)
            if current:
                li.setLabel2(_apply_color(current['title'], 'COLOR_EPG') + '  ' + _apply_color('(' + nice_time(current['start']) + '-' + nice_time(current['stop']) + ')', 'COLOR_TIME'))
                li.setInfo('video', {**info, 'plot': current.get('desc','')})
        li.addContextMenuItems([('Add To Your Live TV Favorites', f"RunPlugin({build_url({'action':'fav_add','src':src.idx,'cname':ch.get('name',''),'tvg':ch.get('tvg_id',''),'url':ch.get('url',''),'logo':channel_logo(ch, src)})})")], replaceItems=True)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'play','url':ch['url']}), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def show_guide_now(src_idx: int):
    log(f"Rendering Guide (Now) for source {src_idx}")
    src = next((x for x in load_sources() if x.idx == src_idx), None)
    if not src:
        xbmcgui.Dialog().ok('Guide', 'Source not found.')

        return

    channels = src.load_channels()
    src.load_epg()

    matched = sum(1 for ch in channels if src.match_epg_key(ch))
    log(f"Match rate: {matched}/{len(channels)} channels mapped to EPG (src {src_idx})")

    now_utc = datetime.now(timezone.utc)
    xbmcplugin.setContent(HANDLE, 'videos')

    for ch in channels:
        epg_key = src.match_epg_key(ch)
        current = None
        if epg_key and src.progs.get(epg_key):
            for pr in src.progs[epg_key]:
                if pr['start'] <= now_utc < pr['stop']:
                    current = pr
                    break

        title_plain = ch.get('name', 'Channel')
        title_col = _apply_color(title_plain, 'COLOR_CHANNEL')

        if current:
            tstart = nice_time(current['start'])
            tstop = nice_time(current['stop'])
            epg_title = current.get('title', '') or ''
            epg_col = _apply_color(epg_title, 'COLOR_EPG')
            time_col = _apply_color(f"({tstart}-{tstop})", 'COLOR_TIME')
            label_epg = f"{epg_col}  {time_col}"

            # Put EPG info both in Label (after channel) AND in Label2 for skins that show only one
            label = f"{title_col}  {label_epg}"
            label2 = label_epg

            desc = current.get('desc', '') or ''
            plot = f"{epg_title}  ({tstart}-{tstop})\n{desc}"
        else:
            # No current EPG: show only the channel name (no extra '(No current EPG)' text)
            label = f"{title_col}"
            label2 = ''
            plot = ''

        li = xbmcgui.ListItem(label=label)
        li.setLabel2(label2)
        li.setInfo('video', {'title': title_col, 'plot': plot, 'mediatype': 'video'})
        set_art(li, channel_logo(ch, src))
        li.setProperty('IsPlayable', 'true')
        li.addContextMenuItems([('Add To Your Live TV Favorites', f"RunPlugin({build_url({'action':'fav_add','src':src.idx,'cname':ch.get('name',''),'tvg':ch.get('tvg_id',''),'url':ch.get('url',''),'logo':channel_logo(ch, src)})})")], replaceItems=True)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'play', 'url': ch['url']}), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def list_channel_groups(src_idx: int):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src:
        xbmcgui.Dialog().ok('Channel Groups', 'Source not found.')
        xbmcplugin.endOfDirectory(HANDLE); return
    channels = src.load_channels()
    # Collect unique non-empty groups
    groups = sorted({(ch.get('group') or '').strip() for ch in channels if (ch.get('group') or '').strip()})
    if not groups:
        li = xbmcgui.ListItem(label='No groups found'); set_art(li)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'channels','src':src.idx}), li, isFolder=True)
        xbmcplugin.endOfDirectory(HANDLE); return
    for grp in groups:
        li = xbmcgui.ListItem(label=grp); set_art(li)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'channels_by_group','src':src.idx,'group':grp}), li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def list_channels_by_group(src_idx: int, group_name: str):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src:
        xbmcgui.Dialog().ok('Channels', 'Source not found.')
        xbmcplugin.endOfDirectory(HANDLE); return
    channels = [ch for ch in src.load_channels() if (ch.get('group') or '').strip() == (group_name or '').strip()]
    src.load_epg()
    xbmcplugin.setContent(HANDLE, 'videos')
    now_utc = datetime.now(timezone.utc)
    for ch in channels:
        epg_key = src.match_epg_key(ch)
        current = None
        if epg_key and src.progs.get(epg_key):
            for pr in src.progs[epg_key]:
                if pr['start'] <= now_utc < pr['stop']:
                    current = pr
                    break

        title_plain = ch.get('name','Channel')
        title_col = _apply_color(title_plain, 'COLOR_CHANNEL')

        if current:
            tstart = nice_time(current['start'])
            tstop = nice_time(current['stop'])
            epg_title = current.get('title','') or ''
            epg_col = _apply_color(epg_title, 'COLOR_EPG')
            time_col = _apply_color(f"({tstart}-{tstop})", 'COLOR_TIME')
            label_epg = f"{epg_col}  {time_col}"
            label = f"{title_col}  {label_epg}"
            label2 = label_epg
            plot = f"{epg_title}  ({tstart}-{tstop})\n{current.get('desc','') or ''}"
        else:
            # No current EPG: show only the channel name (no extra '(No current EPG)' text)
            label = f"{title_col}"
            label2 = ''
            plot = ''

        li = xbmcgui.ListItem(label=label)
        li.setLabel2(label2)
        li.setInfo('video', {'title': title_col, 'plot': plot, 'mediatype':'video', 'genre': ch.get('group','Live')})
        set_art(li, channel_logo(ch, src)); li.setProperty('IsPlayable','true')
        li.addContextMenuItems([('Add To Your Live TV Favorites', f"RunPlugin({build_url({'action':'fav_add','src':src.idx,'cname':ch.get('name',''),'tvg':ch.get('tvg_id',''),'url':ch.get('url',''),'logo':channel_logo(ch, src)})})")], replaceItems=True)
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'play','url':ch['url']}), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def list_guide_channels(src_idx: int):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src: xbmcgui.Dialog().ok('Guide', 'Source not found.'); xbmcplugin.endOfDirectory(HANDLE); return
    channels = src.load_channels(); src.load_epg()
    for ch in channels:
        li = xbmcgui.ListItem(label=ch.get('name','Channel')); set_art(li, channel_logo(ch, src))
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'guide_channel','src':src.idx,'cname':ch.get('name',''),'tvg':ch.get('tvg_id',''),'url':ch.get('url','')}), li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def show_guide_for_channel(src_idx: int, cname: str, tvg: str, play_url: str):
    src = next((x for x in load_sources() if x.idx==src_idx), None)
    if not src: xbmcgui.Dialog().ok('Guide', 'Source not found.'); xbmcplugin.endOfDirectory(HANDLE); return
    channels = src.load_channels(); src.load_epg()
    ch = None
    for c in channels:
        if (tvg and c.get('tvg_id') == tvg) or c.get('name') == cname: ch = c; break
    if not ch: xbmcgui.Dialog().ok('Guide', 'Channel not in this source.'); xbmcplugin.endOfDirectory(HANDLE); return
    epg_key = src.match_epg_key(ch); progs = src.progs.get(epg_key, [])
    if not progs:
        li = xbmcgui.ListItem(label=f"No EPG for {ch.get('name','Channel')}"); set_art(li, channel_logo(ch, src))
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'noop'}), li, isFolder=False); xbmcplugin.endOfDirectory(HANDLE); return
    now_utc = datetime.now(timezone.utc)
    for pr in progs:
        if pr['stop'] < now_utc and pr['stop'].date() == now_utc.date(): continue
        lo_start = _fmt_ampm_range_start(pr['start']); lo_stop = _fmt_ampm_time(pr['stop'])
        li = xbmcgui.ListItem(label=_apply_color(f"{lo_start}-{lo_stop}", 'COLOR_TIME') + '  ' + _apply_color(pr['title'], 'COLOR_EPG')); li.setInfo('video', {'title': pr['title'], 'plot': pr.get('desc',''), 'mediatype':'video'})
        set_art(li, channel_logo(ch, src)); li.setProperty('IsPlayable','true')
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'play','url': play_url or ch.get('url','')}), li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)

def play_item(stream_url: str):
    li = xbmcgui.ListItem(path=stream_url); li.setProperty('IsPlayable','true')
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

# ---------- Router ----------
def router(paramstring):
    log("Router start")
    params = dict(urllib.parse.parse_qsl(paramstring[1:])) if paramstring else {}
    action = params.get('action')
    if action == 'settings': ADDON.openSettings()
    elif action == 'refresh_epg': refresh_epg(int(params.get('src','0') or '0'))
    elif action == 'refresh_channels': refresh_channels(int(params.get('src','0') or '0'))
    elif action == 'write_match_report': write_match_report(int(params.get('src','0') or '0'))
    elif action == 'play': play_item(params.get('url',''))
    elif action == 'source': list_source_home(int(params.get('src','0') or '0'))
    elif action == 'channels': list_channels(int(params.get('src','0') or '0'))
    elif action == 'guide_now': show_guide_now(int(params.get('src','0') or '0'))
    elif action == 'guide_channels': list_guide_channels(int(params.get('src','0') or '0'))
    elif action == 'guide_channel': show_guide_for_channel(int(params.get('src','0') or '0'), params.get('cname',''), params.get('tvg',''), params.get('url',''))
    elif action == 'channel_groups': list_channel_groups(int(params.get('src','0') or '0'))
    elif action == 'channels_by_group': list_channels_by_group(int(params.get('src','0') or '0'), params.get('group',''))
    elif action == 'favorites': list_favorites()
    elif action == 'fav_add': fav_add(int(params.get('src','0') or '0'), params.get('cname',''), params.get('tvg',''), params.get('url',''), params.get('logo','') or '')
    elif action == 'fav_remove': fav_remove(params.get('cname',''), params.get('tvg',''), params.get('url',''))
    elif action == 'refresh_all': refresh_all_sources()
    else: list_root()

if __name__ == '__main__':
    log("Addon boot"); router(sys.argv[2])
