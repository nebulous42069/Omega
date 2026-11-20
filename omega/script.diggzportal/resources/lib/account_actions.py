"""Explicit user-requested account writes and shared media actions."""
from datetime import date
from urllib.parse import urlencode
import requests
import xbmc, xbmcgui, xbmcaddon
from resources.lib import accounts

NAMES={'tmdb':'TMDB','trakt':'Trakt','mdblist':'MDBList','simkl':'SIMKL'}

def target(w, selected=False):
    info=getattr(w,'info',{}) or {}
    if selected:
        li=getattr(w,'listitem',None)
        if not li: return None
        get=li.getProperty
        kind=(get('mediatype') or get('media_type') or li.getVideoInfoTag().getMediaType()).lower()
        ident=get('id'); parent=get('tmdb_id') or getattr(w,'tvshow_id',None) or info.get('tmdb_id') or (info.get('id') if str(getattr(w,'type','')).lower() in ('tv','tvshow') else None)
        season=get('season'); episode=get('episode')
    else:
        kind=str(getattr(w,'type','')).lower(); ident=info.get('id') or info.get('tmdb_id')
        parent=getattr(w,'tvshow_id',None) or info.get('tmdb_id'); season=info.get('season'); episode=info.get('episode')
    kind={'tvshow':'tv','show':'tv','actor':'person','director':'person'}.get(kind,kind)
    if kind not in ('movie','tv','season','episode','person'): return None
    try:
        t={'kind':kind,'id':int(parent if kind in ('season','episode') else ident)}
        if kind in ('season','episode'): t['season']=int(season)
        if kind=='episode': t['episode']=int(episode)
        if t['id']<=0: return None
        return t
    except (ValueError,TypeError): return None

def sources(t, history=False):
    if not t or t['kind']=='person': return []
    return [s for s in ('tmdb','trakt','mdblist','simkl') if (not history or s!='tmdb') and (s!='tmdb' or t['kind'] in ('movie','tv')) and accounts.configured(s)]

def payload(t, source, action):
    if source=='simkl':
        from resources.lib.simkl_api import action_payload
        return action_payload(t)
    kind=t['kind']; key='movies' if kind=='movie' else 'shows'; item={'ids':{'tmdb':t['id']}}
    if kind in ('season','episode'):
        season={'number':t['season']}
        if kind=='episode': season['episodes']=[{'number':t['episode']}]
        item['seasons']=[season]
    if source=='mdblist' and action=='watchlist': item=item['ids']
    return {key:[item]}

def write(source,path,body,params=None,method='POST'):
    if source=='simkl':
        from resources.lib import simkl_api
        return simkl_api.request(path,params,body)
    if source=='tmdb':
        data=accounts.tmdb(path,params,body)
        if data.get('success') is False or data.get('status_code') not in (None,1,12,13): raise RuntimeError('TMDb rejected action')
        return data
    if source=='trakt':
        from resources.lib import trakt_api
        token=trakt_api.get_access_token()
        if not token: raise RuntimeError('Trakt authorization unavailable')
        url='https://api.trakt.tv/'+path; headers=dict(trakt_api.HEADERS,Authorization='Bearer '+token)
    else:
        from resources.lib import mdblist_oauth as oauth
        token=oauth.token(); url=oauth.API+'/'+path; headers={'Authorization':'Bearer '+token}
    r=requests.request(method,url,json=body,headers=headers,timeout=15)
    if source=='mdblist' and r.status_code==401:
        headers['Authorization']='Bearer '+oauth.token(rejected=token)
        r=requests.request(method,url,json=body,headers=headers,timeout=15)
    if not r.ok: raise RuntimeError('Request rejected (%s)'%r.status_code)
    data=r.json() if r.content else {}
    if isinstance(data,dict) and (data.get('error') or data.get('errors') or any((data.get('not_found') or {}).values())): raise RuntimeError('Service could not apply action')
    return data

def watched(t,h):
    ident=str(t['id']); kind=t['kind']; eps=h.get('episodes',{}).get(ident,set())
    if kind=='movie': return ident in h.get('movies',{})
    if kind=='episode': return (t['season'],t['episode']) in eps
    if not eps: return False
    if kind=='season':
        rows=detail('tv/%s/season/%s'%(t['id'],t['season'])).get('episodes',[])
        aired={(t['season'],e['episode_number']) for e in rows if e.get('air_date') and e['air_date']<=date.today().isoformat()}
        return bool(aired) and aired.issubset(eps)
    total=h.get('shows',{}).get(ident) or detail('tv/'+ident).get('number_of_episodes',0)
    return bool(total) and len([e for e in eps if e[0]>0])>=int(total)

def detail(path):
    from resources.lib.personal_history import detail as get
    return get(path) or {}

def refresh(w,t,services=None):
    # Refresh history, then redraw only the visible items. Keep page and focus.
    if services:
        for source in services: accounts.history(force=True,include_disabled=True,scope=source)
    else: accounts.history(force=True, include_disabled=True)
    h=accounts.history(include_disabled=True, scope=accounts.window_scope(w))
    from resources.lib import Utils
    focus=w.getFocusId()
    if hasattr(w,'listitems2'):
        ctl=w.getControl(500); pos=ctl.getSelectedPosition()
        # History pools can have changed membership as well as badges.
        if getattr(w,'mode','')=='trakt_catalog' and isinstance(w.search_str,dict) and (w.search_str.get('category','').startswith('history_') or w.search_str.get('source')=='simkl'):
            w.update_content(force_update=True); items=w.listitems
        else:
            items=Utils.create_listitems(w.listitems2,preload_images=0,enable_clearlogo=Utils.netflix_view(),history_source=accounts.window_scope(w))
            w.listitems=items
        ctl.reset(); ctl.addItems(items)
        if items: ctl.selectItem(min(pos,len(items)-1))
    elif hasattr(w,'fill_lists'):
        for cid,rows in w.listitems:
            ctl=w.getControl(cid); pos=ctl.getSelectedPosition()
            items=Utils.create_listitems(rows,preload_images=0,enable_clearlogo=False,info=w.info,history_source=accounts.window_scope(w))
            ctl.reset(); ctl.addItems(items)
            if items: ctl.selectItem(min(pos,len(items)-1))
    try: w.setFocusId(focus)
    except RuntimeError: pass
    set_properties(w,h)

def history_sources(w,t):
    scope=accounts.window_scope(w)
    return [s for s in sources(t,True) if scope=='combined' or s==scope]

def set_properties(w,h=None):
    t=target(w)
    if not t: return
    for s in NAMES: w.setProperty('PortalAccount'+s,'true' if s in sources(t) else '')
    w.setProperty('PortalHistoryActions','true' if history_sources(w,t) else '')
    # Avoid extra metadata requests on initial dialog open.
    if h is not None:
        try: w.setProperty('PortalWatchAction','Mark as Unwatched' if watched(t,h) else 'Mark as Watched')
        except Exception: pass
    else:
        try:
            h=accounts.history(include_disabled=True, scope=accounts.window_scope(w)) if history_sources(w,t) else {}
            w.setProperty('PortalWatchAction','Mark as Unwatched' if watched(t,h) else 'Mark as Watched')
        except Exception: w.setProperty('PortalWatchAction','Watched Status')
    w.setProperty('PortalHasTrailers','true' if (getattr(w,'data',{}) or {}).get('videos') else '')

def mark(w,t,remove=None,source=None):
    dlg=xbmcgui.Dialog(); choices=sources(t,True)
    if not source and accounts.window_scope(w) in ('trakt','mdblist','simkl'): source=accounts.window_scope(w)
    if source: choices=[s for s in choices if s==source]
    if not choices: return
    if remove is None:
        h=accounts.history(include_disabled=True, scope=accounts.window_scope(w)); remove=watched(t,h)
    action='Mark as Unwatched' if remove else 'Mark as Watched'
    if len(choices)>1:
        i=dlg.select(action,[NAMES[s] for s in choices]+['All available services'])
        if i<0: return
        if i<len(choices): choices=[choices[i]]
    if not dlg.yesno(action,'Update '+ ' and '.join(NAMES[s] for s in choices)+'?'): return
    success=[]; failed=[]
    for s in choices:
        try:
            body=payload(t,s,'history'); path='sync/history' if s in ('trakt','simkl') else 'sync/watched'
            if s=='simkl' and t['kind']=='tv' and not remove:
                next(iter(body.values()))[0]['to']='completed'; path='sync/add-to-list'
            write(s,path+('/remove' if remove else ''),body); success.append(s)
        except Exception: failed.append(s)
    if success:
        accounts.note_history_change(t)
        try: refresh(w,t,success)
        except Exception: dlg.notification('Diggz Portal','Saved; refresh history to update indicators')
    if failed: dlg.ok('Account update','Failed: '+', '.join(NAMES[s] for s in failed)+('. Saved: '+', '.join(NAMES[s] for s in success) if success else ''))
    elif success: dlg.notification('Diggz Portal',action+' saved')

def custom(source,t,remove):
    dlg=xbmcgui.Dialog()
    if source=='trakt':
        from resources.lib.trakt_catalog import request
        rows=request('users/me/lists',{'limit':100},personal=True)
        options=[(r['ids']['trakt'],r.get('name','List')) for r in rows if r.get('ids',{}).get('trakt')]
    else:
        rows,_=accounts.mdb('lists/user'); rows=rows.get('lists',[]) if isinstance(rows,dict) else rows
        options=[(r['id'],r.get('name','List')) for r in rows if r.get('id') and not r.get('dynamic')]
    i=dlg.select('Remove from list' if remove else 'Add to list',[n for _,n in options]) if options else -1
    if i<0: return False
    ident=int(options[i][0]); suffix='remove' if remove else 'add'
    if source=='trakt': write(source,'users/me/lists/%s/items'%ident+('/remove' if remove else ''),payload(t,source,'list'))
    else: write(source,'lists/%s/items/%s'%(ident,suffix),{('movies' if t['kind']=='movie' else 'shows'):[{'tmdb':t['id']}]})
    return True

def manage_simkl(w,t):
    from resources.lib import simkl_api
    dlg=xbmcgui.Dialog(); options=[]
    if t['kind'] in ('movie','tv'):
        statuses=simkl_api.STATUSES if t['kind']=='tv' else [s for s in simkl_api.STATUSES if s[0]!='watching']
        options.extend((status,'Set: '+label) for status,label in statuses)
        options.append(('remove_list','Remove title and watched history'))
    options.extend([('watched','Mark as Watched'),('unwatched','Mark as Unwatched')])
    i=dlg.select('My SIMKL',[v for k,v in options])
    if i<0: return
    action,label=options[i]
    if action in ('watched','unwatched'): return mark(w,t,action=='unwatched','simkl')
    if not dlg.yesno('SIMKL',label+'?'): return
    try:
        body=payload(t,'simkl','list')
        if action=='remove_list': path='sync/history/remove'
        else:
            path='sync/add-to-list'; next(iter(body.values()))[0]['to']=action
        write('simkl',path,body); accounts.note_history_change(t); refresh(w,t,['simkl'])
        dlg.notification('SIMKL',label+' saved')
    except Exception: dlg.ok('SIMKL','Account action failed. Check authorization and try again.')

def manage(w,t,source):
    if source not in sources(t): return
    if source=='simkl': return manage_simkl(w,t)
    dlg=xbmcgui.Dialog(); whole=t['kind'] in ('movie','tv'); options=[]
    if whole:
        options.extend([('watchlist',False,'Add to Watchlist'),('watchlist',True,'Remove from Watchlist')])
        if source=='tmdb': options.extend([('favorite',False,'Add to Favorites'),('favorite',True,'Remove from Favorites')])
        else: options.extend([('custom',False,'Add to Custom List'),('custom',True,'Remove from Custom List')])
    if source=='tmdb' or (source=='trakt' and whole): options.append(('rating',False,'Rate Title'))
    if source!='tmdb': options.extend([('history',False,'Mark as Watched'),('history',True,'Mark as Unwatched')])
    i=dlg.select('My '+NAMES[source],[x[2] for x in options])
    if i<0: return
    action,remove,label=options[i]
    try:
        if action=='history': return mark(w,t,remove,source)
        if action=='custom':
            if not custom(source,t,remove): return
        elif source=='tmdb':
            a=accounts.addon(); p={'session_id':a.getSetting('tmdb_session')}; kind=t['kind']
            if action=='rating':
                rating=dlg.select('Rate Title',[str(n) for n in range(1,11)])
                if rating<0: return
                write(source,'%s/%s/rating'%(kind,t['id']),{'value':rating+1},p)
            else: write(source,'account/%s/%s'%(a.getSetting('tmdb_account'),action),{'media_type':kind,'media_id':t['id'],action:not remove},p)
        elif action=='rating':
            rating=dlg.select('Rate Title',[str(n) for n in range(1,11)])
            if rating<0: return
            body=payload(t,source,action); next(iter(body.values()))[0]['rating']=rating+1
            write(source,'sync/ratings',body)
        else:
            path=('sync/watchlist'+('/remove' if remove else '')) if source=='trakt' else 'watchlist/items/'+('remove' if remove else 'add')
            write(source,path,payload(t,source,action))
        dlg.notification(NAMES[source],label+' saved')
    except Exception: dlg.ok(NAMES[source],'Account action failed. Check authorization and try again.')

def play(w,t):
    from resources.lib.tmdb_helper import choose_player
    kind=t['kind']; p={'info':'play','tmdb_id':t['id'],'type':'movie' if kind=='movie' else 'episode'}
    if kind!='movie':
        if kind=='episode': p.update(season=t['season'],episode=t['episode'])
        else:
            h=accounts.history(include_disabled=True, scope=accounts.window_scope(w)); eps=h.get('episodes',{}).get(str(t['id']),set()); show=detail('tv/'+str(t['id'])); today=date.today().isoformat()
            found=None
            for s in sorted(show.get('seasons',[]),key=lambda s:s['season_number']):
                sn=s['season_number']
                if sn<=0 or (kind=='season' and sn!=t['season']): continue
                if s.get('episode_count') and sum(a==sn for a,b in eps)>=s['episode_count']: continue
                for e in detail('tv/%s/season/%s'%(t['id'],sn)).get('episodes',[]):
                    if e.get('air_date') and e['air_date']<=today and (sn,e['episode_number']) not in eps: found=(sn,e['episode_number']); break
                if found: break
            if not found:
                xbmcgui.Dialog().ok('Next Episode','No available unwatched episode found.'); return
            p.update(season=found[0],episode=found[1])
    choose_player('plugin://plugin.video.themoviedb.helper/?'+urlencode(p))

def trailers(w,t):
    from resources.lib import TheMovieDB as db, YouTube
    path=media_path(t)+'/videos'; data=db.handle_tmdb_videos(detail(path).get('results',[]))
    if not data: xbmcgui.Dialog().notification('Official Trailers','No official trailers available'); return
    i=xbmcgui.Dialog().select('Official Trailers',[r['title'] for r in data])
    if i>=0: YouTube.play_video(data[i]['youtube_id'],dialog=w)

def media_path(t):
    k=t['kind']; path=('movie' if k=='movie' else 'tv')+'/'+str(t['id'])
    if k in ('season','episode'): path+='/season/'+str(t['season'])
    if k=='episode': path+='/episode/'+str(t['episode'])
    return path

def information(w,t):
    from resources.lib.WindowManager import wm
    k=t['kind']; ident=t['id']
    if k=='movie': wm.open_movie_info(prev_window=w,movie_id=ident)
    elif k=='tv': wm.open_tvshow_info(prev_window=w,tmdb_id=ident)
    elif k=='season': wm.open_season_info(prev_window=w,tvshow_id=ident,season=t['season'])
    elif k=='episode': wm.open_episode_info(prev_window=w,tvshow_id=ident,season=t['season'],episode=t['episode'])
    elif k=='person': wm.open_actor_info(prev_window=w,actor_id=ident)

def similar(w,t):
    from resources.lib import TheMovieDB as db
    from resources.lib.WindowManager import wm
    kind=t['kind']; rows=detail(media_path(t)+'/recommendations').get('results',[])
    items=db.handle_tmdb_movies(rows,sortkey=None) if kind=='movie' else db.handle_tmdb_tvshows(rows,sortkey=None)
    if not items: xbmcgui.Dialog().notification('Similar Titles','No recommendations available'); return
    wm.open_video_list(prev_window=w,mode='list_items',search_str=items,filter_label='Similar Titles',media_type=kind)

def menu(w,t):
    if not t: return
    dlg=xbmcgui.Dialog(); k=t['kind']; options=[]
    if k!='person': options.append(('Play' if k in ('movie','episode') else 'Next Episode',lambda:play(w,t)))
    options.append(('Information',lambda:information(w,t)))
    if k!='person': options.append(('Official Trailers',lambda:trailers(w,t)))
    if history_sources(w,t):
        try: remove=watched(t,accounts.history(include_disabled=True, scope=accounts.window_scope(w)))
        except Exception: remove=False
        options.append(('Mark as Unwatched' if remove else 'Mark as Watched',lambda:mark(w,t,remove)))
    for s in sources(t): options.append(('My '+NAMES[s],lambda s=s:manage(w,t,s)))
    if k in ('movie','tv'): options.append(('Similar Titles',lambda:similar(w,t)))
    labels=[a for a,b in options]; i=dlg.contextmenu(labels)
    if i>=0:
        try: options[i][1]()
        except Exception: dlg.ok('Diggz Portal','Action failed. Check service availability and try again.')

def button(w,control):
    t=target(w)
    if control==445:
        xbmcaddon.Addon().openSettings()
        from resources.lib.appearance import apply_focus_appearance
        apply_focus_appearance(w); set_properties(w); return True
    if control not in (460,461,462,463,464,465,9,10) or not t: return False
    try:
        if control==460: trailers(w,t)
        elif control==461: mark(w,t)
        elif control in (462,463,464,465): manage(w,t,{462:'tmdb',463:'trakt',464:'mdblist',465:'simkl'}[control])
        elif control in (9,10): play(w,t)
    except Exception: xbmcgui.Dialog().ok('Diggz Portal','Action failed. Check service availability and try again.')
    return True
