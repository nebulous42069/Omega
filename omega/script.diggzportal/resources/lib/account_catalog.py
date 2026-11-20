"""MDBList and TMDb personal browsing using existing TMDb hydration."""
from urllib.parse import quote
from resources.lib import accounts


def entries(source,kind):
    noun='Movies' if kind=='movie' else 'TV Shows'
    if source=='tmdb': return [('favorite','Favorite '+noun),('watchlist',noun+' Watchlist'),('rated','Rated '+noun)]
    return [('top','Top Lists'),('curated','Curated Lists'),('official','Official Lists'),('search','Search Lists'),('charts','Streaming Charts')]

def personal_entries(source,kind):
    if source=='tmdb': return entries(source,kind)+[('history_released','Watchlist (Released)'),('history_anticipated','Watchlist (Anticipated)')]
    from resources.lib.personal_history import entries as history_entries
    return [('watchlist','My Watchlist')]+history_entries(kind)+[('user','My Lists'),('liked','Liked Lists'),('watched','My Watched Titles')]

def choose(source,kind,category,label,expand=False,value=''):
    import xbmcgui
    dlg=xbmcgui.Dialog()
    if source=='simkl':
        from resources.lib import simkl_discovery as discovery, simkl_api
        from urllib.parse import unquote_plus
        category=unquote_plus(str(category or ''))
        group,_,selection=category.partition(':')
        needs_account=not group.startswith('public_') or selection in ('search','best','unwatched')
        if needs_account and not accounts.configured(source):
            dlg.ok('SIMKL','Authorize SIMKL first.'); return None
        if group.startswith('custom_') and selection!='items':
            media=group[7:]
            try:
                if selection=='id':
                    discovery.require_premium()
                    entered=dlg.input('SIMKL Custom List ID').strip()
                    if not entered: return None
                    if not entered.isdigit() or not simkl_api.positive(entered): raise simkl_api.SimklError('Custom Lists',reason='Invalid list ID')
                    return group+':items',entered,'SIMKL List '+entered
                uid=None
                if selection=='user':
                    uid=dlg.input('SIMKL User ID').strip()
                    if not uid: return None
                    if not uid.isdigit() or not simkl_api.positive(uid): raise simkl_api.SimklError('Custom Lists',reason='Invalid user ID')
                options=discovery.custom_choices(media,selection,uid)
                if not options:
                    dlg.ok('SIMKL','No matching custom lists.'); return None
                if expand: return [(group+':items',v,n) for v,n in options]
                i=dlg.select(label,[n for _,n in options])
                if i<0: return None
                ident,name=options[i]; return group+':items',ident,name
            except Exception as exc:
                simkl_api.log_failure('custom list selection',exc)
                dlg.ok('SIMKL',str(exc) if isinstance(exc,simkl_api.SimklError) else 'Unable to retrieve custom lists. See kodi.log.'); return None
        if selection=='search' and group.startswith('public_') and not value:
            value=dlg.input('Search SIMKL').strip()
            if not value: return None
            label='Search SIMKL: '+value
        return category,str(value or ''),label
    if not accounts.configured(source):
        dlg.ok(source.upper(),'Authorize this service in Accounts settings first.'); return None
    if category.startswith('history_'): return category,'',label
    if source=='tmdb' or category in ('watchlist','watched'): return category,'',label
    if category=='charts':
        if expand: return [('charts',str(v),n) for v,n in zip((1,7,30),('Today','This Week','This Month'))]
        i=dlg.select('Streaming Charts',['Today','This Week','This Month'])
        return (category,str((1,7,30)[i]),label) if i>=0 else None
    params={}
    if category=='search':
        text=dlg.input('Search MDBList lists').strip()
        if not text: return None
        params['query']=text
    if category=='official': params['mediatype']='movie' if kind=='movie' else 'show'
    if category=='liked':
        rows=[]
        for page in range(20):
            data,_=accounts.mdb('lists/liked',{'limit':100,'offset':page*100})
            batch=data.get('lists',[]) if isinstance(data,dict) else data
            rows.extend(batch)
            if len(batch)<100: break
    else:
        data,_=accounts.mdb('lists/'+category,params)
        rows=data.get('lists',[]) if isinstance(data,dict) else data
    options=[(str(r.get('slug') if category=='official' else r.get('id')),r.get('name','List')) for r in rows if isinstance(r,dict) and (r.get('slug') if category=='official' else r.get('id'))]
    if expand: return [('official_items' if category=='official' else 'items',v,n) for v,n in options]
    i=dlg.select(label,[n for _,n in options]) if options else -1
    if i<0: return None
    value,name=options[i]; return ('official_items' if category=='official' else 'items',value,name)

def pool(source,kind,category,value):
    if source=='simkl':
        from resources.lib import simkl_api
        return simkl_api.pool(kind,category,value)
    if source=='tmdb':
        a=accounts.addon(); path='account/'+a.getSetting('tmdb_account')+'/'+category+'/'+('movies' if kind=='movie' else 'tv')
        out=[]
        for page in range(1,101):
            data=accounts.tmdb(path,{'session_id':a.getSetting('tmdb_session'),'page':page,'language':'en-US'})
            out.extend(r['id'] for r in data.get('results',[]))
            if page>=data.get('total_pages',1): break
        return list(dict.fromkeys(out))
    media='movie' if kind=='movie' else 'show'; rows=[]
    if category=='watched':
        data=accounts.mdb_pages('sync/watched',{'mediatype':'movie' if kind=='movie' else 'episode'},'movies' if kind=='movie' else 'episodes')
        return list(dict.fromkeys(r.get('movie',r).get('ids',{}).get('tmdb') if kind=='movie' else r.get('episode',{}).get('show',{}).get('ids',{}).get('tmdb') for r in data if isinstance(r,dict)))
    if category=='watchlist': rows=accounts.mdb_pages('watchlist/items',{'mediatype':media},media+'s')
    elif category=='charts':
        data,_=accounts.mdb('justwatch/streaming-charts/'+media,{'rank':value}); rows=[r for r in data.get('results',[]) if r.get('matched')]
    else:
        path=('lists/official/' if category=='official_items' else 'lists/')+quote(value,safe='')+'/items'
        for page in range(20):
            data,h=accounts.mdb(path,{'unified':'true','mediatype':media,'limit':100,'offset':page*100})
            batch=data.get('items',[]) if isinstance(data,dict) else data
            if not isinstance(batch,list): raise RuntimeError('Unexpected MDBList list response')
            rows.extend(batch)
            if len(batch)<100 or (h.get('X-Total-Items') and len(rows)>=int(h['X-Total-Items'])): break
    out=[]
    for row in rows:
        item=row.get(media,row)
        if item.get('mediatype',item.get('type',media)) not in (media,kind): continue
        ident=item.get('ids',{}).get('tmdb') or item.get('tmdb_id') or (item.get('id') if category!='charts' else None)
        if ident and str(ident).isdigit(): out.append(int(ident))
    return list(dict.fromkeys(out))
