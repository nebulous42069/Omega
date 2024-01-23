import xbmcaddon, xbmc, sys, os, time

COLOR1         = 'white'
COLOR2         = 'white'

KODIV            = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
if KODIV > 17:
	from . import zfile as zipfile
else:
	import zipfile

def all(_in, _out, dp=None, ignore=None, title=None):
	if dp: return allWithProgress(_in, _out, dp, ignore, title)
	else: return allNoProgress(_in, _out, ignore)

def allNoProgress(_in, _out, ignore):
	try:
		zin = zipfile.ZipFile(_in, 'r')
		zin.extractall(_out)
	except Exception as e:
		wiz.log(str(e))
		return False
	return True

def allWithProgress(_in, _out, dp, ignore, title):
	count = 0; errors = 0; error = ''; update = 0; size = 0; excludes = []
	try:
		zin = zipfile.ZipFile(_in,  'r')
	except Exception as e:
		errors += 1; error += '%s\n' % e
		return update, errors, error
	nFiles = float(len(zin.namelist()))
	zipsize = convertSize(sum([item.file_size for item in zin.infolist()]))

	zipit = str(_in).replace('\\', '/').split('/')
	title = title if not title == None else zipit[-1].replace('.zip', '')

	for item in zin.infolist():
		try:
			str(item.filename).encode('ascii')
		except UnicodeDecodeError:
			continue
		count += 1; prog = int(count / nFiles * 100); size += item.file_size
		file = str(item.filename).split('/')
		line1  = '%s [B][Errors:%s][/B]' % (title, errors)
		line2  = '[B]File:[/B]%s/%s ' % (count, int(nFiles))
		line2 += '[B]Size:[/B] %s/%s' % (convertSize(size), zipsize)
		line3  = '%s' % item.filename
		try:
			zin.extract(item, _out)
		except Exception as e:
			pass
		dp.update(prog, line1, line2, line3)
		if dp.iscanceled(): break
	if dp.iscanceled():
		dp.close()
		sys.exit()
	return prog, errors, error

def convertSize(num, suffix='B'):
	for unit in ['', 'K', 'M', 'G']:
		if abs(num) < 1024.0:
			return "%3.02f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.02f %s%s" % (num, 'G', suffix)