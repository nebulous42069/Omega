# -*- coding: utf-8 -*-

import os
import sys

from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import tmdb_utils
from resources.lib.modules import log_utils

try:
    #from infotagger.listitem import ListItemInfoTag
    from resources.lib.modules.listitem import ListItemInfoTag
except:
    pass

sysaddon = sys.argv[0]
syshandle = int(sys.argv[1])
control.moderator()

imdbCredentials = False if control.setting('imdb.user') == '' else True
tmdbCredentials = tmdb_utils.getTMDbCredentialsInfo()
traktCredentials = trakt.getTraktCredentialsInfo()
traktIndicators = trakt.getTraktIndicatorsInfo()

kodi_version = control.getKodiVersion()


class navigator:
    def root(self):
        self.addDirectoryItem('Browse Movies', 'movies_menu', 'movies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Browse TV Shows', 'tvshows_menu', 'tvshows.png', 'DefaultTVShows.png')           
        self.addDirectoryItem('Tools', 'tools_menu', 'tools.png', 'DefaultAddonProgram.png')
        if not control.setting('dev.widget') == 'false':
            self.addDirectoryItem('Dev Tools', 'devtools_menu', 'tools.png', 'DefaultAddonProgram.png')
        self.endDirectory(cached=False)


    def episode_widget(self):
        widgetChoice = 'Episodes (Widget) [I]- %s[/I]'
        if traktIndicators == True:
            setting = control.setting('episode.widget.alt')
        else:
            setting = control.setting('episode.widget')
        if setting == '1':
            return widgetChoice % 'TVmaze Calendar'
        elif setting == '2':
            return widgetChoice % 'TVmaze Episodes'
        elif setting == '3':
            return widgetChoice % 'Trakt Progress'
        elif setting == '4':
            return widgetChoice % 'Trakt Episodes'
        else:
            return 'Disabled'



    def movies(self):
        self.addDirectoryItem('Your Trakt And Library', 'my_movies_menu', 'mymovies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Free99 Movie Favorites', 'movieFavorites', 'icon.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Search...', 'search_movies_menu', 'search.png', 'DefaultFolder.png')    
        self.addDirectoryItem('Movie Genres', 'movies_tmdb_genres', 'genres.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Trending Today On Trakt', 'movies&url=trakt_trending', 'people-watching.png', 'DefaultMovies.png')                      
        self.addDirectoryItem('Latest Releases By Giladg', 'movies&url=https://api.trakt.tv/users/giladg/lists/latest-releases/items?', 'trakt.png', 'DefaultMovies.png')         
        self.addDirectoryItem('Most Popular Movies', 'movies&url=trakt_popular', 'most-popular.png', 'DefaultMovies.png')
        self.addDirectoryItem('In Theatres Now', 'movies&url=tmdb_in_theatres', 'latest-movies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Premieres', 'movies&url=tmdb_premiere', 'latest-movies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Top Rated Movies', 'movies&url=tmdb_toprated', 'highly-rated.png', 'DefaultMovies.png')
        self.addDirectoryItem('Movie Boxsets', 'movies_tmdb_collections_menu', 'tmdb.png', 'DefaultVideoPlaylists.png')
        self.addDirectoryItem('Browse IMDb User Lists', 'movies_imdb_userlists', 'imdb.png', 'DefaultVideoPlaylists.png')        
        self.addDirectoryItem('Browse Trakt User Lists', 'movies_trakt_moviemosts', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Browse TMDB User Lists', 'movies_tmdb_userlists_menu', 'tmdb.png', 'DefaultVideoPlaylists.png')        
        self.addDirectoryItem('Upcoming Movies', 'movies&url=tmdb_upcoming', 'highly-rated.png', 'DefaultMovies.png')  
        self.addDirectoryItem('Popular People', 'movies_tmdb_popular_people', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Movies By Year', 'movies_tmdb_years', 'years.png', 'DefaultMovies.png')
        self.addDirectoryItem('Movies By Decade', 'movies_tmdb_decades', 'years.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Sort By Age Ratings', 'movies_tmdb_certifications', 'certificates.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Languages', 'movies_tmdb_languages', 'languages.png', 'DefaultMovies.png')        
        self.endDirectory()


    def tvshows(self):
        self.addDirectoryItem('Your Trakt And Library', 'my_tvshows_menu', 'mytvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Free99 TV Show Favorites', 'tvFavorites', 'highly-rated.png', 'DefaultTVShows.png')        
        self.addDirectoryItem('Search...', 'search_tvshows_menu', 'search.png', 'DefaultFolder.png')
        self.addDirectoryItem('TV Genres', 'tvshows_tmdb_genres', 'genres.png', 'DefaultTVShows.png')
        self.addDirectoryItem('TV Networks', 'tvshows_tmdb_networks', 'networks.png', 'DefaultTVShows.png')        
        self.addDirectoryItem('Trending On Trakt', 'tvshows&url=trakt_trending', 'people-watching.png', 'DefaultTVShows.png') 
        self.addDirectoryItem('Popular On Trakt', 'tvshows&url=trakt_popular', 'most-popular.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Popular On TMDB', 'tvshows&url=tmdb_popular', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Featured On TMDB', 'tvshows&url=tmdb_featured', 'featured.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Featured On Trakt', 'tvshows&url=trakt_featured', 'featured.png', 'DefaultTVShows.png')        
        self.addDirectoryItem('Currently Airing', 'tvshows&url=tmdb_active', 'returning-tvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Trakt TV Show Mosts', 'tvshows_trakt_showmosts', 'trakt.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Top Rated TV Shows', 'tvshows&url=tmdb_toprated', 'highly-rated.png', 'DefaultTVShows.png')
        self.addDirectoryItem('IMDb User Lists', 'tvshows_imdb_userlists', 'imdb.png', 'DefaultVideoPlaylists.png')
        self.addDirectoryItem('TMDB User Lists', 'tvshows_tmdb_userlists_menu', 'tmdb.png', 'DefaultVideoPlaylists.png')        
        self.addDirectoryItem('TV Calendar', 'calendars', 'calendar.png', 'DefaultRecentlyAddedEpisodes.png')
        self.addDirectoryItem('Streaming Services', 'tvshows_tvmaze_webchannels', 'networks.png', 'DefaultTVShows.png')
        self.addDirectoryItem('TV Shows By Year', 'tvshows_tmdb_years', 'years.png', 'DefaultTVShows.png')
        self.addDirectoryItem('TV Shows By Decade', 'tvshows_tmdb_decades', 'years.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Popular People', 'tvshows_tmdb_popular_people', 'tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Popular Companies', 'tvshows_tmdb_popular_companies', 'tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Popular Keywords', 'tvshows_tmdb_popular_keywords', 'tmdb.png', 'DefaultTVShows.png')        
        self.addDirectoryItem('Languages', 'tvshows_tmdb_languages', 'languages.png', 'DefaultTVShows.png')        
        self.endDirectory()


    def movieTrakt(self):
        self.addDirectoryItem('Most Popular', 'movies&url=trakt_popular', 'most-popular.png', 'DefaultMovies.png')
        self.addDirectoryItem('Featured', 'movies&url=trakt_featured', 'featured.png', 'DefaultMovies.png')
        self.addDirectoryItem('Box Office', 'movies&url=trakt_boxoffice', 'box-office.png', 'DefaultMovies.png')
        self.addDirectoryItem('Trending', 'movies&url=trakt_trending', 'people-watching.png', 'DefaultMovies.png')
        self.addDirectoryItem('Anticipated', 'movies&url=trakt_anticipated', 'latest-movies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Movie Mosts', 'movies_trakt_moviemosts', 'trakt.png', 'DefaultMovies.png')
        self.endDirectory()


    def tvTrakt(self):
        self.addDirectoryItem('Most Popular', 'tvshows&url=trakt_popular', 'most-popular.png', 'DefaultMovies.png')
        self.addDirectoryItem('Featured', 'tvshows&url=trakt_featured', 'featured.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Trending', 'tvshows&url=trakt_trending', 'people-watching.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Anticipated', 'tvshows&url=trakt_anticipated', 'new-tvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Premiere', 'tvshows&url=trakt_premieres', 'new-tvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem('TV Show Mosts', 'tvshows_trakt_showmosts', 'trakt.png', 'DefaultTVShows.png')
        self.endDirectory()


    def imdbMovieLists(self):
        self.addDirectoryItem('Explore Keywords', 'movies_imdb_keywords', 'imdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Explore UserLists', 'movies_imdb_userlists', 'imdb.png', 'DefaultMovies.png')
        self.endDirectory()


    def imdbShowLists(self):
        self.addDirectoryItem('Explore Keywords', 'tvshows_imdb_keywords', 'imdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Explore UserLists', 'tvshows_imdb_userlists', 'imdb.png', 'DefaultTVShows.png')
        self.endDirectory()


    def tmdbMovieCollections(self):
        self.addDirectoryItem('Collections List: All', 'movies_tmdb_collections&url=all', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Alphabetical', 'movies_tmdb_collections_alphabetical_menu', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Genres', 'movies_tmdb_collections_genres_menu', 'tmdb.png', 'DefaultMovies.png')
        self.endDirectory()


    def tmdbMovieCollectionsAlphabetical(self):
        self.addDirectoryItem('Collections List: 1 (#-Am)', 'movies_tmdb_collections&url=page1', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 2 (Am-Be)', 'movies_tmdb_collections&url=page2', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 3 (Be-Ch)', 'movies_tmdb_collections&url=page3', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 4 (Ch-De)', 'movies_tmdb_collections&url=page4', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 5 (De-Es)', 'movies_tmdb_collections&url=page5', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 6 (Es-Gi)', 'movies_tmdb_collections&url=page6', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 7 (Gl-Ho)', 'movies_tmdb_collections&url=page7', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 8 (Ho-Ki)', 'movies_tmdb_collections&url=page8', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 9 (Ki-Ma)', 'movies_tmdb_collections&url=page9', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 10 (Mc-Ni)', 'movies_tmdb_collections&url=page10', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 11 (Ni-Ps)', 'movies_tmdb_collections&url=page11', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 12 (Pu-Se)', 'movies_tmdb_collections&url=page12', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 13 (Se-St)', 'movies_tmdb_collections&url=page13', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 14 (St-Th)', 'movies_tmdb_collections&url=page14', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 15 (Th-Th)', 'movies_tmdb_collections&url=page15', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 16 (Th-Th)', 'movies_tmdb_collections&url=page16', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 17 (Th-Un)', 'movies_tmdb_collections&url=page17', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: 18 (Un-Zu)', 'movies_tmdb_collections&url=page18', 'tmdb.png', 'DefaultMovies.png')
        self.endDirectory()


    def tmdbMovieCollectionsGenres(self):
        self.addDirectoryItem('Collections List: Action', 'movies_tmdb_collections_genres&url=Action', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Adventure', 'movies_tmdb_collections_genres&url=Adventure', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Animation', 'movies_tmdb_collections_genres&url=Animation', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Comedy', 'movies_tmdb_collections_genres&url=Comedy', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Crime', 'movies_tmdb_collections_genres&url=Crime', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Documentary', 'movies_tmdb_collections_genres&url=Documentary', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Drama', 'movies_tmdb_collections_genres&url=Drama', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Family', 'movies_tmdb_collections_genres&url=Family', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Fantasy', 'movies_tmdb_collections_genres&url=Fantasy', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: History', 'movies_tmdb_collections_genres&url=History', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Horror', 'movies_tmdb_collections_genres&url=Horror', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Music', 'movies_tmdb_collections_genres&url=Music', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Mystery', 'movies_tmdb_collections_genres&url=Mystery', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Romance', 'movies_tmdb_collections_genres&url=Romance', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Science Fiction', 'movies_tmdb_collections_genres&url=Science Fiction', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: TV Movie', 'movies_tmdb_collections_genres&url=TV Movie', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Thriller', 'movies_tmdb_collections_genres&url=Thriller', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: War', 'movies_tmdb_collections_genres&url=War', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections List: Western', 'movies_tmdb_collections_genres&url=Western', 'tmdb.png', 'DefaultMovies.png')
        self.endDirectory()


    def tmdbMovieLists(self):
        self.addDirectoryItem('Assortment of Lists', 'movies_tmdb_userlists&url=tmdbAssortment', 'tmdb.png', 'DefaultMovies.png')    
        self.addDirectoryItem('Actor Collections', 'movies_tmdb_userlists&url=tmdbActorCollections', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Holidays', 'movies_tmdb_userlists&url=tmdbHolidays', 'tmdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('Boxset Collections', 'movies_tmdb_userlists&url=tmdbCollections', 'tmdb.png', 'DefaultMovies.png')
        self.endDirectory()


    def tmdbShowLists(self):
        self.addDirectoryItem('TV Show Lists', 'tvshows_tmdb_userlists', 'tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Hulu Originals', 'tvshows&url=tmdb_huluorig', 'tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Netflix Originals', 'tvshows&url=tmdb_netflixorig', 'tmdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Amazon Originals', 'tvshows&url=tmdb_amazonorig', 'tmdb.png', 'DefaultTVShows.png')
        self.endDirectory()


    def movieMosts(self):
        self.addDirectoryItem('Latest Releases', 'movies&url=https://api.trakt.tv/users/giladg/lists/latest-releases/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Academy Award Winners', 'movies&url=https://api.trakt.tv/users/movistapp/lists/88th-academy-awards-winners/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Best Action Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/action/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Adventure Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/adventure/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Animated Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/animation/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Cinematography', 'movies&url=https://api.trakt.tv/users/giladg/lists/academy-award-for-best-cinematography/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Best Comedy Movies', 'movies&url=https://api.trakt.tv/users/ljransom/lists/comedy-movies/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Crime Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/crime/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Dance Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/dance-movies/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Best Drama Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/drama/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Family Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/family/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best History Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/history/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Halloween Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/halloween-movies/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Best Horror Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/horror/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Music Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/music/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Mystery Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/mystery/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Romance Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/romance/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Romantic Comedy Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/the-30-best-romantic-comedies-of-all-time/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Best Sci-Fi Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/science-fiction/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Thriller Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/thriller/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best War Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/war/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Best Western Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/western/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Kids Dreamworks Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/dreamworks-animation/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Kids Pixar Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/pixar-animation-studios/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Kids Walt Disney Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/walt-disney-animated-feature-films/items?', 'trakt.png', 'DefaultMovies.png')        
        self.addDirectoryItem('Marvel Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/marvel/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Batman Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/batman/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Superman Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/superman/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Star Wars Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/star-wars/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('007 Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/007/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Quentin Tarantino Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/quentin-tarantino-collection/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Rocky Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/rocky/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('DC Comics Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/dc-comics/items?', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Most Sexy Movies', 'movies&url=https://api.trakt.tv/users/movistapp/lists/most-sexy-movies/items?', 'trakt.png', 'DefaultMovies.png')        
        self.endDirectory()


    def showMosts(self):
        self.addDirectoryItem('Most Played This Week', 'tvshows&url=trakt_played1', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Played This Month', 'tvshows&url=trakt_played2', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Played This Year', 'tvshows&url=trakt_played3', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Played All Time', 'tvshows&url=trakt_played4', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Collected This Week', 'tvshows&url=trakt_collected1', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Collected This Month', 'tvshows&url=trakt_collected2', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Collected This Year', 'tvshows&url=trakt_collected3', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Collected All Time', 'tvshows&url=trakt_collected4', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Watched This Week', 'tvshows&url=trakt_watched1', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Watched This Month', 'tvshows&url=trakt_watched2', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Watched This Year', 'tvshows&url=trakt_watched3', 'most-popular.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Most Watched All Time', 'tvshows&url=trakt_watched4', 'most-popular.png', 'DefaultTVShows.png')
        self.endDirectory()


    def tvTVmaze(self):
        self.addDirectoryItem('New Episodes', 'calendar&url=tvmaze_added', 'latest-episodes.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
        self.addDirectoryItem('TV Calendar', 'calendars', 'calendar.png', 'DefaultRecentlyAddedEpisodes.png')
        self.addDirectoryItem('Networks', 'tvshows_tvmaze_networks', 'networks.png', 'DefaultTVShows.png')
        self.addDirectoryItem('WebChannels', 'tvshows_tvmaze_webchannels', 'networks.png', 'DefaultTVShows.png')
        self.endDirectory()


    def mymovies(self):
        if traktCredentials == True:
            self.addDirectoryItem('Trakt Movie Collection', 'movies&url=trakt_collection', 'trakt.png', 'DefaultMovies.png', queue=True, context=('Add to Library', 'movies_to_library&url=trakt_collection'))
            self.addDirectoryItem('Trakt Watchlist', 'movies&url=trakt_watchlist', 'trakt.png', 'DefaultMovies.png', queue=True, context=('Add to Library', 'movies_to_library&url=trakt_watchlist'))
        if traktIndicators == True:
            self.addDirectoryItem('History', 'movies&url=trakt_history', 'trakt.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem('OnDeck', 'movies&url=trakt_ondeck', 'trakt.png', 'DefaultMovies.png', queue=True)
        self.addDirectoryItem('Your Trakt UserLists', 'movies_userlists_trakt', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Your Trakt Liked UserLists', 'movies_userlists_trakt_liked', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Your Kodi Movie Library', 'library_menu', 'mymovies.png', 'DefaultAddonProgram.png')
        self.endDirectory()


    def mytvshows(self):
        if traktCredentials == True:
            self.addDirectoryItem('Trakt TV Show Collection', 'tvshows&url=trakt_collection', 'trakt.png', 'DefaultTVShows.png', context=('Add to Library', 'tvshows_to_library&url=trakt_collection'))
            self.addDirectoryItem('Trakt Watchlist', 'tvshows&url=trakt_watchlist', 'trakt.png', 'DefaultTVShows.png', context=('Add to Library', 'tvshows_to_library&url=trakt_watchlist'))
        if traktIndicators == True:
            self.addDirectoryItem('In Progress TV Shows', 'calendar&url=trakt_progress', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem('Next Episodes', 'calendar&url=trakt_mycalendar', 'trakt.png', 'DefaultRecentlyAddedEpisodes.png', queue=True)
            self.addDirectoryItem('History', 'calendar&url=trakt_history', 'trakt.png', 'DefaultTVShows.png', queue=True)
            self.addDirectoryItem('OnDeck', 'calendar&url=trakt_ondeck', 'trakt.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Your Trakt UserLists', 'tvshows_userlists_trakt', 'trakt.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Your Trakt Liked UserLists', 'tvshows_userlists_trakt_liked', 'trakt.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Your Kodi TV Show Library', 'library_menu', 'mytvshows.png', 'DefaultAddonProgram.png')
        self.endDirectory()


    def myimdb(self):
        self.addDirectoryItem('My IMDb Movies', 'my_imdb_movies_menu', 'imdb.png', 'DefaultSets.png')
        self.addDirectoryItem('My IMDb TV Shows', 'my_imdb_tvshows_menu', 'imdb.png', 'DefaultSets.png')
        self.endDirectory()


    def myimdbmovies(self):
        if imdbCredentials == True:
            if control.setting('imdb.sort.order') == '1':
                self.addDirectoryItem('Watchlist', 'movies&url=imdb_watchlist2', 'imdb.png', 'DefaultMovies.png', queue=True)
            else:
                self.addDirectoryItem('Watchlist', 'movies&url=imdb_watchlist', 'imdb.png', 'DefaultMovies.png', queue=True)
        self.endDirectory()


    def myimdbtvshows(self):
        if imdbCredentials == True:
            if control.setting('imdb.sort.order') == '1':
                self.addDirectoryItem('Watchlist', 'tvshows&url=imdb_watchlist2', 'imdb.png', 'DefaultTVShows.png')
            else:
                self.addDirectoryItem('Watchlist', 'tvshows&url=imdb_watchlist', 'imdb.png', 'DefaultTVShows.png')
        self.endDirectory()


    def mytmdb(self):
        self.addDirectoryItem('My TMDb Movies', 'my_tmdb_movies_menu', 'tmdb.png', 'DefaultSets.png')
        self.addDirectoryItem('My TMDb TV Shows', 'my_tmdb_tvshows_menu', 'tmdb.png', 'DefaultSets.png')
        self.endDirectory()


    def mytmdbmovies(self):
        if tmdbCredentials == True:
            self.addDirectoryItem('Favorites', 'movies&url=tmdb_favorites', 'tmdb.png', 'DefaultMovies.png', queue=True)
            self.addDirectoryItem('Watchlist', 'movies&url=tmdb_watchlist', 'tmdb.png', 'DefaultMovies.png', queue=True)
        self.endDirectory()


    def mytmdbtvshows(self):
        if tmdbCredentials == True:
            self.addDirectoryItem('Favorites', 'tvshows&url=tmdb_favorites', 'tmdb.png', 'DefaultTVShows.png')
            self.addDirectoryItem('Watchlist', 'tvshows&url=tmdb_watchlist', 'tmdb.png', 'DefaultTVShows.png')
        self.endDirectory()


    def myuserlists(self):
        self.addDirectoryItem('Movie UserLists', 'my_userlists_movies_menu', 'mymovies.png', 'DefaultMovies.png')
        self.addDirectoryItem('TV Show UserLists', 'my_userlists_tvshows_menu', 'mytvshows.png', 'DefaultTVShows.png')
        #self.addDirectoryItem('Episode UserLists', 'episodes_userlists', 'mytvshows.png', 'DefaultTVShows.png')
        self.endDirectory()


    def myuserlistsmovies(self):
        self.addDirectoryItem('Trakt UserLists', 'movies_userlists_trakt', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('Trakt Liked UserLists', 'movies_userlists_trakt_liked', 'trakt.png', 'DefaultMovies.png')
        self.addDirectoryItem('IMDb UserLists', 'movies_userlists_imdb', 'imdb.png', 'DefaultMovies.png')
        self.addDirectoryItem('TMDb UserLists', 'movies_userlists_tmdb', 'tmdb.png', 'DefaultMovies.png')
        self.endDirectory()


    def myuserliststvshows(self):
        self.addDirectoryItem('Trakt UserLists', 'tvshows_userlists_trakt', 'trakt.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Trakt Liked UserLists', 'tvshows_userlists_trakt_liked', 'trakt.png', 'DefaultTVShows.png')
        self.addDirectoryItem('IMDb UserLists', 'tvshows_userlists_imdb', 'imdb.png', 'DefaultTVShows.png')
        self.addDirectoryItem('TMDb UserLists', 'tvshows_userlists_tmdb', 'tmdb.png', 'DefaultTVShows.png')
        self.endDirectory()


    def search_setting_widget(self, the_setting):
        setting = control.setting(the_setting) or '0'
        if setting == '1':
            return 'IMDb'
        elif setting == '2':
            return 'Trakt'
        else:
            return 'TMDb'


    def search_movies(self):
        movies_setting_label = self.search_setting_widget('search.movies.source')
        self.addDirectoryItem('Movies (%s)' % movies_setting_label, 'movies_search&select=movies', 'search.png', 'DefaultMovies.png')
        people_setting_label = self.search_setting_widget('search.people.source')
        self.addDirectoryItem('People (%s)' % people_setting_label, 'movies_search&select=people', 'people-search.png', 'DefaultMovies.png')
        keywords_setting_label = self.search_setting_widget('search.keywords.source')
        self.addDirectoryItem('Keywords (%s)' % keywords_setting_label, 'movies_search&select=keywords', 'search.png', 'DefaultMovies.png')
        self.addDirectoryItem('Companies (TMDb)', 'movies_search&select=companies', 'search.png', 'DefaultMovies.png')
        self.addDirectoryItem('Collections (TMDb)', 'movies_search&select=collections', 'search.png', 'DefaultMovies.png')
        self.endDirectory()


    def search_tvshows(self):
        tvshows_setting_label = self.search_setting_widget('search.tvshows.source')
        self.addDirectoryItem('TV Shows (%s)' % tvshows_setting_label, 'tvshows_search&select=tvshow', 'search.png', 'DefaultTVShows.png')
        people_setting_label = self.search_setting_widget('search.people.source')
        self.addDirectoryItem('People (%s)' % people_setting_label, 'tvshows_search&select=people', 'people-search.png', 'DefaultTVShows.png')
        keywords_setting_label = self.search_setting_widget('search.keywords.source')
        self.addDirectoryItem('Keywords (%s)' % keywords_setting_label, 'tvshows_search&select=keywords', 'search.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Companies (TMDb)', 'tvshows_search&select=companies', 'search.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Collections (TMDb)', 'tvshows_search&select=collections', 'search.png', 'DefaultTVShows.png')
        self.endDirectory()


    def favorites(self):
        self.addDirectoryItem('Movie Favorites', 'movieFavorites', 'highly-rated.png', 'DefaultMovies.png')
        self.addDirectoryItem('TV Show Favorites', 'tvFavorites', 'highly-rated.png', 'DefaultTVShows.png')
        self.endDirectory()


    def library(self):
        movie_library = control.setting('library.movie')
        if len(control.listDir(movie_library)[0]) > 0:
            self.addDirectoryItem('Library Movie Folder', movie_library, 'movies.png', 'DefaultMovies.png', isAction=False)
        tv_library = control.setting('library.tv')
        if len(control.listDir(tv_library)[0]) > 0:
            self.addDirectoryItem('Library TV Show Folder', tv_library, 'tvshows.png', 'DefaultTVShows.png', isAction=False)
        self.addDirectoryItem('Library Settings', 'open_settings&query=6.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Update Library', 'update_library&query=tool', 'library_update.png', 'DefaultAddonProgram.png', isFolder=False)
        if traktCredentials == True:
            self.addDirectoryItem('Import Trakt Movie Collection...', 'movies_to_library&url=trakt_collection', 'trakt.png', 'DefaultMovies.png', isFolder=False)
            self.addDirectoryItem('Import Trakt Movie Watchlist...', 'movies_to_library&url=trakt_watchlist', 'trakt.png', 'DefaultMovies.png', isFolder=False)
            self.addDirectoryItem('Import Trakt TV Show Collection...', 'tvshows_to_library&url=trakt_collection', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
            self.addDirectoryItem('Import Trakt TV Show Watchlist...', 'tvshows_to_library&url=trakt_watchlist', 'trakt.png', 'DefaultTVShows.png', isFolder=False)
        self.endDirectory()


    def downloads(self):
        movie_downloads = control.setting('movie.download.path')
        if len(control.listDir(movie_downloads)[0]) > 0:
            self.addDirectoryItem('Downloads Movie Folder', movie_downloads, 'movies.png', 'DefaultMovies.png', isAction=False)
        tv_downloads = control.setting('tv.download.path')
        if len(control.listDir(tv_downloads)[0]) > 0:
            self.addDirectoryItem('Downloads TV Show Folder', tv_downloads, 'tvshows.png', 'DefaultTVShows.png', isAction=False)
        self.endDirectory()


    def tools(self):
        self.addDirectoryItem('Free99 Settings', 'open_settings&query=0.0', 'icon.png', 'DefaultAddonProgram.png', isFolder=False)    
        self.addDirectoryItem('Authorize Trakt', 'auth_trakt', 'trakt.png', 'DefaultAddonProgram.png', isFolder=False)   
        self.addDirectoryItem('Setup ViewTypes', 'views_menu', 'tools.png', 'DefaultAddonProgram.png')        
        self.addDirectoryItem('Cleaning Tools', 'cleantools_menu', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem('Provider Settings', 'open_settings&query=4.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('ResolveUrl Settings', 'open_resolveurl_settings', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)


        self.endDirectory()


    def devtools(self):
        self.addDirectoryItem('Testing', 'testing', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem('In Theatres', 'movies&url=tmdb_in_theatres', 'latest-movies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Test Movies(TMDB)', 'movies&url=tmdb_jewtestmovies', 'movies.png', 'DefaultMovies.png')
        self.addDirectoryItem('Test TV Shows(TMDB)', 'tvshows&url=tmdb_jewtestshows', 'tvshows.png', 'DefaultTVShows.png')
        self.addDirectoryItem('Provider Domains', 'get_provider_domains', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Provider Settings', 'open_settings&query=4.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('View Debug Log', 'view_debuglog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear Debug Log', 'clear_debuglog', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Cleaning Tools', 'cleantools_menu', 'tools.png', 'DefaultAddonProgram.png')
        self.addDirectoryItem('Force Open SideMenu/SlideMenu', 'open_sidemenu', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.endDirectory()


    def cleantools(self):
        self.addDirectoryItem('Clear All Cache', 'clear_all_cache', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear Providers', 'clear_sources', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear Meta Cache', 'clear_meta_cache', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear Cache', 'clear_cache', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear ResolveURL Cache', 'clear_resolveurl_cache', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear All Search Cache', 'clear_search_cache&select=all', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clean Old Settings',  'clean_settings',  'tools.png',  'DefaultAddonProgram.png', isFolder=False)
        self.addDirectoryItem('Clear ViewTypes',  'clear_viewtypes',  'tools.png',  'DefaultAddonProgram.png', isFolder=False)
        self.endDirectory()


    def cleantools_widget(self):
        try:
            items = [('[B]Clear All Cache[/B]', 'clear_all_cache')]
            items += [('[B]Clear Providers[/B]', 'clear_sources')]
            items += [('[B]Clear Meta Cache[/B]', 'clear_meta_cache')]
            items += [('[B]Clear Cache[/B]', 'clear_cache')]
            items += [('[B]Clear ResolveURL Cache[/B]', 'clear_resolveurl_cache')]
            items += [('[B]Clear All Search Cache[/B]', 'clear_search_cache&select=all')]
            items += [('[B]Clean Old Settings[/B]', 'clean_settings')]
            items += [('[B]Clear ViewTypes[/B]', 'clear_viewtypes')]
            if not control.setting('addon.debug') == 'false':
                items += [('[B]Clear Debug Log[/B]', 'clear_debuglog')]
                items += [('[B]View Debug Log[/B]', 'view_debuglog')]
            select = control.selectDialog([i[0] for i in items], 'Cleaning Tools')
            if select == -1:
                return
            control.execute('RunPlugin(%s?action=%s)' % (sysaddon, items[select][1]))
        except:
            return


    def installsmenu(self):
        if not control.condVisibility('System.HasAddon(plugin.program.lazylinks)'):
            self.addDirectoryItem('plugin.program.lazylinks - Install Addon', 'installAddon&id=plugin.program.lazylinks', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        else:
            self.addDirectoryItem('plugin.program.lazylinks - Open Addon', 'plugin://plugin.program.lazylinks', 'tools.png', 'DefaultAddonProgram.png', isAction=False)
        if not control.condVisibility('System.HasAddon(script.free99.artwork)'):
            self.addDirectoryItem('script.free99.artwork - Install Addon', 'installAddon&id=script.free99.artwork', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        else:
            self.addDirectoryItem('script.free99.artwork - Open Settings', 'open_settings&query=0.0', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        if not control.condVisibility('System.HasAddon(script.trakt)'):
            self.addDirectoryItem('script.trakt - Install Addon', 'installAddon&id=script.trakt', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        else:
            self.addDirectoryItem('script.trakt - Open Settings', 'open_settings&id=script.trakt', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        if not control.condVisibility('System.HasAddon(plugin.video.youtube)'):
            self.addDirectoryItem('plugin.video.youtube - Install Addon', 'installAddon&id=plugin.video.youtube', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        else:
            self.addDirectoryItem('plugin.video.youtube - Open Settings', 'open_settings&id=plugin.video.youtube', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        if not control.condVisibility('System.HasAddon(plugin.video.json_iptv)'):
            self.addDirectoryItem('plugin.video.json_iptv - Install Addon', 'installAddon&id=plugin.video.json_iptv', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        else:
            self.addDirectoryItem('plugin.video.json_iptv - Open Settings', 'open_settings&id=plugin.video.json_iptv', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        if not control.condVisibility('System.HasAddon(service.subtitles.a4ksubtitles)'):
            self.addDirectoryItem('service.subtitles.a4ksubtitles - Install Addon', 'installAddon&id=service.subtitles.a4ksubtitles', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        else:
            self.addDirectoryItem('service.subtitles.a4ksubtitles - Open Settings', 'open_settings&id=service.subtitles.a4ksubtitles', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
        self.endDirectory()


    def views(self):
        try:
            items = [('Movies', 'movies')]
            items += [('TV Shows', 'tvshows')]
            items += [('Seasons', 'seasons')]
            items += [('Episodes', 'episodes')]
            select = control.selectDialog([i[0] for i in items], 'Setup ViewTypes')
            if select == -1:
                return
            content = items[select][1]
            title = 'Click Here To Save View'
            url = '%s?action=add_view&content=%s' % (sysaddon, content)
            poster = control.addonPoster()
            banner = control.addonBanner()
            fanart = control.addonFanart()
            #item = control.item(label=title) # Could probably swap it all back and remove the kodi_v20 changes as none of this seems to give any issues or errors.
            ##New Starts
            try:
                item = control.item(label=title, offscreen=True)
            except:
                item = control.item(label=title)
            ##New Ends
            item.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'banner': banner})
            item.setProperty('Fanart_Image', fanart)
            ##New Starts
            if kodi_version >= 20:
                info_tag = ListItemInfoTag(item, 'video')
                info_tag.set_info({'title': title})
            else:
                item.setInfo(type='Video', infoLabels={'title': title})
            ##New Ends
            #item.setInfo(type='Video', infoLabels={'title': title}) # Seems to be a useless line of code lol. (been commented out since before the kodi_v20 changes.)
            control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
            ## Added in to help those to disable the TopBar lol.
            self.addDirectoryItem('Force Open SideMenu/SlideMenu', 'open_sidemenu', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
            control.content(syshandle, content)
            control.directory(syshandle, cacheToDisc=True)
            from resources.lib.modules import views
            views.setView(content, {})
        except:
            return


    def clearCache(self):
        from resources.lib.modules import cache
        yes = control.yesnoDialog('Clear Cache?')
        if not yes:
            return
        cache.cache_clear()
        control.infoDialog('Cache Cleared.', sound=True, icon='INFO')


    def clearCacheMeta(self):
        from resources.lib.modules import cache
        yes = control.yesnoDialog('Clear Meta Cache?')
        if not yes:
            return
        cache.cache_clear_meta()
        control.infoDialog('Meta Cache Cleared.', sound=True, icon='INFO')


    def clearCacheProviders(self):
        from resources.lib.modules import cache
        yes = control.yesnoDialog('Clear Providers Cache?')
        if not yes:
            return
        cache.cache_clear_providers()
        control.infoDialog('Providers Cache Cleared.', sound=True, icon='INFO')


    def clearCacheSearch(self, select):
        from resources.lib.modules import cache
        yes = control.yesnoDialog('Clear All Search Cache?')
        if not yes:
            return
        cache.cache_clear_search(select)
        control.infoDialog('All Search Cache Cleared.', sound=True, icon='INFO')


    def clearCacheAll(self):
        from resources.lib.modules import cache
        yes = control.yesnoDialog('Clear All Cache?')
        if not yes:
            return
        cache.cache_clear_all()
        control.infoDialog('All Cache Cleared.', sound=True, icon='INFO')


    def cleanSettings(self):
        from resources.lib.modules import cache
        yes = control.yesnoDialog('Clean Old Settings?')
        if not yes:
            return
        cache.clean_settings()
        control.infoDialog('Old Settings Cleaned.', sound=True, icon='INFO')


    def clearDebugLog(self):
        yes = control.yesnoDialog('Clear Debug Log?')
        if not yes:
            return
        log_utils.empty_log()
        control.infoDialog('Debug Log Cleared.', sound=True, icon='INFO')


    def clearViewTypes(self):
        from resources.lib.modules import views
        yes = control.yesnoDialog('Clear All ViewTypes?')
        if not yes:
            return
        views.deleteView()
        control.infoDialog('All ViewTypes Cleared.', sound=True, icon='INFO')


    def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True):
        url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
        artPath = control.artPath()
        fanart = control.addonFanart()
        thumb = os.path.join(artPath, thumb) if not (artPath == None or thumb == None) else icon
        cm = []
        cm.append(('[B]View Change Log[/B]', 'RunPlugin(%s?action=view_changelog)' % sysaddon))
        cm.append(('[B]Clean Tools Widget[/B]', 'RunPlugin(%s?action=cleantools_widget)' % sysaddon))
        if queue == True:
            cm.append(('Queue Item', 'RunPlugin(%s?action=queue_item)' % sysaddon))
        if not context == None:
            cm.append((context[0], 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))
        try:
            item = control.item(label=name, offscreen=True)
        except:
            item = control.item(label=name)
        item.addContextMenuItems(cm)
        item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})
        control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


    def addDirectory(self, items, queue=False, isFolder=True):
        if items == None or len(items) == 0:
            control.idle()
            #sys.exit()
        sysfanart = control.addonFanart()
        for i in items:
            try:
                url = '%s?action=%s&url=%s' % (sysaddon, i['action'], i['url'])
                title = i['title']
                icon = i['image'] if 'image' in i and not i['image'] == (None or 'None' or '0') else 'DefaultVideo.png'
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == (None or 'None' or '0') else sysfanart
                try:
                    item = control.item(label=title, offscreen=True)
                except:
                    item = control.item(label=title)
                item.setProperty('IsPlayable', 'true')
                item.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart})
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
            except Exception:
                #log_utils.log('addDirectory', 1)
                pass
        self.endDirectory()


    def endDirectory(self, cached=True):
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=cached)


