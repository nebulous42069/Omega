# -*- coding: utf-8 -*-

import re

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['gomoviz1.biz', 'gomoviz1.top', 'gomoviz1.pro', 'gomoviz1.bond', 'gomoviz1.ink', 'gomoviz1.icu',
            '0gomoviz.me', 'gomoviz1.click', 'gomoviz.store', 'gomoviz.gay', '0gomoviz.net', '0gomoviz.com', 'gomoviz.top',
            'gomoviz.uno', 'gomoviz.cyou', 'gomoviz.online', 'gomoviz.us', 'gomoviz.xyz', 'gomoviz.org', 'gomoviz.live'
        ]
        self.base_link = 'https://gomoviz1.biz'
        self.search_link = '/?s=%s'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            r = client.scrapePage(search_url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), re.findall(r'(\d{4})', i), client_utils.parseDOM(i, 'a', ret='oldtitle')) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            r = [(i[0], i[1], re.findall(r'(.+?)(?:\(|$)', i[2])) for i in r]
            r = [(i[0], i[1], i[2][0]) for i in r if len(i[2]) > 0]
            url = [i[0] for i in r if cleantitle.match_alias(i[2], aliases) and cleantitle.match_year(i[1], year)][0]
            return url
        except:
            #log_utils.log('movie', 1)
            return


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            html = client.scrapePage(url).text
            try:
                qual = client_utils.parseDOM(html, 'span', attrs={'class': 'quality'})[0]
            except:
                qual = ''
            links = []
            links += client_utils.parseDOM(html, 'iframe', ret='src')
            links += client_utils.parseDOM(html, 'a', attrs={'class': 'su-button su-button-style-flat'}, ret='href')
            for link in links:
                try:
                    if any(i in link for i in ['youtube.com', 'abcvideo.cc']):
                        continue
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


