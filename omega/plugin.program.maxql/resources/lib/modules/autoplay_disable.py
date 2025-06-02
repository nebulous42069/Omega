import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import string
import os

addon_icon = 'special://home/addons/plugin.program.maxql/icon.png'

class ap_disable:
    def disable():
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.seren/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.seren/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.seren")
                addon.setSetting("general.playstyleMovie", '1')
                addon.setSetting("general.playstyleEpisodes", '1') 
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fen/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fen/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.fen")
                addon.setSetting("auto_play_movie", 'false')
                addon.setSetting("auto_play_episode", 'false')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fenlight/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/settings.db')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                from resources.lib.modules import maxql_db
                maxql_db.disable_fenlt_ap()
                xbmc.executebuiltin('PlayMedia(plugin://plugin.video.fenlight/?mode=sync_settings&amp;silent=true)')
                xbmc.sleep(2000)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ezra/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ezra/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.ezra")
                addon.setSetting("auto_play_movie", 'false')
                addon.setSetting("auto_play_episode", 'false')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.coalition/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.coalition/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.coalition")
                addon.setSetting("auto_play_movie", 'false')
                addon.setSetting("auto_play_episode", 'false')
        except:
            pass
        
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.pov/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.pov/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.pov")
                addon.setSetting("auto_play_movie", 'false')
                addon.setSetting("auto_play_episode", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.umbrella/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.umbrella/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.umbrella")
                addon.setSetting("play.mode.movie", '0')
                addon.setSetting("play.mode.tv", '0')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.infinity/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.infinity/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.infinity")
                addon.setSetting("play.mode.movie", '0')
                addon.setSetting("play.mode.tv", '0')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.dradis/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.dradis/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.dradis")
                addon.setSetting("play.mode", '0')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.taz19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.taz19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.taz19")
                addon.setSetting("auto_play_movie", 'false')
                addon.setSetting("auto_play_episode", 'false')
                addon.setSetting("autoplay_next_episode", 'false')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.shadow/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.shadow/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.shadow")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ghost/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ghost/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.ghost")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.base/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.base/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.base")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.thechains/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.thechains/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.thechains")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.magicdragon/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.magicdragon/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.magicdragon")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.asgard/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.asgard/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.asgard")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.patriot/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.patriot/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.patriot")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.blacklightning/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.blacklightning/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.blacklightning")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.aliundek19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.aliundek19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.aliundek19")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.NightwingLite/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.NightwingLite/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.NightwingLite")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.twisted/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.twisted/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.twisted")
                addon.setSetting("one_click", 'false')
                addon.setSetting("one_click_tv", 'false')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.homelander/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.homelander/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.homelander")
                addon.setSetting("hosts.mode", '1')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.quicksilver/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.quicksilver/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.quicksilver")
                addon.setSetting("hosts.mode", '1')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.chainsgenocide/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                addon.setSetting("hosts.mode", '1')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.absolution/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.absolution/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.absolution")
                addon.setSetting("hosts.mode", '1')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.shazam/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.shazam/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.shazam")
                addon.setSetting("hosts.mode", '1')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.alvin/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.alvin/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.alvin")
                addon.setSetting("hosts.mode", '1')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.moria/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.moria/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.moria")
                addon.setSetting("hosts.mode", '1')
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.nine/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.nine/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.nine")
                addon.setSetting("hosts.mode", '1')
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.scrubsv2/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.scrubsv2/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                addon = xbmcaddon.Addon("plugin.video.scrubsv2")
                addon.setSetting("hosts.mode", '1')
        except:
                pass
            
        xbmcgui.Dialog().notification('MaxQL', 'Auto-Play Disabled!', addon_icon, 3000)
