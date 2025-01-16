# -*- coding: utf-8 -*-

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        try:
            self.results = []
            self.domains = ['main.dailyflix.stream', 'dailyflix.stream']
            self.base_link = 'https://main.dailyflix.stream'
            self.search_link = '/?s=%s'
            self.cookie = client.request(self.base_link, output='cookie', timeout='5')
        except:
            #log_utils.log('__init__', 1)
            return


#Sites TV Show section is here...
#https://watch.dailyflix.stream


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            movie_title = cleantitle.get_plus(title)
            check_title = cleantitle.get(title)
            movie_link = self.base_link + self.search_link % movie_title
            html = client.request(movie_link, cookie=self.cookie)
            tbody = client_utils.parseDOM(html, 'tbody')[0]
            items = client_utils.parseDOM(tbody, 'tr')
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a')) for i in items]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            url = [i[0] for i in r if check_title == cleantitle.get(i[1])][0]
            return url
        except:
            #log_utils.log('movie', 1)
            return


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            html = client.request(url, cookie=self.cookie)
            links = []
            alt_servers = client_utils.parseDOM(html, 'div', attrs={'class': 'motopress-button-obj'})
            links += [client_utils.parseDOM(i, 'a', ret='href')[0] for i in alt_servers]
            links += client_utils.parseDOM(html, 'iframe', ret='src')
            for link in links:
                for source in scrape_sources.process(hostDict, link):
                    self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


