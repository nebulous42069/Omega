
import xbmc, xbmcvfs, xbmcaddon, xbmcgui, xbmcplugin,os,sys,random,urllib.request,urllib.error,urllib.parse,glob,re
from resources import tools

ADDON_ID       = 'script.diggzskins'
fanart         = xbmcvfs.translatePath(os.path.join('special://home/addons/' + ADDON_ID , 'fanart.jpg'))
icon           = xbmcvfs.translatePath(os.path.join('special://home/addons/' + ADDON_ID, 'icon.png'))
HOME           = xbmcvfs.translatePath('special://home/')
ADDONS         = os.path.join(HOME,      'addons')
USERDATA       = os.path.join(HOME,      'userdata')
ADDOND         = os.path.join(USERDATA,  'addon_data')
DIALOG         = xbmcgui.Dialog()
KODIV            = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
repositoryurl = 'https://diggz1.me/Repo/_repo//'
repositoryxml = 'https://diggz1.me/Repo/_repo/addons.xml'

#### Icons Kodi 17 Style #################
eminence            = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.eminence.2.mod/icon.png'))
fentastic            = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.eminence.2.fen/icon.png'))
shadowriffic            = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.eminence.2.shadow/icon.png'))

#### Icons Kodi 18 Style #########
mtv          = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.mtv/resources/icon.png'))
home        = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.home/resources/icon.png'))
live         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.live/resources/icon.png'))
sports          = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.sports/resources/icon.png'))
music        = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.music/resources/icon.png'))
debrid         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.debrid/resources/icon.png'))
xenon         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.xenon19ss/resources/icon.png'))
portal         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.portal/resources/icon.png'))
amber         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.amber/resources/icon.png'))
livetvsports         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.estuary.modv2/resources/icon.png'))
ultra         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.xenonultra/resources/icon.png'))
disparity         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.disparity/resources/icon.png'))
xenonx         = xbmcvfs.translatePath(os.path.join('special://home/addons/skin.xenonx/resources/icon.png'))


def MainMenu():
	addItem('Current Skin -- %s' % currSkin(),'url','',icon,fanart,'')
	addItem('**Click here to Switch skin** ','url',1,icon,fanart,'')

		
		
	
#Example how to add more Skins
#addItem('Skin Name','url',5,icon,fanart,'') The number will be the mode at the bottom
#addItem('Skin Name','url',6,icon,fanart,'') The number will be the mode at the bottom

def skinWIN():
	idle()
	fold = glob.glob(os.path.join(ADDONS, 'skin*'))
	name = []; addonids = []
	for folder in sorted(fold, key = lambda x: x):
		foldername = os.path.split(folder[:-1])[1]
		xml = os.path.join(folder, 'addon.xml')
		if os.path.exists(xml):
			xbmc.log('xml = ' + str(xml), xbmc.LOGINFO)
			f      = open(xml, encoding = 'utf-8')
			a      = f.read()
			match  = tools.parseDOM(a, 'addon', ret='id')
			addid  = foldername if len(match) == 0 else match[0]
			try: 
				add = xbmcaddon.Addon(id=addid)
				name.append(add.getAddonInfo('name'))
				addonids.append(addid)
			except:
				pass
	selected = []; choice = 0
	skin = ["Current Skin -- %s" % currSkin()] + name
	choice = DIALOG.select("Choose a skin below.", skin)
	if choice == -1: return
	else: 
		choice1 = (choice-1)
		selected.append(choice1)
		skin[choice] = "%s" % ( name[choice1])
	if selected == None: return
	for addon in selected:
		swapSkins(name,addonids[addon])

def currSkin():
	skiname = xbmc.getSkinDir('Container.PluginName')
	skiname = xbmcaddon.Addon(skiname).getAddonInfo('name')
	return skiname

def swapSkins(name,skin, title="Error"):
	if not xbmc.getCondVisibility('System.HasAddon('+skin+')'):
		Skin_install(name,skin)
	else:
		old = 'lookandfeel.skin'
		value = skin
		current = getOld(old)
		new = old
		setNew(new, value)
		x = 0
		while not xbmc.getCondVisibility("Window.isVisible(yesnodialog)") and x < 100:
			x += 1
			xbmc.sleep(100)
		if xbmc.getCondVisibility("Window.isVisible(yesnodialog)"):
			xbmc.executebuiltin('SendClick(11)')
		sys.exit(0)

def getOld(old):
	try:
		old = '"%s"' % old 
		query = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue","params":{"setting":%s}, "id":1}' % (old)
		response = xbmc.executeJSONRPC(query)
		response = simplejson.loads(response)
		if 'result' in response:
			if 'value' in response['result']:
				return response ['result']['value'] 
	except:
		pass
	return None

def setNew(new, value):
	try:
		new = '"%s"' % new
		value = '"%s"' % value
		query = '{"jsonrpc":"2.0", "method":"Settings.SetSettingValue","params":{"setting":%s,"value":%s}, "id":1}' % (new, value)
		response = xbmc.executeJSONRPC(query)
	except:
		pass
	return None

def idle():
	return xbmc.executebuiltin('Dialog.Close(busydialog)')

def addItem(name, url, mode, iconimage, fanart, description=None):
	if description == None: description = ''
	description = '[COLOR white]' + description + '[/COLOR]'
	u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&iconimage="+urllib.parse.quote_plus(iconimage)+"&fanart="+urllib.parse.quote_plus(fanart)
	ok=True
	liz=xbmcgui.ListItem(name)
	liz.setArt({'icon': iconimage, 'thumb': iconimage, 'fanart': fanart}) 
	liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": description } )
	liz.setProperty( "fanart_Image", fanart )
	liz.setProperty( "icon_Image", iconimage )
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
	return ok

def get_params():
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
						splitparams=pairsofparams[i].split('=')
						if (len(splitparams))==2:
								param[splitparams[0]]=splitparams[1]
								
		return param

params=get_params(); name=None; url=None; mode=None; iconimage=None; fanartimage=None
try: name=urllib.parse.unquote_plus(params["name"])
except: pass
try: url=urllib.parse.unquote_plus(params["url"])
except: pass
try: mode=int(params["mode"])
except: pass
try: iconimage=urllib.parse.unquote_plus(params["iconimage"])
except: pass
try: fanartimage=urllib.parse.quote_plus(params["fanartimage"])
except: pass

if mode is None or url is None or len(url)<1: 
	MainMenu()#change to skinWIN() to open select window automaticly
skinWIN()



# How to add more modes 
#elif mode==4:swapSkins(name,'Exact skin folder')
#elif mode==5:swapSkins(name,'Exact skin folder')
xbmcplugin.endOfDirectory(int(sys.argv[1]))

