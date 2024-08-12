import xbmc
import xbmcaddon
import json
import time
from ..DI import DI
from ..plugin import Plugin

class cached_list(Plugin):
    name = "Cached List"
    priority = 1000

    def get_list(self, url):
        if not xbmcaddon.Addon().getSettingBool("use_cache"):
            return
        cache_timer =  xbmcaddon.Addon().getSetting("time_cache") or 0
        cache_timer =  float(cache_timer*1)
        cached = DI.db.get(url)
        if not cached:
            return
        response, created = cached
        try:
            if float(created + json.loads(response).get("cache_time", cache_timer)) < time.time():
                return
        except json.decoder.JSONDecodeError as e:
            xbmc.log(f'Json Error: {e}', xbmc.LOGINFO)
            if created + cache_timer < time.time():
                return 
        return response
