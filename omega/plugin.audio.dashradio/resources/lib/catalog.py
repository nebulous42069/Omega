"""Public LITT Live station snapshot, with a cached and bundled fallback."""
import json
import os
import time
from urllib.request import Request, urlopen

ENDPOINT = 'https://v4.dash-api.com/stations/events'
MAX_AGE = 6 * 60 * 60
MAX_BYTES = 2 * 1024 * 1024
FIELDS = ('station_id', 'station_name', 'station_slug', 'station_genre',
          'genre_order', 'genre_priority', 'description', 'logo_url',
          'image_url', 'stream_url', 'is_explicit')


def validate(payload):
    stations = payload.get('stations') if isinstance(payload, dict) else None
    if not isinstance(stations, list) or not stations:
        raise ValueError('Empty station catalog')
    result, seen = [], set()
    for station in stations:
        if not isinstance(station, dict):
            raise ValueError('Invalid station')
        if not all(isinstance(station.get(k), str) and station[k].strip()
                   for k in ('station_id', 'station_name', 'station_genre', 'stream_url')):
            raise ValueError('Incomplete station')
        if not station['stream_url'].startswith(('https://', 'http://')):
            raise ValueError('Invalid stream URL')
        if station['station_id'] in seen:
            raise ValueError('Duplicate station ID')
        seen.add(station['station_id'])
        result.append({key: station.get(key) for key in FIELDS})
    return result


def read_snapshot(response):
    event, data, count = '', [], 0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        raw = response.readline(MAX_BYTES + 1)
        count += len(raw)
        if not raw or count > MAX_BYTES:
            break
        line = raw.decode('utf-8').rstrip('\r\n')
        if line.startswith('event:'):
            event = line[6:].strip()
        elif line.startswith('data:'):
            data.append(line[5:].lstrip())
        elif not line:
            if data and event == 'snapshot':
                return validate(json.loads('\n'.join(data)))
            event, data = '', []
    raise ValueError('No station snapshot received')


def fetch():
    request = Request(ENDPOINT, headers={'Accept': 'text/event-stream',
                                       'User-Agent': 'Kodi-LittLive/421.5'})
    with urlopen(request, timeout=6) as response:
        return read_snapshot(response)


def read_file(path):
    with open(path, encoding='utf-8') as stream:
        return validate(json.load(stream))


def load(cache_path, bundled_path, force=False, logger=None):
    cached = None
    try:
        cached = read_file(cache_path)
        if not force and 0 <= time.time() - os.path.getmtime(cache_path) < MAX_AGE:
            return cached, 'cache'
    except (OSError, ValueError, TypeError):
        pass
    try:
        stations = fetch()
    except Exception as error:
        if logger:
            logger('Catalog refresh failed: %s' % error)
        return (cached, 'stale cache') if cached else (read_file(bundled_path), 'bundled')
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        temporary = cache_path + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as stream:
            json.dump({'stations': stations}, stream, ensure_ascii=False)
        os.replace(temporary, cache_path)
    except OSError as error:
        if logger:
            logger('Catalog cache write failed: %s' % error)
    return stations, 'live'


def groups(stations):
    result = {}
    for station in stations:
        result.setdefault(station['station_genre'], []).append(station)
    for genre in result:
        result[genre].sort(key=lambda s: (-(s.get('genre_priority') or 0), s['station_name']))
    return sorted(result.items(), key=lambda pair: (-(pair[1][0].get('genre_order') or 0), pair[0]))
