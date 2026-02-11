# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file player.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import base64
import codecs
import gzip
import json
import os
import re
import sys
import time
import xbmc

import six
from six.moves import xmlrpc_client


import urllib
from urllib.parse import quote_plus, unquote_plus


from resources.lib.modules import bookmarks
from resources.lib.modules import control
from resources.lib.modules import cleantitle
from resources.lib.modules import playcount
from resources.lib.modules import trakt
from resources.lib.modules import log_utils


class player(xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)

    def run(self, title, year, season, episode, imdb, tmdb, url, meta):
        try:
            control.sleep(200)

            self.totalTime = 0
            self.currentTime = 0

            self.content = 'movie' if season == None or episode == None else 'episode'

            self.title = title
            self.year = year
            self.name = urllib.parse.quote_plus(title) + urllib.parse.quote_plus(' (%s)' % year) if self.content == 'movie' else urllib.parse.quote_plus(
                title) + urllib.parse.quote_plus(' S%02dE%02d' % (int(season), int(episode)))
            self.name = urllib.parse.unquote_plus(self.name)
            self.season = '%01d' % int(season) if self.content == 'episode' else None
            self.episode = '%01d' % int(episode) if self.content == 'episode' else None

            self.DBID = None
            self.imdb = imdb if not imdb == None else '0'
            self.tmdb = tmdb if not tmdb == None else '0'
            self.ids = {'imdb': self.imdb, 'tmdb': self.tmdb}
            self.ids = dict((k,v) for k, v in six.iteritems(self.ids) if not v == '0')

            self.offset = bookmarks.get(self.content, imdb, season, episode)

            poster, thumb, fanart, clearlogo, clearart, discart, meta = self.getMeta(meta)


            item = control.item(path=url)
            if self.content == 'movie':
                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': poster, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart})
            else:
                item.setArt({'icon': thumb, 'thumb': thumb, 'tvshow.poster': poster, 'season.poster': poster, 'fanart': fanart, 'clearlogo': clearlogo, 'clearart': clearart})
            item.setInfo(type='video', infoLabels = control.metadataClean(meta))

            if 'plugin' in control.infoLabel('Container.PluginName'):
                control.player.play(url, item)

            control.resolve(int(sys.argv[1]), True, item)

            control.window.setProperty('script.trakt.ids', json.dumps(self.ids))

            self.keepPlaybackAlive()

            control.window.clearProperty('script.trakt.ids')
        except Exception as e:
            log_utils.log('player_fail')
            return

    def getMeta(self, meta):

        try:
            poster = meta.get('poster')
            thumb = meta.get('thumb') or poster
            fanart = meta.get('fanart')
            clearlogo = meta.get('clearlogo', '')
            clearart = meta.get('clearart', '')
            discart = meta.get('discart', '')

            return poster, thumb, fanart, clearlogo, clearart, discart, meta
        except:
            pass




        try:
            if not self.content == 'movie': raise Exception()

            meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "originaltitle", "year", "genre", "studio", "country", "runtime", "rating", "votes", "mpaa", "director", "writer", "plot", "plotoutline", "tagline", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
            meta = six.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['movies']

            t = cleantitle.get(self.title)
            meta = [i for i in meta if self.year == str(i['year']) and (t == cleantitle.get(i['title']) or t == cleantitle.get(i['originaltitle']))][0]

            for k, v in six.iteritems(meta):
                if type(v) == list:
                    try:
                        meta[k] = str(' / '.join([six.ensure_str(i) for i in v]))
                    except:
                        meta[k] = ''
                else:
                    try:
                        meta[k] = str(six.ensure_str(v))
                    except:
                        meta[k] = str(v)

            if not 'plugin' in control.infoLabel('Container.PluginName'):
                self.DBID = meta['movieid']

            poster = thumb = meta['thumbnail']

            return poster, thumb, '', '', '', '', meta
        except:
            pass

        try:
            if not self.content == 'episode':
                raise Exception()

            meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["title", "year", "thumbnail", "file"]}, "id": 1}' % (self.year, str(int(self.year)+1), str(int(self.year)-1)))
            meta = six.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['tvshows']

            t = cleantitle.get(self.title)
            meta = [i for i in meta if self.year == str(i['year']) and t == cleantitle.get(i['title'])][0]

            tvshowid = meta['tvshowid']
            poster = meta['thumbnail']

            meta = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{ "tvshowid": %d, "filter":{"and": [{"field": "season", "operator": "is", "value": "%s"}, {"field": "episode", "operator": "is", "value": "%s"}]}, "properties": ["title", "season", "episode", "showtitle", "firstaired", "runtime", "rating", "director", "writer", "plot", "thumbnail", "file"]}, "id": 1}' % (tvshowid, self.season, self.episode))
            meta = six.ensure_text(meta, errors='ignore')
            meta = json.loads(meta)['result']['episodes'][0]

            for k, v in six.iteritems(meta):
                if type(v) == list:
                    try: meta[k] = str(' / '.join([six.ensure_str(i) for i in v]))
                    except: meta[k] = ''
                else:
                    try: meta[k] = str(six.ensure_str(v))
                    except: meta[k] = str(v)

            if not 'plugin' in control.infoLabel('Container.PluginName'):
                self.DBID = meta['episodeid']

            thumb = meta['thumbnail']

            return poster, thumb, '', '', '', '', meta
        except:
            pass

        poster, thumb, fanart, clearlogo, clearart, discart, meta = '', '', '', '', '', '', {'title': self.name}
        return poster, thumb, fanart, clearlogo, clearart, discart, meta



#TC 2/01/19 started
    def keepPlaybackAlive(self):
        pname = '%s.player.overlay' % control.addonInfo('id')
        control.window.clearProperty(pname)

        if self.content == 'movie':
            overlay = playcount.getMovieOverlay(playcount.getMovieIndicators(), self.imdb)

        elif self.content == 'episode':
            overlay = playcount.getEpisodeOverlay(playcount.getTVShowIndicators(), self.imdb, self.tmdb, self.season, self.episode)

        else:
            overlay = '6'

        for i in range(0, 240):
            if self.isPlayingVideo(): break
            xbmc.sleep(1000)

        if overlay == '7':

            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()
                except:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'movie':

            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = (self.currentTime / self.totalTime >= .92)
                    property = control.window.getProperty(pname)

                    if watcher == True and not property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markMovieDuringPlayback(self.imdb, '7')

                    elif watcher == False and not property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markMovieDuringPlayback(self.imdb, '6')
                except:
                    pass
                xbmc.sleep(2000)

        elif self.content == 'episode':

            while self.isPlayingVideo():
                try:
                    self.totalTime = self.getTotalTime()
                    self.currentTime = self.getTime()

                    watcher = (self.currentTime / self.totalTime >= .92)
                    property = control.window.getProperty(pname)

                    if watcher == True and not property == '7':
                        control.window.setProperty(pname, '7')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '7')

                    elif watcher == False and not property == '6':
                        control.window.setProperty(pname, '6')
                        playcount.markEpisodeDuringPlayback(self.imdb, self.tmdb, self.season, self.episode, '6')
                except:
                    pass
                xbmc.sleep(2000)

        control.window.clearProperty(pname)

    def libForPlayback(self):
        try:
            if self.DBID == None: raise Exception()

            if self.content == 'movie':
                rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : 1 }, "id": 1 }' % str(self.DBID)
            elif self.content == 'episode':
                rpc = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : 1 }, "id": 1 }' % str(self.DBID)

            control.jsonrpc(rpc)
            control.refresh()
        except:
            pass

    def idleForPlayback(self):
        for i in range(0, 400):
            if control.condVisibility('Window.IsActive(busydialog)') == 1 or control.condVisibility('Window.IsActive(busydialognocancel)') == 1:
                control.idle()
            else:
                break
            control.sleep(100)


    def onAVStarted(self):
        control.execute('Dialog.Close(all,true)')

        if control.setting('bookmarks') == 'true' and int(self.offset) > 120 and self.isPlayingVideo():
            if control.setting('bookmarks.auto') == 'true':
                self.seekTime(float(self.offset))
            else:
                self.pause()
                minutes, seconds = divmod(float(self.offset), 60)
                hours, minutes = divmod(minutes, 60)
                label = '%02d:%02d:%02d' % (hours, minutes, seconds)
                label = control.lang2(12022).format(label)
                if control.setting('bookmarks.auto') == 'true' and trakt.getTraktCredentialsInfo() == True:
                    yes = control.yesnoDialog(label + '[CR]  (Trakt scrobble)', heading=control.lang2(13404))
                else:
                    yes = control.yesnoDialog(label, heading=control.lang2(13404))
                if yes:
                    self.seekTime(float(self.offset))
                control.sleep(1000)
                self.pause()

        subtitles().get(self.name, self.imdb, self.season, self.episode)
        self.idleForPlayback()

    def onPlayBackStarted(self):

        if control.setting('bookmarks') == 'true' and int(self.offset) > 120 and self.isPlayingVideo():
            if control.setting('bookmarks.auto') == 'true':
                self.seekTime(float(self.offset))
            else:
                self.pause()
                minutes, seconds = divmod(float(self.offset), 60)
                hours, minutes = divmod(minutes, 60)
                label = '%02d:%02d:%02d' % (hours, minutes, seconds)
                label = control.lang2(12022).format(label)
                if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() == True:
                    yes = control.yesnoDialog(label + '[CR]  (Trakt scrobble)', heading=control.lang2(13404))
                else:
                    yes = control.yesnoDialog(label, heading=control.lang2(13404))
                if yes:
                    self.seekTime(float(self.offset))
                control.sleep(1000)
                self.pause()


            subtitles().get(self.name, self.imdb, self.season, self.episode)
            self.idleForPlayback()
        else:
            #self.onAVStarted()
            pass

    def onPlayBackStopped(self):
        if self.totalTime == 0 or self.currentTime == 0:
            control.sleep(2000)
            return


        bookmarks.reset(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode)

        if (trakt.getTraktCredentialsInfo() == True and control.setting('trakt.scrobble') == 'true'):
            bookmarks.set_scrobble(self.currentTime, self.totalTime, self.content, self.imdb, self.season, self.episode)

        if float(self.currentTime / self.totalTime) >= 0.92:
            self.libForPlayback()
            
            control.refresh()


    def onPlayBackEnded(self):
        self.onPlayBackStopped()


class subtitles:
    def get(self, name, imdb, season, episode):
        try:
            if not control.setting('subtitles') == 'true': raise Exception()

            OSuser = control.setting('OSuser') or ''
            OSpass = control.setting('OSpass') or ''

            langDict = {
                'Afrikaans': 'afr', 'Albanian': 'alb', 'Arabic': 'ara', 'Armenian': 'arm', 'Basque': 'baq',
                'Bengali': 'ben', 'Bosnian': 'bos', 'Breton': 'bre', 'Bulgarian': 'bul', 'Burmese': 'bur',
                'Catalan': 'cat', 'Chinese': 'chi', 'Croatian': 'hrv', 'Czech': 'cze', 'Danish': 'dan', 'Dutch': 'dut',
                'English': 'eng', 'Esperanto': 'epo', 'Estonian': 'est', 'Finnish': 'fin', 'French': 'fre',
                'Galician': 'glg', 'Georgian': 'geo', 'German': 'ger', 'Greek': 'ell', 'Hebrew': 'heb', 'Hindi': 'hin',
                'Hungarian': 'hun', 'Icelandic': 'ice', 'Indonesian': 'ind', 'Italian': 'ita', 'Japanese': 'jpn',
                'Kazakh': 'kaz', 'Khmer': 'khm', 'Korean': 'kor', 'Latvian': 'lav', 'Lithuanian': 'lit',
                'Luxembourgish': 'ltz', 'Macedonian': 'mac', 'Malay': 'may', 'Malayalam': 'mal', 'Manipuri': 'mni',
                'Mongolian': 'mon', 'Montenegrin': 'mne', 'Norwegian': 'nor', 'Occitan': 'oci', 'Persian': 'per',
                'Polish': 'pol', 'Portuguese': 'por,pob', 'Portuguese(Brazil)': 'pob,por', 'Romanian': 'rum',
                'Russian': 'rus', 'Serbian': 'scc', 'Sinhalese': 'sin', 'Slovak': 'slo', 'Slovenian': 'slv',
                'Spanish': 'spa', 'Swahili': 'swa', 'Swedish': 'swe', 'Syriac': 'syr', 'Tagalog': 'tgl', 'Tamil': 'tam',
                'Telugu': 'tel', 'Thai': 'tha', 'Turkish': 'tur', 'Ukrainian': 'ukr', 'Urdu': 'urd'}

            codePageDict = {'ara': 'cp1256', 'ar': 'cp1256', 'ell': 'cp1253', 'el': 'cp1253', 'heb': 'cp1255',
                            'he': 'cp1255', 'tur': 'cp1254', 'tr': 'cp1254', 'rus': 'cp1251', 'ru': 'cp1251'}

            quality = ['bluray', 'hdrip', 'brrip', 'bdrip', 'dvdrip', 'webrip', 'hdtv']

            langs = []
            try:
                try:
                    langs = langDict[control.setting('subtitles.lang.1')].split(',')
                except:
                    langs.append(langDict[control.setting('subtitles.lang.1')])
            except:
                pass
            try:
                try:
                    langs = langs + langDict[control.setting('subtitles.lang.2')].split(',')
                except:
                    langs.append(langDict[control.setting('subtitles.lang.2')])
            except:
                pass


            try:
                subLang = xbmc.Player().getSubtitles()
            except:
                subLang = ''
            if subLang == langs[0]:
                raise Exception()

            server = xmlrpc_client.Server('https://api.opensubtitles.org/xml-rpc', verbose=0)
            token = server.LogIn(OSuser, OSpass, 'en', 'XBMC_Subtitles_v5.2.14')['token']

            sublanguageid = ','.join(langs)
            imdbid = re.sub('[^0-9]', '', imdb)

            if not (season == None or episode == None):
                result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid, 'season': season, 'episode': episode}])['data']
                fmt = ['hdtv']
            else:
                result = server.SearchSubtitles(token, [{'sublanguageid': sublanguageid, 'imdbid': imdbid}])['data']
                try:
                    vidPath = xbmc.Player().getPlayingFile()
                except:
                    vidPath = ''
                fmt = re.split('\.|\(|\)|\[|\]|\s|\-', vidPath)
                fmt = [i.lower() for i in fmt]
                fmt = [i for i in fmt if i in quality]

            filter = []
            result = [i for i in result if i['SubSumCD'] == '1']

            for lang in langs:
                filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in fmt)]
                filter += [i for i in result if i['SubLanguageID'] == lang and any(x in i['MovieReleaseName'].lower() for x in quality)]
                filter += [i for i in result if i['SubLanguageID'] == lang]

            try:
                lang = xbmc.convertLanguage(filter[0]['SubLanguageID'], xbmc.ISO_639_1)
            except:
                lang = filter[0]['SubLanguageID']

            content = [filter[0]['IDSubtitleFile'], ]
            content = server.DownloadSubtitles(token, content)
            content = base64.b64decode(content['data'][0]['data'])
            content = gzip.GzipFile(fileobj=six.BytesIO(content)).read()

            subtitle = control.transPath('special://temp/')
            subtitle = os.path.join(subtitle, 'TemporarySubs.%s.srt' % lang)

            if control.setting('subtitles.utf') == 'true':
                codepage = codePageDict.get(lang, '')
                if codepage and not filter[0].get('SubEncoding', '').lower() == 'utf-8':
                    try:
                        content_encoded = codecs.decode(content, codepage)
                        content = codecs.encode(content_encoded, 'utf-8')
                    except:
                        pass

            file = control.openFile(subtitle, 'w')
            file.write(content)
            file.close()

            control.sleep(1000)
            xbmc.Player().setSubtitles(subtitle)
        except:
            pass
