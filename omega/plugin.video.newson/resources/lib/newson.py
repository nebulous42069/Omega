#   Copyright (C) 2022 Lunatixz
#
#
# This file is part of NewsOn.
#
# NewsOn is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NewsOn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NewsOn.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, traceback, routing
import socket, json, collections

from six.moves     import urllib
from itertools     import repeat, cycle, chain, zip_longest
from simplecache   import SimpleCache, use_cache
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

# Import custom client instead of requests
from resources.lib import client

try:
    if (xbmc.getCondVisibility('System.Platform.Android') or xbmc.getCondVisibility('System.Platform.Windows')):
        from multiprocessing.dummy import Pool as ThreadPool
    else:
        from multiprocessing.pool  import ThreadPool

    from multiprocessing  import cpu_count
    from _multiprocessing import SemLock, sem_unlink

    SUPPORTS_POOL = True
    CPU_COUNT     = cpu_count()
except Exception as e:
    CPU_COUNT     = 2
    SUPPORTS_POOL = False

# Plugin Info
ADDON_ID      = 'plugin.video.newson'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
NEWSART       = os.path.join(ADDON_PATH,'resources','images','newscast.jpg')
CLIPART       = os.path.join(ADDON_PATH,'resources','images','videoclips.jpg')
ROUTER        = routing.Plugin()

## GLOBALS ##
DEFAULT_ENCODING = "utf-8"
CONTENT_TYPE     = 'episodes'
DISC_CACHE       = False
DEBUG            = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'

# Updated API endpoints for v5
BASE_API      = 'https://newson-api.triple-it.nl/v5api'
LOGO_URL      = 'https://dummyimage.com/512x512/035e8b/FFFFFF.png&text=%s'
FAN_URL       = 'https://dummyimage.com/1280x720/035e8b/FFFFFF.png&text=%s'

## MAIN MENU ROUTES ##
@ROUTER.route('/')
def buildMenu():
    NewsOn().buildMenu()

## SEARCH ROUTES ##
@ROUTER.route('/search')
def showSearchMenu():
    NewsOn().showSearchMenu()

@ROUTER.route('/search/stations')
def searchStations():
    NewsOn().searchStations()

@ROUTER.route('/search/clips')
def searchClips():
    NewsOn().searchClips()

@ROUTER.route('/search/stations/new')
def newStationSearch():
    NewsOn().newStationSearch()

@ROUTER.route('/search/clips/new')
def newClipSearch():
    NewsOn().newClipSearch()

@ROUTER.route('/search/stations/results/<query>')
def stationSearchResults(query):
    NewsOn().stationSearchResults(query)

@ROUTER.route('/search/clips/results/<query>')
def clipSearchResults(query):
    NewsOn().clipSearchResults(query)

@ROUTER.route('/search/stations/edit/<query>')
def editStationSearch(query):
    NewsOn().editStationSearch(query)

@ROUTER.route('/search/clips/edit/<query>')
def editClipSearch(query):
    NewsOn().editClipSearch(query)

@ROUTER.route('/search/stations/delete/<query>')
def deleteStationSearch(query):
    NewsOn().deleteStationSearch(query)

@ROUTER.route('/search/clips/delete/<query>')
def deleteClipSearch(query):
    NewsOn().deleteClipSearch(query)

@ROUTER.route('/search/stations/clear')
def clearStationHistory():
    NewsOn().clearStationHistory()

@ROUTER.route('/search/clips/clear')
def clearClipHistory():
    NewsOn().clearClipHistory()

## CONTENT ROUTES ##
@ROUTER.route('/home')
def buildHome():
    NewsOn().browse('home')

@ROUTER.route('/home/row/<row_id>')
def homeRowContent(row_id):
    NewsOn().displayRowContent(row_id, NewsOn().getHomeData)

@ROUTER.route('/livenow')
def buildLiveNow():
    NewsOn().buildLiveNowMenu()

@ROUTER.route('/livenow/<category>')
def liveNowCategory(category):
    NewsOn().browseLiveNowCategory(category)

@ROUTER.route('/trending')
def buildTrending():
    NewsOn().browse('trending')

@ROUTER.route('/trending/row/<row_id>')
def trendingRowContent(row_id):
    NewsOn().displayRowContent(row_id, NewsOn().getTrendingData)

@ROUTER.route('/sports')
def buildSports():
    # Using universal parser - automatically handles entire sports navigation
    NewsOn().browseSportsUniversal()

@ROUTER.route('/sports/category/<category_id>')
def sportsCategoryContent(category_id):
    NewsOn().displaySportsCategoryContent(category_id)

@ROUTER.route('/sports/feed/<feed_id>')
def sportsFeedContent(feed_id):
    NewsOn().displaySportsFeedContent(feed_id)

@ROUTER.route('/sports/feed/<feed_id>/show/<show_id>')
def sportsSubShowContent(feed_id, show_id):
    NewsOn().displaySportsSubShowContent(feed_id, show_id)

@ROUTER.route('/sports/show/<show_id>/row/<row_id>')
def sportsShowRowContent(show_id, row_id):
    NewsOn().displaySportsShowRowContent(show_id, row_id)

@ROUTER.route('/sports/show/<show_id>/overview/<row_id>')
def sportsShowOverviewContent(show_id, row_id):
    NewsOn().displaySportsShowOverviewContent(show_id, row_id)

@ROUTER.route('/whatson')
def buildWhatsOn():
    NewsOn().browse('whatson')

@ROUTER.route('/whatson/row/<row_id>')
def whatsonRowContent(row_id):
    NewsOn().displayRowContent(row_id, NewsOn().getWhatsOnData)

@ROUTER.route('/weather')
def buildWeather():
    NewsOn().showWeather()

## UNIVERSAL PARSER ROUTES ##
@ROUTER.route('/view/endpoint/<endpoint_type>/<entity_id>')
def viewEndpoint(endpoint_type, entity_id):
    NewsOn().viewEndpoint(endpoint_type, entity_id)

@ROUTER.route('/view/content/<content_type>/<row_id>/<context_json>')
def viewContent(content_type, row_id, context_json):
    NewsOn().viewContent(content_type, row_id, context_json)

@ROUTER.route('/station/<chid>')
def buildStation(chid):
    NewsOn().browseStation(chid)

@ROUTER.route('/station/<chid>/<opt>')
def browseDetails(chid,opt):
    NewsOn().browseStation(chid,opt)

## PLAYBACK ROUTES ##
@ROUTER.route('/play/vod/<vid>/<vtype>')
def playVOD(vid, vtype):
    NewsOn().playVideo(vid, opt='vod', videoType=vtype)

@ROUTER.route('/play/live/<url>')
def playURL(url):
    NewsOn().playVideo(url, opt='live')

def log(msg, level=xbmc.LOGDEBUG):
    try: msg = str(msg)
    except: pass
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

def encodeString(text):
    if not isinstance(text,str): text = str(text)
    return urllib.parse.quote_plus(text)

def decodeString(text):
    return urllib.parse.unquote_plus(text)

class NewsOn(object):
    def __init__(self, sysARG=sys.argv):
        log('__init__, sysARG = %s'%(sysARG))
        self.sysARG    = sysARG
        self.cache     = SimpleCache()
        self.config    = self.getConfig()
        self.location  = self.config.get('location', {})
        self.weather   = self.config.get('weather', {})


    def buildMenu(self):
        """Build main menu - 7 items matching NewsON website"""
        log('buildMenu')
        MENU = [
            ('Search',     (showSearchMenu,) ),
            ('Home',       (buildHome,)      ),
            ('Live Now',   (buildLiveNow,)   ),
            ('Trending',   (buildTrending,)  ),
            ('Sports',     (buildSports,)    ),
            ('Weather',    (buildWeather,)   ),
            ("What'sON",   (buildWhatsOn,)   ),
        ]
        for item in MENU: self.addDir(*item)


    ## SEARCH SYSTEM ##

    def showSearchMenu(self):
        """Show search type selection: Stations or Clips"""
        log('showSearchMenu')
        self.addDir('Search Stations', (searchStations,))
        self.addDir('Search Most Recent Clips', (searchClips,))


    def searchStations(self):
        """Show station search menu with history"""
        log('searchStations')
        history = self.loadSearchHistory('stations')

        # Always show New Search and Clear History at top
        self.addDir('New Search', (newStationSearch,))

        if history:
            self.addDir('Clear Search History', (clearStationHistory,))

        # Show history items (most recent first - reverse order)
        for query in reversed(history):
            liz = xbmcgui.ListItem(query)
            liz.setProperty('IsPlayable', 'false')
            liz.setInfo(type='video', infoLabels={"mediatype":"video", "label":query, "title":query})
            liz.setArt({'thumb':ICON, 'fanart':FANART})

            # Add context menu
            context_menu = [
                ('Edit Search', 'RunPlugin(%s)' % ROUTER.url_for(editStationSearch, query=encodeString(query))),
                ('Delete from History', 'RunPlugin(%s)' % ROUTER.url_for(deleteStationSearch, query=encodeString(query)))
            ]
            liz.addContextMenuItems(context_menu)

            xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(stationSearchResults, query=encodeString(query)), liz, isFolder=True)


    def searchClips(self):
        """Show clips search menu with history"""
        log('searchClips')
        history = self.loadSearchHistory('clips')

        # Always show New Search and Clear History at top
        self.addDir('New Search', (newClipSearch,))

        if history:
            self.addDir('Clear Search History', (clearClipHistory,))

        # Show history items (most recent first - reverse order)
        for query in reversed(history):
            liz = xbmcgui.ListItem(query)
            liz.setProperty('IsPlayable', 'false')
            liz.setInfo(type='video', infoLabels={"mediatype":"video", "label":query, "title":query})
            liz.setArt({'thumb':ICON, 'fanart':FANART})

            # Add context menu
            context_menu = [
                ('Edit Search', 'RunPlugin(%s)' % ROUTER.url_for(editClipSearch, query=encodeString(query))),
                ('Delete from History', 'RunPlugin(%s)' % ROUTER.url_for(deleteClipSearch, query=encodeString(query)))
            ]
            liz.addContextMenuItems(context_menu)

            xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(clipSearchResults, query=encodeString(query)), liz, isFolder=True)


    def newStationSearch(self):
        """Prompt for new station search"""
        log('newStationSearch')
        dialog = xbmcgui.Dialog()
        query = dialog.input('Search Stations', type=xbmcgui.INPUT_ALPHANUM)

        if query:
            self.addToSearchHistory('stations', query)
            self.stationSearchResults(encodeString(query))
        else:
            # User cancelled, go back
            xbmc.executebuiltin('Action(Back)')


    def newClipSearch(self):
        """Prompt for new clip search"""
        log('newClipSearch')
        dialog = xbmcgui.Dialog()
        query = dialog.input('Search Clips', type=xbmcgui.INPUT_ALPHANUM)

        if query:
            self.addToSearchHistory('clips', query)
            self.clipSearchResults(encodeString(query))
        else:
            # User cancelled, go back
            xbmc.executebuiltin('Action(Back)')


    def stationSearchResults(self, query):
        """Display station search results"""
        query = decodeString(query)
        log('stationSearchResults, query = %s'%(query))

        results = self.executeSearch(query)

        # Filter for STATION_ROW only
        for result in results.get('results', []):
            if result.get('type') == 'STATION_ROW':
                items = result.get('items', [])
                for station in items:
                    self.buildStationItem(station)
                break


    def clipSearchResults(self, query):
        """Display clip search results"""
        query = decodeString(query)
        log('clipSearchResults, query = %s'%(query))

        results = self.executeSearch(query)

        # Filter for VOD_ROW only
        for result in results.get('results', []):
            if result.get('type') == 'VOD_ROW':
                items = result.get('items', [])
                self.poolList(self.buildVideoItem, items, 'search')
                break


    def editStationSearch(self, query):
        """Edit existing station search"""
        query = decodeString(query)
        log('editStationSearch, query = %s'%(query))

        dialog = xbmcgui.Dialog()
        new_query = dialog.input('Search Stations', defaultt=query, type=xbmcgui.INPUT_ALPHANUM)

        if new_query:
            # Remove original query from history
            history = self.loadSearchHistory('stations')
            if query in history:
                history.remove(query)
                self.saveSearchHistory('stations', history)

            # Add new query to history
            self.addToSearchHistory('stations', new_query)
            self.stationSearchResults(encodeString(new_query))
            xbmc.executebuiltin('Container.Refresh')


    def editClipSearch(self, query):
        """Edit existing clip search"""
        query = decodeString(query)
        log('editClipSearch, query = %s'%(query))

        dialog = xbmcgui.Dialog()
        new_query = dialog.input('Search Clips', defaultt=query, type=xbmcgui.INPUT_ALPHANUM)

        if new_query:
            # Remove original query from history
            history = self.loadSearchHistory('clips')
            if query in history:
                history.remove(query)
                self.saveSearchHistory('clips', history)

            # Add new query to history
            self.addToSearchHistory('clips', new_query)
            self.clipSearchResults(encodeString(new_query))
            xbmc.executebuiltin('Container.Refresh')


    def deleteStationSearch(self, query):
        """Delete station search from history"""
        query = decodeString(query)
        log('deleteStationSearch, query = %s'%(query))

        history = self.loadSearchHistory('stations')
        if query in history:
            history.remove(query)
            self.saveSearchHistory('stations', history)

        xbmc.executebuiltin('Container.Refresh')


    def deleteClipSearch(self, query):
        """Delete clip search from history"""
        query = decodeString(query)
        log('deleteClipSearch, query = %s'%(query))

        history = self.loadSearchHistory('clips')
        if query in history:
            history.remove(query)
            self.saveSearchHistory('clips', history)

        xbmc.executebuiltin('Container.Refresh')


    def clearStationHistory(self):
        """Clear all station search history"""
        log('clearStationHistory')
        self.saveSearchHistory('stations', [])
        xbmc.executebuiltin('Container.Refresh')


    def clearClipHistory(self):
        """Clear all clip search history"""
        log('clearClipHistory')
        self.saveSearchHistory('clips', [])
        xbmc.executebuiltin('Container.Refresh')


    def loadSearchHistory(self, search_type):
        """Load search history from settings"""
        setting_key = '%s_search_history' % search_type
        history_json = REAL_SETTINGS.getSetting(setting_key)

        if history_json:
            try:
                return json.loads(history_json)
            except:
                return []
        return []


    def saveSearchHistory(self, search_type, history):
        """Save search history to settings"""
        setting_key = '%s_search_history' % search_type
        REAL_SETTINGS.setSetting(setting_key, json.dumps(history))


    def addToSearchHistory(self, search_type, query):
        """Add query to search history (no duplicates, most recent at end)"""
        history = self.loadSearchHistory(search_type)

        # Remove if already exists
        if query in history:
            history.remove(query)

        # Add to end (most recent)
        history.append(query)

        # Save
        self.saveSearchHistory(search_type, history)


    def executeSearch(self, query):
        """Execute search API call"""
        log('executeSearch, query = %s'%(query))
        return self.openURL(BASE_API + '/search', params={'platformType': 'website', 'query': query})


    ## CONTENT BROWSING ##

    def browse(self, opt='home'):
        """Browse different content sections using universal parser"""
        log('browse, opt = %s'%(opt))

        if opt == 'home':
            data = self.getHomeData()
            context = {
                'storefront': 'home',
                'endpoint': BASE_API + '/storefront/home'
            }
            self.parseContent(data, context)

        elif opt == 'trending':
            data = self.getTrendingData()
            context = {
                'storefront': 'trending',
                'endpoint': BASE_API + '/storefront/trending'
            }
            self.parseContent(data, context)

        elif opt == 'whatson':
            data = self.getWhatsOnData()
            context = {
                'storefront': 'whatson',
                'endpoint': BASE_API + '/storefront/whatson'
            }
            self.parseContent(data, context)


    def parseRowsAsMenu(self, rows, page_type):
        """Parse API rows and display as menu folders"""
        log('parseRowsAsMenu, page_type = %s'%(page_type))

        for row in rows:
            row_id = str(row.get('id', ''))
            row_title = row.get('title', 'Content')
            row_type = row.get('type', '')

            # Skip certain row types
            if row_type in ['FAVORITES_ROW', 'POLL_ROW', 'COMMENTS_ROW', 'WEATHER_INFO_EXTENDED']:
                continue

            # Build appropriate menu item
            if row_type == 'SPORTS_FEED_ROW':
                # Sports feeds - create simple folders that link to feed content (which shows sub-shows)
                feeds = row.get('items', [])

                for feed in feeds:
                    feed_id = str(feed.get('id', ''))
                    feed_title = feed.get('title', 'Sports Feed')
                    logo = feed.get('logoUrl', ICON)
                    image = feed.get('imageUrl', FANART)

                    infoArt = {"thumb": logo, "poster": image, "fanart": image, "icon": logo, "logo": logo}
                    self.addDir(feed_title, (sportsFeedContent, feed_id), infoArt=infoArt)

            elif row_type in ['VOD_ROW', 'STATION_ROW', 'TWO_LINE_STATION_ROW', 'BREAKING',
                             'SPORTS_SHOW_ROW', 'WHATSON_ROW', 'WHATSON_HEADER', 'AUTOPLAY_HEADER']:
                # These become folders that lead to row content
                if page_type == 'home':
                    self.addDir(row_title, (homeRowContent, row_id))
                elif page_type == 'trending':
                    self.addDir(row_title, (trendingRowContent, row_id))
                elif page_type == 'whatson':
                    self.addDir(row_title, (whatsonRowContent, row_id))


    def displayRowContent(self, row_id, data_func):
        """Display content from a specific row"""
        log('displayRowContent, row_id = %s'%(row_id))

        data = data_func()

        for row in data.get('rows', []):
            if str(row.get('id', '')) == row_id:
                row_type = row.get('type', '')
                row_items = row.get('items', [])

                if row_type == 'VOD_ROW':
                    self.poolList(self.buildVideoItem, row_items, 'vod')

                elif row_type == 'STATION_ROW' or row_type == 'TWO_LINE_STATION_ROW':
                    if row_type == 'TWO_LINE_STATION_ROW':
                        # Trending stations have nested station object
                        for item in row_items:
                            station = item.get('station', {})
                            self.buildStationItem(station)
                    else:
                        for station in row_items:
                            self.buildStationItem(station)

                elif row_type == 'BREAKING':
                    self.poolList(self.buildVideoItem, row_items, 'breaking')

                elif row_type == 'WHATSON_ROW' or row_type == 'WHATSON_HEADER':
                    item = row.get('item', {})
                    if item:
                        self.buildVideoItem((item, 'whatson'))

                elif row_type == 'AUTOPLAY_HEADER':
                    station = row.get('item', {}).get('station', {})
                    playables = row.get('item', {}).get('playables', {})
                    if playables and playables.get('vod'):
                        vod = playables['vod']
                        vod['station'] = station
                        vod['title'] = row.get('item', {}).get('title', 'Featured')
                        self.buildVideoItem((vod, 'live'))

                break


    def buildLiveNowMenu(self):
        """Build Live Now submenu with categories"""
        log('buildLiveNowMenu')
        self.addDir('Nearby live stations', (liveNowCategory, 'nearby'))
        self.addDir('Trending live', (liveNowCategory, 'trending'))
        self.addDir('Most popular', (liveNowCategory, 'popular'))


    def browseLiveNowCategory(self, category):
        """Browse Live Now category"""
        log('browseLiveNowCategory, category = %s'%(category))

        home_data = self.getHomeData()

        if category == 'nearby':
            # Get live now row from home
            for row in home_data.get('rows', []):
                if row.get('type') == 'VOD_ROW' and 'live' in row.get('title', '').lower():
                    items = row.get('items', [])
                    self.poolList(self.buildVideoItem, items, 'live')
                    break

        elif category == 'trending':
            # Get trending data
            trending_data = self.getTrendingData()
            for row in trending_data.get('rows', []):
                if row.get('type') == 'TWO_LINE_STATION_ROW':
                    items = row.get('items', [])
                    for item in items:
                        station = item.get('station', {})
                        self.buildStationItem(station)
                    break

        elif category == 'popular':
            # Get popular live videos
            for row in home_data.get('rows', []):
                if row.get('type') == 'VOD_ROW' and 'for you' in row.get('title', '').lower():
                    items = row.get('items', [])
                    # Filter for live items
                    live_items = [item for item in items if 'LIVE' in item.get('tags', [])]
                    if live_items:
                        self.poolList(self.buildVideoItem, live_items, 'live')
                    else:
                        self.poolList(self.buildVideoItem, items, 'vod')
                    break


    def browseSportsUniversal(self):
        """
        Browse sports section using universal parser

        This demonstrates how the universal parser automatically handles
        the entire sports menu structure without manual route/function creation
        """
        log('browseSportsUniversal')
        data = self.getSportsData()

        # That's it! The universal parser handles everything:
        # - Detects SPORTS_FEED_ROW and creates feed folders
        # - Each feed links to /view/endpoint/sportsfeed/{id}
        # - That endpoint auto-fetches and displays SPORTS_SHOW_ROW items
        # - Each show links to /view/endpoint/sportsshow/{id}
        # - That endpoint displays Most Recent and Explore sections
        # - Those sections link to /view/content which displays final videos/shows

        # No manual functions needed for each level!
        context = {
            'storefront': 'sports',
            'endpoint': BASE_API + '/storefront/sports'
        }
        self.parseContent(data, context)


    def browseSports(self):
        """Browse sports section - show category folders (Level 1)"""
        log('browseSports')
        data = self.getSportsData()
        rows = data.get('rows', [])

        # Display SPORTS_FEED_ROW items as category folders
        # Use index as ID since multiple rows have same id "sport-feed-row"
        category_index = 0
        for row in rows:
            row_type = row.get('type', '')

            if row_type == 'SPORTS_FEED_ROW':
                category_title = row.get('title', 'Sports')

                # Use thumbnail from first feed item
                items = row.get('items', [])
                thumb = ICON
                if items and len(items) > 0:
                    thumb = items[0].get('logoUrl', ICON)

                infoArt = {"thumb": thumb, "poster": thumb, "fanart": FANART, "icon": thumb, "logo": thumb}
                self.addDir(category_title, (sportsCategoryContent, str(category_index)), infoArt=infoArt)
                category_index += 1


    def displaySportsCategoryContent(self, category_id):
        """Display feeds within a category (Level 2)"""
        log('displaySportsCategoryContent, category_id = %s' % category_id)

        data = self.getSportsData()
        rows = data.get('rows', [])

        # Find the category row by index
        category_index = int(category_id)
        current_index = 0

        for row in rows:
            if row.get('type') == 'SPORTS_FEED_ROW':
                if current_index == category_index:
                    feeds = row.get('items', [])

                    for feed in feeds:
                        feed_id = str(feed.get('id', ''))
                        feed_title = feed.get('title', 'Sports Feed')
                        logo = feed.get('logoUrl', ICON)
                        image = feed.get('imageUrl', FANART)

                        infoArt = {"thumb": logo, "poster": image, "fanart": image, "icon": logo, "logo": logo}
                        self.addDir(feed_title, (sportsFeedContent, feed_id), infoArt=infoArt)
                    return
                current_index += 1


    def displaySportsFeedContent(self, feed_id):
        """Display sub-shows within a feed using detail endpoint (Level 3)"""
        log('displaySportsFeedContent, feed_id = %s' % feed_id)

        # Use the /v5api/detail/sportsfeed endpoint to get shows for this feed
        endpoint = BASE_API + '/detail/sportsfeed/%s' % feed_id
        data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))

        if not data:
            xbmcgui.Dialog().notification(ADDON_NAME, 'Could not load feed content', ICON, 3000)
            return

        rows = data.get('rows', [])

        if not rows:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No shows available for this feed', ICON, 3000)
            return

        # Display each SPORTS_SHOW_ROW as a folder
        for row in rows:
            if row.get('type') == 'SPORTS_SHOW_ROW':
                show_id = str(row.get('id', ''))
                show_title = row.get('title', 'Sports Show')
                logo = row.get('logoUrl', ICON)
                items = row.get('items', [])
                video_count = len(items)

                # Create label with video count
                label = '%s (%d videos)' % (show_title, video_count) if video_count > 0 else show_title

                infoArt = {"thumb": logo, "poster": logo, "fanart": FANART, "icon": logo, "logo": logo}
                self.addDir(label, (sportsSubShowContent, feed_id, show_id), infoArt=infoArt)


    def displaySportsSubShowContent(self, feed_id, show_id):
        """Display show menu with Most Recent and Explore sections (Level 4)"""
        log('displaySportsSubShowContent, feed_id = %s, show_id = %s' % (feed_id, show_id))

        # Use the /v5api/detail/sportsshow endpoint to get show details and related content
        endpoint = BASE_API + '/detail/sportsshow/%s' % show_id
        data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))

        if not data:
            xbmcgui.Dialog().notification(ADDON_NAME, 'Could not load show content', ICON, 3000)
            return

        rows = data.get('rows', [])

        if not rows:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No content available', ICON, 3000)
            return

        # Display each row as a folder or content
        for row in rows:
            row_type = row.get('type', '')
            row_id = str(row.get('id', ''))
            row_title = row.get('title', 'Content')

            if row_type == 'VOD_ROW':
                # Most Recent section - display as folder
                items = row.get('items', [])
                video_count = len(items)
                label = '%s (%d videos)' % (row_title, video_count) if video_count > 0 else row_title

                infoArt = {"thumb": ICON, "poster": ICON, "fanart": FANART, "icon": ICON, "logo": ICON}
                self.addDir(label, (sportsShowRowContent, show_id, row_id), infoArt=infoArt)

            elif row_type == 'SPORTS_SHOW_OVERVIEW_ROW':
                # Explore other shows section - display as folder
                items = row.get('items', [])
                show_count = len(items)
                label = '%s (%d shows)' % (row_title, show_count) if show_count > 0 else row_title

                infoArt = {"thumb": ICON, "poster": ICON, "fanart": FANART, "icon": ICON, "logo": ICON}
                self.addDir(label, (sportsShowOverviewContent, show_id, row_id), infoArt=infoArt)


    def displaySportsShowRowContent(self, show_id, row_id):
        """Display videos from a specific row in sports show (Level 5 - Most Recent videos)"""
        log('displaySportsShowRowContent, show_id = %s, row_id = %s' % (show_id, row_id))

        # Fetch the show details to get the row content
        endpoint = BASE_API + '/detail/sportsshow/%s' % show_id
        data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))

        if not data:
            xbmcgui.Dialog().notification(ADDON_NAME, 'Could not load show content', ICON, 3000)
            return

        rows = data.get('rows', [])

        # Find the specific row by row_id
        for row in rows:
            if str(row.get('id', '')) == row_id:
                items = row.get('items', [])

                if not items:
                    xbmcgui.Dialog().notification(ADDON_NAME, 'No videos available', ICON, 3000)
                    return

                # Display videos
                self.poolList(self.buildVideoItem, items, 'sports')
                return

        # Row not found
        log('Row not found: %s in show: %s' % (row_id, show_id), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Content not found', ICON, 3000)


    def displaySportsShowOverviewContent(self, show_id, row_id):
        """Display related sports shows from overview row (Level 5 - Explore other shows)"""
        log('displaySportsShowOverviewContent, show_id = %s, row_id = %s' % (show_id, row_id))

        # Fetch the show details to get the overview row content
        endpoint = BASE_API + '/detail/sportsshow/%s' % show_id
        data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))

        if not data:
            xbmcgui.Dialog().notification(ADDON_NAME, 'Could not load show content', ICON, 3000)
            return

        rows = data.get('rows', [])

        # Find the specific overview row by row_id
        for row in rows:
            if str(row.get('id', '')) == row_id and row.get('type') == 'SPORTS_SHOW_OVERVIEW_ROW':
                items = row.get('items', [])

                if not items:
                    xbmcgui.Dialog().notification(ADDON_NAME, 'No shows available', ICON, 3000)
                    return

                # Display each SPORTS_SHOW item as a clickable folder
                # These shows link to other sports show pages
                for show_item in items:
                    show_item_id = str(show_item.get('id', ''))
                    show_title = show_item.get('title', 'Sports Show')
                    logo = show_item.get('logoUrl', ICON)
                    cover = show_item.get('coverUrl', FANART)

                    infoArt = {"thumb": logo, "poster": cover, "fanart": cover, "icon": logo, "logo": logo}

                    # Link to the show's content using a dummy feed_id (we'll navigate directly to show)
                    # Since we're linking to a SPORTS_SHOW directly, we need a route that accepts just show_id
                    # For now, use the existing route with a placeholder feed_id
                    self.addDir(show_title, (sportsSubShowContent, 'overview', show_item_id), infoArt=infoArt)

                return

        # Row not found
        log('Overview row not found: %s in show: %s' % (row_id, show_id), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Content not found', ICON, 3000)


    def showWeather(self):
        """Show weather information dialog"""
        log('showWeather')

        config = self.getConfig()
        weather = config.get('weather', {})
        location = config.get('location', {})

        city = location.get('city', 'Unknown')
        state = location.get('state', 'Unknown')
        temp = weather.get('temperature', 0)

        # Try to get extended weather from home data
        home_data = self.getHomeData()
        for row in home_data.get('rows', []):
            if row.get('type') == 'WEATHER_INFO_EXTENDED':
                city = row.get('city', city)
                state = row.get('state', state)
                temp = row.get('temperature', temp)
                feels_like = row.get('feelsLike', temp)
                description = row.get('description', '')
                humidity = row.get('humidity', 0)
                wind = row.get('wind', 0)

                dialog = xbmcgui.Dialog()
                message = (
                    '[B]%s, %s[/B]\n\n'
                    'Temperature: %.1f°F\n'
                    'Feels Like: %.1f°F\n'
                    'Conditions: %s\n'
                    'Humidity: %d%%\n'
                    'Wind: %.1f mph'
                ) % (city, state, temp, feels_like, description, humidity, wind)

                dialog.ok('NewsON Weather', message)
                return

        # Fallback
        dialog = xbmcgui.Dialog()
        message = '[B]%s, %s[/B]\n\nTemperature: %.1f°F' % (city, state, temp)
        dialog.ok('NewsON Weather', message)


    def parseContent(self, data, context=None):
        """
        Universal content parser - automatically determines content type and creates appropriate menus

        Args:
            data: API response data (dict with 'rows' or 'items')
            context: Optional context dict with:
                - 'parent_id': ID of parent entity
                - 'parent_type': Type of parent (feed, show, etc.)
                - 'endpoint': API endpoint used

        This function intelligently:
        1. Detects content type (videos, stations, feeds, shows, etc.)
        2. Determines if items are final content or folders
        3. Creates appropriate menu structure automatically
        """
        log('parseContent, context = %s' % str(context))

        context = context or {}
        rows = data.get('rows', [])

        # If data has 'item' field, extract it for metadata
        parent_item = data.get('item', {})

        for row in rows:
            row_type = row.get('type', '')
            row_id = str(row.get('id', ''))
            row_title = row.get('title', 'Content')
            items = row.get('items', [])

            # Skip certain row types
            if row_type in ['FAVORITES_ROW', 'POLL_ROW', 'COMMENTS_ROW', 'WEATHER_INFO_EXTENDED']:
                continue

            # Parse based on row type
            if row_type == 'VOD_ROW':
                # Videos - create folder that displays videos when clicked
                video_count = len(items)
                label = '%s (%d videos)' % (row_title, video_count) if video_count > 0 else row_title

                # Create folder that will display the videos
                infoArt = {"thumb": ICON, "poster": ICON, "fanart": FANART, "icon": ICON, "logo": ICON}

                # Use generic content viewer route
                self.addDir(label, (viewContent, 'vod_row', row_id, encodeString(json.dumps(context))), infoArt=infoArt)

            elif row_type == 'STATION_ROW' or row_type == 'TWO_LINE_STATION_ROW':
                # Stations - create folder that displays stations when clicked
                station_count = len(items)
                label = '%s (%d stations)' % (row_title, station_count) if station_count > 0 else row_title

                infoArt = {"thumb": ICON, "poster": ICON, "fanart": FANART, "icon": ICON, "logo": ICON}
                self.addDir(label, (viewContent, 'station_row', row_id, encodeString(json.dumps(context))), infoArt=infoArt)

            elif row_type == 'SPORTS_FEED_ROW':
                # Sports feeds - each feed item becomes a folder
                for feed in items:
                    feed_id = str(feed.get('id', ''))
                    feed_title = feed.get('title', 'Sports Feed')
                    logo = feed.get('logoUrl', ICON)
                    image = feed.get('imageUrl', FANART)

                    infoArt = {"thumb": logo, "poster": image, "fanart": image, "icon": logo, "logo": logo}

                    # Create folder that will fetch and parse the feed detail endpoint
                    self.addDir(feed_title, (viewEndpoint, 'sportsfeed', feed_id), infoArt=infoArt)

            elif row_type == 'SPORTS_SHOW_ROW':
                # Sports show - create folder leading to show detail
                show_id = str(row.get('id', ''))
                show_title = row.get('title', 'Sports Show')
                logo = row.get('logoUrl', ICON)
                video_count = len(items)

                label = '%s (%d videos)' % (show_title, video_count) if video_count > 0 else show_title

                infoArt = {"thumb": logo, "poster": logo, "fanart": FANART, "icon": logo, "logo": logo}

                # Create folder that will fetch and parse the show detail endpoint
                self.addDir(label, (viewEndpoint, 'sportsshow', show_id), infoArt=infoArt)

            elif row_type == 'SPORTS_SHOW_OVERVIEW_ROW':
                # Related sports shows - each show item becomes a folder
                show_count = len(items)
                label = '%s (%d shows)' % (row_title, show_count) if show_count > 0 else row_title

                infoArt = {"thumb": ICON, "poster": ICON, "fanart": FANART, "icon": ICON, "logo": ICON}

                # Create folder that will display the shows
                self.addDir(label, (viewContent, 'sports_show_overview', row_id, encodeString(json.dumps(context))), infoArt=infoArt)

            elif row_type in ['WHATSON_ROW', 'WHATSON_HEADER', 'AUTOPLAY_HEADER', 'BREAKING']:
                # These are content rows that can be displayed
                item_count = len(items)
                label = '%s (%d items)' % (row_title, item_count) if item_count > 0 else row_title

                infoArt = {"thumb": ICON, "poster": ICON, "fanart": FANART, "icon": ICON, "logo": ICON}
                self.addDir(label, (viewContent, row_type.lower(), row_id, encodeString(json.dumps(context))), infoArt=infoArt)


    def viewEndpoint(self, endpoint_type, entity_id):
        """
        Universal endpoint viewer - fetches data from an endpoint and parses it

        Args:
            endpoint_type: Type of endpoint (sportsfeed, sportsshow, etc.)
            entity_id: ID of entity to fetch
        """
        log('viewEndpoint, endpoint_type = %s, entity_id = %s' % (endpoint_type, entity_id))

        # Map endpoint type to API path
        endpoint_map = {
            'sportsfeed': '/detail/sportsfeed/%s',
            'sportsshow': '/detail/sportsshow/%s',
        }

        if endpoint_type not in endpoint_map:
            log('Unknown endpoint type: %s' % endpoint_type, xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, 'Invalid endpoint type', ICON, 3000)
            return

        # Fetch data from endpoint
        endpoint = BASE_API + (endpoint_map[endpoint_type] % entity_id)
        data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))

        if not data:
            xbmcgui.Dialog().notification(ADDON_NAME, 'Could not load content', ICON, 3000)
            return

        # Parse the content with context
        context = {
            'parent_id': entity_id,
            'parent_type': endpoint_type,
            'endpoint': endpoint
        }

        self.parseContent(data, context)


    def viewContent(self, content_type, row_id, context_json):
        """
        Universal content viewer - displays final content (videos, stations, etc.)

        Args:
            content_type: Type of content (vod_row, station_row, etc.)
            row_id: ID of the row to display
            context_json: JSON string with context information (URL-encoded)
        """
        log('viewContent, content_type = %s, row_id = %s, context = %s' % (content_type, row_id, context_json))

        context = json.loads(decodeString(context_json)) if context_json else {}

        # Re-fetch parent data to find the specific row
        parent_type = context.get('parent_type', '')
        parent_id = context.get('parent_id', '')
        endpoint = context.get('endpoint', '')

        # Fetch the data
        if endpoint:
            # We have the exact endpoint, re-fetch it
            data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))
        else:
            # No endpoint in context, can't proceed
            log('No endpoint in context for viewContent', xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, 'Cannot load content', ICON, 3000)
            return

        if not data:
            xbmcgui.Dialog().notification(ADDON_NAME, 'Could not load content', ICON, 3000)
            return

        # Find the specific row by row_id
        rows = data.get('rows', [])
        target_row = None

        for row in rows:
            if str(row.get('id', '')) == row_id:
                target_row = row
                break

        if not target_row:
            log('Row not found: %s' % row_id, xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, 'Content not found', ICON, 3000)
            return

        # Display content based on type
        items = target_row.get('items', [])

        if content_type == 'vod_row':
            # Display videos
            self.poolList(self.buildVideoItem, items, 'vod')

        elif content_type in ['station_row', 'two_line_station_row']:
            # Display stations
            if target_row.get('type') == 'TWO_LINE_STATION_ROW':
                # Trending stations have nested station object
                stations = []
                for item in items:
                    station = item.get('station', {})
                    if station:
                        stations.append(station)
                self.poolList(self.buildStationItem, stations)
            else:
                self.poolList(self.buildStationItem, items)

        elif content_type == 'sports_show_overview':
            # Display sports shows from overview row
            for show_item in items:
                show_item_id = str(show_item.get('id', ''))
                show_title = show_item.get('title', 'Sports Show')
                logo = show_item.get('logoUrl', ICON)
                cover = show_item.get('coverUrl', FANART)

                infoArt = {"thumb": logo, "poster": cover, "fanart": cover, "icon": logo, "logo": logo}

                # Link to the show's detail page
                self.addDir(show_title, (viewEndpoint, 'sportsshow', show_item_id), infoArt=infoArt)

        elif content_type in ['whatson_row', 'whatson_header', 'autoplay_header', 'breaking']:
            # Display videos or stations depending on item type
            if items and len(items) > 0:
                first_item_type = items[0].get('type', '')

                if first_item_type == 'VOD':
                    self.poolList(self.buildVideoItem, items, 'vod')
                elif first_item_type == 'STATION':
                    self.poolList(self.buildStationItem, items)
                else:
                    # Mixed or unknown, try to display as videos
                    self.poolList(self.buildVideoItem, items, 'vod')

        else:
            log('Unknown content type: %s' % content_type, xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(ADDON_NAME, 'Unknown content type', ICON, 3000)


    def browseStation(self, chid, opt=None):
        """Browse station content"""
        log('browseStation, chid = %s, opt = %s'%(chid, opt))

        if opt is None:
            self.addDir('Live Now', (browseDetails, chid, 'live'))
            self.addDir('Recent Videos', (browseDetails, chid, 'recent'))
        else:
            if opt == 'live':
                # Get live content for this station
                home_data = self.getHomeData()
                for row in home_data.get('rows', []):
                    if row.get('type') == 'VOD_ROW' and 'live' in row.get('title', '').lower():
                        items = row.get('items', [])
                        for item in items:
                            if item.get('station', {}).get('id') == chid:
                                self.buildVideoItem((item, 'live'))

            elif opt == 'recent':
                # Get recent videos for this station
                home_data = self.getHomeData()
                for row in home_data.get('rows', []):
                    if row.get('type') == 'VOD_ROW':
                        items = row.get('items', [])
                        for item in items:
                            if item.get('station', {}).get('id') == chid:
                                self.buildVideoItem((item, 'vod'))


    ## BUILD ITEM FUNCTIONS ##

    def buildStationItem(self, station):
        """Build a station directory item"""
        if not station: return None

        chid   = station.get('id', '')
        name   = station.get('name', 'Unknown')
        city   = station.get('city', '')
        state  = station.get('state', '')
        logo   = station.get('logoUrl', ICON)
        cover  = station.get('coverUrl', FANART)
        tags   = station.get('tags', [])

        label = '%s - %s' % (name, city) if city else name

        # Add badges
        if 'TRENDING' in tags:
            label = '[COLOR red][TRENDING][/COLOR] ' + label
        if 'ALWAYSON' in tags:
            label = '[24/7] ' + label

        infoArt = {"thumb":logo, "poster":logo, "fanart":cover, "icon":logo, "logo":logo}
        self.addDir(label, (buildStation, chid), infoArt=infoArt)
        return True


    def buildVideoItem(self, data):
        """Build a video item from API data - creates folder with video + station sections"""
        item, opt = data
        if not item: return None

        vid         = item.get('id', '')
        title       = item.get('title', 'Unknown')
        description = item.get('description', '')
        duration    = item.get('duration', 0)
        airDate     = item.get('airDate', 0)
        imageUrl    = item.get('imageUrl', CLIPART)
        videoType   = item.get('videoType', 'program')
        tags        = item.get('tags', [])

        station     = item.get('station', {})
        station_id  = station.get('id', '') if station else ''
        station_name= station.get('name', '') if station else ''
        station_city= station.get('city', '') if station else ''
        station_distance = station.get('distance', 0) if station else 0
        station_logo= station.get('logoUrl', ICON) if station else ICON
        station_cover = station.get('coverUrl', FANART) if station else FANART

        # Build label with station info
        if station_name and station_city and station_distance:
            label = '%s - %s • %d miles away' % (title, station_name, station_distance)
        elif station_name and station_city:
            label = '%s - %s, %s' % (title, station_name, station_city)
        elif station_name:
            label = '%s - %s' % (title, station_name)
        else:
            label = title

        # Check if live
        is_live = 'LIVE' in tags
        if is_live:
            label = '[COLOR red][LIVE][/COLOR] ' + label

        # Build info
        infoLabel = {
            "mediatype": "video",
            "label": label,
            "title": title,
            "plot": description,
            "duration": duration,
            "genre": ['News'] if opt not in ['sports'] else ['Sports']
        }

        infoArt = {
            "thumb": imageUrl,
            "poster": imageUrl,
            "fanart": station_cover,
            "icon": station_logo,
            "logo": station_logo
        }

        # Build context menu items for station sections
        contextMenu = []
        if station_id:
            contextMenu.append(('Browse %s' % station_name, 'RunPlugin(%s)' % ROUTER.url_for(buildStation, station_id)))

        # Create playable link (plays immediately when clicked)
        if vid:
            self.addLink(label, (playVOD, vid, videoType), infoList=infoLabel, infoArt=infoArt, contextMenu=contextMenu)
            return True

        return None


    ## API FUNCTIONS ##

    @use_cache(28)
    def getConfig(self):
        """Get NewsON configuration"""
        log('getConfig')
        return self.openURL(BASE_API + '/config', params={'platformType': 'website'})


    def getHomeData(self):
        """Get home page data"""
        log('getHomeData')
        return self.openURL(BASE_API + '/storefront/home', params={'platformType': 'website'})


    def getTrendingData(self):
        """Get trending data"""
        log('getTrendingData')
        return self.openURL(BASE_API + '/storefront/trending', params={'platformType': 'website'})


    def getSportsData(self):
        """Get sports data"""
        log('getSportsData')
        return self.openURL(BASE_API + '/storefront/sports', params={'platformType': 'website'})


    def getWhatsOnData(self):
        """Get What'sON data"""
        log('getWhatsOnData')
        return self.openURL(BASE_API + '/storefront/whatson', params={'platformType': 'website'})


    def openURL(self, url, params=None, life=datetime.timedelta(minutes=15)):
        """Open URL using custom client module"""
        try:
            log('openURL, url = %s'%(url))

            param_str = json.dumps(params) if params else ''
            cacheName = '%s.openURL, url = %s.%s'%(ADDON_NAME, url, param_str)

            cacheresponse = self.cache.get(cacheName)
            if cacheresponse:
                return json.loads(cacheresponse)

            response = client.get(url, params=params, timeout=30)

            if response and response.ok:
                data = response.json()
                self.cache.set(cacheName, json.dumps(data),
                             checksum=len(json.dumps(data)), expiration=life)
                return data
            else:
                log("openURL Failed! Status: %s"%(response.status_code if response else 'None'), xbmc.LOGERROR)
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
                return {}

        except Exception as e:
            log("openURL Failed! %s"%(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30001), ICON, 4000)
            return {}


    def playVideo(self, url_or_id, opt='live', videoType='program'):
        """Play video content"""
        log('playVideo, url_or_id = %s, opt = %s, videoType = %s'%(url_or_id, opt, videoType))

        stream_url = None

        if opt == 'vod':
            # Get stream URL from /v5api/item/{videoType}/{videoId} endpoint
            try:
                endpoint = BASE_API + '/item/%s/%s' % (videoType, url_or_id)
                log('Fetching stream from: %s' % endpoint)

                data = self.openURL(endpoint, params={'platformType': 'website'}, life=datetime.timedelta(minutes=15))

                if data:
                    sources = data.get('sources', [])
                    if sources and len(sources) > 0:
                        stream_url = sources[0].get('file', '')
                        stream_type = sources[0].get('type', 'HLS')
                        log('Found stream: %s (type: %s)' % (stream_url, stream_type))
                    else:
                        log('No sources found in API response', xbmc.LOGERROR)
                else:
                    log('Empty response from item endpoint', xbmc.LOGERROR)

            except Exception as e:
                log('Failed to fetch stream URL: %s' % str(e), xbmc.LOGERROR)

            if not stream_url:
                log('Could not find stream URL for VOD ID: %s (type: %s)'%(url_or_id, videoType), xbmc.LOGERROR)
                xbmcgui.Dialog().notification(ADDON_NAME, 'Stream not found', ICON, 4000)
                return
        else:
            stream_url = decodeString(url_or_id)

        # Play the stream
        log('Playing stream: %s' % stream_url)
        liz = xbmcgui.ListItem(path=stream_url)
        liz.setProperty('IsPlayable', 'true')
        liz.setProperty('IsInternetStream', 'true')
        xbmcplugin.setResolvedUrl(ROUTER.handle, True, liz)


    ## HELPER FUNCTIONS ##

    def poolList(self, method, items=None, args=None, chunk=25):
        """Execute method on items using thread pool"""
        log("poolList")
        results = []
        if SUPPORTS_POOL:
            pool = ThreadPool()
            if args is not None:
                results = pool.imap(method, zip(items,repeat(args)))
            elif items:
                results = pool.imap(method, items)
            pool.close()
            pool.join()
        else:
            if args is not None:
                results = [method((item, args)) for item in items]
            elif items:
                results = [method(item) for item in items]
        return filter(None, results)


    def addLink(self, name, uri=(''), infoList={}, infoArt={}, infoVideo={}, infoAudio={}, infoType='video', total=0, contextMenu=[]):
        log('addLink, name = %s'%name)
        liz = xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable','true')
        liz.setProperty('IsInternetStream','true')
        if infoList:  liz.setInfo(type=infoType, infoLabels=infoList)
        else:         liz.setInfo(type=infoType, infoLabels={"mediatype":infoType,"label":name,"title":name})
        if infoArt:   liz.setArt(infoArt)
        else:         liz.setArt({'thumb':ICON,'fanart':FANART})
        if infoVideo: liz.addStreamInfo('video', infoVideo)
        if infoAudio: liz.addStreamInfo('audio', infoAudio)
        if contextMenu: liz.addContextMenuItems(contextMenu)
        xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=False, totalItems=total)


    def addDir(self, name, uri=(''), infoList={}, infoArt={}, infoType='video'):
        log('addDir, name = %s'%name)
        liz = xbmcgui.ListItem(name)
        liz.setProperty('IsPlayable','false')
        if infoList: liz.setInfo(type=infoType, infoLabels=infoList)
        else:        liz.setInfo(type=infoType, infoLabels={"mediatype":infoType,"label":name,"title":name})
        if infoArt:  liz.setArt(infoArt)
        else:        liz.setArt({'thumb':ICON,'fanart':FANART})
        xbmcplugin.addDirectoryItem(ROUTER.handle, ROUTER.url_for(*uri), liz, isFolder=True)


    def run(self):
        ROUTER.run()
        xbmcplugin.setContent(ROUTER.handle     ,CONTENT_TYPE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(ROUTER.handle  ,xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(ROUTER.handle ,cacheToDisc=DISC_CACHE)
