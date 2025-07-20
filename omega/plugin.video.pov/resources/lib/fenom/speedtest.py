import requests
from multiprocessing.dummy import Pool
from time import monotonic
import xbmc, xbmcaddon, xbmcgui
from fenom import sources as fs_sources

log = xbmc.log
Addon = xbmcaddon.Addon
list_item = xbmcgui.ListItem
select, dialog = xbmcgui.Dialog().select, xbmcgui.DialogProgress()
input, notification = xbmcgui.Dialog().input, xbmcgui.Dialog().notification

default_icon = Addon().getAddonInfo('icon')
movie_year_check_url = 'https://v2.sg.media-imdb.com/suggestion/t/%s.json'
total_str = 'TOTAL: [COLOR red][B]%s[/B][/COLOR]  |  '
total_str += '4K: [COLOR red][B]%d[/B][/COLOR]  |  1080p: [COLOR red][B]%d[/B][/COLOR]  |  '
total_str += '720p: [COLOR red][B]%d[/B][/COLOR]  |  SD: [COLOR red][B]%d[/B][/COLOR]'
input_str, nf_str = 'Enter a valid [B]Movie[/B] IMDb id:', 'Movie %s Not Found'
heading, resolutions = 'Magneto', '4K 1080p 720p SD'

def get_movie_source(module):
	try:
		start_time = monotonic()
		module.results = module.sources(module.data, {})
		module.elapsed = round(monotonic() - start_time, 3)
		if module.results is None: raise Exception(f"{heading.upper()}: {module.name} fatal error")
		for result in module.results:
			quality = result.get('quality')
			if not quality in module.metrics: module.metrics['SD'] += 1
			else: module.metrics[quality] = module.metrics.get(quality, 0) + 1
	except Exception as e: log(str(e), 1)
	return module

class Magneto:
	def __init__(self):
		self.data = {'imdb': 'tt0448134', 'title': 'Sunshine', 'aliases': [], 'year': 2007}
		self.data['poster'] = default_icon

	def speedtest(self):
		imdb_id = input(input_str, defaultt=self.data['imdb'])
		url = movie_year_check_url % imdb_id
		dialog.create(heading, 'Please Wait...')
		dialog.update(0, 'Fetching Metadata...')
		result = requests.get(url, timeout=5)
		if result.ok:
			result = result.json()
			items = (i for i in result['d'] if i['id'] == imdb_id)
			items = next(items, {}) if 'd' in result else {}
			for item in items:
				self.data['poster'] = items.get('i', {}).get('imageUrl')
				self.data['title'] = items.get('l')
				self.data['imdb'] = items.get('id')
				self.data['year'] = items.get('y')
				break
			else:
				dialog.close()
				return notification(heading, nf_str % imdb_id, time=3000)
		self.data['rootname'] = f"{self.data['title']} ({self.data['year']})"
		self.data['year'] = str(self.data['year'])

		modules = list(self.build_modules())
		len_modules = len(modules)
		line0 = 'Title: %s' % self.data['rootname']
		with Pool(len_modules or 1) as pool:
			for i, module in enumerate(pool.imap_unordered(get_movie_source, modules), 1):
				line1 = 'Source: %s' % module.name.upper()
				line2 = 'Elapsed: %.3f' % module.elapsed
				line3 = 'Results: %3d' % sum(module.metrics.values())
				dialog.update(int(i / len_modules * 100), '[CR]'.join((line0, line1, line2, line3)))
		pool.join()
		dialog.update(100, 'Processing Results...')
		modules.sort(key=lambda k: k.elapsed)
		results = [i for i in modules if i.results]
		modules = results + [i for i in modules if not i in results]
		items = list(self._make_items(modules))
		dialog.close()
		select(f"{heading} - {self.data['rootname']}", items, useDetails=True)

	def build_modules(self):
		for provider, module in fs_sources(ret_all=True):
			if not module.hasMovies: continue
			if provider.lower() in ('tidebrid', 'cmdebrid', 'mfdebrid'): continue
			m = module()
			m.results, m.elapsed = None, 0
			m.data, m.name = self.data, provider
			m.metrics = dict.fromkeys(resolutions.split(), 0)
			yield m

	def _make_items(self, modules):
		for i, module in enumerate(modules):
			try:
				values = list(module.metrics.values())
				total = 'NONE' if module.results is None else sum(values)
				line1 = '%s: %.3fs' % (module.name.upper(), module.elapsed)
				line2 = total_str % (total, *values)
				icon = self.data['poster'] or default_icon
				item = list_item(line1, line2, offscreen=True)
				item.setArt({'poster': icon})
				yield item
			except: pass

