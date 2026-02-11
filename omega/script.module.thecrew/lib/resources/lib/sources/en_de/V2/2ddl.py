# -*- coding: utf-8 -*-

'''
**Created by Tempest**
Updated For New Domain and changed
'''


import re

try: from urlparse import parse_qs, urljoin
except ImportError: from urllib.parse import parse_qs, urljoin
try: from urllib import urlencode, quote_plus, quote
except ImportError: from urllib.parse import urlencode, quote_plus, quote

from six import ensure_text

from resources.lib.modules import client
from resources.lib.modules import debrid
from resources.lib.modules import source_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import dom_parser



class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['onceddl.net']
        self.base_link = 'https://2ddl.ms'
        self.search_link = '/?q=%s'

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
            if url is None:
                return

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

            query = '%s S%02dE%02d' % (
            data['tvshowtitle'], int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
            data['title'], data['year'])
            query = re.sub('(\\\|/| -|:|\.|;|\*|\?|"|\'|<|>|\|)', ' ', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url).replace('%3A+', '-').replace('+', '-').replace('--', '-').lower()

            r = client.request(url)
            r = client.parseDOM(r, 'h2', attrs={'class': 'title'})
            r = [re.findall('<a class=""\s*href="([^"]*)"\s*title="([^"]*)', i, re.DOTALL)[0] for i in r]

            hostDict = hostprDict + hostDict
            items = []
            for item in r:
                try:
                    t = item[1]
                    t1 = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d+|3D)(\.|\)|\]|\s|)(.+|)', '', t)

                    if not cleantitle.get(t1) == cleantitle.get(title): raise Exception()

                    y = re.findall('[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', t)[-1].upper()

                    if not y == hdlr: raise Exception()

                    data = client.request(item[0])
                    data = re.findall('<a href="([^"]*)',data)

                    u = [(t, i) for i in data]
                    items += u

                except:
                    pass

            for item in items:
                try:
                    name = item[0]
                    name = client.replaceHTMLCodes(name)

                    quality, info = source_utils.get_release_quality(name, item[1])

                    url = item[1]
                    if any(x in url for x in ['.rar', '.zip', '.iso', 'www.share-online.biz', 'https://ouo.io','http://guard.link']): raise Exception()
                    url = client.replaceHTMLCodes(url)
                    url = ensure_text(url)
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    host = client.replaceHTMLCodes(host)
                    host = ensure_text(host)
                    info = ' | '.join(info)
                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info,'direct': False, 'debridonly': True})
                except:
                    pass
            return sources
        except:
            return sources

    def resolve(self, url):
        return url
