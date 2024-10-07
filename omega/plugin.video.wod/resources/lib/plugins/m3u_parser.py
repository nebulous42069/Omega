from ..plugin import Plugin
import re
import operator

import os, json

import xbmcaddon
import xbmcvfs

try:
    from resources.lib.util.common import *
except ImportError:
    from .resources.lib.util.common import *

PATH = xbmcaddon.Addon().getAddonInfo("path")
data_path = os.path.join(PATH, "xml", "data")
if not xbmcvfs.exists(data_path) : xbmcvfs.mkdirs(data_path) 

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')

class m3u(Plugin):
    name = "m3u"
    description = "add support for m3u lists"
    priority = 2
    
    def parse_list(self, url: str, response):
        item_list = []
        thumbnail = '' 
        channel_name = '' 
        if url.endswith(".m3u") or url.endswith(".m3u8") or '#EXTINF' in response : 
            response = response.strip()
            try : 
                match = re.compile(r'#EXTINF:(.+?),(.*?)[\n\r]+([^\n]+)').findall(response)            
                for other,channel_name,stream_url in match:
                    if 'tvg-logo' in other:
                        thumbnail = self.re_me(other,'tvg-logo=[\'"](.*?)[\'"]')
                    if thumbnail:
                        thumbnail = thumbnail
                    else:
                        thumbnail = default_icon # ''
                    item = {'title': channel_name, 'link': stream_url, 'thumbnail': thumbnail, 'type': 'item'}
                    item_list.append(item)
                               
            except :
                match = re.compile(r'#EXTINF:-?[0-9](.+?)\n(.+?)$', re.M).findall(response)
                # do_log(f'{self.name} - match = \n' + str(match) )  
                for m in match :
                    # do_log(f'{self.name} - m = \n' + str(m) )  
                    channel_name = re.compile(r',(.+?)$').findall(str(m[0]).strip())
                    thumbnail = re.compile(r'tvg-logo="(.+?)"').findall(str(m[0]).strip())
                    stream_url = str(m[-1])
                    if not channel_name : channel_name = 'Channel Unknown' 
                    if not thumbnail : thumbnail = default_icon
                    
                    item = {'title': channel_name.strip(), 'link': stream_url, 'thumbnail': thumbnail.strip(), 'type': 'item'}
                    item_list.append(item)
                               
                
        item_list.sort(key = operator.itemgetter('title'), reverse = False)
        
        return item_list
    
    def re_me(self, data, re_patten):
        match = ''
        m = re.search(re_patten, data)
        if m != None:
              match = m.group(1)
        else:
              match = ''
        return match
    
    

        