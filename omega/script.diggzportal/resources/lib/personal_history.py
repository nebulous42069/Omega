"""Read-only service-specific history lists. Episode references are [show, season, episode, progress]."""
from datetime import date
from resources.lib import accounts

COMMON=[('released','Watchlist (Released)'),('anticipated','Watchlist (Anticipated)'),('recent','Your Recently Watched'),('most','Your Most Watched'),('progress','Your In-Progress'),('still','Still to Watch'),('current','Currently Watching'),('rec_recent','Based on Recently Watched'),('rec_most','Based on Most Watched')]
def entries(kind):
    rows=COMMON+([('progress_unwatched','Your In-Progress (Unwatched)'),('next_movies','Your Next Movies')] if kind=='movie' else [('progress_episodes','Your In-Progress Episodes'),('progress_unwatched','Your In-Progress Episodes (Unwatched)'),('next_episodes','Your Next Episodes'),('dropped','Dropped TV Shows'),('airing','Your Episodes Airing Next')])
    return [('history_'+k,v) for k,v in rows]

def identifier(item):
    return (item or {}).get('ids',{}).get('tmdb') or (item or {}).get('tmdb_id')

def unique(rows):
    seen=set(); out=[]
    for row in rows:
        key=tuple(row[:3]) if isinstance(row,list) else row
        if row and key not in seen: seen.add(key); out.append(row)
    return out

def get(source,path,params=None,key=None):
    if source=='trakt':
        from resources.lib.trakt_catalog import request
        return request(path,params,personal=True)
    return accounts.mdb_pages(path,params or {},key)

def detail(path):
    from resources.lib import tmdb_catalog as cat, TheMovieDB as db
    return cat.query(db.get_tmdb_data,path,{'language':'en-US'},1)

def watched(source,kind):
    media='movies' if kind=='movie' else 'shows'
    if source=='trakt':
        from resources.lib.trakt_catalog import watched_pages
        rows=watched_pages(kind)
    else:
        rows=get(source,'sync/watched',{'mediatype':'movie' if kind=='movie' else 'episode'},'movies' if kind=='movie' else 'episodes')
    out={}
    for row in rows:
        ep=row.get('episode',{}); item=row.get('movie',row) if kind=='movie' else row.get('show') or ep.get('show',{})
        ident=identifier(item)
        if not ident: continue
        entry=out.setdefault(int(ident),{'plays':0,'time':'','episodes':set(),'trakt':item.get('ids',{}).get('trakt'),'aired':int(item.get('aired_episodes') or 0)})
        entry['plays']+=sum(int(e.get('plays',0) or 0) for season in row.get('seasons',[]) for e in season.get('episodes',[])) if kind=='tv' and source=='trakt' else int(row.get('plays',1) or 0)
        entry['time']=max(entry['time'],str(row.get('last_watched_at') or row.get('watched_at') or ''))
        if ep and ep.get('season',0)>0: entry['episodes'].add((ep['season'],ep['number']))
        for season in row.get('seasons',[]):
            if season['number']>0:
                entry['episodes'].update((season['number'],e['number']) for e in season.get('episodes',[]) if e.get('plays',0)>0)
    return out

def playback(source,kind):
    media='movies' if kind=='movie' else 'episodes'
    if source=='trakt':
        rows=[]
        for page in range(1,101):
            batch=get(source,'sync/playback/'+media,{'limit':100,'page':page})
            if not isinstance(batch,list): raise RuntimeError('Invalid Trakt playback response')
            rows.extend(batch)
            if len(batch)<100: break
        else: raise RuntimeError('Trakt playback exceeds sync limit')
    else:
        rows=get(source,'sync/playback')
    out=[]
    for row in sorted(rows,key=lambda r:r.get('paused_at') or '',reverse=True):
        ep=row.get('episode') or {}; item=row.get('movie') if kind=='movie' else row.get('show') or ep.get('show')
        ident=identifier(item); progress=float(row.get('progress') or 0)
        if not ident or not 0<progress<100: continue
        if kind=='movie': out.append([int(ident),0,0,progress])
        elif ep.get('season') is not None and ep.get('number'): out.append([int(ident),int(ep['season']),int(ep['number']),progress])
    return unique(out)

def watchlist(source,kind):
    from resources.lib import account_catalog, trakt_catalog
    if source in ('mdblist','tmdb'): return account_catalog.pool(source,kind,'watchlist','')
    return trakt_catalog.pool(kind,'personal_list','users/me/watchlist/'+('movies' if kind=='movie' else 'shows'))

def next_items(hist, future=False):
    today=date.today().isoformat(); out=[]
    for sid,state in sorted(hist.items(),key=lambda x:x[1]['time'],reverse=True)[:50]:
        show=detail('tv/'+str(sid)); seen=state['episodes']
        if future:
            ep=show.get('next_episode_to_air') or {}
            if ep.get('air_date','')>today and ep.get('episode_number'): out.append([sid,ep['season_number'],ep['episode_number'],0])
            continue
        found=False
        for season in sorted(show.get('seasons',[]),key=lambda s:s['season_number']):
            sn=season['season_number']
            if sn<=0 or not season.get('air_date') or season['air_date']>today: continue
            if season.get('episode_count') and sum(s==sn for s,e in seen)>=season['episode_count']: continue
            for ep in detail('tv/%s/season/%s'%(sid,sn)).get('episodes',[]):
                en=ep.get('episode_number'); aired=ep.get('air_date')
                if en and aired and aired<=today and (sn,en) not in seen:
                    out.append([sid,sn,en,0]); found=True; break
            if found: break
    return out

def dropped(source):
    if source=='trakt':
        rows=[]
        for page in range(1,11):
            batch=get(source,'users/hidden/progress_watched',{'type':'show','limit':100,'page':page})
            rows.extend(batch)
            if len(batch)<100: break
    else:
        rows=[]
        for offset in range(0,1000,100):
            data,_=accounts.mdb('sync/dropped',{'mediatype':'show','limit':100,'offset':offset})
            batch=data.get('shows',[]) if isinstance(data,dict) else data
            rows.extend(batch)
            if len(batch)<100: break
    return unique([int(identifier(r.get('show',r))) for r in rows if identifier(r.get('show',r))])

def pool(source,kind,category):
    if source=='simkl':
        from resources.lib import simkl_discovery
        return unique(simkl_discovery.history_refs(kind,category))
    key=category.removeprefix('history_') if hasattr(category,'removeprefix') else category[8:]
    today=date.today().isoformat()
    if key in ('released','anticipated'):
        out=[]
        for ident in watchlist(source,kind)[:200]:
            d=detail(kind+'/'+str(ident)); dt=d.get('release_date' if kind=='movie' else 'first_air_date')
            if dt and ((dt<=today)==(key=='released')): out.append(ident)
        return out
    hist=watched(source,kind)
    recent=sorted(hist,key=lambda i:hist[i]['time'],reverse=True); most=sorted(hist,key=lambda i:hist[i]['plays'],reverse=True)
    if key=='recent': return recent
    if key=='most': return most
    if key.startswith('rec_'):
        out=[]
        for ident in (recent if key=='rec_recent' else most)[:5]:
            out.extend(r['id'] for r in detail('%s/%s/recommendations'%(kind,ident)).get('results',[]) if r.get('id') and r['id'] not in hist)
        return unique(out)
    if key=='dropped':
        return dropped(source)
    if kind=='tv' and key in ('airing','next_episodes','still','current','progress'):
        hidden=set(dropped(source)); hist={i:v for i,v in hist.items() if i not in hidden}
    if key=='airing': return sorted(next_items(hist,True),key=lambda r:detail('tv/%s/season/%s/episode/%s'%tuple(r[:3])).get('air_date',''))
    if key=='next_movies':
        out=[]
        for ident in recent[:50]:
            c=detail('movie/'+str(ident)).get('belongs_to_collection') or {}
            if c.get('id'):
                parts=sorted(detail('collection/'+str(c['id'])).get('parts',[]),key=lambda p:p.get('release_date') or '9999')
                nxt=next((p['id'] for p in parts if p.get('release_date') and p['release_date']<=today and p['id'] not in hist),None)
                if nxt: out.append(nxt)
        return unique(out)
    if key=='next_episodes': return next_items(hist)
    if kind=='tv' and key=='progress':
        # A show-level progress list requires at least one completed episode.
        # Keep paused-only episodes in the episode playback lists instead.
        if source=='trakt':
            started={i:v for i,v in hist.items() if v['episodes']}
            unknown={i:v for i,v in started.items() if not v['aired']}
            fallback=set(r[0] for r in next_items(unknown)) if unknown else set()
            ids=[i for i in recent if i in started and (started[i]['aired']>len(started[i]['episodes']) or i in fallback)]
        else:
            ids=unique([r[0] for r in next_items({i:v for i,v in hist.items() if v['episodes']})])
        return [{'id':i,'episodes':[list(e) for e in sorted(hist[i]['episodes'])],'aired':hist[i]['aired']} for i in ids]
    if key=='still':
        if kind=='movie': return [i for i in watchlist(source,kind) if i not in hist]
        return unique([r[0] for r in next_items(hist)]+[i for i in watchlist(source,kind) if i not in hist and i not in hidden])
    rows=playback(source,kind)
    if key=='progress_unwatched': rows=[r for r in rows if (r[0] not in hist if kind=='movie' else tuple(r[1:3]) not in hist.get(r[0],{}).get('episodes',set()))]
    if kind=='movie' or key in ('progress_episodes','progress_unwatched'): return rows
    if key=='current': return unique([r[0] for r in rows if r[0] not in hidden]+[r[0] for r in next_items(hist)])
    return unique([r[0] for r in rows])

def hydrate(kind,refs,source=None,category=None):
    from resources.lib import TheMovieDB as db, trakt_catalog as cat
    out=[]
    history={}
    if kind=='tv' and source and source!='simkl' and refs and not all(isinstance(ref,dict) for ref in refs):
        try: history=watched(source,kind)
        except Exception:
            import xbmc
            xbmc.log('Diggz Portal: personal show history unavailable during hydration',xbmc.LOGWARNING)
    for ref in refs:
        try:
            ident=ref['id'] if isinstance(ref,dict) else ref[0] if isinstance(ref,list) else ref
            if isinstance(ref,list) and kind=='tv':
                ep=db.extended_episode_info(ident,ref[1],ref[2])[0]; ep['tmdb_id']=ident; ep['title']='%s - S%02dE%02d - %s'%(ep.get('TVShowTitle',''),ref[1],ref[2],ep['title']); row=ep
            else:
                data=cat.hydrate(kind,'personal_list','',[ident]); handler=db.handle_tmdb_movies if kind=='movie' else db.handle_tmdb_tvshows
                if not data: continue
                row=handler(data,sortkey=None)[0]
            if kind=='tv' and not isinstance(ref,list):
                state=ref if isinstance(ref,dict) else history.get(int(ident),{})
                if state.get('episodes'):
                    row['PortalHistoryEpisodes']=[list(e) for e in sorted(state['episodes'])]
                    row['PortalHistoryAired']=state.get('aired',0)
            if isinstance(ref,list) and ref[3]: row['PercentPlayed']=int(ref[3]); row['StartPercent']=int(ref[3])
            row['PortalHistorySource']=source or ''
            out.append(row)
        except Exception:
            import xbmc
            xbmc.log('Diggz Portal: unable to load a personal history item',xbmc.LOGWARNING)
    return out
