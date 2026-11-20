from resources.lib import account_actions
import os, shutil, threading
import xbmc, xbmcgui, xbmcvfs, xbmcaddon
from resources.lib import Utils
from resources.lib import ImageTools
from resources.lib import TheMovieDB
from resources.lib.WindowManager import wm
from resources.lib.tmdb_helper import choose_player
from resources.lib.OnClickHandler import OnClickHandler
from resources.lib.DialogBaseInfo import DialogBaseInfo
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short
from resources.lib.trakt import trakt_next_episode_normal
from resources.lib.trakt import trakt_next_episode_rewatch
from resources.lib.trakt import trakt_calendar_hide_show

ch = OnClickHandler()

def get_tvshow_window(window_type):

	class DialogTVShowInfo(DialogBaseInfo, window_type):

		def __init__(self, *args, **kwargs):
			super(DialogTVShowInfo, self).__init__(*args, **kwargs)
			self.type = 'TVShow'
			data = TheMovieDB.extended_tvshow_info(tvshow_id=kwargs.get('tmdb_id', False))


			if Utils.netflix_view(info_only=True):
				#super(DialogTVShowInfo, self).__init__(*args, **kwargs)
				#self.type = 'TVShow'
				#data = TheMovieDB.extended_tvshow_info(tvshow_id=kwargs.get('tmdb_id', False))
				if not data:
					return None
				self.info, self.data = data
				self.info['poster'] = Utils.get_file(self.info.get('poster', ''))



				self.listitems = [
					(250, self.data['seasons']),
					(150, self.data['similar']),
					(1000, self.data['actors']),
					(750, self.data['crew']),
					(550, self.data['studios']),
					(1450, self.data['networks']),
					(850, self.data['genres']),
					(1250, self.data['images']),
					(1350, self.data['backdrops'])
					]
			else:
				#super(DialogTVShowInfo, self).__init__(*args, **kwargs)
				#self.type = 'TVShow'
				#data = TheMovieDB.extended_tvshow_info(tvshow_id=kwargs.get('tmdb_id', False))
				if not data:
					return None
				self.info, self.data = data
				self.info['poster'] = Utils.get_file(self.info.get('poster', ''))
				self.info['ImageFilter'], self.info['ImageColor'] = ImageTools.filter_image(input_img=self.info.get('thumb', ''), radius=25)
				"""
				try:
					filter_thread = ImageTools.FilterImageThread(self.data['backdrops'][0]['thumb'], 25)
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
					(250, self.data['seasons']),
					(150, self.data['similar']),
					(1000, self.data['actors']),
					(750, self.data['crew']),
					(550, self.data['studios']),
					(1450, self.data['networks']),
					(650, TheMovieDB.merge_with_cert_desc(self.data['certifications'], 'tv')),
					(850, self.data['genres']),
					(1250, self.data['images']),
					(1350, self.data['backdrops'])
					]

		def onInit(self):
			super(DialogTVShowInfo, self).onInit()
			Utils.pass_dict_to_skin(data=self.info, prefix='movie.', window_id=self.window_id)
			self.show_trailers()
			self.fill_lists()

		@ch.click(350)
		@ch.click(1150)
		def play_youtube_video(self):
			from resources.lib.YouTube import play_video
			play_video(self.listitem.getProperty('youtube_id') if self.listitem else '', dialog=self)

		@ch.click(28)
		def play_tv_trailer_button(self):
			TheMovieDB.play_trailer('tv', self.info['id'], windowed=True)

		@ch.click(29)
		def stop_tv_trailer_button(self):
			xbmc.executebuiltin('PlayerControl(Stop)')


		def onClick(self, control_id):
			if account_actions.button(self, control_id): return
			super(DialogTVShowInfo, self).onClick(control_id)
			ch.serve(control_id, self)

		def onAction(self, action):
			if action.getId() == xbmcgui.ACTION_CONTEXT_MENU and self.getFocusId() in (8, 9, 10):
				return account_actions.menu(self, account_actions.target(self))
			super(DialogTVShowInfo, self).onAction(action)
			ch.serve_action(action, self.getFocusId(), self)



		@ch.action('play', 250)
		def context_play(self):
			tmdb_id = self.info['id']
			self.info['media_type'] = 'season'
			Utils.context_play(window=self,tmdb_id = tmdb_id)

		@ch.action('play', 150)
		@ch.action('play', 9)
		def context_play(self):
			try: 
				tmdb_id = self.listitem.getProperty('id')
			except: 
				tmdb_id = self.info['id']
				self.info['media_type'] = 'tvshow'
			Utils.context_play(window=self,tmdb_id = tmdb_id)

		@ch.action('contextmenu', 150)
		def right_click_similar(self):
			return account_actions.menu(self, account_actions.target(self, True))

		@ch.click(750)
		@ch.click(1000)
		def credit_dialog(self):
			selection = xbmcgui.Dialog().contextmenu(['Show actor TV show appearances','Show Actor Information'])
			if selection == 0:
				self.open_credit_dialog(self.listitem.getProperty('credit_id'))
			if selection == 1:
				wm.open_actor_info(prev_window=self, actor_id=self.listitem.getProperty('id'))

		@ch.action('contextmenu', 750)
		@ch.action('contextmenu', 1000)
		def actor_context_menu(self):
			listitems = ['Search Person']
			selection = xbmcgui.Dialog().contextmenu([i for i in listitems])
			if selection == 0:
				self.close()
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=search_person,person=%s)' % self.listitem.getLabel())

		@ch.click(150)
		def open_tvshow_dialog(self):
			if self.listitem.getProperty('media_type') == 'movie':
				wm.open_movie_info(prev_window=self, movie_id=self.listitem.getProperty('id'))
			else:
				wm.open_tvshow_info(prev_window=self, tmdb_id=self.listitem.getProperty('id'))

		@ch.click(250)
		def open_season_dialog(self):
			wm.open_season_info(prev_window=self, tvshow_id=self.info['id'], season=self.listitem.getProperty('season'), tvshow=self.info['title'])

		@ch.action('contextmenu', 250)
		def season_context_menu(self):
			return account_actions.menu(self, account_actions.target(self, True))

		@ch.click(550)
		def open_company_info(self):
			filters = [
				{
					'id': self.listitem.getProperty('id'),
					'type': 'with_companies',
					'typelabel': 'Studios',
					'label': self.listitem.getLabel()#.decode('utf-8')
				}]
			wm.open_video_list(prev_window=self, filters=filters)

		@ch.click(850)
		def open_genre_info(self):
			filters = [
				{
					'id': self.listitem.getProperty('id'),
					'type': 'with_genres',
					'typelabel': 'Genres',
					'label': self.listitem.getLabel()#.decode('utf-8')
				}]
			wm.open_video_list(prev_window=self, filters=filters, media_type='tv')

		@ch.click(1450)
		def open_network_info(self):
			filters = [
				{
					'id': self.listitem.getProperty('id'),
					'type': 'with_networks',
					'typelabel': 'Networks',
					'label': self.listitem.getLabel()#.decode('utf-8')
				}]
			wm.open_video_list(prev_window=self, filters=filters, media_type='tv')





		@ch.click(6002)
		def open_list(self):
			index = xbmcgui.Dialog().select(heading='Choose list', list=['Starred TV shows', 'Rated TV shows'])

		@ch.click(6006)
		def open_rated_items(self):
			wm.open_video_list(prev_window=self, mode='rating', media_type='tv')

		@ch.action('contextmenu', 9)
		def context_menu(self):
			return account_actions.menu(self, account_actions.target(self))


		@ch.click(9)
		def play_tvshow(self):
			choose_player('plugin://plugin.video.themoviedb.helper?info=play&type=episode&tmdb_id=%s&season=1&episode=1' % self.info['id'])
		@ch.click(132)
		def open_text(self):
			wm.open_textviewer(header='Overview', text=self.info['Plot'], color='FFFFFFFF')





	return DialogTVShowInfo