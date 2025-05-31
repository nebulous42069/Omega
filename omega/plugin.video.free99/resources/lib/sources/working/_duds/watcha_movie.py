# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['watcha.movie']
        self.base_link = 'https://watcha.movie'
        self.search_link = '/search/%s'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def episode(self, url, imdb, tmdb, tvdb, title, premiered, season, episode):
        if not url:
            return
        url = parse_qs(url)
        url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
        url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
        url = urlencode(url)
        return url


    def sources(self, url, hostDict):
        try:
            if url == None:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_url = self.base_link + self.search_link % cleantitle.get_utf8(title)
            search_html = client.scrapePage(search_url).text
            results = client_utils.parseDOM(search_html, 'div', attrs={'class': 'list-movie'})
            results = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', attrs={'class': 'list-title'}), client_utils.parseDOM(i, 'div', attrs={'class': 'quality'})) for i in results]
            results = [(i[0][0], i[1][0], i[2][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            result = [(i[0], i[2]) for i in results if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[0], year, data['year'])][0]
            url = result[0]
            qual = result[1]
            if 'tvshowtitle' in data:
                url = url[:-1] if url.endswith('/') else url
                url = url.replace('/show/', '/episode/')
                url = url + '/season-%s-episode-%s/' % (season, episode)
            page_html = client.scrapePage(url).text
            src_links = client_utils.parseDOM(page_html, 'a', attrs={'target': '_&quot;blank&quot;'}, ret='href')
            for src_link in src_links:
                try:
                    #https://remotestre.am/d/?tmdb=436270&apikey=whXgvN4kVyoubGwqXpw26Oy3PVryl8dm
                    #https://remotestre.am/d/?tmdb=44006&s=1&e=12
                    src_html = client.scrapePage(src_link).text
                    links = re.compile(client_utils.regex_pattern6).findall(src_html)
                    for link in links:
                        try:
                            item = scrape_sources.make_direct_item(hostDict, link, host=None, info=qual, referer=src_link, prep=True)
                            if item:
                                if not scrape_sources.check_host_limit(item['source'], self.results):
                                    self.results.append(item)
                            
                        except:
                            #log_utils.log('sources', 1)
                            pass
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


