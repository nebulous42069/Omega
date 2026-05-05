# -*- coding: utf-8 -*-
import xbmcgui
import ipaddress
import re
import time as _time
import datetime
import requests
import unicodedata
import urllib.parse
import xbmc
import xbmcaddon

from lang import _t


def _is_private_ip_literal(hostname):
    """Check if hostname is an IP-literal pointing to private address space.

    Returns True only for actual IP addresses (not hostnames) in private ranges.
    Hostnames that resolve to private IPs are allowed (handled by DNS).
    """
    if not hostname:
        return False
    # Check for localhost variants first
    if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"):
        return True
    # Strip IPv6 brackets if present
    if hostname.startswith("[") and hostname.endswith("]"):
        hostname = hostname[1:-1]
    try:
        # Try to parse as IP address
        ip = ipaddress.ip_address(hostname)
        # Check if private, loopback, link-local, or reserved
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        # Not an IP address - it's a hostname, allow it
        return False


def _validate_url(url, allow_http=True):
    """Validate URL format and security. Returns sanitized URL or None."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    # Security: block potential SSRF attempts via IP-literal private addresses
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname or ""
        # Block IP-literal private addresses (but allow hostnames)
        if _is_private_ip_literal(hostname):
            return None
        # Block file:// protocol (shouldn't happen with above check but defense in depth)
        if parsed.scheme == "file":
            return None
    except Exception:
        return None
    return url


HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 5]
# Cap M3U download size — prevents OOM on low-memory Android devices
M3U_MAX_BYTES = 50 * 1024 * 1024  # 50 MB (10x larger than any legitimate M3U)


_LOG_REDACT_PATH_RE = re.compile(
    r"(/(?:live|movie|series)/)([^/?\s]+)(/?)([^/?\s]*)", re.IGNORECASE
)
_LOG_REDACT_QUERY_RE = re.compile(r"(?i)\b(password|pwd|pass)=([^&\s]+)")
_LOG_MAX_LEN = 4000


def _log(msg):
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
    xbmc.log(f"[XStream Player] {safe_msg}", xbmc.LOGDEBUG)


def _notify(msg):

    xbmcgui.Dialog().notification(
        "XStream Player", msg, xbmcgui.NOTIFICATION_ERROR, 3000
    )


def _request_with_retry(url, params=None, headers=None, timeout=15):
    """Make an HTTP GET request with retry, manual same-host redirects, and exponential backoff."""
    # Validate URL before fetching (block IP-literal private addresses)
    if not _validate_url(url):
        _log(f"URL blocked by SSRF protection: {url}")
        raise requests.exceptions.ConnectionError(
            f"URL blocked by security policy: {url}"
        )
    if headers is None:
        headers = _get_headers()
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Credentials live in the query string, so a cross-host redirect would leak them.
            # Disable automatic redirects and only follow same-host ones.
            initial_host = urllib.parse.urlparse(url).netloc.lower()
            current_url = url
            current_params = params
            resp = None
            for _hop in range(5):
                resp = requests.get(
                    current_url,
                    params=current_params,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=False,
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
                            f"Redirect to different host blocked (creds protection): {next_host}"
                        )
                    current_url = next_url
                    current_params = None  # params already in URL after first request
                    resp.close()
                    continue
                break
            else:
                if resp is not None:
                    resp.close()
                raise ValueError("Redirect loop")
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as e:
            last_error = e
            _log(f"Connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        except requests.exceptions.Timeout as e:
            last_error = e
            _log(f"Timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        except requests.exceptions.HTTPError as e:
            # Don't retry on 4xx errors (auth failures, not found, etc.)
            if e.response is not None and 400 <= e.response.status_code < 500:
                _log(f"HTTP {e.response.status_code}: {e}")
                raise
            last_error = e
            _log(f"HTTP error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            last_error = e
            _log(f"Request error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            _log(f"Retrying in {delay}s...")
            _time.sleep(delay)
    _log(f"All {MAX_RETRIES} attempts failed for {url.split('?')[0]}")
    if last_error:
        raise last_error
    raise requests.exceptions.ConnectionError(f"Failed after {MAX_RETRIES} attempts")


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


def _clean_base_url(url):
    if not url:
        return url
    url = url.rstrip("/")
    if url.endswith("/player_api.php"):
        url = url[: -len("/player_api.php")]
    return url.rstrip("/")


class IPTV:
    @staticmethod
    def get_m3u_channels(m3u_url):
        channels = []
        if not m3u_url:
            return channels
        # Validate URL before fetching (block IP-literal private addresses)
        if not _validate_url(m3u_url):
            _log(f"M3U URL blocked by SSRF protection: {m3u_url}")
            _notify(_t(30700))
            return channels
        try:
            current_url = m3u_url
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
                    # SSRF guard: block redirects to private IP literals only
                    if not _validate_url(next_url):
                        resp.close()
                        _log(f"M3U redirect blocked (SSRF): {next_url}")
                        _notify(_t(30700))
                        return channels
                    resp.close()
                    current_url = next_url
                    continue
                break
            resp.raise_for_status()
            # Validate Content-Type
            content_type = resp.headers.get("Content-Type", "").lower()
            valid_m3u_types = (
                "application/vnd.apple.mpegurl",
                "application/x-mpegurl",
                "audio/mpegurl",
                "text/plain",
                "text/",
            )
            if content_type and not any(ct in content_type for ct in valid_m3u_types):
                _log(f"M3U unexpected Content-Type: {content_type}")
            # Stream-read with size cap to prevent OOM on hostile/misconfigured URLs
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > M3U_MAX_BYTES:
                    resp.close()
                    _log(f"M3U payload exceeds {M3U_MAX_BYTES} bytes, aborting")
                    _notify(_t(30700))
                    return channels
                chunks.append(chunk)
            resp.close()
            content = b"".join(chunks)
            if len(content) < 10:
                _log(f"M3U content too short ({len(content)} bytes)")
                _notify(_t(30700))
                return channels
            raw_text = content.decode("utf-8", errors="replace")
            # Warn if missing M3U header
            if not raw_text.strip().startswith("#EXTM3U"):
                _log("M3U missing #EXTM3U header, attempting parse anyway")
            lines = raw_text.splitlines()
        except Exception as e:
            _log(f"M3U fetch error: {e}")
            _notify(_t(30700))
            return channels

        _VALID_STREAM_SCHEMES = (
            "http://", "https://",
            "rtmp://", "rtmps://", "rtmpe://", "rtmpt://",
            "rtsp://",
            "udp://", "rtp://",
            "pipe://",
        )
        current = {}
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                current = {
                    "name": "",
                    "group": _t(30701),
                    "logo": "",
                    "tvg_id": "",
                    "catchup": "",
                    "catchup_source": "",
                    "catchup_days": "",
                    "kodi_props": {},
                    "user_agent": "",
                    "referrer": "",
                }
                if "," in line:
                    current["name"] = line.split(",", 1)[1].strip()
                current["name"] = _extract_attr(line, "tvg-name") or current["name"]
                current["logo"] = _extract_attr(line, "tvg-logo") or ""
                current["group"] = _extract_attr(line, "group-title") or "General"
                current["tvg_id"] = _extract_attr(line, "tvg-id") or ""
                current["radio"] = (
                    _extract_attr(line, "radio") or _extract_attr(line, "type") or ""
                )
                current["catchup"] = _extract_attr(line, "catchup") or ""
                current["catchup_source"] = _extract_attr(line, "catchup-source") or ""
                current["catchup_days"] = _extract_attr(line, "catchup-days") or ""
            elif line.startswith("#KODIPROP:") and current:
                prop = line[len("#KODIPROP:"):]
                if "=" in prop:
                    k, v = prop.split("=", 1)
                    current["kodi_props"][k.strip()] = v.strip()
            elif line.startswith("#EXTVLCOPT:") and current:
                opt = line[len("#EXTVLCOPT:"):]
                if opt.lower().startswith("http-user-agent="):
                    current["user_agent"] = opt.split("=", 1)[1]
                elif opt.lower().startswith("http-referrer="):
                    current["referrer"] = opt.split("=", 1)[1]
            elif line and not line.startswith("#") and current:
                if line.startswith(_VALID_STREAM_SCHEMES):
                    # Auto-detect DASH/ISM from URL extension if not set via KODIPROP
                    if not current["kodi_props"].get("inputstream"):
                        url_path = line.split("?")[0].lower()
                        if url_path.endswith(".mpd"):
                            current["kodi_props"]["inputstream"] = "inputstream.adaptive"
                            current["kodi_props"].setdefault(
                                "inputstream.adaptive.manifest_type", "mpd"
                            )
                        elif url_path.endswith((".ism", ".isml")):
                            current["kodi_props"]["inputstream"] = "inputstream.adaptive"
                            current["kodi_props"].setdefault(
                                "inputstream.adaptive.manifest_type", "ism"
                            )
                    current["url"] = line
                    channels.append(current)
                else:
                    _log(
                        f"M3U skipping channel '{current.get('name', 'unknown')}': unsupported URL scheme"
                    )
                current = {}
        return channels

    @staticmethod
    def validate_xtream(base_url, username, password):
        """Validate Xtream credentials. Returns dict with account info or None on failure."""
        url = f"{_clean_base_url(base_url)}/player_api.php"
        try:
            resp = _request_with_retry(
                url,
                params={"username": username, "password": password},
                timeout=_get_timeout(),
            )
            data = resp.json()
            user_info = data.get("user_info", {})
            server_info = data.get("server_info", {})
            if user_info.get("auth") == 0:
                return None
            return {
                "status": user_info.get("status", "unknown"),
                "exp_date": user_info.get("exp_date", ""),
                "max_connections": user_info.get("max_connections", ""),
                "active_cons": user_info.get("active_cons", "0"),
                "is_trial": user_info.get("is_trial", "0"),
                "created_at": user_info.get("created_at", ""),
                "server_url": server_info.get("url", ""),
                "timezone": server_info.get("timezone", ""),
            }
        except Exception:
            return None

    @staticmethod
    def get_xtream_categories(base_url, username, password, stype="live"):
        url = f"{_clean_base_url(base_url)}/player_api.php"
        action = {
            "live": "get_live_categories",
            "movie": "get_vod_categories",
            "series": "get_series_categories",
        }.get(stype, "get_live_categories")
        _log(f"Calling Xtream categories URL: {url}")
        try:
            resp = _request_with_retry(
                url,
                params={"username": username, "password": password, "action": action},
                timeout=_get_timeout(),
            )
            data = resp.json()
            _log(f"Xtream categories ({stype}): got {len(data)} items")
            return data or []
        except Exception as e:
            _log(f"Xtream categories error ({stype}): {e}")
            _notify(_t(30821))
            return []

    @staticmethod
    def get_xtream_streams(
        base_url, username, password, stype="live", category_id=None
    ):
        url = f"{_clean_base_url(base_url)}/player_api.php"
        action = {
            "live": "get_live_streams",
            "movie": "get_vod_streams",
            "series": "get_series",
        }.get(stype, "get_live_streams")
        params = {"username": username, "password": password, "action": action}
        if category_id:
            params["category_id"] = category_id
        try:
            resp = _request_with_retry(url, params=params, timeout=_get_timeout())
            data = resp.json()
            _log(f"Xtream streams ({stype}): got {len(data)} items")
            return data or []
        except Exception as e:
            _log(f"Xtream streams error ({stype}): {e}")
            return []

    @staticmethod
    def get_xtream_series_info(base_url, username, password, series_id):
        url = f"{_clean_base_url(base_url)}/player_api.php"
        try:
            resp = _request_with_retry(
                url,
                params={
                    "username": username,
                    "password": password,
                    "action": "get_series_info",
                    "series_id": series_id,
                },
                timeout=_get_timeout(),
            )
            return resp.json() or {}
        except Exception as e:
            _log(f"Xtream series info error: {e}")
            return {}

    @staticmethod
    def get_vod_info(base_url, username, password, vod_id):
        url = f"{_clean_base_url(base_url)}/player_api.php"
        try:
            resp = _request_with_retry(
                url,
                params={
                    "username": username,
                    "password": password,
                    "action": "get_vod_info",
                    "vod_id": vod_id,
                },
                timeout=_get_timeout(),
            )
            return resp.json() or {}
        except Exception as e:
            _log(f"Xtream vod info error: {e}")
            return {}

    @staticmethod
    def build_xtream_stream_url(base_url, username, password, stream, stype="live"):
        base = _clean_base_url(base_url)
        if stype == "live":
            sid = stream.get("stream_id")
            ext = "ts"
            return f"{base}/live/{username}/{password}/{sid}.{ext}"
        elif stype == "movie":
            sid = stream.get("stream_id")
            container = stream.get("container_extension", "mp4")
            return f"{base}/movie/{username}/{password}/{sid}.{container}"
        elif stype == "series":
            sid = stream.get("id")
            container = stream.get("container_extension", "mp4")
            return f"{base}/series/{username}/{password}/{sid}.{container}"
        return ""

    @staticmethod
    def get_xtream_epg(base_url, username, password, stream_id):
        url = f"{_clean_base_url(base_url)}/player_api.php"
        try:
            resp = _request_with_retry(
                url,
                params={
                    "username": username,
                    "password": password,
                    "action": "get_short_epg",
                    "stream_id": stream_id,
                },
                timeout=_get_timeout(),
            )
            data = resp.json()
            return data.get("epg_listings", [])
        except Exception as e:
            _log(f"Xtream EPG error for stream {stream_id}: {e}")
            return []

    @staticmethod
    def build_catchup_url(
        base_url, username, password, stream_id, start_timestamp, duration_sec
    ):
        base = _clean_base_url(base_url)
        if len(start_timestamp) == 16:
            start_fmt = start_timestamp
        else:
            # Handle ISO formats like 2023-10-01T12:30:00
            try:
                dt = datetime.datetime.strptime(
                    start_timestamp.replace("T", " "), "%Y-%m-%d %H:%M:%S"
                )
                start_fmt = dt.strftime("%Y-%m-%d:%H-%M")
            except ValueError:
                start_fmt = start_timestamp
        return (
            f"{base}/streaming/timeshift.php?"
            f"username={urllib.parse.quote(username)}&"
            f"password={urllib.parse.quote(password)}&"
            f"stream={stream_id}&"
            f"start={urllib.parse.quote(start_fmt)}&"
            f"duration={duration_sec}"
        )

    @staticmethod
    def build_m3u_catchup_url(channel, start_utc, end_utc):
        """
        Build catchup URL for M3U-based channels.

        Supports catchup types: default (append utc params), append, and explicit
        catchup-source templates.

        Template variables:
        {utc}, {start}, {end}, {duration}, {offset}, {lutc}, {timestamp}
        {Y}, {m}, {d}, {H}, {M}, {S}
        and ${} variants

        Args:
            channel: dict with 'catchup', 'catchup_source', 'url' keys
            start_utc: start timestamp in UTC seconds
            end_utc: end timestamp in UTC seconds

        Returns:
            Constructed URL or None
        """

        base_url = channel.get("url", "")
        if not base_url:
            return None

        catchup_type = channel.get("catchup", "")
        catchup_source = channel.get("catchup_source", "")

        # Calculate duration
        duration_sec = int(end_utc - start_utc)

        # Format timestamps
        start_dt = datetime.datetime.utcfromtimestamp(start_utc)
        end_dt = datetime.datetime.utcfromtimestamp(end_utc)
        now_dt = datetime.datetime.utcnow()

        # Template variable mapping
        vars_map = {
            "utc": str(int(start_utc)),
            "start": str(int(start_utc)),
            "end": str(int(end_utc)),
            "duration": str(duration_sec),
            "offset": str(int(now_dt.timestamp() - start_utc)),
            "lutc": str(int(now_dt.timestamp())),
            "timestamp": str(int(start_utc)),
            "Y": start_dt.strftime("%Y"),
            "m": start_dt.strftime("%m"),
            "d": start_dt.strftime("%d"),
            "H": start_dt.strftime("%H"),
            "M": start_dt.strftime("%M"),
            "S": start_dt.strftime("%S"),
        }

        def _replace_vars(template):
            """Replace both {var} and ${var} patterns."""
            result = template
            for key, value in vars_map.items():
                result = result.replace("{" + key + "}", value)
                result = result.replace("${" + key + "}", value)
            return result

        # If explicit catchup-source template is provided, use it
        if catchup_source:
            return _replace_vars(catchup_source)

        # Handle different catchup types
        if catchup_type == "append":
            # Append mode: base_url?utc=start&lutc=end
            sep = "&" if "?" in base_url else "?"
            return f"{base_url}{sep}utc={vars_map['utc']}&lutc={vars_map['lutc']}"
        elif catchup_type == "default" or not catchup_type:
            # Default mode: similar to append
            sep = "&" if "?" in base_url else "?"
            return f"{base_url}{sep}utc={vars_map['utc']}&lutc={vars_map['lutc']}"
        else:
            # Unknown catchup type, try default behavior
            sep = "&" if "?" in base_url else "?"
            return f"{base_url}{sep}utc={vars_map['utc']}&lutc={vars_map['lutc']}"


def _extract_attr(line, attr):
    try:
        start = line.index(f'{attr}="') + len(attr) + 2
        end = line.index('"', start)
        return line[start:end]
    except ValueError:
        return ""


def _m3u_safe(val):
    if not val:
        return ""
    val = str(val).replace('"', "").replace("\n", " ").replace("\r", " ")
    allowed = set(" -_.():&/+'|`=?@#%")
    val = "".join(
        c for c in val if unicodedata.category(c)[0] in "LNZP" or c in allowed
    )
    return val.strip()


def build_m3u_content(channels):
    lines = ["#EXTM3U"]
    # Reconnect parameters for ffmpegdirect - critical for radio stream stability
    reconnect_opts = (
        "reconnect=1&reconnect_streamed=1&reconnect_at_eof=1&reconnect_delay_max=5"
    )
    for ch in channels:
        url = _m3u_safe(ch.get("url", ""))
        if not url:
            continue
        name = _m3u_safe(ch.get("name", "Unknown"))
        tvg_id = _m3u_safe(ch.get("tvg_id")) or name or "unknown"
        logo = _m3u_safe(ch.get("logo") or ch.get("stream_icon"))
        group = _m3u_safe(ch.get("group")) or "General"
        catchup = _m3u_safe(ch.get("catchup", ""))
        catchup_source = _m3u_safe(ch.get("catchup_source", ""))
        catchup_days = _m3u_safe(ch.get("catchup_days", ""))
        # Detect radio channels by group name or explicit radio attributes
        is_radio = (
            "radio" in group.lower()
            or ch.get("stream_type", "") == "radio"
            or str(ch.get("radio", "")).lower() == "true"
        )
        attrs = [
            f'tvg-id="{tvg_id}"',
            f'tvg-name="{name}"',
        ]
        if logo:
            attrs.append(f'tvg-logo="{logo}"')
        if group:
            attrs.append(f'group-title="{group}"')
        if catchup:
            attrs.append(f'catchup="{catchup}"')
            if catchup_source:
                attrs.append(f'catchup-source="{catchup_source}"')
            if catchup_days:
                attrs.append(f'catchup-days="{catchup_days}"')
        lines.append(f"#EXTINF:-1 {' '.join(attrs)},{name}")
        # Add inputstream.ffmpegdirect property BEFORE URL for all streams
        lines.append("#KODIPROP:inputstream=inputstream.ffmpegdirect")
        lines.append("#KODIPROP:inputstream.ffmpegdirect.is_realtime_stream=true")
        if is_radio:
            lines.append("#KODIPROP:inputstream.ffmpegdirect.stream_mode=timeshift")
        else:
            lines.append("#KODIPROP:inputstream.ffmpegdirect.stream_mode=live")
        # reconnect_at_eof conflicts with catchup_terminates=true on catchup channels.
        if is_radio or not catchup:
            if "|" in url:
                url = url + "&" + reconnect_opts
            else:
                url = url + "|" + reconnect_opts
        lines.append(url)
    return "\n".join(lines)
