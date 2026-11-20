"""SIMKL V2 device grant, cached public/personal feeds and TMDb identity bridge."""
import hashlib, json, os, tempfile, time, uuid, threading, traceback
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote_plus
import requests
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

CLIENT_ID = '00ce4b288e913a45e9d6df007acf523ba21f1fa806142322649be1746060548a'
API = 'https://api.simkl.com/'
DATA = 'https://data.simkl.in/discover/trending/'
VERSION = '10.24.53'
UA = 'DiggzPortal/'+VERSION
MANAGER = 'script.module.authorizediggz'
_LOCK = threading.RLock()
STATUSES = [('plantowatch','Plan to Watch'),('watching','Watching'),('completed','Completed'),('hold','On Hold'),('dropped','Dropped')]

def addon(): return xbmcaddon.Addon('script.diggzportal')
def parse(raw):
    try:
        b=json.loads(raw or '{}')
        if not isinstance(b,dict) or not b.get('access_token') or not b.get('client_id'): return {}
        return b
    except (ValueError,TypeError): return {}

def grant():
    a=addon()
    if a.getSetting('simkl_managed')=='true':
        # Account Manager is the sole renewer of a centrally owned session.
        # Do not use the mirrored token after central sign-out or account change.
        try:
            m=xbmcaddon.Addon(MANAGER); b=parse(m.getSetting('simkl.authorization'))
            token=m.getSetting('simkl.token')
            if b and b['access_token']==token: return b
            if token: return dict(access_token=token,client_id=m.getSetting('simkl.client.id') or CLIENT_ID,session_id=hashlib.sha256(token.encode()).hexdigest())
        except Exception: pass
        return {}
    return parse(a.getSetting('simkl_authorization'))

def manager_available():
    try: return bool(xbmc.getCondVisibility('System.HasAddon('+MANAGER+')') and xbmc.getCondVisibility('System.AddonIsEnabled('+MANAGER+')'))
    except Exception: return False

def configured(): return bool(grant())
def identity():
    b=grant(); return b.get('session_id') or hashlib.sha256(b.get('access_token','').encode()).hexdigest()

def make_bundle(data,previous=None):
    p=previous or {}; scope=data.get('scope') or p.get('scope') or ''
    refresh=data.get('refresh_token') or p.get('refresh_token')
    if not data.get('access_token') or not refresh or not {'media:read','media:write'}.issubset(scope.split()) or int(data.get('expires_in') or 0)<=0: raise RuntimeError('Incomplete SIMKL grant')
    return dict(client_id=p.get('client_id') or CLIENT_ID,session_id=p.get('session_id') or uuid.uuid4().hex,access_token=data['access_token'],refresh_token=refresh,expires_at=time.time()+int(data['expires_in']),scope=scope)

def token_request(data): return requests.post(API+'oauth2/token',data=data,headers={'User-Agent':UA},timeout=15)
def token(rejected=None):
    with _LOCK: return _token(rejected)

def _token(rejected=None):
    b=grant()
    if not b: raise SimklError('Authorization',reason='Authorize SIMKL first')
    due=float(b.get('expires_at') or 0) and float(b['expires_at'])<=time.time()+300
    if not due and rejected!=b['access_token']: return b
    if addon().getSetting('simkl_managed')=='true':
        # Central startup/service renews and backs up the grant. A later request
        # reads it directly; never rotate its refresh token from two add-ons.
        if rejected==b['access_token'] or (b.get('expires_at') and float(b['expires_at'])<=time.time()): raise SimklError('Authorization',reason='Renew SIMKL in Account Manager')
        return b
    r=token_request({'client_id':b['client_id'],'grant_type':'refresh_token','refresh_token':b.get('refresh_token','')})
    if not r.ok: raise SimklError('Token renewal',r.status_code)
    renewed=make_bundle(r.json(),b)
    if grant()!=b: return grant()
    addon().setSetting('simkl_authorization',json.dumps(renewed)); return renewed

def login():
    dlg=xbmcgui.Dialog()
    # Standalone remains available even when Account Manager is installed.
    try:
        r=requests.post(API+'oauth2/device',data={'client_id':CLIENT_ID,'scope':'media:read media:write'},headers={'User-Agent':UA},timeout=15)
        if not r.ok: raise RuntimeError('PIN request failed')
        d=r.json(); interval=max(1,int(d.get('interval') or 5)); end=time.time()+int(d.get('expires_in') or 900)
        progress=xbmcgui.DialogProgress(); progress.create('SIMKL','Open %s and enter %s'%(d['verification_uri'],d['user_code']))
        try:
            monitor=xbmc.Monitor(); start=time.time()
            while time.time()<end and not progress.iscanceled():
                if monitor.waitForAbort(interval) or progress.iscanceled(): return False
                r=token_request({'client_id':CLIENT_ID,'grant_type':'urn:ietf:params:oauth:grant-type:device_code','device_code':d['device_code']})
                data=r.json()
                if r.ok and data.get('access_token'):
                    b=make_bundle(data); a=addon(); clear_private(); a.setSetting('simkl_authorization',json.dumps(b)); a.setSetting('simkl_managed','false'); a.setSetting('simkl_manager_grant',''); a.setSetting('simkl_optout','true'); return True
                if data.get('error')=='slow_down' or r.status_code==429: interval+=5
                elif data.get('error')!='authorization_pending': raise RuntimeError('Authorization rejected')
                progress.update(min(99,int(100*(time.time()-start)/max(1,end-start))))
        finally: progress.close()
    except Exception: dlg.notification('SIMKL','Authorization failed. Check connection and retry.',xbmcgui.NOTIFICATION_ERROR)
    return False

def logout():
    clear_private(); a=addon(); a.setSetting('simkl_managed','false'); a.setSetting('simkl_authorization',''); a.setSetting('simkl_manager_grant',''); a.setSetting('simkl_optout','true')

def folder():
    p=xbmcvfs.translatePath(addon().getAddonInfo('profile')); os.makedirs(p,exist_ok=True); return p

def cached(key,ttl,loader):
    path=os.path.join(folder(),'simkl_'+hashlib.sha256(key.encode()).hexdigest()+'.json')
    try:
        with open(path,encoding='utf8') as f: old=json.load(f)
        if time.time()-old['time']<ttl: return old['data']
    except (OSError,ValueError,KeyError,TypeError): pass
    data=loader()
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',dir=folder(),delete=False) as f:
            json.dump({'time':time.time(),'data':data},f); tmp=f.name
        os.replace(tmp,path)
    except OSError: pass
    return data

def private_file():
    return os.path.join(folder(),'simkl_private_'+hashlib.sha256(identity().encode()).hexdigest()+'.json')

def read_file(path):
    try:
        with open(path,encoding='utf8') as f: return json.load(f)
    except (OSError,ValueError): return {}

def save_file(path,data):
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',dir=folder(),delete=False) as f:
            json.dump(data,f); tmp=f.name
        os.replace(tmp,path)
    except OSError: pass

def clear_private():
    # Changing users or disconnecting should remove private snapshots, not public feeds.
    _ACTIVITY_CACHE.clear(); _ACTIVITY_FAILURES.clear(); _GROUP_FAILURES.clear()
    for name in os.listdir(folder()):
        if name.startswith('simkl_private_') or name=='history_simkl.json':
            try: os.remove(os.path.join(folder(),name))
            except OSError: pass

def invalidate():
    # Preserve the previous snapshot and its delta cursor after writes, but bypass TTL.
    _ACTIVITY_CACHE.clear(); _ACTIVITY_FAILURES.clear(); _GROUP_FAILURES.clear()
    for group in GROUPS:
        path=private_file().replace('.json','_v2_'+group+'.json'); old=read_file(path)
        if old:
            old['time']=0; old['dirty']=True; save_file(path,old)
    try:
        from resources.lib import accounts
        accounts._MEMORY.pop(('simkl',accounts.identity('simkl')),None)
    except Exception: pass

class SimklError(RuntimeError):
    """Safe diagnostic; never includes request URL, headers, or raw body."""
    def __init__(self, operation, status=None, reason=''):
        self.status=status; self.reason=reason
        super().__init__('%s%s%s' % (operation, ' HTTP '+str(status) if status is not None else '', ' ('+reason+')' if reason else ''))


def log_failure(stage, exc):
    frames=traceback.extract_tb(exc.__traceback__)
    location=' > '.join('%s:%s:%s'%(os.path.basename(fr.filename),fr.lineno,fr.name) for fr in frames[-5:])
    detail=str(exc) if isinstance(exc,SimklError) else type(exc).__name__
    xbmc.log('Diggz Portal SIMKL: %s: %s [%s]'%(stage,detail,location),xbmc.LOGWARNING)


def app_params(client_id, params=None):
    return dict(params or {},client_id=client_id,**{'app-name':'diggz-portal','app-version':VERSION})


_ERROR_CODES={'insufficient_scope','oauth2_token_required','invalid_token','user_token_failed','user_token_required','client_id_failed','forbidden','premium_only','max_items','invalid_request','wrong_parameter','rate_limit','user_limit_exceeded','app_limit_exceeded','method_not_allowed'}


def response_json(r, operation):
    if not r.ok:
        reason=''
        try:
            parsed=r.json(); error=parsed.get('error') if isinstance(parsed,dict) else None
            if isinstance(error,str) and error in _ERROR_CODES: reason=error
        except (ValueError,TypeError): pass
        if not reason: reason='non-JSON or unrecognized error' 
        exc=SimklError(operation,r.status_code,reason)
        xbmc.log('Diggz Portal SIMKL: '+str(exc),xbmc.LOGWARNING)
        raise exc
    try: return r.json() if r.content else {}
    except ValueError: raise SimklError(operation,r.status_code,'invalid JSON')


def request(path,params=None,body=None):
    path=path.strip('/')
    b=token()
    for attempt in range(2):
        headers={'User-Agent':UA,'simkl-api-key':b['client_id'],'Authorization':'Bearer '+b['access_token']}
        kwargs={'params':app_params(b['client_id'],params),'headers':headers,'timeout':20}
        if body is not None:
            headers['Content-Type']='application/json'; kwargs['json']=body
        method='POST' if body is not None else 'GET'
        try: r=requests.request(method,API+path,**kwargs)
        except requests.RequestException as exc: raise SimklError(path,reason=type(exc).__name__) from None
        if r.status_code!=401 or attempt: break
        b=token(rejected=b['access_token'])
    data=response_json(r,path)
    if isinstance(data,dict):
        not_found=data.get('not_found') or {}
        if data.get('error') in ('premium_only','oauth2_token_required'):
            raise SimklError(path,reason=data['error'])
        if data.get('error') or data.get('errors') or (body is not None and (any(not_found.values()) if isinstance(not_found,dict) else bool(not_found))): raise SimklError(path,reason='SIMKL rejected action')
    if body is not None: invalidate()
    return data

GROUPS=('movies','shows','anime')

def normalized(data):
    if data is None: data={}
    if not isinstance(data,dict) or any(not isinstance(data.get(k,[]),list) for k in GROUPS): raise RuntimeError('Invalid SIMKL watchlist')
    return {k:data.get(k,[]) for k in GROUPS}

def row_id(row):
    ids=item(row).get('ids') or {}
    return str(ids.get('simkl') or ids.get('simkl_id') or '')

def activity_cursor(value):
    if isinstance(value,(int,float)) and value>0:
        value=datetime.fromtimestamp(value/1000 if value>1e11 else value,timezone.utc).isoformat()
    if not isinstance(value,str): return ''
    try:
        # One-second overlap avoids losing changes with the same server timestamp.
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))-timedelta(seconds=1)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except ValueError: return ''

_ACTIVITY_CACHE={}
_ACTIVITY_FAILURES={}
_GROUP_FAILURES={}


def activities(force=False):
    ident=identity(); old=_ACTIVITY_CACHE.get(ident)
    if not force and old and time.time()-old[0]<60: return old[1]
    fail=_ACTIVITY_FAILURES.get(ident)
    if not force and fail and time.time()-fail[0]<30: raise fail[1]
    try:
        data=request('sync/activities')
        if not isinstance(data,dict) or not isinstance(data.get('all'),str): raise SimklError('sync/activities',reason='invalid activity response')
    except Exception as exc:
        _ACTIVITY_FAILURES.clear(); _ACTIVITY_FAILURES[ident]=(time.time(),exc if isinstance(exc,SimklError) else SimklError('sync/activities',reason=type(exc).__name__))
        raise
    _ACTIVITY_FAILURES.clear(); _ACTIVITY_CACHE.clear(); _ACTIVITY_CACHE[ident]=(time.time(),data)
    return data


def group_rows(group,force=False,activity=None):
    if group not in GROUPS: raise ValueError('Invalid group')
    if not configured(): raise SimklError('Personal list',reason='Authorize SIMKL first')
    with _LOCK:
        ident=identity(); path=private_file().replace('.json','_v2_'+group+'.json'); old=read_file(path)
        if not force and time.time()-old.get('time',0)<900 and 'rows' in old: return old['rows']
        # Avoid repeated failed history fetches during list rendering.
        failure=_GROUP_FAILURES.get((ident,group))
        if not force and failure and time.time()-failure[0]<30: raise failure[1]
        try:
            activity=activity if activity is not None else activities(force)
            activity_group='tv_shows' if group=='shows' else group
            previous=old.get('activity',{}); prev_group=previous.get(activity_group,{}); now_group=activity.get(activity_group,{})
            cursor=previous.get('all')
            params={'extended':'full_anime_seasons' if group=='anime' else 'full'}
            if group!='movies': params['include_all_episodes']='yes'
            endpoint='sync/all-items/'+group
            def fetch(p):
                data=request(endpoint,p)
                if not isinstance(data,dict) or (data and group not in data): raise SimklError(endpoint,reason='invalid list response')
                rows=data.get(group,[])
                if not isinstance(rows,list) or any(not isinstance(row,dict) or not row_id(row) for row in rows): raise SimklError(endpoint,reason='invalid list entries')
                return rows
            if 'rows' not in old or not cursor:
                rows=fetch(params)
            elif not old.get('dirty') and (activity==previous or (prev_group and now_group==prev_group)):
                rows=old['rows']
            else:
                changed=fetch(dict(params,date_from=cursor)); by_id={row_id(r):r for r in old['rows']}
                by_id.update((row_id(r),r) for r in changed)
                if old.get('dirty') or not prev_group or not now_group or prev_group.get('removed_from_list')!=now_group.get('removed_from_list'):
                    membership=[row_id(r) for r in fetch({'extended':'simkl_ids_only'})]
                    rows=[by_id[i] for i in membership] if all(i in by_id for i in membership) else fetch(params)
                else: rows=list(by_id.values())
            if ident!=identity(): raise SimklError(endpoint,reason='account changed during sync')
            save_file(path,{'time':time.time(),'activity':activity,'rows':rows})
            _GROUP_FAILURES.pop((ident,group),None)
            return rows
        except Exception as exc:
            log_failure('personal '+group,exc)
            _GROUP_FAILURES[(ident,group)]=(time.time(),exc if isinstance(exc,SimklError) else SimklError('Personal '+group,reason=type(exc).__name__))
            raise


def all_items(force=False):
    if not configured(): raise SimklError('Personal list',reason='Authorize SIMKL first')
    with _LOCK:
        # A successfully cached group is reusable independently of the others.
        activity=activities(force) if force else None
        return {group:group_rows(group,force,activity) for group in GROUPS}

def trending(media,period):
    if media not in ('movies','tv','anime') or period not in ('today','week','month'): raise ValueError('Invalid SIMKL feed')
    def load():
        operation='trending/'+media+'/'+period
        try: r=requests.get(DATA+media+'/'+period+'_100.json',params=app_params(CLIENT_ID),headers={'User-Agent':UA},timeout=15)
        except requests.RequestException as exc: raise SimklError(operation,reason=type(exc).__name__) from None
        data=response_json(r,operation)
        if isinstance(data,dict): data=data.get(media,data.get('shows' if media=='tv' else media))
        if not isinstance(data,list) or any(not isinstance(row,dict) for row in data): raise SimklError(operation,reason='invalid feed shape')
        return data
    return cached('public:v2:'+media+':'+period,3600 if period=='today' else 86400,load)

def media_kind(row,group):
    if group=='movies': return 'movie'
    if group=='anime' and str(row.get('anime_type') or item(row).get('anime_type') or row.get('type') or '').lower() in ('movie','movies'): return 'movie'
    return 'tv'

def item(row): return row.get('movie') or row.get('show') or row.get('anime') or row

def positive(value):
    try: return int(value) if int(value)>0 else None
    except (ValueError,TypeError): return None

def tmdb_id(row,kind):
    from resources.lib import tmdb_catalog as tm, TheMovieDB as db
    ids=item(row).get('ids') or {}; direct=positive(ids.get('tmdb'))
    if direct: return direct
    for field,source in (('imdb','imdb_id'),('tvdb','tvdb_id')):
        ident=ids.get(field)
        if not ident or (field=='tvdb' and kind=='movie'): continue
        data=tm.query(db.get_tmdb_data,'find/'+str(ident),{'external_source':source,'language':'en-US'},30)
        results=data.get('movie_results' if kind=='movie' else 'tv_results',[])
        if len(results)==1: return positive(results[0].get('id'))
    return None

def pool(kind,category,value):
    # Also accept saved window state/legacy favourites with a URL-encoded colon.
    group,separator,selection=unquote_plus(str(category or '')).partition(':')
    if not separator or not selection:
        raise SimklError('Browser category',reason='Invalid menu route')
    from resources.lib import simkl_discovery as discovery
    if group=='public_tmdb': return discovery.tmdb_ids(kind,selection,value)
    result=discovery.rows_for(group,selection,value)
    if result is not None:
        rows,group=result
    elif group.startswith('public_'):
        media=group[7:]; rows=trending(media,selection); group='shows' if media=='tv' else media
    else:
        rows=group_rows(group)
        if selection!='all': rows=[r for r in rows if ('dropped' if r.get('status')=='notinteresting' else r.get('status'))==selection]
        rows=sorted(rows,key=lambda r:r.get('last_watched_at') or r.get('added_to_watchlist_at') or '',reverse=True)
    ids=[]; eligible=0; failed=0
    for r in rows:
        if selection in ('random','unwatched') and len(set(ids))>=20: break
        if not isinstance(r,dict): continue
        if media_kind(r,group)!=kind: continue
        eligible+=1
        try: mid=tmdb_id(r,kind)
        except Exception as exc:
            failed+=1; log_failure('TMDb mapping',exc); continue
        if mid: ids.append(mid)
    xbmc.log('Diggz Portal SIMKL: %s %s: %d entries, %d eligible, %d mapped, %d mapping errors'%(group,selection,len(rows),eligible,len(set(ids)),failed),xbmc.LOGINFO)
    if eligible and not ids: raise SimklError('TMDb mapping',reason='No matching TMDb IDs')
    return list(dict.fromkeys(ids))

def snapshot(force=False):
    data=all_items(force); result={'movies':{},'shows':{},'episodes':{}}
    for group in ('movies','shows','anime'):
        for row in data.get(group,[]):
            kind=media_kind(row,group); mid=tmdb_id(row,kind)
            if not mid: continue
            key=str(mid)
            if kind=='movie':
                if row.get('status')=='completed': result['movies'][key]=1
                continue
            eps=set()
            for season in row.get('seasons') or []:
                for ep in season.get('episodes') or []:
                    if group=='anime':
                        # SIMKL anime seasons are separate entries. Never assume S1.
                        mapped=ep.get('tvdb') or {}; sn=positive(mapped.get('season')); en=positive(mapped.get('episode'))
                    else: sn=positive(season.get('number')); en=positive(ep.get('number'))
                    if sn and en: eps.add((sn,en))
            if eps:
                result['episodes'].setdefault(key,[]).extend([list(e) for e in sorted(eps)])
            # Anime counts describe an individual SIMKL entry, not the whole TMDb show.
            if group=='shows':
                try: total=int(row.get('total_episodes_count') or 0)-int(row.get('not_aired_episodes_count') or 0)
                except (TypeError,ValueError): total=0
                if total>0: result['shows'][key]=max(total,result['shows'].get(key,0))
    return result


def public_request(path,params=None):
    def load():
        r=requests.get(API+path.strip('/'),params=app_params(CLIENT_ID,params),headers={'User-Agent':UA},timeout=15)
        return response_json(r,path)
    return cached('mapping:'+path+':'+json.dumps(params or {},sort_keys=True),86400,load)

def action_payload(t):
    """Avoid applying TMDb show-level numbers to an unrelated anime season.

    Prefer exact account SIMKL IDs; for split anime use its mapped episode list.
    For new titles the API accepts TMDb IDs, but don't invent season mappings.
    """
    kind=t['kind']; key='movies' if kind=='movie' else 'shows'; media='movie' if kind=='movie' else 'tv'
    data=all_items(); matches=[]
    for group in ('movies','shows','anime'):
        for row in data.get(group,[]):
            if media_kind(row,group)==media and tmdb_id(row,media)==t['id'] and row_id(row): matches.append((group,row))
    # Match episode/season to its anime entry using the source's TVDB mapping.
    if kind in ('episode','season') and any(g=='anime' for g,r in matches):
        candidates=[]
        for group,row in matches:
            if group!='anime': continue
            episodes=public_request('anime/episodes/'+row_id(row),{'extended':'full_anime_seasons'})
            if not isinstance(episodes,list): continue
            mapped=[]
            for ep in episodes:
                pair=ep.get('tvdb') or {}
                if positive(pair.get('season'))!=t['season']: continue
                if kind=='episode' and positive(pair.get('episode'))!=t['episode']: continue
                number=positive(ep.get('number') or ep.get('episode'))
                if number: mapped.append({'number':number})
            if mapped: candidates.append((row,mapped))
        if len(candidates)!=1: raise RuntimeError('No unique SIMKL anime episode mapping')
        row,mapped=candidates[0]
        return {'shows':[{'ids':{'simkl':int(row_id(row))},'seasons':[{'number':1,'episodes':mapped}]}]}
    if matches:
        if len(matches)>1:
            # Different broadcast seasons can share a TMDb show ID. Require a selection.
            if kind not in ('movie','tv'): raise RuntimeError('Ambiguous SIMKL match')
            labels=['%s (%s) - SIMKL %s'%(item(r).get('title','Title'),item(r).get('year',''),row_id(r)) for g,r in matches]
            selected=xbmcgui.Dialog().select('Choose SIMKL title',labels)
            if selected<0: raise RuntimeError('SIMKL action cancelled')
            matches=[matches[selected]]
        group,row=matches[0]; ids={'simkl':int(row_id(row))}
        # Anime films are stored under anime, but the API accepts anime under shows.
        if group=='anime': key='shows'
    else:
        ids={'tmdb':t['id']}
        # For a new TV title, use TMDb's verified external IDs where available.
        if media=='tv':
            from resources.lib import tmdb_catalog as tm, TheMovieDB as db
            info=tm.query(db.get_tmdb_data,'tv/%s/external_ids'%t['id'],{},7)
            if info.get('tvdb_id'): ids={'tvdb':info['tvdb_id']}
            elif info.get('imdb_id'): ids={'imdb':info['imdb_id']}
    obj={'ids':ids}
    if kind in ('season','episode'):
        season={'number':t['season']}
        if kind=='episode': season['episodes']=[{'number':t['episode']}]
        obj['seasons']=[season]
    return {key:[obj]}
