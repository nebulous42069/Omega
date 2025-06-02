import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

addon_icon = 'special://home/addons/plugin.program.maxql/icon.png'

class hd:
    def hd_config():
        
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.seren/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.seren/settings.xml')
            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                
                res = '1'
                addon = xbmcaddon.Addon("plugin.video.seren")
                addon.setSetting("general.maxResolution", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fen/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fen/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = 'SD, 720p, 1080p'
                addon = xbmcaddon.Addon("plugin.video.fen")
                addon.setSetting("results_quality_movie", res)
                addon.setSetting("results_quality_episode", res)
                addon.setSetting("autoplay_quality_movie", res)
                addon.setSetting("autoplay_quality_episode", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fenlight/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/settings.db')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                from resources.lib.modules import maxql_db
                maxql_db.enable_fenlt_1080p()
                xbmc.executebuiltin('PlayMedia(plugin://plugin.video.fenlight/?mode=sync_settings&amp;silent=true)')
                xbmc.sleep(2000)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ezra/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ezra/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = 'SD, 720p, 1080p'
                addon = xbmcaddon.Addon("plugin.video.ezra")
                addon.setSetting("results_quality_movie", res)
                addon.setSetting("results_quality_episode", res)
                addon.setSetting("autoplay_quality_movie", res)
                addon.setSetting("autoplay_quality_episode", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.coalition/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.coalition/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = 'SD, 720p, 1080p'
                addon = xbmcaddon.Addon("plugin.video.coalition")
                addon.setSetting("results_quality_movie", res)
                addon.setSetting("results_quality_episode", res)
                addon.setSetting("autoplay_quality_movie", res)
                addon.setSetting("autoplay_quality_episode", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.pov/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.pov/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = 'SD, 720p, 1080p'
                addon = xbmcaddon.Addon("plugin.video.pov")
                addon.setSetting("results_quality_movie", res)
                addon.setSetting("results_quality_episode", res)
                addon.setSetting("autoplay_quality_movie", res)
                addon.setSetting("autoplay_quality_episode", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.umbrella/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.umbrella/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.umbrella")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.infinity/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.infinity/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.infinity")
                addon.setSetting("hosts.quality", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.dradis/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.dradis/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.dradis")
                addon.setSetting("hosts.quality", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.taz19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.taz19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = 'SD, 720p, 1080p'
                addon = xbmcaddon.Addon("plugin.video.taz19")
                addon.setSetting("results_quality_movie", res)
                addon.setSetting("results_quality_episode", res)
                addon.setSetting("autoplay_quality_movie", res)
                addon.setSetting("autoplay_quality_episode", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.shadow/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.shadow/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.shadow")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ghost/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ghost/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.ghost")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.base/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.base/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.base")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.thechains/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.thechains/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.thechains")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.magicdragon/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.magicdragon/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.magicdragon")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.asgard/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.asgard/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.asgard")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.patriot/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.patriot/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.patriot")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.blacklightning/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.blacklightning/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.blacklightning")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.aliundek19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.aliundek19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.aliundek19")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.NightwingLite/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.NightwingLite/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.NightwingLite")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.twisted/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.twisted/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.twisted")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.metv19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.metv19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.metv19")
                addon.setSetting("max_q", res)
                addon.setSetting("max_q_tv", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.homelander/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.homelander/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.homelander")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.quicksilver/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.quicksilver/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.quicksilver")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.chainsgenocide/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.absolution/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.absolution/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.absolution")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.shazam/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.shazam/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.shazam")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.thecrew/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.thecrew/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.thecrew")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.alvin/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.alvin/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.alvin")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.moria/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.moria/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.moria")
                addon.setSetting("hosts.quality", res)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.nine/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.nine/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '1'
                addon = xbmcaddon.Addon("plugin.video.nine")
                addon.setSetting("hosts.quality", res)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.scrubsv2/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.scrubsv2/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                res = '4'
                addon = xbmcaddon.Addon("plugin.video.scrubsv2")
                addon.setSetting("quality.max", res)
        except:
                pass
            
        xbmcgui.Dialog().notification('MaxQL', '1080P Max Enabled!', addon_icon, 3000)
