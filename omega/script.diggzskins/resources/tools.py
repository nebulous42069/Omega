import xbmc, xbmcvfs, xbmcaddon, xbmcgui, xbmcplugin,os,sys,random,urllib.request,urllib.error,urllib.parse,urllib.request,urllib.parse,urllib.error,glob,re,zipfile
from resources import downloader,extract
from datetime import date, datetime, timedelta
try:    from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

ADDON_ID       = 'script.diggzskins'
fanart         = xbmcvfs.translatePath(os.path.join('special://home/addons/' + ADDON_ID , 'fanart.jpg'))
icon           = xbmcvfs.translatePath(os.path.join('special://home/addons/' + ADDON_ID, 'icon.png'))
HOME             = xbmcvfs.translatePath('special://home/')
LOG              = xbmcvfs.translatePath('special://logpath/')
PROFILE          = xbmcvfs.translatePath('special://profile/')
TEMPDIR          = xbmcvfs.translatePath('special://temp')
ADDONS           = os.path.join(HOME,      'addons')
USERDATA         = os.path.join(HOME,      'userdata')
PLUGIN           = os.path.join(ADDONS,    ADDON_ID)
PACKAGES         = os.path.join(ADDONS,    'packages')
DATABASE       = os.path.join(USERDATA,  'Database')
DIALOG           = xbmcgui.Dialog()
DP               = xbmcgui.DialogProgress()
KODIV            = float(xbmc.getInfoLabel("System.BuildVersion")[:4])


def installFromKodi(skin, over=True):
	if over == True:
		xbmc.sleep(2000)
	xbmc.executebuiltin('RunPlugin(plugin://%s)' % plugin)
	if not whileWindow('yesnodialog'):
		return False
	xbmc.sleep(500)
	if whileWindow('okdialog'):
		return False
	whileWindow('progressdialog')
	if os.path.exists(os.path.join(ADDONS, plugin)): return True
	else: return False
	
def whileWindow(window, active=False, count=0, counter=15):
	windowopen = getCond('Window.IsActive(%s)' % window)
	while not windowopen and count < counter:
		windowopen = getCond('Window.IsActive(%s)' % window)
		count += 1
		xbmc.sleep(500)
	while windowopen:
		active = True
		windowopen = getCond('Window.IsActive(%s)' % window)
		xbmc.sleep(250)
	return active
	
def installAddon(name, url):
	DP.create('Diggz Skins','[B]Downloading:[/B] %s' % name, '', '[COLOR red]Please Wait[/COLOR]')
	urlsplits = url.split('/')
	lib=os.path.join(PACKAGES, urlsplits[-1])
	try: os.remove(lib)
	except: pass
	downloader.download(url, lib, DP)
	title = '[B]Installing:[/B]] %s' % (name)
	DP.update(0, title,'', 'Please Wait')
	percent, errors, error = extract.all(lib,ADDONS,DP, title=title)
	DP.update(0, title,'', 'Installing Dependencies')
	installed(name)
	installlist = grabAddons(lib)
	if KODIV >= 17: addonDatabase(installlist, 1, True)
	installDep(name, DP)
	DP.close()
	xbmc.executebuiltin('UpdateAddonRepos()')
	xbmc.executebuiltin('UpdateLocalAddons()')
	
def installed(addon):
    url = os.path.join(ADDONS,addon,'addon.xml')
    if os.path.exists(url):
        try:
            list  = open(url,mode='r'); g = list.read(); list.close()
            name = wiz.parseDOM(g, 'addon', ret='name', attrs = {'id': addon})
            icon  = os.path.join(ADDONS,addon,'icon.png')
        except: pass

def grabAddons(path):
    zfile = zipfile.ZipFile(path)
    addonlist = []
    for item in zfile.infolist():
        if str(item.filename).find('addon.xml') == -1: continue
        info = str(item.filename).split('/')
        if not info[-2] in addonlist:
            addonlist.append(info[-2])
    return addonlist
	
def installDep(name, DP=None):
	dep=os.path.join(ADDONS,name,'addon.xml')
	if os.path.exists(dep):
		source = open(dep,mode='r'); link = source.read(); source.close();
		match  = parseDOM(link, 'import', ret='addon')
		for depends in match:
			if not 'xbmc.python' in depends:
				if not DP == None:
					DP.update(0, '', '%s' % depends)
				try:
					add   = xbmcaddon.Addon(id=depends)
					name2 = add.getAddonInfo('name')
				except:
					createTemp(depends)
					if KODIV >= 17: addonDatabase(depends, 1)
					
def createTemp(plugin):
	temp   = os.path.join(PLUGIN, 'resources', 'tempaddon.xml')
	f      = open(temp, 'r'); r = f.read(); f.close()
	plugdir = os.path.join(ADDONS, plugin)
	if not os.path.exists(plugdir): os.makedirs(plugdir)
	a = open(os.path.join(plugdir, 'addon.xml'), 'w')
	a.write(r.replace('testid', plugin).replace('testversion', '0.0.1'))
	a.close()
					
def openURL(url):
	req = urllib.request.Request(url)
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0')
	response = urllib.request.urlopen(req)
	link=response.read()
	response.close()
	return link

def addonDatabase(addon=None, state=1, array=False):
	dbfile = latestDB('Addons')
	dbfile = os.path.join(DATABASE, dbfile)
	installedtime = str(datetime.now())[:-7]
	if os.path.exists(dbfile):
		try:
			textdb = database.connect(dbfile)
			textexe = textdb.cursor()
		except Exception as e:
			log("DB Connection Error: %s" % str(e), xbmc.LOGERROR)
			return False
	else: return False
	if state == 2:
		try:
			textexe.execute("DELETE FROM installed WHERE addonID = ?", (addon,))
			textdb.commit()
			textexe.close()
		except Exception as e:
			log("Error Removing %s from DB" % addon)
		return True
	try:
		if array == False:
			textexe.execute('INSERT or IGNORE into installed (addonID , enabled, installDate) VALUES (?,?,?)', (addon, state, installedtime,))
			textexe.execute('UPDATE installed SET enabled = ? WHERE addonID = ? ', (state, addon,))
		else:
			for item in addon:
				textexe.execute('INSERT or IGNORE into installed (addonID , enabled, installDate) VALUES (?,?,?)', (item, state, installedtime,))
				textexe.execute('UPDATE installed SET enabled = ? WHERE addonID = ? ', (state, item,))
		textdb.commit()
		textexe.close()
	except Exception as e:
		log("Erroring enabling addon: %s" % addon)

def latestDB(DB):
	if DB in ['Addons', 'ADSP', 'Epg', 'MyMusic', 'MyVideos', 'Textures', 'TV', 'ViewModes']:
		match = glob.glob(os.path.join(DATABASE,'%s*.db' % DB))
		comp = '%s(.+?).db' % DB[1:]
		highest = 0
		for file in match :
			try: check = int(re.compile(comp).findall(file)[0])
			except: check = 0
			if highest < check :
				highest = check
		return '%s%s.db' % (DB, highest)
	else: return False
	
def parseDOM(html, name="", attrs={}, ret=False):
	# Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

	if isinstance(html, str):
		try:
			html = [html.decode("utf-8")]
		except:
			html = [html]
	elif isinstance(html, str):
		html = [html]
	elif not isinstance(html, list):
		return ""

	if not name.strip():
		return ""

	ret_lst = []
	for item in html:
		temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
		for match in temp_item:
			item = item.replace(match, match.replace("\n", " "))

		lst = []
		for key in attrs:
			lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
			if len(lst2) == 0 and attrs[key].find(" ") == -1:
				lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)

			if len(lst) == 0:
				lst = lst2
				lst2 = []
			else:
				test = list(range(len(lst)))
				test.reverse()
				for i in test:
					if not lst[i] in lst2:
						del(lst[i])

		if len(lst) == 0 and attrs == {}:
			lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
			if len(lst) == 0:
				lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

		if isinstance(ret, str):
			lst2 = []
			for match in lst:
				attr_lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
				if len(attr_lst) == 0:
					attr_lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
				for tmp in attr_lst:
					cont_char = tmp[0]
					if cont_char in "'\"":
						if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
							tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

						if tmp.rfind(cont_char, 1) > -1:
							tmp = tmp[1:tmp.rfind(cont_char)]
					else:
						if tmp.find(" ") > 0:
							tmp = tmp[:tmp.find(" ")]
						elif tmp.find("/") > 0:
							tmp = tmp[:tmp.find("/")]
						elif tmp.find(">") > 0:
							tmp = tmp[:tmp.find(">")]

					lst2.append(tmp.strip())
			lst = lst2
		else:
			lst2 = []
			for match in lst:
				endstr = "</" + name

				start = item.find(match)
				end = item.find(endstr, start)
				pos = item.find("<" + name, start + 1 )

				while pos < end and pos != -1:
					tend = item.find(endstr, end + len(endstr))
					if tend != -1:
						end = tend
					pos = item.find("<" + name, pos + 1)

				if start == -1 and end == -1:
					temp = ""
				elif start > -1 and end > -1:
					temp = item[start + len(match):end]
				elif end > -1:
					temp = item[:end]
				elif start > -1:
					temp = item[start + len(match):]

				if ret:
					endstr = item[end:item.find(">", item.find(endstr)) + 1]
					temp = match + temp + endstr

				item = item[item.find(temp, item.find(match)) + len(temp):]
				lst2.append(temp)
			lst = lst2
		ret_lst += lst

	return ret_lst