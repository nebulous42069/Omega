#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, time
import xbmc, xbmcaddon, xbmcgui  # type: ignore

ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
TARGET_ID  = 'pvr.iptvsimple'

def log(msg: str) -> None:
    try:
        xbmc.log(f"[{ADDON_ID}] {msg}", xbmc.LOGINFO)
    except Exception:
        pass

def jsonrpc(method: str, params: dict | None = None) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        payload["params"] = params
    resp = xbmc.executeJSONRPC(json.dumps(payload))
    try:
        return json.loads(resp)
    except Exception:
        return {"error": "json parse failed", "raw": resp}

def notify(heading: str, msg: str, ms: int = 2500) -> None:
    xbmcgui.Dialog().notification(heading, msg, xbmcgui.NOTIFICATION_INFO, ms)

def ensure_addon_installed(addon_id: str) -> bool:
    if xbmc.getCondVisibility(f"System.HasAddon({addon_id})"):
        jsonrpc("Addons.SetAddonEnabled", {"addonid": addon_id, "enabled": True})
        return True
    xbmc.executebuiltin(f"InstallAddon({addon_id})", True)
    for _ in range(60):
        if xbmc.getCondVisibility(f"System.HasAddon({addon_id})"):
            jsonrpc("Addons.SetAddonEnabled", {"addonid": addon_id, "enabled": True})
            return True
        xbmc.sleep(500)
    return False


# ---------- Profile purge + XML copy ----------
def purge_iptv_profile_dir() -> int:
    """Delete everything in special://profile/addon_data/pvr.iptvsimple/"""
    import xbmcvfs, os, shutil, glob
    prof = _iptv_profile_dir()
    removed = 0
    try:
        if not xbmcvfs.exists(prof):
            xbmcvfs.mkdirs(prof)
            return 0
        # Delete files
        for fp in glob.glob(os.path.join(prof, "*")):
            try:
                if xbmcvfs.exists(fp):
                    # Try delete as file
                    if not xbmcvfs.delete(fp):
                        # If it's a directory, recurse
                        try:
                            shutil.rmtree(fp)
                            removed += 1
                            continue
                        except Exception:
                            pass
                    else:
                        removed += 1
                        continue
                # Fallback
                try:
                    os.remove(fp); removed += 1
                except Exception:
                    pass
            except Exception:
                pass
    except Exception as e:
        log(f"purge_iptv_profile_dir error: {e}")
    return removed

def copy_preset_instance_settings(xmlkey: str) -> bool:
    """Copy resources/Presets/<xmlkey>/instance-settings-1.xml to the IPTV Simple profile dir."""
    import xbmcvfs, os, shutil
    src = xbmcvfs.translatePath(os.path.join(ADDON.getAddonInfo('path'), 'resources', 'Presets', xmlkey, 'instance-settings-1.xml'))
    dest_dir = _iptv_profile_dir()
    dest = os.path.join(dest_dir, 'instance-settings-1.xml')
    try:
        if not xbmcvfs.exists(src):
            xbmcgui.Dialog().ok(ADDON_NAME, f"Missing preset XML for '{xmlkey}'.")
            log(f"missing preset instance-settings at {src}")
            return False
        if not xbmcvfs.exists(dest_dir):
            xbmcvfs.mkdirs(dest_dir)
        # Prefer xbmcvfs copy
        try:
            data = xbmcvfs.File(src).readBytes()
            f = xbmcvfs.File(dest, 'w')
            try:
                f.write(data)
            finally:
                f.close()
        except Exception:
            # Fallback to shutil if xbmcvfs not available
            try:
                shutil.copyfile(src, dest)
            except Exception as e:
                log(f"copy fallback failed: {e}")
                return False
        log(f"Copied preset XML {src} -> {dest}")
        return True
    except Exception as e:
        log(f"copy_preset_instance_settings error: {e}")
        return False
# ---------- Settings / instances ----------
def _iptv_profile_dir() -> str:
    import xbmcvfs
    return xbmcvfs.translatePath("special://profile/addon_data/pvr.iptvsimple/")



def stop_pvr_and_wait(max_ms: int = 8000) -> None:
    log("stop_pvr_and_wait()")
    try:
        jsonrpc("Addons.SetAddonEnabled", {"addonid": TARGET_ID, "enabled": False})
    except Exception:
        pass
    xbmc.executebuiltin("StopPVRManager")
    t, step = 0, 400
    while t < max_ms:
        try:
            grp = jsonrpc("PVR.GetChannelGroups", {"channeltype": "tv"})
            groups = (grp.get("result") or {}).get("channelgroups", []) if isinstance(grp, dict) else []
            if not groups:
                log("PVR appears stopped (no channel groups)")
                return
        except Exception:
            log("PVR.GetChannelGroups threw; assuming stopped")
            return
        xbmc.sleep(step); t += step
    log("stop_pvr_and_wait(): timeout; proceeding anyway")

def clear_pvr_data() -> tuple[int, int]:
    log("clear_pvr_data() begin")
    try:
        try:
            jsonrpc("PVR.ClearEPG", {})
            log("PVR.ClearEPG invoked")
        except Exception:
            pass
        import xbmcvfs, os, glob
        removed_db = 0
        dbdir = xbmcvfs.translatePath("special://database/")
        patterns = ["Epg*.db", "Epg*.db-shm", "Epg*.db-wal",
                    "TV*.db",  "TV*.db-shm",  "TV*.db-wal"]
        for attempt in range(1, 6):
            this_round = 0
            for pat in patterns:
                for fp in glob.glob(os.path.join(dbdir, pat)):
                    try:
                        ok = xbmcvfs.delete(fp)
                        if not ok:
                            try:
                                os.remove(fp); ok = True
                            except Exception:
                                ok = False
                        if ok:
                            removed_db += 1; this_round += 1
                    except Exception:
                        pass
            if this_round == 0:
                break
            xbmc.sleep(500)
        # Purge all IPTV Simple profile files
        removed_cache = purge_iptv_profile_dir()
        log(f"clear_pvr_data done: removed_db={removed_db}, removed_profile_items={removed_cache}")
        return removed_db, removed_cache
    except Exception as e:
        xbmcgui.Dialog().notification(ADDON_NAME, f"Clear failed: {e}", xbmcgui.NOTIFICATION_ERROR, 4000)
        log(f"clear failed: {e}")
        return 0, 0

# ---------- Presets (settings + bundled) ----------
def load_bundled_presets() -> list[dict]:
    """Read resources/presets.json and yield items with {"label": str, "xmlkey": str}."""
    try:
        import xbmcvfs, os, json as _json
        path = xbmcvfs.translatePath(os.path.join(ADDON.getAddonInfo('path'), 'resources', 'presets.json'))
        if not xbmcvfs.exists(path):
            log(f"no presets.json at {path}")
            return []
        f = xbmcvfs.File(path)
        try:
            data = f.read()
        finally:
            f.close()
        s = data.decode('utf-8', 'ignore') if isinstance(data, (bytes, bytearray)) else data
        arr = _json.loads(s) if s else []
    except Exception as e:
        log(f"failed to load presets: {e}")
        arr = []
    out = []
    for item in arr or []:
        try:
            label = (item.get("name") or item.get("label") or "").strip()
            xmlkey = (item.get("xml") or "").strip()
            if label and xmlkey:
                out.append({"label": label, "xmlkey": xmlkey})
        except Exception:
            pass
    return out

def prompt_install_iptv_if_missing() -> bool:
    log("prompt_install_iptv_if_missing()")
    try:
        if xbmc.getCondVisibility(f"System.HasAddon({TARGET_ID})"):
            return True
    except Exception:
        pass
    if xbmcgui.Dialog().yesno(ADDON_NAME, "IPTV Simple client is required.", "Install pvr.iptvsimple now?"):
        notify(ADDON_NAME, "Installing IPTV Simple…")
        ok = ensure_addon_installed(TARGET_ID)
        if not ok:
            xbmcgui.Dialog().ok(ADDON_NAME, "Could not install/enable pvr.iptvsimple.")
        return ok
    return False

def choose_preset_or_custom() -> dict:
    log("choose_preset_or_custom()")
    d = xbmcgui.Dialog()
    bundled = load_bundled_presets()
    labels = [p["label"] for p in bundled]
    if not labels:
        xbmcgui.Dialog().ok(ADDON_NAME, "No presets found in presets.json")
        return {}
    choice = d.select("Select preset", labels)
    if choice < 0:
        return {}
    chosen = bundled[choice]
    return {"xmlkey": chosen["xmlkey"]}

# ---------- Entry (direct to presets) ----------
def run() -> None:
    log("run() start"); log("version=" + ADDON.getAddonInfo('version'))
    info = choose_preset_or_custom()
    if not info:
        notify(ADDON_NAME, "Cancelled"); return
    if not ensure_addon_installed(TARGET_ID):
        xbmcgui.Dialog().ok(ADDON_NAME, "Could not install/enable pvr.iptvsimple."); return
    pass  # settings will be applied via instance-settings XML copy
    notify(ADDON_NAME, "Stopping PVR…")
    stop_pvr_and_wait(8000)
    db_cnt, cache_cnt = clear_pvr_data()
    xbmcgui.Dialog().ok(ADDON_NAME, f"Purged {db_cnt} DB + {cache_cnt} file(s).")
    # Copy preset instance settings
    xmlkey = info.get("xmlkey") or ""
    if not xmlkey:
        xbmcgui.Dialog().ok(ADDON_NAME, "No preset selected.")
        return
    if not copy_preset_instance_settings(xmlkey):
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to apply preset XML.")
        return
    try:
        jsonrpc("Addons.SetAddonEnabled", {"addonid": TARGET_ID, "enabled": True})
        log("pvr.iptvsimple enabled for next start")
    except Exception as e:
        log(f"failed to enable pvr.iptvsimple: {e}")
    # Final notice and close Kodi
    xbmcgui.Dialog().ok(ADDON_NAME, "EPG Enabled. Kodi Will Close To Apply PVR Settings")
    try:
        xbmc.executebuiltin("Quit")
    except Exception:
        pass
    return

if __name__ == "__main__":
    run()
