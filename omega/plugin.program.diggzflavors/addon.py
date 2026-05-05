# -*- coding: utf-8 -*-
#####-----XBMC Library Modules-----#####
import xbmc, xbmcplugin, xbmcaddon, xbmcgui
from xbmc import log
#####-----External Modules-----#####
import sys, os, shutil, json, base64
import xml.etree.ElementTree as ET
from urllib.parse import unquote_plus
from urllib.request import urlopen
from urllib.request import Request
from zipfile import ZipFile

#####-----Internal Modules-----#####
from addonvar import *
from resources.lib.modules.utils import addDir
from resources.lib.modules import skinSwitch

addon.setSetting('firstrun', 'true')
args = parse_qs(sys.argv[2][1:])
KODIV  = float(xbmc.getInfoLabel("System.BuildVersion")[:4])

def currSkin():
	return xbmc.getSkinDir()
def percentage(part, whole):
	return 100 * float(part)/float(whole)

try:
	if isBase64(buildfile):
		buildfile = base64.b64decode(buildfile).decode('utf8')
except:
	pass

def MainMenu():
	addDir('Diggz 22 AIO Flavors','',1,addon_icon,addon_fanart,local_string(30001),isFolder=True)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def subMenu_maintenance():
	addDir('Clear Packages','',6,addon_icon,addon_fanart,local_string(30005),isFolder=False)
	addDir('Clear Thumbnails','',7,addon_icon,addon_fanart,local_string(30008),isFolder=False)
	addDir('Advanced Settings','',8,addon_icon,addon_fanart,local_string(30009),isFolder=False)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def get_text(item, tag, default=''):
	try:
		child = item.find(tag)
		if child is not None and child.text:
			return child.text.strip()
	except:
		pass
	try:
		value = item.get(tag)
		if value:
			return value.strip()
	except:
		pass
	return default

def get_category_nodes(root):
	categories = []
	seen = set()
	for path in ('category', 'section', './categories/category', './categories/section'):
		for item in root.findall(path):
			key = id(item)
			if key not in seen:
				seen.add(key)
				categories.append(item)
	return categories

def get_category_name(category):
	return get_text(category, 'name', get_text(category, 'title', category.get('id', 'Category')))

def add_build_item(name, version, build_url, icon, fanart, description):
	version = str(version or '0')
	label = name + ' Version ' + version if version else name
	if build_url.endswith('.zip'):
		addDir(label, build_url, 3, icon, fanart, description, name2=name, version=version, isFolder=False)
	elif build_url.endswith('.xml') or build_url.endswith('.json'):
		addDir(label, build_url, 1, icon, fanart, description, name2=name, version=version, isFolder=True)
	else:
		addDir('Invalid build URL. Please contact the build creator.', '', '', '', '', '', isFolder=False)

def add_json_build(build):
	name = (build.get('name') or build.get('title') or '')
	version = (build.get('version') or '0')
	build_url = (build.get('url') or '')
	icon = (build.get('icon') or addon_icon)
	fanart = (build.get('fanart') or addon_fanart)
	description = (build.get('description') or 'No Description Available.')
	add_build_item(name, version, build_url, icon, fanart, description)

def add_xml_build(build):
	name = get_text(build, 'name', '')
	version = get_text(build, 'version', '0')
	build_url = get_text(build, 'url', '')
	icon = get_text(build, 'icon', addon_icon)
	fanart = get_text(build, 'fanart', addon_fanart)
	description = get_text(build, 'description', 'No Description Available.')
	add_build_item(name, version, build_url, icon, fanart, description)

def BuildMenu():
	source = url if url else buildfile
	req = Request(source, headers = headers)
	response = urlopen(req).read()
	try:
		text = response.decode('utf-8')
	except:
		text = response

	try:
		data = json.loads(text)
		json_categories = data.get('categories', data.get('sections', []))
		root_builds = data.get('builds', [])

		# Also allow the top-level "builds" list to contain category objects.
		for item in root_builds:
			if isinstance(item, dict) and item.get('builds'):
				json_categories.append(item)

		if section:
			for category in json_categories:
				category_key = str(category.get('id') or category.get('name') or category.get('title') or '')
				if category_key == section:
					for build in category.get('builds', []):
						add_json_build(build)
					break
		else:
			for category in json_categories:
				category_name = str(category.get('name') or category.get('title') or category.get('id') or 'Category')
				category_key = str(category.get('id') or category_name)
				category_url = str(category.get('url') or '')
				category_icon = str(category.get('icon') or addon_icon)
				category_fanart = str(category.get('fanart') or addon_fanart)
				category_description = str(category.get('description') or '')
				if category_url:
					addDir(category_name, category_url, 1, category_icon, category_fanart, category_description, isFolder=True)
				else:
					addDir(category_name, source, 1, category_icon, category_fanart, category_description, isFolder=True, section=category_key)

			for build in root_builds:
				if isinstance(build, dict) and not build.get('builds'):
					add_json_build(build)

	except:
		builds = ET.fromstring(text)
		categories = get_category_nodes(builds)

		if section:
			for category in categories:
				category_key = category.get('id', get_category_name(category))
				if category_key == section:
					for build in category.findall('build'):
						add_xml_build(build)
					break
		else:
			for category in categories:
				category_name = get_category_name(category)
				category_key = category.get('id', category_name)
				category_url = get_text(category, 'url', '')
				category_icon = get_text(category, 'icon', addon_icon)
				category_fanart = get_text(category, 'fanart', addon_fanart)
				category_description = get_text(category, 'description', '')
				if category_url and len(category.findall('build')) == 0:
					addDir(category_name, category_url, 1, category_icon, category_fanart, category_description, isFolder=True)
				else:
					addDir(category_name, source, 1, category_icon, category_fanart, category_description, isFolder=True, section=category_key)

			# Keep old single-list XML files working. Root-level builds appear below categories.
			for build in builds.findall('build'):
				add_xml_build(build)

	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def save_check():
	if setting('savefavs')=='true':
		EXCLUDES.append('favourites.xml')
	if setting('savesources')=='true':
		EXCLUDES.append('sources.xml')
	if setting('savedebrid')=='true':
		EXCLUDES.append('script.module.resolveurl')
	if setting('saveadvanced')=='true':
		EXCLUDES.append('advancedsettings.xml')
	return EXCLUDES

def save_move1():
	if os.path.exists(os.path.join(user_path, addon_id)):
		shutil.move(os.path.join(user_path, addon_id), os.path.join(packages, addon_id))
	if os.path.exists(os.path.join(user_path,'favourites.xml')):
		shutil.move(os.path.join(user_path, 'favourites.xml'), os.path.join(packages, 'favourites.xml'))
	if os.path.exists(os.path.join(user_path,'sources.xml')):
		shutil.move(os.path.join(user_path, 'sources.xml'), os.path.join(packages, 'sources.xml'))
	if os.path.exists(os.path.join(data_path,'script.module.resolveurl')):
		shutil.move(os.path.join(data_path, 'script.module.resolveurl'), os.path.join(packages, 'script.module.resolveurl'))
	if os.path.exists(os.path.join(user_path,'advancedsettings.xml')):
		shutil.move(os.path.join(user_path, 'advancedsettings.xml'), os.path.join(packages, 'advancedsettings.xml'))

def save_move2():
	if os.path.exists(os.path.join(packages,addon_id)):
		if os.path.exists(os.path.join(user_path, addon_id)):
			os.remove(os.path.join(user_path, addon_id))
		shutil.move(os.path.join(packages, addon_id), os.path.join(user_path, addon_id))
	
	if os.path.exists(os.path.join(packages,'favourites.xml')):
		if os.path.exists(os.path.join(user_path, 'favourites.xml')):
			os.remove(os.path.join(user_path, 'favourites.xml'))
		shutil.move(os.path.join(packages, 'favourites.xml'), os.path.join(user_path, 'favourites.xml'))
		
	if os.path.exists(os.path.join(packages,'sources.xml')):
		if os.path.exists(os.path.join(user_path, 'sources.xml')):
			os.remove(os.path.join(user_path, 'sources.xml'))
		shutil.move(os.path.join(packages, 'sources.xml'), os.path.join(user_path, 'sources.xml'))
	
	if os.path.exists(os.path.join(packages,'script.module.resolveurl')):
		if os.path.exists(os.path.join(data_path, 'script.module.resolveurl')):
			shutil.rmtree(os.path.join(data_path, 'script.module.resolveurl'))
		shutil.move(os.path.join(packages, 'script.module.resolveurl'), os.path.join(data_path, 'script.module.resolveurl'))
	shutil.rmtree(packages)
	
	if os.path.exists(os.path.join(packages,'advancedsettings.xml')):
		if os.path.exists(os.path.join(user_path, 'advancedsettings.xml')):
			os.remove(os.path.join(user_path, 'advancedsettings.xml'))
		shutil.move(os.path.join(packages, 'advancedsettings.xml'), os.path.join(user_path, 'advancedsettings.xml'))
	
def main(NAME, NAME2, VERSION, URL, ICON, FANART, DESCRIPTION):
	
	yesInstall = dialog.yesno(NAME, 'Can You Smell What The Chef Is Cooking?  Open Wide And Give This A Taste..', nolabel='Cancel', yeslabel='Continue')
	if yesInstall:  	
	    buildInstall(NAME, NAME2, VERSION, URL)
	else:
		return

def freshStart():
	yesFresh = dialog.yesno('Fresh Start', 'Are you sure you wish to clear all data?  This action cannot be undone.', nolabel='No', yeslabel='Fresh Start')
	if yesFresh:
		
		#Skin Switch
		if not currSkin() in ['skin.estuary']:
			skinSwitch.swapSkins('skin.estuary')
			x = 0
			xbmc.sleep(1000)
			while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 150:
				x += 1
				xbmc.sleep(200)
				xbmc.executebuiltin('SendAction(Select)')
			if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
				xbmc.executebuiltin('SendClick(11)')
			else: 
				log('Fresh Install: Skin Swap Timed Out!', xbmc.LOGINFO)
				return False
			xbmc.sleep(1000)
		if not currSkin() in ['skin.estuary']:
			log('Fresh Install: Skin Swap failed.', xbmc.LOGINFO)
			return
		
		if mode==4:
			save_check()
			save_move1()
			
		dp.create(addon_name, 'Deleting files and folders...')
		xbmc.sleep(1000)
		dp.update(30, 'Deleting files and folders...')
		xbmc.sleep(1000)
		for root, dirs, files in os.walk(xbmcPath, topdown=True):
			dirs[:] = [d for d in dirs if d not in EXCLUDES]
			for name in files:
				if name not in EXCLUDES:
					try:
						os.remove(os.path.join(root, name))
					except:
						log('Unable to delete ' + name, xbmc.LOGINFO)
		dp.update(60, 'Deleting files and folders...')
		xbmc.sleep(1000)	
		for root, dirs, files in os.walk(xbmcPath,topdown=True):
			dirs[:] = [d for d in dirs if d not in EXCLUDES]
			for name in dirs:
				if name not in ["Database","userdata","temp","addons","packages","addon_data"]:
					try:
						shutil.rmtree(os.path.join(root,name),ignore_errors=True, onerror=None)
					except:
						log('Unable to delete ' + name, xbmc.LOGINFO)
		dp.update(60, 'Deleting files and folders...')
		xbmc.sleep(1000)
		if not os.path.exists(packages):
			os.mkdir(packages)
		dp.update(100, 'Deleting files and folders...done')
		xbmc.sleep(2000)
		if mode == 4:
			save_move2()
			addon.setSetting('firstrun', 'true')
			addon.setSetting('buildname', 'No Build Installed')
			addon.setSetting('buildversion', '0')
			dialog.ok(addon_name, 'Fresh Start Complete. Click OK to Force Close Kodi.')
			os._exit(1)
	else:
		return

def buildInstall(NAME, NAME2, VERSION, URL):
	zippath = os.path.join(packages + "tempfile.zip")
	if os.path.exists(zippath):
		os.unlink(zippath)
	tempzip = open(zippath, 'wb')
	response = Request(URL, headers = headers)
	zipresp = urlopen(response)
	length = zipresp.getheader('content-length')
	if length:
		length2 = int(int(length)/1000000)
	else:
		length2 = 'Unknown Size'
	dp.create(NAME + ' - ' + str(length2) + ' MB', 'Switching Flavors...')
	dp.update(0, 'Switching Flavors...')
	#
	if length:
		blocksize = max(int(length)/512, 1000000)
		size = 0
		while True:
			buf = zipresp.read(blocksize)
			if not buf:
				break
			size += len(buf)
			size2 = int(size/1000000)
			percentage = int(int(size)/int(length)*100) 
			tempzip.write(buf)
			dp.update(percentage, 'Switching Flavors...' + '\n' + str(size2) + '/' + str(length2) + 'MB')
				
	else:
		dp.update(50, 'Switching Flavors...')
		tempzip.write(zipresp.read())
	if length:
		dp.update(100, 'Switching Flavors...Done!' + '\n' + str(size2) + '/' + str(length2) + 'MB')
	else:
		dp.update(100, 'Switching Flavors...Done!')
	xbmc.sleep(1000)      
	tempzip.close()
	dp.update(66, 'Extracting files...')
	xbmc.sleep(1000)
	zf = ZipFile(zippath)
	zf.extractall(path = home)
	dp.update(100, 'Extracting files...Done!')
	xbmc.sleep(2000)
	zf.close()
	os.unlink(zippath)
	save_move2()
	addon.setSetting('buildname', NAME2)
	addon.setSetting('buildversion', VERSION)
	addon.setSetting('firstrun', 'true')
	dialog.ok(addon_name, 'Update Is Complete. Click OK to Force Close Kodi.')
	os._exit(1)

def clear_packages():
    file_count = len([name for name in os.listdir(packages)])
    for filename in os.listdir(packages):
    	file_path = os.path.join(packages, filename)
    	try:
    	       if os.path.isfile(file_path) or os.path.islink(file_path):
    	       	os.unlink(file_path)
    	       elif os.path.isdir(file_path):
    	       	shutil.rmtree(file_path)
    	except Exception as e:
    		log('Failed to delete %s. Reason: %s' % (file_path, e), xbmc.LOGINFO)
    xbmcgui.Dialog().ok(addon_name, str(file_count)+' packages cleared.' )
	
def GetParams():
	param=[]
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=', 1)
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]
	return param

params=GetParams()
url=None
name=None
name2=None
version=None
mode=None
iconimage=None
fanart=None
description=None
section=None
log(str(params),xbmc.LOGDEBUG)

try:
	url=unquote_plus(params["url"])
except:
	pass
try:
	name=unquote_plus(params["name"])
except:
	pass
try:
	iconimage=unquote_plus(params.get("iconimage", params.get("icon", "")))
except:
	pass
try:        
	mode=int(params["mode"])
except:
	pass
try:        
	fanart=unquote_plus(params["fanart"])
except:
	pass
try:
    description=unquote_plus(params["description"])
except:
	pass
try:
	name2 =unquote_plus(params["name2"])
except:
	pass
try:
	version =unquote_plus(params["version"])
except:
	pass
try:
	section =unquote_plus(params["section"])
except:
	pass

'''
modes for support script 
'''
xbmc.executebuiltin('Dialog.Close(busydialog)')

if mode==None:
	MainMenu()
	
elif mode==1:
	BuildMenu()

elif mode==3:
	main(name, name2, version, url, iconimage, fanart, description)

elif mode==4:
	freshStart()

elif mode==5:
	subMenu_maintenance()
	
elif mode==6:
	from resources.lib.modules import maintenance
	maintenance.clear_packages()
	
elif mode==7:
	from resources.lib.modules import maintenance
	maintenance.clear_thumbnails()

elif mode==8:
	from resources.lib.modules import maintenance
	maintenance.advanced_settings()
	
elif mode==9:
	xbmcaddon.Addon(addon_id).openSettings()

elif mode==100:
	from resources.lib.GUIcontrol import notify
	d=notify.notify()
	d.doModal()
	del d
	
xbmcplugin.endOfDirectory(int(sys.argv[1]))