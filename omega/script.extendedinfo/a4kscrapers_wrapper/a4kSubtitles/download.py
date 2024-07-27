# -*- coding: utf-8 -*-
#from resources.lib.modules.globals import g
try:
	import tools
except:
	from a4kscrapers_wrapper import tools
import os
from inspect import currentframe, getframeinfo
#print(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))

def __download(core, filepath, request):
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log(filepath)
	request['stream'] = True

	with core.request.execute(core, request) as r:
		with open(filepath, 'wb') as f:
			core.shutil.copyfileobj(r.raw, f)
	return filepath

def __extract_gzip(core, archivepath, filename):
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	filepath = core.os.path.join(core.utils.temp_dir, filename)

	if core.utils.py2:
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		with open(archivepath, 'rb') as f:
			gzip_file = f.read()

		with core.gzip.GzipFile(fileobj=core.utils.StringIO(gzip_file)) as gzip:
			#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
			with open(filepath, 'wb') as f:
				f.write(gzip.read())
				f.flush()
	else:
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		with core.gzip.open(archivepath, 'rb') as f_in:
			with open(filepath, 'wb') as f_out:
				core.shutil.copyfileobj(f_in, f_out)

	return filepath

def __extract_zip(core, archivepath, filename, episodeid):
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	sub_exts = ['.srt', '.sub']
	sub_exts_secondary = ['.smi', '.ssa', '.aqt', '.jss', '.ass', '.rt', '.txt']

	try:
		using_libvfs = False
		with open(archivepath, 'rb') as f:
			zipfile = core.zipfile.ZipFile(core.BytesIO(f.read()))
		namelist = core.utils.get_zipfile_namelist(zipfile)
	except:
		using_libvfs = True
		archivepath_ = core.utils.quote_plus(archivepath)
		(dirs, files) = core.kodi.xbmcvfs.listdir('archive://%s' % archivepath_)
		namelist = [file.decode(core.utils.default_encoding) if core.utils.py2 else file for file in files]

	subfile = core.utils.find_file_in_archive(core, namelist, sub_exts, episodeid)
	if not subfile:
		subfile = core.utils.find_file_in_archive(core, namelist, sub_exts_secondary, episodeid)

	dest = core.os.path.join(core.utils.temp_dir, filename)
	if not subfile:
		try:
			return __extract_gzip(core, archivepath, filename)
		except:
			try: core.os.remove(dest)
			except: pass
			try: core.os.rename(archivepath, dest)
			except: pass
			return dest

	if not using_libvfs:
		src = core.utils.extract_zipfile_member(zipfile, subfile, core.utils.temp_dir)
		try: core.os.remove(dest)
		except: pass
		try: core.os.rename(src, dest)
		except: pass
	else:
		src = 'archive://' + archivepath_ + '/' + subfile
		core.kodi.xbmcvfs.copy(src, dest)

	return dest

def __insert_lang_code_in_filename(core, filename, lang_code):
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	filename_chunks = core.utils.strip_non_ascii_and_unprintable(filename).split('.')
	filename_chunks.insert(-1, lang_code)
	return '.'.join(filename_chunks)

def __postprocess(core, filepath, lang_code):
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	try:
	#if 1==1:
		with open(filepath, 'rb') as f:
			text_bytes = f.read()

		if core.kodi.get_bool_setting('general.use_chardet'):
			encoding = ''
			if core.utils.py3:
				detection = core.utils.chardet.detect(text_bytes)
				#detected_lang_code = core.kodi.xbmc.convertLanguage(detection['language'], core.kodi.xbmc.ISO_639_2)
				detected_lang_code = core.utils.get_lang_id(detection['language'], core.kodi.xbmc.ISO_639_2)
				if detection['confidence'] == 1.0 or detected_lang_code == lang_code:
					encoding = detection['encoding']

			if not encoding:
				encoding = core.utils.code_pages.get(lang_code, core.utils.default_encoding)

			text = text_bytes.decode(encoding)
		else:
			text = text_bytes.decode(core.utils.default_encoding)

		try:
			if all(ch in text for ch in core.utils.cp1251_garbled):
				text = text.encode(core.utils.base_encoding).decode('cp1251')
			elif all(ch in text for ch in core.utils.koi8r_garbled):
				try:
					text = text.encode(core.utils.base_encoding).decode('koi8-r')
				except:
					text = text.encode(core.utils.base_encoding).decode('koi8-u')
		except: pass

		try:
			clean_text = core.utils.cleanup_subtitles(core, text)
			if len(clean_text) > len(text) / 2:
				text = clean_text
		except: pass

		with open(filepath, 'wb') as f:
			f.write(text.encode(core.utils.default_encoding))
	except: pass

def download(core, params):
	#core.logger.debug(lambda: core.json.dumps(params, indent=2))
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))

	try: new_VIDEO_META = core.utils.DictAsObject(params.get('VIDEO_META'))
	except: new_VIDEO_META = None
	if new_VIDEO_META:
		tools.VIDEO_META = new_VIDEO_META

	core.shutil.rmtree(core.utils.temp_dir, ignore_errors=True)
	if not os.path.exists(core.utils.temp_dir):
		os.mkdir(core.utils.temp_dir)
	#core.kodi.xbmcvfs.mkdirs(core.utils.temp_dir)

	actions_args = params['action_args']
	#lang_code = core.kodi.xbmc.convertLanguage(actions_args['lang'], core.kodi.xbmc.ISO_639_2)
	#filename = __insert_lang_code_in_filename(core, actions_args['filename'], lang_code)
	lang_code = core.utils.get_lang_id(actions_args['lang'], core.kodi.xbmc.ISO_639_2)
	#tools.log(lang_code)
	filename = __insert_lang_code_in_filename(core, tools.VIDEO_META['subs_filename'], lang_code)

	sub_ext = '.' + params['name'].split('.')[-1]
	sub_exts = ['.sub', '.smi', '.ssa', '.aqt', '.jss', '.ass', '.rt', '.txt']
	sub_ext_checked = None
	for i in sub_exts:
		if sub_ext == i:
			sub_ext_checked = i
			break

	if sub_ext_checked:
		filename = filename.replace('.srt',sub_ext_checked)
	if actions_args.get('gzip', False):
		archivepath = core.os.path.join(core.utils.temp_dir, 'sub.gzip')
	else:
		archivepath = core.os.path.join(core.utils.temp_dir, 'sub.zip')

	service_name = params['service_name']
	service = core.services[service_name]
	request = service.build_download_request(core, service_name, actions_args)
	#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
	#tools.log(request)

	
	if actions_args.get('raw', False):
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		filepath = core.os.path.join(core.utils.temp_dir, filename)
		download_filepath = __download(core, filepath, request)
	else:
		#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
		download_filepath = __download(core, archivepath, request)
		
		if actions_args.get('gzip', False) or 'gzip' in download_filepath:
			tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
			filepath = __extract_gzip(core, archivepath, filename)
		else:
			tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))
			episodeid = actions_args.get('episodeid', '')
			filepath = __extract_zip(core, archivepath, filename, episodeid)

	__postprocess(core, filepath, lang_code)

	tools.SUB_FILE = filepath
	if core.api_mode_enabled:
		return filepath

	listitem = core.kodi.xbmcgui.ListItem(label=filepath, offscreen=True)
	core.kodi.xbmcplugin.addDirectoryItem(handle=core.handle, url=filepath, listitem=listitem, isFolder=False)
