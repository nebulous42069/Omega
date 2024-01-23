# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# Plugin Tools v1.0.10
#---------------------------------------------------------------------------
# License: GPL (http://www.gnu.org/licenses/gpl-3.0.html)
# Based on code from youtube, parsedom and pelisalacarta addons
# OrigAuthor: 
# Jesús
# tvalacarta@gmail.com
# http://www.mimediacenter.info/plugintools
#---------------------------------------------------------------------------
# Currently maintained by Titán
# https://github.com/TitanKodi/Plugintools
#---------------------------------------------------------------------------
# Changelog:
# 1.0.0
# - First release
# 1.0.1
# - If find_single_match can't find anything, it returns an empty string
# - Remove addon id from this module, so it remains clean
# 1.0.2
# - Added parameter on "add_item" to say that item is playable
# 1.0.3
# - Added direct play
# - Fixed bug when video isPlayable=True
# 1.0.4
# - Added get_temp_path, get_runtime_path, get_data_path
# - Added get_setting, set_setting, open_settings_dialog and get_localized_string
# - Added keyboard_input
# - Added message
# 1.0.5
# - Added read_body_and_headers for advanced http handling
# - Added show_picture for picture addons support
# - Added optional parameters "title" and "hidden" to keyboard_input
# 1.0.6
# - Added fanart, show, episode and infolabels to add_item
# 1.0.7
# - Added set_view function
# 1.0.8
# - Added selector
# 1.0.9
# - Welcome Matrix
# 1.0.10
# - Added support to params encoded on base64
# - Added the possibility to add extra params to the add_item function
#---------------------------------------------------------------------------

import base64
import xbmc,xbmcvfs
import xbmcplugin
import xbmcaddon
import xbmcgui
import re
import sys
import os
import time
import socket
from io import BytesIO
import gzip
import six
from six.moves import urllib_request
from six.moves.urllib.parse import unquote_plus, quote_plus, urlencode
module_log_enabled = False
http_debug_log_enabled = False
if six.PY3:
    unicode = str
    transPath = xbmcvfs.translatePath
else:
	transPath = xbmc.translatePath
LIST = "list"
THUMBNAIL = "thumbnail"
MOVIES = "movies"
TV_SHOWS = "tvshows"
SEASONS = "seasons"
EPISODES = "episodes"
OTHER = "other"
b64 = False
# Suggested view codes for each type from different skins (initial list thanks to xbmcswift2 library)
ALL_VIEW_CODES = {
    'list': {
        'skin.confluence': 50, # List
        'skin.aeon.nox': 50, # List
        'skin.droid': 50, # List
        'skin.quartz': 50, # List
        'skin.re-touched': 50, # List
    },
    'thumbnail': {
        'skin.confluence': 500, # Thumbnail
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 51, # Big icons
        'skin.re-touched': 500, #Thumbnail
    },
    'movies': {
        'skin.confluence': 500, # Thumbnail 515, # Media Info 3
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 52, # Media info
        'skin.re-touched': 500, #Thumbnail
    },
    'tvshows': {
        'skin.confluence': 500, # Thumbnail 515, # Media Info 3
        'skin.aeon.nox': 500, # Wall
        'skin.droid': 51, # Big icons
        'skin.quartz': 52, # Media info
        'skin.re-touched': 500, #Thumbnail
    },
    'seasons': {
        'skin.confluence': 50, # List
        'skin.aeon.nox': 50, # List
        'skin.droid': 50, # List
        'skin.quartz': 52, # Media info
        'skin.re-touched': 50, # List
    },
    'episodes': {
        'skin.confluence': 504, # Media Info
        'skin.aeon.nox': 518, # Infopanel
        'skin.droid': 50, # List
        'skin.quartz': 52, # Media info
        'skin.re-touched': 550, # Wide
    },
}

# Write something on XBMC log
def log(message):
    if not isinstance(message, str): 
        try:
            message = str(message)
        except: return
    xbmc.log("[%s] - %s"% (xbmcaddon.Addon().getAddonInfo('id'), message), xbmc.LOGINFO)

# Write this module messages on XBMC log
def _log(message):
    if module_log_enabled:
        xbmc.log("%s plugintools.%s"% (xbmcaddon.Addon().getAddonInfo('id'), message), xbmc.LOGINFO)

# Parse XBMC params - based on script.module.parsedom addon & modified by Titán
def get_params():
    _log("get_params")

    param_string = sys.argv[2]

    if b64 or '%3D' in str(param_string) or not '&' in str(param_string) or not '=' in str(param_string):
        try:
            if '?' in str(param_string): param_string = param_string.split('?')[1]
            param_string = six.ensure_text(base64.b64decode(six.ensure_binary(unquote_plus(param_string))))
        except:
            _log("Error, base64 can´t be decoded")

    commands = {}

    if param_string:
        split_commands = param_string[param_string.find('?') + 1:].split('&')
    
        for command in split_commands:
            _log("get_params command="+str(command))
            if len(command) > 0:
                if "=" in command:
                    split_command = command.split('=')
                    key = split_command[0]
                    value = unquote_plus(split_command[1])
                    commands[key] = value
                else:
                    commands[command] = ""
    
    _log("get_params "+repr(commands))
    return commands

# Fetch text content from an URL
def read(url):
    _log("read "+url)

    f = urllib_request.urlopen(url)
    data = f.read()
    f.close()
    if not isinstance(data, str):
        data = data.decode("utf-8", "strict")
    return data

def read_body_and_headers(url, post=None, headers=[], follow_redirects=False, timeout=None):
    xbmc.log("read_body_and_headers "+url, 2)


    if len(headers)==0:
        headers.append(["User-Agent","Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:18.0) Gecko/20100101 Firefox/18.0"])

    # Start cookie lib
    ficherocookies = os.path.join( get_data_path(), 'cookies.dat' )
    _log("read_body_and_headers cookies_file="+ficherocookies)

    cj = None
    ClientCookie = None
    cookielib = None

    # Let's see if cookielib is available
    try:
        _log("read_body_and_headers importing cookielib")
        import cookielib
    except ImportError:
        _log("read_body_and_headers cookielib no disponible")
        # If importing cookielib fails
        # let's try ClientCookie
        try:
            _log("read_body_and_headers importing ClientCookie")
            import ClientCookie
        except ImportError:
            _log("read_body_and_headers ClientCookie not available")
            # ClientCookie isn't available either
            urlopen = urllib_request.urlopen
            Request = urllib_request.Request
        else:
            _log("read_body_and_headers ClientCookie available")
            # imported ClientCookie
            urlopen = ClientCookie.urlopen
            Request = ClientCookie.Request
            cj = ClientCookie.MozillaCookieJar()

    else:
        _log("read_body_and_headers cookielib available")
        # importing cookielib worked
        urlopen = urllib_request.urlopen
        Request = urllib_request.Request
        cj = cookielib.MozillaCookieJar()
        # This is a subclass of FileCookieJar
        # that has useful load and save methods

    if cj is not None:
    # we successfully imported
    # one of the two cookie handling modules
        _log("read_body_and_headers Cookies enabled")

        if os.path.isfile(ficherocookies):
            _log("read_body_and_headers Reading cookie file")
            # if we have a cookie file already saved
            # then load the cookies into the Cookie Jar
            try:
                cj.load(ficherocookies)
            except:
                _log("read_body_and_headers Wrong cookie file, deleting...")
                os.remove(ficherocookies)

        # Now we need to get our Cookie Jar
        # installed in the opener;
        # for fetching URLs
        if cookielib is not None:
            _log("read_body_and_headers opener using urllib_request (cookielib)")
            # if we use cookielib
            # then we get the HTTPCookieProcessor
            # and install the opener in urllib_request
            if not follow_redirects:
                opener = urllib_request.build_opener(urllib_request.HTTPHandler(debuglevel=http_debug_log_enabled),urllib_request.HTTPCookieProcessor(cj),NoRedirectHandler())
            else:
                opener = urllib_request.build_opener(urllib_request.HTTPHandler(debuglevel=http_debug_log_enabled),urllib_request.HTTPCookieProcessor(cj))
            urllib_request.install_opener(opener)

        else:
            _log("read_body_and_headers opener using ClientCookie")
            # if we use ClientCookie
            # then we get the HTTPCookieProcessor
            # and install the opener in ClientCookie
            opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(cj))
            ClientCookie.install_opener(opener)

    # -------------------------------------------------
    # Cookies instaladas, lanza la petición
    # -------------------------------------------------

    # Contador
    inicio = time.time()
    

    # Diccionario para las cabeceras
    txheaders = {}
    if type(post) == dict: post = urlencode(post)
    if post:
        if isinstance(post, unicode):
            post = post.encode('utf-8', 'strict')
    if post is None:
        _log("read_body_and_headers GET request")
    else:
        _log("read_body_and_headers POST request")
    
    # Añade las cabeceras
    _log("read_body_and_headers ---------------------------")
    for header in headers:
        _log("read_body_and_headers header %s=%s" % (str(header[0]),str(header[1])) )
        txheaders[header[0]]=header[1]
    _log("read_body_and_headers ---------------------------")
    if post and six.PY3:
        post = six.ensure_binary(post)
    req = Request(url, post, txheaders)
    if timeout is None:
        handle=urlopen(req)
    else:        
        #Disponible en python 2.6 en adelante --> handle = urlopen(req, timeout=timeout)
        #Para todas las versiones:
        try:
            import socket
            deftimeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            handle=urlopen(req)            
            socket.setdefaulttimeout(deftimeout)
        except:
            import sys
            for line in sys.exc_info():
                _log( "%s" % line )
    
    # Actualiza el almacén de cookies
    if cj:  cj.save(ficherocookies)

    # Lee los datos y cierra
    if handle.info().get('Content-Encoding') == 'gzip':
        buf = BytesIO( handle.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data=handle.read()

    info = handle.info()
    _log("read_body_and_headers Response")

    returnheaders=[]
    _log("read_body_and_headers ---------------------------")
    for header in info:
        _log("read_body_and_headers "+header+"="+info[header])
        returnheaders.append([header,info[header]])
    handle.close()
    _log("read_body_and_headers ---------------------------")

    '''
    # Lanza la petición
    try:
        response = urllib_request.urlopen(req)
    # Si falla la repite sustituyendo caracteres especiales
    except:
        req = urllib_request.Request(url.replace(" ","%20"))
    
        # Añade las cabeceras
        for header in headers:
            req.add_header(header[0],header[1])

        response = urllib_request.urlopen(req)
    '''
    
    # Tiempo transcurrido
    fin = time.time()
    _log("read_body_and_headers Downloaded in %d seconds " % (fin-inicio+1))
    if not isinstance(data, str):
        try:
            data = data.decode("utf-8", "strict")
        except: data = str(data)    
    return data,returnheaders

class NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        try:
            from urllib import addinfourl
        except:
            from six.moves.urllib import addinfourl    
        infourl = addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl
    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302

# Parse string and extracts multiple matches using regular expressions
def find_multiple_matches(text,pattern):
    _log("find_multiple_matches pattern="+pattern)
    
    matches = re.findall(pattern,text,re.DOTALL)

    return matches

# Parse string and extracts first match as a string
def find_single_match(text,pattern):
    _log("find_single_match pattern="+pattern)

    result = ""
    try:    
        matches = re.findall(pattern,text, flags=re.DOTALL)
        result = matches[0]
    except:
        result = ""

    return result

def add_item(**kwargs):
    listitem = xbmcgui.ListItem(six.ensure_str(kwargs.get('title')))
    listitem.setArt({'poster': 'poster.png', 'banner': 'banner.png'})
    listitem.setArt({'icon': kwargs.get('thumbnail'), 'thumb': kwargs.get('thumbnail'), 'poster': kwargs.get('thumbnail'),
                    'fanart': kwargs.get('fanart')})

    info_labels = kwargs.get('info_labels') if 'info_labels' in kwargs else None

    if info_labels is None:
        info_labels = { "Title" : six.ensure_str(kwargs.get('title')), "FileName" : six.ensure_str(kwargs.get('title')), "Plot" : kwargs.get('plot'), "Genre": kwargs.get('genre'), "dateadded": kwargs.get('genre'), "credits": kwargs.get('credits') }

    listitem.setInfo( "video", info_labels )

    if kwargs.get('fanart') and kwargs.get('fanart') !="":
        listitem.setProperty('fanart_image',kwargs.get('fanart'))
        xbmcplugin.setPluginFanart(int(sys.argv[1]), kwargs.get('fanart'))

    if kwargs.get('url') and kwargs.get('url').startswith("plugin://"):
        itemurl = kwargs.get('url')
        listitem.setProperty('IsPlayable', 'true')
    elif kwargs.get('isPlayable'):
        listitem.setProperty("Video", "true")
        listitem.setProperty('IsPlayable', 'true')

    itemurl = '%s?%s' %(sys.argv[ 0 ], urlencode(kwargs) if b64 == False else quote_plus(six.ensure_text(base64.b64encode(six.ensure_binary(urlencode(kwargs))))))
    xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]), url=itemurl, listitem=listitem, isFolder=kwargs.get('folder') if kwargs.get('folder') != None else False if kwargs.get('isPlayable') and kwargs.get('isPlayable') == True else True)
    if kwargs.get('sort'):
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
def close_item_list():
    _log("close_item_list")

    xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)

def play_resolved_url(url, title=None, inputstream=True):
    _log("play_resolved_url ["+url+"]")
    if title== None: 
        listitem = xbmcgui.ListItem(path=url)
    else: 
        listitem = xbmcgui.ListItem(title)
        listitem.setPath(url)
    listitem.setProperty('IsPlayable', 'true')
    if get_setting("inputstream") == 'true' and xbmc.getCondVisibility('System.HasAddon("inputstream.ffmpegdirect")') and inputstream:
       listitem.setMimeType("video/mp2t")
       listitem.setProperty("inputstream", "inputstream.ffmpegdirect")
       listitem.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "true")
       listitem.setProperty("inputstream.ffmpegdirect.stream_mode", "timeshift")
    return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def direct_play(url):
    _log("direct_play ["+url+"]")

    title = ""

    try:
        xlistitem = xbmcgui.ListItem( title, path=url)
    except:
        xlistitem = xbmcgui.ListItem( title)
    xlistitem.setInfo( "video", { "Title": title } )

    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    playlist.add( url, xlistitem )

    player_type = xbmc.PLAYER_CORE_AUTO
    xbmcPlayer = xbmc.Player( player_type )
    xbmcPlayer.play(playlist)

def show_picture(url):

    local_folder = os.path.join(get_data_path(),"images")
    if not os.path.exists(local_folder):
        try:
            os.mkdir(local_folder)
        except:
            pass
    local_file = os.path.join(local_folder,"temp.jpg")

    # Download picture
    urllib_request.urlretrieve(url, local_file)
    
    # Show picture
    xbmc.executebuiltin( "SlideShow("+local_folder+")" )

def get_temp_path():
    _log("get_temp_path")

    dev = transPath( "special://temp/" )
    _log("get_temp_path ->'"+str(dev)+"'")

    return dev

def get_runtime_path():
    _log("get_runtime_path")

    dev = transPath( __settings__.getAddonInfo('Path') )
    _log("get_runtime_path ->'"+str(dev)+"'")

    return dev

def get_data_path():
    _log("get_data_path")

    dev = transPath( __settings__.getAddonInfo('Profile') )
    
    # Parche para XBMC4XBOX
    if not os.path.exists(dev):
        os.makedirs(dev)

    _log("get_data_path ->'"+str(dev)+"'")

    return dev

def get_setting(name):
    _log("get_setting name='"+name+"'")

    dev = __settings__.getSetting( name )

    _log("get_setting ->'"+str(dev)+"'")

    return dev

def set_setting(name,value):
    _log("set_setting name='"+name+"','"+value+"'")

    __settings__.setSetting( name,value )

def open_settings_dialog():
    _log("open_settings_dialog")

    __settings__.openSettings()

def get_localized_string(code):
    _log("get_localized_string code="+str(code))

    dev = __language__(code)

    try:
        dev = dev.encode("utf-8")
    except:
        pass

    _log("get_localized_string ->'"+dev+"'")

    return dev

def keyboard_input(default_text="", title="", hidden=False):
    _log("keyboard_input default_text='"+default_text+"'")

    keyboard = xbmc.Keyboard(default_text,title,hidden)
    keyboard.doModal()
    
    if (keyboard.isConfirmed()):
        tecleado = keyboard.getText()
    else:
        tecleado = ""

    _log("keyboard_input ->'"+tecleado+"'")

    return tecleado

def message(text1, text2="", text3=""):
    _log("message text1='"+text1+"', text2='"+text2+"', text3='"+text3+"'")

    if text3=="":
        xbmcgui.Dialog().ok( text1 , text2 )
    elif text2=="":
        xbmcgui.Dialog().ok( "" , text1 )
    else:
        xbmcgui.Dialog().ok( text1 , text2 , text3 )

def message_yes_no(line1, line2='', line3='', heading=None, nolabel='', yeslabel=''):
	_log("message_yes_no text1='"+line1+"', text2='"+line2+"', text3='"+line3+"'")
	if heading == 'default' or heading is None:
		heading = xbmcaddon.Addon().getAddonInfo('name')
	if six.PY3:return xbmcgui.Dialog().yesno(heading, line1+"\n"+line2+"\n"+line3, nolabel, yeslabel)
	else:return xbmcgui.Dialog().yesno(heading, line1,line2,line3, nolabel, yeslabel)

def selector(list, heading="Select one", multiselect = False):
	if multiselect:
		if heading == 'default' or heading == 'Select one':
			heading = xbmcaddon.Addon().getAddonInfo('name')
		return xbmcgui.Dialog().multiselect(str(heading), list)
	return xbmcgui.Dialog().select(heading, list)

def set_view(view_mode, view_code=0):
    _log("set_view view_mode='"+view_mode+"', view_code="+str(view_code))

    # Set the content for extended library views if needed
    if view_mode==MOVIES:
        _log("set_view content is movies")
        xbmcplugin.setContent( int(sys.argv[1]) ,"movies" )
    elif view_mode==TV_SHOWS:
        _log("set_view content is tvshows")
        xbmcplugin.setContent( int(sys.argv[1]) ,"tvshows" )
    elif view_mode==SEASONS:
        _log("set_view content is seasons")
        xbmcplugin.setContent( int(sys.argv[1]) ,"seasons" )
    elif view_mode==EPISODES:
        _log("set_view content is episodes")
        xbmcplugin.setContent( int(sys.argv[1]) ,"episodes" )

    # Reads skin name
    skin_name = xbmc.getSkinDir()
    _log("set_view skin_name='"+skin_name+"'")

    try:
        if view_code==0:
            _log("set_view view mode is "+view_mode)
            view_codes = ALL_VIEW_CODES.get(view_mode)
            view_code = view_codes.get(skin_name)
            _log("set_view view code for "+view_mode+" in "+skin_name+" is "+str(view_code))
            xbmc.executebuiltin("Container.SetViewMode("+str(view_code)+")")
        else:
            _log("set_view view code forced to "+str(view_code))
            xbmc.executebuiltin("Container.SetViewMode("+str(view_code)+")")
    except:
        _log("Unable to find view code for view mode "+str(view_mode)+" and skin "+skin_name)

def run():
	params = get_params()
	import init
	if not params:
		init.portals(params)
	#if params.get("action") is None:
	else:
		getattr(init, params['action'])(params)
		#globals()[params['action']](params)
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
	close_item_list()

__settings__ = xbmcaddon.Addon()
__language__ = __settings__.getLocalizedString