from resources.lib import account_actions
import xbmc, xbmcgui, xbmcaddon, threading
from resources.lib import Utils
from resources.lib import ImageTools
from resources.lib import TheMovieDB
from resources.lib.WindowManager import wm
from resources.lib.tmdb_helper import choose_player
from resources.lib.OnClickHandler import OnClickHandler
from resources.lib.DialogBaseInfo import DialogBaseInfo
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short

ch = OnClickHandler()

def get_season_window(window_type):

	class DialogSeasonInfo(DialogBaseInfo, window_type):

		def __init__(self, *args, **kwargs):
			if Utils.netflix_view(info_only=True):
				super(DialogSeasonInfo, self).__init__(*args, **kwargs)
				self.type = 'Season'
				self.tvshow_id = kwargs.get('tvshow_id')
				data = TheMovieDB.extended_season_info(tvshow_id=self.tvshow_id, season_number=kwargs.get('season'))
				if not data:
					return None
				self.info, self.data = data
				self.info['poster'] = Utils.get_file(url=self.info.get('poster', ''))
				self.listitems = [
					(2000, self.data['episodes']),
					(1000, self.data['actors']),
					(750, self.data['crew']),
					(1250, self.data['images'])
					]
			else:
				super(DialogSeasonInfo, self).__init__(*args, **kwargs)
				self.type = 'Season'
				self.tvshow_id = kwargs.get('tvshow_id')
				data = TheMovieDB.extended_season_info(tvshow_id=self.tvshow_id, season_number=kwargs.get('season'))
				if not data:
					return None
				self.info, self.data = data
				self.info['poster'] = Utils.get_file(url=self.info.get('poster', ''))
				#self.info['ImageFilter'], self.info['ImageColor'] = ImageTools.filter_image(input_img=self.info.get('poster', ''), radius=25)
				self.info['ImageFilter'], self.info['ImageColor'] = ImageTools.filter_image(input_img=self.info.get('thumb', ''), radius=25)
				"""
				try:
					filter_thread = ImageTools.FilterImageThread(self.data['images'][0]['thumb'], 25)
					filter_thread.start()
					filter_thread.join()
					self.info['ImageFilter'] = filter_thread.image
					self.info['ImageColor'] = filter_thread.imagecolor
					filter_thread.terminate()
				except:
					#self.info['ImageFilter'] = ''
					#self.info['ImageColor'] = ''
					try: filter_thread.terminate()
					except: pass
				"""
				self.listitems = [
					(2000, self.data['episodes']),
					(1000, self.data['actors']),
					(750, self.data['crew']),
					(1250, self.data['images'])
					]

		def onInit(self):
			super(DialogSeasonInfo, self).onInit()
			try: clearlogo = TheMovieDB.get_fanart_clearlogo(tmdb_id=self.info['tmdb_id'],media_type='tv')
			except: clearlogo = ''
			xbmcgui.Window(self.window_id).setProperty('movie.logo', str(clearlogo))
			xbmcgui.Window(10000).setProperty('movie.logo', str(clearlogo))
			Utils.pass_dict_to_skin(data=self.info, prefix='movie.', window_id=self.window_id)
			self.show_trailers()
			self.fill_lists()

		@ch.click(350)
		@ch.click(1150)
		def play_youtube_video(self):
			from resources.lib.YouTube import play_video
			play_video(self.listitem.getProperty('youtube_id') if self.listitem else '', dialog=self)


		def onClick(self, control_id):
			from resources.lib.tmdb_helper import cancel_on_portal_input
			cancel_on_portal_input(self)
			if account_actions.button(self, control_id): return
			super(DialogSeasonInfo, self).onClick(control_id)
			ch.serve(control_id, self)

		def onAction(self, action):
			from resources.lib.tmdb_helper import cancel_on_portal_input
			cancel_on_portal_input(self, action)
			if action.getId() == xbmcgui.ACTION_CONTEXT_MENU and self.getFocusId() in (8, 9, 10):
				return account_actions.menu(self, account_actions.target(self))
			super(DialogSeasonInfo, self).onAction(action)
			ch.serve_action(action, self.getFocusId(), self)



		@ch.action('play', 10)
		def context_play(self):
			self.info['media_type'] = 'season'
			Utils.context_play(window=self,tmdb_id = self.tvshow_id)

		@ch.action('play', 2000)
		def context_play(self):
			self.info['media_type'] = 'episode'
			Utils.context_play(window=self,tmdb_id = self.info['tmdb_id'])

		@ch.click(750)
		@ch.click(1000)
		def open_actor_info(self):
			wm.open_actor_info(prev_window=self, actor_id=self.listitem.getProperty('id'))

		@ch.action('contextmenu', 750)
		@ch.action('contextmenu', 1000)
		def actor_context_menu(self):
			listitems = ['Show TV show information', 'Search Person']
			selection = xbmcgui.Dialog().contextmenu([i for i in listitems])
			if selection == 0:
				wm.open_tvshow_info(prev_window=self, tmdb_id=self.tvshow_id)
			if selection == 1:
				self.close()
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=search_person,person=%s)' % self.listitem.getLabel())

		@ch.click(2000)
		def open_episode_info(self):
			wm.open_episode_info(prev_window=self, tvshow=self.info['TVShowTitle'], tvshow_id=self.tvshow_id, season=self.listitem.getProperty('season'), episode=self.listitem.getProperty('episode'))

		@ch.action('contextmenu', 2000)
		def context_menu(self):
			return account_actions.menu(self, account_actions.target(self, True))



		@ch.action('play', 2000)
		@ch.action('playpause', 2000)
		@ch.action('pause', 2000)
		def play_episode(self):
			episode_id = self.listitem.getProperty('episode')
			url = 'plugin://plugin.video.themoviedb.helper?info=play&amp;tmdb_id=%s&amp;type=episode&amp;season=%s&amp;episode=%s' % (self.tvshow_id, self.listitem.getProperty('season'), episode_id)
			#xbmc.executebuiltin('Dialog.Close(all,true)')
			Utils.show_busy()
			choose_player(url)

		@ch.click(10)
		def play_season(self):
			url = 'plugin://plugin.video.themoviedb.helper?info=play&amp;type=episode&amp;tmdb_id=%s&amp;season=%s&amp;episode=1' % (self.tvshow_id, self.info['season'])
			#xbmc.executebuiltin('RunPlugin(%s)' % url)
			#xbmc.executebuiltin('Dialog.Close(all,true)')
			Utils.show_busy()
			choose_player(url)

		@ch.action('contextmenu', 10)
		def play_season_choose_player(self):
			return account_actions.menu(self, account_actions.target(self))





		@ch.click(132)
		def open_text(self):
			wm.open_textviewer(header='Overview', text=self.info['Plot'], color='FFFFFFFF')


	return DialogSeasonInfo