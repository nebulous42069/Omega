import os
import shutil
import subprocess
import xbmcgui
import xbmcvfs
import xbmc, xbmcaddon
dialog = xbmcgui.Dialog()
settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenon/')

def Xenon_Widget_Flavors():
        flavor_list = ['[B]Diggz Xenon[/B] - [COLOR chartreuse]2/11/26[/COLOR]']
        select = dialog.select('Check For Skin Updates..', flavor_list)
        if select == None:
            return          

        if select == 0:
                src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenon/resources/switch/Diggz_Xenon/settings.xml')
                dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenon/settings.xml')
                
                if os.path.exists(os.path.join(settings_path)):
                        try:
                                shutil.copyfile(src_settings, dst_settings)
                                xbmcgui.Dialog().ok('Xenon Updated', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                                os._exit(1)
                        except:
                                xbmcgui.Dialog().ok('Xenon Updater', 'Error switching skin, please contact developer')
                else:
                        xbmcgui.Dialog().ok('Xenon Updater', 'Error switching skin, please contact developer')