# -*- coding: utf-8 -*-

import re
import os
import sys

import six
from six.moves import urllib_parse

from resources.lib.indexers import movies
from resources.lib.indexers import tvshows

from resources.lib.modules import cache
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import control
from resources.lib.modules import scrape_sources
from resources.lib.modules import sources as get_the
from resources.lib.modules import tmdb_utils
from resources.lib.modules import workers
#from resources.lib.modules import log_utils

try:
    #from infotagger.listitem import ListItemInfoTag
    from resources.lib.modules.listitem import ListItemInfoTag
except:
    pass

kodi_version = control.getKodiVersion()


class indexer:
    def __init__(self):
        try:
            self.list = []
            self.items = []
            self.default_image = 'DefaultVideo.png'
            self.default_fanart = control.addonFanart()
            self.hostDict = get_the.sources().getHostDict()
            self.base_link = 'https://api.gdriveplayer.us'
            self.lang = control.apiLanguage()['tmdb']
            self.studio_artwork = control.setting('studio.artwork') or 'false'
            self.tmdb_key = control.setting('tmdb.api')
            if not self.tmdb_key:
                self.tmdb_key = '3d000491a0f37d4962d02bdb062af037'
            self.tmdb_movie_api_link = 'https://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=credits,releases,external_ids' % ('%s', self.tmdb_key, self.lang)
            self.tmdb_tv_api_link = 'https://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=aggregate_credits,content_ratings,external_ids' % ('%s', self.tmdb_key, self.lang)
            self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'
            self.newest_movies_link = self.base_link + '/v1/movie/newest?limit=100'
            self.newest_series_link = self.base_link + '/v2/series/newest?limit=100'
            self.newest_dramas_link = self.base_link + '/v1/drama/newest?limit=100'
            self.search_dramas_link = self.base_link + '/v1/drama/search?title=%s&limit=100'
            self.newest_animes_link = self.base_link + '/v1/animes/newest?limit=100'
            self.search_animes_link = self.base_link + '/v1/animes/search?title=%s&limit=100'
        except:
            #log_utils.log('__init__', 1)
            return


    def root(self):
        try:
            self.list = [
                {'title': 'Movies - Newest', 'url': self.newest_movies_link, 'image': self.default_image, 'fanart': self.default_fanart, 'action': 'gdriveplayer.newest'},
                {'title': 'Series - Newest', 'url': self.newest_series_link, 'image': self.default_image, 'fanart': self.default_fanart, 'action': 'gdriveplayer.newest'},
                {'title': 'Dramas - Newest', 'url': self.newest_dramas_link, 'image': self.default_image, 'fanart': self.default_fanart, 'action': 'gdriveplayer.newest'},
                {'title': 'Dramas - Search', 'url': self.search_dramas_link, 'image': self.default_image, 'fanart': self.default_fanart, 'action': 'gdriveplayer.search'},
                {'title': 'Animes - Newest', 'url': self.newest_animes_link, 'image': self.default_image, 'fanart': self.default_fanart, 'action': 'gdriveplayer.newest'},
                {'title': 'Animes - Search', 'url': self.search_animes_link, 'image': self.default_image, 'fanart': self.default_fanart, 'action': 'gdriveplayer.search'},
            ]
            self.addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('root', 1)
            return self.list


    def newest(self, url):
        try:
            if url == self.newest_movies_link:
                return cache.get(self.medata_list, 0, url)
            elif url == self.newest_series_link:
                return cache.get(self.medata_list, 0, url)
            else:
                self.list = cache.get(self.api_list, 0, url)
                for i in self.list:
                    i.update({'item': urllib_parse.urlencode(i)})
                for i in self.list:
                    i.update({'action': 'gdriveplayer.details'})
                for i in self.list:
                    i.update({'fanart': self.default_fanart})
                self.addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('newest', 1)
            return self.list


    def search(self, url):
        try:
            k = control.keyboard('', '') ; k.setHeading(control.infoLabel('ListItem.Label')) ; k.doModal()
            if k.getText() == '' or not k.isConfirmed():
                return
            url = url % urllib_parse.quote_plus(k.getText())
            self.list = cache.get(self.api_list, 0, url)
            for i in self.list:
                i.update({'item': urllib_parse.urlencode(i)})
            for i in self.list:
                i.update({'action': 'gdriveplayer.details'})
            for i in self.list:
                i.update({'fanart': self.default_fanart})
            self.addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('search', 1)
            return self.list


    def medata_list(self, url):
        try:
            content = 'movies' if url == self.newest_movies_link else 'tvshows'
            results = client.scrapePage(url).json()
            for result in results:
                try:
                    title = result.get('title')
                    title = cleantitle.normalize(title)
                    title = client_utils.replaceHTMLCodes(title)
                    imdb = result.get('imdb')
                    item = (imdb, title, content)
                    if item in self.items:
                        continue
                    self.items.append(item)
                except:
                    #log_utils.log('medata_list', 1)
                    pass
            threads = []
            for i in range(0, len(self.items)):
                threads.append(workers.Thread(self.medata_info, self.items[i]))
            [i.start() for i in threads]
            [i.join() for i in threads]
            if content == 'movies':
                movies.movies().movieDirectory(self.list)
            else:
                tvshows.tvshows().tvshowDirectory(self.list)
            return self.list
        except:
            #log_utils.log('medata_list', 1)
            return self.list


    def medata_info(self, i):
        try:
            imdb = i[0]
            list_title = i[1]
            content = i[2]
            if content == 'movies':
                tmdb_api_link = self.tmdb_movie_api_link
                try:
                    temp_item = tmdb_utils.find_movie_by_external_source(imdb=imdb)
                    tmdb = temp_item.get('id', '0') or '0'
                except:
                    tmdb = '0'
            else:
                tmdb_api_link = self.tmdb_tv_api_link
                try:
                    temp_item = tmdb_utils.find_tvshow_by_external_source(imdb=imdb)
                    tmdb = temp_item.get('id', '0') or '0'
                except:
                    tmdb = '0'
            if not tmdb or tmdb == '0':
                raise Exception()
            en_url = tmdb_api_link % (tmdb)
            f_url = en_url + ',translations'
            url = en_url if self.lang == 'en' else f_url
            item = client.scrapePage(url).json()
            if not item:
                raise Exception()
            if not imdb or imdb == '0':
                try:
                    imdb = item.get('external_ids', {}).get('imdb_id', '0')
                    if not imdb:
                        imdb = '0'
                except:
                    imdb = '0'
            try:
                tvdb = item.get('external_ids', {}).get('tvdb_id', '0')
                if not tvdb:
                    tvdb = '0'
            except:
                tvdb = '0'
            original_language = item.get('original_language', '')
            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data'] for x in translations if x['iso_639_1'] == 'en'][0]
                except:
                    en_trans_item = {}
            if content == 'movies':
                name = item.get('title', '')
                original_name = item.get('original_title', '')
                en_trans_name = en_trans_item.get('title', '') if not self.lang == 'en' else None
            else:
                name = item.get('name', '')
                original_name = item.get('original_name', '')
                en_trans_name = en_trans_item.get('name', '') if not self.lang == 'en' else None
            if self.lang == 'en':
                title = label = name
            else:
                title = en_trans_name or original_name
                if original_language == self.lang:
                    label = name
                else:
                    label = en_trans_name or name
            if not title:
                title = original_name or list_title
            title = cleantitle.normalize(title)
            if not label:
                label = original_name or list_title
            label = cleantitle.normalize(label)
            plot = item.get('overview', '') or '0'
            tagline = item.get('tagline', '') or '0'
            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview', '')
                    if en_plot:
                        plot = en_plot
                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline', '')
                    if en_tagline:
                        tagline = en_tagline
            if content == 'movies':
                premiered = item.get('release_date', '') or '0'
            else:
                premiered = item.get('first_air_date', '')
            if not premiered:
                premiered = '0'
            try:
                year = re.findall('(\d{4})', premiered)[0]
            except:
                year = ''
            if not year:
                year = '0'
            status = item.get('status', '') or '0'
            if self.studio_artwork == 'true':
                studio = item.get('production_companies', [])
                if studio and studio != []:
                    studio = [x['name'] for x in studio]
                else:
                    studio = []
            else:
                studio = []
            try:
                genres = item['genres']
                genres = [d['name'] for d in genres]
            except:
                genres = []
            if not genres:
                genres = []
            try:
                countries = item['production_countries']
                countries = [c['name'] for c in countries]
            except:
                countries = []
            if not countries:
                countries = []
            if content == 'movies':
                try:
                    duration = item['runtime']
                    duration = str(duration)
                except:
                    duration = ''
            else:
                try:
                    duration = item['episode_run_time'][0]
                    duration = str(duration)
                except:
                    duration = ''
            if not duration:
                duration = '0'
            if content == 'movies':
                try:
                    mpaa = item['releases']['countries']
                    mpaa = [x['certification'] for x in mpaa if not x['certification'] == '' and str(x['iso_3166_1']) == 'US'][0]
                except:
                    mpaa = ''
            else:
                try:
                    mpaa = item['content_ratings']['results']
                    mpaa = [x['rating'] for x in mpaa if not x['rating'] == '' and str(x['iso_3166_1']) == 'US'][0]
                except:
                    mpaa = ''
            if not mpaa:
                mpaa = '0'
            rating = str(item.get('vote_average', '')) or '0'
            votes = item.get('vote_count', '') or '0'
            castwiththumb = []
            if content == 'movies':
                try:
                    c = item['credits']['cast'][:30]
                    for person in c:
                        _icon = person['profile_path']
                        icon = self.tm_img_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
                except:
                    pass
            else:
                try:
                    c = item['aggregate_credits']['cast'][:30]
                    for person in c:
                        _icon = person['profile_path']
                        icon = self.tm_img_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
                except:
                    pass
            if not castwiththumb:
                castwiththumb = []
            try:
                crew = item['credits']['crew']
                director = [d['name'] for d in [x for x in crew if x['job'] == 'Director']]
                writer = [w['name'] for w in [y for y in crew if y['job'] in ['Writer', 'Screenplay', 'Author', 'Novel']]]
            except:
                director = writer = []
            poster_path = item.get('poster_path')
            if poster_path:
                poster = self.tm_img_link % ('500', poster_path)
            else:
                poster = '0'
            fanart_path = item.get('backdrop_path')
            if fanart_path:
                fanart = self.tm_img_link % ('1280', fanart_path)
            else:
                fanart = '0'
            banner = clearlogo = clearart = landscape = discart = '0'
            self.list.append({'title': title, 'originaltitle': title, 'label': label, 'year': year, 'premiered': premiered, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb,
                'poster': poster, 'banner': banner, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'discart': discart,
                'genre': genres, 'duration': duration, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'plot': plot, 'tagline': tagline,
                'status': status, 'studio': studio, 'country': countries, 'mpaa': mpaa, 'rating': rating, 'votes': votes}
            )
        except:
            #log_utils.log('medata_info', 1)
            pass


    def api_list(self, url): # Went haywire with replaceHTMLCodes for the hell of it and to be lazy. Their api is sorta dirty anyways.
        try:
            items = client.scrapePage(url).json()
            for item in items:
                title = item.get('title', '')
                title = cleantitle.normalize(title)
                title = client_utils.replaceHTMLCodes(title)
                genre = item.get('genre', '')
                genre = client_utils.replaceHTMLCodes(genre)
                genre = [genre.title()]
                summary = item.get('summary', '') or ''
                summary = client_utils.replaceHTMLCodes(summary)
                status = item.get('status', '')
                status = client_utils.replaceHTMLCodes(status)
                content = item.get('type', '')
                content = client_utils.replaceHTMLCodes(content)
                image = item.get('poster', '')
                image = client_utils.replaceHTMLCodes(image)
                total_episode = item.get('total_episode', '')
                total_episode = client_utils.replaceHTMLCodes(total_episode)
                url = item.get('player_url', '')
                url = client_utils.replaceHTMLCodes(url)
                label = '[B]%s[/B] (%s | %s)' % (title, status, content)
                self.list.append({'label': label, 'title': title, 'status': status, 'content': content,
                    'genre': genre, 'url': url, 'plot': summary, 'image': image, 'episodes': total_episode}
                )
            return self.list
        except:
            #log_utils.log('api_list', 1)
            return self.list


    def details(self, url, image=None, item=None):
        try:
            data = urllib_parse.parse_qs(item)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['title']
            episodes = data['episodes']
            url = url.split('&episode=')[0]
            for i in range(1, int(episodes)+1):
                label = '[B]%s[/B] | Episode %s' % (title, i)
                link = url + '&episode=%s' % i
                self.list.append({'label': label, 'title': title, 'url': link, 'image': image})
            for i in self.list:
                i.update({'action': 'gdriveplayer.sources'})
            for i in self.list:
                i.update({'fanart': self.default_fanart})
            self.addDirectory(self.list)
            return self.list
        except:
            #log_utils.log('details', 1)
            return self.list


    def sources(self, url, image=None):
        try:
            url = scrape_sources.prepare_link(url)
            if not url: raise Exception()
            html = client.scrapePage(url).text
            servers = client_utils.parseDOM(html, 'ul', attrs={'class': 'list-server-items'})[0]
            links = client_utils.parseDOM(servers, 'a', ret='href')
            for link in links:
                try:
                    if not link or link.startswith('/player.php'):
                        continue
                    for source in scrape_sources.process(self.hostDict, link):
                        label = '[B]%s[/B] | %s %s' % (source['source'], source['quality'], source['info'])
                        link = source['url']
                        self.list.append({'title': label, 'url': link, 'image': image, 'action': 'alt_play'})
                except:
                    #log_utils.log('sources', 1)
                    pass
            self.addDirectory(self.list, content='files')
            return self.list
        except:
            #log_utils.log('sources', 1)
            pass


    def addDirectory(self, items, content='addons'):
        try:
            if items == None or len(items) == 0:
                return
            sysaddon = sys.argv[0]
            artPath = control.artPath()
            sysimage = control.addonInfo('icon')
            sysfanart = control.addonInfo('fanart')
            for i in items:
                try:
                    try:
                        label = i['label']
                    except:
                        label = i['title']
                    if 'image' in i and not i['image'] == '0':
                        image = i['image']
                    elif 'icon' in i and not i['icon'] == '0':
                        image = os.path.join(artPath, i['icon'])
                    else:
                        image = sysimage
                    fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else sysfanart
                    isFolder = False if 'isFolder' in i and not i['isFolder'] == '0' else True
                    url = '%s?action=%s' % (sysaddon, i['action'])
                    try:
                        url += '&url=%s' % urllib_parse.quote_plus(i['url'])
                    except:
                        pass
                    try:
                        url += '&title=%s' % urllib_parse.quote_plus(i['title'])
                    except:
                        pass
                    try:
                        url += '&image=%s' % urllib_parse.quote_plus(i['image'])
                    except:
                        pass
                    try:
                        url += '&item=%s' % urllib_parse.quote_plus(i['item'])
                    except:
                        pass
                    meta = dict((k, v) for k, v in six.iteritems(i) if not v == '0')
                    try:
                        meta.update({'duration': str(int(meta['duration']) * 60)})
                    except:
                        pass
                    try:
                        item = control.item(label=label, offscreen=True)
                    except:
                        item = control.item(label=label)
                    try:
                        item.setArt({'icon': image, 'thumb': image, 'poster': image, 'banner': image})
                    except:
                        #log_utils.log('addDirectory', 1)
                        pass
                    item.setProperty('Fanart_Image', fanart)
                    cm = []
                    cm.append(('Clean Tools Widget', 'RunPlugin(%s?action=cleantools_widget)' % sysaddon))
                    cm.append(('Information', 'Action(Info)'))
                    item.addContextMenuItems(cm)
                    if kodi_version >= 20:
                        info_tag = ListItemInfoTag(item, 'video')
                    if kodi_version >= 20:
                        info_tag.set_info(control.metadataClean(meta))
                    else:
                        item.setInfo(type='Video', infoLabels=control.metadataClean(meta))
                    
                    if isFolder == False:
                        item.setProperty('IsPlayable', 'true')
                    control.addItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isFolder)
                except:
                    #log_utils.log('addDirectory', 1)
                    pass
            control.content(int(sys.argv[1]), content)
            control.directory(int(sys.argv[1]), cacheToDisc=True)
        except:
            #log_utils.log('addDirectory', 1)
            pass


