# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
from resources.lib.modules import log_utils

DOM = client_utils.parseDOM


class source:
    def __init__(self):
        self.results = []
        self.domains = ['1movies.la']
        self.base_link = 'https://1movies.la'
        self.search_link = '/search/%s'


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
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            r = client.scrapePage(search_url).text
            r = DOM(r, 'div', attrs={'class': 'ml-item'})
            r = [((DOM(i, 'a', ret='href')), DOM(i, 'span', attrs={'class': 'mli-info'}), DOM(i, 'a', ret='title')) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            if 'tvshowtitle' in data:   # get season link
                check_season = 'season %s' % season
                result_url = [i[0] for i in r if data['tvshowtitle'] in i[2] and check_season in i[2].lower() and i[0].startswith('/tv/')][0]
                url = self.base_link + result_url
            else:
                result_url = [i[0] for i in r if cleantitle.match_alias(i[2], aliases) and cleantitle.match_year(i[1], year) and i[0].startswith('/movie/')][0]
                url = self.base_link + result_url
            r = client.scrapePage(url).text
            if 'tvshowtitle' in data:  # get episode link
                r = DOM(r, 'div', attrs={'class': 'les-content'})
                r = zip(DOM(r, 'a', ret='href'), DOM(r, 'a'))
                check_episode = 'episode %s' % episode
                episode_url = [i[0] for i in r if check_episode == client_utils.remove_tags(i[1]).lower()][0]
                url = self.base_link + episode_url
                r = client.scrapePage(url).text
                r = DOM(r, 'div', attrs={'class': 'les-content'})
                result_links = list(zip(DOM(r, 'a', ret='data-file'), DOM(r, 'a')))
            else:  # movies
                r = DOM(r, 'div', attrs={'class': 'les-content'})
                result_links = list(zip(DOM(r, 'a', ret='data-file'), DOM(r, 'a')))
            hosters = []
            for link, hoster in result_links:
                try:
                    linknew = client.request(link, output='geturl')
                    for source in scrape_sources.process(hostDict, linknew):
                        self.results.append(source)
                except:
                    # log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


