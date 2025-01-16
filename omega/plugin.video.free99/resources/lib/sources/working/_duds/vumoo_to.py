# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
from resources.lib.modules import source_utils
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['vumoo.to']
        self.base_link = 'https://vumoo.to'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if tvshowtitle == 'House':
            tvshowtitle = 'House M.D.'
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'year': year}
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
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['year']
            search_title = cleantitle.geturl(title)
            se_check = 's%02de%02d' % (int(season), int(episode))
            if 'tvshowtitle' in data:
                search_link = self.base_link + '/tv-series/%s-season-%s/' % (search_title, season)
            else:
                search_link = self.base_link + '/movies/%s-%s/' % (search_title, year)
            html = client.scrapePage(search_link).text
            links = zip(client_utils.parseDOM(html, 'a', attrs={'class': 'play'}, ret='embedUrl'), client_utils.parseDOM(html, 'a', attrs={'class': 'play'}))
            for link, sinfo in links:
                try:
                    if 'tvshowtitle' in data:
                        if not se_check == sinfo:
                            continue
                        qual = 'HD'
                    else:
                        qual = sinfo
                    item = scrape_sources.make_direct_item(hostDict, link, host=None, info=qual, referer=None, prep=True)
                    if item:
                        if not scrape_sources.check_host_limit(item['source'], self.results):
                            self.results.append(item)
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        try:
            html = client.scrapePage(url, referer=self.base_link).text
            link = re.compile(client_utils.regex_pattern6).findall(html)[0]
            link = "https:" + link if link.startswith('//') else link
            link += source_utils.append_headers({'Referer': url})
            return link
        except:
            #log_utils.log('resolve', 1)
            return url


