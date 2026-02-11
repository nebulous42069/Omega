import xbmc
import xbmcplugin
import xbmcaddon
import sys
import os
from .params import Params
from .home_switch import Xenon_Home_Layout 
from .widget_switch import Xenon_Widget_Flavors

handle = int(sys.argv[1])

def router(paramstring):

    p = Params(paramstring)
    xbmc.log(str(p.get_params()),xbmc.LOGDEBUG)

    mode = p.get_mode()
    
    xbmcplugin.setContent(handle, 'files')
    
    if mode == 1:
        Xenon_Home_Layout()

    elif mode == 2:
        Xenon_Widget_Flavors()        
        
    xbmcplugin.endOfDirectory(handle)
