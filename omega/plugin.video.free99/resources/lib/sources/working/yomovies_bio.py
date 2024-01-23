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
        self.domains = ['yomovies.ltd', 'yomovies.monster', 'yomovies.baby', 'yomovies.team', 'yomovies.work',
            'yomovies.hair', 'yomovies.bid', 'yomovies.bio', 'yomovies.rest', 'yomovies.kim', 'yomovies.run',
            'yomovies.fyi', 'yomovies.rs', 'yomovies.cloud', 'yomovies.skin', 'yomovies.vip', 'yomovies.ws',
            'yomovies.bz', 'yomovies.lol'
        ]
        self.base_link = 'https://yomovies.ltd'
        self.search_link = '/?s=%s'


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
            search_url = self.base_link + self.search_link % cleantitle.get_plus(search_term)
            r = client.scrapePage(search_url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            if not r and 'tvshowtitle' in data:
                search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
                r = client.scrapePage(search_url).text
                r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), re.findall('/release-year/(\d{4})/"', i), client_utils.parseDOM(i, 'a', ret='oldtitle')) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            if 'tvshowtitle' in data:
                r = [(i[0], i[1], re.findall('(.+?) Season (\d+)$', client_utils.replaceHTMLCodes(i[2]))) for i in r]
                r = [(i[0], i[1], i[2][0]) for i in r if len(i[2]) > 0]
                url = [i[0] for i in r if cleantitle.match_alias(i[2][0], aliases) and cleantitle.match_year(i[1], year, data['year']) and i[2][1] == season][0]
                r = client.scrapePage(url).text
                r = client_utils.parseDOM(r, 'div', attrs={'class': 'les-content'})[0]
                r = zip(client_utils.parseDOM(r, 'a', ret='href'))
                check_epi = '-season-%s-episode-%s' % (season, episode)
                url = [i[0] for i in r if i[0].endswith(check_epi)][0]
            else:
                r = [(i[0], i[1], re.findall('(.+?)(?:\(\d+\)|$)', client_utils.replaceHTMLCodes(i[2]))) for i in r]
                r = [(i[0], i[1], i[2][0]) for i in r if len(i[2]) > 0]
                url = [i[0] for i in r if cleantitle.match_alias(i[2], aliases) and cleantitle.match_year(i[1], year)][0]
            html = client.scrapePage(url).text
            try:
                r = client_utils.parseDOM(html, 'div', attrs={'class': 'les-content'})
                qual = client_utils.parseDOM(r, 'a')[0]
            except:
                qual = ''
            links = client_utils.parseDOM(html, 'iframe', ret='src')
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


