"""One Kodi service entry starts the independent relay and cache workers."""
import os
import runpy
import threading
import xbmc
import xbmcaddon


def run():
    addon = xbmcaddon.Addon('plugin.video.playlistbrowser')
    root = addon.getAddonInfo('path')
    xbmc.log('Playlist Browser service bootstrap version=' + addon.getAddonInfo('version'), xbmc.LOGINFO)

    def refresh_worker():
        try:
            runpy.run_path(os.path.join(root, 'service.py'), run_name='__main__')
        except Exception as error:
            xbmc.log('Playlist Browser cache service stopped: ' + type(error).__name__, xbmc.LOGERROR)

    worker = threading.Thread(target=refresh_worker, name='PlaylistBrowserCache', daemon=True)
    worker.start()
    try:
        runpy.run_path(os.path.join(root, 'dlhd_service.py'), run_name='__main__')
    finally:
        # If relay is disabled, the cache worker must still live until Kodi exits.
        monitor = xbmc.Monitor()
        while worker.is_alive() and not monitor.waitForAbort(1):
            pass
        worker.join(timeout=2)


if __name__ == '__main__':
    run()
