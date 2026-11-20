import sys
import xbmc
from resources.lib.trakt import addon_ID
from resources.lib.trakt import addon_ID_short
from resources.lib import process

if __name__ == '__main__':
	base = 'RunScript('+str(addon_ID())+',info='
	info = sys.listitem.getVideoInfoTag()
	type = info.getMediaType()

	if not type in ['movie','tvshow','season','episode','actor','director']:
		if xbmc.getInfoLabel('listitem.DBTYPE') == 'movie':
			type = 'movie'
		elif xbmc.getInfoLabel('listitem.DBTYPE') in ['tv', 'tvshow', 'season', 'episode']:
			type = 'tvshow'

	try: imdb_id = info.getUniqueID('imdb')
	except: imdb_id = None
	try: tmdb_id = info.getUniqueID('tmdb')
	except: tmdb_id = None
	try: tvdb_id = info.getUniqueID('tvdb')
	except: tvdb = None
	if tmdb_id:
		remote_id = tmdb_id
	else:
		remote_id = sys.listitem.getProperty('id')
	params = {}
	infos = []
	if type   == 'movie':
		base = 'RunScript('+str(addon_ID())+',info='+str(addon_ID_short())
		infos.append(str(addon_ID_short()))
		if tmdb_id:
			params['id'] = tmdb_id
		else:
			params['id'] = remote_id
		if imdb_id:
			params['imdb_id'] = imdb_id
		else:
			params['imdb_id'] = info.getIMDBNumber()
		params['name'] = info.getTitle()
		#xbmc.executebuiltin(url)
	elif type == 'tvshow':
		infos.append('diggzportaltvinfo')
		if tmdb_id:
			params['id'] = tmdb_id
		else:
			params['id'] = remote_id
		if imdb_id:
			params['imdb_id'] = imdb_id
		else:
			params['imdb_id'] = info.getIMDBNumber()
		params['name'] = info.getTitle()
	elif type == 'season':
		infos.append('diggzportalseasoninfo')
		if tmdb_id:
			params['id'] = tmdb_id
		else:
			params['id'] = remote_id
		params['tvshow'] = info.getTVShowTitle()
		params['season'] = info.getSeason()
	elif type == 'episode':
		infos.append('diggzportalepisodeinfo')
		if tmdb_id:
			params['id'] = tmdb_id
		else:
			params['id'] = remote_id
		params['tvshow'] = info.getTVShowTitle()
		params['season'] = info.getSeason()
		params['episode'] = info.getEpisode()
	elif type in ['actor', 'director']:
		infos.append('diggzportalactorinfo')
		params['name'] = sys.listitem.getLabel()
		#xbmc.executebuiltin('%sextendedactorinfo,name=%s)' % (base, sys.listitem.getLabel()))
	if infos:
		process.start_info_actions(infos, params)
