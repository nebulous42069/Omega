from resources.lib import account_actions
import os, shutil, urllib.request, urllib.parse, urllib.error
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import requests, json
from pathlib import Path
from resources.lib import Utils
from resources.lib import TheMovieDB
from resources.lib.WindowManager import wm
from resources.lib.tmdb_helper import choose_player
from resources.lib.OnClickHandler import OnClickHandler
from resources.lib.DialogBaseList import DialogBaseList
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short
from resources.lib.trakt import trakt_next_episode_normal
from resources.lib.trakt import trakt_next_episode_rewatch
from resources.lib.trakt import trakt_watched_tv_shows
from resources.lib.trakt import trakt_unwatched_tv_shows
from resources.lib.trakt import trakt_watched_movies
from resources.lib.trakt import trakt_collection_shows
from resources.lib.trakt import trakt_collection_movies
from resources.lib.trakt import trakt_uncollected_watched_movies
from resources.lib.trakt import trakt_unwatched_collection_movies
from resources.lib.trakt import trakt_trending_movies
from resources.lib.trakt import trakt_trending_shows
from resources.lib.trakt import trakt_popular_movies
from resources.lib.trakt import trakt_popular_shows
from resources.lib.trakt import trakt_lists
from resources.lib.trakt import trakt_watched_tv_shows_progress
from resources.lib.trakt import trak_auth
from resources.lib.TheMovieDB import get_trakt_playback
from resources.lib.TheMovieDB import extended_episode_info
#from resources.lib.TheMovieDB import extended_season_info
from resources.lib.TheMovieDB import extended_movie_info
from resources.lib.trakt import get_trakt_data
from datetime import datetime, timedelta

import math
import re

from inspect import currentframe, getframeinfo
#xbmc.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))+'===>OPENINFO', level=xbmc.LOGINFO)
ch = OnClickHandler()
SORTS = {
	'movie': {
		'popularity': 'Popularity',
		'vote_average': 'Vote average',
		'vote_count': 'Vote count',
		'release_date': 'Release date',
		'revenue': 'Revenue',
		'original_title': 'Original title'
		},
	'tv': {
		'popularity': 'Popularity',
		'vote_average': 'Vote average',
		'vote_count': 'Vote count',
		'first_air_date': 'First aired'
		}}
LANGUAGES = [
	{'id': '', 'name': ''},
	{'id': 'bg', 'name': 'Bulgarian'},
	{'id': 'cs', 'name': 'Czech'},
	{'id': 'da', 'name': 'Danish'},
	{'id': 'de', 'name': 'German'},
	{'id': 'el', 'name': 'Greek'},
	{'id': 'en', 'name': 'English'},
	{'id': 'es', 'name': 'Spanish'},
	{'id': 'fi', 'name': 'Finnish'},
	{'id': 'fr', 'name': 'French'},
	{'id': 'he', 'name': 'Hebrew'},
	{'id': 'hi', 'name': 'Hindi'},
	{'id': 'hr', 'name': 'Croatian'},
	{'id': 'hu', 'name': 'Hungarian'},
	{'id': 'it', 'name': 'Italian'},
	{'id': 'ja', 'name': 'Japanese'},
	{'id': 'ko', 'name': 'Korean'},
	{'id': 'nl', 'name': 'Dutch'},
	{'id': 'no', 'name': 'Norwegian'},
	{'id': 'pl', 'name': 'Polish'},
	{'id': 'pt', 'name': 'Portuguese'},
	{'id': 'ru', 'name': 'Russian'},
	{'id': 'sl', 'name': 'Slovenian'},
	{'id': 'sv', 'name': 'Swedish'},
	{'id': 'tr', 'name': 'Turkish'},
	{'id': 'zh', 'name': 'Chinese'}
]



def write_fetch_data_dict_file():
	import os
	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
	if not os.path.exists(Path(addonUserDataFolder)):
		os.makedirs(Path(addonUserDataFolder))
	fetch_data_dict_file = open(Path(addonUserDataFolder + '/fetch_data_dict'), "w+", encoding="utf-8")
	return fetch_data_dict_file

def read_fetch_data_dict_file():
	addon = xbmcaddon.Addon()
	addon_path = addon.getAddonInfo('path')
	addonID = addon.getAddonInfo('id')
	addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
	return open(Path(addonUserDataFolder + '/fetch_data_dict'), "r")

def get_tmdb_window(window_type):
	Utils.show_busy()
	class DialogVideoList(DialogBaseList, window_type):

		def setup_filter(self, meta_filters):
			#import urllib.parse
			#meta_filters_encoded  = urllib.parse.quote(str(meta_filters))
			#meta_filters_encoded = meta_filters
			#meta_filters_decoded  = eval(urllib.parse.unquote(meta_filters_encoded))
			meta_filters_decoded = meta_filters

			for i in meta_filters_decoded['filters']:
				if i == 'sort':
					self.order = meta_filters_decoded['filters'][i]
				if i == 'sort_string':
					if self.media_type == 'tv':
						if meta_filters_decoded['filters'][i] in str(SORTS['tv']):
							self.sort_label = SORTS['tv'][meta_filters_decoded['filters'][i]]
							self.sort = meta_filters_decoded['filters'][i]
						else:
							self.sort = 'popularity'
							self.sort_label = SORTS['tv']['popularity']
					else:
						if meta_filters_decoded['filters'][i] in str(SORTS['movie']):
							self.sort_label = SORTS['movie'][meta_filters_decoded['filters'][i]]
							self.sort = meta_filters_decoded['filters'][i]
						else:
							self.sort = 'popularity'
							self.sort_label = SORTS['movie']['popularity']
				if 'genre' in str(i) and i != 'genre_mode':
					response = TheMovieDB.get_tmdb_data('genre/%s/list?language=%s&' % (self.type, xbmcaddon.Addon().getSetting('LanguageID')), 10)
					id_list = [item['id'] for item in response['genres']]
					label_list = [item['name'] for item in response['genres']]
					ids = []
					labels = ', '
					ids_or = '| '
					for genre in meta_filters_decoded['filters'][i]:
						labels = labels + genre.capitalize() + ', '
						for idx, x in enumerate(label_list):
							if str(genre).lower() in str(x).lower():
								ids.append(id_list[idx])
								ids_or = ids_or + str(id_list[idx]) + '| '
					labels = labels[2:-2]
					ids_or = ids_or[2:-2]
					if meta_filters_decoded['filters']['genre_mode'] == 'OR':
						ids = ids_or
						labels = labels.replace(',','|')
					if 'without_genres' == i:
						self.add_filter('without_genres', ids, 'Genres', 'NOT ' + labels)
					if 'with_genres' == i:
						self.add_filter('with_genres', ids, 'Genres', labels)
				if i == 'with_original_language':
					id = meta_filters_decoded['filters'][i]
					id_list = [item['id'] for item in LANGUAGES]
					label_list = [item['name'] for item in LANGUAGES]
					self.add_filter('with_original_language', id, 'Original language', label_list[id_list.index(id)])
				if i == 'vote_count.gte':
					result = meta_filters_decoded['filters'][i]
					self.add_filter('vote_count.gte', result, 'Vote count', ' > %s' % result)
				if i == 'vote_count.lte':
					result = meta_filters_decoded['filters'][i]
					self.add_filter('vote_count.lte', result, 'Vote count', ' < %s' % result)
				if i == 'upper_year' or i == 'lower_year':
					if i == 'upper_year':
						order = 'lte'
						value = '%s-12-31' % meta_filters_decoded['filters'][i] 
						label = ' < ' + meta_filters_decoded['filters'][i] 
					if i == 'lower_year':
						order = 'gte'
						value = '%s-01-01' % meta_filters_decoded['filters'][i] 
						label = ' > ' + meta_filters_decoded['filters'][i] 
					if self.media_type == 'movie':
						self.add_filter('primary_release_date.%s' % order, value, 'Year', label)
					if self.media_type == 'tv':
						self.add_filter('first_air_date.%s' % order, value, 'First aired', label)

		def __init__(self, *args, **kwargs):
			super(DialogVideoList, self).__init__(*args, **kwargs)
			self._blade_stack = []
			self._blade_root = 5015
			self._blade_refresh_focus = None
			self.type = kwargs.get('type', 'movie')
			self.media_type = self.type
			self.list_id = kwargs.get('list_id', False)
			self.sort = kwargs.get('sort', 'popularity')
			self.sort_label = kwargs.get('sort_label', 'Popularity')
			self.order = kwargs.get('order', 'desc')
			if self.list_id == 'tmdb_newest' or self.mode == 'tmdb_ranked':
				self.sort = 'release_date' if self.type == 'movie' else 'first_air_date' if self.type == 'tv' else 'popularity'
				self.sort_label = 'Release date' if self.type == 'movie' else 'First aired' if self.type == 'tv' else 'TMDb ranking'
			self.mode2 = None
			self.curr_window = None
			self.prev_window = None
			self.filter_url = None
			self.filter = None
			self.control_id2 = None
			self.action2  = None
			self.listitems = []
			self.listitems2 = []
			xbmcgui.Window(10000).clearProperty('ImageFilter')
			xbmcgui.Window(10000).clearProperty('ImageColor')

			if wm.custom_filter:
				self.setup_filter(wm.custom_filter)
				wm.custom_filter = None
				self.update_content(force_update=kwargs.get('force', False))

			if self.listitem_list:
				#xbmc.log(str(wm.page), level=xbmc.LOGINFO)
				#xbmc.log(str(self.page), level=xbmc.LOGINFO)

				#self.listitems = Utils.create_listitems(self.listitem_list)
				#self.total_items = len(self.listitem_list)
				self.update_content(force_update=kwargs.get('force', False))
			elif self.filters == [] and self.mode not in ('tmdb_ranked','trakt_catalog'):
				try:
					import os
					addon = xbmcaddon.Addon()
					addon_path = addon.getAddonInfo('path')
					addonID = addon.getAddonInfo('id')
					addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
					if os.path.exists(str(Path(addonUserDataFolder + '/custom_for_me'))):
						self.add_filter('with_original_language', 'en', 'Original language', 'English')
						self.add_filter('without_genres', '27', 'Genres', 'NOT Horror')
						self.add_filter('vote_count.gte', '1000', '%s (%s)' % ('Vote count', '>'), '1000')
					else:
						self.filters == []
				except:
					self.filters == []
				self.update_content(force_update=kwargs.get('force', False))
			elif self.filters != [] or self.mode in ('tmdb_ranked','trakt_catalog'):
				self.update_content(force_update=kwargs.get('force', False))

		def update_fetch_data_dict(self, info, fetch_data_dict):
			fetch_data_dict['self.info'] = info
			fetch_data_dict['self.mode'] = self.mode
			fetch_data_dict['self.history_source'] = self.history_scope_value()
			fetch_data_dict['self.sort'] = self.sort
			fetch_data_dict['self.sort_label'] = self.sort_label
			fetch_data_dict['self.order'] = self.order
			fetch_data_dict['self.type'] = self.type
			fetch_data_dict['self.search_str'] = self.search_str
			fetch_data_dict['self.page'] = self.page
			fetch_data_dict['self.filter_label'] = self.filter_label
			fetch_data_dict['self.list_id'] = self.list_id
			fetch_data_dict['self.filter_url'] = self.filter_url
			fetch_data_dict['self.total_items'] = self.total_items
			fetch_data_dict['self.total_pages'] = self.total_pages
			fetch_data_dict['self.next_page_token'] = self.next_page_token
			fetch_data_dict['self.prev_page_token'] = self.prev_page_token
			fetch_data_dict['self.filters'] = self.filters
			fetch_data_dict['self.filter'] = self.filter


			return fetch_data_dict

		def get_fetch_data_dict_read(self, fetch_data_dict_read):
			self.history_source = fetch_data_dict_read.get('self.history_source','combined')
			try: self.mode = fetch_data_dict_read['self.mode']
			except: pass
			try: self.type = fetch_data_dict_read['self.type']
			except: pass
			try: self.sort_label = fetch_data_dict_read['self.sort_label']
			except: pass
			try: self.sort = fetch_data_dict_read['self.sort']
			except: pass
			try: info = fetch_data_dict_read['self.info']
			except: pass
			try: self.order = fetch_data_dict_read['self.order']
			except: pass
			try: self.search_str = fetch_data_dict_read['self.search_str']
			except: pass
			try: self.filter_label = fetch_data_dict_read['self.filter_label'].replace('Results for:  ','')
			except: pass
			try: self.page = fetch_data_dict_read['self.page']
			except: pass
			try: self.list_id = fetch_data_dict_read['self.list_id']
			except: pass
			try: self.filter_url = fetch_data_dict_read['self.filter_url']
			except: pass

			try: self.filters = fetch_data_dict_read['self.filters']
			except: pass
			try: self.filter = fetch_data_dict_read['self.filter']
			except: pass

			try: self.total_items = fetch_data_dict_read['self.total_items']
			except: pass
			try: self.total_pages = fetch_data_dict_read['self.total_pages']
			except: pass

			try: self.next_page_token = fetch_data_dict_read['self.next_page_token']
			except: pass
			try: self.prev_page_token = fetch_data_dict_read['self.prev_page_token']
			except: pass

			return info

		def onClick(self, control_id):
			# Dedicated pointer controls do not depend on Kodi focusing a hidden group.
			if control_id == 9020:
				self.setProperty('PortalBladePinned', 'true')
				for _ in range(12):
					try: self.setFocusId(6000)
					except RuntimeError: pass
					if self.getFocusId() == 6000: break
					xbmc.sleep(25)
				return
			if control_id == 9021:
				return self.close_pointer_blade()
			if control_id in (9012, 9013):
				return self.blade_page(-1 if control_id == 9012 else 1)
			if control_id in (72, 9011):
				return  # Native page controls handle their own input.
			if control_id in (9024, 9025):
				return self.pointer_page(control_id == 9025)
			if control_id == 500 and self.getProperty('PortalBladePinned') == 'true':
				self.blade_close()
				self.clearProperty('PortalBladePinned')
			# Browse service folders without closing the current dialog.
			browser_roots = {5015: 'sub_trakt', 5017: 'mdb_browser', 5019: 'tmdb_browser', 5021: 'simkl_browser'}
			if control_id == 9010:
				self.blade_select()
				return
			if control_id in browser_roots:
				self._blade_root = control_id
				self.open_service_browser(browser_roots[control_id])
				return
			if control_id in (5001,5002,5003,5004):
				ch.serve(control_id, self)
				return
			if (self.search_str == 'Trakt Episodes/Movies in progress' or self.search_str == 'Trakt Calendar Episodes') and xbmc.getInfoLabel('listitem.DBTYPE') == 'episode':
				try: wm.open_tvshow_info(prev_window=self, tmdb_id=self.listitem.getProperty('tmdb_id'))
				except: wm.open_tvshow_info(prev_window=self, tmdb_id=self.listitems[self.position].getProperty('tmdb_id'))
			else:
				super(DialogVideoList, self).onClick(control_id)
				self.control_id2 = control_id
				ch.serve(control_id, self)

		def onFocus(self, control_id):
			if getattr(self, '_blade_stack', []):
				# Kodi can deliver queued focus events from the control we just hid.
				# Ignore those events and any intermediate focus during a transition.
				if getattr(self, '_blade_transition', False):
					return
				if control_id not in (9010, 9011, 9012, 9013, 9021):
					if self.getFocusId() in (9010, 9011, 9012, 9013, 9021):
						return
					if self.getProperty('PortalBladePinned') != 'true':
						self.blade_close()
			super(DialogVideoList, self).onFocus(control_id)

		def onAction(self, action):
			ident = action.getId()
			focus = self.getFocusId()
			pinned = self.getProperty('PortalBladePinned') == 'true'
			if pinned and ident in (9, 10, 92):
				if self._blade_stack:
					self.blade_back()
				else:
					self.close_pointer_blade()
				return
			if self._blade_stack and focus in (9010, 9011, 9012, 9013, 9021):
				if ident in (9, 10, 92):
					self.blade_back()
				return
			# A remote direction that deliberately leaves a pointer-opened sideblade
			# restores the original focus-driven behaviour; passive mouse hover does not.
			if pinned and focus == 500 and ident in (1, 2, 3, 4):
				self.blade_close()
				self.clearProperty('PortalBladePinned')
			super(DialogVideoList, self).onAction(action)
			self.action2 = action
			ch.serve_action(action, self.getFocusId(), self)

		def update_ui(self):
			addon=xbmcaddon.Addon()
			from resources.lib.appearance import apply_focus_appearance
			apply_focus_appearance(self)
			types = {'movie':'Movies','tv':'TV Shows','person':'People'}
			self.setProperty('Type', types.get(self.type, 'Movies'))
			self.setProperty('Search_Label', 'Search '+types.get(self.type,'Movies')+'...')
			can_discover = self.type in ('movie','tv') and self.mode == 'filter'
			for control in (5002,5003):
				self.getControl(control).setVisible(can_discover)
			self.getControl(5004).setVisible(can_discover or int(self.total_pages or 0)>1)
			super(DialogVideoList, self).update_ui()

		@ch.click(5004)
		def open_filters(self):
			options = []
			if self.mode == 'filter' and self.type in ('movie','tv'):
				options = [('Original Language',self.set_language_filter),('Genre',self.set_genre_filter),('Release date' if self.type=='movie' else 'First aired',self.set_year_filter)]
				if self.type=='movie':
					options += [('Certification',self.set_certification_filter),('Actor / Crew member',self.set_actor_filter)]
				options += [('Keyword',self.set_keyword_filter),('Studio',self.set_company_filter),('Vote count',self.set_vote_count_filter),('Edit / Remove Filters',self.reset_filters)]
			if int(self.total_pages or 0)>1: options.insert(1 if options else 0,('Page Number',self.set_page_number))
			if not options: return
			self._blade_root = 5004
			self.blade_push('Filters', [(label, {'callback':fn}) for label,fn in options])

		def blade_push(self, heading, rows, browser_key=None):
			if not rows:
				xbmcgui.Dialog().notification(heading, 'No results available.')
				return
			if self._blade_stack:
				self._blade_stack[-1]['position'] = self.getControl(9010).getSelectedPosition()
			self._blade_stack.append({'heading':heading, 'rows':rows, 'position':1, 'browser_key':browser_key})
			self.blade_render()

		def blade_render(self):
			frame = self._blade_stack[-1]
			self._blade_transition = True
			try:
				control = self.getControl(9010)
				control.reset()
				items = [xbmcgui.ListItem(label='‹ Back')]
				for label, params in frame['rows']:
					items.append(xbmcgui.ListItem(label=label + ('  ›' if 'sub_menu' in params else '')))
				control.addItems(items)
				self.setProperty('PortalBladeHeading', frame['heading'])
				self.setProperty('PortalBladeNested', 'true')
				# Keep root controls visible until the nested list actually has focus.
				# Visibility conditions are evaluated on Kodi's GUI thread.
				for attempt in range(10):
					try:
						self.setFocusId(9010)
					except RuntimeError:
						pass
					if self.getFocusId() == 9010:
						break
					xbmc.sleep(25)
				if self.getFocusId() != 9010:
					raise RuntimeError('Unable to focus sideblade list')
				control.selectItem(frame['position'])
				self.setProperty('PortalBladeReady', 'true')
			except Exception:
				self.blade_close(restore=True)
				raise
			finally:
				self._blade_transition = False

		def blade_close(self, restore=False):
			self._blade_stack = []
			self.clearProperty('PortalBladeReady')
			self.clearProperty('PortalBladeNested')
			self.clearProperty('PortalBladeHeading')
			if restore:
				for attempt in range(10):
					try:
						self.setFocusId(self._blade_root)
					except RuntimeError:
						pass
					if self.getFocusId() == self._blade_root:
						break
					xbmc.sleep(25)

		def close_pointer_blade(self):
			self.blade_close()
			self.clearProperty('PortalBladePinned')
			self.setProperty('PortalBladeClosing', 'true')
			try:
				# The opener remains visible during this focus transfer, including empty catalogs.
				target = 500 if self.listitems else 9020
				for _ in range(12):
					try: self.setFocusId(target)
					except RuntimeError: pass
					if self.getFocusId() == target: break
					xbmc.sleep(25)
			finally:
				self.clearProperty('PortalBladeClosing')

		def blade_page(self, direction):
			if not self._blade_stack: return
			control = self.getControl(9010)
			count = control.size()
			if not count: return
			position = max(0, min(count-1, control.getSelectedPosition() + direction * 10))
			self.setFocusId(9010)
			control.selectItem(position)

		def pointer_page(self, forward):
			# The native scrollbar changes positions within a page; these buttons fetch pages.
			if not (int(self.page or 1) < int(self.total_pages or 0) if forward else int(self.page or 1) > 1):
				return
			self.blade_close()
			self.clearProperty('PortalBladePinned')
			self.setFocusId(500)
			self.position = wm.position = 0
			if forward: self.go_to_next_page(pointer=True)
			else: self.go_to_prev_page(pointer=True)
			if self.listitems:
				self.getControl(500).selectItem(0)
				self.setFocusId(500)
				self.save_position()

		def blade_back(self):
			if len(self._blade_stack) > 1:
				self._blade_stack.pop()
				self.refresh_blade_account_rows()
				self.blade_render()
			else: self.blade_close(restore=True)

		def service_browser_rows(self, root):
			from resources.lib import browser_menu
			class InlineMenu(browser_menu.BrowserMenu):
				def menu_item(self, display_label, art=None, **params):
					self.rows.append((display_label, params))
			menu = InlineMenu()
			menu.sub_menu = root
			menu.rows = []
			menu.populate_browser()
			return menu.rows

		def refresh_blade_account_rows(self):
			# Refresh only cheap, credential-dependent menus; never refetch discovery feeds.
			from resources.lib.browser_menu import ACCOUNT_STATE_MENUS
			frame = self._blade_stack[-1]
			key = frame.get('browser_key')
			if key not in ACCOUNT_STATE_MENUS: return False
			rows = self.service_browser_rows(key)
			if rows == frame['rows']: return False
			frame['rows'] = rows
			frame['position'] = min(frame['position'], len(rows))
			return True

		def open_service_browser(self, root, heading=None):
			heading = heading or {'sub_trakt':'Trakt Browser','mdb_browser':'MDBList Browser','tmdb_browser':'TMDB Browser','simkl_browser':'SIMKL Browser'}.get(root, root)
			try:
				self.blade_push(heading, self.service_browser_rows(root), browser_key=root)
			except Exception:
				Utils.hide_busy()
				xbmcgui.Dialog().notification(heading, 'Unable to open list. Check account or network access.', xbmcgui.NOTIFICATION_ERROR)

		def blade_load(self, loader, *args):
			# Keep the existing sideblade control, stack and scroll position during refresh.
			focus = self.getFocusId()
			position = self.getControl(9010).getSelectedPosition() if focus == 9010 else None
			self._blade_refresh_focus = focus
			self._blade_transition = True
			try:
				return loader(*args)
			finally:
				try:
					self.setFocusId(focus)
					if position is not None and self._blade_stack:
						self._blade_stack[-1]['position'] = position
						self.getControl(9010).selectItem(position)
				finally:
					self._blade_refresh_focus = None
					self._blade_transition = False

		def focus_loaded_catalog(self):
			if self.listitems:
				self.getControl(500).selectItem(0)
			if not getattr(self, '_blade_refresh_focus', None):
				self.setFocusId(500 if self.listitems else 6000)

		def blade_select(self):
			from resources.lib import account_catalog, trakt_catalog, accounts
			if not self._blade_stack: return
			frame = self._blade_stack[-1]
			index = self.getControl(9010).getSelectedPosition()
			if index == 0: return self.blade_back()
			if not 1 <= index <= len(frame['rows']): return
			label, params = frame['rows'][index-1]
			dlg = xbmcgui.Dialog()
			try:
				# An Account Manager sync may have completed while this menu was open.
				frame['position'] = index
				if self.refresh_blade_account_rows():
					if not frame['rows']: return self.blade_back()
					return self.blade_render()
				if 'callback' in params:
					self.blade_close(restore=True)
					return params['callback']()
				if 'sub_menu' in params: return self.open_service_browser(params['sub_menu'], label)
				if 'resolved' in params:
					return self.blade_load(self.load_service_list, *params['resolved'])
				info = params.get('info')
				kind = params.get('kind')
				category, value = params.get('category',''), params.get('value','')
				if info == 'simkl_manager':
					accounts.authorize_browser('simkl',managed=True)
					self.blade_back(); return
				if info == 'account_manager':
					accounts.authorize_browser(params.get('source',''),managed=True)
					self.blade_back(); return
				if info == 'account_logout':
					accounts.confirm_disconnect(params['source'])
					self.blade_back(); return
				if info == 'account_login':
					accounts.authorize_browser(params['source'])
					self.blade_back()
					return
				if info == 'tmdb_search' or (info == 'trakt_browse' and kind == 'person'):
					text = dlg.input(label).strip()
					if not text: return
					category, value, label = 'search', text, label + ': ' + text
				if info in ('tmdb_browse','tmdb_search'):
					return self.blade_load(self.load_catalog, kind, category, value, label)
				if info == 'account_browse':
					source = params['source']
					leaf = account_catalog.choose(source, kind, category, label, expand=True, value=value)
				elif info == 'trakt_browse':
					source = 'trakt'
					leaf = (category,value,label) if kind == 'person' else trakt_catalog.choose(kind,category,str(value),label,expand=True)
				else: return
				if isinstance(leaf,list):
					return self.blade_push(label, [(n, {'resolved':(source,kind,c,v,n)}) for c,v,n in leaf])
				if not leaf: return
				self.blade_load(self.load_service_list, source, kind, *leaf)
			except Exception:
				Utils.hide_busy()
				dlg.notification(label, 'Unable to open list. Check account or network access.', xbmcgui.NOTIFICATION_ERROR)

		def load_service_list(self, source, kind, category, value, label):
			self.type = self.media_type = kind
			self.history_source = source if source in ('trakt','mdblist','simkl') else 'combined'
			self.mode = 'trakt_catalog'; self.list_id = False; self.page = 1
			self.filters = []; self.filter = self.filter_url = None
			self.search_str = {'source':source,'category':category,'value':str(value)}
			self.filter_label = label
			self.listitem_list = []; self._trakt_rows = None; self._ranked_rows = None
			self.page_token = self.prev_page_token = self.next_page_token = ''
			self.position = 0; wm.page = -1; wm.prev_page_num = 0; wm.page_position = 0; wm.position = 0
			self.update()
			self.focus_loaded_catalog()
			Utils.hide_busy()

		def search_catalog(self):
			# Invoked by the inherited search button handler (6000).
			kind = self.type if self.type in ('movie','tv','person') else 'movie'
			label = {'movie':'Movies','tv':'TV Shows','person':'People'}[kind]
			text = xbmcgui.Dialog().input(heading='Search '+label,type=xbmcgui.INPUT_ALPHANUM).strip()
			if text:
				if self.history_scope_value()=='simkl' and kind in ('movie','tv'):
					from resources.lib import simkl_api
					if not simkl_api.configured():
						xbmcgui.Dialog().ok('SIMKL','Authorize SIMKL to search.'); return
					category=self.search_str.get('category','') if isinstance(self.search_str,dict) else ''
					media='anime' if 'anime' in category else 'movies' if kind=='movie' else 'tv'
					return self.load_service_list('simkl',kind,'public_'+media+':search',text,'Search SIMKL: '+text)
				self.load_catalog(kind,'search',text,label+': '+text)

		def load_catalog(self, kind, category, value='', label=''):
			self.history_source = 'combined'
			from resources.lib import tmdb_catalog as catalog
			self.type = self.media_type = kind
			self._ranked_rows = None
			self._trakt_rows = None
			self.page = 1
			self.order = 'desc'
			self.sort = 'release_date' if kind=='movie' else 'first_air_date' if kind=='tv' else 'popularity'
			self.sort_label = SORTS.get(kind,{}).get(self.sort,'Relevance')
			self.filters = []
			self.filter = self.filter_url = None
			self.search_str = ''
			self.filter_label = label
			self.listitem_list = []
			self.page_token = self.prev_page_token = self.next_page_token = ''
			if category in catalog.RANKED or category=='search' or kind=='person':
				self.mode = 'tmdb_ranked'
				self.list_id = False
				self.search_str = {'category':category,'value':str(value)}
			else:
				self.mode = 'filter'
				self.list_id = 'tmdb_newest'
				self.filters = catalog.filters(kind,category,value,label)
			wm.page = -1
			wm.prev_page_num = 0
			wm.position = 0
			wm.page_position = 0
			self.position = 0
			self.update()
			self.focus_loaded_catalog()
			Utils.hide_busy()

		def go_to_next_page(self, pointer=False):
			if self.page == self.total_pages:
				return
			self.get_column()

			wm.page_position = 0 if pointer else self.position -16
			self.position = wm.page_position

			xbmcgui.Window(10000).clearProperty('focus_id')
			xbmcgui.Window(10000).clearProperty('position')
			xbmcgui.Window(10000).clearProperty('pop_stack_focus_id')
			xbmcgui.Window(10000).clearProperty('pop_stack_position')

			if self.page < self.total_pages:
				self.page += 1
				self.prev_page_token = self.page_token
				self.page_token = self.next_page_token
				self.update()

		def go_to_prev_page(self, pointer=False):
			if self.page == 1:
				return
			self.get_column()

			wm.prev_page_flag = True
			wm.prev_page_num = self.page -1 
			wm.page_position = 0 if pointer else self.position + 16
			self.position = wm.page_position

			xbmcgui.Window(10000).clearProperty('focus_id')
			xbmcgui.Window(10000).clearProperty('position')
			xbmcgui.Window(10000).clearProperty('pop_stack_focus_id')
			xbmcgui.Window(10000).clearProperty('pop_stack_position')

			if self.page > 1:
				self.page -= 1
				self.next_page_token = self.page_token
				self.page_token = self.prev_page_token
				self.update()

		@ch.action('pagedown', 5019)
		def pgdn_last_browser(self):
			xbmc.executebuiltin('Control.SetFocus('+str(6000)+')')

		@ch.action('pageup', 6000)
		def pgup_6000(self):
			xbmc.executebuiltin('Control.SetFocus('+str(5019)+')')


		@ch.action('pagedown', 6000)
		def pgdn_6000(self):
			xbmc.executebuiltin('Control.SetFocus('+str(5001)+')')

		@ch.action('pageup', 5001)
		def pgup_5001(self):
			xbmc.executebuiltin('Control.SetFocus('+str(5019)+')')




		@ch.action('play', 500)
		def context_play(self):
			t=account_actions.target(self,True)
			if t:
				if t["kind"]=="person": return account_actions.information(self,t)
				return account_actions.play(self,t)

		@ch.action('info', 500)
		@ch.action('contextmenu', 500)
		def context_menu(self):
			return account_actions.menu(self, account_actions.target(self, True))

		@ch.click(5002)
		def get_sort_type(self):
			self._blade_root = 5002
			self.blade_push('Sort by', [(label, {'callback':lambda k=key,n=label:self.apply_sort(k,n)}) for key,label in SORTS.get(self.type,{}).items()])

		def apply_sort(self, key, label):
			if key == 'vote_average':
				self.add_filter('vote_count.gte','10','Vote count (greater than)','10')
			self.sort, self.sort_label = key, label
			self.update()

		def add_filter(self, key, value, typelabel, label):
			if '.gte' in key or '.lte' in key:
				super(DialogVideoList, self).add_filter(key=key, value=value, typelabel=typelabel, label=label, force_overwrite=True)
			else:
				super(DialogVideoList, self).add_filter(key=key, value=value, typelabel=typelabel, label=label, force_overwrite=False)

		@ch.click(5003)
		def toggle_order(self):
			self._blade_root = 5003
			self.blade_push('Order', [(n,{'callback':lambda v=v:self.apply_order(v)}) for v,n in [('desc','Descending'),('asc','Ascending')]])

		def apply_order(self, value):
			self.order = value
			self.update()

		@ch.click(5001)
		def toggle_media_type(self):
			kind = 'tv' if self.type == 'movie' else 'movie'
			return self.blade_load(self.load_catalog, kind, 'all', '', 'All TV Shows' if kind == 'tv' else 'All Movies')

		@ch.click(5007)
		def set_genre_filter(self):
			response = TheMovieDB.get_tmdb_data('genre/%s/list?language=%s&' % (self.type, xbmcaddon.Addon().getSetting('LanguageID')), 10)
			"""
			id_list = [item['id'] for item in response['genres']]
			label_list = [item['name'] for item in response['genres']]
			index = xbmcgui.Dialog().select(heading='Choose genre', list=label_list)
			if index == -1:
				return None
			self.add_filter('with_genres', str(id_list[index]), 'Genres', label_list[index])
			self.mode = 'filter'
			self.page = 1
			self.update()
			
			params = {"language": addon.setting("LanguageID")}
			response = tmdb.get_data(url="genre/%s/list" % (self.type),
									 params=params,
									 cache_days=100)
			"""
			selected = [i["id"] for i in self.filters if i["type"] == "with_genres"]
			ids = [item["id"] for item in response["genres"]]
			labels = [item["name"] for item in response["genres"]]
			preselect = [ids.index(int(i)) for i in str(selected[0]).split(",")] if selected else []

			try: without_genres = 'NOT Genres: ' + str([i["label"] for i in self.filters if i["type"] == "without_genres"][0]).replace(',','+').replace('|',' OR ')
			except: without_genres = ''
			try: with_genres = 'Genres: ' + str([i["label"] for i in self.filters if i["type"] == "with_genres"][0]).replace(',','+').replace('|',' OR ') + ' '
			except: with_genres = ''
			filter_label = with_genres + without_genres
			
			indexes = xbmcgui.Dialog().multiselect(heading='Choose genre: ' + filter_label,options=labels,preselect=preselect)
			if indexes == -1:
				return

			try: selected_indexes = [labels[i] for i in indexes]
			except: return
			preselect_indexes = [labels[i] for i in  [ids.index(int(j)) for j in [ids[i] for i in preselect]]]
			selected_indexes2 = str([i for i in selected_indexes if i not in preselect_indexes]).replace('[','').replace(']','')
			#xbmc.log(str([i["label"] for i in self.filters if i["type"] == "without_genres"])+'without_genres===>OPENINFO', level=xbmc.LOGFATAL)
			#xbmc.log(str([i["label"] for i in self.filters if i["type"] == "with_genres"])+'with_genres===>OPENINFO', level=xbmc.LOGFATAL)

			if indexes is None:
				return None
			indexes2 = xbmcgui.Dialog().yesno('Genres', 'Set with/without genres for newly selected items' + ' ' + selected_indexes2, 'With Genres', 'Without Genres', 3500) 
			if indexes2 == -1:
				return
			indexes3 = str(indexes2)

			#xbmc.log(str([i["label"] for i in self.filters if i["type"] == "without_genres"])+'without_genres===>OPENINFO', level=xbmc.LOGFATAL)
			#xbmc.log(str([i["label"] for i in self.filters if i["type"] == "with_genres"])+'with_genres===>OPENINFO', level=xbmc.LOGFATAL)

			self.filters = [i for i in self.filters if i["type"] != "with_genres"]
			for i in indexes:
				if indexes2 == False:
					self.add_filter('with_genres', ids[i], 'Genres', labels[i])
				else:
					if str(i) in str(preselect):
						self.add_filter('with_genres', ids[i], 'Genres', labels[i])
					else:
						self.add_filter('without_genres', ids[i], 'NOT Genres', labels[i])
			self.mode = 'filter'
			self.page = 1
			self.update()

		@ch.click(5013)
		def set_vote_count_filter(self):
			ret = True
			if not self.type == 'tv':
				ret = xbmcgui.Dialog().yesno(heading='Choose option', message='Choose filter behaviour', nolabel='Lower limit', yeslabel='Upper limit')
			result = xbmcgui.Dialog().input(heading='Vote count', type=xbmcgui.INPUT_NUMERIC)
			if result:
				if ret:
					self.add_filter('vote_count.lte', result, 'Vote count', ' < %s' % result)
				else:
					self.add_filter('vote_count.gte', result, 'Vote count', ' > %s' % result)
				self.mode = 'filter'
				self.page = 1
				self.update()

		@ch.click(5008)
		def set_year_filter(self):
			ret = xbmcgui.Dialog().yesno(heading='Choose option', message='Choose filter behaviour', nolabel='Lower limit', yeslabel='Upper limit')
			result = xbmcgui.Dialog().input(heading='Year', type=xbmcgui.INPUT_NUMERIC)
			if not result:
				return None
			if ret:
				order = 'lte'
				value = '%s-12-31' % result
				label = ' < ' + result
			else:
				order = 'gte'
				value = '%s-01-01' % result
				label = ' > ' + result
			if self.type == 'tv':
				self.add_filter('first_air_date.%s' % order, value, 'First aired', label)
			else:
				self.add_filter('primary_release_date.%s' % order, value, 'Year', label)
			self.mode = 'filter'
			self.page = 1
			self.update()

		@ch.click(5010)
		def set_actor_filter(self):
			result = xbmcgui.Dialog().input(heading='Enter search string', type=xbmcgui.INPUT_ALPHANUM)
			if not result or result == -1:
				return None
			response = TheMovieDB.get_person_info(result)
			if not response:
				return None
			self.add_filter('with_people', str(response['id']), 'Person', response['name'])
			self.mode = 'filter'
			self.page = 1
			self.update()

		@ch.click(500)
		def open_media(self):
			Utils.show_busy()
			self.last_position = self.control.getSelectedPosition()
			media_type = self.listitem.getProperty('media_type')
			if media_type == 'episode':
				wm.open_episode_info(prev_window=self,tvshow_id=self.listitem.getProperty('tmdb_id'),season=int(self.listitem.getProperty('season')),episode=int(self.listitem.getProperty('episode')))
				return
			if media_type == 'tvshow':
				media_type = 'tv'
			if 'movie' in str(media_type):
				media_type = 'movie'
			if media_type:
				self.type = media_type
			else:
				self.type = self.media_type
			if self.type == 'tv':
				if str(self.listitem.getProperty('id')) == '':
					response = TheMovieDB.get_tmdb_data('search/%s?query=%s&first_air_date_year=%s&language=%s&include_adult=%s&' % ('tv', str(self.listitem.getProperty('title')), str(self.listitem.getProperty('year')) , str(xbmcaddon.Addon().getSetting('LanguageID')) , xbmcaddon.Addon().getSetting('include_adults')), 30)
					tmdb_id = response['results'][0]['id']
					wm.open_tvshow_info(prev_window=self, tmdb_id=tmdb_id)
				else:
					wm.open_tvshow_info(prev_window=self, tmdb_id=self.listitem.getProperty('id'))
			elif self.type == 'person':
				wm.open_actor_info(prev_window=self, actor_id=self.listitem.getProperty('id'))
			else:
				if str(self.listitem.getProperty('id')) == '':
					response = TheMovieDB.get_tmdb_data('search/%s?query=%s&primary_release_year=%s&language=%s&include_adult=%s&' % ('movie', str(self.listitem.getProperty('title')), str(self.listitem.getProperty('year')) , str(xbmcaddon.Addon().getSetting('LanguageID')) , xbmcaddon.Addon().getSetting('include_adults')), 30)
					tmdb_id = response['results'][0]['id']
					wm.open_movie_info(prev_window=self, movie_id=tmdb_id)
				else:
					wm.open_movie_info(prev_window=self, movie_id=self.listitem.getProperty('id'))

		@ch.click(5012)
		def set_company_filter(self):
			result = xbmcgui.Dialog().input(heading='Enter search string', type=xbmcgui.INPUT_ALPHANUM)
			if not result or len(result) < 1:
				return None
			response = TheMovieDB.search_company(result)
			if len(response) > 1:
				selection = xbmcgui.Dialog().select(heading='Choose studio', list=[item['name'] for item in response])
				if selection > -1:
					response = response[selection]
				else: return
			elif response:
				response = response[0]
			else:
				Utils.notify('No company found')
				return
			self.add_filter('with_companies', str(response['id']), 'Studios', response['name'])
			self.mode = 'filter'
			self.page = 1
			self.update()

		@ch.click(5011)
		def set_keyword_filter(self):
			result = xbmcgui.Dialog().input(heading='Enter search string', type=xbmcgui.INPUT_ALPHANUM)
			if not result or result == -1:
				return None
			response = TheMovieDB.get_keyword_id(result)
			if not response:
				return None
			self.add_filter('with_keywords', str(response['id']), 'Keyword', response['name'])
			self.mode = 'filter'
			self.page = 1
			self.update()

		@ch.click(5009)
		def set_certification_filter(self):
			response = TheMovieDB.get_certification_list(self.type)
			country_list = [key for key in list(response.keys())]
			index = xbmcgui.Dialog().select(heading='Country code', list=country_list)
			if index == -1:
				return None
			country = country_list[index]
			cert_list = ['%s  -  %s' % (i['certification'], i['meaning']) for i in response[country]]
			index = xbmcgui.Dialog().select(heading='Choose certification', list=cert_list)

			if index == -1:
				return None
			cert = cert_list[index].split('  -  ')[0]
			self.add_filter('certification_country', country, 'Certification country', country)
			self.add_filter('certification', cert, 'Certification', cert)
			self.mode = 'filter'
			self.page = 1
			self.update()

		@ch.click(5006)
		def set_page_number(self):
			page = xbmcgui.Dialog().input(heading='Page Number', type=xbmcgui.INPUT_NUMERIC)#
			try: self.page = int(page)
			except: return
			self.update()

		@ch.click(5005)
		def set_language_filter(self):
			list = sorted(LANGUAGES, key=lambda k: k['name'])
			ids = [i['id'] for i in list]
			names = [i['name'] for i in list]
			index = xbmcgui.Dialog().select(heading='Choose language', list=names)

			if index == -1:
				return None
			id = ids[index]
			name = names[index]
			self.filters = [i for i in self.filters if i['type'] != 'with_original_language']
			self.add_filter('with_original_language', id, 'Original language', name)
			self.mode = 'filter'
			self.page = 1
			self.update()

		def reload_trakt(self):
			if 'Trakt Watched Movies' in str(self.filter_label):
				self.type = 'movie'
				self.search_str = trakt_watched_movies()
			if 'Trakt Watched Shows' in str(self.filter_label):
				self.type = 'tv'
				self.search_str = trakt_watched_tv_shows()
			if 'Trakt Unwatched Shows' in str(self.filter_label):
				self.type = 'tv'
				self.search_str = trakt_unwatched_tv_shows()
			else:
				return
			self.fetch_data()
			self.update()


		def fetch_data(self, force=False):
			addon = xbmcaddon.Addon()
			addon_path = addon.getAddonInfo('path')
			addonID = addon.getAddonInfo('id')
			addonUserDataFolder = xbmcvfs.translatePath("special://profile/addon_data/"+addonID)
			Utils.show_busy()
			
			if 'Trakt Episodes/Movies in progress' in str(self.search_str):
				self.filter_label = 'Trakt Episodes/Movies in progress'
			if 'Trakt Calendar Episodes' in str(self.search_str):
				self.filter_label = 'Trakt Calendar Episodes'

			if wm.pop_video_list == True:

				try: 
					self.page = int(wm.prev_window['params']['page'])
				except:
					diggzportal_prev_window = xbmcgui.Window(10000).getProperty('diggzportal_prev_window')
					diggzportal_curr_window = xbmcgui.Window(10000).getProperty('diggzportal_curr_window')

					wm.curr_window = json.loads(diggzportal_curr_window) if diggzportal_curr_window else None
					wm.prev_window = wm.curr_window

					wm.curr_window = json.loads(diggzportal_curr_window) if diggzportal_curr_window else None
					if wm.curr_window == None:
						wm.prev_window = json.loads(diggzportal_prev_window)
					else:
						wm.prev_window = wm.curr_window


					try: self.page = int(wm.prev_window['params']['page'])
					except: self.page = 1
				self.filter_label =wm.prev_window['params']['filter_label']

				self.sort = wm.prev_window['params']['sort']
				self.sort_label  = wm.prev_window['params']['sort_label']

				self.history_source = wm.prev_window['params'].get('history_source','combined')
				self.mode = wm.prev_window['params']['mode']
				self.type = wm.prev_window['params']['type']
				self.order = wm.prev_window['params']['order']
				self.search_str =wm.prev_window['params']['search_str']

				if 'Trakt Episodes/Movies in progress' in str(self.search_str) or 'Trakt Episodes/Movies in progress' in str(self.filter_label):
					response = get_trakt_playback('tv')
					listitems1 = []
					if response:
						for i in response:
							ep = extended_episode_info(i['show']['ids']['tmdb'], i['episode']['season'], i['episode']['number'])
							ep[0]['tmdb_id'] = ep[1]['tvshow_id']
							ep[0]['PercentPlayed'] = int(i['progress'])
							ep[0]['StartPercent'] = int(i['progress'])
							listitems1.append(ep[0])
					response = None
					response = get_trakt_playback('movie')
					if response:
						for i in response:
							mov = extended_movie_info(i['movie']['ids']['tmdb'])
							mov[0]['PercentPlayed'] = int(i['progress'])
							mov[0]['StartPercent'] = int(i['progress'])
							listitems1.append(mov[0])

					x = 0
					page = int(self.page)
					listitems = []
					for i in listitems1:
						if x + 1 <= page * 20 and x + 1 > (page - 1) *  20:
							listitems.append(i)
							x = x + 1
						else:
							x = x + 1

					wm.prev_window['params']['listitems'] = listitems
					wm.prev_window['params']['total_pages'] = int(x/20) + (1 if x % 20 > 0 else 0)
					wm.prev_window['params']['total_items'] = x
					#xbmc.log(str(listitems)+'===>OPEN_INFO', level=xbmc.LOGINFO)
					self.mode = 'trakt'
					self.type = 'movie'

				self.filter_label =wm.prev_window['params']['filter_label']
				self.list_id = wm.prev_window['params']['list_id']
				self.filter_url = wm.prev_window['params']['filter_url']
				self.media_type = wm.prev_window['params']['media_type']
				self.filters = wm.prev_window['params']['filters']
				self.filter = wm.prev_window['params']['filter']
				info = {
					'listitems': wm.prev_window['params']['listitems'],
					'results_per_page': wm.prev_window['params']['total_pages'],
					'total_results': wm.prev_window['params']['total_items']
					}
				self.focus_id = xbmcgui.Window(10000).getProperty('focus_id')
				self.position = xbmcgui.Window(10000).getProperty('position')
				if str(self.position) != 'No position':
					xbmc.executebuiltin('Control.SetFocus(%s,%s)' % (self.focus_id,self.position))
				wm.pop_video_list = False

				fetch_data_dict_file = write_fetch_data_dict_file()
				fetch_data_dict = {}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()

				return info

			if self.mode == 'reopen_window':
				fetch_data_dict_file = read_fetch_data_dict_file()
				import ast
				fetch_data_dict_read = ast.literal_eval(fetch_data_dict_file.read())
				info = self.get_fetch_data_dict_read(fetch_data_dict_read)

				if 'Trakt Episodes/Movies in progress' in str(self.search_str) or 'Trakt Episodes/Movies in progress' in str(self.filter_label):
					listitems1 = []
					response = get_trakt_playback('tv')
					if response:
						for i in response:
							for x in info['listitems']:
								if x['tmdb_id'] == i['show']['ids']['tmdb']:
									if x['episode'] == i['episode']['number'] and x['season'] == i['episode']['season']:
										x['PercentPlayed'] = int(i['progress'])
										x['StartPercent'] = int(i['progress'])
										listitems1.append(x)
					response = get_trakt_playback('movie')
					if response:
						for i in response:
							for x in info['listitems']:
								if x['tmdb_id'] == i['movie']['ids']['tmdb']:
									x['PercentPlayed'] = int(i['progress'])
									x['StartPercent'] = int(i['progress'])
									listitems1.append(x)
					info['listitems'] = listitems1
				reopen_window = True

				fetch_data_dict_file = write_fetch_data_dict_file()
				fetch_data_dict = {}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info


				if self.mode == 'trakt' and 'Trakt Watched Movies' in str(self.filter_label):
					self.search_str = trakt_watched_movies()
				if self.mode == 'trakt' and 'Trakt Watched Shows' in str(self.filter_label):
					#xbmc.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))+'===>PHIL', level=xbmc.LOGINFO)
					self.search_str = trakt_watched_tv_shows()
				if self.mode == 'trakt' and 'Trakt Unwatched Shows' in str(self.filter_label):
					self.search_str = trakt_unwatched_tv_shows()
			else:
				reopen_window = False

			fetch_data_dict_file = write_fetch_data_dict_file()
			sort_by = ('primary_release_date' if self.type == 'movie' and self.sort == 'release_date' and self.list_id == 'tmdb_newest' else self.sort) + '.' + self.order
			fetch_data_dict = {}



			if self.mode == 'trakt_catalog':
				from resources.lib import trakt_catalog as cat, accounts
				category=self.search_str['category']; value=self.search_str['value']; source=self.search_str.get('source','trakt')
				if category.startswith('history_'):
					from resources.lib import personal_history, accounts
					try:
						if force or 'ids' not in self.search_str or self.search_str.get('history_revision',0)!=accounts.HISTORY_REVISION or (source=='simkl' and self.search_str.get('simkl_identity')!=accounts.identity('simkl')):
							self.search_str['ids']=personal_history.pool(source,self.type,category)
							self.search_str['history_revision']=accounts.HISTORY_REVISION
							if source=='simkl': self.search_str['simkl_identity']=accounts.identity('simkl')
						ids=self.search_str['ids']; total=len(ids)
						items=personal_history.hydrate(self.type,ids[(self.page-1)*20:self.page*20],source,category)
					except Exception as exc:
						if source=='simkl':
							from resources.lib import simkl_api
							simkl_api.log_failure('personal history '+category,exc)
							self.search_str.pop('ids',None)
						xbmcgui.Dialog().notification(source.upper(),'Unable to retrieve personal history',xbmcgui.NOTIFICATION_ERROR)
						items=[]; total=0
					info={'listitems':items,'results_per_page':max(1,(total+19)//20),'total_results':total}
					self.sort_label=source.upper()+' history order'
					fetch_data_dict=self.update_fetch_data_dict(info,fetch_data_dict)
					fetch_data_dict_file.write(str(fetch_data_dict)); fetch_data_dict_file.close()
					return info
				is_random=category.startswith('random') or category=='personal_random'
				try:
					# Persist the ordered IDs in window state so restoring an info window
					# does not reroll random lists or move page boundaries.
					if force or 'ids' not in self.search_str or (source=='simkl' and (self.search_str.get('history_revision',-1)!=accounts.HISTORY_REVISION or self.search_str.get('simkl_identity')!=accounts.identity('simkl'))):
						if source=='trakt': self.search_str['ids']=cat.pool(self.type,category,value,force)
						else:
							from resources.lib import account_catalog
							self.search_str['ids']=[i for i in account_catalog.pool(source,self.type,category,value) if i]
						self.search_str['history_revision']=accounts.HISTORY_REVISION
						if source=='simkl': self.search_str['simkl_identity']=accounts.identity('simkl')
					ids=self.search_str['ids']
					if is_random:
						if force or not self.search_str.get('random_ids'):
							page_rows=cat.hydrate(self.type,category,value,ids[:60],maximum=20)
							self.search_str['random_ids']=[i['id'] for i in page_rows]
						else: page_rows=cat.hydrate(self.type,category,value,self.search_str['random_ids'])
						total=len(page_rows); pages=1
					else:
						total=len(ids); pages=max(1,(total+19)//20)
						page_rows=cat.hydrate(self.type,category if source=='trakt' else 'personal_list',value,ids[(self.page-1)*20:self.page*20])
				except Exception as exc:
					message='Unable to retrieve list'
					if source=='simkl':
						from resources.lib import simkl_api
						simkl_api.log_failure('browser '+category,exc)
						message=str(exc) if isinstance(exc,simkl_api.SimklError) else 'Unable to retrieve list; see kodi.log'
						self.search_str.pop('ids',None)
					xbmcgui.Dialog().notification(source.upper(),message,xbmcgui.NOTIFICATION_ERROR)
					page_rows=[]; total=0; pages=1
				handler=TheMovieDB.handle_tmdb_people if self.type=='person' else TheMovieDB.handle_tmdb_movies if self.type=='movie' else TheMovieDB.handle_tmdb_tvshows
				listitems=handler(page_rows) if self.type=='person' else handler(page_rows,sortkey=None) if page_rows else []
				self.sort_label='Random' if is_random else source.upper()+' list order'
				info={'listitems':listitems,'results_per_page':pages,'total_results':total}
				fetch_data_dict=self.update_fetch_data_dict(info,fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict)); fetch_data_dict_file.close()
				return info

			if self.mode == 'tmdb_ranked':
				from resources.lib import tmdb_catalog as catalog
				category = self.search_str['category']
				if category == 'search':
					data = catalog.search(TheMovieDB.get_tmdb_data, self.type, self.search_str['value'], self.page, xbmcaddon.Addon().getSetting('include_adults'), force)
					rows = data.get('results', [])
					if self.type == 'person':
						listitems = TheMovieDB.handle_tmdb_people(rows)
					else:
						handler = TheMovieDB.handle_tmdb_movies if self.type == 'movie' else TheMovieDB.handle_tmdb_tvshows
						listitems = handler(rows, sortkey=None) if rows else []
					self.sort_label = 'Relevance'
					info = {'listitems':listitems, 'results_per_page':max(1,min(500,int(data.get('total_pages') or 0))), 'total_results':int(data.get('total_results') or 0)}
					fetch_data_dict = self.update_fetch_data_dict(info,fetch_data_dict)
					fetch_data_dict_file.write(str(fetch_data_dict))
					fetch_data_dict_file.close()
					return info
				if self.type != 'person' and 'English / USA' not in self.filter_label:
					self.filter_label += ' - English / USA'
				if self.type == 'person':
					path = 'trending/person/'+category.split('/')[1] if category.startswith('trending/') else 'person/popular'
					if category == 'actors':
						rows = []
						for p in range(1,catalog.RANKED_PAGES+1):
							data = catalog.query(TheMovieDB.get_tmdb_data,path,{'language':'en-US','page':p},0.125)
							rows.extend(i for i in data.get('results',[]) if i.get('known_for_department')=='Acting')
							if p >= int(data.get('total_pages') or 0): break
						total = len(rows)
						pages = (total+19)//20
						rows = rows[(self.page-1)*20:self.page*20]
					else:
						data = catalog.query(TheMovieDB.get_tmdb_data,path,{'language':'en-US','page':self.page},0.125)
						rows = data.get('results',[])
						total = data.get('total_results',0)
						pages = min(500,data.get('total_pages',0))
					listitems = TheMovieDB.handle_tmdb_people(rows)
				else:
					if force or getattr(self,'_ranked_rows',None) is None:
						self._ranked_rows = self.search_str.get('random_rows') if category.startswith('random_') and not force else None
						if self._ranked_rows is None:
							self._ranked_rows = catalog.ranked(TheMovieDB.get_tmdb_data,self.type,category,self.search_str.get('value',''),force)
							if category.startswith('random_'): self.search_str['random_rows']=self._ranked_rows
					rows = self._ranked_rows
					total = len(rows)
					pages = (total+19)//20
					rows = rows[(self.page-1)*20:self.page*20]
					handler = TheMovieDB.handle_tmdb_movies if self.type=='movie' else TheMovieDB.handle_tmdb_tvshows
					listitems = handler(rows,sortkey=None) if rows else []
				info = {'listitems':listitems,'results_per_page':max(1,pages),'total_results':total}
				fetch_data_dict = self.update_fetch_data_dict(info,fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info

			if self.type == 'tv':
				temp = 'tv'
				rated = 'Rated TV shows'
				starred = 'Starred TV shows'
			else:
				temp = 'movies'
				rated = 'Rated movies'
				starred = 'Starred movies'


			if self.mode == 'search':
				#fetch_data_dict_file = write_fetch_data_dict_file()
				url = 'search/multi?query=%s&page=%i&include_adult=%s&' % (urllib.parse.quote_plus(self.search_str), self.page, xbmcaddon.Addon().getSetting('include_adults'))
				if self.search_str:
					self.filter_label = 'Results for:  ' + self.search_str.replace('Results for:  ','')
				else:
					self.filter_label = ''
				fetch_data_dict['self.search_str'] = self.search_str
				fetch_data_dict['self.filter_label'] = self.filter_label
				fetch_data_dict['self.page'] = self.page
				fetch_data_dict['self.sort'] = self.sort
				fetch_data_dict['self.sort_label'] = self.sort_label
				fetch_data_dict['self.order'] = self.order
				
			elif self.mode == 'person':
				#fetch_data_dict_file = write_fetch_data_dict_file()
				self.filter_label = 'Results for:  ' + self.search_str['person']
				listitems = self.search_str['cast_crew']
				info = {
					'listitems': listitems,
					'results_per_page': 1,
					'total_results': len(self.search_str['cast_crew'])
					}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info

			elif self.mode ==  'google_similar':
				movies = self.search_str
				x = 0
				page = int(self.page)

				listitems = []
				for i in movies:
					if x + 1 <= page * 20 and x + 1 > (page - 1) *  20:
						listitems.append(i)
						x = x + 1
					else:
						x = x + 1

				info = {
					'listitems': listitems,
					'results_per_page': int(int(x/20) + (1 if x % 20 > 0 else 0)),
					'total_results': len(self.search_str)
					}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info


			elif self.mode == 'list_items':
				#fetch_data_dict_file = write_fetch_data_dict_file()
				if int(self.page) == 1:
					self.filter_label = 'Results for:  ' + self.filter_label.replace('Results for:  ','')
				movies = self.search_str
				x = 0
				page = int(self.page)

				listitems = []
				for i in movies:
					if x + 1 <= page * 20 and x + 1 > (page - 1) *  20:
						listitems.append(i)
						x = x + 1
					else:
						x = x + 1

				info = {
					'listitems': listitems,
					'results_per_page': int(int(x/20) + (1 if x % 20 > 0 else 0)),
					'total_results': len(self.search_str)
					}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info
			elif self.mode == 'list':
				#fetch_data_dict_file = write_fetch_data_dict_file()
				url = 'list/%s?language=%s&' % (str(self.list_id), xbmcaddon.Addon().getSetting('LanguageID'))
				fetch_data_dict['self.list_id'] = self.list_id

			elif 'Trakt Calendar Episodes' in str(self.search_str) or 'Trakt Calendar Episodes' in str(self.filter_label):
				#url = 'https://api.trakt.tv/sync/playback/type?start_at=2023-09-26T00%3A00%3A00.000Z&end_at=2023-07-01T23%3A59%3A59.000Z'
				past_date = datetime.now() - timedelta(days=12)
				tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
				today = (datetime.now()).strftime('%Y-%m-%d')
				url = 'https://api.trakt.tv/calendars/my/shows/%s/14' % str(past_date.strftime('%Y-%m-%d'))
				response = get_trakt_data(url=url, cache_days=0.0001, folder='Trakt')
				listitems1 = []
				self.filter_label = 'Trakt Calendar Episodes' 
				for i in reversed(response):
					ep = extended_episode_info(i['show']['ids']['tmdb'], i['episode']['season'], i['episode']['number'])
					#if ep[0]['episode'] == '':
					#	season = extended_season_info(i['show']['ids']['tmdb'], i['episode']['season'])
					#	ep[1]['actors'] = season[1]['actors']
					#	ep[1]['crew'] = season[1]['crew']
					#	#ep[1]['guest_stars'] = season[1]['guest_stars']
					#	ep[0]['season'] = i['episode']['season']
					#	ep[0]['episode'] = i['episode']['number']
					#	ep[0]['Plot'] = season[1]['episodes'][i['episode']['number']-1]['Description']
					#	ep[0]['Description'] = season[1]['episodes'][i['episode']['number']-1]['Description']
					#	ep[0]['Votes'] = season[1]['episodes'][i['episode']['number']-1]['Votes']
					#	ep[0]['Rating'] = season[1]['episodes'][i['episode']['number']-1]['Rating']
					#	ep[0]['id'] = season[1]['episodes'][i['episode']['number']-1]['id']
					#	ep[0]['production_code'] = season[1]['episodes'][i['episode']['number']-1]['production_code']
					#	ep[0]['release_date'] = season[1]['episodes'][i['episode']['number']-1]['release_date']
					#	ep[0]['title'] = season[1]['episodes'][i['episode']['number']-1]['title']
					#	ep[0]['still'] = season[1]['episodes'][i['episode']['number']-1]['still'] 
					#	ep[0]['still_original'] = season[1]['episodes'][i['episode']['number']-1]['still_original'] 
					#	ep[0]['still_small'] = season[1]['episodes'][i['episode']['number']-1]['still_small'] 
					#	ep[0]['thumb'] = season[1]['episodes'][i['episode']['number']-1]['thumb'] 
					#	ep[1]['images'] = {}
					#	ep[1]['images']['still'] = season[1]['episodes'][i['episode']['number']-1]['still'] 
					#	ep[1]['images']['still_original'] = season[1]['episodes'][i['episode']['number']-1]['still_original'] 
					#	ep[1]['images']['still_small'] = season[1]['episodes'][i['episode']['number']-1]['still_small'] 
					#	ep[1]['images']['thumb'] = season[1]['episodes'][i['episode']['number']-1]['thumb'] 
					if ep[0]['release_date'] == tomorrow:
						ep[0]['title'] = ep[0]['title'] + '**'
					if ep[0]['release_date'] == today:
						ep[0]['title'] = ep[0]['title'] + '*'
					episode_title = str('%s - S%sE%s - %s' % (i['show']['title'], str(ep[0]['season']).zfill(2), str(ep[0]['episode']).zfill(2), ep[0]['title']))
					ep[0]['tmdb_id'] = ep[1]['tvshow_id']
					ep[0]['Plot'] = episode_title + ' \n ' + ep[0]['Plot']
					ep[0]['Description'] = episode_title + ' \n ' + ep[0]['Description'] 
					listitems1.append(ep[0])

				x = 0
				page = int(self.page)
				listitems = []
				for i in listitems1:
					if x + 1 <= page * 20 and x + 1 > (page - 1) *  20:
						listitems.append(i)
						x = x + 1
					else:
						x = x + 1

				#response['total_pages'] = y 
				total_pages = int(x/20) + (1 if x % 20 > 0 else 0)
				total_results = x
				#xbmc.log(str(listitems)+'===>OPEN_INFO', level=xbmc.LOGINFO)
				info = {
					'listitems': listitems,
					'results_per_page': total_pages,
					'total_results': total_results
					}
				self.mode = 'trakt'
				self.type = 'movie'
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info

			elif self.search_str == 'Trakt Episodes/Movies in progress':
				response = get_trakt_playback('tv')
				listitems1 = []
				if response:
					for i in response:
						ep = extended_episode_info(i['show']['ids']['tmdb'], i['episode']['season'], i['episode']['number'])
						ep[0]['tmdb_id'] = ep[1]['tvshow_id']
						ep[0]['PercentPlayed'] = int(i['progress'])
						listitems1.append(ep[0])
				response = get_trakt_playback('movie')
				if response:
					for i in response:
						mov = extended_movie_info(i['movie']['ids']['tmdb'])
						mov[0]['PercentPlayed'] = int(i['progress'])
						listitems1.append(mov[0])

				x = 0
				page = int(self.page)
				listitems = []
				for i in listitems1:
					if x + 1 <= page * 20 and x + 1 > (page - 1) *  20:
						listitems.append(i)
						x = x + 1
					else:
						x = x + 1

				#response['total_pages'] = y 
				total_pages = int(x/20) + (1 if x % 20 > 0 else 0)
				total_results = x
				#xbmc.log(str(listitems)+'===>OPEN_INFO', level=xbmc.LOGINFO)
				info = {
					'listitems': listitems,
					'results_per_page': total_pages,
					'total_results': total_results
					}
				self.mode = 'trakt'
				self.type = 'movie'
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info


			elif self.mode == 'trakt':
				#fetch_data_dict_file = write_fetch_data_dict_file()
				movies = self.search_str
				x = 0
				page = int(self.page)
				listitems = None
				responses = {'page': 1, 'results': [],'total_pages': 1, 'total_results': 0}
				if movies == None:
					info = {'listitems': None, 'results_per_page': 0, 'total_results': 0}
					return info

				for i in movies:
					response1 = None
					if (x + 1 <= page * 20 and x + 1 > (page - 1) *  20) or page == 0:
						try: 
							if i['type'] == 'movie':
								self.type = 'movie'
							else: 
								self.type = 'tv'
						except: 
							if "'movie': {'" in str(i) or 'movie' in str(self.filter_label).lower():
								self.type = 'movie'
							elif "'show': {'" in str(i) or not 'movie' in str(self.filter_label).lower():
								self.type = 'tv'
						try: 
							if self.type == 'movie':
								response1 = TheMovieDB.single_movie_info(i['movie']['ids']['tmdb'])
							else:
								response1 = TheMovieDB.single_tvshow_info(i['show']['ids']['tmdb'])
						#except TypeError:
						#	continue
						except KeyError or TypeError:
							try:
								if self.type == 'movie':
									response1 = TheMovieDB.single_movie_info(i['ids']['tmdb'])
								else:
									response1 = TheMovieDB.single_tvshow_info(i['ids']['tmdb'])
							except:
								continue
						if response1:
							responses['results'].append(response1)
						x = x + 1
					else:
						x = x + 1
				total_pages = int(x/20) + (1 if x % 20 > 0 else 0)
				total_results = x
				responses['total_pages'] = total_pages
				responses['total_results'] = total_results
				listitems = TheMovieDB.handle_tmdb_multi_search(responses['results'])
				info = {
					'listitems': listitems,
					'results_per_page': responses['total_pages'],
					'total_results': responses['total_results']
					}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return info
			else:
				#fetch_data_dict_file = write_fetch_data_dict_file()
				if reopen_window == False:
					self.set_filter_url()
					self.set_filter_label()

				url = 'discover/%s?sort_by=%s&%slanguage=%s&page=%i&append_to_response=external_ids&include_adult=%s&' % (self.type, sort_by, self.filter_url, ('en-US' if self.list_id == 'tmdb_newest' else xbmcaddon.Addon().getSetting('LanguageID')), int(self.page), xbmcaddon.Addon().getSetting('include_adults'))
			if self.list_id == 'tmdb_newest' and self.mode == 'filter' and self.type in ('movie','tv'):
				from resources.lib import tmdb_catalog as catalog
				# Provider and network availability is verified against fresh results.
				from urllib.parse import parse_qsl, urlsplit
				category_params = dict(parse_qsl(urlsplit(url).query))
				checked_category = any(k in category_params for k in ('with_watch_providers','with_networks','with_companies'))
				fresh_category = checked_category and self.page == 1 and addon.getSetting('catalog_hide_empty') != 'false'
				response = catalog.discover_page(TheMovieDB.get_tmdb_data,url,catalog.thresholds(self.type),0 if force or fresh_category else 2)
			elif force:
				response = TheMovieDB.get_tmdb_data(url=url, cache_days=0)
			else:
				response = TheMovieDB.get_tmdb_data(url=url, cache_days=2)
			if not response:
				info = {'listitems': [], 'results_per_page': 0, 'total_results': 0}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return None
			if 'results' not in response:
				info = {'listitems': [], 'results_per_page': 0, 'total_results': 0}
				fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
				fetch_data_dict_file.write(str(fetch_data_dict))
				fetch_data_dict_file.close()
				return {'listitems': [], 'results_per_page': 0, 'total_results': 0}
			if not response['results']:
				Utils.notify('No results found')
			if self.mode == 'search':
				listitems = TheMovieDB.handle_tmdb_multi_search(response['results'])
			elif self.type == 'movie':
				listitems = TheMovieDB.handle_tmdb_movies(results=response['results'], sortkey=None)
			else:
				listitems = TheMovieDB.handle_tmdb_tvshows(results=response['results'], sortkey=None)
			info = {
				'listitems': listitems,
				'results_per_page': max(1,min(500,response['total_pages'])),
				'total_results': response['total_results']
				}
			fetch_data_dict = self.update_fetch_data_dict(info, fetch_data_dict)
			fetch_data_dict_file.write(str(fetch_data_dict))
			fetch_data_dict_file.close()
			return info
	return DialogVideoList
