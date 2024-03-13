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

'POP': [
			          {'name': '[COLOR aqua][B]Dash Pop X[/B][/COLOR]   -All your favorite hit music!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/28/logos/542622a1-a645-4626-9bec-a4d7417d3909.png',
                       'video': 'https://ice55.securenetsystems.net/DASH17',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Hits X[/B][/COLOR]   -Hits X gives you the biggest hits from today and back in the day.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/214/logos/15a68223-d534-4f66-998f-5c92f224456d.png',
                       'video': 'https://ice55.securenetsystems.net/DASH58',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Lit Live X[/B][/COLOR]   -Only The worlds hottest Live - EXPLICIT!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHX/dash_x_nowplaying_1080.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH50',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Fusion - Blending Pop, Latin, Country & More![/B][/COLOR]   -Blending Pop, Latin, Country & More!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/172/logos/cedbbb9d-2b5b-46ef-ab26-02c48478a4de.png',
                       'video': 'https://ice55.securenetsystems.net/DASH88',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Pop Family - Hits for the Family to Enjoy[/B][/COLOR]   -Kid-friendly songs that the whole family can enjoy!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/199/logos/a1bbe3e1-0d61-4145-b406-6d9b9452a22d.png',
                       'video': 'https://ice55.securenetsystems.net/DASH94',
                       'genre': 'MusicChoice'},				   
					   
                      {'name': '[COLOR aqua][B]Discover[/B][/COLOR]   -Discover is updated constantly to bring you breaking and building artists!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/59/logos/0b25c175-0a06-4fcf-897e-88f2ef82ef46.png',
                       'video': 'https://ice55.securenetsystems.net/DASH46',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Wonderfront[/B][/COLOR]   -Wonderfront Music and Arts Festival Radio.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/231/logos/44ca3ba7-8fe9-40ce-aca0-a2fb90a4ab49.png',
                       'video': 'https://ice55.securenetsystems.net/DASH51',
                       'genre': 'MusicChoice'},
                      ],
					   
'Hip-Hop': [
			         {'name': '[COLOR aqua][B]Litt Hip-Hop X[/B][/COLOR]   -Todays Biggest Hip Hop Hits!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/33/logos/a28f1da9-17ca-455f-a2d8-288b7ddfd930.png',
                       'video': 'https://ice55.securenetsystems.net/DASH90',
                       'genre': 'MusicChoice'},
                     
                      {'name': '[COLOR aqua][B]Ice Cube Presents: BIG3 Radio[/B][/COLOR]   -Home Of Ice Cubes BIG3! Check Out BIG3.com. ',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/186/logos/089e1196-12f5-420e-a7ac-80ac0d4b21ba.png',
                       'video': 'https://ice55.securenetsystems.net/DASH37',
                       'genre': 'MusicChoice'},                     
					   
                      {'name': '[COLOR aqua][B]The City[/B][/COLOR]   -Todays Hottest Hip-Hop and R&B',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/49/logos/8ceedadb-34d9-4641-8595-344c48e6ff54.png',
                       'video': 'https://ice55.securenetsystems.net/DASH2',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Southside - Live from the ATL[/B][/COLOR]   -Southside is your destination to hear the best music, interviews and mixes!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/SOUTHSIDE/southside_nowplaying_1080.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH95',
                       'genre': 'MusicChoice'},
					   				   
                      {'name': '[COLOR aqua][B]1580 - Classic Hip-Hop Hits[/B][/COLOR]   -Let legendary hip-hop DJ Julio G guide you down memory lane.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/1580.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH11',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Native Rhymes - Classic Hip-Hop[/B][/COLOR]   -Listen to your favorite throwbacks & discover new underground artists!',
                       'thumb': 'http://radio.securenetsystems.net/file_radio/stations_large/DASH8/v5/album-art-default.png',
                       'video': 'https://ice55.securenetsystems.net/DASH18',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Independent Grind - Powered by Tech N9ne[/B][/COLOR]   -Powered by Tech N9ne and independent rap label, Strange Music!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/IndependentGrind.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH8',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Delicious Vinyl Radio[/B][/COLOR]   -Classic Hip-Hop',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/POPUPS/DVR/vinyl_600.png',
                       'video': 'https://ice55.securenetsystems.net/DASH93',
                       'genre': 'MusicChoice'},	
                   
                      {'name': '[COLOR aqua][B]TASTE[/B][/COLOR]   -TASTE is your acoustic experience of music & talk curated for culture & entmt.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/233/logos/36b2f937-08da-49fb-836e-363c28ab8c91.png',
                       'video': 'https://ice55.securenetsystems.net/DASH85',
                       'genre': 'MusicChoice'}, 

                      {'name': '[COLOR aqua][B]Jardín Sounds[/B][/COLOR]   -Roll up and listen loud with premium sounds from Las Vegas #1 cannabis dispensary Jardin',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/233/logos/36b2f937-08da-49fb-836e-363c28ab8c91.png',
                       'video': 'https://ice55.securenetsystems.net/DASH49',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]SmashHaus - Classic Hip-Hop[/B][/COLOR]   -Spinning the best emerging artists worldwide',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/235/logos/125c06b7-9682-4e9d-a918-901a8152e48c.png',
                       'video': 'https://ice55.securenetsystems.net/DASH84',
                       'genre': 'MusicChoice'},
                   
                      {'name': '[COLOR aqua][B]Doggystyle[/B][/COLOR]   -West Coast Hip-Hop Programmed By Snoop Dogg',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/147/logos/a7fdc27f-b1f6-469a-87a0-4ea639121695.png',
                       'video': 'https://ice55.securenetsystems.net/DASH78',
                       'genre': 'MusicChoice'},

                      {'name': '[COLOR aqua][B]Gods House of Hip Hop - Gospel Hip-Hop[/B][/COLOR]   -CHH & Gospel Hip Hop music curated by Emcee N.I.C.E',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/GH3/GH3_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH77',
                       'genre': 'MusicChoice'},
                      
	                  {'name': '[COLOR aqua][B]Lofi - Chill & Instrumental Hip-Hop Beats[/B][/COLOR]   -Lofi beats for your body, mind, & soul.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/57/logos/370c1db2-d4d6-4d6c-a8e7-57c52b954c96.png',
                       'video': 'https://ice55.securenetsystems.net/DASH54',
                       'genre': 'MusicChoice'},

                      {'name': '[COLOR aqua][B]Nothin But Net - All Things Basketball[/B][/COLOR]   -Showcasing NBA, WNBA, NBA2K League, and Fantasy Basketball coverage.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/NOTHINBUTNET/nbn_2_nowplaying_1080.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH96',
                       'genre': 'MusicChoice'},
                       
                      ],					   
'Electronic And Dance': [

                      {'name': '[COLOR aqua][B]Overdrive[/B][/COLOR]   -Mixes, Remixes, Bootlegs, & Mashups',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/180/logos/90dc5bff-51ac-4766-bc41-17b3557fc9a6.png',
                       'video': 'https://ice55.securenetsystems.net/DASH73',
                       'genre': 'MusicChoice'},
                       
					  {'name': '[COLOR aqua][B]Insomniac Radio[/B][/COLOR]   -Electronic Music & Festivals',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/218/logos/b82b4aa1-dcad-46b2-9987-ea4baa1462e3.png',
                       'video': 'https://ice55.securenetsystems.net/DASH32',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Litt Dance X[/B][/COLOR]   -A non-stop mix of all the hottest dance music worldwide.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/198/logos/2d8f5e64-774d-4caf-a89f-bb305e3656ae.png',
                       'video': 'https://ice55.securenetsystems.net/DASH81',
                       'genre': 'MusicChoice'},
                       
                      {'name': '[COLOR aqua][B]Electro City[/B][/COLOR]   -Your home for electronic music.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/ElectroCity.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH9',
                       'genre': 'MusicChoice'},                                              

                      {'name': '[COLOR aqua][B]Waves - Chill Electronic & Lofi[/B][/COLOR]   -Let your mind drift away in this ocean of future electronic beats.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/104/logos/90e61667-6557-4603-8b95-be5f9f071847.png',
                       'video': 'https://ice55.securenetsystems.net/DASH55',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Monstercat - Electronic Music[/B][/COLOR]   -Iconic music from the largest EDM label in the world.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/MonsterCat_2.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH4',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Tastemakers[/B][/COLOR]   -The quintessential party station!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/9/logos/e068e789-cc45-4253-a8b9-0dbbc03603cc.png',
                       'video': 'https://ice55.securenetsystems.net/DASH72',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Rinse - Live from East London[/B][/COLOR]   -Pulse of the underground.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/artwork/iphone6plus/Rinse/RinseArtworkB.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH70',
                       'genre': 'MusicChoice'},
                
                      {'name': '[COLOR aqua][B]Disco Fever/B][/COLOR] - Celebrating the Disco Fever era!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/colored_light/Rinse.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH20',
                       'genre': 'MusicChoice'},                
                      ],					   
'Latin': [
			          {'name': '[COLOR aqua][B]Litt Latin X[/B][/COLOR]   -DASH LATIN X features artists like J Balvin, Maluma, Shakira & more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/60/logos/b5a42255-1bb8-45ac-9f3a-08ee09c066ce.png',
                       'video': 'https://ice55.securenetsystems.net/DASH48',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]La Isla-Pure Tropical[/B][/COLOR]   -Grab your dancing partner for Bachata, Merengue, Salsa, y Más!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/95/logos/45e42f4c-bfba-4588-8af4-8c7c5a5fa002.png',
                       'video': 'https://ice55.securenetsystems.net/DASH10',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Imperio - Corridos y Más[/B][/COLOR]   -Imperio es El Patron de los Corridos!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/now_playing_artwork/IMPERIO/imperio_1080.png',
                       'video': 'https://ice55.securenetsystems.net/DASH27',
                       'genre': 'MusicChoice'},
					   					   
                      ],
'Rock': [
			          {'name': '[COLOR aqua][B]Litt Rock X[/B][/COLOR]   -All your favorite rock music, all in one place!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/22/logos/0d5b5dbd-f093-4f99-9605-878b456ecf41.png',
                       'video': 'https://ice55.securenetsystems.net/DASH38',
                       'genre': 'MusicChoice'},
					   
			          {'name': '[COLOR aqua][B]Litt Alt X[/B][/COLOR]   -Catch top alternative hits by the bands you love!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/37/logos/afc9fb3c-c309-4e58-a99f-49b9beb773c8.png',
                       'video': 'https://ice55.securenetsystems.net/DASH12',
                       'genre': 'MusicChoice'},	

			          {'name': '[COLOR aqua][B]Alt X Classics[/B][/COLOR]   -Yesterdays Alternative Hits',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/37/logos/afc9fb3c-c309-4e58-a99f-49b9beb773c8.png',
                       'video': 'https://ice55.securenetsystems.net/DASH83',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]MONSTERS OF ROCK[/B][/COLOR]   -Home To Musics greatest hard rock and Heavy Metal',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/MONSTERSOFROCK/mor_nowplaying_1080.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH14',
                       'genre': 'MusicChoice'},
                       
                      {'name': '[COLOR aqua][B]Church of Rock & Roll[/B][/COLOR]   -If Rock & Roll is your religion, this is your house of worship.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/41/logos/23045a34-c70f-49b5-b316-1b3a310461f3.png',
                       'video': 'https://ice55.securenetsystems.net/DASH21',
                       'genre': 'MusicChoice'},

                      {'name': '[COLOR aqua][B]The Strip - 80s Hair Band Rock[/B][/COLOR]   -The head-bangin’, hair-slingin’ rock & roll you used to listen to in your mom’s basement. Hopefully you’re not still living there.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/TheStrip.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH24',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Litt Indie[/B][/COLOR]   -Your #1 stop for Indie Rock!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/DashIndie.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH16',
                       'genre': 'MusicChoice'},                      
					  
                      {'name': '[COLOR aqua][B]Grunge - 90s Rock[/B][/COLOR]   -Put on your lumberjack shirt, tattered boots & long underwear, and enjoy some raw, American-made rock & roll.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/164/logos/0e64637e-7b29-477e-883b-ae7408d275ee.png',
                       'video': 'https://ice55.securenetsystems.net/DASH25',
                       'genre': 'MusicChoice'},					   					   
					   						   
                      ],
'Decades': [
			          {'name': '[COLOR aqua][B]10Dash20[/B][/COLOR]   -The biggest hits of 2010-2020. This is the music of Gen Z.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/234/logos/e04c7371-c2da-4b2c-8877-f86a4019f629.png',
                       'video': 'https://ice55.securenetsystems.net/DASH52',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Y2K[/B][/COLOR]   -A diverse mix of your favorite songs from the 2000s.',
                       'thumb': 'http://radio.securenetsystems.net/file_radio/stations_large/DASH19/v5/album-art-default.png',
                       'video': 'https://ice55.securenetsystems.net/DASH19',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]90s[/B][/COLOR]   -90s hits at their finest.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/90s.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH1',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]80s[/B][/COLOR]   -Hair metal, new wave, pop, electronic. You catch the drift.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/31/logos/957e6bf2-7337-47d9-86dd-144423eb18e5.png',
                       'video': 'https://ice55.securenetsystems.net/DASH7',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]70s[/B][/COLOR]   -From R&B to Glam rock to Disco, all the Grooviest 70s Hits!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/70s.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH26',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]60s[/B][/COLOR]   -A decade of great change - a decade of great music.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/2/logos/2ef5a3b9-01cb-454f-8208-eb694543e420.png',
                       'video': 'https://ice55.securenetsystems.net/DASH34',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Swing - Classic to Electro[/B][/COLOR]   -From the hotel ballroom, we present a program of dancing music for all ages.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/artwork/iphone6plus/SWING/SWING_COVER_ART.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH79',
                       'genre': 'MusicChoice'},
					   				   
                      ],
'R & B': [
			          {'name': '[COLOR aqua][B]Litt R&B X[/B][/COLOR]   -Listen to your favorite artists such as Beyonce, Kehlani, The Weeknd and more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/50/logos/3c5bb9ef-948d-40e0-b8e8-f451f77b948f.png',
                       'video': 'https://ice55.securenetsystems.net/DASH47',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Snoop Doggs Cadillacc Music[/B][/COLOR]   -Presented by Snoop Dogg aka DJ Snoopadelic, this is Cadillacc Music.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/107/logos/dc003550-a8af-433a-a93c-f202166c2cba.png',
                       'video': 'https://ice55.securenetsystems.net/DASH57',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Boomerang 90s R&B  -Curated by Shawn Stockman of BoyzIIMen, feat. his show “The Bridge”',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/53/logos/be546344-8468-4ab3-9b5e-713d43aabea7.png',
                       'video': 'https://ice55.securenetsystems.net/DASH39',
                       'genre': 'MusicChoice'},					   				  
					   
                      {'name': '[COLOR aqua][B]Pure Soul - Powered by Isaac Hayes[/B][/COLOR]   -Sit back and let Isaac Hayes guide your journey to soulful bliss.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/PureSoulPoweredByIsaacHayes.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH36',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Love Songs[/B][/COLOR]   -Bow-chicka-wow-wow. Baby-making music at its finest.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/artwork/iphone6plus/Love/Love.png',
                       'video': 'https://ice55.securenetsystems.net/DASH53',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Super Freak[/B][/COLOR]   -Give it to me baby, Gimme that funk, that sweet, that funky stuff.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/SUPERFREAK/superfreak_nowplaying_1080.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH22',
                       'genre': 'MusicChoice'},                      
                      ],					   

'Jazz And Classical': [
			          {'name': '[COLOR aqua][B]Cool - Classic Jazz[/B][/COLOR]   -Welcome to Masterclass. Take a seat & enjoy a conversation between instruments.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/Cool.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH6',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Blue Spot[/B][/COLOR]   -The root from which R&B, rock & roll, and hip-hop all sprouted: The Blues.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/181/logos/7ecb6c8d-9b23-443a-a94d-470e78a70744.png',
                       'video': 'https://ice55.securenetsystems.net/DASH41',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Ratpack-Sinatra &Friends[/B][/COLOR]   -The original boy band. Without these guys, Vegas would still be a truckstop.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/Ratpack.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH5',
                       'genre': 'MusicChoice'},                      
					   
                      {'name': '[COLOR aqua][B]Concerto - Classical[/B][/COLOR]   -Who is ready for some good, old-fashioned sax and violins? The greatest music of all time.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/Concerto.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH33',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Cinescore - Movie Soundtracks[/B][/COLOR]   -Great movies have great music. And sometimes, bad movies–still have pretty good soundtracks.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/Cinescore.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH29',
                       'genre': 'MusicChoice'},	
					   
                      {'name': '[COLOR aqua][B]Smooth Jazz Hits[/B][/COLOR]   -This ain’t your father’s jazz music. Unless you’re Kenny G’s kid.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/229/logos/8326cdbf-76c9-4dce-9aee-9a5eb60e6317.png',
                       'video': 'https://ice55.securenetsystems.net/DASH44',
                       'genre': 'MusicChoice'},					   
                      ],
'Country': [
			          {'name': '[COLOR aqua][B]Litt Country X[/B][/COLOR]   -Home For Country Musics Biggest Hits and Upcoming Stars!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/43/logos/285cae01-9538-434c-8aed-02060594bba3.png',
                       'video': 'https://ice55.securenetsystems.net/DASH35',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Ranch - Classic Country[/B][/COLOR]   -Country Musics Greatest Hits From Years Past.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/TheRanch.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH13',
                       'genre': 'MusicChoice'},

                      {'name': '[COLOR aqua][B]Nashville - Country Hits 2000-2020[/B][/COLOR]   - This ain’t your daddy’s country music. Unless he had you when he was 15.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/TheRanch.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH82',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Hooche Country - Mainstream Hits[/B][/COLOR]   - Your favorite kick-ass country + breaking artists & music: Live from Nashville!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/226/logos/404ac8e5-9a9a-46ac-8c2a-40d9ab808a42.png',
                       'video': 'https://ice55.securenetsystems.net/DASH15',
                       'genre': 'MusicChoice'},                      
                      ],
'Faith And Gospel': [
			          {'name': '[COLOR aqua][B]Rhythm & Praise - Gospel R&B[/B][/COLOR]   -Rhythm & Praise, Gospels R&B! Curated by Those Baxters & Emcee N.I.C.E',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/200/logos/a48cdc6e-3c01-4090-aa3d-c0f1d102d52b.png',
                       'video': 'https://ice55.securenetsystems.net/DASH56',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Gods House of Hip Hop - Gospel Hip-Hop[/B][/COLOR]   -CHH & Gospel Hip Hop music curated by Emcee N.I.C.E',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/GH3/GH3_324.png?raw=true',
                       'video': 'https://ice55.securenetsystems.net/DASH77',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Cross - Christian Pop/Rock[/B][/COLOR]   -Jesus, grab the wheel! The best of Christian pop and rock.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/TheCross2016Cover.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH42',
                       'genre': 'MusicChoice'},
                      ],					   
'World': [
					   
                      {'name': '[COLOR aqua][B]Island City - Music of the Pacific Islands[/B][/COLOR]   -Island City is your home for NEW Polynesian, Micronesian and Melanesian sound!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/171/logos/c5cbcc32-bef0-4322-9c84-1dee82d53930.png',
                       'video': 'https://ice55.securenetsystems.net/DASH40',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]MyxRadio - Fresh Global Music First[/B][/COLOR]   -Discover R&B, Hip-Hop, Pop & Dance artists from around the world here.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/223/logos/8d93276b-4c19-4755-989f-8dbaea73d5f0.png',
                       'video': 'https://ice55.securenetsystems.net/DASH62',
                       'genre': 'MusicChoice'},                      					   
					   
                      {'name': '[COLOR aqua][B]YG Presents - K-Pops Top Label[/B][/COLOR]   -Koreas top label, presents you with your favorite YG artists.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/YGGeneralArtwork.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH28',
                       'genre': 'MusicChoice'},	

                      {'name': '[COLOR aqua][B]Island Fever - Where Caribbean Music Lives[/B][/COLOR]   -Hits from across the Islands! Reggae, Dancehall, Soca, Calypso, and more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/215/logos/d49bcaf7-03c7-45bf-8780-c4d284384e3a.png',
                       'video': 'https://ice55.securenetsystems.net/DASH74',
                       'genre': 'MusicChoice'},
				   
                     ],
'Talk': [
                      {'name': '[COLOR aqua][B]Providence- Future Of Health Radio[/B][/COLOR]   -The future of health is here, with Providence.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/227/logos/3f639087-0630-4090-bf1a-6b2cc4092ed9.png',
                       'video': 'https://ice55.securenetsystems.net/DASH76',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Laugh Factory - Live Comedy[/B][/COLOR]   -The best of moments from the World Famous Laugh Factory!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/217/logos/c445149d-357b-4dd8-bf99-6613745afb0a.png',
                       'video': 'https://ice55.securenetsystems.net/DASH92',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Old Time Radio[/B][/COLOR]   -Comedy, Mystery, Drama! Entertainment from the Golden Age Of Radio.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/207/logos/29d5e33c-4f36-4b83-a0ed-601b5de2fadf.png',
                       'video': 'https://ice55.securenetsystems.net/DASH30',
                       'genre': 'MusicChoice'},

                      {'name': '[COLOR aqua][B]Nothin But Net - All Things Basketball[/B][/COLOR]   -Showcasing NBA, WNBA, NBA2K League, and Fantasy Basketball coverage.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/NOTHINBUTNET/nbn_2_nowplaying_1080.jpg',
                       'video': 'https://ice55.securenetsystems.net/DASH96',
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
