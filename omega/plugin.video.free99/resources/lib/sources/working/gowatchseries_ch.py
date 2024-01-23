# -*- coding: utf-8 -*-
                 
#Credit to JewBMX for base code

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import scrape_sources



class source:
    def __init__(self):
        self.results = []
        self.domains = ['gowatchseries.tv', 'gowatchseries.ch', 'gowatchseries.live', 'gowatchseries.online',
            'gowatchseries.io', 'gowatchseries.co', 'gowatchseries.bz'
        ]
        self.base_link = 'http://www5.gowatchseries.tv'
        self.search_link = '/search.html?keyword=%s'


    def movie(self, imdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
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
            search = '%s Season %s' % (title, season) if 'tvshowtitle' in data else title
            search_url = self.base_link + self.search_link % cleantitle.get_utf8(search)
            r = client.scrapePage(search_url).text
            r = client_utils.parseDOM(r, 'ul', attrs={'class': 'listing items'})[0]
            r = client_utils.parseDOM(r, 'li')
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'img', ret='alt')) for i in r]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            if 'tvshowtitle' in data:
                r = [(i[0], re.findall('(.+?) Season (\d+)', i[1])) for i in r]
                r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
                url = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and i[1][1] == season][0]
            else:
                results = [(i[0], i[1], re.findall('\((\d{4})', i[1])) for i in r]
                try:
                    r = [(i[0], i[1], i[2][0]) for i in results if len(i[2]) > 0]
                    url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year)][0]
                except:
                    url = [i[0] for i in results if cleantitle.match_alias(i[1], aliases)][0]
            url = '/' + url if not url.startswith('/') else url
            url = self.base_link +'%s-episode-%s' % (url.replace('/info', ''), episode)
            r = client.scrapePage(url).text
            if not 'tvshowtitle' in data: # My lazy workaround for shows not passing this when they should lol.
                check_year = client_utils.parseDOM(r, 'div', attrs={'class': 'right'})[0]
                check_year = re.findall('(\d{4})', check_year)[0]
                check_year = cleantitle.match_year(check_year, year, data['year'])
                if not check_year:
                    return self.results
            links = client_utils.parseDOM(r, 'li', ret='data-video')
            for link in links:
                for source in scrape_sources.process(hostDict, link):
                    self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


