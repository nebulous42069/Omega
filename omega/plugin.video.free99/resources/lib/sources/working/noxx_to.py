# -*- coding: utf-8 -*-
                 
#Credit to JewBMX for base code

import re

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import scrape_sources



class source:
    def __init__(self):
        self.results = []
        self.domains = ['noxx.to']
        self.base_link = 'https://noxx.to'


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = cleantitle.geturl(tvshowtitle)
            return url
        except Exception:
            #log_utils.log('tvshow', 1)
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            url = self.base_link + '/tv/%s/%s/%s/' % (url, season, episode)
            return url
        except Exception:
            #log_utils.log('episode', 1)
            return


    def sources(self, url, hostDict):
        try:
            if url == None:
                return self.results
            html = client.scrapePage(url).text
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


