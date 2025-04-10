# -*- coding: utf-8 -*-
import sys
import json
from threading import Thread
from urllib.parse import unquote
from caches.personal_lists_cache import personal_lists_cache, get_timestamp
from indexers.movies import Movies
from indexers.tvshows import TVShows
from modules import kodi_utils
from modules.utils import paginate_list, sort_for_article
from modules.settings import paginate, page_limit
logger = kodi_utils.logger

def get_personal_lists(params):
	def _process():
		for item in personal_lists:
			try:
				cm = []
				cm_append = cm.append
				list_name, sort_order, list_total = item['name'], item['sort_order'], item['total']
				mode = 'random.build_personal_lists_contents' if random else 'personal_lists.build_personal_list'
				url_params = {'mode': mode, 'list_name': list_name, 'category_name': list_name, 'sort_order': sort_order}
				if random: url_params['random'] = 'true'
				url = build_url(url_params)
				cm = [('[B]Edit List Properties[/B]', 'RunPlugin(%s)' % build_url({'mode': 'personal_lists.adjust_personal_list_properties',
					'original_list_name': list_name,
				'original_sort_order': sort_order, 'list_total': list_total})),
				('[B]Make New List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'personal_lists.make_new_personal_list'})),
				('[B]Delete List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'personal_lists.delete_personal_list', 'list_name': list_name})),
				('[B]Empty List Contents[/B]', 'RunPlugin(%s)' % build_url({'mode': 'personal_lists.delete_personal_list_contents', 'list_name': list_name})),
				('[B]Import Trakt List[/B]', 'RunPlugin(%s)' % build_url({'mode': 'personal_lists.import_trakt_list', 'list_name': list_name}))]
				listitem = kodi_utils.make_listitem()
				listitem.setLabel('%s (x%02d)' % (list_name, list_total))
				listitem.setArt({'icon': icon, 'poster': icon, 'thumb': icon, 'fanart': fanart, 'banner': fanart})
				info_tag = listitem.getVideoInfoTag()
				info_tag.setPlot(' ')
				listitem.addContextMenuItems(cm)
				yield (url, listitem, True)
			except: pass
	def _new_process():
		url = build_url({'mode': 'personal_lists.make_new_personal_list'})
		new_icon = kodi_utils.get_icon('new')
		listitem = kodi_utils.make_listitem()
		listitem.setLabel('[I]Make New Personal List...[/I]')
		listitem.setArt({'icon': new_icon, 'poster': new_icon, 'thumb': new_icon, 'fanart': fanart, 'banner': fanart})
		info_tag = listitem.getVideoInfoTag()
		info_tag.setPlot(' ')
		yield (url, listitem, False)
	icon = kodi_utils.get_icon('lists')
	build_url = kodi_utils.build_url
	random = params.get('random', 'false') == 'true'
	try:
		handle = int(sys.argv[1])
		fanart = kodi_utils.get_addon_fanart()
		personal_lists = get_all_personal_lists()
		if personal_lists: kodi_utils.add_items(handle, list(_process()))
		else: kodi_utils.add_items(handle, list(_new_process()))
	except: pass
	kodi_utils.set_content(handle, 'files')
	kodi_utils.set_category(handle, 'Personal Lists')
	kodi_utils.set_sort_method(handle, 'label')
	kodi_utils.end_directory(handle)
	kodi_utils.set_view_mode('view.main')

def build_personal_list(params):
	def _process(function, _list):
		item_list_extend(function(_list).worker())
	def _paginate_list(data, page_no, paginate_start):
		if use_result: total_pages = 1
		elif paginate_enabled:
			limit = page_limit(is_home)
			data, total_pages = paginate_list(data, page_no, limit, paginate_start)
			if is_home: paginate_start = limit
		else: total_pages = 1
		return data, total_pages, paginate_start
	handle, is_external, is_home = int(sys.argv[1]), kodi_utils.external(), kodi_utils.home()
	try:
		threads, item_list, content = [], [], 'movies'
		item_list_extend = item_list.extend
		paginate_enabled = paginate(is_home)
		use_result = 'result' in params
		page_no, paginate_start = int(params.get('new_page', '1')), int(params.get('paginate_start', '0'))
		if page_no == 1 and not is_external: kodi_utils.set_property('fenlight.exit_params', kodi_utils.folder_path())
		if use_result: result = params.get('result', [])
		else: result = get_personal_list(params)
		process_list, total_pages, paginate_start = _paginate_list(result, page_no, paginate_start)
		movie_list = {'list': [(c, i['media_id']) for c, i in enumerate(process_list) if i['type'] == 'movie'], 'custom_order': 'true'}
		tvshow_list = {'list': [(c, i['media_id']) for c, i in enumerate(process_list) if i['type'] == 'tvshow'], 'custom_order': 'true'}
		content = 'movies' if len(movie_list['list']) > len(tvshow_list['list']) else 'tvshows'
		for item in ((Movies, movie_list), (TVShows, tvshow_list)):
			if not item[1]['list']: continue
			threaded_object = Thread(target=_process, args=item)
			threaded_object.start()
			threads.append(threaded_object)
		[i.join() for i in threads]
		if use_result: return content, [i[0] for i in item_list]
		item_list.sort(key=lambda k: k[1])
		list_name, sort_order = params.get('list_name'), params.get('sort_order')
		kodi_utils.add_items(handle, [i[0] for i in item_list])
		if total_pages > page_no:
			new_page = str(page_no + 1)
			new_params = {'mode': 'personal_lists.build_personal_list', 'list_name': list_name, 'sort_order': sort_order,
			'paginate_start': paginate_start, 'new_page': new_page}
			kodi_utils.add_dir(new_params, 'Next Page (%s) >>' % new_page, handle, 'nextpage', kodi_utils.nextpage_landscape())
	except: pass
	kodi_utils.set_content(handle, content)
	kodi_utils.set_category(handle, list_name)
	kodi_utils.end_directory(handle, cacheToDisc=False if is_external else True)
	if not is_external:
		if params.get('refreshed') == 'true': kodi_utils.sleep(1000)
		kodi_utils.set_view_mode('view.%s' % content, content, is_external)

def make_new_personal_list(list_name, sort_order):
	return personal_lists_cache.make_list(list_name, sort_order)

def get_all_personal_lists():
	return personal_lists_cache.get_lists()

def delete_personal_list(params):
	list_name = params.get('list_name', '')
	if not kodi_utils.confirm_dialog(heading='Personal Lists', text='Delete [B]%s[/B] Personal List?' % list_name): return
	if personal_lists_cache.delete_list(list_name): return kodi_utils.kodi_refresh()
	kodi_utils.notification('Error Deleting List', 3000)

def delete_personal_list_contents(params):
	list_name = params.get('list_name', '')
	if not kodi_utils.confirm_dialog(heading='Personal Lists', text='Delete all the contents of [B]%s[/B] Personal List?' % list_name): return
	if personal_lists_cache.delete_list_contents(list_name): return kodi_utils.kodi_refresh()
	kodi_utils.notification('Error Deleting List Contents', 3000)

def get_personal_list(params):
	list_name, sort_order = params['list_name'], params['sort_order']
	contents = personal_lists_cache.get_list(list_name)
	try:
		if sort_order in ('', '0', 'None', '1'):
			contents = sort_for_article(contents, 'title')
		elif sort_order in ('1', '2'):
			reverse = sort_order != '1'
			contents.sort(key=lambda k: k['date_added'], reverse=reverse)
		else:
			reverse = sort_order != '3'
			contents.sort(key=lambda k: (k['release_date'] is None, k['release_date']), reverse=reverse)
	except: pass
	return contents

def make_new_personal_list(params):
	def cancel_or_retry(dialog):
		if kodi_utils.confirm_dialog(heading='Personal Lists', text='Re-enter [B]%s[/B] Value or Cancel Making List?' % dialog, ok_label='Re-enter', default_control=10):
			return make_new_personal_list(params)
		return None, None, None
	list_name, sort_order = params.get('list_name', ''), params.get('sort_order', '')
	if not list_name:
		list_name = personal_list_name(list_name)
		if list_name == None: return cancel_or_retry('List Name')
		params['list_name'] = list_name
	if not sort_order:
		sort_order = personal_sort_order()
		if sort_order == None: return cancel_or_retry('Sort Order')
		params['sort_order'] = sort_order
	success = personal_lists_cache.make_list(list_name, sort_order)
	if not success:
		kodi_utils.notification('Error Creating List', 3000)
		return None, None, None
	if params.get('refresh', 'true') == 'true' and any([kodi_utils.path_check('get_personal_lists') or kodi_utils.external()]): kodi_utils.kodi_refresh()
	return list_name, sort_order

def adjust_personal_list_properties(params):
	sort_order_dict = {'0': 'Title', '1': 'Date Added (asc)', '2': 'Date Added (desc)', '3': 'Release Date (asc)', '4': 'Release Date (desc)'}
	original_list_name, original_sort_order = params.get('original_list_name', ''), params.get('original_sort_order', '')
	list_name, list_total, sort_order = params.get('list_name', ''), params.get('list_total', '0'), params.get('sort_order', '')
	current_name, current_sort_order = list_name or original_list_name, sort_order or original_sort_order
	choices = [('List Name', 'Currently [B]%s[/B]' % (current_name), 'list_name'),
				('List Sort Order', 'Currently [B]%s[/B]' % sort_order_dict[current_sort_order], 'sort_order')]
	list_items = [{'line1': item[0], 'line2': item[1] or item[0]} for item in choices]
	kwargs = {'items': json.dumps(list_items), 'heading': 'Personal List Properties', 'multi_line': 'true', 'narrow_window': 'true'}
	action = kodi_utils.select_dialog([i[2] for i in choices], **kwargs)
	if action == None: return kodi_utils.kodi_refresh() if params.get('refresh', 'false') == 'true' else None
	if action == 'list_name':
		list_name = personal_list_name(current_name)
		if list_name == None: return adjust_personal_list_properties(params)
		current_name = list_name
		params.update({'list_name': current_name, 'refresh': 'true'})
	elif action == 'sort_order':
		sort_order = personal_sort_order()
		if sort_order == None: return adjust_personal_list_properties(params)
		current_sort_order = sort_order
		params.update({'sort_order': current_sort_order, 'refresh': 'true'})
	personal_lists_cache.update_list_details(current_name, current_sort_order, original_list_name)
	return adjust_personal_list_properties(params)

def import_trakt_list(params):
	from apis.trakt_api import get_trakt_list_selection, trakt_fetch_collection_watchlist, get_trakt_list_contents
	media_type_check = {'movie': 'movie', 'show': 'tvshow', 'tvshow': 'tvshow'}
	list_name = params.get('list_name', '')
	chosen_list = get_trakt_list_selection(include_all=True)
	if chosen_list == None: return
	trakt_list_type, trakt_list_name = chosen_list.get('list_type'), chosen_list.get('name')
	logger('trakt_list_name', trakt_list_name)
	new_contents = []
	new_contents_append = new_contents.append
	current_time = get_timestamp()
	if trakt_list_type in ('collection', 'watchlist'):
		trakt_media_type = chosen_list.get('media_type')
		result = trakt_fetch_collection_watchlist(trakt_list_type, trakt_media_type)
		try: result.sort(key=lambda k: (k['collected_at']))
		except: pass
	else:
		result = get_trakt_list_contents(trakt_list_type, chosen_list.get('user'), chosen_list.get('slug'), trakt_list_type == 'my_lists')
		try: result.sort(key=lambda k: (k['order']))
		except: pass
	for count, item in enumerate(result):
		try:
			media_type = item.get('type') or media_type_check[trakt_media_type]
			if trakt_list_type in ('my_lists', 'liked_lists') and item['type'] not in ('movie', 'show'): continue
			media_id = item['media_ids']['tmdb']
			if media_id in (None, 'None', ''): continue
			title = item['title']
			try: release_date = item['released'].split('T')[0]
			except: release_date = item['released']
			date_added = current_time + count
			new_contents_append({'media_id': str(media_id), 'title': title, 'type': media_type_check[media_type],
								'release_date': release_date, 'date_added': str(date_added)})
		except: continue
	result = personal_lists_cache.add_many_list_items(new_contents, list_name)
	kodi_utils.notification(result, 3000)
	if any([kodi_utils.path_check('get_personal_lists') or kodi_utils.external()]): kodi_utils.kodi_refresh()

def personal_list_name(current_name=''):
	list_name = kodi_utils.kodi_dialog().input('Please Choose a Name for the New List', defaultt=current_name)
	if not list_name: return None
	list_name = unquote(list_name)
	return list_name

def personal_sort_order():
	choices = [('Title (asc)', '0'), ('Date Added (asc)', '1'), ('Date Added (desc)', '2'), ('Release Date (asc)', '3'), ('Release Date (desc)', '4')]
	list_items = [{'line1': item[0]} for item in choices]
	kwargs = {'items': json.dumps(list_items), 'heading': 'List Sort Order', 'narrow_window': 'true'}
	sort_order = kodi_utils.select_dialog([i[1] for i in choices], **kwargs)
	if sort_order == None: return None
	return sort_order
