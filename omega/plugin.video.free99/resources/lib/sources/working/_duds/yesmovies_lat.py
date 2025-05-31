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
        self.domains = ['yesmovies.lat', 'yesmovies.gg']
        self.base_link = 'https://yesmovies.lat'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'year': year}
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
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_title = cleantitle.geturl(title)
            try:
                if 'tvshowtitle' in data:
                    search_link = self.base_link + '/film/%s-%s-season-%s/watching.html?ep=%s' % (search_title, data['year'], data['season'], data['episode'])
                else:
                    search_link = self.base_link + '/film/%s-%s/watching.html?ep=0' % (search_title, year)
                search_request = client.request(search_link, output='extended')
                html_url = search_request[4]
                if html_url.endswith('/watching.html'):
                    raise Exception()
                html = search_request[0]
                check_year = re.findall(r'Release:.+?(\d{4})', html)[0]
                check_year = cleantitle.match_year(check_year, year, data['year'])
                if not check_year:
                    raise Exception()
            except:
                if 'tvshowtitle' in data:
                    search_link = self.base_link + '/film/%s-season-%s/watching.html?ep=%s' % (search_title, data['season'], data['episode'])
                else:
                    search_link = self.base_link + '/film/%s/watching.html?ep=0' % search_title
                search_request = client.request(search_link, output='extended')
                html_url = search_request[4]
                if html_url.endswith('/watching.html'):
                    raise Exception()
                html = search_request[0]
                check_year = re.findall(r'Release:.+?(\d{4})', html)[0]
                check_year = cleantitle.match_year(check_year, year, data['year'])
                if not check_year:
                    raise Exception()
            try:
                qual = client_utils.parseDOM(html, 'span', attrs={'class': 'quality'})[0]
            except:
                qual = ''
            links = client_utils.parseDOM(html, 'li', ret='data-video')
            for link in links:
                try:
                    for source in scrape_sources.process(hostDict, link, info=qual):
                        if scrape_sources.check_host_limit(source['source'], self.results):
                            continue
                        self.results.append(source)
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


