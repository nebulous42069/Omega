from ..plugin import Plugin
from ..DI import DI
import xml.etree.ElementTree as ET
import json, xbmc, requests, re

class youtube(Plugin):
    name = "youtube"
    priority = 120
    
    def get_list(self, url):
        # if "youtube.com" in url:     
        if "youtube.com" in url or 'plugin.video.youtube' in url :     
            url2 = swap_link(url)      
            if "/channel/" in url or "playlist_list" in url2:
                r = requests.get("https://api.youtubemultidownloader.com/playlist", params={"url": url2.replace("playlist_list", "playlist?list"), "nextPageToken": ""}).text
                return "youtube://" + r
            
            # if "/channel/" in url or "playlist_list" in url:
                # r = requests.get("https://api.youtubemultidownloader.com/playlist", params={"url": url.replace("playlist_list", "playlist?list"), "nextPageToken": ""}).text
                # return "youtube://" + r

    def parse_list(self, url, response):
        items = []
        if response.startswith("youtube://"):
            r = json.loads(response[10:])
            for item in r["items"]:
                jen_data = {
                    "title": item["title"],
                    "thumbnail": item["thumbnails"].replace("default", "hqdefault"),
                    "fanart": item["thumbnails"].replace("default", "hqdefault"),
                    "summary": item["title"],
                    "link": item["url"],
                    "type": "item"
                }
                items.append(jen_data)
            return items
    
    def play_video(self, item):
        item = json.loads(item)
        xbmc.log(str(item), xbmc.LOGINFO)
        if "link" not in item: return
        link = item["link"]
        if isinstance(link, list) and len(link) > 0: link = link[0]
        link2 = swap_link(link)  
        # r = re.findall(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", link)
        r = re.findall(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", link2)
        if len(r) > 0:
            xbmc.executebuiltin(f"RunPlugin(plugin://plugin.video.youtube/play/?video_id={r[0]})")
            return True

#####
def swap_link(link) :
    pl_base = 'https://www.youtube.com/playlist_list=' 
    ch_base = 'https://www.youtube.com/channel/' 
    vid_base = 'https://www.youtube.com/watch?v=' 
    
    if 'plugin.video.youtube/playlist' in link :
        if link.lower().endswith('/') : 
            new_link = pl_base + link.split('/')[-2]
        else : 
            new_link = pl_base + link.split('/')[-1]
        
    elif 'plugin.video.youtube/channel' in link :
        if link.lower().endswith('/') : 
            new_link = ch_base + link.split('/')[-2]
        else : 
            new_link = ch_base + link.split('/')[-1]
        
    elif 'plugin.video.youtube/watch' in link :   
        new_link = vid_base + link.split('=')[-1]
        
    elif 'youtube.com/watch' in link :   
        new_link = vid_base + link.split('=')[-1]

    else :  new_link = link
  
    return new_link
