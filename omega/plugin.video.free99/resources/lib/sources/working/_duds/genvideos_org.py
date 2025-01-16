# -*- coding: utf-8 -*-

import re

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['afdah.me', 'genvideos.org', 'genvideos.co']
        self.base_link = 'https://afdah.me'
        self.search_link = '/results?q=%s'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            movie_title = cleantitle.get_plus(title)
            check_term = '%s (%s)' % (title, year)
            check_title = cleantitle.get_plus(check_term)
            search_url = self.base_link + self.search_link % movie_title
            html = client.scrapePage(search_url).text
            r = client_utils.parseDOM(html, 'div', attrs={'class': 'cell_container'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', ret='title')) for i in r]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            url = [i[0] for i in r if cleantitle.get_plus(i[1]).startswith(check_title)][0]
            url = self.base_link + url
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
                qual = client_utils.parseDOM(html, 'div', attrs={'class': 'video_quality'})[0]
            except:
                qual = ''
            links = re.compile(r'''frame_url = ['"](.+?)['"];''', re.DOTALL).findall(html)
            for link in links:
                for source in scrape_sources.process(hostDict, link, info=qual):
                    self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


