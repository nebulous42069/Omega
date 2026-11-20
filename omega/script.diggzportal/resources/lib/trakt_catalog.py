"""Independent Trakt charts and list browsing. No TMDb Helper sync imports."""
from datetime import date
import time
from urllib.parse import urlencode, quote
import random

PERIODS=[('daily','Today'),('weekly','This Week'),('monthly','This Month'),('yearly','This Year'),('all','All Time')]

_PUBLIC_CACHE={}

def authorized():
    import xbmcaddon
    addon=xbmcaddon.Addon()
    from resources.lib import trakt_api
    trakt_api.ensure_client()
    return bool(addon.getSetting('access_token') or addon.getSetting('refresh_token'))

def request(path, params=None, personal=False):
    from resources.lib import trakt_api
    import requests
    headers=dict(trakt_api.HEADERS)
    if personal:
        token=trakt_api.get_access_token()
        if not token: raise RuntimeError('Authorize Trakt in add-on settings first.')
        headers['Authorization']='Bearer '+token
    params=params or {}
    key=(path,urlencode(sorted(params.items())))
    if not personal:
        cached=_PUBLIC_CACHE.get(key)
        if cached and time.monotonic()-cached[0]<900: return cached[1]
    response=requests.get('https://api.trakt.tv/'+path,params=params,headers=headers,timeout=12)
    if response.status_code in (401,403,402):
        raise RuntimeError('Trakt denied access to this list. Check authorization or API access.')
    if response.status_code==429: raise RuntimeError('Trakt rate limit reached. Try again later.')
    response.raise_for_status()
    data=response.json()
    if not personal:
        if len(_PUBLIC_CACHE)>128: _PUBLIC_CACHE.clear()
        _PUBLIC_CACHE[key]=(time.monotonic(),data)
    return data

def watched_pages(kind):
    """Fetch complete watched history; Trakt caps progress pages at 100."""
    shows=kind=='tv'
    path='sync/watched/'+('shows' if shows else 'movies')
    params={'limit':100 if shows else 250}
    if shows: params['extended']='full,progress'
    rows=[]; seen=set()
    for page in range(1,1001):
        batch=request(path,dict(params,page=page),personal=True)
        if not isinstance(batch,list): raise RuntimeError('Invalid Trakt watched response')
        if not batch: return rows
        for row in batch:
            if not isinstance(row,dict): raise RuntimeError('Invalid Trakt watched item')
            item=row.get('show' if shows else 'movie') or {}
            ident=item.get('ids',{}).get('trakt')
            if ident is None or ident in seen: raise RuntimeError('Invalid or repeated Trakt watched item')
            if shows and not isinstance(row.get('seasons'),list): raise RuntimeError('Trakt season progress missing')
            seen.add(ident); rows.append(row)
    raise RuntimeError('Trakt watched history exceeds sync limit')

def entries(kind):
    noun='Movies' if kind=='movie' else 'TV Shows'
    rows=[('genre','Genres',True),('subgenre','Subgenres',True),('popular','Popular '+noun,False),('trending','Trending '+noun,False),('anticipated','Most Anticipated',False)]
    rows += [(x,'Most '+label,True) for x,label in [('watched','Watched'),('played','Played'),('favorited','Favorited')]]
    if kind=='movie': rows.append(('boxoffice','Box Office',False))
    rows += [('year','By Year',True),('decade','By Decade',True),('provider','By Provider (TMDb-assisted)',True),('studio' if kind=='movie' else 'network','By Studio (TMDb-assisted)' if kind=='movie' else 'By Network',True),('community','Community Lists',True),('random','Random Lists',True)]
    if authorized(): rows.append(('personal','My Trakt',True))
    return rows

STUDIOS=[(174,'Warner Bros.'),(33,'Universal Pictures'),(4,'Paramount'),(2,'Walt Disney Pictures'),(5,'Columbia Pictures'),(25,'20th Century Studios'),(1632,'Lionsgate'),(21,'MGM'),(41077,'A24'),(521,'DreamWorks Animation'),(3,'Pixar'),(12,'New Line Cinema')]

def choices(kind, category):
    from resources.lib import tmdb_catalog, TheMovieDB
    plural='movies' if kind=='movie' else 'shows'
    if category in ('watched','played','favorited'): return PERIODS
    if category in ('genre','subgenre'):
        rows=request('genres/'+plural,{'extended':'subgenres'} if category=='subgenre' else {})
        if category=='subgenre': rows=[j for i in rows for j in (i.get('subgenres') or [])]
        return sorted({i['slug']:i['name'] for i in rows if i.get('slug') and i.get('name')}.items(),key=lambda x:x[1].casefold())
    if category=='network':
        from resources.lib.catalog_availability import filter_rows
        rows=request('networks')
        options=sorted({str(i['id']):i['name'] for i in rows if i.get('id') and i.get('name')}.items(),key=lambda x:x[1].casefold())
        return filter_rows(kind,category,options,'trakt')
    if category in ('year','decade'):
        return tmdb_catalog.submenu_entries(TheMovieDB.get_tmdb_data,kind,category)
    if category in ('provider','studio'):
        from resources.lib.catalog_availability import filter_rows
        rows=STUDIOS if category=='studio' else tmdb_catalog.submenu_entries(TheMovieDB.get_tmdb_data,kind,category,check_availability=False)
        return filter_rows(kind,category,rows,'trakt')
    if category=='random': return [(i,l) for i,l in [('popular','Random Popular'),('trending','Random Trending'),('watched/weekly','Random Most Watched'),('played/weekly','Random Most Played'),('anticipated','Random Most Anticipated'),('genre','Random by Genre'),('decade','Random by Decade'),('community_popular','Random Popular Community List'),('community_trending','Random Trending Community List')]]
    if category=='community': return [('popular','Popular Community Lists'),('trending','Trending Community Lists'),('search','Search Public Lists')]
    if category=='personal':
        from resources.lib.personal_history import entries as history_entries
        return history_entries(kind)+[('watchlist','My Watchlist'),('custom','My Custom Lists'),('liked','My Liked Lists'),('random_watchlist','Random Watchlist'),('random_custom','Random Custom List'),('random_liked','Random Liked List'),('watched','My Watched Titles'),('collection','My Collection')] + ([('progress','My Shows Progress'),('unwatched','My Unwatched Shows')] if kind=='tv' else [])
    return []

def list_choices(source, text=''):
    personal=source in ('custom','liked')
    path={'custom':'users/me/lists','liked':'users/likes/lists','popular':'lists/popular','trending':'lists/trending','search':'search/list'}[source]
    rows=request(path,dict(limit=100,page=1,**({'query':text,'fields':'name'} if source=='search' else {})),personal)
    result=[]
    for entry in rows:
        item=entry.get('list',entry); ident=item.get('ids',{}).get('trakt'); user=item.get('user',{}).get('ids',{}).get('slug') or ('me' if source=='custom' else '')
        if ident:
            prefix='users/'+quote(str(user),safe='')+'/' if user else ''
            sort_by=item.get('sort_by'); sort_how=item.get('sort_how')
            sort_suffix='/'+sort_by+'/'+sort_how if sort_by in ('rank','added','title','released','runtime','popularity','percentage','votes','my_rating','random') and sort_how in ('asc','desc') else ''
            result.append((prefix+'lists/'+str(ident)+'/items'+sort_suffix,item.get('name','List')))
    return result

def choose(kind, category, value='', label='', expand=False):
    """Return a leaf specification; UI selection shared by root and sideblade."""
    import xbmcgui
    dlg=xbmcgui.Dialog()
    if category=='community':
        text=dlg.input('Search Trakt public lists').strip() if value=='search' else ''
        if value=='search' and not text: return None
        options=list_choices(value,text)
        if expand: return [('list',p,n) for p,n in options]
        idx=dlg.select(label,[n for p,n in options]) if options else -1
        return ('list',options[idx][0],options[idx][1]) if idx>=0 else None
    if category=='personal':
        if value.startswith('history_'): return (value,'',label)
        if value.endswith('watchlist'): return ('personal_random' if value.startswith('random') else 'personal_list','users/me/watchlist/'+('movies' if kind=='movie' else 'shows'),label)
        if value in ('watched','collection'): return ('personal_list','sync/'+value+'/'+('movies' if kind=='movie' else 'shows'),label)
        if value=='progress' and kind=='tv': return ('history_progress','',label)
        if value=='unwatched': return ('personal_legacy',value,label)
        options=list_choices(value.replace('random_',''))
        if expand and not value.startswith('random'): return [('personal_list',p,n) for p,n in options]
        idx=random.randrange(len(options)) if options and value.startswith('random') else dlg.select(label,[n for p,n in options]) if options else -1
        return ('personal_random' if value.startswith('random') else 'personal_list',options[idx][0],options[idx][1]) if idx>=0 else None
    if category=='random' and value in ('genre','decade'):
        options=choices(kind,value)
        if expand: return [('random_'+value,str(p),label+': '+n) for p,n in options]
        idx=dlg.select(label,[n for p,n in options]) if options else -1
        return ('random_'+value,str(options[idx][0]),label+': '+options[idx][1]) if idx>=0 else None
    if category=='random' and value.startswith('community_'):
        options=list_choices(value.split('_',1)[1]); return ('random_list',random.choice(options)[0],label) if options else None
    if category in ('watched','played','favorited'): label='Most '+category.title()+' - '+label
    return category,str(value),label

def pool(kind, category, value, force=False, api=None, strict=False):
    """Return a bounded, ordered ID snapshot. Hydrate only the visible page."""
    from resources.lib import tmdb_catalog as tm, TheMovieDB as db
    api = api or db.get_tmdb_data
    if force: _PUBLIC_CACHE.clear()
    plural='movies' if kind=='movie' else 'shows'; singular='movie' if kind=='movie' else 'show'
    randomize=category.startswith('random') or category=='personal_random'
    personal=category.startswith('personal'); direct=category in ('list','random_list','personal_list','personal_random','personal_legacy')
    filters={}; path=plural+'/popular'; limit=100
    if kind=='person': path='search/person'; singular='person'; filters={'query':value}
    elif category=='personal_legacy':
        from resources.lib import trakt
        func=trakt.trakt_watched_tv_shows_progress if value=='progress' else trakt.trakt_unwatched_tv_shows
        result=func() or []
        return list(dict.fromkeys(i.get('show',i).get('ids',{}).get('tmdb') for i in result if i.get('show',i).get('ids',{}).get('tmdb')))
    elif direct:
        path=value
        if '/items' in path:
            before,after=path.split('/items',1)
            path=before+'/items/'+singular+after
    elif category in ('genre','subgenre','random_genre'): filters['subgenres' if category=='subgenre' else 'genres']=value
    elif category in ('year','decade','random_decade'): filters['years']=value if category=='year' else value+'-'+str(int(value)+9)
    elif category=='network': filters['network_ids']=value
    elif category in ('provider','studio'): pass
    elif category=='random': path=plural+'/'+value
    elif category in ('watched','played','favorited'): path=plural+'/'+category+'/'+value
    else: path=plural+'/'+category
    anticipated=category=='anticipated' or (category=='random' and value=='anticipated')
    if kind!='person' and not direct and category!='boxoffice':
        filters.update(languages='en',countries='us')
        if not anticipated:
            limits=tm.thresholds(kind)
            if limits['votes']: filters['tmdb_votes']=str(limits['votes'])+'-1000000'
            if limits['rating']: filters['tmdb_ratings']=str(limits['rating'])+'-10'
            if limits['runtime']: filters['runtimes']=str(limits['runtime'])+'-1000'
    # For provider/studio discovery, intersect the Trakt ranking with a TMDb candidate set.
    # This is intentionally a bounded pool, not a claim of exhaustive Trakt availability.
    allowed=None
    if category in ('provider','studio'):
        opts={'language':'en-US','with_original_language':'en','with_origin_country':'US','sort_by':'popularity.desc','include_adult':'false'}
        if category=='provider': opts.update(with_watch_providers=value,watch_region='US',with_watch_monetization_types='flatrate')
        else: opts['with_companies']=value
        tm.discover_thresholds(opts,tm.thresholds(kind))
        allowed=set()
        for page in range(1,11):
            data=tm.query(api,'discover/'+kind,dict(opts,page=page),2)
            if strict and (not isinstance(data.get('results'),list) or not isinstance(data.get('total_pages'),int)): raise ValueError('Unknown TMDb availability')
            allowed.update(i.get('id') for i in data.get('results',[]))
            if page>=int(data.get('total_pages') or 0): break
        if not allowed: return []
    if path in ('sync/watched/movies','sync/watched/shows'):
        return list(dict.fromkeys(row[singular]['ids']['tmdb'] for row in watched_pages(kind) if row.get(singular,{}).get('ids',{}).get('tmdb')))
    rows=[]; seen=set()
    # Personal and public list items may include a mixture of media types.
    # Request typed lists at the endpoint when supported, but always validate wrappers.
    max_pages=10 if direct and not randomize else 3 if randomize or allowed is not None else 2
    for page in range(1,max_pages+1):
        result=request(path,dict(filters,page=page,limit=limit,extended='full') if category!='boxoffice' else {},personal)
        if not isinstance(result,list):
            if strict: raise ValueError('Unknown Trakt availability')
            break
        before=len(seen)
        for entry in result:
            if not isinstance(entry,dict): continue
            item=entry.get(singular,entry if 'ids' in entry and not direct else {})
            ident=(item or {}).get('ids',{}).get('tmdb')
            if not ident or ident in seen: continue
            seen.add(ident)
            if allowed is None or ident in allowed: rows.append(ident)
        if category=='boxoffice' or len(result)<limit or (len(seen)==before and not direct): break
    if randomize: random.shuffle(rows)
    return rows[:100] if randomize else rows


def hydrate(kind, category, value, ids, maximum=None, api=None, strict=False):
    """Convert ordered Trakt TMDb IDs to browser rows; don't filter personal lists."""
    from resources.lib import tmdb_catalog as tm, TheMovieDB as db
    import xbmcaddon
    api = api or db.get_tmdb_data
    personal=category.startswith('personal'); direct=category in ('list','random_list','personal_list','personal_random','personal_legacy')
    anticipated=category=='anticipated' or (category=='random' and value=='anticipated')
    limits=tm.thresholds(kind) if kind in ('movie','tv') else None
    output=[]
    for ident in ids:
        data=tm.query(api,kind+'/'+str(ident),{'language':'en-US'},7)
        if not data.get('id'):
            if strict: raise ValueError('Unknown title availability')
            continue
        if data.get('adult') and xbmcaddon.Addon().getSetting('include_adults')!='true': continue
        if kind!='person' and not personal and not direct and not anticipated:
            if not tm.matches(data,limits) or (limits['runtime'] and (data.get('runtime') or 0)<limits['runtime']): continue
            if data.get('original_language')!='en': continue
            countries=data.get('origin_country') or [c.get('iso_3166_1') for c in data.get('production_countries',[])]
            if 'US' not in countries: continue
        data=dict(data,genre_ids=[g['id'] for g in data.get('genres',[])],media_type=kind)
        output.append(data)
        if maximum and len(output)>=maximum: break
    return output
