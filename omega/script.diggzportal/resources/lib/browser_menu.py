"""Shared service directory and in-dialog menu definitions."""
import xbmcgui
from resources.lib import TheMovieDB

# These directories depend on current credentials and must not be cached by Kodi.
ACCOUNT_STATE_MENUS = frozenset((
	'tmdb_browser','sub_trakt','mdb_browser','simkl_browser',
	'tmdb_account','trakt_account','mdblist_account','simkl_account',
	'my_tmdb_root','my_trakt_root','mdb_personal_root','simkl_personal',
	'simkl_custom','simkl_discover'))

class BrowserMenu:
	def populate_browser(self):
		if self.sub_menu in ('trakt_account','mdblist_account','tmdb_account'): self.service_account_menu(self.sub_menu[:-8])
		elif self.sub_menu.startswith('simkl_'): self.simkl_menu()
		elif self.sub_menu.startswith(('mdb_','my_tmdb_','my_trakt_')): self.account_menu()
		elif self.sub_menu.startswith('sub_trakt'): self.trakt()
		elif self.sub_menu.startswith('tmdb_'): self.tmdb_menu()

	def service_account_menu(self, source):
		from resources.lib import accounts
		if accounts.configured(source): return
		name=accounts.SERVICE_NAMES[source]
		if accounts.manager_available(): self.menu_item('Authorize in Account Manager',info='account_manager',source=source,browser_auth='true')
		self.menu_item('Authorize '+name+' (standalone)',info='account_login',source=source,browser_auth='true')

	def authorization_entry(self, source):
		from resources.lib import accounts
		if not accounts.configured(source):
			self.menu_item('Authorize '+accounts.SERVICE_NAMES[source]+' Account',sub_menu=source+'_account')

	def browser_artwork(self, kind, category, rows, source='tmdb'):
		return [None] * len(rows)

	def tmdb_menu(self):
		from resources.lib import tmdb_catalog as catalog
		from datetime import date
		if self.sub_menu == 'tmdb_browser':
			self.menu_item('My TMDB',sub_menu='my_tmdb_root')
			for key, label in [('tmdb_movie','TMDB Movies'),('tmdb_tv','TMDB TV Shows'),('tmdb_people','TMDB People')]:
				self.menu_item(label, sub_menu=key)
			self.authorization_entry('tmdb')
			return
		if self.sub_menu == 'tmdb_people':
			self.menu_item('Search People',info='tmdb_search',kind='person')
			for category,label in [('popular','Popular People'),('trending/day','Trending People Today'),('trending/week','Trending People This Week'),('actors','Popular Actors')]:
				self.menu_item(label,info='tmdb_browse',kind='person',category=category,label=label)
			return
		parts=self.sub_menu.split('_')
		kind=parts[1]
		if kind not in ('movie','tv'): return
		noun='Movies' if kind=='movie' else 'TV Shows'
		def leaf(category,label,value='',art=None):
			self.menu_item(label,art=art,info='tmdb_browse',kind=kind,category=category,value=value,label=label)
		if len(parts)==2:
			self.menu_item('Search '+noun,info='tmdb_search',kind=kind)
			for category,label,folder in catalog.menu_entries(kind):
				if folder: self.menu_item(label,sub_menu=self.sub_menu+'_'+category)
				else: leaf(category,label)
			return
		category='_'.join(parts[2:])
		from resources.lib import directory_art
		rows=catalog.submenu_entries(TheMovieDB.get_tmdb_data,kind,category)
		for (value,label),art in zip(rows,self.browser_artwork(kind,category,rows)):
			leaf(category,label,value,art)

	def trakt(self):
		from resources.lib import trakt_catalog as cat
		parts=self.sub_menu.split('_',3)
		if len(parts)==2:
			self.menu_item('My Trakt',sub_menu='my_trakt_root')
			for kind,label in [('movie','Trakt Movies'),('tv','Trakt TV Shows'),('person','Trakt People')]:
				self.menu_item(label,sub_menu='sub_trakt_'+kind)
			self.authorization_entry('trakt')
			return
		kind=parts[2]
		if kind=='person':
			self.menu_item('Search Trakt People',info='trakt_browse',kind='person',category='search',label='Trakt People')
			self.menu_item('Popular People (TMDb)',info='tmdb_browse',kind='person',category='popular',label='Popular People (TMDb)')
			return
		if kind not in ('movie','tv'): return
		try:
			if len(parts)==3:
				for category,label,folder in cat.entries(kind):
					if category=='personal': continue
					if folder: self.menu_item(label,sub_menu=self.sub_menu+'_'+category)
					else: self.menu_item(label,info='trakt_browse',kind=kind,category=category,label=label)
			else:
				category=parts[3]
				from resources.lib import directory_art
				rows=cat.choices(kind,category)
				for (value,label),art in zip(rows,self.browser_artwork(kind,category,rows,'trakt')):
					self.menu_item(label,art=art,info='trakt_browse',kind=kind,category=category,value=value,label=label)
		except Exception as exc:
			xbmcgui.Dialog().notification('Trakt',str(exc)[:160],xbmcgui.NOTIFICATION_ERROR)

	def account_menu(self):
		from resources.lib import account_catalog as cat, accounts, trakt_catalog
		key=self.sub_menu
		if key=='mdb_browser':
			self.menu_item('My MDBList',sub_menu='mdb_personal_root')
			for kind,label in [('movie','MDBList Movies'),('tv','MDBList TV Shows')]: self.menu_item(label,sub_menu='mdb_public_'+kind)
			self.authorization_entry('mdblist')
			return
		prefix,kind=key.rsplit('_',1)
		source='tmdb' if prefix=='my_tmdb' else 'trakt' if prefix=='my_trakt' else 'mdblist'
		if kind=='root':
			if not accounts.configured(source):
				self.service_account_menu(source)
				return
			for k,label in [('movie','Movies'),('tv','TV Shows')]: self.menu_item(label,sub_menu=prefix+'_'+k)
			return
		if kind not in ('movie','tv'): return
		if source=='trakt':
			for value,label in trakt_catalog.choices(kind,'personal'):
				self.menu_item(label,info='trakt_browse',kind=kind,category='personal',value=value,label=label)
			return
		rows=cat.entries(source,kind) if prefix=='mdb_public' else cat.personal_entries(source,kind)
		for category,label in rows: self.menu_item(label,info='account_browse',source=source,kind=kind,category=category,label=label)


	def simkl_menu(self):
		from resources.lib import simkl_api as simkl, simkl_discovery as discovery
		key=self.sub_menu
		groups=[('movies','Movies'),('tv','TV Shows'),('anime_tv','Anime Series'),('anime_movie','Anime Movies')]
		def leaf(label,kind,category,value=''):
			self.menu_item(label,info='account_browse',source='simkl',kind=kind,category=category,value=str(value),label=label)
		def media_kind(group):
			return ('anime' if group.startswith('anime_') else 'tv' if group=='shows' else group, 'movie' if group in ('movies','anime_movie') else 'tv')
		def folder(prefix,group,label): self.menu_item(label,sub_menu=prefix+group)
		if key=='simkl_browser':
			self.menu_item('My SIMKL',sub_menu='simkl_personal')
			for group,label in [('movies','Movies'),('tv','TV Shows'),('anime','Anime')]:
				folder('simkl_public_',group,'SIMKL '+label)
			self.menu_item('SIMKL Custom Lists (PRO/VIP)',sub_menu='simkl_custom')
			self.menu_item('Discover on SIMKL',sub_menu='simkl_discover')
			self.authorization_entry('simkl')
			return
		if key=='simkl_account':
			self.service_account_menu('simkl')
			return
		if key=='simkl_personal':
			if not simkl.configured():
				self.service_account_menu('simkl'); return
			for group,label in [('movies','Movies'),('shows','TV Shows'),('anime_tv','Anime Series'),('anime_movie','Anime Movies')]: folder('simkl_personal_',group,label)
			return
		if key=='simkl_discover':
			for group,label in groups:
				media,kind=media_kind(group)
				leaf('Random Trending '+label+' on SIMKL',kind,'public_'+media+':random')
				if simkl.configured(): leaf('Unwatched Trending '+label+' on SIMKL',kind,'public_'+media+':unwatched')
			return
		if key=='simkl_custom':
			if not simkl.configured():
				self.authorization_entry('simkl'); return
			for group,label in groups: folder('simkl_custom_',group,label)
			return
		if key.startswith('simkl_custom_'):
			group=key[len('simkl_custom_'):]; media,kind=media_kind(group)
			for selection,label in [('own','My Custom Lists'),('followed','Followed Lists'),('shared','Shared Lists'),('favorites','Favorites'),('user','Browse by User ID'),('id','Browse by List ID')]:
				leaf(label,kind,'custom_'+media+':'+selection)
			return
		if key.startswith('simkl_genres_'):
			group=key[len('simkl_genres_'):]; media,kind=media_kind(group)
			try:
				for value,label in discovery.genre_choices(media): leaf(label+' - Trending on SIMKL',kind,'public_'+media+':genre',value)
			except Exception as exc:
				simkl.log_failure('genre index '+media,exc)
				xbmcgui.Dialog().notification('SIMKL',str(exc) if isinstance(exc,simkl.SimklError) else 'Unable to retrieve genres',xbmcgui.NOTIFICATION_ERROR)
			return
		if key.startswith('simkl_tmdb_'):
			# These paths all stay in account_browse/source=simkl for watched indicators.
			kind,selection=key[len('simkl_tmdb_'):].split('_',1)
			try:
				rows=discovery.tmdb_choices(kind,selection)
				for (value,label),art in zip(rows,self.browser_artwork(kind,selection,rows)):
					self.menu_item(label+' (TMDB)',art=art,info='account_browse',source='simkl',kind=kind,category='public_tmdb:'+selection,value=str(value),label=label+' (TMDB / Top 100)')
			except Exception as exc:
				simkl.log_failure('TMDB directory '+selection,exc)
				xbmcgui.Dialog().notification('SIMKL','Unable to retrieve TMDB choices',xbmcgui.NOTIFICATION_ERROR)
			return
		if key.startswith('simkl_public_'):
			group=key[13:]
			if group=='anime':
				folder('simkl_public_','anime_tv','Anime Series')
				folder('simkl_public_','anime_movie','Anime Movies'); return
			if group not in dict(groups): return
			media,kind=media_kind(group)
			for period,label in [('today','Trending Today'),('week','Trending This Week'),('month','Trending This Month')]:
				leaf(label+' on SIMKL',kind,'public_'+media+':'+period)
			folder('simkl_genres_',group,'Trending by Genre on SIMKL')
			leaf('Top Rated on SIMKL (Trending This Month)',kind,'public_'+media+':top_rated')
			leaf('Latest '+('Releases' if kind=='movie' else 'Premieres')+' on SIMKL (30 Days)',kind,'public_'+media+':recent')
			if media=='movies': leaf('DVD / Blu-ray Releases on SIMKL',kind,'public_movies:dvd')
			if kind=='tv':
				for selection,label in [('today_calendar','Airing Today'),('week_calendar','Airing This Week'),('upcoming','Upcoming Episodes (33 Days)'),('premieres','Upcoming New Premieres')]: leaf(label+' on SIMKL',kind,'public_'+media+':'+selection)
			else: leaf('Upcoming Releases on SIMKL (33 Days)',kind,'public_'+media+':upcoming')
			if simkl.configured(): leaf('Search SIMKL',kind,'public_'+media+':search')
			else: self.menu_item('Authorize SIMKL to Search',sub_menu='simkl_account')
			if media in ('movies','tv'):
				for selection,label in [('provider','Streaming Providers (TMDB / US)'),('year','Years (TMDB)'),('decade','Decades (TMDB)')]+([('network','Networks (TMDB)')] if kind=='tv' else []):
					self.menu_item(label,sub_menu='simkl_tmdb_'+kind+'_'+selection)
			return
		if not key.startswith('simkl_personal_'): return
		group=key[15:]; media,kind=media_kind(group)
		actual='shows' if media=='tv' else media
		statuses=[('all','All My Titles')]+simkl.STATUSES
		if actual=='movies': statuses=[s for s in statuses if s[0] in ('all','plantowatch','completed','dropped')]
		for status,label in statuses: leaf(label,kind,actual+':'+status)
		leaf('Continue Watching',kind,'history_simkl_resume_'+media)
		if media=='tv': leaf('Next Up - TV Episodes',kind,'history_simkl_next_tv')
		leaf('My Ratings',kind,'personal_'+media+':rated')
		leaf('My Upcoming Calendar',kind,'personal_'+media+':calendar')
		if kind=='tv': leaf('My Shows with Episodes Remaining',kind,'personal_'+media+':remaining')
