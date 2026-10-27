# -*- coding: utf-8 -*-
"""Studio artwork for the focused video-browser item, isolated from Home widgets."""
import time
import urllib.parse
import xbmc
import xbmcgui
from x2_studio_logos import choose_logo, pack_logo

FIELDS = ('Label','Title','Studio','DBType','UniqueID(tmdb)','Property(tmdb_id)',
          'Property(tmdbshow_id)','IMDBNumber','UniqueID(imdb)','TVShowTitle','Year','FileNameAndPath','Director','Writer')


def snapshot():
    return {name: xbmc.getInfoLabel('ListItem.' + name).strip() for name in FIELDS}


def eligible():
    return xbmc.getCondVisibility('Window.IsActive(videos) + !Window.IsVisible(movieinformation) + !ListItem.IsParentFolder')


def identity(item):
    return tuple(item[name] for name in FIELDS)


def resolve(item, settings, fetch):
    studio = item['Studio']
    local = {'studio': studio}
    result = {'logo': '', 'director': item.get('Director', ''), 'writer': item.get('Writer', '')}
    # A local logo does not supply missing film credits.
    logo, _ = choose_logo(local)
    result['logo'] = logo
    if result['director'] and result['writer'] and logo.startswith('resource://resource.images.studios.coloured/'):
        return result
    credential, language, _ = settings()
    if not credential:
        return result
    dbtype = item['DBType'].lower()
    media = 'movie' if dbtype in ('movie', 'movies') else ('tv' if dbtype in ('tv','tvshow','season','episode') or item['TVShowTitle'] else 'movie')
    tmdb = item['Property(tmdbshow_id)'] if media == 'tv' else ''
    tmdb = tmdb or item['UniqueID(tmdb)'] or item['Property(tmdb_id)']
    # Episode IDs must not be mistaken for a parent series ID.
    if dbtype in ('episode','season') and not item['Property(tmdbshow_id)']:
        tmdb = ''
    imdb = item['IMDBNumber'] or item['UniqueID(imdb)']
    if not tmdb and imdb.startswith('tt'):
        results = fetch(credential, '/find/' + urllib.parse.quote(imdb, safe=''),
                        {'external_source':'imdb_id'}, timeout=5) or {}
        entries = results.get(media + '_results') or []
        if entries:
            tmdb = str(entries[0]['id'])
    if not tmdb:
        title = (item['TVShowTitle'] if media == 'tv' else '') or item['Title'] or item['Label']
        params = {'query':title, 'language':language}
        if item['Year'].isdigit() and len(item['Year']) == 4 and dbtype not in ('episode','season'):
            params['first_air_date_year' if media == 'tv' else 'year'] = item['Year']
        data = fetch(credential, '/search/' + media, params, timeout=5) or {}
        for entry in data.get('results') or []:
            names = [entry.get(k,'').casefold() for k in ('title','original_title','name','original_name')]
            if title.casefold() in names:
                tmdb = str(entry['id'])
                break
    if not tmdb:
        return result
    data = fetch(credential, '/%s/%s' % (media, urllib.parse.quote(tmdb, safe='')),
                 {'language':language, 'append_to_response':'credits'}, timeout=5) or {}
    crew = (data.get('credits') or {}).get('crew') or []
    if media == 'movie' and not crew:
        credits = fetch(credential, '/movie/%s/credits' % urllib.parse.quote(tmdb, safe=''), {}, timeout=5) or {}
        crew = credits.get('crew') or []
    def names(jobs):
        return ' / '.join(dict.fromkeys(c.get('name') for c in crew if c.get('name') and c.get('job') in jobs))
    result['director'] = result['director'] or names({'Director'})
    result['writer'] = result['writer'] or names({'Writer', 'Screenplay', 'Story', 'Teleplay'})
    xbmc.log('[X2 video credits] type=%s; director=%s; writer=%s' % (media, bool(result['director']), bool(result['writer'])), xbmc.LOGINFO)
    enriched = {'logo_studio':studio, 'studio':studio}
    for field, name_key, logo_key in [('production_companies','studio','studio_logo'),('networks','network','network_logo')]:
        for company in data.get(field) or []:
            if company.get('logo_path'):
                enriched[name_key] = company.get('name') or ''
                enriched[logo_key] = 'https://image.tmdb.org/t/p/w185' + company['logo_path']
                break
    # Preserve coloured pack priority over remotely supplied studio artwork.
    result['logo'] = logo if logo.startswith('resource://resource.images.studios.coloured/') else (choose_logo(enriched)[0] or logo)
    return result


def watch(stop, settings, fetch):
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(10000)
    pending = None
    shown = None
    since = 0
    cache = {}
    def clear():
        home.clearProperty('X2ViewStudio.Logo')
        home.clearProperty('X2ViewStudio.Label')
        home.clearProperty('X2ViewStudio.Director')
        home.clearProperty('X2ViewStudio.Writer')
    try:
        while not stop.is_set() and not monitor.abortRequested():
            if not eligible():
                if pending is not None:
                    clear()
                pending = shown = None
            else:
                item = snapshot()
                key = identity(item)
                now = time.monotonic()
                if key != pending:
                    pending, shown, since = key, None, now
                    clear()
                    # Immediate local match; metadata only runs after focus settles.
                    home.setProperty('X2ViewStudio.Label', item['Label'])
                    home.setProperty('X2ViewStudio.Logo', choose_logo({'studio':item['Studio']})[0])
                    home.setProperty('X2ViewStudio.Director', item.get('Director', ''))
                    home.setProperty('X2ViewStudio.Writer', item.get('Writer', ''))
                if now - since >= .35 and shown != key:
                    old = cache.get(key)
                    ttl = 1800 if old and old[1].get('director') and old[1].get('writer') else 30
                    details = old[1] if old and now-old[0] < ttl else resolve(item, settings, fetch)
                    cache[key] = (time.monotonic(), details)
                    if len(cache)>128:
                        del cache[min(cache, key=lambda k:cache[k][0])]
                    if not stop.is_set() and eligible() and identity(snapshot()) == key:
                        home.setProperty('X2ViewStudio.Label', item['Label'])
                        home.setProperty('X2ViewStudio.Logo', details['logo'])
                        home.setProperty('X2ViewStudio.Director', details['director'])
                        home.setProperty('X2ViewStudio.Writer', details['writer'])
                        shown = key
            if monitor.waitForAbort(.15):
                break
    except Exception as exc:
        xbmc.log('[X2 video studio] Lookup stopped: %s' % type(exc).__name__, xbmc.LOGWARNING)
    finally:
        clear()
