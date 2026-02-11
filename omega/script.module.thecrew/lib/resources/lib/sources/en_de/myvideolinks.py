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

import re

from resources.lib.modules import control
from resources.lib.modules import cleantitle
from resources.lib.modules import debrid
from resources.lib.modules import client
from resources.lib.modules import source_utils

try: from urlparse import parse_qs, urljoin
except ImportError: from urllib.parse import parse_qs, urljoin
try: from urllib import urlencode, quote_plus, quote
except ImportError: from urllib.parse import urlencode, quote_plus, quote

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['iwantmyshow.tk', 'myvideolinks.net', 'go.myvideolinks.net', 'to.myvideolinks.net/', 'see.home.kg', 'to.myvideolinks.net']
        self.base_link = 'https://new.myvid.one/'
        self.search_link = '/?s=%s'

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
        try:
            sources = []

            if url is None:
                return sources
            
            if debrid.status() is False:
                raise Exception()

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            hostDict = hostprDict + hostDict
            
            items = [] ; urls = [] ; posts = [] ; links = []

            url = urljoin(self.base_link, self.search_link % data['imdb'])
            r = client.request(url)
            if 'CLcBGAs/s1600/1.jpg' in r:
                url = client.parseDOM(r, 'a', ret='href')[0]
                self.base_link = url = urljoin(url, self.search_link % data['imdb'])
                r = client.request(url)
            posts = client.parseDOM(r, 'article')
            if not posts:
                if 'tvshowtitle' in data:
                    url = urljoin(self.base_link, self.search_link % (cleantitle.geturl(title).replace('-','+') + '+' + hdlr))
                    r = client.request(url, headers={'User-Agent': client.agent()})
                    posts += client.parseDOM(r, 'article')
                    url = urljoin(self.base_link, self.search_link % cleantitle.geturl(title).replace('-','+'))
                    r = client.request(url, headers={'User-Agent': client.agent()})
                    posts += client.parseDOM(r, 'article')

            if not posts: return sources
            for post in posts:
                try:
                    t = client.parseDOM(post, 'img', ret='title')[0]
                    u = client.parseDOM(post, 'a', ret='href')[0]
                    s = re.search('((?:\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', post)
                    s = s.groups()[0] if s else '0'
                    items += [(t, u, s, post)]
                except:
                    pass
            items = set(items)
            items = [i for i in items if cleantitle.get(title) in cleantitle.get(i[0])]

            for item in items:
                name = item[0]
                u = client.request(item[1])
                if 'tvshowtitle' in data:
                    if hdlr.lower() not in name.lower():
                        pattern = '''<p>\s*%s\s*<\/p>(.+?)<\/ul>''' % hdlr.lower()
                        r = re.search(pattern, u, flags = re.I|re.S)
                        if not r: continue
                        links = client.parseDOM(r.groups()[0], 'a', ret='href')
                    else:
                        links = client.parseDOM(u, 'a', ret='href')
                else: links = client.parseDOM(u, 'a', ret='href')
                for url in links:
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if not valid: continue
                    host = client.replaceHTMLCodes(host)
                    host = host.encode('utf-8')

                    info = []
                    quality, info = source_utils.get_release_quality(name, url)

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+) (?:GB|GiB|MB|MiB))', item[2])[0]
                        div = 1 if size.endswith(('GB', 'GiB')) else 1024
                        size = float(re.sub('[^0-9|/.|/,]', '', size)) / div
                        size = '%.2f GB' % size
                        info.append(size)
                    except:
                        pass
                        
                    info = ' | '.join(info)
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': False})

            return sources
        except:
            return sources
                    
    def resolve(self, url):
        return url