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

ch = OnClickHandler()

def get_movie_window(window_type):

	class DialogVideoInfo(DialogBaseInfo, window_type):

		def __init__(self, *args, **kwargs):
			super(DialogVideoInfo, self).__init__(*args, **kwargs)
			self.type = 'Movie'
			#imdb_id = TheMovieDB.get_imdb_id_from_movie_id(kwargs.get('id'))
			#xbmc.log(str(imdb_id)+'===>OPENINFO', level=xbmc.LOGINFO)
			#xbmc.log(str(kwargs.get('id'))+'===>OPENINFO', level=xbmc.LOGINFO)
			data = TheMovieDB.extended_movie_info(movie_id=kwargs.get('id'))



			if Utils.netflix_view(info_only=True):
				#super(DialogVideoInfo, self).__init__(*args, **kwargs)
				#self.type = 'Movie'
				#data = TheMovieDB.extended_movie_info(movie_id=kwargs.get('id'))
				if not data:
					return None
				self.info, self.data = data
				sets_thread = SetItemsThread(self.info['SetId'])
				sets_thread.start()
				self.info['poster'] = Utils.get_file(self.info.get('poster', ''))
				sets_thread.join()
				self.setinfo = sets_thread.setinfo

				self.data['similar'] = [i for i in self.data['similar'] if i['id'] not in sets_thread.id_list]

				#if imdb_similar:
				#	for i in imdb_similar:
				#		if str(i) not in str(self.data['similar']):
				#			self.data['similar'].append(i)
				#self.data['similar'] = [i for i in self.data['similar'] if i['id'] not in sets_thread.id_list]
				#self.data['similar'] = sorted(self.data['similar'], key=lambda k: k['Popularity'], reverse=True)

				self.listitems = [
					(250, sets_thread.listitems),
					(1000, self.data['actors']),
					(750, Utils.merge_dict_lists(self.data['crew'])),
					(150, self.data['similar']),
					(550, self.data['studios']),
					(850, self.data['genres']),
					(1050, self.data['reviews']),
					(1250, self.data['images']),
					(1350, self.data['backdrops'])
					]
			else:
				#super(DialogVideoInfo, self).__init__(*args, **kwargs)
				#self.type = 'Movie'
				#data = TheMovieDB.extended_movie_info(movie_id=kwargs.get('id'))
				if not data:
					return None

				self.info, self.data = data
				sets_thread = SetItemsThread(self.info['SetId'])
				filter_thread = ImageTools.FilterImageThread(self.info.get('thumb', ''), 25)
				for thread in [sets_thread, filter_thread]:
					thread.start()
				self.info['poster'] = Utils.get_file(self.info.get('poster', ''))
				sets_thread.join()
				self.setinfo = sets_thread.setinfo

				filter_thread.join()
				self.info['ImageFilter'] = filter_thread.image
				self.info['ImageColor'] = filter_thread.imagecolor
				filter_thread.terminate()

				#if imdb_similar:
				#	for i in imdb_similar:
				#		if str(i) not in str(self.data['similar']):
				#			self.data['similar'].append(i)
				#self.data['similar'] = [i for i in self.data['similar'] if i['id'] not in sets_thread.id_list]
				#self.data['similar'] = sorted(self.data['similar'], key=lambda k: k['Popularity'], reverse=True)

				self.data['similar'] = [i for i in self.data['similar'] if i['id'] not in sets_thread.id_list]

				self.listitems = [
					(250, sets_thread.listitems),
					(150, self.data['similar']),
					(1000, self.data['actors']),
					(750, Utils.merge_dict_lists(self.data['crew'])),
					(550, self.data['studios']),
					(650, TheMovieDB.merge_with_cert_desc(self.data['releases'], 'movie')),
					(850, self.data['genres']),
					(1050, self.data['reviews']),
					(1250, self.data['images']),
					(1350, self.data['backdrops'])
					]

		def onInit(self):
			super(DialogVideoInfo, self).onInit()
			Utils.pass_dict_to_skin(data=self.info, prefix='movie.', window_id=self.window_id)
			Utils.pass_dict_to_skin(data=self.setinfo, prefix='movie.set.', window_id=self.window_id)
			self.show_trailers()
			self.fill_lists()

		@ch.click(350)
		@ch.click(1150)
		def play_youtube_video(self):
			from resources.lib.YouTube import play_video
			play_video(self.listitem.getProperty('youtube_id') if self.listitem else '', dialog=self)

		@ch.click(28)
		def play_movie_trailer_button(self):
			TheMovieDB.play_trailer('movie', self.info['id'], windowed=True)

		@ch.click(29)
		def stop_movie_trailer_button(self):
			xbmc.executebuiltin('PlayerControl(Stop)')


		def onClick(self, control_id):
			from resources.lib.tmdb_helper import cancel_on_portal_input
			cancel_on_portal_input(self)
			if account_actions.button(self, control_id): return
			super(DialogVideoInfo, self).onClick(control_id)
			ch.serve(control_id, self)

		def onAction(self, action):
			from resources.lib.tmdb_helper import cancel_on_portal_input
			cancel_on_portal_input(self, action)
			if action.getId() == xbmcgui.ACTION_CONTEXT_MENU and self.getFocusId() in (8, 9, 10):
				return account_actions.menu(self, account_actions.target(self))
			super(DialogVideoInfo, self).onAction(action)
			ch.serve_action(action, self.getFocusId(), self)



		@ch.click(1000)
		@ch.click(750)
		def open_actor_info(self):
			wm.open_actor_info(prev_window=self, actor_id=self.listitem.getProperty('id'))

		@ch.action('contextmenu', 750)
		@ch.action('contextmenu', 1000)
		def actor_context_menu(self):
			listitems = ['Search Person']
			selection = xbmcgui.Dialog().contextmenu([i for i in listitems])
			if selection == 0:
				self.close()
				xbmc.executebuiltin('RunScript('+str(addon_ID())+',info=search_person,person=%s)' % self.listitem.getLabel())

		@ch.action('play', 250)
		@ch.action('play', 150)
		@ch.action('play', 8)
		def context_play(self):
			try: 
				tmdb_id = self.listitem.getProperty('id')
			except: 
				tmdb_id = self.info['id']
				self.info['media_type'] = 'movie'
			Utils.context_play(window=self, tmdb_id = tmdb_id)

		@ch.action('contextmenu', 150)
		@ch.action('contextmenu', 250)
		def context_menu(self):
			return account_actions.menu(self, account_actions.target(self, True))

		@ch.click(150)
		@ch.click(250)
		def open_movie_info(self):
			if self.listitem.getProperty('media_type') == 'movie':
				wm.open_movie_info(prev_window=self, movie_id=self.listitem.getProperty('id'))
			else:
				wm.open_tvshow_info(prev_window=self, tmdb_id=self.listitem.getProperty('id'))

		@ch.click(550)
		def open_company_list(self):
			filters = [
				{
					'id': self.listitem.getProperty('id'),
					'type': 'with_companies',
					'typelabel': 'Studios',
					'label': self.listitem.getLabel()
				}]
			wm.open_video_list(prev_window=self, filters=filters)

		@ch.click(1050)
		def show_review(self):
			author = self.listitem.getProperty('author')
			text = '[B]%s[/B][CR]%s' % (author, Utils.clean_text(self.listitem.getProperty('content')))
			wm.open_textviewer(header='Plot', text=text, color='FFFFFFFF')

		@ch.click(850)
		def open_genre_list(self):
			filters = [
				{
					'id': self.listitem.getProperty('id'),
					'type': 'with_genres',
					'typelabel': 'Genres',
					'label': self.listitem.getLabel()
				}]
			wm.open_video_list(prev_window=self, filters=filters)

		@ch.click(650)
		def open_cert_list(self):
			filters = [
				{
					'id': self.listitem.getProperty('iso_3166_1'),
					'type': 'certification_country',
					'typelabel': 'Certification country',
					'label': self.listitem.getProperty('iso_3166_1')
				},
				{
					'id': self.listitem.getProperty('certification'),
					'type': 'certification',
					'typelabel': 'Certification',
					'label': self.listitem.getProperty('certification')
				},
				{
					'id': self.listitem.getProperty('year'),
					'type': 'year',
					'typelabel': 'Year',
					'label': self.listitem.getProperty('year')
				}]
			wm.open_video_list(prev_window=self, filters=filters)


		@ch.click(132)
		def show_plot(self):
			wm.open_textviewer(header='Plot', text=self.info['Plot'], color='FFFFFFFF')

		@ch.action('contextmenu', 8)
		@ch.click(8)
		def play_movie(self):
			choose_player('plugin://plugin.video.themoviedb.helper?info=play&type=movie&tmdb_id=%s' % self.info['id'])











	class SetItemsThread(threading.Thread):

		def __init__(self, set_id=''):
			threading.Thread.__init__(self)
			self.set_id = set_id

		def run(self):
			if self.set_id:
				self.listitems, self.setinfo = TheMovieDB.get_set_movies(self.set_id)
				self.id_list = [item['id'] for item in self.listitems]
			else:
				self.id_list = []
				self.listitems = []
				self.setinfo = {}

	return DialogVideoInfo
