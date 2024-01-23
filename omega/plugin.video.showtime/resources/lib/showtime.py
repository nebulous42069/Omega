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
        helper.add_item('[COLOR gold][B]Series[/COLOR][/B]', plugin.url_for(listcontent, 'series'),folder=True)
        
        helper.add_item('[COLOR gold][B]Movies[/COLOR][/B]', plugin.url_for(listsubmenu, "Movies"),folder=True)
        
        helper.add_item('[COLOR gold][B]Collections[/COLOR][/B]', plugin.url_for(listcollections),folder=True)
        
        helper.add_item('[COLOR gold][B]Sports[/COLOR][/B]', plugin.url_for(listsubmenu, 'Sports'),folder=True)
        helper.add_item('[COLOR gold][B]Comedy[/COLOR][/B]', plugin.url_for(listsubmenu, 'Comedy'),folder=True)
        helper.add_item('[COLOR gold][B]Documentaries[/COLOR][/B]', plugin.url_for(listsubmenu, 'Documentaries'),folder=True)
        helper.add_item('[COLOR gold][B]Live TV[/COLOR][/B]', plugin.url_for(mylist),folder=True)
        
        
        helper.add_item('[COLOR gold][B]-=Log Out=-[/COLOR][/B]', plugin.url_for(logout),folder=False)
    else:
        helper.add_item('[COLOR gold][B]Log In[/COLOR][/B]', plugin.url_for(login),folder=False)
    
    helper.add_item('[COLOR gold][B]Settings[/COLOR][/B]', plugin.url_for(ustawienia),folder=False)

    helper.eod()


@plugin.route('/listcollections')    
def listcollections():    

    zz=''
    jsdata = helper.request_sess('https://www.showtime.com/api/collections', 'get', headers=helper.headers, json=True)

    for item in jsdata:
        _id = item.get('id', None)
        name = item.get('name', None)
        description = item.get('description', None)
        images = item.get('images', [])

        for im in images:
            thumbnail = None
            fanart = None

            if im.get('type', None) == 'COLLECTION_FEED_DISPLAY':
                thumbnail = im.get('url', None)
            elif im.get('type', None) ==  'COLLECTION_ALL_DISPLAY':
                fanart = im.get('url', None)
                #if '00h' in  fanart:
                #    fanart = fanart.replace('00h','00')
            else:
                continue

            if not thumbnail or not fanart:
                if images:
                    thumbnail = images[0].get('url', None)
                    fanart = images[0].get('url', None)
                else:
                    thumbnail = helper.addon.getAddonInfo('icon')
                    fanart = helper.addon.getAddonInfo('fanart')

        idx = quote_plus('mixed/collections/%s'%str(_id))
        mod = plugin.url_for(listcateg, id=idx, page = 1)
    
            
        info = {'title': name, 'plot':description}
        art={'icon':thumbnail, 'fanart':fanart}
        helper.add_item(name, mod, playable=False, info=info, art=art, folder=True) 
    
    
    helper.eod()

@plugin.route('/listsubmenu/<typ>')    
def listsubmenu(typ):    
    typ = unquote_plus(typ)
    jsdata = helper.request_sess('https://www.showtime.com/api/menu', 'get', headers=helper.headers, json=True)
    
    zz=''
    for subm in jsdata:
        if subm.get('name', None) == typ:

            break
    
    for menuitem in subm.get('menuItems', None):

        type = menuitem.get('type', None)
        if 'category' in type.lower() or 'SERIES_LIST' == type:
            _id = str(menuitem.get('id', None))
            name = menuitem.get('name', None)
            fold = True
            ispla = False

            idx = quote_plus('titles/collections/%s'%str(_id))
            if 'SERIES_LIST' == type:
                idx = quote_plus('mixed/collections/%s'%str(_id))
            mod = plugin.url_for(listcateg, id=idx, page = 1)
            
                
            info = {'title': name, 'plot':name}
            art={'icon':helper.addon.getAddonInfo('icon'), 'fanart':helper.addon.getAddonInfo('fanart')}
            helper.add_item(name, mod, playable=ispla, info=info, art=art, folder=fold) 
            
    helper.eod()

@plugin.route('/listcateg/<id>/<page>')    
def listcateg(id,page):

    id = unquote_plus(id)

    nturl = id+'/page/'+str(page)
    url = helper.base_api_url.format(nturl)
    
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    pagecount = jsdata.get('pageCount', None)
    if 'mixed/collections/' in id:
        for item in jsdata.get('items', []):
            typ = item.get('type', None)
            if typ.lower() == 'series':
                name = item.get('name', None)
                releaseYear  = item.get('releaseYear', None)
                _id = str(item.get('id', None) )
                thumbnail = item.get('images',None)[0].get('url', None)
                description = item.get('description', None).get('long', None)
                info = {'title': name, 'plot':description, 'year':releaseYear}
                art={'icon':thumbnail, 'fanart':helper.addon.getAddonInfo('fanart')}
                fold = True
                ispla = False
                
                mod = plugin.url_for(listcontent2, id=quote_plus('series/'+_id)) 
                helper.add_item(name, mod, playable=ispla, info=info, art=art, folder=fold) 
            else:
                if typ.lower() == 'movie':
                    name = item.get('name', None)
                    releaseYear  = item.get('releaseYear', None)
                    _id = str(item.get('id', None) )
                    
                    duration  = item.get('duration', None)
                    
                    images = item.get('images', [])
                    
                    for im in images:
                        thumbnail = None
                        fanart = None
                        if im.get('type', None) == 'COLLECTION_MOVIE_LIST_DISPLAY':
                            thumbnail = im.get('url', None)
                        elif im.get('type', None) ==  'COLLECTION_MOVIE_LIST_DISPLAY_LANDSCAPE':#"TITLE_FEED_SEASON_DISPLAY":
                            fanart = im.get('url', None)
                            #if '00h' in  fanart:
                            #    fanart = fanart.replace('00h','00')
                        else:
                            continue

                        if not thumbnail or not fanart:
                            if images:
                                thumbnail = images[0].get('url', None)
                                fanart = images[0].get('url', None)
                            else:
                                thumbnail = helper.addon.getAddonInfo('icon')
                                fanart = helper.addon.getAddonInfo('fanart')

                    description = item.get('description', None).get('long', None)
                    info = {'title': name, 'plot':description, 'year':releaseYear, 'duration':duration}
                    art={'icon':thumbnail, 'fanart':fanart}
                    fold = False
                    ispla = True
                    
                    mod = plugin.url_for(playvid, mpd_url=quote_plus('title/startplay/title/%s/format/WIDEVINE'%str(_id)), widevine_url = 'xx')

                    helper.add_item(name, mod, playable=ispla, info=info, art=art, folder=fold) 

    else:
        for item in jsdata.get('titles', []):
            _id = item.get('id', None)
            releaseYear = item.get('releaseYear', None)
            duration = item.get('duration', None)
            name = item.get('name', None)
            type = item.get('type', None).lower()
            description = item.get('description', None).get('long',None)
            
            
            thumbnail = None
            fanart = None
            
            images = item.get('images', [])

            for im in images:
                if im.get('type', None) == 'COLLECTION_MOVIE_LIST_DISPLAY':
                    thumbnail = im.get('url', None)
                elif im.get('type', None) ==  'COLLECTION_MOVIE_LIST_DISPLAY_LANDSCAPE':#"TITLE_FEED_SEASON_DISPLAY":
                    fanart = im.get('url', None)
                    #if '00h' in  fanart:
                    #    fanart = fanart.replace('00h','00')
                else:
                    continue

            if not thumbnail or not fanart:
                if images:
                    thumbnail = images[0].get('url', None)
                    fanart = images[0].get('url', None)
                else:
                    thumbnail = helper.addon.getAddonInfo('icon')
                    fanart = helper.addon.getAddonInfo('fanart')
            info = {'title': name, 'plot':description, 'year':releaseYear, 'duration': duration }
            art={'icon':thumbnail, 'fanart':fanart}

            ispla = True
            fold = False

            mod = plugin.url_for(playvid, mpd_url=quote_plus('title/startplay/title/%s/format/WIDEVINE'%str(_id)), widevine_url = 'xx')

            helper.add_item(name, mod, playable=ispla, info=info, art=art, folder=fold) 

    if pagecount>int(page):
        helper.add_item('[COLOR gold]>> Next Page >>[/COLOR]', plugin.url_for(listcateg, id=quote_plus(id), page = int(page)+1),folder=True)

    helper.eod()

@plugin.route('/mylist')    
def mylist():

    url = helper.base_api_url.format('now')
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    #
    sched = str(jsdata.get('schedule', None))
    url = helper.base_api_url.format('schedule/%s'%sched) 
    
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    
    for chan in jsdata.get('channels', None):
        acv=''
        href = str(chan.get('channelId', None))
        title = '[COLOR gold][B]Live channel: '+chan.get('name', None)+'[/COLOR][/B]'
        mod = plugin.url_for(playvid, mpd_url=quote_plus(href), widevine_url = 'xx')
        info = {'title': title, 'plot':title}
        art={'icon':helper.addon.getAddonInfo('fanart'), 'fanart':helper.addon.getAddonInfo('fanart')}
        ispla = True
        helper.add_item(title, mod, playable=ispla, info=info, art=art, folder=False) 
        
        for progr in chan.get('programs',[]):
            
            strt = int(progr.get('start', None))/1000
            tstampnow = helper.getCurTStamp()
            endprogram = strt+progr.get('runtime', None) 
            if endprogram>tstampnow:
                pocz,koniec = helper.convertUnixTime(strt,endprogram)
                title = progr.get("title", None)
                descMedium = progr.get("descMedium", None)
                titleId = progr.get("titleId", None)
                imageLive = progr.get("imageLive", None)
               
                imageSchedule = progr.get("imageSchedule", None)
                if not title and 'series' in progr:
                    title = progr.get('series', None).get('name', None)

                titlek= '[B][COLOR khaki]%s - %s[/COLOR] '%(str(pocz),str(koniec))+title+'[COLOR lightgreen][I] play on demand[/COLOR][/I][/B]'

                plot = '[COLOR khaki]%s - %s[/COLOR][CR]'%(str(pocz),str(koniec))+descMedium

                ispla = True
        
                mod = plugin.url_for(playvid, mpd_url=quote_plus('title/startplay/title/%s/format/WIDEVINE'%str(titleId)), widevine_url = 'xx')
                info = {'title': titlek, 'plot':plot}
                art={'icon':imageSchedule, 'fanart':imageLive}
                helper.add_item(titlek, mod, playable=ispla, info=info, art=art, folder=False) 

    helper.eod()

@plugin.route('/listcontent/<id>')    
def listcontent(id):
    url = helper.base_api_url.format(id)
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    for item in jsdata.get('allSeries', None):
        _id = str(item.get("id", None))
        title = item.get("name", None)
        thumbnail = item.get('images', None)[0].get('url', None)
        description = item.get("description", None).get('long', None)
        genre = item.get("genre", None).lower()
        releaseYear = item.get("releaseYear", None)
        mod = plugin.url_for(listcontent2, id=quote_plus(id+'/'+_id))
        fold = True
        ispla = False
        info = {'title': title, 'plot':description,'genre':genre, 'year':releaseYear}
        art = {'icon': thumbnail, 'fanart': helper.addon.getAddonInfo('fanart')}
        helper.add_item(title, mod, playable=ispla, info=info, art=art)    
    helper.eod()

def CreateInfo(video_data):

    seasonNum = video_data.get('series', None).get('seasonNum', None)
    episodeNum = video_data.get('series', None).get('episodeNum', None)

    title = video_data.get('sortName', None)

    description = video_data.get('description', None).get("long", None)
    try:
        duration = video_data.get('duration', None)#.get("seconds", None)
    except:
        duration = ''

    year = video_data.get('releaseYear', None)
    year = year if year else ''

    info = {'title': title, 'plot':description, 'year':year, 'season' : int(seasonNum),'episode' : int(episodeNum) }
    if duration:
        info.update({'duration':duration})
    return info
    
def getArts(video_data):
    fanart=None
    imag=None
    images = video_data.get("images", [])
    for im in images:
        if im.get('type', None) == "TITLE_FEED_DETAILS_EPISODE":
            thumbnail = im.get('url', None)
        elif im.get('type', None) ==  "SERIES_DETAIL_SMALL":
            fanart = im.get('url', None)
        else:
            continue

    art = {'icon': thumbnail, 'fanart': fanart}
    return art
    
@plugin.route('/listcontent2/<id>')    
def listcontent2(id):
    id = unquote_plus(id)
    
    if    '|' in id:
        id,season = id.split('|')
    url = helper.base_api_url.format(id)
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    fanart=''
    if 'titles/series/' in url:
        abc=''
        
        for episode in jsdata.get('episodesForSeries', []):

            seasonNum = episode.get("series", None).get('seasonNum', None)
            if seasonNum == int(season):
                episodeNum = episode.get("series", None).get('episodeNum', None)
                seriesTitle = episode.get("series", None).get('seriesTitle', None)
                tit1 =' S%02dE%02d '%(int(seasonNum),int(episodeNum))
                _id = episode.get("id", None)
                name = episode.get("name", None)
                info = CreateInfo(episode)
                art = getArts(episode)
                nazwa = seriesTitle + tit1 + name

                mod = plugin.url_for(playvid, mpd_url=quote_plus('title/startplay/title/%s/format/WIDEVINE'%str(_id)), widevine_url = 'xx')

                fold = False
                ispla = True
                helper.add_item(nazwa, mod, playable=ispla, info=info, art=art)
                
                
                
    else:
        for im in jsdata.get("images", []):
            if im.get("type",None)=="SERIES_ABOUT_IMAGE":
                fanart = im.get("url",None)
                break
        _id = str(jsdata.get("id", None))
        name = jsdata.get("name", None)
        totalSeasons = str(jsdata.get("totalSeasons", None))
        releaseYear = str(jsdata.get("releaseYear", None))
        genre = jsdata.get("genre", None)
    
        for seas in jsdata.get('seasons', []):
            seasonNum = str(seas.get("seasonNum", None))
            description = seas.get("description", None).get('long', None)
            seasonimage = 'https://segami.showtime.com/segami/'+_id+'/'+seasonNum+'/0/97/1920x1080/image.jpg'
            nazwa = '[COLOR gold]'+name +'[/COLOR] - Season %02d'%int(seasonNum)
    
            mod = plugin.url_for(listcontent2, id=quote_plus('titles/series/%s/format/WIDEVINE|%s'%(str(_id),str(seasonNum)) )) 
            fold = True
            ispla = False
            info = {'title': nazwa, 'plot':description,'genre':genre, 'year':releaseYear}
            art = {'icon': seasonimage, 'fanart': seasonimage}#helper.addon.getAddonInfo('fanart')}
            helper.add_item(nazwa, mod, playable=ispla, info=info, art=art)
        

    helper.eod()

    
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
def login(ses=True):

    if not helper.username or not helper.password:
        helper.notification('Info', 'No credentials')
    
        helper.set_setting('logged', 'false')
    else:
        json_data = {
            'email': helper.username,
            'password': helper.password,}
        url = helper.base_api_url.format('user/login')
        try:
            jsdata = helper.request_sess(url, 'post', headers=helper.headers, data = json_data, json=True, json_data = True)
            if 'error' in jsdata:
                helper.notification('Information', jsdata.get('error', None).get('title', None))
                helper.set_setting('logged', 'false')    
            else:
    
                if jsdata.get("registered", None):
                    abc = helper._sess.cookies
                    helper.save_file(file=helper.datapath+'kukis', data=(abc).get_dict(), isJSON=True)    
                    helper.set_setting('logged', 'true')
        except:
            helper.notification('Information', 'Something wrong\nPlease try again later')
            helper.set_setting('logged', 'false')  
    if ses:
        helper.refresh()



@plugin.route('/playvid/<mpd_url>/<widevine_url>')
def playvid(mpd_url,widevine_url):
    mpd_url = unquote_plus(mpd_url)
    widevine_url = unquote_plus(widevine_url)
    if 'title/startplay/title' in mpd_url:
        url = helper.base_api_url.format(mpd_url)
    else:
        url = helper.base_api_url.format('channel/startplay/%s/format/WIDEVINE'%mpd_url)
    
    jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    if jsdata.get('error', None):
        login(ses=False)
        jsdata = helper.request_sess(url, 'get', headers=helper.headers, json=True)
    mpd_url = jsdata.get("uri",None)
    refid = jsdata.get("refid",None)
    if 'channel' in url:
        widevine_url = jsdata.get("licenseUrl",None) +'?refid='+refid+'&authToken=Yml0ZSBteSBzaGlueSBtZXRhbCBkcm0='
    else:
        import base64
        entitlement= (base64.b64encode(jsdata.get("entitlement",None).encode("utf-8"))).decode("utf-8")
        widevine_url = jsdata.get("licenseUrl",None) +'/download?refid='+refid+'&authToken=Yml0ZSBteSBzaGlueSBtZXRhbCBkcm0=&showtime='+entitlement#sdUri
    
    subt=[]
    lic_url =  widevine_url+"|Content-Type=application/octet-stream|R{SSM}|"
    PROTOCOL = 'mpd'
    DRM = 'com.widevine.alpha'
    helper.PlayVid(mpd_url, lic_url, PROTOCOL, DRM, flags=False, subs = subt)


class Showtime(Helper):
    def __init__(self):
        super().__init__()
        plugin.run()


