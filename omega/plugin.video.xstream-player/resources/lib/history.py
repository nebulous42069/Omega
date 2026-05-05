# -*- coding: utf-8 -*-
"""Watch history tracking — stores last N watched items with deduplication."""

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs
import re

MAX_HISTORY = 50


def _get_active_profile_num(addon):
    raw = addon.getSetting("active_pvr_profile") or "Profile 1"
    match = re.search(r"(\d+)$", raw)
    try:
        return int(match.group(1)) if match else 1
    except Exception:
        return 1


class WatchHistory:
    def __init__(self, addon=None, profile_num=None):
        if addon is None:
            addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile):
            os.makedirs(profile)
        pnum = profile_num if profile_num is not None else _get_active_profile_num(addon)
        if profile_num is None:
            xbmc.log(
                f"[XStream Player] Warning: WatchHistory instantiated without profile_num, falling back to PVR profile {pnum}",
                xbmc.LOGWARNING,
            )
        self._path = os.path.join(profile, f"watch_history_p{pnum}.json")
        self._items = self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save(self):
        tmp_file = self._path + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self._path)

    def add(self, name, url, icon="", stype="live", extra=None):
        """Add an item to history. Deduplicates by name+stype, most recent first."""
        entry = {
            "name": name,
            "url": url,
            "icon": icon,
            "stype": stype,
            "timestamp": time.time(),
        }
        if extra and isinstance(extra, dict):
            entry.update(extra)
        # Remove existing entry with same name+stype
        self._items = [
            i
            for i in self._items
            if not (i.get("name") == name and i.get("stype") == stype)
        ]
        # Insert at front
        self._items.insert(0, entry)
        # Trim
        self._items = self._items[:MAX_HISTORY]
        self._save()

    def get_all(self, stype=None):
        """Return history items, optionally filtered by type."""
        if stype:
            return [i for i in self._items if i.get("stype") == stype]
        return list(self._items)

    def clear(self):
        self._items = []
        self._save()

    def remove(self, name, stype=None):
        """Remove a specific item from history."""
        if stype:
            self._items = [
                i
                for i in self._items
                if not (i.get("name") == name and i.get("stype") == stype)
            ]
        else:
            self._items = [i for i in self._items if i.get("name") != name]
        self._save()

    def clear_by_type(self, stype):
        """Clear all history items of a specific type."""
        self._items = [i for i in self._items if i.get("stype") != stype]
        self._save()


class ResumePoints:

    def __init__(self, addon=None, profile_num=None):
        if addon is None:
            addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile):
            os.makedirs(profile)
        if profile_num is None:
            pnum = _get_active_profile_num(addon)
            xbmc.log(
                f"[XStream Player] Warning: ResumePoints instantiated without profile_num, falling back to PVR profile {pnum}",
                xbmc.LOGWARNING,
            )
        else:
            pnum = profile_num
        self._path = os.path.join(profile, f"resume_points_p{pnum}.json")
        self._data = self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self):
        tmp_file = self._path + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self._path)

    def _key(self, name, url):
        return f"{name}||{url}"

    def save_position(self, name, url, position, duration):
        """Save playback position. Only saves if >60s in and not near the end."""
        if position < 60 or duration < 120:
            return
        if position > duration * 0.93:
            # Near end — mark as finished, remove resume point
            self._data.pop(self._key(name, url), None)
            self._save()
            return
        self._data[self._key(name, url)] = {
            "name": name,
            "url": url,
            "position": position,
            "duration": duration,
            "timestamp": time.time(),
        }
        self._save()

    def get_position(self, name, url):
        """Return saved position in seconds, or 0 if none."""
        entry = self._data.get(self._key(name, url))
        if entry:
            return entry.get("position", 0)
        return 0

    def remove(self, name, url):
        self._data.pop(self._key(name, url), None)
        self._save()

    def clear(self):
        self._data = {}
        self._save()


class WatchedMovies:

    def __init__(self, addon=None, profile_num=None):
        if addon is None:
            addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile):
            os.makedirs(profile)
        pnum = (
            profile_num if profile_num is not None else _get_active_profile_num(addon)
        )
        if profile_num is None:
            xbmc.log(
                f"[XStream Player] Warning: WatchedMovies instantiated without profile_num, falling back to PVR profile {pnum}",
                xbmc.LOGWARNING,
            )
        self._path = os.path.join(profile, f"watched_movies_p{pnum}.json")
        self._data = self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self):
        tmp_file = self._path + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self._path)

    def mark_watched(self, stream_id):
        """Mark a movie as watched."""
        self._data[str(stream_id)] = True
        self._save()

    def mark_unwatched(self, stream_id):
        """Mark a movie as unwatched."""
        self._data.pop(str(stream_id), None)
        self._save()

    def is_watched(self, stream_id):
        """Check if a movie has been watched."""
        return str(stream_id) in self._data

    def clear(self):
        self._data = {}
        self._save()


class WatchedEpisodes:

    def __init__(self, addon=None, profile_num=None):
        if addon is None:
            addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile):
            os.makedirs(profile)
        pnum = (
            profile_num if profile_num is not None else _get_active_profile_num(addon)
        )
        if profile_num is None:
            xbmc.log(
                f"[XStream Player] Warning: WatchedEpisodes instantiated without profile_num, falling back to PVR profile {pnum}",
                xbmc.LOGWARNING,
            )
        self._path = os.path.join(profile, f"watched_episodes_p{pnum}.json")
        self._data = self._load()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self):
        tmp_file = self._path + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_file, self._path)

    def mark_watched(self, series_id, season_num, episode_id):
        """Mark an episode as watched."""
        key = str(series_id)
        if key not in self._data:
            self._data[key] = {}
        season = str(season_num)
        if season not in self._data[key]:
            self._data[key][season] = []
        ep_id = str(episode_id)
        if ep_id not in self._data[key][season]:
            self._data[key][season].append(ep_id)
            self._save()

    def mark_unwatched(self, series_id, season_num, episode_id):
        """Mark an episode as unwatched."""
        key = str(series_id)
        season = str(season_num)
        if key in self._data and season in self._data[key]:
            ep_id = str(episode_id)
            if ep_id in self._data[key][season]:
                self._data[key][season].remove(ep_id)
                self._save()

    def is_watched(self, series_id, season_num, episode_id):
        """Check if an episode has been watched."""
        key = str(series_id)
        season = str(season_num)
        return str(episode_id) in self._data.get(key, {}).get(season, [])

    def get_watched_count(self, series_id, season_num=None):
        """Get count of watched episodes for a series or season."""
        key = str(series_id)
        if key not in self._data:
            return 0
        if season_num is not None:
            return len(self._data[key].get(str(season_num), []))
        return sum(len(eps) for eps in self._data[key].values())

    def clear_series(self, series_id):
        """Clear all watched data for a series."""
        key = str(series_id)
        if key in self._data:
            del self._data[key]
            self._save()

    def mark_season_watched(self, series_id, season_num, episode_ids):
        """Mark all episodes in a season as watched."""
        key = str(series_id)
        if key not in self._data:
            self._data[key] = {}
        season = str(season_num)
        if season not in self._data[key]:
            self._data[key][season] = []
        for ep_id in episode_ids:
            ep_str = str(ep_id)
            if ep_str not in self._data[key][season]:
                self._data[key][season].append(ep_str)
        self._save()

    def mark_season_unwatched(self, series_id, season_num):
        """Mark all episodes in a season as unwatched."""
        key = str(series_id)
        season = str(season_num)
        if key in self._data and season in self._data[key]:
            del self._data[key][season]
            self._save()

    def is_season_fully_watched(self, series_id, season_num, total_episodes):
        """Check if all episodes in a season are watched."""
        return self.get_watched_count(series_id, season_num) >= total_episodes

    def clear(self):
        self._data = {}
        self._save()
