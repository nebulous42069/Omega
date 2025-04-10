# -*- coding: utf-8 -*-
import sys
import apis
from modules import meta_lists
from modules.metadata import movie_meta, movieset_meta
from modules.utils import get_datetime, get_current_timestamp, paginate_list, jsondate_to_datetime, TaskPool
from modules import kodi_utils, settings, watched_status, favorites
# logger = kodi_utils.logger

class Movies:
	main = ('tmdb_movies_popular', 'tmdb_movies_popular_today','tmdb_movies_blockbusters','tmdb_movies_in_theaters', 'tmdb_movies_upcoming',
	'tmdb_movies_latest_releases', 'tmdb_movies_premieres', 'tmdb_movies_oscar_winners')
	special = ('tmdb_movies_languages', 'tmdb_movies_providers', 'tmdb_movies_year', 'tmdb_movies_decade', 'tmdb_movies_certifications', 'tmdb_movies_recommendations',
	'tmdb_movies_genres', 'tmdb_movies_search', 'tmdb_movie_keyword_results', 'tmdb_movie_keyword_results_direct')
	personal = {'in_progress_movies': {'module': 'watched_status', 'function': 'get_in_progress_movies'},
	'favorites_movies': {'module': 'favorites','function': 'get_favorites'},
	'watched_movies': {'module': 'watched_status', 'function': 'get_watched_items'}, 'recent_watched_movies': {'module': 'watched_status', 'function': 'get_recently_watched'}}
	trakt_main = ('trakt_movies_trending', 'trakt_movies_trending_recent', 'trakt_movies_most_watched', 'trakt_movies_most_favorited', 'trakt_movies_top10_boxoffice')
	trakt_personal = ('trakt_collection', 'trakt_watchlist', 'trakt_collection_lists', 'trakt_watchlist_lists', 'trakt_favorites')
	
	def __init__(self, params):
		self.params = params
		self.params_get = self.params.get
		self.category_name = self.params_get('category_name', None) or self.params_get('name', None) or 'Movies'
		self.id_type, self.list, self.action = self.params_get('id_type', 'tmdb_id'), self.params_get('list', []), self.params_get('action', None)
		self.items, self.new_page, self.total_pages, self.is_external, self.is_home = [], {}, None, kodi_utils.external(), kodi_utils.home()
		self.widget_hide_next_page = self.is_home and settings.widget_hide_next_page()
		self.widget_hide_watched = self.is_home and settings.widget_hide_watched()
		self.custom_order = self.params_get('custom_order', 'false') == 'true'
		self.paginate_start = int(self.params_get('paginate_start', '0'))
		self.tmdb_api_key = settings.tmdb_api_key()
		self.rpdb_api_key = settings.rpdb_api_key('movie')
		self.mpaa_region = settings.mpaa_region()
		self.append = self.items.append
		self.movieset_list_active = False

	def fetch_list(self):
		handle = int(sys.argv[1])
		try:
			try: page_no = int(self.params_get('new_page', '1'))
			except: page_no = self.params_get('new_page')
			if page_no == 1 and not self.is_external: kodi_utils.set_property('fenlight.exit_params', kodi_utils.folder_path())
			if self.action in self.main:
				data = self.get_data(page_no, module='apis.tmdb_api')
				self.list = [i['id'] for i in data['results']]
				if data['total_pages'] > page_no: self.new_page = {'new_page': str(data['page'] + 1)}
			elif self.action in self.special:
				key_id = self.params_get('key_id') or self.params_get('query')
				if not key_id: return
				data = self.get_data(key_id, page_no, module='apis.tmdb_api')
				self.list = [i['id'] for i in data['results']]
				if data['total_pages'] > page_no: self.new_page = {'new_page': str(data['page'] + 1), 'key_id': key_id}
			elif self.action in self.personal:
				data = self.get_data('movie', page_no, **self.personal[self.action])
				if self.action == 'recent_watched_movies': total_pages = 1
				else: data, total_pages = self.paginate_list(data, page_no)
				self.list = [i['media_id'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				if total_pages > page_no: self.new_page = {'new_page': str(page_no + 1), 'paginate_start': self.paginate_start}
			elif self.action in self.trakt_main:
				self.id_type = 'trakt_dict'
				data = self.get_data(page_no, module='apis.trakt_api')
				try: self.list = [i['movie']['ids'] for i in data]
				except: self.list = [i['ids'] for i in data]
				if self.action not in ('trakt_movies_top10_boxoffice', 'trakt_recommendations'): self.new_page = {'new_page': str(page_no + 1)}
			elif self.action in self.trakt_personal:
				self.id_type = 'trakt_dict'
				data = self.get_data('movies', page_no, module='apis.trakt_api')
				if self.action in ('trakt_collection_lists', 'trakt_watchlist_lists', 'trakt_favorites'): total_pages = 1
				else: data, total_pages = self.paginate_list(data, page_no)
				self.list = [i['media_ids'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				try:
					if total_pages > page_no: self.new_page = {'new_page': str(page_no + 1), 'paginate_start': self.paginate_start}
				except: pass
			elif self.action == 'trakt_recommendations':
				self.id_type = 'trakt_dict'
				data = self.get_data('movies', module='apis.trakt_api')
				data, total_pages = self.paginate_list(data, page_no)
				self.list = [i['ids'] for i in data]
				if total_pages > 2: self.total_pages = total_pages
				try:
					if total_pages > page_no: self.new_page = {'new_page': str(page_no + 1), 'paginate_start': self.paginate_start}
				except: pass
			elif self.action == 'tmdb_movies_discover':
				url = self.params_get('url')
				data = self.get_data(url, page_no, module='apis.tmdb_api')
				self.list = [i['id'] for i in data['results']]
				if data['total_pages'] > page_no: self.new_page = {'url': url, 'new_page': str(data['page'] + 1)}
			elif self.action  == 'tmdb_movies_sets':
				self.movieset_list_active = True
				data = sorted(movieset_meta(self.params_get('key_id'), self.tmdb_api_key)['parts'], key=lambda k: k['release_date'] or '2050')
				self.list = [i['id'] for i in data]
			elif self.action == 'imdb_more_like_this':
				from apis.imdb_api import imdb_more_like_this
				if self.params_get('get_imdb'):
					self.params['key_id'] = movie_meta('tmdb_id', self.params_get('key_id'), self.tmdb_api_key, self.mpaa_region,
														get_datetime(), get_current_timestamp())['imdb_id']
				self.id_type = 'imdb_id'
				self.list = imdb_more_like_this(self.params_get('key_id'))
			kodi_utils.add_items(handle, self.worker())
			if self.new_page and not self.widget_hide_next_page:
							self.new_page.update({'mode': 'build_movie_list', 'action': self.action, 'category_name': self.category_name})
							kodi_utils.add_dir(self.new_page, 'Next Page (%s) >>' % self.new_page['new_page'], handle, 'nextpage', kodi_utils.nextpage_landscape())
		except: pass
		kodi_utils.set_content(handle, 'movies')
		kodi_utils.set_category(handle, self.category_name)
		kodi_utils.end_directory(handle, cacheToDisc=False if self.is_external else True)
		if not self.is_external:
			if self.params_get('refreshed') == 'true': kodi_utils.sleep(1000)
			kodi_utils.set_view_mode('view.movies', 'movies', self.is_external)
		
	def build_movie_content(self, _position, _id):
		try:
			meta = movie_meta(self.id_type, _id, self.tmdb_api_key, self.mpaa_region, self.current_date, self.current_time)
			if not meta or 'blank_entry' in meta: return
			listitem = self.make_listitem()
			cm = []
			cm_append = cm.append
			set_properties = listitem.setProperties
			clearprog_params, watched_status_params = '', ''
			meta_get = meta.get
			premiered = meta_get('premiered')
			title, year = meta_get('title'), meta_get('year') or '2050'
			tmdb_id, imdb_id = meta_get('tmdb_id'), meta_get('imdb_id')
			str_tmdb_id = str(tmdb_id)
			if self.rpdb_api_key:
				try: poster = meta_get('rpdb_poster') % self.rpdb_api_key
				except: poster = meta_get('poster') or self.poster_empty
			else: poster = meta_get('poster') or self.poster_empty
			fanart = meta_get('fanart') or self.fanart_empty
			clearlogo, landscape = meta_get('clearlogo') or '', meta_get('landscape') or ''
			thumb = poster or landscape or fanart
			movieset_id, movieset_name = meta_get('extra_info').get('collection_id', None), meta_get('extra_info').get('collection_name', None)
			first_airdate = jsondate_to_datetime(premiered, '%Y-%m-%d', True)
			if not first_airdate or self.current_date < first_airdate: unaired = True
			else: unaired = False
			progress = watched_status.get_progress_status_movie(self.bookmarks, str_tmdb_id)
			playcount = watched_status.get_watched_status_movie(self.watched_info, str_tmdb_id)
			play_params = self.build_url({'mode': 'playback.media', 'media_type': 'movie', 'tmdb_id': tmdb_id})
			extras_params = self.build_url({'mode': 'extras_menu_choice', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'is_external': self.is_external})
			options_params = self.build_url({'mode': 'options_menu_choice', 'content': 'movie', 'tmdb_id': tmdb_id, 'poster': poster, 'is_external': self.is_external})
			more_like_this_params = self.build_url({'mode': 'build_movie_list', 'action': 'imdb_more_like_this', 'key_id': imdb_id,
							'name': 'More Like This based on %s' % title, 'is_external': self.is_external})
			belongs_to_movieset = 'true' if all([movieset_id, movieset_name]) else 'false'
			movieset_active = self.open_movieset and belongs_to_movieset == 'true'
			if self.open_extras or movieset_active: cm_append(['extras', ('[B]Playback[/B]', 'RunPlugin(%s)' % play_params)])
			if not self.open_extras or movieset_active: cm_append(['extras', ('[B]Extras[/B]', 'RunPlugin(%s)' % extras_params)])
			if movieset_active: url_params = self.build_url({'mode': 'open_movieset_choice', 'key_id': movieset_id, 'name': movieset_name, 'is_external': self.is_external})
			elif self.open_extras: url_params = extras_params
			else: url_params = play_params
			cm_append(['options', ('[B]Options[/B]', 'RunPlugin(%s)' % options_params)])
			cm_append(['playback_options', ('[B]Playback Options[/B]', 'RunPlugin(%s)' % self.build_url({'mode': 'playback_choice', 'media_type': 'movie', 'meta': tmdb_id}))])
			if belongs_to_movieset == 'true' and not self.movieset_list_active and not self.open_movieset:
				cm_append(['browse_set_season', ('[B]Browse Movie Set[/B]', self.window_command % \
							self.build_url({'mode': 'build_movie_list', 'action': 'tmdb_movies_sets', 'key_id': movieset_id, 'name': movieset_name}))])
			cm_append(['recommended', ('[B]Browse Recommended[/B]', self.window_command % \
							self.build_url({'mode': 'build_movie_list', 'action': 'tmdb_movies_recommendations', 'key_id': tmdb_id, 'name': 'Recommended based on %s' % title}))])
			cm_append(['more_like_this', ('[B]Browse More Like This[/B]', self.window_command % more_like_this_params)])
			if imdb_id: cm_append(['in_trakt_list', ('[B]In Trakt Lists[/B]', self.window_command % \
							self.build_url({'mode': 'trakt.list.in_trakt_lists', 'media_type': 'movie', 'imdb_id': imdb_id, 'category_name': '%s In Trakt Lists' % title}))])
			cm_append(['trakt_manager', ('[B]Trakt Lists Manager[/B]', 'RunPlugin(%s)' % \
							self.build_url({'mode': 'trakt_manager_choice', 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'tvdb_id': 'None', 'media_type': 'movie', 'icon': poster}))])
			cm_append(['personal_manager', ('[B]Personal Lists Manager[/B]', 'RunPlugin(%s)' % \
							self.build_url({'mode': 'personal_lists_choice', 'list_type': 'movie', 'tmdb_id': tmdb_id, 'title': title,
										'premiered': premiered, 'current_time': self.current_time, 'icon': poster}))])
			cm_append(['favorites_manager', ('[B]Favorites Manager[/B]', 'RunPlugin(%s)' % \
							self.build_url({'mode': 'favorites_choice', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'title': title}))])
			if playcount:
				if self.widget_hide_watched: return
				cm_append(['mark_watched', ('[B]Mark Unwatched %s[/B]' % self.watched_title, 'RunPlugin(%s)' % \
							self.build_url({'mode': 'watched_status.mark_movie', 'action': 'mark_as_unwatched',
											'tmdb_id': tmdb_id, 'title': title}))])
			elif not unaired:
				cm_append(['mark_watched', ('[B]Mark Watched %s[/B]' % self.watched_title, 'RunPlugin(%s)' % \
							self.build_url({'mode': 'watched_status.mark_movie', 'action': 'mark_as_watched',
											'tmdb_id': tmdb_id, 'title': title}))])
			if progress:
				cm_append(['mark_watched', ('[B]Clear Progress[/B]', 'RunPlugin(%s)' % self.build_url({'mode': 'watched_status.erase_bookmark', 'media_type': 'movie',
											'tmdb_id': tmdb_id, 'refresh': 'true'}))])
			if not self.is_external: cm_append(['exit', ('[B]Exit Movie List[/B]', 'RunPlugin(%s)' % self.build_url({'mode': 'navigator.exit_media_menu'}))])
			cm = self.sort_context_menu(cm)
			if self.is_external:
				cm.extend([('[B]Refresh Widgets[/B]', 'RunPlugin(%s)' % self.build_url({'mode': 'refresh_widgets'})),
						('[B]Reload Widgets[/B]', 'RunPlugin(%s)' % self.build_url({'mode': 'kodi_refresh'}))])
			info_tag = listitem.getVideoInfoTag()
			info_tag.setMediaType('movie'), info_tag.setTitle(title), info_tag.setOriginalTitle(meta_get('original_title')), info_tag.setGenres(meta_get('genre'))
			info_tag.setDuration(meta_get('duration')), info_tag.setPlaycount(playcount), info_tag.setPlot(meta_get('plot'))
			info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': str_tmdb_id}), info_tag.setIMDBNumber(imdb_id), info_tag.setPremiered(premiered)
			info_tag.setYear(int(year)), info_tag.setRating(meta_get('rating')), info_tag.setVotes(meta_get('votes')), info_tag.setMpaa(meta_get('mpaa'))
			info_tag.setCountries(meta_get('country')), info_tag.setTrailer(meta_get('trailer'))
			info_tag.setTagLine(meta_get('tagline')), info_tag.setStudios(meta_get('studio'))
			info_tag.setWriters(meta_get('writer')), info_tag.setDirectors(meta_get('director'))
			info_tag.setCast([self.kodi_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in meta_get('cast', [])])
			if progress:
				info_tag.setResumePoint(float(progress))
				set_properties({'WatchedProgress': progress})
			listitem.setLabel(title)
			listitem.addContextMenuItems(cm)
			listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'clearlogo': clearlogo, 'landscape': landscape, 'thumb': thumb})
			set_properties({'fenlight.extras_params': extras_params, 'fenlight.options_params': options_params,
							'belongs_to_collection': belongs_to_movieset, 'fenlight.more_like_this_params': more_like_this_params})
			self.append(((url_params, listitem, False), _position))
		except: pass

	def worker(self):
		self.kodi_actor, self.make_listitem, self.build_url = kodi_utils.kodi_actor(), kodi_utils.make_listitem, kodi_utils.build_url
		self.poster_empty, self.fanart_empty = kodi_utils.empty_poster(), kodi_utils.addon_fanart()
		self.current_date, self.current_time, self.watched_indicators = get_datetime(), get_current_timestamp(), settings.watched_indicators()
		self.cm_sort_order = settings.cm_sort_order()
		self.watched_title = 'Trakt' if self.watched_indicators == 1 else 'Fen Light'
		watched_db = watched_status.get_database(self.watched_indicators)
		self.watched_info, self.bookmarks = watched_status.watched_info_movie(watched_db), watched_status.get_bookmarks_movie(watched_db)
		self.window_command = 'ActivateWindow(Videos,%s,return)' if self.is_external else 'Container.Update(%s)'
		open_action = settings.media_open_action('movie')
		self.open_movieset = open_action in (2, 3) and not self.movieset_list_active
		self.open_extras = open_action in (1, 3)
		if self.custom_order: [i.join() for i in TaskPool().tasks(self.build_movie_content, self.list, min(len(self.list), settings.max_threads()))]
		else:
			[i.join() for i in TaskPool().tasks_enumerate(self.build_movie_content, self.list, min(len(self.list), settings.max_threads()))]
			self.items.sort(key=lambda k: k[1])
			self.items = [i[0] for i in self.items]
		return self.items

	def get_data(self, *args, module=None, function=None):
		return eval('%s.%s(*args)' % (module, function or self.action))

	def sort_context_menu(self, context_menu_items):
		try: context_menu_items = sorted([i for i in context_menu_items if i[0] in self.cm_sort_order], key=lambda k: self.cm_sort_order[k[0]])
		except: pass
		return [i[1] for i in context_menu_items]

	def paginate_list(self, data, page_no):
		if settings.paginate(self.is_home):
			limit = settings.page_limit(self.is_home)
			data, total_pages = paginate_list(data, page_no, limit, self.paginate_start)
			if self.is_home: self.paginate_start = limit
		else: total_pages = 1
		return data, total_pages
