# -*- coding: utf-8 -*-
import json
import os

import xbmc
import xbmcvfs

from lang import _t


class Favorites:
    def __init__(self, addon, profile_num="1"):
        self.profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        self.file = os.path.join(self.profile_path, f"favorites_{profile_num}.json")
        self._ensure_profile()
        # Note: No migration from global favorites - each profile starts with empty favorites
        # This ensures complete isolation between global and profile-specific favorites
        self.items = self._load()

    def _ensure_profile(self):
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)

    def _load(self):
        folder_name = _t(30009) or "Favorites"
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migration: old format was flat list, new format has folders
                if isinstance(data, list):
                    return {"version": 1, folder_name: data}
                if isinstance(data, dict) and "version" not in data:
                    data["version"] = 1
                return data
        except FileNotFoundError:
            return {"version": 1, folder_name: []}
        except Exception as e:
            xbmc.log(
                f"[XStream Player] Favorites load failed for {self.file}: {e}",
                xbmc.LOGWARNING,
            )
            # Backup corrupted file if it exists
            if os.path.exists(self.file):
                try:
                    os.replace(self.file, self.file + ".corrupted")
                except OSError:
                    pass
            return {"version": 1, folder_name: []}

    def _save(self):
        tmp_file = self.file + ".tmp"
        payload = {"version": 1, **self.items}
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            # fsync before rename for Android durability.
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self.file)

    def get_folders(self):
        """Return list of folder names."""
        return [k for k in self.items.keys() if k != "version"]

    def is_favorite(self, item_id, folder=None):
        if folder:
            return any(i.get("id") == item_id for i in self.items.get(folder, []))
        return any(
            i.get("id") == item_id
            for k, items in self.items.items()
            if k != "version"
            for i in items
        )

    def add(self, item, folder=None):
        # Resolve default folder at call time to track UI language changes.
        if folder is None:
            folder = _t(30009) or "Favorites"
        if folder not in self.items:
            self.items[folder] = []
        if not self.is_favorite(item.get("id"), folder):
            self.items[folder].append(item)
            self._save()
            return True
        return False

    def remove(self, item_id, folder=None):
        removed = False
        if folder:
            before = len(self.items.get(folder, []))
            self.items[folder] = [
                i for i in self.items.get(folder, []) if i.get("id") != item_id
            ]
            removed = len(self.items[folder]) < before
        else:
            for f in self.items:
                if f == "version":
                    continue
                before = len(self.items[f])
                self.items[f] = [i for i in self.items[f] if i.get("id") != item_id]
                if len(self.items[f]) < before:
                    removed = True
        if removed:
            self._save()
        return removed

    def remove_by_type(self, folder, stype):
        if folder not in self.items:
            return False
        before = len(self.items[folder])
        self.items[folder] = [
            i for i in self.items[folder] if i.get("stype", "live") != stype
        ]
        removed = len(self.items[folder]) < before
        if removed:
            self._save()
        return removed

    def get_all(self, folder=None):
        if folder:
            return self.items.get(folder, [])
        # Flat list of all items across all folders
        result = []
        for k, items in self.items.items():
            if k == "version":
                continue
            result.extend(items)
        return result

    def toggle(self, item, folder=None):
        if folder is None:
            folder = _t(30009) or "Favorites"
        if self.is_favorite(item.get("id")):
            self.remove(item.get("id"))
            return False
        else:
            self.add(item, folder)
            return True

    def create_folder(self, name):
        if name == "version" or name in self.items:
            return
        self.items[name] = []
        self._save()

    def rename_folder(self, old_name, new_name):
        if new_name == "version":
            return
        if old_name in self.items and new_name not in self.items:
            self.items[new_name] = self.items.pop(old_name)
            self._save()

    def delete_folder(self, name):
        # Protect default folder across all UI languages.
        protected = {"Favorites", _t(30009) or "Favorites", "version"}
        if name in self.items and name not in protected:
            del self.items[name]
            self._save()

    def export_m3u(self, path, folder=None):
        """Export favorites as M3U file."""
        items = self.get_all(folder)
        lines = ["#EXTM3U"]
        for item in items:
            name = item.get("name", "Unknown")
            url = item.get("url", "")
            icon = item.get("icon", "")
            if not url:
                continue
            attrs = f'tvg-name="{name}"'
            if icon:
                attrs += f' tvg-logo="{icon}"'
            lines.append(f"#EXTINF:-1 {attrs},{name}")
            lines.append(url)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
        return len(items)
