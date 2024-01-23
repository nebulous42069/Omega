# -*- coding: utf-8 -*-
from modules import meta_lists
from modules import kodi_utils, settings
from modules.metadata import movie_meta
from modules.utils import manual_function_import, get_datetime, make_thread_list, make_thread_list_enumerate, make_thread_list_multi_arg, \
						get_current_timestamp, paginate_list, jsondate_to_datetime
from modules.watched_status import get_watched_info_movie, get_watched_status_movie, get_bookmarks, get_progress_percent
# logger = kodi_utils.logger

make_listitem, build_url, nextpage_landscape, item_jump_landscape = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.nextpage_landscape, kodi_utils.item_jump_landscape
string, sys, external, add_items, add_dir = str, kodi_utils.sys, kodi_utils.external, kodi_utils.add_items, kodi_utils.add_dir
set_content, end_directory, set_view_mode, folder_path = kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode, kodi_utils.folder_path
progress_percent_function, get_watched_function, get_watched_info_function, random = get_progress_percent, get_watched_status_movie, get_watched_info_movie, kodi_utils.random
poster_empty, fanart_empty, set_property = kodi_utils.empty_poster, kodi_utils.get_addon_fanart(), kodi_utils.set_property
sleep, xbmc_actor, set_category, json = kodi_utils.sleep, kodi_utils.xbmc_actor, kodi_utils.set_category, kodi_utils.json
meta_function, get_datetime_function, add_item, home = movie_meta, get_datetime, kodi_utils.add_item, kodi_utils.home
jsondate_to_datetime_function = jsondate_to_datetime
watched_indicators, use_minimal_media_info, widget_hide_next_page = settings.watched_indicators, settings.use_minimal_media_info, settings.widget_hide_next_page
widget_hide_watched, extras_open_action, page_limit, paginate = settings.widget_hide_watched, settings.extras_open_action, settings.page_limit, settings.paginate
run_plugin = 'RunPlugin(%s)'
main = ('tmdb_movies_popular', 'tmdb_movies_popular_today','tmdb_movies_blockbusters','tmdb_movies_in_theaters',
			'tmdb_movies_upcoming', 'tmdb_movies_latest_releases', 'tmdb_movies_premieres', 'tmdb_movies_oscar_winners')
special = ('tmdb_movies_languages', 'tmdb_movies_networks', 'tmdb_movies_year', 'tmdb_movies_decade',
			'tmdb_movies_certifications', 'tmdb_movies_recommendations', 'tmdb_movies_genres', 'tmdb_movies_search', 'tmdb_movie_keyword_results', 'tmdb_movie_keyword_results_direct')
personal = {'favorites_movies': ('modules.favorites', 'get_favorites'), 'in_progress_movies': ('modules.watched_status', 'get_in_progress_movies'), 
			'watched_movies': ('modules.watched_status', 'get_watched_items'), 'recent_watched_movies': ('modules.watched_status', 'get_recently_watched')}
trakt_main = ('trakt_movies_trending', 'trakt_movies_trending_recent', 'trakt_movies_most_watched', 'trakt_movies_top10_boxoffice', 'trakt_recommendations')
trakt_personal = ('trakt_collection', 'trakt_watchlist', 'trakt_collection_lists', 'trakt_watchlist_lists')
meta_list_dict = {'tmdb_movies_languages': meta_lists.languages, 'tmdb_movies_networks': meta_lists.watch_providers, 'tmdb_movies_year': meta_lists.years_movies,
			'tmdb_movies_decade': meta_lists.decades_movies, 'tmdb_movies_certifications': meta_lists.movie_certifications, 'tmdb_movies_genres': meta_lists.movie_genres}
view_mode, content_type = 'view.movies', 'movies'

class Movies:
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get
		self.category_name = self.params_get('category_name', None) or self.params_get('name', None) or 'Movies'
		self.id_type, self.list, self.action = self.params_get('id_type', 'tmdb_id'), self.params_get('list', []), self.params_get('action', None)
		self.items, self.new_page, self.total_pages, self.is_external, self.is_home = [], {}, None, external(), home()
		self.widget_hide_next_page = self.is_home and widget_hide_next_page()
		self.widget_hide_watched = self.is_home and widget_hide_watched()
		self.custom_order = self.params_get('custom_order', 'false') == 'true'
		self.paginate_start = int(self.params_get('paginate_start', '0'))
		self.append = self.items.append

	def fetch_list(self):
		handle = int(sys.argv[1])
		try:
			is_random = self.params_get('random', 'false') == 'true'
			try: page_no = int(self.params_get('new_page', '1'))
			except: page_no = self.params_get('new_page')
			if page_no == 1 and not self.is_external: set_property('fenlight.exit_params', folder_path())
			if self.action in personal: var_module, import_function = personal[self.action]
			else: var_module, import_function = 'apis.%s_api' % self.action.split('_')[0], self.action
			try: function = manual_function_import(var_module, import_function)
			except: pass
			if self.action in main:
				if is_random: data = self.random_worker(function)
				else: data = function(page_no)
				self.list = [i['id'] for i in data['results']]
				if not is_random and  data['total_pages'] > page_no: self.new_page = {'new_page': string(data['page'] + 1)}
			elif self.action in special:
				if is_random: data, key_id = self.random_worker(function), None
				else:
					key_id = self.params_get('key_id') or self.params_get('query')
					if not key_id: return
					data = function(key_id, page_no)
				self.list = [i['id'] for i in data['results']]
				if not is_random and data['total_pages'] > page_no: self.new_page = {'new_page': string(data['page'] + 1), 'key_id': key_id}
			elif self.action in personal:
				data = function('movie', page_no)
				if self.action == 'recent_watched_movies': total_pages = 1
				else: data, total_pages = self.paginate_list(data, page_no)
				self.list = [i['media_id'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'paginate_start': self.paginate_start}
			elif self.action in trakt_main:
				self.id_type = 'trakt_dict'
				if is_random: data = self.random_worker(function)['results']
				else: data = function(page_no)
				try: self.list = [i['movie']['ids'] for i in data]
				except: self.list = [i['ids'] for i in data]
				if not is_random and self.action not in ('trakt_movies_top10_boxoffice', 'trakt_recommendations'): self.new_page = {'new_page': string(page_no + 1)}
			elif self.action in trakt_personal:
				self.id_type = 'trakt_dict'
				data = function('movies', page_no)
				if self.action in ('trakt_collection_lists', 'trakt_watchlist_lists'): total_pages = 1
				else: data, total_pages = self.paginate_list(data, page_no)
				self.list = [i['media_ids'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				try:
					if total_pages > page_no: self.new_page = {'new_page': string(page_no + 1), 'paginate_start': self.paginate_start}
				except: pass
			add_items(handle, self.worker())
			if self.new_page and not self.widget_hide_next_page:
					self.new_page.update({'mode': 'build_movie_list', 'action': self.action, 'category_name': self.category_name})
					add_dir(self.new_page, 'Next Page (%s) >>' % self.new_page['new_page'], handle, 'nextpage', nextpage_landscape)
		except: pass
		set_content(handle, content_type)
		set_category(handle, self.category_name)
		end_directory(handle, cacheToDisc=False if self.is_external else True)
		if not self.is_external:
			if self.params_get('refreshed') == 'true': sleep(1000)
			set_view_mode(view_mode, content_type, self.is_external)
		
	def build_movie_content(self, _position, _id):
		try:
			meta = meta_function(self.id_type, _id, self.current_date, self.current_time)
			if not meta or 'blank_entry' in meta: return
			meta_get = meta.get
			premiered = meta_get('premiered')
			first_airdate = jsondate_to_datetime_function(premiered, '%Y-%m-%d', True)
			if not first_airdate or self.current_date < first_airdate: unaired = True
			else: unaired = False
			playcount = get_watched_function(self.watched_info, string(meta_get('tmdb_id')))
			cm = []
			cm_append = cm.append
			listitem = make_listitem()
			set_properties = listitem.setProperties
			clearprog_params, watched_status_params = '', ''
			title, year = meta_get('title'), meta_get('year') or '2050'
			tmdb_id, imdb_id = meta_get('tmdb_id'), meta_get('imdb_id')
			poster, fanart, clearlogo = meta_get('poster') or poster_empty, meta_get('fanart') or fanart_empty, meta_get('clearlogo') or ''
			progress = progress_percent_function(self.bookmarks, tmdb_id)
			play_params = build_url({'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': tmdb_id})
			extras_params = build_url({'mode': 'extras_menu_choice', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'is_external': self.is_external})
			options_params = build_url({'mode': 'options_menu_choice', 'content': 'movie', 'tmdb_id': tmdb_id, 'poster': poster, 'playcount': playcount,
										'progress': progress, 'is_external': self.is_external, 'unaired': unaired})
			if self.open_extras:
				url_params = extras_params
				cm_append(('[B]Playback...[/B]', run_plugin % play_params))
			else:
				url_params = play_params
				cm_append(('[B]Extras...[/B]', run_plugin % extras_params))
			cm_append(('[B]Options...[/B]', run_plugin % options_params))
			cm_append(('[B]Playback Options...[/B]', run_plugin % build_url({'mode': 'playback_choice', 'media_type': 'movie', 'poster': poster, 'meta': tmdb_id})))
			if playcount:
				if self.widget_hide_watched: return
				cm_append(('[B]Mark Unwatched %s[/B]' % self.watched_title, run_plugin % build_url({'mode': 'watched_status.mark_movie', 'action': 'mark_as_unwatched',
							'tmdb_id': tmdb_id, 'title': title})))
			elif not unaired:
				cm_append(('[B]Mark Watched %s[/B]' % self.watched_title, run_plugin % build_url({'mode': 'watched_status.mark_movie', 'action': 'mark_as_watched',
							'tmdb_id': tmdb_id, 'title': title})))
			if progress:
				cm_append(('[B]Clear Progress[/B]', run_plugin % build_url({'mode': 'watched_status.erase_bookmark', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'refresh': 'true'})))
			if self.is_home: cm_append(('[B]Refresh Widgets[/B]', run_plugin % build_url({'mode': 'kodi_refresh'})))
			else: cm_append(('[B]Exit Movie List[/B]', run_plugin % build_url({'mode': 'navigator.exit_media_menu'})))
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('movie'), info_tag.setTitle(title), info_tag.setOriginalTitle(meta_get('original_title')), info_tag.setGenres(meta_get('genre'))
			info_tag.setDuration(meta_get('duration')), info_tag.setPlaycount(playcount), info_tag.setPlot(meta_get('plot'))
			info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': string(tmdb_id)}), info_tag.setIMDBNumber(imdb_id), info_tag.setPremiered(premiered)
			if not self.use_minimal_media:
				info_tag.setYear(int(year)), info_tag.setRating(meta_get('rating')), info_tag.setVotes(meta_get('votes')), info_tag.setMpaa(meta_get('mpaa'))
				info_tag.setCountries(meta_get('country')), info_tag.setTrailer(meta_get('trailer'))
				info_tag.setTagLine(meta_get('tagline')), info_tag.setStudios(meta_get('studio'))
				info_tag.setWriters(meta_get('writer')), info_tag.setDirectors(meta_get('director'))
				info_tag.setCast([xbmc_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in meta_get('cast', [])])
			if progress:
				info_tag.setResumePoint(float(progress))
				set_properties({'WatchedProgress': progress})
			listitem.setLabel(title)
			listitem.addContextMenuItems(cm)
			listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'clearlogo': clearlogo})
			set_properties({'fenlight.extras_params': extras_params, 'fenlight.options_params': options_params})
			self.append(((url_params, listitem, False), _position))
		except: pass

	def worker(self):
		self.current_date, self.current_time, self.watched_indicators = get_datetime_function(), get_current_timestamp(), watched_indicators()
		self.watched_info, self.bookmarks = get_watched_info_function(self.watched_indicators), get_bookmarks(self.watched_indicators, 'movie')
		self.open_extras, self.watched_title = extras_open_action('movie'), 'Trakt' if self.watched_indicators == 1 else 'Fen Light'
		self.use_minimal_media = use_minimal_media_info()
		if self.custom_order:
			threads = list(make_thread_list_multi_arg(self.build_movie_content, self.list))
			[i.join() for i in threads]
		else:
			threads = list(make_thread_list_enumerate(self.build_movie_content, self.list))
			[i.join() for i in threads]
			self.items.sort(key=lambda k: k[1])
			self.items = [i[0] for i in self.items]
		return self.items

	def random_worker(self, function):
		try:
			random_results = []
			if self.action in main: threads = list(make_thread_list(lambda x: random_results.extend(function(x)['results']), range(1, 6)))
			elif self.action in trakt_main: threads = list(make_thread_list(lambda x: random_results.extend(function(x)), range(1, 6)))
			else:
				info = random.choice(meta_list_dict[self.action])
				self.category_name = 'Random %s' % info['name']
				threads = list(make_thread_list(lambda x: random_results.extend(function(info['id'], x)['results']), range(1, 6)))
			[i.join() for i in threads]
			return {'results': random.sample(random_results, min(len(random_results), 20))}
		except: return {'results': []}

	def paginate_list(self, data, page_no):
		if paginate(self.is_home):
			limit = page_limit(self.is_home)
			data, total_pages = paginate_list(data, page_no, limit, self.paginate_start)
			if self.is_home: self.paginate_start = limit
		else: total_pages = 1
		return data, total_pages
