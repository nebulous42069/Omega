################################################################################
#(_)                                                                           #
# |___________________________________________                                 #
# |`-._`-._         :|    |:         _.-'_.-'|                                 #
# |`-._`-._`-._     :|    |:     _.-'_.-'_.-'|                                 #
# |    `-._`-._`-._ :|    |: _.-'_.-'_.-'    |                                 #
# | _ _ _ _`-._`-._`:|    |:`_.-'_.-' _ _ _ _|                                 #
# |------------------      ------------------|                                 #
# |                                          |                                 #
# |__________________      __________________|                                 #
# |- - - - -_.--_.--:|    |:--._--._- - - - -|                                 #
# |     _.-'_.-'_.-':|    |:`-._`-._`-._     |                                 #
# | _.-'_.-'_.-'    :|    |:    `-._`-._`-._ |                                 #
# |'_.-'_.-'        :|    |:        `-._`-._`|                                 #
# |------------------------------------------|                                 #
# |                                                                            #
# |    GRIND      Add-on                                                         #
# |    Copyright (C) 2017                                                      #
# |                                                                            #
# |    This program is free software: you can redistribute it and/or modify    #
# |    it under the terms of the GNU General Public License as published by    #
# |    the Free Software Foundation, either version 3 of the License, or       #
# |    (at your option) any later version.                                     #
# |                                                                            #
# |    This program is distributed in the hope that it will be useful,         #
# |    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
# |    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
# |    GNU General Public License for more details.                            #
# |                                                                            #
################################################################################

import xbmc, xbmcaddon, xbmcgui, xbmcplugin,os,sys,xbmcvfs
from xbmc import log
import shutil
import urllib.request, urllib.parse, urllib.error
import re
import time




USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
dialog       =  xbmcgui.Dialog()
base = 'http://www.grumpeh.hemera.feralhosting.com/WALLPAPERS/WALLPAPERS.txt'

def INDEX():
	link = OPEN_URL(base).replace(b'\n',b'').replace(b'\r',b'').replace(b'\t',b'')
	match = re.compile(b'name="(.+?)".+?rl="(.+?)".+?con="(.+?)".+?anart="(.+?)".+?escription="(.+?)"').findall(link)
	for name, url, icon, fanart, description in match:
		addDir(name,url,2,icon,fanart,description)

def installer(name,url,description):
	choice = xbmcgui.Dialog().yesno('Diggz Backgrounds', 'This will switch your backgrounds to this theme' + '\n' + 'Would you like to install this background pack now and restart???..', nolabel='No Thanks',yeslabel='Continue')
	if choice == 0:
		return
	if choice == 1:
		path = xbmcvfs.translatePath(os.path.join('special://home/addons','packages'))
		dp = xbmcgui.DialogProgress()
		dp.create("Diggz Backgrounds","Installing your background pack now" + '\n' + 'Hold on a sec...')
		lib=os.path.join(path,'CUSTOM.zip')
		try:
			custom = xbmcvfs.translatePath(os.path.join('special://home/addons/resource.images.skinbackgrounds.xenon/resources/','custom'))
			Destroy_Path(custom)
			if not os.path.exists(custom): os.makedirs(custom)
		except:
			pass
		download(url, lib, dp)
		time.sleep(2)
		dp.update(0, '\n' + "Extracting Images ")
		log('=======================================', xbmc.LOGINFO)
		log(custom, xbmc.LOGINFO)
		log('=======================================', xbmc.LOGINFO)
		all(lib,custom,dp)
		dialog = xbmcgui.Dialog()
		dialog.ok("Diggz Backgrounds", "Ok, all done!! Lets restart Kodi to finish up..")
		thumbs = xbmcvfs.translatePath(os.path.join('special://home/userdata','Thumbnails'))
		Destroy_Path(thumbs)
		killxbmc()

   
def OPEN_URL(url):
	req = urllib.request.Request(url)
	req.add_header('User-Agent', USER_AGENT)
	response = urllib.request.urlopen(req)
	link=response.read()
	response.close()
	return link

def Destroy_Path(path):
    shutil.rmtree(path, ignore_errors=True)
	
def killxbmc():
	os._exit(1)


##################DOWNLOAD############################
def download(url, dest, dp = None):
    if not dp:
        dp = xbmcgui.DialogProgress()
        dp.create("Diggz Backgrounds","Installing your new backgrounds.")
    dp.update(0)
    urllib.request.urlretrieve(url,dest,lambda nb, bs, fs, url=url: _pbhook(nb,bs,fs,url,dp))
 
def _pbhook(numblocks, blocksize, filesize, url, dp):
    try:
        percent = min((numblocks*blocksize*100)/filesize, 100)
        dp.update(percent)
    except:
        percent = 100
        dp.update(percent)
    if dp.iscanceled(): 
        raise Exception("Canceled")
        dp.close()


#################EXTRACT####################################
import zipfile

def all(_in, _out, dp=None):
    if dp:
        return allWithProgress(_in, _out, dp)

    return allNoProgress(_in, _out)
        

def allNoProgress(_in, _out):
    try:
        zin = zipfile.ZipFile(_in, 'r')
        zin.extractall(_out)
    except Exception as e:
        log(str(e), xbmc.LOGINFO)
        return False

    return True


def allWithProgress(_in, _out, dp):

    zin = zipfile.ZipFile(_in,  'r')

    nFiles = float(len(zin.infolist()))
    count  = 0

    try:
        for item in zin.infolist():
            count += 1
            update = count / nFiles * 100
            dp.update(int(update))
            zin.extract(item, _out)
    except Exception as e:
        log(str(e), xbmc.LOGINFO)
        return False

    return True
###################################################


def addDir(name,url,mode,icon,fanart,description):
        u=sys.argv[0]+"?url="+urllib.parse.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.parse.quote_plus(name)+"&icon="+urllib.parse.quote_plus(icon)+"&fanart="+urllib.parse.quote_plus(fanart)+"&description="+urllib.parse.quote_plus(description)
        ok=True
        liz=xbmcgui.ListItem(name)
        liz.setArt({'icon': 'DefaultFolder.png', 'thumb': icon, 'fanart': fanart}) 
        liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot": description } )
        liz.setProperty( "Fanart_Image", fanart )
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
        
                      
params=get_params()
url=None
name=None
mode=None
iconimage=None
fanart=None
description=None


try:
        url=urllib.parse.unquote_plus(params["url"])
except:
        pass
try:
        name=urllib.parse.unquote_plus(params["name"])
except:
        pass
try:
        iconimage=urllib.parse.unquote_plus(params["iconimage"])
except:
        pass
try:        
        mode=int(params["mode"])
except:
        pass
try:        
        fanart=urllib.parse.unquote_plus(params["fanart"])
except:
        pass
try:        
        description=urllib.parse.unquote_plus(params["description"])
except:
        pass
        
        
print("Mode: "+str(mode))
print("URL: "+str(url))
print("Name: "+str(name))
print("IconImage: "+str(iconimage))



        
if mode==None or url==None or len(url)<1:
        INDEX()
		
elif mode==2:installer(name,url,description)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
