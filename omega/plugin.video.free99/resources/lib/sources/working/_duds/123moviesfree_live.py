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
        self.domains = ['123movies-free.live']
        self.base_link = 'https://123movies-free.live'
        self.search_link = '/index.php?do=search&filter=true'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            search_url = self.base_link + self.search_link
            post = ('do=search&subaction=search&search_start=0&full_search=0&result_from=1&story=%s' % cleantitle.get_utf8(title))
            html = client.scrapePage(search_url, post=post).text
            html = html.replace('\n', '')
            r = client_utils.parseDOM(html, 'div', attrs={'class': 'ml-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'img', ret='alt'), client_utils.parseDOM(i, 'div', attrs={'class': 'jt-info jt-imdb'})) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year)][0]
            if not url:
                url = imdb
            return url
        except:
            #log_utils.log('movie', 1)
            return imdb


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            if url.startswith('tt'):
                html = ''
                qual = ''
                try:
                    iframe_url = 'https://simplemovie.xyz/movie/%s' % url
                    html += client.scrapePage(iframe_url).text
                except:
                    pass
                try:
                    script_url = 'https://simplemovie.xyz/ddl/%s' % url
                    html += client.scrapePage(script_url).text
                except:
                    pass
            else:
                html = client.scrapePage(url).text
                try:
                    qual = client_utils.parseDOM(html, 'span', attrs={'class': 'quality'})[0]
                except:
                    qual = ''
                try:
                    iframe_url = client_utils.parseDOM(html, 'iframe', ret='src')[0]
                    html += client.scrapePage(iframe_url).text
                except:
                    pass
                try:
                    script_url = re.compile(r'<script src="(https://simplemovie.xyz/.+?)"').findall(html)[0]
                    html += client.scrapePage(script_url).text
                except:
                    pass
            if html:
                html = html.replace("\\", "")
                links = []
                links += re.compile(r'''<tr onclick="window\.open\( \\'(.+?)\\' \)">''').findall(html)
                links += client_utils.parseDOM(html, 'a', ret='data-link')
                links += client_utils.parseDOM(html, 'a', ret='class data-link')
                links += client_utils.parseDOM(html, 'div', ret='data-link')
                links += client_utils.parseDOM(html, 'div', ret='class data-link')
                links += client_utils.parseDOM(html, 'li', ret='data-link')
                links += client_utils.parseDOM(html, 'li', ret='class data-link')
                for link in links:
                    try:
                        if link.endswith('voe.sx/e/') or link.endswith('voe.sx/'):
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


