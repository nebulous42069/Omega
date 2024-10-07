import json
import xbmc
import xbmcaddon

from ..plugin import Plugin

class plugplay(Plugin):
    name = "external plugin"
    priority = 100    
    
    def routes(self, plugin):
        @plugin.route("/run_plug/<path:url>")
        def run_plug(url):
            import urllib.parse
            plug_link = url 
            this_plug = urllib.parse.unquote_plus(plug_link)
            
            if 'dailymotion' in this_plug.lower():
                u = 'plugin.video.dailymotion_com' + ',' + this_plug.split('?')[-1]
                z = 'plugin://plugin.video.dailymotion_com/?'+ this_plug.split('?')[-1]                
                xbmc.executebuiltin('RunAddon({})'.format(u))
                
            elif 'resolveurl_auth' in this_plug.lower():
                u = 'script.module.resolveurl/?mode=auth_rd'
                z = 'plugin://script.module.resolveurl/?mode=auth_rd'
                xbmc.executebuiltin('RunPlugin({})'.format(z))
                
            elif 'resolveurl_settings' in this_plug.lower():
                u = 'script.module.resolveurl'
                z = 'plugin://script.module.resolveurl'
                xbmcaddon.Addon(u).openSettings()
                
                
                
                
            
