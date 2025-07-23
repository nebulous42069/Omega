import sqlite3 as database
from pathlib import Path
from datetime import datetime, timedelta
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

def notification(line1, time=3000, sound=False):
	addon_info = xbmcaddon.Addon().getAddonInfo
	xbmcgui.Dialog().notification(addon_info('name'), line1, addon_info('icon'), time, sound)

def thumb_cleaner():
	current_date = datetime.date(datetime.utcnow())
	thumbs_folder = Path(xbmcvfs.translatePath('special://thumbnails'))
	dbfile = Path(xbmcvfs.translatePath('special://database')) / 'Textures13.db'
	if not dbfile.exists(): return notification('Failed')
	item_list = []
	minimum_uses = 30
	days = xbmcgui.Dialog().input(
		'Remove Thumbs Older Than (Days)...',
		defaultt=str(minimum_uses),
		type=xbmcgui.INPUT_NUMERIC
	)
	if not days: return notification('No Days Set')
	back_date = (current_date - timedelta(days=int(days))).strftime('%Y-%m-%d %H:%M:%S')
	progress_dialog = xbmcgui.DialogProgress()
	progress_dialog.create('Thumbnails Remover', '')
	progress_dialog.update(0, 'Gathering Thumbnail Info...')
	dbcon = database.connect(str(dbfile), isolation_level=None)
	dbcur = dbcon.cursor()
	dbcur.execute('''PRAGMA synchronous = OFF''')
	dbcur.execute('''PRAGMA journal_mode = OFF''')
#	dbcur.execute(
#		"SELECT idtexture FROM sizes WHERE usecount < ? AND lastusetime < ?",
#		(minimum_uses, str(back_date))
#	)
	dbcur.execute("SELECT idtexture FROM sizes WHERE lastusetime < ?", (str(back_date), ))
	result = dbcur.fetchall()
	result_length = len(result)
	if not result_length > 0: return notification('No Thumbnails to Clear')
	for count, item in enumerate(result):
		if progress_dialog.iscanceled(): break
		_id = item[0]
		dbcur.execute("SELECT cachedurl FROM texture WHERE id = ?", (_id, ))
		url = dbcur.fetchall()[0][0]
		path = thumbs_folder / url
		path.unlink(missing_ok=True)
		item_list.append((_id,))
		percent = int(count / result_length * 100)
		line = '[B]Total To Remove:[/B] %s[CR][B]Removing:[/B] %02d - %s[CR][B]Path: [/B]%s'
		line = line % (result_length, count, str(path.name), str(path.parent))
		progress_dialog.update(max(1, percent), line)
	line = 'Removing Database Entries...[CR]Please Wait...[CR]%s'
	progress_dialog.update(33, line % 'Removing Sizes IDS...')
	dbcur.executemany("DELETE FROM sizes WHERE idtexture = ?", item_list)
	progress_dialog.update(66, line % 'Removing Texture IDS...')
	dbcur.executemany("DELETE FROM texture WHERE id = ?", item_list)
	progress_dialog.update(99, line % 'Cleaning Database...')
	dbcur.execute("VACUUM")
	dbcon.commit()
	xbmc.sleep(1500)
	try: progress_dialog.close()
	except: pass
	return notification('Success')

