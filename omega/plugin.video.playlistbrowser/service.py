# -*- coding: utf-8 -*-
"""Refresh playlist caches in the background while Kodi is running."""
import json
import os
import time
import gzip
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcvfs

from main import (PROFILE, _playlist_cache_paths, get_int_setting,
                  load_sources, log, parse_json, parse_m3u, read_text)

REQUEST_PATH = os.path.join(PROFILE, 'refresh_all.request')

def refresh_playlist(source, hours=None):
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
    sources = [s for s in load_sources() if not getattr(s, 'alias_source', None)]
    failures = 0
    for source in sources:
        if monitor.abortRequested():
            return
        if not refresh_playlist(source):
            failures += 1
        if source.epg:
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
    """Update the XML cache without constructing every programme in memory."""
    xml_path, gz_path = source._cache_paths()
    temp_path = xml_path + '.refresh.tmp'
    try:
        if source.epg.startswith(('http://', 'https://')):
            req = Request(source.epg, headers={'User-Agent': 'Mozilla/5.0 (Kodi Addon)'})
            with urlopen(req, timeout=90) as response:
                data = response.read()
        else:
            stream = xbmcvfs.File(source.epg)
            try:
                data = stream.read()
            finally:
                stream.close()
            if isinstance(data, str):
                data = data.encode('utf-8')
        xml_data = gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data
        with open(temp_path, 'wb') as output:
            output.write(xml_data)
        # Check the document before replacing a working cache.
        root = next(ET.iterparse(temp_path, events=('start',)))[1]
        if root.tag.rsplit('}', 1)[-1].lower() != 'tv':
            raise ValueError('EPG response is not XMLTV')
        os.replace(temp_path, xml_path)
        if os.path.exists(gz_path):
            os.remove(gz_path)  # prevent the normal reader using an older gzip cache
        log(f"Background EPG cache updated for source {source.idx}")
        return True
    except Exception as exc:
        log(f"Background EPG download failed for source {source.idx}: {exc}")
        return False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


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
