# -*- coding: utf-8 -*-
import sys
from threading import Thread
from apis.trakt_api import trakt_get_lists, trakt_search_lists, get_trakt_list_contents, trakt_lists_with_media
from indexers.movies import Movies
from indexers.tvshows import TVShows
from indexers.seasons import single_seasons
from indexers.episodes import build_single_episode
from modules import kodi_utils
from modules.utils import paginate_list
from modules.settings import paginate, page_limit
logger = kodi_utils.logger

from apis.tmdblist_api import tmdb_list_api

def get_tmdb_lists(params):
	def _process():
		for item in data['results']:
			try:
				cm = []
				cm_append = cm.append
				item_count = item['number_of_items']
				list_name = ' '.join(w.capitalize() for w in item['name'].split())
				# mode = 'random.build_tmdb_lists_contents' if random else 'tmdblist.build_tmdb_list'
				mode = 'tmdblist.build_tmdb_list'
				url_params = {'mode': mode, 'list_id': item['id']}
				if random: url_params['random'] = 'true'
				url = kodi_utils.build_url(url_params)
				display = '%s [I](x%02d)[/I]' % (list_name, item_count)
				# cm_append(('[B]Make New List[/B]', 'RunPlugin(%s)' % kodi_utils.build_url({'mode': 'trakt.make_new_trakt_list'})))
				# cm_append(('[B]Delete List[/B]', 'RunPlugin(%s)' % kodi_utils.build_url({'mode': 'trakt.delete_trakt_list'})))
				listitem = kodi_utils.make_listitem()
				listitem.setLabel(display)
				listitem.setArt({'icon': icon, 'poster': icon, 'thumb': icon, 'fanart': fanart, 'banner': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.addContextMenuItems(cm)
				yield (url, listitem, True)
			except: pass
	handle, icon, fanart = int(sys.argv[1]), kodi_utils.get_icon('tmdb'), kodi_utils.get_addon_fanart()
	# try:
	random = params.get('random', 'false') == 'true'
	data = tmdb_list_api.get_user_lists()
	page, total_pages = data['page'], data['total_pages']
	kodi_utils.add_items(handle, list(_process()))
	# except: pass
	kodi_utils.set_content(handle, 'files')
	kodi_utils.set_category(handle, params.get('category_name', ''))
	kodi_utils.set_sort_method(handle, 'label')
	kodi_utils.end_directory(handle)
	kodi_utils.set_view_mode('view.main')


def build_tmdb_list(params):
	logger('params', params)
	result = tmdb_list_api.get_list_details(params['list_id'])
	logger('result', result)
	def _process(function, _list, _type):
		if not _list['list']: return
		item_list_extend(function(_list).worker())
	def _paginate_list(data, page_no, paginate_start):
		if use_result: total_pages = 1
		elif paginate_enabled:
			limit = page_limit(is_home)
			data, total_pages = paginate_list(data, page_no, limit, paginate_start)
			if is_home: paginate_start = limit
		else: total_pages = 1
		return data, total_pages, paginate_start
	handle, is_external, is_home, list_name = int(sys.argv[1]), kodi_utils.external(), kodi_utils.home(), params.get('list_name')
	# try:
	threads, item_list = [], []
	item_list_extend = item_list.extend
	user, slug, list_type = '', '', ''
	paginate_enabled = paginate(is_home)
	use_result = 'result' in params
	list_id = params.get('list_id')
	page_no, paginate_start = int(params.get('new_page', '1')), int(params.get('paginate_start', '0'))
	if page_no == 1 and not is_external: kodi_utils.set_property('fenlight.exit_params', kodi_utils.folder_path())
	if use_result: result = params.get('result', [])
	else: result = tmdb_list_api.get_list_details(list_id, page_no)
	# process_list, total_pages, paginate_start = _paginate_list(result, page_no, paginate_start)
	# all_movies = [dict(i, **{'order': c}) for c, i in enumerate(process_list) if i['media_type'] == 'movie']
	# all_tvshows = [dict(i, **{'order': c}) for c, i in enumerate(process_list) if i['media_type'] == 'tv']
	all_movies = [dict(i, **{'order': c}) for c, i in enumerate(result['results']) if i['media_type'] == 'movie']
	all_tvshows = [dict(i, **{'order': c}) for c, i in enumerate(result['results']) if i['media_type'] == 'tv']
	movie_list = {'list': [(i['order'], i['id']) for i in all_movies], 'custom_order': 'true'}
	tvshow_list = {'list': [(i['order'], i['id']) for i in all_tvshows], 'custom_order': 'true'}
	logger('movie_list', movie_list)
	logger('tvshow_list', tvshow_list)
	content = max([('movies', len(all_movies)), ('tvshows', len(all_tvshows))], key=lambda k: k[1])[0]
	for item in ((Movies, movie_list, 'movies'), (TVShows, tvshow_list, 'tvshows')):
		threaded_object = Thread(target=_process, args=item)
		threaded_object.start()
		threads.append(threaded_object)
	[i.join() for i in threads]
	if use_result: return content, [i[0] for i in item_list]
	item_list.sort(key=lambda k: k[1])
	logger('item_list', item_list)
	kodi_utils.add_items(handle, [i[0] for i in item_list])
	# if total_pages > page_no:
	# 	new_page = str(page_no + 1)
	# 	new_params = {'mode': 'trakt.list.build_trakt_list', 'list_id': list_id, 'paginate_start': paginate_start, 'new_page': new_page}
	# 	kodi_utils.add_dir(new_params, 'Next Page (%s) >>' % new_page, handle, 'nextpage', kodi_utils.nextpage_landscape())
	# except: pass
	kodi_utils.set_content(handle, content)
	kodi_utils.set_category(handle, list_name)
	kodi_utils.end_directory(handle, cacheToDisc=False if is_external else True)
	if not is_external:
		if params.get('refreshed') == 'true': kodi_utils.sleep(1000)
		kodi_utils.set_view_mode('view.%s' % content, content, is_external)
