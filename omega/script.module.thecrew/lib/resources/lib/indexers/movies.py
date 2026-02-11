# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file movies.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import os
import sys
import re
import datetime
import base64
import traceback
import json
import requests

from bs4 import BeautifulSoup

from resources.lib.modules import trakt
from resources.lib.modules import keys
from resources.lib.modules import bookmarks
from resources.lib.modules import cleangenre
from resources.lib.modules import cleantitle
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import cache
from resources.lib.modules import metacache
from resources.lib.modules import playcount
from resources.lib.modules import workers
from resources.lib.modules import views
from resources.lib.modules import utils
from resources.lib.modules import log_utils
from resources.lib.indexers import navigator


import urllib
from urllib.parse import quote_plus, parse_qsl, urlparse, urlsplit, urlencode
from sqlite3 import dbapi2 as database


import six
from six.moves import zip, range

from resources.lib.modules.crewruntime import c

params = dict(parse_qsl(sys.argv[2].replace('?', ''))) if len(sys.argv) > 1 else dict()
action = params.get('action')


class movies:
    def __init__(self):

        self.count = int(control.setting('page.item.limit'))
        self.list = []

        self.session = requests.Session()

        self.showunaired = control.setting('showunaired') or 'true'

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tmdb_link = 'https://api.themoviedb.org/3/'

        #####
        # dates
        self.datetime = datetime.datetime.now()
        self.systime = (self.datetime).strftime('%Y%m%d%H%M%S%f')
        self.year_date = (self.datetime - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        self.month_date = (self.datetime - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        self.today_date = (self.datetime).strftime('%Y-%m-%d')
        self.year = self.datetime.strftime('%Y')
        self.country = control.setting('official.country') or 'US'

        #####
        # users
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.fanart_tv_user = control.setting('fanart.tv.user')

        self.tmdb_user = control.setting('tm.personal_user') or control.setting('tm.user')
        if not self.tmdb_user: self.tmdb_user = keys.tmdb_key

        self.fanart_tv_headers = {'api-key': keys.fanart_key}
        if not self.fanart_tv_user == '': self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})

        self.user = self.tmdb_user

        #####
        # Settings
        self.lang = control.apiLanguage()['trakt']

        #####cm#
        # define links
        self.search_link = 'https://api.trakt.tv/search/movie?limit=20&page=1&query='
        self.fanart_tv_art_link = 'https://webservice.fanart.tv/v3/movies/%s'
        self.fanart_tv_level_link = 'https://webservice.fanart.tv/v3/level'
        self.tm_art_link = 'https://api.themoviedb.org/3/movie/%s/images?api_key=%s&language=en-US&include_image_language=en,%s,null' % ('%s', self.tmdb_user, self.lang)
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'

        ######
        # tmdb
        self.person_link = ('{}{}/{}?api_key={}&query={}&include_adult=false&language=en-US&page=1' ).format(self.tmdb_link, 'search', 'person', self.tmdb_user, '%s')
        self.persons_link = ('{}{}/{}?api_key={}&?language=en-US').format(self.tmdb_link, 'person', '%s', self.tmdb_user)
        self.personlist_link = ('{}{}/{}/{}?api_key={}&language=en-US').format(self.tmdb_link, 'trending', 'person', 'day', self.tmdb_user)
        self.personmovies_link = ('{}{}/{}/movie_credits?api_key={}&language=en-US').format(self.tmdb_link, 'person', '%s', self.tmdb_user)

        self.keyword_link = 'https://www.imdb.com/search/title?title_type=feature,tv_movie,documentary&num_votes=100,&keywords=%s&sort=moviemeter,asc&count=%d&start=1' % ('%s', self.count)
        self.oscars_link = ( '{}{}/{}?api_key={}&language=en-US&page=1' ).format(self.tmdb_link, 'list', '28', self.tmdb_user)
        self.xristmas_link = ( '{}{}/{}?api_key={}&language=en-US&page=1' ).format(self.tmdb_link, 'list', '8280352', self.tmdb_user)
        self.oscarsnominees_link = 'https://www.imdb.com/search/title?title_type=feature,tv_movie&production_status=released&groups=oscar_best_picture_nominees&sort=year,desc&count=%d&start=1' % self.count
        self.theaters_link = ('{}{}/{}?api_key={}&now_playing?language=en-US&page=1&region=US|UK&sort_by=popularity.desc').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user)
        self.year_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&language=en-US&region=US&sort_by=primary_release_date.desc&year={}&page=1').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user, '%s')
        self.language_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&sort_by=popularity.desc&with_original_language={}&page=1').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user, '%s')
        self.year_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&language=en-US&region=US&sort_by=primary_release_date.desc&year={}&page=1').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user, '%s')
        self.certification_link = 'https://www.imdb.com/search/title?title_type=feature,tv_movie&num_votes=100,&production_status=released&certificates=%s&sort=moviemeter,asc&count=%d&start=1' % ('%s', self.count)
        self.featured_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc&with_release_type=1|2|3&release_date.gte=date[60]&release_date.lte=date[0]').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user)
        self.popular_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc&with_release_type=1|2|3&release_date.gte=date[60]&release_date.lte=date[0]').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user)
        self.views_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&language=en-US&page=1&sort_by=popularity.desc&vote_average.gte=8&vote_average.lte=10&with_original_language=en').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user)
        self.genre_link = ('{}{}/{}?api_key={}&include_adult=false&include_video=false&language=en-US&sort_by=primary_release_date.desc&with_original_language=en&primary_release_date.lte={}&with_genres={}&page=1').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user, self.today_date, '%s')

        ###cm#
        # Trakt
        self.trending_link = 'https://api.trakt.tv/movies/trending?limit=%d&page=1' % self.count
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/movies'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/movies'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/movies?limit=%d' % self.count
        self.trakthistory_link = 'https://api.trakt.tv/users/me/history/movies?limit=%d&page=1' % self.count
        self.onDeck_link = 'https://api.trakt.tv/sync/playback/movies?extended=full&limit=%d' % self.count


        self.tmdb_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.tmdb_img_prelink = 'https://image.tmdb.org/t/p/{}{}'

        self.tmdb_by_imdb = 'https://api.themoviedb.org/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tmdb_user)
        self.tm_search_link = 'https://api.themoviedb.org/3/search/movie?api_key=%s&language=en-US&query=%s&page=1' % (self.tmdb_user, '%s')
        self.related_link = 'https://api.themoviedb.org/3/movie/%s/similar?api_key=%s&page=1' % ('%s', self.tmdb_user)
        self.tmdb_providers_link = 'https://api.themoviedb.org/3/discover/movie?api_key=%s&sort_by=popularity.desc&with_watch_providers=%s&watch_region=%s&page=1' % (self.tmdb_user, '%s', self.country)
        self.tmdb_art_link = 'https://api.themoviedb.org/3/movie/%s/images?api_key=%s&language=en-US&include_image_language=en,%s,null' % ('%s', self.tmdb_user, self.lang)

        self.tmdb_api_link = ('{}movie/{}?api_key={}&language={}&append_to_response=aggregate_credits,content_ratings,external_ids').format(self.tmdb_link, '%s', self.tmdb_user, self.lang)
        self.tmdb_networks_link_no_unaired = ('{}discover/movie?api_key={}&first_air_date.lte={}&sort_by=first_air_date.desc&with_networks={}&page=1').format( self.tmdb_link, self.tmdb_user, self.today_date, '%s')
        self.tmdb_networks_link = ('{}discover/movie?api_key={}&with_networks={}&language=en-US&release_date.lte={}&sort_by=primary_release_date.desc&page=1').format(self.tmdb_link, self.tmdb_user, '%s', self.today_date)
        self.tmdb_search_movie_link = ('{}search/movie?api_key={}&language=en-US&query={}&page=1').format(self.tmdb_link, self.tmdb_user, '%s')
        self.search_link = ('{}search/movie?api_key={}&language=en-US&query={}&page=1').format(self.tmdb_link, self.tmdb_user, '%s')
        self.related_link = ('{}movie/{}/similar?api_key={}&language=en-US&page=1').format(self.tmdb_link, '%s', self.tmdb_user)
        self.tmdb_info_tvshow_link = ('{}{}/{}?api_key={}&language={}&append_to_response=images').format(self.tmdb_link, 'movie', '%s', self.tmdb_user, self.lang)
        self.tmdb_by_imdb = ('{}find/{}?api_key={}&external_source=imdb_id').format(self.tmdb_link, '%s', self.tmdb_user)

        self.tmdb_movie_top_rated_link = ('{}{}/{}?api_key={}&language={}&sort_by=popularity.desc&page=1').format( self.tmdb_link, 'movie', 'top_rated', self.tmdb_user, self.lang)
        self.tmdb_movie_popular_link = ('{}{}/{}?api_key={}&language={}&page=1').format(self.tmdb_link, 'movie', 'popular', self.tmdb_user, self.lang)
        self.tmdb_movie_trending_day_link = ('{}/{}/{}/{}?api_key={}').format(self.tmdb_link, 'trending', 'movie', 'day', self.tmdb_user)
        self.tmdb_movie_trending_week_link = ('{}/{}/{}/{}?api_key={}').format(self.tmdb_link, 'trending', 'movie', 'week', self.tmdb_user)
        self.tmdb_movie_discover_year_link = ('{}{}/{}?api_key={}&language=%s&sort_by=popularity.desc&first_air_date_year={}&include_null_first_air_dates=false&with_original_language=en&page=1').format(self.tmdb_link, 'discover', 'movie', self.tmdb_user, self.year)

    def __del__(self):
        self.session.close()

    def get(self, url, tid=0, idx=True, create_directory=True):
        try:
            try:
                url = getattr(self, url + '_link')

            except:
                pass

            ####cm#
            # Making it possible to use date[xx] in url's where xx is a str(int)
            for i in re.findall('date\[(\d+)\]', url):
                url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))

            try:
                u = urlparse(url).netloc.lower()
            except:
                pass

            if self.trakt_link in url and url == self.onDeck_link:
                self.blist = cache.get(self.trakt_list, 720, url, self.trakt_user)
                self.list = []
                self.list = cache.get(self.trakt_list, 0, url, self.trakt_user)
                self.list = self.list[::-1]

                if idx == True: self.worker()

            elif u in self.trakt_link and '/users/' in url:
                try:
                    if url == self.trakthistory_link: raise Exception()
                    if not '/users/me/' in url: raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user): raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                    self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
                except:
                    self.list = cache.get(self.trakt_list, 6, url, self.trakt_user)
                    self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)


                #if '/users/me/' in url and '/collection/' in url:
                    #self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))
                if idx == True: self.worker()

            elif u in self.search_link and '/search/movie' in url:
                self.list = cache.get(self.tmdb_list, 1, url)
                if idx == True: self.worker()

            elif u in self.trakt_link and '/sync/playback/' in url:
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=False)
                if idx == True: self.worker()

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                if idx == True: self.worker()

            elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.imdb_list, 0, url)
                if idx == True: self.worker()

            elif u in self.imdb_link:
                self.list = cache.get(self.imdb_list, 24, url)
                if idx == True: self.worker()

            elif u in self.tmdb_networks_link and tid > 0:
                #c.log(f"[cm debug in movies.py @ 344] u={u} and url={url}")
                self.list = cache.get(self.tmdb_list, 24, url, tid)
                if idx == True: self.worker()

            elif u in self.tmdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.list_tmdb_list, 0, url)
                #self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
                if idx == True: self.worker()

            elif u in self.tmdb_link and '/movie_credits' in url:
                self.list = cache.get(self.tmdb_cast_list, 24, url)
                #self.list = self.tmdb_cast_list(url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
                if idx == True: self.worker()

            elif u in self.tmdb_link:
                # self.list = cache.get(self.tmdb_list, 24, url)
                self.list = self.tmdb_list(url)
                if idx == True: self.worker()

            if idx == True and create_directory == True:
                self.movieDirectory(self.list)
            return self.list
        except Exception as e:
            #import traceback
            #failure = traceback.format_exc()
            #c.log('[CM Debug @ 322 in movies.py]Traceback:: ' + str(failure))
            #c.log('[CM Debug @ 323 in movies.py]Exception raised. Error = ' + str(e))
            c.log(f'Exception raised in movies.get(), error = {e}', 1)
            pass

    def widget(self):

        self.get(self.featured_link)

        # setting = control.setting('movie.widget')

        # if setting == '2':
        #     self.get(self.trending_link)
        # elif setting == '3':
        #     self.get(self.popular_link)
        # elif setting == '4':
        #     self.get(self.theaters_link)
        # elif setting == '5':
        #     self.get(self.added_link)
        # else:
        # self.get(self.featured_link)

    def search(self):
        navigator.navigator().addDirectoryItem(32603, 'movieSearchnew', 'search.png', 'DefaultMovies.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS movies (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM movies ORDER BY ID DESC")
        lst = []

        delete_option = False
        for (id, term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term, f'movieSearchterm&name={term}', 'search.png', 'DefaultMovies.png')
                lst += [(term)]
        dbcur.close()

        if delete_option:
            navigator.navigator().addDirectoryItem(32605, 'clearCacheSearch', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator().endDirectory()

    def search_new(self):
        control.idle()

        t = control.lang(32010)
        k = control.keyboard('', t)
        k.doModal()
        q = k.getText() if k.isConfirmed() else None

        if not q:
            return

        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM movies WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO movies VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.search_link % quote_plus(q)
        self.get(url)

    def search_term(self, name):
        url = self.search_link % quote_plus(name)
        self.get(url)

    def person(self):
        try:
            t = control.lang(32010)
            k = control.keyboard('', t)
            k.doModal()
            q = k.getText() if k.isConfirmed() else None

            if (q == None or q == ''):
                return

            url = self.person_link % quote_plus(q)
            self.persons(url)
        except:
            return


# TC 2/01/19 started

    #####cm#
    # Completely redone for compatibility with tmdb
    #
    def genres(self):
        genres = [
            {"id": 28, "name": "Action"},
            {"id": 12, "name": "Adventure"},
            {"id": 16, "name": "Animation"},
            {"id": 35, "name": "Comedy"},
            {"id": 80, "name": "Crime"},
            {"id": 99, "name": "Documentary"},
            {"id": 18, "name": "Drama"},
            {"id": 10751, "name": "Family"},
            {"id": 14, "name": "Fantasy"},
            {"id": 36, "name": "History"},
            {"id": 27, "name": "Horror"},
            {"id": 10402, "name": "Music"},
            {"id": 9648, "name": "Mystery"},
            {"id": 10749, "name": "Romance"},
            {"id": 878, "name": "Science Fiction"},
            {"id": 10770, "name": "TV Movie"},
            {"id": 53, "name": "Thriller"},
            {"id": 10752, "name": "War"},
            {"id": 37, "name": "Western"}
        ]

        for i in genres:
            self.list.append(
                {
                    'name': cleangenre.lang(i['name'], self.lang),
                    'url': self.genre_link % i['id'],
                    'image': 'genres.png',
                    'action': 'movies'
                })

        self.addDirectory(self.list)
        return self.list

    def languages(self):
        languages = [
            ('Arabic', 'ar'),
            ('Bosnian', 'bs'),
            ('Bulgarian', 'bg'),
            ('Chinese', 'zh'),
            ('Croatian', 'hr'),
            ('Dutch', 'nl'),
            ('English', 'en'),
            ('Finnish', 'fi'),
            ('French', 'fr'),
            ('German', 'de'),
            ('Greek', 'el'),
            ('Hebrew', 'he'),
            ('Hindi ', 'hi'),
            ('Hungarian', 'hu'),
            ('Icelandic', 'is'),
            ('Italian', 'it'),
            ('Japanese', 'ja'),
            ('Korean', 'ko'),
            ('Macedonian', 'mk'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Slovenian', 'sl'),
            ('Spanish', 'es'),
            ('Swedish', 'sv'),
            ('Turkish', 'tr'),
            ('Ukrainian', 'uk')
        ]

        for i in languages:
            self.list.append({'name': str(
                i[0]), 'url': self.language_link % i[1], 'image': 'international.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def certifications(self):
        certificates = ['[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]G[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]', '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]PG[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]',
                        '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]PG-13[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]', '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]R[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]', '[COLOR dodgerblue][B]¤[/B][/COLOR] [B][COLOR white]NC-17[/COLOR][/B] [COLOR dodgerblue][B]¤[/B][/COLOR]']

        for i in certificates:
            self.list.append({'name': str(i), 'url': self.certification_link % str(
                i).replace('-', '_').lower(), 'image': 'certificates.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def years(self):
        year = (self.datetime.strftime('%Y'))

        for i in range(int(year)-0, 1900, -1):
            self.list.append({'name': str(i), 'url': self.year_link % (str(i)), 'image': 'years.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def persons(self, url):
        if url == None:
            #self.list = cache.get(self.tmdb_person_list, 24, self.personlist_link)
            self.tmdb_person_list(self.personlist_link)
        else:
            self.list = cache.get(self.tmdb_person_list, 1, url)

        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list

    def userlists(self):
        try:
            userlists = []
            if trakt.getTraktCredentialsInfo() == False:
                raise Exception()
            activity = trakt.getActivity()
        except:
            pass

        try:
            if trakt.getTraktCredentialsInfo() == False:
                raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlists_link, self.trakt_user):
                    raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlists_link, self.trakt_user)
        except:
            pass
        try:
            self.list = []
            if self.imdb_user == '':
                raise Exception()
            userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
        except:
            pass
        try:
            self.list = []
            if trakt.getTraktCredentialsInfo() == False:
                raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user):
                    raise Exception()
                userlists += cache.get(self.trakt_user_list, 720,
                                       self.traktlikedlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
        except:
            pass

        self.list = userlists
        for i in range(len(self.list)):
            self.list[i].update({'image': 'userlists.png', 'action': 'movies'})
        self.addDirectory(self.list, queue=True)
        return self.list

    def trakt_list(self, url, user):
        try:
            q = dict(parse_qsl(urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urlparse(url).query, '') + '?' + q

            result = trakt.getTraktAsJson(u)

            items = []

            for i in result:
                try:
                    items.append(i['movie'])
                except:
                    pass
            if len(items) == 0:
                items = result
        except Exception as e:
            c.log(f'Exception in movies.trakt_list 0. Error = {e}')
            return

        try:
            q = dict(parse_qsl(urlsplit(url).query))
            if not int(q['limit']) == len(items):
                raise Exception()

            q.update({'page': str(int(q['page']) + 1)})
            q = (urlencode(q)).replace('%2C', ',')
            next = url.replace('?' + urlparse(url).query, '') + '?' + q
            next = str(next)
        except:
            next = ''

        for item in items:
            try:
                title = item.get('title')
                title = client.replaceHTMLCodes(title)

                year = item.get('year')
                if year:
                    year = re.sub(r'[^0-9]', '', str(year))
                else:
                    year = '0'
                # if int(year) > int((self.datetime).strftime('%Y')): raise Exception()

                imdb = item.get('ids', {}).get('imdb')
                if not imdb:
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub(r'[^0-9]', '', str(imdb))

                tmdb = item.get('ids', {}).get('tmdb')
                if not tmdb:
                    tmdb == '0'
                else:
                    tmdb = str(tmdb)

                premiered = item.get('released')
                if premiered:
                    premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                else:
                    premiered = '0'

                genre = item.get('genres')
                if genre:
                    genre = [i.title() for i in genre]
                    genre = ' / '.join(genre)
                else:
                    genre = '0'

                duration = item.get('runtime')
                if duration:
                    duration = str(duration)
                else:
                    duration = '0'

                rating = item.get('rating')
                if rating and not rating == '0.0':
                    rating = str(rating)
                else:
                    rating = '0'

                try:
                    votes = str(item['votes'])
                except:
                    votes = '0'
                try:
                    votes = str(format(int(votes), ',d'))
                except:
                    pass
                if votes is None:
                    votes = '0'

                if int(year) > int((self.datetime).strftime('%Y')):
                    raise Exception()

                try:
                    premiered = item['released']
                except:
                    premiered = '0'
                try:
                    premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except:
                    premiered = '0'

                try:
                    genre = item['genres']
                except:
                    genre = '0'
                genre = [i.title() for i in genre]
                if genre == []:
                    genre = '0'
                genre = ' / '.join(genre)

                try:
                    duration = str(item['runtime'])
                except:
                    duration = '0'
                if duration == None:
                    duration = '0'

                try:
                    rating = str(item['rating'])
                except:
                    rating = '0'
                if rating == None or rating == '0.0':
                    rating = '0'

                try:
                    votes = str(item['votes'])
                except:
                    votes = '0'
                try:
                    votes = str(format(int(votes), ',d'))
                except:
                    pass
                if not votes:
                    votes = '0'

                try:
                    mpaa = item['certification']
                except:
                    mpaa = '0'
                if not mpaa:
                    mpaa = '0'

                try:
                    plot = item['overview']
                except:
                    plot = '0'
                if not plot:
                    plot = '0'
                plot = client.replaceHTMLCodes(plot)

                country = item.get('country')
                if not country:
                    country = '0'
                else:
                    country = country.upper()

                try:
                    tagline = item['tagline']
                except:
                    tagline = '0'
                if tagline == None:
                    tagline = '0'
                tagline = client.replaceHTMLCodes(tagline)

                paused_at = item.get('paused_at', '0') or '0'
                paused_at = re.sub('[^0-9]+', '', paused_at)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered,
                                  'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes,
                                  'mpaa': mpaa, 'plot': plot, 'tagline': tagline, 'imdb': imdb, 'tmdb': tmdb,
                                  'country': country, 'tvdb': '0', 'poster': '0', 'next': next, 'paused_at': paused_at})
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log('[CM Debug @ 776 in movies.py]Traceback:: ' + str(failure))
                c.log('[CM Debug @ 777 in movies.py]Exception raised. Error = ' + str(e))
                pass

        return self.list

    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
        except:
            pass

        for item in items:
            try:
                try:
                    name = item['list']['name']
                except:
                    name = item['name']
                name = client.replaceHTMLCodes(name)

                try:
                    url = (trakt.slug(
                        item['list']['user']['username']), item['list']['ids']['slug'])
                except:
                    url = ('me', item['ids']['slug'])
                url = self.traktlist_link % url
                url = url.encode('utf-8')

                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list

    ####cm#
    # new def for tmdb lists
    def list_tmdb_list(self, url, tid=0):
        try:
            if not tid == 0: url = url % tid

            result = self.session.get(url, timeout=15).json()
            items = result['items']
        except:
            return
        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total:
                raise Exception()
            if 'page=' not in url:
                raise Exception()
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except:
            next = ''

        for item in items:
            try:
                tmdb = str(item['id'])
                title = item['title']

                originaltitle = item['original_title']
                if not originaltitle: originaltitle = title

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try: premiered = item['release_date']
                except: premiered = ''
                if not premiered: premiered = '0'

                try: year = re.findall(r'(\d{4})', premiered)[0]
                except: year = ''
                if not year: year = '0'

                if premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    if self.showunaired != 'true':
                        raise Exception()

                try: plot = item['overview']
                except:  plot = ''
                if not plot: plot = '0'

                try:  poster_path = item['poster_path']
                except: poster_path = ''
                if poster_path:
                    poster = self.tmdb_img_prelink.format('original', poster_path)
                else:
                    poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    fanart = self.tmdb_img_prelink.format('original', 'backdrop_path')
                else:
                    fanart = ''

                self.list.append({'title': title, 'originaltitle': originaltitle,
                                  'premiered': premiered, 'year': year, 'rating': rating,
                                  'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                  'tvdb': '0', 'fanart': fanart, 'poster': poster, 'next': next})
            except:
                pass

        return self.list

    def tmdb_cast_list(self, url):
        try:
            result = self.session.get(url, timeout=15).json()
            items = result['cast']
        except:
            return

        for item in items:

            try:
                tmdb = str(item['id'])
                title = item['title']
                originaltitle = item['original_title']
                if not originaltitle: originaltitle = title

                try:
                    rating = str(item['vote_average'])
                except:
                    rating = ''
                if not rating:
                    rating = '0'

                try:
                    votes = str(item['vote_count'])
                except:
                    votes = ''
                if not votes:
                    votes = '0'

                try:
                    premiered = item['release_date']
                except:
                    premiered = ''
                if not premiered:
                    premiered = '0'

                try:
                    year = re.findall(r'(\d{4})', premiered)[0]
                except:
                    year = ''
                if not year:
                    year = '0'

                if not premiered or premiered == '0':
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    if self.showunaired != 'true':
                        raise Exception()

                try:
                    plot = item['overview']
                except:
                    plot = ''
                if not plot:
                    plot = '0'

                try:
                    poster_path = item['poster_path']
                except:
                    poster_path = ''
                if poster_path:
                    poster = self.tmdb_img_prelink.format('original', poster_path)
                else:
                    poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path:
                    fanart = self.tmdb_img_prelink.format('original', 'backdrop_path')
                else:
                    fanart = ''

                self.list.append({'title': title, 'originaltitle': originaltitle,
                                  'premiered': premiered, 'year': year, 'rating': rating,
                                  'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                                  'tvdb': '0', 'fanart': fanart, 'poster': poster})
            except Exception as e:
                c.log('[Error @ 1012 in movies.py] Exception raised: e= = ' + str(e))
                pass

        return self.list

    def tmdb_list(self, url, tid=0):
        """Fetch a TMDb endpoint while honoring the addon's per-page limit.

        TMDb returns 20 results per API page. The addon setting (page.item.limit)
        can be higher (e.g. 30). We pull multiple TMDb pages until we have
        self.count items (or we run out), then set the correct "next" page.
        """
        try:
            if not tid == 0:
                url = url % tid
        except:
            pass

        if 'page=' not in url:
            url = url + ('&page=1' if '?' in url else '?page=1')

        collected = []
        next_url = ''

        try:
            current_page = int(re.findall(r'page=(\d+)', url)[-1])
        except:
            current_page = 1

        page = current_page
        total_pages = None

        while len(collected) < self.count:
            try:
                page_url = re.sub(r'page=\d+', 'page=%d' % page, url)
                result = self.session.get(page_url, timeout=15).json()
                items = result.get('results') or []
                if total_pages is None:
                    total_pages = int(result.get('total_pages', page))
            except:
                break

            if not items:
                break

            if total_pages is not None and page < total_pages:
                next_url = re.sub(r'page=\d+', 'page=%d' % (page + 1), url)
            else:
                next_url = ''

            for item in items:
                if len(collected) >= self.count:
                    break
                try:
                    tmdb = str(item['id'])
                    title = item.get('title') or ''
                    if not title:
                        raise Exception()
                    originaltitle = item.get('original_title') or title

                    rating = str(item.get('vote_average') or '0')
                    votes = str(item.get('vote_count') or '0')

                    premiered = item.get('release_date') or '0'
                    try:
                        year = re.findall(r'(\d{4})', premiered)[0]
                    except:
                        year = '0'

                    if premiered and premiered != '0':
                        if int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                            if self.showunaired != 'true':
                                raise Exception()

                    plot = item.get('overview') or '0'

                    poster_path = item.get('poster_path') or ''
                    poster = self.tmdb_img_prelink.format('original', poster_path) if poster_path else '0'

                    backdrop_path = item.get('backdrop_path') or ''
                    fanart = self.tmdb_img_prelink.format('original', backdrop_path) if backdrop_path else ''

                    collected.append({'title': title, 'originaltitle': originaltitle,
                            'premiered': premiered, 'year': year, 'rating': rating,
                            'votes': votes, 'plot': plot, 'imdb': '0', 'tmdb': tmdb,
                            'fanart': fanart, 'poster': poster, 'next': next_url})
                except:
                    pass

            if total_pages is not None and page >= total_pages:
                next_url = ''
                break

            page += 1
            if total_pages is not None and page > total_pages:
                break

        self.list = collected
        return self.list


    def disabled_imdb_list(self, url):
        try:
            for i in re.findall(r'date\[(\d+)\]', url):
                url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))

            def imdb_watchlist_id(url):
                return client.parseDOM(client.request(url), 'meta', ret='content', attrs={'property': 'pageId'})[0]

            if url == self.imdbwatchlist_link:
                url = cache.get(imdb_watchlist_id, 8640, url)
                url = self.imdblist_link % url

            elif url == self.imdbwatchlist2_link:
                url = cache.get(imdb_watchlist_id, 8640, url)
                url = self.imdblist2_link % url

            result = client.request(url)

            result = result.replace('\n', ' ')

            items = client.parseDOM(result, 'div', attrs={'class': 'lister-item .+?'})
            items += client.parseDOM(result, 'div', attrs={'class': 'list_item.+?'})
        except:
            return

        try:
            next = client.parseDOM(result, 'a', ret='href', attrs={'class': '.+?ister-page-nex.+?'})

            if len(next) == 0:
                next = client.parseDOM(result, 'div', attrs={'class': 'pagination'})[0]
                next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
                next = [i[0] for i in next if 'Next' in i[1]]

            next = url.replace(urlparse(url).query, urlparse(next[0]).query)
            next = client.replaceHTMLCodes(next)
            next = six.ensure_str(next)
        except:
            next = ''

        for item in items:
            try:

                title = client.parseDOM(item, 'a')[1]
                title = client.replaceHTMLCodes(title)
                title = six.ensure_str(title)

                year = client.parseDOM(item, 'span', attrs={'class': 'lister-item-year.+?'})

                try:
                    year = re.sub("\D", "", year[0])
                except:
                    year = '0'

                if int(year) > int((self.datetime).strftime('%Y')):
                    raise Exception()

                imdb = client.parseDOM(item, 'a', ret='href')[0]
                imdb = re.findall(r'(tt\d*)', imdb)[0]

                try:
                    poster = client.parseDOM(item, 'img', ret='loadlate')[0]
                except:
                    poster = '0'
                if '/nopicture/' in poster or '/sash/' in poster:
                    poster = '0'
                poster = re.sub('(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', poster)
                poster = client.replaceHTMLCodes(poster)
                poster = six.ensure_str(poster, errors='ignore')

                try:
                    genre = client.parseDOM(item, 'span', attrs={'class': 'genre'})[0]
                except:
                    genre = '0'
                genre = ' / '.join([i.strip() for i in genre.split(',')])
                if genre == '': genre = '0'
                genre = client.replaceHTMLCodes(genre)
                genre = six.ensure_str(genre)

                try:
                    duration = re.findall(r'(\d+?) min(?:s|)', item)[-1]
                except:
                    duration = '0'
                duration = six.ensure_str(duration)

                rating = '0'
                try:
                    rating = client.parseDOM(item, 'span', attrs={'class': 'rating-rating'})[0]
                except:
                    pass
                try:
                    rating = client.parseDOM(rating, 'span', attrs={'class': 'value'})[0]
                except:
                    rating = '0'
                try:
                    rating = client.parseDOM(
                        item, 'div', ret='data-value', attrs={'class': '.*?imdb-rating'})[0]
                except:
                    pass
                if rating == '' or rating == '-':
                    rating = '0'
                rating = client.replaceHTMLCodes(rating)

                try:
                    votes = client.parseDOM(item, 'div', ret='title', attrs={'class': '.*?rating-list'})[0]
                except:
                    votes = '0'
                try:
                    votes = re.findall('\((.+?) vote(?:s|)\)', votes)[0]
                except:
                    votes = '0'
                if not votes:
                    votes = '0'
                votes = client.replaceHTMLCodes(votes)

                try:
                    mpaa = client.parseDOM(item, 'span', attrs={'class': 'certificate'})[0]
                except:
                    mpaa = '0'
                if mpaa == '' or mpaa.lower() in ['not_rated', 'not rated']:
                    mpaa = '0'
                mpaa = mpaa.replace('_', '-')
                mpaa = client.replaceHTMLCodes(mpaa)
                mpaa = six.ensure_str(mpaa, errors='ignore')

                try:
                    director = re.findall(
                        'Director(?:s|):(.+?)(?:\||</div>)', item)[0]
                    director = client.parseDOM(director, 'a')
                    director = ' / '.join(director)
                    if not director:
                        director = '0'
                    director = client.replaceHTMLCodes(director)
                    director = six.ensure_str(director, errors='ignore')
                except:
                    director = '0'

                try:
                    cast = re.findall(
                        'Stars(?:s|):(.+?)(?:\||</div>)', item)[0]
                    cast = client.replaceHTMLCodes(cast)
                    cast = six.ensure_str(cast, errors='ignore')
                    cast = client.parseDOM(cast, 'a')
                    if not cast:
                        cast = '0'
                except:
                    cast = '0'

                plot = '0'
                try:
                    plot = client.parseDOM(item, 'p', attrs={'class': 'text-muted'})[0]
                except:
                    pass
                if plot == '0':
                    try:
                        plot = client.parseDOM(item, 'div', attrs={'class': 'item_description'})[0]
                    except:
                        pass
                if plot == '0':
                    try:
                        plot = client.parseDOM(item, 'p')[1]
                    except:
                        pass
                if plot == '':
                    plot = '0'
                if plot and not plot == '0':
                    plot = plot.rsplit('<span>', 1)[0].strip()
                    plot = re.sub(r'<.+?>|</.+?>', '', plot)
                    plot = client.replaceHTMLCodes(plot)
                    plot = six.ensure_str(plot, errors='ignore')

                self.list.append({'title': title, 'originaltitle': title, 'year': year,
                                  'genre': genre, 'duration': duration, 'rating': rating,
                                  'votes': votes, 'mpaa': mpaa, 'director': director,
                                  'plot': plot, 'tagline': '0', 'imdb': imdb, 'tmdb': '0',
                                  'tvdb': '0', 'poster': poster, 'cast': cast, 'next': next})
            except Exception as e:
                import traceback
                failure = traceback.format_exc()
                c.log('[CM Debug @ 993 in movies.py]Traceback:: ' + str(failure))
                c.log('[CM Debug @ 993 in movies.py]Exception raised. Error = ' + str(e))
                pass

        return self.list

    ####cm#
    # New def to hande tmdb persons listings
    def tmdb_person_list(self, url):
        try:
            result = self.session.get(url, timeout=15).json()
            items = result['results']
        except:
            pass

        for item in items:
            try:
                name = item['name']
                id = item['id']
                image = self.tmdb_img_prelink.format('original', item['profile_path'])
                url = self.personmovies_link % id
                self.list.append({'name': name, 'url': url, 'image': image})
            except:
                pass
        
        return self.list
        
    def worker(self, level=1):
        self.meta = []
        total = len(self.list)

        for i in range(total): self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        for r in range(0, total, 40):
            threads = []
            for i in list(range(r, r+40)):
                if i <= total:
                    threads.append(workers.Thread(self.super_info, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

        if self.meta:
            metacache.insert(self.meta)

        self.list = [i for i in self.list if not i['imdb'] == '0']

    def super_info(self, i) -> None:
        '''
        Filling missing pieces
        '''
        try:
            if self.list[i]['metacache'] == True:
                # raise Exception()

                return

            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            list_title = self.list[i]['title']

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=15).json()
                    movie_result = result['movie_results'][0]
                    tmdb = movie_result['id']
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except:
                    pass

            _id = tmdb if not tmdb == '0' else imdb
            if _id == '0':
                raise Exception()

            en_url = self.tmdb_api_link % _id
            trans_url = en_url + ',translations'
            url = en_url if self.lang == 'en' else trans_url

            item = self.session.get(url, timeout=15).json()

            if imdb == '0':
                try:
                    imdb = item['external_ids']['imdb_id']
                    if not imdb:
                        imdb = '0'
                except:
                    imdb = '0'

            mpaa = item.get('mpaa', '0')

            original_language = item.get('original_language', '')

            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data']
                                     for x in translations if x['iso_639_1'] == 'en'][0]
                except:
                    en_trans_item = {}

            name = item.get('title', '')
            original_title = item.get('original_title', '')
            en_trans_name = en_trans_item.get(
                'title', '') if not self.lang == 'en' else None
            # c.log('self_lang: %s | original_language: %s | list_title: %s | name: %s | original_title: %s | en_trans_name: %s' % (self.lang, original_language, list_title, name, original_name, en_trans_name))

            if self.lang == 'en':
                title = label = name
            else:
                title = en_trans_name or original_title
                if original_language == self.lang:
                    label = name
                else:
                    label = en_trans_name or name
            if not title:
                title = list_title
            if not label:
                label = list_title

            plot = item.get('overview') or self.list[i]['plot']

            tagline = item.get('tagline') or '0'

            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview', '')
                    if en_plot:
                        plot = en_plot

                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline', '')
                    if en_tagline:
                        tagline = en_tagline

            premiered = item.get('release_date') or '0'

            try:
                _year = re.findall('(\d{4})', premiered)[0]
            except:
                _year = ''
            if not _year:
                _year = '0'
            year = self.list[i]['year'] if not self.list[i]['year'] == '0' else _year

            status = item.get('status') or '0'

            try:
                studio = item['production_companies'][0]['name']
            except:
                studio = ''
            if not studio:
                studio = '0'

            try:
                genre = item['genres']
                genre = [d['name'] for d in genre]
                genre = ' / '.join(genre)
            except:
                genre = ''
            if not genre:
                genre = '0'

            try:
                country = item['production_countries']
                country = [c['name'] for c in country]
                country = ' / '.join(country)
            except:
                country = ''
            if not country:
                country = '0'

            try:
                duration = str(item['runtime'])
            except:
                duration = ''
            if not duration:
                duration = '0'

            rating = item['vote_average'] if 'vote_average' in item else '0'
            votes = item['votese'] if 'votes' in item else '0'

            castwiththumb = []
            try:
                cast = item['aggregate_credits']['cast'][:30]
                for person in cast:
                    _icon = person['profile_path']
                    icon = self.tmdb_img_link % ('185', _icon) if _icon else ''
                    castwiththumb.append(
                        {'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
            except:
                pass
            if not castwiththumb:
                castwiththumb = '0'

            try:
                crew = item['credits']['crew']
                director = ', '.join([d['name'] for d in [x for x in crew if x['job'] == 'Director']])
                writer = ', '.join([w['name'] for w in [y for y in crew if y['job'] in ['Writer', 'Screenplay', 'Author', 'Novel']]])
            except:
                director = writer = '0'

            poster1 = self.list[i]['poster']

            poster_path = item.get('poster_path')
            if poster_path:
                poster2 = self.tmdb_img_prelink.format('original', poster_path)
            else:
                poster2 = ''

            backdrop_path = item.get('backdrop_path')
            if backdrop_path:
                fanart1 = self.tmdb_img_prelink.format('original', backdrop_path)
            else:
                fanart1 = '0'

            poster3 = fanart2 = ''
            banner = clearlogo = clearart = landscape = discart = '0'

            if not imdb == '0':

                try:
                    r2 = self.session.get(self.fanart_tv_art_link % imdb, headers=self.fanart_tv_headers, timeout=16)
                    r2.raise_for_status()
                    r2.encoding = 'utf-8'
                    art = r2.json()

                    try:
                        _poster3 = art['movieposter']
                        _poster3 = [x for x in _poster3 if x.get('lang') == self.lang][::-1] + [x for x in _poster3 if x.get(
                            'lang') == 'en'][::-1] + [x for x in _poster3 if x.get('lang') in ['00', '']][::-1]
                        _poster3 = _poster3[0]['url']
                        if _poster3:
                            poster3 = _poster3
                    except:
                        pass

                    try:
                        if 'moviebackground' in art:
                            _fanart2 = art['moviebackground']
                        else:
                            _fanart2 = art['moviethumb']
                        _fanart2 = [x for x in _fanart2 if x.get('lang') == self.lang][::-1] + [x for x in _fanart2 if x.get('lang') == 'en'][::-1] + [x for x in _fanart2 if x.get('lang') in ['00', '']][::-1]
                        _fanart2 = _fanart2[0]['url']
                        if _fanart2:
                            fanart2 = _fanart2
                    except:
                        pass

                    try:
                        _banner = art['moviebanner']
                        _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
                        _banner = _banner[0]['url']
                        if _banner: banner = _banner
                    except:
                        pass

                    try:
                        if 'hdmovielogo' in art:
                            _clearlogo = art['hdmovielogo']
                        else:
                            _clearlogo = art['clearlogo']
                        _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
                        _clearlogo = _clearlogo[0]['url']
                        if _clearlogo: clearlogo = _clearlogo
                    except:
                        pass

                    try:
                        if 'hdmovieclearart' in art:
                            _clearart = art['hdmovieclearart']
                        else:
                            _clearart = art['clearart']
                        _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
                        _clearart = _clearart[0]['url']
                        if _clearart: clearart = _clearart
                    except:
                        pass

                    try:
                        if 'moviethumb' in art: 
                            _landscape = art['moviethumb']
                        else:
                            _landscape = art['moviebackground']
                        _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
                        _landscape = _landscape[0]['url']
                        if _landscape: landscape = _landscape
                    except:
                        pass

                    try:
                        if 'moviedisc' in art: _discart = art['moviedisc']
                        _discart = [x for x in _discart if x.get('lang') == self.lang][::-1] + [x for x in _discart if x.get('lang') == 'en'][::-1] + [x for x in _discart if x.get('lang') in ['00', '']][::-1]
                        _discart = _discart[0]['url']
                        if _discart: discart = _discart
                    except:
                        pass
                except Exception as e:
                    c.log('fanart.tv art fail. Error = ' + str(e))
                    pass

            poster = poster3 or poster2 or poster1
            fanart = fanart2 or fanart1

            item = {'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb,
                    'tmdb': tmdb, 'poster': poster,
                    'banner': banner, 'fanart': fanart, 'landscape': landscape, 'discart': discart,
                    'fanart2': fanart2, 'clearlogo': clearlogo,
                    'clearart': clearart, 'premiered': premiered, 'genre': genre,
                    'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa,
                    'director': director, 'writer': writer, 'castwiththumb': castwiththumb,
                    'plot': plot, 'tagline': tagline}

            item = dict((k, v) for k, v in item.items() if not v == '0')
            self.list[i].update(item)

            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0',
                    'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)

        except:
            pass

    def movieDirectory(self, items):
        if items == None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()
        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')
        addonClearlogo, addonClearart = control.addonClearlogo(), control.addonClearart()
        addonDiscart = control.addonDiscart()

        traktCredentials = trakt.getTraktCredentialsInfo()

        isPlayable = 'true' if not 'plugin' in control.infoLabel( 'Container.PluginName') else 'false'
        indicators = playcount.getMovieIndicators(refresh=True) if action == 'movies' else playcount.getMovieIndicators()
        findSimilar = control.lang(32100)
        playbackMenu = control.lang(32063) if control.setting('hosts.mode') == '2' else control.lang(32064)
        watchedMenu = control.lang(32068) if traktCredentials else control.lang(32066)
        unwatchedMenu = control.lang(32069) if traktCredentials else control.lang(32067)
        queueMenu = control.lang(32065)
        traktManagerMenu = control.lang(32515)
        nextMenu = control.lang(32053)
        addToLibrary = control.lang(32551)
        infoMenu = control.lang(32101)

        for i in items:
            # c.log('[CM Debug @ 1507 in movies.py] i =' + repr(i))
            try:
                label = '%s (%s)' % (i['title'], i['year'])
                imdb, tmdb, title, year = i['imdb'], i['tmdb'], i['originaltitle'], i['year']
                sysname = quote_plus('%s (%s)' % (title, year))
                label = i['label'] if 'label' in i and not i['label'] == '0' else title
                label = '%s (%s)' % (label, year)
                status = i['status'] if 'status' in i else '0'
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Upcoming', 'In Production', 'Planned']) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):

                        # changed by cm -  17-5-2023
                        colorlist = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
                        colornr = colorlist[int(control.setting('unaired.identify'))]
                        unairedcolor = re.sub("\][\w\s]*\[", "][I]%s[/I][", control.lang(int(colornr)))
                        label = unairedcolor % label

                        if unairedcolor == '':
                            unairedcolor = '[COLOR red][I]%s[/I][/COLOR]'
                except:
                    pass

                sysname = quote_plus('%s (%s)' % (title, year))
                systitle = quote_plus(title)

                meta = dict((k, v) for k, v in i.items() if not v == '0')
                meta.update({'code': imdb, 'imdbnumber': imdb})
                meta.update({'tmdb_id': tmdb})
                meta.update({'imdb_id': imdb})
                meta.update({'mediatype': 'movie'})
                meta.update({'trailer': '%s?action=trailer&name=%s&tmdb=%s&imdb=%s' % (
                    sysaddon, quote_plus(label), tmdb, imdb)})

                if (not 'duration' in i) or (i['duration'] == '0'):
                    meta.update({'duration': '120'})

                try:
                    meta.update({'duration': str(int(meta['duration']) * 60)})
                except:
                    pass
                try:
                    meta.update(
                        {'genre': cleangenre.lang(meta['genre'], self.lang)})
                except:
                    pass

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                banner = i['banner'] if 'banner' in i and not i['banner'] == '0' else addonBanner
                landscape = i['landscape'] if 'landscape' in i and not i['landscape'] == '0' else fanart
                clearlogo = i['clearlogo'] if 'clearlogo' in i and not i['clearlogo'] == '0' else addonClearlogo
                clearart = i['clearart'] if 'clearart' in i and not i['clearart'] == '0' else addonClearart
                discart = i['discart'] if 'discart' in i and not i['discart'] == '0' else addonDiscart

                poster = [i[x] for x in ['poster3', 'poster',
                                         'poster2'] if i.get(x, '0') != '0']
                poster = poster[0] if poster else addonPoster
                meta.update({'poster': poster})

                sysmeta = quote_plus(json.dumps(meta))

                url = '%s?action=play&title=%s&year=%s&imdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)
                sysurl = quote_plus(url)

                cm = []
                cm.append((findSimilar, 'Container.Update(%s?action=movies&url=%s)' % (sysaddon, quote_plus(self.related_link % tmdb))))
                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try:
                    overlay = int(playcount.getMovieOverlay(indicators, imdb))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=6)' % (sysaddon, imdb)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=moviePlaycount&imdb=%s&query=7)' % (sysaddon, imdb)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&imdb=%s&content=movie)' % (sysaddon, sysname, imdb)))

                cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

                cm.append((addToLibrary, 'RunPlugin(%s?action=movieToLibrary&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))

                try:
                    item = control.item(label=label, offscreen=True)
                except:
                    item = control.item(label=label)

                art = {}
                art.update({'icon': poster, 'thumb': poster, 'poster': poster})

                if settingFanart == 'true':
                    art.update({'fanart': fanart})
                art.update({'banner': banner})
                art.update({'clearlogo': clearlogo})
                art.update({'clearart': clearart})
                art.update({'landscape': landscape})
                art.update({'discart': discart})

                item.setArt(art)

                item.addContextMenuItems(cm)

                item.setProperty('IsPlayable', isPlayable)

                castwiththumb = i.get('castwiththumb')

                if castwiththumb and not castwiththumb == '0':
                    item.setCast(castwiththumb)

                offset = bookmarks.get('movie', imdb, '', '', True)
                if float(offset) > 120:
                    percentPlayed = int(float(offset) / float(meta['duration']) * 100)
                    item.setProperty('resumetime', str(offset))
                    item.setProperty('percentplayed', str(percentPlayed))

                item.setProperty('imdb_id', imdb)
                item.setProperty('tmdb_id', tmdb)
                try:
                    item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})

                except:
                    pass
                item.setInfo(type='Video', infoLabels=control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
            except:
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()

            icon = control.addonNext()
            url = '%s?action=moviePage&url=%s' % (sysaddon, quote_plus(url))

            try:
                item = control.item(label=nextMenu, offscreen=True)
            except:
                item = control.item(label=nextMenu)

            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': addonFanart})

            control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
        except:
            pass

        control.content(syshandle, 'movies')
        control.directory(syshandle, cacheToDisc=True)
        views.setView('movies', {'skin.estuary': 55, 'skin.confluence': 500})

    def addDirectory(self, items, queue=False):
        if items == None or len(items) == 0:
            control.idle()
            sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()
        queueMenu = control.lang(32065)
        playRandom = control.lang(32535)
        addToLibrary = control.lang(32551)

        for i in items:
            try:
                name = i['name']

                plot = i.get('plot') or '[CR]'
                if i['image'].startswith('http'):
                    thumb = i['image']
                elif not artPath == None:
                    thumb = os.path.join(artPath, i['image'])
                else:
                    thumb = addonThumb

                url = '%s?action=%s' % (sysaddon, i['action'])
                try:
                    url += '&url=%s' % quote_plus(i['url'])
                except:
                    pass

                cm = []

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=movie&url=%s)' % (sysaddon, quote_plus(i['url']))))

                if queue == True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try:
                    cm.append((addToLibrary, 'RunPlugin(%s?action=moviesToLibrary&url=%s)' % (sysaddon, quote_plus(i['context']))))
                except:
                    pass

                try:
                    item = control.item(label=name, offscreen=True)
                except:
                    item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addonFanart})
                item.setInfo(type='video', infoLabels={'plot': plot})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                c.log('mov_addDir', 1)
                pass

        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)
