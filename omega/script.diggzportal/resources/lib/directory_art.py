"""Optional directory art. No impact on content routes or metadata filters."""
import random
import os
import sqlite3
import time
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date

IMAGE = 'https://image.tmdb.org/t/p/'
MAX_REFRESH = 12

def image(path, size):
    if isinstance(path, str) and path.startswith('/') and not path.endswith('.svg'):
        return IMAGE + size + path
    return ''

def normalized(name):
    return ''.join(c for c in str(name).casefold() if c.isalnum())

def specs(kind, category, rows, source, providers, genres, networks):
    category = category.replace('popular_', '').replace('random_', '')
    pmap = {str(x['provider_id']): x for x in providers if 'provider_id' in x}
    gmap = {normalized(x['name']): x['id'] for x in genres if 'name' in x and 'id' in x}
    nmap = {normalized(name): ident for ident, name in networks}
    aliases = {'sciencefiction':'scifi','scififantasy':'sciencefiction','actionadventure':'action','warpolitics':'war'}
    result=[]
    for value,label in rows:
        ident=str(value); logo=''; detail=''; params={}
        if category=='provider':
            logo=image(pmap.get(ident,{}).get('logo_path'),'w185')
            params={'with_watch_providers':ident,'watch_region':'US','with_watch_monetization_types':'flatrate'}
        elif category=='network':
            if source=='trakt': ident=str(nmap.get(normalized(label),''))
            if ident: detail='network/'+ident; params={'with_networks':ident}
        elif category=='studio':
            detail='company/'+ident; params={'with_companies':ident}
        elif category=='genre':
            if source=='trakt':
                name=normalized(label)
                ident=str(gmap.get(name) or next((v for k,v in gmap.items() if aliases.get(k)==name or aliases.get(name)==k),''))
            if ident: params={'with_genres':ident}
        elif category in ('year','decade'):
            try:
                start=int(ident); end=min(start+(9 if category=='decade' else 0),date.today().year)
                key='primary_release_date' if kind=='movie' else 'first_air_date'
                params={key+'.gte':str(start)+'-01-01',key+'.lte':str(end)+'-12-31'}
            except (ValueError,TypeError): pass
        result.append((logo,detail,params))
    return result

def artwork(kind, category, rows, source='tmdb'):
    """Return art dictionaries aligned with rows, using a bounded daily cache warmup."""
    from resources.lib import TheMovieDB, tmdb_catalog
    import xbmcaddon, xbmcvfs, requests
    category_base=category.replace('popular_', '').replace('random_', '')
    if category_base not in ('provider','network','studio','genre','year','decade'): return [{} for _ in rows]
    def metadata(path, params):
        try: return tmdb_catalog.query(TheMovieDB.get_tmdb_data,path,params,7).get('results' if 'providers' in path else 'genres',[])
        except Exception: return []
    providers=metadata('watch/providers/'+kind,{'language':'en-US','watch_region':'US'}) if category_base=='provider' else []
    genres=metadata('genre/'+kind+'/list',{'language':'en-US'}) if category_base=='genre' and source=='trakt' else []
    items=specs(kind,category,rows,source,providers,genres,tmdb_catalog.NETWORKS)
    output=[{'thumb':logo,'icon':logo,'poster':logo} if logo else {} for logo,_,_ in items]
    def fetch(path, params):
        response=requests.get('https://api.themoviedb.org/3/'+path,params=dict(params,api_key=TheMovieDB.API_key),timeout=(3,4))
        response.raise_for_status(); return response.json()
    def refresh(job):
        idx,key,detail,params=job; art={}
        try:
            if detail:
                logo=image(fetch(detail,{}).get('logo_path'),'w500')
                if logo: art.update(thumb=logo,icon=logo,poster=logo)
            if params:
                q=dict(params,language='en-US',with_original_language='en',with_origin_country='US',include_adult='false',sort_by='popularity.desc')
                choices=[image(x.get('backdrop_path'),'w1280') for x in fetch('discover/'+kind,q).get('results',[])]
                choices=[x for x in choices if x]
                if choices: art['fanart']=random.choice(choices)
            return idx,key,art,True
        except Exception: return idx,key,art,False
    try:
        folder=xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile')); os.makedirs(folder,exist_ok=True)
        with closing(sqlite3.connect(os.path.join(folder,'directory_art.db'),timeout=2)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS art (key TEXT PRIMARY KEY, expires REAL, data TEXT)')
            jobs=[]; now=time.time()
            for idx,(_,detail,params) in enumerate(items):
                if not detail and not params: continue
                key=json.dumps([kind,detail,params],sort_keys=True)
                cached=db.execute('SELECT expires,data FROM art WHERE key=?',(key,)).fetchone()
                if cached:
                    output[idx].update(json.loads(cached[1]))
                    if cached[0]>now: continue
                jobs.append((idx,key,detail,params))
            # Prioritize missing artwork over expired artwork, so long folders fill on later visits.
            jobs.sort(key=lambda x:bool(output[x[0]].get('fanart')))
            if jobs:
                with ThreadPoolExecutor(max_workers=6) as pool:
                    for idx,key,art,ok in pool.map(refresh,jobs[:MAX_REFRESH]):
                        output[idx].update(art)
                        if ok: db.execute('INSERT OR REPLACE INTO art VALUES (?,?,?)',(key,now+86400,json.dumps(art)))
    except Exception: pass
    if category_base=='genre':
        base='special://home/addons/script.diggzportal/resources/skins/Default/media/icons/genre/'
        for idx,(_,label) in enumerate(rows):
            name=normalized(label); icon=base+(name if name in GENRE_ICONS else 'genre')+'.png'
            output[idx].update(thumb=icon,icon=icon)
    return output

GENRE_ICONS = {'action','adventure','animation','comedy','crime','documentary','drama','family','fantasy','history','horror','music','mystery','romance','sciencefiction','tvmovie','thriller','war','western','actionadventure','kids','news','reality','scififantasy','soap','talk','warpolitics'}
