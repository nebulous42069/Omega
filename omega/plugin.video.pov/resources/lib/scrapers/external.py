import json, time
from threading import Thread
from windows import create_window
from caches.providers_cache import ExternalProvidersCache
from modules import kodi_utils, source_utils
from modules.debrid import debrid_list, DebridCheck
from modules.utils import clean_file_name, TaskPool
from modules.settings import display_sleep_time, date_offset
# logger = kodi_utils.logger

ls, sleep, monitor, get_setting = kodi_utils.local_string, kodi_utils.sleep, kodi_utils.monitor, kodi_utils.get_setting
get_property, set_property, clear_property = kodi_utils.get_property, kodi_utils.set_property, kodi_utils.clear_property
notification, hide_busy_dialog, progressDialogBG = kodi_utils.notification, kodi_utils.hide_busy_dialog, kodi_utils.progressDialogBG
normalize, get_filename_match, get_file_info = source_utils.normalize, source_utils.get_filename_match, source_utils.get_file_info
pack_display, format_line, total_format = '%s (%s)', '%s[CR]%s[CR]%s', '[COLOR %s][B]%s[/B][/COLOR]'
int_format, ext_format = '[COLOR %s][B]Int: [/B][/COLOR]%s', '[COLOR %s][B]Ext: [/B][/COLOR]%s'
ext_scr_format, unfinshed_import_format = '[COLOR %s][B]%s[/B][/COLOR]', '[COLOR red]+%s[/COLOR]'
diag_format, resolutions = '4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s', '4K 1080p 720p SD'
cached_debrids = {'Real-Debrid', 'AllDebrid', 'tidebrid', 'mfdebrid', 'cmdebrid'}
season_display, show_display = ls(32537), ls(32089)
pack_check = (season_display, show_display)

class source:
	def __init__(self, source_dict, debrid_torrents, debrid_hosters, internal_scrapers, prescrape_sources, display_uncached_torrents, progress_dialog, disabled_ignored=False):
		self.scrape_provider = 'external'
		self.debrid_torrents, self.debrid_hosters = debrid_torrents, debrid_hosters
		self.source_dict, self.hostDict = source_dict, self.make_host_dict()
		self.internal_scrapers, self.prescrape_sources = internal_scrapers, prescrape_sources
		self.display_uncached_torrents = display_uncached_torrents
		self.disabled_ignored, self.progress_dialog = disabled_ignored, progress_dialog
		self.internal_activated, self.internal_prescraped = len(self.internal_scrapers) > 0, len(self.prescrape_sources) > 0
		self.processed_prescrape, self.threads_completed = False, False
		self.sources, self.cached_sources = [], []
		self.processed_internal_scrapers, self.final_sources = [], []
		self.processed_internal_scrapers_append = self.processed_internal_scrapers.append
		self.sleep_time = display_sleep_time()
		self.int_dialog_highlight, self.ext_dialog_highlight = get_setting('int_dialog_highlight', 'darkgoldenrod'), get_setting('ext_dialog_highlight', 'dodgerblue')
		self.finish_early, self.load_action = get_setting('search.finish.early') == 'true', get_setting('load_action') == '1'
		self.int_total, self.ext_total = total_format % (self.int_dialog_highlight, '%s'), total_format % (self.ext_dialog_highlight, '%s')
		self.timeout = 30 if self.disabled_ignored else int(get_setting('scrapers.timeout.1', '10'))
		self.meta = json.loads(get_property('pov_playback_meta'))
		self.background = self.meta.get('background', False)
		self.internal_sources_total, self.internal_resolutions = 0, dict.fromkeys(resolutions.split(), 0)
		self.sources_total, self.resolutions = {'total': 0}, dict.fromkeys(resolutions.split(), 0)

	def results(self, info):
		if not self.background:
			hide_busy_dialog()
			if not self.progress_dialog and not self.load_action:
				progressDialogBG.create('POV', 'POV loading...')
			else: self._make_progress_dialog()
		Sources.sources_total, Sources.resolutions = self.sources_total, self.resolutions
		Sources.hostDict, Sources.sources, Sources.cached_sources = self.hostDict, self.sources, self.cached_sources
		threads = []
		for provider, module, *pack in self.source_dict:
			if info['media_type'] == 'movie':
				if not module.hasMovies: continue
				args, name = (provider, module), provider
			else:
				if not module.hasEpisodes: continue
				args = provider, module, pack[0] if pack else ''
				name = pack_display % (provider, pack[0]) if pack and pack[0] else provider
			obj = Sources(info, self.meta)
			obj.thread = Thread(target=obj.get_source, args=args, name=name)
			threads.append(obj)
		self.wait(threads)
		try:
			self.cached_sources = self.process_duplicates(self.cached_sources)
			self.sources = self.process_duplicates(self.sources)
			torrent_sources = [i for i in self.sources if 'hash' in i]
			result_hashes = list({i['hash'] for i in torrent_sources})
			DebridCheck.set_cached_hashes(result_hashes)
			threads = []
			for item in self.debrid_torrents:
				if not (args := next((i for i in debrid_list if i[0] == item), None)): continue
				obj = DebridCheck(*args)
				obj.thread.start()
				threads.append(obj)
			self.wait(threads, debrid_check=True)
			for item in threads:
				name, hashes = item.name, item.cached_list
				if name in cached_debrids:
					self.final_sources.extend([{**i, 'cache_provider': name, 'debrid': name} for i in self.cached_sources])
				else:
					self.final_sources.extend([{**i, 'cache_provider': name, 'debrid': name} for i in torrent_sources if i['hash'] in hashes])
				if self.display_uncached_torrents:
					self.final_sources.extend([{**i, 'cache_provider': 'Uncached %s' % name, 'debrid': name} for i in torrent_sources if not i['hash'] in hashes])
			hoster_sources = [i for i in self.sources if not 'hash' in i]
			result_hosters = list({i['source'].lower() for i in hoster_sources})
			for item in self.debrid_hosters:
				for k, v in item.items():
					valid_hosters = [i for i in result_hosters if i in v]
					self.final_sources.extend([{**i, 'debrid': k} for i in hoster_sources if i['source'] in valid_hosters])
		except: notification(32574)
		if not self.background:
			if not self.progress_dialog and not self.load_action:
				progressDialogBG.close()
			else: self._kill_progress_dialog()
		clear_property('fs_filterless_search')
		return self.final_sources

	def wait(self, threads, debrid_check=False):
		if not self.background:
			string1, string2 = ls(32579) if debrid_check else ls(32676), ls(32677)
			if self.internal_activated or self.internal_prescraped:
				string3 = int_format % (self.int_dialog_highlight, '%s')
				string4 = ext_format % (self.ext_dialog_highlight, '%s')
			else: string4 = ext_scr_format % (self.ext_dialog_highlight, ls(32118))
			line1 = line2 = line3 = ''
		len_threads = len(threads)
		end_time = time.monotonic() + self.timeout
		if not debrid_check: list(TaskPool.process([i.thread for i in threads]))
		while not all((i.completed for i in threads)):
			if time.monotonic() > end_time or monitor.abortRequested(): break
			sleep(self.sleep_time)
			alive_threads = [x.thread.name for x in threads if not x.completed]
			if not self.background:
				try:
					if self.progress_dialog and self.progress_dialog.iscanceled(): break
					ext_totals = [self.ext_total % v for v in self.resolutions.values()]
					source_total_label = self.ext_total % self.sources_total['total']
					len_alive_threads = len(alive_threads)
					if self.internal_activated or self.internal_prescraped:
						remaining_internal_scrapers = self.process_internal_results()
						int_totals = [self.int_total % v for v in self.internal_resolutions.values()]
						internalSource_total_label = self.int_total % self.internal_sources_total
						alive_threads.extend(remaining_internal_scrapers)
						line1 = string3 % diag_format % (*int_totals, string2, internalSource_total_label)
						line2 = string4 % diag_format % (*ext_totals, string2, source_total_label)
					else:
						line1 = string4
						line2 = diag_format % (*ext_totals, string2, source_total_label)
					if len_alive_threads > 5: line3 = string1 % str(len_threads-len_alive_threads)
					else: line3 = string1 % ', '.join(alive_threads).upper()
					progress = int((len_threads-len_alive_threads)/len_threads*100)
					if self.progress_dialog: self.progress_dialog.update(format_line % (line1, line2, line3), progress)
					else: progressDialogBG.update(progress, line3)
					finish_early = debrid_check is False and self.finish_early and len(self.sources) > len_threads // 0.1
					if finish_early: break
				except: pass

	def process_duplicates(self, _sources):
		def _process():
			uniqueURLs, uniqueHashes = set(), set()
			for provider in _sources:
				try:
					url = provider['url'].lower()
					if url not in uniqueURLs:
						uniqueURLs.add(url)
						if 'hash' in provider:
							if provider['hash'] not in uniqueHashes:
								uniqueHashes.add(provider['hash'])
								yield provider
						else: yield provider
				except: yield provider
		return list(_process())

	def process_internal_results(self):
		def _process_quality_count(sources):
			for i in sources:
				quality = i['quality']
				if quality == '4K': self.internal_resolutions[quality] += 1
				elif quality == '1080p': self.internal_resolutions[quality] += 1
				elif quality == '720p': self.internal_resolutions[quality] += 1
				else: self.internal_resolutions['SD'] += 1
				self.internal_sources_total += 1
		if self.internal_prescraped and not self.processed_prescrape:
			_process_quality_count(self.prescrape_sources)
			self.processed_prescrape = True
		for i in self.internal_scrapers:
			win_property = get_property('%s.internal_results' % i)
			if win_property in ('checked', '', None): continue
			try: internal_sources = json.loads(win_property)
			except: continue
			set_property('%s.internal_results' % i, 'checked')
			self.processed_internal_scrapers_append(i)
			_process_quality_count(internal_sources)
		return [i for i in self.internal_scrapers if not i in self.processed_internal_scrapers]

	def make_host_dict(self):
		pr_list = []
		pr_list_extend = pr_list.extend
		for item in self.debrid_hosters:
			for k, v in item.items(): pr_list_extend(v)
		return list(set(pr_list))

	def _make_progress_dialog(self):
		if self.progress_dialog: return
		self.progress_dialog = create_window(('windows.sources', 'ProgressMedia'), 'progress_media.xml', meta=self.meta)
		Thread(target=self.progress_dialog.run).start()

	def _kill_progress_dialog(self):
		try: self.progress_dialog.close()
		except: pass
		try: del self.progress_dialog
		except: pass
		self.progress_dialog = None

class Sources:
	scrape_provider = 'external'
	hostDict = {}
	sources, cached_sources = [], []
	sources_total, resolutions = {'total': 0}, dict.fromkeys(resolutions.split(), 0)

	def __init__(self, info, meta):
		self.completed = False
		self.media_type, self.tmdb_id, self.year = info['media_type'], str(info['tmdb_id']), info['year']
		self.season, self.episode, self.total_seasons = info['season'], info['episode'], info['total_seasons']
		self.title, self.orig_title, aliases = normalize(info['title']), info['title'], info['aliases']
		self.single_expiry, self.season_expiry, self.show_expiry = info['expiry_times']
		if self.media_type == 'movie':
			self.get_source = self.get_movie_source
			self.season_divider, self.show_divider = 1, 1
			self.data = {'imdb': info['imdb_id'], 'title': self.title, 'aliases': aliases, 'year': self.year}
		else:
			self.get_source = self.get_episode_source
			self.season_divider = int(next((x['episode_count'] for x in meta['season_data'] if int(x['season_number']) == int(meta['season'])), 1))
			self.show_divider = int(meta['total_aired_eps'])
			self.data = {'imdb': info['imdb_id'], 'title': normalize(info['ep_name']), 'aliases': aliases, 'year': self.year,
						'tvdb': info['tvdb_id'], 'tvshowtitle': self.title, 'season': str(self.season), 'episode': str(self.episode)}

	def get_movie_source(self, provider, module):
		_cache = ExternalProvidersCache()
		sources = _cache.get(provider, self.media_type, self.tmdb_id, self.title, self.year, '', '')
		if sources is None:
			sources = module().sources(self.data, self.hostDict)
			sources = self.process_sources(provider, sources)
			_cache.set(provider, self.media_type, self.tmdb_id, self.title, self.year, '', '', sources, self.single_expiry)
		if sources:
			self.process_quality_count(sources)
			if provider in cached_debrids: self.cached_sources.extend(sources)
			else: self.sources.extend(sources)
		self.completed = True

	def get_episode_source(self, provider, module, pack):
		if pack in pack_check:
			s_check, e_check = '' if pack == show_display else self.season, ''
		else: s_check, e_check = self.season, self.episode
		_cache = ExternalProvidersCache()
		sources = _cache.get(provider, self.media_type, self.tmdb_id, self.title, self.year, s_check, e_check)
		if sources is None:
			if pack == show_display:
				expiry_hours = self.show_expiry
				sources = module().sources_packs(self.data, self.hostDict, search_series=True, total_seasons=self.total_seasons)
			elif pack == season_display:
				expiry_hours = self.season_expiry
				sources = module().sources_packs(self.data, self.hostDict)
			else:
				expiry_hours = self.single_expiry
				sources = module().sources(self.data, self.hostDict)
			sources = self.process_sources(provider, sources)
			_cache.set(provider, self.media_type, self.tmdb_id, self.title, self.year, s_check, e_check, sources, expiry_hours)
		if sources:
			if pack == season_display: sources = [i for i in sources if not 'episode_start' in i or i['episode_start'] <= self.episode <= i['episode_end']]
			elif pack == show_display: sources = [i for i in sources if i['last_season'] >= self.season]
			self.process_quality_count(sources)
			if provider in cached_debrids: self.cached_sources.extend(sources)
			else: self.sources.extend(sources)
		self.completed = True

	def process_sources(self, provider, sources):
		try:
			for i in sources:
				try:
					i_get = i.get
					if 'hash' in i:
						_hash = i_get('hash').lower()
						i['hash'] = str(_hash)
					size, size_label, divider = 0, None, None
					if 'name' in i: URLName = clean_file_name(i_get('name')).replace('html', ' ').replace('+', ' ').replace('-', ' ')
					else: URLName = get_filename_match(self.orig_title, i_get('url'), i_get('name', None))
					if 'name_info' in i: quality, extraInfo = get_file_info(name_info=i_get('name_info'))
					else: quality, extraInfo = get_file_info(url=i_get('url'))
					try:
						size = i_get('size')
						if 'package' in i and provider not in ('torrentio', 'mediafusion', 'tidebrid', 'mfdebrid'):
							if i_get('package') == 'season': divider = self.season_divider
							else: divider = self.show_divider
							size = float(size) / divider
							size_label = '%.2f GB' % size
						else: size_label = '%.2f GB' % size
					except: pass
					i.update({'provider': provider, 'external': True, 'scrape_provider': self.scrape_provider, 'extraInfo': extraInfo,
								'URLName': URLName, 'quality': quality, 'size_label': size_label, 'size': round(size, 2)})
				except: pass
		except: pass
		return sources

	def process_quality_count(self, sources):
		for i in sources:
			quality = i['quality']
			if quality == '4K': self.resolutions[quality] += 1
			elif quality == '1080p': self.resolutions[quality] += 1
			elif quality == '720p': self.resolutions[quality] += 1
			else: self.resolutions['SD'] += 1
			self.sources_total['total'] += 1

