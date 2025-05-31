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
        self.results = [] ## Mirror Holder  https://hollymoviehd-official.com/
        self.domains = ['hollymoviehd.cc'] # Alt domains:  nmovies.cc  yeshd.net
        self.base_link = 'https://hollymoviehd.cc'
        self.search_link = '/?s=%s'
        self.notes = 'Dupe of novamovie_net. Search has blockage.'


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
            search = '%s Season %s' % (title, season) if 'tvshowtitle' in data else title
            search_url = self.base_link + self.search_link % cleantitle.get_plus(search)
            try:
                r = client.scrapePage(search_url).text
                r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
                if not r and 'tvshowtitle' in data:
                    search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
                    r = client.scrapePage(search_url).text
                    r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
                r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', ret='title')) for i in r]
                r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
                if 'tvshowtitle' in data:
                    r = [(i[0], re.findall(r'(.+?) Season (\d+)', i[1])) for i in r]
                    r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
                    url = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and i[1][1] == season][0]
                    url = url.replace('/series/', '/episode/')
                    url = url[:-1] if url.endswith('/') else url
                    url = url + '-episode-%s/' % episode
                else:
                    try:
                        r = [(i[0], re.findall(r'(.+?) \((\d{4})', i[1])) for i in r]
                        r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
                        url = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and cleantitle.match_year(i[1][1], year)][0]
                    except:
                        url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases)][0]
            except:
                if 'tvshowtitle' in data:
                    url = self.base_link + '/episode/%s-season-%s-episode-%s/' % (cleantitle.get_dash(title), season, episode)
                else:
                    url = self.base_link + '/%s-%s/' % (cleantitle.get_dash(title), year)
            html = client.scrapePage(url).text
            links = client_utils.parseDOM(html, 'a', attrs={'target': '_blank'}, ret='href')
            for link in links:
                try:
                    if link == '#' or any(x in link for x in ['pkayprek.com', 'facebook.com', 'imdb.com']):
                        continue
                    if any(x in link for x in ['getlinkstream.xyz', 'novastream.cloud', 'novalinks.online']):
                        html = client.scrapePage(link).text
                        try:
                            qual = client_utils.parseDOM(html, 'title')[0]
                        except:
                            qual = ''
                        vlinks = client_utils.parseDOM(html, 'a', ret='href')
                        for vlink in vlinks:
                            if 'pkayprek.com' in vlink:
                                continue
                            for source in scrape_sources.process(hostDict, vlink, info=qual):
                                if scrape_sources.check_host_limit(source['source'], self.results):
                                    continue
                                self.results.append(source)
                    else:
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


