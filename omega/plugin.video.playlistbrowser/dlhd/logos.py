"""Country-aware exact-name matching against the public iptv-org logo catalog."""
import json
import os
import re
import time
import difflib
from collections import Counter
from urllib.parse import quote
from urllib.parse import urlsplit
from dlhd import resolver
from dlhd.groups import normalized, details, COUNTRIES

COUNTRY_CODES = dict(zip(
    ('USA','UK','Ireland','Canada','Australia','New Zealand','Germany','Austria','France','Italy','Spain','Portugal','Netherlands','Belgium','Poland','Czechia','Slovakia','Denmark','Sweden','Norway','Finland','Serbia','Croatia','Bulgaria','Romania','Greece','Hungary','Turkey','Russia','Ukraine','Brazil','Mexico','Argentina','Chile','Colombia','India','Pakistan','Bangladesh','Malaysia','South Africa','Saudi Arabia','UAE','Qatar','Israel'),
    ('US','UK','IE','CA','AU','NZ','DE','AT','FR','IT','ES','PT','NL','BE','PL','CZ','SK','DK','SE','NO','FI','RS','HR','BG','RO','GR','HU','TR','RU','UA','BR','MX','AR','CL','CO','IN','PK','BD','MY','ZA','SA','AE','QA','IL')))


def safe_url(value):
    try:
        parsed = urlsplit(value) if isinstance(value,str) else None
        return bool(parsed and parsed.scheme in ('http','https') and parsed.netloc and not any(c in value for c in ('"','\r','\n','<','>')))
    except ValueError:
        return False



def safe_logo_reference(value):
    if safe_url(value):return True
    if not isinstance(value,str) or any(c in value for c in ('"','\r','\n','<','>')):return False
    return value.startswith('special://') or os.path.isabs(value)


def local_bundle(addon_path):
    if not addon_path:return {},None
    folder=os.path.join(addon_path,'resources','logos')
    try:
        with open(os.path.join(folder,'manifest.json'),encoding='utf-8') as stream:data=json.load(stream)
        return data,folder
    except (OSError,ValueError):return {},folder


def local_image(channel,name,profile,bundle,folder):
    # User overrides are outside the installed add-on so updates do not erase them.
    for directory in (os.path.join(profile,'logos'), os.path.join(folder,'custom') if folder else None):
        if directory:
            for extension in ('.png','.jpg','.jpeg','.webp'):
                path=os.path.join(directory,str(int(channel))+extension)
                if os.path.isfile(path):return path,'local custom logo'
    entry=bundle.get('channels',{}).get(str(channel),{})
    if folder and canonical(entry.get('name',''))==canonical(name):
        filename=entry.get('file','')
        if filename and filename==os.path.basename(filename):
            path=os.path.join(folder,filename)
            if os.path.isfile(path):return path,'bundled channel-name tile' if entry.get('placeholder') else 'bundled channel logo'
    return None,None

def canonical(name, strip_country=False):
    value = normalized(name)
    if strip_country:
        for _, pattern in COUNTRIES:
            value = re.sub(pattern, '', value, flags=re.I).strip()
    value = value.replace('&','and').casefold()
    return ''.join(c for c in value if c.isalnum())


def build_index(channels, logos):
    preferred = {}
    for logo in logos:
        if not isinstance(logo,dict) or not safe_url(logo.get('url')):
            continue
        # Prefer current, channel-wide raster logos rather than a regional feed.
        score = (logo.get('in_use') is not False, not logo.get('feed'), str(logo.get('format','')).upper() in ('PNG','JPEG','WEBP'), int(logo.get('width') or 0))
        channel = logo.get('channel')
        if channel not in preferred or score > preferred[channel][0]:
            preferred[channel] = score,logo['url']
    matches = {}
    for channel in channels:
        if not isinstance(channel,dict) or channel.get('closed') or channel.get('id') not in preferred:
            continue
        country = str(channel.get('country','')).upper()
        if country == 'GB': country = 'UK'
        url = preferred[channel['id']][1]
        for name in [channel.get('name','')] + (channel.get('alt_names') or []):
            if not isinstance(name,str): continue
            key = canonical(name)
            if not key: continue
            for scope in (country,'*'):
                matches.setdefault(scope+'|'+key,set()).add((channel['id'],url))
    # Never arbitrarily pick a channel when a name is ambiguous.
    return {key:next(iter(values))[1] for key,values in matches.items() if len(values)==1}


def load_index(profile):
    path = os.path.join(profile,'logo-index.json')
    cached = None
    try:
        with open(path,encoding='utf-8') as stream: cached=json.load(stream)
        if not isinstance(cached,dict) or not isinstance(cached.get('index'),dict): cached=None
        if cached and time.time()-cached.get('at',0) < 7*86400:
            return cached['index'],'cached catalog'
    except (OSError,ValueError,TypeError):
        cached=None
    try:
        channels = json.loads(resolver.fetch('https://iptv-org.github.io/api/channels.json')[0])
        logos = json.loads(resolver.fetch('https://iptv-org.github.io/api/logos.json')[0])
        if not isinstance(channels,list) or not isinstance(logos,list):
            raise ValueError('Invalid logo catalog')
        index = build_index(channels,logos)
        os.makedirs(profile,exist_ok=True)
        temporary = path+'.tmp'
        with open(temporary,'w',encoding='utf-8') as stream:
            json.dump({'at':time.time(),'index':index},stream)
        os.replace(temporary,path)
        return index,'updated catalog'
    except Exception:
        return (cached['index'],'older cached catalog') if cached else ({},'catalog unavailable; no automatic logos')



FAMILIES = (
    (r'^showtime\b', ('Showtime', 'Paramount Plus with Showtime', 'Paramount+ with Showtime')),
    (r'^hbo\b', ('HBO',)),
    (r'^cinemax\b', ('Cinemax',)),
    (r'^starz\b', ('Starz',)),
    (r'^sky cinema\b', ('Sky Cinema',)),
    (r'^sky sports?\b', ('Sky Sports',)),
    (r'^bein sports?\b', ('beIN Sports',)),
    (r'^eurosport\b', ('Eurosport',)),
    (r'^discovery\b', ('Discovery Channel','Discovery')),
    (r'^(?:national geographic|nat geo)\b', ('National Geographic',)),
    (r'^nick(?:elodeon|toons| jr)?\b', ('Nickelodeon',)),
    (r'^disney\b', ('Disney Channel',)),
    (r'^mtv\b', ('MTV',)),
    (r'^espn\b', ('ESPN',)),
    (r'^fox sports\b', ('Fox Sports',)),
    (r'^tnt sports\b', ('TNT Sports',)),
    (r'^dazn\b', ('DAZN',)),
)


def name_keys(name):
    candidates = (name,re.sub(r'\([^)]*\)', '', name))
    return list(dict.fromkeys(canonical(n,strip) for n in candidates for strip in (False,True) if canonical(n,strip)))


def build_backup_index(tree):
    entries = {}
    for item in tree.get('tree',[]):
        path = item.get('path','')
        if item.get('type') != 'blob' or not path.startswith('countries/'):
            continue
        match = re.fullmatch(r'(.+)-([a-z]{2})\.png',os.path.basename(path),re.I)
        if not match: continue
        name,code = match.groups()
        code = code.upper()
        if code=='GB': code='UK'
        key = code+'|'+canonical(name.replace('-',' '))
        url = 'https://raw.githubusercontent.com/tv-logo/tv-logos/main/'+quote(path,safe='/')
        # Prefer the normal country-wide image over duplicates in HD/icon subfolders.
        score = (path.count('/'),len(path),path)
        if key not in entries or score<entries[key][0]:
            entries[key]=(score,url)
    return {key:value[1] for key,value in entries.items()}


def load_backup_index(profile):
    path=os.path.join(profile,'backup-logo-index.json')
    cached=None
    try:
        with open(path,encoding='utf-8') as stream: cached=json.load(stream)
        if not isinstance(cached,dict) or not isinstance(cached.get('index'),dict): cached=None
        if cached and time.time()-cached.get('at',0)<7*86400:
            return cached['index'],'cached backup'
    except (OSError,ValueError,TypeError): cached=None
    try:
        tree=json.loads(resolver.fetch('https://api.github.com/repos/tv-logo/tv-logos/git/trees/main?recursive=1')[0])
        if tree.get('truncated') or not isinstance(tree.get('tree'),list):
            raise ValueError('Incomplete backup logo catalog')
        index=build_backup_index(tree)
        os.makedirs(profile,exist_ok=True)
        with open(path+'.tmp','w',encoding='utf-8') as stream:
            json.dump({'at':time.time(),'index':index},stream)
        os.replace(path+'.tmp',path)
        return index,'updated backup'
    except Exception:
        return (cached['index'],'older cached backup') if cached else ({},'backup unavailable')



def us_network_parents(name):
    value=canonical(re.sub(r'\([^)]*\)','',name),True)
    if value.startswith('nvcny'):value='nbcny'+value[5:]
    if value in ('foxweather','foxweatherchannel'):return ('FOX Weather',)
    for network in ('abc','cbs','cw','fox','nbc'):
        if not value.startswith(network):continue
        suffix=value[len(network):]
        # Deliberate local/affiliate aliases, not arbitrary substring matches.
        if suffix and not re.fullmatch(r'(?:ny|nyc|newyork|philly|philadelphia|pix\d+|wpix|wabc|wcbs|wnbc|wnyw|\d+)',suffix):
            return ()
        if network=='cbs':return ('CBS','CBS logo white','CBS network')
        if network=='cw':return ('CW','The CW')
        return (network.upper(),)
    return ()

def lookup(name,scope,index,backup):
    keys=name_keys(name)
    text=normalized(re.sub(r'\([^)]*\)','',name))
    if scope=='US':
        # Catalog artwork labels can include descriptive color text.
        if canonical(name,True)=='cbs':keys.extend(('cbslogowhite','cbsnetwork'))
        if canonical(name,True)=='foxweatherchannel':keys.append('foxweather')
    # The tv-logo catalog is preferred, including deliberate parent-brand matches.
    # iptv-org is consulted only when the preferred catalog has no such match.
    for catalog,source in ((backup,'preferred'),(index,'fallback')):
        for key in keys:
            url=catalog.get(scope+'|'+key)
            if safe_url(url):return url,source+' exact/alias'
        if scope!='*':
            for pattern,parents in FAMILIES:
                if re.search(pattern,text,re.I):
                    for parent in parents:
                        key=scope+'|'+canonical(parent)
                        if safe_url(catalog.get(key)):
                            return catalog[key],source+' brand fallback'
    # An exact affiliate logo in either source wins before a generic US network logo.
    if scope=='US':
        parents=us_network_parents(name)
        for catalog,source in ((backup,'preferred'),(index,'fallback')):
            for parent in parents:
                url=catalog.get('US|'+canonical(parent))
                if safe_url(url):return url,source+' local network fallback'
    # Conservative typo matching, within one country, preserving numbered feeds.
    if scope!='*':
        combined=dict(index)
        combined.update(backup)
        candidates={k.split('|',1)[1]:v for k,v in combined.items() if k.startswith(scope+'|') and safe_url(v)}
        key=canonical(re.sub(r'\([^)]*\)','',name),True)
        if len(key)>=6:
            ranked=[]
            numbers=re.findall(r'\d+',key)
            for candidate,url in candidates.items():
                if re.findall(r'\d+',candidate)!=numbers:continue
                score=difflib.SequenceMatcher(None,key,candidate).ratio()
                if score>=0.93:ranked.append((score,candidate,url))
            ranked.sort(reverse=True)
            if ranked and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=0.04):
                return ranked[0][2],'similar name'
    return None,'unmatched'


def match_logos(items, profile, addon_path=None, online=True):
    items=list(items)
    bundle,folder=local_bundle(addon_path)
    result,report,pending={},{},[]
    for channel,name in items:
        path,method=local_image(channel,name,profile,bundle,folder)
        if path:
            result[int(channel)]=path
            report[int(channel)]={'id':int(channel),'name':name,'method':method}
        else:pending.append((channel,name))
    status,backup_status='local logo bundle','online lookup not needed'
    index,backup={},{}
    if pending and online:
        index,status=load_index(profile)
        backup,backup_status=load_backup_index(profile)
    for channel,name in pending:
        scope=COUNTRY_CODES.get(details(name)[1],'*')
        url,method=lookup(name,scope,index,backup) if online else (None,'no online lookup')
        if not url and folder:
            generic=os.path.join(folder,'default.png')
            if os.path.isfile(generic):url,method=generic,'generic TV placeholder'
        if url:result[int(channel)]=url
        report[int(channel)]={'id':int(channel),'name':name,'method':method}
    report=list(report.values())
    try:
        with open(os.path.join(profile,'channel_logos.json'),encoding='utf-8') as stream:
            overrides=json.load(stream)
        for channel,url in overrides.items():
            if str(channel).isdigit():
                if safe_logo_reference(url): result[int(channel)]=url
                elif url=='': result.pop(int(channel),None)
                for entry in report:
                    if entry['id']==int(channel):entry['method']='manual override'
    except (OSError,ValueError,TypeError,AttributeError):
        pass
    try:
        with open(os.path.join(profile,'logo-matches.json'),'w',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2)
    except OSError: pass
    counts=Counter(entry['method'] for entry in report)
    summary=', '.join('{} {}'.format(count,method) for method,count in sorted(counts.items()))
    return result,status+'; '+backup_status+'; '+summary
