import re
import xbmc, xbmcgui, xbmcaddon
from resources.lib import Utils
from resources.lib.WindowManager import wm
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short
from resources.lib.trakt import fanart_api_key, tmdb_api_key

import html
from inspect import currentframe, getframeinfo
#xbmc.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))+'===>OPENINFO', level=xbmc.LOGINFO)

API_key = tmdb_api_key()

def get_certification_list(media_type):
	response = get_tmdb_data('certification/%s/list?' % media_type, 999999)
	if 'certifications' in response:
		return response['certifications']
	else:
		return []

def merge_with_cert_desc(input_list, media_type):
	cert_list = get_certification_list(media_type)
	for item in input_list:
		if item['iso_3166_1'].upper() not in cert_list:
			continue
		hit = Utils.dictfind(lst=cert_list[item['iso_3166_1'].upper()], key='certification', value=item['certification'])
		if hit:
			item['meaning'] = hit['meaning']
	return input_list

def handle_tmdb_multi_search(results=[]):
	listitems = []
	for item in results:
		if item['media_type'] == 'movie':
			listitem = handle_tmdb_movies([item])[0]
		elif item['media_type'] == 'tv':
			listitem = handle_tmdb_tvshows([item])[0]
		else:
			try: listitem = handle_tmdb_people([item])[0]
			except: continue
		listitems.append(listitem)
	return listitems

def handle_tmdb_movies(results=[], sortkey='year'):
	response = get_tmdb_data('genre/movie/list?language=%s&' % xbmcaddon.Addon().getSetting('LanguageID'), 30)
	id_list = [item['id'] for item in response.get('genres',[])]
	label_list = [item['name'] for item in response.get('genres',[])]
	movies = []
	for movie in results:
		if 'genre_ids' in movie:
			genre_list = [label_list[id_list.index(genre_id)] for genre_id in movie['genre_ids'] if genre_id in id_list]
			genres = ' / '.join(genre_list)
		else:
			genres = ''
		tmdb_id = str(Utils.fetch(movie, 'id'))
		artwork = get_image_urls(poster=movie.get('poster_path'), fanart=movie.get('backdrop_path'))
		year = Utils.get_year(Utils.fetch(movie, 'release_date'))
		path = 'plugin://'+str(addon_ID())+'?info='+str(addon_ID_short())+'&&id=%s&year=%s' % (str(tmdb_id), str(year))
		original_title = Utils.fetch(movie, 'original_title')
		original_title2 = ''
		try:
			for i in movie['alternative_titles']['titles']:
				if i['type'] == 'original title' and i['iso_3166_1'] in {'US','UK'}:
					original_title2 = i['title']
			if original_title2 != original_title and original_title2 != '':
				original_title = original_title2
		except:
			pass
		listitem = {
			'title': Utils.fetch(movie, 'title'),
			'Label': Utils.fetch(movie, 'title'),
			'OriginalTitle': original_title,
			'id': tmdb_id,
			'imdb_id': Utils.fetch(movie, 'imdb_id'),
			'path': path,
			'media_type': 'movie',
			'mediatype': 'movie',
			'country': Utils.fetch(movie, 'original_language'),
			'plot': Utils.fetch(movie, 'overview'),
			'Trailer': 'plugin://%s?info=playtrailer&&id=%s' % (addon_ID(), tmdb_id),
			'Popularity': Utils.fetch(movie, 'popularity'),
			'Rating': Utils.fetch(movie, 'vote_average'),
			'credit_id': Utils.fetch(movie, 'credit_id'),
			'character': Utils.fetch(movie, 'character'),
			'job': Utils.fetch(movie, 'job'),
			'department': Utils.fetch(movie, 'department'),
			'Votes': Utils.fetch(movie, 'vote_count'),
			'User_Rating': Utils.fetch(movie, 'rating'),
			'year': year,
			'genre': genres,
			'Premiered': Utils.fetch(movie, 'release_date')
			}
		listitem.update(artwork)
		date = Utils.fetch(movie, 'release_date')
		movies.append(listitem)
	#Utils.hide_busy()
	return sorted(movies, key=lambda item: item[sortkey], reverse=True) if sortkey else movies

def handle_tmdb_tvshows(results, sortkey='year'):

	tvshows = []
	response = get_tmdb_data('genre/tv/list?language=%s&' % xbmcaddon.Addon().getSetting('LanguageID'), 30)
	id_list = [item['id'] for item in (response or {}).get('genres',[])]
	label_list = [item['name'] for item in (response or {}).get('genres',[])]
	for tv in results:
		tmdb_id = Utils.fetch(tv, 'id')
		artwork = get_image_urls(poster=tv.get('poster_path'), fanart=tv.get('backdrop_path'))
		if 'genre_ids' in tv:
			genre_list = [label_list[id_list.index(genre_id)] for genre_id in tv['genre_ids'] if genre_id in id_list]
			genres = ' / '.join(genre_list)
		else:
			genres = ''
		duration = ''
		if 'episode_run_time' in tv:
			if len(tv['episode_run_time']) > 1:
				duration = '%i - %i' % (min(tv['episode_run_time']), max(tv['episode_run_time']))
			elif len(tv['episode_run_time']) == 1:
				duration = '%i' % tv['episode_run_time'][0]

		newtv = {
			'title': Utils.fetch(tv, 'name'),
			'TVShowTitle': Utils.fetch(tv, 'name'),
			'OriginalTitle': Utils.fetch(tv, 'original_name'),
			'duration': duration,
			'id': tmdb_id,
			'imdb_id': Utils.fetch(tv, 'imdb_id'),
			'genre': genres,
			'country': Utils.fetch(tv, 'original_language'),
			'Popularity': Utils.fetch(tv, 'popularity'),
			'credit_id': Utils.fetch(tv, 'credit_id'),
			'Plot': Utils.fetch(tv, 'overview'),
			'Trailer': 'plugin://'+str(addon_ID())+'?info=tvtrailer&&id=%s' % str(tmdb_id),
			'year': Utils.get_year(Utils.fetch(tv, 'first_air_date')),
			'media_type': 'tv',
			'mediatype': 'tvshow',
			'character': Utils.fetch(tv, 'character'),
			'path': 'plugin://'+str(addon_ID())+'?info=diggzportaltvinfo&&id=%s' % str(tmdb_id),
			'Rating': Utils.fetch(tv, 'vote_average'),
			'User_Rating': str(Utils.fetch(tv, 'rating')),
			'Votes': Utils.fetch(tv, 'vote_count'),
			'TotalEpisodes': Utils.fetch(tv, 'number_of_episodes'),
			'TotalSeasons': Utils.fetch(tv, 'number_of_seasons'),
			'Release_Date': Utils.fetch(tv, 'first_air_date'),
			'status': Utils.fetch(tv, 'status'),
			'Premiered': Utils.fetch(tv, 'first_air_date')
			}
		newtv.update(artwork)
		date = Utils.fetch(tv, 'first_air_date')
		tvshows.append(newtv)
	return sorted(tvshows, key=lambda item: item[sortkey], reverse=True) if sortkey else tvshows

def handle_tmdb_seasons(results):
	listitems = []
	for season in results:
		season_number = str(Utils.fetch(season, 'season_number'))
		artwork = get_image_urls(poster=season.get('poster_path'))
		title = 'Specials' if season_number == '0' else 'Season %s' % season_number
		listitem = {
			'media_type': 'season',
			'mediatype': 'season',
			'title': title,
			'season': season_number,
			'air_date': Utils.fetch(season, 'air_date'),
			'year': Utils.get_year(Utils.fetch(season, 'air_date')),
			'id': Utils.fetch(season, 'id')
			}
		listitem.update(artwork)
		listitems.append(listitem)
	return listitems

def handle_tmdb_episodes(results):
	listitems = []
	for item in results:
		title = Utils.clean_text(Utils.fetch(item, 'name'))
		if not title:
			title = '%s %s' % ('Episode', Utils.fetch(item, 'episode_number'))
		try:
			artwork = get_image_urls(still=item.get('still_path'))
		except:
			artwork = []
		try: rating = round(float(Utils.fetch(item, 'vote_average')), 1)
		except: rating = 0
		listitem = {
			'media_type': 'episode',
			'mediatype': 'episode',
			'title': title,
			'release_date': Utils.fetch(item, 'air_date'),
			'episode': Utils.fetch(item, 'episode_number'),
			'production_code': Utils.fetch(item, 'production_code'),
			'season': Utils.fetch(item, 'season_number'),
			'Rating': rating,
			'Votes': Utils.fetch(item, 'vote_count'),
			'Plot': Utils.fetch(item, 'overview'),
			'id': Utils.fetch(item, 'id'),
			'Description': Utils.clean_text(Utils.fetch(item, 'overview'))
			}
		listitem.update(artwork)
		date = Utils.fetch(item, 'air_date')
		listitems.append(listitem)
	return listitems

def handle_tmdb_misc(results):
	listitems = []
	for item in results:
		artwork = get_image_urls(poster=item.get('poster_path'))
		# TMDb companies and networks supply logo_path, not poster_path.
		logo_path = item.get('logo_path')
		if isinstance(logo_path, str) and logo_path.startswith('/'):
			artwork['clearlogo'] = 'https://image.tmdb.org/t/p/w500' + logo_path
		listitem = {
			'title': Utils.clean_text(Utils.fetch(item, 'name')),
			'certification': Utils.fetch(item, 'certification') + Utils.fetch(item, 'rating'),
			'item_count': Utils.fetch(item, 'item_count'),
			'release_date': Utils.fetch(item, 'release_date'),
			'path': 'plugin://'+str(addon_ID())+'?info=listmovies&---id=%s' % Utils.fetch(item, 'id'),
			'year': Utils.get_year(Utils.fetch(item, 'release_date')),
			'iso_3166_1': Utils.fetch(item, 'iso_3166_1').lower(),
			'author': Utils.fetch(item, 'author'),
			'content': Utils.clean_text(Utils.fetch(item, 'content')),
			'id': Utils.fetch(item, 'id'),
			'url': Utils.fetch(item, 'url'),
			'Description': Utils.clean_text(Utils.fetch(item, 'description'))
			}
		listitem.update(artwork)
		listitems.append(listitem)
	return listitems

def handle_tmdb_videos(results):
	# Only TMDb-verified official YouTube trailers; never substitute other clips.
	def resolution(item):
		try:
			return int(item.get('size') or 0)
		except (ValueError, TypeError):
			return 0
	eligible = [item for item in (results or []) if isinstance(item, dict)
		and item.get('official') is True and item.get('type') == 'Trailer'
		and item.get('site') == 'YouTube'
		and re.fullmatch(r'[A-Za-z0-9_-]{11}', str(item.get('key', '')))]
	# Primary trailer first; promotional variants follow in semantic order.
	def trailer_priority(item):
		name = ' '.join(re.findall(r'\w+', str(item.get('name') or '').casefold()))
		# Sneak peeks are last even when TMDb labels them as official trailers.
		if re.search(r'\bsneak\s*peek\b', name):
			return (0, 0)
		if re.search(r'\binternational\b', name):
			return (2, 0)
		if re.search(r'\bfinal\b', name):
			return (3, 0)
		match = re.search(r'\bofficial trailer(?: (?:no )?(\d+))?$', name)
		if match:
			return (5, -int(match.group(1))) if match.group(1) else (6, 0)
		match = re.fullmatch(r'(?:.*? )?trailer(?: (?:no )?(\d+))?', name)
		if match and not re.search(r'\b(?:teaser|special|extended|new|promo|launch|red band|green band)\b', name):
			return (4, -int(match.group(1) or 0))
		return (1, 0)
	eligible.sort(key=lambda item: (trailer_priority(item), resolution(item) >= 1080,
		str(item.get('published_at') or ''), resolution(item)), reverse=True)
	listitems = []
	seen = set()
	for item in eligible:
		key = item['key']
		if key in seen:
			continue
		seen.add(key)
		listitems.append(dict(item, thumb='https://i.ytimg.com/vi/%s/hqdefault.jpg' % key,
			title=item.get('name') or 'Official Trailer', youtube_id=key))
	return listitems


def play_trailer(media_type, tmdb_id, windowed=False, dialog=None):
	from resources.lib.YouTube import play_video
	if not tmdb_id:
		return
	language = xbmcaddon.Addon().getSetting('LanguageID')
	response = get_tmdb_data('%s/%s/videos?language=%s&' % (media_type, tmdb_id, language), 30)
	videos = handle_tmdb_videos((response or {}).get('results', []))
	if not videos:
		Utils.notify('No official trailer available', sound=False)
		return
	play_video(videos[0]['key'], windowed=windowed, dialog=dialog)

def handle_tmdb_people(results):
	people = []
	for person in results:
		artwork = get_image_urls(profile=person.get('profile_path'))
		also_known_as = ' / '.join(person.get('also_known_as') or [])
		newperson = {
			'adult': str(Utils.fetch(person, 'adult')),
			'name': Utils.fetch(person, 'name'),
			'title': Utils.fetch(person, 'name'),
			'also_known_as': also_known_as,
			'alsoknownas': also_known_as,
			'biography': Utils.clean_text(Utils.fetch(person, 'biography')),
			'birthday': Utils.fetch(person, 'birthday'),
			'age': Utils.calculate_age(Utils.fetch(person, 'birthday'), Utils.fetch(person, 'deathday')),
			'character': Utils.fetch(person, 'character'),
			'department': Utils.fetch(person, 'department'),
			'job': Utils.fetch(person, 'job'),
			'media_type': 'person',
			'id': str(Utils.fetch(person, 'id')),
			'cast_id': str(Utils.fetch(person, 'cast_id')),
			'credit_id': str(Utils.fetch(person, 'credit_id')),
			'path': 'plugin://'+str(addon_ID())+'?info=diggzportalactorinfo&&id=%s' % str(Utils.fetch(person, 'id')),
			'deathday': Utils.fetch(person, 'deathday'),
			'place_of_birth': Utils.fetch(person, 'place_of_birth'),
			'placeofbirth': Utils.fetch(person, 'place_of_birth'),
			'homepage': Utils.fetch(person, 'homepage')
			}
		newperson.update(artwork)
		people.append(newperson)
	return people

def handle_tmdb_images(results):
	images = []
	for item in results:
		artwork = get_image_urls(poster=item.get('file_path'))
		image = {
			'aspectratio': item['aspect_ratio'],
			'vote_average': Utils.fetch(item, 'vote_average'),
			'iso_639_1': Utils.fetch(item, 'iso_639_1')
			}
		image.update(artwork)
		images.append(image)
	return images

def handle_tmdb_tagged_images(results):
	images = []
	for item in results:
		artwork = get_image_urls(poster=item.get('file_path'))
		image = {
			'aspectratio': item['aspect_ratio'],
			'vote_average': Utils.fetch(item, 'vote_average'),
			'iso_639_1': Utils.fetch(item, 'iso_639_1'),
			'title': Utils.fetch(item['media'], 'title'),
			'mediaposter': 'https://image.tmdb.org/t/p/w500%s' % Utils.fetch(item['media'], 'poster_path')
			}
		image.update(artwork)
		images.append(image)
	return images

def search_company(company_name):
	regex = re.compile('\(.+?\)')
	company_name = regex.sub('', company_name)
	response = get_tmdb_data('search/company?query=%s&' % Utils.url_quote(company_name), 10)
	if response and 'results' in response:
		return response['results']
	else:
		return ''

def get_movie_info(movie_label, year=None, use_dialog=True, item_id=None, notify = True):
	if item_id:
		return single_movie_info(movie_id=item_id, cache_time=7, notify=notify)
	#movies = movie_label.split(' / ')
	if year:
		year_string = '&primary_release_year=' + str(year)
	else:
		year_string = ''
	response = get_tmdb_data('search/movie?query=%s%s&include_adult=%s&' % (Utils.url_quote(movie_label), year_string, xbmcaddon.Addon().getSetting('include_adults')), 30)
	if not response or 'results' not in response:
		return False
	for i in range(len(response['results'])-1, 0, -1):
		if response['results'][i]['title'] != movie_label:
			del response['results'][i]
	if len(response['results']) > 1 and use_dialog:
		listitem, index = wm.open_selectdialog(listitems=handle_tmdb_movies(response['results']))
		if int(index) == -1:
			return False
		elif index >= 0:
			return listitem
	elif response['results']:
		return response['results'][0]
	return False

def get_tvshow_info(tvshow_label, year=None, use_dialog=True, item_id=None):
	if item_id:
		return single_tvshow_info(tvshow_id=item_id, cache_time=7)
	#tvshow = tvshow_label.split(' / ')
	if year:
		year_string = '&first_air_date_year=' + str(year)
	else:
		year_string = ''
	response = get_tmdb_data('search/tv?query=%s%s&include_adult=%s&' % (Utils.url_quote(tvshow_label), year_string, xbmcaddon.Addon().getSetting('include_adults')), 30)
	if not response or 'results' not in response:
		return False
	for i in range(len(response['results'])-1, 0, -1):
		if response['results'][i]['original_name'] != tvshow_label:
			del response['results'][i]
	if len(response['results']) > 1 and use_dialog:
		listitem, index = wm.open_selectdialog(listitems=handle_tmdb_tvshows(response['results']))#
		if int(index) == -1:
			return False
		elif index >= 0:
			return listitem
	elif response['results']:
		return response['results'][0]
	return False

def get_person_info(person_label):
	persons = person_label.split(' / ')
	response = get_tmdb_data('search/person?query=%s&include_adult=%s&' % (Utils.url_quote(persons[0]), xbmcaddon.Addon().getSetting('include_adults')), 30)
	if not response or 'results' not in response:
		return False
	if len(response['results']) > 1:
		listitem, index = wm.open_selectdialog(listitems=handle_tmdb_people(response['results']))
		if index >= 0:
			return response['results'][index]
	elif response['results']:
		return response['results'][0]
	return False

def get_keyword_id(keyword):
	response = get_tmdb_data('search/keyword?query=%s&include_adult=%s&' % (Utils.url_quote(keyword), xbmcaddon.Addon().getSetting('include_adults')), 30)
	if response and 'results' in response and response['results']:
		if len(response['results']) > 1:
			names = [item['name'] for item in response['results']]
			selection = xbmcgui.Dialog().select('Keyword', names)
			if selection > -1:
				return response['results'][selection]
		elif response['results']:
			return response['results'][0]
	else:
		return False

def get_set_id(set_name):
	set_name = set_name.replace('[', '').replace(']', '').replace('Kollektion', 'Collection')
	response = get_tmdb_data('search/collection?query=%s&language=%s&' % (Utils.url_quote(set_name.encode('utf-8')), xbmcaddon.Addon().getSetting('LanguageID')), 14)
	if 'results' in response and response['results']:
		return response['results'][0]['id']
	else:
		return ''

def get_tmdb_data(url='', cache_days=14, folder='TheMovieDB'):
	url = 'https://api.themoviedb.org/3/%sapi_key=%s' % (url, API_key)
	#xbmc.log(str(url)+'===>PHIL', level=xbmc.LOGINFO)
	return Utils.get_JSON_response(url, cache_days, folder)

def get_fanart_clearlogo(tmdb_id=None, media_type=None):
	fanart_clearlogos = xbmcaddon.Addon().getSetting('fanart_clearlogos')
	if fanart_clearlogos == 'false':
		clearlogo = ''
		return clearlogo
	if media_type !='tv' and media_type != 'movie':
		clearlogo = ''
		return clearlogo
	response = get_fanart_data(tmdb_id=tmdb_id,media_type=media_type)
	if media_type =='tv':
		try:
			for i in response['hdtvlogo']:
				if i['lang'] in ('en','00',''):
					clearlogo = i['url']
					break
		except: 
			try:
				for i in response['clearlogo']:
					if i['lang'] in ('en','00',''):
						clearlogo = i['url']
						break
			except: 
				pass
	if media_type =='movie':
		try:
			for i in response['hdmovielogo']:
				if i['lang'] in ('en','00',''):
					clearlogo = i['url']
					break
		except: 
			try:
				for i in response['clearlogo']:
					if i['lang'] in ('en','00',''):
						clearlogo = i['url']
						break
			except: 
				pass
	return clearlogo








def get_fanart_data(url='', tmdb_id=None, media_type=None, cache_days=14, folder='FanartTV'):
	fanart_api = fanart_api_key()
	import requests,json
	if media_type =='tv':
		tvdb_id = get_tvshow_ids(tmdb_id)
		tvdb_id = tvdb_id['tvdb_id']
		url = 'http://webservice.fanart.tv/v3/tv/'+str(tvdb_id)+'?api_key=' + fanart_api
		#response = requests.get(url).json()
	elif media_type =='tv_tvdb':
		url = 'http://webservice.fanart.tv/v3/tv/'+str(tmdb_id)+'?api_key=' + fanart_api
		#response = requests.get(url).json()
	else:
		url = 'http://webservice.fanart.tv/v3/movies/'+str(tmdb_id)+'?api_key=' + fanart_api
		#response = requests.get(url).json()
	return Utils.get_JSON_response(url, cache_days, folder)

def get_company_data(company_id):
	response = get_tmdb_data('company/%s/movies?' % company_id, 30)
	if response and 'results' in response:
		return handle_tmdb_movies(response['results'])
	else:
		return []

def get_credit_info(credit_id):
	return get_tmdb_data('credit/%s?language=%s&' % (credit_id, xbmcaddon.Addon().getSetting('LanguageID')), 30)

def get_image_urls(poster=None, still=None, fanart=None, profile=None):
	images = {}
	if poster:
		images['poster'] = 'https://image.tmdb.org/t/p/w500' + poster
		images['poster_original'] = 'https://image.tmdb.org/t/p/original' + poster
		images['original'] = 'https://image.tmdb.org/t/p/original' + poster
		images['poster_small'] = 'https://image.tmdb.org/t/p/w342' + poster
		images['thumb'] = 'https://image.tmdb.org/t/p/w342' + poster
	if still:
		images['thumb'] = 'https://image.tmdb.org/t/p/w300' + still
		images['still'] = 'https://image.tmdb.org/t/p/w300' + still
		images['still_original'] = 'https://image.tmdb.org/t/p/original' + still
		images['still_small'] = 'https://image.tmdb.org/t/p/w185' + still
	if fanart:
		images['fanart'] = 'https://image.tmdb.org/t/p/w1280' + fanart
		images['fanart_original'] = 'https://image.tmdb.org/t/p/original' + fanart
		images['original'] = 'https://image.tmdb.org/t/p/original' + fanart
		images['fanart_small'] = 'https://image.tmdb.org/t/p/w780' + fanart
	if profile:
		images['poster'] = 'https://image.tmdb.org/t/p/w500' + profile
		images['poster_original'] = 'https://image.tmdb.org/t/p/original' + profile
		images['poster_small'] = 'https://image.tmdb.org/t/p/w342' + profile
		images['thumb'] = 'https://image.tmdb.org/t/p/w342' + profile
	return images

def get_movie_tmdb_id(imdb_id=None, name=None):
	if imdb_id:
		response = get_tmdb_data('find/%s?external_source=imdb_id&language=%s&' % (imdb_id, xbmcaddon.Addon().getSetting('LanguageID')), 30)
		if 'movie_results' in response:
			if response['movie_results'] != None and len(response['movie_results']) > 0:
				try:
					return response['movie_results'][0]['id']
				except: 
					if name:
						movie = get_movie_info(movie_label=name, year=year)
						if movie and movie.get('id'):
							return movie.get('id')
					else:
						Utils.notify('Could not find TMDb-id 2')
						return None
			elif name:
				movie = get_movie_info(movie_label=name, year=year)
				if movie and movie.get('id'):
					return movie.get('id')
			else: 
				Utils.notify('Could not find TMDb-id 3')
				return None
	elif name:
		return search_media(name)
	else:
		Utils.notify('Could not find TMDb-id 4')
		return None


def get_show_tmdb_id(tvdb_id=None, db=None, imdb_id=None, source=None):
	if tvdb_id:
		id = tvdb_id
		db = 'tvdb_id'
	elif imdb_id:
		id = 'tt%s' % imdb_id
		id = id.replace('tttt','tt')
		db = 'imdb_id'
	response = get_tmdb_data('find/%s?external_source=%s&language=%s&' % (id, db, xbmcaddon.Addon().getSetting('LanguageID')), 30)
	if response:
		return response['tv_results'][0]['id']
	else:
		Utils.notify('TV Show info not found', time=5000, sound=False)
		return None


def single_movie_info(movie_id=None, cache_time=14, notify = True):
	if not movie_id:
		return None
	session_str = ''
	response = get_tmdb_data('movie/%s?append_to_response=external_ids,recommendations,rating,alternative_titles&language=%s&%s' % (movie_id, xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	#response = get_tmdb_data('movie/%s?append_to_response=alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,rating&include_image_language=en,null,%s&language=%s&%s' % (movie_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	if not response and notify:
		Utils.notify('Could not get movie information', sound=False)
		return {}
	try: genres = [i['id'] for i in response['genres']]
	except KeyError: genres = []
	results = {
			'media_type': 'movie',
			'mediatype': 'movie',
			'adult': Utils.fetch(response,'adult'),
			'backdrop_path': Utils.fetch(response,'backdrop_path'),
			'genre_ids': genres,
			'id': Utils.fetch(response,'id'),
			'imdb_id': Utils.fetch(Utils.fetch(response, 'external_ids'), 'imdb_id'),
			'original_language': Utils.fetch(response,'original_language'),
			'original_title': Utils.fetch(response,'original_title'),
			'alternative_titles': response.get('alternative_titles',[]),
			'overview': Utils.fetch(response,'overview'),
			'similar': response.get('recommendations',{'page': 1, 'results': []}),
			'Rating': Utils.fetch(response, 'vote_average'),
			'Votes': Utils.fetch(response, 'vote_count'),
			'popularity': Utils.fetch(response,'popularity'),
			'poster_path': Utils.fetch(response,'poster_path'),
			'release_date': Utils.fetch(response,'release_date'),
			'title': Utils.fetch(response,'title'),
			'video': Utils.fetch(response,'video'),
			'vote_average': Utils.fetch(response,'vote_average'),
			'vote_count': Utils.fetch(response,'vote_count')
			}
	return results

def single_tvshow_info(tvshow_id=None, cache_time=7):
	if not tvshow_id:
		return None
	session_str = ''
	response = get_tmdb_data('tv/%s?append_to_response=external_ids,recommendations,rating,alternative_titles&language=%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	#response = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	if not response:
		return False
	try: genres = [i['id'] for i in response['genres']]
	except KeyError: genres = []
	alternative_titles =  [i['title'] for i in response['alternative_titles']['results']]
	if response['original_name'] == response['name'] and len(alternative_titles) > 0:
		response['original_name'] = alternative_titles[0]
	results = {
		'media_type': 'tv',
		'mediatype': 'tv',
		'backdrop_path': Utils.fetch(response,'backdrop_path'),
		'first_air_date': Utils.fetch(response,'first_air_date'),
		'genre_ids': genres,
		'id': Utils.fetch(response,'id'),
		'imdb_id': Utils.fetch(Utils.fetch(response, 'external_ids'), 'imdb_id'),
		'name': Utils.fetch(response,'name'),
		'title': Utils.fetch(response,'name'),
		'origin_country': Utils.fetch(response,'origin_country'),
		'original_language': Utils.fetch(response,'original_language'),
		'original_name': Utils.fetch(response,'original_name'),
		'alternative_titles': alternative_titles,
		'overview': Utils.fetch(response,'overview'),
		'similar': response.get('recommendations',{'page': 1, 'results': []}),
		'Rating': Utils.fetch(response, 'vote_average'),
		'Votes': Utils.fetch(response, 'vote_count'),
		'popularity': Utils.fetch(response,'popularity'),
		'poster_path': Utils.fetch(response,'poster_path'),
		'status': Utils.fetch(response,'status'),
		'vote_average': Utils.fetch(response,'vote_average'),
		'vote_count': Utils.fetch(response,'vote_count')
		}
	return results

def extended_movie_info(movie_id=None, cache_time=14, notify=True):
	if not movie_id:
		return None
	session_str = ''
	#response = get_tmdb_data('movie/%s?append_to_response=alternative_titles,credits,images,keywords,releases,videos,translations,recommendations,reviews,rating&include_image_language=en,null,%s&language=%s&%s' % (movie_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	response = get_tmdb_data('movie/%s?append_to_response=alternative_titles,credits,images,keywords,releases,videos,recommendations,reviews,rating&include_image_language=en,null,%s&language=%s&%s' % (movie_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	if not response and notify:
		Utils.notify('Could not get movie information', sound=False)
		return {}
	mpaa = ''
	set_name = ''
	set_id = ''
	genres = [i['name'] for i in response['genres']]
	Studio = [i['name'] for i in response['production_companies']]
	authors = [i['name'] for i in response['credits']['crew'] if i['department'] == 'Writing']
	directors = [i['name'] for i in response['credits']['crew'] if i['department'] == 'Directing']
	us_cert = Utils.dictfind(response['releases']['countries'], 'iso_3166_1', 'US')
	if us_cert:
		mpaa = us_cert['certification']
	elif response['releases']['countries']:
		mpaa = response['releases']['countries'][0]['certification']
	movie_set = Utils.fetch(response, 'belongs_to_collection')
	if movie_set:
		set_name = Utils.fetch(movie_set, 'name')
		set_id = Utils.fetch(movie_set, 'id')
	artwork = get_image_urls(poster=response.get('poster_path'), fanart=response.get('backdrop_path'))
	movie = {
		'media_type': 'movie',
		'mediatype': 'movie',
		'title': Utils.fetch(response, 'title'),
		'Label': Utils.fetch(response, 'title'),
		'Tagline': Utils.fetch(response, 'tagline'),
		'duration': Utils.fetch(response, 'runtime'),
		'duration(h)': Utils.format_time(Utils.fetch(response, 'runtime'), 'h'),
		'duration(m)': Utils.format_time(Utils.fetch(response, 'runtime'), 'm'),
		'duration(hm)': Utils.format_time(Utils.fetch(response, 'runtime')),
		'mpaa': mpaa,
		'Director': ' / '.join(directors),
		'writer': ' / '.join(authors),
		'Budget': Utils.millify(Utils.fetch(response, 'budget')),
		'Revenue': Utils.millify(Utils.fetch(response, 'revenue')),
		'Homepage': Utils.fetch(response, 'homepage'),
		'Set': set_name, 'SetId': set_id,
		'id': Utils.fetch(response, 'id'),
		'tmdb_id': Utils.fetch(response, 'id'),
		'imdb_id': Utils.fetch(response, 'imdb_id'),
		'Plot': Utils.clean_text(Utils.fetch(response, 'overview')),
		'OriginalTitle': Utils.fetch(response, 'original_title'),
		'Country': Utils.fetch(response, 'original_language'),
		'genre': ' / '.join(genres),
		'Rating': Utils.fetch(response, 'vote_average'),
		'Votes': Utils.fetch(response, 'vote_count'),
		'Adult': str(Utils.fetch(response, 'adult')),
		'Popularity': Utils.fetch(response, 'popularity'),
		'Status': translate_status(Utils.fetch(response, 'status')),
		'release_date': Utils.fetch(response, 'release_date'),
		'Premiered': Utils.fetch(response, 'release_date'),
		'Studio': ' / '.join(Studio),
		'year': Utils.get_year(Utils.fetch(response, 'release_date')),
		'path': 'plugin://'+str(addon_ID())+'?info='+str(addon_ID_short())+'&&id=%s' % str(movie_id),
		'trailer': 'plugin://'+str(addon_ID())+'?info=playtrailer&&id=%s' % str(movie_id)
		}
	movie.update(artwork)
	videos = handle_tmdb_videos(response['videos']['results']) if 'videos' in response else []
	movie['Rating'] = Utils.fetch(response, 'vote_average')
	pop_list = []
	try:
		for idx, i in enumerate(response['recommendations']['results']):
			if int(i.get('vote_count',0)) < 250:
				pop_list.append(idx)
		for i in reversed(pop_list):
			response['recommendations']['results'].pop(i)
	except:
		response['recommendations'] = {'page': 1, 'results': []}

	listitems = {
		'actors': handle_tmdb_people(response['credits']['cast']),
		'similar': handle_tmdb_movies(response['recommendations']['results']),
		'studios': handle_tmdb_misc(response['production_companies']),
		'releases': handle_tmdb_misc(response['releases']['countries']),
		'crew': handle_tmdb_people(response['credits']['crew']),
		'genres': handle_tmdb_misc(response['genres']),
		'keywords': handle_tmdb_misc(response['keywords']['keywords']),
		'reviews': handle_tmdb_misc(response['reviews']['results']),
		'videos': videos,
		'images': handle_tmdb_images(response['images']['posters']),
		'backdrops': handle_tmdb_images(response['images']['backdrops'])
		}
	return (movie, listitems)

def extended_tvshow_info(tvshow_id=None, cache_time=7):
	if not tvshow_id:
		return None
	session_str = ''
	#response = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,recommendations,translations,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	response = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,recommendations,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	if not response:
		return False
	videos = handle_tmdb_videos(response['videos']['results']) if 'videos' in response else []
	tmdb_id = Utils.fetch(response, 'id')
	external_ids = Utils.fetch(response, 'external_ids')
	if external_ids:
		imdb_id = Utils.fetch(external_ids, 'imdb_id')
		freebase_id = Utils.fetch(external_ids, 'freebase_id')
		tvdb_id = Utils.fetch(external_ids, 'tvdb_id')
		tvrage_id = Utils.fetch(external_ids, 'tvrage_id')
	artwork = get_image_urls(poster=response.get('poster_path'), fanart=response.get('backdrop_path'))

	runtimes = response.get('episode_run_time') or []

	if len(runtimes) > 1:
		duration = '%i - %i' % (min(runtimes), max(runtimes))
	elif len(runtimes) == 1:
		duration = '%i' % runtimes[0]
	else:
		duration = ''

	us_cert = Utils.dictfind(response['content_ratings']['results'], 'iso_3166_1', 'US')
	if us_cert:
		mpaa = us_cert['rating']
	elif response['content_ratings']['results']:
		mpaa = response['content_ratings']['results'][0]['rating']
	else:
		mpaa = ''
	genres = [item['name'] for item in response['genres']]
	tvshow = {
		'title': Utils.fetch(response, 'name'),
		'TVShowTitle': Utils.fetch(response, 'name'),
		'OriginalTitle': Utils.fetch(response, 'original_name'),
		'duration': duration,
		'duration(h)': Utils.format_time(duration, 'h'),
		'duration(m)': Utils.format_time(duration, 'm'),
		'id': tmdb_id,
		'tmdb_id': tmdb_id,
		'imdb_id': imdb_id,
		'freebase_id': freebase_id,
		'tvdb_id': tvdb_id,
		'tvrage_id': tvrage_id,
		'mpaa': mpaa,
		'genre': ' / '.join(genres),
		'credit_id': Utils.fetch(response, 'credit_id'),
		'Plot': Utils.clean_text(Utils.fetch(response, 'overview')),
		'year': Utils.get_year(Utils.fetch(response, 'first_air_date')),
		'media_type': 'tv',
		'mediatype': 'tvshow',
		'Popularity': Utils.fetch(response, 'popularity'),
		'Rating': Utils.fetch(response, 'vote_average'),
		'country': Utils.fetch(response, 'original_language'),
		'User_Rating': str(Utils.fetch(response, 'rating')),
		'Votes': Utils.fetch(response, 'vote_count'),
		'Status': translate_status(Utils.fetch(response, 'status')),
		'path': 'plugin://'+str(addon_ID())+'?info=diggzportaltvinfo&&id=%s' % str(tvshow_id),
		'trailer': 'plugin://'+str(addon_ID())+'?info=playtvtrailer&&id=%s' % str(tvshow_id),
		'ShowType': Utils.fetch(response, 'type'),
		'homepage': Utils.fetch(response, 'homepage'),
		'last_air_date': Utils.fetch(response, 'last_air_date'),
		'first_air_date': Utils.fetch(response, 'first_air_date'),
		'TotalEpisodes': Utils.fetch(response, 'number_of_episodes'),
		'TotalSeasons': Utils.fetch(response, 'number_of_seasons'),
		'in_production': Utils.fetch(response, 'in_production'),
		'Release_Date': Utils.fetch(response, 'first_air_date'),
		'Premiered': Utils.fetch(response, 'first_air_date')
		}
	tvshow.update(artwork)
	tvshow['Rating'] = Utils.fetch(response, 'vote_average')

	pop_list = []
	try:
		for idx, i in enumerate(response['recommendations']['results']):
			if int(i.get('vote_count',0)) < 150:
				pop_list.append(idx)
		for i in reversed(pop_list):
			response['recommendations']['results'].pop(i)
	except:
		response['recommendations'] = {'page': 1, 'results': []}

	listitems = {
		'actors': handle_tmdb_people(response['credits']['cast']),
		'similar': handle_tmdb_tvshows(response['recommendations']['results']),
		'studios': handle_tmdb_misc(response['production_companies']),
		'networks': handle_tmdb_misc(response['networks']),
		'certifications': handle_tmdb_misc(response['content_ratings']['results']),
		'crew': handle_tmdb_people(response['credits']['crew']),
		'genres': handle_tmdb_misc(response['genres']),
		'keywords': handle_tmdb_misc(response['keywords']['results']),
		'videos': videos,
		'seasons': handle_tmdb_seasons(response['seasons']),
		'images': handle_tmdb_images(response['images']['posters']),
		'backdrops': handle_tmdb_images(response['images']['backdrops'])
		}
	return (tvshow, listitems)

def extended_season_info(tvshow_id, season_number):
	if not tvshow_id or not season_number:
		return None
	session_str = ''
	#tvshow = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), 99999)
	tvshow = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), 99999)
	response = get_tmdb_data('tv/%s/season/%s?append_to_response=videos,images,external_ids,credits&language=%s&include_image_language=en,null,%s&' % (tvshow_id, season_number, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID')), 7)
	tmdb_id = Utils.fetch(tvshow, 'id')
	external_ids = Utils.fetch(tvshow, 'external_ids')
	year = Utils.get_year(Utils.fetch(tvshow, 'first_air_date'))
	if external_ids:
		imdb_id = Utils.fetch(external_ids, 'imdb_id')
		freebase_id = Utils.fetch(external_ids, 'freebase_id')
		tvdb_id = Utils.fetch(external_ids, 'tvdb_id')
		tvrage_id = Utils.fetch(external_ids, 'tvrage_id')
	if not response:
		Utils.notify('Could not find season info')
		return None
	if response.get('name', False):
		title = response['name']
	else:
		title = 'Specials' if season_number == '0' else 'Season %s' % season_number
	season = {
		'SeasonDescription': Utils.clean_text(response['overview']),
		'Plot': Utils.clean_text(response['overview']),
		'TVShowTitle': Utils.fetch(tvshow, 'name'),
		'title': title,
		'imdb_id': imdb_id,
		'tmdb_id': tmdb_id,
		'tvdb_id': tvdb_id,
		'tvrage_id': tvrage_id,
		'year': year,
		'season': season_number,
		'path': 'plugin://'+str(addon_ID())+'?info=diggzportalseasoninfo&tvshow=%s&season=%s' % (Utils.fetch(tvshow, 'name'), season_number),
		'release_date': response['air_date'],
		'AirDate': response['air_date']
		}
	artwork = get_image_urls(poster=response.get('poster_path'))
	season.update(artwork)
	videos = handle_tmdb_videos(response['videos']['results']) if 'videos' in response else []
	listitems = {
		'actors': handle_tmdb_people(response['credits']['cast']),
		'crew': handle_tmdb_people(response['credits']['crew']),
		'videos': videos,
		'episodes': handle_tmdb_episodes(response['episodes']),
		'images': handle_tmdb_images(response['images']['posters'])
		}
	return (season, listitems)

def extended_episode_info(tvshow_id, season, episode, cache_time=7):
	if not tvshow_id or not episode:
		return None
	if not season:
		season = 0
	session_str = ''
	#tvshow = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), 99999)
	tvshow = get_tmdb_data('tv/%s?append_to_response=alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,videos&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), 99999)
	response = get_tmdb_data('tv/%s/season/%s/episode/%s?append_to_response=credits,runtime,external_ids,images,rating,videos&language=%s&include_image_language=en,null,%s&%s&' % (tvshow_id, season, episode, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	tmdb_id = Utils.fetch(tvshow, 'id')
	TVShowTitle = Utils.fetch(tvshow, 'name')
	external_ids = Utils.fetch(tvshow, 'external_ids')
	year = Utils.get_year(Utils.fetch(tvshow, 'first_air_date')),
	if external_ids:
		imdb_id = Utils.fetch(external_ids, 'imdb_id')
		freebase_id = Utils.fetch(external_ids, 'freebase_id')
		tvdb_id = Utils.fetch(external_ids, 'tvdb_id')
		tvrage_id = Utils.fetch(external_ids, 'tvrage_id')
	videos = handle_tmdb_videos(response['videos']['results']) if 'videos' in response else []
	try:
		actors = handle_tmdb_people(response['credits']['cast'])
	except:
		actors = []
	try:
		crew = handle_tmdb_people(response['credits']['crew'])
	except:
		crew = []
	try:
		guest_stars = handle_tmdb_people(response['credits']['guest_stars'])
	except:
		guest_stars = []
	try:
		images = handle_tmdb_images(response['images']['stills'])
	except:
		images = []
	try: overview = Utils.clean_text(response['overview'])
	except KeyError: overview = ''
	try: runtime = response['runtime']
	except KeyError: runtime = None
	answer = {
		'SeasonDescription': overview,
		'Plot': overview,
		'TVShowTitle': TVShowTitle,
		'tvshow_id': tmdb_id,
		'tvdb_id': tvdb_id,
		'actors': actors,
		'path': 'plugin://'+str(addon_ID())+'?info=diggzportalepisodeinfo&tvshow_id=%s&season=%s&episode=%s' % (tvshow_id, season, episode),
		'crew': crew,
		'runtime': runtime,
		'guest_stars': guest_stars,
		'videos': videos,
		'images': images
		}
	#response = {'status_code': 7, 'status_message': 'Invalid API key: You must be granted a valid key.', 'success': False}
	ep = (handle_tmdb_episodes([response])[0], answer)
	ep[0]['poster'] = 'https://image.tmdb.org/t/p/w342' + tvshow['poster_path']
	ep[0]['thumb'] = 'https://image.tmdb.org/t/p/w342' + tvshow['poster_path']
	try: 
		ep[0]['fanart'] = ep[0]['still_original']
	except: 
		ep[0]['fanart'] = 'https://image.tmdb.org/t/p/w342' + tvshow['backdrop_path']
		#xbmc.log(str(ep[0])+'===>PHIL', level=xbmc.LOGINFO)
		#xbmc.log(str(tvshow)+'===>PHIL', level=xbmc.LOGINFO)
		pass
	ep[0]['TVShowTitle'] = TVShowTitle
	ep[0]['status'] = tvshow['status']
	#xbmc.log(str(response)+'===>get_trakt_playback', level=xbmc.LOGINFO)
	#xbmc.log(str(tvshow)+'===>get_trakt_playback', level=xbmc.LOGINFO)
	if ep[0]['episode'] == '':
		season_dict = extended_season_info(tvshow_id, season)
		ep[1]['actors'] = season_dict[1]['actors']
		ep[1]['crew'] = season_dict[1]['crew']
		#ep[1]['guest_stars'] = season[1]['guest_stars']
		ep[0]['season'] = int(season)
		ep[0]['episode'] = int(episode)
		ep[0]['Plot'] = season_dict[1]['episodes'][int(episode)-1]['Description']
		ep[0]['Description'] = season_dict[1]['episodes'][int(episode)-1]['Description']
		ep[0]['Votes'] = season_dict[1]['episodes'][int(episode)-1]['Votes']
		ep[0]['Rating'] = season_dict[1]['episodes'][int(episode)-1]['Rating']
		ep[0]['id'] = season_dict[1]['episodes'][int(episode)-1]['id']
		ep[0]['production_code'] = season_dict[1]['episodes'][int(episode)-1]['production_code']
		ep[0]['release_date'] = season_dict[1]['episodes'][int(episode)-1]['release_date']
		ep[0]['title'] = season_dict[1]['episodes'][int(episode)-1]['title']
		ep[0]['still'] = season_dict[1]['episodes'][int(episode)-1]['still'] 
		ep[0]['still_original'] = season_dict[1]['episodes'][int(episode)-1]['still_original'] 
		ep[0]['still_small'] = season_dict[1]['episodes'][int(episode)-1]['still_small'] 
		ep[0]['thumb'] = season_dict[1]['episodes'][int(episode)-1]['thumb'] 
		ep[0]['poster'] = 'https://image.tmdb.org/t/p/w342/' + tvshow['poster_path']
		ep[1]['images'] = []
		ep[1]['images'].append({'aspectratio': 1.778,
			'iso_639_1': None,
			'original': season_dict[1]['episodes'][int(episode)-1]['still_original'] ,
			'poster': season_dict[1]['episodes'][int(episode)-1]['still'],
			'poster_original': season_dict[1]['episodes'][int(episode)-1]['still_original'],
			'poster_small': season_dict[1]['episodes'][int(episode)-1]['still_small'], 
			'thumb': season_dict[1]['episodes'][int(episode)-1]['thumb'],
			'vote_average': 0.0})
	#return (handle_tmdb_episodes([response])[0], answer)
	ep[0]['year'] = ep[0]['release_date'][:4]
	return ep

def extended_actor_info(actor_id):
	if not actor_id:
		return None
	response = get_tmdb_data('person/%s?append_to_response=tv_credits,movie_credits,combined_credits,images,tagged_images&' % actor_id, 1)
	tagged_images = []
	if 'tagged_images' in response:
		tagged_images = handle_tmdb_tagged_images(response['tagged_images']['results'])
	listitems = {
	'movie_roles': handle_tmdb_movies(response.get('movie_credits', {}).get('cast', [])),
	'tvshow_roles': handle_tmdb_tvshows(response.get('tv_credits', {}).get('cast', [])),
	'movie_crew_roles': handle_tmdb_movies(response.get('movie_credits', {}).get('crew', [])),
	'tvshow_crew_roles': handle_tmdb_tvshows(response.get('tv_credits', {}).get('crew', [])),
	'tagged_images': tagged_images,
	'images': handle_tmdb_images(response.get('images', {}).get('profiles', []))
	}
	info = handle_tmdb_people([response])[0]
	return (info, listitems)

def translate_status(status_string):
	translations = {
		'released': 'Released',
		'post production': 'Post production',
		'in production': 'In production',
		'ended': 'Ended',
		'returning series': 'Continuing',
		'planned': 'Planned'
		}
	if status_string.lower() in translations:
		return translations[status_string.lower()]
	else:
		return status_string

def get_keywords(movie_id):
	response = get_tmdb_data('movie/%s?append_to_response=alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,rating&include_image_language=en,null,%s&language=%s&' % (movie_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID')), 30)
	keywords = []
	if 'keywords' in response:
		for keyword in response['keywords']['keywords']:
			keyword_dict = {
				'id': Utils.fetch(keyword, 'id'),
				'name': keyword['name']
				}
			keywords.append(keyword_dict)
	return keywords

def get_tmdb_shows(tvshow_type):
	response = get_tmdb_data('tv/%s?language=%s&' % (tvshow_type, xbmcaddon.Addon().getSetting('LanguageID')), 0.3)
	if 'results' in response:
		return handle_tmdb_tvshows(response['results'], sortkey=None)
	else:
		return []

def get_tmdb_movies(movie_type):
	response = get_tmdb_data('movie/%s?language=%s&' % (movie_type, xbmcaddon.Addon().getSetting('LanguageID')), 0.3)
	if 'results' in response:
		return handle_tmdb_movies(response['results'], sortkey=None)
	else:
		return []

def get_set_movies(set_id):
	response = get_tmdb_data('collection/%s?language=%s&append_to_response=images&include_image_language=en,null,%s&' % (set_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID')), 14)
	if response['parts'] == []:
		response2 = get_tmdb_data('collection/%s?' % (set_id), 14)
		response['parts'] = response2['parts']
	if response['parts'] == []:
		response2 = get_tmdb_data('collection/%s?&language=NULL&' % (set_id), 14)
		response['parts'] = response2['parts']
	if response:
		artwork = get_image_urls(poster=response.get('poster_path'), fanart=response.get('backdrop_path'))
		info = {
			'label': response['name'],
			'overview': response['overview'],
			'id': response['id']
			}
		info.update(artwork)
		return handle_tmdb_movies(response.get('parts', [])), info
	else:
		return [], {}


def get_person_movies(person_id):
	response = get_tmdb_data('person/%s/credits?language=%s&' % (person_id, xbmcaddon.Addon().getSetting('LanguageID')), 14)
	if 'crew' in response:
		return handle_tmdb_movies(response['crew'])
	else:
		return []

def get_person(person_id):
	response = get_tmdb_data('person/%s?language=%s&append_to_response=combined_credits&' % (person_id, xbmcaddon.Addon().getSetting('LanguageID')), 14)
	listitems = handle_tmdb_multi_search(response['combined_credits']['cast'])
	listitems += handle_tmdb_multi_search(response['combined_credits']['crew'])
	return listitems

def search_media(media_name=None, year='', media_type='movie'):
	search_query = Utils.url_quote('%s %s' % (media_name, year))
	if not search_query:
		return None
	response = get_tmdb_data('search/%s?query=%s&language=%s&include_adult=%s&' % (media_type, search_query, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('include_adults')), 1)
	if not response == 'Empty':
		for item in response['results']:
			if item['id']:
				return item['id']
	return None

def get_imdb_id_from_movie_id(movie_id=None, cache_time=14):
	if not movie_id:
		return None
	session_str = ''
	response = get_tmdb_data('movie/%s?&language=%s,null,%s&%s' % (movie_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	if not response:
		return False
	imdb_id = Utils.fetch(response, 'imdb_id')
	return imdb_id

def get_tvshow_ids(tvshow_id=None, cache_time=14):
	if not tvshow_id:
		return None
	session_str = ''
	response = get_tmdb_data('tv/%s?append_to_response=external_ids&language=%s&include_image_language=en,null,%s&%s' % (tvshow_id, xbmcaddon.Addon().getSetting('LanguageID'), xbmcaddon.Addon().getSetting('LanguageID'), session_str), cache_time)
	if not response:
		return False
	external_ids = Utils.fetch(response, 'external_ids')
	return external_ids



def get_trakt_playback(trakt_type=None):
	import urllib.parse
	from datetime import datetime
	from datetime import timedelta
	from resources.lib.trakt import get_trakt_data
	date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
	now = datetime.strftime(datetime.now() + timedelta(days=1), date_format)
	year_minus_one = datetime.strftime(datetime.now() - timedelta(days=1*180), date_format)
	if trakt_type == 'tv':
		url = 'https://api.trakt.tv/sync/playback/episodes?start_at=%s&end_at=%s' % (urllib.parse.quote(year_minus_one),urllib.parse.quote(now))
		response = get_trakt_data(url=url, cache_days=0.0001, folder='Trakt')
		#xbmc.log(str(response)+'===>get_trakt_playback', level=xbmc.LOGINFO)
		return response
	else:
		url = 'https://api.trakt.tv/sync/playback/movies?start_at=%s&end_at=%s' % (urllib.parse.quote(year_minus_one),urllib.parse.quote(now))
		response = get_trakt_data(url=url, cache_days=0.0001, folder='Trakt')
		#xbmc.log(str(response)+'===>get_trakt_playback', level=xbmc.LOGINFO)
		return response

def update_trakt_playback(trakt_type=None,tmdb_id=None,episode=None,season=None):
	from resources.lib.trakt import trak_auth
	import requests
	if trakt_type == 'tv':
		response = get_trakt_playback('tv')
		item_id = tmdb_id
		episode = str(episode)
		season = str(season)
		DBTYPE = 'episode'
	else:
		response = get_trakt_playback('movie')
		item_id = tmdb_id
		DBTYPE = 'movie'
	for i in response:
		if DBTYPE == 'episode':
			if str(i['show']['ids']['tmdb']) == str(item_id):
				if str(i['episode']['number']) == str(episode) and str(i['episode']['season']) == str(season):
					play_id = i['id']
					url = 'https://api.trakt.tv/sync/playback/' + str(play_id)
					response = requests.delete(url, headers=trak_auth())
		else:
			if str(i['movie']['ids']['tmdb']) == str(item_id):
				play_id = i['id']
				url = 'https://api.trakt.tv/sync/playback/' + str(play_id)
				response = requests.delete(url, headers=trak_auth())	
	return response


def get_watching_user():
	from resources.lib.trakt import get_trakt_data
	trakt_slug = xbmcaddon.Addon().getSetting('trakt_slug')
	url = 'https://api.trakt.tv/users/%s/watching' % str(trakt_slug)
	response = get_trakt_data(url=url, cache_days=0.0001, folder='Trakt')
	return response

def get_trakt_lists(list_name=None,user_id=None,list_slug=None,sort_by=None,sort_order=None,limit=0):
	from resources.lib.trakt import trakt_lists
	movies = trakt_lists(list_name,user_id,list_slug,sort_by,sort_order)
	listitems = None
	x = 0
	if movies == None:
		return listitems
	for i in movies:
		imdb_id = i['ids']['imdb']
		response = get_tmdb_data('find/%s?language=%s&external_source=imdb_id&' % (imdb_id, xbmcaddon.Addon().getSetting('LanguageID')), 13)
		result_type = False
		try:
			response['movie_results'][0]['media_type'] = 'movie'
			result_type = 'movie_results'
		except:
			try:
				response['tv_results'][0]['media_type'] = 'tv'
				result_type = 'tv_results'
			except:
				result_type = False
				pass
		if listitems == None and result_type != False:
			listitems = handle_tmdb_multi_search(response[result_type])
		elif result_type != False:
			listitems += handle_tmdb_multi_search(response[result_type])
		if x + 1 == int(limit) and limit != 0:
			break
		x = x + 1
	Utils.show_busy()
	return listitems

def get_trakt(trakt_type=None,info=None,limit=0):
	import sys
	if trakt_type == 'movie':
		if info == 'trakt_watched':
			from resources.lib.trakt import trakt_watched_movies
			movies = trakt_watched_movies()
			#self.type = 'movie'
		if info == 'trakt_coll':
			from resources.lib.trakt import trakt_collection_movies
			movies = trakt_collection_movies()
			#self.type = 'movie'
		if info == 'trakt_trend':
			from resources.lib.trakt import trakt_trending_movies
			movies = trakt_trending_movies()
		if info == 'trakt_popular':
			from resources.lib.trakt import trakt_popular_movies
			movies = trakt_popular_movies()
	else:
		if info == 'trakt_watched':
			from resources.lib.trakt import trakt_watched_tv_shows
			movies = trakt_watched_tv_shows()
			#self.type = 'tv'
		if info == 'trakt_unwatched':
			from resources.lib.trakt import trakt_unwatched_tv_shows
			movies = trakt_unwatched_tv_shows()
		if info == 'trakt_coll':
			from resources.lib.trakt import trakt_collection_shows
			movies = trakt_collection_shows()
			#self.type = 'tv'
		if info == 'trakt_trend':
			from resources.lib.trakt import trakt_trending_shows
			movies = trakt_trending_shows()
		if info == 'trakt_popular':
			from resources.lib.trakt import trakt_popular_shows
			movies = trakt_popular_shows()
		if info == 'trakt_progress':
			from resources.lib.trakt import trakt_watched_tv_shows_progress
			movies = trakt_watched_tv_shows_progress()

	if 'script=False' in str(sys.argv):
		script = False
	else:
		script = True

	if script:
		listitems = None
		x = 0
		for i in movies:
			try:
				try:
					imdb_id = i['movie']['ids']['imdb']
				except:
					imdb_id = i['show']['ids']['imdb']
			except:
				imdb_id = i['ids']['imdb']
			response = get_tmdb_data('find/%s?language=%s&external_source=imdb_id&' % (imdb_id, xbmcaddon.Addon().getSetting('LanguageID')), 13)
			result_type = False
			try:
				response['movie_results'][0]['media_type'] = 'movie'
				result_type = 'movie_results'
			except:
				try:
					response['tv_results'][0]['media_type'] = 'tv'
					result_type = 'tv_results'
				except:
					result_type = False
					pass
			if listitems == None and result_type != False:
				#listitems = handle_tmdb_multi_search(response[result_type])
				listitems = []
				if result_type == 'movie_results':
					listitems.append(single_movie_info(response[result_type][0]['id']))
				else:
					listitems.append(single_tvshow_info(response[result_type][0]['id']))
			elif result_type != False:
				#listitems += handle_tmdb_multi_search(response[result_type])
				if result_type == 'movie_results':
					#try: 
					#	listitems.append(single_movie_info(response[result_type][0]['id']))
					#except: 
					#	xbmc.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))+'===>OPENINFO', level=xbmc.LOGINFO)
					#	xbmc.log(str(response[result_type][0])+'===>EXCEPTION', level=xbmc.LOGINFO)
					listitems.append(single_movie_info(response[result_type][0]['id']))
				else:
					listitems.append(single_tvshow_info(response[result_type][0]['id']))
		#Utils.show_busy()
			if x + 1 == int(limit) and limit != 0:
				break
			x = x + 1
		return listitems
	else:
		listitems = None
		x = 0
		for i in movies:
			try:
				try:
					imdb_id = i['movie']['ids']['imdb']
				except:
					imdb_id = i['show']['ids']['imdb']
			except:
				imdb_id = i['ids']['imdb']
			response = get_tmdb_data('find/%s?language=%s&external_source=imdb_id&' % (imdb_id, xbmcaddon.Addon().getSetting('LanguageID')), 13)
			result_type = False
			try:
				response['movie_results'][0]['media_type'] = 'movie'
				result_type = 'movie_results'
			except:
				try:
					response['tv_results'][0]['media_type'] = 'tv'
					result_type = 'tv_results'
				except:
					result_type = False
					pass
			if listitems == None and result_type != False:
				listitems = handle_tmdb_multi_search(response[result_type])
			elif result_type != False:
				listitems += handle_tmdb_multi_search(response[result_type])
			if x + 1 == int(limit) and limit != 0:
				break
			x = x + 1
		Utils.show_busy()
		return listitems


def get_imdb_language_api(imdb_id=None, cache_days=14, folder='IMDB'):
	import requests
	import json
	url = "https://api.graphql.imdb.com/"
	headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"User-Agent": "Mozilla/5.0"
	}
	query = """ query ($id: ID!) { title(id: $id) { spokenLanguages { spokenLanguages { id text } } countriesOfOrigin { countries(limit: 1) { id } } } } """
	variables = {"id": imdb_id}
	payload = {"query": query, "variables": variables}
	imdb_url = ('https://www.imdb.com/title/' + str(imdb_id) + '/get_imdb_language').encode('utf-8')
	imdb_header = headers
	try:
		db_result, expired_db_result = Utils.query_db(connection=Utils.db_con,url=imdb_url, cache_days=cache_days, folder=folder, headers=imdb_header)
	except:
		db_result, expired_db_result = None, None
	if db_result:
		return db_result
	else:
		response = requests.post(url, headers=headers, data=json.dumps(payload))
		if response.status_code != 200:
			return []
		data = response.json()
		spoken = data.get("data", {}).get("title", {}).get("spokenLanguages", {}).get("spokenLanguages", [])
		countries = data.get("data", {}).get("title", {}).get("countriesOfOrigin", {}).get("countries", [])
		language_list = [lang.get("text") for lang in spoken if "text" in lang]
		english_speaking_countries = {"US", "UK", "GB", "CA", "AU", "NZ", "IE", "ZA"}
		country_id = countries[0].get("id") if countries else ""
		if "English" in language_list and country_id in english_speaking_countries:
			language_list = ["English"] + [l for l in language_list if l != "English"]
		results = language_list
	#Utils.write_db(connection=Utils.db_con,url=url, cache_days=cache_days, folder=folder,cache_val=results)
	#if not results:
	#	return []
	#else:
	#	return results

	if not results or len(results) == 0:
		if expired_db_result == None:
			return []
		if len(expired_db_result) > 0:
			Utils.write_db(connection=Utils.db_con,url=url, cache_days=0.25, folder=folder,cache_val=expired_db_result)
			return expired_db_result
		return []
	else:
		Utils.write_db(connection=Utils.db_con,url=url, cache_days=cache_days, folder=folder,cache_val=results)
	return results

def imdb_base_title_card(imdb_id: str):
	url = "https://api.graphql.imdb.com/"
	headers = {
		"Content-Type": "application/json",
		"User-Agent": "Mozilla/5.0"
	}
	query = """
	query Title_Summary_Prompt_From_Base($id: ID!) { title(id: $id) { ...BaseTitleCard } }
	fragment BaseTitleCard on Title { 
		id titleText { text } 
		titleType { id text canHaveEpisodes displayableProperty { value { plainText } } }
		originalTitleText { text } 
		primaryImage { id width height url caption { plainText } }
		releaseYear { year endYear }
		ratingsSummary { aggregateRating voteCount }
		runtime { seconds }
		certificate { rating }
		canRate { isRatable }
		titleGenres { genres(limit: 3) { genre { text } } } 
		}
	"""
	variables = {
		"id": imdb_id
	}
	response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
	if response.status_code == 200:
		return response.json()
	else:
		raise Exception(f"Query failed with status code {response.status_code}: {response.text}")

def get_imdb_language(imdb_id=None, cache_days=14, folder='IMDB'):
	Utils.log('get_imdb_language_api')
	results = get_imdb_language_api(imdb_id=imdb_id, cache_days=cache_days, folder='IMDB')
	return results


def get_imdb_season_episodes(imdb_id, season, first=99):
	import requests
	import json
	url = "https://api.graphql.imdb.com/"
	headers = {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"User-Agent": "Mozilla/5.0"
	}
	query = """query SeasonEpisodes($id: ID!, $season: String!, $first: Int!, $originalTitleText: Boolean!) { title(id: $id) { episodes { episodes(first: $first, filter: { includeSeasons: [$season] }, sort: { by: EPISODE_THEN_RELEASE, order: ASC }) { edges { node { id titleText { text } plot { plotText { plaidHtml(showOriginalTitleText: $originalTitleText) } } releaseDate { year month day } ratingsSummary { aggregateRating voteCount } primaryImage { url } series { displayableEpisodeNumber { episodeNumber { displayableProperty { value { plainText } } } displayableSeason { displayableProperty { value { plainText } } } } } } } } } } }"""
	variables = {
		"id": imdb_id,
		"season": str(season),
		"first": first,
		"originalTitleText": True
	}
	payload = {
		"query": query,
		"variables": variables
	}
	response = requests.post(url, headers=headers, data=json.dumps(payload))
	try: response.raise_for_status()
	except requests.exceptions.HTTPError as e: return []
	data = response.json()
	edges = data.get("data", {}).get("title", {}).get("episodes", {}).get("episodes", {}).get("edges", [])
	episodes = []
	for edge in edges:
		try: 
			node = edge.get("node", {})
			displayable_episode_number = node.get("series", {}).get("displayableEpisodeNumber", {})
			episode_number = displayable_episode_number.get("episodeNumber", {}).get("displayableProperty", {}).get("value", {}).get("plainText")
			season_number = displayable_episode_number.get("displayableSeason", {}).get("displayableProperty", {}).get("value", {}).get("plainText")
			plot_html = node.get("plot", {}).get("plotText", {}).get("plaidHtml")
			episodes.append({
				"id": node.get("id"),
				"title": node.get("titleText", {}).get("text"),
				"plot": plot_html,
				"release_date": node.get("releaseDate"),
				"rating": node.get("ratingsSummary", {}).get("aggregateRating"),
				"vote_count": node.get("ratingsSummary", {}).get("voteCount"),
				"image_url": node.get("primaryImage", {}).get("url"),
				"episode_number": episode_number,
				"season_number": season_number
			})
		except: continue
	return episodes





def get_imdb_watchlist_items(movies=None, limit=0, cache_days=14, folder='IMDB', imdb_url=None):
	import time, hashlib, xbmcvfs, os
	import re, json, requests, html

	if imdb_url:
		url = imdb_url +'/get_imdb_watchlist_items'
	else:
		url = 'imdb_'
		for i in movies:
			url = url + str(i) +'/get_imdb_watchlist_items'

	now = time.time()
	url = url.encode('utf-8')
	hashed_url = hashlib.md5(url).hexdigest()
	cache_path = xbmcvfs.translatePath(os.path.join(Utils.ADDON_DATA_PATH, folder)) if folder else xbmcvfs.translatePath(os.path.join(Utils.ADDON_DATA_PATH))
	cache_seconds = int(cache_days * 86400.0)
	path = os.path.join(cache_path, '%s.txt' % hashed_url)

	try: 
		db_result, expired_db_result = Utils.query_db(connection=Utils.db_con,url=url, cache_days=cache_days, folder=folder, headers=None)
	except:
		db_result, expired_db_result = None, None
	if db_result and len(db_result) > 0:
		return db_result
	else:
		listitems = None
		x = 0
		if not movies:
			return None
		for y in movies:
			imdb_id = y
			response = get_tmdb_data('find/%s?language=%s&external_source=imdb_id&' % (imdb_id, xbmcaddon.Addon().getSetting('LanguageID')), 13)
			try:
				response['movie_results'][0]['media_type'] = 'movie'
				if listitems == None:
					listitems = handle_tmdb_multi_search(response['movie_results'])
				else:
					listitems += handle_tmdb_multi_search(response['movie_results'])
			except:
				try:
					response['tv_results'][0]['media_type'] = 'tv'
					if listitems == None:
						listitems = handle_tmdb_multi_search(response['tv_results'])
					else:
						listitems += handle_tmdb_multi_search(response['tv_results'])
				except:
					continue
			if x + 1 == int(limit) and limit != 0:
				break
			x = x + 1

		if not listitems or len(listitems) == 0:
			if expired_db_result == None:
				return []
			if len(expired_db_result) > 0:
				write_db(connection=Utils.db_con,url=url, cache_days=0.25, folder=folder,cache_val=expired_db_result)
				return expired_db_result
			return []
		else:
			Utils.write_db(connection=Utils.db_con,url=url, cache_days=cache_days, folder=folder,cache_val=listitems)
		return listitems


