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
        self.domains = ['movieffm.net']
        self.base_link = 'https://movieffm.net'
        self.notes = 'Might not be worth using, might need more work, but seems quick and decent sources besides the spam start.'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
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
            year = data['year'] # Maybe add a year check.
            se_check = 'Season %s ' % season
            ep_check = '%02d' % int(episode)
            if 'tvshowtitle' in data:
                search_link = self.base_link + '/tvshows/%s/' % cleantitle.geturl(title)
            else:
                search_link = self.base_link + '/movies/%s/' % cleantitle.geturl(title)
            html = client.scrapePage(search_link).text
            if 'tvshowtitle' in data:
                r = client_utils.parseDOM(html, 'div', attrs={'id': 'seasons'})[0]
                r = client_utils.parseDOM(html, 'div', attrs={'class': 'se-c'})
                r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'span', attrs={'class': 'title'})) for i in r]
                r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
                url = [i[0] for i in r if se_check in i[1]][0]
                html = client.scrapePage(url).text
                links = re.findall(r'{"name":"(.+?)","url":"(.+?)"}', html)
            else:
                links = re.findall(r'"url":"(.+?)","type":"(.+?)","ep"', html)
            for link, sinfo in links:
                try:
                    if 'tvshowtitle' in data:
                        if not ep_check == link:
                            continue
                        link = sinfo
                        qual = ''
                    else:
                        qual = sinfo
                    item = scrape_sources.make_direct_item(hostDict, link, host=None, info=qual, referer=url, prep=True)
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
        return url


