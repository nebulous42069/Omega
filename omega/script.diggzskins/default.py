# -*- coding: utf-8 -*-
import os
import json
import xbmc
import xbmcgui
import xbmcvfs

ADDON_ID = "script.diggzskins"
ADDON_PATH = xbmcvfs.translatePath("special://home/addons/%s" % ADDON_ID)
PRESETS_PATH = os.path.join(ADDON_PATH, "resources", "data", "presets.json")
UI_XML = "script-diggzskins.xml"
UI_PATH = os.path.join("resources", "skins", "Default", "1080i", UI_XML)

def _jsonrpc(payload):
    try:
        import json as _json
        if isinstance(payload, dict):
            payload = _json.dumps(payload)
        res = xbmc.executeJSONRPC(payload)
        return _json.loads(res)
    except Exception as e:
        xbmc.log("DiggzSkins JSONRPC error: %s" % e, xbmc.LOGERROR)
        return {}

def _get_setting(setting):
    res = _jsonrpc({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Settings.GetSettingValue",
        "params": {"setting": setting}
    })
    return res.get("result", {}).get("value")

def _set_setting(setting, value):
    _jsonrpc({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Settings.SetSettingValue",
        "params": {"setting": setting, "value": value}
    })

def _wait_until(cond_fn, timeout_ms=15000, step_ms=120):
    waited = 0
    while waited < timeout_ms:
        try:
            if cond_fn():
                return True
        except Exception:
            pass
        xbmc.sleep(step_ms)
        waited += step_ms
    return False

def _get_installed_skins_map():
    q = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Addons.GetAddons",
        "params": {
            "type": "xbmc.gui.skin",
            "installed": True,
            "properties": ["name", "enabled", "installed", "version", "thumbnail"]
        }
    }
    data = _jsonrpc(q)
    addons = data.get("result", {}).get("addons", []) or []
    return {a["addonid"]: a for a in addons}

def install_addon(addonid):
    try:
        xbmc.executebuiltin("InstallAddon(%s)" % addonid, True)
        xbmc.executebuiltin("UpdateLocalAddons")
        # Wait briefly for Kodi to register the install
        _wait_until(lambda: xbmc.getCondVisibility(f"System.HasAddon({addonid})"), timeout_ms=12000)
        return xbmc.getCondVisibility(f"System.HasAddon({addonid})")
    except Exception as e:
        xbmcgui.Dialog().notification("Install failed", str(e), xbmcgui.NOTIFICATION_ERROR, 3500)
        return False

def _get_addon_details(addonid):
    q = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "Addons.GetAddonDetails",
        "params": {
            "addonid": addonid,
            "properties": ["name", "enabled", "installed", "path", "thumbnail", "version"]
        }
    }
    return _jsonrpc(q).get("result", {}).get("addon", {})

def ensure_enabled(addonid):
    try:
        _jsonrpc({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Addons.SetAddonEnabled",
            "params": {"addonid": addonid, "enabled": True}
        })
    except Exception:
        pass

def _auto_accept_keep_skin(timeout_ms=12000):
    waited = 0
    checks = [
        'Window.IsVisible(yesnodialog)',
        'Window.IsVisible(DialogYesNo.xml)',
        'Window.IsVisible(YesNoDialog)'
    ]
    while waited < timeout_ms:
        if any(xbmc.getCondVisibility(c) for c in checks):
            xbmc.sleep(80)
            xbmc.executebuiltin('SendClick(11)')  # Yes
            xbmc.sleep(120)
            return True
        xbmc.sleep(100)
        waited += 100
    return False

def switch_skin(addonid):
    ensure_enabled(addonid)
    xbmc.executebuiltin('Dialog.Close(all,true)')
    xbmc.sleep(150)
    xbmc.executebuiltin('ActivateWindow(home)')
    xbmc.sleep(150)
    _jsonrpc({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Settings.SetSettingValue',
        'params': {'setting': 'lookandfeel.skin', 'value': addonid}
    })
    _auto_accept_keep_skin()

def _load_presets():
    data_override = xbmcvfs.translatePath("special://profile/addon_data/%s/presets.json" % ADDON_ID)
    path = data_override if xbmcvfs.exists(data_override) else PRESETS_PATH
    try:
        f = xbmcvfs.File(path, 'r')
        try:
            raw_data = f.read()
        finally:
            f.close()
        raw = raw_data.decode("utf-8", "replace") if isinstance(raw_data, bytes) else raw_data
        items = json.loads(raw)
        norm = []
        for it in items:
            norm.append({
                "name": it.get("name") or it.get("title") or "",
                "description": it.get("description") or "",
                "screenshot": it.get("screenshot") or it.get("image") or "",
                "addon_id": it.get("id") or it.get("addon_id") or it.get("skin_id") or ""
            })
        return norm
    except Exception as e:
        try:
            xbmcgui.Dialog().ok("Diggz Skin Switcher", "Failed to read presets.json:\n%s" % e)
        except Exception:
            xbmc.log("DiggzSkin presets load error: %s" % e, xbmc.LOGERROR)
        return []

class SkinGallery(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.items = kwargs.get("items", [])
        self.installed_map = kwargs.get("installed_map", {})
        self.panel_id = 100
        self.title_id = 10

    def onInit(self):
        # set title if you have a title control
        try:
            title = self.getControl(self.title_id)
            if title:
                title.setLabel("Diggz Skin Switcher")
        except Exception:
            pass

        # populate the panel
        panel = self.getControl(self.panel_id)
        if panel:
            panel.reset()
            for it in self.items:
                li = xbmcgui.ListItem(label=it.get("name", ""),
                                      label2=it.get("description", ""))
                art = {"thumb": it.get("screenshot", ""), "icon": it.get("screenshot", "")}
                li.setArt(art)
                li.setProperty("addonid", it.get("addon_id",""))
                li.setProperty("installed", "true" if it.get("addon_id","") in self.installed_map else "false")
                panel.addItem(li)

        # yield a tick so layouts exist, then force selection and focus
        xbmc.sleep(50)
        try:
            if panel and panel.size() > 0:
                panel.selectItem(0)              # highlight first card
                self.setFocusId(self.panel_id)   # give focus to control 100
        except Exception:
            pass


    def _selected(self):
        panel = self.getControl(self.panel_id)
        if not panel or panel.size() == 0:
            return None
        return panel.getSelectedItem()

    def onClick(self, controlId):
        # No dialog. Click = install if needed, then switch.
        if controlId != self.panel_id:
            return
        li = self._selected()
        if not li:
            return

        addonid = li.getProperty("addonid")
        name = li.getLabel()
        is_installed = li.getProperty("installed") == "true"

        try:
            if not is_installed:
                ok = install_addon(addonid)
                if not ok:
                    xbmcgui.Dialog().notification("Install failed", name, xbmcgui.NOTIFICATION_ERROR, 3000)
                    return
                li.setProperty("installed", "true")
                xbmcgui.Dialog().notification("Installed", name, xbmcgui.NOTIFICATION_INFO, 2000)

            switch_skin(addonid)

        except Exception as e:
            xbmcgui.Dialog().notification("Action failed", str(e), xbmcgui.NOTIFICATION_ERROR, 3500)

def run():
    items = _load_presets()
    installed_map = _get_installed_skins_map()
    w = SkinGallery(UI_XML, ADDON_PATH, "Default", "1080i", items=items, installed_map=installed_map)
    w.doModal()
    del w

if __name__ == "__main__":
    run()
