"""Minimum-result, persistent availability checks for directory choices."""
import json
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from urllib.parse import parse_qsl, urlsplit

TTL = 86400
MAX_TRAKT_CHECKS = 8
CACHE_VERSION = 2
PRIORITY_NAMES = {
    "netflix", "amazon prime video", "prime video", "disney plus", "disney+",
    "hulu", "hbo max", "max", "apple tv", "apple tv+", "apple tv plus",
    "paramount plus", "paramount+", "peacock", "peacock premium", "apple tv plus",
    "abc", "cbs", "nbc", "fox", "hbo", "showtime",
}


def minimum_results(getter):
    try:
        return max(1, min(20, int(getter('catalog_min_category_results') or 10)))
    except (TypeError, ValueError):
        return 10


def probe_tmdb(api, kind, category, value, limits, adult, minimum=10):
    from resources.lib import tmdb_catalog as tm
    params = {f['type']: f['id'] for f in tm.filters(kind, category, value)}
    if category == 'studio': params['with_companies'] = value
    sort = 'primary_release_date.desc' if kind == 'movie' else 'first_air_date.desc'
    params.update(language='en-US', include_adult=adult, sort_by=sort)
    tm.discover_thresholds(params, limits)
    data = tm.query(api, 'discover/'+kind, dict(params, page=1), 0)
    rows = data.get('results')
    total = data.get('total_results')
    pages = data.get('total_pages')
    if not isinstance(rows, list) or not isinstance(total, int) or not isinstance(pages, int): return None
    if total < minimum: return False
    if not rows: return None
    # Count only distinct, qualifying titles on the actual opening page.
    # TMDb total_results does not account for locally applied popularity limits.
    seen = {item['id'] for item in rows if item.get('id') and tm.matches(item, limits)}
    return len(seen) >= minimum


def probe_trakt(api, kind, category, value, minimum=10):
    from resources.lib import trakt_catalog as cat
    ids = list(dict.fromkeys(cat.pool(kind, category, str(value), api=api, strict=True)))
    if len(ids) < minimum: return False
    first = cat.hydrate(kind, category, str(value), ids[:20], maximum=minimum, api=api, strict=True)
    return len({item['id'] for item in first if item.get('id')}) >= minimum


def filter_rows(kind, category, rows, source='tmdb'):
    if category not in ('provider','network','studio') or not rows: return rows
    import xbmcaddon, xbmcvfs, requests, xbmcgui, xbmc
    from resources.lib import tmdb_catalog as tm, TheMovieDB as db
    addon = xbmcaddon.Addon()
    if addon.getSetting('catalog_hide_empty') == 'false': return rows
    limits = tm.thresholds(kind, addon.getSetting)
    minimum = minimum_results(addon.getSetting)
    adult = 'true' if addon.getSetting('include_adults') == 'true' else 'false'
    def api(url, days=0):
        parts = urlsplit(url)
        response = requests.get('https://api.themoviedb.org/3/'+parts.path,
                                params=dict(parse_qsl(parts.query), api_key=db.API_key), timeout=(3,5))
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get('success') is False: raise ValueError('Invalid TMDb response')
        return result
    def check(job):
        value, key = job
        try:
            result = probe_tmdb(api, kind, category, str(value), limits, adult, minimum) if source == 'tmdb' else probe_trakt(api, kind, category, value, minimum)
            return key, result
        except Exception:
            return key, None
    try:
        folder = xbmcvfs.translatePath(addon.getAddonInfo('profile')); os.makedirs(folder, exist_ok=True)
        with closing(sqlite3.connect(os.path.join(folder,'catalog_availability.db'), timeout=3)) as conn, conn:
            conn.execute('CREATE TABLE IF NOT EXISTS availability (key TEXT PRIMARY KEY, expires REAL, available INTEGER)')
            now=time.time(); conn.execute('DELETE FROM availability WHERE expires <= ?', (now,))
            states={}; jobs=[]; keys=[]
            for value,label in rows:
                key=json.dumps([CACHE_VERSION,source,kind,category,str(value),limits,adult,minimum,date.today().isoformat()],sort_keys=True); keys.append(key)
                cached=conn.execute('SELECT available FROM availability WHERE key=?',(key,)).fetchone()
                if cached is not None: states[key]=cached[0]
                else: jobs.append((value,key))
            # Trakt intersections are substantially more expensive than a TMDb check.
            if source=='trakt':
                names={str(value):label.casefold() for value,label in rows}
                jobs.sort(key=lambda job: names.get(str(job[0]),'') not in PRIORITY_NAMES)
                jobs=jobs[:MAX_TRAKT_CHECKS]
            with ThreadPoolExecutor(max_workers=6 if source=='tmdb' else 2) as pool:
                for key,result in pool.map(check,jobs):
                    if result is not None:
                        states[key]=int(result)
                        conn.execute('INSERT OR REPLACE INTO availability VALUES (?,?,?)',(key,now+TTL,int(result)))
                    else:
                        # Brief retry delay; unknown entries are not displayed.
                        conn.execute('INSERT OR REPLACE INTO availability VALUES (?,?,?)',(key,now+300,2))
            visible = [row for row,key in zip(rows,keys) if states.get(key,2)==1]
            if any(states.get(key,2)==2 for key in keys):
                xbmcgui.Dialog().notification('Diggz Portal', 'Only verified categories shown. Reopen to check more.', xbmcgui.NOTIFICATION_INFO)
            return visible
    except Exception:
        xbmc.log("Diggz Portal: category availability check failed", xbmc.LOGWARNING)
        xbmcgui.Dialog().notification("Diggz Portal", "Category verification failed. Retry or disable filtering in settings.", xbmcgui.NOTIFICATION_WARNING)
        return []
