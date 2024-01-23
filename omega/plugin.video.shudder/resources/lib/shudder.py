# coding: UTF-8
import ast
import sys, re

import requests
import routing

from .helper import Helper


base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = Helper(base_url, handle)
plugin = routing.Plugin()

try:
    # Python 3
    from urllib.parse import quote_plus, unquote_plus, quote, unquote
except:
    # Python 2.7
    from urllib import quote_plus, unquote_plus, quote, unquote
    
@plugin.route('/')
def root():

    if helper.logged:

        helper.add_item('[COLOR orangered][B]Series[/COLOR][/B]', plugin.url_for(listpage, 'series'),folder=True)
        helper.add_item('[COLOR orangered][B]Movies[/COLOR][/B]', plugin.url_for(listmovies, page = 0),folder=True)        
        helper.add_item('[COLOR orangered][B]Live TV[/COLOR][/B]', plugin.url_for(listcontent, 'shudder-tv'),folder=True)
        helper.add_item('[COLOR orangered][B]Search[/COLOR][/B]', plugin.url_for(listsearch),folder=True)
        
        helper.add_item('[COLOR orangered][B]-=Log Out=-[/COLOR][/B]', plugin.url_for(logout),folder=False)
    else:
        helper.add_item('[COLOR orangered][B]Log In[/COLOR][/B]', plugin.url_for(login),folder=False)
    
    helper.add_item('[COLOR orangered][B]Settings[/COLOR][/B]', plugin.url_for(ustawienia),folder=False)

    helper.eod()

@plugin.route('/mylist')    
def mylist():
    url = helper.base_api_url.format('my-list')
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)

    for item in jsdata:

        title = item.get('title', None)
        info = CreateInfo(item)
        art,imag,fanart = getArts(item)
        links = item.get('links', None).get('detail', None)
        if '/series/' in links:
            ispla = False
            mod = plugin.url_for(listcollect, id=quote_plus(links))
        else:
            ispla = True
            href = (item.get('links', None).get('play', None)).replace('/play/','playlist/')
            mod = plugin.url_for(playvid, mpd_url=quote_plus(href), widevine_url = 'xx')

        helper.add_item(title, mod, playable=ispla, info=info, art=art) 

    helper.eod()
    
@plugin.route('/listmovies/<page>')    
def listmovies(page):
    page = str(page)
    url = helper.main_url.format('movies?size=30&start='+page)

    helper.headers.update({'accept': 'application/json','content-type': 'application/json'})

    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    for item in jsdata.get('movies' , None):
        _id = item.get('id', None)
        title = item.get('title', None)
        info = CreateInfo(item)

        art,imag,fanart = getArts(item)
        mpd_url = 'playlist/'+_id
        widevine_url = 'xx'
        mod = plugin.url_for(playvid, mpd_url=quote_plus(mpd_url),widevine_url = quote_plus(widevine_url))
        fold = False
        ispla = True
        
        helper.add_item(title, mod, playable=ispla, info=info, art=art)    
    if jsdata.get('hasMoreMovies', None):
        helper.add_item('[COLOR orangered]>> Next Page >>[/COLOR]', plugin.url_for(listmovies, page = int(page)+30),folder=True)
    helper.eod()

@plugin.route('/listpage/<id>')    
def listpage(id):
    url = helper.main_url.format(id)
    html = helper.request_sess(url, 'get', headers=helper.headers, json=False)

    div = 'div class="series-list-container__tile'
    if 'collect' in id:
        div = 'collection-title'
    ids = [(a.start(), a.end()) for a in re.finditer(div, html)]
    ids.append( (-1,-1) )
    out=[]

    for i in range(len(ids[:-1])):
        item = html[ ids[i][1]:ids[i+1][0] ]

        _id = re.findall('a href="([^"]+)"',item, re.DOTALL)
        _id = quote_plus(_id[0]) if _id else ''
        imag = re.findall('data\-src="([^"]+)"',item, re.DOTALL)[0]
        imag = imag.split('?')[0]+'?w=1920&h=1080'

        if 'collect' in id:
            title = re.findall('>([^<]+)<\/a',item,re.DOTALL)[0].replace('\n','').replace('\t','')
            description =re.findall('collection\-description">([^<]+)<',item,re.DOTALL)[0].replace('\n','').replace('\t','').replace('&#039;',"'")
        else:
            title = re.findall('>([^<]+)<\/h5',item, re.DOTALL)[0]
            description = title

        mod = plugin.url_for(listcollect, id=_id)

        ispla = False
        info = {'title': title, 'plot':description}
        art = {'icon': imag, 'fanart': imag}
        helper.add_item(title, mod, playable=ispla, info=info, art=art)    
        
    helper.eod()

@plugin.route('/listcollect/<id>')    
def listcollect(id):
    out=[]
    id = unquote_plus(id)

    id = id[1:] if id.startswith('/') else id

    url = helper.main_url.format(id)
    html = helper.request_sess(url, 'get', headers=helper.headers, json=False).replace('\n\t',' ').replace('\t','')
    
    if 'collections/' in url:
        if '/watch/' in url:
            result = helper.parseDOM(html,'div',attrs = {'class':"collection-list"})[0] 

            ids = [(a.start(), a.end()) for a in re.finditer('<a h', result)]
            ids.append( (-1,-1) )


            for i in range(len(ids[:-1])):
                item = result[ ids[i][1]:ids[i+1][0] ]
                href = re.findall('ref="([^"]+)"',item,re.DOTALL)[0]
                fanart =re.findall('data\-src="(.*?)"',item,re.DOTALL)[0]
                title = helper.parseDOM(item,'h5')[0]
                description  =  helper.parseDOM(item,'p',attrs = {'class':"movie-card__desc"})[0]
                data_id = re.findall('data\-video\-id="([^"]+)"',item,re.DOTALL)[0]
                if '/movies/' in href:
                    _id = 'playlist/'+data_id
                    mod = plugin.url_for(playvid, mpd_url=quote_plus(_id), widevine_url = 'xx')
                    ispla = True
                else:

                    ispla = False
                    mod = plugin.url_for(listcollect, id=quote_plus(href))

                info = {
                    'title': title,
                    'plot':description
                }
            
                art = {
                    'icon': fanart,
                    'fanart': fanart,
                }
                helper.add_item(title, mod, playable=ispla, info=info, art=art) 
            #acv =''
        else:
            for item in helper.parseDOM(html,'div',attrs = {'class':"collection-tile"}):  # = <div class="collection-tile">

                _id = helper.parseDOM(item, 'a', ret='href')[0]
                fanart =re.findall('data\-src="(.*?)"',item,re.DOTALL)[0]

                title =  helper.parseDOM(item,'h4',attrs = {'class':"collection-tile__title"})[0]# <h4 class="collection-tile__title">
                description  =  helper.parseDOM(item,'p',attrs = {'class':"collection-tile__description"})[0] #<p class="collection-tile__description">F

                try:
                    numb = helper.parseDOM(item,'div',attrs = {'class':"collection-tile__number"})[0]
                except:
                    numb = ''
                title = title+' [[COLOR orangered]%s[/COLOR]]'%(str(numb))
                mod = plugin.url_for(listcollect, id=quote_plus(_id))
                ispla = False
                info = {
                    'title': title,
                    'plot':description
                }
            
                art = {
                    'icon': fanart,
                    'fanart': fanart,
                }
            
                helper.add_item(title, mod, playable=ispla, info=info, art=art)   

    else:
        fanart =re.findall('background-image: url\((.*?)\)"',html,re.DOTALL)[0]
        
        mainimage = re.findall('img src="([^"]+)"',helper.parseDOM(html,'div',attrs = {'class':"detail-page__poster"})[0],re.DOTALL)[0]# div class="detail-page__poste
        maindescription = helper.parseDOM(html,'p',attrs = {'class':"detail-page__description"})[0]#<p class="detail-page__description">
        title = helper.parseDOM(html,'h1')[0]

        seasons = re.findall('<ul id="season-key"(.*?)<\/ul>', html, re.DOTALL)[0]
        for sesnumber in re.findall('data\-season\-num="(.*?)"',seasons,re.DOTALL):

            episodes = helper.parseDOM(html,'div',attrs = {'id':"season-%s"%(sesnumber)})
            for epis in helper.parseDOM(episodes,'div',attrs = {'class':"season-list__item"}):
                _id = helper.parseDOM(epis, 'a', ret='href')[0]
                
                _id = _id.replace('/play/','playlist/')
                imag = helper.parseDOM(epis, 'img', ret='src')[0]
                
                
                
                try:
                    episnumber = re.findall('(\d+)',helper.parseDOM(epis, 'img', ret='alt')[0],re.DOTALL)[0]
                except:
                    imgalt = helper.parseDOM(epis, 'img', ret='alt')[0].lower()
                    if 'part' in imgalt:
                        pp = re.findall('part\s+(\w+)',imgalt,re.DOTALL+re.I)

                        dicts = {'one':'1','two':'2','three':'3','four':'4', 'five':'5', 'six':'6', 'seven':'7','eight':'8','nine':'9','ten':'10'}
                        episnumber = dicts.get(pp[0], None)
                description = re.findall('<p>([^<]+)<',epis,re.DOTALL)[0]
                
                epistitle =  helper.parseDOM(epis,'h2',attrs = {'class':"episode-details__title"})[0]

                jaki = ' - S%02dE%02d '%(int(sesnumber),int(episnumber))+' - [COLOR orangered][B]'+epistitle+'[/B][/COLOR]'
                
                tyt = title+jaki
                out.append({'title':tyt,'href':_id,'img':imag, 'fnrt':fanart, 'plot':description, 'season' : int(sesnumber),'episode' : int(episnumber) })
        
        
        sezony =  splitToSeasons(out)
        for i in sorted(sezony.keys()):
        
            mod = plugin.url_for(listEpisodes2, exlink=quote_plus(str(sezony[i])))
            ispla = False
            info = {
                'title': i,
                'plot':maindescription
            }
        
            art = {
                'icon': mainimage,
                'fanart': fanart,
            }
        
            helper.add_item(i, mod, playable=ispla, info=info, art=art)    
    
    helper.eod()
        
@plugin.route('/listEpisodes2/<exlink>')
def listEpisodes2(exlink):

    episodes = ast.literal_eval(unquote_plus(exlink))
    
    itemz=episodes
    items = len(episodes)
    
    for f in itemz:
    
        ispla = True
        href = f.get('href', None)

        mod = plugin.url_for(playvid, mpd_url=quote_plus(href), widevine_url = 'xx')
        info = {
            'title': f.get('title'),
            'plot': f.get('plot'),
            'season' : f.get('season'),
            'episode' : f.get('episode')
        }
        art = {
            'icon': f.get('img'),
            'fanart': f.get('fnrt'),
        }
    
        helper.add_item(f.get('title'), mod, playable=ispla, info=info, art=art)    
    
    helper.eod()
        
        
        
def splitToSeasons(input):
    out={}
    seasons = [x.get('season') for x in input]

    xx= re.findall('^(.*?)\-',input[0].get('title', None))[0]
    for s in set(seasons):

        out[xx+ ' Season %02d'%s]=[input[i] for i, j in enumerate(seasons) if j == s]
    return out

@plugin.route('/listcontent/<id>')    
def listcontent(id):
    url = helper.base_api_url.format(id)
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    for item in jsdata:
        _id = str(item.get("id", None))
        title = item.get("title", None)
        thumbnail = item.get('thumbnail', None)

        mod = plugin.url_for(listcontent2, id=quote_plus(id+'/'+_id))
        fold = True
        ispla = False
        info = {'title': title}
        art = {'icon': thumbnail, 'fanart': helper.addon.getAddonInfo('fanart')}
        helper.add_item(title, mod, playable=ispla, info=info, art=art)    
    helper.eod()
    
def CreateInfo(video_data):
    title = video_data.get('title', None)

    description = video_data.get('description', None).get("long", None)
    try:
        duration = video_data.get('duration', None).get("seconds", None)
    except:
        duration = ''

    year = video_data.get('year', None)
    year = year if year else ''
    country = video_data.get('origin', None)
    country = country if country else ''

    info = {'title': title, 'plot':description, 'year':year, 'country':country}
    if duration:
        info.update({'duration':duration})
    return info
    
def getArts(video_data):
    fanart=None
    imag=None
    images = video_data.get("images", None)
    thumbnail = images.get('thumbnail', None)
    #thumbnail = thumbnail.split('?')[0]+'?w=1080&h=720'
    fanart = images.get('boxArt', None)
    #fanart = fanart.split('?')[0]+'?w=1080&h=720'
    masthead = images.get('masthead', None)
    #masthead = masthead.split('?')[0]+'?w=1080&h=720'

    art = {'icon': thumbnail, 'fanart': masthead}
    return art, imag, fanart
    
    
@plugin.route('/listcontent2/<id>')    
def listcontent2(id):
    url = helper.base_api_url.format(unquote_plus(id))
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    video_data = jsdata.get("video", None)
    title = video_data.get('title', None)
    info = CreateInfo(video_data)

    art,imag,fanart = getArts(video_data)

    stream_data = jsdata.get("stream", None)
    mpd_url = ''
    widevine_url = ''

    for ss in stream_data.get("sources", None):
        if 'dash+xml' in ss.get('type', None):
            mpd_url = ss.get("src", None)
            widevine_url = ss.get("keySystems", None).get("com.widevine.alpha", None).get('licenseUrl', None)
            break
    
    
    
    mod = plugin.url_for(playvid, mpd_url=quote_plus(mpd_url),widevine_url = quote_plus(widevine_url))
    fold = False
    ispla = True
    
    helper.add_item(title, mod, playable=ispla, info=info, art=art)    
    helper.eod()
 
@plugin.route('/listsearch')
def listsearch():
    query = helper.input_dialog('Search...')
    if len(query)>2:
        query =quote_plus(query)
        url ='https://www.shudder.com/api/search/videos?q={}&field=title'.format(query)
        jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
        for x in jsdata:
        
            title = x.get('title', None)
            thumbnail = x.get('image', None)
            art = {'icon': thumbnail, 'fanart': helper.addon.getAddonInfo('fanart')}
            info = {'title': title, 'plot':title}
            
            if x.get("videoType", None) == 'movie':
                fold = False
                ispla = True
                _id = x.get("links", None).get('play', None)
                mpd_url = _id.replace('/play/','playlist/')
                widevine_url = 'xx'
                mod = plugin.url_for(playvid, mpd_url=quote_plus(mpd_url),widevine_url = quote_plus(widevine_url))

            elif x.get("videoType", None) == 'series':

                ispla = False
                _id   = x.get("links", None).get('detail', None)

                title = title+' [COLOR orangered] (series) [/COLOR]'

                mod = plugin.url_for(listcollect, id=quote_plus(_id))
            
            helper.add_item(title, mod, playable=ispla, info=info, art=art)  
        if jsdata:
            helper.eod()
    else:
        helper.notification('Info', '3 characters min.')

@plugin.route('/ustawienia')
def ustawienia():
    helper.open_settings()
    helper.refresh()


@plugin.route('/logout')
def logout():
    log_out = helper.dialog_choice('Warning','Do you want to log out?',agree='YES', disagree='NO')
    if log_out:
        helper.save_file(file=helper.datapath+'kukis', data={}, isJSON=True)    
        helper.set_setting('logged', 'false')
        helper.refresh()
        
@plugin.route('/login')
def login():

    if not helper.username or not helper.password:
        helper.notification('Info', 'No credentials')

        helper.set_setting('logged', 'false')
    else:
        url = helper.main_url.format('member')
        html = helper.request_sess(url, 'get', headers=helper.headers, json=False)
        csrf = re.findall('csrf-token"\s*content\s*=\s*"([^"]+)"',html,re.DOTALL)#[0]

        if not csrf:
            if 'we are not available' in html:
                helper.notification('Information', html)
            else:
                helper.notification('Information', "Something's gone wrong")
            helper.set_setting('logged', 'false')
            
        else:
            helper.headers.update({'csrf-token':csrf[0]})
            json_data = {
                'email': helper.username,
                'password': helper.password,}

            jsdata = helper.request_sess(helper.auth_url, 'post', headers=helper.headers, data = json_data, json=True, json_data = True)
            if "user" in jsdata:
                abc = helper._sess.cookies
                helper.save_file(file=helper.datapath+'kukis', data=(abc).get_dict(), isJSON=True)    
                helper.set_setting('logged', 'true')
            else:
                message = jsdata.get('message', None)
                helper.notification('Information', message)

    helper.refresh()


@plugin.route('/playvid/<mpd_url>/<widevine_url>')
def playvid(mpd_url,widevine_url):
    mpd_url = unquote_plus(mpd_url)
    widevine_url = unquote_plus(widevine_url)

    if 'playlist/' in mpd_url:
        url = helper.base_api_url.format(mpd_url)

        jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
        stream_data = jsdata.get("stream", None)
        mpd_url = ''
        widevine_url = ''

        for ss in stream_data.get("sources", None):
            if 'dash+xml' in ss.get('type', None):
                mpd_url = ss.get("src", None)
                widevine_url = ss.get("keySystems", None).get("com.widevine.alpha", None).get('licenseUrl', None)
                break

    subt=[]
    lic_url =  widevine_url+"|Content-Type=application/octet-stream|R{SSM}|"#%(urlencode(headers3),data)
    PROTOCOL = 'mpd'
    DRM = 'com.widevine.alpha'
    helper.PlayVid(mpd_url, lic_url, PROTOCOL, DRM, flags=False, subs = subt)


class Shudder(Helper):
    def __init__(self):
        super().__init__()
        plugin.run()


