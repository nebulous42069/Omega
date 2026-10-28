# -*- coding: utf-8 -*-
"""Refresh playlist caches in the background while Kodi is running."""
import json
import os
import time

import xbmc
import xbmcgui

from main import (PROFILE, _playlist_cache_paths, get_int_setting,
                  load_sources, log, parse_json, parse_m3u, read_text)

REQUEST_PATH = os.path.join(PROFILE, 'refresh_all.request')

def refresh_playlist(source, hours=None):
    if getattr(source, 'integrated_dlhd', False) and not __import__('xbmcvfs').exists(source.m3u):
        try:
            from dlhd.exporter import ensure_playlist
            ensure_playlist(__import__('xbmcaddon').Addon('plugin.video.playlistbrowser'))
        except Exception as error:
            log('DaddyLive first-run export pending: ' + type(error).__name__)
            return False
    _, cache_path = _playlist_cache_paths(source.idx, source)
    if hours is not None and os.path.isfile(cache_path):
        try:
            if time.time() - os.path.getmtime(cache_path) < hours * 3600:
                return True
        except OSError:
            pass
    try:
        raw = read_text(source.js or source.m3u)
        channels = parse_json(raw) if source.js else parse_m3u(raw)
        if not channels:
            log(f"Playlist refresh returned no channels for source {source.idx}; keeping cache")
            return False
        temp_path = cache_path + '.scheduled.tmp'
        with open(temp_path, 'w', encoding='utf-8') as output:
            json.dump(channels, output, ensure_ascii=False)
        os.replace(temp_path, cache_path)
        log(f"Playlist refresh: {len(channels)} channels for source {source.idx}")
        return True
    except Exception as exc:
        log(f"Playlist refresh failed for source {source.idx}: {exc}")
        return False


def refresh_due_playlists(hours):
    for source in load_sources():
        if not getattr(source, 'alias_source', None):
            refresh_playlist(source, hours)


def refresh_all(monitor):
    sources = load_sources()
    refreshed_epgs = set()
    failures = 0
    for source in sources:
        if monitor.abortRequested():
            return
        if not getattr(source, 'alias_source', None) and not refresh_playlist(source):
            failures += 1
        epg_key = source._cache_paths()[0] if source.epg else None
        if epg_key and epg_key not in refreshed_epgs:
            refreshed_epgs.add(epg_key)
            try:
                if not refresh_epg_file(source):
                    failures += 1
            except Exception as exc:
                failures += 1
                log(f"Background EPG refresh failed for source {source.idx}: {exc}")
        # Give Kodi time to populate other skin widgets between sources.
        if monitor.waitForAbort(2):
            return
    message = ('Refresh complete' if not failures else
               f'Refresh complete with {failures} failed playlist/EPG updates')
    xbmcgui.Dialog().notification('Playlist Browser', message, xbmcgui.NOTIFICATION_INFO, 5000)


def refresh_epg_file(source):
    """Refresh the same shared cache used by foreground widget requests."""
    try:
        _, updated = source._cached_epg(force=True)
        return updated
    except Exception as exc:
        log(f"Background EPG download failed for source {source.idx}: {type(exc).__name__}")
        return False


def run():
    monitor = xbmc.Monitor()
    last_scheduled_check = 0
    while not monitor.abortRequested():
        if os.path.exists(REQUEST_PATH):
            try:
                os.remove(REQUEST_PATH)
                refresh_all(monitor)
            except Exception as exc:
                log(f"Background refresh-all failed: {exc}")
        if time.time() - last_scheduled_check >= 300:
            last_scheduled_check = time.time()
            hours = max(0, get_int_setting('M3U_REFRESH_HOURS', 6))
            if hours:
                refresh_due_playlists(hours)
        if monitor.waitForAbort(5):
            break


if __name__ == '__main__':
    run()
