# created by kodifitzwell for Fenomscrapers
"""
	Fenomscrapers Project
"""

#from json import loads as jsloads
import hashlib, requests, queue
#from fenom import client
from fenom import source_utils
from fenom.control import setting as getSetting


class source:
	timeout = 9
	priority = 3
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	_queue = queue.SimpleQueue()
	def __init__(self):
		self.user_agent = 'POV for Kodi'
		self.token = getSetting('tb.token')
		self.user_engines_only = getSetting('tb.user_engines_only') == 'true'
		self.language = ['en']
		self.base_link = "https://search-api.torbox.app/usenet"
		self.min_seeders = -2

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		append = sources.append
		try:
			title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
			title = title.replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			episode_title = data['title'] if 'tvshowtitle' in data else None
			year = data['year']
			imdb = data['imdb']
			url = '%s/imdb:%s' % (self.base_link, imdb)
			params = {'check_cache': 'true', 'check_owned': 'true', 'search_user_engines': 'true'}
			if 'tvshowtitle' in data:
				season = data['season']
				episode = data['episode']
				hdlr = 'S%02dE%02d' % (int(season), int(episode))
				params.update({'season': int(season), 'episode': int(episode)})
			else:
				hdlr = year
			# log_utils.log('url = %s' % url)
			try:
				headers = {'User-Agent': self.user_agent, 'Authorization': 'Bearer %s' % self.token}
				results = requests.get(url, params=params, headers=headers, timeout=self.timeout)
				files = results.json()['data']['nzbs']
			except: files = []
			self._queue.put_nowait(files) # if seasons
			self._queue.put_nowait(files) # if shows
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('TORBOXNEWS')
			return sources

		for file in files:
			try:
				if self.user_engines_only and not file['user_search']: continue
				hash = file['hash'] or hashlib.md5(file['nzb'].encode('utf-8')).hexdigest()
				file_title = file['raw_title']

				name = source_utils.clean_name(file_title)

				if not source_utils.check_title(title, aliases, name.replace('.(Archie.Bunker', ''), hdlr, year): continue
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				url = file['nzb']

				try:
					seeders = file['last_known_seeders']
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = f"{float(file['size']) / 1073741824:.2f} GB"
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				append({'provider': 'torboxnews', 'source': 'usenet', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'tracker': file['tracker']})
			except:
				source_utils.scraper_error('TORBOXNEWS')
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		sources = []
		if not data: return sources
		sources_append = sources.append
		try:
			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ')
			aliases = data['aliases']
			imdb = data['imdb']
			year = data['year']
			season = data['season']
			url = '%s/imdb:%s' % (self.base_link, imdb)
			params = {'check_cache': 'true', 'check_owned': 'true', 'search_user_engines': 'true'}
			params.update({'season': int(season), 'episode': int(data['episode'])})
			headers = {'User-Agent': self.user_agent, 'Authorization': 'Bearer %s' % self.token}
#			results = requests.get(url, params=params, headers=headers, timeout=self.timeout)
			files = self._queue.get(timeout=self.timeout + 1)
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error('TORBOXNEWS')
			return sources

		for file in files:
			try:
				if self.user_engines_only and not file['user_search']: continue
				hash = file['hash'] or hashlib.md5(file['nzb'].encode('utf-8')).hexdigest()
				file_title = file['raw_title']

				name = source_utils.clean_name(file_title)

				episode_start, episode_end = 0, 0
				if not search_series:
					if not bypass_filter:
						valid, episode_start, episode_end = source_utils.filter_season_pack(title, aliases, year, season, name.replace('.(Archie.Bunker', ''))
						if not valid: continue
					package = 'season'

				elif search_series:
					if not bypass_filter:
						valid, last_season = source_utils.filter_show_pack(title, aliases, imdb, year, season, name.replace('.(Archie.Bunker', ''), total_seasons)
						if not valid: continue
					else: last_season = total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, title, year, season=season, pack=package)
				if source_utils.remove_lang(name_info, check_foreign_audio): continue
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue

				url = file['nzb']
				try:
					seeders = file['last_known_seeders']
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					size = f"{float(file['size']) / 1073741824:.2f} GB"
					dsize, isize = source_utils._size(size)
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': 'torboxnews', 'source': 'usenet', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package, 'tracker': file['tracker']}
				if search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				sources_append(item)
			except:
				source_utils.scraper_error('TORBOXNEWS')
		return sources

