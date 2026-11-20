"""On-demand SIMKL discovery, calendar and PRO/VIP list browsing.

The CDN is preferred for large discovery lists. TMDb-only discovery categories
still enter Portal through the SIMKL history scope. No background fetches.
"""
import hashlib
import json
import random
import re
import time
from datetime import date, datetime, timedelta, timezone

import requests
from resources.lib import simkl_api as s

BASE = 'https://data.simkl.in/'
MEDIA = ('movies', 'tv', 'anime')
HIDDEN_GENRES = {'erotica', 'hentai', 'video-game-play'}


def row_list(data, operation, key=None):
    if isinstance(data, dict) and key:
        data = data.get(key, data.get("shows") if key=="tv" else data.get("dvd") if key=="movies" else None)
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise s.SimklError(operation, reason='Unexpected list response')
    return data


def cdn(path, ttl, validate):
    def load():
        try:
            r = requests.get(BASE + path, params=s.app_params(s.CLIENT_ID), headers={'User-Agent':s.UA}, timeout=15)
        except requests.RequestException as exc:
            raise s.SimklError(path, reason=type(exc).__name__) from None
        return validate(s.response_json(r, path))
    return s.cached('discovery:v1:'+path, ttl, load)


def group(media):
    return 'shows' if media == 'tv' else media


def checked_media(media):
    if media not in MEDIA:
        raise s.SimklError('Discovery', reason='Unknown media type')
    return media


def genre_choices(media):
    checked_media(media)
    path = 'discover/trending/'+media+'/genre/index.json'
    rows = cdn(path, 86400, lambda d: row_list(d, path))
    return [(r['slug'], r['name']) for r in rows if isinstance(r.get('slug'),str) and re.fullmatch(r'[a-z0-9-]+', r['slug']) and r['slug'] not in HIDDEN_GENRES and isinstance(r.get('name'),str)]


def genre_rows(media, slug):
    checked_media(media)
    if not re.fullmatch(r'[a-z0-9-]+',slug or '') or slug in HIDDEN_GENRES:
        raise s.SimklError('Genre',reason='Invalid genre')
    path = 'discover/trending/%s/genre/%s_month_500.json' % (media, slug)
    return cdn(path, 86400, lambda d: row_list(d,path,media))


def month_rows(media):
    checked_media(media)
    path = 'discover/trending/%s/month_500.json' % media
    return cdn(path,86400,lambda d: row_list(d,path,media))


def dvd_rows():
    path = 'discover/dvd/releases_100.json'
    return cdn(path,86400,lambda d: row_list(d,path,'movies'))


def parse_date(value):
    if not isinstance(value,str) or not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:
        try: d = datetime.strptime(value,'%m/%d/%Y')
        except ValueError: return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def calendar_data(media, month=None):
    checked_media(media)
    file = 'movie_release' if media=='movies' else media
    path='calendar/v2/'+(('%s/%s/'%month) if month else '')+file+'.json'
    def validate(d):
        if not isinstance(d,dict) or not isinstance(d.get('calendar'),list) or not isinstance(d.get('metadata'),dict):
            raise s.SimklError(path,reason='Unexpected calendar response')
        return d
    return cdn(path,21600,validate)


def calendar_rows(media, selection, now=None, allowed=None):
    now = now or datetime.now(timezone.utc)
    # Today is a local calendar date. Upcoming lists use the actual UTC air time.
    today = now.astimezone().date()
    if selection=='recent':
        start = (today-timedelta(days=30))
        # A 30-day window can touch three calendar months in February.
        months=sorted({( (start+timedelta(days=i)).year, (start+timedelta(days=i)).month ) for i in range(31)})
        feeds=[calendar_data(media,m) for m in months]
    else: feeds=[calendar_data(media)]
    candidates=[]
    for d in feeds:
        for event in d['calendar']:
            if not isinstance(event,dict): continue
            ident=str(event.get('simkl_id') or '')
            if not ident or (allowed is not None and ident not in allowed): continue
            row=d['metadata'].get(ident)
            dt=parse_date(event.get('date'))
            if not isinstance(row,dict) or not dt: continue
            local_day=dt.astimezone().date()
            ep=event.get('episode') or {}
            if not isinstance(ep,dict): continue
            # TV premieres are first-ever episodes, not season premieres.
            # Anime has one canonical season; anime films have no episode.
            is_premiere=media=='movies' or (media=='anime' and s.media_kind(row,'anime')=='movie') or (ep.get('episode')==1 and (ep.get('season')==1 if media=='tv' else ep.get('season',1)!=0))
            if selection=='recent':
                include=is_premiere and start<=local_day<=today and dt<=now
            elif selection=='today': include=local_day==today
            elif selection=='week': include=today<=local_day<=today+timedelta(days=6)
            elif selection=='premieres': include=is_premiere and dt>=now
            elif selection=='upcoming': include=dt>=now
            else: raise s.SimklError('Calendar',reason='Invalid calendar selection')
            if include: candidates.append((dt,ident,row))
    candidates.sort(key=lambda r:r[0],reverse=selection=='recent')
    seen=set(); result=[]
    for _,ident,row in candidates:
        if ident not in seen: result.append(row); seen.add(ident)
    return result


def private_cached(key,ttl,loader):
    if not s.configured(): raise s.SimklError('SIMKL',reason='Authorize SIMKL first')
    ident=s.identity()
    path=s.private_file().replace('.json','_discovery_'+hashlib.sha256(key.encode()).hexdigest()+'.json')
    old=s.read_file(path)
    if isinstance(old,dict) and 'data' in old and time.time()-float(old.get('time') or 0)<ttl:
        if ident!=s.identity(): raise s.SimklError('SIMKL',reason='Account changed')
        return old['data']
    data=loader()
    if ident!=s.identity(): raise s.SimklError('SIMKL',reason='Account changed')
    s.save_file(path,{'time':time.time(),'data':data})
    return data


def read_api(path,params=None):
    try: return s.request(path,params)
    except s.SimklError as exc:
        if exc.reason=='premium_only': raise s.SimklError('Custom Lists',reason='SIMKL PRO or VIP required') from None
        if exc.reason=='oauth2_token_required': raise s.SimklError('Custom Lists',reason='Authorize with SIMKL OAuth V2') from None
        raise


def search(media,text):
    checked_media(media)
    text=str(text or '').strip()
    if not text: raise s.SimklError('Search',reason='Enter a title')
    path='search/'+('movie' if media=='movies' else media)
    # One search page, up to 50 matches. Explicit search only.
    return private_cached('search:'+media+':'+text,900,lambda:row_list(read_api(path,{'q':text,'limit':50,'page':1}),path))


def number(value):
    try: return float(value or 0)
    except (TypeError,ValueError): return 0


def top_rated(rows):
    def rating(r):
        ratings=(r.get('ratings') or {}).get('simkl') or {}
        return number(ratings.get('rating')),number(ratings.get('votes'))
    return sorted((r for r in rows if rating(r)[1]>=50 and rating(r)[0]>0),key=rating,reverse=True)


def personal_rows(media, selection):
    if selection=='rated':
        g=group(media); path='sync/ratings/'+g+'/1,2,3,4,5,6,7,8,9,10'
        def load():
            data=read_api(path)
            if not isinstance(data,dict): raise s.SimklError(path,reason='Unexpected ratings response')
            return row_list(data.get(g,[]),path)
        rows=private_cached('ratings:'+g,900,load)
        return sorted((r for r in rows if number(r.get('user_rating'))>0),key=lambda r:(number(r.get('user_rating')),r.get('user_rated_at') or ''),reverse=True)
    rows=s.group_rows(group(media))
    if selection=='remaining':
        def remaining(r):
            return number(r.get('total_episodes_count'))-number(r.get('not_aired_episodes_count'))-number(r.get('watched_episodes_count'))
        return sorted((r for r in rows if r.get('status')=='watching' and remaining(r)>0),key=lambda r:r.get('last_watched_at') or '',reverse=True)
    if selection=='calendar':
        allowed={s.row_id(r) for r in rows if r.get('status') in ('watching','plantowatch')}
        return calendar_rows(media,'upcoming',allowed=allowed) if allowed else []
    raise s.SimklError('Personal discovery',reason='Unknown selection')


def account_info():
    # Only cache the two fields needed; never persist full user profile.
    def load():
        data=read_api('users/settings')
        account=data.get('account') if isinstance(data,dict) else None
        if not isinstance(account,dict) or not s.positive(account.get('id')):
            raise s.SimklError('Custom Lists',reason='Account ID unavailable')
        return {'id':int(account['id']),'type':str(account.get('type') or '').lower()}
    # The settings timestamp gates refresh; otherwise expire after a day.
    try: stamp=json.dumps(s.activities().get('settings',{}),sort_keys=True)
    except Exception: stamp=''
    return private_cached('profile:'+stamp,86400,load)


def require_premium():
    profile=account_info()
    if profile['type'] not in ('pro','vip'):
        raise s.SimklError('Custom Lists',reason='SIMKL PRO or VIP required')
    return profile


def paginated(path,key,params=None):
    rows=[]; info={}
    for page in range(1,21):
        d=read_api(path,dict(params or {},page=page,limit=500))
        if not isinstance(d,dict) or not isinstance(d.get('pagination'),dict):
            raise s.SimklError(path,reason='Unexpected paginated response')
        batch=row_list(d,path,key); rows.extend(batch); info=d
        pages=s.positive(d['pagination'].get('total_pages')) or 1
        if not batch or page>=pages: break
    return rows,info


def custom_choices(media, selection, user_id=None):
    checked_media(media)
    profile=require_premium()
    uid=s.positive(user_id) if selection=='user' else profile['id']
    if not uid: raise s.SimklError('Custom Lists',reason='Invalid user ID')
    params={'followed':'true','collaborants':'true'} if uid==profile['id'] else {}
    path='lists/user/'+str(uid)
    def load(): return paginated(path,'lists',params)[0]
    rows=private_cached('list-index:'+str(uid),900,load)
    out=[]
    for row in rows:
        if row.get('media_type')!=media or not s.positive(row.get('id')): continue
        role=row.get('role'); typ=row.get('type')
        if selection=='own' and (role!='owner' or typ=='favorite'): continue
        if selection=='followed' and role!='follower': continue
        if selection=='shared' and role!='collaborator': continue
        if selection=='favorites' and (typ!='favorite' or role!='owner'): continue
        count=(row.get('counts') or {}).get('items')
        label=str(row.get('name') or 'SIMKL list')+(' (%s)'%count if isinstance(count,int) else '')
        out.append((str(row['id']),label))
    return out


def custom_rows(media,ident):
    require_premium(); ident=s.positive(ident)
    if not ident: raise s.SimklError('Custom Lists',reason='Invalid list ID')
    path='lists/'+str(ident)
    def load():
        rows,info=paginated(path,'items')
        return {'media_type':info.get('media_type'),'items':rows}
    data=private_cached('list-items:'+str(ident),900,load)
    if data.get('media_type')!=media: raise s.SimklError('Custom Lists',reason='List belongs to another media category')
    return data['items']


def tmdb_choices(kind,selection):
    from resources.lib import tmdb_catalog as tm, TheMovieDB as db
    return tm.submenu_entries(db.get_tmdb_data,kind,selection,check_availability=False)


def tmdb_ids(kind,selection,value):
    from resources.lib import tmdb_catalog as tm, TheMovieDB as db
    if kind not in ('movie','tv') or selection not in ('provider','network','year','decade'): raise s.SimklError('TMDB discovery',reason='Invalid category')
    ident=s.positive(value)
    if not ident: raise s.SimklError('TMDB discovery',reason='Invalid filter')
    opts={'language':'en-US','include_adult':'false','sort_by':'popularity.desc'}
    if selection=='provider': opts.update(with_watch_providers=ident,watch_region='US',with_watch_monetization_types='flatrate')
    elif selection=='network' and kind=='tv': opts['with_networks']=ident
    elif selection in ('year','decade'):
        if not 1800<=ident<=date.today().year: raise s.SimklError('TMDB discovery',reason='Invalid year')
        field='primary_release_date' if kind=='movie' else 'first_air_date'
        opts[field+'.gte']='%04d-01-01'%ident; opts[field+'.lte']='%04d-12-31'%(ident+(9 if selection=='decade' else 0))
    else: raise s.SimklError('TMDB discovery',reason='Invalid filter')
    ids=[]
    # Bound discovery to five pages (100 titles). TMDb's existing cache handles each page.
    for page in range(1,6):
        data=tm.query(db.get_tmdb_data,'discover/'+kind,dict(opts,page=page),1)
        if not isinstance(data.get('results'),list): raise s.SimklError('TMDB discovery',reason='Unable to retrieve results')
        ids.extend(s.positive(r.get('id')) for r in data['results'] if isinstance(r,dict))
        if page>=int(data.get('total_pages') or 0): break
    return list(dict.fromkeys(i for i in ids if i))


def rows_for(group_name,selection,value):
    """Return (rows, native media group) or None for an unrelated legacy route."""
    if group_name.startswith('public_'):
        media=group_name[7:]
        if selection=='genre': rows=genre_rows(media,value)
        elif selection=='dvd' and media=='movies': rows=dvd_rows()
        elif selection in ('today_calendar','week_calendar','upcoming','premieres','recent'):
            rows=calendar_rows(media,{'today_calendar':'today','week_calendar':'week'}.get(selection,selection))
        elif selection=='top_rated': rows=top_rated(month_rows(media))
        elif selection=='search': rows=search(media,value)
        elif selection in ('random','unwatched'):
            rows=list(month_rows(media))
            if selection=='unwatched':
                watched={s.row_id(r) for r in s.group_rows(group(media)) if r.get('status') in ('completed','watching') or r.get('last_watched_at')}
                rows=[r for r in rows if s.row_id(r) not in watched]
            random.shuffle(rows)
        else: return None
        return rows,group(media)
    if group_name.startswith('personal_'):
        media=group_name[9:]; return personal_rows(media,selection),group(media)
    if group_name.startswith('custom_') and selection=='items':
        media=group_name[7:]; return custom_rows(media,value),group(media)
    return None


def history_refs(kind,category):
    if category=='history_simkl_next_tv':
        refs=[]
        rows=sorted(s.group_rows('shows'),key=lambda r:r.get('last_watched_at') or '',reverse=True)
        for row in rows:
            if row.get('status')!='watching': continue
            match=re.fullmatch(r'S(\d+)E(\d+)',str(row.get('next_to_watch') or ''),re.I)
            if not match: continue
            season,episode=map(int,match.groups())
            if min(season,episode)<=0: continue
            if number(row.get('total_episodes_count'))-number(row.get('not_aired_episodes_count'))<=number(row.get('watched_episodes_count')): continue
            try: mid=s.tmdb_id(row,'tv')
            except Exception as exc:
                s.log_failure('Next Up mapping',exc); continue
            if mid: refs.append([mid,season,episode,0])
        return refs
    media=category[len('history_simkl_resume_'):] if category.startswith('history_simkl_resume_') else ''
    checked_media(media)
    path='sync/playback'
    rows=private_cached('playback',300,lambda:row_list(read_api(path,{'limit':500}),path))
    refs=[]; seen=set()
    for row in sorted(rows,key=lambda r:r.get('paused_at') or '',reverse=True):
        key='anime' if media=='anime' else 'movie' if media=='movies' else 'show'
        if not isinstance(row.get(key),dict): continue
        if row.get('type')!=('movie' if kind=='movie' else 'episode'): continue
        try: mid=s.tmdb_id(row,kind)
        except Exception as exc:
            s.log_failure('Playback mapping',exc); continue
        progress=number(row.get('progress'))
        if not mid or not 0<progress<100: continue
        season=episode=0
        if kind=='tv':
            ep=row.get('episode') or {}
            # Anime canonical numbering is not show numbering. Only use explicit TVDB mapping.
            season=s.positive(ep.get('tvdb_season' if media=='anime' else 'season'))
            episode=s.positive(ep.get('tvdb_number' if media=='anime' else 'number'))
            if not season or not episode: continue
        key=(mid,season,episode)
        if key not in seen: refs.append([mid,season,episode,max(1,int(progress))]); seen.add(key)
    return refs
