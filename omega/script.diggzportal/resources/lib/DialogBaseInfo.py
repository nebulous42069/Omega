import xbmc, xbmcgui
from resources.lib import Utils
from resources.lib.appearance import apply_focus_appearance
from resources.lib import TheMovieDB
from resources.lib.WindowManager import wm
from resources.lib.OnClickHandler import OnClickHandler
from resources.lib.trakt import addon_ID_short

from resources.lib.Utils import tools_log as log
from inspect import currentframe, getframeinfo

ch = OnClickHandler()

class DialogBaseInfo(object):

	ACTION_PREVIOUS_MENU = [92, 9]
	ACTION_EXIT_SCRIPT = [13, 10]

	def __init__(self, *args, **kwargs):
		super(DialogBaseInfo, self).__init__(*args, **kwargs)
		# Use the actual loaded layout, not a potentially changed setting.
		self.windowed_trailers = bool(args and str(args[0]).endswith("-DialogVideoInfo-Netflix.xml"))
		self.bouncing = False
		self.data = None
		self.total_items = 0
		self.position = None
		self.info = {}
		self.history_source = (wm.curr_window or {}).get('params',{}).get('history_source','combined')

	def onInit(self, *args, **kwargs):
		super(DialogBaseInfo, self).onInit()
		apply_focus_appearance(self)
		from resources.lib import account_actions
		account_actions.set_properties(self)
		xbmcgui.Window(10000).setProperty('ImageColor', self.info.get('ImageColor', ''))
		self.window = xbmcgui.Window(self.window_id)
		self.window.setProperty('type', self.type)
		xbmcgui.Window(10000).setProperty('diggzportal_fanart', self.info.get('fanart', ''))

		#log(Utils.db_con)
		try: clearlogo = TheMovieDB.get_fanart_clearlogo(tmdb_id=self.info['tmdb_id'],media_type=self.info['media_type'])
		except: clearlogo = ''
		xbmcgui.Window(self.window_id).setProperty('movie.logo', str(clearlogo))
		#xbmcgui.Window(10000).setProperty('movie.tmdbid', str(self.info['tmdb_id']))
		xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_fanart', self.info.get('fanart', ''))
		xbmc.sleep(500)


	@ch.action('left', '*')
	@ch.action('right', '*')
	@ch.action('up', '*')
	@ch.action('down', '*')
	def save_position(self):
		# Scrolling controls and pointer navigation are not content selections.
		if self.getFocusId() in (23000,23001,23002,23003,23004,23005) or 24000 <= self.getFocusId() <= 26000:
			return
		currently_popping = xbmcgui.Window(10000).getProperty('currently_popping')
		if currently_popping != 'True':
			self.focus_id = self.getFocusId()
			try: self.position = self.getControl(self.focus_id).getSelectedPosition()
			except: self.position = xbmc.getInfoLabel("Container.Position")
			xbmcgui.Window(10000).setProperty('focus_id', str(self.focus_id))
			try:
				int_test = int(self.position)
				xbmcgui.Window(10000).setProperty('position', str(self.position))
			except:
				self.position = 'No Position'
				xbmcgui.Window(10000).setProperty('position', str('No Position'))
			wm.position = self.position
			wm.focus_id = self.focus_id
			xbmcgui.Window(10000).setProperty('focus_id', str(self.focus_id))
			xbmcgui.Window(10000).setProperty('position', str(self.position))
			xbmcgui.Window(10000).setProperty('pop_stack_focus_id', str(self.focus_id))
			xbmcgui.Window(10000).setProperty('pop_stack_position', str(self.position))

	def onAction(self, action):
		#xbmcgui.Window(10000).setProperty('focus_id', str(self.focus_id))
		#xbmcgui.Window(10000).setProperty('position', str(self.position))
		self.save_position()
		wm.wm_curr_windows_props()
		ch.serve_action(action, self.getFocusId(), self)

	def onClick(self, control_id):
		if control_id == 23000:
			self.control_id = getattr(self, "last_focus", None) or 23000
			return self.previous_menu()
		if control_id == 23001:
			return self.open_section_picker()
		if control_id in (23004, 23005):
			return self.step_section(1 if control_id == 23005 else -1)
		if control_id in (23002,23003) or 24000 <= control_id <= 26000:
			return  # Kodi's native scrollbar already processed the click.
		#xbmcgui.Window(10000).setProperty('focus_id', str(self.focus_id))
		#xbmcgui.Window(10000).setProperty('position', str(self.position))
		self.save_position()
		wm.wm_curr_windows_props()
		ch.serve(control_id, self)

	def section_choices(self):
		# A touch-friendly jump menu, populated from the actual nonempty rows in this dialog.
		if str(self.type).lower() == 'actor':
			rows = [(150,'Movie roles'),(250,'TV roles'),(550,'Movie crew'),(650,'TV crew'),(350,'Trailers'),(450,'Artwork'),(750,'Fanart')]
		else:
			rows = [(2000,'Episodes'),(250,'Seasons' if str(self.type).lower() == 'tvshow' else 'Collection'),(1000,'Cast'),(750,'Crew'),(150,'Recommended titles'),(1150,'Trailers'),(350,'Trailers'),(550,'Studios'),(1450,'Networks'),(650,'Releases'),(850,'Genres'),(1050,'Reviews'),(1250,'Artwork'),(1350,'Fanart')]
		choices = [(132,'Overview')] if xbmc.getCondVisibility('Control.IsVisible(132)') else []
		if str(self.type).lower() != 'actor': choices.append((5000,'Playback & account actions'))
		for cid, label in rows:
			try:
				count = self.getControl(cid).size()
			except (RuntimeError, AttributeError):
				continue
			if count: choices.append((cid, '%s (%d)' % (label, count)))
		return choices

	def focus_section(self, cid):
		try:
			self.setFocusId(cid)
			self._pointer_section_id = cid
		except RuntimeError:
			pass

	def open_section_picker(self):
		choices = self.section_choices()
		if not choices: return
		selected = xbmcgui.Dialog().select('Jump to section', [label for _,label in choices])
		if 0 <= selected < len(choices):
			self.focus_section(choices[selected][0])
		elif getattr(self, 'last_focus', None):
			try: self.setFocusId(self.last_focus)
			except RuntimeError: pass

	def step_section(self, direction):
		choices = self.section_choices()
		ids = [cid for cid, _ in choices]
		if not ids: return
		current = getattr(self, '_pointer_section_id', None)
		if current in ids:
			index = max(0, min(len(ids)-1, ids.index(current)+direction))
		else:
			index = 0 if direction > 0 else len(ids)-1
		self.focus_section(ids[index])

	def onFocus(self, control_id):
		if control_id in (23000,23001,23002,23003,23004,23005) or 24000 <= control_id <= 26000:
			return
		self.focus_id = self.getFocusId()
		if control_id == 132:
			self._pointer_section_id = 132
			self.setProperty('PortalInfoOverview', 'true')
		elif control_id in (7,8,9,10,11,28,29,445,460,461,462,463,464,465,5000):
			self._pointer_section_id = 5000
			self.setProperty('PortalInfoOverview', 'true')
		elif control_id in (150,250,350,450,550,650,750,850,1000,1050,1150,1250,1350,1450,2000):
			self._pointer_section_id = control_id
			self.clearProperty('PortalInfoOverview')
		self.save_position()
		if control_id == 20000:
			if not self.bouncing:
				self.bounce('up')
			self.setFocusId(self.last_focus)
			self.last_focus = control_id
		elif control_id == 20001:
			if not self.bouncing:
				self.bounce('down')
			self.setFocusId(self.last_focus)
			self.last_focus = control_id
		else:
			self.last_focus = control_id

	@Utils.run_async
	def bounce(self, identifier):
		self.bouncing = True
		self.window.setProperty('Bounce.' + identifier, 'true')
		xbmc.sleep(100)
		self.window.clearProperty('Bounce.' + identifier)
		self.bouncing = False

	def fill_lists(self):
		for container_id, listitems in self.listitems:
			self.getControl(container_id).reset()
			self.getControl(container_id).addItems(Utils.create_listitems(listitems,preload_images=0, enable_clearlogo=False, info=self.info, history_source=self.history_source))
		xbmc.sleep(100)
		currently_popping = xbmcgui.Window(10000).getProperty('currently_popping')
		if currently_popping == 'True':
			try: wm_curr_window_focus_id = int(wm.curr_window['params']['focus_id'])
			except: wm_curr_window_focus_id = 0
			try: wm_curr_window_position = int(wm.curr_window['params']['position'])
			except: wm_curr_window_position = 0

			if wm_curr_window_focus_id > 0:
				self.focus_id = wm_curr_window_focus_id
			else:
				try: self.focus_id = int(self.focus_id)
				except: self.focus_id = None

			if wm_curr_window_position > 0:
				self.position = wm_curr_window_position
			else:
				try: self.position = int(self.position)
				except: self.position = 0
			pop_stack_position = self.position
			pop_stack_focus_id = self.focus_id

		else:
			self.focus_id = xbmcgui.Window(10000).getProperty('focus_id')
			self.position = xbmcgui.Window(10000).getProperty('position')
			pop_stack_focus_id = xbmcgui.Window(10000).getProperty('pop_stack_focus_id')
			pop_stack_position = xbmcgui.Window(10000).getProperty('pop_stack_position')

		if pop_stack_focus_id != 500:
			self.focus_id = pop_stack_focus_id
			self.position = pop_stack_position
		try: focus_id_int = int(self.focus_id)
		except: focus_id_int = 0
		if str(self.focus_id) != '':
			xbmc.sleep(100)

			try: self.focus_id = int(self.focus_id)
			except: self.focus_id = 500
			if self.focus_id != 500:
				self.setFocusId(int(self.focus_id))
				if str(self.position) != 'No position':
					xbmc.sleep(100)
					try:
						self.getControl(self.focus_id).selectItem(self.position)
						xbmc.sleep(100)
						self.setFocusId(self.focus_id)
					except:
						control = self.getControl(self.focus_id)
						xbmc.sleep(100)
						self.setFocus(control)
				new_focus_id = self.getFocusId()
				try: new_position = self.getControl(self.focus_id).getSelectedPosition()
				except: new_position = xbmc.getInfoLabel("Container.Position")
				try: test_position = int(self.position)
				except: test_position = None

				window_id = xbmcgui.getCurrentWindowId()
				focused_control = window = xbmcgui.Window(window_id).getFocusId()
				diggzportal_window_number = xbmcgui.Window(10000).getProperty('diggzportal_window_number')


				if xbmc.getCondVisibility('Control.IsVisible(%s)' % self.focus_id) == False:
					xbmc.executebuiltin('Control.SetFocus(%s,%s)' % (self.focus_id,self.position))
				if xbmc.getCondVisibility('Control.IsVisible(%s)' % self.focus_id) == True:
					if self.focus_id == new_focus_id:
						if test_position:
							if new_position == test_position:
								xbmcgui.Window(10000).clearProperty('currently_popping')
						else:
							xbmcgui.Window(10000).clearProperty('currently_popping')


		restore = getattr(self, '_trailer_restore_focus', None)
		if restore is not None:
			self._trailer_restore_focus = None
			focus, position = restore
			try:
				self.setFocusId(focus)
				if position is not None:
					self.getControl(focus).selectItem(position)
			except (AttributeError, RuntimeError):
				pass


	@ch.click(1250)
	@ch.click(1350)
	def open_image(self):
		listitems = next((v for (i, v) in self.listitems if i == self.control_id), None)
		index = self.control.getSelectedPosition()
		pos = wm.open_slideshow(listitems=listitems, index=index)
		self.control.selectItem(pos)



	@ch.action('parentdir', '*')
	@ch.action('parentfolder', '*')
	#@ch.action('back', '*')
	def previous_menu(self):
		import sys
		if 'script=false' in str(sys.argv).lower() or 'diamondinfo' in str(sys.argv) or addon_ID_short() in str(sys.argv) or 'extendedinfo' in str(sys.argv) or 'extendedactorinfo' in str(sys.argv) or 'extendedtvinfo' in str(sys.argv) or 'seasoninfo' in str(sys.argv) or 'extendedepisodeinfo' in str(sys.argv):
			window_stack_enable2 = False
			if 'script=true' in str(sys.argv).lower() or 'reopen_window' in str(sys.argv).lower() :
				window_stack_enable2 = True
		else:
			window_stack_enable2 = True

		if Utils.window_stack_enable == 'false' and window_stack_enable2:
			self.close()
			try: del self
			except: pass
			return wm.open_video_list(search_str='', mode='reopen_window')

		onback = self.window.getProperty('%i_onback' % self.control_id)
		if onback:
			xbmc.executebuiltin(onback)
		else:
			#self.close()
			self.close()
			log('wm.pop_stack()',str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
			xbmcgui.Window(10000).clearProperty('diggzportal_window_number')
			wm.pop_stack()

	@ch.action('previousmenu', '*')
	def exit_script(self):
		xbmcgui.Window(10000).clearProperty('currently_popping')
		Utils.db_con.close()
		self.close()
		try: del self
		except: pass


	def show_trailers(self):
		# Some skins use 1150, others use 350 for their single trailer row.
		for control_id in (1150, 350):
			try:
				row = self.getControl(control_id)
			except RuntimeError:
				continue
			row.reset()
			items = []
			for trailer in self.data.get('videos', []):
				item = xbmcgui.ListItem(label=trailer['title'])
				item.setArt({'thumb': trailer['thumb'], 'icon': trailer['thumb']})
				item.setProperty('youtube_id', trailer['youtube_id'])
				item.setProperty('title', trailer['title'])
				item.setProperty('type', 'Trailer')
				items.append(item)
			row.addItems(items)
			break

	def open_credit_dialog(self, credit_id):
		info = TheMovieDB.get_credit_info(credit_id)
		listitems = []
		if 'seasons' in info['media']:
			listitems += TheMovieDB.handle_tmdb_seasons(info['media']['seasons'])
		if 'episodes' in info['media']:
			listitems += TheMovieDB.handle_tmdb_episodes(info['media']['episodes'])
		if not listitems:
			listitems += [{'label': 'No information available'}]
		listitem, index = wm.open_selectdialog(listitems=listitems)
		if listitem['media_type'] == 'episode':
			wm.open_episode_info(prev_window=self, season=listitems[index]['season'], episode=listitems[index]['episode'], tvshow_id=info['media']['id'])
		elif listitem['media_type'] == 'season':
			wm.open_season_info(prev_window=self, season=listitems[index]['season'], tvshow_id=info['media']['id'])