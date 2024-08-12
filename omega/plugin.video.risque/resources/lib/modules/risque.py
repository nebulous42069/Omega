# -*- coding: utf-8 -*-

# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)

import urllib, sys, re, os, unicodedata
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

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

from resources.lib.modules.common import *

import urllib

params = get_params()
mode = None

addon_id     = xbmcaddon.Addon().getAddonInfo('id') 

selfAddon = xbmcaddon.Addon(id=addon_id)
plugin_handle = int(sys.argv[1])
dialog = xbmcgui.Dialog()
mysettings = xbmcaddon.Addon(id = 'plugin.video.risque')
profile = mysettings.getAddonInfo('profile')
home = mysettings.getAddonInfo('path')

try:
    datapath= xbmcvfs.translatePath(selfAddon.getAddonInfo('profile'))
except:
    datapath= xbmc.translatePath(selfAddon.getAddonInfo('profile'))

try:
    fanart = xbmcvfs.translatePath(os.path.join(home, 'fanart.jpg'))
    icon = xbmcvfs.translatePath(os.path.join(home, 'icon.png'))
    mediapath = xbmcvfs.translatePath(os.path.join('special://home/addons/' + addon_id + '/resources/media/'))
except:
    fanart = xbmc.translatePath(os.path.join(home, 'fanart.jpg'))
    icon = xbmc.translatePath(os.path.join(home, 'icon.png'))
    mediapath = xbmc.translatePath(os.path.join('special://home/addons/' + addon_id + '/resources/media/'))

BASE  = "plugin://plugin.video.youtube/playlist/"
cBASE = "plugin://plugin.video.youtube/channel/"
uBASE = "plugin://plugin.video.youtube/user/"

YOUTUBE_CHANNEL_ID_10001 = "PLgjeA307DhuJFwKSWP0ZAr3p_UBI4BRUw" #Thuggish Shows
YOUTUBE_CHANNEL_ID_10002 = "PLxTol2ZITPv5_X1X7oFT4aHMQldkGSd9D" #Sexy Dance And More
YOUTUBE_CHANNEL_ID_10003 = "AmitBarArt"                         #Amit Bar Art Channel
YOUTUBE_CHANNEL_ID_10004 = "UCMzVdMz4gPfLDn6mrRJPVaQ"           #Body Art Production
YOUTUBE_CHANNEL_ID_10005 = "UCSHGoHQk6K2fsiMrk4ryeBg"           #Sexy Car Wash Channel
YOUTUBE_CHANNEL_ID_10006 = "NakedWave"                          #Naked Wave Channel
YOUTUBE_CHANNEL_ID_10007 = "PL6EL9u-B9FiDTG5HkQ92UYw-oiuFT26Gp" #The Ladies Carwash
YOUTUBE_CHANNEL_ID_10008 = "PLE81L8F7lfJ2vcVbL5vKpHwy2_-1xcoRl" #More Sexy Carwash
YOUTUBE_CHANNEL_ID_10009 = "UCqa56up6zdYrGLSl-96MDEQ"           #Ireila Bodypainting
YOUTUBE_CHANNEL_ID_10010 = "PL_MRwlVErLGHEODU3kPakQSYrlxrscD_o" #Sexy Bottoms
YOUTUBE_CHANNEL_ID_10011 = "" #
YOUTUBE_CHANNEL_ID_10012 = "" #
YOUTUBE_CHANNEL_ID_10013 = "" #
YOUTUBE_CHANNEL_ID_10014 = "" #
YOUTUBE_CHANNEL_ID_10015 = "" #
YOUTUBE_CHANNEL_ID_10016 = "" #
YOUTUBE_CHANNEL_ID_10017 = "" #
YOUTUBE_CHANNEL_ID_10018 = "" #
YOUTUBE_CHANNEL_ID_10019 = "" #
YOUTUBE_CHANNEL_ID_10020 = "" #
YOUTUBE_CHANNEL_ID_10021 = "" #
YOUTUBE_CHANNEL_ID_10022 = "" #
YOUTUBE_CHANNEL_ID_10023 = "" #
YOUTUBE_CHANNEL_ID_10024 = "" #
YOUTUBE_CHANNEL_ID_10025 = "PLmdPopYzmrplKAA8O7j27pBe_-okGrafQ" #WWE Bra And Panties Matches
YOUTUBE_CHANNEL_ID_10026 = "" #
YOUTUBE_CHANNEL_ID_10027 = "PLmDwKqdmioTSpZWw6_dPNDgCtpmg-fySX" #Sexy Aerobics And Fitness
YOUTUBE_CHANNEL_ID_10028 = "PL3kYp2XGtaR6qTlKatLrZfbRFTWqT-51A" #Sexy Sports: Ronda Rousey
YOUTUBE_CHANNEL_ID_10029 = "UC44miMvx10uHMswSGuGP6gA"           #New Car And Hot Girl Channel
YOUTUBE_CHANNEL_ID_10030 = "UCUIAMPkjmqFGYp7m74WNvFA"           #Hot Bike Show Channel
YOUTUBE_CHANNEL_ID_10031 = "UCNycQEfdnPAqijCixW0e8sA"           #Girls N Cars Channel
YOUTUBE_CHANNEL_ID_10032 = "UCK-wZzCTrbCCLi_U83vvPEQ"           #Sports Girls Channel
YOUTUBE_CHANNEL_ID_10033 = "UCHQUWveEpeO1KTkwbDn6jNA"           #Beach Volleyball Channel
YOUTUBE_CHANNEL_ID_10034 = "Csabtube"                           #Amazing Sports Video
YOUTUBE_CHANNEL_ID_10035 = "UCyD8TDCpkfvm0IjAh0_t6fg"           #Hot Games Channel
YOUTUBE_CHANNEL_ID_10036 = "UCDDGTNqFtKVrKEO0pM9S2UQ"           #Hot Bikes N Hot Women
YOUTUBE_CHANNEL_ID_10037 = "UCwJi5YBg3nVecmokqEBECcw"           #WOW Superheroes Channel
YOUTUBE_CHANNEL_ID_10038 = "UCfG7Vi9kskiyCXjQk_US3cQ"           #Girls Grappling Channel
YOUTUBE_CHANNEL_ID_10039 = "" #
YOUTUBE_CHANNEL_ID_10040 = "" #
YOUTUBE_CHANNEL_ID_10041 = "" #
YOUTUBE_CHANNEL_ID_10042 = "" #
YOUTUBE_CHANNEL_ID_10043 = "" #
YOUTUBE_CHANNEL_ID_10044 = "" #
YOUTUBE_CHANNEL_ID_10045 = "" #
YOUTUBE_CHANNEL_ID_10046 = "" #
YOUTUBE_CHANNEL_ID_10047 = "" #
YOUTUBE_CHANNEL_ID_10048 = "" #
YOUTUBE_CHANNEL_ID_10049 = "" #
YOUTUBE_CHANNEL_ID_10050 = "PL6B0B39F8060E1C71"                 #Cooking Made Sexy By Tifa
YOUTUBE_CHANNEL_ID_10051 = "PLGMYlpGoCFGdbFk887YaybSaNuDSEXN9n" #Cooking And Cleaning
YOUTUBE_CHANNEL_ID_10052 = "PLrPhzEPftqQwWF0L4YyyQJ0OGOVPQqzNi" #Sexy: Home Bodies
YOUTUBE_CHANNEL_ID_10053 = "PL1bmxG4QaFq0gW2xgfzh-nMyGwKxNO6Ys" #Sexy Chef Wendy
YOUTUBE_CHANNEL_ID_10054 = "PLnEEn4Wzpcp5PjSRxLljWSpa6K9KwUDBv" #Lilys Sizzlin Cooking Show
YOUTUBE_CHANNEL_ID_10055 = "" #
YOUTUBE_CHANNEL_ID_10056 = "NXfurni"                            #Naked News: Bakers
YOUTUBE_CHANNEL_ID_10057 = "" #
YOUTUBE_CHANNEL_ID_10058 = "" #
YOUTUBE_CHANNEL_ID_10059 = "" #
YOUTUBE_CHANNEL_ID_10060 = "" #
YOUTUBE_CHANNEL_ID_10061 = "" #
YOUTUBE_CHANNEL_ID_10062 = "" #
YOUTUBE_CHANNEL_ID_10063 = "" #
YOUTUBE_CHANNEL_ID_10064 = "" #
YOUTUBE_CHANNEL_ID_10065 = "" #
YOUTUBE_CHANNEL_ID_10066 = "" #
YOUTUBE_CHANNEL_ID_10067 = "" #
YOUTUBE_CHANNEL_ID_10068 = "" #
YOUTUBE_CHANNEL_ID_10069 = "" #
YOUTUBE_CHANNEL_ID_10070 = "" #
YOUTUBE_CHANNEL_ID_10071 = "" #
YOUTUBE_CHANNEL_ID_10072 = "" #
YOUTUBE_CHANNEL_ID_10073 = "" #
YOUTUBE_CHANNEL_ID_10074 = "" #
YOUTUBE_CHANNEL_ID_10075 = "PLxTol2ZITPv5J-VbzCykvLpmw15Jwaqkc" #Hot Sexy Girls
YOUTUBE_CHANNEL_ID_10076 = "PLGcNl6C7tWdQYKhWcav5pOk7zmQyg8g4x" #Victoria Secret Fashion Show
YOUTUBE_CHANNEL_ID_10077 = "PL7D50410F3E2108A9"                 #Fashion Week - Bikini Models
YOUTUBE_CHANNEL_ID_10078 = "PL4gRI2oLPByg9V3Czt60mRHVV4hQgFDNm" #Sexy Tribute
YOUTUBE_CHANNEL_ID_10079 = "PL0Spsv9ZrGnUX6YSO7hSnGt8Nm6yCmhnu" #Sexy Swimwear
YOUTUBE_CHANNEL_ID_10080 = "" #
YOUTUBE_CHANNEL_ID_10081 = "AmitBarArt"                         #AmitBar Art Channel
YOUTUBE_CHANNEL_ID_10082 = "UC5Ls7NQn-RWTuTqbnB3ZY8Q"           #Love Birds Channel
YOUTUBE_CHANNEL_ID_10083 = "TopModelSexy"                       #Top Model Sexy Channel
YOUTUBE_CHANNEL_ID_10084 = "UCKCRuuNG6IMPaNDrzG5ZgsA"           #Hot Women Channel
YOUTUBE_CHANNEL_ID_10085 = "" #
YOUTUBE_CHANNEL_ID_10086 = "" #
YOUTUBE_CHANNEL_ID_10087 = "" #
YOUTUBE_CHANNEL_ID_10088 = "" #
YOUTUBE_CHANNEL_ID_10089 = "" #
YOUTUBE_CHANNEL_ID_10090 = "" #
YOUTUBE_CHANNEL_ID_10091 = "" #
YOUTUBE_CHANNEL_ID_10092 = "" #
YOUTUBE_CHANNEL_ID_10093 = "" #
YOUTUBE_CHANNEL_ID_10094 = "" #
YOUTUBE_CHANNEL_ID_10095 = "" #
YOUTUBE_CHANNEL_ID_10096 = "" #
YOUTUBE_CHANNEL_ID_10097 = "" #
YOUTUBE_CHANNEL_ID_10098 = "" #
YOUTUBE_CHANNEL_ID_10099 = "" #
YOUTUBE_CHANNEL_ID_10100 = "SIswimsuit"                        #Sports Illustrated Swimsuit
YOUTUBE_CHANNEL_ID_10101 = "VICTORIASSECRET"                   #Victoria s Secret Channel
YOUTUBE_CHANNEL_ID_10102 = "playboytelevision"                 #Playboy Television Channel
YOUTUBE_CHANNEL_ID_10103 = "MODELSOCIETYchannel"               #Model Society Channel
YOUTUBE_CHANNEL_ID_10104 = "UCTCWk056cyWlREQxZTzvsug"          #Naked News Channel
YOUTUBE_CHANNEL_ID_10105 = "UCwm7TAVCvvw4yYuAADYo0KQ"          #World Naked Bike Ride
YOUTUBE_CHANNEL_ID_10106 = "AfterEdenLingerie"                 #After Eden Lingerie
YOUTUBE_CHANNEL_ID_10107 = "UCRCXPe_cPl3JbqOaAkUsqrQ"          #Swimwear Hot Collection
YOUTUBE_CHANNEL_ID_10108 = "" #
YOUTUBE_CHANNEL_ID_10109 = "" #
YOUTUBE_CHANNEL_ID_10110 = "" #
YOUTUBE_CHANNEL_ID_10111 = "" #
YOUTUBE_CHANNEL_ID_10112 = "" #
YOUTUBE_CHANNEL_ID_10113 = "" #
YOUTUBE_CHANNEL_ID_10114 = "" #
YOUTUBE_CHANNEL_ID_10115 = "" #
YOUTUBE_CHANNEL_ID_10116 = "" #
YOUTUBE_CHANNEL_ID_10117 = "" #
YOUTUBE_CHANNEL_ID_10118 = "" #
YOUTUBE_CHANNEL_ID_10119 = "" #
YOUTUBE_CHANNEL_ID_10120 = "" #
YOUTUBE_CHANNEL_ID_10121 = "" #
YOUTUBE_CHANNEL_ID_10122 = "" #
YOUTUBE_CHANNEL_ID_10123 = "" #
YOUTUBE_CHANNEL_ID_10124 = "" #
YOUTUBE_CHANNEL_ID_10125 = "3VFitness"                         #Sexy 3VFitness Channel
YOUTUBE_CHANNEL_ID_10126 = "UChaorWQ-1G9FKraHoZ50PWQ"          #Story Female Fitness
YOUTUBE_CHANNEL_ID_10127 = "UCWw8px_taY9kVnttNrhZDfA"          #Sexy Girls Gym Channel
YOUTUBE_CHANNEL_ID_10128 = "myfitgirls"                        #My Fitness Girls Channel
YOUTUBE_CHANNEL_ID_10129 = "UC4orc3EowlmaRDCB59I9KBg"          #Hot Girls Motivation
YOUTUBE_CHANNEL_ID_10130 = "UCEh_nwzVQwP9xM5L_rvnRnA"          #Sexy Fitness Channel
YOUTUBE_CHANNEL_ID_10131 = "UC7DgqOg2haEIwG9RmI3JX8w"          #Hot Fitness Ladies
YOUTUBE_CHANNEL_ID_10132 = "UCJ8ZvW4zwYStmPZxcw_kOfg"          #Sexy Female Muscle
YOUTUBE_CHANNEL_ID_10133 = "UCmO5XUu_V2cDj1vWicp1TMw"          #The Fit Gals Channel
YOUTUBE_CHANNEL_ID_10134 = "UCFuWcYGKNVjnc6g0rsMEbmA"          #Sexy Girls Fitness
YOUTUBE_CHANNEL_ID_10135 = "UCiSj1T1V4LU17IlhFcHHeWQ"          #Hot Flex Yoga Channel
YOUTUBE_CHANNEL_ID_10136 = "" #
YOUTUBE_CHANNEL_ID_10137 = "" #
YOUTUBE_CHANNEL_ID_10138 = "" #
YOUTUBE_CHANNEL_ID_10139 = "" #
YOUTUBE_CHANNEL_ID_10140 = "" #
YOUTUBE_CHANNEL_ID_10141 = "" #
YOUTUBE_CHANNEL_ID_10142 = "" #
YOUTUBE_CHANNEL_ID_10143 = "" #
YOUTUBE_CHANNEL_ID_10144 = "" #
YOUTUBE_CHANNEL_ID_10145 = "" #
YOUTUBE_CHANNEL_ID_10146 = "" #
YOUTUBE_CHANNEL_ID_10147 = "" #
YOUTUBE_CHANNEL_ID_10148 = "" #
YOUTUBE_CHANNEL_ID_10149 = "" #
YOUTUBE_CHANNEL_ID_10150 = "PL9QSd_OnYraaqjk8ce_Q4Zrkv4ehH2sxF" #Sexy Tattoos Playlist
YOUTUBE_CHANNEL_ID_10151 = "UC93-snsJuHVu06j6sJ_TCUA"           #18+ Sexy Tattoo Channel
YOUTUBE_CHANNEL_ID_10152 = "777Mamay"                           #Sexy Intim Tattoo Channel
YOUTUBE_CHANNEL_ID_10153 = "UCeN88Yj5GmpADHghfNNAjjg"           #Sexy Tattoo Channel
YOUTUBE_CHANNEL_ID_10154 = "UCbpeAWEqq9RXnXVQa3J_sJA"           #Sexy Art Tattoo Channel
YOUTUBE_CHANNEL_ID_10155 = "UC-1Lt-BD1HYnx-5jMbuBy8g"           #Sexy Body Art Channel
YOUTUBE_CHANNEL_ID_10156 = "UCEjrL8kRHJvVdwtsmsP7WEQ"           #Body Paint Festival Channel
YOUTUBE_CHANNEL_ID_10157 = "UChB8bzb5-G_YdYpJE_DPK4w"           #Body Art Studio Channel
YOUTUBE_CHANNEL_ID_10158 = "UC3sZyiv4rBYgGRPlcHwvfsw"           #Body Art Channel
YOUTUBE_CHANNEL_ID_10159 = "UCwKElXTmNU0SoBAYJKp6dvQ"           #See Art Works Channel
YOUTUBE_CHANNEL_ID_10160 = "" #
YOUTUBE_CHANNEL_ID_10161 = "" #
YOUTUBE_CHANNEL_ID_10162 = "" #
YOUTUBE_CHANNEL_ID_10163 = "" #
YOUTUBE_CHANNEL_ID_10164 = "" #
YOUTUBE_CHANNEL_ID_10165 = "" #
YOUTUBE_CHANNEL_ID_10166 = "" #
YOUTUBE_CHANNEL_ID_10167 = "" #
YOUTUBE_CHANNEL_ID_10168 = "" #
YOUTUBE_CHANNEL_ID_10169 = "UCT3Hru7fNWcoxTo15nKUTpg"           #Bikini Risque Channel
YOUTUBE_CHANNEL_ID_10170 = "HotBikiniAuditions"                 #Hot Bikini Auditions
YOUTUBE_CHANNEL_ID_10171 = "worldswimsuit"                      #World Swimsuit Channel
YOUTUBE_CHANNEL_ID_10178 = "UCkk1So06xPJUYmBczOcpw_Q"           #Sexy Girls On The Beach
YOUTUBE_CHANNEL_ID_10179 = "bikiniparadiso"                     #Bikini Paradiso Channel
YOUTUBE_CHANNEL_ID_10180 = "UCpM50Bh47knjL3bx1I7Z0vQ"           #Sexy Girls Bikini Channel
YOUTUBE_CHANNEL_ID_10181 = "UC1j6HmuYFgDaYboBupZ9q1w"           #Bikini Beach Party Channel
YOUTUBE_CHANNEL_ID_10182 = "BikiniCelebrity"                    #Bikini Celebrity Channel
YOUTUBE_CHANNEL_ID_10183 = "mrbikinicontest"                    #Mr. Bikini Contest Channel
YOUTUBE_CHANNEL_ID_10184 = "UCXhLWtty_RqdLa--rborKbA"           #Sexy Bikini Models
YOUTUBE_CHANNEL_ID_10185 = "" #
YOUTUBE_CHANNEL_ID_10186 = "" #
YOUTUBE_CHANNEL_ID_10187 = "" #

YOUTUBE_CHANNEL_ID_10210 = "" #
YOUTUBE_CHANNEL_ID_10211 = "" #
YOUTUBE_CHANNEL_ID_10212 = "" #
YOUTUBE_CHANNEL_ID_10213 = "" #
YOUTUBE_CHANNEL_ID_10214 = "" #
YOUTUBE_CHANNEL_ID_10215 = "" #
YOUTUBE_CHANNEL_ID_10216 = "" #
YOUTUBE_CHANNEL_ID_10217 = "" #
YOUTUBE_CHANNEL_ID_10218 = "" #
YOUTUBE_CHANNEL_ID_10219 = "" #

YOUTUBE_CHANNEL_ID_10258 = "" #
YOUTUBE_CHANNEL_ID_10259 = "" #
YOUTUBE_CHANNEL_ID_10260 = "" #
YOUTUBE_CHANNEL_ID_10261 = "" #
YOUTUBE_CHANNEL_ID_10262 = "" #
YOUTUBE_CHANNEL_ID_10263 = "" #
YOUTUBE_CHANNEL_ID_10264 = "" #
YOUTUBE_CHANNEL_ID_10265 = "" #
YOUTUBE_CHANNEL_ID_10266 = "" #
YOUTUBE_CHANNEL_ID_10267 = "" #
YOUTUBE_CHANNEL_ID_10268 = "" #
YOUTUBE_CHANNEL_ID_10269 = "" #
YOUTUBE_CHANNEL_ID_10270 = "" #
YOUTUBE_CHANNEL_ID_10271 = "" #
YOUTUBE_CHANNEL_ID_10272 = "" #
YOUTUBE_CHANNEL_ID_10273 = "" #
YOUTUBE_CHANNEL_ID_10274 = "" #
YOUTUBE_CHANNEL_ID_10275 = "UCgJQ0n1Fj1Rim56ttikyHiA"           #Sexy Girls Dancing Channel
YOUTUBE_CHANNEL_ID_10276 = "UCKJWMH13Zf4tZfftSS4R66Q"           #Mast Manoranjan Channel
YOUTUBE_CHANNEL_ID_10277 = "UCDQfQsif8HgzWHxnAGc5OSg"           #The Hot Dance Channel
YOUTUBE_CHANNEL_ID_10278 = "TheJahful"                          #Female Dance Fitness
YOUTUBE_CHANNEL_ID_10279 = "Madikins411"                        #Maddie sparkle Channel
YOUTUBE_CHANNEL_ID_10280 = "aryannapoledancer"                  #Aryanna The Pole Dancer
YOUTUBE_CHANNEL_ID_10281 = "UCXQAfj66Igqy07nLNHjardQ"           #Dance Filthy USA Channel
YOUTUBE_CHANNEL_ID_10282 = "aletheaaustin"                      #Alethea Austin Channel
YOUTUBE_CHANNEL_ID_10283 = "UCV5e5i0RsFkB_o3N_9w8q9g"           #Twerking Pro XI Channel
YOUTUBE_CHANNEL_ID_10284 = "UCHizJ5AKbXnUgkCAGj_Up-g"           #Twerk With Tinze Channel
YOUTUBE_CHANNEL_ID_10285 = "UCv2p75JI8Tgcw4C-4pvr-CA"           #Empress Cece Channel
YOUTUBE_CHANNEL_ID_10286 = "andreyrepe"                         #Typical Twerk Channel
YOUTUBE_CHANNEL_ID_10287 = "TwerkTrap"                          #The Twerk Trap Channel
YOUTUBE_CHANNEL_ID_10288 = "" #
YOUTUBE_CHANNEL_ID_10289 = "" #
YOUTUBE_CHANNEL_ID_10290 = "" #
YOUTUBE_CHANNEL_ID_10291 = "" #
YOUTUBE_CHANNEL_ID_10292 = "" #
YOUTUBE_CHANNEL_ID_10293 = "" #

##@route(mode='plain_sexy')
def Plain_sexy():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Thuggish Shows[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10001+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Dance And More[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10002+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Amit Bar Art Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10003+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Ladies Carwash[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10007+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Ireila Bodypainting[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10009+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#@route(mode='sexy_sports')
def Sexy_sports():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]WWE Bra And Panties Matches[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10025+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Aerobics And Fitness[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10027+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Sports: Ronda Rousey[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10028+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]New Car And Hot Girl Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10029+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Bike Show Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10030+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Girls N Cars Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10031+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sports Girls Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10032+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Beach Volleyball Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10033+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Amazing Sports Video[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10034+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Games Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10035+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Bikes N Hot Women[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10036+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]WOW Superheroes Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10037+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Girls Grappling Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10038+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#@route(mode='sexy_home')
def Sexy_home():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Cooking Made Sexy By Tifa[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10050+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
	Add_Dir(
		name="[COLOR white][B]Cooking And Cleaning[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10051+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Sexy Home Bodies[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10052+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Sexy Chef Wendy[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10053+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Lilys Sizzlin Cooking Show[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10054+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Naked News: Bakers[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10056+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#@route(mode='sexy_fashion')
def Sexy_fashion():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Sexy Girls[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10075+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Victoria Secret Fashion Show[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10076+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Fashion Week - Bikini Models[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10077+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Sexy Tribute[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10078+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Swimwear[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10079+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]AmitBar Art Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10081+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Love Birds Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10082+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Top Model Sexy Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10083+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Women Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10084+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#@route(mode='sexy_channels')
def Sexy_channels():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Sports Illustrated Swimsuit[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10100+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Victoria s Secret Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10101+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
	
	Add_Dir(
		name="[COLOR white][B]Playboy Television Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10102+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Model Society Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10103+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Naked News Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10104+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]World Naked Bike Ride[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10105+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]After Eden Lingerie[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10106+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Swimwear Hot Collection[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10107+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)
	
#@route(mode='sexy_fitness')
def Sexy_fitness():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy 3VFitness Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10125+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]Story Female Fitness[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10126+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]Sexy Girls Gym Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10127+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]My Fitness Girls Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10128+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Girls Motivation[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10129+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Fitness Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10130+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Hot Fitness Ladies[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10131+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir( 
		name="[COLOR white][B]Sexy Female Muscle[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10132+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Fit Gals Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10133+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]Sexy Girls Fitness[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10134+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir( 
		name="[COLOR white][B]Hot Flex Yoga Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10135+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#@route(mode='sexy_tattoo')
def Sexy_tattoo():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)
		
	Add_Dir( 
		name="[COLOR white][B]Sexy Tattoos Playlist[/B][/COLOR]", url=BASE+YOUTUBE_CHANNEL_ID_10150+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]18+ Sexy Tattoo Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10151+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]Sexy Intim Tattoo Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10152+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir( 
		name="[COLOR white][B]Sexy Tattoo Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10153+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Art Tattoo Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10154+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Body Art Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10155+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
	
	Add_Dir(
		name="[COLOR white][B]Body Paint Festival Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10156+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Body Art Studio Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10157+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Body Art Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10158+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]See Art Works Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10159+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#@route(mode='sexy_bikini')
def Sexy_bikini():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Bikini Risque Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10169+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
	
	Add_Dir(
		name="[COLOR white][B]Hot Bikini Auditions[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10170+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]World Swimsuit Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10171+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Girls On The Beach[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10178+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Bikini Paradiso Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10179+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Girls Bikini Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10180+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Bikini Beach Party Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10181+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Bikini Celebrity Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10182+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Mr. Bikini Contest Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10183+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Bikini Models[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10184+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)
	
#@route(mode='sexy_dance')
def Sexy_dance():

	add_link_info('[B][COLORorange]=== Risque ===[/COLOR][/B]',mediapath+"icon-red.png", fanart)

	Add_Dir(
		name="[COLOR white][B]Sexy Girls Dancing Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10275+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Mast Manoranjan Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10276+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]The Hot Dance Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10277+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Female Dance Fitness[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10278+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Maddie sparkle Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10279+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Aryanna The Pole Dancer[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10280+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Dance Filthy USA Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10281+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Alethea Austin Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10282+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Twerking Pro XI Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10283+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]Twerk With Tinze Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10284+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Empress Cece Channel[/B][/COLOR]", url=cBASE+YOUTUBE_CHANNEL_ID_10285+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)
		
	Add_Dir(
		name="[COLOR white][B]Typical Twerk Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10286+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	Add_Dir(
		name="[COLOR white][B]The Twerk Trap Channel[/B][/COLOR]", url=uBASE+YOUTUBE_CHANNEL_ID_10287+"/", folder=True,
		icon=mediapath+"risque-red.png", fanart=fanart)

	add_link_info('[B][COLORorange] [/COLOR][/B]',mediapath+"icon-red.png", fanart)

#xbmcplugin.endOfDirectory(plugin_handle)
