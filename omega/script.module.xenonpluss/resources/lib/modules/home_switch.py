import os
import shutil
import subprocess
import xbmcgui
import xbmcvfs
import xbmc, xbmcaddon
dialog = xbmcgui.Dialog()

def Xenon_Home_Layout():
        widget_list = ['Xenon- NO TRAKT ', 'Xenon -Movies And TV Shows', 'Xenon- Movies, TV Shows, And Trakt', 'Xenon -No Widgets']
        select = dialog.select('Xenon Flavors - Choose Your Home Screen Layout!',widget_list)
        if select == None:
            return
                
        if select == 0:
                xbmc.executebuiltin("Skin.SetString(HomeItem.1.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.1.Master,false)")                
                xbmc.executebuiltin("Skin.SetString(HomeItem.2.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.2.Master,false)")         
                xbmc.executebuiltin("Skin.SetString(HomeItem.3.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.3.Master,false)")                
                xbmc.executebuiltin("Skin.SetString(HomeItem.4.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.4.Master,false)")        
                xbmc.executebuiltin("Skin.SetString(homeitem.5.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.5.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.6.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.6.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.7.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.7.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.8.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.8.master, true)")                
                xbmc.executebuiltin("Skin.SetString(homeitem.9.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.9.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.10.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.10.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.11.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.11.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.12.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.12.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.13.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.13.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.14.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.14.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.15.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.15.master, false)")                 
                xbmc.executebuiltin("Skin.SetString(subsettings.1.label,[COLOR chartreuse]X.Plus-No Trakt[/COLOR])")                
                xbmc.executebuiltin("ReloadSkin")
                     
                
        if select == 1:
                xbmc.executebuiltin("Skin.SetString(HomeItem.1.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.1.Master,false)")                
                xbmc.executebuiltin("Skin.SetString(HomeItem.2.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.2.Master,false)")         
                xbmc.executebuiltin("Skin.SetString(HomeItem.3.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.3.Master,false)")                
                xbmc.executebuiltin("Skin.SetString(HomeItem.4.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.4.Master,false)")        
                xbmc.executebuiltin("Skin.SetString(homeitem.5.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.5.master, false)")        
                xbmc.executebuiltin("Skin.SetString(homeitem.6.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.6.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.7.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.7.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.8.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.8.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.9.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.9.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.10.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.10.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.11.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.11.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.12.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.12.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.13.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.13.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.14.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.14.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.15.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.15.master, true)")               
                xbmc.executebuiltin("Skin.SetString(subsettings.1.label,[COLOR chartreuse]X.Plus-MTV[/COLOR])")                
                xbmc.executebuiltin("ReloadSkin")
                
        if select == 2:
                xbmc.executebuiltin("Skin.SetString(HomeItem.1.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.1.Master,false)")                
                xbmc.executebuiltin("Skin.SetString(HomeItem.2.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.2.Master,false)")         
                xbmc.executebuiltin("Skin.SetString(HomeItem.3.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.3.Master,false)")                
                xbmc.executebuiltin("Skin.SetString(HomeItem.4.Master,false)")
                xbmc.executebuiltin("Skin.SetBool(HomeItem.4.Master,false)")        
                xbmc.executebuiltin("Skin.SetString(homeitem.5.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.5.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.6.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.6.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.7.master, false)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.7.master, false)")
                xbmc.executebuiltin("Skin.SetString(homeitem.8.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.8.master, true)")                
                xbmc.executebuiltin("Skin.SetString(homeitem.9.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.9.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.10.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.10.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.11.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.11.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.12.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.12.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.13.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.13.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.14.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.14.master, true)")
                xbmc.executebuiltin("Skin.SetString(homeitem.15.master, true)")
                xbmc.executebuiltin("Skin.SetBool(homeitem.15.master, true)")               
                xbmc.executebuiltin("Skin.SetString(subsettings.1.label,[COLOR chartreuse]X.Plus-MTV+T[/COLOR])")                
                xbmc.executebuiltin("ReloadSkin")                  
                
        if select == 3:
                xbmc.executebuiltin("Skin.SetString(HomeItem.1.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.2.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.3.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.4.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.5.Widget, None)")  
                xbmc.executebuiltin("Skin.SetString(HomeItem.6.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.7.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.8.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.9.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.10.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.11.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.12.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.13.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.14.Widget, None)")
                xbmc.executebuiltin("Skin.SetString(HomeItem.15.Widget, None)")                 
                xbmc.executebuiltin("Skin.SetString(subsettings.1.label,[COLOR chartreuse]X.Plus-No Widgets[/COLOR])")                
                xbmc.executebuiltin("ReloadSkin")                
                              
                
                
                
