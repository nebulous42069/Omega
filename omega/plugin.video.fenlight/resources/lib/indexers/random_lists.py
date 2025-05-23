# -*- coding: utf-8 -*-
import sys
import json
import random
from indexers.movies import Movies
from indexers.tvshows import TVShows
from modules import meta_lists
from modules import kodi_utils
from modules.utils import manual_function_import, make_thread_list
# logger = kodi_utils.logger

def get_persistent_content(menu_type, key, remake_widgets, is_external):
	if remake_widgets:
		kodi_utils.clear_property('fenlight.%s' % menu_type)
		return None, True
	if not is_external: return None, False
	try:
		menu_type_content = json.loads(kodi_utils.get_property('fenlight.%s' % menu_type))
		cached_content = menu_type_content.get(key)
		return cached_content, False
	except:
		kodi_utils.clear_property('fenlight.%s' % menu_type)
		return None, True

def set_persistent_content(menu_type, key, data):
	kodi_utils.sleep(random.randrange(50, 500, 50))
	while kodi_utils.get_property('fenlight.%s' % 'making_persistent_random_dict') == 'true': kodi_utils.sleep(10)
	kodi_utils.set_property('fenlight.making_persistent_random_dict', 'true')
	try: menu_type_content = json.loads(kodi_utils.get_property('fenlight.%s' % menu_type))
	except: menu_type_content = {}
	menu_type_content[key] = data
	kodi_utils.set_property('fenlight.%s' % menu_type, json.dumps(menu_type_content))
	kodi_utils.clear_property('fenlight.making_persistent_random_dict')

class RandomLists():
	movie_main = ('tmdb_movies_popular', 'tmdb_movies_popular_today','tmdb_movies_blockbusters','tmdb_movies_in_theaters', 'tmdb_movies_upcoming', 'tmdb_movies_latest_releases',
	'tmdb_movies_premieres', 'tmdb_movies_oscar_winners')
	movie_trakt_main = ('trakt_movies_trending', 'trakt_movies_trending_recent', 'trakt_movies_most_watched', 'trakt_movies_most_favorited',
	'trakt_movies_top10_boxoffice', 'trakt_recommendations')
	movie_meta_list_dict = {'tmdb_movies_languages': meta_lists.languages, 'tmdb_movies_providers': meta_lists.watch_providers_movies, 'tmdb_movies_year': meta_lists.years_movies,
	'tmdb_movies_decade': meta_lists.decades_movies, 'tmdb_movies_certifications': meta_lists.movie_certifications, 'tmdb_movies_genres': meta_lists.movie_genres}
	tvshow_main = ('tmdb_tv_popular', 'tmdb_tv_popular_today', 'tmdb_tv_premieres', 'tmdb_tv_airing_today','tmdb_tv_on_the_air','tmdb_tv_upcoming',
	'tmdb_anime_popular', 'tmdb_anime_popular_recent', 'tmdb_anime_premieres', 'tmdb_anime_upcoming', 'tmdb_anime_on_the_air')
	tvshow_trakt_main = ('trakt_tv_trending', 'trakt_tv_trending_recent', 'trakt_recommendations', 'trakt_tv_most_watched', 'trakt_tv_most_favorited',
	'trakt_anime_trending', 'trakt_anime_trending_recent', 'trakt_anime_most_watched', 'trakt_anime_most_favorited')
	tvshow_meta_list_dict = {'tmdb_tv_languages': meta_lists.languages, 'tmdb_tv_networks': meta_lists.networks, 'tmdb_tv_providers': meta_lists.watch_providers_tvshows,
	'tmdb_tv_year': meta_lists.years_tvshows, 'tmdb_tv_decade': meta_lists.decades_tvshows, 'tmdb_tv_genres': meta_lists.tvshow_genres,
	'trakt_tv_certifications': meta_lists.tvshow_certifications, 'tmdb_anime_year': meta_lists.years_tvshows, 'tmdb_anime_decade': meta_lists.decades_tvshows,
	'tmdb_anime_genres': meta_lists.anime_genres, 'tmdb_anime_providers': meta_lists.watch_providers_tvshows, 'trakt_anime_certifications': meta_lists.tvshow_certifications}
	tvshow_trakt_special = ('trakt_tv_certifications', 'trakt_anime_certifications')

	def __init__(self, params):
		self.handle = int(sys.argv[1])
		self.params = params
		self.params_get = params.get
		self.mode = self.params_get('mode').replace('random.', '')
		self.action = self.params_get('action')
		self.menu_type = self.params_get('menu_type', None) or ('movie' if 'movie' in self.mode else 'tvshow' if 'tvshow' in self.mode else '')
		self.base_list_name = self.params_get('name')
		self.params.update({'mode': self.mode, 'action': self.action, 'menu_type': self.menu_type, 'base_list_name': self.base_list_name})
		self.is_external, self.is_home = kodi_utils.external(), kodi_utils.home()
		self.folder_name = self.params_get('folder_name', None)
		if self.menu_type == 'movie': self.function, self.view_mode, self.content_type = Movies, 'view.movies', 'movies'
		else: self.function, self.view_mode, self.content_type = TVShows, 'view.tvshows', 'tvshows'
		self.category_name, self.list_items, self.random_results = '', [], []
		self.remake_widgets = self.is_external and kodi_utils.get_property('fenlight.refresh_widgets') == 'true'
		if self.action and 'anime' in self.action: self.max_range, self.sample_size = 4, 3
		else: self.max_range, self.sample_size = 10, 3

	def run_random(self):
		if self.mode == 'build_trakt_lists': return self.random_trakt_lists()
		if self.mode == 'build_trakt_lists_contents': return self.trakt_lists_contents()
		if self.mode == 'build_personal_lists': return self.random_personal_lists()
		if self.mode == 'build_personal_lists_contents': return self.personal_lists_contents()
		if self.action in self.movie_main: return self.random_main()
		if self.action in self.tvshow_main: return self.random_main()
		if self.action in self.movie_trakt_main: return self.random_trakt_main()
		if self.action in self.tvshow_trakt_main: return self.random_trakt_main()
		if self.action in ('trakt_collection_lists', 'trakt_watchlist_lists'): return self.random_trakt_personal_lists()
		if self.action in ('tmdb_movies_discover', 'tmdb_tv_discover'): return self.random_discover()
		if self.action == 'because_you_watched': return self.random_because_you_watched()
		return self.random_special_main()

	def random_main(self):
		random_list, cache_to_memory = get_persistent_content('random_main', self.action, self.remake_widgets, self.is_external)
		if not random_list:
			list_function = self.get_function()
			threads = list(make_thread_list(lambda x: self.random_results.extend(list_function(x)['results']), self.get_sample()))
			[i.join() for i in threads]
			random_list = random.sample(self.random_results, min(len(self.random_results), 20))
			if cache_to_memory: set_persistent_content('random_main', self.action, random_list)
		self.params['list'] = [i['id'] for i in random_list]
		self.list_items = self.function(self.params).worker()
		self.category_name = self.params_get('category_name', None) or self.base_list_name or ''
		self.make_directory()

	def random_special_main(self):
		random_list, cache_to_memory = get_persistent_content('random_special_main', self.action, self.remake_widgets, self.is_external)
		if not random_list:
			list_function = self.get_function()
			choice_list = self.movie_meta_list_dict if self.menu_type == 'movie' else self.tvshow_meta_list_dict
			info = random.choice(choice_list[self.action]())
			list_name = info['name']
			if self.action in self.tvshow_trakt_special:
				threads = list(make_thread_list(lambda x: self.random_results.extend(list_function(info['id'], x)), self.get_sample()))			
			else:
				threads = list(make_thread_list(lambda x: self.random_results.extend(list_function(info['id'], x)['results']), self.get_sample()))
			[i.join() for i in threads]
			result = random.sample(self.random_results, min(len(self.random_results), 20))
			if cache_to_memory: set_persistent_content('random_special_main', self.action, {'name': list_name, 'result': result})
		else: list_name, result = random_list['name'], random_list['result']
		if self.action in self.tvshow_trakt_special: self.params.update({'id_type': 'trakt_dict', 'list': [i['show']['ids'] for i in result]})
		else: self.params['list'] = [i['id'] for i in result]
		self.list_items = self.function(self.params).worker()
		self.category_name = list_name
		self.make_directory()

	def random_discover(self):
		url = self.params_get('url', None)
		if not url: return
		random_list, cache_to_memory = get_persistent_content('random_discover', url, self.remake_widgets, self.is_external)
		if not random_list:
			list_function = self.get_function()
			threads = list(make_thread_list(lambda x: self.random_results.extend(list_function(url, x)['results']), self.get_sample()))
			[i.join() for i in threads]
			random_list = random.sample(self.random_results, min(len(self.random_results), 20))
			if cache_to_memory: set_persistent_content('random_discover', url, random_list)
		self.params['list'] = [i['id'] for i in random_list]
		self.list_items = self.function(self.params).worker()
		self.category_name = self.params_get('category_name', None) or self.base_list_name or ''
		self.make_directory()

	def random_trakt_main(self):
		random_list, cache_to_memory = get_persistent_content('random_trakt_main', self.action, self.remake_widgets, self.is_external)
		function_key, list_key = ('movies', 'movie') if self.menu_type == 'movie' else ('shows', 'show')
		if not random_list:
			list_function = self.get_function()
			threads = list(make_thread_list(lambda x: self.random_results.extend(list_function(x)), [function_key,] \
						if self.action == 'trakt_recommendations' else self.get_sample()))
			[i.join() for i in threads]
			random_list = random.sample(self.random_results, min(len(self.random_results), 20))
			if cache_to_memory: set_persistent_content('random_trakt_main', self.action, random_list)
		try: self.params['list'] = [i[list_key]['ids'] for i in random_list]
		except: self.params['list'] = [i['ids'] for i in random_list]
		self.params['id_type'] = 'trakt_dict'
		self.list_items = self.function(self.params).worker()
		self.category_name = self.params_get('category_name', None) or self.base_list_name or ''
		self.make_directory()

	def random_trakt_lists(self):
		from apis.trakt_api import trakt_get_lists, get_trakt_list_contents
		from indexers.trakt_lists import build_trakt_list
		list_type = self.params.get('list_type')
		list_type_name = 'Trakt My Lists' if list_type == 'my_lists' else 'Trakt Liked Lists' if list_type == 'liked_lists' else 'Trakt User Lists'
		random_list, cache_to_memory = get_persistent_content('random_trakt_lists', list_type, self.remake_widgets, self.is_external)
		if not random_list:
			self.random_results = trakt_get_lists(list_type)
			random_list = random.choice(self.random_results)
			if list_type != 'my_lists': random_list = random_list['list']
			user, slug = random_list['user']['ids']['slug'], random_list['ids']['slug']
			list_name = random_list['name']
			with_auth = list_type == 'my_lists'
			result = get_trakt_list_contents(list_type, user, slug, with_auth)
			random.shuffle(result)
			result = [dict(i, **{'order': c}) for c, i in enumerate(random.sample(result, min(len(result), 20)))]
			url_params = {'base_list_name':list_type_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_trakt_list(url_params)
			if cache_to_memory: set_persistent_content('random_trakt_lists', list_type, {'name': list_name, 'result': result})
		else:
			list_name, result = random_list['name'], random_list['result']
			url_params = {'base_list_name':list_type_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_trakt_list(url_params)
		self.view_mode, self.content_type = 'view.%s' % content_type, content_type
		self.category_name = list_name
		self.make_directory()

	def trakt_lists_contents(self):
		from apis.trakt_api import get_trakt_list_contents
		from indexers.trakt_lists import build_trakt_list
		list_name, list_type = self.params.get('list_name'), self.params.get('list_type')
		list_type_name = 'Trakt My Lists' if list_type == 'my_lists' else 'Trakt Liked Lists' if list_type == 'liked_lists' else 'Trakt User Lists'
		random_list, cache_to_memory = get_persistent_content('trakt_lists_contents', '%s_%s' % (list_type, list_name), self.remake_widgets, self.is_external)
		if not random_list:
			user, slug = self.params_get('user'), self.params_get('slug')
			with_auth = list_type == 'my_lists'
			result = get_trakt_list_contents(list_type, user, slug, with_auth)
			random.shuffle(result)
			result = [dict(i, **{'order': c}) for c, i in enumerate(random.sample(result, min(len(result), 20)))]
			url_params = {'base_list_name':list_type_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_trakt_list(url_params)
			if cache_to_memory: set_persistent_content('trakt_lists_contents', '%s_%s' % (list_type, list_name), {'name': list_name, 'result': result})
		else:
			list_name, result = random_list['name'], random_list['result']
			url_params = {'base_list_name':list_type_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_trakt_list(url_params)
		self.category_name = self.base_list_name or list_name or ''
		self.view_mode, self.content_type = 'view.%s' % content_type, content_type
		self.make_directory()

	def random_personal_lists(self):
		from indexers.personal_lists import get_personal_list, build_personal_list, get_all_personal_lists
		random_list, cache_to_memory = get_persistent_content('random_personal_lists', self.action, self.remake_widgets, self.is_external)
		if not random_list:
			self.random_results = get_all_personal_lists()
			random_list = random.choice(self.random_results)
			list_name, sort_order = random_list['name'], random_list['sort_order']		
			result = get_personal_list({'list_name': list_name, 'sort_order': sort_order})
			random.shuffle(result)
			result = [dict(i, **{'order': c}) for c, i in enumerate(result)]
			url_params = {'base_list_name':list_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_personal_list(url_params)
			if cache_to_memory: set_persistent_content('random_personal_lists', self.action, {'name': list_name, 'result': result})
		else:
			list_name, result = random_list['name'], random_list['result']
			url_params = {'base_list_name':list_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_personal_list(url_params)
		self.category_name = list_name or ''
		self.view_mode, self.content_type = 'view.%s' % content_type, content_type
		self.make_directory()

	def random_trakt_personal_lists(self):
		from apis.trakt_api import trakt_collection_lists, trakt_watchlist_lists
		random_list, cache_to_memory = get_persistent_content('random_trakt_personal_lists', '%s_%s' % (self.menu_type, self.action), self.remake_widgets, self.is_external)
		if not random_list:
			function = trakt_collection_lists if self.action == 'trakt_collection_lists' else trakt_watchlist_lists
			self.random_results = function('movies' if self.menu_type in ('movie', 'movies') else 'shows', None)
			random_list = random.sample(self.random_results, min(len(self.random_results), 20))
			if cache_to_memory: set_persistent_content('random_trakt_personal_lists',  '%s_%s' % (self.menu_type, self.action), random_list)
		self.params['list'] = [i['media_ids'] for i in random_list]
		self.params['id_type'] = 'trakt_dict'
		self.list_items = self.function(self.params).worker()
		self.category_name = self.base_list_name or ''
		self.make_directory()

	def random_because_you_watched(self):
		from apis.tmdb_api import tmdb_movies_recommendations, tmdb_tv_recommendations
		from apis.imdb_api import imdb_more_like_this
		from modules.settings import tmdb_api_key, mpaa_region, recommend_service, recommend_seed
		from modules.metadata import movie_meta, tvshow_meta
		from modules.watched_status import get_recently_watched
		from modules.utils import get_current_timestamp, get_datetime
		list_name = self.params.get('list_name')
		random_list, cache_to_memory = get_persistent_content('random_because_you_watched', list_name, self.remake_widgets, self.is_external)
		recommend_type = recommend_service()
		try:
			if not random_list:
				if self.menu_type == 'movie': mode, action, media_type = 'build_movie_list', 'tmdb_movies_recommendations', 'movie'
				else: mode, action, media_type = 'build_tvshow_list', 'tmdb_tv_recommendations', 'episode'
				recently_watched = get_recently_watched(media_type, short_list=0)
				recent_seed = random.choice(recently_watched[:recommend_seed()])
				seed_tmdb_id = recent_seed['media_id'] if self.menu_type == 'movie' else recent_seed['media_ids']['tmdb']
				list_name = 'Because You Watched... %s' % recent_seed['title']
				if recommend_type == 0:
					list_function = tmdb_movies_recommendations if self.menu_type == 'movie' else tmdb_tv_recommendations
					result = list_function(seed_tmdb_id, 1)['results']
				else:
					meta_function = movie_meta if self.menu_type == 'movie' else tvshow_meta
					result = imdb_more_like_this(meta_function('tmdb_id', seed_tmdb_id, tmdb_api_key(), mpaa_region(), get_datetime(), get_current_timestamp())['imdb_id'])
				if cache_to_memory: set_persistent_content('random_because_you_watched',  self.menu_type, {'name': list_name, 'result': result})
			else: list_name, result = random_list['name'], random_list['result']
			if recommend_type == 0: self.params['list'] = [i['id'] for i in result]
			else: self.params.update({'list': result, 'id_type': 'imdb_id'})
			self.list_items = self.function(self.params).worker()
			self.category_name =  list_name
		except: kodi_utils.clear_property('fenlight.random_because_you_watched')
		self.make_directory()

	def personal_lists_contents(self):
		from indexers.personal_lists import get_personal_list, build_personal_list
		list_name = self.params.get('list_name')
		random_list, cache_to_memory = get_persistent_content('personal_lists_contents', list_name, self.remake_widgets, self.is_external)
		if not random_list:
			result = get_personal_list(self.params)
			random.shuffle(result)
			result = [dict(i, **{'order': c}) for c, i in enumerate(random.sample(result, min(len(result), 20)))]
			url_params = {'base_list_name':list_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_personal_list(url_params)
			if cache_to_memory: set_persistent_content('personal_lists_contents', list_name, {'name': list_name, 'result': result})
		else:
			list_name, result = random_list['name'], random_list['result']
			url_params = {'base_list_name':list_name, 'list_name': list_name, 'result': result}
			content_type, self.list_items = build_personal_list(url_params)
		self.category_name = self.base_list_name or list_name or ''
		self.view_mode, self.content_type = 'view.%s' % content_type, content_type
		self.make_directory()

	def make_directory(self, next_page_params={}):
		kodi_utils.add_items(self.handle, self.list_items)
		if next_page_params: kodi_utils.add_dir(next_page_params, 'Next Page (%s) >>' % next_page_params['new_page'], self.handle, 'nextpage', kodi_utils.nextpage_landscape())
		kodi_utils.set_content(self.handle, self.content_type)
		kodi_utils.set_category(self.handle, self.category_name)
		kodi_utils.end_directory(self.handle, cacheToDisc=False if self.is_external else True)
		if self.is_external:
			if self.folder_name: kodi_utils.set_property('fenlight.%s' % self.folder_name, self.category_name)
			else: kodi_utils.set_property('fenlight.%s' % self.base_list_name, self.category_name)
		else: kodi_utils.set_view_mode(self.view_mode, self.content_type, self.is_external)

	def get_function(self):
		return manual_function_import('apis.%s_api' % self.action.split('_')[0], self.action)

	def get_sample(self):
		return random.sample(range(1, self.max_range), self.sample_size)

def random_shortcut_folders(folder_name, random_results):
	random_episodes_check = {'build_in_progress_episode': 'episode.progress', 'build_recently_watched_episode': 'episode.recently_watched',
	'build_next_episode': 'episode.next', 'build_my_calendar': 'episode.trakt'}
	random_valid_type_check = {'build_movie_list': 'movie', 'build_tvshow_list': 'tvshow', 'build_season_list': 'season', 'build_episode_list': 'episode',
				'build_in_progress_episode': 'single_episode', 'build_recently_watched_episode': 'single_episode', 'build_next_episode': 'single_episode',
				'build_my_calendar': 'single_episode', 'build_trakt_lists': 'trakt_list', 'trakt.list.build_trakt_list': 'trakt_list', 'build_trakt_lists_contents': 'trakt_list'}
	random_results = [i for i in random_results if i['mode'].replace('random.', '') in random_valid_type_check]
	is_external = kodi_utils.external()
	remake_widgets = is_external and kodi_utils.get_property('fenlight.refresh_widgets') == 'true'
	random_list, cache_to_memory = get_persistent_content('random_shortcut_folders', folder_name, remake_widgets, is_external)
	if not random_list:
		if len(random_results) > 1: random_list = random.choice(random_results)
		else: random_list = random_results[0]
		random_list.update({'folder_name': folder_name, 'mode': random_list['mode'].replace('random.', '')})
		if cache_to_memory: set_persistent_content('random_shortcut_folders',  folder_name, random_list)
	if random_list.get('random') == 'true': return RandomLists(random_list).run_random()
	if random_list.get('action') in ('tmdb_movies_discover', 'tmdb_tv_discover'): return RandomLists(random_list).run_random()
	menu_type = random_valid_type_check[random_list['mode']]
	list_name = random_list.get('list_name', None) or random_list.get('name', None) or 'Random'
	if is_external: kodi_utils.set_property('fenlight.%s' % folder_name, list_name)
	if menu_type == 'movie':
		return Movies(random_list).fetch_list()
	if menu_type == 'tvshow':
		return TVShows(random_list).fetch_list()
	if menu_type == 'season':
		from indexers.seasons import build_season_list
		return build_season_list(random_list)
	if menu_type == 'episode':
		from indexers.episodes import build_episode_list
		return build_episode_list(random_list)
	if menu_type == 'single_episode':
		from indexers.episodes import build_single_episode
		return build_single_episode(random_episodes_check[random_list['mode']], random_list)
	if menu_type == 'trakt_list':
		from indexers.trakt_lists import build_trakt_list
		return build_trakt_list(random_list)
	return kodi_utils.end_directory(int(sys.argv[1]))
