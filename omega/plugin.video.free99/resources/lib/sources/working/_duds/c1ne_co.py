# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import source_utils
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['c1ne.co']
        self.base_link = 'https://c1ne.co'
        self.search_link = '/?s=%s'


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
            if url is None:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            imdb = data['imdb']
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_term = '%s Season %s' % (title, season) if 'tvshowtitle' in data else '%s %s' % (title, year)
            search_url = self.base_link + self.search_link % cleantitle.get_plus(search_term)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'DNT': '1'
            }
            html = client.scrapePage(search_url, headers=headers).text
            r = client_utils.parseDOM(html, 'article', attrs={'id': r'post.+?'})
            r = [(client_utils.parseDOM(i, 'a', attrs={'rel': 'bookmark'}, ret='href'), client_utils.parseDOM(i, 'a', attrs={'rel': 'bookmark'})) for i in r]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            if 'tvshowtitle' in data:
                try:
                    r = [(i[0], re.findall(r'(.+?) Season (\d+)', client_utils.replaceHTMLCodes(i[1]))) for i in r]
                    r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
                    url = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and i[1][1] == season][0]
                except:
                    url = [i[0] for i in r if cleantitle.geturl(search_term) in i[0]][0]
            else:
                try:
                    r = [(i[0], re.findall(r'(.+?) \((\d+)\)', client_utils.replaceHTMLCodes(i[1]))) for i in r]
                    r = [(i[0], i[1][0]) for i in r if len(i[1]) > 0]
                    url = [i[0] for i in r if cleantitle.match_alias(i[1][0], aliases) and cleantitle.match_year(i[1][1], year)][0]
                except:
                    url = [i[0] for i in r if cleantitle.geturl(search_term) in i[0]][0]
            r = client.scrapePage(url, headers=headers).text
            check_it = re.findall(r'imdb.com/title/(tt\d+)/', r)[0]
            if not check_it == imdb:
                return self.results
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'su-box-content su-u-clearfix su-u-trim'})[0]
            if 'tvshowtitle' in data:
                check_term = 'Episode %s' % episode
                r = client_utils.parseDOM(r, 'tr')
                r = [(client_utils.parseDOM(i, 'a', attrs={'class': 'su-button su-button-style-flat'}, ret='href'), client_utils.parseDOM(i, 'td')) for i in r]
                r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
                links = [i[0] for i in r if i[1] == check_term]
            else:
                links = client_utils.parseDOM(r, 'a', attrs={'class': 'su-button su-button-style-flat'}, ret='href')
            for link in links:
                try:
                    link = "https:" + link if link.startswith('//') else link
                    html = client.scrapePage(link, headers=headers).text
                    juicycode = client_utils.unjuiced2(html) # Thanks to resolveurl for this one lol.
                    if juicycode:
                        sources = re.findall(r'"sources":\[(.+?)\],', juicycode)[0]
                        sources = re.findall(r'{"type":"(.+?)","label":"(.+?)","file":"(https.+?)"}', sources.replace('\\', ''))
                        for info, qual, file in sources:
                            try:
                                quality, info = source_utils.get_release_quality(qual, info)
                                link = file + source_utils.append_headers({'User-Agent': client.UserAgent, 'Referer': self.base_link})
                                self.results.append({'source': 'Direct', 'quality': quality, 'info': info, 'url': link, 'direct': True})
                            except:
                                #log_utils.log('sources', 1)
                                pass
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


