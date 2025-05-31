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
        self.domains = ['putlocker.unblockit.asia', 'putlocker.unblockit.boo', 'putlocker.unblockit.bio',
            'putlocker.unblockit.ink', 'putlocker.unblockit.page', 'putlocker.unblockit.nz'
        ]
        self.base_link = 'https://putlocker.unblockit.asia'
        self.search_link = '/search/%s/'
        self.notes = 'Tv Shows seem to have the wrong episode sources, error being somewhere in the host site. Dupe of putlockers_do.'


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
            ##### Ghetto block to disable use with tvshows begins.
            if 'tvshowtitle' in data:
                return self.results
            ##### Ghetto block to disable use with tvshows ends.
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.geturl(title)
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            query1 = '%s-season-%s' % (title, season) if 'tvshowtitle' in data else title
            query2 = '%s-%s-season-%s' % (title, year, season) if 'tvshowtitle' in data else '%s-%s' % (title, year)
            check1 = cleantitle.get(query1)
            check2 = cleantitle.get(query2)
            url = self.base_link + self.search_link % (query1.replace('-', '+'))
            self.cookie = client.request(self.base_link, output='cookie', timeout='5')
            html = client.request(url, cookie=self.cookie)
            results = client_utils.parseDOM(html, 'div', attrs={'class': 'ml-item'})
            results = [(client_utils.parseDOM(i, 'a', ret='cid')[0], client_utils.parseDOM(i, 'a', ret='title')[0]) for i in results]
            try:
                url = [i[0] for i in results if check1 == cleantitle.get(i[1])][0]
            except:
                url = [i[0] for i in results if check2 == cleantitle.get(i[1])][0]
            url = self.base_link + url
            r = client.request(url, cookie=self.cookie)
            try:
                check_year = re.findall(r'Release:</strong>.+?/released/(\d+)/', r)[0]
                check_year = cleantitle.match_year(check_year, year, data['year'])
            except:
                check_year = 'Failed to find year info.' # Used to fake out the year check code.
            if not check_year:
                return self.results
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'les-content'})
            if 'tvshowtitle' in data:
                check_epi1 = 'Episode %s' % episode
                check_epi2 = 'Episode %s: %s' % (episode, data['title'])
                check_epi3 = 'Episode %02d: %s' % (int(episode), data['title'])
                try:
                    results = zip(client_utils.parseDOM(r, 'a', ret='title'), client_utils.parseDOM(r, 'a', ret='data-file'))
                    links = [i[1] for i in results if (check_epi1 == i[0] or check_epi2 == i[0] or check_epi3 == i[0])]
                except:
                    try:
                        links = client_utils.parseDOM(r, 'a', attrs={'title': check_epi1}, ret='data-file')
                    except:
                        pass
                    try:
                        links += client_utils.parseDOM(r, 'a', attrs={'title': check_epi2}, ret='data-file')
                    except:
                        pass
                    try:
                        links += client_utils.parseDOM(r, 'a', attrs={'title': check_epi3}, ret='data-file')
                    except:
                        pass
            else:
                links = client_utils.parseDOM(r, 'a', ret='data-file')
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


