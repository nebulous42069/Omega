import sys
from threading import Thread
from apis.trakt_api import trakt_get_hidden_items
from indexers.metadata import tvshow_meta, rpdb_get
from caches.watched_cache import get_watched_info_tv, get_watched_status_tvshow
from modules import kodi_utils, settings
#from modules.utils import manual_function_import, get_datetime, make_thread_list_enumerate
from modules.utils import manual_function_import, get_datetime, TaskPool
# logger = kodi_utils.logger

meta_function, get_datetime_function = tvshow_meta, get_datetime
get_watched_function, get_watched_info_function = get_watched_status_tvshow, get_watched_info_tv
KODI_VERSION, make_cast_list = kodi_utils.get_kodi_version(), kodi_utils.make_cast_list
string, ls, tp, get_infolabel = str, kodi_utils.local_string, kodi_utils.translate_path, kodi_utils.get_infolabel
build_url, remove_meta_keys, dict_removals = kodi_utils.build_url, kodi_utils.remove_meta_keys, kodi_utils.tvshow_dict_removals
run_plugin, container_refresh, container_update = 'RunPlugin(%s)', 'Container.Refresh(%s)', 'Container.Update(%s)'
item_jump, item_next = tp('special://home/addons/plugin.video.pov/resources/media/item_jump.png'), tp('special://home/addons/plugin.video.pov/resources/media/item_next.png')
poster_empty, fanart_empty = tp('special://home/addons/plugin.video.pov/resources/media/box_office.png'), tp('special://home/addons/plugin.video.pov/fanart.png')
watched_str, unwatched_str, traktmanager_str, tmdbmanager_str, mdbmanager_str = ls(32642), ls(32643), ls(32198), '[B]TMDB Lists Manager[/B]', ls(32200)
favmanager_str, extras_str, options_str, recomm_str = ls(32197), ls(32645), ls(32646), '[B]%s...[/B]' % ls(32503)
random_str, exit_str, browse_str = ls(32611), ls(32650), ls(32652)
nextpage_str, switchjump_str, jumpto_str = ls(32799), ls(32784), ls(32964)

class TVShows:
	def __init__(self, params):
		self.params = params
		self.id_type, self.list, self.action, self.exit_list_params = (
			self.params.get('id_type', 'tmdb_id'),
			self.params.get('list', []),
			self.params.get('action', None),
			self.params.get('action', None)
		)
		self.items, self.new_page, self.total_pages, self.is_widget = [], {}, None, 'unchecked'
		self.append = self.items.append
		self.current_date = get_datetime_function()
		self.meta_user_info = settings.metadata_user_info()
		self.watched_indicators = settings.watched_indicators()
		self.watched_info = get_watched_info_function(self.watched_indicators)
		self.all_episodes = settings.default_all_episodes()
		self.include_year_in_title = settings.include_year_in_title('tvshow')
		self.open_extras = settings.extras_open_action('tvshow')
		self.cm_sort = settings.context_menu_sort()
		self.is_folder = False if self.open_extras else True
		self.rpdb_enabled = self.meta_user_info['extra_rpdb_enabled_series']
		self.fanart_enabled = self.meta_user_info['extra_fanart_enabled']
		if self.is_widget == 'unchecked': self.is_widget = kodi_utils.external_browse()
		self.widget_hide_watched = self.is_widget and self.meta_user_info['widget_hide_watched']
		if not self.exit_list_params: self.exit_list_params = get_infolabel('Container.FolderPath')
		self.watched_title = 'Trakt' if self.watched_indicators == 1 else 'POV'
		self.poster_main, self.poster_backup, self.fanart_main, self.fanart_backup = settings.get_art_provider()

	def build_tvshow_content(self, _position, _id):
		try:
			meta = meta_function(self.id_type, _id, self.meta_user_info, self.current_date)
			meta_get = meta.get
			if not meta or meta_get('blank_entry', False): return
			playcount, overlay, total_watched, total_unwatched = get_watched_function(self.watched_info, string(meta['tmdb_id']), meta.get('total_aired_eps'))
			meta.update({'playcount': playcount, 'overlay': overlay})
			sort = _id.get('sort', _position) if self.id_type == 'trakt_dict' else _position
			props = {'pov_sort_order': string(sort)}
			cm = []
			cm_append = cm.append
			rootname, title, year, trailer = meta_get('rootname'), meta_get('title'), meta_get('year'), meta_get('trailer')
			tmdb_id, tvdb_id, imdb_id = meta_get('tmdb_id'), meta_get('tvdb_id'), meta_get('imdb_id')
			total_seasons, total_aired_eps = meta_get('total_seasons'), meta_get('total_aired_eps')
			poster = meta_get(self.poster_main) or meta_get(self.poster_backup) or poster_empty
			fanart = meta_get(self.fanart_main) or meta_get(self.fanart_backup) or fanart_empty
			clearlogo = meta_get('clearlogo') or meta_get('tmdblogo') or ''
			if self.rpdb_enabled:
				rpdb_data = rpdb_get('series', imdb_id or str(tmdb_id), self.meta_user_info['rpdb_api_key'])
				poster = rpdb_data.get('rpdb') or poster
			if self.fanart_enabled: banner, clearart, landscape = meta_get('banner'), meta_get('clearart'), meta_get('landscape')
			else: banner, clearart, landscape = '', '', ''
			if self.all_episodes:
				if self.all_episodes == 1 and total_seasons > 1: url_params = build_url({'mode': 'build_season_list', 'tmdb_id': tmdb_id})
				else: url_params = build_url({'mode': 'build_episode_list', 'tmdb_id': tmdb_id, 'season': 'all'})
			else: url_params = build_url({'mode': 'build_season_list', 'tmdb_id': tmdb_id})
			extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow', 'is_widget': self.is_widget})
			options_params = build_url({'mode': 'options_menu_choice', 'content': 'tvshow', 'tmdb_id': tmdb_id, 'is_widget': self.is_widget})
			recommended_params = build_url({'mode': 'build_tvshow_list', 'action': 'tmdb_tv_recommendations', 'tmdb_id': tmdb_id})
			trakt_manager_params = build_url({'mode': 'trakt_manager_choice', 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id, 'media_type': 'tvshow'})
			tmdb_manager_params = build_url({'mode': 'tmdb_manager_choice', 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id, 'media_type': 'tvshow'})
			mdb_manager_params = build_url({'mode': 'mdb_manager_choice', 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id, 'media_type': 'tvshow'})
			fav_manager_params = build_url({'mode': 'favourites_choice', 'media_type': 'tvshow', 'tmdb_id': tmdb_id, 'title': title})
			cm_append((self.cm_sort['options'], options_str, run_plugin % options_params))
			if self.open_extras:
				cm_append((self.cm_sort['extras'], browse_str, container_update % url_params))
				url_params = extras_params
			else:
				cm_append((self.cm_sort['extras'], extras_str, run_plugin % extras_params))
			cm_append((self.cm_sort['trakt'], traktmanager_str, run_plugin % trakt_manager_params))
			cm_append((self.cm_sort['tmdblist'], tmdbmanager_str, run_plugin % tmdb_manager_params))
			cm_append((self.cm_sort['mdblist'], mdbmanager_str, run_plugin % mdb_manager_params))
			cm_append((self.cm_sort['favourites'], favmanager_str, run_plugin % fav_manager_params))
			if not playcount:
				watched_params = build_url({'mode': 'mark_as_watched_unwatched_tvshow', 'action': 'mark_as_watched', 'title': title, 'year': year, 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id})
				cm_append((self.cm_sort['mark'], watched_str % self.watched_title, run_plugin % watched_params))
			elif self.widget_hide_watched: return
			if total_watched:
				unwatched_params = build_url({'mode': 'mark_as_watched_unwatched_tvshow', 'action': 'mark_as_unwatched', 'title': title, 'year': year, 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': tvdb_id})
				cm_append((self.cm_sort['mark'], unwatched_str % self.watched_title, run_plugin % unwatched_params))
			cm_append((self.cm_sort['exit'], exit_str, container_refresh % self.exit_list_params))
			cm.sort(key=lambda k: k[0])
			cm = [(i[1], i[2]) for i in cm if i[0]]
			props['unwatchedepisodes'] = string(total_unwatched)
			props['totalepisodes'] = string(total_aired_eps)
			props['totalseasons'] = string(total_seasons)
			listitem = kodi_utils.make_listitem()
			listitem.addContextMenuItems(cm)
			listitem.setProperties(props)
			listitem.setLabel(rootname if self.include_year_in_title else title)
#			listitem.setContentLookup(False)
			listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'banner': banner, 'clearart': clearart, 'clearlogo': clearlogo, 'landscape': landscape,
							'tvshow.poster': poster, 'tvshow.clearart': clearart, 'tvshow.clearlogo': clearlogo, 'tvshow.landscape': landscape, 'tvshow.banner': banner})
			if KODI_VERSION < 20:
				listitem.setCast(meta_get('cast', []))
				listitem.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id), 'tvdb': string(tvdb_id)})
				listitem.setInfo('video', remove_meta_keys(meta, dict_removals))
				listitem.setProperty('watchedepisodes', string(total_watched))
			else:
				if total_watched > 0: listitem.setProperty('watchedepisodes', string(total_watched))
				if total_aired_eps > 0: listitem.setProperty('watchedprogress', string(int(total_watched / total_aired_eps * 100)))
				videoinfo = listitem.getVideoInfoTag(offscreen=True)
				videoinfo.setCast(make_cast_list(meta_get('cast', [])))
				videoinfo.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id), 'tvdb': string(tvdb_id)})
				videoinfo.setCountries(meta_get('country'))
				videoinfo.setDirectors(meta_get('director').split(', '))
				videoinfo.setDuration(meta_get('duration'))
				videoinfo.setGenres(meta_get('genre').split(', '))
				videoinfo.setIMDBNumber(imdb_id)
				videoinfo.setMediaType('tvshow')
				videoinfo.setMpaa(meta_get('mpaa'))
				videoinfo.setPlaycount(playcount)
				videoinfo.setPlot(meta_get('plot'))
				videoinfo.setPremiered(meta_get('premiered'))
				videoinfo.setRating(meta_get('rating'))
				videoinfo.setStudios((meta_get('studio'),))
				videoinfo.setTagLine(meta_get('tagline'))
				videoinfo.setTitle(rootname if self.include_year_in_title else title)
				videoinfo.setTrailer(meta_get('trailer'))
				videoinfo.setTvShowStatus(meta_get('status'))
				videoinfo.setTvShowTitle(title)
				videoinfo.setVotes(meta_get('votes'))
				videoinfo.setWriters(meta_get('writer').split(', '))
				videoinfo.setYear(int(year))
			self.append((url_params, listitem, self.is_folder))
		except: pass

	def worker(self):
#		threads = list(make_thread_list_enumerate(self.build_tvshow_content, self.list, Thread))
		threads = TaskPool().tasks_enumerate(self.build_tvshow_content, self.list, Thread)
		for i in threads: i.join()
		self.items.sort(key=lambda k: int(k[1].getProperty('pov_sort_order')))
		return self.items

class Indexer(TVShows):
	tmdb_main = ('tmdb_tv_popular', 'tmdb_tv_premieres', 'tmdb_tv_airing_today', 'tmdb_tv_on_the_air', 'tmdb_tv_upcoming')
	tmdb_personal = ('tmdb_watchlist', 'tmdb_favorite', 'tmdb_recommendations')
	tmdb_special_key_dict = {'tmdb_tv_languages': 'language', 'tmdb_tv_networks': 'network_id', 'tmdb_tv_year': 'year'}
	trakt_main = ('trakt_tv_trending', 'trakt_tv_trending_recent', 'trakt_tv_most_watched', 'trakt_tv_most_favorited')
	trakt_personal = ('trakt_collection', 'trakt_watchlist', 'trakt_collection_lists', 'trakt_droplist')
	mdblist_personal = ('mdblist_watchlist',)
	imdb_personal = ('imdb_watchlist', 'imdb_user_list_contents', 'imdb_keywords_list_contents')
	simkl_main = ('simkl_tv_popular', 'simkl_tv_most_watched', 'simkl_tv_recent_release', 'simkl_onas_popular', 'simkl_onas_most_watched', 'simkl_onas_recent_release')
	simkl_special_key_dict = {'simkl_tv_genres': 'genre_id', 'simkl_tv_year': 'year'}
	similar = ('tmdb_tv_similar', 'tmdb_tv_recommendations')
	personal_dict = {
		'in_progress_tvshows': ('caches.watched_cache', 'get_in_progress_tvshows'),
		'favourites_tvshows': ('caches.favourites_cache', 'retrieve_favourites'),
		'watched_tvshows': ('caches.watched_cache', 'get_watched_items')
	}

	def run(self):
		try:
			params_get = self.params.get
			self.is_widget = kodi_utils.external_browse()
			self.exit_list_params = params_get('exit_list_params', None) or get_infolabel('Container.FolderPath')
			self.handle = int(sys.argv[1])
			view_type, content_type = 'view.tvshows', 'tvshows'
			mode = params_get('mode')
			try: page_no = int(params_get('new_page', '1'))
			except ValueError: page_no = params_get('new_page')
			letter = params_get('new_letter', 'None')
			if self.action in Indexer.personal_dict: var_module, import_function = Indexer.personal_dict[self.action]
			else: var_module, import_function = 'apis.%s_api' % self.action.split('_')[0], self.action
			try: function = manual_function_import(var_module, import_function)
			except: pass
			if self.action in Indexer.tmdb_main:
				data = function(page_no)
				self.list = [i['id'] for i in data['results']]
				total_pages = data['total_pages']
				if total_pages > page_no: self.new_page = {'new_page': string(data['page'] + 1)}
			elif self.action in Indexer.trakt_main:
				self.id_type = 'trakt_dict'
				data = function(page_no)
				self.list = [i['show']['ids'] for i in data]
				self.new_page = {'new_page': string(page_no + 1)}
			elif self.action in Indexer.tmdb_personal:
				data, total_pages = function('tv', page_no, letter)
				self.list = [i['id'] for i in data]
				if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'new_letter': letter}
			elif self.action in Indexer.trakt_personal:
				self.id_type = 'trakt_dict'
				data, total_pages = function('shows', page_no, letter)
				self.list = [i['media_ids'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				try:
					if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'new_letter': letter}
				except: pass
			elif self.action in Indexer.mdblist_personal:
				self.id_type = 'trakt_dict'
				data, total_pages = function('shows', page_no, letter)
				self.list = [{'imdb': i['imdb_id'], 'tmdb': i['id']} for i in data]
				if total_pages > 2: self.total_pages = total_pages
				try:
					if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'new_letter': letter}
				except: pass
			elif self.action in Indexer.imdb_personal:
				self.id_type = 'imdb_id'
				list_id = params_get('list_id', None)
				data, next_page = function('tvshow', list_id, page_no)
				self.list = [i['imdb_id'] for i in data]
				if next_page: self.new_page = {'list_id': list_id, 'new_page': string(page_no + 1), 'new_letter': letter}
			elif self.action in Indexer.personal_dict:
				data, total_pages = function('tvshow', page_no, letter)
				self.list = [i['media_id'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'new_letter': letter}
				if self.watched_indicators == 1:
					try:
						hidden_data = trakt_get_hidden_items('dropped')
						self.list = [i for i in self.list if not int(i) in hidden_data]
					except: pass
			elif self.action in Indexer.similar:
				tmdb_id = self.params['tmdb_id']
				data = function(tmdb_id, page_no)
				self.list = [i['id'] for i in data['results']]
				if data['page'] < data['total_pages']: self.new_page = {'new_page': string(data['page'] + 1), 'tmdb_id': tmdb_id}
			elif self.action in Indexer.tmdb_special_key_dict:
				key = Indexer.tmdb_special_key_dict[self.action]
				function_var = params_get(key, None)
				if not function_var: return
				data = function(function_var, page_no)
				self.list = [i['id'] for i in data['results']]
				if data['page'] < data['total_pages']: self.new_page = {'new_page': string(data['page'] + 1), key: function_var}
			elif self.action == 'tmdb_tv_discover':
				from indexers.discover import set_history
				name = self.params['name']
				query = self.params['query']
				if page_no == 1: set_history('tvshow', name, query)
				data = function(query, page_no)
				self.list = [i['id'] for i in data['results']]
				if data['page'] < data['total_pages']: self.new_page = {'query': query, 'name': name, 'new_page': string(data['page'] + 1)}
			elif self.action == 'tmdb_tv_genres':
				genre_id = self.params['genre_id']
				if not genre_id: return
				data = function(genre_id, page_no)
				self.list = [i['id'] for i in data['results']]
				if data['page'] < data['total_pages']: self.new_page = {'new_page': string(data['page'] + 1), 'genre_id': genre_id}
			elif self.action == 'tmdb_tv_search':
				query = self.params['query']
				data = function(query, page_no)
				self.list = [i['id'] for i in data['results']]
				total_pages = data['total_pages']
				if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'query': query}
			elif self.action == 'trakt_tv_certifications':
				self.id_type = 'trakt_dict'
				data = function(self.params['certification'], page_no)
				self.list = [i['show']['ids'] for i in data]
				self.new_page = {'new_page': string(page_no + 1), 'certification': self.params['certification']}
			elif self.action == 'trakt_recommendations':
				self.id_type = 'trakt_dict'
				data = function('shows')
				self.list = [i['ids'] for i in data]
			elif self.action in Indexer.simkl_main:
				self.id_type = 'trakt_dict'
				data = function(page_no)
				self.list = data
			elif self.action in Indexer.simkl_special_key_dict:
				key = Indexer.simkl_special_key_dict[self.action]
				function_var = params_get(key, None)
				if not function_var: return
				data = function(function_var)
				self.id_type = 'trakt_dict'
				self.list = data
			if self.total_pages and not self.is_widget and settings.nav_jump_use_alphabet():
				url_params = {'mode': 'build_navigate_to_page', 'media_type': 'TV Shows', 'current_page': page_no, 'total_pages': self.total_pages, 'transfer_mode': mode,
							'transfer_action': self.action, 'query': params_get('search_name', ''), 'actor_id': params_get('actor_id', '')}
				kodi_utils.add_dir(self.handle, url_params, jumpto_str, item_jump, isFolder=False)
			kodi_utils.add_items(self.handle, self.worker())
			if self.new_page:
				self.new_page.update({'mode': mode, 'action': self.action, 'exit_list_params': self.exit_list_params, 'name': ls(params_get('name'))})
				kodi_utils.add_dir(self.handle, self.new_page, nextpage_str, item_next)
		except: pass
		kodi_utils.set_category(self.handle, ls(params_get('name')))
		kodi_utils.set_sort_method(self.handle, content_type)
		kodi_utils.set_content(self.handle, content_type)
		kodi_utils.end_directory(self.handle, False if self.is_widget else None)
		kodi_utils.set_view_mode(view_type, content_type)

