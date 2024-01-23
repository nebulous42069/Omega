import xbmc
import xbmcplugin
import xbmcaddon
import sys
import os
from .params import Params
from .switch import Xenon_Plus_Default, Xenon_FREE, Xenon_Free_Light, Xenon_FREE_NO_Trakt, Xenon_Plus_Coalition, Xenon_Plus_FEN, Xenon_Plus_NO_Trakt, Xenon_Plus_POV, Xenon_Plus_Seren, Xenon_Plus_Umbrella, Xenon_Plus_MTV, Xenon_Plus_Light, shutdown 

handle = int(sys.argv[1])

def router(paramstring):

    p = Params(paramstring)
    xbmc.log(str(p.get_params()),xbmc.LOGDEBUG)

    mode = p.get_mode()
    
    xbmcplugin.setContent(handle, 'files')
    
    if mode == 1:
        Xenon_Plus_Default()

    elif mode == 2:
        Xenon_FREE()
        
    elif mode == 3:
        Xenon_Free_Light()

    elif mode == 4:
        Xenon_FREE_NO_Trakt()

    elif mode == 5:
        Xenon_Plus_Coalition()
        
    elif mode == 6:
        Xenon_Plus_FEN()

    elif mode == 7:
        Xenon_Plus_NO_Trakt()

    elif mode == 8:
        Xenon_Plus_POV()
        
    elif mode == 9:
        Xenon_Plus_Seren()

    elif mode == 10:
        Xenon_Plus_Umbrella()
        
    elif mode == 11:
        Xenon_Plus_MTV()   

    elif mode == 12:
        Xenon_Plus_Light()        
        
    elif mode == 13:
        shutdown()        
        
    xbmcplugin.endOfDirectory(handle)
