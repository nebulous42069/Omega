# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file navigator.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import os,sys

import six
import base64

from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import cache
from resources.lib.modules.crewruntime import c
from datetime import date    

month = int(date.today().strftime('%m'))

sysaddon = sys.argv[0]
syshandle = int(sys.argv[1])

artPath = control.artPath()
addonFanart = control.addonFanart()

imdbCredentials = False if control.setting('imdb.user') == '' else True

traktCredentials = trakt.getTraktCredentialsInfo()

traktIndicators = trakt.getTraktIndicatorsInfo()

queueMenu = six.ensure_str(control.lang(32065))


class navigator:
    def root(self):
        if(control.setting('dev_pw') == six.ensure_text(base64.b64decode(b'dGhlY3Jldw=='))):
            self.addDirectoryItem('Developers', 'developers','dev.png', 'dev.png')
        # if self.getMenuEnabled('navi.holidays') == True:
        #self.addDirectoryItem(90157, 'holidaysNavigator', 'holidays.png', 'holidays.png')
        # if self.getMenuEnabled('navi.halloween') == True:
        #self.addDirectoryItem(90144, 'halloweenNavigator', 'halloween.png', 'halloween.png')
        if not control.setting('navi.movies') == 'false':
            self.addDirectoryItem(32001, 'movieNavigator','main_movies.png', 'DefaultMovies.png')
        if not control.setting('navi.tvshows') == 'false':
            self.addDirectoryItem(32002, 'tvNavigator','main_tvshows.png', 'DefaultTVShows.png')
        if not control.setting('navi.sports') == 'false':
            self.addDirectoryItem(90006, 'bluehat', 'main_bluehat.png', 'DefaultMovies.png')
        if not control.setting('navi.iptv') == 'false':
            self.addDirectoryItem(90007, 'whitehat', 'main_whitehat.png', 'DefaultMovies.png')
        if not control.setting('navi.kidsgrey') == 'false':
            self.addDirectoryItem(90009, 'kidsgreyNavigator', 'main_greyhat.png', 'DefaultTVShows.png')
        if not control.setting('navi.1clicks') == 'false':
            self.addDirectoryItem(90011, 'greenhat', 'main_greenhat.png', 'DefaultMovies.png')
        if not control.setting('navi.purplehat') == 'false':
            self.addDirectoryItem(90189, 'purplehat', 'main_purplehat.png', 'DefaultMovies.png')
        #if not control.setting('navi.standup') == 'false':
            #self.addDirectoryItem(90113, 'redhat', 'main_redhat.png', 'DefaultMovies.png')
        #If not control.setting('navi.fitness') == True:
            #self.addDirectoryItem(90010, 'blackhat', 'main_blackhat.png', 'DefaultMovies.png')
        #if not control.setting('navi.food') == True:
            #self.addDirectoryItem(90143, 'food', 'food.png', 'DefaultMovies.png')
        #if not control.setting('navi.radio') == True:
            #self.addDirectoryItem(90012, 'yellowhat','radio.png', 'radio.png'
        #if not control.setting('navi.add_addons') == 'false':
            #self.addDirectoryItem(90181, 'nav_add_addons', 'add_addon.png', 'DefaultMovies.png')
        adult = True if control.setting('adult_pw') == 'lol' else False
        if adult == True:
            self.addDirectoryItem(90008, 'porn', 'main_pinkhat.png', 'DefaultMovies.png')
        if not control.setting('navi.personal.list') == 'false':
            self.addDirectoryItem(90167, 'plist', 'userlists.png', 'userlists.png')
        if not control.setting('furk.ai') == '':
            self.addDirectoryItem('Furk.net', 'furkNavigator', 'movies.png', 'movies.png')
        self.addDirectoryItem(32008, 'toolNavigator','main_tools.png', 'DefaultAddonProgram.png')
        downloads = True if control.setting('downloads') == 'true' and (len(control.listDir(control.setting('movie.download.path'))[0]) > 0 or len(control.listDir(control.setting('tv.download.path'))[0]) > 0) else False
        if downloads == True:
            self.addDirectoryItem(32009, 'downloadNavigator','downloads.png', 'DefaultFolder.png')
        self.addDirectoryItem(32010, 'searchNavigator','main_search.png', 'DefaultFolder.png')

        self.endDirectory()

    def furk(self):
        self.addDirectoryItem(90001, 'furkUserFiles','mytvnavigator.png', 'mytvnavigator.png')
        self.addDirectoryItem(90002, 'furkSearch', 'search.png', 'search.png')
        self.endDirectory()

    def movies(self, lite=False):
        self.addDirectoryItem(32003, 'mymovieliteNavigator','mymovies.png', 'DefaultVideoPlaylists.png')
        if(control.setting('dev_pw') == six.ensure_text(base64.b64decode(b'dGhlY3Jldw=='))) or (month == 12):
            self.addDirectoryItem(90160, 'movies&url=xristmas', 'holidays.png', 'DefaultMovies.png')
        if not control.setting('navi.moviewidget') == 'false':
            self.addDirectoryItem(32005, 'movieWidget','latest-movies.png', 'DefaultMovies.png')
        if not control.setting('navi.movietheaters') == 'false':
            self.addDirectoryItem(32022, 'movies&url=theaters', 'in-theaters.png', 'DefaultMovies.png')
        if not control.setting('navi.movietrending') == 'false':
            self.addDirectoryItem(32017, 'movies&url=trending', 'people-watching.png', 'DefaultMovies.png')
        if not control.setting('navi.moviepopular') == 'false':
            self.addDirectoryItem(32018, 'movies&url=popular', 'most-popular.png', 'DefaultMovies.png')
        if not control.setting('navi.disneym') == 'false':
            self.addDirectoryItem(90166, 'movies&url=https://api.trakt.tv/users/drew-casteo/lists/disney-movies/items?', 'disney.png', 'disney.png')
        if not control.setting('navi.traktlist') == 'false':
            self.addDirectoryItem(90051, 'traktlist','trakt.png', 'DefaultMovies.png')
        #if not control.setting('navi.imdblist') == 'false':
            #self.addDirectoryItem(90141, 'imdblist', 'imdb_color.png', 'DefaultMovies.png')
        if not control.setting('navi.tvTmdb') == 'false':
            self.addDirectoryItem(90210, 'tmdbmovieslist','tmdb.png', 'DefaultMovies.png')
        #if not control.setting('navi.collections') == 'false':
            #self.addDirectoryItem(32000, 'collectionsNavigator', 'boxsets.png', 'DefaultMovies.png')
        #if not control.setting('navi.movieboxoffice') == 'false':
            #self.addDirectoryItem(32020, 'movies&url=boxoffice', 'box-office.png', 'DefaultMovies.png')
        if not control.setting('navi.movieoscars') == 'false':
            self.addDirectoryItem(32021, 'movies&url=oscars','oscar-winners.png', 'DefaultMovies.png')
        if not control.setting('navi.moviegenre') == 'false':
            self.addDirectoryItem(32011, 'movieGenres','genres.png', 'DefaultMovies.png')
        if not control.setting('navi.movieyears') == 'false':
            self.addDirectoryItem(32012, 'movieYears','years.png', 'DefaultMovies.png')
        if not control.setting('navi.movielanguages') == 'false':
            self.addDirectoryItem(32014, 'movieLanguages','international.png', 'DefaultMovies.png')
        if not control.setting('navi.movieviews') == 'false':
            self.addDirectoryItem(32019, 'movies&url=views','most-voted.png', 'DefaultMovies.png')
        if not control.setting('navi.moviepersons') == 'false':
            self.addDirectoryItem(32013, 'moviePersons','people.png', 'DefaultMovies.png')
        self.addDirectoryItem(32028, 'moviePerson','people-search.png', 'DefaultMovies.png')
        self.addDirectoryItem(32010, 'movieSearch','search.png', 'DefaultMovies.png')

        self.endDirectory()

    def mymovies(self, lite=False):
        self.accountCheck()

        if traktCredentials == True:
            self.addDirectoryItem(90050, 'movies&url=onDeck','trakt.png', 'DefaultMovies.png')
            self.addDirectoryItem(32032, 'movies&url=traktcollection', 'trakt.png', 'DefaultMovies.png',queue=True, context=(32551, 'moviesToLibrary&url=traktcollection'))
            self.addDirectoryItem(32033, 'movies&url=traktwatchlist', 'trakt.png', 'DefaultMovies.png',queue=True, context=(32551, 'moviesToLibrary&url=traktwatchlist'))
            self.addDirectoryItem(32035, 'movies&url=traktfeatured', 'trakt.png', 'DefaultMovies.png', queue=True)


        if traktIndicators == True:
            self.addDirectoryItem(32036, 'movies&url=trakthistory', 'trakt.png', 'DefaultMovies.png', queue=True)

        self.addDirectoryItem(32039, 'movieUserlists','userlists.png', 'DefaultMovies.png')

        if lite == False:
            self.addDirectoryItem(32031, 'movieliteNavigator', 'movies.png', 'DefaultMovies.png')
            self.addDirectoryItem(32028, 'moviePerson','people-search.png', 'DefaultMovies.png')
            self.addDirectoryItem(32010, 'movieSearch','search.png', 'DefaultMovies.png')

        self.endDirectory()

    def tvshows(self, lite=False):
        self.addDirectoryItem(32004, 'mytvliteNavigator','mytvshows.png', 'DefaultVideoPlaylists.png')
        if not control.setting('navi.tvAdded') == 'false':
            self.addDirectoryItem(32006, 'calendar&url=added', 'latest-episodes.png','DefaultRecentlyAddedEpisodes.png', queue=True)
        if not control.setting('navi.tvPremier') == 'false':
            self.addDirectoryItem(32026, 'tvshows&url=premiere', 'new-tvshows.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvAiring') == 'false':
            self.addDirectoryItem(32024, 'tvshows&url=airing', 'airing-today.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvTrending') == 'false':
            self.addDirectoryItem(32017, 'tvshows&url=trending','people-watching2.png', 'DefaultRecentlyAddedEpisodes.png')
        if not control.setting('navi.tvPopular') == 'false':
            self.addDirectoryItem(32018, 'tvshows&url=popular', 'most-popular2.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvTmdb') == 'false':
            self.addDirectoryItem(90210, 'tmdbtvlist','tmdb.png', 'DefaultVideoPlaylists.png')
        if not control.setting('navi.disney') == 'false':
            self.addDirectoryItem(90166, 'tvshows&url=tmdb_networks&tid=2739', 'disney.png', 'disney.png')
        if not control.setting('navi.netflix') == 'false':
            self.addDirectoryItem(90218, 'tvshows&url=tmdb_networks&tid=213', 'netflix.png', 'netflix.png')
        if not control.setting('navi.netflix') == 'false':
            self.addDirectoryItem(90219, 'tvshows&url=tmdb_networks&tid=49', 'hbo.png', 'hbo.png')
        if not control.setting('navi.applet') == 'false':
            self.addDirectoryItem(90170, 'tvshows&url=tmdb_networks&tid=2552', 'apple.png', 'apple.png')
        #self.addDirectoryItem(32700, 'docuNavigator','documentaries.png', 'DefaultMovies.png')
        if not control.setting('navi.tvGenres') == 'false':
            self.addDirectoryItem(32011, 'tvGenres', 'genres2.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvNetworks') == 'false':
            self.addDirectoryItem(32016, 'tvNetworks','networks2.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvRating') == 'false':
            self.addDirectoryItem(32023, 'tvshows&url=rating', 'highly-rated.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvViews') == 'false':
            self.addDirectoryItem(32019, 'tvshows&url=views','most-voted2.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvLanguages') == 'false':
            self.addDirectoryItem(32014, 'tvLanguages','international2.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvActive') == 'false':
            self.addDirectoryItem(32025, 'tvshows&url=active', 'returning-tvshows.png', 'DefaultTVShows.png')
        if not control.setting('navi.tvCalendar') == 'false':
            self.addDirectoryItem(32027, 'calendars', 'calendar2.png', 'DefaultRecentlyAddedEpisodes.png')
        self.addDirectoryItem(32028, 'tvPerson', 'people-search2.png', 'DefaultTVShows.png')
        self.addDirectoryItem(32010, 'tvSearch', 'search2.png', 'DefaultTVShows.png')

        self.endDirectory()

    def mytvshows(self, lite=False):
        try:
            self.accountCheck()

            if traktCredentials == True:
                self.addDirectoryItem(90050, 'calendar&url=onDeck', 'trakt.png', 'DefaultTVShows.png')
                self.addDirectoryItem(32032, 'tvshows&url=traktcollection', 'trakt2.png', 'DefaultTVShows.png', context=(32551, 'tvshowsToLibrary&url=traktcollection'))
                self.addDirectoryItem(32033, 'tvshows&url=traktwatchlist', 'trakt2.png', 'DefaultTVShows.png', context=(32551, 'tvshowsToLibrary&url=traktwatchlist'))
                self.addDirectoryItem(32035, 'tvshows&url=traktfeatured', 'trakt2.png', 'DefaultTVShows.png')

            if traktIndicators == True:
                self.addDirectoryItem(32036, 'calendar&url=trakthistory', 'trakt2.png', 'DefaultTVShows.png', queue=True)
                self.addDirectoryItem(32037, 'calendar&url=progress', 'trakt2.png','DefaultRecentlyAddedEpisodes.png', queue=True)
                self.addDirectoryItem(32038, 'calendar&url=mycalendar','trakt2.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)

            self.addDirectoryItem(32040, 'tvUserlists','userlists2.png', 'DefaultTVShows.png')

            if traktCredentials == True:
                self.addDirectoryItem(32041, 'episodeUserlists', 'userlists2.png', 'DefaultTVShows.png')

            if lite == False:
                self.addDirectoryItem(32031, 'tvliteNavigator', 'tvshows.png', 'DefaultTVShows.png')
                self.addDirectoryItem(32028, 'tvPerson', 'people-search2.png', 'DefaultTVShows.png')
                self.addDirectoryItem(32010, 'tvSearch', 'search2.png', 'DefaultTVShows.png')

            self.endDirectory()
        except Exception as e:
            print("ERROR")
            c.log(f'[Exception @ 230 in navigator.py] Error: {e}')

    def tools(self):
        self.addDirectoryItem(32073, 'authTrakt','trakt.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32609, 'ResolveUrlTorrent','resolveurl.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32043, 'openSettings&query=0.0','tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32628, 'openSettings&query=1.0', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32045, 'openSettings&query=2.0', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32047, 'openSettings&query=4.0', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32044, 'openSettings&query=7.0', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32046, 'openSettings&query=10.0', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32556, 'libraryNavigator','tools.png',' DefaultAddonProgram.png')
        self.addDirectoryItem(32049, 'viewsNavigator','tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32713, 'cachingTools', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32714, 'changelog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)

        self.endDirectory()

    def cachingTools(self):
        self.addDirectoryItem(32050, 'clearSources','tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32604, 'clearCacheSearch','tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32052, 'clearCache','tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32614, 'clearMetaCache','tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem(32613, 'clearAllCache','tools.png', 'DefaultAddonProgram.png')

        self.endDirectory()

    def library(self):
        self.addDirectoryItem(32557, 'openSettings&query=8.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32558, 'updateLibrary&query=tool', 'library_update.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem(32559, control.setting('library.movie'), 'movies.png', 'DefaultMovies.png', isAction=False)
        self.addDirectoryItem(32560, control.setting('library.tv'), 'tvshows.png', 'DefaultTVShows.png', isAction=False)

        if trakt.getTraktCredentialsInfo():
            self.addDirectoryItem(32561, 'moviesToLibrary&url=traktcollection', 'trakt.png', 'DefaultMovies.png', isFolder=False)
            self.addDirectoryItem(32562, 'moviesToLibrary&url=traktwatchlist', 'trakt.png', 'DefaultMovies.png', isFolder=False)
            self.addDirectoryItem(32563, 'tvshowsToLibrary&url=traktcollection', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
            self.addDirectoryItem(32564, 'tvshowsToLibrary&url=traktwatchlist', 'trakt.png', 'DefaultTVShows.png', isFolder=False)

        self.endDirectory()

    def downloads(self):
        movie_downloads = control.setting('movie.download.path')
        tv_downloads = control.setting('tv.download.path')

        if len(control.listDir(movie_downloads)[0]) > 0:
            self.addDirectoryItem(32001, movie_downloads, 'movies.png', 'DefaultMovies.png', isAction=False)
        if len(control.listDir(tv_downloads)[0]) > 0:
            self.addDirectoryItem(32002, tv_downloads, 'tvshows.png', 'DefaultTVShows.png', isAction=False)

        self.endDirectory()

    def search(self):
        self.addDirectoryItem(32001, 'movieSearch','search.png', 'DefaultMovies.png')
        self.addDirectoryItem(32002, 'tvSearch', 'search2.png', 'DefaultTVShows.png')
        self.addDirectoryItem(32029, 'moviePerson','people-search.png', 'DefaultMovies.png')
        self.addDirectoryItem(32030, 'tvPerson', 'people-search2.png', 'DefaultTVShows.png')

        self.endDirectory()

    def views(self):
        try:
            control.idle()

            items = [ (control.lang(32001), 'movies'), (control.lang(32002), 'tvshows'), (control.lang(32105), 'seasons'), (control.lang(32106), 'episodes') ]

            select = control.selectDialog([i[0] for i in items], control.lang(32049))

            if select == -1:
                return

            content = items[select][1]

            title = control.lang(32059)
            url = '%s?action=addView&content=%s' % (sys.argv[0], content)

            poster, banner, fanart = control.addonPoster(), control.addonBanner(), control.addonFanart()

            item = control.item(label=title)
            item.setInfo(type='Video', infoLabels={'title': title})
            item.setArt({'icon': poster, 'thumb': poster,
                         'poster': poster, 'banner': banner})
            item.setProperty('fanart', fanart)

            control.addItem(handle=int(
                sys.argv[1]), url=url, listitem=item, isFolder=False)
            control.content(int(sys.argv[1]), content)
            control.directory(int(sys.argv[1]), cacheToDisc=True)

            from resources.lib.modules import views
            views.setView(content, {})
        except:
            return

    def accountCheck(self):
        if traktCredentials == False and imdbCredentials == False:
            control.idle()
            control.infoDialog(control.lang(32042), sound=True, icon='WARNING')
            sys.exit()


    def infoCheck(self, version):
        try:
            control.infoDialog('', control.lang(32074), time=5000, sound=False)
            return '1'
        except:
            return '1'

    def clearCache(self):

        yes = control.yesnoDialog(control.lang(32084))
        if not yes: 
            return

        cache.cache_clear()
        control.infoDialog(control.lang(32081), sound=True, icon='INFO')

    def clearCacheMeta(self):

        yes = control.yesnoDialog(control.lang(32082))
        if not yes: 
            return

        cache.cache_clear_meta()
        control.infoDialog(control.lang(32083), sound=True, icon='INFO')


    def clearCacheSearch(self):

        yes = control.yesnoDialog(control.lang(32078))
        if not yes: 
            return

        cache.cache_clear_search()
        control.infoDialog(control.lang(32079), sound=True, icon='INFO')

    def clearDebridCheck(self):

        yes = control.yesnoDialog(control.lang(32078))
        if not yes: 
            return

        cache.cache_clear_debrid()
        control.infoDialog(control.lang(32079), sound=True, icon='INFO')

    def clearCacheAll(self):

        yes = control.yesnoDialog(control.lang(32080))
        if not yes: 
            return

        cache.cache_clear_all()
        control.infoDialog(control.lang(32081), sound=True, icon='INFO')


    def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True):
        try: name = control.lang(name)
        except: pass
        
        url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
        thumb = os.path.join(artPath, thumb) if not artPath == None else icon

        cm = []
        if queue == True: 
            cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))
        if not context == None: 
            cm.append((control.lang(context[0]), 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))

        item = control.item(label=name)
        item.addContextMenuItems(cm)
        item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})

        if not addonFanart == None: 
            item.setProperty('fanart', addonFanart)

        control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


    def bluehat(self):
        self.addDirectoryItem(90025, 'nfl', 'nfl.png', 'nfl.png')
        self.addDirectoryItem(90026, 'nhl', 'nhl.png', 'nhl.png')
        self.addDirectoryItem(90027, 'nba', 'nba.png', 'nba.png')
        self.addDirectoryItem(90024, 'mlb', 'mlb.png', 'mlb.png')
        self.addDirectoryItem(90023, 'ncaa', 'ncaa.png', 'ncaa.png')
        self.addDirectoryItem(90156, 'ncaab', 'ncaab.png', 'ncaab.png')
        #self.addDirectoryItem(90193, 'xfl', 'xfl.png', 'xfl.png')
        self.addDirectoryItem(90028, 'ufc', 'ufc.png', 'ufc.png')
        self.addDirectoryItem(90049, 'wwe', 'wwe.png', 'wwe.png')
        self.addDirectoryItem(90115, 'boxing', 'boxing.png', 'boxing.png')
        self.addDirectoryItem(90046, 'fifa', 'fifa.png', 'fifa.png')
        self.addDirectoryItem(90136, 'tennis', 'tennis.png', 'tennis.png')
        self.addDirectoryItem(90047, 'motogp', 'motogp.png', 'motogp.png')
        self.addDirectoryItem(90151, 'f1', 'f1.png', 'f1.png')
        self.addDirectoryItem(90153, 'pga', 'pga.png', 'pga.png')
        self.addDirectoryItem(90154, 'cricket', 'cricket.png', 'cricket.png')
        self.addDirectoryItem(90152, 'nascar', 'nascar.png', 'nascar.png')
        self.addDirectoryItem(90142, 'lfl', 'lfl.png', 'lfl.png')
        self.addDirectoryItem(90114, 'misc_sports','misc_sports.png', 'misc_sports.png')
        self.addDirectoryItem(90031, 'sreplays', 'sports_replays.png', 'sports_replays.png')

        self.endDirectory()

    def imdblist(self):

        self.addDirectoryItem(90085, 'movies&url=top100','movies.png', 'DefaultMovies.png')
        self.addDirectoryItem(90086, 'movies&url=top250','movies.png', 'DefaultMovies.png')
        self.addDirectoryItem(90087, 'movies&url=top1000','movies.png', 'DefaultMovies.png')
        self.addDirectoryItem(90089, 'movies&url=rated_g','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90090, 'movies&url=rated_pg','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90091, 'movies&url=rated_pg13','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90092, 'movies&url=rated_r','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90093, 'movies&url=rated_nc17','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90088, 'movies&url=bestdirector','movies.png', 'DefaultMovies.png')
        self.addDirectoryItem(90094, 'movies&url=national_film_board', 'movies.png', 'DefaultMovies.png')
        self.addDirectoryItem(90100, 'movies&url=dreamworks_pictures', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90095, 'movies&url=fox_pictures','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90096, 'movies&url=paramount_pictures', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90097, 'movies&url=mgm_pictures','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90099, 'movies&url=universal_pictures', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90100, 'movies&url=sony_pictures','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90101, 'movies&url=warnerbrothers_pictures', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90102, 'movies&url=amazon_prime','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90098, 'movies&url=disney_pictures', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90138, 'movies&url=family_movies','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90103, 'movies&url=classic_movies','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90104, 'movies&url=classic_horror','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90105, 'movies&url=classic_fantasy', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90106, 'movies&url=classic_western', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90107, 'movies&url=classic_annimation', 'movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90108, 'movies&url=classic_war','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90109, 'movies&url=classic_scifi','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90110, 'movies&url=eighties','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90111, 'movies&url=nineties','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90112, 'movies&url=thousands','movies.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90139, 'movies&url=twentyten','movies.png', 'DefaultTVShows.png')

        self.endDirectory()


    def tmdbmovieslist(self):
        self.addDirectoryItem(90211, 'movies&url=tmdb_movie_top_rated','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90212, 'movies&url=tmdb_movie_popular','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90215, 'movies&url=tmdb_movie_trending_day','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90216, 'movies&url=tmdb_movie_trending_week','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90217, 'movies&url=tmdb_movie_discover_year','tmdb.png', 'DefaultTVShows.png')

        self.endDirectory()

    def tmdbtvlist(self):
        self.addDirectoryItem(90211, 'tvshows&url=tmdb_tv_top_rated','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90212, 'tvshows&url=tmdb_tv_popular_tv','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90213, 'tvshows&url=tmdb_tv_on_the_air','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90214, 'tvshows&url=tmdb_tv_airing_today','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90215, 'tvshows&url=tmdb_tv_trending_day','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90216, 'tvshows&url=tmdb_tv_trending_week','tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem(90217, 'tvshows&url=tmdb_tv_discover_year','tmdb.png', 'DefaultTVShows.png')

        self.endDirectory()

    def developers(self):
        self.addDirectoryItem('Run Startupmaintenance', 'startupMaintenance','dev.png', 'dev.png')
        self.addDirectoryItem('Set Sizes', 'setSizes','dev.png', 'dev.png')
        self.addDirectoryItem('Update Sizes', 'updateSizes','dev.png', 'dev.png')

        self.endDirectory()


    def holidays(self):
        self.addDirectoryItem(90161, 'movies&url=top50_holiday', 'holidays.png', 'holidays.png')
        self.addDirectoryItem(90162, 'movies&url=best_holiday','holidays.png', 'holidays.png')
        self.addDirectoryItem(90158, 'movies&url=https://api.trakt.tv/users/movistapp/lists/christmas-movies/items?', 'holidays.png', 'holidays.png')
        self.addDirectoryItem(90159, 'movies&url=https://api.trakt.tv/users/cjcope/lists/hallmark-christmas/items?', 'holidays.png', 'holidays.png')
        self.addDirectoryItem(90160, 'movies&url=https://api.trakt.tv/users/mkadam68/lists/christmas-list/items?', 'holidays.png', 'holidays.png')

        self.endDirectory()

    def halloween(self):
        self.addDirectoryItem(90146, 'movies&url=halloween_imdb', 'halloween.png', 'halloween.png')
        self.addDirectoryItem(90147, 'movies&url=halloween_top_100', 'halloween.png', 'halloween.png')
        self.addDirectoryItem(90148, 'movies&url=halloween_best', 'halloween.png', 'halloween.png')
        self.addDirectoryItem(90149, 'movies&url=halloween_great', 'halloween.png', 'halloween.png')
        self.addDirectoryItem(90145, 'movies&url=https://api.trakt.tv/users/petermesh/lists/halloween-movies/items?', 'halloween.png', 'halloween.png')

        self.endDirectory()

    def traktlist(self):
        self.addDirectoryItem(90041, 'movies&url=https://api.trakt.tv/users/giladg/lists/latest-releases/items?', 'fhd_releases.png', 'DefaultMovies.png')
        self.addDirectoryItem(90042, 'movies&url=https://api.trakt.tv/users/giladg/lists/latest-4k-releases/items?', '4k_releases.png', 'DefaultMovies.png')
        self.addDirectoryItem(90043, 'movies&url=https://api.trakt.tv/users/giladg/lists/top-10-movies-of-the-week/items?', 'top_10.png', 'DefaultMovies.png')
        self.addDirectoryItem(90044, 'movies&url=https://api.trakt.tv/users/giladg/lists/academy-award-for-best-cinematography/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90045, 'movies&url=https://api.trakt.tv/users/giladg/lists/stand-up-comedy/items?', 'standup.png', 'DefaultMovies.png')
        #self.addDirectoryItem(90052, 'movies&url=https://api.trakt.tv/users/daz280982/lists/movie-boxsets/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90053, 'movies&url=https://api.trakt.tv/users/movistapp/lists/action/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90054, 'movies&url=https://api.trakt.tv/users/movistapp/lists/adventure/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90055, 'movies&url=https://api.trakt.tv/users/movistapp/lists/animation/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90056, 'movies&url=https://api.trakt.tv/users/ljransom/lists/comedy-movies/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90057, 'movies&url=https://api.trakt.tv/users/movistapp/lists/crime/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90058, 'movies&url=https://api.trakt.tv/users/movistapp/lists/drama/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90059, 'movies&url=https://api.trakt.tv/users/movistapp/lists/family/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(32036, 'movies&url=https://api.trakt.tv/users/movistapp/lists/history/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90061, 'movies&url=https://api.trakt.tv/users/movistapp/lists/horror/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90062, 'movies&url=https://api.trakt.tv/users/movistapp/lists/music/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90063, 'movies&url=https://api.trakt.tv/users/movistapp/lists/mystery/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90064, 'movies&url=https://api.trakt.tv/users/movistapp/lists/romance/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90065, 'movies&url=https://api.trakt.tv/users/movistapp/lists/science-fiction/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90066, 'movies&url=https://api.trakt.tv/users/movistapp/lists/thriller/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90067, 'movies&url=https://api.trakt.tv/users/movistapp/lists/war/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90068, 'movies&url=https://api.trakt.tv/users/movistapp/lists/western/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90069, 'movies&url=https://api.trakt.tv/users/movistapp/lists/marvel/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90070, 'movies&url=https://api.trakt.tv/users/movistapp/lists/walt-disney-animated-feature-films/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90071, 'movies&url=https://api.trakt.tv/users/movistapp/lists/batman/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90072, 'movies&url=https://api.trakt.tv/users/movistapp/lists/superman/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90073, 'movies&url=https://api.trakt.tv/users/movistapp/lists/star-wars/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90074, 'movies&url=https://api.trakt.tv/users/movistapp/lists/007/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90075, 'movies&url=https://api.trakt.tv/users/movistapp/lists/pixar-animation-studios/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90076, 'movies&url=https://api.trakt.tv/users/movistapp/lists/quentin-tarantino-collection/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90077, 'movies&url=https://api.trakt.tv/users/movistapp/lists/rocky/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90078, 'movies&url=https://api.trakt.tv/users/movistapp/lists/dreamworks-animation/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90079, 'movies&url=https://api.trakt.tv/users/movistapp/lists/dc-comics/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90080, 'movies&url=https://api.trakt.tv/users/movistapp/lists/the-30-best-romantic-comedies-of-all-time/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90081, 'movies&url=https://api.trakt.tv/users/movistapp/lists/88th-academy-awards-winners/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90082, 'movies&url=https://api.trakt.tv/users/movistapp/lists/most-sexy-movies/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90083, 'movies&url=https://api.trakt.tv/users/movistapp/lists/dance-movies/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem(90084, 'movies&url=https://api.trakt.tv/users/movistapp/lists/halloween-movies/items?', 'trakt.png', 'DefaultMovies.png')

        self.endDirectory()


    def kidsgrey(self, lite=False):
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]Debrid Kids[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'debridkids', 'debrid_kids.png', 'DefaultMovies.png')
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]Kids Trending[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'movies&url=advancedsearchtrending', 'kids_trending.png', 'DefaultMovies.png')
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]Action Hero[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'movies&url=collectionsactionhero', 'action_hero.png', 'DefaultMovies.png')
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]DC vs Marvel[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'movies&url=advancedsearchdcvsmarvel', 'dc_marvel.png', 'DefaultMovies.png')
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]Walt Disney[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'waltdisney', 'walt_disney.png', 'DefaultMovies.png')
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]Learning TV[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'learning', 'learning_tv.png', 'DefaultMovies.png')
        self.addDirectoryItem('[COLOR orchid]¤ [/COLOR] [B][COLOR white]Kids Songs[/COLOR][/B] [COLOR orchid] ¤[/COLOR]', 'songs', 'kids_songs.png', 'DefaultMovies.png')

        self.endDirectory()

#cm-changed cacheToDisc v1.2.0 bool
    def endDirectory(self, cacheToDisc=True):
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc)

