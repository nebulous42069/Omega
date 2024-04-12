# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['epxmovies.net']
        self.base_link = 'https://epxmovies.net'
        self.search_link = '/search.php?search=%s'


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
            search_title = cleantitle.get_plus(title)
            search_link = self.base_link + self.search_link % search_title
            r = client.scrapePage(search_link).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': r'col-lg-2 col-md-3 wow.*?'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'h5')) for i in r if not 'Hindi Dubbed' in i]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            r = [(i[0], re.findall('(.+?) [(](\d{4})[)]', i[1])) for i in r]
            r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
            try:
                r_link = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and cleantitle.match_year(i[1][1], year)][0]
            except:
                r_link = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and '/tv/' in i[0]][0]
            log_utils.log('sources r_link:  '+repr(r_link))
            if r_link.startswith('..'):
                r_link = r_link.replace('..', '')
            if 'tvshowtitle' in data:
                r_link = r_link.replace('-s1', '-s%s'%season)
            else:
                r_link = r_link.replace('/movieid?', '/svop4/movie_srv?')
            r_url = self.base_link + r_link
            log_utils.log('sources r_url:  '+repr(r_url))
            html = client.scrapePage(r_url).text
            links = []
            servers = re.findall(r'''function\s+change\s*\(id\)\s*\{(.+?)}''', html, re.DOTALL | re.IGNORECASE)[0]
            log_utils.log('sources servers:  '+repr(servers))
            links += re.findall(r'''['"](http.+?)['"]''', servers, re.DOTALL | re.IGNORECASE)
            log_utils.log('sources links:  '+repr(links))
            if 'tvshowtitle' in data:
                seaepi = 's%02de%02d' % (int(season), int(episode))
                log_utils.log('sources seaepi:  '+repr(seaepi))
                s_link = [i for i in links if seaepi in i][0]
                log_utils.log('sources s_link:  '+repr(s_link))
            return
            
            
            for link in links:
                if any(x in link for x in self.domains):
                    try:
                        html = client.scrapePage(link).text
                        vurls = []
                        vurls += client_utils.parseDOM(html, 'iframe', ret='src')
                        vurls += client_utils.parseDOM(html, 'iframe', ret='class src')
                        for vurl in vurls:
                            if '1movietv' in vurl:
                                continue
                            for source in scrape_sources.process(hostDict, vurl):
                                self.results.append(source)
                    except:
                        #log_utils.log('sources', 1)
                        pass
                else:
                    for source in scrape_sources.process(hostDict, link):
                        self.results.append(source)
            return self.results
        except:
            log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


