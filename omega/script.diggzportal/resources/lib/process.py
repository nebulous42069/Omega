from ast import literal_eval
import os, shutil
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from resources.lib import Utils
from resources.lib.WindowManager import wm
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short
from resources.lib.trakt import icon_path
from resources.autocomplete import AutoCompletion
from resources.autocomplete import AutoCompletion_plugin
from urllib.parse import quote, urlencode, quote_plus, unquote, unquote_plus
import time

from inspect import currentframe, getframeinfo
#Utils.tools_log( (str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))) )

def start_info_actions(infos, params):
	addonID = addon_ID()
	addonID_short = addon_ID_short()

	wm.custom_filter = params.get('meta_filter')
	Utils.tools_log(Utils.db_con)
	if wm.custom_filter:
		wm.custom_filter = literal_eval(unquote(wm.custom_filter))

	keep_stack = params.get('keep_stack',False)

	if 'imdbid' in params and 'imdb_id' not in params:
		params['imdb_id'] = params['imdbid']
	for info in infos:
		Utils.show_busy()
		data = [], ''

		if info == 'mouse_touch_support':
			Utils.hide_busy()
			from resources.lib.appearance import choose_touch_support
			choose_touch_support()
			return

		if info=='simkl_manager':
			Utils.hide_busy()
			from resources.lib import accounts
			accounts.authorize_browser('simkl',managed=True)
			return

		if info=='account_manager':
			Utils.hide_busy()
			from resources.lib import accounts
			accounts.authorize_browser(params.get('source',''),managed=True)
			return

		if info in ('account_login','account_logout','account_history'):
			from resources.lib import accounts, trakt_api
			Utils.hide_busy()
			source=params.get('source','')
			try:
				if info=='account_history': accounts.history(force=True)
				elif source in ('tmdb','trakt','mdblist','simkl'):
					if info=='account_logout':
						accounts.confirm_disconnect(source)
					elif params.get('browser_auth')=='true': accounts.authorize_browser(source)
					elif source=='trakt': trakt_api.login_trakt()
					else: accounts.login(source)
			except Exception: xbmcgui.Dialog().notification('Accounts','Account operation failed. Check credentials and try again.',xbmcgui.NOTIFICATION_ERROR)
			return

		if info=='account_browse':
			from resources.lib import account_catalog as cat
			Utils.hide_busy()
			source=params.get('source'); kind=params.get('kind'); category=unquote_plus(params.get('category') or ''); label=unquote_plus(params.get('label','Lists'))
			if source not in ('tmdb','mdblist','simkl') or kind not in ('movie','tv'): return
			try: leaf=cat.choose(source,kind,category,label,value=unquote_plus(params.get('value') or ''))
			except Exception: xbmcgui.Dialog().notification(source.upper(),'Unable to retrieve lists',xbmcgui.NOTIFICATION_ERROR); return
			if not leaf: return
			category,value,label=leaf
			wm.window_stack_empty(); wm.page=1
			return wm.open_video_list(media_type=kind,mode='trakt_catalog',filter_label=label,search_str={'source':source,'category':category,'value':value},listitems=[])

		if info == 'trakt_refresh':
			from resources.lib.trakt_api import refresh_token
			refresh_token()
			Utils.hide_busy()
			return

		if info == 'login_trakt':
			from resources.lib.trakt_api import login_trakt
			login_trakt()
			Utils.hide_busy()
			return

		if info == 'trakt_cleanup':
			Utils.tools_log('trakt_watched_tv_movies_cleanup')
			from resources.lib.trakt import trakt_watched_tv_movies_cleanup
			trakt_watched_tv_movies_cleanup()

		if info == 'trakt_uncollected1':
			Utils.tools_log('trakt_uncollected1')
			from resources.lib.trakt import trakt_uncollected_watched_movies
			trakt_list = trakt_uncollected_watched_movies()
			for sit in trakt_list:
				imdb = sit['movie']['ids']['imdb']
				year = sit['movie']['year']
				title = sit['movie']['title']
				Utils.tools_log([title, year, imdb])
			Utils.hide_busy()
			return

		if info == 'trakt_uncollected':
			Utils.tools_log('trakt_uncollected')
			from resources.lib.trakt import trakt_watched_movies
			from resources.lib.trakt import trakt_collection_movies
			Utils.tools_log(trakt_watched_movies())
			Utils.tools_log(trakt_collection_movies())
			Utils.hide_busy()
			return





		if info == 'get_imdb_language':
			from resources.lib import TheMovieDB
			languages = TheMovieDB.get_imdb_language('tt8421350')
			Utils.tools_log(languages)

		if info == 'get_trakt_playback':
			from resources.lib import TheMovieDB
			trakt_type = params.get('trakt_type')
			TheMovieDB.get_trakt_playback(trakt_type)
			return

		if info == 'youtube':
			wm.window_stack_empty()
			return wm.open_youtube_list(search_str=params.get('search_str', ''))
		if info == 'youtubevideo':
			from resources.lib.YouTube import play_video
			Utils.hide_busy()
			return play_video(params.get('id'))
		if info in ('playtrailer', 'playtvtrailer', 'tvtrailer'):
			from resources.lib import TheMovieDB
			kind = 'movie' if info == 'playtrailer' else 'tv'
			item_id = params.get('id')
			if not item_id and kind == 'movie' and params.get('imdb_id'):
				item_id = TheMovieDB.get_movie_tmdb_id(imdb_id=params['imdb_id'])
			elif not item_id and kind == 'tv' and params.get('tvdb_id'):
				item_id = TheMovieDB.get_show_tmdb_id(params['tvdb_id'])
			Utils.hide_busy()
			return TheMovieDB.play_trailer(kind, item_id)

		if info == 'tmdb_search':
			kind = params.get('kind')
			labels = {'movie':'Movies', 'tv':'TV Shows', 'person':'People'}
			Utils.hide_busy()
			if kind not in labels: return
			text = xbmcgui.Dialog().input(heading='Search '+labels[kind], type=xbmcgui.INPUT_ALPHANUM).strip()
			if not text: return
			wm.window_stack_empty()
			wm.page = 1
			return wm.open_video_list(media_type=kind, mode='tmdb_ranked', filter_label=labels[kind]+': '+text, search_str={'category':'search','value':text}, listitems=[])

		if info == 'trakt_browse':
			from resources.lib import trakt_catalog as cat
			kind=params.get('kind','movie')
			category=unquote_plus(params.get('category','popular'))
			value=unquote_plus(params.get('value',''))
			label=unquote_plus(params.get('label','Trakt'))
			try:
				if kind not in ('movie','tv','person'):
					Utils.hide_busy()
					return
				Utils.hide_busy()
				if kind=='person':
					text=xbmcgui.Dialog().input('Search Trakt People').strip()
					if not text: return
					leaf=('search',text,label+': '+text)
				else: leaf=cat.choose(kind,category,value,label)
				if not leaf: return
				category,value,label=leaf
			except Exception as exc:
				xbmcgui.Dialog().notification('Trakt',str(exc)[:160],xbmcgui.NOTIFICATION_ERROR)
				return
			wm.window_stack_empty()
			wm.page=1
			return wm.open_video_list(media_type=kind,mode='trakt_catalog',filter_label=label,search_str={'category':category,'value':value},listitems=[])

		if info == 'tmdb_browse':
			from resources.lib import tmdb_catalog as catalog
			kind = params.get('kind','movie')
			category = unquote_plus(params.get('category','all'))
			value = unquote_plus(params.get('value',''))
			label = unquote_plus(params.get('label','TMDb'))
			if kind not in ('movie','tv','person'): return
			wm.window_stack_empty()
			wm.page = 1
			if kind == 'person' or category in catalog.RANKED:
				return wm.open_video_list(media_type=kind, mode='tmdb_ranked', filter_label=label, search_str={'category':category,'value':value}, listitems=[])
			return wm.open_video_list(media_type=kind, mode='filter', list_id='tmdb_newest', filters=catalog.filters(kind,category,value,label), filter_label=label, listitems=[])

		if info == 'popularmovies':
			from resources.lib import TheMovieDB
			tmdb_var = 'popular'
			filter_label = 'Popular Movies'
			media_type = 'movie'
			try:
				script = str(params['script'])
			except:
				script = 'True'
			if script == 'False':
				return TheMovieDB.get_tmdb_movies(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_movies(tmdb_var), listitems=[])

		elif info == 'topratedmovies':
			from resources.lib import TheMovieDB
			tmdb_var = 'top_rated'
			filter_label = 'Top Rated Movies'
			media_type = 'movie'
			try:
				script = str(params['script'])
			except:
				Utils.hide_busy()
				script = 'False'
			if script == 'False':
				return TheMovieDB.get_tmdb_movies(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_movies(tmdb_var), listitems=[])

		elif info == 'incinemamovies':
			from resources.lib import TheMovieDB
			tmdb_var = 'now_playing'
			filter_label = 'In Theaters Movies'
			media_type = 'movie'
			try:
				script = str(params['script'])
			except:
				script = 'True'
			if script == 'False':
				return TheMovieDB.get_tmdb_movies(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_movies(tmdb_var), listitems=[])

		elif info == 'upcomingmovies':
			from resources.lib import TheMovieDB
			tmdb_var = 'upcoming'
			filter_label = 'Upcoming Movies'
			media_type = 'movie'
			try:
				script = str(params['script'])
			except:
				script = 'True'
			if script == 'False':
				return TheMovieDB.get_tmdb_movies(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_movies(tmdb_var), listitems=[])

		elif info == 'populartvshows':
			from resources.lib import TheMovieDB
			tmdb_var = 'popular'
			filter_label = 'Popular TV Shows'
			media_type = 'tv'
			try:
				script = str(params['script'])
			except:
				script = 'True'
			if script == 'False':
				return TheMovieDB.get_tmdb_shows(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_shows(tmdb_var), listitems=[])


		elif info == 'topratedtvshows':
			from resources.lib import TheMovieDB
			tmdb_var = 'top_rated'
			filter_label = 'Top Rated TV Shows'
			media_type = 'tv'
			try:
				script = str(params['script'])
			except:
				Utils.hide_busy()
				script = 'False'
			if script == 'False':
				return TheMovieDB.get_tmdb_shows(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_shows(tmdb_var), listitems=[])

		elif info == 'onairtvshows':
			from resources.lib import TheMovieDB
			tmdb_var = 'on_the_air'
			filter_label = 'Currently Airing TV Shows'
			media_type = 'tv'
			try:
				script = str(params['script'])
			except:
				script = 'True'
			if script == 'False':
				return TheMovieDB.get_tmdb_shows(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_shows(tmdb_var), listitems=[])

		elif info == 'airingtodaytvshows':
			from resources.lib import TheMovieDB
			tmdb_var = 'airing_today'
			filter_label = 'Airing Today TV Shows'
			media_type = 'tv'
			try:
				script = str(params['script'])
			except:
				script = 'True'
			if script == 'False':
				return TheMovieDB.get_tmdb_shows(tmdb_var)
			wm.window_stack_empty()
			return wm.open_video_list(media_type=media_type, mode='list_items', filter_label=filter_label, search_str=TheMovieDB.get_tmdb_shows(tmdb_var), listitems=[])

		elif info == 'allmovies':
			wm.window_stack_empty()
			wm.open_video_list(media_type='movie',mode='filter')

		elif info == 'alltvshows':
			wm.window_stack_empty()
			wm.open_video_list(media_type='tv',mode='filter')

		elif info == 'search_menu':
			search_str = xbmcgui.Dialog().input(heading='Enter search string', type=xbmcgui.INPUT_ALPHANUM)
			wm.window_stack_empty()
			return wm.open_video_list(search_str=search_str, mode='search')



		elif info == 'ep_movie_progress':
			search_str = 'Trakt Episodes/Movies in progress'
			wm.window_stack_empty()
			return wm.open_video_list(search_str=search_str, mode='filter')



		elif info == 'reopen_window':
			reopen_window()


		elif info == 'autocomplete' or info == 'selectautocomplete':
			items = AutoCompletion_plugin.start_info_actions(infos, params)
			return items

		elif info == 'pop_stack':
			wm.pop_stack()
			return


		elif info == 'open_settings':
			xbmc.executebuiltin('Addon.OpenSettings(%s)' % addon_ID())
			Utils.hide_busy()

		elif info == 'trakt_watched' or info == 'trakt_coll' or info == 'trakt_list' or info == 'trakt_trend' or info == 'trakt_popular' or info == 'trakt_progress' or info == 'trakt_unwatched':
			#kodi-send --action='RunPlugin(plugin://'+str(addon_ID())+'/?info=trakt_watched&trakt_type=movie&script=True)'
			#kodi-send --action='RunPlugin(plugin://'+str(addon_ID())+'/?info=trakt_watched&trakt_type=tv&script=True)'
			#kodi-send --action='RunPlugin(plugin://'+str(addon_ID())+'/?info=trakt_coll&trakt_type=movie&script=True)'
			#kodi-send --action='RunPlugin(plugin://'+str(addon_ID())+'/?info=trakt_coll&trakt_type=tv&script=True)'
			trakt_type = str(params['trakt_type'])
			limit = params.get('limit', 0)
			Utils.show_busy()
			try: trakt_token = xbmcaddon.Addon(addon_ID()).getSetting('trakt_token')
			except: trakt_token = None
			if not trakt_token:
				Utils.hide_busy()
				return
			try:
				trakt_script = str(params['script'])
			except:
				trakt_script = 'True'
			if trakt_script == 'False' and (info == 'trakt_watched' or info == 'trakt_coll' or info == 'trakt_trend' or info == 'trakt_popular'  or info == 'trakt_progress' or info == 'trakt_unwatched'):
				from resources.lib import TheMovieDB
				return TheMovieDB.get_trakt(trakt_type=trakt_type,info=info,limit=limit)
			else:
				if info == 'trakt_watched' and trakt_type == 'movie':
					from resources.lib.trakt import trakt_watched_movies
					movies = trakt_watched_movies()
					trakt_label = 'Trakt Watched Movies'
				elif info == 'trakt_watched' and trakt_type == 'tv':
					from resources.lib.trakt import trakt_watched_tv_shows
					movies = trakt_watched_tv_shows()
					trakt_label = 'Trakt Watched Shows'

				elif info == 'trakt_unwatched' and trakt_type == 'tv':
					from resources.lib.trakt import trakt_unwatched_tv_shows
					movies = trakt_unwatched_tv_shows()
					trakt_label = 'Trakt Unwatched Shows'

				elif info == 'trakt_coll' and trakt_type == 'movie':
					from resources.lib.trakt import trakt_collection_movies
					movies = trakt_collection_movies()
					trakt_label = 'Trakt Collection Movies'
				elif info == 'trakt_coll' and trakt_type == 'tv':
					from resources.lib.trakt import trakt_collection_shows
					movies = trakt_collection_shows()
					trakt_label = 'Trakt Collection Shows'

				elif info == 'trakt_trend' and trakt_type == 'tv':
					from resources.lib.trakt import trakt_trending_shows
					movies = trakt_trending_shows()
					trakt_label = 'Trakt Trending Shows'
				elif info == 'trakt_trend' and trakt_type == 'movie':
					from resources.lib.trakt import trakt_trending_movies
					movies = trakt_trending_movies()
					trakt_label = 'Trakt Trending Movies'

				elif info == 'trakt_popular' and trakt_type == 'tv':
					from resources.lib.trakt import trakt_popular_shows
					movies = trakt_popular_shows()
					trakt_label = 'Trakt Trending Shows'
				elif info == 'trakt_popular' and trakt_type == 'movie':
					from resources.lib.trakt import trakt_popular_movies
					movies = trakt_popular_movies()
					trakt_label = 'Trakt Trending Movies'

				elif info == 'trakt_progress' and trakt_type == 'tv':
					from resources.lib.trakt import trakt_watched_tv_shows_progress
					movies = trakt_watched_tv_shows_progress()
					trakt_label = 'Trakt Shows Progress'
				elif info == 'trakt_list':
					from resources.lib.trakt import trakt_lists
					from resources.lib.TheMovieDB import get_trakt_lists
					trakt_type = str(params['trakt_type'])
					trakt_label = str(params['trakt_list_name'])
					trakt_user_id = str(params['user_id'])
					takt_list_slug = str(params['list_slug'])
					trakt_sort_by = str(params['trakt_sort_by'])
					trakt_sort_order = str(params['trakt_sort_order'])
					if trakt_script == 'False':
						return get_trakt_lists(list_name=trakt_label,user_id=trakt_user_id,list_slug=takt_list_slug,sort_by=trakt_sort_by,sort_order=trakt_sort_order,limit=limit)
					movies = trakt_lists(list_name=trakt_label,user_id=trakt_user_id,list_slug=takt_list_slug,sort_by=trakt_sort_by,sort_order=trakt_sort_order,limit=limit)
				if keep_stack == None or keep_stack == False:
					wm.window_stack_empty()
				return wm.open_video_list(mode='trakt', listitems=[], search_str=movies, media_type=trakt_type, filter_label=trakt_label)

		elif info == 'search_string':
			search_str = params['str']
			wm.window_stack_empty()
			return wm.open_video_list(search_str=search_str, mode='search')

		elif info == 'search_person':
			from resources.lib.TheMovieDB import get_person_info
			from resources.lib.TheMovieDB import get_person
			search_str = params['person']
			if params.get('person'):
				person = get_person_info(person_label=params['person'])
				if person and person.get('id'):
					movies = get_person(person['id'])
					newlist = sorted(movies, key=lambda k: k['Popularity'], reverse=True)
					movies = {}
					movies['cast_crew'] = []
					movies['person'] = params['person']
					for i in newlist:
						try:
							if str("'id': " + str(i['id'])) not in str(movies['cast_crew']) and i['poster'] != None:
								if str("'id': '" + str(i['id']) + "'") not in str(movies['cast_crew']):
									movies['cast_crew'].append(i)
						except KeyError:
							pass
					newlist = None
					wm.window_stack_empty()
					return wm.open_video_list(mode='person', search_str=movies, listitems=movies['cast_crew'])

		elif info == 'studio':
			from resources.lib import TheMovieDB
			if 'id' in params and params['id']:
				wm.window_stack_empty()
				return wm.open_video_list(media_type='tv', mode='filter', listitems=TheMovieDB.get_company_data(params['id']))
			elif 'studio' in params and params['studio']:
				company_data = TheMovieDB.search_company(params['studio'])
				if company_data:
					return TheMovieDB.get_company_data(company_data[0]['id'])

		elif info == 'set':
			from resources.lib import TheMovieDB
			if params.get('setid'):
				set_data, _ = TheMovieDB.get_set_movies(params['setid'])
				return set_data

		elif info == 'keywords':
			from resources.lib import TheMovieDB
			movie_id = params.get('id', False)
			if not movie_id:
				movie_id = TheMovieDB.get_movie_tmdb_id(imdb_id=params.get('imdb_id'))
			if movie_id:
				return TheMovieDB.get_keywords(movie_id)

		elif info == 'directormovies':
			from resources.lib import TheMovieDB
			if params.get('director'):
				director_info = TheMovieDB.get_person_info(person_label=params['director'])
				if director_info and director_info.get('id'):
					movies = TheMovieDB.get_person_movies(director_info['id'])
					for item in movies:
						del item['credit_id']
					return Utils.merge_dict_lists(movies, key='department')

		elif info == 'writermovies':
			from resources.lib import TheMovieDB
			if params.get('writer') and not params['writer'].split(' / ')[0] == params.get('director', '').split(' / ')[0]:
				writer_info = TheMovieDB.get_person_info(person_label=params['writer'])
				if writer_info and writer_info.get('id'):
					movies = TheMovieDB.get_person_movies(writer_info['id'])
					for item in movies:
						del item['credit_id']                    
					return Utils.merge_dict_lists(movies, key='department')

		elif info == 'moviedbbrowser':
			if xbmcgui.Window(10000).getProperty('infodialogs.active'):
				return None
			xbmcgui.Window(10000).setProperty('infodialogs.active', 'true')
			search_str = params.get('id', '')
			if not search_str and params.get('search'):
				result = xbmcgui.Dialog().input(heading='Enter search string', type=xbmcgui.INPUT_ALPHANUM)
				if result and result > -1:
					search_str = result
				else:
					xbmcgui.Window(10000).clearProperty('infodialogs.active')
					return None
			xbmcgui.Window(10000).clearProperty('infodialogs.active')
			wm.window_stack_empty()
			return wm.open_video_list(search_str=search_str, mode='search')

		elif info == 'diamondinfodialog' or info == 'extendedinfodialog' or info == str(addon_ID_short()) + 'dialog':
			resolve_url(params.get('handle'))
			if xbmc.getCondVisibility('System.HasActiveModalDialog | System.HasModalDialog'):
				container_id = ''
			else:
				container_id = xbmc.getInfoLabel('Container(%s).ListItem.label' % xbmc.getInfoLabel('System.CurrentControlID'))
			db_type = xbmc.getInfoLabel('%sListItem.DBType' % container_id)
			if db_type == 'movie':
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info='+str(addon_ID_short())+',id=%s,imdb_id=%s,name=%s)' % (xbmc.getInfoLabel('ListItem.Property(id)'), xbmc.getInfoLabel('ListItem.IMDBNumber'), xbmc.getInfoLabel('ListItem.Title')))
			elif db_type == 'tvshow':
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=diggzportaltvinfo,id=%s,tvdb_id=%s,name=%s)' % (xbmc.getInfoLabel('ListItem.Property(id)'), xbmc.getInfoLabel('ListItem.Property(tvdb_id)'), xbmc.getInfoLabel('ListItem.Title')))
			elif db_type == 'season':
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=diggzportalseasoninfo,tvshow=%s,season=%s)' % (xbmc.getInfoLabel('ListItem.TVShowTitle'), xbmc.getInfoLabel('ListItem.Season')))
			elif db_type == 'episode':
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=diggzportalepisodeinfo,tvshow=%s,season=%s,episode=%s)' % (xbmc.getInfoLabel('ListItem.TVShowTitle'), xbmc.getInfoLabel('ListItem.Season'), xbmc.getInfoLabel('ListItem.Episode')))
			elif db_type in ['actor', 'director']:
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=diggzportalactorinfo,name=%s)' % xbmc.getInfoLabel('ListItem.Label'))
			else:
				Utils.notify('Error', 'Could not find valid content type')

		elif info == 'diamondinfo' or info == 'extendedinfo' or info == str(addon_ID_short()):
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).setProperty('infodialogs.active', 'true')
			if not params.get('id'):
				from resources.lib.TheMovieDB import get_movie_info

				if not params.get('id') and (not params.get('imdb_id') or not 'tt' in str(params.get('imdb_id'))):
					movie = get_movie_info(movie_label=params.get('name'), year=params.get('year'))
					if movie and movie.get('id'):
						params['id'] = movie.get('id')
					elif not movie:
						xbmcgui.Window(10000).clearProperty('infodialogs.active')
						Utils.hide_busy()
						return
			wm.window_stack_empty()
			wm.open_movie_info(movie_id=params.get('id'), imdb_id=params.get('imdb_id'), name=params.get('name'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')

		elif info in ('diggzportalactorinfo', 'extendedactorinfo'):
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).setProperty('infodialogs.active', 'true')
			wm.window_stack_empty()
			wm.open_actor_info(actor_id=params.get('id'), name=params.get('name'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')

		elif info in ('diggzportaltvinfo', 'extendedtvinfo'):
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).setProperty('infodialogs.active', 'true')
			if not params.get('id'):
				from resources.lib.TheMovieDB import get_tvshow_info

				if not params.get('id') and not params.get('tvdb_id') and (not params.get('imdb_id') or not 'tt' in str(params.get('imdb_id'))):
					tvshow = get_tvshow_info(tvshow_label=params.get('name'), year=params.get('year'))
					if tvshow and tvshow.get('id'):
						params['id'] = tvshow.get('id')
					elif not tvshow:
						xbmcgui.Window(10000).clearProperty('infodialogs.active')
						Utils.hide_busy()
						return
			wm.window_stack_empty()
			wm.open_tvshow_info(tmdb_id=params.get('id'), tvdb_id=params.get('tvdb_id'), imdb_id=params.get('imdb_id'), name=params.get('name'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')

		elif info in ('diggzportalseasoninfo', 'seasoninfo'):
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).setProperty('infodialogs.active', 'true')
			wm.window_stack_empty()
			wm.open_season_info(tvshow=params.get('tvshow'), tvshow_id=params.get('tvshow_id'), season=params.get('season'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')

		elif info in ('diggzportalepisodeinfo', 'extendedepisodeinfo'):
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).setProperty('infodialogs.active', 'true')
			wm.window_stack_empty()
			wm.open_episode_info(tvshow=params.get('tvshow'), tvshow_id=params.get('tvshow_id'), tvdb_id=params.get('tvdb_id'), season=params.get('season'), episode=params.get('episode'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')

		elif info == 'setfocus':
			resolve_url(params.get('handle'))
			xbmc.executebuiltin('SetFocus(22222)')

		elif info == 'slideshow':
			resolve_url(params.get('handle'))
			window_id = xbmcgui.getCurrentwindow_id()
			window = xbmcgui.Window(window_id)
			itemlist = window.getFocus()
			num_items = itemlist.getSelectedPosition()
			for i in range(0, num_items):
				Utils.notify(item.getProperty('Image'))

		elif info == 'deletecache':
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')
			xbmcgui.Window(10000).clearProperty(str(addon_ID_short())+'_running')
			Utils.clear_db(connection=Utils.db_con)
			if os.path.isdir(Utils.IMAGES_DATA_PATH):
				shutil.rmtree(Utils.IMAGES_DATA_PATH)
			Utils.notify('Cache deleted')

		elif info == 'auto_clean_cache':
			#info=auto_clean_cache&days=10
			days = params.get('days')
			resolve_url(params.get('handle'))
			xbmcgui.Window(10000).clearProperty('infodialogs.active')
			xbmcgui.Window(10000).clearProperty(str(addon_ID_short())+'_running')
			auto_clean_cache(days=days)
			Utils.notify('Cache deleted')


		else:
			Utils.hide_busy()

def resolve_url(handle):
	import xbmcplugin
	if handle:
		xbmcplugin.setResolvedUrl(handle=int(handle), succeeded=False, listitem=xbmcgui.ListItem())

def reopen_window():
	while xbmc.Player().isPlaying():
		xbmc.sleep(500)
	wm.window_stack_empty()
	return wm.open_video_list(search_str='', mode='reopen_window')

def auto_clean_cache(days=None):
	Utils.tools_log('STARTING===>auto_clean_cache')
	try:
		Utils.db_delete_expired(connection=Utils.db_con)
	except:
		xbmc.sleep(2*1000)
		try:
			Utils.tools_log('EXCEPTION__1_auto_clean_cache')
			Utils.db_delete_expired(connection=Utils.db_con)
		except:
			Utils.tools_log('EXCEPTION__2_auto_clean_cache')
			pass
	Utils.tools_log('FINISH===>auto_clean_cache')
	#Utils.db_con.close()

