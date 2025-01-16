# -*- coding: utf-8 -*-

import re
import os
import sys
import datetime

import simplejson as json
import six
from six.moves import range, urllib_parse, zip

try:
    #from infotagger.listitem import ListItemInfoTag
    from resources.lib.modules.listitem import ListItemInfoTag
except:
    pass

from resources.lib.indexers import navigator

from resources.lib.modules import bookmarks
from resources.lib.modules import cache
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import control
from resources.lib.modules import favorites
from resources.lib.modules import metacache
from resources.lib.modules import playcount
from resources.lib.modules import tmdb_utils
from resources.lib.modules import trakt
from resources.lib.modules import views
from resources.lib.modules import workers

#from resources.lib.modules import log_utils

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()
action = params.get('action')
control.moderator()
kodi_version = control.getKodiVersion()


class movies:
    def __init__(self):
        self.list = []
        self.datetime = datetime.datetime.utcnow()
        self.systime = (self.datetime).strftime('%Y%m%d%H%M%S%f')
        self.year_date = (self.datetime - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        self.month_date = (self.datetime - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        self.today_date = (self.datetime).strftime('%Y-%m-%d')
        self.addon_caching = control.setting('addon.caching') or 'true'
        self.trakt_user = control.setting('trakt.user').strip()
        self.imdb_user = control.setting('imdb.user').replace('ur', '')
        self.tmdb_key = control.setting('tmdb.api')
        if self.tmdb_key == '' or self.tmdb_key == None:
            self.tmdb_key = '3d000491a0f37d4962d02bdb062af037'
        self.fanart_tv_headers = {'api-key': 'ad7eccc1dd67f889f7f5c2e9ebb810ae'}
        self.fanart_tv_user = control.setting('fanart.api')
        if not self.fanart_tv_user == '' or self.fanart_tv_user == None:
            self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})
        self.shownoyear = control.setting('show.noyear') or 'false'
        self.unairedcolor = control.setting('unaired.color')
        if self.unairedcolor == '':
            self.unairedcolor = 'darkred'
        self.lang = control.apiLanguage()['tmdb'] or 'en'
        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.settingFanart = control.setting('fanart') or 'false'
        self.hq_artwork = control.setting('hq.artwork') or 'false'
        self.studio_artwork = control.setting('studio.artwork') or 'false'
        self.trakt_link = 'https://api.trakt.tv'
        self.imdb_link = 'https://www.imdb.com'
        self.tmdb_link = 'https://api.themoviedb.org'
        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/movies/%s'
        self.fanart_tv_level_link = 'http://webservice.fanart.tv/v3/level'
        self.search_movies_source = control.setting('search.movies.source') or '0'
        self.search_people_source = control.setting('search.people.source') or '0'
        self.search_keywords_source = control.setting('search.keywords.source') or '0'
        self.info_movies_source = control.setting('info.movies.source') or '0'
        self.info_art_source = control.setting('info.art.source') or '0'
        self.original_artwork = control.setting('original.artwork') or 'false'
        if self.original_artwork == 'true':
            self.tmdb_image_link = 'https://image.tmdb.org/t/p/original'
        else:
            self.tmdb_image_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.tmdb_info_link = self.tmdb_link + '/3/movie/%s?api_key=%s&language=en-US&append_to_response=credits,releases' % ('%s', self.tmdb_key)

        self.tmdb_search_link = self.tmdb_link + '/3/search/movie?api_key=%s&query=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, '%s')
        self.tmdb_popular_link = self.tmdb_link + '/3/movie/popular?api_key=%s&language=en-US&page=1' % self.tmdb_key
        self.tmdb_now_playing_link = self.tmdb_link + '/3/movie/now_playing?api_key=%s&language=en-US&page=1' % self.tmdb_key
        self.tmdb_toprated_link = self.tmdb_link + '/3/movie/top_rated?api_key=%s&language=en-US&page=1' % self.tmdb_key
        self.tmdb_upcoming_link = self.tmdb_link + '/3/movie/upcoming?api_key=%s&language=en-US&page=1' % self.tmdb_key
        self.tmdb_trending_day_link = self.tmdb_link + '/3/trending/movie/day?api_key=%s&language=en-US&page=1' % self.tmdb_key
        self.tmdb_trending_week_link = self.tmdb_link + '/3/trending/movie/week?api_key=%s&language=en-US&page=1' % self.tmdb_key
        self.tmdb_featured_link = self.tmdb_link + '/3/discover/movie?api_key=%s&vote_count.gte=100&sort_by=first_air_date.desc&language=en-US&include_adult=false&page=1' % self.tmdb_key
        self.tmdb_premiere_link = self.tmdb_link + '/3/discover/movie?api_key=%s&first_air_date.gte=%s&first_air_date.lte=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, self.year_date, self.today_date)
        self.tmdb_views_link = self.tmdb_link + '/3/discover/movie?api_key=%s&vote_count.gte=100&sort_by=vote_average.desc&language=en-US&include_adult=false&page=1' % self.tmdb_key
        self.tmdb_in_theatres_link = self.tmdb_link + '/3/discover/movie?api_key=%s&release_date.gte=date[90]&release_date.lte=date[0]&language=en-US&include_adult=false&page=1' % self.tmdb_key
        self.tmdb_year_link = self.tmdb_link + '/3/discover/movie?api_key=%s&primary_release_year=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, '%s')
        self.tmdb_decade_link = self.tmdb_link + '/3/discover/movie?api_key=%s&primary_release_date.gte=%s&primary_release_date.lte=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, '%s', '%s')
        self.tmdb_language_link = self.tmdb_link + '/3/discover/movie?api_key=%s&with_original_language=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, '%s')
        self.tmdb_certification_link = self.tmdb_link + '/3/discover/movie?api_key=%s&certification_country=US&certification=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, '%s')
        self.tmdb_genre_link = self.tmdb_link + '/3/discover/movie?api_key=%s&with_genres=%s&language=en-US&include_adult=false&page=1' % (self.tmdb_key, '%s')
        self.tmdb_collections_link = self.tmdb_link + '/3/collection/%s?api_key=%s&language=en-US&page=1' % ('%s', self.tmdb_key)
        self.tmdb_userlists_link = self.tmdb_link + '/3/list/%s?api_key=%s&language=en-US&page=1' % ('%s', self.tmdb_key)
        self.tmdb_jewtestmovies_link = self.tmdb_userlists_link % ('97123')
        self.tmdb_jewmovies_link = self.tmdb_userlists_link % ('86696')
        self.tmdb_favorites_link = tmdb_utils.get_movie_favorites()
        self.tmdb_watchlist_link = tmdb_utils.get_movie_watchlist()

        self.imdb_search_link = self.imdb_link + '/search/title/?title=%s&title_type=feature,tv_movie'
        self.imdb_person_link = self.imdb_link + '/search/title?title_type=movie,short,tvMovie&production_status=released&role=%s&sort=year,desc&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_persons_link = self.imdb_link + '/search/name?count=100&name=%s'
        self.imdb_personlist_link = self.imdb_link + '/search/name?count=100&gender=male,female'
        self.imdb_year_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&year=%s,%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', '%s', self.items_per_page)
        self.imdb_added_link  = self.imdb_link + '/search/title?title_type=movie,tvMovie&languages=en&num_votes=500,&production_status=released&release_date=%s,%s&sort=release_date,desc&count=%s&start=1' % (self.year_date, self.today_date, self.items_per_page)
        self.imdb_theaters_link = self.imdb_link + '/search/title?title_type=feature&release_date=date[120],date[0]&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_theaters1_link = self.imdb_link + '/search/title?title_type=feature&num_votes=1000,&countries=us&languages=en&release_date=date[90],date[0]&sort=release_date,desc&count=%s&start=1' % self.items_per_page
        self.imdb_theaters2_link = self.imdb_link + '/showtimes/location?ref_=inth_ov_sh_sm'
        self.imdb_boxoffice_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&sort=boxoffice_gross_us,desc&count=%s&start=1' % self.items_per_page
        self.imdb_featured_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&release_date=date[365],date[60]&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_popular_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&groups=top_1000&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_oscars_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&groups=oscar_best_picture_winners&sort=year,desc&count=%s&start=1' % self.items_per_page
        self.imdb_rating_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&num_votes=5000,&release_date=,date[0]&sort=user_rating,desc&count=%s&start=1' % self.items_per_page
        self.imdb_views_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&sort=num_votes,desc&count=%s&start=1' % self.items_per_page
        self.imdb_genre_link = self.imdb_link + '/search/title?title_type=feature,tv_movie,documentary&release_date=,date[0]&genres=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_language_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&primary_language=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_certification_link = self.imdb_link + '/search/title?title_type=movie,tvMovie&production_status=released&certificates=us:%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_list_link = self.imdb_link + '/list/%s/?view=simple&sort=date_added,desc&title_type=movie,short,tvMovie,video&start=1'
        self.imdb_list2_link = self.imdb_link + '/list/%s/?view=simple&sort=alpha,asc&title_type=movie,short,tvMovie,video&start=1'
        self.imdb_lists_link = self.imdb_link + '/user/ur%s/lists?tab=all&sort=modified&order=desc&filter=titles' % self.imdb_user
        self.imdb_watchlist_link = self.imdb_link + '/user/ur%s/watchlist?sort=date_added,desc' % self.imdb_user
        self.imdb_watchlist2_link = self.imdb_link + '/user/ur%s/watchlist?sort=alpha,asc' % self.imdb_user
        self.imdb_keyword_link = self.imdb_link + '/search/title?title_type=movie,short,tvMovie&release_date=,date[0]&keywords=%s&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_keywords_link = self.imdb_link + '/search/keyword?keywords=%s&title_type=movie,tvMovie&sort=moviemeter,asc&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_userlists_link = self.imdb_link + '/list/%s/?view=detail&sort=alpha,asc&title_type=movie,tvMovie&count=%s&start=1' % ('%s', self.items_per_page)
        self.imdb_top1000y20to29_link = self.imdb_link + '/search/title/?groups=top_1000&release_date=2020,2029&title_type=movie,tvMovie&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_top1000y10to19_link = self.imdb_link + '/search/title/?groups=top_1000&release_date=2010,2019&title_type=movie,tvMovie&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_top1000y00to09_link = self.imdb_link + '/search/title/?groups=top_1000&release_date=2000,2009&title_type=movie,tvMovie&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_top1000y90to99_link = self.imdb_link + '/search/title/?groups=top_1000&release_date=1990,1999&title_type=movie,tvMovie&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page
        self.imdb_top1000y80to89_link = self.imdb_link + '/search/title/?groups=top_1000&release_date=1980,1989&title_type=movie,tvMovie&sort=moviemeter,asc&count=%s&start=1' % self.items_per_page

        self.trakt_search_link = self.trakt_link + '/search/movie?query=%s&limit=%s&page=1' % ('%s', self.items_per_page)
        self.trakt_person_link = self.trakt_link + '/search/person?query=%s&limit=%s&page=1' % ('%s', self.items_per_page)
        self.trakt_anticipated_link = self.trakt_link + '/movies/anticipated?limit=%s&page=1' % self.items_per_page
        self.trakt_boxoffice_link = self.trakt_link + '/movies/boxoffice?limit=%s&page=1' % self.items_per_page
        self.trakt_popular_link = self.trakt_link + '/movies/popular?limit=%s&page=1' % self.items_per_page
        self.trakt_trending_link = self.trakt_link + '/movies/trending?limit=%s&page=1' % self.items_per_page
        self.trakt_featured_link = self.trakt_link + '/recommendations/movies?limit=%s&page=1' % self.items_per_page
        self.trakt_list_link = self.trakt_link + '/users/%s/lists/%s/items'
        self.trakt_lists_link = self.trakt_link + '/users/me/lists'
        self.trakt_likedlists_link = self.trakt_link + '/users/likes/lists?limit=1000000'
        self.trakt_collection_link = self.trakt_link + '/users/me/collection/movies'
        self.trakt_watchlist_link = self.trakt_link + '/users/me/watchlist/movies'
        self.trakt_watchedlist_link = self.trakt_link + '/users/me/watched/movies'
        self.trakt_history_link = self.trakt_link + '/users/me/history/movies?limit=%s&page=1' % self.items_per_page
        self.trakt_ondeck_link = self.trakt_link + '/sync/playback/movies?limit=%s&page=1' % self.items_per_page
        self.trakt_related_link = self.trakt_link + '/movies/%s/related'
        self.trakt_update_link = self.trakt_link + '/movies/updates/%s?limit=%s&page=1' % ('%s', self.items_per_page)
        self.trakt_played1_link = self.trakt_link + '/movies/played/weekly?limit=%s&page=1' % self.items_per_page
        self.trakt_played2_link = self.trakt_link + '/movies/played/monthly?limit=%s&page=1' % self.items_per_page
        self.trakt_played3_link = self.trakt_link + '/movies/played/yearly?limit=%s&page=1' % self.items_per_page
        self.trakt_played4_link = self.trakt_link + '/movies/played/all?limit=%s&page=1' % self.items_per_page
        self.trakt_collected1_link = self.trakt_link + '/movies/collected/weekly?limit=%s&page=1' % self.items_per_page
        self.trakt_collected2_link = self.trakt_link + '/movies/collected/monthly?limit=%s&page=1' % self.items_per_page
        self.trakt_collected3_link = self.trakt_link + '/movies/collected/yearly?limit=%s&page=1' % self.items_per_page
        self.trakt_collected4_link = self.trakt_link + '/movies/collected/all?limit=%s&page=1' % self.items_per_page
        self.trakt_watched1_link = self.trakt_link + '/movies/watched/weekly?limit=%s&page=1' % self.items_per_page
        self.trakt_watched2_link = self.trakt_link + '/movies/watched/monthly?limit=%s&page=1' % self.items_per_page
        self.trakt_watched3_link = self.trakt_link + '/movies/watched/yearly?limit=%s&page=1' % self.items_per_page
        self.trakt_watched4_link = self.trakt_link + '/movies/watched/all?limit=%s&page=1' % self.items_per_page


    def favorites(self):
        try:
            items = favorites.getFavorites('movie')
            self.list = [i[1] for i in items]
            for i in self.list:
                if not 'year' in i:
                    i['year'] = '0'
                if not 'name' in i:
                    i['name'] = '%s (%s)' % (i['title'], i['year'])
                try:
                    #i['title'] = i['title'].encode('utf-8')
                    i['title'] = client_utils.replaceHTMLCodes(i['title'])
                except:
                    pass
                try:
                    #i['name'] = i['name'].encode('utf-8')
                    i['name'] = client_utils.replaceHTMLCodes(i['name'])
                except:
                    pass
                if not 'duration' in i:
                    i['duration'] = '0'
                if not 'imdb' in i:
                    i['imdb'] = '0'
                if not 'tmdb' in i:
                    i['tmdb'] = '0'
                if not 'tvdb' in i:
                    i['tvdb'] = '0'
                if not 'poster' in i:
                    i['poster'] = '0'
                if not 'banner' in i:
                    i['banner'] = '0'
                if not 'fanart' in i:
                    i['fanart'] = '0'
            self.worker()
            self.list = sorted(self.list, key=lambda k: k['title'])
            self.movieDirectory(self.list)
        except:
            #log_utils.log('favorites', 1)
            return


    def search_term_menu(self, select):
        navigator.navigator().addDirectoryItem('New Search...', 'movies_searchterm&select=%s' % select, 'search.png', 'DefaultMovies.png')
        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS %s (ID Integer PRIMARY KEY AUTOINCREMENT, term);" % select)
        except:
            pass
        dbcur.execute("SELECT * FROM %s ORDER BY ID DESC" % select)
        delete_option = False
        for (id, term) in dbcur.fetchall():
            delete_option = True
            navigator.navigator().addDirectoryItem(term.title(), 'movies_searchterm&select=%s&name=%s' % (select, term), 'search.png', 'DefaultMovies.png')
        dbcur.close()
        if delete_option:
            navigator.navigator().addDirectoryItem('Clear Search History', 'clear_search_cache&select=%s' % select, 'tools.png', 'DefaultAddonProgram.png')
        navigator.navigator().endDirectory(cached=False)


    def search_term(self, select, q=None):
        control.idle()
        if (q == None or q == ''):
            k = control.keyboard('', 'Search') ; k.doModal()
            q = k.getText() if k.isConfirmed() else None
        if (q == None or q == ''):
            return
        q = q.lower()
        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM %s WHERE term = ?" % select, (q,))
        dbcur.execute("INSERT INTO %s VALUES (?, ?)" % select, (None, q))
        dbcon.commit()
        dbcur.close()
        if select == 'movies':
            if self.search_movies_source == '1':
                url = self.imdb_search_link % urllib_parse.quote_plus(q)
            elif self.search_movies_source == '2':
                url = self.trakt_search_link % urllib_parse.quote_plus(q)
            else:
                url = self.tmdb_search_link % urllib_parse.quote_plus(q)
            self.get(url)
        elif select == 'people':
            if self.search_people_source == '1':
                url = self.imdb_persons_link % urllib_parse.quote_plus(q)
                self.search_imdb_persons(url)
            else:
                self.search_tmdb_people(q)
        elif select == 'keywords':
            if self.search_keywords_source == '1':
                url = self.imdb_keyword_link % urllib_parse.quote_plus(q)
                self.get(url)
            else:
                self.search_tmdb_keyword(q)
        elif select == 'companies':
            self.search_tmdb_companies(q)
        elif select == 'collections':
            self.search_tmdb_collection(q)


    def search_imdb_persons(self, url):
        if url == None:
            if self.addon_caching == 'true':
                self.list = cache.get(self.imdb_person_list, 24, self.imdb_personlist_link)
            else:
                self.list = self.imdb_person_list(self.imdb_personlist_link)
        else:
            if self.addon_caching == 'true':
                self.list = cache.get(self.imdb_person_list, 1, url)
            else:
                self.list = self.imdb_person_list(url)
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdb_keywords(self):
        from resources.lib.indexers.metadata.imdb import imdb_various
        keywords = imdb_various.keywords_list
        for keyword in keywords:
            self.list.append({'name': keyword.replace('-', ' '), 'url': self.imdb_keywords_link % keyword, 'image': 'imdb.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdb_years(self):
        year = (self.datetime.strftime('%Y'))
        for i in range(int(year)+1, 1900, -1):
            self.list.append({'name': str(i), 'url': self.imdb_year_link % (str(i), str(i)), 'image': 'years.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdb_decades(self):
        year = (self.datetime.strftime('%Y'))
        dec = int(year[:3]) * 10
        for i in range(dec, 1890, -10):
            self.list.append({'name': str(i) + 's', 'url': self.imdb_year_link % (str(i), str(i+9)), 'image': 'years.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdb_genres(self):
        from resources.lib.indexers.metadata.imdb import imdb_various
        genres = imdb_various.genre_list
        for genre in genres:
            self.list.append({'name': genre[0], 'url': self.imdb_genre_link % genre[1] if genre[2] else self.imdb_keyword_link % genre[1], 'image': 'genres.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdb_languages(self):
        from resources.lib.indexers.metadata.imdb import imdb_various
        languages = imdb_various.languages_list
        for language in languages:
            self.list.append({'name': language[0], 'url': self.imdb_language_link % language[1], 'image': 'languages.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdb_certifications(self):
        certificates = ['G', 'PG', 'PG-13', 'R', 'NC-17']
        for certificate in certificates:
            self.list.append({'name': str(certificate), 'url': self.imdb_certification_link % str(certificate), 'image': 'certificates.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def hellaLifeTimeHallMark(self):
        from resources.lib.indexers.metadata.imdb import imdb_userlists
        userlists = imdb_userlists.imdb_hellaLifeTimeHallMark
        for item in userlists:
            self.list.append({'name': item[0], 'url': self.imdb_userlists_link % item[1], 'image': 'imdb.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def imdbUserLists(self):
        self.list.append({'name': 'IMDb Top1000 (2020 - 2029)', 'url': self.imdb_top1000y20to29_link, 'image': 'imdb.png', 'action': 'movies'})
        self.list.append({'name': 'IMDb Top1000 (2010 - 2019)', 'url': self.imdb_top1000y10to19_link, 'image': 'imdb.png', 'action': 'movies'})
        self.list.append({'name': 'IMDb Top1000 (2000 - 2009)', 'url': self.imdb_top1000y00to09_link, 'image': 'imdb.png', 'action': 'movies'})
        self.list.append({'name': 'IMDb Top1000 (1990 - 1999)', 'url': self.imdb_top1000y90to99_link, 'image': 'imdb.png', 'action': 'movies'})
        self.list.append({'name': 'IMDb Top1000 (1980 - 1989)', 'url': self.imdb_top1000y80to89_link, 'image': 'imdb.png', 'action': 'movies'})
        from resources.lib.indexers.metadata.imdb import imdb_userlists
        userlists = imdb_userlists.imdb_imdbUserLists
        for item in userlists:
            self.list.append({'name': item[0], 'url': self.imdb_userlists_link % item[1], 'image': 'imdb.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def search_tmdb_people(self, q=None):
        query = urllib_parse.quote_plus(q)
        self.list = tmdb_utils.find_people(None, query, 'movie')
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def search_tmdb_keyword(self, q=None):
        query = urllib_parse.quote_plus(q)
        self.list = tmdb_utils.find_keyword(None, query, 'movie')
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def search_tmdb_companies(self, q=None):
        query = urllib_parse.quote_plus(q)
        self.list = tmdb_utils.find_companies(query, 'movie')
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def search_tmdb_collection(self, q=None):
        query = urllib_parse.quote_plus(q)
        self.list = tmdb_utils.find_collection(query)
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_years(self):
        year = (self.datetime.strftime('%Y'))
        for i in range(int(year)+1, 1900, -1):
            self.list.append({'name': str(i), 'url': self.tmdb_year_link % str(i), 'image': 'years.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_decades(self):
        year = (self.datetime.strftime('%Y'))
        dec = int(year[:3]) * 10
        for i in range(dec, 1890, -10):
            self.list.append({'name': str(i) + 's', 'url': self.tmdb_decade_link % (str(i) + '-01-01', str(i+9) + '-01-01'), 'image': 'years.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_genres(self):
        from resources.lib.indexers.metadata.tmdb import tmdb_various
        genres = tmdb_various.genre_list
        for item in genres:
            self.list.append({'name': item[0], 'url': self.tmdb_genre_link % item[1], 'image': 'genres.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_languages(self):
        from resources.lib.indexers.metadata.tmdb import tmdb_various
        languages = tmdb_various.language_list
        for item in languages:
            self.list.append({'name': item[0], 'url': self.tmdb_language_link % item[1], 'image': 'languages.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_certifications(self):
        certificates = ['G', 'PG', 'PG-13', 'R', 'NC-17', 'NR']
        for certificate in certificates:
            self.list.append({'name': str(certificate), 'url': self.tmdb_certification_link % str(certificate), 'image': 'certificates.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_popular_companies(self):
        from resources.lib.indexers.metadata.tmdb import tmdb_production_companies
        companies = tmdb_production_companies.companies
        for item in companies:
            item_url = self.tmdb_link + '/3/discover/movie?api_key=%s&with_companies=%s&language=en-US&page=1' % (self.tmdb_key, '%s')
            if self.original_artwork == 'true':
                item_art = self.tmdb_image_link + item['image'] if 'image' in item and not item['image'] == None else 'tmdb.png'
            else:
                item_art = self.tmdb_image_link % ('300', item['image']) if 'image' in item and not item['image'] == None else 'tmdb.png'
            self.list.append({'name': item['name'], 'url': item_url % item['id'], 'image': item_art, 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_popular_keywords(self):
        from resources.lib.indexers.metadata.tmdb import tmdb_keywords
        keywords = tmdb_keywords.keywords_list
        for item in keywords:
            item_url = self.tmdb_link + '/3/discover/movie?api_key=%s&with_keywords=%s&language=en-US&page=1' % (self.tmdb_key, '%s')
            self.list.append({'name': item['name'], 'url': item_url % item['id'], 'image': 'tmdb.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_popular_people(self):
        self.list = tmdb_utils.get_popular_people(None, 'movie')
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def tmdb_collections_genres(self, url):
        try:
            from resources.lib.indexers.metadata.tmdb import tmdb_collections
            double_line = control.setting('tmdb.collections.linesplit') == '1'
            the_genre = url
            collections = tmdb_collections.tmdb_collections_list
            for item in collections:
                genres = tmdb_utils.parse_genres(item['genres'], line=False)
                if not the_genre in genres:
                    continue
                item_genres = tmdb_utils.parse_genres(item['genres'], line=True)
                if double_line:
                    item_label = '[B]%s[/B][CR][LIGHT](%s)[/LIGHT]' % (item['name'], item_genres)
                    label_up = item_label.split('[CR]')[0]
                    label_up_clean = label_up.replace('[B]', '').replace('[/B]', '')
                    label_down = item_label.split('[CR]')[1]
                    label_down_clean = label_down.replace('[LIGHT]', '').replace('[/LIGHT]', '')
                    if len(label_down_clean) > len(label_up_clean):
                        label_up += (len(label_down_clean) - len(label_up_clean)) * '  '
                        item_label = label_up + '[CR]' + label_down
                else:
                    item_label = '[B]%s[/B] [LIGHT](%s)[/LIGHT]' % (item['name'], item_genres)
                item_url = self.tmdb_collections_link % item['id']
                if self.original_artwork == 'true':
                    item_poster = self.tmdb_image_link + item['poster'] if 'poster' in item and not item['poster'] == None else '0'
                else:
                    item_poster = self.tmdb_image_link % ('500', item['poster']) if 'poster' in item and not item['poster'] == None else '0'
                if self.original_artwork == 'true':
                    item_fanart = self.tmdb_image_link + item['fanart'] if 'fanart' in item and not item['fanart'] == None else '0'
                else:
                    item_fanart = self.tmdb_image_link % ('1280', item['fanart']) if 'fanart' in item and not item['fanart'] == None else '0'
                self.list.append({'name': item_label, 'url': item_url, 'poster': item_poster, 'fanart': item_fanart, 'image': 'tmdb.png', 'action': 'movies'})
            self.addDirectory(self.list)
            return self.list
        except Exception:
            #log_utils.log('tmdb_collections_genres', 1)
            return self.list


    def tmdb_collections(self, url):
        try:
            from resources.lib.indexers.metadata.tmdb import tmdb_collections
            double_line = control.setting('tmdb.collections.linesplit') == '1'
            the_page = url
            collections = tmdb_collections.tmdb_collections_list
            for item in collections:
                if not the_page == 'all':
                    if not the_page == item['page']:
                        continue
                item_genres = tmdb_utils.parse_genres(item['genres'], line=True)
                if double_line:
                    item_label = '[B]%s[/B][CR][LIGHT](%s)[/LIGHT]' % (item['name'], item_genres)
                    label_up = item_label.split('[CR]')[0]
                    label_up_clean = label_up.replace('[B]', '').replace('[/B]', '')
                    label_down = item_label.split('[CR]')[1]
                    label_down_clean = label_down.replace('[LIGHT]', '').replace('[/LIGHT]', '')
                    if len(label_down_clean) > len(label_up_clean):
                        label_up += (len(label_down_clean) - len(label_up_clean)) * '  '
                        item_label = label_up + '[CR]' + label_down
                else:
                    item_label = '[B]%s[/B] [LIGHT](%s)[/LIGHT]' % (item['name'], item_genres)
                item_url = self.tmdb_collections_link % item['id']
                if self.original_artwork == 'true':
                    item_poster = self.tmdb_image_link + item['poster'] if 'poster' in item and not item['poster'] == None else '0'
                else:
                    item_poster = self.tmdb_image_link % ('500', item['poster']) if 'poster' in item and not item['poster'] == None else '0'
                if self.original_artwork == 'true':
                    item_fanart = self.tmdb_image_link + item['fanart'] if 'fanart' in item and not item['fanart'] == None else '0'
                else:
                    item_fanart = self.tmdb_image_link % ('1280', item['fanart']) if 'fanart' in item and not item['fanart'] == None else '0'
                self.list.append({'name': item_label, 'url': item_url, 'poster': item_poster, 'fanart': item_fanart, 'image': 'tmdb.png', 'action': 'movies'})
            self.addDirectory(self.list)
            return self.list
        except Exception:
            #log_utils.log('tmdb_collections', 1)
            return self.list


    def tmdb_userlists_list(self, url):
        from resources.lib.indexers.metadata.tmdb import tmdb_userlists
        if url == 'tmdbActorCollections':
            userlists = tmdb_userlists.tmdb_ActorCollections
        elif url == 'tmdbDCvsMarvel':
            userlists = tmdb_userlists.tmdb_DCvsMarvel
        elif url == 'tmdbHolidays':
            userlists = tmdb_userlists.tmdb_Holidays
        elif url == 'tmdbAssortment':
            userlists = tmdb_userlists.tmdb_Assortment
        elif url == 'tmdbCollections':
            userlists = tmdb_userlists.tmdb_Collections
        elif url == 'tmdbCollectionsDupes':
            userlists = tmdb_userlists.tmdb_CollectionsDupes
        for item in userlists:
            self.list.append({'name': item[0], 'url': self.tmdb_userlists_link % item[1], 'image': 'tmdb.png', 'action': 'movies'})
        self.addDirectory(self.list)
        return self.list


    def userlists_trakt(self):
        userlists = []
        try:
            if trakt.getTraktCredentialsInfo() == False:
                raise Exception()
            activity = trakt.getActivity()
            userlists += self.trakt_user_list(self.trakt_lists_link, self.trakt_user)
        except:
            pass
        self.list = userlists
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list, queue=True)
        return self.list


    def userlists_trakt_liked(self):
        userlists = []
        try:
            if trakt.getTraktCredentialsInfo() == False:
                raise Exception()
            activity = trakt.getActivity()
            userlists += self.trakt_user_list(self.trakt_likedlists_link, self.trakt_user)
        except:
            pass
        self.list = userlists
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list, queue=True)
        return self.list


    def userlists_imdb(self):
        userlists = []
        try:
            if self.imdb_user == '':
                raise Exception()
            userlists += self.imdb_user_list(self.imdb_lists_link)
        except:
            pass
        self.list = userlists
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list, queue=True)
        return self.list


    def userlists_tmdb(self):
        userlists = []
        try:
            if tmdb_utils.getTMDbCredentialsInfo() == False:
                raise Exception()
            userlists += tmdb_utils.get_created_lists(self.tmdb_userlists_link)
        except:
            pass
        self.list = userlists
        for i in range(0, len(self.list)):
            self.list[i].update({'action': 'movies'})
        self.list = sorted(self.list, key=lambda k: (k['image'], k['name'].lower()))
        self.addDirectory(self.list, queue=True)
        return self.list


    def trakt_list(self, url, user):
        try:
            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q
            result = trakt.getTraktAsJson(u)
            items = []
            for i in result:
                try:
                    items.append(i['movie'])
                except:
                    pass
            if len(items) == 0:
                items = result
            try:
                q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
                if not int(q['limit']) == len(items):
                    raise Exception()
                q.update({'page': str(int(q['page']) + 1)})
                q = (urllib_parse.urlencode(q)).replace('%2C', ',')
                next = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q
                next = six.ensure_str(next)
            except:
                next = ''
            for item in items:
                try:
                    title = item['title']
                    title = client_utils.replaceHTMLCodes(title)
                    year = item.get('year')
                    if not year:
                        year = '0'
                    else:
                        year = re.sub(r'[^0-9]', '', str(year))
                    if int(year) > int(self.datetime.strftime('%Y')):
                        if self.shownoyear != 'true':
                            raise Exception()
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
                    paused_at = item.get('paused_at')
                    if not paused_at:
                        paused_at == '0'
                    else:
                        paused_at = re.sub('[^0-9]+', '', str(paused_at))
                    self.list.append({'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'next': next, 'paused_at': paused_at})
                except:
                    #log_utils.log('trakt_list', 1)
                    pass
        except:
            #log_utils.log('trakt_list', 1)
            pass
        return self.list


    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
            for item in items:
                try:
                    try:
                        name = item['list']['name']
                    except:
                        name = item['name']
                    name = client_utils.replaceHTMLCodes(name)
                    try:
                        url = (trakt.slug(item['list']['user']['username']), item['list']['ids']['slug'])
                    except:
                        url = ('me', item['ids']['slug'])
                    url = self.trakt_list_link % url
                    self.list.append({'name': name, 'url': url, 'context': url, 'image': 'trakt.png'})
                except:
                    #log_utils.log('trakt_user_list', 1)
                    pass
        except:
            #log_utils.log('trakt_user_list', 1)
            pass
        return self.list


    def imdb_list(self, url):
        try:
            if 'date[' in url:
                for i in re.findall('date\[(\d+)\]', url):
                    url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))
            def imdb_watchlist_id(url):
                result = client.scrapePage(url, timeout='30').text
                return client_utils.parseDOM(result, 'meta', ret='content', attrs={'property': 'pageId'})[0]
            if url == self.imdb_watchlist_link:
                if self.addon_caching == 'true':
                    url = cache.get(imdb_watchlist_id, 8640, url)
                else:
                    url = imdb_watchlist_id(url)
                url = self.imdb_list_link % url
            elif url == self.imdb_watchlist2_link:
                if self.addon_caching == 'true':
                    url = cache.get(imdb_watchlist_id, 8640, url)
                else:
                    url = imdb_watchlist_id(url)
                url = self.imdb_list2_link % url
            result = client.scrapePage(url, timeout='30').text
            result = control.six_decode(result)
            result = result.replace('\n', ' ')
            items = client_utils.parseDOM(result, 'div', attrs={'class': r'lister-item .*?'})
            items += client_utils.parseDOM(result, 'div', attrs={'class': r'list_item.*?'})
            try:
                result = result.replace(r'"class=".*?ister-page-nex', '" class="lister-page-nex')
                next = client_utils.parseDOM(result, 'a', ret='href', attrs={'class': r'.*?ister-page-nex.*?'})
                if len(next) == 0:
                    next = client_utils.parseDOM(result, 'div', attrs={'class': u'pagination'})[0]
                    next = zip(client_utils.parseDOM(next, 'a', ret='href'), client_utils.parseDOM(next, 'a'))
                    next = [i[0] for i in next if 'Next' in i[1]]
                next = url.replace(urllib_parse.urlparse(url).query, urllib_parse.urlparse(next[0]).query)
                next = client_utils.replaceHTMLCodes(next)
            except:
                next = ''
            for item in items:
                try:
                    title = client_utils.parseDOM(item, 'a')[1]
                    title = client_utils.replaceHTMLCodes(title)
                    year = client_utils.parseDOM(item, 'span', attrs={'class': r'lister-item-year.*?'})
                    year += client_utils.parseDOM(item, 'span', attrs={'class': r'year_type'})
                    try:
                        year = re.compile(r'(\d{4})').findall(str(year))[0]
                    except:
                        year = '0'
                    if int(year) > int(self.datetime.strftime('%Y')):
                        if self.shownoyear != 'true':
                            raise Exception()
                    try:
                        imdb = client_utils.parseDOM(item, 'a', ret='href')[0]
                        imdb = re.findall(r'(tt\d*)', imdb)[0]
                    except:
                        imdb = '0'
                    self.list.append({'title': title, 'originaltitle': title, 'year': year, 'imdb': imdb, 'tmdb': '0', 'tvdb': '0', 'next': next})
                except:
                    #log_utils.log('imdb_list', 1)
                    pass
        except:
            #log_utils.log('imdb_list', 1)
            pass
        return self.list


    def imdb_user_list(self, url):
        try:
            if control.setting('imdb.sort.order') == '1':
                list_url = self.imdb_list2_link
            else:
                list_url = self.imdb_list_link
            result = client.scrapePage(url, timeout='30').text
            items = client_utils.parseDOM(result, 'li', attrs={'class': 'ipl-zebra-list__item user-list'})
            for item in items:
                try:
                    name = client_utils.parseDOM(item, 'a')[0]
                    name = client_utils.replaceHTMLCodes(name)
                    url = client_utils.parseDOM(item, 'a', ret='href')[0]
                    url = url.split('/list/', 1)[-1].strip('/')
                    url = list_url % url
                    url = client_utils.replaceHTMLCodes(url)
                    self.list.append({'name': name, 'url': url, 'context': url, 'image': 'imdb.png'})
                except:
                    #log_utils.log('imdb_user_list', 1)
                    pass
        except:
            #log_utils.log('imdb_user_list', 1)
            pass
        return self.list


    def imdb_person_list(self, url):
        try:
            result = client.scrapePage(url, timeout='30').text
            #items = client_utils.parseDOM(result, 'div', attrs={'class': '.+? mode-detail'})
            items = client_utils.parseDOM(result, 'div', attrs={'class': '.+?etail'})
            for item in items:
                try:
                    name = client_utils.parseDOM(item, 'img', ret='alt')[0]
                    name = client_utils.replaceHTMLCodes(name)
                    url = client_utils.parseDOM(item, 'a', ret='href')[0]
                    url = re.findall(r'(nm\d*)', url, re.I)[0]
                    url = self.imdb_person_link % url
                    url = client_utils.replaceHTMLCodes(url)
                    image = client_utils.parseDOM(item, 'img', ret='src')[0]
                    image = re.sub(r'(?:_SX|_SY|_UX|_UY|_CR|_AL)(?:\d+|_).+?\.', '_SX500.', image)
                    image = client_utils.replaceHTMLCodes(image)
                    self.list.append({'name': name, 'url': url, 'image': image})
                except:
                    #log_utils.log('imdb_person_list', 1)
                    pass
        except:
            #log_utils.log('imdb_person_list', 1)
            pass
        return self.list


    def tmdb_list(self, url):
        try:
            if 'date[' in url:
                for i in re.findall('date\[(\d+)\]', url):
                    url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))
            result = client.scrapePage(url, timeout='30').json()
            try:
                page = int(result['page'])
                total = int(result['total_pages'])
                if page >= total:
                    raise Exception()
                if not 'page=' in url:
                    raise Exception()
                next = '%s&page=%s' % (url.split('&page=', 1)[0], str(page+1))
            except:
                next = ''
            if 'results' in result:
                items = result['results']
            elif 'items' in result:
                items = result['items']
            elif 'parts' in result:
                items = result['parts']
            elif 'cast' in result:
                items = result['cast']
            for item in items:
                try:
                    if 'media_type' in item and not item['media_type'] == 'movie':
                        raise Exception()
                    title = item['title']
                    title = client_utils.replaceHTMLCodes(title)
                    originaltitle = item['original_title']
                    originaltitle = client_utils.replaceHTMLCodes(originaltitle)
                    if not originaltitle:
                        originaltitle = title
                    year = item.get('release_date')
                    if not year:
                        year = '0'
                    else:
                        year = re.compile('(\d{4})').findall(year)[0]
                    if int(year) > int(self.datetime.strftime('%Y')):
                        if self.shownoyear != 'true':
                            raise Exception()
                    tmdb = item.get('id')
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = re.sub('[^0-9]', '', str(tmdb))
                    self.list.append({'title': title, 'originaltitle': originaltitle, 'year': year, 'imdb': '0', 'tmdb': tmdb, 'tvdb': '0', 'next': next})
                except:
                    #log_utils.log('tmdb_list', 1)
                    pass
        except:
            #log_utils.log('tmdb_list', 1)
            pass
        return self.list


    def get_fanart_tv_artwork(self, id): #tmdb
        try:
            art = client.scrapePage(self.fanart_tv_art_link % id, headers=self.fanart_tv_headers, timeout='30').json()
            try:
                poster = art.get('movieposter')
                if poster:
                    poster = [x for x in poster if x.get('lang') == 'en'][::-1] + [x for x in poster if x.get('lang') in ['00', '']][::-1]
                    poster = poster[0].get('url')
                    if not poster:
                        poster = '0'
                else:
                    poster = '0'
            except:
                poster = '0'
            try:
                if 'moviebackground' in art:
                    fanart = art.get('moviebackground')
                else:
                    fanart = art.get('moviethumb')
                if fanart:
                    fanart = [x for x in fanart if x.get('lang') == 'en'][::-1] + [x for x in fanart if x.get('lang') in ['00', '']][::-1]
                    fanart = fanart[0].get('url')
                    if not fanart:
                        fanart = '0'
                else:
                    fanart = '0'
            except:
                fanart = '0'
            try:
                banner = art.get('moviebanner')
                if banner:
                    banner = [x for x in banner if x.get('lang') == 'en'][::-1] + [x for x in banner if x.get('lang') in ['00', '']][::-1]
                    banner = banner[0].get('url')
                    if not banner:
                        banner = '0'
                else:
                    banner = '0'
            except:
                banner = '0'
            try:
                if 'hdmovielogo' in art:
                    clearlogo = art.get('hdmovielogo')
                else:
                    clearlogo = art.get('clearlogo')
                if clearlogo:
                    clearlogo = [x for x in clearlogo if x.get('lang') == 'en'][::-1] + [x for x in clearlogo if x.get('lang') in ['00', '']][::-1]
                    clearlogo = clearlogo[0].get('url')
                    if not clearlogo:
                        clearlogo = '0'
                else:
                    clearlogo = '0'
            except:
                clearlogo = '0'
            try:
                if 'hdmovieclearart' in art:
                    clearart = art.get('hdmovieclearart')
                else:
                    clearart = art.get('clearart')
                if clearart:
                    clearart = [x for x in clearart if x.get('lang') == 'en'][::-1] + [x for x in clearart if x.get('lang') in ['00', '']][::-1]
                    clearart = clearart[0].get('url')
                    if not clearart:
                        clearart = '0'
                else:
                    clearart = '0'
            except:
                clearart = '0'
            try:
                if 'moviethumb' in art:
                    landscape = art.get('moviethumb')
                else:
                    landscape = art.get('moviebackground')
                if landscape:
                    landscape = [x for x in landscape if x.get('lang') == 'en'][::-1] + [x for x in landscape if x.get('lang') in ['00', '']][::-1]
                    landscape = landscape[0].get('url')
                    if not landscape:
                        landscape = '0'
                else:
                    landscape = '0'
            except:
                landscape = '0'
            try:
                discart = art.get('moviedisc')
                if discart:
                    discart = [x for x in discart if x.get('lang') == 'en'][::-1] + [x for x in discart if x.get('lang') in ['00', '']][::-1]
                    discart = discart[0].get('url')
                    if not discart:
                        discart = '0'
                else:
                    discart = '0'
            except:
                discart = '0'
        except:
            poster = fanart = banner = clearlogo = clearart = landscape = discart = '0'
            #log_utils.log('get_fanart_tv_artwork', 1)
        return poster, fanart, banner, clearlogo, clearart, landscape, discart


    def trakt_info(self, i):
        try:
            if self.list[i]['metacache'] == True:
                return
            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            if imdb == '0' and not tmdb == '0':
                try:
                    temp_item = tmdb_utils.get_movie_external_ids(tmdb)
                    imdb = temp_item.get('imdb_id', '0') or '0'
                except:
                    pass
            if imdb == '0' and tmdb == '0':
                try:
                    temp_item = trakt.SearchMovie(self.list[i]['title'], self.list[i]['year'])
                    if temp_item[0]['movie']['title'].lower() != self.list[i]['title'].lower() or int(temp_item[0]['movie']['year']) != int(self.list[i]['year']):
                        raise Exception()
                    imdb = temp_item[0]['movie'].get('ids', {}).get('imdb') or '0'
                    tmdb = temp_item[0]['movie'].get('ids', {}).get('tmdb') or '0'
                except:
                    pass
            if not imdb or imdb == '0':
                raise Exception()
            item = trakt.getMovieSummary(imdb, full=True)
            if not item:
                raise Exception()
            if not tmdb or tmdb == '0':
                tmdb = item.get('ids', {}).get('tmdb', '0') or '0'
            title = self.list[i].get('title')
            if not title or title == '0':
                title = item.get('title')
            title = client_utils.replaceHTMLCodes(title)
            originaltitle = self.list[i].get('originaltitle')
            if not originaltitle or originaltitle == '0':
                originaltitle = title
            originaltitle = client_utils.replaceHTMLCodes(originaltitle)
            year = self.list[i].get('year', '0')
            if not year or year == '0':
                year = item.get('year', '0')
            if year and year != '0':
                year = re.compile('(\d{4})').findall(year)[0] or '0'
            else:
                year = '0'
            premiered = self.list[i].get('premiered', '0')
            if not premiered or premiered == '0':
                premiered = item.get('released', '0')
            if premiered and premiered != '0':
                premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            else:
                premiered = '0'
            if self.studio_artwork == 'true':
                studio = trakt.getStudio(imdb, 'movies')
                if studio and studio != []:
                    studio = [x['name'] for x in studio]
                else:
                    studio = []
            else:
                studio = []
            genre = item.get('genres', [])
            if genre and genre != []:
                genre = [x.title() for x in genre]
                #genre = ' / '.join(genre).strip()
            else:
                genre = []
            duration = item.get('runtime', '0')
            if not duration or duration == '0':
                duration = '0'
            rating = item.get('rating', '0')
            if not rating or rating == '0' or rating == '0.0':
                rating = '0'
            votes = item.get('votes', '0')
            #votes = str(format(int(votes), ',d'))
            if not votes or votes == '0':
                votes = '0'
            mpaa = item.get('certification', '0')
            if not mpaa or mpaa == '0':
                mpaa = '0'
            plot = item.get('overview', '0')
            if not plot or plot == '0':
                plot = '0'
            tagline = item.get('tagline', '0')
            if not tagline or tagline == '0':
                tagline = '0'
            people = trakt.getPeople(imdb, 'movies')
            castwiththumb = []
            try:
                r_cast = people.get('cast', [])#[:30]
                for person in r_cast:
                    castwiththumb.append({'name': person['person']['name'], 'role': person['character'], 'thumbnail': ''})
                #castwiththumb = [(person['name'], person['role']) for person in castwiththumb]
            except:
                pass
            if not castwiththumb:
                castwiththumb = []
            try:
                if 'crew' in people and 'directing' in people['crew']:
                    director = [director['person']['name'] for director in people['crew']['directing'] if director['job'].lower() == 'director']
                    #director = ', '.join([director['person']['name'] for director in people['crew']['directing'] if director['job'].lower() == 'director'])
                else:
                    director = []
            except:
                director = []
            try:
                if 'crew' in people and 'writing' in people['crew']:
                    writer = [writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']]
                    #writer = ', '.join([writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']])
                else:
                    writer = []
            except:
                writer = []
            poster, fanart, banner = tmdb_utils.get_tmdb_artwork(tmdb, 'movie')
            if self.hq_artwork == 'true':
                poster2, fanart2, banner, clearlogo, clearart, landscape, discart = self.get_fanart_tv_artwork(tmdb)
            else:
                poster2, fanart2, banner = poster, fanart, banner
                clearlogo = clearart = landscape = discart = '0'
            if self.info_art_source == '1':
                poster = poster2 if not poster2 == '0' else poster
                fanart = fanart2 if not fanart2 == '0' else fanart
            elif self.info_art_source == '2':
                poster = poster2 if not poster2 == '0' else poster
                fanart = fanart2 if not fanart2 == '0' else fanart
            else:
                poster = poster if not poster == '0' else poster2
                fanart = fanart if not fanart == '0' else fanart2
            item = {'title': title, 'originaltitle': originaltitle, 'year': year, 'premiered': premiered, 'imdb': imdb, 'tmdb': tmdb, 'studio': studio, 'genre': genre, 'duration': duration,
                'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 'tagline': tagline, 'castwiththumb': castwiththumb, 'director': director, 'writer': writer,
                'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'discart': discart
            }
            item = dict((k,v) for k, v in six.iteritems(item) if not v == '0')
            self.list[i].update(item)
            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'lang': self.lang, 'item': item}
            self.meta.append(meta)
        except:
            #log_utils.log('trakt_info', 1)
            pass


    def tmdb_info(self, i):
        try:
            if self.list[i]['metacache'] == True:
                return
            imdb = self.list[i]['imdb'] if 'imdb' in self.list[i] else '0'
            tmdb = self.list[i]['tmdb'] if 'tmdb' in self.list[i] else '0'
            if tmdb == '0' and not imdb == '0':
                try:
                    temp_item = tmdb_utils.find_movie_by_external_source(imdb=imdb)
                    tmdb = temp_item.get('id', '0') or '0'
                except:
                    pass
            if tmdb == '0' and not imdb == '0':
                try:
                    temp_item = trakt.getMovieSummary(imdb)
                    tmdb = temp_item.get('ids', {}).get('tmdb', '0') or '0'
                except:
                    pass
            if tmdb == '0' and imdb == '0':
                try:
                    temp_item = trakt.SearchMovie(self.list[i]['title'], self.list[i]['year'])
                    if temp_item[0]['movie']['title'].lower() != self.list[i]['title'].lower() or int(temp_item[0]['movie']['year']) != int(self.list[i]['year']):
                        raise Exception()
                    imdb = temp_item[0]['movie'].get('ids', {}).get('imdb') or '0'
                    tmdb = temp_item[0]['movie'].get('ids', {}).get('tmdb') or '0'
                except:
                    pass
            if not tmdb or tmdb == '0':
                raise Exception()
            url = self.tmdb_info_link % tmdb
            item = client.scrapePage(url, timeout='30').json()
            if not item:
                raise Exception()
            if not imdb or imdb == '0':
                imdb = item.get('imdb_id', '0') or '0'
            title = self.list[i].get('title')
            if not title or title == '0':
                title = item.get('title')
            title = client_utils.replaceHTMLCodes(title)
            originaltitle = self.list[i].get('originaltitle')
            if not originaltitle or originaltitle == '0':
                originaltitle = item.get('original_title')
            originaltitle = client_utils.replaceHTMLCodes(originaltitle)
            year = self.list[i].get('year', '0')
            if not year or year == '0':
                year = item.get('release_date', '0')
            if year and year != '0':
                year = re.compile('(\d{4})').findall(year)[0]
            else:
                year = '0'
            premiered = self.list[i].get('premiered', '0')
            if not premiered or premiered == '0':
                premiered = item.get('release_date', '0')
            if premiered and premiered != '0':
                premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            else:
                premiered = '0'
            if self.studio_artwork == 'true':
                studio = item.get('production_companies', [])
                if studio and studio != []:
                    studio = [x['name'] for x in studio]
                else:
                    studio = []
            else:
                studio = []
            genre = item.get('genres', [])
            if genre and genre != []:
                genre = [x['name'] for x in genre]
                #genre = ' / '.join(genre).strip()
            else:
                genre = []
            duration = item.get('runtime', '0')
            if not duration or duration == '0':
                duration = '0'
            rating = item.get('vote_average', '0')
            if not rating or rating == '0' or rating == '0.0':
                rating = '0'
            votes = item.get('vote_count', '0')
            #votes = str(format(int(votes), ',d'))
            if not votes or votes == '0':
                votes = '0'
            try:
                mpaa = item['releases']['countries']
                mpaa = [x for x in mpaa if not x['certification'] == '']
                mpaa = [x for x in mpaa if str(x['iso_3166_1']) == 'US'][0]['certification']
            except:
                mpaa = '0'
            plot = item.get('overview', '0')
            if not plot or plot == '0':
                plot = '0'
            tagline = item.get('tagline', '0')
            if not tagline or tagline == '0':
                tagline = '0'
            castwiththumb = []
            try:
                r_cast = item['credits']['cast'][:30]
                for person in r_cast:
                    _icon = person.get('profile_path')
                    if self.original_artwork == 'true':
                        icon = self.tmdb_image_link + _icon if _icon else ''
                    else:
                        icon = self.tmdb_image_link % ('185', _icon) if _icon else ''
                    castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
            except:
                pass
            if not castwiththumb:
                castwiththumb = []
            try:
                director = item['credits']['crew']
                director = [x['name'] for x in director if str(x['job']) == 'Director']
                #director = ' / '.join(director).strip()
            except:
                director = []
            try:
                writer = item['credits']['crew']
                writer = [x['name'] for x in writer if str(x['job']) in ['Writer', 'Screenplay']]
                writer = [x for n,x in enumerate(writer) if x not in writer[:n]]
                #writer = ' / '.join(writer).strip()
            except:
                writer = []
            poster = item.get('poster_path', '')
            if poster and poster != '':
                if self.original_artwork == 'true':
                    poster = self.tmdb_image_link + poster
                else:
                    poster = self.tmdb_image_link % ('500', poster)
            else:
                poster = '0'
            fanart = item.get('backdrop_path', '')
            if fanart and fanart != '':
                if self.original_artwork == 'true':
                    fanart = self.tmdb_image_link + fanart
                else:
                    fanart = self.tmdb_image_link % ('1280', fanart)
            else:
                fanart = '0'
            if self.hq_artwork == 'true':
                poster2, fanart2, banner, clearlogo, clearart, landscape, discart = self.get_fanart_tv_artwork(tmdb)
            else:
                poster2, fanart2, banner = tmdb_utils.get_tmdb_artwork(tmdb, 'movie')
                clearlogo = clearart = landscape = discart = '0'
            if self.info_art_source == '1':
                poster = poster2 if not poster2 == '0' else poster
                fanart = fanart2 if not fanart2 == '0' else fanart
            elif self.info_art_source == '2':
                poster = poster2 if not poster2 == '0' else poster
                fanart = fanart2 if not fanart2 == '0' else fanart
            else:
                poster = poster if not poster == '0' else poster2
                fanart = fanart if not fanart == '0' else fanart2
            item = {'title': title, 'originaltitle': originaltitle, 'year': year, 'premiered': premiered, 'imdb': imdb, 'tmdb': tmdb, 'studio': studio, 'genre': genre, 'duration': duration,
                'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 'tagline': tagline, 'castwiththumb': castwiththumb, 'director': director, 'writer': writer,
                'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'discart': discart
            }
            item = dict((k,v) for k, v in six.iteritems(item) if not v == '0')
            self.list[i].update(item)
            meta = {'imdb': imdb, 'tmdb': tmdb, 'tvdb': '0', 'lang': self.lang, 'item': item}
            self.meta.append(meta)
        except:
            #log_utils.log('tmdb_info', 1)
            pass


    def worker(self):
        try:
            self.meta = []
            if self.info_movies_source == '1':
                final_info = self.trakt_info
            else:
                final_info = self.tmdb_info
            total = len(self.list)
            for i in range(0, total):
                self.list[i].update({'metacache': False})
            self.list = metacache.fetch(self.list, self.lang)
            for r in range(0, total, 40):
                threads = []
                for i in range(r, r+40):
                    if i < total:
                        threads.append(workers.Thread(final_info, i))
                [i.start() for i in threads]
                [i.join() for i in threads]
            if self.meta:
                metacache.insert(self.meta)
            #self.list = [i for i in self.list]
        except:
            #log_utils.log('worker', 1)
            pass


    def get(self, url, idx=True, create_directory=True):
        try:
            try:
                url = getattr(self, url + '_link')
            except:
                pass
            try:
                u = urllib_parse.urlparse(url).netloc.lower()
            except:
                pass
            if u in self.tmdb_link and ('/list/' in url or '/collection/' in url):
                if self.addon_caching == 'true':
                    self.list = cache.get(self.tmdb_list, 24, url)
                else:
                    self.list = self.tmdb_list(url)
                self.list = sorted(self.list, key=lambda k: k['year'])
                if idx == True:
                    self.worker()
            elif u in self.tmdb_link and self.tmdb_search_link in url:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.tmdb_list, 1, url)
                else:
                    self.list = self.tmdb_list(url)
                if idx == True:
                    self.worker()
            elif u in self.tmdb_link:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.tmdb_list, 24, url)
                else:
                    self.list = self.tmdb_list(url)
                if idx == True:
                    self.worker()
            elif u in self.trakt_link and '/users/' in url:
                try:
                    if url == self.trakt_history_link:
                        raise Exception()
                    if not '/users/me/' in url:
                        raise Exception()
                    if self.addon_caching != 'true':
                        raise Exception()
                    self.list = cache.get(self.trakt_list, 720, url, self.trakt_user)
                except:
                    self.list = self.trakt_list(url, self.trakt_user)
                if '/users/me/' in url and '/collection/' in url:
                    self.list = sorted(self.list, key=lambda k: k['title'])
                if idx == True:
                    self.worker()
            elif u in self.trakt_link and '/sync/playback/' in url:
                self.list = self.trakt_list(url, self.trakt_user)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=True)
                if idx == True:
                    self.worker()

            elif u in self.trakt_link and '/search/person?query=' in url:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)
                else:
                    self.list = self.trakt_list(url, self.trakt_user)
                if idx == True:
                    self.worker()
            
            elif u in self.trakt_link:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_list, 24, url, self.trakt_user)
                else:
                    self.list = self.trakt_list(url, self.trakt_user)
                if idx == True:
                    self.worker()

            elif u in self.imdb_link and ('/user/' in url or '/list/' in url):
                if self.addon_caching == 'true':
                    self.list = cache.get(self.imdb_list, 1, url)
                else:
                    self.list = self.imdb_list(url)
                if idx == True:
                    self.worker()
            elif u in self.imdb_link:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.imdb_list, 24, url)
                else:
                    self.list = self.imdb_list(url)
                if idx == True:
                    self.worker()

            if idx == True and create_directory == True:
                self.movieDirectory(self.list)
            return self.list
        except:
            #log_utils.log('get', 1)
            pass


    def movieDirectory(self, items):
        if items == None or len(items) == 0:
            control.idle()
            #sys.exit()
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()
        addonFanart = control.addonFanart()
        traktCredentials = trakt.getTraktCredentialsInfo()
        tmdbCredentials = tmdb_utils.getTMDbCredentialsInfo()
        isPlayable = True if not 'plugin' in control.infoLabel('Container.PluginName') else False
        indicators = playcount.getMovieIndicators()#refresh=True) if action == 'movies' else playcount.getMovieIndicators()
        playbackMenu = '[COLOR goldenrod]Free99[/COLOR] Select Source' if control.setting('hosts.mode') == '2' else '[COLOR goldenrod]Free99[/COLOR] Auto Play'
        watchedMenu = '[COLOR goldenrod]Free99[/COLOR] Mark Watched in Trakt' if trakt.getTraktIndicatorsInfo() == True else 'Watched in Free99'
        unwatchedMenu = '[COLOR goldenrod]Free99[/COLOR] Mark Unwatched in Trakt' if trakt.getTraktIndicatorsInfo() == True else 'Unwatched in Free99'
        nextMenu = '[I]Next Page[/I]'
        try:
            favitems = favorites.getFavorites('movie')
            favitems = [i[0] for i in favitems]
        except:
            pass
        for i in items:
            try:
                if 'channel' in i:
                    label = '%s : %s (%s)' % (i['channel'], i['title'], i['year'])
                else:
                    label = '%s (%s)' % (i['title'], i['year'])
                imdb, tmdb, title, year = i['imdb'], i['tmdb'], i['originaltitle'], i['year']
                try:
                    premiered = i['premiered']
                    if premiered == '0' or (int(re.sub('[^0-9]', '', premiered)) > int(re.sub('[^0-9]', '', str(self.today_date)))):
                        label = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, label)
                except:
                    pass
                sysname = urllib_parse.quote_plus('%s (%s)' % (title, year))
                systitle = urllib_parse.quote_plus(title)
                meta = dict((k,v) for k, v in six.iteritems(i) if not v == '0')
                meta.update({'mediatype': 'movie'})
                meta.update({'code': tmdb, 'imdbnumber': imdb, 'imdb_id': imdb, 'tmdb_id': tmdb})
                meta.update({'trailer': '%s?action=trailer&name=%s&tmdb=%s&imdb=%s' % (sysaddon, systitle, tmdb, imdb)})
                if not 'duration' in i:
                    meta.update({'duration': '120'})
                elif i['duration'] == '0':
                    meta.update({'duration': '120'})
                try:
                    meta.update({'duration': str(int(meta['duration']) * 60)})
                except:
                    pass
                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                meta.update({'poster': poster})
                sysmeta = urllib_parse.quote_plus(json.dumps(meta))
                url = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta, self.systime)
                sysurl = urllib_parse.quote_plus(url)
                path = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s' % (sysaddon, systitle, year, imdb, tmdb)
                cm = []
                cm.append(('[COLOR goldenrod]Free99[/COLOR] Find Similar', 'Container.Update(%s?action=movies&url=%s)' % (sysaddon, self.trakt_related_link % imdb)))
                if traktCredentials == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] Trakt Manager', 'RunPlugin(%s?action=trakt_manager&name=%s&imdb=%s&content=movie)' % (sysaddon, sysname, imdb)))
                if tmdbCredentials == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] TMDb Manager', 'RunPlugin(%s?action=tmdb_manager&name=%s&tmdb=%s&content=movie)' % (sysaddon, sysname, tmdb)))
                cm.append(('[COLOR goldenrod]Free99[/COLOR] Add to Library', 'RunPlugin(%s?action=movie_to_library&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, sysname, systitle, year, imdb, tmdb)))
                if action == 'movieFavorites':
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] Remove from Favorites', 'RunPlugin(%s?action=deleteFavorite&meta=%s&content=movie)' % (sysaddon, sysmeta)))
                else:
                    if not imdb in favitems:
                        cm.append(('[COLOR goldenrod]Free99[/COLOR] Add to Favorites', 'RunPlugin(%s?action=addFavorite&meta=%s&content=movie)' % (sysaddon, sysmeta)))
                    else:
                        cm.append(('[COLOR goldenrod]Free99[/COLOR] Remove from Favorites', 'RunPlugin(%s?action=deleteFavorite&meta=%s&content=movie)' % (sysaddon, sysmeta)))
                if kodi_version < 17:
                    cm.append(('Information', 'Action(Info)'))
                try:
                    overlay = int(playcount.getMovieOverlay(indicators, imdb))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=movies_playcount&imdb=%s&query=6)' % (sysaddon, imdb)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=movies_playcount&imdb=%s&query=7)' % (sysaddon, imdb)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass
                cm.append((playbackMenu, 'RunPlugin(%s?action=alter_sources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
                try:
                    item = control.item(label=label, offscreen=True)
                except:
                    item = control.item(label=label)
                art = {}
                art.update({'icon': poster, 'thumb': poster, 'poster': poster})
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                if self.settingFanart == 'true':
                    art.update({'fanart': fanart})
                else:
                    art.update({'fanart': addonFanart})
                if 'banner' in i and not i['banner'] == '0':
                    art.update({'banner': i['banner']})
                else:
                    art.update({'banner': addonBanner})
                if 'clearlogo' in i and not i['clearlogo'] == '0':
                    art.update({'clearlogo': i['clearlogo']})
                if 'clearart' in i and not i['clearart'] == '0':
                    art.update({'clearart': i['clearart']})
                if 'landscape' in i and not i['landscape'] == '0':
                    art.update({'landscape': i['landscape']})
                else:
                    art.update({'landscape': fanart})
                if 'discart' in i and not i['discart'] == '0':
                    art.update({'discart': i['discart']})
                item.setArt(art)
                item.addContextMenuItems(cm)
                if isPlayable:
                    item.setProperty('IsPlayable', 'true')
                offset = bookmarks.get('movie', imdb, '', '', True)
                if float(offset) > 120:
                    percentPlayed = int(float(offset) / float(meta['duration']) * 100)
                    item.setProperty('resumetime', str(offset))
                    item.setProperty('percentplayed', str(percentPlayed))
                ## New Code Starts... Olds Saved Above each line.
                if kodi_version >= 20:
                    info_tag = ListItemInfoTag(item, 'video')
                castwiththumb = i.get('castwiththumb')
                if castwiththumb and not castwiththumb == '0':
                    if kodi_version >= 18:
                        if kodi_version >= 20:
                            info_tag.set_cast(castwiththumb)
                        else:
                            item.setCast(castwiththumb)
                    else:
                        cast = [(p['name'], p['role']) for p in castwiththumb]
                        meta.update({'cast': cast})
                if kodi_version >= 20:
                    info_tag.set_info(control.metadataClean(meta))
                else:
                    item.setInfo(type='Video', infoLabels=control.metadataClean(meta))
                video_streaminfo = {'codec': 'h264'}
                if kodi_version >= 20:
                    info_tag.add_stream_info('video', video_streaminfo)
                else:
                    item.addStreamInfo('video', video_streaminfo)
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
            except:
                #log_utils.log('movieDirectory', 1)
                pass
        try:
            url = items[0]['next']
            if url == '':
                raise Exception()
            icon = control.addonNext()
            url = '%s?action=movies&url=%s' % (sysaddon, urllib_parse.quote_plus(url))
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
        control.sleep(1000)
        views.setView('movies', {'skin.aeon.nox.silvo' : 50, 'skin.estuary': 55, 'skin.confluence': 500}) #View 50 List #View 501 LowList


    def addDirectory(self, items, queue=False):
        if items == None or len(items) == 0:
            control.idle()
            #sys.exit()
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonFanart = control.addonFanart()
        addonThumb = control.addonThumb()
        artPath = control.artPath()
        for i in items:
            try:
                name = i['name']
                if i['image'].startswith('http'):
                    thumb = i['image']
                elif not artPath == None:
                    thumb = os.path.join(artPath, i['image'])
                else:
                    thumb = addonThumb
                url = '%s?action=%s' % (sysaddon, i['action'])
                try:
                    url += '&url=%s' % urllib_parse.quote_plus(i['url'])
                except:
                    pass
                cm = []
                cm.append(('Clean Tools Widget', 'RunPlugin(%s?action=cleantools_widget)' % sysaddon))
                if queue == True:
                    cm.append(('Queue Item', 'RunPlugin(%s?action=queue_item)' % sysaddon))
                try:
                    cm.append(('Add to Library', 'RunPlugin(%s?action=movies_to_library&url=%s)' % (sysaddon, urllib_parse.quote_plus(i['context']))))
                except:
                    pass
                try:
                    item = control.item(label=name, offscreen=True)
                except:
                    item = control.item(label=name)
                poster = i['poster'] if 'poster' in i and not (i['poster'] == '0' or i['poster'] == None) else thumb
                fanart = i['fanart'] if 'fanart' in i and not (i['fanart'] == '0' or i['fanart'] == None) else addonFanart
                item.setArt({'icon': thumb, 'thumb': poster, 'fanart': fanart})
                item.addContextMenuItems(cm)
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                #log_utils.log('addDirectory', 1)
                pass
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)


