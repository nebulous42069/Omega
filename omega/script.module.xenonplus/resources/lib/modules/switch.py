import os
import shutil
import subprocess
import xbmcgui
import xbmcvfs
import xbmc, xbmcaddon

def Xenon_Plus_Default():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_Default/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')

def Xenon_FREE():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_FREE/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')
                
def Xenon_Free_Light():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Free_Light/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')

def Xenon_FREE_NO_Trakt():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_FREE_NO_Trakt/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')
                
def Xenon_Plus_Coalition():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_Coalition/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')

def Xenon_Plus_FEN():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_FEN/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')
                
def Xenon_Plus_NO_Trakt():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_NO_Trakt/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')

def Xenon_Plus_POV():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_POV/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')
                
def Xenon_Plus_Seren():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_Seren/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')

def Xenon_Plus_Umbrella():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_Umbrella/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')
                
def Xenon_Plus_Light():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_Light/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')

def Xenon_Plus_MTV():
        settings_path = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/')
        src_settings = xbmcvfs.translatePath('special://home/addons/script.module.xenonplus/resources/switch/Xenon_Plus_MTV/settings.xml')
        dst_settings = xbmcvfs.translatePath('special://userdata/addon_data/skin.xenonx/settings.xml')
        
        if os.path.exists(os.path.join(settings_path)):
                try:
                        shutil.copyfile(src_settings, dst_settings)
                except:
                        pass
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'To save skin changes, please close Kodi, Press OK to force close Kodi')
                os._exit(1)
        else:
                xbmcgui.Dialog().ok('Xenon Plus Switcher', 'Error switching skin, please contact developer')                
                
        
def shutdown():
        src_includes = xbmcvfs.translatePath('special://skin/extras/switch/home/Includes_mod.xml')
        dst_includes = xbmcvfs.translatePath('special://skin/xml/Includes_mod.xml')
        src = xbmcvfs.translatePath('special://skin/extras/switch/home/movies')
        dst = xbmcvfs.translatePath('special://userdata/library/video/movies')
        
        try: 
                files_dst = os.listdir(dst)
                files_src = os.listdir(src)
                for file in files_dst:
                        file_path = os.path.join(dst, file)
                        if os.path.isfile(file_path):
                                os.remove(file_path)
                for fname in files_src:
                        shutil.copy2(os.path.join(src,fname), dst)
                shutil.copyfile(src_includes, dst_includes)
        except:
                pass
                
        xbmc.executebuiltin('ReloadSkin')
        xbmc.sleep(2000)
        xbmc.executebuiltin('RunPlugin(plugin://plugin.program.chef20/?mode=18&amp;name=Force%20Close)')
