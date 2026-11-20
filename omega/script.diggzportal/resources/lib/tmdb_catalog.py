"""TMDb menu definitions and bounded ranked-feed snapshots."""
from datetime import date, timedelta
from urllib.parse import urlencode

RANKED_PAGES = 5
NETWORKS = [(2,'ABC'),(6,'NBC'),(16,'CBS'),(19,'FOX'),(49,'HBO'),(67,'Showtime'),(213,'Netflix'),(453,'Hulu'),(1024,'Prime Video'),(2552,'Apple TV'),(2739,'Disney+')]
COMMON = [('all','All'),('popular','Popular'),('top_rated','Top Rated'),('trending/day','Trending Today'),('trending/week','Trending This Week')]

def menu(kind):
    noun = 'Movies' if kind == 'movie' else 'TV Shows'
    items = [(key, label+' '+noun) for key,label in COMMON]
    items += [('now_playing','In Theaters Movies'),('upcoming','Upcoming Movies'),('recent','Newly Released Movies')] if kind == 'movie' else [('on_the_air','Currently Airing TV Shows'),('airing_today','Airing Today TV Shows'),('recent','Newly Released TV Shows')]
    return items

def query(api, path, params, days):
    result = api(path+'?'+urlencode(params)+'&', days)
    return result if isinstance(result,dict) else {}

def filters(kind, category, value='', label='', today=None):
    today = today or date.today()
    datekey = 'primary_release_date' if kind == 'movie' else 'first_air_date'
    out = {'with_original_language':('en','Original language','English'), 'with_origin_country':('US','Origin country','USA')}
    if category != 'upcoming':
        out[datekey+'.lte'] = (today.isoformat(),'Released through', today.isoformat())
    if category == 'recent':
        start = (today-timedelta(days=90)).isoformat()
        out[datekey+'.gte'] = (start,'Released since',start)
    if category in ('year','decade'):
        start = int(value)
        end = start + (9 if category == 'decade' else 0)
        last = min(date(end,12,31),today).isoformat()
        out[datekey+'.gte'] = (str(start)+'-01-01','From year',str(start))
        out[datekey+'.lte'] = (last,'Through year',str(min(end,today.year)))
    if category == 'genre': out['with_genres'] = (value,'Genre',label)
    if category == 'provider':
        out['with_watch_providers'] = (value,'Streaming provider',label)
        out['watch_region'] = ('US','Watch region','USA')
        out['with_watch_monetization_types'] = ('flatrate','Availability','Subscription')
    if category == 'network': out['with_networks'] = (value,'Network',label)
    return [{'type':key,'id':str(v),'typelabel':t,'label':str(l)} for key,(v,t,l) in out.items()]

RANKED = {'popular','top_rated','trending/day','trending/week','now_playing','upcoming','on_the_air','airing_today','popular_genre','popular_decade'}

RANKED.update(('random_genre','random_decade','random_popular','random_trending'))

DEFAULTS = {'movie_votes':50, 'tv_votes':20, 'movie_popularity':5,
            'tv_popularity':3, 'movie_rating':0, 'tv_rating':0, 'movie_runtime':70}

def thresholds(kind, getter=None):
    if getter is None:
        import xbmcaddon
        getter = xbmcaddon.Addon().getSetting
    def read(key, maximum):
        try:
            raw = getter('catalog_'+key)
            value = float(raw) if raw != '' else DEFAULTS[key]
            if not 0 <= value <= maximum: raise ValueError()
            return value
        except (ValueError, TypeError, OverflowError):
            return DEFAULTS[key]
    return {'votes':int(read(kind+'_votes',1000000)),
            'popularity':read(kind+'_popularity',1000000),
            'rating':read(kind+'_rating',10),
            'runtime':int(read('movie_runtime',1000)) if kind=='movie' else 0}

def discover_thresholds(params, limits):
    for key, value in [('vote_count.gte',limits['votes']),('vote_average.gte',limits['rating']),('with_runtime.gte',limits['runtime'])]:
        if value:
            try: previous=float(params.get(key,0))
            except (ValueError,TypeError): previous=0
            params[key]=max(previous,value)
    return params

def matches(item, limits):
    return all(not limits[k] or float(item.get(field) or 0)>=limits[k]
               for k,field in [('votes','vote_count'),('popularity','popularity'),('rating','vote_average')])

def discover_page(api, url, limits, days):
    from urllib.parse import parse_qsl, urlsplit
    parts=urlsplit(url)
    params=dict(parse_qsl(parts.query))
    discover_thresholds(params,limits)
    data=query(api,parts.path,params,days)
    if 'results' in data:
        data=dict(data,results=[i for i in data['results'] if matches(i,limits)])
    return data

def ranked(api,kind,category,value='',force=False):
    """Select the first five ranked pages, then filter and sort the whole pool by date."""
    if category.startswith('random_'):
        import random
        source={'random_genre':'popular_genre','random_decade':'popular_decade','random_popular':'popular','random_trending':'trending/week'}[category]
        rows=ranked(api,kind,source,value,force)
        random.shuffle(rows)
        return rows[:20]
    limits = thresholds(kind) if category != 'upcoming' else dict(votes=0,popularity=0,rating=0,runtime=0)
    today = date.today().isoformat()
    days = 0 if force else 0.125
    params = {'language':'en-US'}
    if category in ('popular','top_rated','popular_genre','popular_decade'):
        path = 'discover/'+kind
        params.update(with_original_language='en',with_origin_country='US',include_adult='false',sort_by='vote_average.desc' if category=='top_rated' else 'popularity.desc')
        if category=='top_rated': params['vote_count.gte']=200
        for f in filters(kind,category.replace('popular_',''),value): params[f['type']]=f['id']
        discover_thresholds(params,limits)
        trusted_origin = True
    else:
        path = 'trending/'+kind+'/'+category.split('/')[1] if category.startswith('trending/') else kind+'/'+category
        if kind=='movie' and category in ('now_playing','upcoming'): params['region']='US'
        trusted_origin = False
    seen = set(); rows=[]
    key = 'release_date' if kind=='movie' else 'first_air_date'
    for page in range(1,RANKED_PAGES+1):
        data=query(api,path,dict(params,page=page),days)
        for item in data.get('results',[]):
            ident=item.get('id'); released=item.get(key) or ''
            if not ident or ident in seen or item.get('adult') or item.get('original_language')!='en' or not released: continue
            if category!='upcoming' and released>today: continue
            if category=='upcoming' and released<today: continue
            if not matches(item,limits): continue
            detail = None
            if not trusted_origin:
                countries=item.get('origin_country')
                if countries is None and kind=='movie':
                    detail=query(api,'movie/'+str(ident),{'language':'en-US'},14)
                    countries=detail.get('origin_country')
                    if countries is None: countries=[c.get('iso_3166_1') for c in detail.get('production_countries',[])]
                if 'US' not in (countries or []): continue
            if not trusted_origin and kind=='movie' and limits['runtime']:
                if detail is None: detail=query(api,'movie/'+str(ident),{'language':'en-US'},14)
                if (detail.get('runtime') or 0)<limits['runtime']: continue
            seen.add(ident); rows.append(item)
        if page>=int(data.get('total_pages') or 0): break
    return sorted(rows,key=lambda item:item.get(key) or '',reverse=True)


def search(api, kind, text, page=1, include_adult='false', force=False):
    """Search one media type, preserving TMDb relevance and pagination."""
    if kind not in ('movie', 'tv', 'person') or not text.strip():
        return {}
    return query(api, 'search/'+kind, {'query':text, 'page':page, 'language':'en-US', 'include_adult':'true' if include_adult == 'true' else 'false'}, 0 if force else 0.125)


def menu_entries(kind):
    """Common root and browser menu, in display order: category, label, folder."""
    noun = 'Movies' if kind == 'movie' else 'TV Shows'
    return [('genre',noun+' by Genre',True)] + [(k,l,False) for k,l in menu(kind)] + [(k,l,True) for k,l in [('popular_genre','Popular '+noun+' by Genre'),('year',noun+' by Year'),('decade',noun+' by Decade'),('provider',noun+' by Streaming Provider')]+([('popular_decade','Popular Movies by Decade')] if kind=='movie' else [('network','TV Shows by Network')])] + [('random_genre','Random '+noun+' by Genre',True),('random_decade','Random '+noun+' by Decade',True),('random_popular','Random Popular '+noun,False),('random_trending','Random Trending '+noun,False)]


# Exact normalized provider names: keep the main services and hide only
# the alternate storefronts, channels and subscription tiers requested.
def provider_name_key(name):
    import re
    return re.sub(r'[^a-z0-9]+', '', str(name).casefold().replace('+', ' plus '))


EXCLUDED_PROVIDERS = frozenset(provider_name_key(name) for name in (
    'Amazon Prime Video with ads', 'Amazon Video', 'Apple TV Amazon Channel',
    'Apple TV Store', 'Cinemax Apple TV Channel', 'HBO Max Amazon Channel',
    'MGM+ Amazon Channel', 'Netflix Standard with Ads',
    'Paramount Plus Essential', 'Paramount+ Amazon Channel',
    'Paramount Plus Amazon', 'Paramount Plus Roku',
    'Paramount+ Roku Premium Channel', 'Paramount Plus Roku Channel',
    'Peacock Premium Plus',
))


def submenu_entries(api, kind, category, check_availability=True):
    if category in ('genre','popular_genre','random_genre'):
        data=query(api,'genre/'+kind+'/list',{'language':'en-US'},30)
        return [(i['id'],i['name']) for i in sorted(data.get('genres',[]),key=lambda x:x['name'])]
    if category=='provider':
        data=query(api,'watch/providers/'+kind,{'language':'en-US','watch_region':'US'},7)
        rows = [(i['provider_id'],i['provider_name']) for i in sorted(data.get('results',[]),key=lambda x:x['provider_name'].casefold())
                if provider_name_key(i['provider_name']) not in EXCLUDED_PROVIDERS]
        if check_availability:
            from resources.lib.catalog_availability import filter_rows
            return filter_rows(kind,category,rows)
        return rows
    if category=='network':
        rows=sorted(NETWORKS,key=lambda x:x[1])
        if check_availability:
            from resources.lib.catalog_availability import filter_rows
            return filter_rows(kind,category,rows)
        return rows
    if category=='year': return [(y,str(y)) for y in range(date.today().year,1899,-1)]
    if category in ('decade','popular_decade','random_decade'): return [(y,str(y)+'s') for y in range(date.today().year//10*10,1899,-10)]
    return []
