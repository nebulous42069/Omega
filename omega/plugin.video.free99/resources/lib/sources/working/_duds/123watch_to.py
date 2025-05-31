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
        self.domains = ['123watch.to']
        self.base_link = 'https://123watch.to'
        self.search_link = '/?search=%s'
        self.notes = 'this site seems to use only embed hosts and doesnt always return results.'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            title = data['title']
            year = data['year']
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            r = client.scrapePage(search_url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'product__item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), re.findall(r'">(.+?)</a></h5>', i), re.findall(r'<li .+?(\d{4})</li></a>', i)) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year)][0]
            url = self.base_link + url.replace('./?details=', '/?details=')
            r = client.scrapePage(url).text #https://123watch.to/?details=284053-free-thor-ragnarok-movie
            url = re.findall(r'<a href="(.+?)" class="follow-btn"><i class="fa fa-play"></i> Watch</a>', r)[0]
            url = self.base_link + url.replace('./?watch=', '/?watch=')
            html = client.scrapePage(url).text #https://123watch.to/?watch=thor-ragnarok-movie-hd-284053
            links = client_utils.parseDOM(html, 'iframe', ret='src')
            for link in links:
                try:
                    for source in scrape_sources.process(hostDict, link):
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


