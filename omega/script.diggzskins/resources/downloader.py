import xbmc, xbmcgui, urllib.request, urllib.parse, urllib.error, sys, time

COLOR1         = 'white'
COLOR2         = 'white'

urllib.request.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'

def download(url, dest, dp = None):
	if not dp:
		dp = xbmcgui.DialogProgress()
		dp.create('Diggz Skins' ,"Downloading Content",' ', ' ')
	dp.update(0)
	start_time=time.time()
	urllib.request.urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time))

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
	try: 
		percent = min(numblocks * blocksize * 100 / filesize, 100) 
		currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
		kbps_speed = numblocks * blocksize / (time.time() - start_time) 
		if kbps_speed > 0 and not percent == 100: 
			eta = (filesize - numblocks * blocksize) / kbps_speed 
		else: 
			eta = 0
		kbps_speed = kbps_speed / 1024 
		type_speed = 'KB'
		if kbps_speed >= 1024:
			kbps_speed = kbps_speed / 1024 
			type_speed = 'MB'
		total = float(filesize) / (1024 * 1024) 
		mbs = '[COLOR %s][B]Size:[/B] [COLOR %s]%.02f[/COLOR] MB of [COLOR %s]%.02f[/COLOR] MB[/COLOR]' % (COLOR2, COLOR1, currently_downloaded, COLOR1, total) 
		e   = '[COLOR %s][B]Speed:[/B] [COLOR %s]%.02f [/COLOR]%s/s ' % (COLOR2, COLOR1, kbps_speed, type_speed)
		e  += '[B]ETA:[/B] [COLOR '+COLOR1+']%02d:%02d[/COLOR][/COLOR]' % divmod(eta, 60)
		dp.update(percent, '', mbs, e)
	except Exception as e:
		return str(e)
	if dp.iscanceled(): 
		dp.close()
		sys.exit()
