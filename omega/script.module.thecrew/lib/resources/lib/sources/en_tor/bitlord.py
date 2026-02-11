# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crew Add-on
*
* @file bitlord.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import re

from urllib.parse import parse_qs, urljoin, urlencode, quote_plus

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import debrid
from resources.lib.modules import source_utils
from resources.lib.modules.crewruntime import c



class source:
    def __init__(self):
        self.priority = 0
        self.language = ['en']
        self.domain = ['bitlordsearch.com']
        self.base_link = 'http://www.bitlordsearch.com'
        self.search_link = '/search?q=%s'


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


        sources = []
        try:
            if url is None:
                return sources

            if debrid.status() is False:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU')

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s %s' % (title, hdlr)
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', '', query)

            url = self.search_link % quote_plus(query)
            url = urljoin(self.base_link, url)

            try:
                r = client.request(url)
                links = zip(client.parseDOM(r, 'a', attrs={'class': 'btn btn-default magnet-button stats-action banner-button'}, ret='href'), client.parseDOM(r, 'td', attrs={'class': 'size'}))

                for link in links:
                    url = link[0].replace('&amp;', '&')
                    url = re.sub(r'(&tr=.+)&dn=', '&dn=', url) # some links on bitlord &tr= before &dn=
                    url = url.split('&tr=')[0]
                    if 'magnet' not in url:
                        continue

                    size = int(link[1])

                    if any(x in url.lower() for x in ['french', 'italian', 'spanish', 'truefrench', 'dublado', 'dubbed']):
                        continue

                    name = url.split('&dn=')[1]
                    t = name.split(hdlr)[0].replace(data['year'], '').replace('(', '').replace(')', '').replace('&', 'and')
                    if cleantitle.get(t) != cleantitle.get(title):
                        continue

                    if hdlr not in name:
                        continue

                    quality, info = source_utils.get_release_quality(name, url)

                    try:
                        if size < 5.12: raise Exception()
                        size = float(size) / 1024
                        size = '%.2f GB' % size
                        info.append(size)
                    except:
                        pass

                    info = ' | '.join(info)

                    sources.append({
                        'source': 'torrent', 'quality': quality, 'language': 'en', 'url': url,
                        'info': info, 'direct': False, 'debridonly': True
                        })

                return sources

            except:
                return sources

        except:
            return sources


    def resolve(self, url):
        return url
