# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import sys
from urllib.parse import urlencode
from urllib.parse import parse_qsl
import xbmcgui
import xbmcplugin
_url = sys.argv[0]
_handle = int(sys.argv[1])

VIDEOS ={            
'Health & Wellness': [
	                  {'name': '[COLOR aqua][B]Myndstream - Meditation Music for Personal Well-being[/B][/COLOR]   -The power of music for personal wellbeing.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/98/logos/ce0c10bc-47ab-403e-8d71-9dbca9f10c21.png',
                       'video': 'https://ice55.securenetsystems.net/DASH93',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Dash Lofi - Chill & Instrumental Hip-Hop Beats[/B][/COLOR]   -Lofi beats for your body, mind, & soul.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/57/logos/5a781df1-227e-452a-8576-0530244dee94.png',
                       'video': 'https://ice55.securenetsystems.net/DASH25',
                       'genre': 'MusicChoice'},					   
                      ],
'POP': [
			          {'name': '[COLOR aqua][B]Dash Pop X[/B][/COLOR]   -Your source for all the top hits right now!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHXPOP/dash_x_pop_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH17',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Dash Hits X[/B][/COLOR]   -Dash Hits X gives you the biggest hits from today and back in the day.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/214/logos/c701b24d-c9f9-41da-8829-01baa5cea68a.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH58',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Dash X[/B][/COLOR]   -Genre-less. No rules. No boundaries.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHX/dash_x_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH31',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Fusion - Blending Pop, Latin, Country & More![/B][/COLOR]   -Blending Pop, Latin, Country & More!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/FUSION/fusion_324.png',
                       'video': 'https://ice55.securenetsystems.net/DASH88',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Pop Family - Hits for the Family to Enjoy[/B][/COLOR]   -Kid-friendly songs that the whole family can enjoy!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/199/logos/ef07f038-a829-4db6-a92c-778973e3f06d.png',
                       'video': 'https://ice55.securenetsystems.net/DASH94',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Triller[/B][/COLOR]   -Keep It Trill...powered by the fastest growing creative video app: Triller!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/228/logos/2849b82f-4546-41d0-9b83-a375b3fda48a.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH81',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Discover[/B][/COLOR]   -Discover is updated constantly to bring you breaking and building artists!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Discover.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH46',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Love Songs[/B][/COLOR]   -Bow-chicka-wow-wow. Baby-making music at its finest.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Love.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH66',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Happy Fun Time Rainbow Radio - Happy Hits[/B][/COLOR]   -Happy Fun Time Rainbow Radio: Good times, happy music!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/HAPPYFUNTIMERAINBOWRADIO/HFTRR_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH41',
                       'genre': 'MusicChoice'},
					   
					   
                      {'name': '[COLOR aqua][B]SoundCloud Radio[/B][/COLOR]   -All the hottest tracks on SoundCloud',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/235/logos/340a73c9-2a3b-4b7d-a63c-f2805d81d928.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH68',
                       'genre': 'MusicChoice'},					   
                      ],
'Hip-Hop': [
			         {'name': '[COLOR aqua][B]Dash Hip-Hop X[/B][/COLOR]   -Todays Biggest Hip Hop Hits!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHXHIPHOP/dash_x_hiphop_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH90',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The City[/B][/COLOR]   -Todays Hottest Hip-Hop and R&B',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/49/logos/f2bfb506-9f0e-4e0a-9a6c-65cf83743777.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH2',
                       'genre': 'MusicChoice'},
					   
					   
                      {'name': '[COLOR aqua][B]Doggystyle[/B][/COLOR]   -West Coast Hip-Hop Programmed By Snoop Dogg',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/DOGGYSTYLE/doggystyle_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH78',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Southside[/B][/COLOR]   -Live from the ATL',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/SOUTHSIDE/southside_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH95',
                       'genre': 'MusicChoice'},
					   
					   
                      {'name': '[COLOR aqua][B]1580 - Classic Hip-Hop Hits[/B][/COLOR]   -Let legendary hip-hop DJ Julio G guide you down memory lane.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/1580.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH11',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Native Rhymes - Classic Hip-Hop[/B][/COLOR]   -Listen to your favorite throwbacks & discover new underground artists!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/NativeRhymes.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH18',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Independent Grind - Powered by Tech N9ne[/B][/COLOR]   -Powered by Tech N9ne and independent rap label, Strange Music!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/IndependentGrind.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH8',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Beat Junkie Radio - Classic Hip-Hop[/B][/COLOR]   -The world famous DJ crew has been unleashed exclusively on Dash Radio!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/BeatJunkieRadio.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH51',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Delicious Vinyl Radio[/B][/COLOR]   -Classic Hip-Hop',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/POPUPS/DVR/vinyl_324_.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH71',
                       'genre': 'MusicChoice'},	
					   
                      {'name': '[COLOR aqua][B]BREALTV - Classic Hip-Hop[/B][/COLOR]   -Brought to you by legendary B-Real of Cypress Hill!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/BREALTVColor.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH60',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Get Familiar Radio[/B][/COLOR]   -Presented By Clinton Sparks',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/208/logos/b190aa6e-fa0b-45cd-8797-0e4d67a6c3d1.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH74',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]TASTE[/B][/COLOR]   -Hip-Hop Culture',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/233/logos/552d1a04-1338-4754-a365-308437c373fe.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH85',
                       'genre': 'MusicChoice'},					   
                      ],
'Electronic And Dance': [
					  {'name': '[COLOR aqua][B]Insomniac Radio[/B][/COLOR]   -Electronic Music & Festivals',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/218/logos/c0d7b14a-9c44-4818-94ab-4ae8039ab5cb.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH65',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Dash Dance X[/B][/COLOR]   -A non-stop mix of all the hottest dance music worldwide.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHDANCE/dash_x_dance_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH84',
                       'genre': 'MusicChoice'},	

                      {'name': '[COLOR aqua][B]Dash Bot X[/B][/COLOR]   -Curated For And By Dash Radio Bot Users!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/138/logos/fb9eaebf-1de6-4cef-99ae-b183e41fe4af.png',
                       'video': 'https://ice55.securenetsystems.net/DASH45',
                       'genre': 'MusicChoice'},						   
					   
                      {'name': '[COLOR aqua][B]Electro City[/B][/COLOR]   -Your home for electronic music.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Electrocity.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH9',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Overdrive[/B][/COLOR]   -Mixes, Remixes, Bootlegs, & Mashups',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/180/logos/8ae49444-f5b2-49a9-8fce-07d985d61fe3.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH73',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Waves - Chill Electronic & Lofi[/B][/COLOR]   -Let your mind drift away in this ocean of future electronic beats.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/104/logos/ebbd8a08-e215-4824-a5cd-d0fcd28aa3c5.png',
                       'video': 'https://ice55.securenetsystems.net/DASH55',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Monstercat - Electronic Music[/B][/COLOR]   -Iconic music from the largest EDM label in the world.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/MonsterCat.png',
                       'video': 'https://ice55.securenetsystems.net/DASH63',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Tastemakers[/B][/COLOR]   -The quintessential party station!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/9/logos/a72898bb-bd72-4075-b98c-f53849c34ceb.png',
                       'video': 'https://ice55.securenetsystems.net/DASH72',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Rinse - Live from East London[/B][/COLOR]   -Pulse of the underground.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Rinse.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH70',
                       'genre': 'MusicChoice'},					   
                      ],					   
'Latin': [
			          {'name': '[COLOR aqua][B]Dash Latin X[/B][/COLOR]   -DASH LATIN X features artists like J Balvin, Maluma, Shakira & more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHXLATIN/dash_x_latin_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH48',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]La Campesina[/B][/COLOR]   -Popular Regional Mexican Music, News & Entertainment!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/127/logos/45abdfd9-6fe6-4dfe-9651-70a23c44dd1f.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH43',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Imperio - Corridos y Más[/B][/COLOR]   -Imperio es El Patron de los Corridos!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/IMPERIO/imperio_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH27',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]La Isla - Pure Bachata[/B][/COLOR]   -Spice up the romance with a dose of pure Bachata.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/LaIsla.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH10',
                       'genre': 'MusicChoice'},					   
                      ],
'Rock': [
			          {'name': '[COLOR aqua][B]Dash Alt X[/B][/COLOR]   -Catch top alternative hits by the bands you love!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHXALT/dash_x_alt_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH12',
                       'genre': 'MusicChoice'},
					   
			          {'name': '[COLOR aqua][B]Dash Alt X Classics[/B][/COLOR]   -Yesterdays Alternative Hits!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/206/logos/2d7a5d8c-8a87-4458-95f5-0aab1eec1746.png',
                       'video': 'https://ice55.securenetsystems.net/DASH83',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]MONSTERS OF ROCK[/B][/COLOR]   -Home To Musics greatesthard rock and Heavy Metal',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/MONSTERSOFROCK/mor_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH14',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Grunge - 90s Rock[/B][/COLOR]   -Seattles signature sound dominated 90s rock. This is the era of Grunge.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/164/logos/491736a0-b88d-45ee-852c-5325eb9d6174.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH61',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Church of Rock & Roll[/B][/COLOR]   -If Rock & Roll is your religion, this is your house of worship.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/41/logos/2ed70706-c9b5-451d-8852-5dbcebe42ca9.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH21',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Dash Indie[/B][/COLOR]   -Your #1 stop for Indie Rock!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/DashIndie.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH32',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Strip - 80s Hair Band Rock[/B][/COLOR]   -Relive the Sunset Strip circa de 1980.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/TheStrip.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH24',
                       'genre': 'MusicChoice'},						   
                      ],
'Decades': [
			          {'name': '[COLOR aqua][B]10Dash20[/B][/COLOR]   -The biggest hits of 2010-2020. This is the music of Gen Z.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/234/logos/fad9ff01-5200-4df6-a3a1-ed17922a5586.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH52',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Y2K[/B][/COLOR]   -A diverse mix of your favorite songs from the 2000s.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Y2K.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH19',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]90s[/B][/COLOR]   -90s hits at their finest.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/90s.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH1',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]80s[/B][/COLOR]   -Hair metal, new wave, pop, electronic. You catch the drift.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/31/logos/b096f16a-dd7e-48fa-973c-af79143fc008.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH7',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]70s[/B][/COLOR]   -From R&B to Glam rock to Disco, all the Grooviest 70s Hits!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/70s.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH26',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]60s[/B][/COLOR]   -A decade of great change - a decade of great music.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/2/logos/9a78de9b-4366-45c8-b3e7-911ef7251352.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH34',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Ratpack - Sinatra & Friends[/B][/COLOR]   -Frank, Sammy, Dean, and everything in between!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Ratpack.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH5',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Disco Fever[/B][/COLOR]   -Celebrating the Disco Fever era!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/DiscoFever.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH4',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Swing - Classic to Electro[/B][/COLOR]   -From the hotel ballroom, we present a program of dancing music for all ages.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/SWING/Swing-Color.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH80',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Fun For Life Radio[/B][/COLOR]   -Discovery Worthy TUNES x Real-Talk SHOWS... Punch your ears in the face!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/178/logos/bfa8b3d6-1d26-493d-a24a-8bbe17ee75aa.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH49',
                       'genre': 'MusicChoice'},	
					   
                      {'name': '[COLOR aqua][B]Hawkins Radio[/B][/COLOR]   -Hawkins Radio-Hawkins hometown radio station!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/226/logos/986176e9-a112-4329-bff2-fb16c80a133f.png',
                       'video': 'http://ice55.securenetsystems.net/DASH44',
                       'genre': 'MusicChoice'},					   
                      ],
'R & B': [
			          {'name': '[COLOR aqua][B]Dash R&B X[/B][/COLOR]   -Listen to your favorite artists such as Beyonce, Kehlani, The Weeknd and more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/50/logos/80156832-ba8b-4c3a-9e24-c5590be67b37.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH47',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Snoop Doggs Cadillacc Music[/B][/COLOR]   -Presented by Snoop Dogg aka DJ Snoopadelic, this is Cadillacc Music.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/107/logos/590aec9f-6927-4ad8-8125-96353e4c3ca9.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH16',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Moonlight - Todays R&B[/B][/COLOR]   -All your favorite R&B hits!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/224/logos/e3723e8b-7696-4f8b-a591-c3eb518e1b86.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH37',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Boomerang - 90s R&B[/B][/COLOR]   -Curated by Shawn Stockman of BoyzIIMen, feat. his show “The Bridge”',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/53/logos/0c3ecccd-1495-44c8-9fcd-cc7e9e53a7c4.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH39',
                       'genre': 'MusicChoice'},					  
					   
                      {'name': '[COLOR aqua][B]Pure Soul - Powered by Isaac Hayes[/B][/COLOR]   -Sit back and let Isaac Hayes guide your journey to soulful bliss.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/PureSoul.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH36',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Super Freak[/B][/COLOR]   -Powered by Rick James, the best funk and soul of the 60s, 70s & 80s!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/SUPERFREAK/superfreak_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH22',
                       'genre': 'MusicChoice'},
                      ],					   
'Talk': [
                      {'name': '[COLOR aqua][B]Dash Talk X[/B][/COLOR]   -Bold personalities covering a range of topics.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHXTALK/dash_x_talk_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH50',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Laugh Factory - Live Comedy[/B][/COLOR]   -The best of moments from the World Famous Laugh Factory!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/217/logos/298f4cb0-baae-4dba-89ee-5ae7ea0ea523.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH92',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Old Time Radio[/B][/COLOR]   -Entertainment from Radios Golden Age. Comedy, Mystery, Drama!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/207/logos/d8400d1a-0002-4c50-b369-8e0d351ad69d.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH30',
                       'genre': 'MusicChoice'},	
					  
                      {'name': '[COLOR aqua][B]Future of Health[/B][/COLOR]   -Powered by Providence St. Joseph Health',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/227/logos/688c68dd-ca72-43a0-928f-9819656c6299.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH76',
                       'genre': 'MusicChoice'},	

                      {'name': '[COLOR aqua][B]Nothin But Net - All Things Basketball[/B][/COLOR]   -Showcasing NBA, WNBA, NBA2K League, and Fantasy Basketball coverage.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/NOTHINBUTNET/nbn_2_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH96',
                       'genre': 'MusicChoice'},					   					   					   
					   
                      {'name': '[COLOR aqua][B]Multiplayer - Gaming Talk[/B][/COLOR]   -From e-sports to platformers, your center for gaming talk!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/MULTIPLAYER/multiplayer_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH57',
                       'genre': 'MusicChoice'},					   
					   				   
                      ],
'Jazz And Classical': [
			          {'name': '[COLOR aqua][B]Cool - Classic Jazz[/B][/COLOR]   -The best of jazz from then and now. No one messes with our sax appeal.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Cool.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH6',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Blue Spot[/B][/COLOR]   -Home of the Blues',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/181/logos/a01caaa1-ed34-4591-a04a-eb5787b91fac.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH59',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Concerto - Classical[/B][/COLOR]   -Timeless classical pieces performed by the best orchestras in the world.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Concerto.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH33',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Cinescore - Movie Soundtracks[/B][/COLOR]   -Cinescore presents classic film scores & movie soundtracks.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Cinescore.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH29',
                       'genre': 'MusicChoice'},	
					   
                      {'name': '[COLOR aqua][B]Broadway Records Radio - Showtunes and Broadway Stars[/B][/COLOR]   -Your favorite Broadway hits and vocalists from Broadway’s premiere Grammy-winning label!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/77/logos/c4fdcf0d-aaad-4fe6-a126-7bcb6f28c118.png',
                       'video': 'https://ice55.securenetsystems.net/DASH75',
                       'genre': 'MusicChoice'},					   
                      ],
'Country': [
			          {'name': '[COLOR aqua][B]Dash Country X[/B][/COLOR]   -Home For Country Musics Biggest Hits and Upcoming Stars!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/43/logos/d1b67ff2-ec59-4caf-a2c0-670b9e79f899.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH35',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Ranch - Classic Country[/B][/COLOR]   -Country Musics Greatest Hits From Years Past.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/TheRanch.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH13',
                       'genre': 'MusicChoice'},				   
                      ],
'Faith And Gospel': [
			          {'name': '[COLOR aqua][B]Rhythm & Praise - Gospel R&B[/B][/COLOR]   -Rhythm & Praise, Gospels R&B! Curated by Those Baxters & Emcee N.I.C.E',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/200/logos/b95fc039-b72e-40ec-bfd4-617e11f88af8.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH56',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Gods House of Hip Hop - Gospel Hip-Hop[/B][/COLOR]   -CHH & Gospel Hip Hop music curated by Emcee N.I.C.E',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/GH3/GH3_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH77',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Cross - Christian Pop/Rock[/B][/COLOR]   -Jesus, grab the wheel! The best of Christian pop and rock.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/TheCross2016Color.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH42',
                       'genre': 'MusicChoice'},
                      ],					   
'World': [
			          {'name': '[COLOR aqua][B]Identity Asia Radio - K-Pop Hits[/B][/COLOR]   -Listen now for the hottest K-Pop hits and more! @IdentityAsia',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/IDENTITY/asia_color_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH53',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Island City - Music of the Pacific Islands[/B][/COLOR]   -Island City is your home for NEW Polynesian, Micronesian and Melanesian sound!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/171/logos/69cff7b9-353b-43e6-9458-4862e11d6e81.png',
                       'video': 'https://ice55.securenetsystems.net/DASH40',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Rukus Avenue Radio - South Asian Culture[/B][/COLOR]   -Rukus Avenue Radio is Dash Radio’s exclusive South Asian radio station.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/212/logos/b2474560-e61f-4a4e-a6c0-9bd2d3b43bd0.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH54',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]YG Presents - K-Pops Top Label[/B][/COLOR]   -Koreas top label, presents you with your favorite YG artists.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/YG.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH28',
                       'genre': 'MusicChoice'},	
					   
                      {'name': '[COLOR aqua][B]Reggae King[/B][/COLOR]   -Taking you straight to the Caribbean with the biggest reggae tracks!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/ReggaeKing.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH79',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]MyxRadio - Fresh Global Music First[/B][/COLOR]   -Discover R&B, Hip-Hop, Pop & Dance artists from around the world here.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/223/logos/bdfb58cc-db23-4e80-898a-7ceaa3c55bdc.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH62',
                       'genre': 'MusicChoice'},	

                      {'name': '[COLOR aqua][B]Afrobeats[/B][/COLOR]   -Groove to the biggest sounds and top artists from Africa and its diaspora.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/118/logos/d0918be2-d818-4bd5-b41a-f9ee9a44e7a0.png',
                       'video': 'https://ice55.securenetsystems.net/DASH64',
                       'genre': 'MusicChoice'},					   
                     ]}


def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def get_categories():
    return iter(VIDEOS.keys())

def get_videos(category):
    return VIDEOS[category]

def list_categories():
    xbmcplugin.setPluginCategory(_handle, 'My Video Collection')
    xbmcplugin.setContent(_handle, 'videos')
    categories = get_categories()
    for category in categories:
        list_item = xbmcgui.ListItem(label=category)
        list_item.setArt({'thumb': VIDEOS[category][0]['thumb'],
                          'icon': VIDEOS[category][0]['thumb']})
        list_item.setInfo('video', {'title': category,
                                    'genre': category,
                                    'mediatype': 'video'})
        url = get_url(action='listing', category=category)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    xbmcplugin.endOfDirectory(_handle)

def list_videos(category):
    xbmcplugin.setPluginCategory(_handle, category)
    xbmcplugin.setContent(_handle, 'videos')
    videos = get_videos(category)
    for video in videos:
        list_item = xbmcgui.ListItem(label=video['name'])
        list_item.setInfo('video', {'title': video['name'],
                                    'genre': video['genre'],
                                    'mediatype': 'video'}) 
        list_item.setArt({'thumb': video['thumb'], 'icon': video['thumb']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play', video=video['video'])
        is_folder = False
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    xbmcplugin.endOfDirectory(_handle)

def play_video(path):
    play_item = xbmcgui.ListItem(path=path)
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            list_videos(params['category'])
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        list_categories()

if __name__ == '__main__':
    router(sys.argv[2][1:])
