# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * Genesis Add-on
 * Copyright (C) 2015 lambda
 *
 * - Mofidied by The Crew
 *
 * @file bookmarks.py
 * @package script.module.thecrew
 *
 * @copyright 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import log_utils

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database



def get(media_type, imdb, season, episode, local=False):

    if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() == True and local == False:
        try:
            if media_type == 'episode':

                # Looking for a Episode progress
                traktInfo = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/episodes?extended=full')
                for i in traktInfo:
                    if imdb == i['show']['ids']['imdb']:
                        # Checking Episode Number
                        if int(season) == i['episode']['season'] and int(episode) == i['episode']['number']:
                            seekable = 1 < i['progress'] < 92
                            if seekable:
                                # Calculating Offset to seconds
                                offset = (float(i['progress'] / 100) * int(i['episode']['runtime']) * 60)
                            else:
                                offset = 0
            else:

                # Looking for a Movie Progress
                traktInfo = trakt.getTraktAsJson('https://api.trakt.tv/sync/playback/movies?extended=full')
                for i in traktInfo:
                    if imdb == i['movie']['ids']['imdb']:
                        seekable = 1 < i['progress'] < 92
                        if seekable:
                            # Calculating Offset to seconds
                            offset = (float(i['progress'] / 100) * int(i['movie']['runtime']) * 60)
                        else:
                            offset = 0
            return offset
        except:
            return 0
    else:
        try:
            sql_select = "SELECT * FROM bookmarks WHERE imdb = '%s'" % imdb
            if media_type == 'episode':
                sql_select += " AND season = '%s' AND episode = '%s'" % (season, episode)

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.bookmarksFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""timeInSeconds TEXT, ""type TEXT, ""imdb TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""UNIQUE(imdb, season, episode)"");")
            dbcur.execute(sql_select)
            match = dbcur.fetchone()
            dbcon.commit()
            if match:
                offset = match[0]
                return float(offset)
            else:
                return 0
        except:
            log_utils.log('Exception in bookmarks.get()')
            return 0


def reset(current_time, total_time, media_type, imdb, season='', episode=''):
    try:
        _playcount = 0
        overlay = 6
        timeInSeconds = str(current_time)
        ok = int(current_time) > 120 and (current_time / total_time) < .92
        watched = (current_time / total_time) >= .92

        sql_select = "SELECT * FROM bookmarks WHERE imdb = '%s'" % imdb
        if media_type == 'episode':
            sql_select += " AND season = '%s' AND episode = '%s'" % (season, episode)

        sql_update = "UPDATE bookmarks SET timeInSeconds = '%s' WHERE imdb = '%s'" % (timeInSeconds, imdb)
        if media_type == 'episode':
            sql_update += " AND season = '%s' AND episode = '%s'" % (season, episode)

        if media_type == 'movie':
            sql_update_watched = "UPDATE bookmarks SET timeInSeconds = '0', playcount = %s, overlay = %s WHERE imdb = '%s'" % ('%s', '%s', imdb)
        elif media_type == 'episode':
            sql_update_watched = "UPDATE bookmarks SET timeInSeconds = '0', playcount = %s, overlay = %s WHERE imdb = '%s' AND season = '%s' AND episode = '%s'" % ('%s', '%s', imdb, season, episode)

        if media_type == 'movie':
            sql_insert = "INSERT INTO bookmarks Values ('%s', '%s', '%s', '', '', '%s', '%s')" % (timeInSeconds, media_type, imdb, _playcount, overlay)
        elif media_type == 'episode':
            sql_insert = "INSERT INTO bookmarks Values ('%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (timeInSeconds, media_type, imdb, season, episode, _playcount, overlay)

        if media_type == 'movie':
            sql_insert_watched = "INSERT INTO bookmarks Values ('%s', '%s', '%s', '', '', '%s', '%s')" % (timeInSeconds, media_type, imdb, '%s', '%s')
        elif media_type == 'episode':
            sql_insert_watched = "INSERT INTO bookmarks Values ('%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (timeInSeconds, media_type, imdb, season, episode, '%s', '%s')

        control.makeFile(control.dataPath)
        dbcon = database.connect(control.bookmarksFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""timeInSeconds TEXT, ""type TEXT, ""imdb TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""UNIQUE(imdb, season, episode)"");")
        dbcur.execute(sql_select)
        match = dbcur.fetchone()
        if match:
            if ok:
                dbcur.execute(sql_update)
            elif watched:
                _playcount = match[5] + 1
                overlay = 7
                dbcur.execute(sql_update_watched % (_playcount, overlay))
        else:
            if ok:
                dbcur.execute(sql_insert)
            elif watched:
                _playcount = 1
                overlay = 7
                dbcur.execute(sql_insert_watched % (_playcount, overlay))
        dbcon.commit()
    except:
        log_utils.log('Exception in bookmarks.reset()')
        pass


def set_scrobble(current_time, total_time, _content, _imdb='', _season='', _episode=''):
    try:
        if not (current_time == 0 or total_time == 0):
            percent = float((current_time / total_time)) * 100
        else:
            percent = 0
        if int(current_time) > 120 and 2 < percent < 92:
            trakt.scrobbleMovie(_imdb, percent, action='pause') if _content == 'movie' else trakt.scrobbleEpisode(_imdb, _season, _episode, percent, action='pause')
            if control.setting('trakt.scrobble.notify') == 'true':
                control.sleep(1000)
                control.infoDialog('Trakt: Scrobble Paused')
        elif percent >= 92:
            trakt.scrobbleMovie(_imdb, percent, action='stop') if _content == 'movie' else trakt.scrobbleEpisode(_imdb, _season, _episode, percent, action='stop')
            if control.setting('trakt.scrobble.notify') == 'true':
                control.sleep(1000)
                control.infoDialog('Trakt: Scrobbled')
    except:
        log_utils.log('Exception in bookmarks.set_scrobble()')
        control.infoDialog('Scrobble Failed')


def _indicators():
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute("SELECT * FROM bookmarks WHERE overlay = 7")
    match = dbcur.fetchall()
    dbcon.commit()
    if match:
        return [i[2] for i in match]
    else:
        return []


def _get_watched(media_type, imdb, season, episode):
    sql_select = "SELECT * FROM bookmarks WHERE imdb = '%s' AND overlay = 7" % imdb
    if media_type == 'episode':
        sql_select += " AND season = '%s' AND episode = '%s'" % (season, episode)
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_select)
    match = dbcur.fetchone()
    dbcon.commit()
    if match:
        return 7
    else:
        return 6


def _update_watched(media_type, new_value, imdb, season, episode):
    sql_update = "UPDATE bookmarks SET overlay = %s WHERE imdb = '%s'" % (new_value, imdb)
    if media_type == 'episode':
        sql_update += " AND season = '%s' AND episode = '%s'" % (season, episode)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_update)
    dbcon.commit()


def _delete_record(media_type, imdb, season, episode):
    sql_delete = "DELETE FROM bookmarks WHERE imdb = '%s'" % imdb
    if media_type == 'episode':
        sql_delete += " AND season = '%s' AND episode = '%s'" % (season, episode)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_delete)
    dbcon.commit()