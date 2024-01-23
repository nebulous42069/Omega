import os
import sys 
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon 
import requests 
import re 
from urllib.parse import parse_qs, urlencode, quote_plus, unquote
from bs4 import BeautifulSoup

_url = sys.argv[0]
_handle = int(sys.argv[1])   
_addon = xbmcaddon.Addon('plugin.audio.datpiff')
_language = _addon.getLocalizedString 
_default_icon = _addon.getAddonInfo('icon')
_default_fanart = _addon.getAddonInfo('fanart')
_artist_url = 'http://www.datpiff.com/mixtapes-artist.php?filter=month&l='
_title_url = 'http://www.datpiff.com/mixtapes-title.php?filter=month&l='
_most_listens_url = 'http://www.datpiff.com/mixtapes-popular.php?filter=month&sort=listens&p='
_most_downloads_url = 'http://www.datpiff.com/mixtapes-popular.php?filter=month&sort=downloads&p='
_most_favorited_url = 'http://www.datpiff.com/mixtapes-popular.php?filter=month&sort=rating&p='
_highest_rating_url = 'http://www.datpiff.com/mixtapes-popular.php?filter=month&sort=favorites&p='
_newest_url = 'http://www.datpiff.com/mixtapes.php?filter=all&p='
_celebrated_url = 'http://www.datpiff.com/mixtapes/'
_hot_this_week_url = 'http://www.datpiff.com/mixtapes-hot.php'
_search_url = 'http://www.datpiff.com/mixtapes-search.php?criteria={SEARCH_CRITERIA}&sort=relevance&search=&search[]=title&search[]=artists&search[]=djs&p='

def get_page(url): 
    return BeautifulSoup(requests.get(url).text, 'html.parser')
    
def build_url(query):    
    return f'{_url}?{urlencode(query)}'

def parse_duration(durationText):
    match = re.match(r'PT(.*?)M(.*?)S', durationText, re.I)	
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return minutes * 60 + seconds
        
    return 0
    
def guess_mp3_url(directory, id, title, length):
    # can't find it just quit and return the title
    if length < 40:
        return title
    
    truncated_title = title[:length].replace(' ', '%20');
    url = f'http://hw-mp3.datpiff.com/mixtapes/{directory}/{id}/{truncated_title}.mp3'	
    
    #Head doesn't work, so try to download the first byte of the mp3
    r = requests.get(url, headers = { 'Range': 'bytes=0-1' })
    if r.status_code >= 400:		
        return guess_mp3_url(directory, id, title, length - 1)
    
    return truncated_title
    
def parse_mp3_url(mixtape_id, mixtape_hash, track_number, track_title): 
    removedChars = ['-', '.', '\'', ',', '{', '}', '@', '$', '&', ':', ';']
    directory = mixtape_id[0]
    track = f'{track_number}'.rjust(2, '0')
    
    title = track_title
    for char in removedChars:
        title = title.replace(char, '')
        
    title = f'{track} - {title}'
    
    #The URL length is inconsistent, but the title part max seems to be between 49 - 55 characters
    if len(title) > 49: 
        title = guess_mp3_url(directory, mixtape_hash, title, min(len(title) - 1, 56))        
    title = title.replace(' ', '%20')							   

    return f'http://hw-mp3.datpiff.com/mixtapes/{directory}/{mixtape_hash}/{title}.mp3'
     
def create_track_listings(params):
    listings = []
    category = None
    page = get_page(params['url'])
    
    art = page.find(id = 'coverImage1')['src']
    artist = page.find(class_ = 'tapeDetails').find(class_ = 'artist').text
    album = page.find(class_ = 'tapeDetails').find(class_ = 'title').text
    playcount = int(page.find(class_ = 'tapeDetails').find(class_ = 'listens').text.replace(',', ''))	
    mixtape_id = page.find('meta', {'name': 'twitter:app:url:iphone'})['content'].replace('https://mobile.datpiff.com/mixtape/', '')
    mixtape_hash = ''

    track_nodes = page.find(class_ = 'tracklist').find_all('li')	
    for node in track_nodes:
        if category is None:
            category = f'{artist} - {album}'
 
        if mixtape_hash == '':
            meta_player_url = node.find('meta', { 'itemprop': 'url' })['content']
            mixtape_hash = re.match(r'.*?player\/(.*?)\?', meta_player_url, re.I).group(1)
 
        title = node.find(class_ = 'trackTitle').text			
        track_number = int(node.find(class_ = 'tracknumber').text.replace('.', ''))

        li = xbmcgui.ListItem(label = f'{track_number}. {title}')
        li.setArt({ 'thumb': art, 'icon': art, 'fanart': _default_fanart })
        li.setInfo('music', {
            'album': album, 
            'artist': artist,  
            'tracknumber': track_number,
            'title': title,
            'duration': parse_duration(node.find('meta', { 'itemprop': 'duration' })['content']),
            'playcount': playcount		
        })
        li.setProperty('IsPlayable', 'true')
        url = build_url({ 'action': 'play', 'url': parse_mp3_url(mixtape_id, mixtape_hash, track_number, title) })
        listings.append((url, li, False))
    
    xbmcplugin.addDirectoryItems(_handle, listings, len(listings))
    xbmcplugin.endOfDirectory(_handle)
    xbmcplugin.setPluginCategory(_handle, category)
    
def is_pageable(url):
    return url != _hot_this_week_url
    
def get_mixtape_url(url, page_number):
    if url == _hot_this_week_url:
        return url 
    elif url.startswith(_artist_url) or url.startswith(_title_url):
        return f'{url}&p={page_number}'
    else:
        return f'{url}{page_number}'
 
def create_mixtape_listings(params):
    xbmcplugin.setPluginCategory(_handle, params['category'])

    listings = []	
    page_url = params['url']
    page_number = int(params.get('page_number', '1'))	 
    page = get_page(get_mixtape_url(page_url, page_number))
    mixtape_nodes = page.find(id = 'leftColumnWide').find_all(class_ = 'contentItemInner')

    for node in mixtape_nodes:
        artist = node.find(class_ = 'artist').text
        title = node.find(class_ = 'title').text
        art = node.find(class_ = 'contentThumb').a.img['src']
        link = node.find(class_ = 'title').a['href'];
        url = f'http://www.datpiff.com{link}'

        li = xbmcgui.ListItem(label = f'{artist} - {title}')
        li.setArt({ 'thumb': art, 'icon': art, 'fanart': _default_fanart })
        li.setInfo('music', { 'album': title, 'artist': artist }) 
        url = build_url({ 'action': 'tracks', 'url': url })
        listings.append((url, li, True))
    
    if(is_pageable(page_url)):
        li =  xbmcgui.ListItem(label = 'More...')
        url = build_url({'action': 'mixtapes', 'url': page_url, 'page_number': page_number + 1, 'category': params['category'] })
        listings.append((url, li, True))
    
    xbmcplugin.addDirectoryItems(_handle, listings, len(listings)) 
    xbmcplugin.endOfDirectory(_handle)
    
def create_alpha_listing(params):	
    alphabet = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ'    
    listings = []	
    type_url_base = _artist_url
    category = params['category']

    if params['type'] == 'title':
        type_url_base = _title_url
    
    for i in range(27): 
        char = alphabet[i]      
        page_type = params['type'].title()
        li = xbmcgui.ListItem(label = char)
        li.setArt({ 'thumb': _default_icon, 'icon': _default_icon, 'fanart': _default_fanart }) 
        mixtapes_url = f'{type_url_base}{char}'	
        url = build_url({ 'action': 'mixtapes', 'url': mixtapes_url, 'category': f'{category} - {char}' })		
        listings.append((url, li, True))
    
    xbmcplugin.setPluginCategory(_handle, category)
    xbmcplugin.addDirectoryItems(_handle, listings, len(listings)) 
    xbmcplugin.endOfDirectory(_handle)
    
def search(params):
    kb = xbmc.Keyboard(heading = 'Search') 
    kb.doModal()
    
    if kb.isConfirmed() and kb.getText() != "":
        search_term = kb.getText()
        params['url'] = _search_url.replace('{SEARCH_CRITERIA}', quote_plus(search_term))
        params['category'] = f'Search Results for {search_term}'
        create_mixtape_listings(params)

def play_track(params):
    xbmcplugin.setResolvedUrl(_handle, True, listitem = xbmcgui.ListItem(path = params['url']))
    
def get_text(key):
    return unquote(_language(key))

def route(params):  
    if params:
        if params['action'] == 'alpha':
            create_alpha_listing(params)
        if params['action'] == 'mixtapes':
            create_mixtape_listings(params)
        if params['action'] == 'tracks':
            create_track_listings(params)
        if params['action'] == 'search':
            xbmc.log('datpiff - searching...')
            search(params)
        if params['action'] == 'play':
            play_track(params)
    else:
        xbmc.log('DatPiff - Default Render')
        listings = [] 

        home = [
            {'title': get_text(30001), 'url': build_url({ 'action': 'alpha', 'type': 'artist', 'category': get_text(30001) })},
            {'title': get_text(30002), 'url': build_url({ 'action': 'alpha', 'type': 'title', 'category': get_text(30002) })},
            {'title': get_text(30003), 'url': build_url({ 'action': 'mixtapes', 'url': _most_listens_url, 'category': get_text(30003) })},
            {'title': get_text(30004), 'url': build_url({ 'action': 'mixtapes', 'url': _most_downloads_url, 'category': get_text(30004) })},
            {'title': get_text(30005), 'url': build_url({ 'action': 'mixtapes', 'url': _most_favorited_url, 'category': get_text(30005) })},
            {'title': get_text(30006), 'url': build_url({ 'action': 'mixtapes', 'url': _highest_rating_url, 'category': get_text(30006) })},
            {'title': get_text(30007), 'url': build_url({ 'action': 'mixtapes', 'url': _hot_this_week_url, 'category': get_text(30007) })},
            {'title': get_text(30008), 'url': build_url({ 'action': 'mixtapes', 'url': _newest_url, 'category': get_text(30008) })},
            {'title': get_text(30009), 'url': build_url({ 'action': 'mixtapes', 'url': f'{_celebrated_url}2xplatinum/', 'category': get_text(30009) })},
            {'title': get_text(30010), 'url': build_url({ 'action': 'mixtapes', 'url': f'{_celebrated_url}platinum/', 'category': get_text(30010) })},
            {'title': get_text(30011), 'url': build_url({ 'action': 'mixtapes', 'url': f'{_celebrated_url}gold/', 'category': get_text(30011) })},
            {'title': get_text(30012), 'url': build_url({ 'action': 'mixtapes', 'url': f'{_celebrated_url}sliver/', 'category': get_text(30012) })},
            {'title': get_text(30013), 'url': build_url({ 'action': 'mixtapes', 'url': f'{_celebrated_url}bronze/', 'category': get_text(30013) })},
            {'title': get_text(30014), 'url': build_url({ 'action': 'search' })}
        ]
        
        for item in home:             
            li = xbmcgui.ListItem(label = item['title'])
            li.setArt({ 'thumb': _default_icon, 'icon': _default_icon, 'fanart': _default_fanart }) 
            li.setInfo('music', { 'title': item['title'] })
            listings.append((item['url'], li, True))
            
        xbmcplugin.addDirectoryItems(_handle, listings, len(listings)) 
        xbmcplugin.endOfDirectory(_handle)

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsOfParams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsOfParams)):
            splitparams = {}
            splitparams = pairsOfParams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = unquote(splitparams[1])

    return param

if __name__ == '__main__': 
    route(get_params())