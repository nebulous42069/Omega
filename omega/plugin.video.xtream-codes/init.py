import six.moves.urllib.request,sys,re,xbmcplugin,xbmcgui,xbmcaddon,datetime,os,json,base64,plugintools,xbmcvfs,six, xbmc
from plugintools import *
import xml.etree.ElementTree as ElementTree
from time import time
if six.PY2:
	reload(sys)
	sys.setdefaultencoding("utf-8")
	transPath = xbmc.translatePath
else:
	transPath = xbmcvfs.translatePath
SKIN_VIEW_FOR_MOVIES="515"
addonDir = get_runtime_path()
addonname  = xbmcaddon.Addon().getAddonInfo('name')
artPath  = os.path.join( get_runtime_path() , "resources", "art")

def menu(params):
	log(addonname +"Main Menu"+repr(params))
	log(addonname +"Login Success")
	add_item( action="account",portal=params['url'], title="My Account" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=True)
	add_item( action="play", portal=params['url'], title ="Live TV" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=True)
	add_item( action="vod_categories",   portal=params['url'], title="Video On Demand" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=True)
	add_item( action="series_categories",   portal=params['url'], title="Series" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=True)
	add_item( action="cleargroups", portal=params['url'], title="Gruppen zurücksetzen" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=False)
	add_item( action="settings", title="Settings" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png"), folder=False)
	set_view( LIST)
def portal_settings(number):
	return get_setting("website" + number), get_setting("port" + number), get_setting("username" + number), get_setting("password" + number)
def reset_portal_settings(number):
	set_setting("website" + number, "None"), set_setting("port" + number, "None"), set_setting("username" + number, "None"), set_setting("password" + number, "None")
def settings(params):
    log(addonname +"Settings menu"+repr(params))
    open_settings_dialog()
def live_categories(params):
    groups = get_data_path() + '/' + params['portal'] + '-groups';
    log(addonname +"Live Menu"+repr(params))
    get_live_categories  = "%s:%s/enigma2.php?username=%s&password=%s&type=get_live_categories"%(portal_settings(params['portal']))
    request = six.moves.urllib.request.Request(get_live_categories , headers={"Accept" : "application/xml"})
    u = six.moves.urllib.request.urlopen(request)
    tree = ElementTree.parse(u)
    rootElem = tree.getroot()
    titles = []
    ids=[]
    for channel in tree.findall("channel"):
        titles.append(decode_data(channel.find("title").text))
        ids.append(channel.find("category_id").text)
    indicies = selector(titles, "Choose Groups", True)
    group = []
    if indicies:
        for i in indicies:
            group.append(ids[i])
    if len(group) > 0:
    	with open(groups,'w') as k:
            json.dump(group, k)
    return group
def vod_categories(params):
    get_vod_categories  = "%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_categories"%(portal_settings(params['portal']))
    log(addonname +"VOD Menu" +repr(params))        
    request = six.moves.urllib.request.Request(get_vod_categories , headers={"Accept" : "application/xml"})
    u = six.moves.urllib.request.urlopen(request)
    tree = ElementTree.parse(u)
    rootElem = tree.getroot()
    for channel in tree.findall("channel"):
        title = channel.find("title").text
        title = decode_data(title)
        category_id = channel.find("category_id").text
        add_item( action="vod_channels", title=title , portal=params['portal'],id=category_id, thumbnail = "" , fanart=os.path.join(artPath ,"theater.jpg") , folder=True)
    set_view( LIST)
def series_categories(params):
    get_series_categories  = "%s:%s/enigma2.php?username=%s&password=%s&type=get_series_categories"%(portal_settings(params['portal']))
    log(addonname +"SERIES Menu "+repr(params))        
    request = six.moves.urllib.request.Request(get_series_categories , headers={"Accept" : "application/xml"})
    u = six.moves.urllib.request.urlopen(request)
    tree = ElementTree.parse(u)
    rootElem = tree.getroot()
    for channel in tree.findall("channel"):
        title = channel.find("title").text
        title = decode_data(title)
        category_id = channel.find("category_id").text
        add_item( action="series_channels", title=title , portal=params['portal'],id=category_id, thumbnail = "" , fanart=os.path.join(artPath ,"logo.png") , folder=True)
    set_view( LIST)
def live_channels(params):
    groups = get_data_path() + '/' + params['portal'] + '-groups';
    chanid = params.get("chan_id")
    try:
        with open(groups) as k:
            ids = json.load(k)
    except:
        ids = live_categories(params)
    log(addonname +"Live Channels Menu "+repr(params))
    root = ElementTree.Element("items")
    for id in ids:
        get_live_channels  = "%s:%s/enigma2.php?username=%s&password=%s&type=get_live_streams"%(portal_settings(params['portal']))+"&cat_id="+ id
        request = six.moves.urllib.request.Request(get_live_channels, headers={"Accept" : "application/xml"})
        u = six.moves.urllib.request.urlopen(request)
        items = ElementTree.parse(u)
        channels = items.findall("channel")
        for channel in channels:
            root.append (channel)
    tree = ElementTree.ElementTree(root)
    stream = {}
    for channel in tree.findall("channel"):
        title = channel.find("title").text
        title = decode_data(title)
        title = title.partition("[")
        stream_url = channel.find("stream_url").text
        desc_image = channel.find("desc_image").text
        guide = title[1]+title[2]
        guide = guide.partition("]")
        guide = guide[2]
        guide = guide.partition("   ")
        guide = guide[2]
        if guide == "":
        	guide = "keine Programminfos"
        name = re.sub("\(.*\)", "", title[0])
        name = re.sub("\[.*\]", "", name)
        name = name.replace('CH: ', '').replace('DE: ', '').replace('AT: ', '').replace(' FHD', '').replace(' HD', '').replace(' HEVC', '').replace(' DE', '').replace(' CH', '').replace(' AT', '').replace('Sky Arte', 'Arte').replace('Sky Classica', 'Classica').replace(' H②⑥⑤', '').replace("[B]", "").strip()
        description = channel.find("description").text
        if description:
           description = decode_data(description)
           now = description.partition("(")
           now = "NOW: " +now[0]
           next = description.partition(")\n")
           next = next[2].partition("(")
           next = "NEXT: " +next[0]
           plot = now+next
        else:
           plot = ""
        if name not in stream:
             stream[name] = []
             if desc_image and not "---" in name and not "###" in name:
                add_item( action="play", title=name+' : '+guide, chan=name, portal=params['portal'], thumbnail=desc_image, plot=plot, fanart=os.path.join(artPath ,"hometheater.jpg"), extra="", isPlayable=True, folder=False)
             elif not "---" in name and not "###" in name:
                add_item( action="play", title=name+' : '+guide, chan=name, portal=params['portal'], thumbnail=os.path.join(artPath ,"defaultlogo.png") , plot=plot, fanart=os.path.join(artPath ,"hometheater.jpg") , extra="", isPlayable=True, folder=False)
        stream[name].append(stream_url)
    if chanid:
        return stream[chanid]
    set_view( EPISODES)
    xbmc.executebuiltin("Container.SetViewMode(503)")
def vod_channels(params):
        log(addonname +"VOD channels menu "+repr(params))
        url  = "%s:%s/enigma2.php?username=%s&password=%s&type=get_vod_streams"%(portal_settings(params['portal']))+"&cat_id="+params['id']
        request = six.moves.urllib.request.Request(url, headers={"Accept" : "application/xml"})
        u = six.moves.urllib.request.urlopen(request)
        tree = ElementTree.parse(u)
        rootElem = tree.getroot()
        for channel in tree.findall("channel"):
            title = channel.find("title").text
            title = decode_data(title)
            title = title.encode("utf-8")
            stream_url = channel.find("stream_url").text
            desc_image = channel.find("desc_image").text 
            description = channel.find("description").text
            if description:
               description = decode_data(description) 
            if desc_image:
               add_item( action="play", title=title , url=stream_url, thumbnail=desc_image, plot=description, fanart=os.path.join(artPath ,"theater.jpg") , extra="", isPlayable=True, folder=False)
            else:
               add_item( action="play", title=title , url=stream_url, thumbnail=os.path.join(artPath ,"noposter.jpg"), plot=description, fanart="" , extra="", isPlayable=True, folder=False)
        set_view( MOVIES)
        xbmc.executebuiltin('Container.SetViewMode(515)')
def series_channels(params):
    log(addonname +"SERIES channels menu "+repr(params))
    url  = "%s:%s/enigma2.php?username=%s&password=%s&type=get_series"%(portal_settings(params['portal']))+"&cat_id="+params['id']
    request = six.moves.urllib.request.Request(url, headers={"Accept" : "application/xml"})
    u = six.moves.urllib.request.urlopen(request)
    tree = ElementTree.parse(u)
    rootElem = tree.getroot()
    for channel in tree.findall("channel"):
        title = channel.find("title").text
        title = decode_data(title)
        stream_url = channel.find("stream_url")
        if stream_url is None:
            playlist_url = channel.find("playlist_url").text
            add_item( action="series_channels ", title=title , url=playlist_url , thumbnail = "" , fanart=os.path.join(artPath ,"hometheater.jpg") , folder=True)
        else:
            stream_url = channel.find("stream_url").text
            title = title.encode("utf-8")
            desc_image = channel.find("desc_image").text 
            if desc_image:
               add_item( action="play", title=title , url=stream_url, thumbnail=desc_image, plot="", fanart=os.path.join(artPath ,"hometheater.jpg") , extra="", isPlayable=True, folder=False)
            else:
               add_item( action="play", title=title , url=stream_url, thumbnail=os.path.join(artPath ,"noposter.jpg"), plot="", fanart="" , extra="", isPlayable=True, folder=False)
    set_view( MOVIES)
    xbmc.executebuiltin('Container.SetViewMode(515)')
def decode_data(data):
    data = six.ensure_str(base64.b64decode(data))
    return data
def handle_wait(time_to_wait, kanal, heading="Abbrechen zur manuellen Auswahl", text1="Starte Stream in  : ", text2="STARTE  : "):
    progress = xbmcgui.DialogProgress()
    create = progress.create(heading, text2+kanal)
    secs=0
    percent=0
    increment = int(100 / time_to_wait)
    cancelled = False
    while secs < time_to_wait:
        secs += 1
        percent = increment*secs
        secs_left = str((time_to_wait - secs))
        if six.PY2:progress.update(percent,text2+kanal,text1+str(secs_left))
        else:progress.update(percent,text2+kanal+"\n"+text1+str(secs_left))
        xbmc.sleep(1000)
        if (progress.iscanceled()):
            cancelled = True
            break
    if cancelled == True:
        progress.close()
        return False
    else:
        progress.close()
        return True
def play(params):
	inputstream = True
	log(addonname +"PLAY"+repr(params))
	chan = params.get("chan", False)
	title = params.get("title")
	url = params.get("url")
	if not chan and not url:
	    return live_channels(params)
	if url:
		inputstream = False
		n = url
	else:
		#chanid = title.split(" : ")[0]
		params["chan_id"] = chan
		m = live_channels(params)
		if len(m) > 1:
			if get_setting('auto') == "0" or get_setting('auto') == "1" and handle_wait(int(get_setting('count')), chan):
				n = m[0]
			else:
				cap=[]
				i = 0
				while i < len(m):
					i+=1
					cap.append('STREAM'+' '+str(i))
				index = selector(cap, '')
				if index < 0:
					return
				n = m[index]
		else:
			n = m[0]
	play_resolved_url(url=n, title=title, inputstream=inputstream)
def account(params):
    panelapi  = "%s:%s/panel_api.php?username=%s&password=%s"%(portal_settings(params['url']))
    log(addonname +"My account Menu "+repr(params))
    req = six.moves.urllib.request.Request(panelapi)
    req.add_header("User-Agent" , "Kodi plugin by MikkM")
    link = six.moves.urllib.request.urlopen(req).read()
    user_info = json.loads(link.decode('utf8'))["user_info"]
    status = user_info["status"]
    exp_date = user_info["exp_date"]
    if exp_date:
       exp_date = datetime.datetime.fromtimestamp(int(exp_date)).strftime('%H:%M %d.%m.%Y')
    else:
       exp_date = "Never" 
    is_trial = user_info["is_trial"]
    if is_trial == "0":
       is_trial = "No"
    else:
       is_trial = "Yes"
    add_item( action="",   title="[COLOR = white]User: [/COLOR]"+user_info["username"] , thumbnail="" , fanart=os.path.join(artPath ,"background.png") , folder=False)
    add_item( action="",   title="[COLOR = white]Status: [/COLOR]"+status , thumbnail="" , fanart=os.path.join(artPath ,"background.png") , folder=False)
    add_item( action="",   title="[COLOR = white]Expires: [/COLOR]"+exp_date , thumbnail="" , fanart=os.path.join(artPath ,"background.png") , folder=False)
    add_item( action="",   title="[COLOR = white]Trial account: [/COLOR]"+is_trial , thumbnail="" , fanart=os.path.join(artPath ,"background.png") , folder=False)
    add_item( action="",   title="[COLOR = white]Max connections: [/COLOR]"+user_info["max_connections"] , thumbnail="" , fanart=os.path.join(artPath ,"background.png") , folder=False)
    set_view( LIST)

def portals(params):
	for i in range(13):
		if get_setting("website"+str(i)) != "" and get_setting("website"+str(i)) != "None":
			panelapi  = "%s:%s/panel_api.php?username=%s&password=%s"%(portal_settings(str(i)))
			try:
				req = six.moves.urllib.request.Request(panelapi)
				req.add_header("User-Agent" , "Kodi plugin by MikkM")
				link = six.moves.urllib.request.urlopen(req).read()
				user_info = json.loads(link.decode('utf8'))["user_info"]
				auth = user_info["auth"]
				ok = "true"
			except:
				ok = "false"
				reset_portal_settings(str(i))
			if ok == 'true':
				log(addonname +"Main Menu"+repr(params))
				add_item( action="menu",  url=str(i),  title="Portal %s"%(str(i+1)) ,thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=True)
	add_item( action="cleargroups", title="Alle Gruppen zurücksetzen" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png") , folder=False)
	add_item( action="settings", title="Settings" , thumbnail=os.path.join(artPath ,"logo.png"), fanart=os.path.join(artPath ,"background.png"), folder=False)
	set_view( LIST)

def cleargroups(params):
	dataPath=get_data_path()
	if params.get("portal") is None:
		if message_yes_no("Alle Gruppen zurücksetzen?"):
			for i in range(13):
				groups = dataPath + '/' + str(i) + '-groups';
				if os.path.exists(groups):
					os.remove(groups)
	else:
		if message_yes_no("Gruppen von Portal: "+params.get("portal")+" zurücksetzen?"):
			groups = dataPath + '/' + params.get("portal") + '-groups';
			if os.path.exists(groups):
				os.remove(groups)

if __name__ == '__main__':
	run()