# -*- coding: utf-8 -*-
from windows.base_window import BaseDialog
from apis import tmdb_api
from caches.discover_cache import discover_cache
from modules import kodi_utils, meta_lists
from modules.utils import safe_string, remove_accents
# from modules.kodi_utils import logger

json, dialog, select_dialog, ok_dialog, get_icon = kodi_utils.json, kodi_utils.dialog, kodi_utils.select_dialog, kodi_utils.ok_dialog, kodi_utils.get_icon
sleep, container_refresh, tmdb_api_key = kodi_utils.sleep, kodi_utils.container_refresh, kodi_utils.tmdb_default_api
years_movies, years_tvshows, movie_genres, tvshow_genres = meta_lists.years_movies, meta_lists.years_tvshows, meta_lists.movie_genres, meta_lists.tvshow_genres
movie_certifications, networks, movie_certifications = meta_lists.movie_certifications, meta_lists.networks, meta_lists.movie_certifications
watch_providers_movies, watch_providers_tvshows = meta_lists.watch_providers_movies, meta_lists.watch_providers_tvshows
movie_sorts, tvshow_sorts, discover_items = meta_lists.movie_sorts, meta_lists.tvshow_sorts, meta_lists.discover_items

base_url = 'https://api.themoviedb.org/3/discover/%s?api_key=%s&language=en-US&region=US&with_original_language=en%s%s'
filter_list_id = 2100
button_ids = (10, 11)
button_actions = {10: 'Save and Exit', 11: 'Exit'}
default_key_values = ('key', 'display_key')
empty_list_label = '[B]***Set Properties to make List***[/B]'

class Discover(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, *args)
		self.set_attributes_status()
		self.set_starting_constants(kwargs)

	def onInit(self):
		self.make_menu()

	def run(self):
		self.doModal()
		self.clearProperties()

	def onClick(self, controlID):
		if controlID == filter_list_id:
			self.position = self.get_position(filter_list_id)
			try:
				self.chosen_item = discover_items[self.get_listitem(controlID).getProperty('key')]
				if self.selection_action(): exec('self.%s()' % self.chosen_item['action'])
				if self.remake: self.make_menu()
			except:
				self.chosen_item = None
				return
		elif controlID in button_ids:
			refresh_listings = False
			if controlID == 10:
				label = dialog.input('List Name', defaultt=self.label)
				if not label: return
				refresh_listings = True
				discover_cache.insert_one(label, self.media_type, self.url)
			self.close()
			if refresh_listings:
				sleep(500)
				container_refresh()

	def make_menu(self):
		def builder():
			for key, values in discover_items.items():
				if 'limited' in values and values['limited'] != self.media_type: continue
				if 'certification' in key:
					if key == 'certification' and self.certification_and_lower: continue
					if key == 'certification_and_lower' and self.certification: continue
				if self.media_type == 'tvshow':
					if key == 'with_network' and self.with_provider: continue
					if key == 'with_provider' and self.with_network: continue
				listitem = self.make_listitem()
				listitem.setProperty('label1', values['label'])
				try: listitem.setProperty('label2', self.get_attribute(self, values['display_key']))
				except: pass
				try: listitem.setProperty('icon', get_icon(values['icon']))
				except: listitem.setProperty('icon', get_icon('discover'))
				listitem.setProperty('key', key)
				yield listitem
		if self.remake:
			self.remake = False
			self.reset_window(filter_list_id)
			self.add_items(filter_list_id, list(builder()))
			self.select_item(filter_list_id, self.position)
			active_attributes = self.get_active_attributes()
			if active_attributes:
				self.make_url(active_attributes)
				self.make_label(active_attributes)
			self.set_attributes_status('true' if active_attributes else 'false')
		else:
			self.add_items(filter_list_id, list(builder()))
			self.setFocusId(filter_list_id)

	def selection_action(self):
		current_value = self.get_attribute(self, self.chosen_item['display_key'])
		if not current_value: return True
		clear_value = kodi_utils.confirm_dialog(heading='Discover', text='Value of [B]%s[/B] already exists.[CR]Change current value or Clear current value?' % current_value,
												ok_label='Clear', cancel_label='Change', default_control=11)
		if not clear_value: return True
		self.set_key_values('', '')
		return False

	def years(self):
		years = years_movies if self.media_type == 'movie' else years_tvshows
		if self.chosen_item['key'] == 'with_year_start' and self.with_year_end_display: years = [i for i in years if i['id'] <= int(self.with_year_end_display)]
		elif self.with_year_start_display: years = [i for i in years if i['id'] >= int(self.with_year_start_display)]
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in years], years)
		if choice != None: self.set_key_values(self.chosen_item['url_insert_%s' % self.media_type] % str(choice['id']), str(choice['id']))

	def genres(self):
		genres = movie_genres if self.media_type == 'movie' else tvshow_genres
		if self.chosen_item['key'] == 'with_genres' and self.without_genres_display: genres = [i for i in genres if not i['name'] in self.without_genres_display.split(', ')]
		elif self.with_genres_display: genres = [i for i in genres if not i['name'] in self.with_genres_display.split(', ')]
		choice = self.multiselect_dialog(self.chosen_item['label'], [{'name': i['name'], 'icon': get_icon(i['icon'])} for i in genres], genres)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % ','.join([i['id'] for i in choice]), ', '.join([i['name'] for i in choice]))

	def keywords(self):
		keyword = dialog.input(self.chosen_item['label'])
		if not keyword: return
		try: result = tmdb_api.tmdb_keywords_by_query(keyword, 1)['results']
		except: result = None
		if not result: return ok_dialog()
		choice = self.multiselect_dialog(self.chosen_item['label'], [{'name': i['name']} for i in result], result)
		if choice != None:
			self.set_key_values(self.chosen_item['url_insert'] % ','.join([str(i['id']) for i in choice]), ', '.join([i['name'] for i in choice]))

	def provider(self):
		providers = watch_providers_movies if self.media_type == 'movie' else watch_providers_tvshows
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in providers], providers)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % str(choice['id']), str(choice['name']))

	def network(self):
		network_list = sorted(networks, key=lambda k: k['name'])
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in network_list], network_list)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % str(choice['id']), str(choice['name']))

	def certifications(self):
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in movie_certifications], movie_certifications)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % str(choice['id']), str(choice['name']))

	def certification_and_lowers(self):
		movie_and_lower_certifications = [{'name': '%s and lower' % i['name'], 'id': i['id']} for i in movie_certifications if not i['id'] == 'g']
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in movie_and_lower_certifications], movie_and_lower_certifications)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % str(choice['id']), str(choice['name']))

	def ratings(self):
		ratings = [{'name': str(float(i)), 'id': str(i)} for i in range(1,11)]
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in ratings], ratings)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % choice['id'], choice['name'])

	def votes(self):
		votes = [{'name': '1', 'id': '1'}] + [{'name': str(i), 'id': str(i)} for i in range(50, 1001, 50)]
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in votes], votes)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % choice['id'], choice['name'])

	def casts(self):
		result, actor_id, search_name = None, None, None
		search_name = dialog.input(self.chosen_item['label'])
		if not search_name: return
		try: result = tmdb_api.tmdb_people_info(search_name)['results']
		except: result = None
		if not result: return ok_dialog()
		actor_list = []
		append = actor_list.append
		if len(result) > 1:
			for item in result:
				name = item['name']
				known_for_list = [i.get('title') for i in item['known_for'] if i.get('title', 'NA') != 'NA']
				known_for = ', '.join(known_for_list) if known_for_list else ''
				if item.get('profile_path'): icon = 'https://image.tmdb.org/t/p/h632/%s' % item['profile_path']
				else: icon = get_icon('genre_family')
				append({'line1': name, 'line2': known_for, 'icon': icon, 'name': name, 'id': item['id']})
			kwargs = {'items': json.dumps(actor_list), 'heading': self.chosen_item['label'], 'enumerate': 'false', 'multi_line': 'true'}
			choice = select_dialog(actor_list, **kwargs)
		else: choice = result[0]
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % choice['id'], choice['name'])

	def sort(self):
		if self.media_type == 'movie': sort_by_list = movie_sorts
		else: sort_by_list = tvshow_sorts
		choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in sort_by_list], sort_by_list)
		if choice != None: self.set_key_values(self.chosen_item['url_insert'] % choice['id'], choice['name'])

	def released(self):
		current_attribute_value = self.get_attribute(self, self.chosen_item['display_key'])
		current_date = tmdb_api.get_current_date()
		if not current_attribute_value or current_attribute_value == 'False': choice = {'name': 'True', 'id': current_date}
		else: choice = {'name': 'False', 'id': current_date}
		self.set_key_values(self.chosen_item['url_insert_%s' % self.media_type] % choice['id'], choice['name'])

	def adult(self):
		current_attribute_value = self.get_attribute(self, self.chosen_item['display_key'])
		if not current_attribute_value or current_attribute_value == 'True': choice = {'name': 'False', 'id': 'false'}
		else: choice = {'name': 'True', 'id': 'true'}
		self.set_key_values(self.chosen_item['url_insert'] % choice['id'], choice['name'])

	def get_active_attributes(self):
		return {key: discover_items[key] for key in [i for i in discover_items if self.get_attribute(self, i)]}

	def make_url(self, active_attributes):
		self.url = base_url % (('movie' if self.media_type == 'movie' else 'tv'), tmdb_api_key, ''.join([self.get_attribute(self, i) for i in active_attributes]), '&page=%s')

	def make_label(self, active_attributes):
		label = '[B]%sS[/B]' % self.media_type.upper()
		ignore_year_end = False
		for key, values in active_attributes.items():
			attribute_value = self.get_attribute(self, values['display_key'])
			if key == 'with_year_start':
				if 'with_year_end' in active_attributes:
					ignore_year_end = True
					year_end = self.get_attribute(self, discover_items['with_year_end']['display_key'])
					if attribute_value == year_end: label_extend = ' | %s' % attribute_value
					else: label_extend = ' | %s-%s' % (attribute_value, year_end)
				else: label_extend = values['name_value'] % attribute_value
			elif key == 'with_year_end':
				if ignore_year_end: continue
				label_extend = values['name_value'] % attribute_value
			elif key == 'with_released':
				if attribute_value == 'True': label_extend = values['name_value']
				else: continue
			elif key == 'with_adult':
				if attribute_value == 'True': label_extend = values['name_value']
				else: continue
			else: label_extend = values['name_value'] % attribute_value
			label += label_extend
		self.label = label#.upper()

	def set_key_values(self, key_content, display_key_content):
		self.set_attribute(self, self.chosen_item['key'], key_content)
		self.set_attribute(self, self.chosen_item['display_key'], display_key_content)
		self.remake, self.chosen_item = True, None

	def selection_dialog(self, heading, dialog_list, function_list=None):
		list_items = [{'line1': item['name']} for item in dialog_list]
		kwargs = {'items': json.dumps(list_items), 'heading': heading, 'narrow_window': 'true'}
		return select_dialog(function_list, **kwargs)

	def multiselect_dialog(self, heading, dialog_list, function_list=None, preselect= []):
		if not function_list: function_list = dialog_list
		list_items = [{'line1': item['name'], 'icon': item.get('icon', 'discover')} for item in dialog_list]
		kwargs = {'items': json.dumps(list_items), 'heading': heading, 'enumerate': 'false', 'multi_choice': 'true', 'preselect': preselect}
		return select_dialog(function_list, **kwargs)

	def set_attributes_status(self, status='false'):
		self.setProperty('active_attributes', status)
		self.setProperty('list_label', self.label if status == 'true' else empty_list_label)

	def set_starting_constants(self, kwargs):
		self.position, self.remake, self.chosen_item, self.media_type, self.active_attributes,  self.label, self.url = 0, False, None, kwargs['media_type'], [], '', ''
		for key, values in discover_items.items():
			for key_value in default_key_values: self.set_attribute(self, values[key_value], '')
