# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file playcount.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


from resources.lib.modules import bookmarks
from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import log_utils


def getMovieIndicators(refresh=False):
    try:
        if trakt.getTraktIndicatorsInfo() == True: raise Exception()
        indicators = bookmarks._indicators()
        return indicators
    except:
        pass
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if refresh == False: timeout = 720
        elif trakt.getWatchedActivity() < trakt.timeoutsyncMovies(): timeout = 720
        else: timeout = 0
        indicators = trakt.cachesyncMovies(timeout=timeout)
        return indicators
    except:
        pass


def getTVShowIndicators(refresh=False):
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if refresh == False: timeout = 720
        elif trakt.getWatchedActivity() < trakt.timeoutsyncTVShows(): timeout = 720
        else: timeout = 0
        indicators = trakt.cachesyncTVShows(timeout=timeout)
        return indicators
    except:
        pass


def getSeasonIndicators(imdb):
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        indicators = trakt.syncSeason(imdb)
        return indicators
    except:
        pass


def getMovieOverlay(indicators, imdb):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            overlay = bookmarks._get_watched('movie', imdb, '', '')
            return str(overlay)
        else:
            playcount = [i for i in indicators if i == imdb]
            overlay = 7 if len(playcount) > 0 else 6
            return str(overlay)
    except:
        return '6'

def getTVShowOverlay(indicators, tmdb):
    try:
        playcount = [i[0] for i in indicators if i[0] == tmdb and len(i[2]) >= int(i[1])]
        playcount = 7 if len(playcount) > 0 else 6
        return str(playcount)
    except:
        return '6'

def getSeasonOverlay(indicators, imdb, season):
    try:
        playcount = [i for i in indicators if int(season) == int(i)]
        playcount = 7 if len(playcount) > 0 else 6
        return str(playcount)
    except:
        return '6'


def getEpisodeOverlay(indicators, imdb, tmdb, season, episode):
    try:
        if trakt.getTraktIndicatorsInfo() == False:
            overlay = bookmarks._get_watched('episode', imdb, season, episode)
            return str(overlay)
        else:
            playcount = [i[2] for i in indicators if i[0] == tmdb]
            playcount = playcount[0] if len(playcount) > 0 else []
            playcount = [i for i in playcount if int(season) == int(i[0]) and int(episode) == int(i[1])]
            overlay = 7 if len(playcount) > 0 else 6
            return str(overlay)
    except:
        return '6'


def markMovieDuringPlayback(imdb, watched):
    try:
        if trakt.getTraktIndicatorsInfo() == False: 
            raise Exception()

        if int(watched) == 7: 
            trakt.markMovieAsWatched(imdb)
        else: 
            trakt.markMovieAsNotWatched(imdb)
        trakt.cachesyncMovies()

        if trakt.getTraktAddonMovieInfo() is True:
            trakt.markMovieAsNotWatched(imdb)
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'movie', imdb, '', '')
    except:
        pass


def markEpisodeDuringPlayback(imdb, tmdb, season, episode, watched):
    try:
        if trakt.getTraktIndicatorsInfo() is False: raise Exception()

        if int(watched) == 7: trakt.markEpisodeAsWatched(imdb, season, episode)
        else: trakt.markEpisodeAsNotWatched(imdb, season, episode)
        trakt.cachesyncTVShows()

        if trakt.getTraktAddonEpisodeInfo() is True:
            trakt.markEpisodeAsNotWatched(imdb, season, episode)
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'episode', imdb, season, episode)
    except:
        pass

#TC 2/01/19 started
def movies(imdb, watched):
    try:
        if trakt.getTraktIndicatorsInfo() == False: 
            raise Exception()
        if int(watched) == 7: 
            trakt.markMovieAsWatched(imdb)
        else: 
            trakt.markMovieAsNotWatched(imdb)
        trakt.cachesyncMovies()
        control.refresh()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'movie', imdb, '', '')
        else:
            bookmarks._delete_record('movie', imdb, '', '')
        if trakt.getTraktIndicatorsInfo() is False: 
            control.refresh()
    except:
        pass


def episodes(imdb, tmdb, season, episode, watched):
    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()
        if int(watched) == 7: trakt.markEpisodeAsWatched(imdb, season, episode)
        else: trakt.markEpisodeAsNotWatched(imdb, season, episode)
        trakt.cachesyncTVShows()
        control.refresh()
    except:
        pass

    try:
        if int(watched) == 7:
            bookmarks.reset(1, 1, 'episode', imdb, season, episode)
        else:
            bookmarks._delete_record('episode', imdb, season, episode)
        if trakt.getTraktIndicatorsInfo() is False: control.refresh()
    except:
        pass


def tvshows(tvshowtitle, imdb, tmdb, season, watched):
    control.busy()
    try:
        import sys,xbmc

        if not trakt.getTraktIndicatorsInfo() == False: raise Exception()

        from resources.lib.indexers import episodes

        name = control.addonInfo('name')

        dialog = control.progressDialogBG
        dialog.create(str(name), str(tvshowtitle))
        dialog.update(0, str(name), str(tvshowtitle))

        items = []
        if season:
            items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=season, idx=False)
            items = [i for i in items if int('%01d' % int(season)) == int('%01d' % int(i['season']))]
            items = [{'label': '%s S%02dE%02d' % (tvshowtitle, int(i['season']), int(i['episode'])), 'season': int('%01d' % int(i['season'])), 'episode': int('%01d' % int(i['episode'])), 'unaired': i['unaired']} for i in items]

            for i in range(len(items)):
                if control.monitor.abortRequested(): return sys.exit()

                dialog.update(int((100 / float(len(items))) * i), str(name), str(items[i]['label']))

                _season, _episode, unaired = items[i]['season'], items[i]['episode'], items[i]['unaired']
                if int(watched) == 7:
                    if not unaired == 'true':
                        bookmarks.reset(1, 1, 'episode', imdb, _season, _episode)
                    else: pass
                else:
                    bookmarks._delete_record('episode', imdb, _season, _episode)

        else:
            seasons = episodes.seasons().get(tvshowtitle, '0', imdb, tmdb, meta=None, idx=False)
            seasons = [i['season'] for i in seasons]

            for s in seasons:
                items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=s, idx=False)
                items = [{'label': '%s S%02dE%02d' % (tvshowtitle, int(i['season']), int(i['episode'])), 'season': int('%01d' % int(i['season'])), 'episode': int('%01d' % int(i['episode'])), 'unaired': i['unaired']} for i in items]

                for i in range(len(items)):
                    if control.monitor.abortRequested(): return sys.exit()

                    dialog.update(int((100 / float(len(items))) * i), str(name), str(items[i]['label']))

                    _season, _episode, unaired = items[i]['season'], items[i]['episode'], items[i]['unaired']
                    if int(watched) == 7:
                        if not unaired == 'true':
                            bookmarks.reset(1, 1, 'episode', imdb, _season, _episode)
                        else: pass
                    else:
                        bookmarks._delete_record('episode', imdb, _season, _episode)

        try: dialog.close()
        except: pass
    except:
        log_utils.log('Exception in playcount trakt_local_shows')
        try: dialog.close()
        except: pass


    try:
        if trakt.getTraktIndicatorsInfo() == False: raise Exception()

        if season:
            from resources.lib.indexers import episodes
            items = episodes.episodes().get(tvshowtitle, '0', imdb, tmdb, meta=None, season=season, idx=False)
            items = [(int(i['season']), int(i['episode'])) for i in items]
            items = [i[1] for i in items if int('%01d' % int(season)) == int('%01d' % i[0])]
            for i in items:
                if int(watched) == 7: trakt.markEpisodeAsWatched(imdb, season, i)
                else: trakt.markEpisodeAsNotWatched(imdb, season, i)
        else:
            if int(watched) == 7: trakt.markTVShowAsWatched(imdb)
            else: trakt.markTVShowAsNotWatched(imdb)
        trakt.cachesyncTVShows()
    except:
        log_utils.log('Exception in playcount trakt_shows')
        pass

    control.refresh()
    control.idle()


