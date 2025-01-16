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
        self.domains = ['123moviesfree.so']
        self.base_link = 'https://123moviesfree.so'
        self.search_link = '/movie/search/%s'


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
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_term = '%s Season %s' % (title, season) if 'tvshowtitle' in data else title
            search_url = self.base_link + self.search_link % cleantitle.geturl(search_term)
            r = client.scrapePage(search_url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            if not r and 'tvshowtitle' in data:
                search_url = self.base_link + self.search_link % cleantitle.geturl(title)
                r = client.scrapePage(search_url).text
                r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = zip(client_utils.parseDOM(r, 'a', ret='href'), client_utils.parseDOM(r, 'a', ret='title'))
            if 'tvshowtitle' in data:
                results = [(i[0], i[1], re.findall(r'(.+?) Season (\d+)$', i[1])) for i in r]
                try:
                    r = [(i[0], i[1], i[2][0]) for i in results if len(i[2]) > 0]
                    url = [i[0] for i in r if cleantitle.match_alias(i[2][0], aliases) and i[2][1] == season][0]
                except:
                    url = [i[0] for i in results if cleantitle.match_alias(i[1], aliases)][0]
                url = self.base_link + '%s/watching.html?ep=%s' % (url, episode)
            else:
                results = [(i[0], i[1], re.findall(r'\((\d{4})', i[1])) for i in r]
                try:
                    r = [(i[0], i[1], i[2][0]) for i in results if len(i[2]) > 0]
                    url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year)][0]
                except:
                    url = [i[0] for i in results if cleantitle.match_alias(i[1], aliases)][0]
                url = self.base_link + '%s/watching.html' % url
            r = client.scrapePage(url).text
            try:
                check_year = re.findall(r'Release:.+?(\d{4})', r)[0]
                check_year = cleantitle.match_year(check_year, year, data['year'])
            except:
                check_year = 'Failed to find year info.' # Used to fake out the year check code.
            if not check_year:
                return self.results
            try:
                qual = client_utils.parseDOM(r, 'span', attrs={'class': 'quality'})[0]
            except:
                qual = ''
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'les-content'})
            if 'tvshowtitle' in data:
                links = client_utils.parseDOM(r, 'a', attrs={'episode-data': episode}, ret='player-data')
            else:
                links = client_utils.parseDOM(r, 'a', ret='player-data')
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


