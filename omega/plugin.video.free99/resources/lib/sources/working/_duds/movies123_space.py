# -*- coding: utf-8 -*-

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['movies-123.space']
        self.base_link = 'https://movies-123.space'
        self.search_link = '/search?type=all&q=%s' # swapped to a coded searching_link for type.


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
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            cleanedtitle = cleantitle.get_plus(title)
            check = '/tv/' if 'tvshowtitle' in data else '/movie/'
            searching_link = '/search-tv?q=%s&category=tv' if 'tvshowtitle' in data else '/search?q=%s&category=movies'
            link = self.base_link + searching_link % cleanedtitle
            html = client.scrapePage(link).text
            results = zip(client_utils.parseDOM(html, 'a', ret='href'), client_utils.parseDOM(html, 'a'))
            results = [(i[0], i[1]) for i in results]
            result = [i[0] for i in results if cleanedtitle in cleantitle.get_plus(i[1]) and check in i[0]][0]
            if 'tvshowtitle' in data:
                link = self.base_link + result + '/episode?season=%s&episode=%s' % (data['season'], data['episode'])
            else:
                link = self.base_link + result + '/watch'
            html = client.scrapePage(link).text
            links = client_utils.parseDOM(html, 'iframe', ret='src')
            for link in links:
                for source in scrape_sources.process(hostDict, link):
                    self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


