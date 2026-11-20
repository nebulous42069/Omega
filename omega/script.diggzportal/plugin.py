import xbmc
import sys, os
import xbmcgui, xbmcplugin
import requests,json,xbmcaddon,xbmcvfs
os.environ['first_run'] = str('True')

from resources.lib import process
from resources.lib import Utils
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short
from resources.lib import TheMovieDB

from resources.lib.browser_menu import BrowserMenu, ACCOUNT_STATE_MENUS

class Main(BrowserMenu):
	def __init__(self):
		xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
		self._parse_argv()
		self.sub_menu = self.params.get('sub_menu')
		root_menu = not self.infos

		for info in self.infos:
			listitems = process.start_info_actions([info], self.params)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_TITLE)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_DURATION)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

			if info.endswith('shows') or '=tv' in str(sys.argv):
				xbmcplugin.setContent(self.handle, 'tvshows')
			elif info.endswith('movies'):
				xbmcplugin.setContent(self.handle, 'movies')
			elif '=movie' in str(sys.argv):
				xbmcplugin.setContent(self.handle, 'movies')
			else:
				xbmcplugin.setContent(self.handle, 'addons')
			try:
				Utils.pass_list_to_skin(name=info, data=listitems, prefix=self.params.get('prefix', ''), handle=self.handle, limit=self.params.get('limit', ''))
			except:
				Utils.hide_busy()
				return

		if not root_menu:
			Utils.hide_busy()
		if root_menu:
			if not self.sub_menu:
				xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
				self.menu_item('Movie Portal',art=self.root_art('movie'),info='tmdb_browse',kind='movie',category='all',label='Movie Portal')
				self.menu_item('TV Show Portal',art=self.root_art('tv'),info='tmdb_browse',kind='tv',category='all',label='TV Show Portal')
				for key, label in [('simkl_browser','SIMKL Browser'),('sub_trakt','Trakt Browser'),('mdb_browser','MDBList Browser'),('tmdb_browser','TMDB Browser')]:
					self.menu_item(label, art=self.root_art({'sub_trakt':'trakt','mdb_browser':'mdblist','tmdb_browser':'tmdb','simkl_browser':'simkl'}[key]), sub_menu=key)
				self.menu_item('Mouse / Touchscreen Support', art=self.root_art('mouse-touch'), info='mouse_touch_support')
			else:
				self.populate_browser()
			Utils.hide_busy()
			xbmcplugin.endOfDirectory(self.handle, cacheToDisc=not bool(self.sub_menu and (self.sub_menu in ACCOUNT_STATE_MENUS or self.sub_menu.startswith('simkl_') or self.sub_menu.endswith(('_provider','_network','_studio','_account')))))

		xbmcgui.Window(10000).clearProperty(str(addon_ID_short())+'_running')

	def root_art(self, name):
		base = 'special://home/addons/'+str(addon_ID())+'/'
		icon = base+'resources/skins/Default/media/rootmenu/'+name+'.png'
		return {'thumb':icon,'icon':icon,'poster':icon,'fanart':base+'fanart.jpg'}

	def menu_item(self, display_label, art=None, **params):
		from urllib.parse import urlencode
		url = 'plugin://'+str(addon_ID())+'?'+urlencode(params)
		li = xbmcgui.ListItem(label=display_label)
		base = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/'
		thumb = 'trakt.png' if str(params.get('sub_menu','')).startswith('sub_trakt') or params.get('info')=='trakt_browse' else 'tmdb/thumb.png'
		default_art={'thumb':base+thumb,'icon':base+thumb,'fanart':base+'tmdb/fanart.jpg'}
		default_art.update(art or {})
		li.setArt(default_art)
		xbmcplugin.addDirectoryItem(handle=self.handle,url=url,listitem=li,isFolder='sub_menu' in params)

	def browser_artwork(self, kind, category, rows, source='tmdb'):
		from resources.lib import directory_art
		return directory_art.artwork(kind,category,rows,source)

	def _parse_argv(self):
		args = sys.argv[2][1:]
		self.handle = int(sys.argv[1])
		self.infos = []
		self.params = {'handle': self.handle}
		if args.startswith('---'):
			delimiter = '&'
			args = args[3:]
		else:
			delimiter = '&'
		for arg in args.split(delimiter):
			param = arg.replace('"', '').replace("'", " ")
			if param.startswith('info='):
				if param[5:]:
					self.infos.append(param[5:])
			else:
				try:
					self.params[param.split('=')[0].lower()] = '='.join(param.split('=')[1:]).strip()
				except:
					pass

		params = self.params
		search_flag = False
		search_text = None
		pop_index = []
		search_dict_name = None
		for idx, i in enumerate(params):
			if 'search_text' == i or 'str' == i:
				search_flag = True
				search_dict_name = i
			if search_flag == True and ('search_text' == i or 'str' == i):
				search_text = params[i]
			if search_text != None and params[i] == '' and search_flag == True:
				search_text = search_text + ', ' + i
				pop_index.append(i)

		if search_dict_name:
			for i in pop_index:
				params.pop(i)
			params[search_dict_name] = search_text
		if search_dict_name:
			self.params = params

if (__name__ == '__main__'):
	Main()
	del Main
	del sys
	del xbmcgui
	del xbmcplugin
	del requests
	del json
	del xbmcaddon
	del xbmcvfs
	del process
	del Utils
	del addon_ID
	del addon_ID_short
