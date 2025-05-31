# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils

DOM = client_utils.parseDOM


class source:
    def __init__(self):
        self.results = []
        self.domains = ['goku.watch', 'goku.sx', 'goku.to']
        self.base_link = 'https://goku.watch'
        self.search_link = '/search?keyword=%s'


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
            r = DOM(r, 'div', attrs={'class': 'movie-info'})
            r = [(DOM(i, 'a', attrs={'class': 'movie-link'}, ret='href'), DOM(i, 'h3', attrs={'class': 'movie-name'}), DOM(i, 'div', attrs={'class': 'info-split'})) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            if 'tvshowtitle' in data:
                result_url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and i[0].startswith('/series/')][0]
            else:
                r = [(i[0], i[1], re.findall(r'<div>(\d{4})</div>', client_utils.clean_html(i[2]))) for i in r]
                r = [(i[0], i[1], i[2][0]) for i in r if len(i[2]) > 0]
                result_url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year) and i[0].startswith('/movie/')][0]
            item_id = re.findall(r'([0-9]+)$', result_url)[0]
            if 'tvshowtitle' in data:
                check_season = 'Season %s' % season
                seasons_url = self.base_link + '/ajax/movie/seasons/%s' % item_id
                r = client.scrapePage(seasons_url).text
                r = DOM(r, 'div', attrs={'class': 'dropdown-menu dropdown-primary'})[0]
                r = zip(DOM(r, 'a', ret='data-id'), DOM(r, 'a'))
                item_season_id = [i[0] for i in r if check_season == client_utils.remove_tags(i[1])][0]
                check_episode = 'Eps %s:' % episode
                episodes_url = self.base_link + '/ajax/movie/season/episodes/%s' % item_season_id
                r = client.scrapePage(episodes_url).text
                r = zip(DOM(r, 'a', ret='data-id'), DOM(r, 'a'))
                item_episode_id = [i[0] for i in r if check_episode in i[1]][0]
                servers_url = self.base_link + '/ajax/movie/episode/servers/%s' % item_episode_id
            else:
                result_url = self.base_link + result_url.replace('/movie/', '/watch-movie/')
                new_result_url = client.request(result_url, timeout='10', output='geturl')
                new_item_id = re.findall(r'([0-9]+)$', new_result_url)[0]
                servers_url = self.base_link + '/ajax/movie/episode/servers/%s' % new_item_id
            r = client.scrapePage(servers_url).text
            server_ids = DOM(r, 'a', ret='data-id')
            for server_id in server_ids:
                try:
                    get_link = self.base_link + '/ajax/movie/episode/server/sources/%s' % server_id
                    link_json = client.scrapePage(get_link).json()
                    try:
                        link = link_json['data']['link']
                    except: #  Forgot to look at this but i think its always data{link
                        link = link_json['link']
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


