# -*- coding: utf-8 -*-
import sys
import calendar
import json
import os
import time
import re
import urllib.parse

import requests
import xbmc
import xbmcaddon
import xbmcvfs

from profiles import ProfileManager
from lang import _t
from iptv import _validate_url

# Use defusedxml if available; otherwise block DOCTYPE/ENTITY payloads.
try:
    from defusedxml import ElementTree as ET

    _USING_DEFUSEDXML = True

    def _safe_fromstring(text, forbid_entities=True):
        return ET.fromstring(text)
except ImportError:
    import xml.etree.ElementTree as ET

    _USING_DEFUSEDXML = False

    def _safe_fromstring(text, forbid_entities=True):
        if forbid_entities:
            # Look at a bounded prefix only — DOCTYPE/ENTITY must appear in
            # the prolog if they exist at all. Works for both bytes and str.
            head = (
                text[:4096]
                if isinstance(text, (bytes, bytearray))
                else text[:4096].encode("utf-8", "ignore")
            )
            lowered = head.lower()
            if b"<!doctype" in lowered or b"<!entity" in lowered:
                raise ValueError(
                    "XML rejected: DOCTYPE/ENTITY not allowed (install defusedxml for safe parsing)"
                )
        return ET.fromstring(text)


# Cap on EPG download size — without this, a misconfigured or hostile EPG URL
# can stream multi-GB into RAM and OOM the addon process on a 2-3 GB Shield.
EPG_MAX_BYTES = 200 * 1024 * 1024  # 200 MB

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

_startup_forced = False


def _get_timeout():
    try:
        return int(xbmcaddon.Addon().getSetting("stream_timeout") or "15")
    except ValueError:
        return 15


def _get_headers():
    custom_ua = xbmcaddon.Addon().getSetting("custom_user_agent")
    if custom_ua:
        return {"User-Agent": custom_ua}
    return HEADERS


_LOG_REDACT_PATH_RE = re.compile(
    r"(/(?:live|movie|series)/)([^/?\s]+)(/?)([^/?\s]*)", re.IGNORECASE
)
_LOG_REDACT_QUERY_RE = re.compile(r"(?i)\b(password|pwd|pass)=([^&\s]+)")
_LOG_MAX_LEN = 4000


def _epg_log(msg):
    safe_msg = str(msg)
    safe_msg = _LOG_REDACT_PATH_RE.sub(
        lambda m: (
            m.group(1)
            + "***REDACTED***"
            + m.group(3)
            + ("***REDACTED***" if m.group(4) else "")
        ),
        safe_msg,
    )
    safe_msg = _LOG_REDACT_QUERY_RE.sub(r"\1=***REDACTED***", safe_msg)
    if len(safe_msg) > _LOG_MAX_LEN:
        safe_msg = safe_msg[:_LOG_MAX_LEN] + "...[truncated]"
    xbmc.log(f"[XStream Player EPG] {safe_msg}", xbmc.LOGINFO)


class EPG:
    def __init__(self, addon, profile_num=None):
        self.addon = addon
        if profile_num is not None:
            active_profile = str(profile_num)
            # Import addon.py helper via local import to avoid circular dependency

            addon_module = sys.modules.get("resources.lib.addon")
            if addon_module is not None and hasattr(
                addon_module, "_get_credentials_for_profile"
            ):
                creds = addon_module._get_credentials_for_profile(active_profile)
            else:
                # Fallback: use ProfileManager directly
                pm = ProfileManager(addon)
                original = pm.active
                try:
                    pm.active = active_profile
                    creds = pm.get_credentials()
                finally:
                    pm.active = original
        else:
            pm = ProfileManager(addon)
            creds = pm.get_credentials()
            active_profile = pm.active

        # Get source type to determine which EPG URL to use
        source_type = creds.get("source_type", "Xtream Codes")

        # Use appropriate EPG URL based on source type
        if source_type == "M3U":
            self.epg_url = creds.get("epg_m3u", "")
        else:
            self.epg_url = creds.get("epg_xtream", "")

        # Auto-detect XMLTV URL from Xtream if no EPG URL is set and auto-detect is enabled
        self._auto_detected = False
        if not self.epg_url and addon.getSetting("auto_epg").lower() != "false":
            xt_url = creds.get("xtream_url", "")
            xt_user = creds.get("xtream_username", "")
            xt_pwd = creds.get("xtream_password", "")
            if xt_url and xt_user and xt_pwd:
                self.epg_url = f"{xt_url.rstrip('/')}/xmltv.php?username={urllib.parse.quote(xt_user)}&password={urllib.parse.quote(xt_pwd)}"
                self._auto_detected = True
                _epg_log("Auto-detected EPG URL from Xtream credentials")
        try:
            self.cache_hours = int(addon.getSetting("epg_refresh") or "4")
        except ValueError:
            self.cache_hours = 4
        try:
            self.offset_hours = float(addon.getSetting("epg_offset") or "0")
        except ValueError:
            self.offset_hours = 0.0
        self.profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        self.cache_file = os.path.join(
            self.profile_path, f"epg_cache_profile_{active_profile}.json"
        )
        self.programs = {}
        self.channel_names = {}
        self._program_starts = {}
        self.is_refreshing = False
        self._bg_thread = None

    def _ensure_profile(self):
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)

    def _cache_valid(self):
        if not os.path.exists(self.cache_file):
            return False
        age = time.time() - os.path.getmtime(self.cache_file)
        return age < (self.cache_hours * 3600)

    def _save_cache(self):
        self._ensure_profile()
        tmp_file = self.cache_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "programs": self.programs,
                    "channel_names": self.channel_names,
                    "program_starts": self._program_starts,
                },
                f,
            )
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self.cache_file)

    def _load_cache(self):
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "programs" in data:
                self.programs = data.get("programs", {})
                self.channel_names = data.get("channel_names", {})
                self._program_starts = data.get("program_starts", {})
            else:
                # Legacy cache format (just programs dict)
                self.programs = data
                self.channel_names = {}
                self._program_starts = {}
            _epg_log(f"Loaded cache with {len(self.programs)} channels")
        except Exception as e:
            _epg_log(f"Cache load failed: {e}")
            self.programs = {}
            self.channel_names = {}
            self._program_starts = {}

    def _try_fetch_epg(self, url):
        """Try to fetch and parse EPG from a URL. Returns ET root or None on failure."""
        if not _validate_url(url):
            _epg_log(f"EPG URL blocked by SSRF protection")
            return None
        # Security: only log base URL, never query params (may contain credentials)
        safe_url = url
        if safe_url:
            parsed = urllib.parse.urlparse(safe_url)
            safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        _epg_log(f"Fetching EPG from {safe_url}")
        try:
            # Credentials live in the query string, so a cross-host redirect
            # would leak username/password into a third-party access log.
            # Disable automatic redirects and only follow same-host ones.
            initial_host = urllib.parse.urlparse(url).netloc.lower()
            current_url = url
            resp = None
            for _hop in range(5):
                resp = requests.get(
                    current_url,
                    headers=_get_headers(),
                    timeout=_get_timeout(),
                    allow_redirects=False,
                    stream=True,
                )
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location", "")
                    if not loc:
                        break
                    next_url = urllib.parse.urljoin(current_url, loc)
                    next_host = urllib.parse.urlparse(next_url).netloc.lower()
                    if next_host != initial_host:
                        resp.close()
                        raise ValueError(
                            f"EPG redirect to different host blocked (creds protection): {next_host}"
                        )
                    current_url = next_url
                    resp.close()
                    continue
                break
            else:
                if resp is not None:
                    resp.close()
                raise ValueError("EPG redirect loop")
            resp.raise_for_status()
            # Bounded read so we cannot OOM on a hostile / misconfigured EPG URL.
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > EPG_MAX_BYTES:
                    resp.close()
                    raise ValueError(f"EPG payload exceeds {EPG_MAX_BYTES} bytes")
                chunks.append(chunk)
            resp.close()
            payload = b"".join(chunks)
            # Security: refuse XML containing DOCTYPE/ENTITY (XXE protection)
            root = _safe_fromstring(payload, forbid_entities=True)
            return root
        except Exception as e:
            _epg_log(f"EPG fetch failed for {safe_url}: {e}")
            return None

    def fetch(self):
        if not self.epg_url:
            _epg_log("No EPG URL configured")
            self.programs = {}
            return
        # Try primary URL
        root = self._try_fetch_epg(self.epg_url)
        # If auto-detected and failed, try fallback endpoint
        if root is None and self._auto_detected:
            fallback_url = self.epg_url.replace(
                "/xmltv.php?", "/get_litepanels_xmltv.php?"
            )
            if fallback_url != self.epg_url:
                _epg_log("Trying fallback EPG endpoint")
                root = self._try_fetch_epg(fallback_url)
        if root is None:
            self.programs = {}
            # Notify user that EPG failed
            try:
                import xbmcgui

                xbmcgui.Dialog().notification(
                    "XStream Player", _t(30757), xbmcgui.NOTIFICATION_WARNING, 5000
                )
            except Exception as e:
                _epg_log(f"EPG notify warning: {e}")
            return

        lang_pref = (self.addon.getSetting("epg_language") or "").lower()

        # Build channel name map from <channel> elements
        self.channel_names = {}
        for ch_el in root.findall("channel"):
            ch_id = ch_el.get("id", "")
            if ch_id:
                disp = ch_el.find("display-name")
                self.channel_names[ch_id] = disp.text if disp is not None else ch_id

        self.programs = {}
        for prog in root.findall("programme"):
            channel = prog.get("channel", "")
            if not channel:
                continue

            titles = prog.findall("title")
            title_el = titles[0] if titles else None
            if lang_pref and titles:
                for t in titles:
                    if (t.get("lang") or "").lower() == lang_pref:
                        title_el = t
                        break

            descs = prog.findall("desc")
            desc_el = descs[0] if descs else None
            if lang_pref and descs:
                for d in descs:
                    if (d.get("lang") or "").lower() == lang_pref:
                        desc_el = d
                        break

            icon_el = prog.find("icon")

            start = prog.get("start", "")
            stop = prog.get("stop", "")

            entry = {
                "title": title_el.text if title_el is not None else _t(30702),
                "desc": desc_el.text if desc_el is not None else "",
                "icon": icon_el.get("src") if icon_el is not None else "",
                "start": start,
                "stop": stop,
                "start_timestamp": _xmltv_time_to_simple(start),
                "start_str": _xmltv_time_to_display(start),
                "stop_timestamp": _xmltv_time_to_simple(stop),
                "duration_sec": _xmltv_duration_sec(start, stop),
            }
            self.programs.setdefault(channel, []).append(entry)

        try:
            past_days = int(self.addon.getSetting("epg_past_days") or "3")
        except ValueError:
            past_days = 3
        cutoff = time.time() - (past_days * 86400)

        for ch in self.programs:
            self.programs[ch] = [
                p for p in self.programs[ch] if _parse_xmltv_time(p["stop"]) > cutoff
            ]
            self.programs[ch].sort(key=lambda x: x["start"])
            self._program_starts[ch] = [
                _parse_xmltv_time(p["start"]) for p in self.programs[ch]
            ]
        _epg_log(f"Parsed {len(self.programs)} channels from XMLTV")
        self._save_cache()

    def _fetch_in_background(self):
        try:
            self.is_refreshing = True
            self.fetch()
        finally:
            self.is_refreshing = False
            self._bg_thread = None

    def load(self):
        global _startup_forced
        force_startup = (
            self.addon.getSetting("epg_force_refresh_startup").lower() == "true"
        )
        if force_startup and not _startup_forced:
            _epg_log("Startup force refresh triggered")
            _startup_forced = True
            self.fetch()
            return
        if self._cache_valid():
            _epg_log("EPG cache is valid, loading from disk")
            self._load_cache()
            return
        # Stale-cache-first: load expired cache immediately, refresh in background
        if os.path.exists(self.cache_file):
            _epg_log("EPG cache expired, loading stale data while refreshing in background")
            self._load_cache()
        else:
            _epg_log("EPG cache missing, will fetch in background")
            self.programs = {}
            self.channel_names = {}
            self._program_starts = {}
        if self._bg_thread is None or not self._bg_thread.is_alive():
            self._bg_thread = threading.Thread(target=self._fetch_in_background, daemon=True)
            self._bg_thread.start()

    def _apply_offset(self, ts):
        if not self.offset_hours:
            return ts
        return ts + (self.offset_hours * 3600)

    def _find_channel_id(self, channel_id, channel_name=""):
        if not channel_id and not channel_name:
            return None
        # Exact ID match
        if channel_id and channel_id in self.programs:
            return channel_id
        # Name match (case-insensitive, exact)
        if channel_name:
            name_lower = channel_name.lower()
            for cid in self.programs:
                if cid.lower() == name_lower:
                    return cid
        # Numeric ID vs string match
        if channel_id:
            for cid in self.programs:
                if str(cid) == str(channel_id):
                    return cid
        # Partial name match
        if channel_name:
            for cid in self.programs:
                if name_lower in cid.lower() or cid.lower() in name_lower:
                    return cid
        return None

    def get_current_program(self, channel_id, channel_name=""):
        matched_id = self._find_channel_id(channel_id, channel_name)
        if not matched_id:
            return None
        now = time.time()
        for prog in self.programs[matched_id]:
            start = self._apply_offset(_parse_xmltv_time(prog["start"]))
            stop = self._apply_offset(_parse_xmltv_time(prog["stop"]))
            if start and stop and start <= now < stop:
                return prog
        return None

    def get_next_program(self, channel_id, channel_name=""):
        matched_id = self._find_channel_id(channel_id, channel_name)
        if not matched_id:
            return None
        now = time.time()
        found_current = False
        for prog in self.programs[matched_id]:
            start = self._apply_offset(_parse_xmltv_time(prog["start"]))
            stop = self._apply_offset(_parse_xmltv_time(prog["stop"]))
            if start and stop and start <= now < stop:
                found_current = True
                continue
            if found_current and start and start > now:
                return prog
        # If no current program found, return first future program
        for prog in self.programs[matched_id]:
            start = self._apply_offset(_parse_xmltv_time(prog["start"]))
            if start and start > now:
                return prog
        return None

    def get_programs_for_channel(self, channel_id, channel_name="", days_back=None):
        matched_id = self._find_channel_id(channel_id, channel_name)
        if not matched_id:
            return []
        if days_back is None:
            try:
                days_back = int(self.addon.getSetting("replay_days") or "7")
            except ValueError:
                days_back = 7
        cutoff = time.time() - (days_back * 86400)
        result = []
        for prog in self.programs[matched_id]:
            stop = self._apply_offset(_parse_xmltv_time(prog["stop"]))
            if stop and stop > cutoff:
                result.append(prog)
        return result

    def export_xmltv(self, dest_path):
        if not self.programs:
            return False
        try:
            # Export all EPG data — time window filtering caused empty exports
            # when provider timestamps fell outside the hardcoded window.
            root = ET.Element("tv")
            exported_channels = set()
            for channel_id, progs in self.programs.items():
                channel_has_progs = False
                for prog in progs:
                    if channel_id not in exported_channels:
                        ch_el = ET.SubElement(root, "channel", {"id": str(channel_id)})
                        disp = ET.SubElement(ch_el, "display-name")
                        disp.text = str(self.channel_names.get(channel_id, channel_id))
                        exported_channels.add(channel_id)
                    channel_has_progs = True
                    prog_el = ET.SubElement(
                        root,
                        "programme",
                        {
                            "start": prog.get("start", ""),
                            "stop": prog.get("stop", ""),
                            "channel": str(channel_id),
                        },
                    )
                    title_el = ET.SubElement(prog_el, "title")
                    title_el.text = prog.get("title", "Unknown")
                    if prog.get("desc"):
                        desc_el = ET.SubElement(prog_el, "desc")
                        desc_el.text = prog["desc"]
                    if prog.get("icon"):
                        icon_el = ET.SubElement(prog_el, "icon", {"src": prog["icon"]})
                if channel_has_progs:
                    _epg_log(f"Exported channel {channel_id} with programs in window")
            tree = ET.ElementTree(root)
            self._ensure_profile()
            tmp_path = dest_path + ".tmp"
            with open(tmp_path, "wb") as f:
                tree.write(f, encoding="utf-8", xml_declaration=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, dest_path)
            _epg_log(f"Exported XMLTV to {dest_path}")
            return True
        except Exception as e:
            _epg_log(f"Export XMLTV failed: {e}")
            return False


def epg_file_has_data(epg_path):
    """Check if EPG XML contains actual programme data (not just empty <tv/>).

    Empty XML files (e.g., <tv></tv>) must be treated as stale so they get
    re-exported. This prevents the freshness check from blocking regeneration
    when the previous export was empty due to time-window filtering or
    provider timestamp issues.
    """
    try:
        with open(epg_path, "r", encoding="utf-8") as f:
            content = f.read(2048)  # Read first 2 KB only
        return "<programme" in content
    except Exception:
        return False


def _parse_xmltv_time(ts):
    if not ts:
        return 0
    ts = ts.strip()
    offset_sec = 0
    if " " in ts:
        parts = ts.split(" ", 1)
        ts = parts[0]
        tz = parts[1].strip()
        if tz and (tz[0] == "+" or tz[0] == "-"):
            try:
                sign = 1 if tz[0] == "+" else -1
                tz = tz[1:]
                offset_sec = sign * (int(tz[:2]) * 3600 + int(tz[2:4]) * 60)
            except (ValueError, IndexError):
                offset_sec = 0
    try:
        t = time.strptime(ts, "%Y%m%d%H%M%S")
        return calendar.timegm(t) - offset_sec
    except ValueError:
        return 0


def _xmltv_time_to_simple(ts):
    t = _parse_xmltv_time(ts)
    if not t:
        return ts
    return time.strftime("%Y-%m-%d:%H-%M", time.localtime(t))


def _xmltv_time_to_display(ts):
    t = _parse_xmltv_time(ts)
    if not t:
        return ""
    return time.strftime("%d/%m %H:%M", time.localtime(t))


def _xmltv_duration_sec(start, stop):
    s = _parse_xmltv_time(start)
    e = _parse_xmltv_time(stop)
    if s and e:
        return int(e - s)
    return 3600
