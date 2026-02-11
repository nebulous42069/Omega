# -*- coding: UTF-8 -*-
#######################################################################
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# @tantrumdev wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return. - Muad'Dib
# ----------------------------------------------------------------------------
#######################################################################


import re

try: from urlparse import parse_qs, urljoin, urlparse
except ImportError: from urllib.parse import parse_qs, urljoin, urlparse
try: from urllib import urlencode, quote_plus
except ImportError: from urllib.parse import urlencode, quote_plus

from six import ensure_text

from resources.lib.modules import cleantitle, client, debrid, log_utils, source_utils
from resources.lib.modules import cfscrape


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['rlsbb.com', 'rlsbb.ru', 'rlsbb.to', 'proxybb.com' , 'ReleaseBB.net']
        self.base_link = 'https://rlsbb.in/'
        self.old_base_link = 'http://old3.https://rlsbb.in/'
        self.search_base_link = 'http://search.rlsbb.in/'
        self.search_cookie = 'serach_mode=rlsbb'
        self.search_link = 'lib/search526049.php?phrase=%s&pindex=1&content=true'

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
            scraper = cfscrape.create_scraper()

            if url is None:
                return sources

            if debrid.status() is False:
                return sources

            hostDict = hostprDict + hostDict

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            year = data['year']
            _year = re.findall('(\d{4})', data['premiered'])[0] if 'tvshowtitle' in data else year
            title = cleantitle.get_query(title)
            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else year
            #premDate = ''

            query = '%s S%02dE%02d' % (title, int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (title, year)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
            query = query.replace(" ", "-")

            _base_link = self.base_link if int(year) >= 2021 else self.old_base_link

            url = _base_link + query

            r = scraper.get(url).content
            r = ensure_text(r, errors='replace')

            if r is None and 'tvshowtitle' in data:
                season = re.search('S(.*?)E', hdlr)
                season = season.group(1)
                query = title
                query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)
                query = query + "-S" + season
                query = query.replace("&", "and")
                query = query.replace("  ", " ")
                query = query.replace(" ", "-")
                url = _base_link + query
                r = scraper.get(url).content
                r = ensure_text(r, errors='replace')

            for loopCount in list(range(0, 2)):
                if loopCount == 1 or (r is None and 'tvshowtitle' in data):

                    query = re.sub(r'[\\\\:;*?"<>|/\-\']', '', title)
                    query = query.replace(
                        "&", " and ").replace(
                        "  ", " ").replace(
                        " ", "-")  # throw in extra spaces around & just in case
                    #query = query + "-" + premDate

                    url = _base_link + query
                    url = url.replace('The-Late-Show-with-Stephen-Colbert', 'Stephen-Colbert')

                    r = scraper.get(url).content
                    r = ensure_text(r, errors='replace')

                posts = client.parseDOM(r, "div", attrs={"class": "content"})
                #hostDict = hostprDict + hostDict
                items = []
                for post in posts:
                    try:
                        u = client.parseDOM(post, 'a', ret='href')
                        for i in u:
                            try:
                                name = str(i)
                                if hdlr in name.upper():
                                    items.append(name)
                                #elif len(premDate) > 0 and premDate in name.replace(".", "-"):
                                    #items.append(name)
                            except:
                                pass
                    except:
                        pass

                if len(items) > 0:
                    break

            seen_urls = set()

            for item in items:
                try:
                    info = []

                    url = str(item)
                    url = client.replaceHTMLCodes(url)
                    url = ensure_str(url, errors='ignore')

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    host = url.replace("\\", "")
                    host2 = host.strip('"')
                    host = re.findall('([\w]+[.][\w]+)$', urlparse(host2.strip().lower()).netloc)[0]

                    if host not in hostDict:
                        continue
                    if any(x in host2 for x in ['.rar', '.zip', '.iso', '.part']):
                        continue

                    quality, info = source_utils.get_release_quality(host2)

                    #try:
                    #    size = re.findall('((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GiB|MiB|GB|MB))', post)[0]
                    #    div = 1 if size.endswith(('GB', 'GiB')) else 1024
                    #    size = float(re.sub('[^0-9|/.|/,]', '', size.replace(',', '.'))) / div
                    #    size = '%.2f GB' % size
                    #    info.append(size)
                    #except:
                    #    pass

                    info = ' | '.join(info)

                    host = client.replaceHTMLCodes(host)
                    host = ensure_text(host)
                    sources.append({'source': host, 'quality': quality, 'language': 'en',
                                    'url': host2, 'info': info, 'direct': False, 'debridonly': True})
                except:
                    pass
            check = [i for i in sources if not i['quality'] == 'CAM']
            if check:
                sources = check
            return sources
        except:
            return sources

    def resolve(self, url):
        return url
