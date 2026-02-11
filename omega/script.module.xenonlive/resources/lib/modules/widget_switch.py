import os
import shutil
import subprocess
import xbmcgui
import xbmcvfs
import xbmc, xbmcaddon
dialog = xbmcgui.Dialog()
settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonlive/')

def Xenon_Widget_Flavors():
        flavor_list = ['[B]Diggz Xenon Live[/B] - [COLOR chartreuse]2/11/2026[/COLOR]']
        select = dialog.select('Update Xenon Live TV And Sports', flavor_list)
        if select == None:
            return          

        if select == 0:
                src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonlive/resources/switch/Xenon_Live/settings.xml')
                dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonlive/settings.xml')
                
                if os.path.exists(os.path.join(settings_path)):
                        try:
                                shutil.copyfile(src_settings, dst_settings)
                                xbmcgui.Dialog().ok('Xenon Live Updater', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                                os._exit(1)
                        except:
                                xbmcgui.Dialog().ok('Xenon Live Updater', 'Error switching skin, please contact developer')
                else:
                        xbmcgui.Dialog().ok('Xenon Live Updater', 'Error switching skin, please contact developer')                        
                        
                        
                        
                 
