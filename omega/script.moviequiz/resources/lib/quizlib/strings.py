#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import xbmcaddon

ADDON = xbmcaddon.Addon()

# the strings in this section are defined by kodi.
# see https://github.com/xbmc/xbmc/blob/master/addons/resource.language.en_gb/resources/strings.po
# K_SETTINGS = 5
# K_DOWNLOAD = 33003

# Question strings - movie
Q_WHAT_MOVIE_IS_THIS = 30400
Q_WHAT_MOVIE_IS_ACTOR_NOT_IN = 30401
Q_WHAT_YEAR_WAS_MOVIE_RELEASED = 30402
Q_WHAT_TAGLINE_BELONGS_TO_MOVIE = 30403
Q_WHO_DIRECTED_THIS_MOVIE = 30404
Q_WHAT_STUDIO_RELEASED_MOVIE = 30405
Q_WHAT_ACTOR_IS_THIS = 30406
Q_WHO_PLAYS_ROLE_IN_MOVIE = 30407
Q_WHO_VOICES_ROLE_IN_MOVIE = 30408
Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM = 30409
Q_WHAT_MOVIE_IS_THE_NEWEST = 30410
Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY = 30411
Q_WHAT_ACTOR_IS_IN_THESE_MOVIES = 30412
Q_WHAT_ACTOR_IS_IN_MOVIE_BESIDES_OTHER_ACTOR = 30413
Q_WHAT_MOVIE_HAS_THE_LONGEST_RUNTIME = 30414

# Question strings - TV show
Q_WHAT_TVSHOW_IS_THIS = 30450
Q_WHAT_SEASON_IS_THIS = 30451
Q_WHAT_EPISODE_IS_THIS = 30452
Q_WHEN_WAS_TVSHOW_FIRST_AIRED = 30454
Q_WHO_PLAYS_ROLE_IN_TVSHOW = 30455
Q_WHO_VOICES_ROLE_IN_TVSHOW = 30456
Q_WHAT_TVSHOW_IS_THIS_QUOTE_FROM = 30457
Q_WHAT_TVSHOW_IS_THIS_THEME_FROM = 30458
Q_SPECIALS = 30005
Q_SEASON_NO = 30006

# Question strings - Music
Q_WHAT_SONG_IS_THIS = 30475
Q_WHO_MADE_THE_SONG = 30476
Q_WHO_MADE_THE_ALBUM = 30477

# Menu strings
M_DOWNLOAD_IMDB = 30519
M_DOWNLOAD_IMDB_INFO = 30522
M_SETTINGS = 30806
M_EXIT = 30103
M_PLAY_MUSIC_QUIZ = 30106
M_PLAY_MOVIE_QUIZ = 30100
M_PLAY_TVSHOW_QUIZ = 30101
M_ABOUT = 30801
M_ABOUT_TEXT_BODY = 30802

# Settings strings
S_DOWNLOADING_IMDB_DATA = 30520
S_RETRIEVED_X_OF_Y_MB = 30521
S_FILE_X_OF_Y = 30525
S_DOWNLOAD_COMPLETE = 30526

# Error strings
E_WARNING = 30050
E_ALL_MOVIE_QUESTIONS_DISABLED = 30051
E_ALL_TVSHOW_QUESTIONS_DISABLED = 30052
E_QUIZ_TYPE_NOT_AVAILABLE = 30053
E_REQUIREMENTS_MISSING = 30054
E_HAS_NO_CONTENT = 30055
E_ONLY_WATCHED = 30061
E_MOVIE_RATING_LIMIT = 30064
E_TVSHOW_RATING_LIMIT = 30067

SETT_ONLY_WATCHED_MOVIES = 'only.watched.movies'
SETT_MOVIE_RATING_LIMIT_ENABLED = 'movie.rating.limit.enabled'
SETT_TVSHOW_RATING_LIMIT_ENABLED = 'tvshow.rating.limit.enabled'


def strings(*args):
    return ' '.join([ADDON.getLocalizedString(arg) for arg in args])