# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on - Scraper Module
 *
 *
 * @file torrentio.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2025, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
  ***********************************************************cm*
'''


import re
import queue
import json

from urllib.parse import urlencode, parse_qs

import requests

from resources.lib.modules import cleantitle
from resources.lib.modules import debrid
from resources.lib.modules import source_utils
from resources.lib.modules import client
from resources.lib.modules.crewruntime import c


class source:

    def __init__(self):
        '''
        Torrentio (v.0.0.15) supports YTS(+), EZTV(+), RARBG(+), 1337x(+), ThePirateBay(+),
        KickassTorrents(+), TorrentGalaxy(+), MagnetDL(+), HorribleSubs(+), NyaaSi(+), TokyoTosho(+),
        AniDex(+), Rutor(+), Rutracker(+), Comando(+), BluDV(+), Torrent9(+), ilCorSaRoNeRo(+),
        MejorTorrent(+), Wolfmax4k(+), Cinecalidad(+) and BestTorrents(+)
        '''

        self._queue = queue.SimpleQueue()
        self.priority = 1
        self.pack_capable = True
        self.hasMovies = True
        self.hasEpisodes = True
        self.language = ['en']
        self.base_link = "https://torrentio.strem.fun"
        self.movieSearch_link = '/stream/movie/%s.json'
        self.tvSearch_link = '/stream/series/%s:%s:%s.json'
        self.min_seeders = 0
        self.tv_cache_max_age = 3600 # cm get from json file: "cacheMaxAge": 3600, this is in secs
        self.movie_cache_max_age = 3600 # cm get from json file: "cacheMaxAge": 3600, this is in secs
        self.headers = {'User-Agent': 'Mozilla/5.0'}



    def movie(self, imdb, title, localtitle, aliases, year):
        '''
        Movie Search
        We need to remove this, it is obsolete for a lot of scrapers.
        For now it is kept for compatibility
        '''
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        '''
        TV Show Search
        We need to remove this, it is obsolete for a lot of scrapers.
        For now it is kept for compatibility
        '''
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        '''
        Episode Search
        We need to remove this, it is obsolete for a lot of scrapers.
        For now it is kept for compatibility
        '''
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


    def sources(self, data, hostDict, hostprDict):
        sources = []
        if not data:
            return sources
        append = sources.append
        try:
            data = parse_qs(data)
            #data = {'imdb': ['tt0899043'], 'title': ['The Amateur'], 'year': ['2025']")
            title = data['tvshowtitle'][0] if 'tvshowtitle' in data else data['title'][0]
            title = title.replace('&', 'and').replace('/', ' ')
            year = data['year'][0]
            imdb = data['imdb'][0]
            if 'tvshowtitle' in data:
                season = data['season'][0]
                episode = data['episode'][0]
                #hdlr = 'S%02dE%02d' % (int(season), int(episode))
                url = '%s%s' % (self.base_link, self.tvSearch_link % (imdb, season, episode))
            else:
                url = '%s%s' % (self.base_link, self.movieSearch_link % imdb)
                hdlr = year
            try:
                results = requests.get(url, headers=self.headers, timeout=5)
                files = results.json()['streams']
            except (requests.RequestException, json.JSONDecodeError):
                files = []

            self._queue.put_nowait(files)
            self._queue.put_nowait(files)
            ITEMINFO = re.compile(r'👤.*')
        except Exception as e:
            c.scraper_error(f'Exception (1) in sources: {e}', 'Torrentio', 1)
            return sources

        for file in files:
            try:
                infohash = file['infoHash']
                file_title = file['title'].split('\n')
                file_info = [x for x in file_title if ITEMINFO.match(x)][0]

                # cm - 2025/06/13
                #behaviourHints = file['behaviorHints']
                #b_filename = behaviourHints['filename']
                #b_bingegroup = behaviourHints['bingegroup']

                # cm - 2025/06/13
                # we can get a lot of info from the Bingegroup, things like HDR or DV, 10BIT etc,
                # but the info is too scattered, so we just use the filename and the old functions for now

                name = cleantitle.get(file_title[0])
                title = cleantitle.get(title)

                if str(title) not in str(name):
                    continue

                url = f'magnet:?xt=urn:btih:{infohash}&dn={name}'
                seeders_match = re.search(r'(\d+)', file_info)
                if seeders_match:
                    seeders = int(seeders_match.group(1))
                else:
                    seeders = 0

                quality, info = source_utils.get_release_quality(file_title[0], url)

                size_match = re.search(r'((?:\d+\,\d+\.\d+|\d+\.\d+|\d+\,\d+|\d+)\s*(?:GB|GiB|Gb|MB|MiB|Mb))', file_info)
                if size_match:
                    size = size_match.group(0)
                    dsize, isize = source_utils._size(size)
                    info.insert(0, isize)
                else:
                    dsize = 0

                info = ' | '.join(info)

                append({'provider': 'torrentio', 'source': 'torrent', 'seeders': seeders, 'hash': infohash, 'name': name, 'quality': quality,
                            'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
            except Exception as e:
                c.scraper_error(f'Exception (2) in sources: {e}', 'Torrentio', 1)
        return sources


    def resolve(self, url):
        return url
