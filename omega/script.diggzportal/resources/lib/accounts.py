"""Independent account access; credentials never enter directory URLs or logs."""
import json, os, time, hashlib
import requests
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from resources.lib import mdblist_oauth


SERVICE_NAMES = {'tmdb':'TMDB','trakt':'Trakt','mdblist':'MDBList','simkl':'SIMKL'}
MANAGER_ID = 'script.module.authorizediggz'
# MDBList's legacy API-key action does not authorize Portal's OAuth client.
MANAGER_ACTIONS = {'tmdb':'tmdbAuth','trakt':'traktAuth','mdblist':'mdblistOAuthAuth','simkl':'simklAuth'}

def manager_available():
    try:
        return bool(xbmc.getCondVisibility('System.HasAddon('+MANAGER_ID+')') and xbmc.getCondVisibility('System.AddonIsEnabled('+MANAGER_ID+')'))
    except Exception:
        return False

def launch_manager(source):
    action=MANAGER_ACTIONS.get(source)
    if not action: return
    if manager_available():
        xbmc.executebuiltin('RunScript('+MANAGER_ID+',action='+action+')')
    else:
        xbmcgui.Dialog().notification('Accounts','Account Manager is not installed or enabled',xbmcgui.NOTIFICATION_ERROR)

def authorize_browser(source, managed=False):
    """A stale browser entry must not start a second login. Settings remain independent."""
    if source not in SERVICE_NAMES or configured(source): return False
    if managed:
        launch_manager(source)
    elif source=='trakt':
        from resources.lib import trakt_api
        trakt_api.login_trakt()
    else:
        login(source)
    return True

def confirm_disconnect(source):
    name=SERVICE_NAMES.get(source)
    if not name: return False
    message='Disconnect '+name+' from Portal?'
    if source!='simkl' and manager_available():
        message+=' Account Manager may resync its saved account later.'
    if not xbmcgui.Dialog().yesno(name,message): return False
    logout(source)
    return True

def addon(): return xbmcaddon.Addon()
def configured(source):
    a=addon()
    if source=='simkl':
        from resources.lib import simkl_api
        return simkl_api.configured()
    if source=='trakt':
        from resources.lib import trakt_api
        trakt_api.ensure_client()
    return bool(a.getSetting({'tmdb':'tmdb_session','mdblist':'mdblist_access_token','trakt':'access_token'}[source]) or (source=='trakt' and a.getSetting('refresh_token')))

TMDB_SESSION_CLIENT = 'v4-compatible'
TMDB_APP_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhMDczMjRjNjY5Y2FjNGQ5Njc4OTE5NzEzNGNlMjcyYiIsIm5iZiI6MTUxOTkzOTM2NC42MDYwMDAyLCJzdWIiOiI1YTk4NmYyNGMzYTM2ODA3M2EwMDZiYzAiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.YMASJX_w-l8tDnqGHl_6EZljra3TOp-hnkgKjyFM4Y8'

def tmdb(path, params=None, body=None):
    from resources.lib.TheMovieDB import API_key
    p=dict(params or {})
    headers={}
    a=addon()
    if p.get('session_id') and p['session_id']==a.getSetting('tmdb_session') and a.getSetting('tmdb_session_client')==TMDB_SESSION_CLIENT:
        headers['Authorization']='Bearer '+TMDB_APP_READ_TOKEN
    else:
        p['api_key']=API_key
    r=requests.request('POST' if body is not None else 'GET','https://api.themoviedb.org/3/'+path,params=p,json=body,headers=headers,timeout=15)
    if not r.ok: raise RuntimeError('TMDb request failed (%s)'%r.status_code)
    return r.json()

def mdb(path, params=None):
    return mdblist_oauth.request(path, params)

def login(source):
    dlg=xbmcgui.Dialog(); a=addon()
    if source=='tmdb':
        username=dlg.input('TMDb - Enter your username').strip()
        if not username: return
        password=dlg.input('TMDb - Enter your password',option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if not password: return
        try:
            token=tmdb('authentication/token/new')['request_token']
            validated=tmdb('authentication/token/validate_with_login',body={
                'username':username,'password':password,'request_token':token})
            if validated.get('success') is not True:
                raise RuntimeError('TMDb login rejected')
            result=tmdb('authentication/session/new',body={'request_token':validated.get('request_token') or token})
            if result.get('success') is not True or not result.get('session_id'):
                raise RuntimeError('TMDb session creation failed')
            session=result['session_id']
            user=tmdb('account',{'session_id':session})
            account_id=str(user['id'])
        except Exception:
            dlg.notification('TMDb','Authorization failed. Check login details and try again.',xbmcgui.NOTIFICATION_ERROR)
            return
        finally:
            del password
        a.setSetting('tmdb_session_client',''); a.setSetting('tmdb_account',account_id); a.setSetting('tmdb_session',session)
    elif source=='mdblist':
        if not mdblist_oauth.login(): return
    elif source=='simkl':
        from resources.lib import simkl_api
        if not simkl_api.login(): return
    else: return
    dlg.notification(source.upper(),'Account authorized')

def logout(source):
    if source=='simkl':
        from resources.lib import simkl_api
        simkl_api.logout()
        xbmcgui.Dialog().notification('SIMKL','Disconnected locally'); return
    a=addon()
    for key in {'tmdb':('tmdb_session','tmdb_account','tmdb_session_client'),'trakt':('access_token','refresh_token','token_expires','trakt_token','trakt_slug','trakt_user_name'),'mdblist':('mdblist_access_token','mdblist_refresh_token','mdblist_expires','mdblist_identity','mdblist_key')}[source]: a.setSetting(key,'')
    if source in ('trakt','mdblist','simkl'):
        try: os.remove(os.path.join(xbmcvfs.translatePath(a.getAddonInfo('profile')),'history_'+source+'.json'))
        except OSError: pass
    xbmcgui.Dialog().notification(source.upper(),'Disconnected locally')

def mdb_pages(path,params,keyname=None,max_pages=100):
    rows=[]; seen=set(); p=dict(params); p.setdefault('limit',100)
    for _ in range(max_pages):
        data,h=mdb(path,p)
        batch=data.get(keyname) if isinstance(data,dict) and keyname else data
        if not isinstance(batch,list): raise RuntimeError('Unexpected MDBList response')
        rows.extend(batch)
        pagination=data.get('pagination',{}) if isinstance(data,dict) else {}
        cursor=pagination.get('next_cursor') or h.get('x-next-cursor')
        if not cursor:
            if pagination.get('has_more') or h.get('x-has-more','').lower()=='true': raise RuntimeError('MDBList missing pagination cursor')
            return rows
        if cursor in seen: raise RuntimeError('MDBList repeated pagination cursor')
        seen.add(cursor); p['cursor']=cursor
    raise RuntimeError('MDBList history exceeds sync limit')

def identity(source):
    if source=='simkl':
        from resources.lib import simkl_api
        return simkl_api.identity()
    a=addon(); key=(a.getSetting('mdblist_identity') if source=='mdblist' else a.getSetting('refresh_token') or a.getSetting('access_token'))
    return hashlib.sha256(key.encode()).hexdigest()

def snapshot(source,force=False):
    if source=='simkl':
        from resources.lib import simkl_api
        return simkl_api.snapshot(force)
    if source=='trakt':
        from resources.lib.trakt_catalog import watched_pages
        movies=watched_pages('movie')
        shows=watched_pages('tv')
    else:
        movies=mdb_pages('sync/watched',{'mediatype':'movie'},'movies')
        episodes=mdb_pages('sync/watched',{'mediatype':'episode'},'episodes')
        shows=[]
    if not isinstance(movies,list) or not isinstance(shows,list): raise RuntimeError('Invalid history response')
    result={'movies':{},'shows':{},'episodes':{}}
    for row in movies:
        movie=row.get('movie',row); ident=movie.get('ids',{}).get('tmdb')
        if ident and int(row.get('plays',1) or 0)>0: result['movies'][str(ident)]=1
    def add(show,s,e):
        ident=show.get('ids',{}).get('tmdb')
        if ident and int(s)>0: result['episodes'].setdefault(str(ident),[]).append([int(s),int(e)])
    if source=='trakt':
        for row in shows:
            show=row['show']; ident=show.get('ids',{}).get('tmdb')
            if ident and show.get('aired_episodes'): result['shows'][str(ident)]=int(show['aired_episodes'])
            for season in row.get('seasons',[]):
                for ep in season.get('episodes',[]):
                    if ep.get('plays',0)>0: add(show,season['number'],ep['number'])
    else:
        for row in episodes:
            ep=row['episode']; add(ep['show'],ep['season'],ep['number'])
    return result

_MEMORY={}
HISTORY_REVISION=0
_HISTORY_CHANGED=set()
def note_history_change(t):
    global HISTORY_REVISION
    HISTORY_REVISION+=1
    _HISTORY_CHANGED.add(('movie' if t['kind']=='movie' else 'tv',str(t['id'])))

def clean_history_row(result,show_id,scope='combined'):
    kind=result.get('mediatype')
    if kind not in ('movie','tvshow','season','episode'): return result
    ident=str(result.get('id') if kind in ('movie','tvshow') else result.get('tmdb_id') or show_id)
    if scope in ('trakt','mdblist','simkl'):
        for field in ('playcount','PlayCount','WatchedEpisodes','UnWatchedEpisodes'):
            result.pop(field,None)
        if result.get('PortalHistorySource') != scope:
            for field in ('PortalHistoryEpisodes','PortalHistoryAired','PercentPlayed','StartPercent'):
                result.pop(field,None)
    if ('movie' if kind=='movie' else 'tv',ident) in _HISTORY_CHANGED:
        result=dict(result)
        for field in ('PortalHistoryEpisodes','PortalHistoryAired','playcount','WatchedEpisodes','UnWatchedEpisodes','PlayCount','PercentPlayed','StartPercent'):
            result.pop(field,None)
    return result

def history_scope(mode, search_str=None, inherited='combined'):
    if mode == 'trakt_catalog':
        source = search_str.get('source','trakt') if isinstance(search_str,dict) else 'trakt'
        return source if source in ('trakt','mdblist','simkl') else 'combined'
    if mode == 'trakt': return 'trakt'
    if mode in ('list_items','list','person','reopen_window',None):
        return inherited if inherited in ('trakt','mdblist','simkl') else 'combined'
    return 'combined'

def window_scope(w):
    return history_scope(getattr(w,'mode',None),getattr(w,'search_str',None),getattr(w,'history_source','combined'))

def history(force=False, include_disabled=False, scope='combined'):
    a=addon(); merged={'movies':{},'shows':{},'episodes':{},'movie_progress':{},'episode_progress':{},'complete':False}
    if not include_disabled and a.getSetting('trakt_watched_stats')=='false': return merged
    folder=xbmcvfs.translatePath(a.getAddonInfo('profile')); os.makedirs(folder,exist_ok=True)
    configured_count=0
    available_count=0
    for source in ('trakt','mdblist','simkl'):
        if scope in ('trakt','mdblist','simkl') and source != scope: continue
        if not configured(source): continue
        configured_count+=1
        ident=identity(source); path=os.path.join(folder,'history_'+source+'.json'); cache={}
        try:
            with open(path,encoding='utf8') as f: cache=json.load(f)
        except (OSError,ValueError): pass
        if cache.get('identity')!=ident or cache.get('version')!=2: cache={}
        changed=False
        if source=='trakt' and cache.get('watched_api_revision')!=1:
            cache.pop('data',None); cache.pop('time',None)
        if force or (time.time()-cache.get('time',0)>900 and time.time()-_MEMORY.get((source,ident),0)>120):
            _MEMORY[(source,ident)]=time.time()
            try:
                data=snapshot(source,force)
                cache.update(version=2,identity=identity(source),time=time.time(),data=data,watched_api_revision=1)
                changed=True
            except Exception as exc:
                if source=='simkl':
                    from resources.lib import simkl_api
                    simkl_api.log_failure('watched history',exc)
                else: xbmc.log('Diggz Portal: '+source+' watched history refresh failed',xbmc.LOGWARNING)
                if force: xbmcgui.Dialog().notification(source.upper(),'History refresh failed; retaining previous history')
        # Playback is independent of completed history: a failed endpoint must
        # not discard a successful watched-history refresh (or vice versa).
        progress_key=(source,ident,'playback')
        if source!='simkl' and (force or (time.time()-cache.get('playback_time',0)>900 and time.time()-_MEMORY.get(progress_key,0)>120)):
            _MEMORY[progress_key]=time.time()
            try:
                from resources.lib.personal_history import playback
                movies=playback(source,'movie')
                episodes=playback(source,'tv')
                cache.update(version=2,identity=identity(source),playback_time=time.time(),playback=movies+episodes)
                changed=True
            except Exception:
                xbmc.log('Diggz Portal: '+source+' playback progress refresh failed',xbmc.LOGWARNING)
        if changed:
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',dir=folder,delete=False) as f:
                    json.dump(cache,f); tmp=f.name
                os.replace(tmp,path)
            except OSError:
                xbmc.log('Diggz Portal: unable to persist '+source+' history cache',xbmc.LOGWARNING)
        for mid,season,episode,progress in cache.get('playback',[]):
            if not 0<progress<100: continue
            if season==0 and episode==0:
                key=str(mid); dest=merged['movie_progress']
            else:
                key=(str(mid),int(season),int(episode)); dest=merged['episode_progress']
            dest[key]=max(progress,dest.get(key,0))
        data=cache.get('data',{})
        if all(isinstance(data.get(k),dict) for k in ('movies','shows','episodes')): available_count+=1
        merged['movies'].update(data.get('movies',{}))
        for sid,total in data.get('shows',{}).items(): merged['shows'][sid]=max(total,merged['shows'].get(sid,0))
        for ident,eps in data.get('episodes',{}).items(): merged['episodes'].setdefault(ident,set()).update(tuple(e) for e in eps)
    merged['complete']=configured_count>0 and configured_count==available_count
    return merged

def mark(result,show_id,li,hist):
    kind=result.get('mediatype'); ident=str(result.get('id',''))
    if kind=='movie' and ident in hist['movies']: result['playcount']=1; li.setProperty('PlayCount','1')
    if kind in ('tvshow','season','episode'):
        sid=ident if kind=='tvshow' else str(result.get('tmdb_id') or show_id)
        eps=hist['episodes'].get(sid,set())
        if kind=='tvshow' and result.get('PortalHistoryEpisodes') and addon().getSetting('trakt_watched_stats')!='false':
            eps=set(eps).union(tuple(e) for e in result['PortalHistoryEpisodes'])
        if not eps: return
        if kind=='episode':
            if (int(result.get('season',-1)),int(result.get('episode',-1))) in eps: result['playcount']=1; li.setProperty('PlayCount','1')
        elif kind=='tvshow':
            total=hist['shows'].get(sid) or result.get('PortalHistoryAired') or result.get('TotalEpisodes')
            if not total:
                from resources.lib import TheMovieDB as db,tmdb_catalog as cat
                detail=cat.query(db.get_tmdb_data,'tv/'+sid,{'language':'en-US'},1)
                total=detail.get('number_of_episodes')
            if total:
                total=int(total); count=min(total,len(eps)); remaining=max(0,total-count)
                li.setProperty('PlayCount',str(int(remaining==0)))
                result['playcount']=int(remaining==0); result['UnWatchedEpisodes']=remaining; result['WatchedEpisodes']=count; result['TotalEpisodes']=total
                for k,v in [('UnWatchedEpisodes',remaining),('WatchedEpisodes',count),('TotalEpisodes',total)]: li.setProperty(k,str(v))
        else:
            season=int(result.get('season',-1)); count=sum(s==season for s,e in eps)
            total=result.get('TotalEpisodes') or result.get('episode_count')
            if not total and count:
                from resources.lib import TheMovieDB as db,tmdb_catalog as cat
                from datetime import date
                detail=cat.query(db.get_tmdb_data,'tv/'+sid+'/season/'+str(season),{'language':'en-US'},1)
                total=sum(1 for ep in detail.get('episodes',[]) if ep.get('air_date') and ep['air_date']<=date.today().isoformat())
            if total and count:
                total=int(total); remaining=max(0,total-count); result['playcount']=int(remaining==0); li.setProperty('UnWatchedEpisodes',str(remaining)); li.setProperty('WatchedEpisodes',str(count)); li.setProperty('PlayCount',str(int(remaining==0)))


def status_overlay(result,show_id,li,hist):
    """Display known history; an unavailable history is not an unwatched title."""
    kind=result.get('mediatype')
    if kind not in ('movie','tvshow','season','episode'): return
    if addon().getSetting('trakt_watched_stats')=='false':
        li.setProperty('PortalWatchState',''); li.setProperty('PortalWatchLabel',''); return
    ident=str(result.get('id',''))
    if not ident or ident=='0': return
    def number(value):
        try: return int(value or 0)
        except (ValueError,TypeError): return 0
    watched=number(li.getProperty('PlayCount'))
    remaining=number(li.getProperty('UnWatchedEpisodes'))
    count=number(li.getProperty('WatchedEpisodes'))
    state=label=''
    if kind in ('tvshow','season') and count>0 and remaining>0:
        state='partial'; label='%d episode%s left'%(remaining,'' if remaining==1 else 's')
    elif watched>0:
        state='watched'; label='Watched'
    elif kind in ('tvshow','season'):
        sid=ident if kind=='tvshow' else str(result.get('tmdb_id') or show_id)
        eps=hist.get('episodes',{}).get(sid,set())
        if kind=='tvshow' and addon().getSetting('trakt_watched_stats')!='false': eps=set(eps).union(tuple(e) for e in result.get('PortalHistoryEpisodes',[]))
        if kind=='season': eps=[e for e in eps if e[0]==number(result.get('season'))]
        if eps: state='partial'; label='In progress'
    if not state:
        progress=0
        if kind=='movie':
            progress=hist.get('movie_progress',{}).get(ident,0)
        elif kind=='episode':
            sid=str(result.get('tmdb_id') or show_id)
            progress=hist.get('episode_progress',{}).get((sid,number(result.get('season')),number(result.get('episode'))),0)
        elif kind in ('tvshow','season'):
            sid=ident if kind=='tvshow' else str(result.get('tmdb_id') or show_id)
            if any(key[0]==sid and (kind=='tvshow' or key[1]==number(result.get('season'))) for key in hist.get('episode_progress',{})):
                state='partial'; label='In progress'
        # Account-list rows can carry a fresh percentage even before the
        # shared snapshot is refreshed. Preserve that existing behavior.
        if not state:
            progress=max(number(result.get('PercentPlayed')),progress)
            if 0<progress<100:
                state='partial'; label='%d%% watched'%max(1,int(progress))
    li.setProperty('PortalWatchState',state)
    li.setProperty('PortalWatchLabel',label)
