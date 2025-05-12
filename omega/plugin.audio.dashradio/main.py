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
			          {'name': '[COLOR aqua][B]LITT Pop[/B][/COLOR]   -All your favorite hit music!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/28/logos/b5581835-5a3a-4586-ada0-7a562b0c06c7.png',
                       'video': 'https://das-sa39.cdnstream1.com/5587_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]LITT Hits[/B][/COLOR]   -LITT Hits gives you the biggest hits from today and back in the day.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/214/logos/9e4e2f0e-0c45-4e00-a9f1-78d3400f3171.png',
                       'video': 'https://das-sa39.cdnstream1.com/5572_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]LITT Now[/B][/COLOR]   -The worlds hottest new music - EXPLICIT!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/DASHX/dash_x_nowplaying_1080.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5603_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Sunny[/B][/COLOR]   -SUNNY is your acoustic experience of music & talk curated for culture & entmt.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/233/logos/a038651d-a1bf-48b4-a94e-2d8573fa69a3.png',
                       'video': 'https://das-sa39.cdnstream1.com/5598_128',
                       'genre': 'MusicChoice'},
                      ],
					   
'Hip-Hop': [
			         {'name': '[COLOR aqua][B]Litt Hip-Hop[/B][/COLOR]   -Todays Biggest Hip-Hop Hits!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/33/logos/4d8962e9-0160-409e-9dd5-7d460af1d38d.png',
                       'video': 'https://das-sa39.cdnstream1.com/6067_128',
                       'genre': 'MusicChoice'},
                     
                      {'name': '[COLOR aqua][B]LITT City Radio[/B][/COLOR]   -Whats Hot On Da Block.!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/49/logos/3b45a2de-aa2e-421f-8648-027c1931bbbc.png',
                       'video': 'https://das-sa39.cdnstream1.com/6066_128',
                       'genre': 'MusicChoice'},                     
					   
                      {'name': '[COLOR aqua][B]Konvict Kulture[/B][/COLOR]   -Todays Hottest Hip-Hop and R&B',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/140/logos/6f5f0875-0690-4961-88ad-9726e743ebc8.png',
                       'video': 'https://das-sa39.cdnstream1.com/5600_128',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Ice Cube Presents: BIG3 Radio[/B][/COLOR]   -Home of Ice Cubes BIG3! Check Out Big3.Com for more info!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/186/logos/089e1196-12f5-420e-a7ac-80ac0d4b21ba.png',
                       'video': 'https://das-sa39.cdnstream1.com/5573_128',
                       'genre': 'MusicChoice'},
					   				   
                      {'name': '[COLOR aqua][B]Southside - Live from the ATL[/B][/COLOR]   -Southside is your destination to hear the best music, interviews and mixes!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/SOUTHSIDE/southside_nowplaying_1080.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5596_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Jardín Sounds[/B][/COLOR]   -Roll up & listen loud with premium sounds from the #1 cannabis dispensary in Las Vegas, Jardin!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/156/logos/69f91403-9496-47d1-9324-2f587ada247b.png',
                       'video': 'https://das-sa39.cdnstream1.com/5579_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Shaq Fu[/B][/COLOR]   -The Biggest DJ in the World — Shaq live in the mix on Shaq Fu Radio. Non Stop Hip-Hop and DJs from around the world. Check out Shaq DJing live from his house - DJ Diesel Throwing Down!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/237/logos/153c5af9-c065-4603-b3f0-e92b451111e4.png',
                       'video': 'https://radiocustoms.cdnstream1.com/shaqfu',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Doggystyle - West Coast Hip-Hop programmed by Snoop Dogg[/B][/COLOR]   -Taking you back to arguably one of the best eras in music!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/147/logos/a7fdc27f-b1f6-469a-87a0-4ea639121695.png',
                       'video': 'https://das-sa39.cdnstream1.com/5567_128',
                       'genre': 'MusicChoice'},	
                   
                      {'name': '[COLOR aqua][B]1580 ® - Classic Hip-Hop Hits[/B][/COLOR]   -Let legendary hip-hop DJ Julio G guide you down memory lane.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/1580.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5556_128',
                       'genre': 'MusicChoice'}, 

                      {'name': '[COLOR aqua][B]Native Rhymes - Classic Hip-Hop[/B][/COLOR]   -Listen to your favorite throwbacks & discover new underground artists!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/NATIVERHYMES/hiphopheads.png',
                       'video': 'https://das-sa39.cdnstream1.com/5584_128',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Delicious Vinyl Radio - Classic Hip-Hop[/B][/COLOR]   -Powered By Delicious Vinyl!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/icon_logos/POPUPS/DVR/vinyl_600.png',
                       'video': 'https://das-sa39.cdnstream1.com/5565_128',
                       'genre': 'MusicChoice'},                     
                      ],					   
'Electronic And Dance': [

					  {'name': '[COLOR aqua][B]SmashHaus[/B][/COLOR]   -Spinning the best emerging artists worldwide',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/235/logos/125c06b7-9682-4e9d-a918-901a8152e48c.png',
                       'video': 'https://das-sa39.cdnstream1.com/5593_128',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Litt Dance X[/B][/COLOR]   -A non-stop mix of all the hottest dance music worldwide.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/198/logos/0b05d464-7097-4fb2-b200-54cf0e60e7ee.png',
                       'video': 'https://das-sa39.cdnstream1.com/5564_128',
                       'genre': 'MusicChoice'},

                      {'name': '[COLOR aqua][B]Overdrive - Mixes, Remixes, Bootlegs, & Mashups[/B][/COLOR]   -Todays biggest dance hits, remixes, bootlegs & mashups!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/180/logos/90dc5bff-51ac-4766-bc41-17b3557fc9a6.png',
                       'video': 'https://das-sa39.cdnstream1.com/5586_128',
                       'genre': 'MusicChoice'},              
                      ],					   
'Latin': [
			          {'name': '[COLOR aqua][B]Litt Latin[/B][/COLOR]   -DASH LATIN X features artists like J Balvin, Maluma, Shakira & more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/60/logos/367878a9-887b-4a07-8e9b-30e18da9510e.png',
                       'video': 'https://das-sa39.cdnstream1.com/5580_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Imperio - Corridos y Más[/B][/COLOR]   -Corridos y más...Imperio es El Patron de los Corridos!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/now_playing_artwork/IMPERIO/imperio_1080.png',
                       'video': 'https://das-sa39.cdnstream1.com/5574_128',
                       'genre': 'MusicChoice'},
					   					   
                      ],
'Rock': [
			          {'name': '[COLOR aqua][B]LITT Rock[/B][/COLOR]   -All your favorite rock music, all in one place!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/22/logos/1c529027-4444-48e2-9485-f7ad7927f712.png',
                       'video': 'https://das-sa39.cdnstream1.com/5591_128',
                       'genre': 'MusicChoice'},
					   
			          {'name': '[COLOR aqua][B]LITT Alt[/B][/COLOR]   -Catch top alternative hits by the bands you love!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/37/logos/87118530-4b2b-45a9-8887-788263aafc78.png',
                       'video': 'https://das-sa39.cdnstream1.com/5561_128',
                       'genre': 'MusicChoice'},	

			          {'name': '[COLOR aqua][B]LITT Classics[/B][/COLOR]   -The head-bangin’, hair-slingin’ rock & roll you used to listen to in your mom’s basement. Hopefully you’re not still living there.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/40/logos/b9f5976b-5775-4286-8a08-3ba7f88eb707.png',
                       'video': 'https://das-sa39.cdnstream1.com/5602_128',
                       'genre': 'MusicChoice'},
				  
                      {'name': '[COLOR aqua][B]Grunge - 90s Rock[/B][/COLOR]   -Put on your lumberjack shirt, tattered boots & long underwear, and enjoy some raw, American-made rock & roll.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/164/logos/0e64637e-7b29-477e-883b-ae7408d275ee.png',
                       'video': 'https://das-sa39.cdnstream1.com/5570_128',
                       'genre': 'MusicChoice'},					   					   
					   						   
                      ],
'Decades': [
			          {'name': '[COLOR aqua][B]LITT "The Tens"[/B][/COLOR]   -For the generation born with a smart phone in their hand. So many hits-we could barely fit it all in!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/234/logos/0712c68a-17b8-45a4-9c54-631e09988b78.png',
                       'video': 'https://das-sa39.cdnstream1.com/5555_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]LITT Y2K Hits[/B][/COLOR]   -Enjoy it in your flying car, or your bubble house on the moon. Oh wait-none of that happened. We just got velour tracksuits.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/19/logos/1493e061-9cca-41fa-8949-1e713289de76.png',
                       'video': 'https://das-sa39.cdnstream1.com/5604_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]90s[/B][/COLOR]   -This is the music you did all that roller-blading to…and still have the scarred knees to prove it.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/62/logos/bf4e171f-9844-45a6-8a4e-41b4f2a1c1ab.png',
                       'video': 'https://das-sa39.cdnstream1.com/5560_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]80s[/B][/COLOR]   -From ET to MTV, from Reaganomics to Hooked on Phonics, we’re sending you back!...to the 80s',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/31/logos/6047ce0f-e66e-4fd5-85bc-371931d229e6.png',
                       'video': 'https://das-sa39.cdnstream1.com/5559_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]70s[/B][/COLOR]   -A DY-NO-MITE! collection of groovy 70s classics. Who loves ya, baby?',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/70/logos/44d12425-56d7-4dfd-ba09-32b84d733f99.png',
                       'video': 'https://das-sa39.cdnstream1.com/5558_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]60s[/B][/COLOR]   -A decade of great change... a decade of great music.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/2/logos/2ef5a3b9-01cb-454f-8208-eb694543e420.png',
                       'video': 'https://das-sa39.cdnstream1.com/5557_128',
                       'genre': 'MusicChoice'},					   
					   
                      {'name': '[COLOR aqua][B]Disco Fever[/B][/COLOR]   -Celebrating the Disco Fever era!',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/DiscoFever.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5566_128',
                       'genre': 'MusicChoice'},
                  
                      {'name': '[COLOR aqua][B]Yacht Rock Radio[/B][/COLOR]   -Smooth sounds of the late 70s and early 80s. Classic Yacht that softly rocks.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/69/logos/2ad0743a-6bee-4029-a684-736690cb7708.png',
                       'video': 'https://das-sa39.cdnstream1.com/5605_128',
                       'genre': 'MusicChoice'},
					   				   
                      ],
'R & B': [
			          {'name': '[COLOR aqua][B]LITT R&B[/B][/COLOR]   -Listen to your favorite artists such as Beyonce, Kehlani, The Weeknd and more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/50/logos/5c6f0370-4ec9-44a9-9bdb-aa86f5d0188c.png',
                       'video': 'https://das-sa39.cdnstream1.com/5589_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Snoop Doggs Cadillacc Music - Soul, R&B, Funk, & Hip-Hop[/B][/COLOR]   -Presented by Snoop Dogg aka DJ Snoopadelic, this is Cadillacc Music.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/107/logos/dc003550-a8af-433a-a93c-f202166c2cba.png',
                       'video': 'https://littlive-live-a.cdnstream1.com/5595_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Boomerang 90s R&B  -Curated by Shawn Stockman of BoyzIIMen, feat. his show “The Bridge”',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/53/logos/be546344-8468-4ab3-9b5e-713d43aabea7.png',
                       'video': 'https://das-sa39.cdnstream1.com/5562_128',
                       'genre': 'MusicChoice'},					   				  
					   
                      {'name': '[COLOR aqua][B]Pure Soul - Powered by Isaac Hayes[/B][/COLOR]   -Sit back and let Isaac Hayes guide your journey to soulful bliss.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/PureSoulPoweredByIsaacHayes.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5588_128',
                       'genre': 'MusicChoice'},
                      
                      {'name': '[COLOR aqua][B]Super Freak - Powered by Rick James[/B][/COLOR]   -Give it to me baby, Gimme that funk, that sweet, that funky stuff.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/icon_logos/SUPERFREAK/superfreak_nowplaying_1080.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5597_128',
                       'genre': 'MusicChoice'},                      
                      ],					   

'Jazz': [
			          {'name': '[COLOR aqua][B]Lofi - Chill & Instrumental Jazz Beats[/B][/COLOR]   -Lofi beats for your body, mind, & soul.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/57/logos/370c1db2-d4d6-4d6c-a8e7-57c52b954c96.png',
                       'video': 'https://das-sa39.cdnstream1.com/5582_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]Smooth Jazz[/B][/COLOR]   -This ain’t your father’s jazz music. Unless you’re Kenny G’s kid.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/229/logos/05ca76f4-8204-466d-87ce-e4677d3585ba.png',
                       'video': 'https://das-sa39.cdnstream1.com/5594_128',
                       'genre': 'MusicChoice'},
                      ],
'Country': [
			          {'name': '[COLOR aqua][B]LITT Country[/B][/COLOR]   -The home for country musics biggest hits and upcoming superstars.',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/43/logos/21b831cb-db8a-422f-a425-67687882c08e.png',
                       'video': 'https://das-sa39.cdnstream1.com/5563_128',
                       'genre': 'MusicChoice'},
					   
                      {'name': '[COLOR aqua][B]The Ranch - Classic Country[/B][/COLOR]   -This is country music, before they made it into pop. It don’t mean a thang, if it ain’t got that twang.',
                       'thumb': 'https://s3.amazonaws.com/dashradio-files/now_playing_artwork/TheRanch.jpg',
                       'video': 'https://das-sa39.cdnstream1.com/5601_128',
                       'genre': 'MusicChoice'},                      
                      ],
'Faith And Gospel': [
			          {'name': '[COLOR aqua][B]Rhythm & Praise - Gospel R&B[/B][/COLOR]   -Rhythm & Praise, Gospels R&B! Curated by Those Baxters & Emcee N.I.C.E',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/200/logos/f11c0749-7e90-48cc-8abb-89043fe7ed8d.png',
                       'video': 'https://das-sa39.cdnstream1.com/5590_128',
                       'genre': 'MusicChoice'},
                      ],					   
'World': [
					   
                      {'name': '[COLOR aqua][B]Island Fever - Where Caribbean Music Lives[/B][/COLOR]   -Hits from across the Islands! Reggae, Dancehall, Soca, Calypso, and more!',
                       'thumb': 'https://dashradio-files.s3.amazonaws.com/development/icon_logos/215/logos/d49bcaf7-03c7-45bf-8780-c4d284384e3a.png',
                       'video': 'https://das-sa39.cdnstream1.com/5578_128',
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
