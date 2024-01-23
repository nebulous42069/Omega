# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import importlib
import os, json
import sys
import shutil
import re

import tools, source_tools
#import queue
#import threading, time, random
from a4kSubtitles.lib import utils


from inspect import currentframe, getframeinfo
#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))

from a4kSubtitles import api
from source_tools import get_guess
import distance 

META = None

import struct
__64k = 65536
__longlong_format_char = 'q'
__byte_size = struct.calcsize(__longlong_format_char)

def sum_64k_bytes(file, filehash):
	range_value = __64k / __byte_size
	from a4kSubtitles.lib import utils
	if utils.py3:
		range_value = round(range_value)

	for _ in range(range_value):
		try: chunk = file.readBytes(__byte_size)
		except: chunk = file.read(__byte_size)
		(value,) = struct.unpack(__longlong_format_char, chunk)
		filehash += value
		filehash &= 0xFFFFFFFFFFFFFFFF
		return filehash

def set_size_and_hash(meta, filepath):
	if meta == None and META != None:
		meta = META
	#f = xbmcvfs.File(filepath)
	if 'http' in str(filepath):
		meta = set_size_and_hash_url(meta=meta, file_path=filepath)
		return meta
	f = open(filepath, 'rb')
	try:
		#filesize = f.size()
		filesize = os.path.getsize(filepath)
		meta['filesize'] = filesize

		if filesize < __64k * 2:
			return

		# ref: https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
		# filehash = filesize + 64bit sum of the first and last 64k of the file
		filehash = lambda: None
		filehash = filesize

		filehash = sum_64k_bytes(f, filehash)
		f.seek(filesize - __64k, os.SEEK_SET)
		filehash = sum_64k_bytes(f, filehash)

		meta['filehash'] = "%016x" % filehash
	finally:
		f.close()
	return meta


def temp_file():
	import tempfile
	file = tempfile.NamedTemporaryFile()
	filename = file.name
	return filename

def set_size_and_hash_url(meta, filepath):
	if meta == None and META != None:
		meta = META
	import urllib
	from urllib import request
	f = None
	opener = None
	url = filepath
	request.urlcleanup()
	
	f = request.urlopen(url)

	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log(f.headers)

	filesize = int(f.headers['Content-Length'])
	if filesize < __64k * 2:
		try: filesize = int(str(f.headers['Content-Range']).split('/')[1])
		except: pass

	opener = request.build_opener()
	#opener.addheaders = [('Range', 'bytes=%s-%s' % (0, __64k-1))]
	opener.addheaders = [('Range','bytes=0-65535')]

	first_64kb = temp_file()
	last_64kb = temp_file()
	request.install_opener(opener)
	#tools.log('first_64kb',first_64kb,'last_64kb',last_64kb)
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	request.urlretrieve(url, first_64kb)
	opener = request.build_opener()

	if filesize > 0:
		opener.addheaders = [('Range', 'bytes=%s-%s' % (filesize - __64k, 0))]
		#tools.log(str('bytes=%s-%s' % (1+filesize - __64k, 0)))
	else:
		opener.addheaders = [('Range','bytes=-65535-0')]
	request.install_opener(opener)
	request.urlretrieve(url, last_64kb)

	#f = xbmcvfs.File(filepath)
	f = open(first_64kb, 'rb')

	#try:
	if 1==1:
		#filesize = f.size()
		meta['filesize'] = filesize
		
		if filesize < __64k * 2:
			f.close()
			meta['filehash'] = ''
			tools.delete_file(first_64kb)
			tools.delete_file(last_64kb)
			#del request
			return meta

		# ref: https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
		# filehash = filesize + 64bit sum of the first and last 64k of the file
		filehash = lambda: None
		filehash = filesize
		filehash = sum_64k_bytes(f, filehash)
		#f.seek(filesize - __64k, os.SEEK_SET)
		#tools.log(first_64kb, 'size='+str(os.path.getsize(first_64kb)),'set_size_and_hash_url')
		f.close()
		f = open(last_64kb, 'rb')
		filehash = sum_64k_bytes(f, filehash)
		#tools.log(last_64kb, 'size='+str(os.path.getsize(last_64kb)),'set_size_and_hash_url')
		meta['filehash'] = "%016x" % filehash
		
	#finally:
		f.close()
		tools.delete_file(first_64kb)
		tools.delete_file(last_64kb)
	#del request
	return meta

def get_subtitles_meta(VIDEO_META, file_path):
	"""
import get_meta, getSources
meta = get_meta.get_movie_meta(movie_name='Point Break',year=1991)
info = meta

import get_meta, getSources
meta = get_meta.get_episode_meta(season=1,episode=1,show_name='The Flash', year=2014)
info = meta['episode_meta']

##FILEPATH!!
getSources.get_subtitles(info , '')

"""
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#try:
	from urllib.parse import unquote
	if 1==1:
		VIDEO_META['season'] = str(VIDEO_META['season'] )
		VIDEO_META['episode'] = str(VIDEO_META['episode'])
	#except:
	#	pass
	#try:
	if 1==1:
		VIDEO_META['file_name'] = unquote(os.path.basename(file_path))
		VIDEO_META['filename'] = unquote(VIDEO_META['file_name'])
		VIDEO_META['filename_without_ext'] = unquote(os.path.splitext(VIDEO_META['file_name'])[0])
		VIDEO_META['subs_filename'] = unquote(VIDEO_META['filename_without_ext'] + '.srt')
		#tools.VIDEO_META = VIDEO_META
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		#tools.log('VIDEO_META',VIDEO_META, 'file_path',file_path)
		if 'http' in str(file_path):
			VIDEO_META2 = set_size_and_hash_url(meta=VIDEO_META, filepath=file_path)
		else:
			VIDEO_META2 = set_size_and_hash(meta=VIDEO_META, filepath=file_path)
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		#tools.log('VIDEO_META2',VIDEO_META2, 'file_path',file_path)
	#except:
	#	pass
	#os.environ['A4KSUBTITLES_API_MODE'] = str({'kodi': 'false'})
	#try: import subtitles
	#except: from a4kscrapers_wrapper import subtitles
	#subfile = subtitles.SubtitleService().get_subtitle()
	#VIDEO_META['SUB_FILE'] = tools.SUB_FILE
	#tools.VIDEO_META = VIDEO_META
	
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log('VIDEO_META', VIDEO_META,'json.dumps???????????????????????')
	VIDEO_META = VIDEO_META2
	if VIDEO_META.get('tvshowtitle','') != '':
		if (VIDEO_META['tvshowtitle'] in VIDEO_META['aliases']) == False:
			VIDEO_META['aliases'].append(VIDEO_META['tvshowtitle'])
	#tools.VIDEO_META['SUB_FILE'] = tools.SUB_FILE
	#json_data = json.dumps(VIDEO_META, indent=2)
	#curr_meta = os.path.join(tools.ADDON_USERDATA_PATH, 'curr_meta.json')
	#tools.log('write_all_text')
	#tools.log(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))
	#tools.write_all_text(curr_meta, json_data)
	#tools.log(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename))
	return VIDEO_META



def get_subtitles(VIDEO_META, file_path):
	"""
import get_meta, getSources
meta = get_meta.get_movie_meta(movie_name='Point Break',year=1991)
info = meta

import get_meta, getSources
meta = get_meta.get_episode_meta(season=1,episode=1,show_name='The Flash', year=2014)
info = meta['episode_meta']

##FILEPATH!!
getSources.get_subtitles(info , '')

"""
	if 1==1:
		VIDEO_META['season'] = str(VIDEO_META['season'] )
		VIDEO_META['episode'] = str(VIDEO_META['episode'])

	if 1==1:
		VIDEO_META['file_name'] = os.path.basename(file_path)
		VIDEO_META['filename'] = VIDEO_META['file_name']
		VIDEO_META['filename_without_ext'] = os.path.splitext(VIDEO_META['file_name'])[0]
		VIDEO_META['subs_filename'] = VIDEO_META['filename_without_ext'] + '.srt'
		#tools.VIDEO_META = VIDEO_META
		if 'http' in str(file_path):
			VIDEO_META = set_size_and_hash_url(meta=VIDEO_META, filepath=file_path)
		else:
			VIDEO_META = set_size_and_hash(meta=VIDEO_META, filepath=file_path)
	tools.VIDEO_META = VIDEO_META
	os.environ['A4KSUBTITLES_API_MODE'] = str({'kodi': 'false'})
	from a4kscrapers_wrapper import subtitles
	subfile = subtitles.SubtitleService().get_subtitle()
	tools.VIDEO_META['SUB_FILE'] = tools.SUB_FILE

	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log('tools.VIDEO_META', tools.VIDEO_META)
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log(META, VIDEO_META)
	return tools.VIDEO_META


def get_subtitles_list(VIDEO_META, file_path):
	#from a4kscrapers_wrapper import subs

	meta = get_subtitles_meta(VIDEO_META, file_path)
	#tools.VIDEO_META = VIDEO_META
	META = meta
	VIDEO_META = meta
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log('META',META,'VIDEO_META', VIDEO_META,'meta',meta)
	#tools.VIDEO_META = meta
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log('tools.VIDEO_META', tools.VIDEO_META)

	subfile = SubtitleService(meta).get_subtitle()
	tools.SUB_FILE = subfile
	#tools.VIDEO_META['SUB_FILE'] = subfile
	#tools.log('SUBTITLES_____________',tools.VIDEO_META)
	#SUB_FILE = tools.VIDEO_META['SUB_FILE']
	try: 
		SUB_FILE = tools.VIDEO_META['SUB_FILE']
	except: 
		SUB_FILE = meta['SUB_FILE']
		tools.VIDEO_META = meta
	#tools.log(tools.VIDEO_META,meta)
	try: 
		SUB_FILE_FORCED = tools.VIDEO_META['SUB_FILE_FORCED']
	except: 
		SUB_FILE_FORCED = meta['SUB_FILE_FORCED']
		tools.VIDEO_META = meta
	subs_list = []
	if str(SUB_FILE) != '' and SUB_FILE != None:
		subs_list.append(SUB_FILE)
	if str(SUB_FILE_FORCED) != '' and SUB_FILE_FORCED != None:
		subs_list.append(SUB_FILE_FORCED)
	return subs_list



class SubtitleService(object):
	"""
	Connects to available subtitle services and retrieves available subtitles for media
	"""

	def __init__(self, meta):
		#self.task_queue = queue.Queue()
		#self.subtitle_languages = g.get_kodi_subtitle_languages()
		#self.preferred_language = g.get_kodi_preferred_subtitle_language()
		#self.base_request = {
		#	"languages": ",".join(self.subtitle_languages),
		#	"preferredlanguage": self.preferred_language,
		#}

		if meta == None and META != None:
			meta = META
		self.VIDEO_META = meta
		#tools.VIDEO_META = self.VIDEO_META
		#tools.log('SUBS.PY',meta, tools.VIDEO_META)
		self.base_request = {'action': 'search', 'languages': 'English', 'preferredlanguage': 'forced_only'}
		self.base_request = {'action': 'search', 'languages': 'English', 'preferredlanguage': 'English'}
		self.base_request['VIDEO_META'] = meta
		tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)), self.base_request)

		self.sources = [A4kSubtitlesAdapter(self.VIDEO_META)]

	def get_subtitle(self):
		"""
		Fetch subtitle source
		:return: Url to subtitle
		:rtype: str
		"""
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		#if self.VIDEO_META == None:
		#	self.VIDEO_META = json.loads(tools.read_all_text(os.path.join(tools.ADDON_USERDATA_PATH, 'curr_meta.json')))
		#	#tools.VIDEO_META = self.VIDEO_META
		#	self.base_request['VIDEO_META'] = self.VIDEO_META
		#	tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)), self.base_request)

		result = None
		sources = [A4kSubtitlesAdapter(self.VIDEO_META)]
		if sources is None:
			return None
		result_store = []
		total_result = 0
		for r in sources:
			#self.base_request['VIDEO_META'] = self.VIDEO_META
			result = r.search(self.base_request)
			if total_result > 66:
				break
			for i in result:
				i['VIDEO_META'] = self.VIDEO_META
				if not "impaired': 'true" in str(i):
					result_store.append(i)
					total_result = total_result + 1
				if total_result > 66:
					break

		download_type = self.VIDEO_META.get('download_type',False)
		#if download_type == 'movie':
		#	simple_info = tools._build_simple_movie_info(self.VIDEO_META)
		#	simple_info['imdb_id'] = self.VIDEO_META['imdb_id']
		#else:
		#	simple_info = tools._build_simple_show_info(self.VIDEO_META)

		#source_list = []
		#for i in result_store:
		#	tools.log(i['name'])
		#	if download_type == 'movie':
		#		test = source_tools.filter_movie_title(i['name'], source_tools.clean_title(i['name']), meta['title'], simple_info)
		#		if test:
		#			test = ': True'
		#	else:
		#		test = source_tools.run_show_filters(simple_info, pack_title = source_tools.clean_title(i['name']), show_title_match = True)
		#		test2 = source_tools.run_show_filters(simple_info, release_title = source_tools.clean_title(i['name']), show_title_match = True)
		#	tools.log(test, test2)

		#	if ': True' in str(test):
		#		source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': tools.get_info(i['name']), 'quality': tools.get_quality(i['name'])})
		source_list = []
		if download_type == 'movie':
			input_guess = get_guess(self.VIDEO_META['file_name'])
			for i in result_store:
				guess = get_guess(i['name'])
				if distance.jaro_similarity(input_guess.get('title',''), guess.get('title','')) > 0.92:
					source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': tools.get_info(i['name']), 'quality': tools.get_quality(i['name'])})
		else:
			input_guess = get_guess(self.VIDEO_META['file_name'])
			for i in result_store:
				guess = get_guess(i['name'])
				try: ep_test = int(guess.get('episode',0))
				except: ep_test = 0
				try: season_test = int(guess.get('season',0))
				except: season_test = 0
				i_info = tools.get_info(i['name'])
				i_quality = tools.get_quality(i['name'])
				if 'web' in str(i_info).lower():
					if i_quality != '4K' and i_quality != '1080p':
						i_quality = '720p'
				if input_guess.get('season','') == guess.get('season','') and input_guess.get('episode','') == guess.get('episode',''):
					if distance.jaro_similarity(input_guess.get('episode_title',''), guess.get('episode_title','')) > 0.92:
						source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': i_info, 'quality': i_quality})
						continue
				if input_guess.get('season','') == guess.get('season','') and input_guess.get('episode','') != guess.get('episode','') and ep_test > 0:
					if distance.jaro_similarity(input_guess.get('episode_title',''), guess.get('episode_title','')) > 0.92:
						source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': i_info, 'quality': i_quality})
						continue
				if distance.jaro_similarity(input_guess.get('episode_title',''), guess.get('episode_title','')) > 0.92:
					source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': i_info, 'quality': i_quality})
					continue
				if (ep_test == 0 or ep_test == int(self.VIDEO_META['episode'])) and guess.get('episode_title','') == '' and season_test == int(self.VIDEO_META['season_number']) and guess.get('title') != None:
					clean_guess_title = source_tools.clean_title(guess.get('title'))
					try: 
						guess_title2 = guess.get('title') + ' ' + guess.get('alternative_title')
						clean_guess_title2 = source_tools.clean_title(guess_title2)
					except: 
						guess_title2 = guess.get('title')
						clean_guess_title2 = clean_guess_title
					clean_guess_title = re.sub(r'\W+', '', clean_guess_title)
					clean_guess_title2 = re.sub(r'\W+', '', clean_guess_title2)
					match = False
					for x in self.VIDEO_META['aliases']:
						clean_alias = source_tools.clean_title(x).lower().replace(' ','')
						score = distance.jaro_similarity(guess.get('title'), x)
						score2 = distance.jaro_similarity(guess_title2 , x)
						#tools.log(score, x)
						clean_alias = re.sub(r'\W+', '', clean_alias)
						if (clean_alias == clean_guess_title.lower().replace(' ','') or score > 0.92) or (clean_alias == clean_guess_title2.lower().replace(' ','') or score2 > 0.92):
							match = True
							break
					if match == True:
						source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': i_info, 'quality': i_quality})
						continue
				elif guess.get('title') == None and ep_test == int(self.VIDEO_META['episode']) and season_test == int(self.VIDEO_META['season_number']):
					source_list.append({'pack_title': i['name'], 'release_title': i['name'], 'filename': i['name'], 'pack_size': 999, 'size': 999, 'info': i_info, 'quality': i_quality})
					continue
				#tools.log(guess)
		new_source_list = tools.SourceSorter(self.VIDEO_META).sort_sources(source_list)
		#tools.log('new_source_list',new_source_list)
		#tools.log('result_store',result_store)
		#tools.log(source_list)
		result_store2 = result_store
		result_store = []
		for x in new_source_list:
			match = False
			for i in result_store2:
				if i['name'] == x['release_title']:
					match = True
					break
			if match == True:
				result_store.append(i)

		#tools.log(result_store)
		#for i in result_store:
		#	tools.log(i['name'])
		"""
		input_guess = get_guess(self.VIDEO_META['file_name'])
		#tools.log(input_guess)
		index_scores = []
		for i in result_store:
			guess = get_guess(i['name'])
			#tools.log(guess)
			score = 0
			try: ep_test = int(guess.get('episode',0))
			except: ep_test = 0

			if input_guess.get('season','') == guess.get('season','') and input_guess.get('episode','') == guess.get('episode','') and self.VIDEO_META['is_movie'] == False:
				score = score + 2
				if guess.get('episode','') == '':
					score = score - 1
			if input_guess.get('season','') == guess.get('season','') and input_guess.get('episode','') != guess.get('episode','') and ep_test > 0 and self.VIDEO_META['is_movie'] == False:
				score = score - 2
				if distance.jaro_similarity(input_guess.get('episode_title',''), guess.get('episode_title','')) > 0.92:
					score = score + 2
				else:
					score = score - 1
			if distance.jaro_similarity(input_guess.get('episode_title',''), guess.get('episode_title','')) > 0.92 and self.VIDEO_META['is_movie'] == False:
					score = score + 2
			if distance.jaro_similarity(input_guess.get('title',''), guess.get('title','')) > 0.92:
					score = score + 1

			for x in input_guess:
				if x in ['screen_size','source','streaming_service','video_codec','release_group','audio_channels','audio_codec']:
					if guess.get(x,'') == '':
						continue
					jaro_score = distance.jaro_similarity(input_guess[x], guess.get(x,''))
					if distance.jaro_similarity(input_guess[x], guess.get(x,'')) > 0.85:
						if x == 'source':
							score = score + 2
							if guess.get('episode','') == '' and self.VIDEO_META['is_movie'] == False:
								score = score - 1
						else:
							score = score + 1
			#tools.log(i['name'],score)
			index_scores.append(score)
			#tools.log(score,i['name'])
		for idx, i in enumerate(index_scores):
			result_store[idx]['score'] = i

		result_store_sorted = sorted(result_store, key=lambda x: (x['score'],len(x['name'])), reverse=True)
		#tools.log(result_store_sorted)
		result_store = result_store_sorted
		"""
		sources = [A4kSubtitlesAdapter(self.VIDEO_META)]
		#result_store[0]['VIDEO_META'] = self.VIDEO_META
		foreign_parts = []
		normal_subs = []
		foreign_parts_flag = False
		result_foreign = None
		sub_result = None
		for i in result_store:
			if 'foreign' in str(i).lower() or 'forced' in str(i).lower() or 'non english' in str(i).lower():
				foreign_parts.append(i)
				foreign_parts_flag = True
			else:
				normal_subs.append(i)
		if foreign_parts_flag:
			shutil.rmtree(utils.temp_dir2, ignore_errors=True)
			if not os.path.exists(utils.temp_dir2):
				os.mkdir(utils.temp_dir2)
			for r in sources:
				sub_result = r.download(foreign_parts[0])
				tools.log(foreign_parts[0]['name'])
				break
			#result_foreign = os.path.splitext(sub_result)[0] + '.FOREIGN.PARTS' +os.path.splitext(sub_result)[1]
			result_foreign = os.path.splitext(sub_result)[0] + '.FORCED' +os.path.splitext(sub_result)[1]
			result_foreign = os.path.basename(result_foreign)
			result_foreign1 = os.path.join(utils.temp_dir2, result_foreign)
			result_foreign2 = os.path.join(utils.temp_dir, result_foreign)

			os.rename(sub_result, result_foreign1)
		for r in sources:
			try: 
				sub_result = r.download(normal_subs[0])
				tools.log(normal_subs[0]['name'])
			except Exception as e: 
				if 'zipfile.BadZipFile' in str(e):
					pass
			if sub_result:
				break
		if foreign_parts_flag:
			os.rename(result_foreign1, result_foreign2)
			result_foreign = result_foreign2
			shutil.rmtree(utils.temp_dir2, ignore_errors=True)

		self.VIDEO_META['SUB_FILE'] = ''
		self.VIDEO_META['SUB_FILE_FORCED'] = ''
		tools.log(sub_result)
		if sub_result:
			if os.path.exists(sub_result):
				self.VIDEO_META['SUB_FILE'] = sub_result
			else:
				self.VIDEO_META['SUB_FILE'] = ''
		if result_foreign:
			if os.path.exists(result_foreign):
				self.VIDEO_META['SUB_FILE_FORCED'] = result_foreign
			else:
				self.VIDEO_META['SUB_FILE_FORCED'] = ''
		#tools.VIDEO_META['SUB_FILE_FORCED'] = result_foreign
		tools.VIDEO_META = self.VIDEO_META
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		#tools.log('self.VIDEO_META',self.VIDEO_META,'result_foreign',result_foreign,'result',sub_result)
		tools.log('result_foreign',result_foreign,'result',sub_result)#
		if os.path.exists(utils.temp_dir2):
			shutil.rmtree(utils.temp_dir2, ignore_errors=True)
		#tools.log('normal_subs[0]', normal_subs[0])
		return sub_result


class A4kSubtitlesAdapter(object):
	"""
	Ease of use adapter for A4kSubtitles
	"""

	def __init__(self, meta):

		#path = tools.translate_path(
		#	os.path.join(g.ADDONS_PATH, "/plugin.video.seren_downloader/resources/lib/modules")
		#)
		#try:
		#	sys.path.append(path)
		#	self.service = importlib.import_module("a4kSubtitles.api").A4kSubtitlesApi(
		#		{"kodi": tools.is_stub()}
		#	)
		#	self.enabled = True
		#except ImportError:
		#	self.enabled = False

		self.VIDEO_META = meta
		self.service = api.A4kSubtitlesApi(
			{"kodi": False}
		)
		self.service.VIDEO_META = meta

		self.enabled = True

	def search(self, request, **extra):
		"""
		Search for a subtitle
		:param request: Dictionary containing currently available subtitles and the preferred language
		:type request: dict
		:param extra: Kwargs to provide video meta and settings to A4kSubtitles
		:type extra: dict
		:return: Available subtitle matches
		:rtype: list
		"""
		video_meta = extra.pop("video_meta", None)
		settings = extra.pop("settings", None)
		return self.service.search(request, video_meta=self.VIDEO_META, settings=settings)

	def download(self, request, **extra):
		"""
		Downloads requested subtitle
		:param request: Selected subtitle from search results
		:type request: dict
		:param extra: Kwargs, set settings to settings to request to use
		:type extra: dict
		:return: Path to subtitle
		:rtype: str
		"""
		settings = extra.pop("settings", None)
		return self.service.download(request, settings)
		#try:
		#	
		#except (OSError, IOError):
		#	tools.log("Unable to download subtitle, file already exists", "error")
		#except Exception as e:
		#	tools.log("Unknown error acquiring subtitle: {}".format(e), "error")
		#	#g.log_stacktrace()
