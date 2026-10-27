"""USA/UK exact and alias mapping to EPGTalk; never substitute a parent network schedule."""
import io
import json
import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
import zlib
from dlhd import resolver
from dlhd.groups import details,normalized,display_name,COUNTRIES

GUIDE_URL='https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/guide.xml.gz'
COUNTRY_URLS={c:'https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/'+c+'_lite.xml.gz' for c in ('US','UK')}
MAX_XML=96*1024*1024


def channel_records(data):
    if data.startswith(b'\x1f\x8b'):
        decoder=zlib.decompressobj(31)
        data=decoder.decompress(data,MAX_XML+1)
        if len(data)>MAX_XML or decoder.unconsumed_tail or not decoder.eof:
            raise ValueError('EPG file is oversized or incomplete')
    if len(data)>MAX_XML:raise ValueError('EPG file exceeds size limit')
    result={}
    root=None
    for event,node in ET.iterparse(io.BytesIO(data),events=('start','end')):
        if root is None:
            root=node
            if root.tag!='tv':raise ValueError('Guide response is not XMLTV')
        if event=='end' and node.tag=='channel':
            ident=node.get('id','')
            names=[n.text.strip() for n in node.findall('display-name') if n.text and n.text.strip()]
            if ident and names:result[ident]=names
            node.clear()
        elif event=='start' and node.tag=='programme':
            # XMLTV puts channel definitions before programmes. No schedule data is needed here.
            break
    if not result:raise ValueError('EPG contains no channel definitions')
    return result


def key(name,strip_country=False):
    value=normalized(name)
    value=re.sub(r'^\d+\s+','',value)
    value=re.sub(r'^(?:UK|US|USA)\s*[-:]\s*','',value,flags=re.I)
    if strip_country and not re.fullmatch(r'5 USA',value,re.I):
        for _,pattern in COUNTRIES:value=re.sub(pattern,'',value,flags=re.I).strip()
    value=value.casefold().replace('&','and').replace('+','plus')
    value=re.sub(r'\s+(?:channel|tv)$','',value)
    value=re.sub(r'^c[ -]?span\s*1$','cspan',value)
    value=re.sub(r'\bbbc\s+(one|two|three|four)\b',lambda m:'bbc '+{'one':'1','two':'2','three':'3','four':'4'}[m.group(1)],value)
    return ''.join(c for c in value if c.isalnum())


def keys(name,strip_country=False):
    candidates=[name]
    if not re.search(r'\([^)]*\b(?:Pacific|West|Eastern|East)\b',name,re.I):
        candidates.append(re.sub(r'\([^)]*\)','',name))
    return list(dict.fromkeys(k for n in candidates if (k:=key(n,strip_country)) and not k.isdigit()))


def build_catalog(combined,us,uk):
    result=[]
    def station(ident):
        found=re.fullmatch(r'I\d+\.(\d+)\.(?:gracenote\.com|schedulesdirect\.org)',ident)
        return found.group(1) if found else ident
    memberships={c:{station(i) for i in records} for c,records in (('USA',us),('UK',uk))}
    for ident,names in combined.items():
        countries=[c for c in ('USA','UK') if station(ident) in memberships[c]]
        # Explicit UK labels/brands cover channels absent from the public UK lite lineup.
        if not countries and not re.search(r'Latin|Mexico|México|Argentina',' '.join(names),re.I):
            if any(re.match(r'^(?:\d+\s+)?UK\s*[-:]',n,re.I) for n in names) or re.match(r'^(?:Sky (?:Sports|Cinema|Arts|Max|Showcase)|BBC (?:One|Two|Three|Four)|ITV|S4C|E4|Film4)\b',names[0],re.I):
                countries=['UK']
            elif re.search(r'\b(?:US|USA)\b',names[0],re.I):countries=['USA']
        if not countries:continue
        primary=names[0]
        aliases={}
        for pos,name in enumerate(names):
            if name.isdigit():continue
            for k in keys(name,True):aliases[k]=max(aliases.get(k,0),100 if pos==0 else 90)
        if countries[0]=='USA':
            # General US feed names conventionally use the East feed. Explicit West names stay distinct.
            east=re.sub(r'\s+(?:East|Eastern)(?:\s+HD)?$','',primary,flags=re.I)
            if east!=primary:
                for k in keys(east,True):aliases[k]=max(aliases.get(k,0),96)
        for country in countries:
            result.append({'id':ident,'country':country,'name':primary,'keys':aliases,'hd':bool(re.search(r'\bHD\b',' '.join(names),re.I)),'feed':re.sub(r'(?:east|eastern)$','',key(primary,True)),'slot':(re.match(r'^(I[0-9.]+)\.[0-9]+\.(?:gracenote\.com|schedulesdirect\.org)$',ident).group(1) if re.match(r'^(I[0-9.]+)\.[0-9]+\.(?:gracenote\.com|schedulesdirect\.org)$',ident) else re.sub(r'(?:east|eastern)$','',key(primary,True)))})
    if not result:raise ValueError('EPGTalk country guides do not match the combined guide')
    return result


def load_catalog(folder):
    path=os.path.join(folder,'epgtalk-index.json')
    cached=None
    try:
        with open(path,encoding='utf-8') as stream:cached=json.load(stream)
        if not isinstance(cached,dict) or cached.get('schema')!=1 or not isinstance(cached.get('records'),list):cached=None
        if cached and time.time()-cached.get('at',0)<86400:return cached['records'],'cached EPGTalk mapping'
    except (OSError,ValueError,TypeError):cached=None
    try:
        combined=channel_records(resolver.fetch(GUIDE_URL)[0])
        us=channel_records(resolver.fetch(COUNTRY_URLS['US'])[0])
        uk=channel_records(resolver.fetch(COUNTRY_URLS['UK'])[0])
        records=build_catalog(combined,us,uk)
        os.makedirs(folder,exist_ok=True)
        temporary=path+'.'+uuid.uuid4().hex+'.tmp'
        with open(temporary,'w',encoding='utf-8') as stream:json.dump({'schema':1,'at':time.time(),'records':records},stream)
        os.replace(temporary,path)
        return records,'updated EPGTalk mapping'
    except Exception:
        if cached:return cached['records'],'older cached EPGTalk mapping'
        raise ValueError('Cannot download EPGTalk mapping. Existing M3U retained; retry later or disable EPG matching.')


def match(items,records,overrides=None):
    mapped={};report=[]
    by_key={}
    by_id={(r['country'],r['id']):r for r in records}
    for record in records:
        for k,score in record['keys'].items():
            by_key.setdefault((record['country'],k),[]).append((score,record))
    for channel,name in items:
        country=details(name)[1]
        selected=None;method='not USA/UK'
        if country in ('USA','UK'):
            candidates={}
            for order,k in enumerate(keys(name,True)):
                for score,record in by_key.get((country,k),[]):
                    rank=score-order
                    old=candidates.get(record['id'])
                    if not old or rank>old[0]:candidates[record['id']]=(rank,record)
            ranked=sorted(candidates.values(),key=lambda x:(-x[0],not x[1]['hd'],x[1]['id']))
            method='unmatched'
            if ranked:
                best=ranked[0]
                rivals=[r for r in ranked if r[0]>=best[0]-2 and r[1]['feed']!=best[1]['feed'] and (not r[1].get('slot') or r[1].get('slot')!=best[1].get('slot'))]
                if not rivals:
                    selected=best[1];method='default East feed' if 92<=best[0]<=96 else 'exact/alias'
                else:method='ambiguous; manual mapping needed'
        override=(overrides or {}).get(str(channel))
        if not isinstance(override,str):override=None
        if override=='':selected=None;method='disabled by override'
        elif override and (country,override) in by_id:
            selected=by_id[(country,override)];method='manual mapping'
        if selected:
            mapped[int(channel)]={'id':selected['id'],'name':selected['name']}
        report.append({'channel_id':int(channel),'channel_name':display_name(name),'country':country,'epg_id':selected['id'] if selected else '', 'epg_name':selected['name'] if selected else '', 'method':method})
    return mapped,report


def map_channels(items,folder):
    records,status=load_catalog(folder)
    overrides={}
    try:
        with open(os.path.join(folder,'epg-overrides.json'),encoding='utf-8') as stream:overrides=json.load(stream)
        if not isinstance(overrides,dict):overrides={}
    except (OSError,ValueError):pass
    mapped,report=match(items,records,overrides)
    os.makedirs(folder,exist_ok=True)
    with open(os.path.join(folder,'epg-matches.json'),'w',encoding='utf-8') as stream:json.dump(report,stream,indent=2,ensure_ascii=False)
    return mapped,status
