import xbmc

def log(message, level=xbmc.LOGDEBUG):
    xbmc.log("script.moviequiz >> " + message, xbmc.LOGDEBUG)