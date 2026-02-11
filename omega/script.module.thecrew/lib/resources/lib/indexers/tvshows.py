# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file tvshows.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import urllib

from urllib.parse import quote, quote_plus, parse_qsl, urlparse, urlsplit, urlencode



from resources.lib.modules import trakt
from resources.lib.modules import keys
from resources.lib.modules import cleantitle
from resources.lib.modules import cleangenre
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
from resources.lib.modules.crewruntime import c

from bs4 import BeautifulSoup

import os,sys,re,datetime, base64
import simplejson as json

import six
from six.moves import zip

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

import requests

params = dict(urllib.parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')





class tvshows:
    def __init__(self):
        self.list = []

        self.session = requests.Session()

        self.imdb_link = 'https://www.imdb.com'
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://www.tvmaze.com'
        self.tmdb_link = 'https://api.themoviedb.org/3'
        self.logo_link = 'https://i.imgur.com/'
        self.tvdb_key = control.setting('tvdb.user')
        if self.tvdb_key == '' or self.tvdb_key == None:
            self.tvdb_key = '27bef29779bbffe947232dc310a91f0c'

        self.datetime = datetime.datetime.now()
        self.year = self.datetime.strftime('%Y')

        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.user = control.setting('fanart.tv.user') + str('')
        self.count = int(control.setting('page.item.limit'))
        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.trailer_source = control.setting('trailer.source') or '2'
        self.country = control.setting('official.country') or 'US'
        self.lang = control.apiLanguage()['tmdb'] or 'en'


        self.datetime = datetime.datetime.now()# - datetime.timedelta(hours = 5)
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.specials = control.setting('tv.specials') or 'true'
        self.showunaired = control.setting('showunaired') or 'true'
        self.hq_artwork = control.setting('hq.artwork') or 'true'
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.fanart_tv_user = control.setting('fanart.tv.user')
        self.user = control.setting('fanart.tv.user')

        self.tmdb_user = control.setting('tm.personal_user') or control.setting('tm.user')
        if not self.tmdb_user: self.tmdb_user = keys.tmdb_key

        self.fanart_tv_headers = {'api-key': keys.fanart_key}
        if not self.fanart_tv_user == '': self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})

        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.trailer_source = control.setting('trailer.source') or '2'
        self.country = control.setting('official.country') or 'US'
        self.lang = control.apiLanguage()['tmdb'] or 'en'

        self.search_link = 'https://api.trakt.tv/search/show?limit=20&page=1&query='
        self.tvmaze_info_link = 'https://api.tvmaze.com/shows/%s'
        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'
        self.fanart_tv_level_link = 'http://webservice.fanart.tv/v3/level'

        ####cm##
        # tmdb status movies
        # [ 'Canceled', 'In Production', 'Planned', 'Post Production', 'Released', 'Rumored' ]
        #
        # tmdb status tvshow
        # ['Returning Series', 'Planned', 'In Production', 'Ended', 'Canceled', 'Pilot']

        ######
        #IMDB
        #
        #self.imdblists_link = 'https://www.imdb.com/user/ur%s/lists?tab=all&sort=modified&order=desc&filter=titles' % self.imdb_user
        #self.imdblist_link = 'https://www.imdb.com/list/%s/?view=simple&sort=date_added,desc&title_type=tv_series,tv_miniseries&start=1'
        #self.imdblist2_link = 'https://www.imdb.com/list/%s/?view=simple&sort=alpha,asc&title_type=tv_series,tv_miniseries&start=1'
        #self.imdbwatchlist2_link = 'https://www.imdb.com/user/ur%s/watchlist?sort=alpha,asc' % self.imdb_user
        #self.imdbwatchlist_link = 'https://www.imdb.com/user/ur%s/watchlist?sort=date_added,desc' % self.imdb_user

        #self.active_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=10,&production_status=active&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        #self.views_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&num_votes=100,&release_date=,date[0]&sort=num_votes,desc&count=%s&start=1' % self.items_per_page
        #self.keyword_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&keywords=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        #self.certification_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&certificates=us:%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)

        self.person_link = ('{}/{}/{}?api_key={}&query={}&include_adult=false&language=en-US&page=1' ).format(self.tmdb_link, 'search', 'person', self.tmdb_user, '%s')
        self.persons_link = ('{}/{}/{}?api_key={}&?language=en-US').format(self.tmdb_link, 'person', '%s', self.tmdb_user)
        self.personlist_link = ('{}/{}/{}/{}?api_key={}&language=en-US').format(self.tmdb_link, 'trending', 'person', 'day', self.tmdb_user)
        self.person_show_link = ('{}/{}/{}/tv_credits?api_key={}&language=en-US').format(self.tmdb_link, 'person', '%s', self.tmdb_user)

        self.premiere_link = ('{}/{}/{}?api_key={}&include_adult=false&first_air_date.gte=date[60]&include_null_first_air_dates=false&language={}&sort_by=popularity.desc&with_origin_country=US|UK|AU&with_original_language={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US','en')
        self.airing_link = ('{}/{}/{}?api_key={}&language={}&with_origin_country=US|UK|AU&with_original_language={}&sort_by=popularity.desc&air_date.lte=date[0]&air_date.gte=date[1]&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US', 'en')
        self.popular_link = ('{}/{}/{}?api_key={}&include_adult=false&include_null_first_air_dates=false&sort_by=popularity.desc&vote_count.gte=1000&with_origin_country=US|UK|AU&air_date.gte=date[1]&language={}&with_original_language={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US', 'en')
        self.genre_link = ('{}/{}/{}?api_key={}&include_adult=false&include_null_first_air_dates=false&language={}&sort_by=popularity.desc&with_origin_country=US|UK|AU&with_original_language={}&first_air_date.lte={}&with_genres={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US', 'en', self.today_date, '%s')
        self.rating_link = ('{}/{}/{}?api_key={}&include_adult=false&include_null_first_air_dates=false&language={}&with_origin_country=US|UK|AU&with_original_language={}&sort_by=vote_average.desc&vote_count.gte={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US', 'en', '200')
        self.views_link = ('{}/{}/{}?api_key={}&include_adult=false&include_null_first_air_dates=false&language={}&with_origin_country=US|UK|AU&with_original_language={}&sort_by=vote_count.desc&vote_count.gte={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US', 'en', '1500')
        self.language_link = ('{}/{}/{}?api_key={}&include_adult=false&include_video=false&sort_by=popularity.desc&with_original_language={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, '%s')
        self.active_link = ('{}/{}/{}?api_key={}&include_adult=false&include_null_first_air_dates=false&language={}&sort_by=popularity.desc&with_origin_country=US|UK|AU&with_original_language={}&with_status={}&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, 'en-US', 'en', '0|2')

        ######
        #trakt
        #
        self.trending_link = 'https://api.trakt.tv/shows/trending?limit=40&page=1'
        self.traktlists_link = 'https://api.trakt.tv/users/me/lists'
        self.traktlikedlists_link = 'https://api.trakt.tv/users/likes/lists?limit=1000000'
        self.traktlist_link = 'https://api.trakt.tv/users/%s/lists/%s/items'
        self.traktcollection_link = 'https://api.trakt.tv/users/me/collection/shows'
        self.traktwatchlist_link = 'https://api.trakt.tv/users/me/watchlist/shows'
        self.traktfeatured_link = 'https://api.trakt.tv/recommendations/shows?limit=40'
        self.related_link = 'https://api.trakt.tv/shows/%s/related'

        ######
        #tmdb
        #
        self.tmdb_link = 'https://api.themoviedb.org/3/'
        self.tmdb_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.tmdb_img_prelink = 'https://image.tmdb.org/t/p/{}{}'

        self.tmdb_api_link = ('{}tv/{}?api_key={}&language={}&append_to_response=aggregate_credits,content_ratings,external_ids').format(self.tmdb_link, '%s', self.tmdb_user, self.lang)
        self.tmdb_networks_link = ('{}discover/tv?api_key={}&sort_by=first_air_date.desc&with_networks={}&page=1').format(self.tmdb_link, self.tmdb_user, '%s')
        self.tmdb_networks_link_no_unaired = ('{}discover/tv?api_key={}&first_air_date.lte={}&sort_by=first_air_date.desc&with_networks={}&page=1').format(self.tmdb_link, self.tmdb_user, self.today_date, '%s')
        self.tmdb_search_tvshow_link = 'https://api.themoviedb.org/3/search/tv?api_key=%s&language=en-US&query=%s&page=1' % (self.tmdb_user, '%s')
        self.search_link = 'https://api.themoviedb.org/3/search/tv?api_key=%s&language=en-US&query=%s&page=1' % (self.tmdb_user, '%s')
        self.related_link = 'https://api.themoviedb.org/3/tv/%s/similar?api_key=%s&page=1' % ('%s', self.tmdb_user)

        self.tmdb_info_tvshow_link = ('{}{}/{}?api_key={}&language={}&append_to_response=images').format(self.tmdb_link, 'tv', '%s', self.tmdb_user, self.lang)
        self.tmdb_by_imdb = ('{}find/{}?api_key={}&external_source=imdb_id').format(self.tmdb_link, '%s', self.tmdb_user)

        self.tmdb_tv_top_rated_link = ('{}{}/{}?api_key={}&language={}&sort_by=popularity.desc&page=1').format(self.tmdb_link, 'tv', 'top_rated', self.tmdb_user, self.lang)
        self.tmdb_tv_popular_tv_link = ('{}{}/{}?api_key={}&language={}&page=1').format(self.tmdb_link, 'tv', 'popular', self.tmdb_user, self.lang)
        self.tmdb_tv_on_the_air_link = ('{}{}/{}?api_key={}&language={}&page=1').format(self.tmdb_link, 'tv', 'on_the_air', self.tmdb_user, self.lang)
        self.tmdb_tv_airing_today_link = ('{}{}/{}?api_key={}&language={}&page=1').format(self.tmdb_link, 'tv', 'airing_today', self.tmdb_user, self.lang)
        self.tmdb_tv_trending_day_link = ('{}/{}/{}/{}?api_key={}').format(self.tmdb_link, 'trending', 'tv', 'day', self.tmdb_user)
        self.tmdb_tv_trending_week_link = ('{}/{}/{}/{}?api_key={}').format(self.tmdb_link, 'trending', 'tv', 'week', self.tmdb_user)
        self.tmdb_tv_discover_year_link = ('{}{}/{}?api_key={}&language=%s&sort_by=popularity.desc&first_air_date_year={}&include_null_first_air_dates=false&with_original_language=en&page=1').format(self.tmdb_link, 'discover', 'tv', self.tmdb_user, self.year)

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
                    
            if(self.showunaired) == 'false' and url == self.tmdb_networks_link:
                url = self.tmdb_networks_link_no_unaired

            try: 
                u = urllib.parse.urlparse(url).netloc.lower()
            except: 
                pass

            if u in self.trakt_link and '/users/' in url:
                try:
                    if not '/users/me/' in url:  raise Exception()
                    if trakt.getActivity() > cache.timeout(self.trakt_list, url, self.trakt_user): 
                        raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                except:
                    self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)

                if '/users/me/' in url and '/collection/' in url:
                    self.list = sorted(self.list, key=lambda k: utils.title_key(k['title']))
                if idx == True: self.worker()

            elif u in self.trakt_link:
                self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                if idx == True: self.worker()

            elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
                self.list = cache.get(self.imdb_list, 1, url)
                if idx == True: self.worker()

            elif u in self.imdb_link: #checked
                self.list = cache.get(self.imdb_list, 24, url)
                if idx == True: self.worker()

            elif u in self.tvmaze_link:
                self.list = cache.get(self.tvmaze_list, 168, url)
                if idx == True: self.worker()

            elif u in self.tmdb_link and 'tv_credits' in url:
                self.list = cache.get(self.tmdb_cast_list, 24, url)
                #self.list = self.tmdb_cast_list(url)
                self.list = sorted(self.list, key=lambda k: int(k['year']), reverse=True)
                if idx == True: self.worker()

            elif u in self.tmdb_link and self.search_link in url:
                self.list = cache.get(self.tmdb_list, 1, url)
                if idx == True: self.worker(level=0)

            elif u in self.tmdb_networks_link:
                self.list = cache.get(self.tmdb_list, 24, url, tid)
                if idx == True: self.worker()

            elif u in self.tmdb_link:
                self.list = cache.get(self.tmdb_list, 24, url)
                c.log(f'[CM DEBUG @ 247 in tvshows.py] url = {url} and u = {u}')
                #self.tmdb_list(url)
                if idx == True: self.worker()

            if idx == True and create_directory == True: self.tvshowDirectory(self.list)
            return self.list
        except Exception as e:
            #import traceback
            #failure = traceback.format_exc()
            #c.log('[CM Debug @ 288 in tvshows.py]Traceback:: ' + str(failure))
            c.log('[CM Debug @ 288 in ]Exception raised. Error = ' + str(e))
            pass
        
        
        #except:
        #    c.log('Exception in tvshows.get()')
        #    pass


#TC 2/01/19 started
    def search(self):
        navigator.navigator().addDirectoryItem(32603, 'tvSearchnew', 'search.png', 'DefaultTVShows.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS tvshow (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM tvshow ORDER BY ID DESC")

        lst = []
        delete_option = False
        for (id, term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term, f'tvSearchterm&name={term}', 'search.png', 'DefaultTVShows.png')
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

        if not q: return
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO tvshow VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.search_link % urllib.parse.quote_plus(q)

        self.get(url)

    def search_term(self, q):
        control.idle()
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM tvshow WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO tvshow VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.search_link % urllib.parse.quote_plus(q)

        self.get(url)

    def person(self):
        try:
            control.idle()

            t = control.lang(32010)
            k = control.keyboard('', t)
            k.doModal()
            q = k.getText() if k.isConfirmed() else None

            if not q:
                return

            url = self.person_link % urllib.parse.quote(q)
            c.log('[CM DEBUG @ 364 in tvshows.py] url = ' + str(url))

            self.persons(url)

        except:
            return

    #####cm#
    # Completely redone for compatibility with tmdb
    # source reference/genre-tv-list
    def genres(self):
        genres = [
            { "id": 10759, "name": "Action & Adventure"},
            { "id": 16, "name": "Animation"},
            { "id": 35, "name": "Comedy"},
            { "id": 80, "name": "Crime"},
            { "id": 99, "name": "Documentary"},
            { "id": 18, "name": "Drama"},
            { "id": 10751, "name": "Family"},
            { "id": 10762, "name": "Kids"},
            { "id": 9648, "name": "Mystery"},
            { "id": 10763, "name": "News"},
            { "id": 10764, "name": "Reality"},
            { "id": 10765, "name": "Sci-Fi & Fantasy"},
            { "id": 10766, "name": "Soap"},
            { "id": 10767, "name": "Talk"},
            { "id": 10768, "name": "War & Politics"},
            { "id": 37, "name": "Western"}
        ]

        for i in genres:
            self.list.append(
                {
                    'name': cleangenre.lang(i['name'], self.lang),
                    'url': self.genre_link % i['id'],
                    'image': 'genres.png',
                    'action': 'tvshows'
                })

        self.addDirectory(self.list)
        return self.list

    def networks(self):
        networks = [
        (129,"A&E", 'https://image.tmdb.org/t/p/original/ptSTdU4GPNJ1M8UVEOtA0KgtuNk.png'),
        (2,"ABC", 'https://image.tmdb.org/t/p/original/an88sKsFz0KX5CQngAM95WkncX4.png'),
        (1024,"Amazon", 'https://image.tmdb.org/t/p/original/uK6yuqMkUvKhCgVJjg5JWDUoabA.png'),
        (174,"AMC", 'https://image.tmdb.org/t/p/original/alqLicR1ZMHMaZGP3xRQxn9sq7p.png'),
        (91,"Animal Planet", 'https://image.tmdb.org/t/p/original/xQ25rzpv83d74V1zpOzSHbYlwJq.png'),
        (173,"AT-X", 'https://image.tmdb.org/t/p/original/fERjndErEpveJmQZccJbJDi93rj.png'),
        (493,"BBC America", 'https://image.tmdb.org/t/p/original/8Js4sUaxjE3RSxJcOCDjfXvhZqz.png'),
        (4,"BBC One", 'https://image.tmdb.org/t/p/original/uJjcCg3O4DMEjM0xtno9OWFciRP.png'),
        (332,"BBC Two", 'https://image.tmdb.org/t/p/original/7HVPn1p2w1nC5oRKBehXVHpss7e.png'),
        (3,"BBC Three", 'https://image.tmdb.org/t/p/original/s22fRhj8xFPbiexrJwiAOcDEIrS.png'),
        (100,"BBC Four", 'https://image.tmdb.org/t/p/original/AgsOSxGvfxIonhPgrfkWCmsOKfA.png'),
        (24,"BET", 'https://image.tmdb.org/t/p/original/gaouRlJrfZlEA5EPHhO5qqZ1Fgu.png'),
        (74,"Bravo", 'https://image.tmdb.org/t/p/original/wX5HsfS47u6UUCSpYXqaQ1x2qdu.png'),
        (56,"Cartoon Network", 'https://image.tmdb.org/t/p/original/c5OC6oVCg6QP4eqzW6XIq17CQjI.png'),
        (201,"CBC", 'https://image.tmdb.org/t/p/original/qNooLje0YQh1y3y9LUM2Y5QCtiF.png'),
        (16,"CBS", 'https://image.tmdb.org/t/p/original/wju8KhOUsR5y4bH9p3Jc50hhaLO.png'),
        (26,"Channel 4", 'https://image.tmdb.org/t/p/original/zCUWm0Xb6AnjUbxzjL5OkzmHhd7.png'),
        (99,"Channel 5", 'https://image.tmdb.org/t/p/original/bMuKs6xuhI0GHSsq4WWd9FsntUN.png'),
        (47,"Comedy Central", 'https://image.tmdb.org/t/p/original/6ooPjtXufjsoskdJqj6pxuvHEno.png'),
        (2548,"CBC", 'https://image.tmdb.org/t/p/original/qe2RYSTCxbPh3jCaM1tk9E4uJZ6.png'),
        (403,"CTV", 'https://image.tmdb.org/t/p/original/volHUxY1MHjSPI4ju7j36EdhR2m.png'),
        (928,"Crackle", 'https://image.tmdb.org/t/p/original/bR8S6Fjv3VGtEKyKF5lvvRJ5xfw.png'),
        (71,"The CW", 'https://image.tmdb.org/t/p/original/ge9hzeaU7nMtQ4PjkFlc68dGAJ9.png'),
        (1049,"CW seed", 'https://image.tmdb.org/t/p/original/wwo3PZyBpHL3Wz8eg4cr3kqVZQY.png'),
        (64,"Discovery", 'https://image.tmdb.org/t/p/original/8qkdZlbrTSVfkJ73DjOBrwYtMSC.png'),
        (4883,"discovery+", 'https://image.tmdb.org/t/p/original/iKvdFk5lpbvs4g0vd6yVUcV36i3.png'),
        (244,"Discovery ID", 'https://image.tmdb.org/t/p/original/yfkdPLHjsed7vwUNuh20eMuDiDO.png'),
        (2739,"Disney+", 'https://image.tmdb.org/t/p/original/PQxvkeK8cTtD7vjataBsNpjbJ5.png'),
        (54,"Disney Channel", 'https://image.tmdb.org/t/p/original/gvhBea9OGqChmGKHa5CntbmsDBp.png'),
        (44,"Disney XD", 'https://image.tmdb.org/t/p/original/nKM9EnV7jTpt3MKRbhBusJ03lAY.png'),
        (2087,"Discovery Channel", 'https://image.tmdb.org/t/p/original/8qkdZlbrTSVfkJ73DjOBrwYtMSC.png'),
        (76,"E! Entertainment", 'https://image.tmdb.org/t/p/original/ptpx2Ag52sYJG6LiX9zBlnKsQOS.png'),
        (136,"E4", 'https://image.tmdb.org/t/p/original/fJPM9Rj12us4HF03N3qvakz7WuZ.png'),
        (19,"FOX", 'https://image.tmdb.org/t/p/original/1DSpHrWyOORkL9N2QHX7Adt31mQ.png'),
        (1267,"Freeform", 'https://image.tmdb.org/t/p/original/jk2Z7WH6JnHSZrxouYh4sireM3a.png'),
        (88,"FX", 'https://image.tmdb.org/t/p/original/aexGjtcs42DgRtZh7zOxayiry4J.png'),
        (384,"Hallmark Channel", 'https://image.tmdb.org/t/p/original/9JTL7HcaiVxq7M6eu5m7giFqaxR.png'),
        (65,"History", 'https://image.tmdb.org/t/p/original/9fGgdJz17aBX7dOyfHJtsozB7bf.png'),
        (49,"HBO", 'https://image.tmdb.org/t/p/original/hizvY65SpyF3BPY2qsBZMgUOxjs.png'),
        (3186,"HBO Max", 'https://image.tmdb.org/t/p/original/nmU0UMDJB3dRRQSTUqawzF2Od1a.png'),
        (210,"HGTV", 'https://image.tmdb.org/t/p/original/tzTtKdQ7vC2FkBvJDUErOhBPdKJ.png'),
        (453,"Hulu", 'https://image.tmdb.org/t/p/original/pqUTCleNUiTLAVlelGxUgWn1ELh.png'),
        (9,"ITV", 'https://image.tmdb.org/t/p/original/j3KAlTmxGDCHQZqs1A2hagzjYqu.png'),
        (34,"Lifetime", 'https://image.tmdb.org/t/p/original/kU18GafTybg4uMhkj3wvsGBgn8s.png'),
        (33,"MTV USA", 'https://image.tmdb.org/t/p/original/w4qtv7xBkSVsbOQdSzjUjlyOuSr.png'),
        (488,"MTV UK", 'https://image.tmdb.org/t/p/original/w4qtv7xBkSVsbOQdSzjUjlyOuSr.png'),
        (43,"National Geographic", 'https://image.tmdb.org/t/p/original/q9rPBG1rHbUjII1Qn98VG2v7cFa.png'),
        (6,"NBC", 'https://image.tmdb.org/t/p/original/cm111bsDVlYaC1foL0itvEI4yLG.png'),
        (213,"Netflix", 'https://image.tmdb.org/t/p/original/wwemzKWzjKYJFfCeiB57q3r4Bcm.png'),
        (13,"Nickelodeon", 'https://image.tmdb.org/t/p/original/aYkLXz4dxHgOrFNH7Jv7Cpy56Ms.png'),
        (14,"PBS", 'https://image.tmdb.org/t/p/original/hp2Fs7AIdsMlEjiDUC1V8Ows2jM.png'),
        (67,"Showtime", 'https://image.tmdb.org/t/p/original/Allse9kbjiP6ExaQrnSpIhkurEi.png'),
        (1755,"Sky History", 'https://image.tmdb.org/t/p/original/mzLlbqnnLiDIzriohlvfSbWlEfR.png'),
        (1431,"Sky One", 'https://image.tmdb.org/t/p/original/dVBHOr0nYCx9GSNesTVb1TT52Xj.png'),
        (318,"Starz", 'https://image.tmdb.org/t/p/original/GMDGZk9iDG4WDijY3VgUgJeyus.png'),
        (270,"SundanceTV", 'https://image.tmdb.org/t/p/original/xhTdszjVRy1tABMix2dffBcdDJ1.png'),
        (77,"Syfy", 'https://image.tmdb.org/t/p/original/iYfrkobwDhTOFJ4AXYPSLIEeaAT.png'),
        (68,"TBS", 'https://image.tmdb.org/t/p/original/9PYsQf3YbDUJo1rg3pgtaiOrb6s.png'),
        (84,"TLC", 'https://image.tmdb.org/t/p/original/6GRfZSrYh9D6C88n9kWlyrySB2l.png'),
        (41,"TNT", 'https://image.tmdb.org/t/p/original/6ISsKwa2XUhSC6oBtHZjYf6xFqv.png'),
        (209,"Travel Channel", 'https://image.tmdb.org/t/p/original/8SwN81R7P5vD5mhtOE0taw5mji4.png'),
        (364,"truTV", 'https://image.tmdb.org/t/p/original/c48pVcWAEYhEFXrWFsYxx343mjx.png'),
        (30,"USA Network", 'https://image.tmdb.org/t/p/original/g1e0H0Ka97IG5SyInMXdJkHGKiH.png'),
        (158,"VH1", 'https://image.tmdb.org/t/p/original/w9oUxxUiXTC1O1MzJSvsMjQbgft.png'),
        (202,"WGN America", 'https://image.tmdb.org/t/p/original/kCNFRiqVRMgNWKSWu0LzAIpy9um.png'),
        (247,"YouTube", 'https://image.tmdb.org/t/p/original/9Ga8A5QegQmiSVHp4hyusfMfpVk.png'),
        (1436,"YouTube Premium", 'https://image.tmdb.org/t/p/original/3p05CgodUb9gPayuliuhawNj1Wo.png'),
        ]

        for i in networks:
            #self.list.append({'name': i[0], 'url': self.tvmaze_link + i[1], 'image': i[2], 'action': 'tvshows'})
            self.list.append({'name': i[1], 'url': self.tmdb_networks_link % i[0], 'image': i[2], 'action': 'tvshows'})
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
            ('Hindi', 'hi'),
            ('Hungarian', 'hu'),
            ('Icelandic', 'is'),
            ('Italian', 'it'),
            ('Japanese', 'ja'),
            ('Korean', 'ko'),
            ('Norwegian', 'no'),
            ('Persian', 'fa'),
            ('Polish', 'pl'),
            ('Portuguese', 'pt'),
            ('Punjabi', 'pa'),
            ('Romanian', 'ro'),
            ('Russian', 'ru'),
            ('Serbian', 'sr'),
            ('Spanish', 'es'),
            ('Swedish', 'sv'),
            ('Turkish', 'tr'),
            ('Ukrainian', 'uk')
        ]


        for i in languages: 
            self.list.append({'name': str(i[0]), 'url': self.language_link % i[1], 'image': 'international2.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def certifications(self):
        certificates = ['TV-G', 'TV-PG', 'TV-14', 'TV-MA']

        for i in certificates:
            self.list.append({'name': str(i), 'url': self.certification_link % str(i), 'image': 'certificates.png', 'action': 'tvshows'})
        self.addDirectory(self.list)
        return self.list

    def persons(self, url):
        c.log('[CM DEBUG @ 542 in tvshows.py] url = ' + str(url))
        if url == None:
            #self.list = cache.get(self.tmdb_person_list, 24, self.personlist_link)
            self.tmdb_person_list(self.personlist_link)
            
        else:
            #self.list = cache.get(self.tmdb_person_list, 1, url)
            self.tmdb_person_list (url)

        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'tvshows'})
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
            if self.imdb_user == '': raise Exception()
            userlists += cache.get(self.imdb_user_list, 0, self.imdblists_link)
        except:
            pass
        try:
            self.list = []
            if trakt.getTraktCredentialsInfo() == False: raise Exception()
            try:
                if activity > cache.timeout(self.trakt_user_list, self.traktlikedlists_link, self.trakt_user): raise Exception()
                userlists += cache.get(self.trakt_user_list, 720, self.traktlikedlists_link, self.trakt_user)
            except:
                userlists += cache.get(self.trakt_user_list, 0, self.traktlikedlists_link, self.trakt_user)
        except:
            pass

        self.list = userlists

        for i in range(0, len(self.list)): 
            self.list[i].update({'image': 'userlists.png', 'action': 'tvshows'})

        self.addDirectory(self.list)
        return self.list

    def trakt_list(self, url, user):
        try:
            dupes = []

            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib.parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib.parse.urlparse(url).query, '') + '?' + q
            result = trakt.getTraktAsJson(u)

            items = []
            for i in result:
                try: items.append(i['show'])
                except: pass
            if len(items) == 0:
                items = result
        except:
            return

        try:
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            if not int(q['limit']) == len(items): raise Exception()
            q.update({'page': str(int(q['page']) + 1)})
            q = (urllib.parse.urlencode(q)).replace('%2C', ',')
            next = url.replace('?' + urllib.parse.urlparse(url).query, '') + '?' + q
            next = str(next)
        except:
            next = ''

        def items_list(item):
            try:
                title = item['title']
                title = re.sub('\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)

                year = item['year']
                year = re.sub('[^0-9]', '', str(year))

                imdb = item['ids']['imdb']
                if not imdb: imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                tmdb = item['ids']['tmdb']
                if not tmdb: tmdb = '0'
                tvdb = item['ids']['tvdb']
                if not tvdb: tvdb = '0'

                year = str(year)
                tmdb = str(tmdb)
                tvdb = str(tvdb)

                if tmdb in dupes: raise Exception()
                dupes.append(tmdb)

                try: premiered = item['first_aired']
                except: premiered = '0'
                try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                except: premiered = '0'

                try: studio = item['network']
                except: studio = '0'
                if studio == None: studio = '0'

                try: genre = item['genres']
                except: genre = '0'

                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)

                try: duration = str(item['runtime'])
                except: duration = '0'
                if duration == None: duration = '0'

                try: rating = str(item['rating'])
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'

                try: votes = str(item['votes'])
                except: votes = '0'
                try: votes = str(format(int(votes), ',d'))
                except: pass
                if votes == None: votes = '0'

                try: mpaa = item['certification']
                except: mpaa = '0'
                if mpaa == None: mpaa = '0'

                try: plot = item['overview']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = client.replaceHTMLCodes(plot)

                country = item.get('country')
                if not country: country = '0'
                else: country = country.upper()

                status = item.get('status')
                if not status: status = '0'

                trailer = item.get('trailer')
                if not trailer: trailer = '0'

                if not tmdb == '0':
                    url = self.tmdb_info_tvshow_link % tmdb
                    result = self.session.get(url, timeout=10).json()
                    try:
                        poster = self.tmdb_img_prelink.format('original', result['poster_path'])
                        fanart = self.tmdb_img_prelink.format('original', result['backdrop_path'])
                    except:
                        poster = '0'; fanart = '0'
                        pass


                self.list.append({'title': title, 'originaltitle': title, 'poster': poster,
                                    'fanart': fanart, 'year': year, 'premiered': premiered, 
                                    'studio': studio, 'genre': genre, 'duration': duration, 
                                    'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 
                                    'country': country, 'status': status, 'imdb': imdb, 'tvdb': tvdb, 
                                    'tmdb': tmdb, 'trailer': trailer, 'next': next})
            except:
                c_utils.log('Exception in tvshows.trakt_list().items_list')
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            return self.list
        except:
            return

    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
        except:
            pass

        for item in items:
            try:
                try: name = item['list']['name']
                except: name = item['name']
                name = client.replaceHTMLCodes(name)

                try: url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
                except: url = ('me', item['ids']['slug'])
                url = self.traktlist_link % url
                url = str(url)
 
                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list

    def disabled_imdb_list(self, url):
        try:
            dupes = []

            for i in re.findall('date\[(\d+)\]', url):
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
            result = control.six_decode(result)
            result = result.replace('\n', ' ')

            items = client.parseDOM(result, 'div', attrs={'class': 'lister-item .+?'})
            items += client.parseDOM(result, 'div', attrs={'class': 'list_item.+?'})
        except:
            return

        try:
            result = result.replace(r'class="lister-page-next', ' class="crew-next')
            next = client.parseDOM(result, 'a', ret='href', attrs = {'class': r'crew-next .+?'})

            if len(next) == 0:
                next = client.parseDOM(result, 'div', attrs = {'class': u'pagination'})[0]
                next = zip(client.parseDOM(next, 'a', ret='href'), client.parseDOM(next, 'a'))
                next = [i[0] for i in next if 'Next' in i[1]]

            next = url.replace(urllib.parse.urlparse(url).query, urllib.parse.urlparse(next[0]).query)
            next = client.replaceHTMLCodes(next)
            next = str(next)
        except:
            next = ''

        for item in items:
            try:
                title = client.parseDOM(item, 'a')[1]
                title = client.replaceHTMLCodes(title)
                title = str(title)

                year = client.parseDOM(item, 'span', attrs={'class': 'lister-item-year.+?'})
                year += client.parseDOM(item, 'span', attrs={'class': 'year_type'})
                year = re.findall(r'(\d{4})', year[0])[0]
                year = str(year)

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = client.parseDOM(item, 'a', ret='href')[0]
                imdb = re.findall('(tt\d*)', imdb)[0]
                imdb = str(imdb)

                if imdb in dupes: raise Exception()
                dupes.append(imdb)

                try:
                    poster = client.parseDOM(item, 'img', ret='loadlate')[0]
                except:
                    poster = '0'
                if '/nopicture/' in poster or '/sash/' in poster:
                    poster = '0'
                   
                poster = re.sub('(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', poster)
                poster = client.replaceHTMLCodes(poster)
                poster = str(poster)

                rating = votes = '0'
                try:
                    rating = client.parseDOM(item, 'span', attrs = {'class': 'rating-rating'})[0]
                    rating = client.parseDOM(rating, 'span', attrs = {'class': 'value'})[0]
                except:
                    pass
                if rating == '0':
                    try:
                        rating = client.parseDOM(item, 'div', ret='data-value', attrs = {'class': '.*?imdb-rating'})[0]
                    except:
                        pass
                if rating == '0':
                    try:
                        rating = client.parseDOM(item, 'span', attrs = {'class': '.*?_rating'})[0]
                    except:
                        pass
                if rating == '0':
                    try:
                        rating = client.parseDOM(item, 'div', attrs = {'class': 'col-imdb-rating'})[0]
                        rating = client.parseDOM(rating, 'strong', ret='title')[0]
                        rating = re.findall(r'(.+?) base', rating)[0]
                    except:
                        pass
                if rating == '' or rating == '-':
                    rating = '0'
                try:
                    votes = client.parseDOM(item, 'div', ret='title', attrs = {'class': '.*?rating-list'})[0]
                    votes = re.findall(r'\((.+?) vote(?:s|)\)', votes)[0]
                except:
                    pass
                if votes == '0':
                    try:
                        votes = client.parseDOM(item, 'span', ret='data-value')[0]
                    except:
                        pass
                if votes == '0':
                    try:
                        votes = client.parseDOM(item, 'div', attrs = {'class': 'col-imdb-rating'})[0]
                        votes = client.parseDOM(votes, 'strong', ret='title')[0]
                        votes = re.findall(r'base on (.+?) votes', votes)[0]
                    except:
                        pass
                if votes == '':
                    votes = '0'

                plot = '0'
                try: plot = client.parseDOM(item, 'p', attrs = {'class': 'text-muted'})[0]
                except: pass
                if plot == '0':
                    try: plot = client.parseDOM(item, 'div', attrs = {'class': 'item_description'})[0]
                    except: pass
                if plot == '0':
                    try: plot = client.parseDOM(item, 'p')[1]
                    except: pass
                if plot == '': plot = '0'
                if plot and not plot == '0':
                    plot = plot.rsplit('<span>', 1)[0].strip()
                    plot = re.sub(r'<.+?>|</.+?>', '', plot)
                    plot = client.replaceHTMLCodes(plot)
                    plot = six.ensure_str(plot)

                try:
                    cast = re.findall('Stars(?:s|):(.+?)(?:\||</div>)', item)[0]
                    cast = client.replaceHTMLCodes(cast)
                    cast = six.ensure_str(cast, errors='ignore')
                    cast = client.parseDOM(cast, 'a')
                    if not cast: cast = '0'
                except:
                    cast = '0'

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 
                                  'rating': rating, 'votes': votes, 'plot': plot,
                                  'cast': cast, 'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 
                                  'poster': poster, 'next': next})
            except:
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
                url = self.person_show_link % id
                c.log('[CM DEBUG @ 924 in tvshows.py] url = ' + str(url))
                self.list.append({'name': name, 'url': url, 'image': image})
            except:
                pass
        
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
        
        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total: raise Exception()
            if 'page=' not in url: raise Exception()
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except:
            next = ''

        for item in items:

            try:
                tmdb = str(item['id'])
                title = item['name']
                originaltitle = item.get('original_name', '') or title

                try: rating = str(item['vote_average'])
                except: rating = ''
                if not rating: rating = '0'

                try: votes = str(item['vote_count'])
                except: votes = ''
                if not votes: votes = '0'

                try: premiered = item['first_air_date']
                except: premiered = ''
                if not premiered : premiered = '0'

                unaired = ''
                if not premiered or premiered == '0': 
                    pass
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true': raise Exception('unaired == false')

                try: year = re.findall('(\d{4})', premiered)[0]
                except: year = ''
                if not year : year = '0'

                try: plot = item['overview']
                except: plot = ''
                if not plot: plot = '0'

                try: poster_path = item['poster_path']
                except: poster_path = ''
                if poster_path: poster = self.tmdb_img_link % ('original', poster_path)
                else: poster = '0'

                backdrop_path = item['backdrop_path'] if 'backdrop_path' in item else ''
                if backdrop_path: 
                    fanart = self.tmdb_img_link % ('original', 'backdrop_path')

                self.list.append({'title': title, 'originaltitle': originaltitle, 'premiered': premiered, 
                                    'year': year, 'rating': rating, 'votes': votes, 'plot': plot, 
                                    'imdb': '0', 'tmdb': tmdb, 'tvdb': '0', 'poster': poster, 'fanart': fanart, 'next': next})
            except Exception as e:
                c.log(f'[CM DEBUG @ 1082 in tvshows.py] Exception raised: e = {e}')
                pass

        return self.list

    def disabled_imdb_person_list(self, url):
        try:
            result = client.request(url)
            items = client.parseDOM(result, 'div', attrs={'class': '.+? mode-detail'})
        except:
            return

        for item in items:
            try:
                name = client.parseDOM(item, 'img', ret='alt')[0]
                name = client.replaceHTMLCodes(name)
                name = str(name)

                url = client.parseDOM(item, 'a', ret='href')[0]
                url = re.findall('(nm\d*)', url, re.I)[0]
                url = self.person_link % url
                url = client.replaceHTMLCodes(url)
                url = six.ensure_str(url)
                #url = str(url)

                image = client.parseDOM(item, 'img', ret='src')[0]
                # if not ('._SX' in image or '._SY' in image): raise Exception()
                # image = re.sub('(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', image)
                image = client.replaceHTMLCodes(image)
                image = str(image)

                self.list.append({'name': name, 'url': url, 'image': image})
            except:
                pass

        return self.list

    def disabled_imdb_user_list(self, url):
        try:
            result = client.request(url)
            items = client.parseDOM(result, 'li', attrs={'class': 'ipl-zebra-list__item user-list'})
        except:
            pass

        for item in items:
            try:
                name = client.parseDOM(item, 'a')[0]
                name = client.replaceHTMLCodes(name)
                name = str(name)

                url = client.parseDOM(item, 'a', ret='href')[0]
                url = url = url.split('/list/', 1)[-1].strip('/')
                url = self.imdblist_link % url
                url = client.replaceHTMLCodes(url)
                url = six.ensure_str(url)
                #url = str(url)

                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                pass

        self.list = sorted(self.list, key=lambda k: utils.title_key(k['name']))
        return self.list

    def tvmaze_list(self, url):
        try:
            result = client.request(url)
            result = client.parseDOM(result, 'section', attrs={'id': 'this-seasons-shows'})

            items = client.parseDOM(result, 'div', attrs={'class': 'content auto cell'})
            items = [client.parseDOM(i, 'a', ret='href') for i in items]
            items = [i[0] for i in items if len(i) > 0]
            items = [re.findall('/(\d+)/', i) for i in items]
            items = [i[0] for i in items if len(i) > 0]
            
            #items = items[:50]

            next = ''; last = []; nextp = []
            page = int(str(url.split('&page=', 1)[1]))
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
            last = client.parseDOM(result, 'li', attrs = {'class': 'last disabled'})
            nextp = client.parseDOM(result, 'li', attrs = {'class': 'next'})
            if last != [] or nextp == []: next = ''
        except:
            return

        def items_list(i):
            try:
                url = self.tvmaze_info_link % i

                item = self.session.get(url, timeout=16).json()

                #item = client.request(url)
                #item = json.loads(item)

                title = item['name']
                title = re.sub('\s(|[(])(UK|US|AU|\d{4})(|[)])$', '', title)
                title = client.replaceHTMLCodes(title)
                title = str(title)
                premiered = item['premiered']
                try: premiered = re.findall('(\d{4}-\d{2}-\d{2})', premiered)[0]
                except: premiered = '0'
                premiered = six.ensure_str(premiered)

                year = item['premiered']
                try: year = re.findall('(\d{4})', year)[0]
                except: year = '0'
                year = str(year)

                #if int(year) > int(self.datetime.strftime('%Y')): raise Exception()

                imdb = item['externals']['imdb']
                if imdb == None or imdb == '': imdb = '0'
                else: imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                imdb = str(imdb)

                tvdb = item['externals']['thetvdb']
                if tvdb == None or tvdb == '': tvdb = '0'
                else: tvdb = re.sub('[^0-9]', '', str(tvdb))
                tvdb = str(tvdb)

                try: poster = item['image']['original']
                except: poster = '0'
                if  not poster: poster = '0'
                poster = str(poster)

                try: studio = item['network']['name']
                except: studio = '0'
                if studio == None: studio = '0'
                studio = six.ensure_str(studio)

                try: genre = item['genres']
                except: genre = '0'
                genre = [i.title() for i in genre]
                if genre == []: genre = '0'
                genre = ' / '.join(genre)
                genre = str(genre)

                try: duration = item['runtime']
                except: duration = '0'
                if duration == None: duration = '0'
                duration = str(duration)

                try: rating = item['rating']['average']
                except: rating = '0'
                if rating == None or rating == '0.0': rating = '0'
                rating = str(rating)

                try: plot = item['summary']
                except: plot = '0'
                if plot == None: plot = '0'
                plot = re.sub('<.+?>|</.+?>|\n', '', plot)
                plot = client.replaceHTMLCodes(plot)
                plot = str(plot)

                try: content = item['type'].lower()
                except: content = '0'
                if content == None or content == '': content = '0'
                content = str(content)

                self.list.append({'title': title, 'originaltitle': title, 'year': year, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'plot': plot,
                                  'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0', 'poster': poster, 'content': content, 'next': next})
            except:
                pass

        try:
            threads = []
            for i in items: threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]

            #filter = [i for i in self.list if i['content'] == 'scripted']
            #filter += [i for i in self.list if not i['content'] == 'scripted']
            #self.list = filter

            return self.list
        except:
            return

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
                    title = item.get('name') or ''
                    if not title:
                        raise Exception()
                    originaltitle = item.get('original_name') or title

                    rating = str(item.get('vote_average') or '0')
                    votes = str(item.get('vote_count') or '0')

                    premiered = item.get('first_air_date') or '0'
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
                            'tvdb': '0', 'fanart': fanart, 'poster': poster, 'next': next_url})
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


    def worker(self, level=1):
        self.meta = []
        total = len(self.list)


        for i in range(0, total): self.list[i].update({'metacache': False})

        self.list = metacache.fetch(self.list, self.lang, self.user)

        for r in range(0, total, 40):
            threads = []
            for i in range(r, r+40):
                if i < total: threads.append(workers.Thread(self.super_info, i))

        [i.start() for i in threads]
        [i.join() for i in threads]

        if self.meta: metacache.insert(self.meta)

        #self.list = [i for i in self.list if not i['imdb'] == '0']

        #if self.fanart_tv_user == '':
            #for i in self.list:
                #i.update({'clearlogo': '0', 'clearart': '0'})

    def super_info(self, i):
        try:
            if self.list[i]['metacache'] == True: return

            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            tvdb = self.list[i]['tvdb'] if 'tvdb' in self.list[i] else '0'

            list_title = self.list[i]['title']

            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_imdb % imdb
                    result = self.session.get(url, timeout=10).json()

                    tv_results = result['tv_results'][0]
                    tmdb = tv_results['id']
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            if tmdb == '0':
                try:
                    url = self.search_link % (urllib.parse.quote(self.list[i]['title'])) + '&first_air_date_year=' + self.list[i]['year']
                    result = client.request(url)
                    result = json.loads(result)
                    results = result['results']
                    show = [r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(list_title)][0]# and re.findall('(\d{4})', r.get('first_air_date'))[0] == self.list[i]['year']][0]
                    tmdb = show.get('id')
                    if not tmdb: tmdb = '0'
                    else: tmdb = str(tmdb)
                except:
                    pass

            if tmdb == '0': raise Exception() 
                

            en_url = self.tmdb_api_link % (tmdb)
            foreign_url = en_url + ',translations'

            url = en_url if self.lang == 'en' else foreign_url
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            item = r.json()

            if item == None: raise Exception()

            if imdb == '0':
                try:
                    imdb = item['external_ids']['imdb_id']
                    if not imdb: imdb = '0'
                except:
                    imdb = '0'

            if tvdb == '0':
                try:
                    tvdb = item['external_ids']['tvdb_id']
                    if not tvdb: tvdb = '0'
                    else: tvdb = str(tvdb)
                except:
                    tvdb = '0'

            original_language = item.get('original_language', '')

            if self.lang == 'en':
                en_trans_item = None
            else:
                try:
                    translations = item['translations']['translations']
                    en_trans_item = [x['data'] for x in translations if x['iso_639_1'] == 'en'][0]
                except:
                    en_trans_item = {}

            name = item.get('name', '')
            original_name = item.get('original_name', '')
            en_trans_name = en_trans_item.get('name', '') if not self.lang == 'en' else None

            if self.lang == 'en':
                title = label = name
            else:
                title = en_trans_name or original_name
                if original_language == self.lang:
                    label = name
                else:
                    label = en_trans_name or name
            if not title: title = list_title
            if not label: label = list_title

            plot = item.get('overview', '')
            if not plot: plot = self.list[i]['plot']

            tagline = item.get('tagline', '')
            if not tagline : tagline = '0'

            if not self.lang == 'en':
                if plot == '0':
                    en_plot = en_trans_item.get('overview', '')
                    if en_plot: plot = en_plot

                if tagline == '0':
                    en_tagline = en_trans_item.get('tagline', '')
                    if en_tagline: tagline = en_tagline

            premiered = item.get('first_air_date', '')
            if not premiered : premiered = '0'

            try: year = re.findall('(\d{4})', premiered)[0]
            except: year = ''
            if not year : year = '0'

            status = item.get('status', '')
            if not status : status = '0'

            try: studio = item['networks'][0]['name']
            except: studio = ''
            if not studio: studio = '0'

            try:
                genres = item['genres']
                genres = [d['name'] for d in genres]
                genre = ' / '.join(genres)
            except:
                genre = ''
            if not genre: genre = '0'

            try:
                countries = item['production_countries']
                countries = [c['name'] for c in countries]
                country = ' / '.join(countries)
            except:
                country = ''
            if not country: country = '0'

            try:
                duration = item['episode_run_time'][0]
                duration = str(duration)
            except: duration = ''
            if not duration: duration = '0'

            try:
                m = item['content_ratings']['results']
                mpaa = [d['rating'] for d in m if d['iso_3166_1'] == 'US'][0]
            except: mpaa = ''
            if not mpaa: mpaa = '0'

            try: status = item['status']
            except: status = ''
            if not status: status = '0'

            try: plot = item['overview']
            except: plot = ''
            if not plot: plot = self.list[i]['plot']
            else: plot = client.replaceHTMLCodes(str(plot))

            try: tagline = item['tagline']
            except: tagline = ''
            if not tagline: tagline = '0'
            else: tagline = client.replaceHTMLCodes(str(tagline))

            if not self.lang == 'en':
                try:
                    translations = item.get('translations', {})
                    translations = translations.get('translations', [])
                    trans_item = [x['data'] for x in translations if x.get('iso_639_1') == 'en'][0]

                    en_title = trans_item.get('name', '')
                    if en_title and not original_language == 'en': title = label = str(en_title)

                    if plot == '0':
                        en_plot = trans_item.get('overview', '')
                        if en_plot: plot = client.replaceHTMLCodes(str(en_plot))

                    if tagline == '0':
                        en_tagline = trans_item.get('tagline', '')
                        if en_tagline: tagline = client.replaceHTMLCodes(str(en_tagline))
                except:
                    pass

            castwiththumb = []
            try:
                c = item['aggregate_credits']['cast'][:30]
                for person in c:
                    _icon = person['profile_path']
                    icon = self.tmdb_img_link % ('185', _icon) if _icon else ''
                    castwiththumb.append({'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
            except:
                pass
            if not castwiththumb: castwiththumb = '0'

            poster1 = self.list[i].get('poster', '0') or '0'

            poster_path = item.get('poster_path')
            if poster_path:
                poster2 = self.tmdb_img_link % ('500', poster_path)
                poster2 = str(poster2)
            else:
                poster2 = None

            fanart_path = item.get('backdrop_path')
            if fanart_path:
                fanart1 = self.tmdb_img_link % ('1280', fanart_path)
                fanart1 = str(fanart1)
            else:
                fanart1 = '0'

            poster3 = fanart2 = None
            banner = clearlogo = clearart = landscape = '0'
            if self.hq_artwork == 'true' and not tvdb == '0':
                try:
                    r2 = self.session.get(self.fanart_tv_art_link % tvdb, headers=self.fanart_tv_headers, timeout=10)
                    r2.raise_for_status()
                    r2.encoding = 'utf-8'
                    art = r2.json()
                except:
                    pass

                try:
                    _poster3 = art['tvposter']
                    _poster3 = [x for x in _poster3 if x.get('lang') == self.lang][::-1] + [x for x in _poster3 if x.get('lang') == 'en'][::-1] + [x for x in _poster3 if x.get('lang') in ['00', '']][::-1]
                    _poster3 = _poster3[0]['url']
                    if _poster3: poster3 = str(_poster3)
                except:
                    pass

                try:
                    _fanart2 = art['showbackground']
                    _fanart2 = [x for x in _fanart2 if x.get('lang') == self.lang][::-1] + [x for x in _fanart2 if x.get('lang') == 'en'][::-1] + [x for x in _fanart2 if x.get('lang') in ['00', '']][::-1]
                    _fanart2 = _fanart2[0]['url']
                    #if _fanart2: fanart2 = str(_fanart2)
                    if _fanart2: fanart2 = six.ensure_str(_fanart2)
                except:
                    pass

                try:
                    _banner = art['tvbanner']
                    _banner = [x for x in _banner if x.get('lang') == self.lang][::-1] + [x for x in _banner if x.get('lang') == 'en'][::-1] + [x for x in _banner if x.get('lang') in ['00', '']][::-1]
                    _banner = _banner[0]['url']
                    #if _banner: banner = str(_banner)
                    if _banner: banner = six.ensure_str(_banner)
                except:
                    pass

                try:
                    if 'hdtvlogo' in art: _clearlogo = art['hdtvlogo']
                    else: _clearlogo = art['clearlogo']
                    _clearlogo = [x for x in _clearlogo if x.get('lang') == self.lang][::-1] + [x for x in _clearlogo if x.get('lang') == 'en'][::-1] + [x for x in _clearlogo if x.get('lang') in ['00', '']][::-1]
                    _clearlogo = _clearlogo[0]['url']
                    #if _clearlogo: clearlogo = str(_clearlogo)
                    if _clearlogo: clearlogo = six.ensure_str(_clearlogo)
                except:
                    pass

                try:
                    if 'hdclearart' in art: _clearart = art['hdclearart']
                    else: _clearart = art['clearart']
                    _clearart = [x for x in _clearart if x.get('lang') == self.lang][::-1] + [x for x in _clearart if x.get('lang') == 'en'][::-1] + [x for x in _clearart if x.get('lang') in ['00', '']][::-1]
                    _clearart = _clearart[0]['url']
                    #if _clearart: clearart = str(_clearart)
                    if _clearart: clearart = six.ensure_str(_clearart)
                except:
                    pass

                try:
                    if 'tvthumb' in art: _landscape = art['tvthumb']
                    else: _landscape = art['showbackground']
                    _landscape = [x for x in _landscape if x.get('lang') == self.lang][::-1] + [x for x in _landscape if x.get('lang') == 'en'][::-1] + [x for x in _landscape if x.get('lang') in ['00', '']][::-1]
                    _landscape = _landscape[0]['url']
                    #if _landscape: landscape = str(_landscape)
                    if _landscape: landscape = six.ensure_str(_landscape)
                except:
                    pass

            poster = poster3 or poster2 or poster1
            fanart = fanart2 or fanart1

            item = {'title': title, 'originaltitle': title, 'label': label, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'banner': banner,
                    'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'premiered': premiered, 'studio': studio, 'genre': genre, 'duration': duration, 'mpaa': mpaa,
                    'castwiththumb': castwiththumb, 'plot': plot, 'status': status, 'tagline': tagline}

            item = dict((k,v) for k, v in item.items() if not v == '0')

            self.list[i].update(item)

            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'lang': self.lang, 'user': self.user, 'item': item}
            self.meta.append(meta)
        except:
            pass

    def tvshowDirectory(self, items):
        if items == None or len(items) == 0: control.idle()# ; sys.exit()

        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])

        traktIndicatorInfo = trakt.getTraktIndicatorsInfo()

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()

        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')

        traktCredentials = trakt.getTraktCredentialsInfo()

        indicators = playcount.getTVShowIndicators(refresh=True) if action == 'tvshows' else playcount.getTVShowIndicators() #fixme

        flatten = control.setting('flatten.tvshows') or 'false'

        #cm - menus
        findSimilar = control.lang(32100)
        playRandom = control.lang(32535)
        queueMenu = control.lang(32065)
        watchedMenu = control.lang(32068) if traktIndicatorInfo == True else control.lang(32066)
        unwatchedMenu = control.lang(32069) if traktIndicatorInfo == True else control.lang(32067)
        traktManagerMenu = control.lang(32515)
        addToLibrary = control.lang(32551)
        infoMenu = control.lang(32101)
        nextMenu = control.lang(32053)

        colorvalues = control.setting('unaired.identify')

        for i in items:
            try:
                label = i['label'] if 'label' in i and not i['label'] == '0' else i['title']
                status = i.get('status', '')
                try:
                    premiered = i['premiered']
                    if (premiered == '0' and status in ['Upcoming', 'In Production', 'Planned']) or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):

                        #changed by oh -  27-4-2023
                        colorlist = [32589, 32590, 32591, 32592, 32593, 32594, 32595, 32596, 32597, 32598]
                        colornr = colorlist[int(control.setting('unaired.identify'))]
                        unairedcolor = re.sub("\][\w\s]*\[", "][I]%s[/I][", control.lang(int(colornr)))
                        label = unairedcolor % label

                        if unairedcolor == '':
                            unairedcolor = '[COLOR red][I]%s[/I][/COLOR]'
                except: 
                    pass

                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                banner1 = i.get('banner', '')
                banner = banner1 or fanart or addonBanner
                if 'landscape' in i and not i['landscape'] == '0':
                    landscape = i['landscape']
                else:
                    landscape = fanart

                systitle = sysname = urllib.parse.quote_plus(i['title'])
                sysimage = urllib.parse.quote_plus(poster)

                seasons_meta = {'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': i.get('clearlogo', '0'), 'clearart': i.get('clearart', '0'), 'landscape': landscape}

                sysmeta = urllib.parse.quote_plus(json.dumps(seasons_meta))

                imdb, tvdb, tmdb, year = i.get('imdb', ''), i.get('tvdb', ''), i.get('tmdb', ''), i.get('year', '')

                meta = dict((k,v) for k, v in i.items() if not v == '0')
                meta.update({'code': tmdb, 'imdbnumber': imdb})

                meta.update({'mediatype': 'tvshow'})
                meta.update({'tvshowtitle': i['title']})

                trailer_url = urllib.parse.quote(i['trailer']) if 'trailer' in i else '0'
                search_name = systitle

                if trailer_url == '0':
                    meta.update({'trailer': '%s?action=trailer&name=%s&imdb=%s&tmdb=%s' % (sysaddon, search_name, imdb, tmdb)})
                else:
                    meta.update({'trailer': '%s?action=trailer&name=%s&url=%s&imdb=%s&tmdb=%s' % (sysaddon, search_name, trailer_url, imdb, tmdb)})

                if not 'duration' in meta: meta.update({'duration': '45'})
                elif meta['duration'] == '0': meta.update({'duration': '45'})
                try: meta.update({'duration': str(int(meta['duration']) * 60)})
                except: pass
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass
                if 'castwiththumb' in i and not i['castwiththumb'] == '0': meta.pop('cast', '0')

                try:
                    overlay = int(playcount.getTVShowOverlay(indicators, tmdb))
                    if overlay == 7: meta.update({'playcount': 1, 'overlay': 7})
                    else: meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass

                cm = []

                cm.append((findSimilar, 'Container.Update(%s?action=tvshows&url=%s)' % (sysaddon, urllib.parse.quote_plus(self.related_link % tmdb))))

                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=season&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (
                            sysaddon, urllib.parse.quote_plus(systitle), urllib.parse.quote_plus(year), urllib.parse.quote_plus(imdb), urllib.parse.quote_plus(tmdb)))
                            )

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                cm.append((watchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&query=7)' % (sysaddon, systitle, imdb, tmdb)))

                cm.append((unwatchedMenu, 'RunPlugin(%s?action=tvPlaycount&name=%s&imdb=%s&tmdb=%s&query=6)' % (sysaddon, systitle, imdb, tmdb)))

                if traktCredentials == True:
                    cm.append((traktManagerMenu, 'RunPlugin(%s?action=traktManager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, sysname, tmdb)))

                cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowToLibrary&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systitle, year, imdb, tmdb)))

                try: item = control.item(label=label, offscreen=True)
                except: item = control.item(label=label)


                art = {}

                art.update({'icon': poster, 'thumb': poster, 'poster': poster, 'tvshow.poster': poster, 'season.poster': poster, 'banner': banner, 'landscape': landscape})

                if settingFanart == 'true':
                    art.update({'fanart': fanart})
                else:
                    art.update({'fanart': addonFanart})

                if 'clearlogo' in i and not i['clearlogo'] == '0':
                    art.update({'clearlogo': i['clearlogo']})

                if 'clearart' in i and not i['clearart'] == '0':
                    art.update({'clearart': i['clearart']})

                castwiththumb = i.get('castwiththumb')
                if castwiththumb and not castwiththumb == '0':
                   item.setCast(castwiththumb)

                item.setProperty('imdb_id', imdb)
                item.setProperty('tmdb_id', tmdb)
                try: item.setUniqueIDs({'imdb': imdb, 'tmdb': tmdb})
                except:
                    pass

                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setInfo(type='Video', infoLabels=control.metadataClean(meta))

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                if flatten == 'true':
                    url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&fanart=%s&duration=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, fanart, i['duration'], sysmeta)
                else:
                    url = '%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                log_utils.log('exception in tvshows.adddirectory()')
                pass

        try:
            url = items[0]['next']
            if url == '': raise Exception()

            icon = control.addonNext()
            url = '%s?action=tvshowPage&url=%s' % (sysaddon, urllib.parse.quote_plus(url))

            try: item = control.item(label=nextMenu, offscreen=True)
            except: item = control.item(label=nextMenu)

            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': addonFanart})

            control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
        except:
            pass

        control.content(syshandle, 'tvshows')
        control.directory(syshandle, cacheToDisc=True)

    def addDirectory(self, items, queue=False):
        if items == None or len(items) == 0: return #control.idle() ; sys.exit()

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

                if i['image'].startswith('http'): thumb = i['image']
                elif not artPath == None: thumb = os.path.join(artPath, i['image'])
                else: thumb = addonThumb

                url = '%s?action=%s' % (sysaddon, i['action'])

                try: url += '&url=%s' % urllib.parse.quote_plus(i['url'])
                except: pass

                cm = []
                cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=show&url=%s)' % (sysaddon, urllib.parse.quote_plus(i['url']))))

                if queue == True:
                    cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                try: cm.append((addToLibrary, 'RunPlugin(%s?action=tvshowsToLibrary&url=%s)' % (sysaddon, urllib.parse.quote_plus(i['context']))))
                except: pass

                try: item = control.item(label=name, offscreen=True)
                except: item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addonFanart})
                item.setInfo(type='video', infoLabels={'plot': plot})

                item.addContextMenuItems(cm)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                pass

        control.content(syshandle, '')
        control.directory(syshandle, cacheToDisc=True)