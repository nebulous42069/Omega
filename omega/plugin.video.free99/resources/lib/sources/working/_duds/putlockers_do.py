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
        self.domains = ['putlockers.do']
        self.base_link = 'https://www4.putlockers.do'
        self.search_link = '/search/%s/'
        self.notes = 'Tv Shows seem to have the wrong episode sources error being somewhere in the site. Dupe of putlocker_unblockit.'


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
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            episode_check = 'Episode %s' % episode
            episode_check = cleantitle.get_plus(episode_check)
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search = '%s Season %s' % (title, season) if 'tvshowtitle' in data else title
            url = self.base_link + self.search_link % cleantitle.get_utf8(search)
            r = client.scrapePage(url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            if not r and 'tvshowtitle' in data:
                url = self.base_link + self.search_link % cleantitle.get_utf8(title)
                r = client.scrapePage(url).text
                r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = zip(client_utils.parseDOM(r, 'a', ret='cid'), client_utils.parseDOM(r, 'a', ret='title'))
            if 'tvshowtitle' in data:
                r = [(i[0], i[1], re.findall(r'(.*?)\s+-\s+Season\s+(\d)', i[1])) for i in r]
                r = [(i[0], i[1], i[2][0]) for i in r if len(i[2]) > 0]
                url = [i[0] for i in r if cleantitle.match_alias(i[2][0], aliases) and i[2][1] == season][0]
            else:
                r = [(i[0], i[1]) for i in r]
                url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases)][0]
            if not url:
                return self.results
            url = self.base_link + url
            r = client.scrapePage(url).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'les-content'})
            if 'tvshowtitle' in data:
                r = zip(client_utils.parseDOM(r, 'a', ret='data-file'), client_utils.parseDOM(r, 'a', ret='title'))
                r = [(i[0], i[1]) for i in r]
                links = [i[0] for i in r if (episode_check == cleantitle.get_plus(i[1]) or cleantitle.get_plus(i[1]).startswith(episode_check+'+'))]
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


