import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import string
import os

addon_icon = 'special://home/addons/plugin.program.maxql/icon.png'

class three_d:
    def threed_enable():
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.seren/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.seren/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                chk_seren_ftr = xbmcaddon.Addon('plugin.video.seren').getSetting("general.filters")
                addon = xbmcaddon.Addon("plugin.video.seren")
                setting = addon.getSetting("general.filters")
                single_ftr = '3D'
                additional_ftr = ',3D'
                
                if str(chk_seren_ftr) != '' and single_ftr not in str(chk_seren_ftr):
                    addon.setSetting("general.filters", setting + additional_ftr)
                    
                else:
                    addon.setSetting("general.filters", single_ftr)        
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fen/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fen/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.fen")
                addon.setSetting("include_3d_results", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fenlight/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/settings.db')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                from resources.lib.modules import maxql_db
                maxql_db.enable_fenlt_3d()
                xbmc.executebuiltin('PlayMedia(plugin://plugin.video.fenlight/?mode=sync_settings&amp;silent=true)')
                xbmc.sleep(2000)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ezra/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ezra/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.ezra")
                addon.setSetting("include_3d_results", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.coalition/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.coalition/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.coalition")
                addon.setSetting("include_3d_results", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.pov/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.pov/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.pov")
                addon.setSetting("include_3d_results", ftr)
        except:
                pass
 
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.umbrella/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.umbrella/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'false'
                addon = xbmcaddon.Addon("plugin.video.umbrella")
                addon.setSetting("remove.3D.sources", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.infinity/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.infinity/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'false'
                addon = xbmcaddon.Addon("plugin.video.infinity")
                addon.setSetting("remove.3D.sources", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.taz19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.taz19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.taz19")
                addon.setSetting("include_3d_results", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.shadow/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.shadow/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.shadow")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ghost/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ghost/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.ghost")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.base/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.base/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.base")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.thechains/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.thechains/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.thechains")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.magicdragon/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.magicdragon/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.magicdragon")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.asgard/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.asgard/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.asgard")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.patriot/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.patriot/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.patriot")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.blacklightning/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.blacklightning/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.blacklightning")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.aliundek19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.aliundek19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.aliundek19")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.NightwingLite/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.NightwingLite/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.NightwingLite")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.metv19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.metv19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                encoding = 'true'
                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.metv19")
                addon.setSetting("encoding_filter", encoding)
                addon.setSetting("3d", ftr)
                addon.setSetting("encoding_filter_tv", encoding)
                addon.setSetting("3d_tv", ftr)
        except:
                pass
 
        xbmcgui.Dialog().notification('MaxQL', '3D Enabled!', addon_icon, 3000)
