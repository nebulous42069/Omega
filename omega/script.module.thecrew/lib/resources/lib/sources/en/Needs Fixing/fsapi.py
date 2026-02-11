# -*- coding: utf-8 -*-

'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import re, base64

from six import ensure_text

from resources.lib.modules import client
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils

try: from urlparse import parse_qs, urljoin, urlparse
except ImportError: from urllib.parse import parse_qs, urljoin, urlparse
try: from urllib import urlencode, quote_plus
except ImportError: from urllib.parse import urlencode, quote_plus

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['fsapi.xyz']
        self.base_link = 'https://fsapi.xyz'
        self.search_link = '/movie/%s'
        self.search_link2 = '/tv-imdb/%s-%s-%s'

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None: return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            hostDict = hostprDict + hostDict
            direct_stream = tuple(source_utils.supported_video_extensions())

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            if not data['imdb'] or data['imdb'] == '0':
                return sources

            if 'tvshowtitle' in data:
                query = self.search_link2 % (data['imdb'], data['season'], data['episode'])
            else:
                query = self.search_link % data['imdb']

            url = urljoin(self.base_link, query)
            posts = client.request(url)
            #log_utils.log('fsapi_posts: ' + posts)
            r = re.findall('<a href="(.+?)" rel', posts)
            r = client.parseDOM(posts, 'a', ret='href', attrs={'target': 'iframe_a'})
            urls = [u.split('url=')[1] for u in r]
            urls = [ensure_text(base64.b64decode(url), errors='ignore') for url in urls]
            urls = ['https:' + url if url.startswith('//') else url for url in urls]
            urls = list(set(urls))
            #log_utils.log('fsapi_all_urls: ' + repr(urls))

            for url in urls:

                try:
                    url = url.replace('vidcloud.icu', 'vidembed.io').replace(
                                      'vidcloud9.com', 'vidembed.io').replace(
                                      'vidembed.cc', 'vidembed.io').replace(
                                      'vidnext.net', 'vidembed.me')
                    if 'vidembed' in url:
                        for source in self.get_vidembed(url, hostDict):
                            sources.append(source)

                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})

                    elif '/hls/' in url or url.endswith(direct_stream):
                        sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': url, 'direct': True, 'debridonly': False})

                    # elif 'vidsrc' in url: # vidsrc turned on a scraper of its own
                        # try:
                            # r = client.request(url, headers={'User-Agent': client.agent(), 'Referer': 'https://v2.vidsrc.me'})
                            # r = re.findall('data-hash="(.+?)"', r)[0]
                            # log_utils.log('fsapi_vidsrc_r: ' + repr(r))
                            # r = 'https://v2.vidsrc.me/src/%s' % r
                            # r2 = client.request(r, headers={'User-Agent': client.agent(), 'Referer': 'https://v2.vidsrc.me'})
                            # links = re.findall("'player' src='(.+?)'", r2) + re.findall('"file": "(.+?)"', r2)
                            # log_utils.log('fsapi_vidsrc_links: ' + repr(links))
                            # links = [link + '|Referer=https://vidsrc.me' for link in links]
                            # for url in links:
                                # url = url if url.startswith('http') else 'https:{0}'.format(url)
                                # sources.append({'source': 'CDN', 'quality': '720p', 'language': 'en', 'url': url, 'direct': True, 'debridonly': False})
                        # except:
                            # pass
                except:
                    log_utils.log('FSAPI Exception', 1)
                    pass

            return sources
        except:
            log_utils.log('FSAPI Exception', 1)
            return sources

    def resolve(self, url):
        #log_utils.log('FSAPI url: ' + repr(url))
        return url

    def get_vidembed(self, link, hostDict):
        sources = []
        try:
            html = client.request(link)
            urls = client.parseDOM(html, 'li', ret='data-video')
            if urls:
                for url in urls:
                    url = url.replace('vidcloud.icu', 'vidembed.io').replace(
                                      'vidcloud9.com', 'vidembed.io').replace(
                                      'vidembed.cc', 'vidembed.io').replace(
                                      'vidnext.net', 'vidembed.me')
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        url = url.split('&title=')[0]
                        sources.append({'source': host, 'quality': '720p', 'language': 'en', 'url': url, 'direct': False, 'debridonly': False})
            return sources
        except Exception:
            #log_utils.log('vidembed', 1)
            return sources
