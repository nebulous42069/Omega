from resources.lib import account_actions
import xbmc, xbmcgui, threading
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

def get_episode_window(window_type):

	class DialogEpisodeInfo(DialogBaseInfo, window_type):

		def __init__(self, *args, **kwargs):
			if Utils.netflix_view(info_only=True):
				super(DialogEpisodeInfo, self).__init__(*args, **kwargs)
				self.type = 'Episode'
				self.tvshow_id = kwargs.get('tvshow_id')
				data = TheMovieDB.extended_episode_info(tvshow_id=self.tvshow_id, season=kwargs.get('season'), episode=kwargs.get('episode'))
				if not data:
					return None
				self.info, self.data = data
				self.listitems = [
					(1000, self.data['actors'] + self.data['guest_stars']),
					(750, self.data['crew']),
					(1350, self.data['images'])
					]
			else:
				super(DialogEpisodeInfo, self).__init__(*args, **kwargs)
				self.type = 'Episode'
				self.tvshow_id = kwargs.get('tvshow_id')
				data = TheMovieDB.extended_episode_info(tvshow_id=self.tvshow_id, season=kwargs.get('season'), episode=kwargs.get('episode'))
				if not data:
					return None
				self.info, self.data = data
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
					(1000, self.data['actors'] + self.data['guest_stars']),
					(750, self.data['crew']),
					(1350, self.data['images'])
					]

		def onInit(self):
			super(DialogEpisodeInfo, self).onInit()
			try: clearlogo = TheMovieDB.get_fanart_clearlogo(tmdb_id=self.tvshow_id,media_type='tv')
			except: clearlogo = ''
			xbmcgui.Window(self.window_id).setProperty('movie.logo', str(clearlogo))
			xbmcgui.Window(10000).setProperty('movie.logo', str(clearlogo))
			Utils.pass_dict_to_skin(self.info, 'movie.', False, False, self.window_id)
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
			super(DialogEpisodeInfo, self).onClick(control_id)
			ch.serve(control_id, self)

		def onAction(self, action):
			from resources.lib.tmdb_helper import cancel_on_portal_input
			cancel_on_portal_input(self, action)
			if action.getId() == xbmcgui.ACTION_CONTEXT_MENU and self.getFocusId() in (8, 9, 10):
				return account_actions.menu(self, account_actions.target(self))
			super(DialogEpisodeInfo, self).onAction(action)
			ch.serve_action(action, self.getFocusId(), self)

		@ch.click(750)
		@ch.click(1000)
		def open_actor_info(self):
			wm.open_actor_info(prev_window=self, actor_id=self.listitem.getProperty('id'))

		@ch.action('play', 8)
		def context_play(self):
			tmdb_id = self.tvshow_id
			self.info['media_type'] = 'episode'
			Utils.context_play(window=self,tmdb_id = tmdb_id)

		@ch.action('contextmenu', 750)
		@ch.action('contextmenu', 1000)
		def context_menu(self):
			listitems = ['TV Show Info']
			listitems += ['Season Info']
			listitems += ['Search Person']
			selection = xbmcgui.Dialog().select(heading='Choose option', list=listitems)
			if selection == 0:
				wm.open_tvshow_info(prev_window=self, tmdb_id=self.tvshow_id)
			if selection == 1:
				wm.open_season_info(prev_window=self, tvshow_id=self.tvshow_id, season=self.info['season'], tvshow='')
			if selection == 2:
				self.close()
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=search_person,person=%s)' % self.listitem.getLabel())

		@ch.click(132)
		def open_text(self):
			wm.open_textviewer(header='Overview', text=self.info['Plot'], color='FFFFFFFF')


		@ch.action('contextmenu', 8)
		@ch.click(8)
		def play_episode(self):
			choose_player('plugin://plugin.video.themoviedb.helper?info=play&type=episode&tmdb_id=%s&season=%s&episode=%s' % (self.tvshow_id, self.info['season'], self.info['episode']))





	return DialogEpisodeInfo