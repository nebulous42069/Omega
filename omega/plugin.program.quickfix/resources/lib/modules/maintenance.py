import os, shutil, sqlite3
import xbmc, xbmcgui
from xbmc import log
from addonvar import *

def purge_db(db):
	if os.path.exists(db):
		try:
			conn = sqlite3.connect(db)
			cur = conn.cursor()
		except Exception as e:
			log("DB Connection Error: %s" % str(e), xbmc.LOGDEBUG)
			return False
	else: 
		log('%s not found.' % db, xbmc.LOGINFO)
		return False
	cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
	for table in cur.fetchall():
		if table[0] == 'version': 
			log('Data from table `%s` skipped.' % table[0], xbmc.LOGDEBUG)
		else:
			try:
				cur.execute("DELETE FROM %s" % table[0])
				conn.commit()
				log('Data from table `%s` cleared.' % table[0], xbmc.LOGDEBUG)
			except Exception as e:
				log("DB Remove Table `%s` Error: %s" % (table[0], str(e)), xbmc.LOGERROR)
	conn.close()
	log('%s DB Purging Complete.' % db, xbmc.LOGINFO)

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
    xbmc.sleep(1000)
    xbmcgui.Dialog().ok(addon_name, str(file_count)+' packages cleared.' )
    return

def clear_thumbnails():
	try:
		if os.path.exists(os.path.join(user_path, 'Thumbnails')):
			shutil.rmtree(os.path.join(user_path, 'Thumbnails'))
	except Exception as e:
    		log('Failed to delete %s. Reason: %s' % (os.path.join(user_path, 'Thumbnails'), e), xbmc.LOGINFO)
    		return
	try:
		if os.path.exists(os.path.join(db_path, 'Textures13.db')):
			os.unlink(os.path.join(db_path, 'Textures13.db'))
	except:
		purge_db(textures_db)
	xbmc.sleep(1000)
	xbmcgui.Dialog().ok(addon_name, 'Thumbnails have been deleted. Reboot Kodi to refresh thumbs.')
	return

def advanced_settings():
	selection = xbmcgui.Dialog().select('Select the Ram Size of your device.', ['1GB (1st - 3rd gen, Lite Firestick)','1GB to 1.5GB (4k Firestick)','1.5GB to 2GB (Firebox, Cube, Sheild Tube)','2GB to 3GB RAM','3GB or more (Nvidia Shield Pro)','Delete Advanced Settings'])
	if selection==0:
		xml = os.path.join(advancedsettings_folder, 'less1.xml')
	elif selection==1:
		xml = os.path.join(advancedsettings_folder, '1plus.xml')
	elif selection==2:
		xml = os.path.join(advancedsettings_folder, 'firetv.xml')
	elif selection==3:
		xml = os.path.join(advancedsettings_folder, '2plus.xml')
	elif selection==4:
		xml = os.path.join(advancedsettings_folder,'shield.xml')
	elif selection==5:
		if os.path.exists(advancedsettings_xml):
			os.unlink(advancedsettings_xml)
		xbmc.sleep(1000)
		deleted = xbmcgui.Dialog().ok(addon_name, 'Advanced Settings have been deleted. Kodi will now close to apply the settings.')
		os._exit(1)
	else:
		return
	if os.path.exists(advancedsettings_xml):
		os.unlink(advancedsettings_xml)
	shutil.copyfile(xml, advancedsettings_xml)
	xbmc.sleep(1000)
	apply = xbmcgui.Dialog().ok(addon_name, 'Advanced Settings have been set. Kodi will now close to apply the settings.')
	os._exit(1)