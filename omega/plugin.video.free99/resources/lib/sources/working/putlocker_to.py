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
        self.domains = ['putlocker.to']
        self.base_link = 'https://w5.putlocker.to'
        self.search_link = '/?s=%s'


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
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            self.cookie = client.request(self.base_link, output='cookie', timeout='5')
            r = client.request(search_url, cookie=self.cookie, timeout='5')
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', ret='oldtitle'), re.findall('/release-year/(\d{4})"', i)) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year)][0]
            if 'tvshowtitle' in data:
                url = url[:-1] if url.endswith('/') else url
                url = url.replace('/series/', '/episode/')
                url = url + '-season-%s-episode-%s/' % (season, episode)
            html = client.request(url, cookie=self.cookie, timeout='5')
            links = client_utils.parseDOM(html, 'iframe', ret='src')
            for link in links:
                for source in scrape_sources.process(hostDict, link):
                    self.results.append(source)
            return self.results
        except Exception:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


