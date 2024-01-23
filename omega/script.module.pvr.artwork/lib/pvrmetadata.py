"""
    This module is mainly inspired from the script.module.metadatautils from Marcel van der Veldt
    and other contributors. This modules use a subset from metadatautils reduced to PVR related content.
"""

from difflib import SequenceMatcher as SM
import simplecache

from .tools import *
from .tmdb import Tmdb
from .fanart_tv import FanartTv

from datetime import timedelta

if ADDON.getSetting('pvr_art_custom_path') == '' or ADDON.getSetting('pvr_art_custom_path') == PROFILE:
    ADDON.setSetting('pvr_art_custom_path', os.path.join(PROFILE, 'artwork'))
    xbmcvfs.mkdirs(os.path.join(PROFILE, 'artwork'))
    log('set artwork costum path to %s' % os.path.join(PROFILE, 'artwork'))

labels = list(['director', 'writer', 'genre', 'country', 'studio', 'studiologo', 'premiered', 'mpaa', 'status', 'is_db',
               'rating', 'ratings', 'ratings.imdb', 'ratings.tmdb', 'ratings.themoviedb', 'castandrole', 'description'])

win = xbmcgui.Window(10000)


def download_artwork(folderpath, artwork, dict_arttypes):
    """
        download artwork to local folder
    """
    art = {}
    if artwork and not xbmcvfs.exists(folderpath): xbmcvfs.mkdir(folderpath)
    for [item, value] in artwork.items():
        if item in dict_arttypes: art.update({item: download_image(os.path.join(folderpath, dict_arttypes[item]), value)})
        elif item == "fanarts":
            images = list()
            for count, image in enumerate(value):
                if count >= int(ADDON.getSetting('pvr_art_max_downloads')) - 1: break
                image = download_image(os.path.join(folderpath, "fanart%s.jpg" % str(count + 1)), image)
                images.append(image)
            art[item] = images
        elif item == "posters":
            images = list()
            for count, image in enumerate(value):
                if count >= int(ADDON.getSetting('pvr_art_max_downloads')) - 1: break
                image = download_image(os.path.join(folderpath, "poster%s.jpg" % str(count + 1)), image)
                images.append(image)
            art[item] = images
    return art


def download_image(filename, url):
    """
        download specific image to local folder, cache image in textures.db
    """
    if not url: return url
    if xbmcvfs.exists(filename) and filename == url: return filename
    # only overwrite if new image is different
    else:
        if xbmcvfs.exists(filename): xbmcvfs.delete(filename)
        if xbmcvfs.copy(url, filename):

            # tell kodi texture cache to refresh a particular image
            import sqlite3
            dbpath = xbmcvfs.translatePath("special://database/Textures13.db")
            connection = sqlite3.connect(dbpath, timeout=30, isolation_level=None)

            try:
                cache_image = connection.execute('SELECT cachedurl FROM texture WHERE url = ?', (filename,)).fetchone()[0]
                if cache_image and isinstance(cache_image, str):
                    if xbmcvfs.delete("special://profile/Thumbnails/%s" % cache_image):
                        connection.execute('DELETE FROM texture WHERE url = ?', (filename,))
                connection.close()
            except Exception as e:
                log(str(e), xbmc.LOGERROR)
            finally:
                del connection
            return filename
    return url


def manual_set_artwork(artwork, dict_arttypes):
    """
        Allow user to manually select the artwork with a select dialog
        show dialogselect with all artwork options
    """
    changemade = False
    abort = False

    while not abort:
        listitems = list()
        for arttype in dict_arttypes:
            img = url_unquote(artwork.get(arttype, ""))
            listitem = xbmcgui.ListItem(label=arttype, label2=img)
            listitem.setArt({'icon': img})
            listitem.setProperty("icon", img)
            listitems.append(listitem)
        dialog = xbmcgui.Dialog().select(xbmc.getLocalizedString(13511), list=listitems, useDetails=True)
        if dialog == -1:
            abort = True
        else:
            # show results for selected art type
            artoptions = []
            selected_item = listitems[dialog]
            image = selected_item.getProperty("icon")
            label = selected_item.getLabel()
            subheader = "%s: %s" % (xbmc.getLocalizedString(13511), label.capitalize())
            if image:
                # current image
                listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(13512), label2=image)
                listitem.setArt({'icon': image})
                listitem.setProperty("icon", image)
                artoptions.append(listitem)
                # none option
                listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(231))
                listitem.setArt({'icon': "DefaultAddonNone.png"})
                listitem.setProperty("icon", "DefaultAddonNone.png")
                artoptions.append(listitem)

            # browse option
            listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(1024))
            listitem.setArt({'icon': "DefaultFolder.png"})
            listitem.setProperty("icon", "DefaultFolder.png")
            artoptions.append(listitem)

            # add remaining images as option
            allarts = artwork.get(label + "s", [])
            for item in allarts:
                listitem = xbmcgui.ListItem(label=item)
                listitem.setArt({'icon': item})
                listitem.setProperty("icon", item)
                artoptions.append(listitem)

            dialog = xbmcgui.Dialog().select(subheader, list=artoptions, useDetails=True)
            if image and dialog == 1:
                # set image to None
                artwork[label] = ""
                changemade = True
            elif (image and dialog > 2) or (not image and dialog > 0):
                # one of the optional images is selected as new default
                artwork[label] = artoptions[dialog].getProperty("icon")
                changemade = True
            elif (image and dialog == 2) or (not image and dialog == 0):
                # manual browse...
                image = xbmcgui.Dialog().browse(2, subheader, 'files', mask='.gif|.png|.jpg')
                if image:
                    artwork[label] = image
                    changemade = True
    return changemade, artwork


def create_castandrole(cast):
    """
        creates a list in format 'actor (role)'
    """
    cast_and_role = list()
    for item in cast:
        if item['role']: cast_and_role.append('%s (%s)' % (item['name'], item['role']))
    return cast_and_role


def get_studiologo(studios):
    for studio in studios:
        studiologo = '%s%s.png' % (xbmc.getInfoLabel('Skin.String(studiologos.path)'), studio)
        if xbmcvfs.exists(studiologo): return studiologo
    return ''


def get_cache_lifetime():
    try:
        return int(ADDON.getSetting('cache_lifetime').split()[0])
    except IndexError:
        return 180


class PVRMetaData(object):

    def __init__(self):
        self.cache = simplecache.SimpleCache()
        self.cache_str = ''
        self.tmdb = Tmdb()
        self.dict_arttypes = {'fanart': 'fanart.jpg', 'thumb': 'folder.jpg', 'discart': 'discart.png',
                              'banner': 'banner.jpg', 'logo': 'logo.png', 'clearlogo': 'clearlogo.png',
                              'clearart': 'clearart.png', 'characterart': 'characterart.png', 'poster': 'poster.jpg',
                              'landscape': 'landscape.jpg'}

        self.dict_providers = {'imdb': 'IMDB', 'themoviedb': 'TMDB', 'tmdb': 'TMDB'}
        self.prefix = 'PVR.Artwork'

        log('Initialized', type=xbmc.LOGINFO)

    def lookup_local_recording(self, title):
        """
            lookup actual recordings to get details for grouped recordings
            also grab a thumb provided by the pvr
        """
        cache = self.cache.get("recording.%s" % title)
        if cache:
            return cache
        details = dict()
        query = {'method': 'PVR.GetRecordings',
                 'params': {'properties': ['title', 'file', 'channel', 'art', 'icon', 'genre']}}
        result = jsonrpc(query)
        for item in result['recordings']:
            if title == item["title"] or title in item["file"]:

                # grab thumb from pvr
                if item.get("art"): details.update({'thumbnail': item['art'].get('thumb')})
                # ignore tvheadend thumb as it returns the channellogo
                elif item.get("icon") and "imagecache" not in item["icon"]: details.update({'thumbnail': item['icon']})

                details.update({'channel': item['channel'], 'genre': ' / '.join(item['genre'])})
                break

        if details: self.cache.set('recording.%s' % title, details, expiration=timedelta(days=get_cache_lifetime()))
        return details

    def lookup_custom_path(self, searchtitle, title, delete_content=False):
        """
            looks up a custom directory if it contains a subdir for the title
        """

        # ToDo: Grab artists if an .artists folder exists

        details = dict({'art': {}})
        fanarts = list()
        posters = list()
        title_path = self.get_custom_path(searchtitle, title)
        if title_path and xbmcvfs.exists(title_path):
            # we have found a folder for the title, look for artwork
            files = xbmcvfs.listdir(title_path)[1]
            if delete_content:
                rmdirs(title_path, 0, force=True)
            else:
                for image in files:
                    if image.split('.')[0] in self.dict_arttypes:
                        details['art'].update({image.split('.')[0]: os.path.join(title_path, image)})
                for n in range(1, 6):
                    if ('fanart%s.jpg' % n) in files: fanarts.append(os.path.join(title_path, 'fanart%s.jpg' % n))
                    if ('poster%s.jpg' % n) in files: posters.append(os.path.join(title_path, 'poster%s.jpg' % n))
                details['art'].update({'fanarts': fanarts})
                details['art'].update({'posters': posters})

        details.update({'path': title_path})
        return details

    def lookup_local_library(self, title, media_type):
        """
            lookup the title in the local video db
        """
        log('look up in local databases for \'%s\'' % title)
        details = dict()

        if not media_type or media_type == "tvshow":
            query = {'method': 'VideoLibrary.GetTVShows',
                     'params': {'properties': ['cast', 'file', 'art', 'genre', 'studio', 'premiered', 'mpaa',
                                               'ratings', 'plot'],
                                'limits': {'start': 0, 'end': 1},
                                'filter': {'operator': 'is', 'field': 'title', 'value': title}
                                }
                     }
            result = jsonrpc(query)
            if result and len(result['tvshows']) > 0:
                details.update({'cast': result['tvshows'][0]['cast'], 'path': result['tvshows'][0]['file'],
                                'art': result['tvshows'][0]['art'], 'genre': result['tvshows'][0]['genre'],
                                'studio': result['tvshows'][0]['studio'], 'description': result['tvshows'][0]['plot'],
                                'premiered': result['tvshows'][0]['premiered'], 'mpaa': result['tvshows'][0]['mpaa'],
                                'ratings': result['tvshows'][0]['ratings'], 'media_type': 'tvshow',
                                'is_db': MEDIA_LOCAL})
                media_type = 'tvshow'

        if not details and (not media_type or media_type == "movie"):
            query = {'method': 'VideoLibrary.GetMovies',
                     'params': {'properties': ['cast', 'file', 'art', 'director', 'writer', 'genre', 'country',
                                               'studio', 'premiered', 'mpaa', 'ratings'],
                                'limits': {'start': 0, 'end': 1},
                                'filter': {'operator': 'is', 'field': 'title', 'value': title}
                                }
                     }
            result = jsonrpc(query)
            if result and len(result['movies']) > 0:
                details.update({'cast': result['movies'][0]['cast'], 'path': result['movies'][0]['file'],
                                'art': result['movies'][0]['art'], 'director': result['movies'][0]['director'],
                                'writer': result['movies'][0]['writer'], 'genre': result['movies'][0]['genre'],
                                'country': result['movies'][0]['country'], 'studio': result['movies'][0]['studio'],
                                'premiered': result['movies'][0]['premiered'], 'mpaa': result['movies'][0]['mpaa'],
                                'ratings': result['movies'][0]['ratings'], 'media_type': 'movie',
                                'is_db': MEDIA_LOCAL})
                media_type = 'movie'

        # unquote and cleanup data, create CastAndRole
        if 'cast' in details:
            details.update({'castandrole': create_castandrole(details['cast'])})
            details.pop('cast')

        # get studio logos graphics from studios depending on ressource images
        if details.get('studio', False): details.update({'studiologo': get_studiologo(details['studio'])})

        if 'art' in details:
            # repack fanarts, posters, fanart, poster, banner, clearart into list/single objects and unquote item values
            fanarts = list()
            posters = list()
            artworks = dict()

            artwork_fanarts = ['fanart1', 'fanart2', 'fanart3', 'fanart4', 'fanart5']
            artwork_posters = ['poster1', 'poster2', 'poster3', 'poster4', 'poster5']
            artwork_others = ['poster', 'fanart', 'banner', 'clearlogo', 'clearart', 'logo']

            for key in details['art'].keys():
                if key in artwork_fanarts: fanarts.append(url_unquote(details['art'][key]))
                if key in artwork_posters: posters.append(url_unquote(details['art'][key]))
                if key in artwork_others: artworks.update({key: url_unquote(details['art'][key])})

            details.pop('art')
            details.update({'art': {'posters': posters, 'fanarts': fanarts}})
            details['art'].update(extend_dict(details['art'], artworks))

        if details and ADDON.getSetting('log_results') == 'true':
            log('fetched data for \'%s\' in %s database:' % (title, media_type), pretty_print=details)
        else:
            log('no results in local databases', type=xbmc.LOGINFO)

        return details

    @staticmethod
    def get_custom_path(searchtitle, title):
        """
            locate custom folder on disk as pvrart location
        """
        title_path = ""
        custom_path = ADDON.getSetting("pvr_art_custom_path")
        dirs = xbmcvfs.listdir(custom_path)[0]

        for strictness in [1, 0.95, 0.9, 0.8]:
            for directory in dirs:
                curpath = os.path.join(custom_path, directory)
                for item in [title, searchtitle]:
                    match = SM(None, item, directory).ratio()
                    if match >= strictness: return curpath

        if not title_path and ADDON.getSetting("pvr_art_download").lower() == "true":
            title_path = os.path.join(custom_path, normalize_string(title))
        return title_path

    @staticmethod
    def cleanup_title(title):
        """
            common logic to get a proper searchtitle from crappy titles provided by pvr
        """
        # split characters - split on common splitters beginning from right
        splitters = ADDON.getSetting("pvr_art_splittitlechar").split("|")

        for splitchar in splitters:
            if len(title.split(splitchar)) > 1:
                title = splitchar.join(title.split(splitchar)[:-1])
            else:
                title = title.split(splitchar)[0]

        # replace common chars and words and return title
        return re.sub(ADDON.getSetting("pvr_art_replace_by_space"), ' ', title).strip()

    @staticmethod
    def pvr_proceed_lookup(title, channel, genre, recordingdetails):
        """
            perform some checks if we can proceed with the lookup
        """
        filters = list()
        channel = pure_channelname(channel)
        if not title:
            filters.append("Title is empty")

        for item in ADDON.getSetting("pvr_art_ignore_titles").split(", "):
            if item and item.lower() == title.lower():
                filters.append("Title is in list of titles to ignore")

        for item in ADDON.getSetting("pvr_art_ignore_channels").split(", "):
            if item and item.lower() == channel.lower():
                filters.append("Channel is in list of channels to ignore")

        for item in ADDON.getSetting("pvr_art_ignore_genres").split(", "):
            if genre and item and item.lower() in genre.lower():
                filters.append("Genre is in list of genres to ignore")

        if ADDON.getSetting("pvr_art_ignore_commongenre") == "true":
            # skip common genres like sports, weather, news etc.
            genre = genre.lower()
            kodi_strings = [19516, 19517, 19518, 19520, 19548, 19549, 19551,
                            19552, 19553, 19554, 19555, 19556, 19557, 19558, 19559]
            for kodi_string in kodi_strings:
                kodi_string = xbmc.getLocalizedString(kodi_string).lower()
                if (genre and (genre in kodi_string or kodi_string in genre)) or kodi_string in title:
                    filters.append("Common genres like weather/sports are set to be ignored")
        if ADDON.getSetting("pvr_art_recordings_only") == "true" and not recordingdetails:
            filters.append("PVR Artwork is enabled for recordings only")
        if filters:
            log("Filter active for title: %s (%s): %s" % (title, channel, ' - '.join(filters)))
            return True
        else:
            return False

    @staticmethod
    def get_mediatype_from_genre(genre):
        """guess media type from genre for better matching"""
        media_type = ""
        if "movie" in genre.lower() or "film" in genre.lower():
            media_type = "movie"
        if "show" in genre.lower():
            media_type = "tvshow"
        if not media_type:

            # Kodi defined movie genres
            kodi_genres = [19500, 19507, 19508, 19602, 19603]
            for kodi_genre in kodi_genres:
                if xbmc.getLocalizedString(kodi_genre) in genre:
                    media_type = "movie"
                    break
        if not media_type:

            # Kodi defined tvshow genres
            kodi_genres = [19505, 19516, 19517, 19518, 19520, 19532, 19533, 19534, 19535, 19548, 19549,
                           19550, 19551, 19552, 19553, 19554, 19555, 19556, 19557, 19558, 19559]
            for kodi_genre in kodi_genres:
                if xbmc.getLocalizedString(kodi_genre) in genre:
                    media_type = "tvshow"
                    break
        return media_type

    @staticmethod
    def calc_duration(duration):
        """
            helper to get a formatted duration
        """
        if isinstance(duration, str) and ":" in duration:
            hours, mins = duration.split(':')
            return {'Duration': duration, 'Runtime': int(hours) * 60 + int(mins)}
        else:
            hours = str(int(duration) // 60)
            _m = int(duration) % 60
            mins = str(_m) if _m > 9 else '0' + str(_m)
            return {'Duration': '%s:%s' % (hours, mins), 'Runtime': int(duration)}

    def get_tmdb_details(self, imdb_id=None, tvdb_id=None, title=None, year=None, media_type=None,
                         preftype=None, manual_select=False):
        """
            returns details from tmdb
        """
        log('Fetch items from tmdb: ImdbId: %s, TvdbId: %s, title: %s, year: %s, '
            'mediatype: %s, preferred type: %s, manual selection: %s' %
            (imdb_id, tvdb_id, title, year, media_type, preftype, manual_select))

        result = dict()
        if imdb_id:
            result = self.tmdb.get_videodetails_by_externalid(imdb_id, "imdb_id")
        elif tvdb_id:
            result = self.tmdb.get_videodetails_by_externalid(tvdb_id, "tvdb_id")
        elif title and media_type in ["movies", "setmovies", "movie"]:
            result = self.tmdb.search_movie(title, year, manual_select=manual_select)
        elif title and media_type in ["tvshows", "tvshow"]:
            result = self.tmdb.search_tvshow(title, year, manual_select=manual_select)
        elif title:
            result = self.tmdb.search_video(title, year, preftype=preftype, manual_select=manual_select)

        return result

    def get_pvr_artwork(self, prefix, title, channel="", genre="", year="",
                        manual_select=False, manual_set=False, ignore_cache=False):
        """
            collect full metadata and artwork for pvr entries (MAINFUNCTION)
            parameters: title (required)
            channel: channel name (required)
            year: year or date (optional)
            genre: (optional)
            the more optional parameters are supplied, the better the search results
        """
        # try cache first
        # use cleantitle when searching cache

        if not title: return False
        if not prefix: prefix = self.prefix

        win.setProperty("%s.Lookup" % prefix, "busy")
        self.clear_properties(prefix)

        searchtitle = self.cleanup_title(title.lower())
        self.cache_str = "%s.%s" % (DB_PREFIX, searchtitle)
        cache = self.cache.get(self.cache_str)

        if cache and not (manual_select or ignore_cache):
            log("fetch data from cache: %s" % self.cache_str, type=xbmc.LOGINFO)
            if ADDON.getSetting('log_results') == 'true':
                log('lookup for title: %s - final result:' % searchtitle, pretty_print=cache)
            if manual_set: return cache
            return self.set_art_and_labels(prefix, cache)

        else:
            # no cache - start our lookup adventure
            log("start lookup: %s" % self.cache_str)

            # workaround for recordings
            recording = self.lookup_local_recording(title)
            art = ''
            if recording:
                art = recording['thumbnail']
                if not (channel and genre):
                    genre = recording["genre"]
                    channel = recording["channel"]

            details = dict({'title': title, 'channel': channel, 'genre': genre,
                            'media_type': '', 'art': dict()})
            if art: details.update({'thumbnail': art})

            # filter genre unknown/other
            if not genre or genre.split(" / ")[0] in xbmc.getLocalizedString(19499).split(" / "):
                details.update({'genre': list()})
                genre = ""
                log("Genre is unknown, ignore....")
            else:
                details.update({'genre': genre.split(' / '), 'media_type': self.get_mediatype_from_genre(genre)})

            # only continue if we pass our basic checks
            excluded = self.pvr_proceed_lookup(title, channel, genre, recording)
            proceed = False
            if excluded and manual_select:
                # warn user about active skip filter
                proceed = xbmcgui.Dialog().yesno(message=LOC(32027), heading=LOC(750))
            if excluded:
                if not manual_select: return self.reset_busy_state(prefix)
                if not proceed: return self.reset_busy_state(prefix)

            # if manual lookup get the title from the user
            if manual_select:
                searchtitle = xbmcgui.Dialog().input(xbmc.getLocalizedString(16017), searchtitle,
                                                     type=xbmcgui.INPUT_ALPHANUM)
                if not searchtitle:
                    log('manual selection aborted')
                    return self.reset_busy_state(prefix)

            # if manual lookup and no mediatype, ask the user
            if manual_select and not details["media_type"]:
                choice = xbmcgui.Dialog().yesnocustom(LOC(32022), LOC(32041) % searchtitle, LOC(32015),
                                                      nolabel=LOC(32043), yeslabel=LOC(32042))
                if choice == 0: details["media_type"] = "tvshow"
                elif choice == 1: details["media_type"] = "movie"

            # append thumb from recordingdetails
            if recording and recording.get("thumbnail"): details["art"]["thumb"] = recording["thumbnail"]

            # lookup movie/tv library
            if not manual_select and ADDON.getSetting('pvr_art_custom') == 'true':
                details = extend_dict(details, self.lookup_local_library(searchtitle, details["media_type"]))
                if details.get('is_db', False):

                    if ADDON.getSetting('log_results') == 'true':
                        log('lookup for title: %s - final result:' % searchtitle, pretty_print=details)

                    log("cache data (expire in %s days) - %s " % (get_cache_lifetime(), self.cache_str))
                    self.cache.set(self.cache_str, details, expiration=timedelta(days=get_cache_lifetime()))
                    return self.set_art_and_labels(prefix, details)

                # lookup custom path
            if not manual_select: details = extend_dict(details, self.lookup_custom_path(searchtitle, title))
            else: details.update(self.lookup_custom_path(searchtitle, title, delete_content=True))

            # do TMDB scraping if enabled and no arts in previous lookups
            if ADDON.getSetting("use_tmdb").lower() == "true" and ADDON.getSetting('tmdb_apikey'):

                log("scraping metadata from TMDB for title: %s (media type: %s)" %
                    (searchtitle, details["media_type"]), type=xbmc.LOGINFO)
                tmdb_result = self.get_tmdb_details(title=searchtitle, preftype=details["media_type"], year=year,
                                                    manual_select=manual_select)
                if tmdb_result:
                    # Discard online art form tmdb if local art is present and not manual select
                    if details.get('art', False) and not manual_select: tmdb_result.pop('art')
                    details = extend_dict(details, tmdb_result)
                    details["media_type"] = tmdb_result["media_type"]
                elif ignore_cache:
                    xbmcgui.Dialog().notification(LOC(32001), LOC(32021), xbmcgui.NOTIFICATION_WARNING)

                thumb = ''
                if 'thumbnail' in details: thumb = details["thumbnail"]
                else:
                    for [item, value] in details['art'].items():
                        if item == 'fanart': thumb = value
                        elif item == 'poster': thumb = value
                        if thumb: break

                if thumb: details.update({'thumbnail': thumb})

                # get additional fanart from fanart.tv if enabled
                if ADDON.getSetting("use_fanart_tv").lower() == "true" and ADDON.getSetting('fanart_apikey'):

                    FTv = FanartTv()
                    if details.get('media_type', False):
                        id = details.get('tmdb_id', None) if details['media_type'] == 'movie' else details.get('tvdb_id', None)
                        additional_fanart = FTv.get_fanarts(details.get('media_type'), id)

                        if additional_fanart:
                            for key in additional_fanart.keys():
                                if not details['art'].get(key, False): details['art'].update({key: additional_fanart[key]})
                                elif ADDON.getSetting('prefer_fanart_tv').lower() == 'true':
                                    details['art'].update({key: additional_fanart[key]})
                                    log('overwrite TMDB %s with item from fanart.tv due settings' % key)
                                else:
                                    continue

                # download artwork to custom folder
                if ADDON.getSetting("pvr_art_download").lower() == "true":
                    details.update({'art': download_artwork(details['path'], details["art"], self.dict_arttypes)})

            if details.get("runtime", False): details.update({'runtime': self.calc_duration(details["runtime"] / 60)})
            if details.get('released', False): details.update({'premiered': convert_date(details.get('released'))})
            elif details.get('premiered', False): details.update({'premiered': convert_date(details.get('premiered'))})
            if details.get('cast', False):
                details.update({'castandrole': create_castandrole(details['cast'])})
                details.pop('cast')

            if ADDON.getSetting('log_results') == 'true':
                log('lookup for title: %s - final result:' % searchtitle, pretty_print=details)

            # get studio logos graphics from studios depending on ressource images
            if details.get('studio', False): details.update({'studiologo': get_studiologo(details['studio'])})

        # always store result in cache
        log("store data in cache (expire in %s days) - %s " % (get_cache_lifetime(), self.cache_str))
        self.cache.set(self.cache_str, details, expiration=timedelta(days=get_cache_lifetime()))
        return self.set_art_and_labels(prefix, details)

    # Main entry from context menu call
    # Do not remove

    def pvr_artwork_options(self, prefix, title, channel, genre, year):
        """
            show options for pvr artwork
        """

        # Refresh item (auto lookup), Refresh item (manual lookup), Choose art
        options = list([LOC(32028), LOC(32029), LOC(32036)])
        channel = pure_channelname(channel)

        ignorechannels = split_addonsetting('pvr_art_ignore_channels', ', ')
        ignoretitles = split_addonsetting('pvr_art_ignore_titles', ', ')
        ignoregenres = split_addonsetting('pvr_art_ignore_genres', ', ')
        genres = genre.split(' / ')

        if channel in ignorechannels:
            options.append(LOC(32030))  # Remove channel from ignore list
        else:
            options.append(LOC(32031))  # Add channel to ignore list
        if title in ignoretitles:
            options.append(LOC(32032))  # Remove title from ignore list
        else:
            options.append(LOC(32033))  # Add title to ignore list
        for genre in genres:
            if genre in ignoregenres:
                if LOC(32046) not in options: options.append(LOC(32046))  # Remove genre(s) from ignorelist
            else:
                if LOC(32047) not in options: options.append(LOC(32047))  # Add genre(s) from ignorelist

        options.append(LOC(32034))  # Open addon settings

        dialog = xbmcgui.Dialog().select(LOC(32035), options)
        if dialog == 0:
            # Refresh item (auto lookup)
            #
            # FOR TESTING CACHE MECHANISM SET 'IGNORE_CACHE' TO FALSE !!!
            #
            log('Auto lookup for title: %s (%s), channel: %s, genre: %s' % (title, year, channel, genre))
            self.get_pvr_artwork(prefix, title=title, channel=channel, genre=genre, year=year,
                                 ignore_cache=True, manual_select=False)
        elif dialog == 1:
            # Refresh item (manual lookup)
            log('Manual lookup for title: %s (%s), channel: %s, genre: %s' % (title, year, channel, genre))
            self.get_pvr_artwork(prefix, title=title, channel=channel, genre=genre, year=year,
                                 ignore_cache=True, manual_select=True)
        elif dialog == 2:
            # Choose art
            self.manual_set_pvr_artwork(prefix, title, channel, genre)
        elif dialog == 3:
            # Add/remove channel to ignore list
            if channel in ignorechannels:
                ignorechannels.remove(channel)
            else:
                ignorechannels.append(channel)
            ADDON.setSetting("pvr_art_ignore_channels", ', '.join(ignorechannels))
        elif dialog == 4:
            # Add/remove title to ignore list
            if title in ignoretitles:
                ignoretitles.remove(title)
            else:
                ignoretitles.append(title)
            ADDON.setSetting("pvr_art_ignore_titles", ', '.join(ignoretitles))
        elif dialog == 5:
            # Add/remove genre(s) to ignore list
            for genre in genres:
                if genre in ignoregenres:
                    ignoregenres.remove(genre)
                else:
                    ignoregenres.append(genre)
            ADDON.setSetting("pvr_art_ignore_genres", ', '.join(ignoregenres))
        elif dialog == 6:
            # Open addon settings
            xbmc.executebuiltin("Addon.OpenSettings(%s)" % ADDON_ID)

    def manual_set_pvr_artwork(self, prefix, title, channel, genre):
        """manual override artwork options"""

        details = self.get_pvr_artwork(prefix, title=title, channel=channel, genre=genre, manual_set=True)

        # show dialogselect with all artwork option
        changemade, artwork = manual_set_artwork(details["art"], self.dict_arttypes)
        if changemade:
            details["art"] = artwork
            # save results in cache
            log("store data in cache (expire in %s days) - %s " % (get_cache_lifetime(), self.cache_str))
            self.cache.set(self.cache_str, details, expiration=timedelta(days=get_cache_lifetime()))
        return self.set_art_and_labels(prefix, details)

    def clear_properties(self, prefix):

        for item in self.dict_arttypes:
            win.clearProperty('%s.%s' % (prefix, item))
            for i in range(1, 6): win.clearProperty('%s.fanart%s' % (prefix, i))

        for label in labels: win.clearProperty('%s.ListItem.%s' % (prefix, label))

        win.clearProperty('%s.present' % prefix)
        xbmc.log('Properties of %s cleared' % prefix)

    def set_properties(self, prefix, artwork):

        # set artwork properties
        for item in artwork:
            if item in self.dict_arttypes: win.setProperty('%s.%s' % (prefix, item), artwork[item])

        # Lookup for fanarts/posters list
        fanarts = artwork.get('fanarts', False)
        posters = artwork.get('posters', False)
        cf = 0
        if fanarts:
            for cf, fanart in enumerate(fanarts):
                if cf > 5: break
                win.setProperty('%s.fanart%s' % (prefix, str(cf + 1)), fanart)
            cf += 1
        if posters and cf < 2:
            for count, fanart in enumerate(posters):
                if count > 5: break
                win.setProperty('%s.fanart%s' % (prefix, str(cf + count + 1)), fanart)

    def set_art_and_labels(self, prefix, details):

        if details.get('art', False):
            self.set_properties(prefix, details['art'])
            win.setProperty('%s.present' % prefix, 'true')

        for label in labels:

            # handle special part 'ratings'

            if label == 'ratings' and details.get(label, False):
                allratings = list()
                for key in self.dict_providers:
                    if details[label].get(key, False):
                        (property, value) = '%s.ListItem.%s.%s' % (prefix, label, key), \
                                        str(round(details[label][key].get('rating', 0), 1))
                        win.setProperty(property, value)
                        allratings.append('%s (%s)' % (round(details[label][key].get('rating', 0), 1),
                                                       self.dict_providers[key]))
                win.setProperty('%s.ListItem.rating' % prefix, ', '.join(allratings))

            elif details.get(label, False) and details[label]:
                value = str(details[label])
                if isinstance(details[label], list): value = ', '.join(details[label])
                win.setProperty('%s.ListItem.%s' % (prefix, label), value)

        win.clearProperty("%s.Lookup" % prefix)
        return True

    def reset_busy_state(self, prefix):
        win.clearProperty("%s.Lookup" % prefix)
        return False