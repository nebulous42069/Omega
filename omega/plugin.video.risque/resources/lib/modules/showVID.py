"""

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import os
import json
import base64
import re
import xbmc
import xbmcplugin
import xbmcgui
import sys
import string
import random

try:
    # Python 3
    from urllib.request import urlopen, Request
except ImportError:
    # Python 2
    from urllib2 import urlopen, Request

try:
    # Python 3
    from html.parser import HTMLParser
except ImportError:
    # Python 2
    from HTMLParser import HTMLParser

convert_special_characters = HTMLParser()
dlg = xbmcgui.Dialog()

from resources.lib.modules.common import *

stream_failed = "Unable to get stream. Please try again later."
stream_plug = "aHR0cHM6Ly9tN2xpYi5kZXYvYXBpL2xpdmVfc3RyZWFtcy92MS9nZXRfc3RyZWFtLnBocD9pZD0="

BASE  = "plugin://plugin.video.youtube/playlist/"
cBASE = "plugin://plugin.video.youtube/channel/"
uBASE = "plugin://plugin.video.youtube/user/"

#======================================================================================================

class Common:

    @staticmethod
    def print_dlg(mode,str):
        dlg.ok(mode, str)
        return
		
    @staticmethod
    def dlg_failed(mode):
        dlg.ok(mode, stream_failed)
        exit()


#======================================================================================================

    @staticmethod
    # Play stream
    # Optional: set xbmc_player to True to use xbmc.Player() instead of xbmcplugin.setResolvedUrl()
    def play(stream, channel=None, xbmc_player=False):
        if xbmc_player:
            li = xbmcgui.ListItem(channel)
            xbmc.Player().play(stream, li, False)
        else:
            item = xbmcgui.ListItem(channel, path=stream)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

#======================================================================================================

    @staticmethod
    # Return the Channel ID from YouTube URL
    def get_youtube_channel_id(url):
        return url.split("?v=")[-1].split("/")[-1].split("?")[0].split("&")[0]

    @staticmethod
    # Return the full YouTube plugin url
    def get_playable_youtube_channel(channel_id):
        return 'plugin://plugin.video.youtube/play/c/' % channel_id +'/live'

    @staticmethod
    # Return the full YouTube plugin url
    def get_playable_youtube_url(channel_id):
        return 'plugin://plugin.video.youtube/play/?video_id=%s' % channel_id

#======================================================================================================

    @staticmethod
    # Get and Play stream
    def getVID(mode):
		
        #errorMsg="%s" % (mode)
        #xbmcgui.Dialog().ok("mode", errorMsg)

        vid_id = mode
        stream = Stream.get_video_id(vid_id)
 		
        #errorMsg="%s" % (stream)
        #xbmcgui.Dialog().ok("stream", errorMsg)
 		
        if stream is not None:		
            Common.play(stream)
        else:
            wd = None #Common.dlg_failed(mode)

#======================================================================================================

class Stream:

    @staticmethod
    def get_video_id(vid):
        try:
            channel_id = vid
            if channel_id is not "":
                return Common.get_playable_youtube_url(channel_id)
            else:
                return None
        except StandardError:
            return None

#=======================================================================================================
