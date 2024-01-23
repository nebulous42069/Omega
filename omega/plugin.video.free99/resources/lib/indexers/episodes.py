# -*- coding: utf-8 -*-

import re
import os
import sys
import datetime

import simplejson as json
import six
from six.moves import range, urllib_parse

try:
    #from infotagger.listitem import ListItemInfoTag
    from resources.lib.modules.listitem import ListItemInfoTag
except:
    pass

from resources.lib.modules import tmdb_utils
from resources.lib.modules import trakt
from resources.lib.modules import bookmarks
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cache
from resources.lib.modules import playcount
from resources.lib.modules import workers
from resources.lib.modules import views
#from resources.lib.modules import log_utils

params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()
action = params.get('action')
control.moderator()
kodi_version = control.getKodiVersion()


class seasons:
    def __init__(self):
        self.list = []
        self.datetime = datetime.datetime.utcnow()
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.addon_caching = control.setting('addon.caching') or 'true'
        self.lang = control.apiLanguage()['tmdb'] or 'en'
        self.specials = control.setting('tv.specials') or 'false'
        self.shownoyear = control.setting('show.noyear') or 'false'
        self.showunaired = control.setting('showunaired') or 'true'
        self.unairedcolor = control.setting('unaired.color')
        if self.unairedcolor == '':
            self.unairedcolor = 'darkred'
        self.tmdb_key = control.setting('tmdb.api')
        if self.tmdb_key == '' or self.tmdb_key == None:
            self.tmdb_key = '3d000491a0f37d4962d02bdb062af037'
        self.tmdb_link = 'https://api.themoviedb.org'
        self.original_artwork = control.setting('original.artwork') or 'false'
        if self.original_artwork == 'true':
            self.tmdb_image_link = 'https://image.tmdb.org/t/p/original'
        else:
            self.tmdb_image_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.tmdb_info_link = self.tmdb_link + '/3/tv/%s?api_key=%s&language=en-US&append_to_response=credits,content_ratings,external_ids' % ('%s', self.tmdb_key)
        self.info_tvshows_source = control.setting('info.tvshows.source') or '0'


    def trakt_info(self, tvshowtitle, year, imdb, tmdb, meta=None, lite=False):
        try:
            tvdb = '0'
            if imdb == '0' and not tmdb == '0':
                try:
                    temp_item = tmdb_utils.get_tvshow_external_ids(tmdb)
                    imdb = temp_item.get('imdb_id', '0') or '0'
                except:
                    pass
            if imdb == '0' and tmdb == '0':
                try:
                    temp_item = trakt.SearchTVShow(tvshowtitle, year)
                    if temp_item[0]['show']['title'].lower() != tvshowtitle.lower() or int(temp_item[0]['show']['year']) != int(year):
                        raise Exception()
                    imdb = temp_item[0]['show']['ids'].get('imdb', '0') or '0'
                    tmdb = temp_item[0]['show']['ids'].get('tmdb', '0') or '0'
                    if tvdb == '0':
                        tvdb = temp_item[0]['show']['ids'].get('tvdb', '0') or '0'
                except:
                    pass
            if not imdb or imdb == '0':
                raise Exception()
            item = trakt.getTVShowSummary(imdb, full=True)
            if not item:
                raise Exception()
            if not tmdb or tmdb == '0':
                tmdb = item.get('ids', {}).get('tmdb', '0')
            if not tvdb or tvdb == '0':
                tvdb = item.get('ids', {}).get('tvdb', '0')
            studio = trakt.getStudio(imdb, 'shows')
            if studio and studio != []:
                studio = [x['name'] for x in studio]
            else:
                studio = []
            genre = item.get('genres', [])
            if genre and genre != []:
                genre = [x.title() for x in genre]
                #genre = ' / '.join(genre).strip()
            else:
                genre = []
            duration = item.get('runtime', '0')
            duration = str(duration)
            if not duration or duration == '0':
                duration = '0'
            mpaa = item.get('certification', '0')
            if not mpaa or mpaa == '0':
                mpaa = '0'
            status = item.get('status', '0')
            if not status or status == '0':
                status = '0'
            people = trakt.getPeople(imdb, 'shows')
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
            show_plot = item.get('overview', '0')
            if not show_plot or show_plot == '0':
                show_plot = '0'
            else:
                show_plot = client_utils.replaceHTMLCodes(show_plot)
            unaired = ''
            clearlogo = clearart = landscape = '0'
            if meta:
                _meta = json.loads(urllib_parse.unquote_plus(meta))
                show_poster, fanart, banner, clearlogo, clearart, landscape = _meta['poster'], _meta['fanart'], _meta['banner'], _meta['clearlogo'], _meta['clearart'], _meta['landscape']
            else:
                show_poster, fanart, banner = tmdb_utils.get_tmdb_artwork(tmdb, 'tv')
            seasons = trakt.getSeasonsSummary(imdb, full=True)
            if self.specials == 'false':
                seasons = [s for s in seasons if not s['number'] == 0]
            for item in seasons:
                try:
                    season = str(int(item['number']))
                    premiered = item.get('first_aired', '0')
                    if premiered and premiered != '0':
                        premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                    if status == 'Ended':
                        pass
                    elif not premiered or premiered == '0':
                        if self.shownoyear != 'true':
                            raise Exception()
                    elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception()
                    plot = item.get('overview', '0')
                    if not plot or plot == '0':
                        plot = show_plot
                    else:
                        plot = client_utils.replaceHTMLCodes(plot)
                    season_poster, season_fanart, season_banner = tmdb_utils.get_tmdb_artwork(tmdb, 'tv', season=season)
                    poster = season_poster if not season_poster == '0' else show_poster
                    fanart = season_fanart if not season_fanart == '0' else fanart
                    banner = season_banner if not season_banner == '0' else banner
                    self.list.append({'season': season, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre, 'duration': duration, 'mpaa': mpaa, 'castwiththumb': castwiththumb,
                        'plot': plot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'banner': banner,'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'unaired': unaired}
                    )
                except:
                    #log_utils.log('trakt_info', 1)
                    pass
        except:
            #log_utils.log('trakt_info', 1)
            pass
        return self.list


    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, meta=None, lite=False):
        try:
            tvdb = '0'
            if tmdb == '0' and not imdb == '0':
                try:
                    temp_item = tmdb_utils.find_tvshow_by_external_source(imdb=imdb)
                    tmdb = temp_item.get('id', '0') or '0'
                except:
                    pass
            if imdb == '0' and tmdb == '0':
                try:
                    temp_item = trakt.SearchTVShow(tvshowtitle, year)
                    if temp_item[0]['show']['title'].lower() != tvshowtitle.lower() or int(temp_item[0]['show']['year']) != int(year):
                        raise Exception()
                    imdb = temp_item[0]['show']['ids'].get('imdb', '0') or '0'
                    tmdb = temp_item[0]['show']['ids'].get('tmdb', '0') or '0'
                    if tvdb == '0':
                        tvdb = temp_item[0]['show']['ids'].get('tvdb', '0') or '0'
                except:
                    pass
            if not tmdb or tmdb == '0':
                raise Exception()
            seasons_url = self.tmdb_info_link % tmdb
            item = client.scrapePage(seasons_url, timeout='30').json()
            if not item:
                raise Exception()
            if not imdb or imdb == '0':
                imdb = item.get('external_ids', {}).get('imdb_id', '0')
            if not tvdb or tvdb == '0':
                tvdb = item.get('external_ids', {}).get('tvdb_id', '0')
            studio = item.get('networks', [])
            if studio and studio != []:
                studio = [x['name'] for x in studio]
            else:
                studio = []
            genre = item.get('genres', [])
            if genre and genre != []:
                genre = [x['name'] for x in genre]
                #genre = ' / '.join(genre).strip()
            else:
                genre = []
            try:
                duration = item['episode_run_time'][0]
                duration = str(duration)
            except:
                duration = '0'
            if not duration or duration == '0':
                duration = '0'
            status = item.get('status', '0')
            if not status or status == '0':
                status = '0'
            try:
                mpaa = item['content_ratings']['results']
                mpaa = [x['rating'] for x in mpaa if x['iso_3166_1'] == 'US'][0]
            except:
                mpaa = '0'
            if not mpaa or mpaa == '0':
                mpaa = '0'
            show_plot = item.get('overview', '0')
            if not show_plot or show_plot == '0':
                show_plot = '0'
            else:
                show_plot = client_utils.replaceHTMLCodes(show_plot)
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
            unaired = ''
            banner = clearlogo = clearart = landscape = '0'
            if meta:
                _meta = json.loads(urllib_parse.unquote_plus(meta))
                show_poster, fanart, banner, clearlogo, clearart, landscape = _meta['poster'], _meta['fanart'], _meta['banner'], _meta['clearlogo'], _meta['clearart'], _meta['landscape']
            else:
                show_poster = item.get('poster_path', '')
                if show_poster and show_poster != '':
                    if self.original_artwork == 'true':
                        show_poster = self.tmdb_image_link + show_poster
                    else:
                        show_poster = self.tmdb_image_link % ('500', show_poster)
                else:
                    show_poster = '0'
                fanart = item.get('backdrop_path', '')
                if fanart and fanart != '':
                    if self.original_artwork == 'true':
                        fanart = self.tmdb_image_link + fanart
                    else:
                        fanart = self.tmdb_image_link % ('1280', fanart)
                else:
                    fanart = '0'
            seasons = item['seasons']
            if self.specials == 'false':
                seasons = [s for s in seasons if not s['season_number'] == 0]
            for item in seasons:
                try:
                    season = str(int(item['season_number']))
                    premiered = item.get('air_date', '0')
                    if status == 'Ended':
                        pass
                    elif not premiered or premiered == '0':
                        if self.shownoyear != 'true':
                            raise Exception()
                    elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                        unaired = 'true'
                        if self.showunaired != 'true':
                            raise Exception()
                    plot = item.get('overview', '0')
                    if not plot or plot == '0':
                        plot = show_plot
                    else:
                        plot = client_utils.replaceHTMLCodes(plot)
                    poster = item.get('poster_path', '')
                    if poster and poster != '':
                        if self.original_artwork == 'true':
                            poster = self.tmdb_image_link + poster
                        else:
                            poster = self.tmdb_image_link % ('500', poster)
                    else:
                        poster = show_poster
                    self.list.append({'season': season, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre, 'duration': duration, 'mpaa': mpaa, 'castwiththumb': castwiththumb,
                        'plot': plot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'poster': poster, 'fanart': fanart, 'banner': banner,'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'unaired': unaired}
                    )
                except:
                    #log_utils.log('tmdb_list', 1)
                    pass
        except:
            #log_utils.log('tmdb_list', 1)
            pass
        return self.list


    def get(self, tvshowtitle, year, imdb, tmdb, meta, idx=True, create_directory=True):
        try:
            if self.info_tvshows_source == '1':
                final_info = self.trakt_info
            else:
                final_info = self.tmdb_list
            if idx == True:
                if self.addon_caching == 'true':
                    self.list = cache.get(final_info, 24, tvshowtitle, year, imdb, tmdb, meta)
                else:
                    self.list = final_info(tvshowtitle, year, imdb, tmdb, meta)
                if create_directory == True:
                    self.seasonDirectory(self.list)
                return self.list
            else:
                self.list = final_info(tvshowtitle, year, imdb, tmdb, lite=True)
                return self.list
        except:
            #log_utils.log('get', 1)
            pass


    def seasonDirectory(self, items):
        if items == None or len(items) == 0:
            control.idle()
            #sys.exit()
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonPoster = control.addonPoster()
        addonBanner = control.addonBanner()
        addonFanart = control.addonFanart()
        settingFanart = control.setting('fanart')
        traktCredentials = trakt.getTraktCredentialsInfo()
        tmdbCredentials = tmdb_utils.getTMDbCredentialsInfo()
        try:
            indicators = playcount.getSeasonIndicators(items[0]['imdb'])
        except:
            pass
        watchedMenu = '[COLOR goldenrod]Free99[/COLOR] Mark Watched in Trakt' if trakt.getTraktIndicatorsInfo() == True else 'Watched in Scrubs'
        unwatchedMenu = '[COLOR goldenrod]Free99[/COLOR] Mark Unwatched in Trakt' if trakt.getTraktIndicatorsInfo() == True else 'Unwatched in Scrubs'
        for i in items:
            try:
                label = 'Season %s' % i['season']
                try:
                    stats = re.findall('(\d{4})', i['premiered'])[0]
                except:
                    stats = i['premiered']
                label = '%s (%s)' % (label, stats)
                try:
                    if i['unaired'] == 'true':
                        label = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, label)
                except:
                    pass
                systitle = sysname = urllib_parse.quote_plus(i['tvshowtitle'])
                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                banner1 = i.get('banner', '')
                banner = banner1 or fanart or addonBanner
                if 'landscape' in i and not i['landscape'] == '0':
                    landscape = i['landscape']
                else:
                    landscape = fanart
                ep_meta = {'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': i.get('clearlogo', '0'), 'clearart': i.get('clearart', '0'), 'landscape': landscape, 'duration': i.get('duration', '45'), 'status': i.get('status', '0')}
                sysmeta = urllib_parse.quote_plus(json.dumps(ep_meta))
                imdb, tvdb, tmdb, year, season, fanart, duration, status = i['imdb'], i['tvdb'], i['tmdb'], i['year'], i['season'], i['fanart'], i['duration'], i['status']
                meta = dict((k,v) for k, v in six.iteritems(i) if not v == '0')
                meta.update({'mediatype': 'tvshow'})
                meta.update({'code': tmdb, 'imdbnumber': imdb, 'imdb_id': imdb, 'tvdb_id': tvdb})
                meta.update({'trailer': '%s?action=trailer&name=%s&tmdb=%s&imdb=%s&season=%s' % (sysaddon, systitle, tmdb, imdb, season)})
                if not 'duration' in i:
                    meta.update({'duration': '60'})
                elif i['duration'] == '0':
                    meta.update({'duration': '60'})
                try:
                    meta.update({'duration': str(int(meta['duration']) * 60)})
                except:
                    pass
                try:
                    seasonYear = i['premiered']
                    seasonYear = re.findall('(\d{4})', seasonYear)[0]
                    meta.update({'year': seasonYear})
                except:
                    pass
                cm = []
                if traktCredentials == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] Trakt Manager', 'RunPlugin(%s?action=trakt_manager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, sysname, tmdb)))
                if tmdbCredentials == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] TMDb Manager', 'RunPlugin(%s?action=tmdb_manager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, sysname, tmdb)))
                cm.append(('[COLOR goldenrod]Free99[/COLOR] Add to Library', 'RunPlugin(%s?action=tvshow_to_library&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systitle, year, imdb, tmdb)))
                if kodi_version < 17:
                    cm.append(('Information', 'Action(Info)'))
                try:
                    overlay = int(playcount.getSeasonOverlay(indicators, imdb, season))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=tvshows_playcount&name=%s&imdb=%s&tmdb=%s&season=%s&query=6)' % (sysaddon, systitle, imdb, tmdb, season)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=tvshows_playcount&name=%s&imdb=%s&tmdb=%s&season=%s&query=7)' % (sysaddon, systitle, imdb, tmdb, season)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass
                try:
                    item = control.item(label=label, offscreen=True)
                except:
                    item = control.item(label=label)
                art = {}
                art.update({'icon': poster, 'thumb': poster, 'poster': poster, 'banner': banner, 'landscape': landscape})
                if settingFanart == 'true':
                    art.update({'fanart': fanart})
                elif not addonFanart == None:
                    art.update({'fanart': addonFanart})
                if 'clearlogo' in i and not i['clearlogo'] == '0':
                    art.update({'clearlogo': i['clearlogo']})
                if 'clearart' in i and not i['clearart'] == '0':
                    art.update({'clearart': i['clearart']})
                item.setArt(art)
                item.addContextMenuItems(cm)
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
                url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&season=%s' % (sysaddon, systitle, year, imdb, tmdb, sysmeta, season)
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                #log_utils.log('seasonDirectory', 1)
                pass
        try:
            control.property(syshandle, 'showplot', items[0]['plot'])
        except:
            #log_utils.log('seasonDirectory', 1)
            pass
        control.content(syshandle, 'seasons')
        control.directory(syshandle, cacheToDisc=True)
        views.setView('seasons', {'skin.aeon.nox.silvo' : 50, 'skin.estuary': 55, 'skin.confluence': 500}) #View 50 List #View 501 LowList


class episodes:
    def __init__(self):
        self.list = []
        self.datetime = datetime.datetime.utcnow()
        self.systime = self.datetime.strftime('%Y%m%d%H%M%S%f')
        self.today_date = self.datetime.strftime('%Y-%m-%d')
        self.addon_caching = control.setting('addon.caching') or 'true'
        self.episode_thumbs = control.setting('episode.thumbs') or 'false'
        self.episode_views = control.setting('episode.views') or 'false'
        self.shownoyear = control.setting('show.noyear') or 'false'
        self.showunaired = control.setting('showunaired') or 'true'
        self.unairedcolor = control.setting('unaired.color')
        if self.unairedcolor == '':
            self.unairedcolor = 'darkred'
        self.specials = control.setting('tv.specials') or 'true'
        self.lang = control.apiLanguage()['tmdb'] or 'en'
        self.hq_artwork = control.setting('hq.artwork') or 'false'
        self.tmdb_key = control.setting('tmdb.api')
        if self.tmdb_key == '' or self.tmdb_key == None:
            self.tmdb_key = '3d000491a0f37d4962d02bdb062af037'
        self.trakt_user = control.setting('trakt.user').strip()
        self.trakt_item_limit = str(control.setting('trakt.item.limit')) or '100'
        self.fanart_tv_headers = {'api-key': 'ad7eccc1dd67f889f7f5c2e9ebb810ae'}
        self.fanart_tv_user = control.setting('fanart.api')
        if not self.fanart_tv_user == '' or self.fanart_tv_user == None:
            self.fanart_tv_headers.update({'client-key': self.fanart_tv_user})
        self.trakt_link = 'https://api.trakt.tv'
        self.tvmaze_link = 'https://api.tvmaze.com'
        self.tmdb_link = 'https://api.themoviedb.org'
        self.fanart_tv_art_link = 'http://webservice.fanart.tv/v3/tv/%s'
        self.original_artwork = control.setting('original.artwork') or 'false'
        if self.original_artwork == 'true':
            self.tmdb_image_link = 'https://image.tmdb.org/t/p/original'
        else:
            self.tmdb_image_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.info_tvshows_source = control.setting('info.tvshows.source') or '0'

        self.tmdb_season_link = self.tmdb_link + '/3/tv/%s/season/%s?api_key=%s&language=en-US&append_to_response=aggregate_credits' % ('%s', '%s', self.tmdb_key)
        self.tmdb_episode_link = self.tmdb_link + '/3/tv/%s/season/%s/episode/%s?api_key=%s&language=en-US&append_to_response=credits' % ('%s', '%s', '%s', self.tmdb_key)
        self.tmdb_by_query_imdb_link = self.tmdb_link + '/3/find/%s?api_key=%s&external_source=imdb_id' % ('%s', self.tmdb_key)
        self.tmdb_search_link = self.tmdb_link + '/3/search/tv?api_key=%s&language=en-US&query=%s&page=1' % (self.tmdb_key, '%s')

        self.trakt_mycalendar_link = self.trakt_link + '/calendars/my/shows/date[30]/31/' #go back 30 and show all shows aired until tomorrow
        self.trakt_progress_link = self.trakt_link + '/users/me/watched/shows'
        self.trakt_hiddenprogress_link = self.trakt_link + '/users/hidden/progress_watched?limit=1000&type=show'
        self.trakt_history_link = self.trakt_link + '/users/me/history/shows?limit=300' # '40'
        self.trakt_ondeck_link = self.trakt_link + '/sync/playback/episodes?limit=20'
        self.trakt_list_link = self.trakt_link + '/users/%s/lists/%s/items'
        self.trakt_lists_link = self.trakt_link + '/users/me/lists'
        self.trakt_likedlists_link = self.trakt_link + '/users/likes/lists?limit=1000000'

        self.tvmaze_added_link = self.tvmaze_link + '/schedule'
        self.tvmaze_calendar_link = self.tvmaze_link + '/schedule?date=%s'


    def get(self, tvshowtitle, year, imdb, tmdb, meta, season=None, episode=None, idx=True, create_directory=True):
        try:
            if self.info_tvshows_source == '1':
                final_info = self.trakt_info
            else:
                final_info = self.tmdb_list
            if idx == True:
                if season == None or episode == None:
                    if self.addon_caching == 'true':
                        self.list = cache.get(final_info, 1, tvshowtitle, year, imdb, tmdb, season, meta)
                    else:
                        self.list = final_info(tvshowtitle, year, imdb, tmdb, season, meta)
                else:
                    if self.addon_caching == 'true':
                        self.list = cache.get(final_info, 1, tvshowtitle, year, imdb, tmdb, season, meta)
                    else:
                        self.list = final_info(tvshowtitle, year, imdb, tmdb, season, meta)
                    num = [x for x,y in enumerate(self.list) if y['season'] == str(season) and y['episode'] == str(episode)][-1]
                    self.list = [y for x,y in enumerate(self.list) if x >= num]
                if create_directory == True:
                    self.episodeDirectory(self.list)
                return self.list
            else:
                self.list = final_info(tvshowtitle, year, imdb, tmdb, season, lite=True)
                return self.list
        except:
            #log_utils.log('get', 1)
            pass


    def calendar(self, url):
        try:
            try:
                url = getattr(self, url + '_link')
            except:
                pass
            if self.trakt_link in url and url == self.trakt_ondeck_link:
                self.blist = []
                if self.addon_caching == 'true':
                    self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                else:
                    self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = []
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                else:
                    self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: int(k['paused_at']), reverse=True)
            elif self.trakt_link in url and url == self.trakt_progress_link:
                self.blist = []
                if self.addon_caching == 'true':
                    self.blist = cache.get(self.trakt_progress_list, 720, url, self.trakt_user, self.lang)
                else:
                    self.blist = self.trakt_progress_list(url, self.trakt_user, self.lang)
                self.list = []
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_progress_list, 0, url, self.trakt_user, self.lang)
                else:
                    self.list = self.trakt_progress_list(url, self.trakt_user, self.lang)
            elif self.trakt_link in url and url == self.trakt_mycalendar_link:
                self.blist = []
                if self.addon_caching == 'true':
                    self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                else:
                    self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = []
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                else:
                    self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
            elif self.trakt_link in url and url == self.trakt_history_link:
                self.blist = []
                if self.addon_caching == 'true':
                    self.blist = cache.get(self.trakt_episodes_list, 720, url, self.trakt_user, self.lang)
                else:
                    self.blist = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = []
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_episodes_list, 0, url, self.trakt_user, self.lang)
                else:
                    self.list = self.trakt_episodes_list(url, self.trakt_user, self.lang)
                self.list = sorted(self.list, key=lambda k: int(k['watched_at']), reverse=True)
            elif self.trakt_link in url and '/users/' in url:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)
                else:
                    self.list = self.trakt_list(url, self.trakt_user)
                self.list = self.list[::-1]
            elif self.trakt_link in url:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.trakt_list, 1, url, self.trakt_user)
                else:
                    self.list = self.trakt_list(url, self.trakt_user)
            elif self.tvmaze_link in url and url == self.tvmaze_added_link:
                urls = [i['url'] for i in self.calendars(idx=False)][:5]
                self.list = []
                for url in urls:
                    if self.addon_caching == 'true':
                        self.list += cache.get(self.tvmaze_list, 720, url, True)
                    else:
                        self.list += self.tvmaze_list(url, True)
            elif self.tvmaze_link in url:
                if self.addon_caching == 'true':
                    self.list = cache.get(self.tvmaze_list, 1, url, False)
                else:
                    self.list = self.tvmaze_list(url, False)
            self.episodeDirectory(self.list)
            return self.list
        except:
            #log_utils.log('calendar', 1)
            pass


    def widget(self):
        if trakt.getTraktIndicatorsInfo() == True:
            setting = control.setting('episode.widget.alt')
        else:
            setting = control.setting('episode.widget')
        if setting == '2':
            self.calendar(self.tvmaze_added_link)
        elif setting == '3':
            self.calendar(self.trakt_progress_link)
        elif setting == '4':
            self.calendar(self.trakt_mycalendar_link)
        else:
            self.calendars()


    def calendars(self, idx=True):
        m = ('January|February|March|April|May|June|July|August|September|October|November|December').split('|')
        try:
            months = [(m[0], 'January'), (m[1], 'February'), (m[2], 'March'), (m[3], 'April'), (m[4], 'May'), (m[5], 'June'), (m[6], 'July'), (m[7], 'August'), (m[8], 'September'), (m[9], 'October'), (m[10], 'November'), (m[11], 'December')]
        except:
            months = []
        d = ('Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday').split('|')
        try:
            days = [(d[0], 'Monday'), (d[1], 'Tuesday'), (d[2], 'Wednesday'), (d[3], 'Thursday'), (d[4], 'Friday'), (d[5], 'Saturday'), (d[6], 'Sunday')]
        except:
            days = []
        for i in range(0, 30):
            try:
                name = (self.datetime - datetime.timedelta(days = i))
                name = ('[B]%s[/B] : %s' % (name.strftime('%A'), six.ensure_str(name.strftime('%d %B'))))
                for m in months:
                    name = name.replace(m[1], m[0])
                for d in days:
                    name = name.replace(d[1], d[0])
                try:
                    name = six.ensure_str(name)
                except:
                    pass
                url = self.tvmaze_calendar_link % (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d')
                self.list.append({'name': name, 'url': url, 'image': 'calendar.png', 'action': 'calendar'})
            except:
                #log_utils.log('calendars', 1)
                pass
        if idx == True:
            self.addDirectory(self.list)
        return self.list


    def userlists(self):
        userlists = []
        try:
            if trakt.getTraktCredentialsInfo() == False:
                raise Exception()
            activity = trakt.getActivity()
            userlists += self.trakt_user_list(self.trakt_lists_link, self.trakt_user)
            userlists += self.trakt_user_list(self.trakt_likedlists_link, self.trakt_user)
        except:
            pass
        self.list = userlists
        for i in range(0, len(self.list)):
            self.list[i].update({'image': 'userlists.png', 'action': 'calendar'})
        self.addDirectory(self.list, queue=True)
        return self.list


    def trakt_list(self, url, user):
        itemlist = []
        try:
            if 'date[' in url:
                for i in re.findall('date\[(\d+)\]', url):
                    url = url.replace('date[%s]' % i, (self.datetime - datetime.timedelta(days=int(i))).strftime('%Y-%m-%d'))
            q = dict(urllib_parse.parse_qsl(urllib_parse.urlsplit(url).query))
            q.update({'extended': 'full'})
            q = (urllib_parse.urlencode(q)).replace('%2C', ',')
            u = url.replace('?' + urllib_parse.urlparse(url).query, '') + '?' + q
            items = trakt.getTraktAsJson(u)
            for item in items:
                try:
                    title = item.get('episode', {}).get('title')
                    if not title:
                        raise Exception()
                    else:
                        title = client_utils.replaceHTMLCodes(title)
                    season = item.get('episode', {}).get('season', '0')
                    if not season or season == '0':
                        raise Exception()
                    else:
                        season = re.sub('[^0-9]', '', '%01d' % int(season))
                    episode = item.get('episode', {}).get('number', '0')
                    if not episode or episode == '0':
                        raise Exception()
                    else:
                        episode = re.sub('[^0-9]', '', '%01d' % int(episode))
                    tvshowtitle = item.get('show', {}).get('title')
                    if not tvshowtitle:
                        raise Exception()
                    else:
                        tvshowtitle = client_utils.replaceHTMLCodes(tvshowtitle)
                    year = item.get('show', {}).get('year', '0')
                    if not year or year == '0':
                        year = '0'
                    else:
                        year = re.sub('[^0-9]', '', str(year))
                    imdb = item['show'].get('ids', {}).get('imdb') or '0'
                    if not imdb or imdb == '0':
                        imdb = '0'
                    else:
                        imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                    tvdb = item['show'].get('ids', {}).get('tvdb') or '0'
                    if not tvdb or tvdb == '0':
                        tvdb == '0'
                    else:
                        tvdb = re.sub('[^0-9]', '', str(tvdb))
                    tmdb = item['show'].get('ids', {}).get('tmdb') or '0'
                    if not tmdb or tmdb == '0':
                        raise Exception()
                    else:
                        tmdb = str(tmdb)
                    premiered = item.get('episode', {}).get('first_aired', '0')
                    if premiered and premiered != '0':
                        premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                    else:
                        premiered = '0'
                    studio = item.get('show', {}).get('network')
                    if studio and studio != []:
                        #studio = [x['name'] for x in studio]#[0]
                        #studio = [x.title() for x in studio]#[0]
                        studio = [studio.title()]#[0] ## Ghetto rig for studio being a single item lol.
                    else:
                        studio = []#'0'
                    genre = item.get('show', {}).get('genres')
                    if genre and genre != []:
                        genre = [i.title() for i in genre]
                    else:
                        genre = []#'0'
                    #genre = ' / '.join(genre)
                    duration = item.get('show', {}).get('runtime', '0')
                    if not duration or duration == '0':
                        duration = '0'
                    else:
                        duration = str(duration)
                    rating = item.get('episode', {}).get('rating', '0')
                    if not rating or rating == '0' or rating == '0.0':
                        rating = '0'
                    else:
                        rating = str(rating)
                    votes = item.get('episode', {}).get('votes', '0')
                    if not votes or votes == '0':
                        votes = '0'
                    else:
                        votes = str(votes)
                    #try:
                        #votes = str(format(int(votes),',d'))
                    #except:
                        #pass
                    #if not votes:
                        #votes = '0'
                    mpaa = item.get('show', {}).get('certification')
                    if not mpaa:
                        mpaa = '0'
                    plot = item.get('episode', {}).get('overview')
                    if not plot:
                        plot = item.get('show', {}).get('overview')
                    if not plot:
                        plot = '0'
                    else:
                        plot = client_utils.replaceHTMLCodes(plot)
                    paused_at = item.get('paused_at', '0') or '0'
                    if paused_at and paused_at != '0':
                        paused_at = re.sub('[^0-9]+', '', paused_at)
                    else:
                        paused_at = '0'
                    watched_at = item.get('watched_at', '0') or '0'
                    if watched_at and watched_at != '0':
                        watched_at = re.sub('[^0-9]+', '', watched_at)
                    else:
                        watched_at = '0'
                    try:
                        if self.lang == 'en':
                            raise Exception()
                        trans_item = trakt.getTVShowTranslation(imdb, lang=self.lang, season=season, episode=episode, full=True)
                        title = client_utils.replaceHTMLCodes(trans_item.get('title')) or title
                        plot = client_utils.replaceHTMLCodes(trans_item.get('overview')) or plot
                        #tvshowtitle = trakt.getTVShowTranslation(imdb, lang=self.lang) or tvshowtitle
                    except:
                        pass
                    itemlist.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': 'Continuing', 'studio': studio, 'genre': genre,
                        'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': '0', 'thumb': '0', 'paused_at': paused_at, 'watched_at': watched_at}
                    )
                except:
                    #log_utils.log('trakt_list', 1)
                    pass
        except:
            #log_utils.log('trakt_list', 1)
            pass
        itemlist = itemlist[::-1]
        return itemlist


### Recode Stopped Here...
    def trakt_progress_list(self, url, user, lang):
        try:
            url += '?extended=full'
            result = trakt.getTraktAsJson(url)
        except:
            #log_utils.log('trakt_progress_list', 1)
            return
        items = []
        sortorder = control.setting('prgr.sortorder')
        for item in result:
            try:
                num_1 = 0
                for i in range(0, len(item['seasons'])):
                    if item['seasons'][i]['number'] > 0:
                        num_1 += len(item['seasons'][i]['episodes'])
                num_2 = int(item['show']['aired_episodes'])
                if num_1 >= num_2:
                    raise Exception()
                season = str(item['seasons'][-1]['number'])
                episode = [x for x in item['seasons'][-1]['episodes'] if 'number' in x]
                episode = sorted(episode, key=lambda x: x['number'])
                episode = str(episode[-1]['number'])
                tvshowtitle = item.get('show', {}).get('title')
                if not tvshowtitle:
                    raise Exception()
                else:
                    tvshowtitle = client_utils.replaceHTMLCodes(tvshowtitle)
                year = item.get('show', {}).get('year', '0')
                if not year or year == '0':
                    year = '0'
                else:
                    year = re.sub('[^0-9]', '', str(year))
                if int(year) > int(self.datetime.strftime('%Y')):
                    if self.shownoyear != 'true':
                        raise Exception()
                imdb = item['show'].get('ids', {}).get('imdb') or '0'
                if not imdb or imdb == '0':
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                tvdb = item['show'].get('ids', {}).get('tvdb') or '0'
                if not tvdb or tvdb == '0':
                    tvdb == '0'
                else:
                    tvdb = re.sub('[^0-9]', '', str(tvdb))
                tmdb = item['show'].get('ids', {}).get('tmdb') or '0'
                if not tvdb or tvdb == '0':
                    tmdb = '0'
                else:
                    tmdb = str(tmdb)
                studio = item.get('show', {}).get('network')
                if studio and studio != []:
                    #studio = [x['name'] for x in studio]#[0]
                    #studio = [x.title() for x in studio]#[0]
                    studio = [studio.title()]#[0] ## Ghetto rig for studio being a single item lol.
                else:
                    studio = []#'0'
                duration = item.get('show', {}).get('runtime', '0')
                if not duration or duration == '0':
                    duration = '0'
                else:
                    duration = str(duration)
                mpaa = item.get('show', {}).get('certification')
                if not mpaa:
                    mpaa = '0'
                status = item.get('show', {}).get('status')
                if not status:
                    status = '0'
                genre = item.get('show', {}).get('genres')
                if genre and genre != []:
                    genre = [i.title() for i in genre]
                else:
                    genre = []#'0'
                #genre = ' / '.join(genre)
                last_watched = item.get('last_watched_at', '0') or '0'
                if last_watched and last_watched != '0':
                    last_watched = re.sub('[^0-9]+', '', last_watched)
                else:
                    last_watched = '0'
                items.append({'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle, 'year': year, 'studio': studio, 'duration': duration, 'mpaa': mpaa,
                    'status': status, 'genre': genre, 'snum': season, 'enum': episode, '_last_watched': last_watched}
                )
            except:
                #log_utils.log('trakt_progress_list', 1)
                pass
        try:
            result = trakt.getTraktAsJson(self.trakt_hiddenprogress_link)
            result = [str(i['show']['ids']['tmdb']) for i in result]
            items = [i for i in items if not i['tmdb'] in result]
        except:
            #log_utils.log('trakt_progress_list', 1)
            pass
        def items_list(i):
            tmdb, imdb, tvdb = i['tmdb'], i['imdb'], i['tvdb']
            if (not tmdb or tmdb == '0') and not imdb == '0':
                try:
                    url = self.tmdb_by_query_imdb_link % imdb
                    result = client.scrapePage(url, timeout='30').json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except:
                    #log_utils.log('trakt_progress_list', 1)
                    pass
            try:
                item = [x for x in self.blist if x['tmdb'] == tmdb and x['snum'] == i['snum'] and x['enum'] == i['enum']][0]
                item['action'] = 'episodes'
                self.list.append(item)
                return
            except:
                #log_utils.log('trakt_progress_list', 1)
                pass
            try:
                if tmdb == '0':
                    raise Exception()
                _episode = str(int(i['enum']) + 1)
                _season = str(int(i['snum']) + 1)
                url = self.tmdb_episode_link % (tmdb, i['snum'], _episode)
                item = client.scrapePage(url, timeout='30').json()
                if item.get('status_code') == 34:
                    url2 = self.tmdb_episode_link % (tmdb, _season, '1')
                    item = client.scrapePage(url2, timeout='30').json()
                try:
                    premiered = item.get('air_date')
                except:
                    premiered = ''
                if not premiered:
                    premiered = '0'
                unaired = ''
                if i['status'] == 'Ended':
                    pass
                elif premiered == '0':
                    if self.shownoyear != 'true':
                        raise Exception()
                elif int(re.sub(r'[^0-9]', '', str(premiered))) > int(re.sub(r'[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception()
                title = item.get('name')
                if not title:
                    title = '0'
                else:
                    title = client_utils.replaceHTMLCodes(title)
                season = item.get('season_number', i['snum']) ## Added i['snum'] to counter a odd error, think it works out lol.
                season = '%01d' % int(season)
                #if int(season) == 0:# and self.specials != 'true':
                    #raise Exception()
                episode = item.get('episode_number', i['enum']) ## Added i['enum'] to counter a odd error, think it works out lol.
                episode = '%01d' % int(episode)
                tvshowtitle = i['tvshowtitle']
                year = i['year']
                try:
                    thumb = item.get('still_path')
                except:
                    thumb = ''
                if not (thumb == '' or thumb == None):
                    if self.original_artwork == 'true':
                        thumb = self.tmdb_image_link + thumb
                    else:
                        thumb = self.tmdb_image_link % ('300', thumb)
                else:
                    thumb = '0'
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
                    plot = item.get('overview')
                except:
                    plot = ''
                if not plot:
                    plot = '0'
                else:
                    plot = client_utils.replaceHTMLCodes(plot)
                try:
                    r_crew = item['crew']
                    director = [d['name'] for d in r_crew if d['job'] == 'Director']
                    #director = ', '.join([d['name'] for d in director])
                    if not director:
                        director = []#'0'
                    writer = [w['name'] for w in r_crew if w['job'] == 'Writer']
                    #writer = ', '.join([w['name'] for w in writer])
                    if not writer:
                        writer = []#'0'
                except:
                    director = []#''
                    writer = []#''
                castwiththumb = []
                try:
                    r_cast = item['credits']['cast'][:30]
                    for person in r_cast:
                        _icon = person['profile_path']
                        if self.original_artwork == 'true':
                            icon = self.tmdb_image_link + _icon if _icon else ''
                        else:
                            icon = self.tmdb_image_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
                except:
                    pass
                if not castwiththumb:
                    castwiththumb = '0'
                poster = fanart = banner = landscape = clearlogo = clearart = '0'
                if not tvdb == '0':
                    poster, fanart, banner, clearlogo, clearart, landscape = self.get_fanart_tv_artwork(tvdb)
                self.list.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'studio': i.get('studio'), 'genre': i.get('genre'), 'status': i.get('status'),
                    'duration': i.get('duration'), 'rating': rating, 'votes': votes, 'mpaa': i.get('mpaa'), 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'plot': plot,
                    'poster': poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape, 'snum': i['snum'], 'enum': i['enum'], 'action': 'episodes',
                    'unaired': unaired, '_last_watched': i['_last_watched'], 'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, '_sort_key': max(i['_last_watched'],premiered)}
                )
            except:
                #log_utils.log('trakt_progress_list', 1)
                pass
        try:
            if self.trakt_item_limit == '50':
                items = items[:50]
            elif self.trakt_item_limit == '150':
                items = items[:150]
            else:
                items = items[:100]
            threads = []
            for i in items:
                threads.append(workers.Thread(items_list, i))
            [i.start() for i in threads]
            [i.join() for i in threads]
            if sortorder == '0':
                self.list = sorted(self.list, key=lambda k: k['premiered'], reverse=True)
            else:
                self.list = sorted(self.list, key=lambda k: k['_sort_key'], reverse=True)
        except:
            #log_utils.log('trakt_progress_list', 1)
            pass
        return self.list


    def trakt_episodes_list(self, url, user, lang):
        items = self.trakt_list(url, user)
        def items_list(i):
            tmdb, imdb, tvdb = i['tmdb'], i['imdb'], i['tvdb']
            if (not tmdb or tmdb == '0') and not imdb == '0':
                try:
                    url = self.tmdb_by_query_imdb_link % imdb
                    result = client.scrapePage(url, timeout='30').json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except:
                    #log_utils.log('trakt_episodes_list', 1)
                    pass
            try:
                item = [x for x in self.blist if x['tmdb'] == tmdb and x['season'] == i['season'] and x['episode'] == i['episode']][0]
                if item['poster'] == '0':
                    raise Exception()
                self.list.append(item)
                return
            except:
                #log_utils.log('trakt_episodes_list', 1)
                pass
            try:
                if tmdb == '0':
                    raise Exception()
                if i['season'] == '0':
                    raise Exception()
                url = self.tmdb_episode_link % (tmdb, i['season'], i['episode'])
                item = client.scrapePage(url, timeout='30').json()
                title = item['name']
                if not title:
                    title = '0'
                else:
                    title = client_utils.replaceHTMLCodes(title)
                season = item['season_number']
                season = '%01d' % season
                #if int(season) == 0:# and self.specials != 'true':
                    #raise Exception()
                episode = item['episode_number']
                episode = '%01d' % episode
                tvshowtitle = i['tvshowtitle']
                premiered = i['premiered']
                status, duration, mpaa, studio, genre, year = i['status'], i['duration'], i['mpaa'], i['studio'], i['genre'], i['year']
                rating, votes = i['rating'], i['votes']
                try:
                    thumb = item['still_path']
                except:
                    thumb = ''
                if not (thumb == '' or thumb == None):
                    if self.original_artwork == 'true':
                        thumb = self.tmdb_image_link + item['still_path']
                    else:
                        thumb = self.tmdb_image_link % ('300', thumb)
                else:
                    thumb = '0'
                try:
                    plot = item['overview']
                except:
                    plot = ''
                if not plot:
                    plot = i['plot']
                else:
                    plot = client_utils.replaceHTMLCodes(plot)
                try:
                    r_crew = item['crew']
                    director = [d['name'] for d in r_crew if d['job'] == 'Director']
                    #director = ', '.join([d['name'] for d in director])
                    writer = [w['name'] for w in r_crew if w['job'] == 'Writer']
                    #writer = ', '.join([w['name'] for w in writer])
                except:
                    director = writer = []#''
                if not director:
                    director = []#'0'
                if not writer:
                    writer = []#'0'
                castwiththumb = []
                try:
                    r_cast = item['credits']['cast'][:30]
                    for person in r_cast:
                        _icon = person['profile_path']
                        if self.original_artwork == 'true':
                            icon = self.tmdb_image_link + _icon if _icon else ''
                        else:
                            icon = self.tmdb_image_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['character'], 'thumbnail': icon})
                except:
                    pass
                if not castwiththumb:
                    castwiththumb = '0'
                paused_at = i.get('paused_at', '0') or '0'
                watched_at = i.get('watched_at', '0') or '0'
                poster = fanart = banner = landscape = clearlogo = clearart = '0'
                if not tvdb == '0':
                    poster, fanart, banner, clearlogo, clearart, landscape = self.get_fanart_tv_artwork(tvdb)
                self.list.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': status, 'studio': studio, 'genre': genre,
                    'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'plot': plot,
                    'imdb': imdb, 'tvdb': tvdb, 'tmdb': tmdb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'thumb': thumb, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape,
                    'paused_at': paused_at, 'watched_at': watched_at}
                )
            except:
                #log_utils.log('trakt_episodes_list', 1)
                pass
        if self.trakt_item_limit == '50':
            items = items[:50]
        elif self.trakt_item_limit == '150':
            items = items[:150]
        else:
            items = items[:100]
        threads = []
        for i in items:
            threads.append(workers.Thread(items_list, i))
        [i.start() for i in threads]
        [i.join() for i in threads]
        return self.list


    def trakt_user_list(self, url, user):
        try:
            items = trakt.getTraktAsJson(url)
        except:
            #log_utils.log('trakt_user_list', 1)
            pass
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
                self.list.append({'name': name, 'url': url, 'context': url})
            except:
                #log_utils.log('trakt_user_list', 1)
                pass
        self.list = sorted(self.list, key=lambda k: k['name'])
        return self.list


    def tvmaze_list(self, url, limit):
        itemlist = []
        try:
            items = client.scrapePage(url, timeout='30').json()
        except:
            #log_utils.log('tvmaze_list', 1)
            return
        for item in items:
            try:
                if not 'english' in item['show']['language'].lower():
                    raise Exception()
                if limit == True and not 'scripted' in item['show']['type'].lower():
                    raise Exception()
                title = item['name']
                if title == None or title == '':
                    raise Exception()
                title = client_utils.replaceHTMLCodes(title)
                season = item['season']
                season = re.sub('[^0-9]', '', '%01d' % int(season))
                if season == '0':
                    raise Exception()
                episode = item['number']
                episode = re.sub('[^0-9]', '', '%01d' % int(episode))
                if episode == '0':
                    raise Exception()
                tvshowtitle = item['show']['name']
                if tvshowtitle == None or tvshowtitle == '':
                    raise Exception()
                tvshowtitle = client_utils.replaceHTMLCodes(tvshowtitle)
                year = item['show']['premiered']
                year = re.findall('(\d{4})', year)[0]
                imdb = item['show']['externals']['imdb']
                if imdb == None or imdb == '':
                    imdb = '0'
                else:
                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))
                tvdb = item['show']['externals']['thetvdb']
                if tvdb == None or tvdb == '':
                    tvdb = '0'
                tvdb = re.sub('[^0-9]', '', str(tvdb))
                poster1 = '0'
                try:
                    poster1 = item['show']['image']['original']
                except:
                    poster1 = '0'
                if poster1 == None or poster1 == '':
                    poster1 = '0'
                try:
                    thumb1 = item['show']['image']['original']
                except:
                    thumb1 = '0'
                try:
                    thumb2 = item['image']['original']
                except:
                    thumb2 = '0'
                if thumb2 == None or thumb2 == '0':
                    thumb = thumb1
                else:
                    thumb = thumb2
                if thumb == None or thumb == '':
                    thumb = '0'
                premiered = item['airdate']
                try:
                    premiered = re.findall('(\d{4}-\d{2}-\d{2})', premiered)[0]
                except:
                    premiered = '0'
                try:
                    studio = item['show']['network']
                    studio = [x['name'] for x in studio]#[0]
                except:
                    studio = []#'0'
                if studio == '' or studio == None or studio == []:
                    studio = []#'0'
                try:
                    genre = item['show']['genres']
                    genre = [i.title() for i in genre]
                except:
                    genre = []#'0'
                if genre == '' or genre == None or genre == []:
                    genre = []#'0'
                #genre = ' / '.join(genre)
                try:
                    duration = item['show']['runtime']
                except:
                    duration = '0'
                if duration == None:
                    duration = '0'
                try:
                    rating = item['show']['rating']['average']
                except:
                    rating = '0'
                if rating == None or rating == '0.0':
                    rating = '0'
                votes = '0'
                try:
                    plot = item['show']['summary']
                except:
                    plot = '0'
                if plot == None:
                    plot = '0'
                plot = re.sub('<.+?>|</.+?>|\n', '', plot)
                plot = client_utils.replaceHTMLCodes(plot)
                poster2 = fanart = banner = landscape = clearlogo = clearart = '0'
                if not tvdb == '0':
                    poster2, fanart, banner, clearlogo, clearart, landscape = self.get_fanart_tv_artwork(tvdb)
                poster = poster2 if not poster2 == '0' else poster1
                itemlist.append({'title': title, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered, 'status': 'Continuing',
                    'studio': studio, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'plot': plot, 'imdb': imdb, 'tvdb': tvdb, 'tmdb': '0',
                    'thumb': thumb, 'poster': poster, 'banner': banner, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape}
                )
            except:
                #log_utils.log('tvmaze_list', 1)
                pass
        itemlist = itemlist[::-1]
        return itemlist


    def get_fanart_tv_artwork(self, id): #tvdb
        try:
            art = client.scrapePage(self.fanart_tv_art_link % id, headers=self.fanart_tv_headers, timeout='30').json()
            try:
                poster = art.get('tvposter')
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
                if 'showbackground' in art:
                    fanart = art.get('showbackground')
                else:
                    fanart = art.get('tvthumb')
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
                banner = art.get('tvbanner')
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
                if 'hdtvlogo' in art:
                    clearlogo = art.get('hdtvlogo')
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
                if 'hdclearart' in art:
                    clearart = art.get('hdclearart')
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
                if 'tvthumb' in art:
                    landscape = art.get('tvthumb')
                else:
                    landscape = art.get('showbackground')
                if landscape:
                    landscape = [x for x in landscape if x.get('lang') == 'en'][::-1] + [x for x in landscape if x.get('lang') in ['00', '']][::-1]
                    landscape = landscape[0].get('url')
                    if not landscape:
                        landscape = '0'
                else:
                    landscape = '0'
            except:
                landscape = '0'
        except:
            poster = fanart = banner = clearlogo = clearart = landscape = '0'
        return poster, fanart, banner, clearlogo, clearart, landscape


    def trakt_info(self, tvshowtitle, year, imdb, tmdb, season, meta=None, lite=False):
        try:
            tvdb = '0'
            if imdb == '0' and not tmdb == '0':
                temp_item = tmdb_utils.get_tvshow_external_ids(tmdb)
                imdb = temp_item.get('imdb_id', '0')
            if imdb == '0' and tmdb == '0':
                temp_item = trakt.SearchTVShow(tvshowtitle, year)
                if temp_item[0]['show']['title'] != tvshowtitle or int(temp_item[0]['show']['year']) != int(year):
                    raise Exception()
                imdb = temp_item[0]['show']['ids'].get('imdb', '0')
                tmdb = temp_item[0]['show']['ids'].get('tmdb', '0')
                if tvdb == '0':
                    tvdb = temp_item[0]['show']['ids'].get('tvdb', '0')
        except:
            #log_utils.log('trakt_info', 1)
            return
        try:
            if not imdb or imdb == '0':
                raise Exception()
            people = trakt.getPeople(imdb, 'shows')
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
                    writer = [writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']]#'Original Series Creator'
                    #writer = ', '.join([writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']])
                else:
                    writer = []
            except:
                writer = []
            episodes = trakt.getEpisodeSummary(imdb, season, full=True)
            if not episodes:
                raise Exception()
            if self.specials == 'false':
                episodes = [e for e in episodes if not e['season'] == 0]
        except:
            #log_utils.log('trakt_info', 1)
            return
        clearlogo = clearart = landscape = duration = status = '0'
        if meta:
            _meta = json.loads(urllib_parse.unquote_plus(meta))
            poster, fanart, banner, clearlogo, clearart, landscape, duration, status = _meta['poster'], _meta['fanart'], _meta['banner'], _meta['clearlogo'], _meta['clearart'], _meta['landscape'], _meta['duration'], _meta['status']
        else:
            poster, fanart, banner = tmdb_utils.get_tmdb_artwork(tmdb, 'tv', season=season)
        for item in episodes:
            try:
                title = item.get('title', '0')
                title = client_utils.replaceHTMLCodes(title)
                label = title
                season = str(item.get('season'))
                episode = str(item.get('number'))
                premiered = item.get('first_aired', '0')
                if premiered and premiered != '0':
                    premiered = re.compile(r'(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
                else:
                    premiered = '0'
                unaired = ''
                if not premiered or premiered == '0':
                    if self.shownoyear != 'true':
                        raise Exception()
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception()
                rating = item.get('rating', '0')
                if not rating or rating == '0' or rating == '0.0':
                    rating = '0'
                votes = item.get('votes', '0')
                #votes = str(format(int(votes), ',d'))
                if not votes or votes == '0':
                    votes = '0'
                episodeplot = item.get('overview', '0')
                if not episodeplot or episodeplot == '0':
                    episodeplot = '0'
                else:
                    episodeplot = client_utils.replaceHTMLCodes(episodeplot)
                episode_poster, episode_fanart, episode_banner = tmdb_utils.get_tmdb_artwork(tmdb, 'tv', season=season, episode=episode)
                thumb = episode_fanart if not episode_fanart == '0' else fanart
                ### These 3 lines are not really needed from what i can tell but oh well lol.
                poster = episode_poster if not episode_poster == '0' else poster
                fanart = fanart if not fanart == '0' else episode_fanart
                banner = episode_banner if not episode_banner == '0' else banner
                #############################################################################
                self.list.append({'title': title, 'label': label, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
                    'rating': rating, 'votes': votes, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'duration': duration,
                    'status': status, 'plot': episodeplot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'unaired': unaired, 'thumb': thumb, 'poster': poster,
                    'fanart': fanart, 'banner': banner,'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape}
                )
            except:
                #log_utils.log('trakt_info', 1)
                pass
        return self.list


    def tmdb_list(self, tvshowtitle, year, imdb, tmdb, season, meta=None, lite=False):
        try:
            tvdb = '0'
            if tmdb == '0' and not imdb == '0':
                try:
                    url = self.tmdb_by_query_imdb_link % imdb
                    result = client.scrapePage(url, timeout='30').json()
                    id = result.get('tv_results', [])[0]
                    tmdb = id.get('id')
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except:
                    #log_utils.log('tmdb_list', 1)
                    pass
            if tmdb == '0':
                try:
                    url = self.tmdb_search_link % (urllib_parse.quote(tvshowtitle)) + '&first_air_date_year=' + year
                    result = client.scrapePage(url, timeout='30').json()
                    results = result['results']
                    show = [r for r in results if cleantitle.get(r.get('name')) == cleantitle.get(self.list[i]['title'])][0]# and re.findall('(\d{4})', r.get('first_air_date'))[0] == self.list[i]['year']][0]
                    tmdb = show.get('id')
                    if not tmdb:
                        tmdb = '0'
                    else:
                        tmdb = str(tmdb)
                except:
                    #log_utils.log('tmdb_list', 1)
                    pass
        except:
            #log_utils.log('tmdb_list', 1)
            return
        try:
            if tmdb == '0':
                raise Exception()
            episodes_url = self.tmdb_season_link % (tmdb, season)
            result = client.scrapePage(episodes_url, timeout='30').json()
            #result = control.six_decode(result)
            episodes = result.get('episodes', [])
            r_cast = result.get('aggregate_credits', {}).get('cast', [])
            if self.specials == 'false':
                episodes = [e for e in episodes if not e['season_number'] == 0]
        except:
            #log_utils.log('tmdb_list', 1)
            return
        try:
            poster = result['poster_path']
        except:
            poster = ''
        if not (poster == '' or poster == None):
            if self.original_artwork == 'true':
                poster = self.tmdb_image_link + poster
            else:
                poster = self.tmdb_image_link % ('500', poster)
        else:
            poster = '0'
        fanart = banner = clearlogo = clearart = landscape = duration = status = '0'
        if meta:
            _meta = json.loads(urllib_parse.unquote_plus(meta))
            poster, fanart, banner, clearlogo, clearart, landscape, duration, status = _meta['poster'], _meta['fanart'], _meta['banner'], _meta['clearlogo'], _meta['clearart'], _meta['landscape'], _meta['duration'], _meta['status']
        for item in episodes:
            try:
                try:
                    title = item['name']
                except:
                    title = ''
                if not title:
                    title = '0'
                else:
                    title = client_utils.replaceHTMLCodes(title)
                label = title
                season = str(item['season_number'])
                episode = str(item['episode_number'])
                try:
                    premiered = item['air_date']
                except:
                    premiered = '0'
                unaired = ''
                if not premiered or premiered == '0':
                    if self.shownoyear != 'true':
                        raise Exception()
                elif int(re.sub('[^0-9]', '', str(premiered))) > int(re.sub('[^0-9]', '', str(self.today_date))):
                    unaired = 'true'
                    if self.showunaired != 'true':
                        raise Exception()
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
                    episodeplot = item['overview']
                except:
                    episodeplot = ''
                if not episodeplot:
                    episodeplot = '0'
                else:
                    episodeplot = client_utils.replaceHTMLCodes(episodeplot)
                try:
                    r_crew = item['crew']
                    director = [d['name'] for d in r_crew if d['job'] == 'Director']
                    #director = ', '.join([d['name'] for d in director])
                    writer = [w['name'] for w in r_crew if w['job'] == 'Writer']
                    #writer = ', '.join([w['name'] for w in writer])
                except:
                    director = writer = []#''
                if not director:
                    director = []#'0'
                if not writer:
                    writer = []#'0'
                castwiththumb = []
                try:
                    for person in r_cast[:30]:
                        _icon = person['profile_path']
                        if self.original_artwork == 'true':
                            icon = self.tmdb_image_link + _icon if _icon else ''
                        else:
                            icon = self.tmdb_image_link % ('185', _icon) if _icon else ''
                        castwiththumb.append({'name': person['name'], 'role': person['roles'][0]['character'], 'thumbnail': icon})
                except:
                    pass
                if not castwiththumb:
                    castwiththumb = '0'
                try:
                    thumb_path = item['still_path']
                except:
                    thumb_path = ''
                if thumb_path:
                    if self.original_artwork == 'true':
                        thumb = self.tmdb_image_link + thumb_path
                    else:
                        thumb = self.tmdb_image_link % ('300', thumb_path)
                else:
                    thumb = fanart
                self.list.append({'title': title, 'label': label, 'season': season, 'episode': episode, 'tvshowtitle': tvshowtitle, 'year': year, 'premiered': premiered,
                    'rating': rating, 'votes': votes, 'director': director, 'writer': writer, 'castwiththumb': castwiththumb, 'duration': duration,
                    'status': status, 'plot': episodeplot, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb, 'unaired': unaired, 'thumb': thumb, 'poster': poster,
                    'fanart': fanart, 'banner': banner,'clearlogo': clearlogo, 'clearart': clearart, 'landscape': landscape}
                )
            except:
                #log_utils.log('tmdb_list', 1)
                pass
        return self.list


    def episodeDirectory(self, items):
        if items == None or len(items) == 0:
            control.idle()
            #sys.exit()
        sysaddon = sys.argv[0]
        syshandle = int(sys.argv[1])
        addonPoster = control.addonPoster()
        addonBanner = control.addonBanner()
        addonFanart = control.addonFanart()
        settingFanart = control.setting('fanart')
        traktCredentials = trakt.getTraktCredentialsInfo()
        tmdbCredentials = tmdb_utils.getTMDbCredentialsInfo()
        isPlayable = True if not 'plugin' in control.infoLabel('Container.PluginName') else False
        indicators = playcount.getTVShowIndicators(refresh=True)
        try:
            multi = [i['tvshowtitle'] for i in items]
        except:
            multi = []
        multi = len([x for y,x in enumerate(multi) if x not in multi[:y]])
        multi = True if multi > 1 else False
        try:
            sysaction = items[0]['action']
        except:
            sysaction = ''
        isFolder = False if not sysaction == 'episodes' else True
        playbackMenu = '[COLOR goldenrod]Free99[/COLOR] Select Source' if control.setting('hosts.mode') == '2' else '[COLOR goldenrod]Free99[/COLOR] Auto Play'
        watchedMenu = '[COLOR goldenrod]Free99[/COLOR] Mark Watched in Trakt' if trakt.getTraktIndicatorsInfo() == True else 'Watched in Scrubs'
        unwatchedMenu = '[COLOR goldenrod]Free99[/COLOR] Mark Unwatched in Trakt' if trakt.getTraktIndicatorsInfo() == True else 'Unwatched in Scrubs'
        for i in items:
            try:
                if not 'label' in i:
                    i['label'] = i['title']
                if i['label'] == '0':
                    label = '%sx%02d . %s %s' % (i['season'], int(i['episode']), 'Episode', i['episode'])
                else:
                    label = '%sx%02d . %s' % (i['season'], int(i['episode']), i['label'])
                if multi == True:
                    label = '%s - %s' % (i['tvshowtitle'], label)
                try:
                    if i['unaired'] == 'true':
                        label = '[COLOR %s][I]%s[/I][/COLOR]' % (self.unairedcolor, label)
                except:
                    pass
                imdb, tvdb, tmdb, year, season, episode = i['imdb'], i['tvdb'], i['tmdb'], i['year'], i['season'], i['episode']
                poster = i['poster'] if 'poster' in i and not i['poster'] == '0' else addonPoster
                fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else addonFanart
                banner1 = i.get('banner', '')
                banner = banner1 or fanart or addonBanner
                if 'landscape' in i and not i['landscape'] == '0':
                    landscape = i['landscape']
                else:
                    landscape = fanart
                seasons_meta = {'poster': poster, 'fanart': fanart, 'banner': banner, 'clearlogo': i.get('clearlogo', '0'), 'clearart': i.get('clearart', '0'), 'landscape': landscape, 'duration': i.get('duration', '0'), 'status': i.get('status', '0')}
                seas_meta = urllib_parse.quote_plus(json.dumps(seasons_meta))
                systitle = urllib_parse.quote_plus(i['title'])
                systvshowtitle = urllib_parse.quote_plus(i['tvshowtitle'])
                syspremiered = urllib_parse.quote_plus(i['premiered'])
                meta = dict((k,v) for k, v in six.iteritems(i) if not v == '0')
                meta.update({'mediatype': 'episode'})
                meta.update({'code': tmdb, 'imdbnumber': imdb})
                meta.update({'trailer': '%s?action=trailer&name=%s&tmdb=%s&imdb=%s&season=%s&episode=%s' % (sysaddon, systvshowtitle, tmdb, imdb, season, episode)})
                if not 'duration' in i:
                    meta.update({'duration': '45'})
                elif i['duration'] == '0':
                    meta.update({'duration': '45'})
                try:
                    meta.update({'duration': str(int(meta['duration']) * 60)})
                except:
                    pass
                try:
                    meta.update({'year': re.findall('(\d{4})', i['premiered'])[0]})
                except:
                    pass
                try:
                    meta.update({'title': i['label']})
                except:
                    pass
                try:
                    meta.update({'tvshowyear': i['year']}) # Kodi uses the year (the year the show started) as the year for the episode. Change it from the premiered date.
                except:
                    pass
                meta.update({'poster': poster, 'fanart': fanart, 'banner': banner})
                sysmeta = urllib_parse.quote_plus(json.dumps(meta))
                url = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered, sysmeta, self.systime)
                sysurl = urllib_parse.quote_plus(url)
                path = '%s?action=play&title=%s&year=%s&imdb=%s&tmdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&premiered=%s' % (sysaddon, systitle, year, imdb, tmdb, tvdb, season, episode, systvshowtitle, syspremiered)
                if isFolder == True:
                    url = '%s?action=episodes&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s&season=%s&episode=%s' % (sysaddon, systvshowtitle, year, imdb, tmdb, seas_meta, season, episode)
                cm = []
                if multi == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] Browse Series', 'Container.Update(%s?action=seasons&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s&meta=%s,return)' % (sysaddon, systvshowtitle, year, imdb, tmdb, seas_meta)))
                if traktCredentials == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] Trakt Manager', 'RunPlugin(%s?action=trakt_manager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, systvshowtitle, tmdb)))
                if tmdbCredentials == True:
                    cm.append(('[COLOR goldenrod]Free99[/COLOR] TMDb Manager', 'RunPlugin(%s?action=tmdb_manager&name=%s&tmdb=%s&content=tvshow)' % (sysaddon, systvshowtitle, tmdb)))
                cm.append(('[COLOR goldenrod]Free99[/COLOR] Add to Library', 'RunPlugin(%s?action=tvshow_to_library&tvshowtitle=%s&year=%s&imdb=%s&tmdb=%s)' % (sysaddon, systvshowtitle, year, imdb, tmdb)))
                if kodi_version < 17:
                    cm.append(('Information', 'Action(Info)'))
                try:
                    overlay = int(playcount.getEpisodeOverlay(indicators, imdb, tmdb, season, episode))
                    if overlay == 7:
                        cm.append((unwatchedMenu, 'RunPlugin(%s?action=episodes_playcount&imdb=%s&tmdb=%s&season=%s&episode=%s&query=6)' % (sysaddon, imdb, tmdb, season, episode)))
                        meta.update({'playcount': 1, 'overlay': 7})
                    else:
                        cm.append((watchedMenu, 'RunPlugin(%s?action=episodes_playcount&imdb=%s&tmdb=%s&season=%s&episode=%s&query=7)' % (sysaddon, imdb, tmdb, season, episode)))
                        meta.update({'playcount': 0, 'overlay': 6})
                except:
                    pass
                if isFolder == False:
                    cm.append((playbackMenu, 'RunPlugin(%s?action=alter_sources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))
                try:
                    item = control.item(label=label, offscreen=True)
                except:
                    item = control.item(label=label)
                art = {}
                if self.episode_thumbs == 'true':
                    thumb = poster
                else:
                    thumb = meta.get('thumb', '') or fanart
                clearlogo = meta.get('clearlogo', '')
                clearart = meta.get('clearart', '')
                art.update({'icon': thumb, 'thumb': thumb, 'banner': banner, 'poster': thumb, 'tvshow.poster': poster, 'season.poster': poster, 'landscape': landscape, 'clearlogo': clearlogo, 'clearart': clearart})
                if settingFanart == 'true':
                    art.update({'fanart': fanart})
                elif not addonFanart == None:
                    art.update({'fanart': addonFanart})
                item.setArt(art)
                item.addContextMenuItems(cm)
                if isPlayable:
                    item.setProperty('IsPlayable', 'true')
                offset = bookmarks.get('episode', imdb, season, episode, True)
                if float(offset) > 120:
                    percentPlayed = int(float(offset) / float(meta['duration']) * 100)
                    item.setProperty('resumetime', str(offset))
                    item.setProperty('percentplayed', str(percentPlayed))
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
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)
            except:
                #log_utils.log('episodeDirectory', 1)
                pass
        if self.episode_views == 'true':
            control.content(syshandle, 'seasons')
            control.directory(syshandle, cacheToDisc=True)
            views.setView('seasons', {'skin.aeon.nox.silvo' : 50, 'skin.estuary': 55, 'skin.confluence': 500}) #View 50 List #View 501 LowList
        else:
            control.content(syshandle, 'episodes')
            control.directory(syshandle, cacheToDisc=True)
            views.setView('episodes', {'skin.aeon.nox.silvo' : 50, 'skin.estuary': 55, 'skin.confluence': 504}) #View 50 List #View 501 LowList


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
                    item = control.item(label=name, offscreen=True)
                except:
                    item = control.item(label=name)
                item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': addonFanart})
                item.addContextMenuItems(cm)
                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            except:
                #log_utils.log('addDirectory', 1)
                pass
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)


