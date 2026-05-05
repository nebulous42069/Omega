# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
import datetime
import hashlib
import shutil
import traceback
import zipfile
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from iptv import IPTV, build_m3u_content
from epg import EPG, _parse_xmltv_time, epg_file_has_data
from favorites import Favorites
from history import WatchHistory, ResumePoints, WatchedMovies, WatchedEpisodes
from profiles import ProfileManager, RefreshTracker
from tmdb import TMDB
from lang import _t

addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
base_url = sys.argv[0]
args = urllib.parse.parse_qs(sys.argv[2][1:])
pm = ProfileManager(addon)


class _LazyFavorites:
    """Proxy that defers Favorites(addon, 'global') load until first attribute access."""
    _real = None

    def _instance(self):
        if self._real is None:
            _LazyFavorites._real = Favorites(addon, "global")
        return _LazyFavorites._real

    def __getattr__(self, name):
        return getattr(self._instance(), name)


fav = _LazyFavorites()

# Cache Favorites instances per profile to avoid repeated JSON file reads
_profile_fav_instances = {}


def _get_profile_fav(profile_num):
    key = str(profile_num)
    if key not in _profile_fav_instances:
        _profile_fav_instances[key] = Favorites(addon, key)
    return _profile_fav_instances[key]


def _invalidate_profile_fav(profile_num):
    _profile_fav_instances.pop(str(profile_num), None)


def _background_tmdb_fetch(title, is_tv, tmdb_key, cache_file):
    """Fire-and-forget TMDB fetch that writes cache file atomically."""
    try:
        tmdb = TMDB(tmdb_key)
        if is_tv:
            data = tmdb.enrich_tv(title)
        else:
            data = tmdb.enrich(title)
        tmp_file = cache_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, cache_file)
    except Exception as e:
        _log(f"Background TMDB fetch error for {'TV' if is_tv else 'movie'} {title}: {e}")


def _watch_history(profile_num=None):
    if profile_num is None:
        profile_num = pm.active
    return WatchHistory(addon, profile_num=profile_num)


def _resume_db(profile_num=None):
    if profile_num is None:
        profile_num = pm.active
    return ResumePoints(addon, profile_num=profile_num)


import xbmc


def _bootstrap_settings():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    dest = os.path.join(profile, "settings.xml")
    if os.path.exists(dest):
        return
    src = os.path.join(
        xbmcvfs.translatePath(addon.getAddonInfo("path")),
        "resources",
        "userdata",
        "settings.xml",
    )
    if os.path.exists(src):
        if not os.path.exists(profile):
            os.makedirs(profile)

        shutil.copy2(src, dest)
        xbmc.log(
            "[XStream Player] Bootstrapped settings from addon package", xbmc.LOGINFO
        )


_bootstrap_settings()


def _configure_kodi_pvr_osd():
    """Configure Kodi's PVR OSD navigation settings"""
    try:
        if addon.getSetting("pvr_osd_navigation") != "true":
            return

        # Enable PVR channel info and guide on arrow keys
        # These are Kodi settings, not addon settings
        settings = {
            "pvrplayback.confirmchannelswitch": "false",  # Don't confirm channel switch
            "pvrplayback.channelentrytimeout": "0",  # Immediate channel switch
        }

        for setting, value in settings.items():
            xbmc.executeJSONRPC(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "Settings.SetSettingValue",
                        "params": {"setting": setting, "value": value},
                        "id": 1,
                    }
                )
            )

        xbmc.log("[XStream Player] Configured Kodi PVR OSD settings", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[XStream Player] PVR OSD config failed: {e}", xbmc.LOGWARNING)


def _install_pvr_keymap():
    """Install PVR keymap for left/right navigation respecting user toggles."""
    try:
        keymaps_dir = xbmcvfs.translatePath("special://profile/keymaps/")
        keymap_path = os.path.join(keymaps_dir, "xstream_pvr.xml")

        if addon.getSetting("pvr_osd_navigation") != "true":
            if os.path.exists(keymap_path):
                try:
                    os.remove(keymap_path)
                except Exception as e:
                    xbmc.log(
                        f"[XStream Player] PVR keymap remove failed: {e}",
                        xbmc.LOGWARNING,
                    )
            return

        left_enabled = addon.getSetting("pvr_left_channels") == "true"
        right_enabled = addon.getSetting("pvr_right_guide") == "true"

        if not left_enabled and not right_enabled:
            if os.path.exists(keymap_path):
                try:
                    os.remove(keymap_path)
                except Exception as e:
                    xbmc.log(
                        f"[XStream Player] PVR keymap remove failed: {e}",
                        xbmc.LOGWARNING,
                    )
            return

        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<keymap>"]
        for context in ("FullscreenLiveTV", "FullscreenRadio"):
            lines.append(f"  <{context}>")
            lines.append("    <keyboard>")
            if left_enabled:
                lines.append("      <left>ActivateWindow(PVROSDChannels)</left>")
            if right_enabled:
                lines.append("      <right>ActivateWindow(PVROSDGuide)</right>")
            lines.append("    </keyboard>")
            lines.append(f"  </{context}>")
        lines.append("</keymap>")
        keymap_xml = "\n".join(lines) + "\n"

        # Rewrite only if content changed (or file missing)
        if os.path.exists(keymap_path):
            try:
                with open(keymap_path, "r", encoding="utf-8") as f:
                    if f.read() == keymap_xml:
                        return
            except Exception as e:
                xbmc.log(f"[XStream Player] keymap read warning: {e}", xbmc.LOGWARNING)

        if not os.path.exists(keymaps_dir):
            os.makedirs(keymaps_dir)
        with open(keymap_path, "w", encoding="utf-8") as f:
            f.write(keymap_xml)
        xbmc.log("[XStream Player] Installed PVR keymap", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[XStream Player] PVR keymap install failed: {e}", xbmc.LOGWARNING)


def _bootstrap_pvr():
    """Create empty PVR stub files and point pvr.iptvsimple instance 1 at them."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        os.makedirs(profile)
    m3u_path = os.path.join(profile, "pvr_live.m3u8")
    epg_path = os.path.join(profile, "pvr_epg.xml")
    if not os.path.exists(m3u_path):
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
    if not os.path.exists(epg_path):
        with open(epg_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?><tv></tv>\n')
    # Overwrite instance-1 settings to repair misconfiguration.
    try:
        pvr_profile = xbmcvfs.translatePath(
            "special://profile/addon_data/pvr.iptvsimple"
        )
        settings_path = os.path.join(pvr_profile, "instance-settings-1.xml")
        if not os.path.exists(pvr_profile):
            os.makedirs(pvr_profile)
        updates = {
            "m3uPathType": "0",
            "m3uPath": m3u_path,
            "epgPathType": "0",
            "epgPath": epg_path,
        }
        if os.path.exists(settings_path):
            tree = ET.parse(settings_path)
            root = tree.getroot()
            changed = False
            for key, val in updates.items():
                el = root.find(f".//setting[@id='{key}']")
                if el is not None:
                    if (el.text or "") != val:
                        el.text = val
                        if "default" in el.attrib:
                            del el.attrib["default"]
                        changed = True
                else:
                    new_el = ET.SubElement(root, "setting", {"id": key})
                    new_el.text = val
                    changed = True
            if changed:
                tmp_path = settings_path + ".tmp"
                tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
                with open(tmp_path, "r+b") as f:
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                os.replace(tmp_path, settings_path)
        else:
            root = ET.Element("settings", {"version": "2"})
            for key, val in updates.items():
                el = ET.SubElement(root, "setting", {"id": key})
                el.text = val
            tmp_path = settings_path + ".tmp"
            ET.ElementTree(root).write(tmp_path, encoding="utf-8", xml_declaration=True)
            with open(tmp_path, "r+b") as f:
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp_path, settings_path)
    except Exception as e:
        xbmc.log(
            f"[XStream Player] _bootstrap_pvr instance-1 write failed: {e}",
            xbmc.LOGWARNING,
        )
    _configure_kodi_pvr_osd()
    _install_pvr_keymap()


_LOG_REDACT_PATH_RE = re.compile(
    r"(/(?:live|movie|series)/)([^/?\s]+)(/?)([^/?\s]*)", re.IGNORECASE
)
_LOG_REDACT_QUERY_RE = re.compile(r"(?i)\b(password|pwd|pass)=([^&\s]+)")
_LOG_MAX_LEN = 4000


def _log(msg):
    safe_msg = str(msg)
    # Redact /live/USER/PASS, /movie/USER/PASS, /series/USER/PASS path credentials
    safe_msg = _LOG_REDACT_PATH_RE.sub(
        lambda m: (
            m.group(1)
            + "***REDACTED***"
            + m.group(3)
            + ("***REDACTED***" if m.group(4) else "")
        ),
        safe_msg,
    )
    # Redact password=, pwd=, pass= query params
    safe_msg = _LOG_REDACT_QUERY_RE.sub(r"\1=***REDACTED***", safe_msg)
    if len(safe_msg) > _LOG_MAX_LEN:
        safe_msg = safe_msg[:_LOG_MAX_LEN] + "...[truncated]"
    xbmc.log(f"[XStream Player] {safe_msg}", xbmc.LOGINFO)


def _restart_or_prompt():
    """Platform-aware restart. RestartApp is a no-op on Android (Shield, Fire TV);
    on those devices we instruct the user to fully close and reopen Kodi."""
    if xbmc.getCondVisibility("System.Platform.Android"):
        xbmcgui.Dialog().ok(_t(30042), _t(30569))
    else:
        xbmc.executebuiltin("RestartApp")


def _apply_buffer_fix():
    """Write cache settings to advancedsettings.xml (Kodi standard)."""
    if addon.getSetting("buffer_fix_enabled") != "true":
        return
    size_mb = int(addon.getSetting("buffer_size_mb") or "100")
    read_factor = int(addon.getSetting("buffer_read_factor") or "20")
    memorysize_bytes = size_mb * 1024 * 1024

    adv_path = xbmcvfs.translatePath("special://home/userdata/advancedsettings.xml")
    adv_existed = os.path.exists(adv_path)
    try:
        if adv_existed:
            tree = ET.parse(adv_path)
            root = tree.getroot()
        else:
            root = ET.Element("advancedsettings")
            tree = ET.ElementTree(root)

        cache_el = root.find("cache")
        if cache_el is None:
            cache_el = ET.SubElement(root, "cache")

        target = {
            "buffermode": "1",
            "memorysize": str(memorysize_bytes),
            "readfactor": str(read_factor),
        }

        unchanged = True
        for tag, val in target.items():
            el = cache_el.find(tag)
            if el is None or (el.text or "") != val:
                unchanged = False
                break

        if unchanged:
            _log("Buffer fix already correct, skipping write and restart prompt")
            return

        for tag, val in target.items():
            el = cache_el.find(tag)
            if el is None:
                el = ET.SubElement(cache_el, tag)
            el.text = val

        tmp = adv_path + ".tmp"
        tree.write(tmp, encoding="utf-8", xml_declaration=True)
        with open(tmp, "r+b") as f:
            try:
                os.fsync(f.fileno())
            except OSError as e:
                _log(f"Buffer fix fsync warning: {e}")
        os.replace(tmp, adv_path)
    except Exception as e:
        _log(f"Buffer fix advancedsettings.xml write failed: {e}")
        return

    _log(
        f"Buffer fix applied via advancedsettings.xml: {size_mb}MB, read factor {read_factor}x"
    )

    if adv_existed:
        if xbmcgui.Dialog().yesno(_t(30726), _t(30792)):
            _restart_or_prompt()
    else:
        _log(
            "Buffer fix advancedsettings.xml created for the first time; "
            "restart prompt skipped"
        )


def _run_one_time_bootstrap():
    """Gated startup work. The hot path is plugin reinvocation for menu
    navigation, so we skip bootstrap whenever the relevant inputs are
    unchanged. Sidecar stores `addon_version|buffer_enabled|size_mb|read_factor`;
    a mismatch (new install, addon upgrade, or buffer setting change) re-runs."""
    try:
        addon_version = addon.getAddonInfo("version")
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile):
            os.makedirs(profile)
        sidecar = os.path.join(profile, ".bootstrap_signature")
        # Read sidecar before getSetting calls so we can skip settings reads
        # entirely on the rare version-mismatch path (new install / upgrade).
        prev = ""
        if os.path.exists(sidecar):
            try:
                with open(sidecar, "r", encoding="utf-8") as f:
                    prev = f.read().strip()
            except Exception:
                prev = ""
        buf_enabled = addon.getSetting("buffer_fix_enabled") or "false"
        buf_size = addon.getSetting("buffer_size_mb") or "100"
        buf_read = addon.getSetting("buffer_read_factor") or "20"
        pvr_osd = addon.getSetting("pvr_osd_navigation") or "false"
        pvr_left = addon.getSetting("pvr_left_channels") or "true"
        pvr_right = addon.getSetting("pvr_right_guide") or "true"
        signature = f"{addon_version}|{buf_enabled}|{buf_size}|{buf_read}|{pvr_osd}|{pvr_left}|{pvr_right}"
        if prev == signature:
            return
        _bootstrap_pvr()
        _apply_buffer_fix()
        # Also sync PVR Favorites on full bootstrap if enabled
        try:
            if addon.getSetting("pvr_favorites_enabled").lower() == "true":
                _sync_pvr_favorites()
        except Exception as e:
            xbmc.log(
                f"[XStream Player] PVR Favorites bootstrap sync error: {e}",
                xbmc.LOGWARNING,
            )
        _cache_cleanup_stale()
        try:
            with open(sidecar, "w", encoding="utf-8") as f:
                f.write(signature)
        except Exception as e:
            xbmc.log(
                f"[XStream Player] bootstrap sidecar write failed: {e}", xbmc.LOGWARNING
            )
    except Exception as e:
        xbmc.log(f"[XStream Player] one-time bootstrap failed: {e}", xbmc.LOGERROR)


def build_url(query):
    return base_url + "?" + urllib.parse.urlencode(query, doseq=True)


def _apply_sort(stype):
    """Apply Kodi sort method based on per-type user preference.
    'Newest first' is handled via Python pre-sort before pagination,
    so this only registers Kodi-level sort when 'A-Z' is selected.
    """
    setting_key = f"sort_order_{stype}"
    order = addon.getSetting(setting_key) or "Provider order"
    if order == "A-Z":
        xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_LABEL)


def _get_pagination_limit(stype):
    """Return per-page limit from settings. Unlimited returns 0 (show all)."""
    val = addon.getSetting(f"pagination_{stype}") or "Unlimited"
    if val == "Unlimited":
        return 0
    try:
        return int(val)
    except ValueError:
        return 0


def _m3u_has_credentials(m3u_url):
    """Return True if the M3U URL contains embedded credentials in any supported format.

    M3U URLs with credentials are treated like Xtream Codes for UI purposes,
    showing separate Live TV, Movies, and Series categories.
    """
    from profiles import parse_m3u_credentials
    base, user, pwd = parse_m3u_credentials(m3u_url)
    return bool(base and user and pwd)


def _get_credentials():
    """Get credentials for current profile (pm.active).

    ProfileManager already extracts Xtream credentials from M3U URLs,
    so we return its result directly.
    """
    return pm.get_credentials()


def _get_credentials_for_profile(profile_num):
    """Get credentials for a specific profile number (1-10).

    Temporarily switches pm.active to get correct credentials,
    then restores original active profile.
    """
    original_active = pm.active
    try:
        pm.active = str(profile_num)
        return _get_credentials()
    finally:
        pm.active = original_active


def _get_pvr_credentials():
    """Get credentials for the PVR profile (active_pvr_profile setting)."""
    pvr_profile = addon.getSetting("active_pvr_profile") or "Profile 1"
    match = re.search(r"(\d+)$", pvr_profile)
    pnum = match.group(1) if match else "1"

    # Temporarily set pm.active to get credentials for PVR profile
    original = pm.active
    try:
        pm.active = pnum
        return _get_credentials()
    finally:
        pm.active = original


def _select_profile_or_all(allow_all=True):
    """Show a dialog to select an enabled profile. Returns profile number string,
    'all' if allow_all is True and user picks All Profiles, or None on cancel."""
    profiles = []
    for i in range(1, 11):
        if addon.getSetting(f"profile_{i}_enabled") == "true":
            name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
            label = f"Profile {i} - {name}" if name != _t(30390, i) else f"Profile {i}"
            profiles.append((str(i), label))
    if not profiles:
        xbmcgui.Dialog().notification("XStream Player", _t(30056))
        return None
    labels = [p[1] for p in profiles]
    if allow_all:
        labels.insert(0, _t(30018))  # All Profiles
    idx = xbmcgui.Dialog().select(_t(30017), labels)
    if idx < 0:
        return None
    if allow_all:
        if idx == 0:
            return "all"
        return profiles[idx - 1][0]
    return profiles[idx][0]


def _prefetch_vod_info_batch(streams, base_url, user, pwd):
    """Fetch vod_info for a batch of movies in parallel threads."""
    profile_snapshot = pm.active

    def _fetch_one(s):
        original_active = pm.active
        try:
            pm.active = profile_snapshot
            sid = str(s.get("stream_id", ""))
            if not sid:
                return
            cname = f"vod_info_{sid}"
            cached = _cache_load(cname)
            if cached:
                return
            try:
                info = IPTV.get_vod_info(base_url, user, pwd, sid)
                if info:
                    _cache_save(cname, info)
            except Exception as e:
                _log(f"VOD info prefetch error for {sid}: {e}")
        finally:
            pm.active = original_active

    # Throttled prefetch: max 4 concurrent threads with 200ms gap between batches
    # to avoid overwhelming the Xtream provider.
    batch_size = 4
    delay_ms = 200
    all_threads = []
    for i in range(0, len(streams), batch_size):
        batch = streams[i:i + batch_size]
        threads = []
        for s in batch:
            t = threading.Thread(target=_fetch_one, args=(s,))
            t.daemon = True
            threads.append(t)
            t.start()
        all_threads.extend(threads)
        if i + batch_size < len(streams):
            xbmc.sleep(delay_ms)
    # Single 15s deadline for the whole batch
    deadline = time.monotonic() + 15
    for t in all_threads:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        t.join(timeout=remaining)


def _enrich_movie_info(s, base_url=None, user=None, pwd=None):
    # Provider metadata toggles for movies
    use_prov = addon.getSetting("provider_movie_enabled").lower() == "true"
    use_prov_plot = use_prov and (addon.getSetting("provider_movie_plot").lower() == "true")
    use_prov_posters = use_prov and (addon.getSetting("provider_movie_posters").lower() == "true")
    use_prov_ratings = use_prov and (addon.getSetting("provider_movie_ratings").lower() == "true")
    use_prov_cast = use_prov and (addon.getSetting("provider_movie_cast").lower() == "true")
    use_prov_genre = use_prov and (addon.getSetting("provider_movie_genre").lower() == "true")
    use_prov_duration = use_prov and (addon.getSetting("provider_movie_duration").lower() == "true")

    result = {
        "plot": "",
        "poster_url": "",
        "rating": "",
        "year": "",
        "cast": [],
        "genre": "",
        "duration": 0,
    }

    # Apply provider data from stream list item based on toggles
    if use_prov_plot:
        result["plot"] = (
            s.get("plot") or s.get("description") or s.get("info", {}).get("plot") or ""
        )
    if use_prov_posters:
        result["poster_url"] = s.get("stream_icon") or ""
    if use_prov_ratings:
        result["rating"] = str(s.get("rating", "") or s.get("rating_5based", "") or "")

    # Provider vod_info enrichment (only if provider metadata is enabled)
    if use_prov and s.get("stream_id"):
        sid = str(s.get("stream_id"))
        cname = f"vod_info_{sid}"
        info = _cache_load(cname)
        if not info and base_url and user and pwd:
            # On-demand fallback: prefetch missed this movie or cache is empty, fetch it now
            try:
                info = IPTV.get_vod_info(base_url, user, pwd, sid)
                if info:
                    _cache_save(cname, info)
                else:
                    info = {}
            except Exception as e:
                _log(f"VOD info on-demand fetch error for {sid}: {e}")
                info = {}
        if info:
            if use_prov_plot:
                result["plot"] = (
                    info.get("info", {}).get("plot") or info.get("plot") or result["plot"]
                )
            if use_prov_posters:
                result["poster_url"] = (
                    info.get("info", {}).get("movie_image")
                    or info.get("stream_icon")
                    or result["poster_url"]
                )
            if use_prov_ratings:
                result["year"] = str(
                    info.get("info", {}).get("releasedate", "")
                    or info.get("info", {}).get("release_date", "")
                    or ""
                )[:4]
            if use_prov_duration:
                result["duration"] = int(info.get("info", {}).get("duration_secs", 0) or 0)
            if use_prov_cast and info.get("info", {}).get("cast"):
                cast_list = []
                for idx, actor_name in enumerate(info["info"]["cast"].split(",")[:10]):
                    name = actor_name.strip()
                    if name:
                        cast_list.append({"name": name, "role": "", "thumbnail": ""})
                result["cast"] = cast_list
            if use_prov_genre and info.get("info", {}).get("genre"):
                result["genre"] = info["info"]["genre"]

    tmdb_enabled = addon.getSetting("tmdb_enabled").lower() == "true"
    tmdb_key = addon.getSetting("tmdb_api_key") or ""
    use_tmdb_duration = False
    if tmdb_enabled and tmdb_key:
        use_tmdb_plot = addon.getSetting("tmdb_plot").lower() == "true"
        use_tmdb_posters = addon.getSetting("tmdb_posters").lower() == "true"
        use_tmdb_ratings = addon.getSetting("tmdb_ratings").lower() == "true"
        use_tmdb_cast = addon.getSetting("tmdb_cast").lower() == "true"
        use_tmdb_duration = addon.getSetting("tmdb_duration").lower() == "true"
        # Fetch TMDB if ANY feature is enabled
        if use_tmdb_plot or use_tmdb_posters or use_tmdb_ratings or use_tmdb_cast or use_tmdb_duration:
            clean_title = s.get("name", "")
            # Sanitize title for use as filename (remove Windows invalid chars)
            safe_title = re.sub(r'[<>:"/\|?*]', "", clean_title)
            cname = f"tmdb_search_{safe_title.lower().replace(' ', '_')}"
            tmdb_cache_file = _tmdb_cache_path(cname)
            tmdb_data = None
            try:
                with open(tmdb_cache_file, "r", encoding="utf-8") as f:
                    tmdb_data = json.load(f)
            except Exception:
                pass  # Cache file may be corrupt or missing, will be re-fetched
            cache_needs_refresh = tmdb_data is None
            if not cache_needs_refresh:
                try:
                    age = time.time() - os.path.getmtime(tmdb_cache_file)
                    if age >= (720 * 3600):
                        cache_needs_refresh = True
                except OSError:
                    cache_needs_refresh = True
            # Also refresh if cast/genre is enabled but missing from cache
            if not cache_needs_refresh and use_tmdb_cast and not tmdb_data.get("cast"):
                cache_needs_refresh = True
            if not cache_needs_refresh and not tmdb_data.get("genre"):
                cache_needs_refresh = True
            if not cache_needs_refresh and use_tmdb_duration and not tmdb_data.get("duration"):
                cache_needs_refresh = True
            if cache_needs_refresh:
                # Spawn background fetch so UI thread is never blocked by HTTP
                t = threading.Thread(
                    target=_background_tmdb_fetch,
                    args=(clean_title, False, tmdb_key, tmdb_cache_file),
                    daemon=True,
                )
                t.start()
            # Use TMDB data based on individual settings (overwrite provider)
            if use_tmdb_posters and tmdb_data.get("poster_url"):
                result["poster_url"] = tmdb_data["poster_url"]
            if use_tmdb_plot and tmdb_data.get("plot"):
                result["plot"] = tmdb_data["plot"]
            if use_tmdb_ratings and tmdb_data.get("rating"):
                result["rating"] = tmdb_data["rating"]
                result["year"] = tmdb_data.get("year", "")
            if use_tmdb_cast and tmdb_data.get("cast"):
                result["cast"] = tmdb_data["cast"]
            if use_tmdb_duration and tmdb_data.get("duration") and not result["duration"]:
                result["duration"] = tmdb_data["duration"]
            # Always get genre if available
            if tmdb_data.get("genre"):
                result["genre"] = tmdb_data["genre"]

    # Playback-discovered duration fallback (only if at least one duration source is enabled)
    if (use_prov_duration or use_tmdb_duration) and not result["duration"] and s.get("stream_id"):
        pb_dur = _load_playback_duration(str(s.get("stream_id")))
        if pb_dur:
            result["duration"] = pb_dur

    return result

def _enrich_series_info(s, base_url=None, user=None, pwd=None):
    # Provider metadata toggles for series
    use_prov = addon.getSetting("provider_series_enabled").lower() == "true"
    use_prov_plot = use_prov and (addon.getSetting("provider_series_plot").lower() == "true")
    use_prov_posters = use_prov and (addon.getSetting("provider_series_posters").lower() == "true")
    use_prov_ratings = use_prov and (addon.getSetting("provider_series_ratings").lower() == "true")
    use_prov_cast = use_prov and (addon.getSetting("provider_series_cast").lower() == "true")
    use_prov_genre = use_prov and (addon.getSetting("provider_series_genre").lower() == "true")
    use_prov_duration = use_prov and (addon.getSetting("provider_series_duration").lower() == "true")

    result = {
        "plot": "",
        "poster_url": "",
        "rating": "",
        "year": "",
        "cast": [],
        "genre": "",
        "duration": 0,
    }

    # Apply provider data from stream list item based on toggles
    if use_prov_plot:
        result["plot"] = s.get("plot", "")
    if use_prov_posters:
        result["poster_url"] = s.get("cover", "")
    if use_prov_ratings:
        result["rating"] = str(s.get("rating", "") or s.get("rating_5based", "") or "")
    if use_prov_genre and s.get("genre"):
        result["genre"] = s.get("genre")
    if use_prov_cast and s.get("cast"):
        cast_list = []
        for idx, actor_name in enumerate(s.get("cast").split(",")[:10]):
            name = actor_name.strip()
            if name:
                cast_list.append({"name": name, "role": "", "thumbnail": ""})
        result["cast"] = cast_list
    if use_prov_duration and s.get("episode_run_time"):
        try:
            ep_run_time = int(s.get("episode_run_time"))
            result["duration"] = ep_run_time * 60
        except (ValueError, TypeError):
            pass

    tmdb_enabled = addon.getSetting("tmdb_enabled").lower() == "true"
    tmdb_key = addon.getSetting("tmdb_api_key") or ""
    use_tmdb_duration = False
    if tmdb_enabled and tmdb_key:
        use_tmdb_plot = addon.getSetting("tmdb_plot").lower() == "true"
        use_tmdb_posters = addon.getSetting("tmdb_posters").lower() == "true"
        use_tmdb_ratings = addon.getSetting("tmdb_ratings").lower() == "true"
        use_tmdb_cast = addon.getSetting("tmdb_cast").lower() == "true"
        use_tmdb_duration = addon.getSetting("tmdb_duration").lower() == "true"
        # Fetch TMDB if ANY feature is enabled
        if use_tmdb_plot or use_tmdb_posters or use_tmdb_ratings or use_tmdb_cast or use_tmdb_duration:
            clean_title = s.get("name", "")
            safe_title = re.sub(r'[<>:"/\|?*]', "", clean_title)
            cname = f"tmdb_tv_search_{safe_title.lower().replace(' ', '_')}"
            tmdb_cache_file = _tmdb_cache_path(cname)
            tmdb_data = None
            try:
                with open(tmdb_cache_file, "r", encoding="utf-8") as f:
                    tmdb_data = json.load(f)
            except Exception:
                pass  # Cache file may be corrupt or missing, will be re-fetched
            cache_needs_refresh = tmdb_data is None
            if not cache_needs_refresh:
                try:
                    age = time.time() - os.path.getmtime(tmdb_cache_file)
                    if age >= (720 * 3600):
                        cache_needs_refresh = True
                except OSError:
                    cache_needs_refresh = True
            # Also refresh if cast is enabled but missing from cache
            if not cache_needs_refresh and use_tmdb_cast and not tmdb_data.get("cast"):
                cache_needs_refresh = True
            if not cache_needs_refresh and not tmdb_data.get("genre"):
                cache_needs_refresh = True
            if not cache_needs_refresh and use_tmdb_duration and not tmdb_data.get("duration"):
                cache_needs_refresh = True
            if cache_needs_refresh:
                # Spawn background fetch so UI thread is never blocked by HTTP
                t = threading.Thread(
                    target=_background_tmdb_fetch,
                    args=(clean_title, True, tmdb_key, tmdb_cache_file),
                    daemon=True,
                )
                t.start()
            # Use TMDB data based on individual settings (overwrite provider)
            if use_tmdb_posters and tmdb_data.get("poster_url"):
                result["poster_url"] = tmdb_data["poster_url"]
            if use_tmdb_plot and tmdb_data.get("plot"):
                result["plot"] = tmdb_data["plot"]
            if use_tmdb_ratings and tmdb_data.get("rating"):
                result["rating"] = tmdb_data["rating"]
                result["year"] = tmdb_data.get("year", "")
            if use_tmdb_cast and tmdb_data.get("cast"):
                result["cast"] = tmdb_data["cast"]
            if use_tmdb_duration and tmdb_data.get("duration"):
                result["duration"] = tmdb_data["duration"]
            # Always get genre if available
            if tmdb_data.get("genre"):
                result["genre"] = tmdb_data["genre"]
    return result


def _cache_path(name):
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    # Sanitize name to prevent path traversal - only allow alphanumeric, hyphen, underscore
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", str(name))
    return os.path.join(profile, f"data_cache_p{pm.active}_{safe_name}.json")


def _tmdb_cache_path(cname):
    """Global TMDB cache path (shared across all profiles)."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", str(cname))
    return os.path.join(profile, f"{safe_name}.json")


def _playback_duration_path(stream_id):
    """Path for playback-discovered duration cache (global, keyed by stream_id)."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(stream_id))
    return os.path.join(profile, f"playback_duration_{safe_id}.json")


def _save_playback_duration(stream_id, duration):
    """Cache duration discovered during playback for reuse in list views."""
    if not stream_id or not duration:
        return
    path = _playback_duration_path(stream_id)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"duration": int(duration), "timestamp": time.time()}, f)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    except Exception as e:
        _log(f"Playback duration save error: {e}")


def _load_playback_duration(stream_id):
    """Return cached playback-discovered duration in seconds, or 0."""
    if not stream_id:
        return 0
    try:
        path = _playback_duration_path(stream_id)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return int(data.get("duration", 0))
    except Exception:
        return 0


def _cache_load(name):
    try:
        with open(_cache_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _cache_save(name, data):
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        os.makedirs(profile)
    cache_file = _cache_path(name)
    tmp_file = cache_file + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
        # Durability: atomic rename is not enough on Android — without fsync
        # the rename can land before the data, leaving a zero-byte cache file
        # after a crash / power loss.
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, cache_file)


def _cache_valid(name, hours=None):
    if hours is not None:
        pass  # caller-specified
    elif name.startswith("vod_info_") or name.startswith("tmdb_"):
        hours = 30 * 24  # 30 days for static metadata
    else:
        try:
            hours = float(addon.getSetting("auto_refresh_interval") or "24")
        except ValueError:
            hours = 24
    path = _cache_path(name)
    if not os.path.exists(path):
        return False
    age = time.time() - os.path.getmtime(path)
    return age < (hours * 3600)


def _cache_clear_all():
    """Clear cache for all profiles."""
    count = 0
    for pnum in range(1, 11):
        count += _cache_clear_profile(pnum)
    return count


def _cache_clear_profile(pnum):
    """Clear cache for a specific profile number (navigation + EPG only)."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    prefix = f"data_cache_p{pnum}_"
    count = 0
    try:
        for fname in os.listdir(profile):
            if fname.startswith(prefix):
                # Boundary check: p1 must not match p10, p11, etc.
                rest = fname[len(prefix) :]
                if rest and rest[0].isdigit():
                    continue
                os.remove(os.path.join(profile, fname))
                count += 1
            elif fname == f"epg_cache_profile_{pnum}.json":
                os.remove(os.path.join(profile, fname))
                count += 1
    except Exception as e:
        _log(f"Cache clear error: {e}")
    return count


def _purge_profile_data(pnum):
    """Clear ALL profile data except PVR and favorites (for profile unload/refresh)."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    count = _cache_clear_profile(pnum)
    try:
        for fname in os.listdir(profile):
            if fname in (
                f"watch_history_p{pnum}.json",
                f"resume_points_p{pnum}.json",
                f"watched_movies_p{pnum}.json",
                f"watched_episodes_p{pnum}.json",
                f"search_history_p{pnum}.json",
                f"main_menu_order_p{pnum}.json",
            ):
                os.remove(os.path.join(profile, fname))
                count += 1
            elif fname.startswith("hidden_subcats_") and fname.endswith(f"_p{pnum}.json"):
                os.remove(os.path.join(profile, fname))
                count += 1
            elif fname.startswith("hidden_items_") and fname.endswith(f"_p{pnum}.json"):
                os.remove(os.path.join(profile, fname))
                count += 1
    except Exception as e:
        _log(f"Purge profile error: {e}")
    return count


def _cache_clear_type(pnum, stype):
    """Clear cache files for a specific content type on a profile."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    targets = [
        f"data_cache_p{pnum}_xtream_cats_{stype}.json",
        f"data_cache_p{pnum}_xtream_streams_{stype}.json",
    ]
    if stype == "live":
        targets.append(f"epg_cache_profile_{pnum}.json")
    count = 0
    try:
        for fname in targets:
            path = os.path.join(profile, fname)
            if os.path.exists(path):
                os.remove(path)
                count += 1
    except Exception as e:
        _log(f"Cache clear type error: {e}")
    return count


def _cache_clear_all_profiles():
    """Clear cache for all profiles."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    count = 0
    try:
        for fname in os.listdir(profile):
            if (
                fname.startswith("data_cache_")
                or fname.startswith("epg_cache_profile_")
                or fname.startswith("vod_info_")
                or fname.startswith("tmdb_")
                or fname.startswith("playback_duration_")
            ):
                os.remove(os.path.join(profile, fname))
                count += 1
    except Exception as e:
        _log(f"Cache clear error: {e}")
    return count


def _cache_cleanup_stale():
    """Delete cache .json files older than their type-specific TTL."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        return
    now = time.time()
    removed = 0

    # Short-lived: navigation data, EPG, playback durations
    short_prefixes = ("data_cache_", "epg_cache_profile_", "playback_duration_")
    short_max_age = 7 * 24 * 60 * 60  # 7 days
    try:
        for fname in os.listdir(profile):
            if not fname.endswith(".json"):
                continue
            if not fname.startswith(short_prefixes):
                continue
            path = os.path.join(profile, fname)
            try:
                if now - os.path.getmtime(path) > short_max_age:
                    os.remove(path)
                    removed += 1
            except OSError:
                pass
    except Exception as e:
        _log(f"Cache cleanup (short) error: {e}")

    # Long-lived: static metadata (VOD info, TMDB)
    long_prefixes = ("vod_info_", "tmdb_")
    long_max_age = 30 * 24 * 60 * 60  # 30 days
    try:
        for fname in os.listdir(profile):
            if not fname.endswith(".json"):
                continue
            if not fname.startswith(long_prefixes):
                continue
            path = os.path.join(profile, fname)
            try:
                if now - os.path.getmtime(path) > long_max_age:
                    os.remove(path)
                    removed += 1
            except OSError:
                pass
    except Exception as e:
        _log(f"Cache cleanup (long) error: {e}")

    if removed:
        _log(f"Cache cleanup removed {removed} stale file(s)")


def _get_cached_m3u_channels(m3u_url):
    if not m3u_url:
        return []
    cached = _cache_load("m3u")
    if isinstance(cached, dict) and cached.get("_url") == m3u_url and _cache_valid("m3u"):
        return cached.get("_data") or []
    data = IPTV.get_m3u_channels(m3u_url)
    _cache_save("m3u", {"_url": m3u_url, "_data": data})
    return data


def _get_cached_xtream_categories(url, user, pwd, stype):
    if not url or not user or not pwd:
        return []
    key = f"xtream_cats_{stype}"
    cached = _cache_load(key)
    source = f"{url}|{user}|{pwd}"
    if isinstance(cached, dict) and cached.get("_src") == source and _cache_valid(key):
        return cached.get("_data") or []
    data = IPTV.get_xtream_categories(url, user, pwd, stype)
    _cache_save(key, {"_src": source, "_data": data})
    return data


def _get_cached_xtream_streams(url, user, pwd, stype, category_id=None):
    if not url or not user or not pwd:
        return []
    key = f"xtream_streams_{stype}"
    cached = _cache_load(key)
    source = f"{url}|{user}|{pwd}"
    if isinstance(cached, dict) and cached.get("_src") == source and _cache_valid(key):
        data = cached.get("_data") or []
    else:
        data = IPTV.get_xtream_streams(url, user, pwd, stype, None)
        _cache_save(key, {"_src": source, "_data": data})
        # Sidecar: cache category counts so xtream_categories() never loads all streams just for counts
        counts = {}
        for s in data:
            cid = str(s.get("category_id", ""))
            counts[cid] = counts.get(cid, 0) + 1
        _cache_save(f"xtream_counts_{stype}", counts)
    if category_id:
        return [s for s in data if str(s.get("category_id", "")) == str(category_id)]
    return data


def _pvr_m3u_path():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    pvr_profile = _get_pvr_profile_num()
    return os.path.join(profile, f"pvr_live_{pvr_profile}.m3u8")


def _pvr_epg_path():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    pvr_profile = _get_pvr_profile_num()
    return os.path.join(profile, f"pvr_epg_{pvr_profile}.xml")


def _validate_pvr_epg_m3u_match(m3u_path, epg_path):
    """Warn if M3U tvg-ids and EPG channel IDs have no overlap."""
    try:
        m3u_ids = set()
        with open(m3u_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#EXTINF"):
                    match = re.search(r'tvg-id="([^"]*)"', line)
                    if match:
                        m3u_ids.add(match.group(1))
        if not m3u_ids:
            return
        epg_ids = set()
        with open(epg_path, "r", encoding="utf-8") as f:
            chunk = f.read(262144)
        for match in re.finditer(r'<channel[^>]*id="([^"]*)"', chunk):
            epg_ids.add(match.group(1))
        if m3u_ids and epg_ids and not (m3u_ids & epg_ids):
            _log("PVR WARNING: M3U tvg-ids and EPG channel IDs have zero overlap. EPG guide will be empty.")
            try:
                xbmcgui.Dialog().notification("XStream Player", _t(30892), xbmcgui.NOTIFICATION_WARNING, 5000)
            except Exception:
                pass
    except Exception as e:
        _log(f"PVR EPG/M3U validation warning: {e}")


def _export_pvr_m3u():
    _log("PVR: Starting M3U export")
    creds = _get_pvr_credentials()
    m3u_url = creds.get("m3u_url", "")
    xt_url = creds.get("xtream_url", "")
    xt_user = creds.get("xtream_username", "")
    xt_pwd = creds.get("xtream_password", "")
    _log(f"PVR: m3u_url={bool(m3u_url)}, xt_url={bool(xt_url)}")

    channels = []
    total_streams = 0

    # Get PVR profile number for loading correct hidden categories
    pvr_profile = addon.getSetting("active_pvr_profile") or "Profile 1"
    pvr_pnum = (
        re.search(r"(\d+)$", pvr_profile).group(1)
        if re.search(r"(\d+)$", pvr_profile)
        else "1"
    )

    original_active = pm.active
    try:
        pm.active = pvr_pnum

        hidden_live = _get_hidden_subcats("live", pvr_pnum)
        hidden_live_items = _get_hidden_items("live", pvr_pnum)
        hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"

        if m3u_url and not _m3u_has_credentials(m3u_url):
            for ch in _get_cached_m3u_channels(m3u_url):
                group = ch.get("group", "General")
                if group in hidden_live:
                    continue
                item_id = str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
                if item_id in hidden_live_items:
                    continue
                if hide_adult and (
                    _is_adult_category(group) or _is_adult_category(ch.get("name", ""))
                ):
                    continue
                channels.append(
                    {
                        "name": ch.get("name", "Unknown"),
                        "url": ch.get("url", ""),
                        "tvg_id": ch.get("tvg_id", ""),
                        "logo": ch.get("logo", ""),
                        "group": group,
                        "catchup": ch.get("catchup", ""),
                        "catchup_source": ch.get("catchup_source", ""),
                        "catchup_days": ch.get("catchup_days", ""),
                    }
                )
        streams = []
        if xt_url and xt_user and xt_pwd:
            # Build category ID → name lookup
            cats = _cache_load("xtream_cats_live") or IPTV.get_xtream_categories(
                xt_url, xt_user, xt_pwd, "live"
            )
            cat_map = {}
            for c in cats or []:
                cat_map[str(c.get("category_id", ""))] = c.get(
                    "category_name", "Live TV"
                )

            _log(
                f"PVR M3U export: {len(hidden_live)} hidden categories: {hidden_live}, {len(hidden_live_items)} hidden items"
            )
            streams = _get_cached_xtream_streams(xt_url, xt_user, xt_pwd, "live")
        total_streams = len(streams) if xt_url and xt_user and xt_pwd else 0
        skipped = 0
        if xt_url and xt_user and xt_pwd:
            for s in streams:
                cat_id = str(s.get("category_id", ""))
                if cat_id in hidden_live:
                    skipped += 1
                    continue
                if str(s.get("stream_id", "")) in hidden_live_items:
                    skipped += 1
                    continue
                group = cat_map.get(cat_id, "Live TV")
                if hide_adult and (
                    _is_adult_category(group) or _is_adult_category(s.get("name", ""))
                ):
                    skipped += 1
                    continue
                sid = str(s.get("stream_id", ""))
                epg_id = s.get("epg_channel_id") or sid
                url = IPTV.build_xtream_stream_url(xt_url, xt_user, xt_pwd, s, "live")
                # Treat string "0" as falsy for tv_archive/catchup flags
                tv_arch = str(s.get("tv_archive", "")).lower()
                catchup_flag = str(s.get("catchup", "")).lower()
                has_catchup = tv_arch in ("1", "yes", "true") or catchup_flag in (
                    "1",
                    "yes",
                    "true",
                    "default",
                )
                channels.append(
                    {
                        "name": s.get("name", "Unknown"),
                        "url": url,
                        "tvg_id": epg_id,
                        "logo": s.get("stream_icon", ""),
                        "group": group,
                        "stream_type": s.get("stream_type", ""),
                        "catchup": "default" if has_catchup else "",
                        "catchup_source": f"{xt_url}/live/{xt_user}/{xt_pwd}/{sid}.ts?utc={{utc}}&lutc={{lutc}}"
                        if has_catchup
                        else "",
                        "catchup_days": str(s.get("tv_archive_duration", "") or "7")
                        if has_catchup
                        else "",
                    }
                )

        _log(
            f"PVR M3U export: {total_streams} total streams, {skipped} skipped, {len(channels)} exported"
        )

        if not channels:
            return False
        m3u_path = _pvr_m3u_path()
        m3u_data = build_m3u_content(channels)
        tmp = m3u_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(m3u_data)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, m3u_path)
        # Quick validation: every EXTINF must contain a comma
        bad_lines = [
            ln
            for ln in m3u_data.splitlines()
            if ln.startswith("#EXTINF:") and "," not in ln
        ]
        if bad_lines:
            _log(f"M3U validation failed on {len(bad_lines)} lines")
            return False
        _log(f"Exported PVR M3U with {len(channels)} channels")
        return True
    finally:
        pm.active = original_active


def _export_pvr_epg():
    """Export EPG for PVR from cache. Uses existing cache if available."""
    epg_path = _pvr_epg_path()
    pvr_profile = addon.getSetting("active_pvr_profile") or "Profile 1"
    pvr_pnum = (
        re.search(r"(\d+)$", pvr_profile).group(1)
        if re.search(r"(\d+)$", pvr_profile)
        else "1"
    )
    try:
        epg = EPG(addon, profile_num=pvr_pnum)
        epg.load()
        if epg.programs and epg.export_xmltv(epg_path):
            _log(f"Exported real EPG for PVR ({len(epg.programs)} channels)")
            return True
        stub = '<?xml version="1.0" encoding="utf-8"?><tv></tv>'
        tmp = epg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(stub)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, epg_path)
        _log("Exported stub EPG for PVR (no EPG data available)")
        return True
    except Exception as e:
        _log(f"EPG export failed: {e}")
        return False


def _configure_pvr_iptvsimple():
    try:
        pvr_profile = xbmcvfs.translatePath(
            "special://profile/addon_data/pvr.iptvsimple"
        )
        if not os.path.exists(pvr_profile):
            os.makedirs(pvr_profile)
        settings_path = os.path.join(pvr_profile, "instance-settings-1.xml")
        m3u_path = _pvr_m3u_path()
        epg_path = _pvr_epg_path()

        _log("PVR: Configuring IPTV Simple Client")
        catchup_enabled = addon.getSetting("pvr_catchup_enabled").lower() == "true"
        catchup_days = addon.getSetting("pvr_catchup_days") or "7"
        # PVR EPG refresh interval (convert hours to seconds for IPTV Simple)
        try:
            pvr_epg_hours = int(addon.getSetting("pvr_epg_refresh") or "12")
        except ValueError:
            pvr_epg_hours = 12
        pvr_epg_seconds = pvr_epg_hours * 3600
        _log(
            f"PVR: Configuring EPG refresh interval to {pvr_epg_hours} hours ({pvr_epg_seconds} seconds)"
        )
        updates = {
            "m3uPathType": "0",
            "m3uPath": m3u_path,
            "m3uUrl": "",
            "epgPathType": "0",
            "epgPath": epg_path,
            "epgUrl": "",
            "epgRefreshInterval": str(pvr_epg_seconds),
            "m3uRefreshMode": "1",
            "logoPathType": "0",
            "logoPath": "",
            "logoBaseUrl": "",
            "catchupEnabled": "true" if catchup_enabled else "false",
            "catchupPlayEpgAsLive": "false",
            "allChannelsCatchupMode": "0",
            "catchupOverrideMode": "0",
            "catchupDays": catchup_days,
            "catchupOnlyOnFinishedProgrammes": "false",
            "catchupWatchEpgBeginBufferMins": "5",
            "catchupWatchEpgEndBufferMins": "15",
        }
        if os.path.exists(settings_path):
            tree = ET.parse(settings_path)
            root = tree.getroot()
            changed = False
            stale_keys = {"defaultInputstream", "defaultMimeType"}
            for stale in stale_keys:
                el = root.find(f".//setting[@id='{stale}']")
                if el is not None:
                    root.remove(el)
                    changed = True
                    _log(f"PVR: Removed stale setting '{stale}'")
            for key, val in updates.items():
                el = root.find(f".//setting[@id='{key}']")
                if el is not None:
                    if (el.text or "") != val:
                        el.text = val
                        if "default" in el.attrib:
                            del el.attrib["default"]
                        changed = True
                else:
                    new_el = ET.SubElement(root, "setting", {"id": key})
                    new_el.text = val
                    changed = True
            if changed:
                tmp_path = settings_path + ".tmp"
                tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
                with open(tmp_path, "r+b") as f:
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                os.replace(tmp_path, settings_path)
        else:
            root = ET.Element("settings", {"version": "2"})
            for key, val in updates.items():
                el = ET.SubElement(root, "setting", {"id": key})
                el.text = val
            tmp_path = settings_path + ".tmp"
            ET.ElementTree(root).write(tmp_path, encoding="utf-8", xml_declaration=True)
            with open(tmp_path, "r+b") as f:
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp_path, settings_path)
        _log("Configured PVR IPTV Simple Client")

        xbmcgui.Dialog().notification(
            "XStream Player", _t(30099), xbmcgui.NOTIFICATION_INFO, 5000
        )
        return True
    except Exception as e:
        _log(f"Configure PVR failed: {e}")
        _log(f"Traceback: {traceback.format_exc()}")
        return False


def is_pvr_iptvsimple_installed():
    try:
        addon = xbmcaddon.Addon("pvr.iptvsimple")
        _log(f"PVR: IPTV Simple found, version={addon.getAddonInfo('version')}")
        return True
    except Exception as e:
        _log(f"PVR: IPTV Simple not installed: {e}")
        return False


def prompt_install_pvr():
    dlg = xbmcgui.Dialog()
    choice = dlg.yesno(_t(30560), _t(30561), yeslabel=_t(30182), nolabel=_t(30161))
    if choice:
        xbmc.executebuiltin("InstallAddon(pvr.iptvsimple)")
        # Wait for installation and notify
        for _ in range(30):
            xbmc.sleep(1000)
            if is_pvr_iptvsimple_installed():
                xbmcgui.Dialog().notification(
                    "XStream Player", _t(30100), xbmcgui.NOTIFICATION_INFO, 5000
                )
                return True
    return choice


def _sync_pvr():
    if addon.getSetting("auto_sync_pvr").lower() != "true":
        return False
    return _sync_pvr_force()


def _pvr_sync_lock_path():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    return os.path.join(profile, ".pvr_sync_lock")


def _acquire_pvr_sync_lock():
    lock_path = _pvr_sync_lock_path()
    if os.path.exists(lock_path):
        try:
            age = time.time() - os.path.getmtime(lock_path)
            if age < 60:
                _log("PVR: Sync already in progress, skipping")
                xbmcgui.Dialog().notification(
                    "XStream Player", _t(30794), xbmcgui.NOTIFICATION_WARNING, 3000
                )
                return False
            else:
                _log("PVR: Stale sync lock found, removing")
                os.remove(lock_path)
        except Exception as e:
            _log(f"PVR: Lock check warning: {e}")
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception as e:
        _log(f"PVR: Lock create warning: {e}")
    return True


def _release_pvr_sync_lock():
    try:
        lock_path = _pvr_sync_lock_path()
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception as e:
        _log(f"PVR: Lock release warning: {e}")


def _sync_pvr_force():
    """Sync PVR with EPG cache clear to prevent stale data."""
    if not _acquire_pvr_sync_lock():
        return False
    progress = xbmcgui.DialogProgress()
    progress.create("XStream Player", _t(30868))
    try:
        _log("PVR: Starting sync with cache clear")
        if not is_pvr_iptvsimple_installed():
            _log("PVR: IPTV Simple not installed, prompting")
            prompt_install_pvr()
            return False

        # Stop PVR Manager and disable the addon to release SQLite handles
        # (Android requirement — see AGENTS.md §Android gotchas)
        progress.update(5, _t(30869))
        try:
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "PVR.Manager.Stop", "id": 1}'
            )
            _log("PVR: Manager stopped")
            xbmc.sleep(2000)
        except Exception as e:
            _log(f"PVR: Manager stop warning: {e}")

        progress.update(15, _t(30870))
        try:
            xbmc.executeJSONRPC(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "Addons.SetAddonEnabled",
                        "params": {"addonid": "pvr.iptvsimple", "enabled": False},
                    }
                )
            )
            _log("PVR: pvr.iptvsimple disabled")
            xbmc.sleep(1500)
            if sys.platform.startswith("win"):
                xbmc.sleep(2000)
        except Exception as e:
            _log(f"PVR: disable warning: {e}")

        ok = False
        try:
            try:
                # Clear EPG database while addon is disabled
                progress.update(25, _t(30871))
                _hard_reset_pvr_epg_cache(
                    stop_manager=False, start_manager=False, enable_addon=False
                )

                # Export M3U and EPG while addon is DISABLED
                progress.update(40, _t(30872))
                if not _export_pvr_m3u():
                    _log("PVR: M3U export failed, aborting sync")
                    xbmcgui.Dialog().notification("XStream Player", _t(30893))
                    return False

                # Only export EPG if file is missing, stale (>4 hours old), or empty
                progress.update(55, _t(30873))
                epg_path = _pvr_epg_path()
                epg_stale = (
                    not os.path.exists(epg_path)
                    or os.path.getsize(epg_path) == 0
                    or not epg_file_has_data(epg_path)
                    or (
                        os.path.exists(epg_path)
                        and time.time() - os.path.getmtime(epg_path) > 4 * 3600
                    )
                )
                if epg_stale:
                    _log("PVR: Existing EPG file is empty or stale, will re-export")
                    _export_pvr_epg()
                else:
                    _log("PVR: Reusing existing EPG file (fresh)")
                _validate_pvr_epg_m3u_match(_pvr_m3u_path(), epg_path)

                # Configure PVR (write settings while addon is still DISABLED)
                progress.update(70, _t(30874))
                if not _configure_pvr_iptvsimple():
                    _log("PVR: IPTV Simple configuration failed, aborting sync")
                    return False

                # Configure favorites instance (also before re-enable)
                if addon.getSetting("pvr_favorites_enabled").lower() == "true":
                    _configure_pvr_favs_instance()

                progress.update(100, _t(30877))
                ok = True
                _maybe_show_pvr_first_run()
                xbmcgui.Dialog().notification("XStream Player", _t(30878))
            finally:
                # Re-enable pvr.iptvsimple — runs even if export/configure failed
                progress.update(80, _t(30875))
                try:
                    xbmc.sleep(2000)
                    xbmc.executeJSONRPC(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "Addons.SetAddonEnabled",
                                "params": {"addonid": "pvr.iptvsimple", "enabled": True},
                            }
                        )
                    )
                    _log("PVR: pvr.iptvsimple re-enabled")
                    xbmc.sleep(2000)
                except Exception as e:
                    _log(f"PVR: re-enable warning: {e}")

                # Start PVR Manager — config is already in place
                progress.update(90, _t(30876))
                try:
                    xbmc.sleep(2000)
                    xbmc.executeJSONRPC(
                        '{"jsonrpc": "2.0", "method": "PVR.Manager.Start", "id": 1}'
                    )
                    _log("PVR: Manager started with fresh EPG")
                except Exception as e:
                    _log(f"PVR: Manager start warning: {e}")
        except Exception as e:
            _log(f"PVR sync error: {e}")
    finally:
        try:
            progress.close()
        except Exception:
            pass
        _release_pvr_sync_lock()


def _hard_reset_pvr_epg_cache(stop_manager=True, start_manager=True, enable_addon=True):
    """Wipe Kodi's PVR EPG database (Epg16.db) in a way that actually works on Android.

    On Android, PVR.Manager.Stop alone does not release the SQLite handle that
    pvr.iptvsimple holds on Epg16.db, so plain os.remove silently fails or
    leaves a ghost inode. We must disable the binary addon to force the
    handle to close. WAL mode also leaves -wal/-shm siblings that get replayed
    on next open, so we must remove those too. As a last-resort fallback for
    devices where unlink is refused but in-place writes are allowed, we
    truncate the file to zero bytes which forces Kodi to recreate the schema.

    Args:
        stop_manager: Whether to stop PVR Manager at start
        start_manager: Whether to start PVR Manager at end
        enable_addon: Whether to re-enable pvr.iptvsimple (False if caller will do it)
    """
    db_dir = xbmcvfs.translatePath("special://userdata/Database/")
    db_files = ("Epg16.db", "Epg16.db-wal", "Epg16.db-shm", "Epg16.db-journal")

    try:
        if stop_manager:
            try:
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "PVR.Manager.Stop", "id": 1}'
                )
                _log("PVR: Manager stopped (hard reset)")
                xbmc.sleep(2000)
            except Exception as e:
                _log(f"PVR: Manager stop warning: {e}")

        # Disable pvr.iptvsimple to release SQLite handles on Epg16.db.
        try:
            xbmc.executeJSONRPC(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "Addons.SetAddonEnabled",
                        "params": {"addonid": "pvr.iptvsimple", "enabled": False},
                    }
                )
            )
            _log("PVR: pvr.iptvsimple disabled")
            xbmc.sleep(2500)
            # Extra grace period on Windows where file handles linger longer
            if sys.platform.startswith("win"):
                xbmc.sleep(2000)
        except Exception as e:
            _log(f"PVR: disable iptvsimple warning: {e}")

        # Wipe Epg16.db and its WAL/SHM/journal siblings.
        # On Windows, both deletion and truncation of Epg16.db break Kodi's core
        # PVR database connection (SQLITE_MISUSE same-session, SQLITE_ERROR on
        # next boot). Skip the file wipe entirely and let Kodi refresh from the
        # newly exported EPG XML after pvr.iptvsimple restarts.
        if sys.platform.startswith("win"):
            _log("PVR: Skipping Epg16.db wipe on Windows (CPVRDatabase handle safety)")
        else:
            for name in db_files:
                p = os.path.join(db_dir, name)
                if not os.path.exists(p):
                    continue
                removed = False
                for attempt in range(3):
                    try:
                        os.remove(p)
                        removed = True
                        _log(f"PVR: removed {name}")
                        break
                    except OSError:
                        try:
                            renamed = p + ".old"
                            if os.path.exists(renamed):
                                os.remove(renamed)
                            os.rename(p, renamed)
                            os.remove(renamed)
                            removed = True
                            _log(f"PVR: removed {name} via rename trick")
                            break
                        except Exception:
                            if attempt < 2:
                                xbmc.sleep(500)
                            continue
                if not removed:
                    _log(f"PVR: unlink {name} refused; trying truncate fallback")
                    try:
                        with open(p, "wb") as f:
                            pass
                        removed = True
                        _log(f"PVR: truncated {name}")
                    except Exception as e2:
                        _log(f"PVR: could not clear {name}: {e2}")
                if not removed:
                    _log(f"PVR: WARNING {name} still present")

        # Re-enable pvr.iptvsimple only if requested (caller may want to do this later)
        if enable_addon:
            try:
                xbmc.executeJSONRPC(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "Addons.SetAddonEnabled",
                            "params": {"addonid": "pvr.iptvsimple", "enabled": True},
                        }
                    )
                )
                _log("PVR: pvr.iptvsimple re-enabled")
                xbmc.sleep(2000)
            except Exception as e:
                _log(f"PVR: re-enable iptvsimple warning: {e}")

            if start_manager:
                try:
                    xbmc.executeJSONRPC(
                        '{"jsonrpc": "2.0", "method": "PVR.Manager.Start", "id": 1}'
                    )
                    _log("PVR: Manager started (hard reset)")
                    xbmc.sleep(2000)
                    # Backup nudge: explicitly request EPG load.
                    xbmc.executeJSONRPC(
                        '{"jsonrpc": "2.0", "method": "PVR.EPGLoad", "id": 1}'
                    )
                    _log("PVR: EPG reload triggered")
                except Exception as e:
                    _log(f"PVR: Manager start warning: {e}")
    except Exception as e:
        _log(f"PVR: hard reset failed: {e}")


def _unload_pvr():
    """Clear PVR M3U/EPG files and reset EPG database."""
    _log("PVR: Unloading PVR data")
    try:
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "PVR.Manager.Stop", "id": 1}'
        )
        _log("PVR: Manager stopped (unload)")
        xbmc.sleep(2000)
    except Exception as e:
        _log(f"PVR: Manager stop warning (unload): {e}")
    try:
        xbmc.executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "Addons.SetAddonEnabled",
                    "params": {"addonid": "pvr.iptvsimple", "enabled": False},
                }
            )
        )
        _log("PVR: pvr.iptvsimple disabled (unload)")
        xbmc.sleep(2500)
        if sys.platform.startswith("win"):
            xbmc.sleep(2000)
    except Exception as e:
        _log(f"PVR: disable warning (unload): {e}")
    try:
        m3u_path = _pvr_m3u_path()
        if os.path.exists(m3u_path):
            os.remove(m3u_path)
            _log(f"PVR: Removed M3U {m3u_path}")
    except Exception as e:
        _log(f"PVR: M3U remove warning (unload): {e}")
    try:
        epg_path = _pvr_epg_path()
        if os.path.exists(epg_path):
            os.remove(epg_path)
            _log(f"PVR: Removed EPG {epg_path}")
    except Exception as e:
        _log(f"PVR: EPG remove warning (unload): {e}")
    _hard_reset_pvr_epg_cache(
        stop_manager=False, start_manager=False, enable_addon=False
    )
    try:
        xbmc.executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "Addons.SetAddonEnabled",
                    "params": {"addonid": "pvr.iptvsimple", "enabled": True},
                }
            )
        )
        _log("PVR: pvr.iptvsimple re-enabled (unload)")
        xbmc.sleep(2000)
    except Exception as e:
        _log(f"PVR: re-enable warning (unload): {e}")
    try:
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "PVR.Manager.Start", "id": 1}'
        )
        _log("PVR: Manager started (unload)")
        xbmc.sleep(1000)
    except Exception as e:
        _log(f"PVR: Manager start warning (unload): {e}")


def reset_pvr_epg_db_action():
    """User-facing action: hard-reset Kodi's PVR EPG database with confirmation and progress UI."""
    dialog = xbmcgui.Dialog()
    # Confirmation dialog
    confirm = dialog.yesno(_t(30711), _t(30712), yeslabel=_t(30713), nolabel=_t(30714))
    if not confirm:
        return
    pd = xbmcgui.DialogProgress()
    pd.create("XStream Player", _t(30704))
    try:
        _hard_reset_pvr_epg_cache()
    finally:
        pd.close()
    dialog.notification("XStream Player", _t(30705))


def _maybe_show_pvr_first_run():
    flag = os.path.join(
        xbmcvfs.translatePath(addon.getAddonInfo("profile")), "pvr_first_run_shown"
    )
    if os.path.exists(flag):
        return
    try:
        with open(flag, "w", encoding="utf-8") as f:
            f.write("1")
        xbmcgui.Dialog().ok("XStream Player", _t(30057) + "\n" + _t(30058))
    except Exception as e:
        _log(f"PVR first run flag write error: {e}")


def _build_fetch_steps(xt_url, xt_user, xt_pwd, m3u_url):
    """Build list of (label, fn) fetch steps for a profile's data."""
    steps = []
    load_live = False
    if m3u_url and not _m3u_has_credentials(m3u_url):
        steps.append(
            (_t(30350), lambda: _cache_save("m3u", IPTV.get_m3u_channels(m3u_url)))
        )
    if xt_url and xt_user and xt_pwd:
        load_live = pm.get_profile_setting("load_live") != "false"
        load_movies = pm.get_profile_setting("load_movies") != "false"
        load_series = pm.get_profile_setting("load_series") != "false"
        if load_live:
            steps.extend(
                [
                    (
                        _t(30351),
                        lambda: _cache_save(
                            "xtream_cats_live",
                            IPTV.get_xtream_categories(xt_url, xt_user, xt_pwd, "live"),
                        ),
                    ),
                    (
                        _t(30352),
                        lambda: _cache_save(
                            "xtream_streams_live",
                            IPTV.get_xtream_streams(xt_url, xt_user, xt_pwd, "live"),
                        ),
                    ),
                ]
            )
        if load_movies:
            steps.extend(
                [
                    (
                        _t(30353),
                        lambda: _cache_save(
                            "xtream_cats_movie",
                            IPTV.get_xtream_categories(
                                xt_url, xt_user, xt_pwd, "movie"
                            ),
                        ),
                    ),
                    (
                        _t(30354),
                        lambda: _cache_save(
                            "xtream_streams_movie",
                            IPTV.get_xtream_streams(xt_url, xt_user, xt_pwd, "movie"),
                        ),
                    ),
                ]
            )
        if load_series:
            steps.extend(
                [
                    (
                        _t(30355),
                        lambda: _cache_save(
                            "xtream_cats_series",
                            IPTV.get_xtream_categories(
                                xt_url, xt_user, xt_pwd, "series"
                            ),
                        ),
                    ),
                    (
                        _t(30356),
                        lambda: _cache_save(
                            "xtream_streams_series",
                            IPTV.get_xtream_streams(xt_url, xt_user, xt_pwd, "series"),
                        ),
                    ),
                ]
            )
    return steps, load_live


def _prefetch_all_data():
    creds = _get_credentials()
    xt_url = creds.get("xtream_url", "")
    xt_user = creds.get("xtream_username", "")
    xt_pwd = creds.get("xtream_password", "")
    m3u_url = creds.get("m3u_url", "")

    pd = xbmcgui.DialogProgress()
    pd.create("XStream Player", _t(30284))

    steps, load_live = _build_fetch_steps(xt_url, xt_user, xt_pwd, m3u_url)
    if load_live:
        steps.append((_t(30357), lambda: EPG(addon).fetch()))
        if addon.getSetting("auto_sync_pvr").lower() == "true":
            steps.append((_t(30358), _sync_pvr))

    total = len(steps)
    for idx, (label, fn) in enumerate(steps):
        percent = int((idx / total) * 100) if total else 0
        pd.update(percent, _t(30359, label))
        try:
            fn()
        except Exception as e:
            _log(f"Prefetch error {label}: {e}")

    pd.close()
    xbmcgui.Dialog().notification("XStream Player", _t(30080))


def _set_live_props(li):
    li.setContentLookup(False)


def play_stream(
    play_url,
    name,
    title="",
    plot="",
    icon="",
    stype="live",
    series_id="",
    season_num="",
    ep_id="",
    profile_num=None,
    kodi_props=None,
    stream_ua="",
    stream_ref="",
):
    pnum = profile_num if profile_num is not None else pm.active
    li = xbmcgui.ListItem(path=play_url)
    li.setProperty("IsPlayable", "true")
    info_tag = li.getVideoInfoTag()
    info_tag.setMediaType("video")
    info_tag.setTitle(title or name)
    info_tag.setPlot(plot or "")
    if icon:
        li.setArt({"icon": icon, "thumb": icon})
    _prepare_playback_item(li)
    # Per-channel properties from #KODIPROP / #EXTVLCOPT
    if kodi_props:
        for k, v in kodi_props.items():
            li.setProperty(k, v)
    if stream_ua:
        li.setProperty("http-header", f"User-Agent={urllib.parse.quote(stream_ua)}")
    if stream_ref:
        li.setProperty("http-header", f"Referer={urllib.parse.quote(stream_ref)}")
    if stype == "live":
        _set_live_props(li)
    # Resume point for non-live content (Kodi handles resume popup)
    resume_pos = (
        _resume_db(pnum).get_position(name, play_url)
        if stype in ("movie", "series", "episode")
        else 0
    )
    if resume_pos > 0:
        li.setProperty("ResumeTime", str(resume_pos))
        li.setProperty("TotalTime", str(int(resume_pos * 1.1)))
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=li)
    upnext_data = None
    # Prepare next episode data for autoplay and/or Up Next
    autoplay_next = addon.getSetting("series_autoplay_next").lower() == "true"
    upnext_enabled = addon.getSetting("series_upnext_enabled").lower() == "true"
    if (
        stype == "series"
        and series_id
        and season_num
        and ep_id
        and (autoplay_next or upnext_enabled)
    ):
        try:
            creds = _get_credentials_for_profile(pnum)
            xt_url = creds.get("xtream_url", "")
            xt_user = creds.get("xtream_username", "")
            xt_pwd = creds.get("xtream_password", "")
            info = IPTV.get_xtream_series_info(xt_url, xt_user, xt_pwd, series_id)
            eps = info.get("episodes", {}).get(season_num, [])
            for i, ep in enumerate(eps):
                if str(ep.get("id", "")) == str(ep_id):
                    current_ep_num = ep.get("episode_num", "")
                    if i + 1 < len(eps):
                        next_ep = eps[i + 1]
                        next_ep_id = str(next_ep.get("id", ""))
                        next_title = next_ep.get("title") or _t(
                            30542, next_ep.get("episode_num", "?")
                        )
                        next_icon = next_ep.get("info", {}).get("movie_image") or icon
                        next_play_url = IPTV.build_xtream_stream_url(
                            xt_url, xt_user, xt_pwd, next_ep, "series"
                        )
                        next_li = xbmcgui.ListItem(path=next_play_url)
                        next_li.setProperty("IsPlayable", "true")
                        next_info = next_li.getVideoInfoTag()
                        next_info.setMediaType("episode")
                        next_info.setTitle(next_title)
                        next_info.setPlot(next_ep.get("info", {}).get("plot", ""))
                        if next_icon:
                            next_li.setArt({"icon": next_icon, "thumb": next_icon})
                        _prepare_playback_item(next_li)
                        next_url = build_url(
                            {
                                "mode": "play_stream",
                                "url": next_play_url,
                                "name": next_title,
                                "icon": next_icon,
                                "stype": "series",
                                "series_id": series_id,
                                "season_num": season_num,
                                "ep_id": next_ep_id,
                                "profile_num": pnum,
                            }
                        )
                        if autoplay_next:
                            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                            playlist.add(next_url, next_li)
                            _log(f"Queued next episode: {next_title}")
                        if upnext_enabled:
                            upnext_data = {
                                "current_episode": {
                                    "episodeid": ep_id,
                                    "tvshowid": series_id,
                                    "title": title or name,
                                    "art": {"thumb": icon},
                                    "season": season_num,
                                    "episode": current_ep_num,
                                    "showtitle": title or name,
                                    "plot": plot or "",
                                    "playcount": 0,
                                },
                                "next_episode": {
                                    "episodeid": next_ep_id,
                                    "tvshowid": series_id,
                                    "title": next_title,
                                    "art": {"thumb": next_icon},
                                    "season": season_num,
                                    "episode": next_ep.get("episode_num", ""),
                                    "showtitle": next_title,
                                    "plot": next_ep.get("info", {}).get("plot", ""),
                                    "playcount": 0,
                                },
                                "play_url": next_url,
                            }
                    break
        except Exception as e:
            _log(f"Next episode queue error: {e}")
    # Store series metadata in history for proper playback from Recently Watched
    extra = None
    if stype == "series" and series_id and season_num and ep_id:
        extra = {"series_id": series_id, "season_num": season_num, "ep_id": ep_id}
    # Extract stream_id for playback duration caching
    stream_id = ""
    if stype == "movie":
        m = re.search(r"/(\d+)\.[a-zA-Z0-9]+$", play_url)
        if m:
            stream_id = m.group(1)
    elif stype == "series" and ep_id:
        stream_id = str(ep_id)

    _watch_history(pnum).add(name, play_url, icon=icon, stype=stype, extra=extra)
    # Monitor playback for resume saving and error recovery
    _monitor_playback(name, play_url, stype, profile_num=pnum, upnext_data=upnext_data, stream_id=stream_id)


def _monitor_playback(name, url, stype="live", profile_num=None, upnext_data=None, stream_id=""):
    """Background thread to save resume position, detect stream failures, and notify Up Next."""
    pnum = profile_num if profile_num is not None else pm.active

    def _worker():
        player = xbmc.Player()
        xbmc.sleep(3000)  # wait for playback to stabilize
        if not player.isPlaying():
            # Only show error for movies/series, not live TV (user can stop anytime)
            if stype not in ("live", "movie", "series"):
                _log(f"Playback failed to start for: {name}")
                retry = xbmcgui.Dialog().yesno(
                    _t(30031),
                    _t(30053).format(name),
                    yeslabel=_t(30166),
                    nolabel=_t(30161),
                )
                if retry:
                    li = xbmcgui.ListItem(path=url)
                    li.setProperty("IsPlayable", "true")
                    _prepare_playback_item(li)
                    _set_live_props(li)
                    player.play(url, li)
            return
        upnext_sent = False
        cached_dur = 0
        upnext_dur_warned = False
        while player.isPlaying():
            try:
                pos = player.getTime()
                dur = player.getTotalTime()
                if dur > 0:
                    cached_dur = dur
                    _resume_db(pnum).save_position(name, url, pos, dur)
                    if stream_id:
                        _save_playback_duration(stream_id, dur)
                if (
                    upnext_data
                    and addon.getSetting("series_upnext_enabled").lower() == "true"
                    and xbmc.getCondVisibility("System.HasAddon(service.upnext)")
                    and not upnext_sent
                ):
                    if cached_dur > 0 and (cached_dur - pos) <= 60:
                        try:
                            import base64

                            encoded = base64.b64encode(
                                json.dumps(upnext_data).encode("utf-8")
                            ).decode("ascii")
                            rpc_payload = {
                                "jsonrpc": "2.0",
                                "method": "JSONRPC.NotifyAll",
                                "params": {
                                    "sender": "plugin.video.xstream-player.SIGNAL",
                                    "message": "upnext_data",
                                    "data": [encoded],
                                },
                                "id": 1,
                            }
                            xbmc.executeJSONRPC(json.dumps(rpc_payload))
                            upnext_sent = True
                            _log("Sent Up Next notification")
                        except Exception as e:
                            _log(f"Up Next notification error: {e}")
                    elif cached_dur == 0 and pos > 120 and not upnext_dur_warned:
                        _log("Up Next: stream duration unavailable, skipping upnext notification")
                        upnext_dur_warned = True
            except Exception as e:
                _log(f"Playback monitoring error: {e}")
            xbmc.sleep(5000)

    t = threading.Thread(target=_worker)
    t.daemon = True
    t.start()


def _prepare_playback_item(li):
    if addon.getSetting("use_inputstream_adaptive").lower() == "true":
        li.setProperty("inputstream", "inputstream.adaptive")
        li.setProperty("inputstream.adaptive.manifest_type", "hls")
    custom_ua = addon.getSetting("custom_user_agent")
    if custom_ua:
        li.setProperty("http-header", f"User-Agent={urllib.parse.quote(custom_ua)}")


def _pvr_fav_ctx(stream_id, name, icon=""):
    """Return context menu item for adding/removing PVR favorites."""
    sid = str(stream_id)
    if _pvr_favs_is_fav(sid):
        return (
            _t(30217),
            f"RunPlugin({build_url({'mode': 'pvr_fav_remove', 'stream_id': sid})})",
        )
    else:
        return (
            _t(30218),
            f"RunPlugin({build_url({'mode': 'pvr_fav_add', 'stream_id': sid, 'name': name, 'icon': icon})})",
        )


def _build_fav_ctx(
    item_id,
    name,
    stype,
    icon,
    url,
    epg_id="",
    profile_num=None,
    catchup="",
    catchup_source="",
    catchup_days="",
    is_folder=False,
):
    """Build context menu items for favorites. Inside profiles: Profile Favorites + custom groups. Outside: Favorites IPTV + custom groups."""
    ctx = []
    if profile_num and not is_folder:
        # Inside a profile: show Profile Favorites (not for folders)
        profile_fav = _get_profile_fav(profile_num)
        if profile_fav.is_favorite(item_id):
            ctx.append(
                (
                    _t(30747),
                    f"RunPlugin({build_url({'mode': 'toggle_profile_fav', 'id': item_id, 'name': name, 'stype': stype, 'icon': icon, 'url': url, 'epg_id': epg_id, 'pnum': profile_num})})",
                )
            )
        else:
            ctx.append(
                (
                    _t(30746),
                    f"RunPlugin({build_url({'mode': 'toggle_profile_fav', 'id': item_id, 'name': name, 'stype': stype, 'icon': icon, 'url': url, 'epg_id': epg_id, 'pnum': profile_num})})",
                )
            )

    # Outside profiles: show Global Favorites IPTV toggle
    if not profile_num:
        if fav.is_favorite(item_id):
            ctx.append(
                (
                    _t(30745),
                    f"RunPlugin({build_url({'mode': 'toggle_fav', 'id': item_id, 'name': name, 'stype': stype, 'icon': icon, 'url': url, 'epg_id': epg_id, 'catchup': catchup, 'catchup_source': catchup_source, 'catchup_days': catchup_days})})",
                )
            )
        else:
            ctx.append(
                (
                    _t(30744),
                    f"RunPlugin({build_url({'mode': 'toggle_fav', 'id': item_id, 'name': name, 'stype': stype, 'icon': icon, 'url': url, 'epg_id': epg_id, 'catchup': catchup, 'catchup_source': catchup_source, 'catchup_days': catchup_days})})",
                )
            )

    # Add entry for each custom group (available both inside and outside profiles)
    protected_folders = {"Favorites", _t(30009) or "Favorites"}
    for gname in fav.get_folders():
        if gname in protected_folders:
            continue
        ctx.append(
            (
                _t(30219, gname),
                f"RunPlugin({build_url({'mode': 'toggle_fav', 'id': item_id, 'name': name, 'stype': stype, 'icon': icon, 'url': url, 'epg_id': epg_id, 'folder': gname, 'catchup': catchup, 'catchup_source': catchup_source, 'catchup_days': catchup_days})})",
            )
        )
    return ctx


def _watched_ctx_movie(movie_id, profile_num=None, wm=None):
    ctx = []
    if wm is None:
        wm = WatchedMovies(addon, profile_num=profile_num)
    label = _t(30806) if wm.is_watched(movie_id) else _t(30805)
    ctx.append(
        (
            label,
            f"RunPlugin({build_url({'mode': 'toggle_movie_watched', 'movie_id': movie_id, 'profile_num': profile_num})})",
        )
    )
    return ctx


def _watched_ctx_series(series_id, profile_num=None, we=None):
    ctx = []
    if we is None:
        we = WatchedEpisodes(addon, profile_num=profile_num)
    has_any = we.get_watched_count(series_id) > 0
    label = _t(30806) if has_any else _t(30805)
    ctx.append(
        (
            label,
            f"RunPlugin({build_url({'mode': 'toggle_series_watched', 'series_id': series_id, 'profile_num': profile_num})})",
        )
    )
    return ctx


def _watched_ctx_season(series_id, season_num, total_eps, profile_num=None):
    ctx = []
    we = WatchedEpisodes(addon, profile_num=profile_num)
    fully = we.is_season_fully_watched(series_id, season_num, total_eps)
    has_any = we.get_watched_count(series_id, season_num) > 0
    label = _t(30806) if (fully or has_any) else _t(30805)
    ctx.append(
        (
            label,
            f"RunPlugin({build_url({'mode': 'toggle_season_watched', 'series_id': series_id, 'season_num': season_num, 'profile_num': profile_num})})",
        )
    )
    return ctx


def _watched_ctx_episode(series_id, season_num, episode_id, profile_num=None):
    ctx = []
    we = WatchedEpisodes(addon, profile_num=profile_num)
    label = _t(30806) if we.is_watched(series_id, season_num, episode_id) else _t(30805)
    ctx.append(
        (
            label,
            f"RunPlugin({build_url({'mode': 'toggle_episode_watched', 'series_id': series_id, 'season_num': season_num, 'episode_id': episode_id, 'profile_num': profile_num})})",
        )
    )
    return ctx


def _is_adult_category(name):
    # Adult keywords with word boundaries to reduce false positives
    adult_patterns = [
        r"\bxxx\b",
        r"\badult\b",
        r"\bmature\b",
        r"\bporn\b",
        r"\berotic\b",
        r"\berotica\b",
        r"\bnsfw\b",
        r"\bx-rated\b",
        r"\bxrated\b",
        r"\bplayboy\b",
        r"\bhustler\b",
        r"\bpenthouse\b",
        r"\bbrazzers\b",
        r"\bnaughty\b",
        r"\bsexy\b",
        r"\bsex\b",
        r"\bhentai\b",
        r"\bstriptease\b",
        r"\bfetish\b",
        r"\bnude\b",
        r"\bnaked\b",
        r"\borgasm\b",
        r"\bkamasutra\b",
        r"\bmilf\b",
        r"\blesbian\b",
        r"\bgay\b",
        r"\bhardcore\b",
        r"\bsoftcore\b",
        r"\btopless\b",
        r"\buncensored\b",
        r"\buncut\b",
        r"\bvoyeur\b",
        r"\bswinger\b",
        r"\bredlight\b",
        r"\bred light\b",
        r"\bblue film\b",
        r"\bhot club\b",
        r"\bnight show\b",
        r"\bfor adults\b",
        r"\b18\+",
        r"\(\s*18\+\s*\)",
        r"\[\s*18\+\s*\]",
    ]
    lower = name.lower()
    return any(re.search(p, lower) for p in adult_patterns)


def _hash_pin(pin):
    """Hash PIN with SHA-256 and addon-id salt for secure storage."""

    salt = addon.getAddonInfo("id") or "plugin.video.xstream-player"
    return hashlib.sha256((pin + salt).encode("utf-8")).hexdigest()


def _check_pin(required_for=""):
    if addon.getSetting("enable_parental_control").lower() != "true":
        return True
    # Check per-area toggles
    area_map = {
        "Settings": "parental_lock_settings",
        "Tools": "parental_lock_tools",
    }
    setting_key = area_map.get(required_for)
    if setting_key and addon.getSetting(setting_key).lower() != "true":
        return True
    stored_pin = addon.getSetting("parental_pin") or "0000"
    kb = xbmcgui.Dialog().input(
        _t(30032).format(required_for),
        type=xbmcgui.INPUT_ALPHANUM,
        option=xbmcgui.ALPHANUM_HIDE_INPUT,
    )
    # Migration: if stored PIN is plaintext (4 digits), hash the input and compare
    # If already hashed (64 hex chars), hash input and compare hashes
    if len(stored_pin) == 4 and stored_pin.isdigit():
        # Plaintext legacy PIN - compare directly, then migrate to hashed
        if kb != stored_pin:
            xbmcgui.Dialog().notification("XStream Player", _t(30061))
            return False
        # Migrate to hashed storage
        addon.setSetting("parental_pin", _hash_pin(stored_pin))
        return True
    else:
        # Hashed PIN - compare hashes
        if _hash_pin(kb) != stored_pin:
            xbmcgui.Dialog().notification("XStream Player", _t(30061))
            return False
        return True


def _pvr_has_data():
    """Check if PVR already has channels loaded via JSON-RPC."""
    try:
        resp = xbmc.executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "PVR.GetChannels",
                    "params": {
                        "channelgroupid": "alltv",
                        "properties": ["channelnumber"],
                    },
                    "id": 1,
                }
            )
        )
        result = json.loads(resp).get("result", {})
        channels = result.get("channels", [])
        has_channels = len(channels) > 0
        _log(f"PVR data check: {len(channels)} channels loaded")
        return has_channels
    except Exception as e:
        _log(f"PVR data check error: {e}")
        return False


def _check_auto_refresh():
    creds = _get_credentials()
    if not creds.get("xtream_url") and not creds.get("m3u_url"):
        return
    # Don't auto-refresh on first credentials entry (let user manually refresh)
    flag_file = os.path.join(
        xbmcvfs.translatePath(addon.getAddonInfo("profile")), "credentials_saved"
    )
    if not os.path.exists(flag_file):
        return  # First run, user will manually refresh via prompt
    rt = RefreshTracker(addon)
    if rt.should_refresh():
        # Skip if PVR already has data loaded
        if _pvr_has_data():
            _log("PVR already has channels loaded, skipping auto-refresh")
            rt.set_last_refresh()
            return
        _log("Auto-refresh triggered")
        refresh_data()


def _check_credentials_refresh_prompt():
    """Silent fallback: set credentials flag without prompting.

    The main prompt now happens immediately in settings() after credential
    changes, so this startup check only prevents the flag from staying unset.
    """
    creds = _get_credentials()
    has_creds = bool(creds.get("xtream_url") or creds.get("m3u_url"))

    flag_file = os.path.join(
        xbmcvfs.translatePath(addon.getAddonInfo("profile")), "credentials_saved"
    )

    if has_creds and not os.path.exists(flag_file):
        # Silent fallback: credential prompt now happens immediately in settings()
        # after credential changes. This startup check only prevents the flag
        # from staying unset if settings() was bypassed or crashed.
        with open(flag_file, "w", encoding="utf-8") as f:
            f.write("1")
        _log("credentials_saved flag set silently (prompt handled in settings)")
        return True
    return False


def _check_pvr_startup_retry():
    """Offer PVR sync at startup if user previously declined it.

    The deferred restore flag (pvr_sync_after_profile_load.flag) is NOT handled
    here — it is processed by _prompt_sync_pvr_if_needed() after the PVR-linked
    profile is actually loaded. This prevents a premature "Sync PVR?" dialog
    during the addon reload that follows restore.
    """
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    retry_flag = os.path.join(profile_path, "pvr_sync_retry_needed.flag")
    defer_flag = os.path.join(profile_path, "pvr_sync_after_profile_load.flag")

    # Deferred restore sync: do NOT show dialog here. The prompt will appear
    # after the PVR-linked profile is loaded via _prompt_sync_pvr_if_needed().
    if os.path.exists(defer_flag):
        _log("PVR sync deferred - will prompt after PVR-linked profile is loaded")
        return

    if not os.path.exists(retry_flag):
        return

    # Check if PVR already has data (no point retrying if already loaded)
    try:
        pvr_path = _pvr_m3u_path()
        if os.path.exists(pvr_path) and os.path.getsize(pvr_path) > 0:
            os.remove(retry_flag)
            _log("PVR retry flag cleared — PVR already has data")
            return
    except Exception as e:
        _log(f"PVR retry check warning: {e}")

    if not is_pvr_iptvsimple_installed():
        return

    try:
        creds = _get_pvr_credentials()
        if not (creds.get("xtream_url") or creds.get("m3u_url")):
            return

        dialog = xbmcgui.Dialog()
        if dialog.yesno("XStream Player", _t(30866)):
            try:
                _sync_pvr_force()
                os.remove(retry_flag)
                _log("PVR sync completed via startup retry")
            except Exception as e:
                _log(f"PVR startup retry sync warning: {e}")
        else:
            # User declined again — keep retry flag for next startup
            _log("PVR startup retry declined by user")
    except Exception as e:
        _log(f"PVR startup retry warning: {e}")


def _is_first_refresh():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    return not os.path.exists(os.path.join(profile, "first_refresh_done"))


def _mark_first_refresh_done():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    with open(os.path.join(profile, "first_refresh_done"), "w", encoding="utf-8") as f:
        f.write("1")


def refresh_profile_menu():
    """Show menu to select which profile(s) to refresh with progress dialog."""
    try:
        dialog = xbmcgui.Dialog()

        # Build list of enabled profiles
        profiles = []
        for i in range(1, 11):
            if addon.getSetting(f"profile_{i}_enabled") == "true":
                name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
                profiles.append((i, name))

        if not profiles:
            dialog.notification(_t(30770), _t(30074))
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return

        # Build menu items
        items = [(_t(30736), "all")]  # Refresh All Enabled Profiles
        for num, name in profiles:
            label = (
                f"Profile {num} - {name}"
                if name != _t(30390, num)
                else f"Profile {num}"
            )
            items.append((label, num))

        idx = dialog.select(_t(30012), [i[0] for i in items])
        if idx < 0:
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return

        selected = items[idx][1]

        if selected == "all":
            # Refresh all enabled profiles with progress
            _refresh_all_profiles_with_progress(profiles)
        else:
            # Refresh single profile with progress
            _refresh_profile_data(selected)

        xbmc.executebuiltin("Container.Refresh")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
    except Exception as e:
        _log(f"refresh_profile_menu error: {e}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def _refresh_all_profiles_with_progress(profiles):
    """Refresh all profiles with overall progress dialog."""
    if not _acquire_pvr_sync_lock():
        return
    total_profiles = len(profiles)
    if total_profiles == 0:
        _release_pvr_sync_lock()
        return

    progress = xbmcgui.DialogProgress()
    progress.create(_t(30012), _t(30736))  # Refreshing All Profiles

    try:
        for idx, (num, name) in enumerate(profiles):
            if progress.iscanceled():
                break

            # Calculate overall progress
            overall_pct = int((idx / total_profiles) * 100)
            progress.update(
                overall_pct, f"{_t(30749, name)}  {_t(30758, idx + 1, total_profiles)}"
            )

            # Refresh this profile (without showing its own progress dialog)
            _refresh_single_profile_silent(num)

        progress.update(100, _t(30080))
        xbmc.sleep(500)
        progress.close()
        xbmcgui.Dialog().notification("XStream Player", _t(30080))

    except Exception as e:
        progress.close()
        _log(f"Refresh all error: {e}")
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30074), xbmcgui.NOTIFICATION_ERROR
        )
    finally:
        _release_pvr_sync_lock()


def _refresh_single_profile_silent(profile_num):
    """Refresh data for a specific profile without progress dialog (for batch operations)."""
    original_active = pm.active
    pm.active = str(profile_num)

    try:
        _purge_profile_data(profile_num)
        creds = pm.get_credentials()
        xt_url = creds.get("xtream_url", "")
        xt_user = creds.get("xtream_username", "")
        xt_pwd = creds.get("xtream_password", "")
        m3u_url = creds.get("m3u_url", "")
        steps, load_live = _build_fetch_steps(xt_url, xt_user, xt_pwd, m3u_url)
        if load_live:
            steps.append((_t(30357), lambda: EPG(addon).fetch()))
        for label, fn in steps:
            try:
                fn()
            except Exception as e:
                _log(f"Silent refresh error {label}: {e}")
        _log(f"Silently refreshed profile {profile_num}")
    finally:
        pm.active = original_active


def _refresh_profile_data(profile_num):
    """Refresh data for a specific profile with progress bar."""
    profile_name = addon.getSetting(f"profile_{profile_num}_name") or _t(
        30390, profile_num
    )
    progress = xbmcgui.DialogProgress()
    progress.create(_t(30012), _t(30749, profile_name))
    original_active = pm.active
    pm.active = str(profile_num)

    try:
        progress.update(10, _t(30750))
        _purge_profile_data(profile_num)

        creds = pm.get_credentials()
        xt_url = creds.get("xtream_url", "")
        xt_user = creds.get("xtream_username", "")
        xt_pwd = creds.get("xtream_password", "")
        m3u_url = creds.get("m3u_url", "")
        steps, load_live = _build_fetch_steps(xt_url, xt_user, xt_pwd, m3u_url)
        if load_live:
            steps.append((_t(30357), lambda: EPG(addon).fetch()))

        total = len(steps)
        for idx, (label, fn) in enumerate(steps):
            if progress.iscanceled():
                break
            percent = 25 + int(((idx + 1) / total) * 70) if total else 50
            progress.update(percent, label)
            try:
                fn()
            except Exception as e:
                _log(f"Refresh error {label}: {e}")

        progress.update(100, _t(30080))
        xbmc.sleep(500)
        xbmcgui.Dialog().notification("XStream Player", _t(30080))
    except Exception as e:
        _log(f"Refresh profile data error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30081), xbmcgui.NOTIFICATION_ERROR
        )
    finally:
        try:
            progress.close()
        except Exception as e:
            _log(f"PVR favorites progress close warning: {e}")
        pm.active = original_active


def _refresh_profiles_batch(profile_nums):
    """Load multiple profiles under a single progress dialog.

    Used after restore to avoid showing multiple 'Refresh' dialogs.
    """
    if not profile_nums:
        return []

    total_profiles = len(profile_nums)
    progress = xbmcgui.DialogProgress()
    progress.create("XStream Player", f"Loading {total_profiles} profile(s)...")
    loaded = []

    try:
        for p_idx, profile_num in enumerate(profile_nums):
            profile_name = addon.getSetting(f"profile_{profile_num}_name") or _t(
                30390, profile_num
            )
            overall_pct = int((p_idx / total_profiles) * 100)
            progress.update(
                overall_pct,
                f"Loading profile {p_idx + 1} of {total_profiles}: {profile_name}",
            )

            try:
                original_active = pm.active
                pm.active = str(profile_num)
                try:
                    _purge_profile_data(profile_num)
                    creds = pm.get_credentials()
                    xt_url = creds.get("xtream_url", "")
                    xt_user = creds.get("xtream_username", "")
                    xt_pwd = creds.get("xtream_password", "")
                    m3u_url = creds.get("m3u_url", "")
                    steps, load_live = _build_fetch_steps(
                        xt_url, xt_user, xt_pwd, m3u_url
                    )
                    if load_live:
                        steps.append((_t(30357), lambda: EPG(addon).fetch()))

                    for label, fn in steps:
                        if progress.iscanceled():
                            break
                        try:
                            fn()
                        except Exception as e:
                            _log(f"Batch load error {label}: {e}")

                    loaded.append(profile_num)
                    _log(f"Batch loaded profile {profile_num}")
                finally:
                    pm.active = original_active
            except Exception as e:
                _log(f"Batch profile {profile_num} error: {e}")

            if progress.iscanceled():
                break

        progress.update(100, "Loading complete")
        xbmc.sleep(300)
    finally:
        try:
            progress.close()
        except Exception:
            pass

    return loaded


def refresh_data():
    # Confirmation prompt with warning
    choice = xbmcgui.Dialog().yesno(
        "XStream Player",
        _t(30050) + "\n\n" + _t(30051),
        yeslabel=_t(30167),
        nolabel=_t(30161),
    )
    if not choice:
        return False

    if not _acquire_pvr_sync_lock():
        return False
    try:
        first_time = _is_first_refresh()
        clear_cache = addon.getSetting("clear_cache_on_refresh").lower() == "true"
        pd = xbmcgui.DialogProgress()
        pd.create("XStream Player", _t(30285) if clear_cache else _t(30286))
        count = _cache_clear_profile(int(pm.active))
        if clear_cache:
            profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
            for fname in os.listdir(profile_path):
                if (
                    fname.startswith("epg_cache_profile_")
                    or fname == "epg_cache.json"
                    or fname == "view_prefs.json"
                    or fname.startswith("data_cache_epg")
                    or fname.startswith("data_cache_tmdb_")
                    or fname.startswith("tmdb_")
                ):
                    try:
                        os.remove(os.path.join(profile_path, fname))
                        count += 1
                    except Exception as e:
                        _log(f"Cache remove warning: {e}")
            _log(f"Cleared {count} cache files (all caches)")
        else:
            _log(f"Cleared {count} data cache files")
        rt = RefreshTracker(addon)
        rt.set_last_refresh()
        pd.update(30, _t(30562))
        _prefetch_all_data()
        pd.update(100, _t(30563))
        pd.close()
        if first_time:
            _mark_first_refresh_done()
        choice = xbmcgui.Dialog().yesno(
            "XStream Player", _t(30052), yeslabel=_t(30165), nolabel=_t(30164)
        )
        if choice:
            _restart_or_prompt()
            return
        xbmc.executebuiltin("Container.Refresh")
    finally:
        _release_pvr_sync_lock()


def sync_pvr():
    if not is_pvr_iptvsimple_installed():
        prompt_install_pvr()
        return
    pd = xbmcgui.DialogProgress()
    pd.create("XStream Player", _t(30287))
    ok = False
    try:
        ok = _sync_pvr_force()
    except Exception as e:
        _log(f"PVR sync error: {e}")
    pd.close()
    if ok:
        xbmcgui.Dialog().notification("XStream Player", _t(30081))
    else:
        xbmcgui.Dialog().notification("XStream Player", _t(30082))


def open_pvr():
    xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
    xbmc.executebuiltin("ActivateWindow(TVChannels)")


def open_pvr_guide():
    xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
    xbmc.executebuiltin("ActivateWindow(TVGuide)")


def _get_pvr_profile_num():
    """Get the profile number (1-10) of the active PVR profile."""
    raw = addon.getSetting("active_pvr_profile") or "Profile 1"
    match = re.search(r"(\d+)$", raw)
    return match.group(1) if match else "1"


def _pvr_favs_path():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    pvr_profile = _get_pvr_profile_num()
    return os.path.join(profile, f"pvr_favorites_{pvr_profile}.json")


def _pvr_favs_load_all():
    """Load all PVR favorite groups. Returns dict of {group_name: [channels]}."""
    try:
        with open(_pvr_favs_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    # Migration: old format was a flat list
    if isinstance(data, list):
        if data:
            return {"Favorites": data}
        return {}
    return data


def _pvr_favs_save_all(groups):
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        os.makedirs(profile)
    favs_path = _pvr_favs_path()
    tmp_file = favs_path + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, favs_path)


def _pvr_favs_load(group=None):
    """Load channels from a specific group, or all channels flat."""
    groups = _pvr_favs_load_all()
    if group:
        return groups.get(group, [])
    # All channels flat
    all_items = []
    for items in groups.values():
        all_items.extend(items)
    return all_items


def _pvr_favs_save(items, group=None):
    """Save channels to a specific group."""
    if group is None:
        group = _t(30703) or "Favorites"
    groups = _pvr_favs_load_all()
    groups[group] = items
    _pvr_favs_save_all(groups)


def _pvr_favs_add(channel, group=None):
    if group is None:
        group = _t(30703) or "Favorites"
    items = _pvr_favs_load(group)
    sid = str(channel.get("stream_id", "") or channel.get("id", ""))
    if any(str(i.get("stream_id", "")) == sid for i in items):
        return False
    items.append(channel)
    _pvr_favs_save(items, group)
    return True


def _pvr_favs_remove(stream_id, group=None):
    if group is None:
        group = _t(30703) or "Favorites"
    items = _pvr_favs_load(group)
    sid = str(stream_id)
    new_items = [i for i in items if str(i.get("stream_id", "")) != sid]
    if len(new_items) != len(items):
        _pvr_favs_save(new_items, group)
        return True
    return False


def _pvr_favs_is_fav(stream_id):
    sid = str(stream_id)
    return any(str(i.get("stream_id", "")) == sid for i in _pvr_favs_load())


def _pvr_favs_m3u_path():
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    pvr_profile = _get_pvr_profile_num()
    return os.path.join(profile, f"pvr_favorites_{pvr_profile}.m3u8")


def _export_pvr_favs_m3u():
    """Export all PVR favorite groups to M3U for the second PVR instance."""
    groups = _pvr_favs_load_all()
    creds = _get_pvr_credentials()
    xt_url = creds.get("xtream_url", "")
    xt_user = creds.get("xtream_username", "")
    xt_pwd = creds.get("xtream_password", "")
    hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"
    channels = []
    for gname, items in groups.items():
        for ch in items:
            name = ch.get("name", "Unknown")
            if hide_adult and _is_adult_category(name):
                continue
            icon = ch.get("stream_icon", "") or ch.get("icon", "")
            sid = str(ch.get("stream_id", ""))
            epg_id = ch.get("epg_channel_id") or sid
            catchup = ""
            catchup_source = ""
            catchup_days = ""
            url = ""
            if xt_url and xt_user and xt_pwd and sid:
                url = f"{xt_url}/live/{xt_user}/{xt_pwd}/{sid}.ts"
                # Only apply catchup if the original channel data indicated support
                has_catchup = bool(
                    ch.get("tv_archive")
                    or ch.get("catchup")
                    or ch.get("catchup_source")
                    or ch.get("catchup_days")
                )
                if has_catchup:
                    catchup = "default"
                    catchup_source = f"{xt_url}/live/{xt_user}/{xt_pwd}/{sid}.ts?utc={{utc}}&lutc={{lutc}}"
                    catchup_days = str(ch.get("tv_archive_duration") or ch.get("catchup_days") or "7")
            elif ch.get("url"):
                url = ch.get("url").split("|")[0]  # strip any existing pipe params
                catchup = ch.get("catchup", "")
                catchup_source = ch.get("catchup_source", "")
                catchup_days = ch.get("catchup_days", "")
            else:
                continue
            channels.append(
                {
                    "name": name,
                    "url": url,
                    "tvg_id": epg_id,
                    "logo": icon,
                    "group": f"★ Favorites - {gname}",
                    "stream_type": ch.get("stream_type", ""),
                    "radio": ch.get("radio", ""),
                    "catchup": catchup,
                    "catchup_source": catchup_source,
                    "catchup_days": catchup_days,
                }
            )
    m3u_path = _pvr_favs_m3u_path()
    if not channels:
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
        return m3u_path
    m3u_data = build_m3u_content(channels)
    tmp = m3u_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(m3u_data)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, m3u_path)
    return m3u_path


def _configure_pvr_favs_instance():
    """Create/update PVR IPTV Simple Client instance 2 for favorites only."""
    try:
        pvr_profile = xbmcvfs.translatePath(
            "special://profile/addon_data/pvr.iptvsimple"
        )
        if not os.path.exists(pvr_profile):
            os.makedirs(pvr_profile)
        settings_path = os.path.join(pvr_profile, "instance-settings-2.xml")
        m3u_path = _pvr_favs_m3u_path()
        epg_path = _pvr_epg_path()

        _log("PVR Favorites: Configuring instance")
        # PVR EPG refresh interval (convert hours to seconds for IPTV Simple)
        try:
            pvr_epg_hours = int(addon.getSetting("pvr_epg_refresh") or "12")
        except ValueError:
            pvr_epg_hours = 12
        pvr_epg_seconds = pvr_epg_hours * 3600
        _log(
            f"PVR Favorites: Configuring EPG refresh interval to {pvr_epg_hours} hours"
        )
        updates = {
            "kodi_addon_instance_name": "PVR Favorites",
            "kodi_addon_instance_enabled": "true",
            "m3uPathType": "0",
            "m3uPath": m3u_path,
            "m3uUrl": "",
            "epgPathType": "0",
            "epgPath": epg_path,
            "epgUrl": "",
            "epgRefreshInterval": str(pvr_epg_seconds),
            "m3uRefreshMode": "1",
            "logoPathType": "0",
            "logoPath": "",
            "logoBaseUrl": "",
            "catchupEnabled": (
                "true"
                if addon.getSetting("pvr_catchup_enabled").lower() == "true"
                else "false"
            ),
            "catchupPlayEpgAsLive": "false",
            "allChannelsCatchupMode": "0",
            "catchupOverrideMode": "0",
            "catchupDays": addon.getSetting("pvr_catchup_days") or "7",
            "catchupOnlyOnFinishedProgrammes": "false",
            "catchupWatchEpgBeginBufferMins": "5",
            "catchupWatchEpgEndBufferMins": "15",
        }
        if os.path.exists(settings_path):
            tree = ET.parse(settings_path)
            root = tree.getroot()
            changed = False
            stale_keys = {"defaultInputstream", "defaultMimeType"}
            for stale in stale_keys:
                el = root.find(f".//setting[@id='{stale}']")
                if el is not None:
                    root.remove(el)
                    changed = True
                    _log(f"PVR Favorites: Removed stale setting '{stale}'")
            for key, val in updates.items():
                el = root.find(f".//setting[@id='{key}']")
                if el is not None:
                    if (el.text or "") != val:
                        el.text = val
                        if "default" in el.attrib:
                            del el.attrib["default"]
                        changed = True
                else:
                    new_el = ET.SubElement(root, "setting", {"id": key})
                    new_el.text = val
                    changed = True
            if changed:
                tmp_path = settings_path + ".tmp"
                tree.write(tmp_path, encoding="utf-8", xml_declaration=True)
                with open(tmp_path, "r+b") as f:
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                os.replace(tmp_path, settings_path)
        else:
            root = ET.Element("settings", {"version": "2"})
            for key, val in updates.items():
                el = ET.SubElement(root, "setting", {"id": key})
                el.text = val
            tmp_path = settings_path + ".tmp"
            ET.ElementTree(root).write(tmp_path, encoding="utf-8", xml_declaration=True)
            with open(tmp_path, "r+b") as f:
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp_path, settings_path)
        _log("Configured PVR Favorites instance (instance-settings-2.xml)")

        return True
    except Exception as e:
        _log(f"Configure PVR Favorites instance failed: {e}")
        _log(f"Traceback: {traceback.format_exc()}")
        return False


def _is_pvr_iptvsimple_enabled():
    """Check if pvr.iptvsimple is currently enabled via JSON-RPC."""
    try:
        resp = json.loads(
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","params":{"addonid":"pvr.iptvsimple","properties":["enabled"]},"id":1}'
            )
        )
        return resp.get("result", {}).get("addon", {}).get("enabled", False)
    except Exception as e:
        _log(f"PVR Favorites: Could not check addon state: {e}")
        return True  # assume enabled to stay safe


def _sync_pvr_favorites():
    """Sync PVR favorites M3U and configure the second PVR instance."""
    if addon.getSetting("pvr_favorites_enabled").lower() != "true":
        _log("PVR Favorites: Disabled by user setting, removing PVR instance")
        try:
            pvr_profile = xbmcvfs.translatePath(
                "special://profile/addon_data/pvr.iptvsimple"
            )
            settings_path = os.path.join(pvr_profile, "instance-settings-2.xml")
            if os.path.exists(settings_path):
                # Safely disable pvr.iptvsimple before removing instance-2 config
                # to avoid Epg16.db corruption while the binary addon holds handles.
                try:
                    xbmc.executeJSONRPC(
                        '{"jsonrpc": "2.0", "method": "PVR.Manager.Stop", "id": 1}'
                    )
                    xbmc.sleep(1000)
                except Exception as e:
                    _log(f"PVR Favorites: Manager stop warning: {e}")
                try:
                    xbmc.executeJSONRPC(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "Addons.SetAddonEnabled",
                                "params": {
                                    "addonid": "pvr.iptvsimple",
                                    "enabled": False,
                                },
                            }
                        )
                    )
                    xbmc.sleep(1500)
                except Exception as e:
                    _log(f"PVR Favorites: disable warning: {e}")
                try:
                    os.remove(settings_path)
                    _log("PVR Favorites: Removed instance-settings-2.xml")
                except Exception as e:
                    _log(f"PVR Favorites: Error removing instance-settings-2.xml: {e}")
                finally:
                    try:
                        xbmc.executeJSONRPC(
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "Addons.SetAddonEnabled",
                                    "params": {
                                        "addonid": "pvr.iptvsimple",
                                        "enabled": True,
                                    },
                                }
                            )
                        )
                        xbmc.sleep(1000)
                        xbmc.executeJSONRPC(
                            '{"jsonrpc": "2.0", "method": "PVR.Manager.Start", "id": 1}'
                        )
                        _log("PVR Favorites: Re-enabled pvr.iptvsimple after removal")
                    except Exception as e:
                        _log(f"PVR Favorites: re-enable warning: {e}")
        except Exception as e:
            _log(f"PVR Favorites: Error removing instance: {e}")
        return

    # Lightweight lock to prevent overlapping syncs
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    lock_path = os.path.join(profile, ".pvr_fav_sync.lock")
    try:
        if os.path.exists(lock_path):
            try:
                age = time.time() - os.path.getmtime(lock_path)
                if age < 30:
                    _log("PVR Favorites: Sync already in progress, skipping")
                    return
            except OSError:
                pass
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write("1")
    except Exception as e:
        _log(f"PVR Favorites: Lock write warning: {e}")

    try:
        _export_pvr_favs_m3u()
        # Only rewrite instance-settings-2.xml if missing or points to wrong path.
        # This avoids triggering a PVR reload on every favorites edit while keeping
        # the config correct after a PVR profile switch.
        pvr_profile_dir = xbmcvfs.translatePath(
            "special://profile/addon_data/pvr.iptvsimple"
        )
        settings_path = os.path.join(pvr_profile_dir, "instance-settings-2.xml")
        expected_m3u = _pvr_favs_m3u_path()
        needs_config = True
        json_path = _pvr_favs_path()
        m3u_stale = (
            os.path.exists(json_path)
            and os.path.exists(expected_m3u)
            and os.path.getmtime(json_path) > os.path.getmtime(expected_m3u)
        )
        if os.path.exists(settings_path):
            try:
                tree = ET.parse(settings_path)
                root = tree.getroot()
                el = root.find(".//setting[@id='m3uPath']")
                if (
                    el is not None
                    and (el.text or "") == expected_m3u
                    and os.path.exists(expected_m3u)
                    and not m3u_stale
                ):
                    needs_config = False
                    _log(
                        "PVR Favorites: instance-settings-2.xml already correct, skipping rewrite"
                    )
            except Exception as e:
                _log(f"PVR Favorites: XML read warning: {e}")
        if needs_config:
            _configure_pvr_favs_instance()
    finally:
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception as e:
            _log(f"PVR Favorites: Lock remove warning: {e}")


def _safe_sync_pvr_favorites_startup():
    """Startup wrapper: update PVR favorites only if the instance config is missing
    or points to the wrong PVR profile, to avoid races with Kodi's PVR init."""
    try:
        expected_m3u = _pvr_favs_m3u_path()
        profile_dir = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        sidecar = os.path.join(profile_dir, ".pvr_fav_verified")
        # Fast path: skip XML parse if sidecar confirms we already verified this M3U path
        if os.path.exists(expected_m3u) and os.path.exists(sidecar):
            try:
                with open(sidecar, "r", encoding="utf-8") as f:
                    cached_path = f.read().strip()
                if cached_path == expected_m3u:
                    _log("PVR Favorites: Startup sync skipped, instance-settings-2.xml already correct")
                    return
            except Exception:
                pass  # Sidecar may be missing or corrupt; proceed to full sync
        pvr_profile_dir = xbmcvfs.translatePath(
            "special://profile/addon_data/pvr.iptvsimple"
        )
        settings_path = os.path.join(pvr_profile_dir, "instance-settings-2.xml")
        if os.path.exists(settings_path):
            try:
                tree = ET.parse(settings_path)
                root = tree.getroot()
                el = root.find(".//setting[@id='m3uPath']")
                if (
                    el is not None
                    and (el.text or "") == expected_m3u
                    and os.path.exists(expected_m3u)
                ):
                    # Write sidecar so future invocations skip the XML parse
                    try:
                        with open(sidecar, "w", encoding="utf-8") as f:
                            f.write(expected_m3u)
                    except Exception:
                        pass  # Non-critical cache hint; failure is harmless
                    _log(
                        "PVR Favorites: Startup sync skipped, instance-settings-2.xml already correct"
                    )
                    return
            except Exception as e:
                _log(f"PVR Favorites: Startup XML read warning: {e}")
        _log("PVR Favorites: Startup sync needed (profile switch or missing config)")
    except Exception as e:
        _log(f"PVR Favorites: Startup state check error: {e}")
    _sync_pvr_favorites()


def _sync_pvr_favorites_safe():
    """Wrap _sync_pvr_favorites with PVR stop/disable safety for file writes.

    Required when called during restore or other contexts where pvr.iptvsimple
    may already be enabled and holding SQLite handles (Android safety).
    """
    try:
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.Manager.Stop", "id": 1}')
        xbmc.sleep(1000)
    except Exception as e:
        _log(f"PVR Favorites safe: Manager stop warning: {e}")
    try:
        xbmc.executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "Addons.SetAddonEnabled",
                    "params": {"addonid": "pvr.iptvsimple", "enabled": False},
                }
            )
        )
        xbmc.sleep(1500)
        if sys.platform.startswith("win"):
            xbmc.sleep(2000)
    except Exception as e:
        _log(f"PVR Favorites safe: disable warning: {e}")
    try:
        _sync_pvr_favorites()
    finally:
        try:
            xbmc.executeJSONRPC(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "Addons.SetAddonEnabled",
                        "params": {"addonid": "pvr.iptvsimple", "enabled": True},
                    }
                )
            )
            _log("PVR Favorites safe: Re-enabled pvr.iptvsimple")
            xbmc.sleep(2000)
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "PVR.Manager.Start", "id": 1}'
            )
        except Exception as e:
            _log(f"PVR Favorites safe: re-enable warning: {e}")


def pvr_favorites_manager(group=None):
    """PVR Favorites Manager - groups with channels, similar to Favorites Manager."""
    groups = _pvr_favs_load_all()

    # Level 1: show groups + New Group
    if group is None:
        for gname, items in groups.items():
            count = len(items)
            li = xbmcgui.ListItem(label=_t(30272).format(gname, count))
            li.setArt({"icon": "DefaultFavourites.png"})
            ctx_items = [
                (
                    _t(30320),
                    f"RunPlugin({build_url({'mode': 'pvr_favs_rename_group', 'group': gname})})",
                ),
                (
                    _t(30321),
                    f"RunPlugin({build_url({'mode': 'pvr_favs_delete_group', 'group': gname})})",
                ),
            ]
            li.addContextMenuItems(ctx_items)
            q = {"mode": "pvr_favorites_manager", "group": gname}
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
            )
        # + New PVR Group
        li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30200)))
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({"mode": "pvr_favs_new_group"}),
            listitem=li,
            isFolder=False,
        )
        xbmcplugin.endOfDirectory(addon_handle)
        return

    # Level 2: inside a group - manage button + channels
    items = groups.get(group, [])
    li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30201)))
    li.setArt({"icon": "DefaultAddonService.png"})
    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url=build_url({"mode": "pvr_favs_manage_group", "group": group}),
        listitem=li,
        isFolder=True,
    )

    if not items:
        li = xbmcgui.ListItem(label="[COLOR gray]{0}[/COLOR]".format(_t(30202)))
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url="", listitem=li, isFolder=False
        )
    else:
        creds = _get_pvr_credentials()
        xt_url = creds.get("xtream_url", "")
        xt_user = creds.get("xtream_username", "")
        xt_pwd = creds.get("xtream_password", "")
        for ch in items:
            name = ch.get("name", "Unknown")
            icon = ch.get("stream_icon", "") or ch.get("icon", "")
            sid = str(ch.get("stream_id", ""))
            li = xbmcgui.ListItem(label=name)
            li.setArt({"icon": icon, "thumb": icon})
            ctx_items = [
                (
                    _t(30322),
                    f"RunPlugin({build_url({'mode': 'pvr_fav_remove', 'stream_id': sid, 'group': group})})",
                ),
            ]
            li.addContextMenuItems(ctx_items)
            stream_url = f"{xt_url}/live/{xt_user}/{xt_pwd}/{sid}.ts" if xt_url else ""
            q = {
                "mode": "play_stream",
                "url": stream_url,
                "name": name,
                "icon": icon,
                "stype": "live",
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )

    xbmcplugin.endOfDirectory(addon_handle)


def pvr_favs_manage_group(group):
    """Category browser for adding channels to a specific PVR group."""
    creds = _get_pvr_credentials()
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    if not url:
        xbmcgui.Dialog().notification("XStream Player", _t(30056))
        xbmcplugin.endOfDirectory(addon_handle)
        return
    # Current channels multiselect
    current_count = len(_pvr_favs_load(group))
    li = xbmcgui.ListItem(
        label="[COLOR gold]{0}[/COLOR]".format(_t(30203).format(current_count))
    )
    li.setArt({"icon": "DefaultFavourites.png"})
    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url=build_url({"mode": "pvr_favs_group_current", "group": group}),
        listitem=li,
        isFolder=False,
    )
    # Search
    li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30204)))
    li.setArt({"icon": "DefaultAddonsSearch.png"})
    xbmcplugin.addDirectoryItem(
        handle=addon_handle,
        url=build_url({"mode": "pvr_favs_group_search", "group": group}),
        listitem=li,
        isFolder=False,
    )
    # Categories - filter out hidden (use PVR profile's hidden lists)
    pvr_pnum = _get_pvr_profile_num()
    cats = _get_cached_xtream_categories(url, user, pwd, "live")
    hidden_live = _get_hidden_subcats("live", pvr_pnum)
    for c in cats or []:
        cat_id = str(c.get("category_id", ""))
        if cat_id in hidden_live:
            continue
        cat_name = c.get("category_name", "Unknown")
        li = xbmcgui.ListItem(label=cat_name)
        li.setArt({"icon": "DefaultFolder.png"})
        q = {
            "mode": "pvr_favs_manage_cat",
            "cat_id": cat_id,
            "cat_name": cat_name,
            "group": group,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )
    xbmcplugin.endOfDirectory(addon_handle)


def pvr_favs_group_current(group):
    """Multiselect dialog to keep/remove channels in a PVR group."""
    items = _pvr_favs_load(group)
    if not items:
        xbmcgui.Dialog().notification("XStream Player", _t(30101))
        return
    dialog = xbmcgui.Dialog()
    names = [ch.get("name", "Unknown") for ch in items]
    preselect = list(range(len(items)))
    result = dialog.multiselect(_t(30330, group), names, preselect=preselect)
    if result is None:
        return
    if len(result) == len(items):
        return
    new_favs = [items[i] for i in result]
    _pvr_favs_save(new_favs, group)
    _sync_pvr_favorites()
    removed = len(items) - len(new_favs)
    dialog.notification("XStream Player", _t(30168, removed))
    xbmc.sleep(1500)
    dialog.ok("XStream Player", _t(30727))
    xbmc.executebuiltin("Container.Refresh")


def pvr_favs_group_search(group):
    """Search channels and multiselect to add/remove from a PVR group."""
    dialog = xbmcgui.Dialog()
    query = dialog.input(_t(30146))
    if not query:
        return
    creds = _get_pvr_credentials()
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    streams = _get_cached_xtream_streams(url, user, pwd, "live")
    pvr_pnum = _get_pvr_profile_num()
    hidden_live = _get_hidden_subcats("live", pvr_pnum)
    hidden_items = _get_hidden_items("live", pvr_pnum)
    if not streams:
        dialog.notification("XStream Player", _t(30067))
        return
    query_lower = query.lower()
    filtered = [
        s
        for s in streams
        if query_lower in s.get("name", "").lower()
        and str(s.get("category_id", "")) not in hidden_live
        and str(s.get("stream_id", "")) not in hidden_items
    ]
    if not filtered:
        dialog.notification("XStream Player", _t(30067))
        return
    _pvr_favs_multiselect(filtered, dialog, group)


def pvr_favs_manage_cat(cat_id, cat_name, group):
    """Pick a category: add entire or multiselect individual channels for a PVR group."""
    dialog = xbmcgui.Dialog()
    action = dialog.select(cat_name, [_t(30331, group), _t(30332)])
    if action < 0:
        return
    creds = _get_pvr_credentials()
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    streams = _get_cached_xtream_streams(url, user, pwd, "live")
    pvr_pnum = _get_pvr_profile_num()
    hidden_items = _get_hidden_items("live", pvr_pnum)
    filtered = [
        s
        for s in (streams or [])
        if str(s.get("category_id", "")) == cat_id
        and str(s.get("stream_id", "")) not in hidden_items
    ]
    if not filtered:
        dialog.notification("XStream Player", _t(30068))
        return
    if action == 0:
        current_favs = _pvr_favs_load(group)
        fav_ids = {str(i.get("stream_id", "")) for i in current_favs}
        added = 0
        for s in filtered:
            if str(s.get("stream_id", "")) not in fav_ids:
                current_favs.append(s)
                added += 1
        _pvr_favs_save(current_favs, group)
        _sync_pvr_favorites()
        dialog.notification("XStream Player", _t(30169, added))
        xbmc.sleep(1500)
        dialog.ok("XStream Player", _t(30727))
        xbmc.executebuiltin("Container.Refresh")
        return
    _pvr_favs_multiselect(filtered, dialog, group)


def _pvr_favs_multiselect(filtered, dialog, group=None):
    """Multiselect channels to add/remove from a PVR group."""
    if group is None:
        group = _t(30703) or "Favorites"
    names = [s.get("name", "Unknown") for s in filtered]
    current_favs = _pvr_favs_load(group)
    fav_ids = {str(i.get("stream_id", "")) for i in current_favs}
    preselect = [
        i for i, s in enumerate(filtered) if str(s.get("stream_id", "")) in fav_ids
    ]
    result = dialog.multiselect(_t(30151, group), names, preselect=preselect)
    if result is None:
        return
    filtered_ids = {str(s.get("stream_id", "")) for s in filtered}
    new_favs = [
        f for f in current_favs if str(f.get("stream_id", "")) not in filtered_ids
    ]
    for i in result or []:
        new_favs.append(filtered[i])
    _pvr_favs_save(new_favs, group)
    _sync_pvr_favorites()
    dialog.notification("XStream Player", _t(30170, len(new_favs), group))
    xbmc.sleep(1500)
    dialog.ok("XStream Player", _t(30727))
    xbmc.executebuiltin("Container.Refresh")


def _check_account_expiry():
    """Warn if Xtream account expires within 7 days."""
    creds = _get_credentials()
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    if not url or not user or not pwd:
        return
    # Only check once per day using a per-profile flag file
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    flag = os.path.join(profile, f"expiry_checked_p{pm.active}")
    if os.path.exists(flag):
        try:
            age = time.time() - os.path.getmtime(flag)
            if age < 86400:  # check once per day
                return
        except Exception as e:
            _log(f"expiry flag age check warning: {e}")
    try:
        info = IPTV.validate_xtream(url, user, pwd)
        if not info:
            # HTTP/auth failure — don't write the flag, otherwise we'd rate-limit
            # ourselves for 24h after a transient failure.
            return
        if info.get("exp_date"):
            exp_dt = datetime.datetime.fromtimestamp(int(info["exp_date"]))
            days_left = (exp_dt - datetime.datetime.now()).days
            if days_left < 7:
                xbmcgui.Dialog().notification(
                    "XStream Player",
                    _t(30300, days_left),
                    xbmcgui.NOTIFICATION_WARNING,
                    5000,
                )
        try:
            with open(flag, "w", encoding="utf-8") as f:
                f.write("1")
        except Exception as e:
            _log(f"expiry flag write failed: {e}")
    except Exception as e:
        _log(f"account expiry check failed: {e}")


# Per-invocation parse cache for settings.xml. Same plugin invocation may call
# _get_setting_direct() many times across menu builders; reparsing the XML on
# every call is wasteful. We key on (path, mtime) so any external write is seen.
_settings_xml_cache = {"path": None, "mtime": 0, "values": None}


def _get_setting_direct(setting_id, default=""):
    """Read setting directly from settings.xml to bypass Kodi's cache."""
    try:
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        settings_path = os.path.join(profile, "settings.xml")
        if os.path.exists(settings_path):
            mtime = os.path.getmtime(settings_path)
            cache = _settings_xml_cache
            if (
                cache["path"] != settings_path
                or cache["mtime"] != mtime
                or cache["values"] is None
            ):
                import xml.etree.ElementTree as ET

                tree = ET.parse(settings_path)
                root = tree.getroot()
                values = {}
                for setting in root.findall("setting"):
                    sid = setting.get("id")
                    if sid:
                        values[sid] = setting.text or ""
                cache["path"] = settings_path
                cache["mtime"] = mtime
                cache["values"] = values
            if setting_id in cache["values"]:
                return cache["values"][setting_id] or default
    except Exception as e:
        xbmc.log(f"[XStream Player] Settings XML read error: {e}", xbmc.LOGWARNING)
    return addon.getSetting(setting_id) or default


def _get_addon_group_items():
    """Get menu items for enabled addon groups"""
    items = []
    ag_visible = set(_get_ag_visible())

    for i in range(1, 6):
        if _get_setting_direct(f"ag_{i}_enabled", "false") != "true":
            continue
        # Check if this specific group is visible (if ag_visible is set)
        if ag_visible and f"ag_{i}" not in ag_visible:
            continue

        group_name = _get_setting_direct(f"ag_{i}_name", _t(30391, i))
        group_addons = _get_group_addons(i)

        # Empty group - show message item
        if not group_addons:
            items.append(
                (
                    "[COLOR gray]{0} {1}[/COLOR]".format(group_name, _t(30196)),
                    {"mode": "empty_addon_group", "group": str(i)},
                    "DefaultAddonsInstalled.png",
                    True,
                )
            )
            continue

        # Single addon - open directly; Multiple - show list
        # Always use ag_{i} as key for consistency in reordering
        if len(group_addons) == 1:
            items.append(
                (
                    group_name,
                    {
                        "mode": "open_addon",
                        "addon_id": group_addons[0]["id"],
                        "group": str(i),
                    },
                    "DefaultAddonsInstalled.png",
                    False,
                )
            )
        else:
            items.append(
                (
                    group_name,
                    {"mode": "open_addon_group", "group": str(i)},
                    "DefaultAddonsInstalled.png",
                    True,
                )
            )
    return items


def empty_addon_group(group_num):
    """Show empty group message with option to open settings."""
    group_name = _get_setting_direct(f"ag_{group_num}_name", _t(30391, group_num))
    dialog = xbmcgui.Dialog()
    choice = dialog.yesno(group_name, _t(30564), yeslabel=_t(30183), nolabel=_t(30164))
    if choice:
        addon.openSettings()
    # Always end directory properly
    xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def _get_addon_data_path():
    """Get addon data path (shared across profiles)"""
    return xbmcvfs.translatePath(addon.getAddonInfo("profile"))


# v1.1.5 → v2.0 compatibility: addon group file migration
# Addon groups (ag_*) moved from install dir to profile dir to survive updates.
# Gated by file existence — runs once per file, then never again.
def _migrate_ag_files():
    install_path = xbmcvfs.translatePath(addon.getAddonInfo("path"))
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if install_path == profile_path:
        return
    try:
        if not os.path.isdir(install_path) or not os.path.isdir(profile_path):
            return
        for fname in os.listdir(install_path):
            if fname.startswith("ag_") and fname.endswith(".json"):
                src = os.path.join(install_path, fname)
                dst = os.path.join(profile_path, fname)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    _log(f"Migrated addon group file to profile dir: {fname}")
    except Exception as e:
        _log(f"ag_ migration warning: {e}")


def _get_group_addons(group_num):
    """Get list of addons saved for a group (persists across profiles)"""
    data_path = _get_addon_data_path()
    try:
        with open(
            os.path.join(data_path, f"ag_{group_num}_addons.json"),
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _save_group_addons(group_num, addons_list):
    """Save list of addons for a group (persists across profiles)"""
    data_path = _get_addon_data_path()
    addons_file = os.path.join(data_path, f"ag_{group_num}_addons.json")
    tmp_file = addons_file + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(addons_list, f)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, addons_file)


def select_ag_addons(group):
    """Show multiselect dialog to choose addons for a group"""
    dialog = xbmcgui.Dialog()

    # Get all installed addons (no type filter so every addon is selectable)
    all_addons = []
    try:
        resp = xbmc.executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "Addons.GetAddons",
                    "params": {
                        "installed": True,
                        "properties": ["name"],
                    },
                    "id": 1,
                }
            )
        )
        all_addons = json.loads(resp).get("result", {}).get("addons", [])
    except Exception as e:
        _log(f"Addons.GetAddons warning: {e}")

    # Exclude self
    all_addons = [
        a for a in all_addons if a.get("addonid") != "plugin.video.xstream-player"
    ]

    if not all_addons:
        dialog.notification("XStream Player", _t(30069))
        return

    # Sort by name
    all_addons.sort(key=lambda x: x.get("name", "").lower())

    # Get currently saved addons
    saved = _get_group_addons(group)
    saved_ids = {a["id"] for a in saved}

    # Build list for dialog
    names = [a.get("name", "Unknown") for a in all_addons]
    preselect = [i for i, a in enumerate(all_addons) if a.get("addonid") in saved_ids]

    result = dialog.multiselect(_t(30171), names, preselect=preselect)
    if result is None:
        return

    selected = [
        {"id": all_addons[i]["addonid"], "name": all_addons[i]["name"]} for i in result
    ]
    _save_group_addons(group, selected)
    dialog.notification("XStream Player", _t(30259, len(selected)))
    xbmc.sleep(1000)
    dialog.notification("XStream Player", _t(30070), xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.executebuiltin("Container.Refresh")


def open_addon_group(group):
    """Show submenu with addons in a group, or open directly if only 1 addon"""
    group = int(group)
    group_name = addon.getSetting(f"ag_{group}_name") or _t(30391, group)
    addons = _get_group_addons(group)

    if not addons:
        xbmcgui.Dialog().notification("XStream Player", _t(30102))
        xbmcplugin.endOfDirectory(addon_handle)
        return

    # Show list of addons in group
    for a in addons:
        addon_id = a["id"]
        addon_name = a["name"]
        li = xbmcgui.ListItem(label=addon_name)
        li.setArt({"icon": "DefaultAddonsInstalled.png"})
        # Pass group so we know to return to group list
        q = {"mode": "open_addon", "addon_id": addon_id, "group": str(group)}
        # isFolder=False because we launch the addon directly
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )

    xbmcplugin.endOfDirectory(addon_handle)


def open_addon(addon_id, group=None):
    """Launch an addon - user can return via back button"""
    # Validate addon_id format to prevent injection (standard Kodi addon ID pattern)
    if not addon_id or not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", str(addon_id)):
        _log(f"Invalid addon_id format: {addon_id}")
        return
    if group:
        # Called from group - return to group when backing out
        xbmc.executebuiltin(f"Container.Update(plugin://{addon_id})")
    else:
        # Single addon - return to main menu when backing out
        xbmc.executebuiltin(f"Container.Update(plugin://{addon_id})")


def _run_startup_checks():
    """Run startup checks in background thread. Called from main_menu()."""
    _log("Running startup checks")
    _migrate_ag_files()
    # v1.1.5 → v2.0 compatibility: profile default migration
    # One-time per install. Enables credentialed profiles, disables empty ones,
    # infers source_type, and maps legacy active_profile to active_pvr_profile.
    if addon.getSetting("profile_defaults_migrated_v200d") != "true":
        try:
            changed_any = False
            for n in range(1, 11):
                has_xtream = bool(addon.getSetting(f"profile_{n}_xtream_url"))
                has_m3u = bool(addon.getSetting(f"profile_{n}_m3u"))
                if has_xtream or has_m3u:
                    if addon.getSetting(f"profile_{n}_enabled") != "true":
                        addon.setSetting(f"profile_{n}_enabled", "true")
                        changed_any = True
                        _log(f"Migrated profile {n} to enabled (has credentials)")
                else:
                    if addon.getSetting(f"profile_{n}_enabled") == "true":
                        addon.setSetting(f"profile_{n}_enabled", "false")
                        changed_any = True
                        _log(f"Migrated profile {n} to disabled (no credentials)")
                source_type = addon.getSetting(f"profile_{n}_source_type")
                if not source_type or source_type == "Xtream Codes":
                    if has_m3u and not has_xtream:
                        addon.setSetting(f"profile_{n}_source_type", "M3U")
                        changed_any = True
                        _log(f"Inferred profile {n} source_type as M3U")
                    elif has_xtream and source_type != "Xtream Codes":
                        addon.setSetting(f"profile_{n}_source_type", "Xtream Codes")
                        changed_any = True
                        _log(f"Inferred profile {n} source_type as Xtream Codes")
            old_active = addon.getSetting("active_profile")
            if old_active:
                match = re.search(r"(\d+)", old_active)
                old_pnum = match.group(1) if match else "1"
                current_pvr = addon.getSetting("active_pvr_profile") or "Profile 1"
                current_match = re.search(r"(\d+)", current_pvr)
                current_pnum = current_match.group(1) if current_match else "1"
                if old_pnum != current_pnum:
                    addon.setSetting("active_pvr_profile", f"Profile {old_pnum}")
                    changed_any = True
                    _log(
                        f"Mapped active_profile {old_active} -> active_pvr_profile: Profile {old_pnum}"
                    )
                profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
                legacy_json = os.path.join(
                    profile_path, f"pvr_favorites_{old_pnum}.json"
                )
                target_json = os.path.join(
                    profile_path, f"pvr_favorites_{current_pnum}.json"
                )
                if os.path.exists(legacy_json) and not os.path.exists(target_json):
                    shutil.copy2(legacy_json, target_json)
                    changed_any = True
                    _log(
                        f"Migrated pvr_favorites_{old_pnum}.json -> pvr_favorites_{current_pnum}.json"
                    )
                legacy_m3u = os.path.join(
                    profile_path, f"pvr_favorites_{old_pnum}.m3u8"
                )
                target_m3u = os.path.join(
                    profile_path, f"pvr_favorites_{current_pnum}.m3u8"
                )
                if os.path.exists(legacy_m3u) and not os.path.exists(target_m3u):
                    shutil.copy2(legacy_m3u, target_m3u)
                    changed_any = True
                    _log(
                        f"Migrated pvr_favorites_{old_pnum}.m3u8 -> pvr_favorites_{current_pnum}.m3u8"
                    )
            addon.setSetting("profile_defaults_migrated_v200d", "true")
            if changed_any:
                _log("Profile default migration completed")
        except Exception as e:
            _log(f"Profile default migration error: {e}")

    # Migrate legacy single sort setting to per-type sort settings (one-time)
    old_sort = addon.getSetting("default_sort_order")
    if old_sort:
        try:
            for key in ("sort_order_live", "sort_order_movie", "sort_order_series"):
                if not addon.getSetting(key):
                    addon.setSetting(key, old_sort)
                    _log(f"Migrated default_sort_order -> {key}: {old_sort}")
            addon.setSetting("default_sort_order", "")
            _log("Cleared legacy default_sort_order after migration")
        except Exception as e:
            _log(f"Sort setting migration warning: {e}")

    addon.setSetting("backup_folder_display", _read_backup_folder())
    try:
        current = addon.getSetting("pvr_favorites_enabled").lower() == "true"
        saved = addon.getSetting("pvr_fav_saved_state")
        if saved != "" and current != (saved.lower() == "true"):
            xbmcgui.Dialog().notification(
                "XStream Player", _t(30729), xbmcgui.NOTIFICATION_INFO, 5000
            )
        addon.setSetting("pvr_fav_saved_state", "true" if current else "false")
    except Exception as e:
        _log(f"PVR favorites state check error: {e}")
    _check_credentials_refresh_prompt()  # Prompt to refresh after first credentials entry

    # Skip auto-refresh if restore just completed — profiles will be loaded anyway
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    defer_flag = os.path.join(profile_path, "pvr_sync_after_profile_load.flag")
    if not os.path.exists(defer_flag):
        _check_auto_refresh()
    else:
        _log("Skipping auto-refresh — restore pending profile load")

    # PVR startup retry: if user declined PVR sync after restore, offer once more
    _check_pvr_startup_retry()

    # Post-restore profile load: if restore just completed, prompt to load profiles
    _prompt_load_profiles_after_restore()

    if addon.getSetting("pvr_reload_on_launch").lower() == "true":
        try:
            resp = json.loads(
                xbmc.executeJSONRPC(
                    '{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","params":{"addonid":"pvr.iptvsimple","properties":["enabled"]},"id":1}'
                )
            )
            enabled = resp.get("result", {}).get("addon", {}).get("enabled", False)
            if not enabled:
                xbmc.executeJSONRPC(
                    '{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"pvr.iptvsimple","enabled":true},"id":1}'
                )
                _log("PVR was disabled, enabled it on launch")
            else:
                _log("PVR already enabled on launch")
        except Exception as e:
            _log(f"PVR load on launch error: {e}")

    # Run network checks in background with pinned profile snapshot.
    _profile_snapshot = pm.active

    def _bg_startup_checks():
        # Pin profile to snapshot to avoid race with main-thread profile switch.
        try:
            if pm.active != _profile_snapshot:
                _log(
                    f"startup checks: profile changed ({_profile_snapshot}->{pm.active}), pinning to snapshot"
                )
                pm.active = _profile_snapshot
        except Exception as e:
            _log(f"startup checks profile pin warning: {e}")
        try:
            try:
                _check_account_expiry()
            except Exception as e:
                _log(f"Account expiry check error: {e}")
            try:
                from updater import silent_check_on_startup

                silent_check_on_startup()
            except Exception as e:
                _log(f"Update check error: {e}")
        finally:
            try:
                if pm.active != _profile_snapshot:
                    pm.active = _profile_snapshot
            except Exception as e:
                _log(f"startup checks profile restore warning: {e}")

    t = threading.Thread(target=_bg_startup_checks, name="XStreamStartupChecks")
    t.daemon = True
    t.start()
    try:
        current_version = addon.getAddonInfo("version")
        addon.setSetting("current_version_display", current_version)
    except Exception as e:
        _log(f"Version display update error: {e}")

    # Show changelog on first launch after update
    try:
        if addon.getSetting("show_changelog_on_update") != "false":
            current_version = addon.getAddonInfo("version")
            last_seen = addon.getSetting("last_seen_version") or "0.0.0"
            if current_version != last_seen:
                changelog_path = os.path.join(
                    xbmcvfs.translatePath(addon.getAddonInfo("path")), "CHANGELOG.md"
                )
                shown = False
                try:
                    with open(changelog_path, "r", encoding="utf-8") as f:
                        changelog = f.read().strip()
                    if changelog:
                        xbmcgui.Dialog().textviewer(
                            _t(30340, current_version), changelog
                        )
                        shown = True
                except Exception as e:
                    _log(f"changelog read error: {e}")
                if shown:
                    addon.setSetting("last_seen_version", current_version)
    except Exception as e:
        _log(f"Changelog display error: {e}")

    # Obsolete: pvr_reload_after_restore.flag prompt removed.
    # Restore now triggers PVR sync immediately via _finalize_restore().


def _show_all_m3u_channels(profile_num, page=1):
    """Show all M3U channels directly without categories (for simple M3U without creds), with pagination."""
    pnum = profile_num
    creds = _get_credentials_for_profile(pnum)
    m3u_url = creds.get("m3u_url", "")

    if not m3u_url:
        return

    channels = _get_cached_m3u_channels(m3u_url)

    hidden_subcats = _get_hidden_subcats("live", pnum)
    hidden_items = _get_hidden_items("live", pnum)
    channels = [
        ch
        for ch in channels
        if (ch.get("group") or "General") not in hidden_subcats
        and str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
        not in hidden_items
    ]

    per_page = _get_pagination_limit("m3u_classic")
    if per_page == 0:
        per_page = len(channels)
    total = len(channels)
    start = (page - 1) * per_page
    end = start + per_page
    page_channels = channels[start:end]

    for ch in page_channels:
        name = ch.get("name", "Unknown")
        url = ch.get("url", "")
        icon = ch.get("logo", "") or "DefaultVideo.png"
        tvg_id = ch.get("tvg_id") or name
        item_id = str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))

        li = xbmcgui.ListItem(label=name)
        li.setArt({"icon": icon})
        li.setInfo("video", {"title": name})
        li.setProperty("IsPlayable", "true")
        li.setProperty("IsLiveTV", "1")
        _prepare_playback_item(li)
        ctx = _build_fav_ctx(
            item_id,
            name,
            "live",
            icon,
            url,
            tvg_id,
            pnum,
            ch.get("catchup", ""),
            ch.get("catchup_source", ""),
            ch.get("catchup_days", ""),
        )
        li.addContextMenuItems(ctx)

        q = {
            "mode": "play_stream",
            "url": url,
            "name": name,
            "icon": icon,
            "profile_num": pnum,
        }
        kodi_props = ch.get("kodi_props") or {}
        stream_ua = ch.get("user_agent", "")
        stream_ref = ch.get("referrer", "")
        if kodi_props:
            import json as _json
            q["kodi_props"] = _json.dumps(kodi_props)
        if stream_ua:
            q["stream_ua"] = stream_ua
        if stream_ref:
            q["stream_ref"] = stream_ref
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )

    if end < total:
        li = xbmcgui.ListItem(
            label="[COLOR yellow]{0} ({1})[/COLOR]".format(_t(30232), page + 1)
        )
        li.setArt({"icon": "DefaultFolder.png"})
        q = {"mode": "m3u_all_channels", "pnum": pnum, "page": page + 1}
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
        )

    xbmcplugin.endOfDirectory(addon_handle)


def profile_menu(pnum):
    """Show sub-menu for a specific profile (TV Classic, Movies, Series, etc)."""
    _log(f"Opening profile menu for profile {pnum}")

    profile_name = addon.getSetting(f"profile_{pnum}_name") or _t(30390, pnum)

    # Temporarily set pm.active for credential loading
    original_active = pm.active
    pm.active = str(pnum)

    try:
        creds = pm.get_credentials()
        load_live = pm.get_profile_setting("load_live") != "false"
        load_movies = pm.get_profile_setting("load_movies") != "false"
        load_series = pm.get_profile_setting("load_series") != "false"
        has_xtream = bool(creds.get("xtream_url"))
        has_m3u_with_creds = bool(creds.get("m3u_url")) and _m3u_has_credentials(
            creds.get("m3u_url")
        )
        has_m3u_simple = bool(creds.get("m3u_url")) and not has_m3u_with_creds
        has_live = (has_xtream or has_m3u_with_creds or has_m3u_simple) and load_live
        has_movies = (has_xtream or has_m3u_with_creds) and load_movies
        has_series = (has_xtream or has_m3u_with_creds) and load_series
        has_replay = (has_xtream or has_m3u_with_creds) and load_live

        # M3U without creds - special layout: Favs, Recent, Search at top, then all channels
        if has_m3u_simple and load_live:
            # Top: Favorites
            li = xbmcgui.ListItem(
                label="[COLOR yellow]{0}[/COLOR]".format(_t(30009))
            )
            li.setArt({"icon": "DefaultFavourites.png"})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle,
                url=build_url({"mode": "profile_favorites_menu", "pnum": pnum}),
                listitem=li,
                isFolder=True,
            )

            # Top: Recently Watched (if has content)
            recent_live = _get_recent_live(pnum)
            if recent_live:
                li = xbmcgui.ListItem(
                    label="[COLOR yellow]{0}[/COLOR]".format(_t(30230))
                )
                li.setArt({"icon": "DefaultAddonPVRClient.png"})
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle,
                    url=build_url(
                        {"mode": "profile_recently_watched", "pnum": pnum}
                    ),
                    listitem=li,
                    isFolder=True,
                )

            # Top: Search
            li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30007)))
            li.setArt({"icon": "DefaultAddonsSearch.png"})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle,
                url=build_url({"mode": "search_global", "profile_num": pnum}),
                listitem=li,
                isFolder=True,
            )

            # Then: All M3U channels directly
            _show_all_m3u_channels(pnum)
            return

        # Xtream or M3U with creds - standard category layout
        _pmenu_visible = set(pm.get_visible_categories())
        items = []
        if has_live and _profile_section_visible(_pmenu_visible, pnum, "live"):
            items.append(
                (
                    _t(30002),
                    {"mode": "live_menu", "profile_num": pnum},
                    "DefaultAddonPVRClient.png",
                    True,
                )
            )
        if has_movies and _profile_section_visible(_pmenu_visible, pnum, "movies"):
            items.append(
                (
                    _t(30004),
                    {"mode": "movies_menu", "profile_num": pnum},
                    "DefaultMovies.png",
                    True,
                )
            )
        if has_series and _profile_section_visible(_pmenu_visible, pnum, "series"):
            items.append(
                (
                    _t(30005),
                    {"mode": "series_menu", "profile_num": pnum},
                    "DefaultTVShows.png",
                    True,
                )
            )
        if has_replay and _profile_section_visible(_pmenu_visible, pnum, "replay"):
            items.append(
                (
                    _t(30006),
                    {"mode": "replay_menu", "profile_num": pnum},
                    "DefaultAddonsUpdates.png",
                    True,
                )
            )
        if _profile_section_visible(_pmenu_visible, pnum, "favs"):
            items.append(
                (
                    _t(30009),
                    {"mode": "profile_favorites_menu", "pnum": pnum},
                    "DefaultFavourites.png",
                    True,
                )
            )
        if _profile_section_visible(_pmenu_visible, pnum, "recent"):
            items.append(
                (
                    _t(30230),
                    {"mode": "profile_recently_watched", "pnum": pnum},
                    "DefaultAddonPVRClient.png",
                    True,
                )
            )
        if _profile_section_visible(_pmenu_visible, pnum, "search"):
            items.append(
                (
                    _t(30007),
                    {"mode": "search_global", "profile_num": pnum},
                    "DefaultAddonsSearch.png",
                    True,
                )
            )

        for label, q, icon, is_folder in items:
            li = xbmcgui.ListItem(label=label)
            li.setArt({"icon": icon})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=is_folder
            )
        xbmcplugin.endOfDirectory(addon_handle)
    except Exception as e:
        _log(f"profile_menu error for profile {pnum}: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
    finally:
        pm.active = original_active


def manage_active_profiles():
    """Show dialog to enable/disable PVR and profiles from main menu."""
    try:
        dialog = xbmcgui.Dialog()
        changed = False

        while True:
            items = []
            states = []

            # PVR item at the top
            pvr_path = _pvr_m3u_path()
            pvr_loaded = os.path.exists(pvr_path) and os.path.getsize(pvr_path) > 0
            pvr_status = (
                f"[COLOR green]{_t(30786)}[/COLOR]"
                if pvr_loaded
                else f"[COLOR red]{_t(30787)}[/COLOR]"
            )
            pvr_label = f"{_t(30001)} (Profile {_get_pvr_profile_num()})"
            items.append(f"{pvr_status} {pvr_label}")
            states.append(pvr_loaded)

            for n in range(1, 11):
                name = addon.getSetting(f"profile_{n}_name") or _t(30390, n)
                label = (
                    f"Profile {n} - {name}" if name != _t(30390, n) else f"Profile {n}"
                )
                has_creds = bool(
                    addon.getSetting(f"profile_{n}_xtream_url")
                    or addon.getSetting(f"profile_{n}_m3u")
                )
                if not has_creds:
                    items.append(f"[COLOR grey]{label} ({_t(30864)})[/COLOR]")
                    states.append(None)
                    continue
                enabled = addon.getSetting(f"profile_{n}_enabled") == "true"
                status = (
                    "[COLOR green]ON[/COLOR]" if enabled else "[COLOR red]OFF[/COLOR]"
                )
                items.append(f"{status} {label}")
                states.append(enabled)

            items.append("[COLOR yellow]{0}[/COLOR]".format(_t(30158)))

            choice = dialog.select(_t(30740), items)
            if choice == -1 or choice >= len(items) - 1:
                break

            # choice 0 = PVR
            if choice == 0:
                if states[0]:
                    # PVR is loaded — offer unload
                    unload_now = dialog.yesno(
                        _t(30770), _t(30894), nolabel=_t(30163), yeslabel=_t(30162)
                    )
                    if unload_now:
                        pd = xbmcgui.DialogProgress()
                        pd.create("XStream Player", _t(30895))
                        try:
                            _unload_pvr()
                        except Exception as e:
                            _log(f"PVR unload error: {e}")
                        finally:
                            pd.close()
                        dialog.notification("XStream Player", _t(30896))
                else:
                    # PVR is unloaded — offer load
                    load_now = dialog.yesno(
                        _t(30770), _t(30897), nolabel=_t(30403), yeslabel=_t(30162)
                    )
                    if load_now:
                        pd = xbmcgui.DialogProgress()
                        pd.create("XStream Player", _t(30568))
                        try:
                            _sync_pvr_force()
                        except Exception as e:
                            _log(f"PVR load error: {e}")
                        finally:
                            pd.close()
                        dialog.notification("XStream Player", _t(30878))
                continue

            # Profiles (shifted by +1 because PVR is at index 0)
            profile_num = choice
            if states[choice] is None:
                dialog.notification("XStream Player", _t(30893))
                continue

            current = addon.getSetting(f"profile_{profile_num}_enabled") == "true"
            new_state = "false" if current else "true"
            addon.setSetting(f"profile_{profile_num}_enabled", new_state)
            changed = True

            # If profile was enabled, auto-show it on main menu and ask to refresh data
            if new_state == "true":
                visible_cats = set(pm.get_visible_categories())
                if f"profile_{profile_num}" not in visible_cats:
                    visible_cats.add(f"profile_{profile_num}")
                    pm.set_visible_categories(list(visible_cats))
                name = addon.getSetting(f"profile_{profile_num}_name") or _t(
                    30390, profile_num
                )
                refresh_now = dialog.yesno(
                    _t(30770), _t(30748, name), nolabel=_t(30403), yeslabel=_t(30162)
                )
                if refresh_now:
                    _refresh_profile_data(profile_num)
            else:
                # Profile was disabled - ask to unload cached data
                name = addon.getSetting(f"profile_{profile_num}_name") or _t(
                    30390, profile_num
                )
                unload_now = dialog.yesno(
                    _t(30770), _t(30809, name), nolabel=_t(30163), yeslabel=_t(30162)
                )
                if unload_now:
                    count = _purge_profile_data(profile_num)
                    _log(f"Cleared {count} files for profile {profile_num}")

        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        if changed:
            xbmc.executebuiltin(
                "Container.Update(plugin://plugin.video.xstream-player/)"
            )
    except Exception as e:
        _log(f"manage_active_profiles error: {e}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def main_menu():
    _log("Opening main menu")

    # PVR Favorites sync — runs only when main menu opens, not on every navigation
    try:
        _safe_sync_pvr_favorites_startup()
    except Exception as e:
        _log(f"PVR Favorites startup sync error: {e}")

    _run_startup_checks()

    # PVR profile change detection
    current_pvr = addon.getSetting("active_pvr_profile") or "Profile 1"
    last_pvr = addon.getSetting("last_pvr_profile")
    if last_pvr and current_pvr != last_pvr:
        dialog = xbmcgui.Dialog()
        restart = dialog.yesno(
            _t(30732), _t(30733, current_pvr), nolabel=_t(30403), yeslabel=_t(30165)
        )
        if restart:
            if xbmc.getCondVisibility("System.Platform.Android"):
                dialog.ok("XStream Player", _t(30569))
            else:
                xbmc.executebuiltin("RestartApp")
    addon.setSetting("last_pvr_profile", current_pvr)

    visible = set(pm.get_visible_categories())
    # Safety: tools must always be visible so users can't lock themselves out
    visible.add("tools")

    active_profiles = []
    enabled_profiles = []
    profile_names = {}
    for n in range(1, 11):
        if addon.getSetting(f"profile_{n}_enabled") == "true":
            enabled_profiles.append(n)
            profile_names[n] = addon.getSetting(f"profile_{n}_name") or _t(30390, n)
            has_xtream = bool(addon.getSetting(f"profile_{n}_xtream_url"))
            has_m3u = bool(addon.getSetting(f"profile_{n}_m3u"))
            if has_xtream or has_m3u:
                active_profiles.append(n)

    creds = _get_credentials()
    load_live = pm.get_profile_setting("load_live") != "false"
    load_movies = pm.get_profile_setting("load_movies") != "false"
    load_series = pm.get_profile_setting("load_series") != "false"
    has_xtream = bool(creds.get("xtream_url"))
    has_m3u_with_creds = bool(creds.get("m3u_url")) and _m3u_has_credentials(
        creds.get("m3u_url")
    )
    has_m3u_simple = bool(creds.get("m3u_url")) and not has_m3u_with_creds
    has_live = (has_xtream or has_m3u_with_creds or has_m3u_simple) and load_live
    has_movies = (has_xtream or has_m3u_with_creds) and load_movies
    has_series = (has_xtream or has_m3u_with_creds) and load_series
    has_replay = (has_xtream or has_m3u_with_creds) and load_live
    has_search = len(active_profiles) > 0

    # Backwards compat: old 'live' key enables both
    if "live" in visible:
        visible.add("live_pvr")
        visible.add("live_classic")

    items_dict = {}

    # Addon Groups (respect hide/show visibility)
    ag_visible = set(_get_ag_visible())
    ag_items = _get_addon_group_items()
    for item in ag_items:
        if len(item) == 4:
            label, q, icon, is_folder = item
        else:
            label, q, icon = item
            is_folder = True
        # Use group index as key for individual groups (always ag_{num})
        group_num = str(q.get("group", "")) if q.get("group") else None
        if group_num:
            key = f"ag_{group_num}"
            if key in ag_visible:
                items_dict[key] = (label, q, icon, is_folder)
        else:
            # Fallback - shouldn't happen with new structure
            addon_id = str(q.get("addon_id", ""))
            items_dict[f"ag_single_{addon_id}"] = (label, q, icon, is_folder)

    # PVR items (use active_pvr_profile)
    pvr_creds = _get_pvr_credentials()
    pvr_has_live = bool(pvr_creds.get("xtream_url") or pvr_creds.get("m3u_url"))
    if "live_pvr" in visible and pvr_has_live:
        pvr_profile_num = (
            current_pvr.replace("Profile ", "") if "Profile" in current_pvr else "1"
        )
        items_dict["live_pvr"] = (
            f"{_t(30001)} {pvr_profile_num}",
            {"mode": "open_pvr"},
            "DefaultAddonPVRClient.png",
            False,
        )
    if "guide" in visible and pvr_has_live:
        items_dict["guide"] = (
            _t(30003),
            {"mode": "open_pvr_guide"},
            "DefaultPVRGuide.png",
            False,
        )
    if "continue_watching" in visible:
        items_dict["continue_watching"] = (
            _t(30888),
            {"mode": "continue_watching"},
            "DefaultInProgressShows.png",
            True,
        )

    if "pvr_favs" in visible and pvr_has_live:
        items_dict["pvr_favs"] = (
            _t(30008),
            {"mode": "pvr_favorites_manager"},
            "DefaultFavourites.png",
            True,
        )

    if "search" in visible and has_search:
        items_dict["search"] = (
            _t(30889),
            {"mode": "search_global"},
            "DefaultAddonsSearch.png",
            True,
        )

    if "favorites" in visible:
        items_dict["favorites"] = (
            _t(30743),
            {"mode": "favorites_menu"},
            "DefaultFavourites.png",
            True,
        )

    # Enabled profiles as folders
    for n in enabled_profiles:
        section_keys = {
            f"profile_{n}_live", f"profile_{n}_movies",
            f"profile_{n}_series", f"profile_{n}_replay",
            f"profile_{n}_favs", f"profile_{n}_recent",
            f"profile_{n}_search",
        }
        any_section_visible = bool(section_keys & visible)
        if f"profile_{n}" in visible or any_section_visible:
            items_dict[f"profile_{n}"] = (
                profile_names[n],
                {"mode": "profile_menu", "pnum": n},
                "DefaultTVShows.png",
                True,
            )

    # directly onto the main menu instead of showing a profile folder.
    if (
        addon.getSetting("single_profile_direct_mode") == "true"
        and len(active_profiles) == 1
    ):
        pnum = active_profiles[0]
        if f"profile_{pnum}" in items_dict:
            del items_dict[f"profile_{pnum}"]
            pcreds = _get_credentials_for_profile(pnum)
            pload_live = addon.getSetting(f"profile_{pnum}_load_live") != "false"
            pload_movies = addon.getSetting(f"profile_{pnum}_load_movies") != "false"
            pload_series = addon.getSetting(f"profile_{pnum}_load_series") != "false"
            phas_xtream = bool(pcreds.get("xtream_url"))
            phas_m3u_with_creds = bool(pcreds.get("m3u_url")) and _m3u_has_credentials(
                pcreds.get("m3u_url")
            )
            phas_m3u_simple = bool(pcreds.get("m3u_url")) and not phas_m3u_with_creds
            phas_live = (
                phas_xtream or phas_m3u_with_creds or phas_m3u_simple
            ) and pload_live
            phas_movies = (phas_xtream or phas_m3u_with_creds) and pload_movies
            phas_series = (phas_xtream or phas_m3u_with_creds) and pload_series
            phas_replay = (phas_xtream or phas_m3u_with_creds) and pload_live
            if phas_live and _profile_section_visible(visible, pnum, "live"):
                items_dict[f"profile_{pnum}_live"] = (
                    _t(30002),
                    {"mode": "live_menu", "profile_num": pnum},
                    "DefaultAddonPVRClient.png",
                    True,
                )
            if phas_movies and _profile_section_visible(visible, pnum, "movies"):
                items_dict[f"profile_{pnum}_movies"] = (
                    _t(30004),
                    {"mode": "movies_menu", "profile_num": pnum},
                    "DefaultMovies.png",
                    True,
                )
            if phas_series and _profile_section_visible(visible, pnum, "series"):
                items_dict[f"profile_{pnum}_series"] = (
                    _t(30005),
                    {"mode": "series_menu", "profile_num": pnum},
                    "DefaultTVShows.png",
                    True,
                )
            if phas_replay and _profile_section_visible(visible, pnum, "replay"):
                items_dict[f"profile_{pnum}_replay"] = (
                    _t(30006),
                    {"mode": "replay_menu", "profile_num": pnum},
                    "DefaultAddonsUpdates.png",
                    True,
                )
            if _profile_section_visible(visible, pnum, "favs"):
                items_dict[f"profile_{pnum}_favs"] = (
                    _t(30009),
                    {"mode": "profile_favorites_menu", "pnum": pnum},
                    "DefaultFavourites.png",
                    True,
                )
            if _profile_section_visible(visible, pnum, "recent"):
                items_dict[f"profile_{pnum}_recent"] = (
                    _t(30230),
                    {"mode": "profile_recently_watched", "pnum": pnum},
                    "DefaultAddonPVRClient.png",
                    True,
                )
            if _profile_section_visible(visible, pnum, "search"):
                items_dict[f"profile_{pnum}_search"] = (
                    _t(30007),
                    {"mode": "search_global", "profile_num": pnum},
                    "DefaultAddonsSearch.png",
                    True,
                )

    if "tools" in visible:
        items_dict["tools"] = (
            _t(30010),
            {"mode": "tools_menu"},
            "DefaultAddonProgram.png",
            True,
        )

    # Apply saved order if exists, otherwise use new default order
    saved_order = _get_main_menu_order()
    if saved_order:
        ordered_items = []
        direct_pnum = None
        if (
            addon.getSetting("single_profile_direct_mode") == "true"
            and len(active_profiles) == 1
        ):
            direct_pnum = active_profiles[0]
        for key in saved_order:
            if key in items_dict:
                ordered_items.append(items_dict.pop(key))
                # After replay, insert any new section items not yet in saved_order
                if direct_pnum and key == f"profile_{direct_pnum}_replay":
                    for extra in (f"profile_{direct_pnum}_favs",
                                  f"profile_{direct_pnum}_recent",
                                  f"profile_{direct_pnum}_search"):
                        if extra in items_dict:
                            ordered_items.append(items_dict.pop(extra))
            elif direct_pnum and key == f"profile_{direct_pnum}":
                # In direct mode, the saved profile_N key controls all flattened items
                prefix = f"profile_{direct_pnum}_"
                for k in list(items_dict.keys()):
                    if k.startswith(prefix):
                        ordered_items.append(items_dict.pop(k))
        leftover_keys = list(items_dict.keys())
        leftover_items = []
        tools_item = None
        for k in leftover_keys:
            item = items_dict.pop(k)
            if k == "tools":
                tools_item = item
            else:
                leftover_items.append(item)
        ordered_items.extend(leftover_items)
        if tools_item:
            ordered_items.append(tools_item)
        items = ordered_items
    else:
        default_order = []
        for i in range(1, 6):
            if f"ag_{i}" in items_dict:
                default_order.append(f"ag_{i}")
        if "live_pvr" in items_dict:
            default_order.append("live_pvr")
        if "guide" in items_dict:
            default_order.append("guide")
        if "continue_watching" in items_dict:
            default_order.append("continue_watching")
        for n in range(1, 11):
            if f"profile_{n}" in items_dict:
                default_order.append(f"profile_{n}")
            for suffix in ("live", "movies", "series", "replay", "favs", "recent", "search"):
                key = f"profile_{n}_{suffix}"
                if key in items_dict:
                    default_order.append(key)
        if "pvr_favs" in items_dict:
            default_order.append("pvr_favs")
        if "favorites" in items_dict:
            default_order.append("favorites")
        if "search" in items_dict:
            default_order.append("search")
        if "tools" in items_dict:
            default_order.append("tools")

        items = [items_dict[k] for k in default_order if k in items_dict]

    for item in items:
        if len(item) == 4:
            # Addon group item: (label, query, icon, is_folder)
            label, q, icon, is_folder = item
        else:
            # Regular item: (label, query, icon)
            label, q, icon = item
            is_folder = q.get("mode") not in ("open_pvr", "open_pvr_guide")
        li = xbmcgui.ListItem(label=label)
        li.setArt({"icon": icon})
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=is_folder
        )
    xbmcplugin.endOfDirectory(addon_handle)


def tools_menu():
    _log("Opening tools menu")
    if not _check_pin("Tools"):
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return
    creds = _get_credentials()
    active_name = creds.get("name", _t(30390, 1))
    items = [
        (
            "[COLOR yellow]{0}[/COLOR]".format(_t(30011)),
            {"mode": "settings"},
            "DefaultAddonProgram.png",
        ),
        (
            _t(30017, _get_pvr_profile_num()),
            {"mode": "switch_profile"},
            "DefaultAddonPVRClient.png",
        ),
        (_t(30740), {"mode": "manage_active_profiles"}, "DefaultTVShows.png"),
        (_t(30718), {"mode": "reset_reload_menu"}, "DefaultAddonsUpdates.png"),
        (_t(30801), {"mode": "manage_visible_cats"}, "DefaultAddonService.png"),
        (_t(30014), {"mode": "reorder_main_menu"}, "DefaultAddonService.png"),
        (_t(30015), {"mode": "hide_categories_menu"}, "DefaultAddonService.png"),
        (_t(30016), {"mode": "clear_cache_menu"}, "DefaultAddonNone.png"),
        (_t(30723), {"mode": "account_iptv_menu"}, "DefaultAddonWebSkin.png"),
        (
            "[COLOR green]{0}[/COLOR]".format(_t(30020)),
            {"mode": "check_update"},
            "DefaultAddonsUpdates.png",
        ),
    ]
    for label, q, icon in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({"icon": icon})
        is_folder = q.get("mode") not in (
            "settings",
            "refresh_data",
            "toggle_setting",
            "manage_visible_cats",
            "clear_cache_menu",
            "reorder_main_menu",
            "manage_active_profiles",
        )
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=is_folder
        )
    xbmcplugin.endOfDirectory(addon_handle)


def reset_reload_menu():
    """Reset/Reload menu - actions for reloading EPG, PVR, and relaunching Kodi."""
    _log("Opening reset/reload menu")
    items = [
        (_t(30012), {"mode": "refresh_profile_menu"}, "DefaultAddonsUpdates.png"),
        (_t(30719), {"mode": "force_reload_epg"}, "DefaultAddonsUpdates.png"),
        (_t(30720), {"mode": "force_reload_pvr"}, "DefaultAddonsUpdates.png"),
        (_t(30711), {"mode": "reset_pvr_epg_db"}, "DefaultAddonsUpdates.png"),
        (_t(30721), {"mode": "relaunch_kodi"}, "DefaultAddonsUpdates.png"),
    ]
    for label, q, icon in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({"icon": icon})
        is_folder = q.get("mode") not in (
            "refresh_profile_menu",
            "force_reload_epg",
            "force_reload_pvr",
            "reset_pvr_epg_db",
            "relaunch_kodi",
        )
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=is_folder
        )
    xbmcplugin.endOfDirectory(addon_handle)


def account_iptv_menu():
    """Account Info menu - test connection and account information."""
    _log("Opening account info menu")
    items = [
        (_t(30724), {"mode": "test_connection"}, "DefaultAddonService.png"),
        (_t(30725), {"mode": "account_info"}, "DefaultAddonService.png"),
        (_t(30788), {"mode": "loaded_profiles_view"}, "DefaultAddonPVRClient.png"),
    ]
    for label, q, icon in items:
        li = xbmcgui.ListItem(label=label)
        li.setArt({"icon": icon})
        is_folder = q.get("mode") not in (
            "test_connection",
            "account_info",
            "loaded_profiles_view",
        )
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=is_folder
        )
    xbmcplugin.endOfDirectory(addon_handle)


def loaded_profiles_view():
    """Show loading status of PVR and all 10 profiles as an unclickable list."""
    # PVR status
    pvr_profile = addon.getSetting("active_pvr_profile") or "Profile 1"
    pvr_num = (
        re.search(r"(\d+)$", pvr_profile).group(1)
        if re.search(r"(\d+)$", pvr_profile)
        else "1"
    )
    pvr_path = _pvr_m3u_path()
    pvr_loaded = os.path.exists(pvr_path) and os.path.getsize(pvr_path) > 0
    pvr_status = (
        f"[COLOR green]{_t(30786)}[/COLOR]"
        if pvr_loaded
        else f"[COLOR red]{_t(30787)}[/COLOR]"
    )

    items = [f"{pvr_status} {_t(30001)} {pvr_num}"]

    # All 10 profiles
    for n in range(1, 11):
        profile_name = addon.getSetting(f"profile_{n}_name") or _t(30390, n)
        has_creds = bool(
            addon.getSetting(f"profile_{n}_xtream_url")
            or addon.getSetting(f"profile_{n}_m3u")
        )

        if not has_creds:
            # Grey out profiles without credentials
            items.append(f"[COLOR grey]{profile_name} ({_t(30864)})[/COLOR]")
            continue

        loaded = _profile_has_data(n)
        status = (
            f"[COLOR green]{_t(30786)}[/COLOR]"
            if loaded
            else f"[COLOR red]{_t(30787)}[/COLOR]"
        )
        items.append(f"{status} {profile_name}")

    xbmcgui.Dialog().select(_t(30788), items)


def relaunch_kodi_action():
    """Relaunch Kodi - show confirmation and restart."""
    dialog = xbmcgui.Dialog()
    confirm = dialog.yesno(_t(30721), _t(30726), yeslabel=_t(30165), nolabel=_t(30164))
    if not confirm:
        return
    _log("Relaunching Kodi")
    try:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"PVR.Manager.Stop","id":1}')
        xbmc.sleep(1000)
    except Exception as e:
        _log(f"PVR stop before relaunch warning: {e}")
    if xbmc.getCondVisibility("System.Platform.Android"):
        dialog.ok("XStream Player", _t(30569))
    else:
        xbmc.executebuiltin("RestartApp")


def install_upnext():
    if xbmc.getCondVisibility("System.HasAddon(service.upnext)"):
        xbmcgui.Dialog().notification("XStream Player", _t(30859))
        return
    xbmc.executebuiltin("InstallAddon(service.upnext)")


def open_upnext_settings():
    xbmc.executebuiltin("Dialog.Close(all,true)")
    xbmc.sleep(500)
    import xbmcaddon
    xbmcaddon.Addon("service.upnext").openSettings()


def reorder_main_menu():
    """Reorder main menu items - shows only VISIBLE enabled profiles and addon groups."""
    dialog = xbmcgui.Dialog()

    while True:  # Loop to stay in reorder tool
        visible = set(pm.get_visible_categories())
        ag_visible = set(_get_ag_visible())

        # Backwards compat
        if "live" in visible:
            visible.add("live_pvr")
        if "live_classic" in visible:
            visible.discard("live_classic")

        items = []

        for i in range(1, 6):
            if (
                _get_setting_direct(f"ag_{i}_enabled", "false") == "true"
                and f"ag_{i}" in ag_visible
            ):
                group_name = _get_setting_direct(f"ag_{i}_name", _t(30391, i))
                items.append([f"ag_{i}", group_name])

        if "live_pvr" in visible:
            items.append(["live_pvr", _t(30001)])
        if "guide" in visible:
            items.append(["guide", _t(30380)])

        for n in range(1, 11):
            if addon.getSetting(f"profile_{n}_enabled") == "true":
                profile_name = addon.getSetting(f"profile_{n}_name") or _t(30390, n)
                items.append([f"profile_{n}", profile_name])

        if "continue_watching" in visible:
            items.append(["continue_watching", _t(30888)])
        if "pvr_favs" in visible:
            items.append(["pvr_favs", _t(30008)])
        if "favorites" in visible:
            items.append(["favorites", _t(30743)])
        if "search" in visible:
            items.append(["search", _t(30889)])

        if len(items) <= 1:
            dialog.notification(_t(30770), _t(30071))
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return

        saved_order = _get_main_menu_order()
        if saved_order:
            order_map = {k: i for i, k in enumerate(saved_order)}
            items.sort(key=lambda x: order_map.get(x[0], 9999))

        # Pick item to move
        labels = [f"{i + 1}. {name}" for i, (key, name) in enumerate(items)]
        labels.append("[COLOR red]{0}[/COLOR]".format(_t(30158)))

        choice = dialog.select(_t(30172), labels)
        if choice == -1 or choice >= len(items):
            return  # Cancelled - exit

        from_idx = choice
        from_key, from_name = items[from_idx]

        # Pick where to move it (before which item)
        to_labels = []
        original_indices = []  # Track which items[i] each label refers to
        for i, (key, name) in enumerate(items):
            if i == from_idx:
                continue
            to_labels.append(_t(30192, name))
            original_indices.append(i)  # Remember this label = items[i]
        to_labels.append(_t(30193))
        to_labels.append("[COLOR red]{0}[/COLOR]".format(_t(30158)))

        to_choice = dialog.select(_t(30194, from_name), to_labels)
        if to_choice == -1 or to_choice == len(to_labels) - 1:
            return  # Cancel - exit

        # Calculate new position
        if to_choice == len(to_labels) - 2:  # Move to End
            to_idx = len(items)
        else:
            # Map back to original index
            to_idx = original_indices[to_choice]
            # After popping from_idx, indices after it shift down by 1
            if to_idx > from_idx:
                to_idx -= 1

        # Confirm with OK/Cancel dialog
        confirm = dialog.yesno(
            _t(30041), _t(30565, from_name), yeslabel=_t(30160), nolabel=_t(30161)
        )
        if not confirm:
            continue  # Back to start

        # Perform the move
        item = items.pop(from_idx)
        if to_idx > len(items):
            items.append(item)
        else:
            items.insert(to_idx, item)

        new_order = [k for k, n in items]
        _set_main_menu_order(new_order)
        dialog.notification(_t(30770), _t(30072))
        xbmc.executebuiltin(
            "Container.Update(plugin://plugin.video.xstream-player/,replace)"
        )


def _profile_section_visible(visible, pnum, section):
    """Return True if a profile section should be shown.

    Backward compat tiers:
    1. New keys (favs/recent/search) present → respect all section keys explicitly.
    2. Only old keys (live/movies/series/replay) present → respect old keys; new
       sections (favs/recent/search) default to True so they appear automatically.
    3. No section keys at all → fall back to legacy profile_N key.
    """
    visible_set = set(visible)
    old_keys = {
        f"profile_{pnum}_live", f"profile_{pnum}_movies",
        f"profile_{pnum}_series", f"profile_{pnum}_replay",
    }
    new_keys = {
        f"profile_{pnum}_favs", f"profile_{pnum}_recent", f"profile_{pnum}_search",
    }
    has_new = bool(new_keys & visible_set)
    has_old = bool(old_keys & visible_set)

    if has_new:
        # Full new-key mode: respect every key explicitly
        return f"profile_{pnum}_{section}" in visible_set
    if has_old:
        # Old keys exist but new keys were never saved → default new sections to visible
        if section in ("favs", "recent", "search"):
            return True
        return f"profile_{pnum}_{section}" in visible_set
    # No section keys at all → legacy profile_N key
    return f"profile_{pnum}" in visible_set


def manage_visible_cats():
    """Manage visible main menu items - shows only ENABLED profiles and addon groups."""
    visible = set(pm.get_visible_categories())
    ag_visible = set(_get_ag_visible())

    items = []

    for i in range(1, 6):
        if _get_setting_direct(f"ag_{i}_enabled", "false") == "true":
            group_name = _get_setting_direct(f"ag_{i}_name", _t(30391, i))
            items.append([f"ag_{i}", group_name])

    items.append(["live_pvr", _t(30001)])
    items.append(["guide", _t(30003)])

    # Collect profiles with sections (Xtream / M3U-with-creds / simple M3U)
    # Simple M3U only gets Live/Favs/Recent/Search (no Movies/Series/Replay)
    _full_profiles = []  # [(n, profile_name, [(key, label), ...]), ...]
    for n in range(1, 11):
        if addon.getSetting(f"profile_{n}_enabled") == "true":
            profile_name = addon.getSetting(f"profile_{n}_name") or _t(30390, n)
            pcreds_n = _get_credentials_for_profile(n)
            phas_xtream_n = bool(pcreds_n.get("xtream_url"))
            phas_m3u_creds_n = bool(pcreds_n.get("m3u_url")) and _m3u_has_credentials(
                pcreds_n.get("m3u_url")
            )
            phas_m3u_simple_n = bool(pcreds_n.get("m3u_url")) and not phas_m3u_creds_n
            is_full_profile = phas_xtream_n or phas_m3u_creds_n or phas_m3u_simple_n
            if is_full_profile:
                pload_live_n = addon.getSetting(f"profile_{n}_load_live") != "false"
                pload_movies_n = addon.getSetting(f"profile_{n}_load_movies") != "false"
                pload_series_n = addon.getSetting(f"profile_{n}_load_series") != "false"
                supports_cats = phas_xtream_n or phas_m3u_creds_n
                sec = []
                if pload_live_n:
                    sec.append([f"profile_{n}_live", _t(30002)])
                if pload_movies_n and supports_cats:
                    sec.append([f"profile_{n}_movies", _t(30004)])
                if pload_series_n and supports_cats:
                    sec.append([f"profile_{n}_series", _t(30005)])
                if pload_live_n and supports_cats:
                    sec.append([f"profile_{n}_replay", _t(30006)])
                sec.append([f"profile_{n}_favs", _t(30009)])
                sec.append([f"profile_{n}_recent", _t(30230)])
                sec.append([f"profile_{n}_search", _t(30007)])
                _full_profiles.append((n, profile_name, sec))
            else:
                items.append([f"profile_{n}", profile_name])

    # Show/Hide reflects what is actually on the main screen:
    _direct_single = (
        addon.getSetting("single_profile_direct_mode") == "true"
        and len(_full_profiles) == 1
    )
    if _direct_single:
        for _n, _pname, _sec in _full_profiles:
            for _key, _label in _sec:
                items.append([_key, _label])
    else:
        for _n, _pname, _sec in _full_profiles:
            items.append([f"profile_{_n}", _pname])

    items.append(["continue_watching", _t(30888)])
    items.append(["pvr_favs", _t(30008)])
    items.append(["favorites", _t(30743)])
    items.append(["search", _t(30889)])

    # Backwards compat: old keys
    if "live" in visible:
        visible.add("live_pvr")
        visible.discard("live")
    if "live_classic" in visible:
        visible.discard("live_classic")

    saved_order = _get_main_menu_order()
    if saved_order:
        order_map = {k: i for i, k in enumerate(saved_order)}
        items.sort(key=lambda x: order_map.get(x[0], 9999))

    keys = [k for k, _ in items]
    options = [name for _, name in items]

    seen = set(_get_ag_seen())
    new_seen = [k for k in keys if k.startswith("ag_") and k not in seen]
    if new_seen:
        _set_ag_seen(list(seen) + new_seen)

    combined_visible = visible | ag_visible
    preselect = []
    for i, k in enumerate(keys):
        if k.startswith("profile_") and k.count("_") == 2:
            # section key: profile_{n}_{section} — use backward-compat helper
            _, pnum_s, section_s = k.split("_", 2)
            if _profile_section_visible(visible, pnum_s, section_s):
                preselect.append(i)
        elif k.startswith("profile_") and k.count("_") == 1:
            # profile folder key: profile_{n}
            # preselect if folder key visible OR any section key visible (backward compat)
            pnum_s = k.split("_", 1)[1]
            sec_keys_n = {
                f"profile_{pnum_s}_live", f"profile_{pnum_s}_movies",
                f"profile_{pnum_s}_series", f"profile_{pnum_s}_replay",
                f"profile_{pnum_s}_favs", f"profile_{pnum_s}_recent",
                f"profile_{pnum_s}_search",
            }
            if k in combined_visible or bool(sec_keys_n & visible):
                preselect.append(i)
        elif k in combined_visible:
            preselect.append(i)

    dialog = xbmcgui.Dialog()
    result = dialog.multiselect(_t(30173), options, preselect=preselect)
    if result is None:
        return

    new_visible = []
    new_ag_visible = []
    for i in result:
        key = keys[i]
        if key.startswith("ag_"):
            new_ag_visible.append(key)
        else:
            new_visible.append(key)

    if "tools" not in new_visible:
        new_visible.append("tools")

    pm.set_visible_categories(new_visible)
    _set_ag_visible(new_ag_visible)
    xbmcgui.Dialog().notification("XStream Player", _t(30083))
    xbmc.executebuiltin(
        "Container.Update(plugin://plugin.video.xstream-player/,replace)"
    )


def _get_ag_visible():
    """Get list of visible addon groups (persists across profiles).
    Newly enabled groups that have never been seen are auto-added to visible."""
    data_path = _get_addon_data_path()
    try:
        with open(
            os.path.join(data_path, "ag_visible.json"), "r", encoding="utf-8"
        ) as f:
            saved = json.load(f)
    except Exception:
        saved = []

    seen = set(_get_ag_seen())
    currently_enabled = [
        f"ag_{i}"
        for i in range(1, 6)
        if _get_setting_direct(f"ag_{i}_enabled", "false") == "true"
    ]

    merged = saved[:]
    new_seen = []
    for g in currently_enabled:
        if g not in seen:
            if g not in merged:
                merged.append(g)
            new_seen.append(g)

    if new_seen:
        _set_ag_seen(list(seen) + new_seen)
        _set_ag_visible(merged)

    return merged


def _get_main_menu_order_path():
    """Get path to main menu order file for current profile."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    return os.path.join(profile, f"main_menu_order_p{pm.active}.json")


def _get_main_menu_order():
    """Load saved main menu order. Returns list of keys or empty list."""
    try:
        with open(_get_main_menu_order_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _set_main_menu_order(order_list):
    """Save main menu order."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        os.makedirs(profile)
    order_path = _get_main_menu_order_path()
    tmp_file = order_path + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(order_list, f)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, order_path)


def _set_ag_visible(ag_list):
    """Save list of visible addon groups (persists across profiles)"""
    data_path = _get_addon_data_path()
    visible_file = os.path.join(data_path, "ag_visible.json")
    tmp_file = visible_file + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(ag_list, f)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, visible_file)


def _get_ag_seen():
    """Get list of addon group IDs that have already been presented to the user."""
    data_path = _get_addon_data_path()
    try:
        with open(os.path.join(data_path, "ag_seen.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _set_ag_seen(ag_list):
    """Save list of addon group IDs that have already been presented to the user."""
    data_path = _get_addon_data_path()
    seen_file = os.path.join(data_path, "ag_seen.json")
    tmp_file = seen_file + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(ag_list, f)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, seen_file)


def _get_hidden_subcats(stype, profile_num=None):
    """Get list of hidden subcategory IDs for a given type (live/movie/series)."""
    pnum = profile_num or pm.active
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    path = os.path.join(profile, f"hidden_subcats_{stype}_{pnum}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _set_hidden_subcats(stype, hidden, profile_num=None):
    """Save list of hidden subcategory IDs for a given type."""
    pnum = profile_num or pm.active
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        os.makedirs(profile)
    path = os.path.join(profile, f"hidden_subcats_{stype}_{pnum}.json")
    tmp_file = path + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(list(hidden), f)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, path)


def _get_hidden_items(stype, profile_num=None):
    """Get set of hidden individual stream IDs for a given type."""
    pnum = profile_num or pm.active
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    path = os.path.join(profile, f"hidden_items_{stype}_{pnum}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _set_hidden_items(stype, hidden, profile_num=None):
    """Save set of hidden individual stream IDs for a given type."""
    pnum = profile_num or pm.active
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(profile):
        os.makedirs(profile)
    path = os.path.join(profile, f"hidden_items_{stype}_{pnum}.json")
    tmp_file = path + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(list(hidden), f)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, path)


def hide_categories_menu(profile_num=None):
    """Show active profiles, then content types inside each profile.

    For Xtream or M3U with credentials: shows Live TV, Movies, Series separately.
    For M3U without credentials: shows channels directly (all content in one place).
    """
    if profile_num:
        # Inside a specific profile - show content types based on profile type
        pnum = profile_num

        # Get profile credentials to determine what content types to show
        original_active = pm.active
        pm.active = str(pnum)
        try:
            creds = pm.get_credentials()
            has_xtream = bool(creds.get("xtream_url"))
            has_m3u_with_creds = bool(creds.get("m3u_url")) and _m3u_has_credentials(
                creds.get("m3u_url")
            )
            has_m3u_simple = bool(creds.get("m3u_url")) and not has_m3u_with_creds
            supports_categories = has_xtream or has_m3u_with_creds
        finally:
            pm.active = original_active

        # For M3U without credentials, show channels directly (same as main menu)
        if has_m3u_simple:
            manage_hidden_subcats("live", pnum)
            return

        # Build options based on profile type
        options = [(_t(30002), "live", "DefaultAddonPVRClient.png")]
        if supports_categories:
            options.extend(
                [
                    (_t(30004), "movie", "DefaultMovies.png"),
                    (_t(30005), "series", "DefaultTVShows.png"),
                ]
            )

        for label, stype, icon in options:
            li = xbmcgui.ListItem(label=label)
            li.setArt({"icon": icon})
            q = {"mode": "manage_hidden_subcats", "stype": stype, "pnum": pnum}
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
            )
        xbmcplugin.endOfDirectory(addon_handle)
    else:
        # Top level - show all enabled profiles
        has_enabled = False
        for n in range(1, 11):
            if addon.getSetting(f"profile_{n}_enabled") == "true":
                has_enabled = True
                profile_name = addon.getSetting(f"profile_{n}_name") or _t(30390, n)
                label = (
                    f"Profile {n} - {profile_name}"
                    if profile_name != _t(30390, n)
                    else f"Profile {n}"
                )
                li = xbmcgui.ListItem(label=label)
                li.setArt({"icon": "DefaultAddonPVRClient.png"})
                q = {"mode": "hide_categories_menu", "pnum": n}
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
                )
        if not has_enabled:
            # No profiles enabled - show message
            xbmcgui.Dialog().notification("XStream Player", _t(30756))
        xbmcplugin.endOfDirectory(addon_handle)


def _profile_has_data(profile_num):
    """Check if any data is loaded for profile."""
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    prefix = f"data_cache_p{profile_num}_"
    try:
        for fname in os.listdir(profile):
            if fname.startswith(prefix):
                # Boundary check: p1 must not match p10, p11, etc.
                rest = fname[len(prefix) :]
                if rest and rest[0].isdigit():
                    continue
                return True
    except OSError as e:
        _log(f"data cache list warning: {e}")
    return False


def _manage_load_content_toggles(profile_num):
    """Settings dialog to toggle Load TV/Movies/Series for a profile."""
    dialog = xbmcgui.Dialog()
    pnum = profile_num

    # Get profile credentials to determine available content types
    original_active = pm.active
    pm.active = str(pnum)
    try:
        creds = pm.get_credentials()
        has_xtream = bool(creds.get("xtream_url"))
        has_m3u_with_creds = bool(creds.get("m3u_url")) and _m3u_has_credentials(
            creds.get("m3u_url")
        )
        supports_categories = has_xtream or has_m3u_with_creds
    finally:
        pm.active = original_active

    # Get current values
    live = addon.getSetting(f"profile_{pnum}_load_live") == "true"
    movies = addon.getSetting(f"profile_{pnum}_load_movies") == "true"
    series = addon.getSetting(f"profile_{pnum}_load_series") == "true"

    # Build options based on source type
    if supports_categories:
        options = [_t(30002), _t(30004), _t(30005)]  # Live TV, Movies, Series
        preselect = []
        if live:
            preselect.append(0)
        if movies:
            preselect.append(1)
        if series:
            preselect.append(2)
    else:
        # M3U without creds - only Live TV
        options = [_t(30002)]  # Live TV only
        preselect = [0] if live else []

    result = dialog.multiselect(_t(30810), options, preselect=preselect)
    if result is None:
        return

    changed = False
    if supports_categories:
        new_live = "true" if 0 in result else "false"
        new_movies = "true" if 1 in result else "false"
        new_series = "true" if 2 in result else "false"
        if addon.getSetting(f"profile_{pnum}_load_live") != new_live:
            changed = True
        if addon.getSetting(f"profile_{pnum}_load_movies") != new_movies:
            changed = True
        if addon.getSetting(f"profile_{pnum}_load_series") != new_series:
            changed = True
        addon.setSetting(f"profile_{pnum}_load_live", new_live)
        addon.setSetting(f"profile_{pnum}_load_movies", new_movies)
        addon.setSetting(f"profile_{pnum}_load_series", new_series)
    else:
        # M3U simple - only toggle live
        new_live = "true" if 0 in result else "false"
        if addon.getSetting(f"profile_{pnum}_load_live") != new_live:
            changed = True
        addon.setSetting(f"profile_{pnum}_load_live", new_live)

    dialog.notification("XStream Player", _t(30083))

    if changed:
        if dialog.yesno(_t(30012), _t(30012)):
            _refresh_profile_data(pnum)
            # If this is the PVR profile, offer PVR sync after reload
            if _is_pvr_profile(pnum) and is_pvr_iptvsimple_installed():
                xbmc.sleep(500)  # Allow previous dialog to close
                if dialog.yesno("XStream Player", _t(30867)):
                    try:
                        _sync_pvr_force()
                        _log("PVR sync triggered after load toggle change")
                    except Exception as e:
                        _log(f"PVR sync after load toggle warning: {e}")
                else:
                    # User declined — flag for startup retry
                    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
                    retry_flag = os.path.join(
                        profile_path, "pvr_sync_retry_needed.flag"
                    )
                    with open(retry_flag, "w", encoding="utf-8") as f:
                        f.write("1")
                    _log(
                        "PVR sync deferred after load toggle, flagged for startup retry"
                    )


def _manage_content_select(profile_num):
    """Settings dialog to select which content type to manage."""
    dialog = xbmcgui.Dialog()
    pnum = profile_num

    if not _profile_has_data(pnum):
        dialog.ok("XStream Player", _t(30759))
        return

    # Get profile credentials to determine available content types
    original_active = pm.active
    pm.active = str(pnum)
    try:
        creds = pm.get_credentials()
        has_xtream = bool(creds.get("xtream_url"))
        has_m3u_with_creds = bool(creds.get("m3u_url")) and _m3u_has_credentials(
            creds.get("m3u_url")
        )
        supports_categories = has_xtream or has_m3u_with_creds
    finally:
        pm.active = original_active

    # Build options based on source type
    if supports_categories:
        options = [_t(30002), _t(30004), _t(30005)]  # Live TV, Movies, Series
        stype_map = {0: "live", 1: "movie", 2: "series"}
    else:
        # M3U without creds - only Live TV
        options = [_t(30002)]  # Live TV only
        stype_map = {0: "live"}

    choice = dialog.select(_t(30760), options)
    if choice < 0:
        return

    stype = stype_map[choice]

    manage_content_dialog(stype, pnum)


def manage_content_dialog(stype, profile_num):
    """Dialog-based content manager for use from settings. Loops until user cancels."""
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    if not url:
        xbmcgui.Dialog().notification("XStream Player", _t(30073))
        return
    cats = _get_cached_xtream_categories(url, user, pwd, stype)
    if not cats:
        xbmcgui.Dialog().notification("XStream Player", _t(30074))
        return
    dialog = xbmcgui.Dialog()
    streams = _get_cached_xtream_streams(url, user, pwd, stype)
    stype_label_map = {
        "live": _t(30002),  # Live TV
        "movie": _t(30004),  # Movies
        "series": _t(30005),  # Series
    }
    stype_label = stype_label_map.get(stype, stype.capitalize())
    changed = False
    while True:
        hidden = _get_hidden_subcats(stype, pnum)
        hidden_items = _get_hidden_items(stype, pnum)
        hidden_cat_count = len(hidden)
        hidden_item_count = len(hidden_items)
        labels = [
            "[COLOR gold]{0}[/COLOR]".format(_t(30159, hidden_cat_count)),
            "[COLOR gold]{0}[/COLOR]".format(_t(30190, hidden_item_count)),
        ]
        for c in cats:
            cat_name = c.get("category_name", "Unknown")
            labels.append(cat_name)
        choice = dialog.select(_t(30761, stype_label), labels)
        if choice < 0:
            break
        if choice == 0:
            # Multiselect categories — checked = HIDDEN, with Select/Deselect All
            cat_names = [_t(30333), _t(30334)] + [
                c.get("category_name", "Unknown") for c in cats
            ]
            cat_ids = [str(c.get("category_id", "")) for c in cats]
            preselect = [i + 2 for i, cid in enumerate(cat_ids) if cid in hidden]
            result = dialog.multiselect(_t(30335), cat_names, preselect=preselect)
            if result is None:
                continue
            if 0 in result:
                # Select All — reopen with all selected
                preselect = list(range(2, len(cat_names)))
                result = dialog.multiselect(_t(30335), cat_names, preselect=preselect)
                if result is None:
                    continue
            if 1 in result:
                # Deselect All — reopen with none selected
                result = dialog.multiselect(_t(30523), cat_names, preselect=[])
                if result is None:
                    continue
            real_result = [i - 2 for i in result if i >= 2] if result else []
            new_hidden = {cat_ids[i] for i in real_result} if real_result else set()
            if new_hidden != hidden:
                _set_hidden_subcats(stype, new_hidden, pnum)
                dialog.notification("XStream Player", _t(30174, len(new_hidden)))
                changed = True
            continue
        if choice == 1:
            if not hidden_items:
                dialog.notification("XStream Player", _t(30075))
                continue
            hidden_streams = [
                s
                for s in (streams or [])
                if str(s.get("stream_id", "")) in hidden_items
            ]
            if not hidden_streams:
                dialog.notification("XStream Player", _t(30135))
                continue
            h_names = [_t(30334)] + [s.get("name", "Unknown") for s in hidden_streams]
            h_ids = [str(s.get("stream_id", "")) for s in hidden_streams]
            preselect = list(range(1, len(hidden_streams) + 1))
            result = dialog.multiselect(
                _t(30152, stype_label), h_names, preselect=preselect
            )
            if result is None:
                continue
            if 0 in result:
                # Deselect All — reopen with none selected
                result = dialog.multiselect(
                    _t(30524, stype_label), h_names, preselect=[]
                )
                if result is None:
                    continue
            real_result = [i - 1 for i in result if i >= 1] if result else []
            new_hidden = {h_ids[i] for i in real_result} if real_result else set()
            orphan_ids = hidden_items - set(h_ids)
            _set_hidden_items(stype, new_hidden | orphan_ids, pnum)
            unhidden = len(hidden_streams) - (len(real_result) if real_result else 0)
            if unhidden:
                dialog.notification("XStream Player", _t(30175, unhidden))
                changed = True
            continue
        cat = cats[choice - 2]
        cat_id = str(cat.get("category_id", ""))
        cat_name = cat.get("category_name", "Unknown")
        filtered = [
            s for s in (streams or []) if str(s.get("category_id", "")) == cat_id
        ]
        if not filtered:
            dialog.notification("XStream Player", _t(30136))
            continue
        ids = [str(s.get("stream_id", "")) for s in filtered]
        names = [_t(30333), _t(30334)] + [s.get("name", "Unknown") for s in filtered]
        preselect = [i + 2 for i, sid in enumerate(ids) if sid in hidden_items]
        result = dialog.multiselect(_t(30336, cat_name), names, preselect=preselect)
        if result is None:
            continue
        if 0 in result:
            preselect = list(range(2, len(names)))
            result = dialog.multiselect(_t(30336, cat_name), names, preselect=preselect)
            if result is None:
                continue
        if 1 in result:
            result = dialog.multiselect(_t(30524, cat_name), names, preselect=[])
            if result is None:
                continue
        real_result = [i - 2 for i in result if i >= 2] if result else []
        cat_id_set = set(ids)
        new_hidden = (hidden_items - cat_id_set) | (
            {ids[i] for i in real_result} if real_result else set()
        )
        if new_hidden != hidden_items:
            _set_hidden_items(stype, new_hidden, pnum)
            hidden_count = len(result) if result else 0
            dialog.notification("XStream Player", _t(30176, hidden_count, cat_name))
            changed = True
    # Re-sync PVR if anything changed and this is the active profile
    if changed and pnum == pm.active and stype == "live":
        _sync_pvr_force()
    if changed:
        if dialog.yesno(_t(30012), _t(30012)):
            _refresh_profile_data(pnum)
            return
    # Reopen settings at Profiles tab
    xbmc.executebuiltin("Addon.OpenSettings(plugin.video.xstream-player)")
    xbmc.sleep(300)
    xbmc.executebuiltin("SetFocus(9,1)")
    xbmc.executebuiltin("SetFocus(10,0)")


def manage_hidden_subcats(stype, profile_num=None):
    """Show subcategories as folder view. Clicking opens dialog: hide entire or browse content."""
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    m3u_url = creds.get("m3u_url", "")

    is_m3u_only = not url and m3u_url
    if not url and not m3u_url:
        # No credentials - nothing to hide
        xbmcgui.Dialog().notification("XStream Player", _t(30073))
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return

    hidden = _get_hidden_subcats(stype, pnum)
    hidden_items = _get_hidden_items(stype, pnum)

    if is_m3u_only:
        # For M3U without credentials: show flat channel list like main menu
        channels = _get_cached_m3u_channels(m3u_url)
        if not channels:
            xbmcgui.Dialog().notification("XStream Player", _t(30074))
            xbmcplugin.endOfDirectory(addon_handle)
            return

        li = xbmcgui.ListItem(label="[COLOR red]{0}[/COLOR]".format(_t(30260)))
        li.setArt({"icon": "DefaultAddonNone.png"})
        q = {"mode": "hide_all_subcats", "stype": stype, "pnum": pnum, "action": "hide"}
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )
        li = xbmcgui.ListItem(label="[COLOR green]{0}[/COLOR]".format(_t(30261)))
        li.setArt({"icon": "DefaultAddonNone.png"})
        q = {
            "mode": "hide_all_subcats",
            "stype": stype,
            "pnum": pnum,
            "action": "unhide",
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )
        li = xbmcgui.ListItem(
            label="[COLOR gold]{0}[/COLOR]".format(_t(30262).format(len(hidden_items)))
        )
        li.setArt({"icon": "DefaultFavourites.png"})
        q = {"mode": "hidden_items_all", "stype": stype, "pnum": pnum}
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )

        # Show all channels flat, sorted by group then name
        sorted_channels = sorted(
            channels,
            key=lambda ch: (ch.get("group") or "General", ch.get("name", "").lower()),
        )
        for ch in sorted_channels:
            item_id = str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
            is_hidden = item_id in hidden_items
            name = ch.get("name", "Unknown")
            group = ch.get("group") or "General"
            label = (
                "[COLOR red]{0}[/COLOR] [{1}] {2}".format(_t(30191), group, name)
                if is_hidden
                else "[{0}] {1}".format(group, name)
            )
            li = xbmcgui.ListItem(label=label)
            li.setArt({"icon": ch.get("logo", "") or "DefaultVideo.png"})
            q = {
                "mode": "hide_m3u_item_action",
                "stype": stype,
                "item_id": item_id,
                "item_name": name,
                "pnum": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )
        xbmcplugin.endOfDirectory(addon_handle)
        return

    cats = _get_cached_xtream_categories(url, user, pwd, stype)
    if not cats:
        xbmcgui.Dialog().notification("XStream Player", _t(30074))
        xbmcplugin.endOfDirectory(addon_handle)
        return

    # Select All / Deselect All at top
    li = xbmcgui.ListItem(label="[COLOR red]{0}[/COLOR]".format(_t(30260)))
    li.setArt({"icon": "DefaultAddonNone.png"})
    q = {"mode": "hide_all_subcats", "stype": stype, "pnum": pnum, "action": "hide"}
    xbmcplugin.addDirectoryItem(
        handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
    )
    li = xbmcgui.ListItem(label="[COLOR green]{0}[/COLOR]".format(_t(30261)))
    li.setArt({"icon": "DefaultAddonNone.png"})
    q = {"mode": "hide_all_subcats", "stype": stype, "pnum": pnum, "action": "unhide"}
    xbmcplugin.addDirectoryItem(
        handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
    )
    li = xbmcgui.ListItem(
        label="[COLOR gold]{0}[/COLOR]".format(_t(30262).format(len(hidden_items)))
    )
    li.setArt({"icon": "DefaultFavourites.png"})
    q = {"mode": "hidden_items_all", "stype": stype, "pnum": pnum}
    xbmcplugin.addDirectoryItem(
        handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
    )
    for c in cats:
        cat_id = str(c.get("category_id", ""))
        cat_name = c.get("category_name", "Unknown")
        is_hidden = cat_id in hidden
        label = (
            "[COLOR red]{0}[/COLOR] {1}".format(_t(30191), cat_name)
            if is_hidden
            else cat_name
        )
        li = xbmcgui.ListItem(label=label)
        li.setArt({"icon": "DefaultFolder.png"})
        q = {
            "mode": "hide_subcat_action",
            "stype": stype,
            "cat_id": cat_id,
            "cat_name": cat_name,
            "pnum": pnum,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )
    xbmcplugin.endOfDirectory(addon_handle)


def hide_m3u_item_action(stype, item_id, item_name, profile_num=None):
    """Toggle hide/unhide for a single M3U channel."""
    pnum = profile_num or pm.active
    hidden_items = _get_hidden_items(stype, pnum)
    is_hidden = item_id in hidden_items

    if is_hidden:
        hidden_items.discard(item_id)
        xbmcgui.Dialog().notification("XStream Player", _t(30301, item_name))
    else:
        hidden_items.add(item_id)
        xbmcgui.Dialog().notification("XStream Player", _t(30302, item_name))

    _set_hidden_items(stype, hidden_items, pnum)
    xbmc.executebuiltin("Container.Refresh")


def hide_subcat_action(stype, cat_id, cat_name, profile_num=None):
    """Dialog: hide/unhide entire category or browse individual items."""
    pnum = profile_num or pm.active
    hidden = _get_hidden_subcats(stype, pnum)
    is_hidden = cat_id in hidden
    dialog = xbmcgui.Dialog()
    if is_hidden:
        options = [_t(30525), _t(30526)]
    else:
        options = [_t(30527), _t(30526)]
    choice = dialog.select(cat_name, options)
    if choice < 0:
        return
    if choice == 0:
        if is_hidden:
            hidden.discard(cat_id)
            xbmcgui.Dialog().notification("XStream Player", _t(30301, cat_name))
        else:
            hidden.add(cat_id)
            xbmcgui.Dialog().notification("XStream Player", _t(30302, cat_name))
        _set_hidden_subcats(stype, hidden, pnum)
        xbmc.executebuiltin("Container.Refresh")
    elif choice == 1:
        creds = _get_credentials_for_profile(pnum)
        url = creds.get("xtream_url", "")
        user = creds.get("xtream_username", "")
        pwd = creds.get("xtream_password", "")
        streams = _get_cached_xtream_streams(url, user, pwd, stype)
        filtered = [
            s for s in (streams or []) if str(s.get("category_id", "")) == cat_id
        ]
        if not filtered:
            xbmcgui.Dialog().notification("XStream Player", _t(30136))
            return
        hidden_items = _get_hidden_items(stype, pnum)
        ids = [str(s.get("stream_id", "")) for s in filtered]
        names = [_t(30333), _t(30334)] + [s.get("name", "Unknown") for s in filtered]
        preselect = [i + 2 for i, sid in enumerate(ids) if sid in hidden_items]
        result = dialog.multiselect(_t(30528, cat_name), names, preselect=preselect)
        if result is None:
            return
        if 0 in result:
            preselect = list(range(2, len(names)))
            result = dialog.multiselect(_t(30528, cat_name), names, preselect=preselect)
            if result is None:
                return
        if 1 in result:
            result = dialog.multiselect(_t(30528, cat_name), names, preselect=[])
            if result is None:
                return
        real_result = [i - 2 for i in result if i >= 2] if result else []
        cat_ids = set(ids)
        new_hidden = (hidden_items - cat_ids) | (
            {ids[i] for i in real_result} if real_result else set()
        )
        _set_hidden_items(stype, new_hidden, pnum)
        hidden_count = len(result) if result else 0
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30312, hidden_count, cat_name)
        )


def hide_all_subcats(stype, action, profile_num=None):
    """Hide or unhide all subcategories at once."""
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    m3u_url = creds.get("m3u_url", "")
    is_m3u_only = not url and m3u_url

    if is_m3u_only:
        # M3U without credentials - hide/show all individual channels
        channels = _get_cached_m3u_channels(m3u_url)
        if not channels:
            return
        if action == "hide":
            new_hidden = {
                str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
                for ch in channels
            }
            _set_hidden_items(stype, new_hidden, pnum)
            xbmcgui.Dialog().notification("XStream Player", _t(30313, len(new_hidden)))
        else:
            _set_hidden_items(stype, set(), pnum)
            xbmcgui.Dialog().notification("XStream Player", _t(30137))
        xbmc.executebuiltin("Container.Refresh")
        return

    # Xtream/M3U with credentials - hide/show categories
    cats = [
        str(c.get("category_id", ""))
        for c in _get_cached_xtream_categories(url, user, pwd, stype)
    ]

    if not cats:
        return
    if action == "hide":
        new_hidden = set(cats)
        _set_hidden_subcats(stype, new_hidden, pnum)
        xbmcgui.Dialog().notification("XStream Player", _t(30313, len(new_hidden)))
    else:
        _set_hidden_subcats(stype, set(), pnum)
        xbmcgui.Dialog().notification("XStream Player", _t(30137))
    xbmc.executebuiltin("Container.Refresh")


def _get_recent_live(pnum=None):
    """Get recently watched live channels."""
    pnum = pnum or pm.active
    return _watch_history(pnum).get_all("live")[:10]


def _render_recent_items(items, stype, profile_num=None):
    """Render recently watched items."""

    pnum = profile_num or pm.active

    # For series: group by series_id + season_num, keep most recent per group
    if stype == "series":
        seen_groups = {}  # (series_id, season_num) -> entry
        for entry in items:
            series_id = entry.get("series_id")
            season_num = entry.get("season_num")
            if series_id and season_num:
                key = (series_id, season_num)
                # Keep the most recent entry for this series+season
                if key not in seen_groups or entry.get("timestamp", 0) > seen_groups[
                    key
                ].get("timestamp", 0):
                    seen_groups[key] = entry
        for (series_id, season_num), entry in seen_groups.items():
            name = entry.get("name", "")
            icon = entry.get("icon", "")
            ts = entry.get("timestamp", 0)
            when = (
                datetime.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
                if ts
                else ""
            )
            series_name = name
            if " S" in name and "E" in name:
                # Try to extract base series name (e.g., "Breaking Bad S01E05" -> "Breaking Bad")
                parts = name.rsplit(" S", 1)
                if parts:
                    series_name = parts[0]
            label = _t(30540, series_name, season_num)
            if when:
                label += f"  [COLOR gray]({when})[/COLOR]"
            li = xbmcgui.ListItem(label=label)
            if icon:
                li.setArt({"icon": icon, "thumb": icon})
            _prepare_playback_item(li)
            q = {
                "mode": "xtream_season",
                "series_id": series_id,
                "season_num": season_num,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
            )
        return

    # For movies/live: render individual entries
    for entry in items:
        name = entry.get("name", "")
        url = entry.get("url", "")
        icon = entry.get("icon", "")
        ts = entry.get("timestamp", 0)
        when = datetime.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M") if ts else ""
        label = f"{name}  [COLOR gray]({when})[/COLOR]" if when else name
        li = xbmcgui.ListItem(label=label)
        if icon:
            li.setArt({"icon": icon, "thumb": icon})
        li.setProperty("IsPlayable", "true")
        _prepare_playback_item(li)
        q = {
            "mode": "play_stream",
            "url": url,
            "name": name,
            "icon": icon,
            "stype": stype,
            "profile_num": pnum,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )


def live_menu(profile_num=None):
    original_active = pm.active
    if profile_num:
        pm.active = str(profile_num)
    try:
        creds = _get_credentials()
        xtream_url = creds.get("xtream_url", "")
        m3u_url = creds.get("m3u_url", "")
        has_m3u_with_creds = bool(m3u_url) and _m3u_has_credentials(m3u_url)
        _log(
            f"live_menu: profile={pm.active}, xtream_url={bool(xtream_url)}, m3u_url={bool(m3u_url)}, m3u_with_creds={has_m3u_with_creds}"
        )

        if not xtream_url and not m3u_url:
            li = xbmcgui.ListItem(label=_t(30240))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
            return

        recent_live = _get_recent_live(profile_num)
        if recent_live:
                li = xbmcgui.ListItem(
                    label="[COLOR yellow]{0}[/COLOR]".format(_t(30230))
                )
                li.setArt({"icon": "DefaultAddonPVRClient.png"})
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle,
                    url=build_url(
                        {
                            "mode": "recently_watched_by_type",
                            "stype": "live",
                            "pnum": profile_num,
                        }
                    ),
                    listitem=li,
                    isFolder=True,
                )

        # M3U with credentials OR Xtream - treat as Xtream (show category folders)
        if xtream_url or has_m3u_with_creds:
            li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30007)))
            li.setArt({"icon": "DefaultAddonsSearch.png"})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle,
                url=build_url(
                    {
                        "mode": "search_global",
                        "profile_num": profile_num,
                        "stype": "live",
                    }
                ),
                listitem=li,
                isFolder=True,
            )
            xtream_categories("live", profile_num)
            return

        # M3U without credentials - show flat paginated list of all channels
        if m3u_url:
            li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30007)))
            li.setArt({"icon": "DefaultAddonsSearch.png"})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle,
                url=build_url(
                    {
                        "mode": "search_global",
                        "profile_num": profile_num,
                        "stype": "live",
                    }
                ),
                listitem=li,
                isFolder=True,
            )
            _show_all_m3u_channels(profile_num)
            return

        xbmcplugin.endOfDirectory(addon_handle)
    finally:
        if profile_num:
            pm.active = original_active


def _epg_enabled():
    return addon.getSetting("show_epg_live").lower() == "true"


def m3u_group(group, profile_num=None, page=1):
    xbmcplugin.setContent(addon_handle, "livetv")
    show_epg = _epg_enabled()
    pnum = profile_num or pm.active
    epg = EPG(addon, profile_num=pnum)
    if show_epg:
        epg.load()
        if epg.is_refreshing:
            _log("EPG background refresh in progress - showing cached/stale data")
    creds = _get_credentials_for_profile(pnum)
    channels = _get_cached_m3u_channels(creds.get("m3u_url", ""))
    hidden_items = _get_hidden_items("live", pnum)
    group_channels = []
    for ch in channels:
        if (ch.get("group") or "General") != group:
            continue
        item_id = str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
        if item_id in hidden_items:
            continue
        group_channels.append(ch)

    per_page = _get_pagination_limit("live")
    if per_page == 0:
        per_page = len(group_channels)
    total = len(group_channels)
    start = (page - 1) * per_page
    end = start + per_page
    page_channels = group_channels[start:end]

    for ch in page_channels:
        name = ch.get("name", "Unknown")
        tvg_id = ch.get("tvg_id") or name
        url = ch.get("url")
        plot, display_name, current_title = (
            _make_epg_info(epg, tvg_id, name) if show_epg else ("", name, "")
        )
        li = xbmcgui.ListItem(label=display_name)
        info_tag = li.getVideoInfoTag()
        info_tag.setMediaType("video")
        info_tag.setTitle(current_title or name)
        info_tag.setPlot(plot)
        if ch.get("logo"):
            li.setArt({"icon": ch["logo"], "thumb": ch["logo"]})
        li.setProperty("IsPlayable", "true")
        li.setProperty("IsLiveTV", "1")
        li.setProperty("previewpath", url)
        _prepare_playback_item(li)
        _set_live_props(li)
        live_play_url = url
        ctx = _build_fav_ctx(
            item_id,
            name,
            "live",
            ch.get("logo", ""),
            url,
            tvg_id,
            pnum,
            ch.get("catchup", ""),
            ch.get("catchup_source", ""),
            ch.get("catchup_days", ""),
        )
        li.addContextMenuItems(ctx)
        q = {
            "mode": "play_stream",
            "url": live_play_url,
            "name": name,
            "title": current_title or name,
            "plot": plot,
            "icon": ch.get("logo", ""),
            "profile_num": pnum,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )

    if end < total:
        li = xbmcgui.ListItem(
            label="[COLOR yellow]{0} ({1})[/COLOR]".format(_t(30232), page + 1)
        )
        li.setArt({"icon": "DefaultFolder.png"})
        q = {
            "mode": "m3u_group",
            "group": group,
            "pnum": pnum,
            "page": page + 1,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
        )

    _apply_sort("live")
    xbmcplugin.endOfDirectory(addon_handle)


def _is_adult_locked(stype):
    """Check if adult content for this type requires PIN."""
    if addon.getSetting("enable_parental_control").lower() != "true":
        return False
    lock_map = {
        "live": "parental_lock_adult_live",
        "movie": "parental_lock_adult_movies",
        "series": "parental_lock_adult_series",
    }
    key = lock_map.get(stype, "")
    return key and addon.getSetting(key).lower() == "true"


def xtream_categories(stype, profile_num=None):
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    cats = _get_cached_xtream_categories(url, user, pwd, stype)
    show_counts = addon.getSetting("show_content_counts").lower() == "true"
    cat_counts = {}
    if show_counts:
        cat_counts = _cache_load(f"xtream_counts_{stype}") or {}
        if not cat_counts:
            # Fallback: compute once from streams, then cache for next time
            all_streams = _get_cached_xtream_streams(url, user, pwd, stype, None)
            cat_counts = {}
            for s in all_streams:
                cid = str(s.get("category_id", ""))
                cat_counts[cid] = cat_counts.get(cid, 0) + 1
            _cache_save(f"xtream_counts_{stype}", cat_counts)
    hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"
    adult_locked = _is_adult_locked(stype)
    hidden_subcats = _get_hidden_subcats(stype, pnum)
    for c in cats:
        name = c.get("category_name", "Unknown")
        cat_id = str(c.get("category_id", ""))
        if cat_id in hidden_subcats:
            continue
        if hide_adult and _is_adult_category(name):
            continue
        is_adult = _is_adult_category(name)
        count = cat_counts.get(cat_id, 0)
        if show_counts:
            display = f"{name}  [COLOR gray]({count})[/COLOR]"
        else:
            display = name
        if is_adult and adult_locked:
            display = f"[COLOR red]🔒[/COLOR] {display}"
        li = xbmcgui.ListItem(label=display)
        li.setArt({"icon": "DefaultFolder.png"})
        q = {
            "mode": "xtream_streams",
            "type": stype,
            "cat_id": c.get("category_id", ""),
            "adult": "1" if is_adult else "0",
            "profile_num": profile_num,
        }
        cat_url = build_url(q)
        # Allow adding category folders to global custom groups
        item_id = f"{stype}_cat_{cat_id}_p{pnum}"
        ctx = _build_fav_ctx(
            item_id,
            name,
            "folder",
            "DefaultFolder.png",
            cat_url,
            "",
            profile_num,
            is_folder=True,
        )
        li.addContextMenuItems(ctx)
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=cat_url, listitem=li, isFolder=True
        )
    # Note: _apply_sort intentionally NOT called here — category folders stay in provider order
    xbmcplugin.endOfDirectory(addon_handle)


def xtream_streams(stype, cat_id, page=1, adult="0", profile_num=None):
    if adult == "1" and _is_adult_locked(stype):
        if not _check_pin("Adult Content"):
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum) if profile_num else _get_credentials()
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    streams = _get_cached_xtream_streams(url, user, pwd, stype, cat_id)
    hidden_items = _get_hidden_items(stype, profile_num)
    if hidden_items:
        streams = [
            s for s in streams if str(s.get("stream_id", "")) not in hidden_items
        ]

    # Pre-sort by "added" timestamp when user selects "Newest first"
    if stype in ("movie", "series"):
        sort_key = f"sort_order_{stype}"
        if addon.getSetting(sort_key) == "Newest first":
            try:
                streams.sort(
                    key=lambda s: int(s.get("added", 0) or 0), reverse=True
                )
            except Exception:
                pass  # Malformed "added" field — keep provider order

    epg = EPG(addon, profile_num=pnum)
    epg.load()
    if epg.is_refreshing:
        _log("EPG background refresh in progress - showing cached/stale data")

    # Pagination from settings
    per_page = _get_pagination_limit(stype)
    if per_page == 0:
        per_page = len(streams)
    total = len(streams)
    start = (page - 1) * per_page
    end = start + per_page
    page_streams = streams[start:end]

    if stype == "movie" and url and user and pwd:
        if addon.getSetting("provider_movie_enabled").lower() == "true":
            _prefetch_vod_info_batch(page_streams, url, user, pwd)

    if stype == "live":
        xbmcplugin.setContent(addon_handle, "livetv")
    elif stype == "movie":
        xbmcplugin.setContent(addon_handle, "movies")
    elif stype == "series":
        xbmcplugin.setContent(addon_handle, "tvshows")
    show_epg = _epg_enabled() if stype == "live" else False
    wm = WatchedMovies(addon, profile_num=pnum) if stype == "movie" else None
    we = WatchedEpisodes(addon, profile_num=pnum) if stype == "series" else None
    for s in page_streams:
        name = s.get("name", "Unknown")
        if stype == "live":
            sid = str(s.get("stream_id", ""))
            epg_id = s.get("epg_channel_id") or sid
            play_url = IPTV.build_xtream_stream_url(url, user, pwd, s, "live")
            plot, display_name, current_title = (
                _make_epg_info(epg, epg_id, name) if show_epg else ("", name, "")
            )
            li = xbmcgui.ListItem(label=display_name)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(current_title or name)
            info_tag.setPlot(plot)
            if s.get("stream_icon"):
                li.setArt({"icon": s["stream_icon"], "thumb": s["stream_icon"]})
            li.setProperty("IsPlayable", "true")
            li.setProperty("IsLiveTV", "1")
            li.setProperty("previewpath", play_url)
            _prepare_playback_item(li)
            _set_live_props(li)
            catchup = "default" if s.get("tv_archive") or s.get("catchup") else ""
            catchup_source = (
                f"{url}/live/{user}/{pwd}/{sid}.ts?utc={{utc}}&lutc={{lutc}}"
                if (s.get("tv_archive") or s.get("catchup"))
                else ""
            )
            catchup_days = (
                str(s.get("tv_archive_duration", "") or "7")
                if (s.get("tv_archive") or s.get("catchup"))
                else ""
            )
            ctx = _build_fav_ctx(
                sid,
                name,
                "live",
                s.get("stream_icon", ""),
                play_url,
                epg_id,
                profile_num,
                catchup,
                catchup_source,
                catchup_days,
            )
            li.addContextMenuItems(ctx)
            q = {
                "mode": "play_stream",
                "url": play_url,
                "name": name,
                "title": current_title or name,
                "plot": plot,
                "icon": s.get("stream_icon", ""),
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )
        elif stype == "movie":
            sid = str(s.get("stream_id", ""))
            play_url = IPTV.build_xtream_stream_url(url, user, pwd, s, "movie")
            info = _enrich_movie_info(s, url, user, pwd)
            label = name
            li = xbmcgui.ListItem(label=label)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("movie")
            info_tag.setTitle(name)
            header_parts = []
            if info.get("year"):
                header_parts.append(info["year"])
            if info.get("genre"):
                header_parts.append(info["genre"])
            header = " | ".join(header_parts)
            plot = info["plot"]
            if info.get("cast"):
                cast_names = ", ".join([a["name"] for a in info["cast"][:5]])
                if header:
                    plot = f"{header}\n[COLOR gray]Cast: {cast_names}[/COLOR]\n\n{plot}"
                else:
                    plot = f"[COLOR gray]Cast: {cast_names}[/COLOR]\n\n{plot}"
            elif header:
                plot = f"{header}\n\n{plot}"
            info_tag.setPlot(plot)
            if info["rating"]:
                try:
                    info_tag.setRating(float(info["rating"]))
                except Exception as e:
                    _log(f"setRating warning: {e}")
            if info["year"]:
                try:
                    info_tag.setYear(int(info["year"]))
                except Exception as e:
                    _log(f"setYear warning: {e}")
            if info.get("duration"):
                try:
                    info_tag.setDuration(int(info["duration"]))
                except Exception as e:
                    _log(f"setDuration warning: {e}")
            if info.get("cast"):
                cast_list = []
                for idx, actor in enumerate(info["cast"][:10]):  # Top 10 actors
                    name = actor.get("name", "")
                    role = actor.get("role", "")
                    thumbnail = actor.get("thumbnail", "")
                    cast_list.append(xbmc.Actor(name, role, idx, thumbnail))
                if cast_list:
                    info_tag.setCast(cast_list)
            art = {}
            if info["poster_url"]:
                art["icon"] = info["poster_url"]
                art["thumb"] = info["poster_url"]
                art["poster"] = info["poster_url"]
            else:
                art["icon"] = "DefaultMovies.png"
            li.setArt(art)
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
            if wm and wm.is_watched(sid):
                info_tag.setPlaycount(1)
            ctx = _build_fav_ctx(
                sid,
                name,
                "movie",
                info.get("poster_url", ""),
                play_url,
                "",
                profile_num,
            )
            ctx.extend(_watched_ctx_movie(sid, profile_num, wm=wm))
            li.addContextMenuItems(ctx)
            q = {
                "mode": "play_stream",
                "url": play_url,
                "name": name,
                "title": name,
                "plot": plot,
                "icon": s.get("stream_icon", ""),
                "stype": "movie",
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )
        elif stype == "series":
            sid = str(s.get("series_id", ""))
            info = _enrich_series_info(s, url, user, pwd)
            label = name
            q = {"mode": "xtream_series", "series_id": sid, "profile_num": pnum}
            series_url = build_url(q)
            li = xbmcgui.ListItem(label=label)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("tvshow")
            info_tag.setTitle(name)
            header_parts = []
            if info.get("year"):
                header_parts.append(info["year"])
            if info.get("genre"):
                header_parts.append(info["genre"])
            header = " | ".join(header_parts)
            plot = info["plot"]
            if info.get("cast"):
                cast_names = ", ".join([a["name"] for a in info["cast"][:5]])
                if header:
                    plot = f"{header}\n[COLOR gray]Cast: {cast_names}[/COLOR]\n\n{plot}"
                else:
                    plot = f"[COLOR gray]Cast: {cast_names}[/COLOR]\n\n{plot}"
            elif header:
                plot = f"{header}\n\n{plot}"
            info_tag.setPlot(plot)
            if info["rating"]:
                try:
                    info_tag.setRating(float(info["rating"]))
                except Exception as e:
                    _log(f"setRating warning: {e}")
            if info["year"]:
                try:
                    info_tag.setYear(int(info["year"]))
                except Exception as e:
                    _log(f"setYear warning: {e}")
            if info.get("cast"):
                cast_list = []
                for idx, actor in enumerate(info["cast"][:10]):  # Top 10 actors
                    name = actor.get("name", "")
                    role = actor.get("role", "")
                    thumbnail = actor.get("thumbnail", "")
                    cast_list.append(xbmc.Actor(name, role, idx, thumbnail))
                if cast_list:
                    info_tag.setCast(cast_list)
            art = {}
            if info["poster_url"]:
                art["icon"] = info["poster_url"]
                art["thumb"] = info["poster_url"]
                art["poster"] = info["poster_url"]
            li.setArt(art)
            if we and we.get_watched_count(sid) > 0:
                info_tag.setPlaycount(1)
            ctx = _build_fav_ctx(
                sid,
                name,
                "series",
                info.get("poster_url", ""),
                series_url,
                "",
                profile_num,
            )
            ctx.extend(_watched_ctx_series(sid, profile_num, we=we))
            li.addContextMenuItems(ctx)
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=series_url, listitem=li, isFolder=True
            )

    if end < total:
        li = xbmcgui.ListItem(
            label="[COLOR yellow]{0} ({1})[/COLOR]".format(_t(30232), page + 1)
        )
        li.setArt({"icon": "DefaultFolder.png"})
        q = {
            "mode": "xtream_streams",
            "type": stype,
            "cat_id": cat_id,
            "page": page + 1,
        }
        if adult:
            q["adult"] = adult
        if profile_num is not None:
            q["profile_num"] = profile_num
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
        )

    _apply_sort(stype)
    xbmcplugin.endOfDirectory(addon_handle)


def xtream_series(series_id, profile_num=None):
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    info = IPTV.get_xtream_series_info(url, user, pwd, series_id)
    episodes = info.get("episodes", {})
    xbmcplugin.setContent(addon_handle, "seasons")
    we = WatchedEpisodes(addon, profile_num=pnum)

    # Provider metadata toggles for series
    use_prov = addon.getSetting("provider_series_enabled").lower() == "true"
    use_prov_plot = use_prov and (addon.getSetting("provider_series_plot").lower() == "true")
    use_prov_posters = use_prov and (addon.getSetting("provider_series_posters").lower() == "true")
    use_prov_ratings = use_prov and (addon.getSetting("provider_series_ratings").lower() == "true")
    use_prov_cast = use_prov and (addon.getSetting("provider_series_cast").lower() == "true")
    use_prov_genre = use_prov and (addon.getSetting("provider_series_genre").lower() == "true")
    use_prov_duration = use_prov and (addon.getSetting("provider_series_duration").lower() == "true")

    # Look up series metadata from API response or series list cache
    series_meta = info.get("info", {}) or {}
    if not series_meta.get("plot") and not series_meta.get("cover"):
        # Fall back to series list cache
        try:
            all_series = _cache_load("xtream_streams_series") or []
            for s in all_series:
                if str(s.get("series_id", "")) == str(series_id):
                    series_meta = s
                    break
        except Exception:
            pass  # Cache may be missing or corrupt; will be re-fetched

    # Extract metadata fields (respecting toggles)
    series_plot = ""
    if use_prov_plot:
        series_plot = (
            series_meta.get("plot", "")
            or series_meta.get("description", "")
            or info.get("plot", "")
            or ""
        )

    series_cover = ""
    if use_prov_posters:
        series_cover = (
            series_meta.get("cover", "")
            or series_meta.get("stream_icon", "")
            or series_meta.get("poster_url", "")
            or ""
        )

    series_backdrop = ""
    if use_prov_posters:
        bp = series_meta.get("backdrop_path", []) or info.get("backdrop_path", [])
        if bp and isinstance(bp, list) and bp[0]:
            series_backdrop = bp[0]

    series_rating = ""
    if use_prov_ratings:
        series_rating = str(
            series_meta.get("rating", "") or series_meta.get("rating_5based", "") or ""
        )

    series_year = ""
    if use_prov_ratings:
        release_raw = (
            series_meta.get("releaseDate", "")
            or series_meta.get("release_date", "")
            or series_meta.get("releasedate", "")
            or ""
        )
        if release_raw:
            series_year = str(release_raw)[:4]

    series_genre = ""
    if use_prov_genre:
        series_genre = series_meta.get("genre", "") or ""

    series_cast_str = ""
    if use_prov_cast:
        series_cast_str = series_meta.get("cast", "") or ""

    # episode_run_time may be string "60" or integer
    ep_run_time = 0
    if use_prov_duration:
        ep_run_time_raw = series_meta.get("episode_run_time", "") or ""
        try:
            ep_run_time = int(ep_run_time_raw) if ep_run_time_raw else 0
        except (ValueError, TypeError):
            ep_run_time = 0

    show_counts = addon.getSetting("show_content_counts").lower() == "true"
    for season_num in sorted(
        episodes.keys(), key=lambda x: (0, int(x)) if str(x).isdigit() else (1, str(x))
    ):
        eps = episodes.get(season_num, [])
        total_eps = len(eps)
        if show_counts and total_eps:
            label = f"{_t(30541, season_num)}  [COLOR gray]({total_eps})[/COLOR]"
        else:
            label = _t(30541, season_num)
        li = xbmcgui.ListItem(label=label)
        info_tag = li.getVideoInfoTag()
        info_tag.setMediaType("season")
        info_tag.setTitle(label)

        # Plot
        if use_prov_plot and series_plot:
            info_tag.setPlot(series_plot)

        # Season / Episode count
        try:
            info_tag.setSeason(int(season_num))
        except (ValueError, TypeError):
            pass
        if total_eps and show_counts:
            info_tag.setEpisode(total_eps)

        # Year
        if use_prov_ratings and series_year:
            try:
                info_tag.setYear(int(series_year))
            except (ValueError, TypeError):
                pass

        # Rating
        if use_prov_ratings and series_rating:
            try:
                info_tag.setRating(float(series_rating))
            except (ValueError, TypeError):
                pass

        # Cast
        if use_prov_cast and series_cast_str:
            cast_list = []
            for idx, actor_name in enumerate(series_cast_str.split(",")[:10]):
                name = actor_name.strip()
                if name:
                    cast_list.append(xbmc.Actor(name, "", idx, ""))
            if cast_list:
                info_tag.setCast(cast_list)

        # Duration: episode_run_time (minutes) * episode count, or sum of episode durations
        if use_prov_duration:
            season_duration = 0
            if ep_run_time and total_eps:
                season_duration = ep_run_time * total_eps * 60
            else:
                for ep in eps:
                    d = int(ep.get("info", {}).get("duration_secs", 0) or 0)
                    season_duration += d
            if season_duration:
                try:
                    info_tag.setDuration(int(season_duration))
                except Exception as e:
                    _log(f"setDuration warning (season): {e}")

        # Art
        art = {}
        if use_prov_posters and series_cover:
            art["icon"] = series_cover
            art["thumb"] = series_cover
            art["poster"] = series_cover
        else:
            art["icon"] = "DefaultFolder.png"
        if use_prov_posters and series_backdrop:
            art["fanart"] = series_backdrop
        li.setArt(art)

        if we.is_season_fully_watched(series_id, season_num, total_eps):
            info_tag.setPlaycount(1)
        ctx = _watched_ctx_season(series_id, season_num, total_eps, profile_num)
        li.addContextMenuItems(ctx)
        q = {
            "mode": "xtream_season",
            "series_id": series_id,
            "season_num": season_num,
            "profile_num": pnum,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
        )

    xbmcplugin.endOfDirectory(addon_handle)


def xtream_season(series_id, season_num, profile_num=None):
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    info = IPTV.get_xtream_series_info(url, user, pwd, series_id)
    eps = info.get("episodes", {}).get(season_num, [])
    xbmcplugin.setContent(addon_handle, "episodes")
    we = WatchedEpisodes(addon, profile_num=pnum)

    # Provider metadata toggles for series
    use_prov = addon.getSetting("provider_series_enabled").lower() == "true"
    use_prov_plot = use_prov and (addon.getSetting("provider_series_plot").lower() == "true")
    use_prov_posters = use_prov and (addon.getSetting("provider_series_posters").lower() == "true")
    use_prov_duration = use_prov and (addon.getSetting("provider_series_duration").lower() == "true")
    tmdb_enabled = addon.getSetting("tmdb_enabled").lower() == "true"
    use_tmdb_duration = addon.getSetting("tmdb_duration").lower() == "true" if tmdb_enabled else False

    for ep in eps:
        ep_id = str(ep.get("id", ""))
        title = ep.get("title") or _t(30542, ep.get("episode_num", "?"))
        label = title
        li = xbmcgui.ListItem(label=label)
        info_tag = li.getVideoInfoTag()
        info_tag.setMediaType("episode")
        info_tag.setTitle(title)

        # Plot
        if use_prov_plot:
            info_tag.setPlot(ep.get("info", {}).get("plot", ""))

        # Duration: provider first, then playback-discovered fallback
        ep_duration = 0
        if use_prov_duration:
            ep_duration = int(ep.get("info", {}).get("duration_secs", 0) or 0)
        if not ep_duration and (use_prov_duration or use_tmdb_duration) and ep_id:
            pb_dur = _load_playback_duration(ep_id)
            if pb_dur:
                ep_duration = pb_dur
        if ep_duration:
            try:
                info_tag.setDuration(ep_duration)
            except Exception as e:
                _log(f"setDuration warning: {e}")

        movie_image = ep.get("info", {}).get("movie_image")
        if use_prov_posters and movie_image:
            li.setArt({"icon": movie_image, "thumb": movie_image})
        li.setProperty("IsPlayable", "true")
        _prepare_playback_item(li)
        play_url = IPTV.build_xtream_stream_url(url, user, pwd, ep, "series")
        if we.is_watched(series_id, season_num, ep_id):
            info_tag.setPlaycount(1)
        ctx = _build_fav_ctx(
            ep_id,
            title,
            "series",
            movie_image or "",
            play_url,
            epg_id="",
            profile_num=pnum,
        )
        ctx.extend(_watched_ctx_episode(series_id, season_num, ep_id, profile_num))
        li.addContextMenuItems(ctx)
        q = {
            "mode": "play_stream",
            "url": play_url,
            "name": title,
            "icon": movie_image or "",
            "stype": "series",
            "series_id": series_id,
            "season_num": season_num,
            "ep_id": ep_id,
            "profile_num": profile_num,
        }
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
        )

    xbmcplugin.endOfDirectory(addon_handle)


def movies_menu(profile_num=None):
    original_active = pm.active
    if profile_num:
        pm.active = str(profile_num)
    try:
        creds = _get_credentials()
        xtream_url = creds.get("xtream_url", "")
        if xtream_url:
            recent_movies = _watch_history(pm.active).get_all("movie")
            if recent_movies:
                    li = xbmcgui.ListItem(
                        label="[COLOR gold]{0}[/COLOR]".format(_t(30230))
                    )
                    li.setArt({"icon": "DefaultMovies.png"})
                    xbmcplugin.addDirectoryItem(
                        handle=addon_handle,
                        url=build_url(
                            {
                                "mode": "recently_watched_by_type",
                                "stype": "movie",
                                "pnum": profile_num,
                            }
                        ),
                        listitem=li,
                        isFolder=True,
                    )

            li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30007)))
            li.setArt({"icon": "DefaultAddonsSearch.png"})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle,
                url=build_url(
                    {
                        "mode": "search_global",
                        "profile_num": profile_num,
                        "stype": "movie",
                    }
                ),
                listitem=li,
                isFolder=True,
            )
            xtream_categories("movie", profile_num)
        else:
            li = xbmcgui.ListItem(label=_t(30241))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
    finally:
        if profile_num:
            pm.active = original_active


def series_menu(profile_num=None):
    original_active = pm.active
    if profile_num:
        pm.active = str(profile_num)
    try:
        creds = _get_credentials()
        xtream_url = creds.get("xtream_url", "")
        if xtream_url:
            recent_series = _watch_history(pm.active).get_all("series")
            if recent_series:
                    li = xbmcgui.ListItem(
                        label="[COLOR gold]{0}[/COLOR]".format(_t(30230))
                    )
                    li.setArt({"icon": "DefaultTVShows.png"})
                    xbmcplugin.addDirectoryItem(
                        handle=addon_handle,
                        url=build_url(
                            {
                                "mode": "recently_watched_by_type",
                                "stype": "series",
                                "pnum": profile_num,
                            }
                        ),
                        listitem=li,
                        isFolder=True,
                    )

            li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30007)))
            li.setArt({"icon": "DefaultAddonsSearch.png"})
            xbmcplugin.addDirectoryItem(
                handle=addon_handle,
                url=build_url(
                    {
                        "mode": "search_global",
                        "profile_num": profile_num,
                        "stype": "series",
                    }
                ),
                listitem=li,
                isFolder=True,
            )
            xtream_categories("series", profile_num)
        else:
            li = xbmcgui.ListItem(label=_t(30242))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
    finally:
        if profile_num:
            pm.active = original_active


def replay_menu(profile_num=None):
    pnum = profile_num or pm.active
    original_active = pm.active
    if profile_num:
        pm.active = str(profile_num)
    try:
        creds = _get_credentials()
        url = creds.get("xtream_url", "")
        user = creds.get("xtream_username", "")
        pwd = creds.get("xtream_password", "")
        streams = _get_cached_xtream_streams(url, user, pwd, "live")
        epg = EPG(addon, profile_num=pnum)
        epg.load()

        for s in streams:
            if not s.get("tv_archive") and not s.get("catchup"):
                continue
            name = s.get("name", "Unknown")
            li = xbmcgui.ListItem(label=name)
            if s.get("stream_icon"):
                li.setArt({"icon": s["stream_icon"], "thumb": s["stream_icon"]})
            q = {
                "mode": "replay_channel",
                "stream_id": str(s.get("stream_id", "")),
                "epg_id": s.get("epg_channel_id") or str(s.get("stream_id", "")),
                "name": name,
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
            )

        m3u_url = creds.get("m3u_url", "")
        if m3u_url and not _m3u_has_credentials(m3u_url):
            m3u_channels = _get_cached_m3u_channels(m3u_url)
            for ch in m3u_channels:
                if not ch.get("catchup") and not ch.get("catchup_source"):
                    continue
                name = ch.get("name", "Unknown")
                li = xbmcgui.ListItem(label=f"[M3U] {name}")
                if ch.get("logo"):
                    li.setArt({"icon": ch["logo"], "thumb": ch["logo"]})
                q = {
                    "mode": "replay_channel_m3u",
                    "channel_name": name,
                    "epg_id": ch.get("tvg_id", ""),
                    "channel_url": ch.get("url", ""),
                    "catchup": ch.get("catchup", ""),
                    "catchup_source": ch.get("catchup_source", ""),
                    "logo": ch.get("logo", ""),
                    "profile_num": pnum,
                }
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
                )

        _apply_sort("live")
        xbmcplugin.endOfDirectory(addon_handle)
    finally:
        if profile_num:
            pm.active = original_active


def replay_channel(stream_id, epg_id, name="", profile_num=None):
    pnum = profile_num or pm.active
    epg = EPG(addon, profile_num=pnum)
    epg.load()
    try:
        days_back = int(addon.getSetting("replay_days") or "7")
    except ValueError:
        days_back = 7
    programs = epg.get_programs_for_channel(
        epg_id, channel_name=name, days_back=days_back
    )

    if not programs:
        now = datetime.datetime.now()
        for hours_back in range(1, 25):
            start = now - datetime.timedelta(hours=hours_back)
            start_fmt = start.strftime("%Y-%m-%d:%H-%M")
            title = f"{start.strftime('%d/%m %H:%M')} - {_t(30543)}"
            li = xbmcgui.ListItem(label=title)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(title)
            info_tag.setDuration(3600)
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
            q = {
                "mode": "replay_play",
                "stream_id": stream_id,
                "start": start_fmt,
                "duration": 3600,
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )
    else:
        for prog in programs:
            if _parse_xmltv_time(prog["start"]) > time.time():
                continue
            title = f"{prog['start_str']} - {prog['title']}"
            li = xbmcgui.ListItem(label=title)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(prog["title"])
            info_tag.setPlot(prog.get("desc", ""))
            info_tag.setDuration(int(prog["duration_sec"]))
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
            q = {
                "mode": "replay_play",
                "stream_id": stream_id,
                "start": prog["start_timestamp"],
                "duration": prog["duration_sec"],
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )

    xbmcplugin.endOfDirectory(addon_handle)


def replay_play(stream_id, start, duration, profile_num=None):
    pnum = profile_num or pm.active
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        duration = 3600
    play_url = IPTV.build_catchup_url(url, user, pwd, stream_id, start, duration)
    li = xbmcgui.ListItem(path=play_url)
    li.setProperty("IsPlayable", "true")
    info_tag = li.getVideoInfoTag()
    info_tag.setMediaType("video")
    info_tag.setTitle(f"Replay {stream_id}")
    _prepare_playback_item(li)
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=li)


def replay_channel_m3u(
    channel_name, epg_id, channel_url, catchup, catchup_source, logo, profile_num=None
):
    """Show replay/catchup programs for an M3U-based channel."""
    pnum = profile_num or pm.active
    epg = EPG(addon, profile_num=pnum)
    epg.load()
    try:
        days_back = int(addon.getSetting("replay_days") or "7")
    except ValueError:
        days_back = 7

    programs = epg.get_programs_for_channel(
        epg_id, channel_name=channel_name, days_back=days_back
    )

    if not programs:
        # No EPG data - show hourly slots going back

        now = datetime.datetime.now()
        for hours_back in range(1, 25):
            start = now - datetime.timedelta(hours=hours_back)
            start_ts = int(start.timestamp())
            end_ts = start_ts + 3600
            start_fmt = start.strftime("%Y-%m-%d:%H-%M")
            title = f"{start.strftime('%d/%m %H:%M')} - {_t(30543)}"
            li = xbmcgui.ListItem(label=title)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(title)
            info_tag.setDuration(3600)
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
            q = {
                "mode": "replay_play_m3u",
                "channel_name": channel_name,
                "channel_url": channel_url,
                "catchup": catchup,
                "catchup_source": catchup_source,
                "logo": logo,
                "start_ts": str(start_ts),
                "end_ts": str(end_ts),
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )
    else:
        for prog in programs:
            title = f"{prog['start_str']} - {prog['title']}"
            li = xbmcgui.ListItem(label=title)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(prog["title"])
            info_tag.setPlot(prog.get("desc", ""))
            info_tag.setDuration(int(prog["duration_sec"]))
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
            q = {
                "mode": "replay_play_m3u",
                "channel_name": channel_name,
                "channel_url": channel_url,
                "catchup": catchup,
                "catchup_source": catchup_source,
                "logo": logo,
                "start_ts": str(prog["start_timestamp"]),
                "end_ts": str(prog["start_timestamp"] + prog["duration_sec"]),
                "profile_num": pnum,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )

    xbmcplugin.endOfDirectory(addon_handle)


def replay_play_m3u(
    channel_name,
    channel_url,
    catchup,
    catchup_source,
    logo,
    start_ts,
    end_ts,
    profile_num=None,
):
    """Play M3U catchup stream."""
    channel_data = {
        "name": channel_name,
        "url": channel_url,
        "catchup": catchup,
        "catchup_source": catchup_source,
    }
    try:
        start_utc = int(start_ts)
        end_utc = int(end_ts)
    except (ValueError, TypeError):
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30730), xbmcgui.NOTIFICATION_ERROR
        )
        return

    play_url = IPTV.build_m3u_catchup_url(channel_data, start_utc, end_utc)
    if not play_url:
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30731), xbmcgui.NOTIFICATION_ERROR
        )
        return

    li = xbmcgui.ListItem(path=play_url)
    li.setProperty("IsPlayable", "true")
    info_tag = li.getVideoInfoTag()
    info_tag.setMediaType("video")
    info_tag.setTitle(f"Replay: {channel_name}")
    if logo:
        li.setArt({"icon": logo, "thumb": logo})
    _prepare_playback_item(li)
    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=li)


def _search_history_path(profile_num=None):
    profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if profile_num is None:
        return os.path.join(profile, "search_history.json")
    return os.path.join(profile, f"search_history_p{profile_num}.json")


def _load_search_history(profile_num=None):
    path = _search_history_path(profile_num)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_search_history(history, profile_num=None):
    history_path = _search_history_path(profile_num)
    tmp_file = history_path + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(history[:10], f, ensure_ascii=False)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp_file, history_path)


def search_global(query=None, profile_num=None, stype=None):
    try:
        # If profile not specified, ask user which profile to search
        if profile_num is None:
            profiles = []
            for i in range(1, 11):
                if addon.getSetting(f"profile_{i}_enabled") == "true":
                    name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
                    profiles.append((i, name))
            if not profiles:
                xbmcgui.Dialog().notification(_t(30770), _t(30074))
                xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                return
            options = [_t(30771)]  # All Profiles
            options.extend([p[1] for p in profiles])
            idx = xbmcgui.Dialog().select(_t(30140), options)
            if idx < 0:
                xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                return
            if idx == 0:
                # All Profiles
                if query is None:
                    history = _load_search_history()
                    if history:
                        hist_options = [_t(30544)] + history
                        idx2 = xbmcgui.Dialog().select(_t(30140), hist_options)
                        if idx2 < 0:
                            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                            return
                        if idx2 == 0:
                            kb = xbmcgui.Dialog().input(
                                _t(30140), type=xbmcgui.INPUT_ALPHANUM
                            )
                            if not kb:
                                xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                                return
                            query = kb
                        else:
                            query = history[idx2 - 1]
                    else:
                        kb = xbmcgui.Dialog().input(
                            _t(30140), type=xbmcgui.INPUT_ALPHANUM
                        )
                        if not kb:
                            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                            return
                        query = kb
                history = _load_search_history()
                if query in history:
                    history.remove(query)
                history.insert(0, query)
                _save_search_history(history)
                search_all_profiles(query)
                return
            else:
                profile_num = profiles[idx - 1][0]

        original_active = pm.active
        pm.active = str(profile_num)
        try:
            if query is None:
                history = _load_search_history()
                if history:
                    options = [_t(30544)] + history
                    idx = xbmcgui.Dialog().select(_t(30140), options)
                    if idx < 0:
                        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                        return
                    if idx == 0:
                        kb = xbmcgui.Dialog().input(
                            _t(30140), type=xbmcgui.INPUT_ALPHANUM
                        )
                        if not kb:
                            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                            return
                        query = kb
                    else:
                        query = history[idx - 1]
                else:
                    kb = xbmcgui.Dialog().input(_t(30140), type=xbmcgui.INPUT_ALPHANUM)
                    if not kb:
                        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                        return
                    query = kb
            history = _load_search_history()
            if query in history:
                history.remove(query)
            history.insert(0, query)
            _save_search_history(history)

            creds = _get_credentials()
            has_xtream = bool(creds.get("xtream_url"))
            has_m3u = bool(creds.get("m3u_url"))

            if has_xtream:
                unified_search(query, stype=stype)
            elif has_m3u:
                search_m3u(query, stype=stype)
            else:
                xbmcgui.Dialog().notification(_t(30770), _t(30223))
                xbmcplugin.endOfDirectory(addon_handle)
        finally:
            pm.active = original_active
    except Exception as e:
        _log(f"search_global error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def unified_search(query, stype=None):
    creds = _get_credentials()
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    qlower = query.lower()
    epg = EPG(addon, profile_num=pm.active)
    epg.load()
    show_epg = _epg_enabled()
    hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"

    stype_labels = {
        "live": _t(30220),
        "movie": _t(30004),
        "series": _t(30005),
    }
    stype_icons = {
        "live": "DefaultAddonPVRClient.png",
        "movie": "DefaultMovies.png",
        "series": "DefaultTVShows.png",
    }

    results = {}

    if stype is None or stype == "live":
        live_streams = _get_cached_xtream_streams(url, user, pwd, "live")
        live_results = [s for s in live_streams if qlower in s.get("name", "").lower()]
        if hide_adult:
            live_results = [
                s
                for s in live_results
                if not _is_adult_category(
                    s.get("name", "") + " " + s.get("category_name", "")
                )
            ]
        results["live"] = live_results

    if stype is None or stype == "movie":
        movie_streams = _get_cached_xtream_streams(url, user, pwd, "movie")
        movie_results = [
            s for s in movie_streams if qlower in s.get("name", "").lower()
        ]
        if hide_adult:
            movie_results = [
                s
                for s in movie_results
                if not _is_adult_category(
                    s.get("name", "") + " " + s.get("category_name", "")
                )
            ]
        results["movie"] = movie_results

    if stype is None or stype == "series":
        series_streams = _get_cached_xtream_streams(url, user, pwd, "series")
        series_results = [
            s for s in series_streams if qlower in s.get("name", "").lower()
        ]
        if hide_adult:
            series_results = [
                s
                for s in series_results
                if not _is_adult_category(
                    s.get("name", "") + " " + s.get("category_name", "")
                )
            ]
        results["series"] = series_results

    has_any = any(results.values())
    if not has_any:
        li = xbmcgui.ListItem(label=_t(30223))
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url="", listitem=li, isFolder=False
        )
        xbmcplugin.endOfDirectory(addon_handle)
        return

    show_separators = len([v for v in results.values() if v]) > 1 and stype is None
    type_order = ["live", "movie", "series"]

    for t in type_order:
        if t not in results or not results[t]:
            continue
        if show_separators:
            sep = xbmcgui.ListItem(
                label=f"[COLOR gray]────── {stype_labels.get(t, t)} ──────[/COLOR]"
            )
            sep.setArt({"icon": stype_icons.get(t, "DefaultFolder.png")})
            sep.setProperty("IsPlayable", "false")
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=sep, isFolder=False
            )
        for s in results[t]:
            name = s.get("name", "Unknown")
            sid = str(s.get("stream_id", ""))
            if t == "live":
                epg_id = s.get("epg_channel_id") or sid
                play_url = IPTV.build_xtream_stream_url(url, user, pwd, s, "live")
                plot, display_name, current_title = (
                    _make_epg_info(epg, epg_id, name) if show_epg else ("", name, "")
                )
                li = xbmcgui.ListItem(label=display_name)
                info_tag = li.getVideoInfoTag()
                info_tag.setMediaType("video")
                info_tag.setTitle(current_title or name)
                info_tag.setPlot(plot)
                if s.get("stream_icon"):
                    li.setArt(
                        {
                            "icon": s["stream_icon"],
                            "thumb": s["stream_icon"],
                            "poster": s["stream_icon"],
                        }
                    )
                li.setProperty("IsPlayable", "true")
                _prepare_playback_item(li)
                _set_live_props(li)
                ctx = _build_fav_ctx(
                    sid, name, "live", s.get("stream_icon", ""), play_url, epg_id
                )
                li.addContextMenuItems(ctx)
                q = {
                    "mode": "play_stream",
                    "url": play_url,
                    "name": name,
                    "title": current_title or name,
                    "plot": plot,
                    "icon": s.get("stream_icon", ""),
                    "profile_num": pm.active,
                }
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
                )
            elif t == "movie":
                play_url = IPTV.build_xtream_stream_url(url, user, pwd, s, "movie")
                info = _enrich_movie_info(s, url, user, pwd)
                li = xbmcgui.ListItem(label=name)
                info_tag = li.getVideoInfoTag()
                info_tag.setMediaType("movie")
                info_tag.setTitle(name)
                plot = info.get("plot", "")
                info_tag.setPlot(plot)
                art = {}
                if info.get("poster_url"):
                    art["icon"] = info["poster_url"]
                    art["thumb"] = info["poster_url"]
                    art["poster"] = info["poster_url"]
                else:
                    art["icon"] = "DefaultMovies.png"
                li.setArt(art)
                li.setProperty("IsPlayable", "true")
                _prepare_playback_item(li)
                ctx = _build_fav_ctx(
                    sid,
                    name,
                    "movie",
                    info.get("poster_url", ""),
                    play_url,
                    "",
                    pm.active,
                )
                li.addContextMenuItems(ctx)
                q = {
                    "mode": "play_stream",
                    "url": play_url,
                    "name": name,
                    "title": name,
                    "plot": plot,
                    "icon": s.get("stream_icon", ""),
                    "stype": "movie",
                    "profile_num": pm.active,
                }
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
                )
            elif t == "series":
                q_series = {
                    "mode": "xtream_series",
                    "series_id": sid,
                    "profile_num": pm.active,
                }
                li = xbmcgui.ListItem(label=name)
                info_tag = li.getVideoInfoTag()
                info_tag.setMediaType("tvshow")
                info_tag.setTitle(name)
                if s.get("cover"):
                    li.setArt(
                        {"icon": s["cover"], "thumb": s["cover"], "poster": s["cover"]}
                    )
                li.addContextMenuItems(
                    _build_fav_ctx(
                        sid,
                        name,
                        "series",
                        s.get("cover", ""),
                        build_url(q_series),
                        "",
                        pm.active,
                    )
                )
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle,
                    url=build_url(q_series),
                    listitem=li,
                    isFolder=True,
                )

    xbmcplugin.endOfDirectory(addon_handle)


def search_m3u(query=None, stype=None):
    try:
        if query is None:
            kb = xbmcgui.Dialog().input(_t(30141), type=xbmcgui.INPUT_ALPHANUM)
            if not kb:
                xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                return
            query = kb
        if stype in ("movie", "series"):
            li = xbmcgui.ListItem(label=_t(30223))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
            return
        show_epg = _epg_enabled()
        epg = EPG(addon, profile_num=pm.active)
        if show_epg:
            epg.load()
        creds = _get_credentials()
        channels = _get_cached_m3u_channels(creds.get("m3u_url", ""))
        qlower = query.lower()
        for ch in channels:
            if (
                qlower not in ch.get("name", "").lower()
                and qlower not in ch.get("group", "").lower()
            ):
                continue
            name = ch.get("name", "Unknown")
            tvg_id = ch.get("tvg_id") or name
            url = ch.get("url")
            item_id = ch.get("tvg_id") or url
            plot, display_name, current_title = (
                _make_epg_info(epg, tvg_id, name) if show_epg else ("", name, "")
            )
            li = xbmcgui.ListItem(label=display_name)
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(current_title or name)
            info_tag.setPlot(plot)
            if ch.get("logo"):
                li.setArt({"icon": ch["logo"], "thumb": ch["logo"]})
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
            _set_live_props(li)
            ctx = _build_fav_ctx(
                item_id,
                name,
                "live",
                ch.get("logo", ""),
                url,
                tvg_id,
                None,
                ch.get("catchup", ""),
                ch.get("catchup_source", ""),
                ch.get("catchup_days", ""),
            )
            li.addContextMenuItems(ctx)
            q = {
                "mode": "play_stream",
                "url": url,
                "name": name,
                "title": current_title or name,
                "plot": plot,
                "icon": ch.get("logo", ""),
                "profile_num": pm.active,
            }
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=False
            )
        _apply_sort("live")
        xbmcplugin.endOfDirectory(addon_handle)
    except Exception as e:
        _log(f"search_m3u error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def search_all_profiles(query):
    """Search across all enabled profiles and show results grouped by profile."""
    try:
        hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"

        profiles = []
        for i in range(1, 11):
            if addon.getSetting(f"profile_{i}_enabled") == "true":
                name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
                profiles.append((i, name))

        if not profiles:
            xbmcgui.Dialog().notification(_t(30770), _t(30074))
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return

        li = xbmcgui.ListItem(label="[COLOR gold]{0}[/COLOR]".format(_t(30771)))
        li.setArt({"icon": "DefaultFolder.png"})
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url(
                {
                    "mode": "search_all_combined",
                    "query": query,
                }
            ),
            listitem=li,
            isFolder=True,
        )

        any_results = False
        for profile_num, profile_name in profiles:
            original_active = pm.active
            pm.active = str(profile_num)
            try:
                creds = _get_credentials()
                has_xtream = bool(creds.get("xtream_url"))
                has_m3u = bool(creds.get("m3u_url"))

                if not has_xtream and not has_m3u:
                    continue

                has_results = False
                qlower = query.lower()

                if has_xtream:
                    url = creds.get("xtream_url", "")
                    user = creds.get("xtream_username", "")
                    pwd = creds.get("xtream_password", "")

                    live_streams = _get_cached_xtream_streams(url, user, pwd, "live")
                    live_results = [
                        s for s in live_streams if qlower in s.get("name", "").lower()
                    ]
                    if hide_adult:
                        live_results = [
                            s
                            for s in live_results
                            if not _is_adult_category(
                                s.get("name", "") + " " + s.get("category_name", "")
                            )
                        ]

                    movie_streams = _get_cached_xtream_streams(url, user, pwd, "movie")
                    movie_results = [
                        s for s in movie_streams if qlower in s.get("name", "").lower()
                    ]
                    if hide_adult:
                        movie_results = [
                            s
                            for s in movie_results
                            if not _is_adult_category(
                                s.get("name", "") + " " + s.get("category_name", "")
                            )
                        ]

                    series_streams = _get_cached_xtream_streams(
                        url, user, pwd, "series"
                    )
                    series_results = [
                        s for s in series_streams if qlower in s.get("name", "").lower()
                    ]
                    if hide_adult:
                        series_results = [
                            s
                            for s in series_results
                            if not _is_adult_category(
                                s.get("name", "") + " " + s.get("category_name", "")
                            )
                        ]

                    if live_results or movie_results or series_results:
                        has_results = True

                elif has_m3u:
                    channels = _get_cached_m3u_channels(creds.get("m3u_url", ""))
                    for ch in channels:
                        if (
                            qlower in ch.get("name", "").lower()
                            or qlower in ch.get("group", "").lower()
                        ):
                            has_results = True
                            break

                if has_results:
                    any_results = True
                    li = xbmcgui.ListItem(label=profile_name)
                    li.setArt({"icon": "DefaultAddonPVRClient.png"})
                    xbmcplugin.addDirectoryItem(
                        handle=addon_handle,
                        url=build_url(
                            {
                                "mode": "search_global",
                                "profile_num": profile_num,
                                "query": query,
                            }
                        ),
                        listitem=li,
                        isFolder=True,
                    )
            finally:
                pm.active = original_active

        if not any_results:
            li = xbmcgui.ListItem(label=_t(30223))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )

        xbmcplugin.endOfDirectory(addon_handle)
    except Exception as e:
        _log(f"search_all_profiles error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def search_all_profiles_combined(query):
    """Show combined search results from all enabled profiles."""
    try:
        hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"
        show_epg = _epg_enabled()

        qlower = query.lower()
        has_any = False

        profiles = []
        for i in range(1, 11):
            if addon.getSetting(f"profile_{i}_enabled") == "true":
                name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
                profiles.append((i, name))

        for profile_num, profile_name in profiles:
            original_active = pm.active
            pm.active = str(profile_num)
            try:
                epg = EPG(addon, profile_num=profile_num)
                if show_epg:
                    epg.load()
                    if epg.is_refreshing:
                        _log(
                            "EPG background refresh in progress - showing cached/stale data"
                        )
                creds = _get_credentials()
                has_xtream = bool(creds.get("xtream_url"))
                has_m3u = bool(creds.get("m3u_url"))

                if not has_xtream and not has_m3u:
                    continue

                if has_xtream:
                    url = creds.get("xtream_url", "")
                    user = creds.get("xtream_username", "")
                    pwd = creds.get("xtream_password", "")

                    live_streams = _get_cached_xtream_streams(url, user, pwd, "live")
                    live_results = [
                        s for s in live_streams if qlower in s.get("name", "").lower()
                    ]
                    if hide_adult:
                        live_results = [
                            s
                            for s in live_results
                            if not _is_adult_category(
                                s.get("name", "") + " " + s.get("category_name", "")
                            )
                        ]

                    movie_streams = _get_cached_xtream_streams(url, user, pwd, "movie")
                    movie_results = [
                        s for s in movie_streams if qlower in s.get("name", "").lower()
                    ]
                    if hide_adult:
                        movie_results = [
                            s
                            for s in movie_results
                            if not _is_adult_category(
                                s.get("name", "") + " " + s.get("category_name", "")
                            )
                        ]

                    series_streams = _get_cached_xtream_streams(
                        url, user, pwd, "series"
                    )
                    series_results = [
                        s for s in series_streams if qlower in s.get("name", "").lower()
                    ]
                    if hide_adult:
                        series_results = [
                            s
                            for s in series_results
                            if not _is_adult_category(
                                s.get("name", "") + " " + s.get("category_name", "")
                            )
                        ]

                    profile_header_added = False
                    if live_results:
                        has_any = True
                        if not profile_header_added:
                            profile_header_added = True
                            header = xbmcgui.ListItem(
                                label="[COLOR yellow]{0}[/COLOR]".format(profile_name)
                            )
                            header.setArt({"icon": "DefaultAddonPVRClient.png"})
                            header.setProperty("IsPlayable", "false")
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url="",
                                listitem=header,
                                isFolder=False,
                            )
                        sep = xbmcgui.ListItem(
                            label="[COLOR gray]────── {0} ──────[/COLOR]".format(
                                _t(30220)
                            )
                        )
                        sep.setArt({"icon": "DefaultAddonPVRClient.png"})
                        sep.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(
                            handle=addon_handle, url="", listitem=sep, isFolder=False
                        )
                        for s in live_results:
                            name = s.get("name", "Unknown")
                            sid = str(s.get("stream_id", ""))
                            epg_id = s.get("epg_channel_id") or sid
                            play_url = IPTV.build_xtream_stream_url(
                                url, user, pwd, s, "live"
                            )
                            plot, display_name, current_title = (
                                _make_epg_info(epg, epg_id, name)
                                if show_epg
                                else ("", name, "")
                            )
                            li = xbmcgui.ListItem(label=display_name)
                            info_tag = li.getVideoInfoTag()
                            info_tag.setMediaType("video")
                            info_tag.setTitle(current_title or name)
                            info_tag.setPlot(plot)
                            if s.get("stream_icon"):
                                li.setArt(
                                    {
                                        "icon": s["stream_icon"],
                                        "thumb": s["stream_icon"],
                                        "poster": s["stream_icon"],
                                    }
                                )
                            li.setProperty("IsPlayable", "true")
                            _prepare_playback_item(li)
                            _set_live_props(li)
                            ctx = _build_fav_ctx(
                                sid,
                                name,
                                "live",
                                s.get("stream_icon", ""),
                                play_url,
                                epg_id,
                            )
                            li.addContextMenuItems(ctx)
                            q = {
                                "mode": "play_stream",
                                "url": play_url,
                                "name": name,
                                "title": current_title or name,
                                "plot": plot,
                                "icon": s.get("stream_icon", ""),
                                "profile_num": profile_num,
                            }
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url=build_url(q),
                                listitem=li,
                                isFolder=False,
                            )

                    if movie_results:
                        has_any = True
                        if not profile_header_added:
                            profile_header_added = True
                            header = xbmcgui.ListItem(
                                label="[COLOR yellow]{0}[/COLOR]".format(profile_name)
                            )
                            header.setArt({"icon": "DefaultAddonPVRClient.png"})
                            header.setProperty("IsPlayable", "false")
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url="",
                                listitem=header,
                                isFolder=False,
                            )
                        sep = xbmcgui.ListItem(
                            label="[COLOR gray]────── {0} ──────[/COLOR]".format(
                                _t(30221)
                            )
                        )
                        sep.setArt({"icon": "DefaultMovies.png"})
                        sep.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(
                            handle=addon_handle, url="", listitem=sep, isFolder=False
                        )
                        for s in movie_results:
                            name = s.get("name", "Unknown")
                            sid = str(s.get("stream_id", ""))
                            play_url = IPTV.build_xtream_stream_url(
                                url, user, pwd, s, "movie"
                            )
                            info = _enrich_movie_info(s, url, user, pwd)
                            li = xbmcgui.ListItem(label=name)
                            info_tag = li.getVideoInfoTag()
                            info_tag.setMediaType("movie")
                            info_tag.setTitle(name)
                            header_parts = []
                            if info.get("year"):
                                header_parts.append(info["year"])
                            if info.get("genre"):
                                header_parts.append(info["genre"])
                            header = " | ".join(header_parts)
                            plot = info["plot"]
                            if info.get("cast"):
                                cast_names = ", ".join(
                                    [a["name"] for a in info["cast"][:5]]
                                )
                                if header:
                                    plot = f"{header}\n[COLOR gray]Cast: {cast_names}[/COLOR]\n\n{plot}"
                                else:
                                    plot = f"[COLOR gray]Cast: {cast_names}[/COLOR]\n\n{plot}"
                            elif header:
                                plot = f"{header}\n\n{plot}"
                            info_tag.setPlot(plot)
                            if info["rating"]:
                                try:
                                    info_tag.setRating(float(info["rating"]))
                                except (ValueError, TypeError):
                                    pass  # Rating malformed or None, skip
                            if info["year"]:
                                try:
                                    info_tag.setYear(int(info["year"]))
                                except (ValueError, TypeError):
                                    pass  # Year malformed or None, skip
                            if info.get("cast"):
                                cast_list = []
                                for idx, actor in enumerate(info["cast"][:10]):
                                    cast_list.append(
                                        xbmc.Actor(
                                            actor.get("name", ""),
                                            actor.get("role", ""),
                                            idx,
                                            actor.get("thumbnail", ""),
                                        )
                                    )
                                if cast_list:
                                    info_tag.setCast(cast_list)
                            art = {}
                            if info["poster_url"]:
                                art = {
                                    "icon": info["poster_url"],
                                    "thumb": info["poster_url"],
                                    "poster": info["poster_url"],
                                }
                            li.setArt(art)
                            li.setProperty("IsPlayable", "true")
                            _prepare_playback_item(li)
                            ctx = _build_fav_ctx(
                                sid, name, "movie", info.get("poster_url", ""), play_url
                            )
                            li.addContextMenuItems(ctx)
                            q = {
                                "mode": "play_stream",
                                "url": play_url,
                                "name": name,
                                "icon": info.get("poster_url", ""),
                                "stype": "movie",
                                "profile_num": profile_num,
                            }
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url=build_url(q),
                                listitem=li,
                                isFolder=False,
                            )

                    if series_results:
                        has_any = True
                        if not profile_header_added:
                            profile_header_added = True
                            header = xbmcgui.ListItem(
                                label="[COLOR yellow]{0}[/COLOR]".format(profile_name)
                            )
                            header.setArt({"icon": "DefaultAddonPVRClient.png"})
                            header.setProperty("IsPlayable", "false")
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url="",
                                listitem=header,
                                isFolder=False,
                            )
                        sep = xbmcgui.ListItem(
                            label="[COLOR gray]────── {0} ──────[/COLOR]".format(
                                _t(30222)
                            )
                        )
                        sep.setArt({"icon": "DefaultTVShows.png"})
                        sep.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(
                            handle=addon_handle, url="", listitem=sep, isFolder=False
                        )
                        for s in series_results:
                            name = s.get("name", "Unknown")
                            sid = str(s.get("series_id", ""))
                            series_url = build_url(
                                {"mode": "xtream_series", "series_id": sid}
                            )
                            li = xbmcgui.ListItem(label=name)
                            info_tag = li.getVideoInfoTag()
                            info_tag.setMediaType("tvshow")
                            info_tag.setTitle(name)
                            info_tag.setPlot(s.get("plot", ""))
                            if s.get("cover"):
                                li.setArt({"icon": s["cover"], "thumb": s["cover"]})
                            ctx = _build_fav_ctx(
                                sid, name, "series", s.get("cover", ""), series_url
                            )
                            li.addContextMenuItems(ctx)
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url=series_url,
                                listitem=li,
                                isFolder=True,
                            )

                elif has_m3u:
                    channels = _get_cached_m3u_channels(creds.get("m3u_url", ""))
                    m3u_results = [
                        ch
                        for ch in channels
                        if qlower in ch.get("name", "").lower()
                        or qlower in ch.get("group", "").lower()
                    ]
                    if m3u_results:
                        has_any = True
                        header = xbmcgui.ListItem(
                            label="[COLOR yellow]{0}[/COLOR]".format(profile_name)
                        )
                        header.setArt({"icon": "DefaultAddonPVRClient.png"})
                        header.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(
                            handle=addon_handle, url="", listitem=header, isFolder=False
                        )
                        sep = xbmcgui.ListItem(
                            label="[COLOR gray]────── {0} ──────[/COLOR]".format(
                                _t(30220)
                            )
                        )
                        sep.setArt({"icon": "DefaultAddonPVRClient.png"})
                        sep.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(
                            handle=addon_handle, url="", listitem=sep, isFolder=False
                        )
                        for ch in m3u_results:
                            name = ch.get("name", "Unknown")
                            tvg_id = ch.get("tvg_id") or name
                            url = ch.get("url")
                            item_id = ch.get("tvg_id") or url
                            plot, display_name, current_title = (
                                _make_epg_info(epg, tvg_id, name)
                                if show_epg
                                else ("", name, "")
                            )
                            li = xbmcgui.ListItem(label=display_name)
                            info_tag = li.getVideoInfoTag()
                            info_tag.setMediaType("video")
                            info_tag.setTitle(current_title or name)
                            info_tag.setPlot(plot)
                            if ch.get("logo"):
                                li.setArt({"icon": ch["logo"], "thumb": ch["logo"]})
                            li.setProperty("IsPlayable", "true")
                            _prepare_playback_item(li)
                            _set_live_props(li)
                            ctx = _build_fav_ctx(
                                item_id,
                                name,
                                "live",
                                ch.get("logo", ""),
                                url,
                                tvg_id,
                            )
                            li.addContextMenuItems(ctx)
                            q = {
                                "mode": "play_stream",
                                "url": url,
                                "name": name,
                                "title": current_title or name,
                                "plot": plot,
                                "icon": ch.get("logo", ""),
                                "profile_num": profile_num,
                            }
                            xbmcplugin.addDirectoryItem(
                                handle=addon_handle,
                                url=build_url(q),
                                listitem=li,
                                isFolder=False,
                            )
            finally:
                pm.active = original_active

        if not has_any:
            li = xbmcgui.ListItem(label=_t(30223))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )

        xbmcplugin.endOfDirectory(addon_handle)
    except Exception as e:
        _log(f"search_all_profiles_combined error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def _fav_render_items(items, source_folder=None, profile_num=None):
    """Render a list of favorite items with context menus."""
    # Use profile-specific fav instance if profile_num provided
    if profile_num:
        fav_instance = _get_profile_fav(profile_num)
        remove_mode = "profile_fav_remove"
    else:
        fav_instance = fav
        remove_mode = "fav_remove"

    hide_adult = addon.getSetting("hide_adult_categories").lower() == "true"
    if hide_adult:
        items = [
            i
            for i in items
            if not _is_adult_category(
                i.get("name", "") + " " + i.get("category_name", "")
            )
        ]
    has_live = any(i.get("stype", "live") == "live" for i in items)
    epg = None
    if has_live and _epg_enabled():
        epg = EPG(addon, profile_num=profile_num or pm.active)
        epg.load()
    for item in items:
        stype = item.get("stype", "live")
        name = item.get("name", "Unknown")
        li = xbmcgui.ListItem(label=name)
        info_tag = li.getVideoInfoTag()
        info_tag.setMediaType("video")
        info_tag.setTitle(name)
        if item.get("icon"):
            li.setArt({"icon": item["icon"], "thumb": item["icon"]})
        if stype != "folder":
            li.setProperty("IsPlayable", "true")
            _prepare_playback_item(li)
        plot = ""
        current_title = ""
        if stype == "live":
            _set_live_props(li)
            plot, display_name, current_title = (
                _make_epg_info(epg, item.get("epg_id", ""), name)
                if epg
                else ("", name, "")
            )
            info_tag = li.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(current_title or name)
            info_tag.setPlot(plot)
        remove_folder = source_folder or "__all__"
        if profile_num:
            ctx = [
                (
                    _t(30545),
                    f"RunPlugin({build_url({'mode': remove_mode, 'id': item.get('id'), 'folder': remove_folder, 'pnum': profile_num})})",
                ),
            ]
        else:
            ctx = [
                (
                    _t(30545),
                    f"RunPlugin({build_url({'mode': remove_mode, 'id': item.get('id'), 'folder': remove_folder})})",
                ),
            ]
        if not profile_num:
            protected_folders = {"Favorites", _t(30009) or "Favorites"}
            for gname in fav_instance.get_folders():
                if gname in protected_folders:
                    continue
                ctx.append(
                    (
                        _t(30215).format(gname),
                        f"RunPlugin({build_url({'mode': 'toggle_fav', 'id': item.get('id'), 'name': name, 'stype': stype, 'icon': item.get('icon', ''), 'url': item.get('url', ''), 'epg_id': item.get('epg_id', ''), 'folder': gname})})",
                    )
                )
        li.addContextMenuItems(ctx)
        if stype == "live":
            q = {
                "mode": "play_stream",
                "url": item.get("url"),
                "name": name,
                "title": current_title or name,
                "plot": plot,
                "icon": item.get("icon", ""),
                "profile_num": profile_num or pm.active,
            }
            item_url = build_url(q)
        else:
            item_url = item.get("url")
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=item_url,
            listitem=li,
            isFolder=stype in ("series", "folder"),
        )


def profile_favorites_menu(pnum):
    """Show favorites for a specific profile (profile-specific favorites), organized by type."""
    profile_fav = _get_profile_fav(pnum)

    stype_labels = {"live": _t(30360), "movie": _t(30361), "series": _t(30362)}
    stype_icons = {
        "live": "DefaultAddonPVRClient.png",
        "movie": "DefaultMovies.png",
        "series": "DefaultTVShows.png",
    }

    all_items = profile_fav.get_all()
    if not all_items:
        li = xbmcgui.ListItem(label="[COLOR gray]{0}[/COLOR]".format(_t(30211)))
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url="", listitem=li, isFolder=False
        )
        xbmcplugin.endOfDirectory(addon_handle)
        return

    items_by_type = {"live": [], "movie": [], "series": []}
    for item in all_items:
        stype = item.get("stype", "live")
        if stype in items_by_type:
            items_by_type[stype].append(item)

    show_counts = addon.getSetting("show_content_counts").lower() == "true"
    for stype in ["live", "movie", "series"]:
        items = items_by_type[stype]
        if items:
            count = len(items)
            if show_counts:
                label = f"{stype_labels[stype]}  [COLOR gray]({count})[/COLOR]"
            else:
                label = stype_labels[stype]
            li = xbmcgui.ListItem(label=label)
            li.setArt({"icon": stype_icons[stype]})
            q = {"mode": "profile_favorites_by_type", "pnum": pnum, "stype": stype}
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
            )

    xbmcplugin.endOfDirectory(addon_handle)


def favorites_menu(folder=None, stype_filter=None):
    # Use translated labels, falling back to English if translation missing
    stype_labels = {
        "live": _t(30002),
        "movie": _t(30004),
        "series": _t(30005),
        "folder": _t(30808),
    }
    stype_icons = {
        "live": "DefaultAddonPVRClient.png",
        "movie": "DefaultMovies.png",
        "series": "DefaultTVShows.png",
        "folder": "DefaultFolder.png",
    }
    folders = fav.get_folders()
    protected_folders = {"Favorites", _t(30009) or "Favorites"}
    custom_folders = [f for f in folders if f not in protected_folders]

    show_counts = addon.getSetting("show_content_counts").lower() == "true"
    if folder is None and stype_filter is None:
        for gname in custom_folders:
            count = len(fav.get_all(gname))
            if show_counts:
                label = f"{gname}  [COLOR gray]({count})[/COLOR]"
            else:
                label = gname
            li = xbmcgui.ListItem(label=label)
            li.setArt({"icon": "DefaultFavourites.png"})
            ctx_items = [
                (
                    _t(30320),
                    f"RunPlugin({build_url({'mode': 'fav_rename_folder', 'folder': gname})})",
                ),
                (
                    _t(30325),
                    f"RunPlugin({build_url({'mode': 'export_favorites', 'folder': gname})})",
                ),
                (
                    _t(30321),
                    f"RunPlugin({build_url({'mode': 'fav_delete_folder', 'folder': gname})})",
                ),
            ]
            li.addContextMenuItems(ctx_items)
            q = {"mode": "favorites_menu", "folder": gname}
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url=build_url(q), listitem=li, isFolder=True
            )
        # + New Favorites Group
        li = xbmcgui.ListItem(label="[COLOR yellow]{0}[/COLOR]".format(_t(30210)))
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({"mode": "fav_new_folder"}),
            listitem=li,
            isFolder=False,
        )
        xbmcplugin.endOfDirectory(addon_handle)
        return

    # Inside a custom group — show all items flat with visual type separators
    if folder and stype_filter is None:
        items = fav.get_all(folder)
        if not items:
            li = xbmcgui.ListItem(label="[COLOR gray]{0}[/COLOR]".format(_t(30211)))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
            return

        type_order = ["live", "movie", "series", "folder"]
        items_by_type = {}
        for item in items:
            st = item.get("stype", "live")
            items_by_type.setdefault(st, []).append(item)

        show_separators = len(items_by_type) > 1
        for st in type_order:
            if st not in items_by_type:
                continue
            if show_separators:
                label = stype_labels.get(st, st)
                sep = xbmcgui.ListItem(
                    label=f"[COLOR gray]────── {label} ──────[/COLOR]"
                )
                sep.setArt({"icon": stype_icons.get(st, "DefaultFolder.png")})
                sep.setProperty("IsPlayable", "false")
                ctx = [
                    (
                        _t(30813).format(label),
                        f"RunPlugin({build_url({'mode': 'fav_remove_by_type', 'folder': folder, 'stype': st})})",
                    )
                ]
                sep.addContextMenuItems(ctx)
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle, url="", listitem=sep, isFolder=False
                )
            _fav_render_items(items_by_type[st], source_folder=folder)

        xbmcplugin.endOfDirectory(addon_handle)
        return

    # Items in custom group filtered by stype (legacy direct links still supported)
    if folder and stype_filter:
        items = [i for i in fav.get_all(folder) if i.get("stype") == stype_filter]
        if not items:
            li = xbmcgui.ListItem(label="[COLOR gray]{0}[/COLOR]".format(_t(30212)))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
            return
        _fav_render_items(items, source_folder=folder)
        xbmcplugin.endOfDirectory(addon_handle)


def toggle_favorite(
    item_id,
    name,
    stype,
    icon,
    url,
    epg_id="",
    folder=None,
    catchup="",
    catchup_source="",
    catchup_days="",
):
    if folder is None:
        folder = _t(30009) or "Favorites"
    item = {
        "id": item_id,
        "name": name,
        "stype": stype,
        "icon": icon,
        "url": url,
        "epg_id": epg_id,
        "catchup": catchup,
        "catchup_source": catchup_source,
        "catchup_days": catchup_days,
    }
    if fav.is_favorite(item_id, folder):
        fav.remove(item_id, folder)
        xbmcgui.Dialog().notification("XStream Player", _t(30085).format(folder))
        xbmc.executebuiltin("Container.Refresh")
        return
    fav.add(item, folder)
    xbmcgui.Dialog().notification("XStream Player", _t(30084).format(folder))
    xbmc.executebuiltin("Container.Refresh")


def toggle_movie_watched(movie_id, profile_num=None):
    pnum = profile_num or pm.active
    wm = WatchedMovies(addon, profile_num=pnum)
    if wm.is_watched(movie_id):
        wm.mark_unwatched(movie_id)
    else:
        wm.mark_watched(movie_id)
    xbmc.executebuiltin("Container.Refresh")


def toggle_series_watched(series_id, profile_num=None):
    pnum = profile_num or pm.active
    we = WatchedEpisodes(addon, profile_num=pnum)
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    info = IPTV.get_xtream_series_info(url, user, pwd, series_id)
    episodes = info.get("episodes", {})
    has_any = we.get_watched_count(series_id) > 0
    if has_any:
        we.clear_series(series_id)
    else:
        for season_num, eps in episodes.items():
            ep_ids = [str(ep.get("id", "")) for ep in eps if ep.get("id")]
            if ep_ids:
                we.mark_season_watched(series_id, season_num, ep_ids)
    xbmc.executebuiltin("Container.Refresh")


def toggle_season_watched(series_id, season_num, profile_num=None):
    pnum = profile_num or pm.active
    we = WatchedEpisodes(addon, profile_num=pnum)
    creds = _get_credentials_for_profile(pnum)
    url = creds.get("xtream_url", "")
    user = creds.get("xtream_username", "")
    pwd = creds.get("xtream_password", "")
    info = IPTV.get_xtream_series_info(url, user, pwd, series_id)
    eps = info.get("episodes", {}).get(str(season_num), [])
    total_eps = len(eps)
    fully = we.is_season_fully_watched(series_id, season_num, total_eps)
    has_any = we.get_watched_count(series_id, season_num) > 0
    if fully or has_any:
        we.mark_season_unwatched(series_id, season_num)
    else:
        ep_ids = [str(ep.get("id", "")) for ep in eps if ep.get("id")]
        if ep_ids:
            we.mark_season_watched(series_id, season_num, ep_ids)
    xbmc.executebuiltin("Container.Refresh")


def toggle_episode_watched(series_id, season_num, episode_id, profile_num=None):
    pnum = profile_num or pm.active
    we = WatchedEpisodes(addon, profile_num=pnum)
    if we.is_watched(series_id, season_num, episode_id):
        we.mark_unwatched(series_id, season_num, episode_id)
    else:
        we.mark_watched(series_id, season_num, episode_id)
    xbmc.executebuiltin("Container.Refresh")


def switch_profile():
    """Change the PVR profile and prompt for restart."""
    current = addon.getSetting("active_pvr_profile") or "Profile 1"
    current_num = current.replace("Profile ", "") if "Profile " in current else "1"
    profiles = []
    for i in range(1, 11):
        if addon.getSetting(f"profile_{i}_enabled") != "true":
            continue
        has_xtream = bool(addon.getSetting(f"profile_{i}_xtream_url"))
        has_m3u = bool(addon.getSetting(f"profile_{i}_m3u"))
        if not has_xtream and not has_m3u:
            continue
        name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
        label = f"Profile {i} - {name}" if name != _t(30390, i) else f"Profile {i}"
        marker = " [COLOR green]*[/COLOR]" if str(i) == current_num else ""
        profiles.append((str(i), f"{label}{marker}"))
    if not profiles:
        xbmcgui.Dialog().notification("XStream Player", _t(30893))
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return
    labels = [p[1] for p in profiles]
    idx = xbmcgui.Dialog().select(_t(30017), labels)
    if idx < 0:
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return
    selected_num = profiles[idx][0]
    if selected_num == current_num:
        xbmcgui.Dialog().notification("XStream Player", _t(30121))
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return
    selected_profile = f"Profile {selected_num}"
    addon.setSetting("active_pvr_profile", selected_profile)
    addon.setSetting("last_pvr_profile", selected_profile)
    # Offer reload PVR or cancel
    dialog = xbmcgui.Dialog()
    options = [_t(30720), _t(30403)]  # Reload PVR, Cancel
    choice = dialog.select(_t(30732, selected_profile), options)
    if choice == 0:
        pd = xbmcgui.DialogProgress()
        pd.create("XStream Player", _t(30568))
        try:
            _sync_pvr_force()
        except Exception as e:
            _log(f"PVR reload error: {e}")

            _log(f"Traceback: {traceback.format_exc()}")
        finally:
            pd.close()
        xbmcgui.Dialog().notification("XStream Player", _t(30281))
    else:
        xbmcgui.Dialog().notification(
            "XStream Player",
            _t(30307, profiles[idx][1].replace("[COLOR green]*[/COLOR]", "").strip()),
        )
    xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


def view_changelog():
    """Show full changelog from addon folder."""
    changelog_path = os.path.join(
        xbmcvfs.translatePath(addon.getAddonInfo("path")), "CHANGELOG.md"
    )
    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            changelog = f.read()
        current_version = addon.getAddonInfo("version")
        xbmcgui.Dialog().textviewer(_t(30341), changelog)
    except Exception:
        xbmcgui.Dialog().notification("XStream Player", _t(30103))


def test_connection():
    results = []
    checked = 0
    pd = xbmcgui.DialogProgress()
    pd.create("XStream Player", _t(30288))
    for i in range(1, 11):
        if pd.iscanceled():
            break
        if addon.getSetting(f"profile_{i}_enabled") != "true":
            continue
        profile_name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
        pd.update(int((i - 1) * 10), f"{_t(30288)}: {profile_name}")
        creds = _get_credentials_for_profile(i)
        url = creds.get("xtream_url", "")
        user = creds.get("xtream_username", "")
        pwd = creds.get("xtream_password", "")
        if not url or not user or not pwd:
            continue
        checked += 1
        info = IPTV.validate_xtream(url, user, pwd)
        if info is None:
            results.append(f"[COLOR red]{profile_name}[/COLOR]: {_t(30054)}")
            continue

        exp = info.get("exp_date", "")
        exp_str = _t(30546)
        if exp:
            try:
                exp_dt = datetime.datetime.fromtimestamp(int(exp))
                exp_str = exp_dt.strftime("%Y-%m-%d %H:%M")
                days_left = (exp_dt - datetime.datetime.now()).days
                exp_str += _t(30420, days_left)
            except (ValueError, TypeError):
                exp_str = str(exp)
        status = info.get("status", _t(30428))
        max_conn = info.get("max_connections", "N/A")
        active_cons = info.get("active_cons", "0")
        results.append(
            f"[COLOR green]{profile_name}[/COLOR]: {_t(30421)} {status} | {_t(30422)} {exp_str} | {_t(30423)} {max_conn} | {_t(30424)} {active_cons}"
        )
        results.append("[COLOR gray]────────────────────[/COLOR]")
    pd.close()
    if checked == 0:
        xbmcgui.Dialog().ok("XStream Player", _t(30056))
        return
    if not results:
        xbmcgui.Dialog().ok(_t(30031), _t(30054) + "\n" + _t(30055))
        return
    xbmcgui.Dialog().textviewer(_t(30033), "\n".join(results).rstrip())


def account_info():
    lines = []
    has_any = False
    for i in range(1, 11):
        if addon.getSetting(f"profile_{i}_enabled") != "true":
            continue
        profile_name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
        creds = _get_credentials_for_profile(i)
        url = creds.get("xtream_url", "")
        user = creds.get("xtream_username", "")
        pwd = creds.get("xtream_password", "")
        if not url or not user or not pwd:
            continue
        has_any = True
        info = IPTV.validate_xtream(url, user, pwd)
        if info is None:
            lines.append(f"[B]{profile_name}[/B]: {_t(30123)}")
            lines.append("")
            continue

        exp = info.get("exp_date", "")
        exp_str = _t(30546)
        if exp:
            try:
                exp_dt = datetime.datetime.fromtimestamp(int(exp))
                exp_str = exp_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                exp_str = str(exp)
        lines.append(f"[B]{profile_name}[/B]")
        lines.append(f"{_t(30421)}: {info.get('status', _t(30429))}")
        lines.append(f"{_t(30422)}: {exp_str}")
        lines.append(f"{_t(30423)}: {info.get('max_connections', 'N/A')}")
        lines.append(f"{_t(30425)}: {info.get('active_cons', '0')}")
        lines.append(
            f"{_t(30426)}: {_t(30430) if info.get('is_trial') == '1' else _t(30431)}"
        )
        lines.append(f"{_t(30427)}: {info.get('server_url', 'N/A')}")
        lines.append("[COLOR gray]────────────────────[/COLOR]")
    if not has_any:
        xbmcgui.Dialog().ok("XStream Player", _t(30056))
        return
    xbmcgui.Dialog().textviewer(_t(30019), "\n".join(lines).rstrip())


def _validate_settings():
    """Validate settings after user closes settings dialog."""
    from iptv import _validate_url

    creds = _get_credentials()
    xt_url = creds.get("xtream_url", "")
    m3u_url = creds.get("m3u", "")
    for label, url in [(_t(30566), xt_url), (_t(30567), m3u_url)]:
        if not url:
            continue
        validated = _validate_url(url, allow_http=True)
        if not validated:
            xbmcgui.Dialog().notification(
                "XStream Player", _t(30308, label), xbmcgui.NOTIFICATION_WARNING, 5000
            )
        elif (
            url.startswith("http://")
            and addon.getSetting("warn_http").lower() == "true"
        ):
            xbmcgui.Dialog().notification(
                "XStream Player", _t(30309, label), xbmcgui.NOTIFICATION_WARNING, 3000
            )
            _log(f"Warning: {label} uses insecure HTTP connection")


def _snapshot_credentials():
    """Capture current credential state for all 10 profiles before settings open."""
    snapshot = {}
    for n in range(1, 11):
        snapshot[n] = {
            "xtream_url": addon.getSetting(f"profile_{n}_xtream_url") or "",
            "m3u": addon.getSetting(f"profile_{n}_m3u") or "",
        }
    return snapshot


def _detect_credential_changes(snapshot):
    """Compare snapshot to current settings. Returns list of changed profile numbers."""
    changed = []
    for n in range(1, 11):
        current_xt = addon.getSetting(f"profile_{n}_xtream_url") or ""
        current_m3u = addon.getSetting(f"profile_{n}_m3u") or ""
        if snapshot[n]["xtream_url"] != current_xt or snapshot[n]["m3u"] != current_m3u:
            changed.append(n)
    return changed


def _is_pvr_profile(pnum):
    """Check if a profile number is the currently active PVR profile."""
    pvr_profile = addon.getSetting("active_pvr_profile") or "Profile 1"
    match = re.search(r"(\d+)", pvr_profile)
    pvr_num = int(match.group(1)) if match else 1
    return int(pnum) == pvr_num


def _prompt_load_single_profile(pnum):
    """Prompt to load a single changed profile. Returns True if loaded."""
    dialog = xbmcgui.Dialog()
    profile_name = addon.getSetting(f"profile_{pnum}_name") or _t(30390, pnum)
    is_pvr = _is_pvr_profile(pnum)

    if is_pvr:
        msg = _t(30861, profile_name)
    else:
        msg = _t(30862, profile_name)

    if dialog.yesno("XStream Player", msg):
        _refresh_profile_data(pnum)
        return True
    return False


def _prompt_load_multiple_profiles(changed_profiles):
    """Show multi-select dialog for loading changed profiles. Returns list of loaded profiles."""
    dialog = xbmcgui.Dialog()
    options = []
    preselect = []
    idx_map = []

    for pnum in changed_profiles:
        profile_name = addon.getSetting(f"profile_{pnum}_name") or _t(30390, pnum)
        has_creds = bool(
            addon.getSetting(f"profile_{pnum}_xtream_url")
            or addon.getSetting(f"profile_{pnum}_m3u")
        )

        if has_creds:
            is_pvr = _is_pvr_profile(pnum)
            label = f"{profile_name} {_t(30863) if is_pvr else ''}"
            options.append(label)
            preselect.append(len(options) - 1)
            idx_map.append(pnum)
        else:
            # Grey out empty profiles
            options.append(f"[COLOR grey]{profile_name} ({_t(30864)})[/COLOR]")
            idx_map.append(None)

    if not options:
        return []

    result = dialog.multiselect(_t(30865), options, preselect=preselect)
    if result is None:
        return []

    loaded = []
    for idx in result:
        pnum = idx_map[idx]
        if pnum is not None:
            _refresh_profile_data(pnum)
            loaded.append(pnum)

    return loaded


def _prompt_sync_pvr_if_needed(loaded_profiles):
    """Offer PVR sync if any loaded profile is the PVR profile.

    Handles restore-time deferred sync: if restore set the deferred flag,
    clear it and only prompt if the PVR-linked profile was actually loaded.
    """
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    defer_flag = os.path.join(profile_path, "pvr_sync_after_profile_load.flag")

    if os.path.exists(defer_flag):
        os.remove(defer_flag)
        pvr_loaded = any(_is_pvr_profile(p) for p in loaded_profiles)
        if not pvr_loaded:
            _log("PVR sync skipped — PVR-linked profile not loaded")
            return
        _log("Restore-time deferred PVR sync — PVR-linked profile loaded")

    if not loaded_profiles:
        return

    pvr_loaded = any(_is_pvr_profile(p) for p in loaded_profiles)
    pvr_installed = is_pvr_iptvsimple_installed()
    _log(
        f"PVR sync check: loaded_profiles={loaded_profiles}, "
        f"pvr_loaded={pvr_loaded}, pvr_installed={pvr_installed}"
    )

    if not pvr_loaded or not pvr_installed:
        return

    # Allow previous dialog to fully close before showing PVR prompt
    xbmc.sleep(500)

    dialog = xbmcgui.Dialog()
    if dialog.yesno("XStream Player", _t(30866)):
        try:
            _sync_pvr_force()
            _log("PVR sync triggered after profile load")
        except Exception as e:
            _log(f"PVR sync after profile load warning: {e}")
    else:
        # User declined — flag for startup retry
        retry_flag = os.path.join(profile_path, "pvr_sync_retry_needed.flag")
        with open(retry_flag, "w", encoding="utf-8") as f:
            f.write("1")
        _log("PVR sync deferred after profile load, flagged for startup retry")


def settings():
    xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
    if not _check_pin("Settings"):
        return
    _log("Settings opened.")

    # Snapshot credentials before settings change
    cred_snapshot = _snapshot_credentials()

    addon.openSettings()
    _validate_settings()

    # Detect changes and prompt immediately
    changed_profiles = _detect_credential_changes(cred_snapshot)
    if changed_profiles:
        _log(f"Credential changes detected in profiles: {changed_profiles}")
        # Skip prompt if restore already loaded these profiles
        creds_flag = os.path.join(
            xbmcvfs.translatePath(addon.getAddonInfo("profile")), "credentials_saved"
        )
        if os.path.exists(creds_flag):
            _log("Credentials restored, skipping duplicate load prompt")
            return
        if len(changed_profiles) == 1:
            loaded = _prompt_load_single_profile(changed_profiles[0])
            if loaded:
                _prompt_sync_pvr_if_needed([changed_profiles[0]])
        else:
            loaded = _prompt_load_multiple_profiles(changed_profiles)
            _prompt_sync_pvr_if_needed(loaded)

    _log("Settings closed.")


def _prompt_load_profiles_after_restore():
    """If restore just completed, prompt to load profiles before PVR sync."""
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    defer_flag = os.path.join(profile_path, "pvr_sync_after_profile_load.flag")

    if not os.path.exists(defer_flag):
        return

    # Find all enabled profiles with credentials
    enabled_profiles = []
    for n in range(1, 11):
        if addon.getSetting(f"profile_{n}_enabled") == "true":
            has_xtream = bool(addon.getSetting(f"profile_{n}_xtream_url"))
            has_m3u = bool(addon.getSetting(f"profile_{n}_m3u"))
            if has_xtream or has_m3u:
                enabled_profiles.append(n)

    if not enabled_profiles:
        _log("Restore deferred flag set but no enabled profiles with credentials found")
        os.remove(defer_flag)
        return

    # Show multi-select dialog for loading restored profiles
    dialog = xbmcgui.Dialog()
    options = []
    preselect = []
    for pnum in enabled_profiles:
        profile_name = addon.getSetting(f"profile_{pnum}_name") or _t(30390, pnum)
        is_pvr = _is_pvr_profile(pnum)
        label = f"{profile_name} {_t(30863) if is_pvr else ''}"
        options.append(label)
        preselect.append(len(options) - 1)

    result = dialog.multiselect(_t(30887), options, preselect=preselect)
    if result is None:
        # User cancelled — keep flag so they can load profiles later
        _log("User cancelled profile load after restore")
        return

    selected_profiles = [enabled_profiles[idx] for idx in result]
    loaded = _refresh_profiles_batch(selected_profiles)

    if loaded:
        _log(f"Loaded profiles after restore: {loaded}")
        _prompt_sync_pvr_if_needed(loaded)
    else:
        _log("No profiles selected for loading after restore")

    # Remove deferred flag — profiles are now loaded (or user chose not to)
    try:
        os.remove(defer_flag)
    except FileNotFoundError:
        pass
    except Exception as e:
        _log(f"Remove deferred flag warning: {e}")


def _make_epg_info(epg, channel_id, channel_name):
    if not _epg_enabled():
        return "", channel_name, ""
    matched_id = epg._find_channel_id(channel_id, channel_name)
    if not matched_id:
        return "", channel_name, ""
    now = time.time()
    upcoming = []
    current_title = ""
    current_desc = ""
    # Fast O(log m) lookup using bisect on pre-sorted timestamps
    starts = epg._program_starts.get(matched_id, [])
    prog_list = epg.programs.get(matched_id, [])
    if starts and prog_list:
        import bisect
        # Reverse the offset so we can search raw timestamps directly
        offset_now = now - (epg.offset_hours * 3600)
        idx = bisect.bisect_right(starts, offset_now) - 1
        if 0 <= idx < len(prog_list):
            current_prog = prog_list[idx]
            stop = epg._apply_offset(_parse_xmltv_time(current_prog["stop"]))
            if stop > now:
                upcoming.append(current_prog)
                current_title = current_prog["title"]
                current_desc = current_prog.get("desc", "")
        # Append future programs (up to 7 more, or 8 if no current)
        future_start = idx + 1 if idx >= 0 else 0
        upcoming.extend(prog_list[future_start:future_start + 8])
        upcoming = upcoming[:8]
    else:
        # Fallback to linear scan if bisect data is unavailable
        for prog in epg.programs.get(matched_id, []):
            start = epg._apply_offset(_parse_xmltv_time(prog["start"]))
            stop = epg._apply_offset(_parse_xmltv_time(prog["stop"]))
            if start and start > now:
                upcoming.append(prog)
            elif start and start <= now < stop:
                upcoming.insert(0, prog)
                current_title = prog["title"]
                current_desc = prog.get("desc", "")
        upcoming = upcoming[:8]
    if current_title:
        if current_desc:
            clean_desc = current_desc.replace("\n", " ").replace("\r", " ").strip()
            if len(clean_desc) > 150:
                clean_desc = clean_desc[:147] + "..."
            display_name = f"[B]{channel_name}[/B]  -  {current_title}: {clean_desc}"
        else:
            display_name = f"[B]{channel_name}[/B]  -  {current_title}"
    else:
        display_name = f"[B]{channel_name}[/B]"
    plot_lines = []
    for idx, prog in enumerate(upcoming):
        t = _parse_xmltv_time(prog["start"])
        stop_t = _parse_xmltv_time(prog["stop"])
        is_current = idx == 0 and t and stop_t and t <= now < stop_t
        if t:
            time_str = time.strftime("%H:%M", time.localtime(t))
            line = f"{time_str} - {prog['title']}"
        else:
            line = prog["title"]
        if is_current:
            line = f"[B][COLOR yellow]> {line}[/COLOR][/B]"
        plot_lines.append(line)
    plot = "\n".join(plot_lines)
    _log(
        f"EPG info for {channel_name}: found {len(upcoming)} programs, current={current_title}"
    )
    return plot, display_name, current_title


def _get_default_downloads_dir():
    if xbmc.getCondVisibility("System.Platform.Android"):
        return "/storage/emulated/0/Download/"
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _get_backup_folder_path():
    return os.path.join(
        xbmcvfs.translatePath(addon.getAddonInfo("profile")), "backup_folder.txt"
    )


def _read_backup_folder():
    path = _get_backup_folder_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, OSError):
        return ""


def _write_backup_folder(path):
    file_path = _get_backup_folder_path()
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(path)
        try:
            f.flush()
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, file_path)


def _get_backup_dir():
    custom = _read_backup_folder()
    if custom and os.path.isdir(custom):
        return custom
    default = _get_default_downloads_dir()
    if not os.path.isdir(default):
        try:
            os.makedirs(default, exist_ok=True)
        except Exception as e:
            _log(f"Backup default dir creation failed: {e}")
            return xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    return default


def view_backup_path():
    """Show the current backup folder path in a dialog."""
    path = _read_backup_folder() or xbmcvfs.translatePath("special://home")
    xbmcgui.Dialog().ok(_t(30042), path)


def change_backup_folder():
    dialog = xbmcgui.Dialog()
    chosen = dialog.browseSingle(3, _t(30789), "", "", False, False, "")
    if not chosen:
        return
    _write_backup_folder(chosen)
    addon.setSetting("backup_folder_display", chosen)
    xbmcgui.Dialog().notification("XStream Player", _t(30791))


# Backup schema version — bump ONLY when restore logic would behave differently
# on the new format than the old one (renamed files, restructured data, remapped fields).
BACKUP_SCHEMA_VERSION = "2"

# Files that are safe to backup and restore (user data only, no caches or generated files)
_BACKUP_ALLOWED_PREFIXES = (
    "settings.xml",
    "favorites",
    "pvr_favorites_",
    "main_menu_order_",
    "hidden_subcats_",
    "hidden_items_",
    "category_prefs.json",
    "watch_history_",
    "resume_points_",
)

# Settings.xml keys that are safe to carry from v115 backups
_V115_SAFE_SETTINGS_KEYS = {
    "active_profile",
    "parental_pin",
    "warn_http",
    "hide_adult_categories",
    "pvr_favorites_enabled",
    "pvr_catchup_enabled",
    "pvr_catchup_days",
    "pvr_epg_refresh",
    "auto_refresh_enabled",
    "auto_refresh_interval",
    "pvr_reload_on_launch",
}
# Add all profile_{n}_* keys dynamically
for _n in range(1, 11):
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_enabled")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_name")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_source_type")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_m3u")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_xtream_url")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_xtream_username")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_xtream_password")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_epg_m3u")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_epg_xtream")
    _V115_SAFE_SETTINGS_KEYS.add(f"profile_{_n}_epg_url")  # legacy


def _build_backup_manifest(profile_path):
    """Build manifest dict from files present in profile dir."""
    files = []
    profiles_found = set()
    for fname in sorted(os.listdir(profile_path)):
        if not any(fname.startswith(p) for p in _BACKUP_ALLOWED_PREFIXES):
            continue
        fpath = os.path.join(profile_path, fname)
        if not os.path.isfile(fpath):
            continue
        # Detect type from filename
        ftype = "unknown"
        migrate = False
        if fname == "settings.xml":
            ftype = "settings"
            migrate = True
        elif fname.startswith("favorites"):
            ftype = "favorites"
        elif fname.startswith("pvr_favorites_"):
            ftype = "pvr_favorites"
            # Track which PVR profile numbers have favorites
            match = re.search(r"pvr_favorites_(\d+)", fname)
            if match:
                profiles_found.add(int(match.group(1)))
        elif fname.startswith("main_menu_order_"):
            ftype = "menu_order"
        elif fname.startswith("hidden_"):
            ftype = "hidden"
        elif fname == "category_prefs.json":
            ftype = "category_prefs"
        elif fname.startswith("watch_history_"):
            ftype = "watch_history"
        elif fname.startswith("resume_points_"):
            ftype = "resume_points"
        files.append({"path": fname, "type": ftype, "migrate": migrate})
    return {
        "backup_schema_version": BACKUP_SCHEMA_VERSION,
        "addon_version": addon.getAddonInfo("version"),
        "created_at": datetime.datetime.now().isoformat(),
        "profiles": sorted(list(profiles_found)),
        "files": files,
    }


def _validate_zip_manifest(manifest, zip_entries):
    """Validate that all files listed in manifest exist in ZIP before extraction.

    Args:
        manifest: dict from backup_manifest.json
        zip_entries: set of filenames from zf.namelist()
    Raises:
        ValueError if any manifest file is missing from the ZIP.
    """
    missing = [f["path"] for f in manifest["files"] if f["path"] not in zip_entries]
    if missing:
        raise ValueError(f"Backup is incomplete, missing: {missing}")


def _has_pvr_data_in_backup(manifest):
    """Check if backup contains any PVR-related data."""
    for f in manifest["files"]:
        if f["type"] in ("settings", "pvr_favorites"):
            return True
    return False


def backup_settings():

    dialog = xbmcgui.Dialog()
    options = [_t(30794), _t(30795)]
    choice = dialog.select(_t(30682), options)
    if choice < 0:
        return

    if choice == 0:
        backup_dir = _get_default_downloads_dir()
        if not backup_dir or not os.path.isdir(backup_dir):
            xbmcgui.Dialog().notification("XStream Player", _t(30790))
            return
    else:
        chosen = dialog.browseSingle(3, _t(30789), "", "", False, False, "")
        if not chosen:
            return
        backup_dir = chosen
        _write_backup_folder(chosen)

    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    version = addon.getAddonInfo("version")
    backup_path = os.path.join(
        backup_dir, f"xstream-player-{version}-backup-{timestamp}.zip"
    )

    try:
        manifest = _build_backup_manifest(profile_path)
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("backup_manifest.json", json.dumps(manifest, indent=2))
            for entry in manifest["files"]:
                fname = entry["path"]
                fpath = os.path.join(profile_path, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, fname)
        _log(f"Backup created: {backup_path} ({len(manifest['files'])} files)")
        xbmcgui.Dialog().notification("XStream Player", _t(30089))
    except Exception as e:
        _log(f"Backup failed: {e}")
        xbmcgui.Dialog().notification("XStream Player", _t(30090))


# v1.1.5 → v2.0 compatibility: legacy backup restore
# Supports old backup format (no manifest, broad file allowlist).
# This path is permanent — users may always have old backups.
def _restore_v115_backup(zip_path, progress=None):

    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    # Legacy v1.1.5 backups used a broad allowlist — keep it broad for compatibility
    allowed_prefixes = (
        "settings.xml",
        "favorites",
        "epg_cache_",
        "refresh_",
        "category_prefs.json",
        "watch_history_",
        "resume_points_",
        "watched_",
        "hidden_",
        "pvr_favorites",
        "ag_",
        "main_menu_order_",
    )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            total = len(names)
            for idx, name in enumerate(names):
                basename = os.path.basename(name)
                if not any(basename.startswith(p) for p in allowed_prefixes):
                    _log(f"Skipped unexpected legacy backup entry: {name}")
                    continue
                target = os.path.normpath(os.path.join(profile_path, basename))
                if not target.startswith(os.path.normpath(profile_path)):
                    _log(
                        f"Skipped unsafe legacy backup entry (traversal attempt): {name}"
                    )
                    continue
                with open(target, "wb") as f:
                    f.write(zf.read(name))
                if progress and total:
                    pct = 10 + int(((idx + 1) / total) * 25)
                    progress.update(pct, _t(30881))
    except Exception as e:
        _log(f"Legacy backup extraction failed: {e}")
        xbmcgui.Dialog().notification("XStream Player", _t(30092))
        return False

    if progress:
        progress.update(40, _t(30882))
    _sync_restored_settings(use_whitelist=True)

    if progress:
        progress.update(55, _t(30883))
    try:
        old_active = addon.getSetting("active_profile")
        if old_active:
            match = re.search(r"(\d+)", old_active)
            pnum = match.group(1) if match else "1"
            current_pvr = addon.getSetting("active_pvr_profile") or "Profile 1"
            current_match = re.search(r"(\d+)", current_pvr)
            current_pnum = current_match.group(1) if current_match else "1"
            if pnum != current_pnum:
                addon.setSetting("active_pvr_profile", f"Profile {pnum}")
                _log(
                    f"Mapped active_profile {old_active} -> active_pvr_profile: Profile {pnum}"
                )
            legacy_json = os.path.join(profile_path, f"pvr_favorites_{pnum}.json")
            target_json = os.path.join(
                profile_path, f"pvr_favorites_{current_pnum}.json"
            )
            if os.path.exists(legacy_json) and not os.path.exists(target_json):
                shutil.copy2(legacy_json, target_json)
                _log(
                    f"Migrated pvr_favorites_{pnum}.json -> pvr_favorites_{current_pnum}.json"
                )
            legacy_m3u = os.path.join(profile_path, f"pvr_favorites_{pnum}.m3u8")
            target_m3u = os.path.join(
                profile_path, f"pvr_favorites_{current_pnum}.m3u8"
            )
            if os.path.exists(legacy_m3u) and not os.path.exists(target_m3u):
                shutil.copy2(legacy_m3u, target_m3u)
                _log(
                    f"Migrated pvr_favorites_{pnum}.m3u8 -> pvr_favorites_{current_pnum}.m3u8"
                )

        for n in range(1, 11):
            old_epg = addon.getSetting(f"profile_{n}_epg_url")
            if old_epg:
                addon.setSetting(f"profile_{n}_epg_m3u", old_epg)
                addon.setSetting(f"profile_{n}_epg_xtream", old_epg)
                _log(f"Mapped profile_{n}_epg_url -> epg_m3u + epg_xtream")

            has_xtream = bool(addon.getSetting(f"profile_{n}_xtream_url"))
            has_m3u = bool(addon.getSetting(f"profile_{n}_m3u"))
            source_type = addon.getSetting(f"profile_{n}_source_type")
            if not source_type or source_type == "Xtream Codes":
                if has_m3u and not has_xtream:
                    addon.setSetting(f"profile_{n}_source_type", "M3U")
                    _log(f"Inferred profile {n} source_type as M3U after legacy import")
                elif has_xtream and source_type != "Xtream Codes":
                    addon.setSetting(f"profile_{n}_source_type", "Xtream Codes")
                    _log(
                        f"Inferred profile {n} source_type as Xtream Codes after legacy import"
                    )
            if has_xtream or has_m3u:
                enabled = addon.getSetting(f"profile_{n}_enabled")
                if enabled != "true":
                    addon.setSetting(f"profile_{n}_enabled", "true")
                    _log(f"Auto-enabled profile {n} after legacy import")
    except Exception as e:
        _log(f"Legacy backup mapping error: {e}")

    try:
        legacy_fav = os.path.join(profile_path, "favorites.json")
        if os.path.exists(legacy_fav):
            global_fav = os.path.join(profile_path, "favorites_global.json")
            if not os.path.exists(global_fav):
                shutil.copy2(legacy_fav, global_fav)
                _log("Migrated favorites.json -> favorites_global.json")
            for n in range(1, 11):
                if addon.getSetting(f"profile_{n}_enabled") == "true":
                    target_fav = os.path.join(profile_path, f"favorites_{n}.json")
                    if not os.path.exists(target_fav):
                        shutil.copy2(legacy_fav, target_fav)
                        _log(f"Migrated favorites.json -> favorites_{n}.json")
    except Exception as e:
        _log(f"Favorites migration warning: {e}")

    if progress:
        progress.update(80, _t(30884))
    _finalize_restore(profile_path)

    if progress:
        progress.update(100, _t(30885))
    return True


def _finalize_restore(profile_path, manifest=None):
    """Common post-restore steps: credentials flag, cache clear, PVR favorites, PVR sync."""
    # Prevent first-run refresh prompt from firing on restored credentials
    flag_file = os.path.join(profile_path, "credentials_saved")
    if not os.path.exists(flag_file):
        with open(flag_file, "w", encoding="utf-8") as f:
            f.write("1")

    # Clear all caches so restored credentials don't collide with stale data
    try:
        _cache_clear_all()
        _log("All caches cleared after restore")
    except Exception as e:
        _log(f"Cache clear after restore warning: {e}")

    # Defer PVR sync until PVR-linked profile is loaded after restore.
    # Prevents duplicate prompts and ensures sync uses fresh profile data.
    defer_flag = os.path.join(profile_path, "pvr_sync_after_profile_load.flag")
    with open(defer_flag, "w", encoding="utf-8") as f:
        f.write("1")
    _log("PVR sync deferred until PVR-linked profile is loaded")

    xbmc.executebuiltin(
        "Container.Update(plugin://plugin.video.xstream-player/,replace)"
    )


def restore_settings():
    """Restore from a backup ZIP with manifest-based version dispatch."""
    dialog = xbmcgui.Dialog()
    options = [_t(30794), _t(30796)]
    choice = dialog.select(_t(30683), options)
    if choice < 0:
        return

    if choice == 0:
        custom = _read_backup_folder()
        if not custom or not os.path.isdir(custom):
            xbmcgui.Dialog().notification("XStream Player", _t(30790))
            return
        start_dir = custom
    else:
        start_dir = ""

    zip_path = dialog.browse(1, _t(30337), "", ".zip", False, False, start_dir)
    if not zip_path:
        return

    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    progress = xbmcgui.DialogProgress()
    progress.create("XStream Player", _t(30879))

    try:
        progress.update(5, _t(30880))
        with zipfile.ZipFile(zip_path, "r") as zf:
            zip_entries = set(zf.namelist())

            # Find manifest/version files anywhere in ZIP (handles nested folders)
            manifest_names = [
                n for n in zip_entries if n.endswith("backup_manifest.json")
            ]
            version_names = [n for n in zip_entries if n.endswith("backup_version.txt")]

            _log(
                f"Restore dispatch: manifest={len(manifest_names)} "
                f"version_txt={len(version_names)} total_entries={len(zip_entries)}"
            )

            if manifest_names:
                # Modern manifest-based backup
                manifest_name = manifest_names[0]
                manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
                _validate_zip_manifest(manifest, zip_entries)
                schema_version = manifest.get("backup_schema_version", "0")

                if schema_version == BACKUP_SCHEMA_VERSION:
                    _restore_modern_backup(zf, manifest, profile_path, progress)
                else:
                    # Future migration path: bump schema_version when format changes
                    _log(
                        f"Backup schema {schema_version} != {BACKUP_SCHEMA_VERSION}, "
                        "attempting best-effort restore"
                    )
                    _restore_modern_backup(zf, manifest, profile_path, progress)

            elif version_names:
                # Old v2.0 backup (backup_version.txt but no manifest)
                version = zf.read(version_names[0]).decode("utf-8").strip()
                try:
                    major = int(version.split(".")[0])
                except (ValueError, IndexError):
                    major = 0
                if major >= 2:
                    # Treat as modern but without manifest — extract known prefixes
                    _restore_modern_backup_no_manifest(zf, profile_path, progress)
                else:
                    if xbmcgui.Dialog().yesno(
                        "XStream Player",
                        _t(30818),
                        nolabel=_t(30161),
                        yeslabel=_t(30162),
                    ):
                        _restore_v115_backup(zip_path, progress)

            else:
                # Legacy v1.1.5 backup
                if xbmcgui.Dialog().yesno(
                    "XStream Player",
                    _t(30818),
                    nolabel=_t(30161),
                    yeslabel=_t(30162),
                ):
                    _restore_v115_backup(zip_path, progress)

    except ValueError as e:
        _log(f"Restore validation failed: {e}")
        xbmcgui.Dialog().notification("XStream Player", _t(30092))
    except Exception as e:
        _log(f"Restore failed: {e}")
        xbmcgui.Dialog().notification("XStream Player", _t(30092))
    finally:
        try:
            progress.close()
        except Exception:
            pass


def _restore_modern_backup(zf, manifest, profile_path, progress=None):
    """Restore a backup that has a valid manifest (schema v2+)."""
    files = manifest["files"]
    total = len(files)
    for idx, entry in enumerate(files):
        fname = entry["path"]
        if fname not in zf.namelist():
            continue
        target = os.path.normpath(os.path.join(profile_path, fname))
        if not target.startswith(os.path.normpath(profile_path)):
            _log(f"Skipped unsafe backup entry (traversal attempt): {fname}")
            continue
        tmp_target = target + ".tmp"
        with open(tmp_target, "wb") as f:
            f.write(zf.read(fname))
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_target, target)
        if progress and total:
            pct = 10 + int(((idx + 1) / total) * 30)
            progress.update(pct, _t(30881))

    if progress:
        progress.update(45, _t(30882))
    _sync_restored_settings(use_whitelist=False)

    # Infer/fix source_type for profiles (critical for M3U-with-creds)
    if progress:
        progress.update(60, _t(30883))
    try:
        for n in range(1, 11):
            has_xtream = bool(addon.getSetting(f"profile_{n}_xtream_url"))
            has_m3u = bool(addon.getSetting(f"profile_{n}_m3u"))
            source_type = addon.getSetting(f"profile_{n}_source_type")
            if has_m3u and not has_xtream:
                if source_type != "M3U":
                    addon.setSetting(f"profile_{n}_source_type", "M3U")
                    _log(f"Restored profile {n} source_type inferred as M3U")
            elif has_xtream and source_type != "Xtream Codes":
                addon.setSetting(f"profile_{n}_source_type", "Xtream Codes")
                _log(f"Restored profile {n} source_type inferred as Xtream Codes")
            if has_xtream or has_m3u:
                enabled = addon.getSetting(f"profile_{n}_enabled")
                if enabled != "true":
                    addon.setSetting(f"profile_{n}_enabled", "true")
                    _log(f"Auto-enabled profile {n} after restore")
    except Exception as e:
        _log(f"Source type inference after restore warning: {e}")

    if progress:
        progress.update(80, _t(30884))
    _finalize_restore(profile_path, manifest=manifest)

    if progress:
        progress.update(100, _t(30885))
    xbmcgui.Dialog().notification("XStream Player", _t(30091))


def _restore_modern_backup_no_manifest(zf, profile_path, progress=None):
    """Restore a v2.0 backup that has backup_version.txt but no manifest."""
    # Broad extraction for compatibility with early v2.0 backups
    allowed_prefixes = (
        "settings.xml",
        "favorites",
        "watch_history_",
        "resume_points_",
        "pvr_favorites_",
        "main_menu_order_",
        "hidden_",
        "category_prefs.json",
    )
    names = [
        n
        for n in zf.namelist()
        if any(os.path.basename(n).startswith(p) for p in allowed_prefixes)
    ]
    total = len(names)
    for idx, name in enumerate(names):
        basename = os.path.basename(name)
        target = os.path.normpath(os.path.join(profile_path, basename))
        if not target.startswith(os.path.normpath(profile_path)):
            continue
        tmp_target = target + ".tmp"
        with open(tmp_target, "wb") as f:
            f.write(zf.read(name))
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_target, target)
        if progress and total:
            pct = 10 + int(((idx + 1) / total) * 30)
            progress.update(pct, _t(30881))

    if progress:
        progress.update(45, _t(30882))
    _sync_restored_settings(use_whitelist=False)

    # Infer source_type
    if progress:
        progress.update(60, _t(30883))
    try:
        for n in range(1, 11):
            has_xtream = bool(addon.getSetting(f"profile_{n}_xtream_url"))
            has_m3u = bool(addon.getSetting(f"profile_{n}_m3u"))
            source_type = addon.getSetting(f"profile_{n}_source_type")
            if has_m3u and not has_xtream:
                if source_type != "M3U":
                    addon.setSetting(f"profile_{n}_source_type", "M3U")
            elif has_xtream and source_type != "Xtream Codes":
                addon.setSetting(f"profile_{n}_source_type", "Xtream Codes")
            if has_xtream or has_m3u:
                if addon.getSetting(f"profile_{n}_enabled") != "true":
                    addon.setSetting(f"profile_{n}_enabled", "true")
    except Exception as e:
        _log(f"Source type inference warning: {e}")

    if progress:
        progress.update(80, _t(30884))
    _finalize_restore(profile_path)

    if progress:
        progress.update(100, _t(30885))
    xbmcgui.Dialog().notification("XStream Player", _t(30091))


def _sync_restored_settings(use_whitelist=True):
    """Force Kodi to reload restored settings.xml into its live cache.

    Validates XML before touching any live settings. For v1.1.5 restores,
    applies a whitelist to skip incompatible keys. For v2.0+ restores,
    syncs all settings to preserve the full backup state.
    """
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    settings_path = os.path.join(profile_path, "settings.xml")
    try:
        import xml.etree.ElementTree as ET

        # Pre-flight: validate XML is well-formed before touching live settings
        try:
            tree = ET.parse(settings_path)
        except ET.ParseError as e:
            _log(f"Restored settings.xml is malformed: {e}")
            raise ValueError(f"Corrupted settings.xml in backup: {e}")

        restored_count = 0
        skipped_count = 0
        for setting in tree.findall(".//setting"):
            sid = setting.get("id")
            if sid is None:
                continue
            # v115 whitelist: only restore keys we explicitly trust
            if use_whitelist and sid not in _V115_SAFE_SETTINGS_KEYS:
                skipped_count += 1
                continue
            val = (setting.text or "").strip()
            # Don't overwrite live settings with empty values from backup
            if val:
                addon.setSetting(sid, val)
                restored_count += 1
        mode = "whitelist" if use_whitelist else "full"
        _log(
            f"Synced restored settings.xml ({mode}): {restored_count} restored, {skipped_count} skipped"
        )
    except Exception as e:
        _log(f"Settings sync warning: {e}")


def clear_provider_metadata_cache():
    """Clear provider metadata caches: vod_info and playback_duration only.
    Navigation caches (data_cache_*) are handled by Profiles cache."""
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    count = 0
    for fname in os.listdir(profile_path):
        if (
            fname.startswith("vod_info_")
            or fname.startswith("playback_duration_")
        ):
            try:
                os.remove(os.path.join(profile_path, fname))
                count += 1
            except Exception as e:
                _log(f"clear_provider_metadata_cache remove warning: {e}")
    xbmcgui.Dialog().notification("XStream Player", _t(30890, count))


def clear_cache_menu():
    options = [
        _t(30500),  # Profiles cache
        _t(30501),  # EPG cache
        _t(30503),  # TMDB cache
        _t(30891),
        _t(30504),  # Recently watched / watch history
        _t(30505),  # Content watched checkmarks
        _t(30772),  # Search history
        _t(30506),  # Kodi cache
    ]
    dialog = xbmcgui.Dialog()
    choice = dialog.select(_t(30153), options)
    if choice < 0:
        return
    if choice == 0:
        options = [_t(30771)]  # All Profiles
        for i in range(1, 11):
            name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
            options.append(name)
        idx = dialog.select(_t(30500), options)
        if idx < 0:
            return
        if dialog.yesno(_t(30042), _t(30500)):
            if idx == 0:
                clear_all_caches()
            else:
                count = _cache_clear_profile(idx)
                # Also remove legacy global channel cache files as they have no profile prefix
                profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
                try:
                    for fname in os.listdir(profile_path):
                        if (
                            fname.startswith("data_cache_xtream_")
                            or fname.startswith("data_cache_m3u")
                            or fname.startswith("vod_info_")
                        ):
                            os.remove(os.path.join(profile_path, fname))
                            count += 1
                except Exception as e:
                    _log(f"Legacy channel cache remove warning: {e}")
                xbmcgui.Dialog().notification("XStream Player", _t(30258, count))
    elif choice == 1:
        options = [_t(30771)]  # All Profiles
        for i in range(1, 11):
            name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
            options.append(name)
        idx = dialog.select(_t(30501), options)
        if idx < 0:
            return
        if dialog.yesno(_t(30042), _t(30501)):
            clear_epg_cache(idx)
    elif choice == 2:
        if dialog.yesno(_t(30042), _t(30503)):
            clear_tmdb_cache()
    elif choice == 3:
        if dialog.yesno(_t(30042), "Clear provider metadata cache?"):
            clear_provider_metadata_cache()
    elif choice == 4:
        options = [_t(30771)]  # All Profiles
        for i in range(1, 11):
            name = addon.getSetting(f"profile_{i}_name") or _t(30390, i)
            options.append(name)
        idx = dialog.select(_t(30504), options)
        if idx < 0:
            return
        if dialog.yesno(_t(30042), _t(30076)):
            if idx == 0:
                for pnum in range(1, 11):
                    _watch_history(pnum).clear()
                    _resume_db(pnum).clear()
                dialog.notification(_t(30770), _t(30253))
            else:
                _watch_history(idx).clear()
                _resume_db(idx).clear()
                dialog.notification(_t(30770), _t(30253))
    elif choice == 5:
        if dialog.yesno(_t(30042), _t(30505)):
            count = 0
            for pnum in range(1, 11):
                wm = WatchedMovies(addon, profile_num=pnum)
                we = WatchedEpisodes(addon, profile_num=pnum)
                if wm._data:
                    wm.clear()
                    count += 1
                if we._data:
                    we.clear()
                    count += 1
            dialog.notification(_t(30770), _t(30253))
    elif choice == 6:
        _clear_search_history_menu()
    elif choice == 7:
        clear_kodi_cache()


def _clear_search_history_menu():
    """Submenu for clearing search history."""
    dialog = xbmcgui.Dialog()
    options = [
        _t(30773),  # Clear global search history
        _t(30774),  # Clear all profiles search history
    ]
    choice = dialog.select(_t(30772), options)
    if choice < 0:
        return
    if choice == 0:
        if dialog.yesno(_t(30770), _t(30773)):
            try:
                history_path = _search_history_path()
                if os.path.exists(history_path):
                    os.remove(history_path)
                    dialog.notification(_t(30770), _t(30093, "Global"))
                else:
                    dialog.notification(_t(30770), _t(30093, "Global"))
            except Exception as e:
                _log(f"Error clearing global search history: {e}")
                dialog.notification(_t(30770), _t(30091), xbmcgui.NOTIFICATION_ERROR)
    elif choice == 1:
        if dialog.yesno(_t(30770), _t(30774)):
            try:
                count = 0
                for i in range(1, 11):
                    history_path = _search_history_path(i)
                    if os.path.exists(history_path):
                        os.remove(history_path)
                        count += 1
                dialog.notification(_t(30770), _t(30093, f"{count} profiles"))
            except Exception as e:
                _log(f"Error clearing profiles search history: {e}")
                dialog.notification(_t(30770), _t(30091), xbmcgui.NOTIFICATION_ERROR)


def clear_all_caches():
    count = _cache_clear_all_profiles()
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    for fname in os.listdir(profile_path):
        if (
            fname.startswith("epg_cache_profile_")
            or fname == "epg_cache.json"
            or fname == "view_prefs.json"
        ):
            try:
                os.remove(os.path.join(profile_path, fname))
                count += 1
            except Exception as e:
                _log(f"clear_all_caches remove warning: {e}")
    xbmcgui.Dialog().notification("XStream Player", _t(30258, count))


def clear_epg_cache(pnum=None):
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    count = 0
    for fname in os.listdir(profile_path):
        if fname == "epg_cache.json" or fname.startswith("data_cache_epg"):
            try:
                os.remove(os.path.join(profile_path, fname))
                count += 1
            except Exception as e:
                _log(f"clear_epg_cache remove warning: {e}")
        elif pnum is not None and fname == f"epg_cache_profile_{pnum}.json":
            try:
                os.remove(os.path.join(profile_path, fname))
                count += 1
            except Exception as e:
                _log(f"clear_epg_cache remove warning: {e}")
        elif pnum is None and fname.startswith("epg_cache_profile_"):
            try:
                os.remove(os.path.join(profile_path, fname))
                count += 1
            except Exception as e:
                _log(f"clear_epg_cache remove warning: {e}")
    xbmcgui.Dialog().notification("XStream Player", _t(30303, count))


def clear_tmdb_cache():
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    count = 0
    for fname in os.listdir(profile_path):
        if fname.startswith("tmdb_search_") or fname.startswith("tmdb_tv_search_"):
            try:
                os.remove(os.path.join(profile_path, fname))
                count += 1
            except Exception as e:
                _log(f"clear_tmdb_cache remove warning: {e}")
    xbmcgui.Dialog().notification("XStream Player", _t(30305, count))


def clear_kodi_cache():
    """Clear Kodi's system cache (thumbnails, temp files, etc.)"""
    dialog = xbmcgui.Dialog()
    if not dialog.yesno(_t(30044), _t(30283)):
        return

    count = 0
    thumbs_path = xbmcvfs.translatePath("special://thumbnails/")
    if os.path.exists(thumbs_path):
        for root, dirs, files in os.walk(thumbs_path):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                    count += 1
                except Exception as e:
                    _log(f"clear_kodi_cache thumbs warning: {e}")

    temp_path = xbmcvfs.translatePath("special://temp/")
    if os.path.exists(temp_path):
        for fname in os.listdir(temp_path):
            fpath = os.path.join(temp_path, fname)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    count += 1
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                    count += 1
            except Exception as e:
                _log(f"clear_kodi_cache temp warning: {e}")

    cache_path = xbmcvfs.translatePath("special://cache/")
    if os.path.exists(cache_path):
        for fname in os.listdir(cache_path):
            fpath = os.path.join(cache_path, fname)
            try:
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    count += 1
            except Exception as e:
                _log(f"clear_kodi_cache cache warning: {e}")

    dialog.notification("XStream Player", _t(30177, count))


def profile_recently_watched(pnum=None):
    """Show recently watched items grouped by type (Live TV, Movies, Series)."""
    pnum = pnum or pm.active
    original_active = pm.active
    pm.active = str(pnum)
    try:
        stype_labels = {
            "live": _t(30002),
            "movie": _t(30004),
            "series": _t(30005),
        }
        stype_icons = {
            "live": "DefaultAddonPVRClient.png",
            "movie": "DefaultMovies.png",
            "series": "DefaultTVShows.png",
        }
        type_order = ["live", "movie", "series"]
        history = _watch_history(pnum)
        items_by_type = {}
        for st in type_order:
            items = history.get_all(st)[:10]
            if items:
                items_by_type[st] = items

        if not items_by_type:
            li = xbmcgui.ListItem(label=_t(30243))
            xbmcplugin.addDirectoryItem(
                handle=addon_handle, url="", listitem=li, isFolder=False
            )
            xbmcplugin.endOfDirectory(addon_handle)
            return

        show_separators = len(items_by_type) > 1
        for st in type_order:
            if st not in items_by_type:
                continue
            if show_separators:
                label = stype_labels.get(st, st)
                sep = xbmcgui.ListItem(
                    label=f"[COLOR gray]────── {label} ──────[/COLOR]"
                )
                sep.setArt({"icon": stype_icons.get(st, "DefaultFolder.png")})
                sep.setProperty("IsPlayable", "false")
                xbmcplugin.addDirectoryItem(
                    handle=addon_handle, url="", listitem=sep, isFolder=False
                )
            _render_recent_items(items_by_type[st], st, profile_num=pnum)

        xbmcplugin.endOfDirectory(addon_handle)
    finally:
        pm.active = original_active


def recently_watched_by_type(stype, pnum=None):
    """Show recently watched items for a specific type."""
    pnum = pnum or pm.active
    items = _watch_history(pnum).get_all(stype)
    if not items:
        li = xbmcgui.ListItem(label=_t(30243))
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url="", listitem=li, isFolder=False
        )
        xbmcplugin.endOfDirectory(addon_handle)
        return
    _render_recent_items(items, stype, profile_num=pnum)
    xbmcplugin.endOfDirectory(addon_handle)


def continue_watching_menu():
    """Show continue watching: movies and series from all profiles."""
    all_movies = []
    all_series = []
    profile_dir = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    seen_urls = set()

    for pnum in range(1, 11):
        if addon.getSetting(f"profile_{pnum}_enabled") != "true":
            continue
        rp_path = os.path.join(profile_dir, f"resume_points_p{pnum}.json")
        wh_path = os.path.join(profile_dir, f"watch_history_p{pnum}.json")
        try:
            with open(rp_path, "r", encoding="utf-8") as f:
                rp_data = json.load(f)
        except Exception:
            rp_data = {}
        try:
            with open(wh_path, "r", encoding="utf-8") as f:
                wh_list = json.load(f)
        except Exception:
            wh_list = []
        if not isinstance(rp_data, dict):
            rp_data = {}
        if not isinstance(wh_list, list):
            wh_list = []
        rp_by_url = {entry.get("url", ""): entry for entry in rp_data.values() if entry.get("url")}

        # Primary pass: watch history (all recently watched movies/series)
        for wh_entry in wh_list:
            url = wh_entry.get("url", "")
            stype = wh_entry.get("stype", "")
            if stype not in ("movie", "series"):
                continue
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            rp_entry = rp_by_url.get(url)
            position = rp_entry.get("position", 0) if rp_entry else 0
            duration = rp_entry.get("duration", 0) if rp_entry else 0
            ts = wh_entry.get("timestamp", 0)
            if rp_entry and rp_entry.get("timestamp", 0) > ts:
                ts = rp_entry.get("timestamp", 0)
            item = {
                "name": wh_entry.get("name", ""),
                "url": url,
                "position": position,
                "duration": duration,
                "timestamp": ts,
                "stype": stype,
                "profile_num": pnum,
                "icon": wh_entry.get("icon", ""),
                "series_id": wh_entry.get("series_id", ""),
                "season_num": wh_entry.get("season_num", ""),
                "ep_id": wh_entry.get("ep_id", ""),
                "has_resume": bool(rp_entry),
            }
            if stype == "movie":
                all_movies.append(item)
            else:
                all_series.append(item)

        # Fallback pass: resume points with no watch history entry
        for url, rp_entry in rp_by_url.items():
            if url in seen_urls:
                continue
            if "/series/" in url:
                stype = "series"
            elif "/movie/" in url:
                stype = "movie"
            else:
                continue
            seen_urls.add(url)
            item = {
                "name": rp_entry.get("name", ""),
                "url": url,
                "position": rp_entry.get("position", 0),
                "duration": rp_entry.get("duration", 0),
                "timestamp": rp_entry.get("timestamp", 0),
                "stype": stype,
                "profile_num": pnum,
                "icon": "",
                "series_id": "",
                "season_num": "",
                "ep_id": "",
                "has_resume": True,
            }
            if stype == "movie":
                all_movies.append(item)
            else:
                all_series.append(item)

    def _has_meaningful_progress(item):
        position = item["position"]
        duration = item["duration"]
        if item["has_resume"] and duration > 0:
            return int((position / duration) * 100) >= 1
        return True

    all_movies = [m for m in all_movies if _has_meaningful_progress(m)]
    all_series = [s for s in all_series if _has_meaningful_progress(s)]
    all_movies.sort(key=lambda x: x["timestamp"], reverse=True)
    all_series.sort(key=lambda x: x["timestamp"], reverse=True)
    movies = all_movies[:10]
    series = all_series[:10]
    combined = movies + series

    if not combined:
        li = xbmcgui.ListItem(
            label="[COLOR gray]{0}[/COLOR]".format(_t(30211))
        )
        xbmcplugin.addDirectoryItem(
            handle=addon_handle, url="", listitem=li, isFolder=False
        )
        xbmcplugin.endOfDirectory(addon_handle)
        return

    def _render_item(item):
        name = item["name"]
        url = item["url"]
        pnum = item["profile_num"]
        stype = item["stype"]
        position = item["position"]
        duration = item["duration"]
        icon = item["icon"]
        series_id = item["series_id"]
        season_num = item["season_num"]
        ep_id = item["ep_id"]
        has_resume = item.get("has_resume", False)

        if has_resume and duration > 0:
            progress_pct = int((position / duration) * 100)
            label = f"{name}  [COLOR gray]({progress_pct}%)[/COLOR]"
        else:
            label = name

        li = xbmcgui.ListItem(label=label)
        li.setProperty("IsPlayable", "true")
        info_tag = li.getVideoInfoTag()
        info_tag.setMediaType("video")
        info_tag.setTitle(name)
        if icon:
            li.setArt({"icon": icon, "thumb": icon})

        q = {
            "mode": "play_stream",
            "url": url,
            "name": name,
            "stype": stype,
            "profile_num": pnum,
        }
        if series_id:
            q["series_id"] = series_id
        if season_num:
            q["season_num"] = season_num
        if ep_id:
            q["ep_id"] = ep_id
        if icon:
            q["icon"] = icon

        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url(q),
            listitem=li,
            isFolder=False,
        )

    if movies:
        sep = xbmcgui.ListItem(label=f"[COLOR gray]────── {_t(30004)} ──────[/COLOR]")
        sep.setProperty("IsPlayable", "false")
        sep.setArt({"icon": "DefaultMovies.png"})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url="", listitem=sep, isFolder=False)
        for item in movies:
            _render_item(item)

    if series:
        sep = xbmcgui.ListItem(label=f"[COLOR gray]────── {_t(30005)} ──────[/COLOR]")
        sep.setProperty("IsPlayable", "false")
        sep.setArt({"icon": "DefaultTVShows.png"})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url="", listitem=sep, isFolder=False)
        for item in series:
            _render_item(item)

    xbmcplugin.endOfDirectory(addon_handle)


# Note: EPG cache can be cleared via Settings → EPG and guide → Clear EPG database

mode = args.get("mode", [None])[0]

if mode is None:
    main_menu()
elif mode == "live_menu":
    live_menu(args.get("profile_num", [None])[0])
elif mode == "m3u_group":
    try:
        page = int(args.get("page", ["1"])[0])
    except ValueError:
        page = 1
    try:
        pnum = int(args.get("pnum", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    m3u_group(args.get("group", [""])[0], pnum, page)
elif mode == "m3u_all_channels":
    try:
        page = int(args.get("page", ["1"])[0])
    except ValueError:
        page = 1
    try:
        pnum = int(args.get("pnum", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    _show_all_m3u_channels(pnum, page)
elif mode == "xtream_categories":
    xtream_categories(args.get("type", ["live"])[0], args.get("profile_num", [None])[0])
elif mode == "xtream_streams":
    try:
        page = int(args.get("page", ["1"])[0])
    except ValueError:
        page = 1
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    xtream_streams(
        args.get("type", ["live"])[0],
        args.get("cat_id", [""])[0],
        page,
        args.get("adult", ["0"])[0],
        pnum,
    )
elif mode == "xtream_series":
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    xtream_series(args.get("series_id", [""])[0], pnum)
elif mode == "xtream_season":
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    xtream_season(args.get("series_id", [""])[0], args.get("season_num", [""])[0], pnum)
elif mode == "movies_menu":
    movies_menu(args.get("profile_num", [None])[0])
elif mode == "series_menu":
    series_menu(args.get("profile_num", [None])[0])
elif mode == "replay_menu":
    replay_menu(args.get("profile_num", [None])[0])
elif mode == "replay_channel":
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    replay_channel(
        args.get("stream_id", [""])[0],
        args.get("epg_id", [""])[0],
        args.get("name", [""])[0],
        pnum,
    )
elif mode == "replay_play":
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    replay_play(
        args.get("stream_id", [""])[0],
        args.get("start", [""])[0],
        args.get("duration", [""])[0],
        pnum,
    )
elif mode == "replay_channel_m3u":
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    replay_channel_m3u(
        args.get("channel_name", [""])[0],
        args.get("epg_id", [""])[0],
        args.get("channel_url", [""])[0],
        args.get("catchup", [""])[0],
        args.get("catchup_source", [""])[0],
        args.get("logo", [""])[0],
        pnum,
    )
elif mode == "replay_play_m3u":
    try:
        pnum = int(args.get("profile_num", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    replay_play_m3u(
        args.get("channel_name", [""])[0],
        args.get("channel_url", [""])[0],
        args.get("catchup", [""])[0],
        args.get("catchup_source", [""])[0],
        args.get("logo", [""])[0],
        args.get("start_ts", [""])[0],
        args.get("end_ts", [""])[0],
        pnum,
    )
elif mode == "search_global":
    try:
        pnum_raw = args.get("profile_num", [None])[0]
        pnum = int(pnum_raw) if pnum_raw is not None else None
    except (ValueError, TypeError):
        pnum = None
    stype = args.get("stype", [None])[0]
    search_global(args.get("query", [None])[0], profile_num=pnum, stype=stype)
elif mode == "search_all_combined":
    search_all_profiles_combined(args.get("query", [""])[0])
elif mode == "search_m3u":
    stype = args.get("stype", [None])[0]
    search_m3u(args.get("query", [None])[0], stype=stype)
elif mode == "favorites_menu":
    favorites_menu(args.get("folder", [None])[0], args.get("stype_filter", [None])[0])
elif mode == "profile_favorites_menu":
    profile_favorites_menu(int(args.get("pnum", [1])[0]))
elif mode == "profile_favorites_by_type":
    pnum = int(args.get("pnum", [1])[0])
    stype = args.get("stype", ["live"])[0]
    profile_fav = _get_profile_fav(pnum)
    items = [i for i in profile_fav.get_all() if i.get("stype", "live") == stype]
    if items:
        _fav_render_items(items, source_folder=None, profile_num=pnum)
    xbmcplugin.endOfDirectory(addon_handle)
elif mode == "profile_fav_remove":
    pnum = int(args.get("pnum", [1])[0])
    profile_fav = _get_profile_fav(pnum)
    _fav_item_id = args.get("id", [""])[0]
    _fav_folder = args.get("folder", ["__all__"])[0]
    if _fav_folder == "__all__":
        profile_fav.remove(_fav_item_id)
    else:
        profile_fav.remove(_fav_item_id, _fav_folder)
    _invalidate_profile_fav(pnum)
    xbmcgui.Dialog().notification("XStream Player", _t(30747))
    xbmc.executebuiltin("Container.Refresh")
elif mode == "fav_new_folder":
    name = xbmcgui.Dialog().input(_t(30143))
    if name:
        fav.create_folder(name)
        xbmcgui.Dialog().notification("XStream Player", _t(30094).format(name))
        xbmc.executebuiltin("Container.Refresh")
elif mode == "fav_rename_folder":
    fname = args.get("folder", [""])[0]
    if fname:
        new_name = xbmcgui.Dialog().input(_t(30144), defaultt=fname)
        if new_name and new_name != fname:
            fav.rename_folder(fname, new_name)
            xbmcgui.Dialog().notification("XStream Player", _t(30095).format(new_name))
            xbmc.executebuiltin("Container.Refresh")
elif mode == "fav_delete_folder":
    fname = args.get("folder", [""])[0]
    protected_folders = {"Favorites", _t(30009) or "Favorites"}
    if fname and fname not in protected_folders:
        if xbmcgui.Dialog().yesno(_t(30038), _t(30066).format(fname)):
            fav.delete_folder(fname)
            xbmcgui.Dialog().notification("XStream Player", _t(30096).format(fname))
            xbmc.executebuiltin("Container.Refresh")
elif mode == "fav_move":
    item_id = args.get("id", [""])[0]
    from_folder = args.get("from_folder", [_t(30009) or "Favorites"])[0]
    folders = [f for f in fav.get_folders() if f != from_folder]
    if not folders:
        xbmcgui.Dialog().notification("XStream Player", _t(30124))
    else:
        idx = xbmcgui.Dialog().select(_t(30145), folders)
        if idx >= 0:
            source_items = fav.get_all(from_folder)
            item_data = next((i for i in source_items if i.get("id") == item_id), None)
            if item_data:
                fav.remove(item_id, from_folder)
                fav.add(item_data, folders[idx])
                xbmcgui.Dialog().notification(
                    "XStream Player", _t(30097).format(folders[idx])
                )
                xbmc.executebuiltin("Container.Refresh")
elif mode == "export_favorites":
    fname = args.get("folder", [None])[0]
    path = xbmcgui.Dialog().browseSingle(3, _t(30338), "files")
    if path:
        export_name = f"favorites_{fname}.m3u" if fname else "favorites.m3u"
        full_path = os.path.join(path, export_name)
        count = fav.export_m3u(full_path, fname)
        xbmcgui.Dialog().notification("XStream Player", _t(30116).format(count))
elif mode == "fav_remove":
    _fav_item_id = args.get("id", [""])[0]
    _fav_folder = args.get("folder", ["__all__"])[0]
    if _fav_folder == "__all__":
        fav.remove(_fav_item_id)
    else:
        fav.remove(_fav_item_id, _fav_folder)
        xbmcgui.Dialog().notification("XStream Player", _t(30085).format(_fav_folder))
    xbmc.executebuiltin("Container.Refresh")
elif mode == "fav_remove_by_type":
    _fav_folder = args.get("folder", [""])[0]
    _fav_stype = args.get("stype", [""])[0]
    if _fav_folder and _fav_stype:
        stype_labels = {
            "live": _t(30002),
            "movie": _t(30004),
            "series": _t(30005),
            "folder": _t(30808),
        }
        label = stype_labels.get(_fav_stype, _fav_stype)
        if xbmcgui.Dialog().yesno(_t(30813).format(label), _t(30815)):
            removed = fav.remove_by_type(_fav_folder, _fav_stype)
            if removed:
                xbmcgui.Dialog().notification("XStream Player", _t(30814))
    xbmc.executebuiltin("Container.Refresh")
elif mode == "toggle_fav":
    toggle_favorite(
        args.get("id", [""])[0],
        args.get("name", [""])[0],
        args.get("stype", ["live"])[0],
        args.get("icon", [""])[0],
        args.get("url", [""])[0],
        args.get("epg_id", [""])[0],
        args.get("folder", [_t(30009) or "Favorites"])[0],
        args.get("catchup", [""])[0],
        args.get("catchup_source", [""])[0],
        args.get("catchup_days", [""])[0],
    )
elif mode == "toggle_profile_fav":
    pnum = int(args.get("pnum", [1])[0])
    profile_fav = _get_profile_fav(pnum)
    item = {
        "id": args.get("id", [""])[0],
        "name": args.get("name", [""])[0],
        "stype": args.get("stype", ["live"])[0],
        "icon": args.get("icon", [""])[0],
        "url": args.get("url", [""])[0],
        "epg_id": args.get("epg_id", [""])[0],
    }
    if profile_fav.is_favorite(item["id"]):
        profile_fav.remove(item["id"])
        xbmcgui.Dialog().notification("XStream Player", _t(30747))
    else:
        profile_fav.add(item)
        xbmcgui.Dialog().notification("XStream Player", _t(30746))
    _invalidate_profile_fav(pnum)
    xbmc.executebuiltin("Container.Refresh")
elif mode == "toggle_movie_watched":
    pnum = args.get("profile_num", [""])[0]
    toggle_movie_watched(
        args.get("movie_id", [""])[0],
        int(pnum) if pnum else None,
    )
elif mode == "toggle_series_watched":
    pnum = args.get("profile_num", [""])[0]
    toggle_series_watched(
        args.get("series_id", [""])[0],
        int(pnum) if pnum else None,
    )
elif mode == "toggle_season_watched":
    pnum = args.get("profile_num", [""])[0]
    toggle_season_watched(
        args.get("series_id", [""])[0],
        args.get("season_num", [""])[0],
        int(pnum) if pnum else None,
    )
elif mode == "toggle_episode_watched":
    pnum = args.get("profile_num", [""])[0]
    toggle_episode_watched(
        args.get("series_id", [""])[0],
        args.get("season_num", [""])[0],
        args.get("episode_id", [""])[0],
        int(pnum) if pnum else None,
    )
elif mode == "refresh_data":
    refresh_data()
elif mode == "refresh_profile_menu":
    refresh_profile_menu()
elif mode == "profile_menu":
    profile_menu(int(args.get("pnum", [1])[0]))
elif mode == "open_pvr":
    open_pvr()
elif mode == "pvr_favorites_manager":
    pvr_favorites_manager(args.get("group", [None])[0])
elif mode == "pvr_favs_manage_group":
    pvr_favs_manage_group(args.get("group", [_t(30703) or "Favorites"])[0])
elif mode == "pvr_favs_group_current":
    pvr_favs_group_current(args.get("group", [_t(30703) or "Favorites"])[0])
elif mode == "pvr_favs_group_search":
    pvr_favs_group_search(args.get("group", [_t(30703) or "Favorites"])[0])
elif mode == "pvr_favs_manage_cat":
    pvr_favs_manage_cat(
        args.get("cat_id", [""])[0],
        args.get("cat_name", [""])[0],
        args.get("group", [_t(30703) or "Favorites"])[0],
    )
elif mode == "pvr_favs_new_group":
    dialog = xbmcgui.Dialog()
    name = dialog.input(_t(30147))
    if name:
        groups = _pvr_favs_load_all()
        if name in groups:
            dialog.notification("XStream Player", _t(30125))
        else:
            groups[name] = []
            _pvr_favs_save_all(groups)
            _sync_pvr_favorites()
            dialog.notification("XStream Player", _t(30126, name))
            xbmc.sleep(1500)
            dialog.ok("XStream Player", _t(30727))
            xbmc.executebuiltin("Container.Refresh")
elif mode == "pvr_favs_rename_group":
    old_name = args.get("group", [""])[0]
    dialog = xbmcgui.Dialog()
    new_name = dialog.input(_t(30148), defaultt=old_name)
    if new_name and new_name != old_name:
        groups = _pvr_favs_load_all()
        if new_name in groups:
            dialog.notification("XStream Player", _t(30125))
        elif old_name in groups:
            items = groups.pop(old_name)
            groups[new_name] = items
            _pvr_favs_save_all(groups)
            _sync_pvr_favorites()
            dialog.notification("XStream Player", _t(30178, new_name))
            xbmc.executebuiltin("Container.Refresh")
            options = [
                _t(30720),
                _t(30165),
                _t(30403),
            ]  # Reload PVR, Restart Kodi, Cancel
            choice = dialog.select(_t(30732, new_name), options)
            if choice == 0:
                pd = xbmcgui.DialogProgress()
                pd.create("XStream Player", _t(30568))
                try:
                    _sync_pvr_force()
                except Exception as e:
                    _log(f"PVR reload error: {e}")

                    _log(f"Traceback: {traceback.format_exc()}")
                finally:
                    pd.close()
                dialog.notification("XStream Player", _t(30281))
            elif choice == 1:
                try:
                    xbmc.executeJSONRPC(
                        '{"jsonrpc":"2.0","method":"PVR.Manager.Stop","id":1}'
                    )
                    xbmc.sleep(1000)
                except Exception as e:
                    _log(f"PVR stop before restart warning: {e}")
                if xbmc.getCondVisibility("System.Platform.Android"):
                    dialog.ok("XStream Player", _t(30569))
                else:
                    xbmc.executebuiltin("RestartApp")
elif mode == "pvr_favs_delete_group":
    group_name = args.get("group", [""])[0]
    dialog = xbmcgui.Dialog()
    if dialog.yesno(_t(30038), _t(30252, group_name)):
        groups = _pvr_favs_load_all()
        if group_name in groups:
            del groups[group_name]
            _pvr_favs_save_all(groups)
            _sync_pvr_favorites()
            dialog.notification("XStream Player", _t(30179, group_name))
            xbmc.executebuiltin("Container.Refresh")
elif mode == "pvr_fav_add":
    sid = args.get("stream_id", [""])[0]
    name = args.get("name", [""])[0]
    icon = args.get("icon", [""])[0]
    group = args.get("group", [_t(30703) or "Favorites"])[0]
    if _pvr_favs_add({"stream_id": sid, "name": name, "stream_icon": icon}, group):
        _sync_pvr_favorites()
        xbmcgui.Dialog().notification("XStream Player", _t(30084).format(group))
        xbmc.sleep(1500)
        xbmcgui.Dialog().ok("XStream Player", _t(30727))
        xbmc.executebuiltin("Container.Refresh")
elif mode == "pvr_fav_remove":
    sid = args.get("stream_id", [""])[0]
    group = args.get("group", [_t(30703) or "Favorites"])[0]
    if _pvr_favs_remove(sid, group):
        _sync_pvr_favorites()
        xbmcgui.Dialog().notification("XStream Player", _t(30085).format(group))
        xbmc.executebuiltin("Container.Refresh")
elif mode == "open_pvr_guide":
    open_pvr_guide()
elif mode == "tools_menu":
    tools_menu()
elif mode == "manage_active_profiles":
    manage_active_profiles()
elif mode == "reorder_main_menu":
    reorder_main_menu()

elif mode == "play_stream":
    try:
        pnum = int(args.get("profile_num", [pm.active])[0])
    except (ValueError, TypeError):
        pnum = pm.active
    _raw_kodi_props = args.get("kodi_props", [""])[0]
    _kodi_props = None
    if _raw_kodi_props:
        try:
            import json as _json
            _kodi_props = _json.loads(_raw_kodi_props)
        except Exception:
            pass  # Malformed JSON in external URL; ignore extra props
    play_stream(
        args.get("url", [""])[0],
        args.get("name", [""])[0],
        args.get("title", [""])[0],
        args.get("plot", [""])[0],
        args.get("icon", [""])[0],
        args.get("stype", ["live"])[0],
        args.get("series_id", [""])[0],
        args.get("season_num", [""])[0],
        args.get("ep_id", [""])[0],
        profile_num=pnum,
        kodi_props=_kodi_props,
        stream_ua=args.get("stream_ua", [""])[0],
        stream_ref=args.get("stream_ref", [""])[0],
    )
elif mode == "settings":
    settings()
elif mode == "switch_profile":
    switch_profile()
elif mode == "view_changelog":
    view_changelog()
elif mode == "test_connection":
    test_connection()
elif mode == "account_info":
    account_info()
elif mode == "check_update":
    from updater import check_and_install_update

    check_and_install_update()
elif mode == "revert_version":
    from updater import revert_version_menu

    revert_version_menu()
elif mode == "toggle_setting":
    key = args.get("key", [""])[0]
    if key:
        current = addon.getSetting(key).lower() == "true"
        addon.setSetting(key, "false" if current else "true")
        xbmcgui.Dialog().notification(
            "XStream Player",
            _t(30306, key.replace("_", " ").title(), _t(30371 if current else 30370)),
        )
        xbmc.executebuiltin("Container.Refresh")
elif mode == "manage_visible_cats":
    manage_visible_cats()
elif mode == "hide_categories_menu":
    try:
        pnum = int(args.get("pnum", [0])[0])
    except (ValueError, TypeError):
        pnum = None
    hide_categories_menu(pnum)
elif mode == "manage_content_dialog":
    manage_content_dialog(args.get("stype", ["live"])[0], args.get("pnum", [None])[0])
elif mode == "manage_load_content":
    # Settings button - manage load TV/Movies/Series toggles
    try:
        pnum = int(args.get("pnum", [1])[0])
    except (ValueError, TypeError):
        pnum = 1
    _manage_load_content_toggles(pnum)
elif mode == "manage_content_select":
    # Settings button - select which content type to manage
    try:
        pnum = int(args.get("pnum", [1])[0])
    except (ValueError, TypeError):
        pnum = 1
    _manage_content_select(pnum)
elif mode == "hidden_items_all":
    stype = args.get("stype", ["live"])[0]
    pnum = args.get("pnum", [None])[0] or pm.active
    hidden_items = _get_hidden_items(stype, pnum)
    if not hidden_items:
        xbmcgui.Dialog().notification("XStream Player", _t(30075))
    else:
        creds = _get_credentials_for_profile(pnum)
        url = creds.get("xtream_url", "")
        m3u_url = creds.get("m3u_url", "")

        if not url and m3u_url:
            # M3U without credentials
            channels = _get_cached_m3u_channels(m3u_url)
            hidden_channels = [
                ch
                for ch in channels
                if str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
                in hidden_items
            ]
            if not hidden_channels:
                xbmcgui.Dialog().notification("XStream Player", _t(30135))
            else:
                h_names = [ch.get("name", "Unknown") for ch in hidden_channels]
                h_ids = [
                    str(ch.get("tvg_id") or ch.get("url") or ch.get("name", ""))
                    for ch in hidden_channels
                ]
                preselect = list(range(len(hidden_channels)))
                result = xbmcgui.Dialog().multiselect(
                    _t(30339), h_names, preselect=preselect
                )
                if result is not None:
                    new_hidden = {h_ids[i] for i in result} if result else set()
                    orphan_ids = hidden_items - set(h_ids)
                    _set_hidden_items(stype, new_hidden | orphan_ids, pnum)
                    unhidden = len(hidden_channels) - (len(result) if result else 0)
                    if unhidden:
                        xbmcgui.Dialog().notification(
                            "XStream Player", _t(30314, unhidden)
                        )
                    xbmc.executebuiltin("Container.Refresh")
        else:
            # Xtream/M3U with credentials
            streams = _get_cached_xtream_streams(
                url,
                creds.get("xtream_username", ""),
                creds.get("xtream_password", ""),
                stype,
            )
            hidden_streams = [
                s
                for s in (streams or [])
                if str(s.get("stream_id", "")) in hidden_items
            ]
            if not hidden_streams:
                xbmcgui.Dialog().notification("XStream Player", _t(30135))
            else:
                h_names = [s.get("name", "Unknown") for s in hidden_streams]
                h_ids = [str(s.get("stream_id", "")) for s in hidden_streams]
                preselect = list(range(len(hidden_streams)))
                result = xbmcgui.Dialog().multiselect(
                    _t(30339), h_names, preselect=preselect
                )
                if result is not None:
                    new_hidden = {h_ids[i] for i in result} if result else set()
                    orphan_ids = hidden_items - set(h_ids)
                    _set_hidden_items(stype, new_hidden | orphan_ids, pnum)
                    unhidden = len(hidden_streams) - (len(result) if result else 0)
                    if unhidden:
                        xbmcgui.Dialog().notification(
                            "XStream Player", _t(30314, unhidden)
                        )
                    xbmc.executebuiltin("Container.Refresh")
elif mode == "manage_hidden_subcats":
    manage_hidden_subcats(args.get("stype", ["live"])[0], args.get("pnum", [None])[0])
elif mode == "hide_m3u_item_action":
    hide_m3u_item_action(
        args.get("stype", ["live"])[0],
        args.get("item_id", [""])[0],
        args.get("item_name", [""])[0],
        args.get("pnum", [None])[0],
    )
elif mode == "hide_subcat_action":
    hide_subcat_action(
        args.get("stype", ["live"])[0],
        args.get("cat_id", [""])[0],
        args.get("cat_name", [""])[0],
        args.get("pnum", [None])[0],
    )
elif mode == "hide_all_subcats":
    hide_all_subcats(
        args.get("stype", ["live"])[0],
        args.get("action", ["hide"])[0],
        args.get("pnum", [None])[0],
    )
elif mode == "backup_settings":
    try:
        backup_settings()
    except Exception as e:
        _log(f"Backup settings error: {e}")
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30090), xbmcgui.NOTIFICATION_ERROR
        )
elif mode == "restore_settings":
    try:
        restore_settings()
    except Exception as e:
        _log(f"Restore settings error: {e}")
        xbmcgui.Dialog().notification(
            "XStream Player", _t(30092), xbmcgui.NOTIFICATION_ERROR
        )
elif mode == "view_backup_path":
    try:
        view_backup_path()
    except Exception as e:
        _log(f"View backup path error: {e}")
elif mode == "change_backup_folder":
    try:
        change_backup_folder()
    except Exception as e:
        _log(f"Change backup folder error: {e}")
        xbmcgui.Dialog().notification("XStream Player", _t(30790))
elif mode == "clear_cache_menu":
    try:
        clear_cache_menu()
    except Exception as e:
        _log(f"Clear cache menu error: {e}")
elif mode == "clear_all_caches":
    try:
        clear_all_caches()
    except Exception as e:
        _log(f"Clear all caches error: {e}")
elif mode == "clear_epg_cache":
    try:
        clear_epg_cache()
    except Exception as e:
        _log(f"Clear EPG cache error: {e}")
elif mode == "reset_pvr_epg_db":
    try:
        reset_pvr_epg_db_action()
    except Exception as e:
        _log(f"Reset PVR EPG DB error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
elif mode == "clear_tmdb_cache":
    try:
        clear_tmdb_cache()
    except Exception as e:
        _log(f"Clear TMDB cache error: {e}")
elif mode == "force_reload_epg":
    try:
        selected = _select_profile_or_all(allow_all=True)
        if selected is None:
            pass
        elif selected == "all":
            pd = xbmcgui.DialogProgress()
            pd.create("XStream Player", _t(30289))
            try:
                for i in range(1, 11):
                    if addon.getSetting(f"profile_{i}_enabled") == "true":
                        pd.update(int((i - 1) * 10), f"{_t(30289)}: Profile {i}")
                        EPG(addon, profile_num=i).fetch()
            finally:
                pd.close()
            xbmcgui.Dialog().notification("XStream Player", _t(30280))
        else:
            pd = xbmcgui.DialogProgress()
            pd.create("XStream Player", _t(30289))
            try:
                EPG(addon, profile_num=int(selected)).fetch()
            finally:
                pd.close()
            xbmcgui.Dialog().notification("XStream Player", _t(30280))
    except Exception as e:
        _log(f"Force reload EPG error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
elif mode == "force_reload_pvr":
    try:
        if xbmcgui.Dialog().yesno("XStream Player", _t(30820)):
            pd = xbmcgui.DialogProgress()
            pd.create("XStream Player", _t(30568))
            try:
                _sync_pvr_force()
            finally:
                pd.close()
            xbmcgui.Dialog().notification("XStream Player", _t(30281))
    except Exception as e:
        _log(f"Force reload PVR error: {e}")

        _log(f"Traceback: {traceback.format_exc()}")
    xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
elif mode == "select_ag_addons":
    select_ag_addons(args.get("group", ["1"])[0])
elif mode == "open_addon_group":
    open_addon_group(args.get("group", ["1"])[0])
elif mode == "open_addon":
    addon_id = args.get("addon_id", [""])[0]
    if not addon_id or not re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", str(addon_id)):
        _log(f"Invalid addon_id format: {addon_id}")
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
    else:
        group = args.get("group", [None])[0]
        # If called from a group, check if group still has only 1 addon
        if group:
            addons = _get_group_addons(int(group))
            if len(addons) > 1:
                open_addon_group(group)
            else:
                xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
                xbmc.executebuiltin(f"Container.Update(plugin://{addon_id})")
        else:
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            xbmc.executebuiltin(f"Container.Update(plugin://{addon_id})")
elif mode == "empty_addon_group":
    empty_addon_group(args.get("group", ["1"])[0])
elif mode == "continue_watching":
    continue_watching_menu()
elif mode == "recently_watched_by_type":
    try:
        pnum = int(args.get("pnum", [pm.active])[0])
    except (ValueError, TypeError):
        pnum = pm.active
    recently_watched_by_type(args.get("stype", ["movie"])[0], pnum=pnum)
elif mode == "profile_recently_watched":
    try:
        pnum = int(args.get("pnum", [pm.active])[0])
    except (ValueError, TypeError):
        pnum = pm.active
    profile_recently_watched(pnum)
elif mode == "reset_reload_menu":
    reset_reload_menu()
elif mode == "account_iptv_menu":
    account_iptv_menu()
elif mode == "loaded_profiles_view":
    try:
        loaded_profiles_view()
    except Exception as e:
        _log(f"Loaded profiles view error: {e}")
elif mode == "relaunch_kodi":
    try:
        relaunch_kodi_action()
    except Exception as e:
        _log(f"Relaunch Kodi error: {e}")
elif mode == "install_upnext":
    try:
        install_upnext()
    except Exception as e:
        _log(f"Install Up Next error: {e}")
elif mode == "open_upnext_settings":
    try:
        open_upnext_settings()
    except Exception as e:
        _log(f"Open Up Next settings error: {e}")

# One-time startup bootstrap (must run after all helpers are defined)
_run_one_time_bootstrap()
