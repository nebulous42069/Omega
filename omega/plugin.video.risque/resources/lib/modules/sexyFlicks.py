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

import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import os, re, sys, string, json, random, base64
import shutil
import urllib
import time
#import urllib2

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

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

art = 'special://home/addons/script.j1.artwork/lib/resources/art/'
eventsUrl = 'http://j1wizard.net/config/texts/sexyflicks.txt'
genreImage = 'special://home/addons/script.j1.artwork/lib/resources/images/genres/'

#==========================================================================================================

class Listing:

    @staticmethod
    def Genres(type):

        #errorMsg="%s" % (type)
        #xbmcgui.Dialog().ok("type", errorMsg)

        try: #Python 2
            link = OPEN_URL(eventsUrl).replace('\n','').replace('\r','').replace('\t','')
            #match = re.compile('item="(.+?)", "(.+?)", 801, "(.+?)", icon, fanart').findall(link)
        except: #Python 3
            link = OPEN_URL(eventsUrl)
            link = link.decode('ISO-8859-1')  # encoding may vary!

        match = re.compile('item="(.+?)", "(.+?)", 801, "(.+?)", "(.+?)", fanart').findall(link)
		
        #errorMsg="%s" % (match)
        #xbmcgui.Dialog().ok("match", errorMsg)

        for name, url, genre, desc in match:

            addIt=False
            if type is "All":
                icon=genreImage+"All.png"
                addIt=True

            elif "Action" in genre and type is "Action":
                icon=genreImage+"Action.png"
                addIt=True

            elif "Anime" in genre and type is "Anime":
                icon=genreImage+"Anime.png"
                addIt=True

            elif "Classic" in genre and type is "Classic":
                icon=genreImage+"Classic.png"
                addIt=True

            elif "Comedy" in genre and type is "Comedy":
                icon=genreImage+"Comedy.png"
                addIt=True

            elif "Crime" in genre and type is "Crime":
                icon=genreImage+"Crime.png"
                addIt=True

            elif "Docs" in genre and type is "Docs":
                icon=genreImage+"Documentary.png"
                addIt=True

            elif "Drama" in genre and type is "Drama":
                icon=genreImage+"Drama.png"
                addIt=True

            elif "Romance" in genre and type is "Romance":
                icon=genreImage+"Romance.png"
                addIt=True

            elif "Fantasy" in genre and type is "Fantasy":
                icon=genreImage+"Fantasy.png"
                addIt=True

            elif "Horror" in genre and type is "Horror":
                icon=genreImage+"Horror.png"
                addIt=True

            elif "Music" in genre and type is "Music":
                icon=genreImage+"Music.png"
                addIt=True

            elif "Mystery" in genre and type is "Mystery":
                icon=genreImage+"Mystery.png"
                addIt=True

            elif "Scifi" in genre and type is "Scifi":
                icon=genreImage+"Scifi.png"
                addIt=True

            elif "Sports" in genre and type is "Sports":
                icon=genreImage+"Sports.png"
                addIt=True
				
            elif "Thriller" in genre and type is "Thriller":
                icon=genreImage+"Thriller.png"
                addIt=True

            elif "Western" in genre and type is "Western":
                icon=genreImage+"Western.png"
                addIt=True

            elif "Zombie" in genre and type is "Zombie":
                icon=genreImage+"Zombie.png"
                addIt=True
		
            if addIt==True:
                name = name +" | " +desc
                addLink(name,url,801,icon,fanart)

#=====================================
   
def OPEN_URL(url):

    try:
        req = Request(url)
        req.add_header('User-Agent', USER_AGENT)
        response = urlopen(req)
        link=response.read()
        response.close()
        return link
    except:
        errorMsg="%s" % (url)
        xbmcgui.Dialog().ok("ERROR: URL ", errorMsg)
        return
	
#=====================================
