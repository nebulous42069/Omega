# -*- coding: utf-8 -*-
import json
import os
import re
import time
from urllib.parse import urlparse, parse_qs, unquote

import xbmcvfs


def parse_m3u_credentials(m3u_url):
    """Parse credentials from an M3U URL in any common format.

    Supports:
    - Query params:  ?username=U&password=P  (also user/pass, u/p, passwd)
    - Basic auth:    http://U:P@host:port/
    - Path-based:    http://host:port/U/P/m3u8  (or m3u_plus, ts, m3u)

    Returns (base_url, username, password) or ("", "", "") if none found.
    """
    if not m3u_url:
        return "", "", ""
    try:
        parsed = urlparse(m3u_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Format 1: query-string params (most common — standard Xtream and variants)
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=False)
            username = (
                params.get("username", [""])[0]
                or params.get("user", [""])[0]
                or params.get("u", [""])[0]
            )
            password = (
                params.get("password", [""])[0]
                or params.get("pass", [""])[0]
                or params.get("passwd", [""])[0]
                or params.get("p", [""])[0]
            )
            if username and password:
                return base_url, username, password

        # Format 2: basic auth embedded in URL  (http://user:pass@host:port/...)
        if parsed.username and parsed.password:
            host = parsed.hostname or ""
            if parsed.port:
                host = f"{host}:{parsed.port}"
            clean_base = f"{parsed.scheme}://{host}"
            return clean_base, unquote(parsed.username), unquote(parsed.password)

        # Format 3: path-based /username/password/{type}
        # e.g. http://host:port/USER/PASS/m3u8  or  /USER/PASS/m3u_plus
        path_match = re.match(
            r"^/([^/?#]+)/([^/?#]+)/(m3u8?|m3u_plus|ts)(/|\?|$)",
            parsed.path,
            re.IGNORECASE,
        )
        if path_match:
            username = unquote(path_match.group(1))
            password = unquote(path_match.group(2))
            if username and password:
                return base_url, username, password
    except Exception:
        pass  # URL does not contain embedded credentials; fall back to explicit fields
    return "", "", ""


class ProfileManager:
    def __init__(self, addon):
        self.addon = addon
        raw = addon.getSetting("active_pvr_profile") or "Profile 1"
        match = re.search(r"(\d+)$", raw)
        self.active = match.group(1) if match else "1"
        # self.active is PVR profile only; non-PVR code must pass explicit profile_num.
        self.profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)
        self._cat_file = os.path.join(self.profile_path, "category_prefs.json")

    def _load_cat_prefs(self):
        try:
            with open(self._cat_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cat_prefs(self, prefs):
        tmp_file = self._cat_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self._cat_file)

    def get_profile_setting(self, key):
        return self.addon.getSetting(f"profile_{self.active}_{key}")

    def get_credentials(self):
        source_type = self.get_profile_setting("source_type")

        # Get M3U URL if set (always read it regardless of source_type so that
        # a missing/corrupted source_type doesn't silently drop credentials)
        m3u_url = self.get_profile_setting("m3u") or ""

        # Try to extract Xtream credentials from M3U URL (all formats)
        xt_base, xt_user, xt_pass = parse_m3u_credentials(m3u_url)
        has_m3u_creds = bool(xt_base and xt_user and xt_pass)

        if has_m3u_creds:
            xtream_url = xt_base
            xtream_username = xt_user
            xtream_password = xt_pass
        else:
            xtream_url = (
                self.get_profile_setting("xtream_url") if source_type != "M3U" else ""
            )
            xtream_username = (
                self.get_profile_setting("xtream_username")
                if source_type != "M3U"
                else ""
            )
            xtream_password = (
                self.get_profile_setting("xtream_password")
                if source_type != "M3U"
                else ""
            )

        # Get EPG URL (new fields with fallback to legacy epg_url)
        epg_m3u = self.get_profile_setting("epg_m3u") or ""
        epg_xtream = self.get_profile_setting("epg_xtream") or ""
        legacy_epg = self.get_profile_setting("epg_url") or ""  # Legacy field

        # Use appropriate EPG or fallback to legacy
        if source_type == "M3U":
            epg_url = epg_m3u or legacy_epg
        else:
            epg_url = epg_xtream or legacy_epg

        creds = {
            "name": self.get_profile_setting("name"),
            "source_type": source_type,
            "m3u_url": m3u_url,
            "xtream_url": xtream_url,
            "xtream_username": xtream_username,
            "xtream_password": xtream_password,
            "epg_m3u": epg_m3u,
            "epg_xtream": epg_xtream,
            "epg_url": epg_url,  # Legacy + fallback
        }
        return creds

    def get_visible_categories(self):
        prefs = self._load_cat_prefs()
        raw = prefs.get("global")
        if raw is None:
            defaults = ["live_pvr", "guide", "continue_watching", "pvr_favs", "favorites", "search", "tools"]
            # v1.1.5 → v2.0 compatibility: auto-show credentialed profiles
            # When no category_prefs.json exists (fresh install or after update),
            # enabled profiles with login data are automatically visible.
            for n in range(1, 11):
                if self.addon.getSetting(f"profile_{n}_enabled") == "true":
                    has_xtream = bool(self.addon.getSetting(f"profile_{n}_xtream_url"))
                    has_m3u = bool(self.addon.getSetting(f"profile_{n}_m3u"))
                    if has_xtream or has_m3u:
                        defaults.append(f"profile_{n}")
            return defaults
        return [x.strip().lower() for x in raw.split("|") if x.strip()]

    def set_visible_categories(self, categories):
        prefs = self._load_cat_prefs()
        prefs["global"] = "|".join(categories)
        self._save_cat_prefs(prefs)


class RefreshTracker:
    def __init__(self, addon):
        self.addon = addon
        raw = addon.getSetting("active_pvr_profile") or "Profile 1"
        match = re.search(r"(\d+)$", raw)
        self.profile = match.group(1) if match else "1"
        self.profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        self.file = os.path.join(self.profile_path, f"refresh_{self.profile}.txt")
        self._ensure_profile()

    def _ensure_profile(self):
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)

    def get_last_refresh(self):
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                return float(f.read().strip())
        except Exception:
            return 0

    def set_last_refresh(self, t=None):
        t = t or time.time()
        with open(self.file, "w", encoding="utf-8") as f:
            f.write(str(t))

    def should_refresh(self):
        if self.addon.getSetting("auto_refresh_enabled").lower() != "true":
            return False
        interval = self.addon.getSetting("auto_refresh_interval") or "24"
        # settings.xml stores the raw English value from values="12|24|48|Never"
        if interval.lower() == "never":
            return False
        try:
            hours = float(interval)
        except ValueError:
            hours = 24
        last = self.get_last_refresh()
        return (time.time() - last) > (hours * 3600)
