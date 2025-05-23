# -*- coding: utf-8 -*-
import sys
from modules import kodi_utils, settings
from modules.metadata import tvshow_meta
from modules.utils import get_datetime, adjust_premiered_date, make_thread_list
from modules.watched_status import get_database, watched_info_season, get_watched_status_season, get_progress_status_season
# logger = kodi_utils.logger

def build_season_list(params):
	def _process():
		total_aired_eps, episode_count = meta_get('total_aired_eps'), 0
		for item in season_data:
			try:
				cm = []
				cm_append = cm.append
				listitem = make_listitem()
				set_properties = listitem.setProperties
				item_get = item.get
				overview, poster_path, air_date = item_get('overview'), item_get('poster_path'), item_get('air_date')
				season_number, aired_eps = item_get('season_number'), item_get('episode_count')
				season_name = item_get('name', None)
				season_special = season_number == 0
				title = item_get('name', None) or 'Season %s' % season_number
				if custom_order is not None: title = '%s - %s' % (show_title, title)
				poster = 'https://image.tmdb.org/t/p/w780%s' % poster_path if poster_path is not None else show_poster
				thumb = poster or show_landscape or show_fanart
				try: year = air_date.split('-')[0]
				except: year = show_year or '2050'
				plot = overview or show_plot
				try: premiered = adjust_premiered_date(air_date, adjust_hours)[1]
				except: premiered = ''
				unaired = aired_eps == 0
				if unaired or season_special:
					progress, playcount, total_watched, total_unwatched = 0, 0, 0, aired_eps
					if unaired: title = '[COLOR red][I]%s[/I][/COLOR]' % title
					else: title = 'Specials'
				else:
					if season_number < total_seasons:
						episode_count += aired_eps
					else: aired_eps = total_aired_eps - episode_count
					playcount, watched, unwatched = get_watched_status_season(watched_info.get(season_number, None), aired_eps)
					progress = get_progress_status_season(watched, aired_eps)
				visible_progress = 0 if progress == 100 else progress
				url_params = build_url({'mode': 'build_episode_list', 'tmdb_id': tmdb_id, 'season': season_number})
				extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow', 'is_external': is_external})
				options_params = build_url({'mode': 'options_menu_choice', 'content': 'season', 'tmdb_id': tmdb_id, 'poster': show_poster, 'is_external': is_external})
				cm_append(['extras', ('[B]Extras[/B]', 'RunPlugin(%s)' % extras_params)])
				cm_append(['options', ('[B]Options[/B]', 'RunPlugin(%s)' % options_params)])
				if playcount:
					if hide_watched: continue
				elif not unaired and not season_special:
						cm_append(['mark_watched', ('[B]Mark Watched %s[/B]' % watched_title, 'RunPlugin(%s)' \
								% build_url({'mode': 'watched_status.mark_season', 'action': 'mark_as_watched',
															'title': show_title, 'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season_number}))])
				if progress:
					cm_append(['mark_watched', ('[B]Mark Unwatched %s[/B]' % watched_title, 'RunPlugin(%s)' \
								% build_url({'mode': 'watched_status.mark_season', 'action': 'mark_as_unwatched',
														'title': show_title, 'tmdb_id': tmdb_id, 'tvdb_id': tvdb_id, 'season': season_number}))])
				set_properties({'watchedepisodes': str(watched), 'unwatchedepisodes': str(unwatched)})
				set_properties({'totalepisodes': str(aired_eps), 'watchedprogress': str(visible_progress),
								'fenlight.extras_params': extras_params, 'fenlight.options_params': options_params})
				try: cm = sorted([i for i in cm if i[0] in cm_sort_order], key=lambda k: cm_sort_order[k[0]])
				except: pass
				cm = [i[1] for i in cm]
				if is_external:
					cm.extend([('[B]Refresh Widgets[/B]', 'RunPlugin(%s)' % build_url({'mode': 'refresh_widgets'})),
								('[B]Reload Widgets[/B]', 'RunPlugin(%s)' % build_url({'mode': 'kodi_refresh'}))])
				info_tag = listitem.getVideoInfoTag()
				info_tag.setMediaType('season'), info_tag.setTitle(title), info_tag.setOriginalTitle(orig_title), info_tag.setTvShowTitle(show_title), info_tag.setIMDBNumber(imdb_id)
				info_tag.setSeason(season_number), info_tag.setPlot(plot), info_tag.setDuration(episode_run_time), info_tag.setPlaycount(playcount), info_tag.setGenres(genre)
				info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': str_tmdb_id, 'tvdb': str_tvdb_id})
				info_tag.setTvShowStatus(status), info_tag.setFirstAired(premiered), info_tag.setStudios(studio), info_tag.setYear(int(year))
				info_tag.setRating(rating), info_tag.setVotes(votes), info_tag.setMpaa(mpaa), info_tag.setCountries(country), info_tag.setTrailer(trailer)
				info_tag.setCast([kodi_actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']) for item in cast])
				listitem.setLabel(title)
				listitem.setArt({'poster': poster, 'season.poster': poster, 'fanart': show_fanart, 'clearlogo': show_clearlogo, 'landscape': show_landscape, 'thumb': thumb,
								'icon': show_landscape, 'tvshow.poster': poster, 'tvshow.clearlogo': show_clearlogo})
				listitem.addContextMenuItems(cm)
				yield (url_params, listitem, True)
			except: pass
	kodi_actor, make_listitem, build_url = kodi_utils.kodi_actor(), kodi_utils.make_listitem, kodi_utils.build_url
	poster_empty, fanart_empty = kodi_utils.empty_poster(), kodi_utils.addon_fanart()
	handle, is_external, is_home = int(sys.argv[1]), kodi_utils.external(), kodi_utils.home()
	watched_indicators, adjust_hours, hide_watched = settings.watched_indicators(), settings.date_offset(), is_home and settings.widget_hide_watched()
	current_date = get_datetime()
	cm_sort_order = settings.cm_sort_order()
	rpdb_api_key = settings.rpdb_api_key('tvshow')
	watched_title = 'Trakt' if watched_indicators == 1 else 'Fen Light'
	meta = tvshow_meta('tmdb_id', params['tmdb_id'], settings.tmdb_api_key(), settings.mpaa_region(), current_date)
	meta_get = meta.get
	tmdb_id, tvdb_id, imdb_id, show_title, show_year = meta_get('tmdb_id'), meta_get('tvdb_id'), meta_get('imdb_id'), meta_get('title'), meta_get('year') or '2050'
	orig_title, status, show_plot = meta_get('original_title', ''), meta_get('status'), meta_get('plot')
	str_tmdb_id, str_tvdb_id, rating, genre = str(tmdb_id), str(tvdb_id), meta_get('rating'), meta_get('genre')
	cast, mpaa, votes, trailer, studio, country = meta_get('cast', []), meta_get('mpaa'), meta_get('votes'), str(meta_get('trailer')), meta_get('studio'), meta_get('country')
	episode_run_time, season_data, total_seasons = meta_get('duration'), meta_get('season_data'), meta_get('total_seasons')
	rpdb_api_key = settings.rpdb_api_key('tvshow')
	if rpdb_api_key:
		try: show_poster = meta_get('rpdb_poster') % rpdb_api_key
		except: show_poster = meta_get('poster') or poster_empty
	else: show_poster = meta_get('poster') or poster_empty
	show_fanart = meta_get('fanart') or fanart_empty
	show_clearlogo, show_landscape = meta_get('clearlogo') or '', meta_get('landscape') or ''
	custom_order = params.get('custom_order', None)
	if settings.show_specials(): season_data.sort(key=lambda i: (i['season_number'] == 0, i['season_number']))
	elif custom_order is not None: season_data = [i for i in season_data if i['season_number'] == params['season']]
	else:
		season_data = [i for i in season_data if not i['season_number'] == 0]
		season_data.sort(key=lambda k: k['season_number'])
	watched_info = watched_info_season(tmdb_id, get_database(watched_indicators))
	list_items = list(list(_process()))
	if custom_order is not None: return (list_items[0], custom_order)
	kodi_utils.add_items(handle, list_items)
	kodi_utils.set_content(handle, 'seasons')
	kodi_utils.set_category(handle, show_title)
	kodi_utils.end_directory(handle, cacheToDisc=False if is_external else True)
	kodi_utils.set_view_mode('view.seasons', 'seasons', is_external)

def single_seasons(seasons_list):
	def _process(item): season_results_append(build_season_list(item))
	season_results = []
	season_results_append = season_results.append
	threads = make_thread_list(_process, seasons_list)
	[i.join() for i in threads]
	return [i for i in season_results if i]
