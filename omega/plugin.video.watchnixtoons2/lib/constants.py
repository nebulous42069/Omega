# -*- coding: utf-8 -*-

import sys
import xbmcaddon

IMAGES_URL = 'https://cdn.animationexplore.com'

THUMBS_BASEURL = 'https://doko-desuka.github.io/128h/'

PLUGIN_ID = int(sys.argv[1])
PLUGIN_URL = sys.argv[0]
PLUGIN_NAME = PLUGIN_URL.replace("plugin://","")
PLUGIN_TITLE = 'WatchNixtoons2'
PROPERTY_CATALOG_PATH = 'wnt2.catalogPath'
PROPERTY_CATALOG = 'wnt2.catalog'
PROPERTY_EPISODE_LIST_URL = 'wnt2.listURL'
PROPERTY_EPISODE_LIST_DATA = 'wnt2.listData'
PROPERTY_LATEST_MOVIES = 'wnt2.latestMovies'
PROPERTY_INFO_ITEMS = 'wnt2.infoItems'
PROPERTY_SESSION_COOKIE = 'wnt2.cookie'

# Fake user-agent to get past some cloudflare checks :(
WNT2_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'

ADDON = xbmcaddon.Addon()

DOMAINS = {
    0:'www.wcofun.net',
}

BASEURL = 'https://' + DOMAINS.get( int(ADDON.getSetting('baseURL')), DOMAINS[0] )

# Show catalog: whether to show the catalog categories or to go straight to the "ALL" section with all items visible.
ADDON_SHOW_CATALOG = ADDON.getSetting('showCatalog') == 'true'
# Use Latest Releases date: whether to sort the Latest Releases items by their date, or with a catalog.
ADDON_LATEST_DATE = ADDON.getSetting('useLatestDate') == 'true'
# Use Latest Releases thumbs: whether to show a little thumbnail available for the Latest Releases items only.
ADDON_LATEST_THUMBS = ADDON.getSetting('showLatestThumbs') == 'true'
# Use poster images for each catalog folder. Makes for a better experience on custom Kodi skins.
ADDON_CATALOG_THUMBS = ADDON.getSetting('showCatalogThumbs') == 'true'
# Uses ids from files for the ongoing & popular to show the thumbnails
ADDON_POPULAR_THUMBS = ADDON.getSetting('showPopularThumbs') == 'true'
# Uses ids from files for the series to show the thumbnails
ADDON_SERIES_THUMBS = ADDON.getSetting('showSeriesThumbs') == 'true'
# Uses URL to get fan art for videos
ADDON_VIDEO_FANART = ADDON.getSetting('showVideoFanart') == 'true'

ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_ICON_DICT = {'icon': ADDON_ICON, 'thumb': ADDON_ICON, 'poster': ADDON_ICON}
RESOURCE_URL = 'special://home/addons/{0}resources/'.format(PLUGIN_NAME)
ADDON_TRAKT_ICON = RESOURCE_URL + 'media/traktIcon.png'

# Initialized in 'actionResolve()'.
MEDIA_HEADERS = None

# Url paths: paths to parts of the website, to be added to the BASEURL url.
# Also used to tell what kind of catalog is loaded in memory.
# In case they change in the future it'll be easier to modify in here.
URL_PATHS = {
    'latest': 'latest', # No path used, 'makeLatestCatalog()' uses the homepage of website.
    'popular': 'popular', # No path used, 'makePopularCatalog()' uses the hompage of website.
    'dubbed': '/dubbed-anime-list',
    'cartoons': '/cartoon-list',
    'subbed': '/subbed-anime-list',
    'movies': '/movie-list',
    'latestmovies': '/anime/movies',
    'ova': '/ova-list',
    'search': '/search',
    'genre': '/search-by-genre'
}
