import sys
from modules.kodi_utils import parse_qsl, logger, get_property, get_infolabel, external_browse

def runmode(cls, params, mode):
	call = getattr(cls(params), mode, None)
	return call() if callable(call) else None

class Router:
	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		if get_property('pov_rli_fix') == 'true' and external_browse():
			message = f"pov not in '{get_infolabel('Container.PluginName')}'"
			raise SystemExit(message)

	def routing(self, sys):
		try: params = dict(parse_qsl(sys.argv[2][1:]))
		except Exception as e: return logger('routing error', str(e))

		params_get = params.get
		mode = params_get('mode', 'navigator.main')
		if 'navigator.' in mode:
			from indexers.navigator import Navigator
			runmode(Navigator, params, mode.split('.')[1])
		elif 'menu_editor.' in mode:
			from modules.menu_editor import MenuEditor
			runmode(MenuEditor, params, mode.split('.')[1])
		elif 'discover.' in mode:
			from indexers.discover import Discover
			runmode(Discover, params, mode.split('.')[1])
		elif '_play' in mode or 'play_' in mode:
			if mode == 'play_media':
				from modules.sources import Sources
				Sources().playback_prep(params)
			elif mode == 'media_play':
				from modules.player import POVPlayer
				POVPlayer().run(params_get('url'), params_get('media_type'))
		elif 'choice' in mode:
			from modules import dialogs
			if mode == 'scraper_color_choice':
				dialogs.scraper_color_choice(params['setting'])
			elif mode == 'scraper_dialog_color_choice':
				dialogs.scraper_dialog_color_choice(params['setting'])
			elif mode == 'scraper_quality_color_choice':
				dialogs.scraper_quality_color_choice(params['setting'])
			elif mode == 'imdb_images_choice':
				dialogs.imdb_images_choice(params['imdb_id'], params['rootname'])
			elif mode == 'set_quality_choice':
				dialogs.set_quality_choice(params['quality_setting'])
			elif mode == 'results_sorting_choice':
				dialogs.results_sorting_choice()
			elif mode == 'results_layout_choice':
				dialogs.results_layout_choice()
			elif mode == 'options_menu_choice':
				dialogs.options_menu(params)
			elif mode == 'meta_language_choice':
				dialogs.meta_language_choice()
			elif mode == 'extras_menu_choice':
				dialogs.extras_menu(params)
			elif mode == 'enable_scrapers_choice':
				dialogs.enable_scrapers_choice()
			elif mode == 'favourites_choice':
				dialogs.favourites_choice(params)
			elif mode == 'trakt_manager_choice':
				dialogs.trakt_manager_choice(params)
			elif mode == 'tmdb_manager_choice':
				dialogs.tmdb_manager_choice(params)
			elif mode == 'mdb_manager_choice':
				dialogs.mdb_manager_choice(params)
			elif mode == 'folder_scraper_manager_choice':
				dialogs.folder_scraper_manager_choice()
			elif mode == 'set_language_filter_choice':
				dialogs.set_language_filter_choice(params['filter_setting'])
			elif mode == 'media_extra_info_choice':
				dialogs.media_extra_info(params['media_type'], params['meta'])
			elif mode == 'extras_lists_choice':
				dialogs.extras_lists_choice()
			elif mode == 'random_choice':
				dialogs.random_choice(params['mode'], params)
		elif 'trakt.' in mode:
			if 'trakt_account_info' in mode:
				from indexers.trakt import trakt_account_info
				trakt_account_info()
			elif 'hide_unhide_trakt_items' in mode:
				from apis.trakt_api import hide_unhide_trakt_items
				hide_unhide_trakt_items(params['action'], params['media_type'], params['media_id'], params['section'])
			else:
				from modules.utils import manual_function_import
				function = manual_function_import('apis.trakt_api', mode.split('.')[-1])
				function(params)
		elif 'tmdb.' in mode:
			if 'edit_tmdb_list' in mode:
				from indexers.tmdb import edit_tmdb_list
				edit_tmdb_list(params)
			elif 'update_tmdb_list' in mode:
				from indexers.tmdb import update_tmdb_list
				update_tmdb_list(params)
			else:
				from modules.utils import manual_function_import
				function = manual_function_import('apis.tmdb_api', mode.split('.')[-1])
				function(params)
		elif 'build' in mode:
			if 'build_trakt_list' in mode:
				from modules.utils import manual_function_import
				function = manual_function_import('indexers.trakt', mode.split('.')[-1])
				function(params)
			elif 'build_mdb_list' in mode:
				from modules.utils import manual_function_import
				function = manual_function_import('indexers.mdblist', mode.split('.')[-1])
				function(params)
			elif 'build_tmdb_list' in mode:
				from modules.utils import manual_function_import
				function = manual_function_import('indexers.tmdb', mode.split('.')[-1])
				function(params)
			elif mode == 'build_movie_list':
				from indexers.movies import Indexer
				Indexer(params).run()
			elif mode == 'build_tvshow_list':
				from indexers.tvshows import Indexer
				Indexer(params).run()
			elif mode == 'build_season_list':
				from indexers.seasons import Seasons
				Seasons(params).run()
			elif mode == 'build_episode_list':
				from indexers.seasons import Seasons
				Seasons(params).run()
			elif mode == 'build_in_progress_episode':
				from indexers.episodes import Indexer
				Indexer(params).run()
			elif mode == 'build_next_episode':
				from indexers.episodes import Indexer
				Indexer(params).run()
			elif mode == 'build_my_calendar':
				from indexers.episodes import Indexer
				Indexer(params).run()
			elif mode == 'build_my_anime_calendar':
				from indexers.episodes import Indexer
				Indexer(params).run()
			elif mode == 'build_anime_calendar':
				from indexers.episodes import Indexer
				Indexer(params).run()
			elif mode == 'build_navigate_to_page':
				from modules.dialogs import build_navigate_to_page
				build_navigate_to_page(params)
			elif mode == 'imdb_build_user_lists':
				from apis.imdb_api import imdb_build_user_lists
				imdb_build_user_lists(params_get('media_type'))
			elif mode == 'build_popular_people':
				from indexers.people import popular_people
				popular_people()
			elif mode == 'imdb_build_keyword_results':
				from apis.imdb_api import imdb_build_keyword_results
				imdb_build_keyword_results(params['media_type'], params['query'])
		elif 'watched_unwatched' in mode:
			if mode == 'mark_as_watched_unwatched_episode':
				from caches.watched_cache import mark_as_watched_unwatched_episode
				mark_as_watched_unwatched_episode(params)
			elif mode == 'mark_as_watched_unwatched_season':
				from caches.watched_cache import mark_as_watched_unwatched_season
				mark_as_watched_unwatched_season(params)
			elif mode == 'mark_as_watched_unwatched_tvshow':
				from caches.watched_cache import mark_as_watched_unwatched_tvshow
				mark_as_watched_unwatched_tvshow(params)
			elif mode == 'mark_as_watched_unwatched_movie':
				from caches.watched_cache import mark_as_watched_unwatched_movie
				mark_as_watched_unwatched_movie(params)
			elif mode == 'watched_unwatched_erase_bookmark':
				from caches.watched_cache import erase_bookmark
				erase_bookmark(params_get('media_type'), params_get('tmdb_id'), params_get('season', ''), params_get('episode', ''), params_get('refresh', 'false'))
		elif 'toggle' in mode:
			if mode == 'toggle_jump_to':
				from modules.kodi_utils import toggle_jump_to
				toggle_jump_to()
			elif mode == 'toggle_provider':
				from modules.utils import toggle_provider
				toggle_provider()
			elif mode == 'toggle_language_invoker':
				from modules.kodi_utils import toggle_language_invoker
				toggle_language_invoker()
		elif 'history' in mode:
			if mode == 'search_history':
				from indexers.history import search_history
				search_history(params)
			elif mode == 'clear_search_history':
				from indexers.history import clear_search_history
				clear_search_history()
			elif mode == 'remove_from_history':
				from indexers.history import remove_from_search_history
				remove_from_search_history(params)
			elif mode == 'discover_remove_from_history':
				from indexers.discover import remove_from_history
				remove_from_history(params)
			elif mode == 'discover_remove_all_history':
				from indexers.discover import remove_all_history
				remove_all_history(params)
		elif 'easynews.' in mode:
			from modules.utils import manual_function_import
			function = manual_function_import('indexers.easynews', mode.split('.')[-1])
			function(params)
		elif 'alldebrid' in mode:
			if mode == 'alldebrid.ad_torrent_cloud':
				from indexers.alldebrid import ad_torrent_cloud
				ad_torrent_cloud(params_get('id'))
			elif mode == 'alldebrid.browse_ad_cloud':
				from indexers.alldebrid import browse_ad_cloud
				browse_ad_cloud(params['folder'])
			elif mode == 'alldebrid.resolve_ad':
				from indexers.alldebrid import resolve_ad
				resolve_ad(params)
			elif mode == 'alldebrid.show_account_info':
				from indexers.alldebrid import show_account_info
				show_account_info()
		elif 'premiumize' in mode:
			from indexers.premiumize import Indexer
			Indexer().run(params)
		elif 'real_debrid' in mode:
			from indexers.real_debrid import Indexer, resolve_rd
			if 'resolve_' in mode: resolve_rd(params)
			else: Indexer().run(params)
		elif 'torbox' in mode:
			from indexers.torbox import Indexer, resolve_tb
			if 'resolve_' in mode: resolve_tb(params)
			else: Indexer().run(params)
		elif 'offcloud' in mode:
			from indexers.offcloud import Indexer
			Indexer().run(params)
		elif 'easydebrid' in mode:
			from indexers.easydebrid import Indexer
			Indexer().run(params)
		elif '_settings' in mode:
			if mode == 'open_settings':
				from modules.kodi_utils import open_settings
				open_settings(params_get('query'))
			elif mode == 'clean_settings':
				from modules.kodi_utils import clean_settings
				clean_settings()
			elif mode == 'clean_settings_window_properties':
				from modules.kodi_utils import clean_settings_window_properties
				clean_settings_window_properties()
		elif '_cache' in mode:
			from modules import cache_utils
			if mode == 'clear_all_cache':
				cache_utils.clear_all_cache()
			else:
				cache_utils.clear_cache(params_get('cache'))
		elif '_image' in mode:
			from indexers.images import Images
			Images().run(params)
		elif '_text' in mode:
			from modules.kodi_utils import show_text
			show_text(params_get('heading'), params_get('text'), params_get('file'), params_get('font_size', 'small'), params_get('kodi_log', 'false') == 'true')
		elif '_view' in mode:
			if mode == 'choose_view':
				from modules.kodi_utils import choose_view
				choose_view(params['view_type'], params_get('content', ''))
			elif mode == 'set_view':
				from modules.kodi_utils import set_view
				set_view(params['view_type'])
			elif mode == 'clear_view':
				from modules.kodi_utils import clear_view
				clear_view(params['view_type'])
		##EXTRA modes##
		elif mode == 'get_search_term':
			from indexers.history import get_search_term
			get_search_term(params)
		elif mode == 'person_search':
			from indexers.people import person_search
			person_search(params['query'])
		elif 'person_data_dialog' in mode:
			from indexers.people import person_data_dialog
			person_data_dialog(params)
		elif mode == 'downloader':
			from modules.downloader import runner
			runner(params)
		elif mode == 'clean_databases':
			from modules.cache_utils import clean_databases
			clean_databases()
		elif mode == 'clean_thumbnails':
			from modules.thumbnails import thumb_cleaner
			thumb_cleaner()
		elif mode == 'manual_add_magnet_to_cloud':
			from modules.debrid import manual_add_magnet_to_cloud
			manual_add_magnet_to_cloud(params)
		elif mode == 'manual_add_nzb_to_cloud':
			from modules.debrid import manual_add_nzb_to_cloud
			manual_add_nzb_to_cloud(params)
		elif mode == 'debrid.browse_packs':
			from modules.sources import Sources
			Sources().debridPacks(params['provider'], params['name'], params['magnet_url'], params['info_hash'], params['highlight'])
		elif mode == 'upload_logfile':
			from modules.kodi_utils import upload_logfile
			upload_logfile()
		elif mode == 'myservices':
			from modules.myservices import authorize
			authorize(params['action'])
		##FENOM modes###
		elif mode == 'undesirablesInput':
			from caches.undesirables_cache import undesirablesInput
			undesirablesInput()
		elif mode == 'undesirablesUserRemove':
			from caches.undesirables_cache import undesirablesUserRemove
			undesirablesUserRemove()
		elif mode == 'speedTest':
			from fenom.speedtest import magneto
			magneto()


if __name__ == '__main__':
	with Router() as r: r.routing(sys)

