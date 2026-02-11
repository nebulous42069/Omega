# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file sources.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import json

import six
from six.moves import zip, reduce

import datetime
import random
import re
import sys
import time
import traceback
import urllib

from urllib.parse import *

from resources.lib.modules import trakt
from resources.lib.modules import tvmaze
from resources.lib.modules import cache
from resources.lib.modules import control
from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import debrid
from resources.lib.modules import workers
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

try:
    import resolveurl
except:
    pass

try:
    import xbmc
except:
    pass

class sources:
    def __init__(self):
        self.getConstants()
        self.sources = []

    def play(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, meta, select='1'):
        try:
            url = None

            items = self.getSources(title, year, imdb, tmdb, season, episode, tvshowtitle, premiered)
            select = control.setting('hosts.mode') if not select else select

            metadata = json.loads(meta) if not meta == None else {}
            mediatype = metadata['mediatype'] if 'mediatype' in metadata else ''

            if mediatype == 'movie':
                title = title
            else:
                if not tvshowtitle == None:
                    title = tvshowtitle if len(tvshowtitle) > 0 else title
                else:
                    title = title

            if len(items) > 0:

                if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
                    control.window.clearProperty(self.itemProperty)
                    control.window.setProperty(self.itemProperty, json.dumps(items))

                    control.window.clearProperty(self.metaProperty)
                    control.window.setProperty(self.metaProperty, meta)

                    control.sleep(200)

                    return control.execute('Container.Update(%s?action=addItem&title=%s)' % (sys.argv[0], urllib.parse.quote_plus(title)))

                elif select == '0' or select == '1':
                    url = self.sourcesDialog(items)
                else:
                    url = self.sourcesDirect(items)

            if url == 'close://' or not url:
                self.url = url
                return self.errorForSources()

            try:
                meta = json.loads(meta)
            except:
               pass

            from resources.lib.modules.player import player
            player().run(title, year, season, episode, imdb, tmdb, url, meta)
        except:
            pass

    def addItem(self, title):


        def sourcesDirMeta(metadata):
            if metadata == None: return metadata
            allowed = ['poster', 'fanart', 'thumb', 'title', 'year', 'tvshowtitle', 'season', 'episode', 'rating', 'director', 'plot', 'trailer', 'icon', 'mediatype', 'clearlogo', 'clearart', 'discart']
            return {k: v for k, v in metadata.items() if k in allowed}

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()
        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')
        addonClearlogo, addonClearart = control.addonClearlogo(), control.addonClearart()
        addonThumb, addonDiscart = control.addonThumb(), control.addonDiscart()

        control.playlist.clear()

        items = control.window.getProperty(self.itemProperty)
        items = json.loads(items)

        if items == None or len(items) == 0: control.idle() ; sys.exit()

        meta = control.window.getProperty(self.metaProperty)
        meta = json.loads(meta)
        meta = sourcesDirMeta(meta)

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        downloads = True if control.setting('downloads') == 'true' and not (control.setting('movie.download.path') == '' or control.setting('tv.download.path') == '') else False

        systitle = sysname = urllib.parse.quote_plus(title)

        if 'tvshowtitle' in meta and 'season' in meta and 'episode' in meta:
            sysname += urllib.parse.quote_plus(' S%02dE%02d' % (int(meta['season']), int(meta['episode'])))
        elif 'year' in meta:
            sysname += urllib.parse.quote_plus(' (%s)' % meta['year'])

        poster = meta.get('poster3') or '0'
        if poster == '0': poster = meta.get('poster', '') or addonPoster

        fanart = meta.get('fanart2') or '0'
        if fanart == '0': fanart = meta.get('fanart') or addonFanart

        thumb = meta['thumb'] if 'thumb' in meta else '0'
        if thumb == '0': thumb = addonThumb

        banner = meta['banner'] if 'banner' in meta else '0'
        if banner == '0': banner = addonBanner

        clearlogo = meta['clearlogo'] if 'clearlogo' in meta else '0'
        if clearlogo == '0': clearlogo = addonClearlogo

        clearart = meta['clearart'] if 'clearart' in meta else '0'
        if clearart == '0': clearart = addonClearart

        discart = meta['discart'] if 'discart' in meta else '0'
        if discart == '0': discart = addonDiscart

        if not control.setting('fanart') == 'true':
            fanart = addonFanart
            poster = addonPoster
            banner = addonBanner
            thumb = addonThumb
            clearlogo = addonClearlogo
            clearart = addonClearart
            discart = addonDiscart

        sysimage = urllib.parse.quote_plus(str(poster))

        downloadMenu = control.lang(32403)

        for i in range(len(items)):
            try:
                label = str(items[i]['label'])
                if control.setting('sourcelist.multiline') == 'true': label = str(items[i]['multiline_label'])

                syssource = urllib.parse.quote_plus(json.dumps([items[i]]))

                sysurl = '%s?action=playItem&title=%s&source=%s' % (sysaddon, systitle, syssource)

                cm = []

                if downloads == True:
                    cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&source=%s)' % (sysaddon, sysname, sysimage, syssource)))

                item = control.item(label=label)

                item.setArt({'icon': poster, 'thumb': poster, 'poster': poster, 'banner': banner, 'fanart': fanart, 'landscape': fanart, 'clearlogo': clearlogo, 'clearart': clearart, 'discart': discart})

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                item.addContextMenuItems(cm)
                item.setInfo(type='Video', infoLabels=meta)

                control.addItem(handle=syshandle, url=sysurl, listitem=item, isFolder=False)
            except:
                pass

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=True)

    #TC 2/01/19 started
    def playItem(self, title, source):
        try:
            meta = control.window.getProperty(self.metaProperty)
            meta = json.loads(meta)

            year = meta['year'] if 'year' in meta else None
            season = meta['season'] if 'season' in meta else None
            episode = meta['episode'] if 'episode' in meta else None

            imdb = meta['imdb'] if 'imdb' in meta else None
            tvdb = meta['tvdb'] if 'tvdb' in meta else None
            tmdb = meta['tmdb'] if 'tmdb' in meta else None

            next = []
            prev = []
            total = []

            for i in range(1, 1000):
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total:
                        raise Exception()
                    total.append(u)
                    u = dict(urllib.parse.parse_qsl(u.replace('?', '')))
                    u = json.loads(u['source'])[0]
                    next.append(u)
                except:
                    break
            for i in range(-1000,0)[::-1]:
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total:
                        raise Exception()
                    total.append(u)
                    u = dict(urllib.parse.parse_qsl(u.replace('?', '')))
                    u = json.loads(u['source'])[0]
                    prev.append(u)
                except:
                    break

            items = json.loads(source)
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    try:
                        if progressDialog.iscanceled(): break
                        progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label'])+'\n'+ str(' '))
                    except:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header2)+'\n'+ str(items[i]['label']))

                    if items[i]['source'] == block: raise Exception('block')

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    offset = 60 * 2 if items[i].get('source') in self.hostcapDict else 0

                    m = ''

                    for x in range(3600):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() == False or x > 30 + offset) and not k:
                            break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() == False or x > 30 + offset) and not k:
                            break
                        time.sleep(0.5)

                    for x in range(30):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except:
                            pass

                        if m == '':
                            break
                        if w.is_alive() == False:
                            break
                        time.sleep(0.5)

                    if w.is_alive() == True:
                        block = items[i]['source']

                    if self.url == None:
                        raise Exception()

                    try:
                        progressDialog.close()
                    except:
                        pass

                    control.sleep(200)
                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')

                    from resources.lib.modules.player import player
                    player().run(title, year, season, episode, imdb, tmdb, self.url, meta)

                    return self.url
                except Exception as e:
                    pass

            try:
                progressDialog.close()
            except:
                pass

            self.errorForSources()
        except:
            pass


    def getSources(self, title, year, imdb, tmdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):

        progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
        progressDialog.create(control.addonInfo('name'), '')
        progressDialog.update(0)

        self.prepareSources()

        sourceDict = self.sourceDict

        progressDialog.update(0, control.lang(32600))

        content = 'movie' if tvshowtitle == None else 'episode'
        if content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
            genres = trakt.getGenre('movie', 'imdb', imdb)
        else:
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
            genres = trakt.getGenre('show', 'imdb', imdb)

        sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter') or not i[1].genre_filter or any(x in i[1].genre_filter for x in genres)]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == None]

        language = self.getLanguage()
        sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]

        try:
            sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except:
            sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == 'false']

        sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

        random.shuffle(sourceDict)
        sourceDict = sorted(sourceDict, key=lambda i: i[2])

        threads = []

        if content == 'movie':
            title = self.getTitle(title)
            localtitle = self.getLocalTitle(title, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtitle, content)
            for i in sourceDict:
                threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
        else:
            tvshowtitle = self.getTitle(tvshowtitle)
            localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tmdb, content)
            aliases = self.getAliasTitles(imdb, localtvshowtitle, content)

            for i in sourceDict:
                threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))


        s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
        s = [(i[3].getName(), i[0], i[2]) for i in s]

        mainsourceDict = [i[0] for i in s if i[2] == 0]
        sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

        [i.start() for i in threads]

        string1 = control.lang(32404)
        string2 = control.lang(32405)
        string3 = control.lang(32406)
        string4 = control.lang(32601)
        string5 = control.lang(32602)
        string6 = control.lang(32606)
        string7 = control.lang(32607)

        try:
            timeout = int(control.setting('scrapers.timeout.1'))
        except:
            pass

        #fixed oh 27-4-2021
        quality = int(control.setting('hosts.quality')) or 0
        debrid_only = control.setting('debrid.only') or false

        line1 = line2 = line3 = ""

        pre_emp =  control.setting('preemptive.termination')
        pre_emp_limit = int(control.setting('preemptive.limit'))
        source_4k = d_source_4k = 0
        source_1080 = d_source_1080 = 0
        source_720 = d_source_720 = 0
        source_sd = d_source_sd = 0
        total = d_total = 0

        debrid_list = debrid.debrid_resolvers
        debrid_status = debrid.status()

        total_format = '[COLOR %s][B]%s[/B][/COLOR]'
        pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')
        pdiag_bg_format = '4K:%s(%s)|1080p:%s(%s)|720p:%s(%s)|SD:%s(%s)|T:%s(%s)'.split('|')

        for i in range(0, 4 * timeout):
            if str(pre_emp) == 'true':
                if quality in [0, 1]:
                    if (source_4k + d_source_4k) >= int(pre_emp_limit): break
                elif quality == 1:
                    if (source_1080 + d_source_1080) >= int(pre_emp_limit): break
                elif quality == 2:
                    if (source_720 + d_source_720) >= int(pre_emp_limit): break
                elif quality == 3:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit): break
                else:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit): break
            try:
                if control.monitor.abortRequested(): return sys.exit()

                try:
                    if progressDialog.iscanceled():
                        break
                except:
                    pass

                if len(self.sources) > 0:
                    if quality == 0:
                        source_4k = len([e for e in self.sources if e['quality'] == '4K' and e['debridonly'] == False])
                        source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and e['debridonly'] == False])
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] == False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] == False])
                    elif quality == 1:
                        source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and e['debridonly'] == False])
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] == False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] == False])
                    elif quality == 2:
                        source_1080 = len([e for e in self.sources if e['quality'] in ['1080p'] and e['debridonly'] == False])
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] == False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] == False])
                    elif quality == 3:
                        source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and e['debridonly'] == False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] == False])
                    else:
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] == False])

                    total = source_4k + source_1080 + source_720 + source_sd

                    if debrid_status:
                        if quality == 0:
                            for d in debrid_list:
                                d_source_4k = len([e for e in self.sources if e['quality'] in ['4k', '4K'] and d.valid_url(e['url'], e['source'])])
                                d_source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and d.valid_url(e['url'], e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] in ['sd', 'SD'] and d.valid_url(e['url'], e['source'])])
                        elif quality == 1:
                            for d in debrid_list:
                                d_source_1080 = len([e for e in self.sources if e['quality'] in ['1440p','1080p'] and d.valid_url(e['url'], e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])
                        elif quality == 2:
                            for d in debrid_list:
                                d_source_1080 = len([e for e in self.sources if e['quality'] in ['1080p'] and d.valid_url(e['url'], e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])
                        elif quality == 3:
                            for d in debrid_list:
                                d_source_720 = len([e for e in self.sources if e['quality'] in ['720p','HD'] and d.valid_url(e['url'], e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])
                        else:
                            for d in debrid_list:
                                d_source_sd = len([e for e in self.sources if e['quality'] == 'SD' and d.valid_url(e['url'], e['source'])])

                        d_total = d_source_4k + d_source_1080 + d_source_720 + d_source_sd

                if debrid_status:
                    d_4k_label = total_format % ('red', d_source_4k) if d_source_4k == 0 else total_format % ('lime', d_source_4k)
                    d_1080_label = total_format % ('red', d_source_1080) if d_source_1080 == 0 else total_format % ('lime', d_source_1080)
                    d_720_label = total_format % ('red', d_source_720) if d_source_720 == 0 else total_format % ('lime', d_source_720)
                    d_sd_label = total_format % ('red', d_source_sd) if d_source_sd == 0 else total_format % ('lime', d_source_sd)
                    d_total_label = total_format % ('red', d_total) if d_total == 0 else total_format % ('lime', d_total)
                source_4k_label = total_format % ('red', source_4k) if source_4k == 0 else total_format % ('lime', source_4k)
                source_1080_label = total_format % ('red', source_1080) if source_1080 == 0 else total_format % ('lime', source_1080)
                source_720_label = total_format % ('red', source_720) if source_720 == 0 else total_format % ('lime', source_720)
                source_sd_label = total_format % ('red', source_sd) if source_sd == 0 else total_format % ('lime', source_sd)
                source_total_label = total_format % ('red', total) if total == 0 else total_format % ('lime', total)
                if (i / 2) < timeout:
                    try:
                        #@todo oh fix for double duty mainleft and info in threads
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() == True and x.getName() in mainsourceDict]
                        info = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() == True]
                        if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
                            break # improve responsiveness
                        if debrid_status:
                            if quality == 0:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format)) % (string6, d_4k_label, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format)) % (string7, source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                    print (line1 + '\n' + line2)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[:-1]) % (source_4k_label, d_4k_label, source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label)
                            elif quality == 1:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 2:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[1:])) % (string7, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[1:]) % (source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            elif quality == 3:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[2:])) % (string6, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[2:])) % (string7, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[2:]) % (source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label, d_total_label)
                            else:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[3:])) % (string6, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[3:])) % (string7, source_sd_label, str(string4), source_total_label)
                                else:
                                    control.idle()
                                    line1 = '|'.join(pdiag_bg_format[3:]) % (source_sd_label, d_sd_label, source_total_label, d_total_label)
                        else:
                            if quality == 0:
                                line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 1:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 2:
                                line1 = '|'.join(pdiag_format[1:]) % (source_1080_label, source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality == 3:
                                line1 = '|'.join(pdiag_format[2:]) % (source_720_label, source_sd_label, str(string4), source_total_label)
                            else:
                                line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

                        if debrid_status:
                            if len(info) > 6:
                                line3 = string3 % (str(len(info)))
                            elif len(info) > 0:
                                line3 = string3 % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 +'\n' + line2 +'\n' + line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        else:
                            if len(info) > 6:
                                line2 = string3 % (str(len(info)))
                            elif len(info) > 0:
                                line2 = string3 % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            progressDialog.update(max(1, percent), line1 + '\n' + line2)
                    except Exception as e:
                        log_utils.log('Exception Raised: %s' % str(e), log_utils.LOGERROR)
                else:
                    try:
                        #@todo fix for double duty mainleft and info
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() == True and x.getName() in mainsourceDict]
                        info = mainleft
                        if debrid_status:
                            if len(info) > 6:
                                line3 = 'Waiting for: %s' % (str(len(info)))
                            elif len(info) > 0:
                                line3 = 'Waiting for: %s' % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1 + '\n' +  line2 + '\n' +  line3)
                            else:
                                progressDialog.update(max(1, percent), line1 + '\n' + line3)
                        else:
                            if len(info) > 6:
                                line2 = 'Waiting for: %s' % (str(len(info)))
                            elif len(info) > 0:
                                line2 = 'Waiting for: %s' % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            progressDialog.update(max(1, percent), line1 + line2)
                    except:
                        break

                time.sleep(0.5)
            except:
                pass
        try:
            progressDialog.close()
        except:
            pass

        self.sourcesFilter()

        return self.sources

    #checked OH - 26-04-2021
    def prepareSources(self):
        try:
            control.makeFile(control.dataPath)

            self.sourceFile = control.providercacheFile

            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, UNIQUE(source, imdb_id, season, episode));")
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, UNIQUE(source, imdb_id, season, episode));")

        except:
            pass

    def getMovieSource(self, title, localtitle, aliases, year, imdb, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except:
            pass

        #Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database.
        if imdb == '0':
            try:
                dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcon.commit()
            except:
                pass
        #END

        try:
            sources = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update == False:
                sources = eval(six.ensure_str(match[4]))
                return self.sources.extend(sources)
        except:
            pass

        try:
            url = None
            dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = eval(six.ensure_str(url[4]))
        except:
            pass

        try:
            if url == None:
                url = call.movie(imdb, title, localtitle, aliases, year)
            if url == None:
                raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except:
            pass

        try:
            sources = []
            sources = call.sources(url, self.hostDict, self.hostprDict)
            if sources == None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources:
                i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, '', '', repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except:
            pass

    def getEpisodeSource(self, title, year, imdb, tmdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except:
            pass

        try:
            sources = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update == False:
                sources = eval(six.ensure_str(match[4]))
                return self.sources.extend(sources)
        except:
            pass

        try:
            url = None
            query = "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', '')
            dbcur.execute(query)
            url = dbcur.fetchone()
            url = eval(six.ensure_str(url[4]))
        except:
            pass

        try:
            if url == None:
                url = call.tvshow(imdb, tmdb, tvshowtitle, localtvshowtitle, aliases, year)
            if url == None:
                raise Exception()
            dbcur.execute(
                "DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except:
            pass

        try:
            ep_url = None
            query = "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode)
            dbcur.execute(query)
            ep_url = dbcur.fetchone()
            ep_url = eval(six.ensure_str(ep_url[4]))
        except:
            pass

        try:
            if url == None:
                raise Exception()
            if ep_url == None:
                ep_url = call.episode(url, imdb, tmdb, title, premiered, season, episode)
            if ep_url == None:
                raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(ep_url)))
            dbcon.commit()
        except:
            pass

        try:
            sources = []
            sources = call.sources(ep_url, self.hostDict, self.hostprDict)
            if sources == None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources: i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except:
            pass

    def alterSources(self, url, meta):
        try:
            if control.setting('hosts.mode') == '2':
                url += '&select=1'
            else:
                url += '&select=2'
            control.execute('RunPlugin(%s)' % url)
        except:
            pass

    #cm - fixed
    def clearSources(self):
        try:
            control.idle()

            yes = control.yesnoDialog(control.lang(32076))
            if not yes:
                return

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.providercacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DROP TABLE IF EXISTS rel_src")
            dbcur.execute("DROP TABLE IF EXISTS rel_url")
            dbcur.execute("VACUUM")
            dbcon.commit()

            control.infoDialog(control.lang(32077), sound=True, icon='INFO')
        except:
            pass

    def uniqueSourcesGen(self, sources):
        uniqueURLs = set()
        for source in sources:
            url = source.get('url')
            if isinstance(url, six.string_types):
                if 'magnet:' in url:
                    url = url[:60]
                    #url = re.findall(u'btih:(\w{40})', url)[0]
                if url not in uniqueURLs:
                    uniqueURLs.add(url)
                    yield source # Yield the unique source.
                else:
                    pass # Ignore duped sources.
            else:
                yield source # Always yield non-string url sources.

    def sourcesProcessTorrents(self, torrent_sources):#adjusted Fen code
        if len(torrent_sources) == 0: return
        for i in torrent_sources:
            if not i.get('debrid', '') in ['Real-Debrid', 'AllDebrid', 'Premiumize.me']:
                return torrent_sources

        try:
            from resources.lib.modules import debridcheck
            #control.sleep(500)
            DBCheck = debridcheck.DebridCheck()
            hashList = []
            cachedTorrents = []
            uncachedTorrents = []
            #uncheckedTorrents = []
            for i in torrent_sources:
                try:
                    r = re.findall(r'btih:(\w{40})', str(i['url']))[0]
                    if r:
                        infoHash = r.lower()
                        i['info_hash'] = infoHash
                        hashList.append(infoHash)
                except: torrent_sources.remove(i)
            if len(torrent_sources) == 0: return torrent_sources
            torrent_sources = [i for i in torrent_sources if 'info_hash' in i]
            hashList = list(set(hashList))
            control.sleep(500)
            cachedRDHashes, cachedADHashes, cachedPMHashes = DBCheck.run(hashList)

            #cached
            cachedRDSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedRDHashes) and i.get('debrid', '') == 'Real-Debrid')]
            cachedTorrents.extend(cachedRDSources)
            cachedADSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedADHashes) and i.get('debrid', '') == 'AllDebrid')]
            cachedTorrents.extend(cachedADSources)
            cachedPMSources = [dict(i.items()) for i in torrent_sources if (any(v in i.get('info_hash') for v in cachedPMHashes) and i.get('debrid', '') == 'Premiumize.me')]
            cachedTorrents.extend(cachedPMSources)
            for i in cachedTorrents: i.update({'source': 'cached torrent'})

            #uncached
            uncachedRDSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedRDHashes) and i.get('debrid', '') == 'Real-Debrid')]
            uncachedTorrents.extend(uncachedRDSources)
            uncachedADSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedADHashes) and i.get('debrid', '') == 'AllDebrid')]
            uncachedTorrents.extend(uncachedADSources)
            uncachedPMSources = [dict(i.items()) for i in torrent_sources if (not any(v in i.get('info_hash') for v in cachedPMHashes) and i.get('debrid', '') == 'Premiumize.me')]
            uncachedTorrents.extend(uncachedPMSources)
            for i in uncachedTorrents: i.update({'source': 'uncached torrent'})

            return cachedTorrents + uncachedTorrents
        except:
            failure = traceback.format_exc()
            log_utils.log('Torrent check - Exception: ' + str(failure))
            control.infoDialog('Error Processing Torrents')
            return

    def sourcesFilter(self):

        provider = control.setting('hosts.sort.provider') or 'false'
        debrid_only = control.setting('debrid.only') or 'false'
        sortthecrew = control.setting('torrent.sort.the.crew') or 'false'
        quality = int(control.setting('hosts.quality')) or 0
        captcha = control.setting('hosts.captcha') or 'true'
        show_cams = control.setting('hosts.screener') or 'true'
        remove_uncached = control.setting('remove.uncached') or 'false'

        HEVC = control.setting('HEVC')

        #random.shuffle(self.sources)
        #self.sources = [i for i in self.sources if not i['source'].lower() in self.hostblockDict]


        if provider == 'true': self.sources = sorted(self.sources, key=lambda k: k['provider'])

        hevc_list = ['hevc', 'HEVC', 'h265', 'H265', 'h.265', 'H.265', 'x265', 'X265', 'x.265', 'X.265']

        if not HEVC == 'true':
            self.sources = [i for i in self.sources if not any(value in (i['url']).lower() for value in hevc_list)]# and not any(s in i.get('name').lower for s in hevc_list)

        local = [i for i in self.sources if 'local' in i and i['local'] == True]
        for i in local: i.update({'language': self._getPrimaryLang() or 'en'})
        self.sources = [i for i in self.sources if not i in local]

        #Filter-out duplicate links
        try:
            if control.setting('remove.dups') == 'true':
                stotal = len(self.sources)
                self.sources = list(self.uniqueSourcesGen(self.sources))
                dupes = str(stotal - len(self.sources))
                control.infoDialog(control.lang(32089).format(dupes), icon='INFO')
            else:
                self.sources
        except:
            import traceback
            failure = traceback.format_exc()
            log_utils.log('DUP - Exception: ' + str(failure))
            control.infoDialog('Dupes filter failed', icon='INFO')
            self.sources
        #END

        torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
        filter = []

        for d in debrid.debrid_resolvers:
            valid_hoster = set([i['source'] for i in self.sources])
            valid_hoster = [i for i in valid_hoster if d.valid_url('', i)]
            if control.setting('check.torr.cache') == 'true':
                try:
                    for i in self.sources:
                        if 'magnet:' in i['url']: i.update({'debrid': d.name})

                    torrentSources = self.sourcesProcessTorrents([i for i in self.sources if 'magnet:' in i['url']])
                    cached = [i for i in torrentSources if i.get('source') == 'cached torrent']
                    filter += cached
                    unchecked = [i for i in torrentSources if i.get('source').lower() == 'torrent']
                    filter += unchecked
                    if remove_uncached == 'false' or len(cached) == 0:
                        uncached = [i for i in torrentSources if i.get('source') == 'uncached torrent']
                        filter += uncached
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
                except:
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                    filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]
            else:
                filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i.get('source').lower() == 'torrent']
                filter += [dict(list(i.items()) + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in i['url']]

        if debrid_only == 'false' or debrid.status() == False:
            filter += [i for i in self.sources if not i['source'].lower() in self.hostprDict and i['debridonly'] == False]

        self.sources = filter

        for i in range(len(self.sources)):
            if self.sources[i]['quality'] in ['hd', 'HD'] : self.sources[i].update({'quality': '720p'})

        filter = []
        filter += local

        if quality == 0:
            filter += [i for i in self.sources if i['quality'] in ['4k', '4K'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['4k', '4k'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['4k', '4k'] and 'debrid' not in i and 'memberonly' not in i]

        if quality <= 1:
            filter += [i for i in self.sources if i['quality'] in ['1440p','1440P'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['1440p','1440P'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['1440p','1440P'] and 'debrid' not in i and 'memberonly' not in i]


        if quality <= 2:
            filter += [i for i in self.sources if i['quality'] in ['1080p', '1080P'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['1080p', '1080P'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['1080p', '1080P'] and 'debrid' not in i and 'memberonly' not in i]


        if quality <= 3:
            filter += [i for i in self.sources if i['quality'] in ['720p', '720P'] and 'debrid' in i]
            filter += [i for i in self.sources if i['quality'] in ['720p', '720P'] and 'debrid' not in i and 'memberonly' in i]
            filter += [i for i in self.sources if i['quality'] in ['720p', '720P'] and 'debrid' not in i and 'memberonly' not in i]
            filter += [i for i in self.sources if i['quality'] in ['sd', 'SD'] and 'debrid' in i]

        if quality <= 4:
            filter += [i for i in self.sources if i['quality'] in ['sd', 'SD'] and 'debrid' in i]

        if show_cams == 'true':
            filter += [i for i in self.sources if i['quality'] in ['scr', 'cam', 'SCR', 'CAM']]

        self.sources = filter

        if not captcha == 'true':
            filter = [i for i in self.sources if i['source'].lower() in self.hostcapDict and 'debrid' not in i]
            self.sources = [i for i in self.sources if i not in filter]

        filter = [i for i in self.sources if i['source'].lower() in self.hostblockDict and 'debrid' not in i]

        multi = [i['language'] for i in self.sources]
        multi = [x for y, x in enumerate(multi) if x not in multi[:y]]
        multi = True if len(multi) > 1 else False

        if multi == True:
            self.sources = [i for i in self.sources if not i['language'] == 'en'] + [i for i in self.sources if i['language'] == 'en']

        self.sources = self.sources[:int(control.setting('returned.sources'))]
        #self.sources = self.sources[:4000] - OH 04/28/21 keeping for reference

        extra_info = control.setting('sources.extrainfo')
        prem_identify = control.setting('prem.identify') or 'blue'
        torr_identify = control.setting('torrent.identify') or 'cyan'

        prem_identify = self.getPremColor(prem_identify)
        torr_identify = self.getPremColor(torr_identify)

        for i in range(len(self.sources)):

            if extra_info == 'true':
                t = source_utils.getFileType(self.sources[i]['url'])
            else:
                t = None

            u = self.sources[i]['url']
            p = self.sources[i]['provider']
            q = self.sources[i]['quality']
            s = self.sources[i]['source']
            s = s.rsplit('.', 1)[0]
            l = self.sources[i]['language']

            try:
                f = (' | '.join(['[I]%s [/I]' % info.strip() for info in self.sources[i]['info'].split('|')]))
            except:
                f = ''

            try:
                d = self.sources[i]['debrid']
            except:
                d = self.sources[i]['debrid'] = ''

            if d.lower() == 'alldebrid':
                d = 'AD'
            if d.lower() == 'debrid-link.fr':
                d = 'DL.FR'
            if d.lower() == 'linksnappy':
                d = 'LS'
            if d.lower() == 'megadebrid':
                d = 'MD'
            if d.lower() == 'premiumize.me':
                d = 'PM'
            if d.lower() == 'real-debrid':
                d = 'RD'
            if d.lower() == 'zevera':
                d = 'ZVR'
            if not d == '':
                label = '%02d | %s | %s | %s | ' % (int(i+1), d, q, p)
            else:
                label = '%02d | %s | %s | ' % (int(i+1), q, p)

            if multi == True and not l != 'en':
                label += '%s | ' % l

            multiline_label = label

            if not t is None:
                if not f is None:
                    multiline_label += '%s \n       %s | %s' % (s, f, t)
                    label += '%s | %s | %s' % (s, f, t)
                else:
                    multiline_label += '%s \n       %s' % (s, t)
                    label += '%s | %s' % (s, t)
            else:
                if not f is None:
                    multiline_label += '%s \n       %s' % (s, f)
                    label += '%s | %s' % (s, f)
                else:
                    multiline_label += '%s' % s
                    label += '%s' % s
            label = label.replace('| 0 |', '|').replace(' | [I]0 [/I]', '')
            label = re.sub('\[I\]\s+\[/I\]', ' ', label)
            label = re.sub('\|\s+\|', '|', label)
            label = re.sub('\|(?:\s+|)$', '', label)

            if d:
                if 'torrent' in s.lower():
                    if not torr_identify == 'nocolor':
                        self.sources[i]['multiline_label'] = ('[COLOR %s]' % (torr_identify)) + multiline_label.upper() + '[/COLOR]'
                        self.sources[i]['label'] = ('[COLOR %s]' % (torr_identify)) + label.upper() + '[/COLOR]'
                    else:
                        self.sources[i]['multiline_label'] = multiline_label.upper()
                        self.sources[i]['label'] = label.upper()
                else:
                    if not prem_identify == 'nocolor':
                        self.sources[i]['multiline_label'] = ('[COLOR %s]' % (prem_identify)) + multiline_label.upper() + '[/COLOR]'
                        self.sources[i]['label'] = ('[COLOR %s]' % (prem_identify)) + label.upper() + '[/COLOR]'
                    else:
                        self.sources[i]['multiline_label'] = multiline_label.upper()
                        self.sources[i]['label'] = label.upper()
            else:
                self.sources[i]['multiline_label'] = multiline_label.upper()
                self.sources[i]['label'] = label.upper()

        try:
            if not HEVC == 'true':
                self.sources = [i for i in self.sources if not 'HEVC' or 'multiline_label' in i]

        except:
            pass

        self.sources = [i for i in self.sources if 'label' or 'multiline_label' in i['label']]

        return self.sources

    def sourcesResolve(self, item, info=False):
        try:
            self.url = None

            u = url = item['url']

            d = item['debrid']
            direct = item['direct']
            local = item.get('local', False)

            provider = item['provider']
            call = [i[1] for i in self.sourceDict if i[0] == provider][0]
            u = url = call.resolve(url)
            #if url == None or (not '://' in str(url) and not local and 'magnet:' not in str(url)): raise Exception()
            if not url or (not '://' in url and not 'magnet' in url and not local ): raise Exception()

            if not local:
                url = url[8:] if url.startswith('stack:') else url

                urls = []
                for part in url.split(' , '):
                    u = part
                    if not d == '':
                        part = debrid.resolver(part, d)
                    elif not direct == True:
                        hmf = resolveurl.HostedMediaFile(url=u, include_disabled=True, include_universal=False)
                        if hmf.valid_url() == True:
                            part = hmf.resolve()
                    urls.append(part)

                url = 'stack://' + ' , '.join(urls) if len(urls) > 1 else urls[0]

            if url == False or url == None:
                raise Exception()

            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext == 'rar':
                raise Exception()

            try:
                headers = url.rsplit('|', 1)[1]
            except:
                headers = ''
            headers = urllib.parse.quote_plus(headers).replace('%3D', '=') if ' ' in headers else headers
            headers = dict(urllib.parse.parse_qsl(headers))

            # if url.startswith('http') and '.m3u8' in url:
            #     try: result = client.request(url.split('|')[0], headers=headers, output='geturl', timeout='20')
            #     except: pass

            # elif url.startswith('http'):
            #     try: result = client.request(url.split('|')[0], headers=headers, output='chunk', timeout='20')
            #     except: pass

            self.url = url
            return url
        except:
            if info == True:
                self.errorForSources()
            return

    def sourcesDialog(self, items):
        try:

            labels = [i['label'] for i in items]

            select = control.selectDialog(labels)
            if select == -1: return 'close://'

            next = [y for x, y in enumerate(items) if x >= select]
            prev = [y for x, y in enumerate(items) if x < select][::-1]

            items = [items[select]]
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog if control.setting('progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')

            block = None

            for i in range(len(items)):
                try:
                    if items[i]['source'] == block: raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    try:
                        if progressDialog.iscanceled():
                            break
                        progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']))
                    except:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header2) + '\n' + str(items[i]['label']))

                    m = ''

                    for x in range(3600):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k:
                            break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k:
                            break
                        time.sleep(0.5)

                    for x in range(30):
                        try:
                            if control.monitor.abortRequested(): return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        if m == '': break
                        if w.is_alive() == False: break
                        time.sleep(0.5)

                    if w.is_alive() == True: block = items[i]['source']

                    if self.url == None: raise Exception()

                    self.selectedSource = items[i]['label']

                    try:
                        progressDialog.close()
                    except:
                        pass

                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')
                    return self.url
                except:
                    pass

            try:
                progressDialog.close()
            except:
                pass
            del progressDialog

        except Exception as e:
            try:
                progressDialog.close()
            except:
                pass
            del progressDialog
            log_utils.log('Error %s' % str(e), log_utils.LOGNOTICE)

    def sourcesDirect(self, items):
        filter = [i for i in items if i['source'].lower() in self.hostcapDict and not i.get('debrid')]
        items = [i for i in items if not i in filter]

        filter = [i for i in items if i['source'].lower() in self.hostblockDict]# and not i.get('debrid')]
        items = [i for i in items if not i in filter]

        items = [i for i in items if ('autoplay' in i and i['autoplay'] == True) or not 'autoplay' in i]

        if control.setting('autoplay.sd') == 'true':
            items = [i for i in items if not i['quality'] in ['4K', '1440p', '1080p', 'HD']]

        u = None

        header = control.addonInfo('name')
        header2 = header.upper()

        try:
            control.sleep(1000)

            progressDialog = control.progressDialog if control.setting(
                'progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            #progressDialog.update(0)
        except:
            pass

        for i in range(len(items)):
            try:
                if progressDialog.iscanceled():
                    break
                progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']))
            except:
                progressDialog.update(int((100 / float(len(items))) * i), str(header2) + ' ' + str(items[i]['label']))


            try:
                if control.monitor.abortRequested(): return sys.exit()

                url = self.sourcesResolve(items[i])
                if u == None: u = url
                if not url == None: break
            except:
                pass

        try: progressDialog.close()
        except:
            pass
        del progressDialog

        return u

    def errorForSources(self):
        control.infoDialog(control.lang(32401), sound=False, icon='INFO')

    def getLanguage(self):
        langDict = {
            'English': ['en'],
            'German': ['de'],
            'German+English': ['de', 'en'],
            'French': ['fr'],
            'French+English': ['fr', 'en'],
            'Portuguese': ['pt'],
            'Portuguese+English': ['pt', 'en'],
            'Polish': ['pl'],
            'Polish+English': ['pl', 'en'],
            'Korean': ['ko'],
            'Korean+English': ['ko', 'en'],
            'Russian': ['ru'],
            'Russian+English': ['ru', 'en'],
            'Spanish': ['es'],
            'Spanish+English': ['es', 'en'],
            'Greek': ['gr'],
            'Italian': ['it'],
            'Italian+English': ['it', 'en'],
            'Greek+English': ['gr', 'en']}
        name = control.setting('providers.lang')
        return langDict.get(name, ['en'])

    def getLocalTitle(self, title, imdb, tmdb, content):
        lang = self._getPrimaryLang()
        if not lang:
            return title

        if content == 'movie':
            t = trakt.getMovieTranslation(imdb, lang)
        else:
            t = trakt.getTVShowTranslation(imdb, lang)

        return t or title

    def getAliasTitles(self, imdb, localtitle, content):
        lang = self._getPrimaryLang()

        try:
            t = trakt.getMovieAliases(imdb) if content == 'movie' else trakt.getTVShowAliases(imdb)
            t = [i for i in t if i.get('country', '').lower() in [lang, '', 'us']
                 and i.get('title', '').lower() != localtitle.lower()]
            return t
        except:
            return []

    def _getPrimaryLang(self):
        langDict = {
            'English': 'en', 'German': 'de', 'German+English': 'de', 'French': 'fr', 'French+English': 'fr',
            'Portuguese': 'pt', 'Portuguese+English': 'pt', 'Polish': 'pl', 'Polish+English': 'pl', 'Korean': 'ko',
            'Korean+English': 'ko', 'Russian': 'ru', 'Russian+English': 'ru', 'Spanish': 'es', 'Spanish+English': 'es',
            'Italian': 'it', 'Italian+English': 'it', 'Greek': 'gr', 'Greek+English': 'gr'}
        name = control.setting('providers.lang')
        lang = langDict.get(name)
        return lang

    def getTitle(self, title):
        title = cleantitle.normalize(title)
        return title

    def getConstants(self):
        self.itemProperty = 'plugin.video.thecrew.container.items'

        self.metaProperty = 'plugin.video.thecrew.container.meta'

        from resources.lib.sources import sources

        self.sourceDict = sources()

        try:
            self.hostDict = resolveurl.relevant_resolvers(order_matters=True)
            self.hostDict = [i.domains for i in self.hostDict if not '*' in i.domains]
            self.hostDict = [i.lower() for i in reduce(lambda x, y: x+y, self.hostDict)]
            self.hostDict = [x for y, x in enumerate(self.hostDict) if x not in self.hostDict[:y]]
        except:
            self.hostDict = []

        self.hostprDict = [
            '1fichier.com', 'oboom.com', 'rapidgator.net', 'rg.to', 'uploaded.net', 'uploaded.to', 'uploadgig.com',
            'ul.to', 'filefactory.com', 'nitroflare.com', 'turbobit.net', 'uploadrocket.net', 'multiup.org']

        self.hostcapDict = [
            'openload.io', 'openload.co', 'oload.tv', 'oload.stream', 'oload.win', 'oload.download', 'oload.info',
            'oload.icu', 'oload.fun', 'oload.life', 'openload.pw', 'vev.io', 'vidup.me', 'vidup.tv', 'vidup.io',
            'vshare.io', 'vshare.eu', 'flashx.tv', 'flashx.to', 'flashx.sx', 'flashx.bz', 'flashx.cc', 'hugefiles.net',
            'hugefiles.cc', 'thevideo.me', 'streamin.to', 'extramovies.guru', 'extramovies.trade', 'extramovies.host' ]

        self.hosthqDict = [
            'gvideo', 'google.com', 'thevideo.me', 'raptu.com', 'filez.tv', 'uptobox.com', 'uptostream.com',
            'xvidstage.com', 'xstreamcdn.com', 'idtbox.com']

        self.hostblockDict = [
            'zippyshare.com', 'youtube.com', 'facebook.com', 'twitch.tv', 'streamango.com', 'streamcherry.com',
            'openload.io', 'openload.co', 'openload.pw', 'oload.tv', 'oload.stream', 'oload.win', 'oload.download',
            'oload.info', 'oload.icu', 'oload.fun', 'oload.life', 'oload.space', 'oload.monster', 'openload.pw',
            'rapidvideo.com', 'rapidvideo.is', 'rapidvid.to']

    def getPremColor(self, n):
        if n == '0': n = 'blue'
        elif n == '1': n = 'red'
        elif n == '2': n = 'yellow'
        elif n == '3': n = 'deeppink'
        elif n == '4': n = 'cyan'
        elif n == '5': n = 'lawngreen'
        elif n == '6': n = 'gold'
        elif n == '7': n = 'magenta'
        elif n == '8': n = 'yellowgreen'
        elif n == '9': n = 'nocolor'
        else: n == 'blue'
        return n
