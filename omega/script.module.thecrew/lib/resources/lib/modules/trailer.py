# -*- coding: utf-8 -*-
# pylint: disable=W0703

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file trailer.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''



import sys
import re
import requests # type: ignore

from . import client
from . import control
from . import utils
from . import cache
from . import keys
from .crewruntime import c


class trailers:
    """Represents a trailer with associated metadata.

    This class is used to store information about a trailer, including its name, URL, and identifiers
    for IMDb and TMDb. It also provides a method to retrieve sources based on the provided metadata.

    Initializes a new instance of the trailers class.

    This constructor sets up the initial state of the trailer object with empty strings for name,
    URL, IMDb ID, TMDb ID, and windowed trailer.
    """
    def __init__(self):
        self.name = ''
        self.url = ''
        self.imdb = ''
        self.tmdb = ''
        self.windowedtrailer = ''

        self.imdb_link = 'https://www.imdb.com/_json/video/'

    def get(self, name, url, imdb, tmdb, windowedtrailer):

        try:
            self.name = name
            self.url = url
            self.imdb = imdb
            self.tmdb = tmdb
            self.windowedtrailer = windowedtrailer

            c.log(f"[CM Debug @ 89 in trailer.py] trailer name = {name} with url = {url} and imdb = {imdb} and tmdb = {tmdb} and windowedtrailer = {windowedtrailer}")
            #1. start with imdb
            #First try imdb
            result = self.getSources_imdb_tmdb(mode='tmdb')
            #result = self.getSources_imdb_tmdb(mode='imdb')
            c.log(f"[CM Debug @ 63 in trailer.py] result = {result} with type = {type(result)}")
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 50 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 50 in trailer.py]Exception raised. Error = {e}')





    def getSources_imdb_tmdb(self, mode):
        try:
            if mode == 'imdb':
                sources = self.get_imdb_items(self.imdb, self.name)
            elif mode == 'tmdb':
                sources = self.getSources_imdb_tmdb('tmdb')
            else:
                raise Exception('Type not supported')
            return sources
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 50 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 50 in trailer.py]Exception raised. Error = {e}')


    def get_imdb_items(self, imdb, name):
        try:
            url = f"{self.imdb_link}{imdb}"
            #r = cache.get(client.request, 24, url)
            #result = cache.get(client.request, 0, url)
            result = client.request(url)
            c.log(f"[CM Debug @ 98 in trailer.py] result = {repr(result)}")





            items = utils.json_loads_as_str(result)
            c.log(f"[CM Debug @ 104 in trailer.py] infolabels={items}")

            listItems = items['playlists'][imdb]['listItems']
            videoMetadata = items['videoMetadata']
            vids_list = []
            for item in listItems:
                try:
                    desc = item.get('description') or ''
                    videoId = item['videoId']
                    metadata = videoMetadata[videoId]
                    title = metadata['title']
                    icon = metadata['smallSlate']['url2x']
                    related_to = metadata.get('primaryConst') or imdb
                    if (not related_to == imdb) and (not name.lower() in ' '.join((title, desc)).lower()):
                        continue
                    videoUrl = [i['videoUrl'] for i in metadata['encodings'] if i['definition'] == '720p'] + \
                        [i['videoUrl'] for i in metadata['encodings'] if i['definition'] == '1080p'] + \
                        [i['videoUrl'] for i in metadata['encodings'] if i['definition'] in ['480p', '360p', 'SD']]
                    if not videoUrl: continue
                    vids_list.append({'title': title, 'icon': icon, 'description': desc, 'video': videoUrl[0]})
                except:
                    pass

            if not vids_list: return
            vids_list = [v for v in vids_list if 'trailer' in v['title'].lower()] + [v for v in vids_list if 'trailer' not in v['title'].lower()]

            if self.mode == '1':
                vids = []
                for v in vids_list:
                    if control.getKodiVersion() >= 17:
                        li = control.item(label=v['title'])
                        li.setArt({'icon': v['icon'], 'thumb': v['icon'], 'poster': v['icon']})
                        vids.append(li)
                    else:
                        vids.append(v['title'])

                select = control.selectDialog(vids, control.lang(32121) % 'IMDb', useDetails=True)
                if select == -1: return 'canceled'
                return vids_list[select]

            return vids_list[0]
        except Exception as e:
            import traceback
            failure = traceback.format_exc()
            c.log(f'[CM Debug @ 139 in trailer.py]Traceback:: {failure}')
            c.log(f'[CM Debug @ 139 in trailer.py]Exception raised. Error = {e}')
            c.log(f"[CM Debug @ 144 in trailer.py] IMDb_trailer get_items fail with error: {e}")

            return








    def resolve(self,url):
        try:
            id = url.split('?v=')[-1].split('/')[-1].split('?')[0].split('&')[0]
            url = 'https://www.youtube.com/watch?v=%s' % id
            result = client.request(url)

            message = client.parseDom(result, 'div', attrs={'id': 'unavailable-submessage'})
            message = ''.join(message)

            alert = client.parseDom(result, 'div', attrs={'id': 'watch7-notification-area'})

            if len(alert) > 0: raise Exception()
            if re.search('[a-zA-Z]', message): raise Exception()

            url = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % id
            return url
        except:
            return