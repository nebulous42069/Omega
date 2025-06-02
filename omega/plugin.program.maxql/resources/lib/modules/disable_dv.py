import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import string
import os

addon_icon = 'special://home/addons/plugin.program.maxql/icon.png'

class dv:
    def dv_disable():
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.seren/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.seren/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                chk_seren_ftr = xbmcaddon.Addon('plugin.video.seren').getSetting("general.filters")
                addon = xbmcaddon.Addon("plugin.video.seren")
                setting = addon.getSetting("general.filters")
                single_ftr = 'DV'
                additional_ftr1 = ',DV'
                additional_ftr2 = 'DV,'
                
                if str(chk_seren_ftr) == single_ftr:
                    addon.setSetting("general.filters", "AV1")
                    
                if additional_ftr1 in chk_seren_ftr:
                    current = str(addon.getSetting("general.filters"))
                    new = current.replace(",DV", "")
                    addon.setSetting("general.filters", new)
                    
                if additional_ftr2 in chk_seren_ftr:
                    current = str(addon.getSetting("general.filters"))
                    new = current.replace("DV,", "")
                    addon.setSetting("general.filters", new)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fen/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fen/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = '1'
                addon = xbmcaddon.Addon("plugin.video.fen")
                addon.setSetting("filter_dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.fenlight/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.fenlight/databases/settings.db')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):
                from resources.lib.modules import maxql_db
                maxql_db.disable_fenlt_dv()
                xbmc.executebuiltin('PlayMedia(plugin://plugin.video.fenlight/?mode=sync_settings&amp;silent=true)')
                xbmc.sleep(2000)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.ezra/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.ezra/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = '1'
                addon = xbmcaddon.Addon("plugin.video.ezra")
                addon.setSetting("filter_dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.coalition/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.coalition/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = '1'
                addon = xbmcaddon.Addon("plugin.video.coalition")
                addon.setSetting("filter_dv", ftr)
        except:
            pass
        
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.pov/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.pov/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = '1'
                addon = xbmcaddon.Addon("plugin.video.pov")
                addon.setSetting("filter_dv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.umbrella/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.umbrella/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.umbrella")
                addon.setSetting("remove.dolby.vision", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.infinity/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.infinity/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.infinity")
                addon.setSetting("remove.dolby.vision", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.dradis/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.dradis/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.dradis")
                addon.setSetting("remove.dolby.vision", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.taz19/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.taz19/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = '1'
                addon = xbmcaddon.Addon("plugin.video.taz19")
                addon.setSetting("filter_dv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.homelander/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.homelander/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.homelander")
                addon.setSetting("remove.dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.quicksilver/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.quicksilver/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.quicksilver")
                addon.setSetting("remove.dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.chainsgenocide/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.chainsgenocide/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                addon.setSetting("remove.dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.absolution/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.absolution/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.absolution")
                addon.setSetting("remove.dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.shazam/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.shazam/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.shazam")
                addon.setSetting("remove.dv", ftr)
        except:
                pass

        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.alvin/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.alvin/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.alvin")
                addon.setSetting("remove.dv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.moria/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.moria/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.moria")
                addon.setSetting("remove.dv", ftr)
        except:
                pass
            
        try:
            addon = xbmcvfs.translatePath('special://home/addons/plugin.video.nine/')
            file = xbmcvfs.translatePath('special://userdata/addon_data/plugin.video.nine/settings.xml')

            if xbmcvfs.exists(addon) and xbmcvfs.exists(file):

                ftr = 'true'
                addon = xbmcaddon.Addon("plugin.video.nine")
                addon.setSetting("remove.dv", ftr)
        except:
                pass

        xbmcgui.Dialog().notification('MaxQL', 'Dolby Vision Disabled!', addon_icon, 3000)
