from lib.tools import *
import xbmcgui
from lib.pvrmetadata import PVRMetaData

Pmd = PVRMetaData()

content_types = dict({'MyPVRChannels.xml': 'channels', 'MyPVRGuide.xml': 'tvguide', 'DialogPVRInfo.xml': 'info',
                      'MyPVRRecordings.xml': 'recordings', 'MyPVRTimers.xml': 'timers', 'MyPVRSearch.xml': 'search'})

win = xbmcgui.Window(10000)


def pvrartwork(current_item):

    prefix = 'PVR.Artwork'
    current_content = None

    if xbmc.getCondVisibility('Container(%s).Scrolling') % xbmcgui.getCurrentWindowId() or \
            win.getProperty('%s.Lookup' % prefix) == 'busy':
        xbmc.sleep(500)
        xbmc.log('Artwork module is busy or scrolling is active, return')
        return current_item

    # check if Live TV or PVR related window is active

    for pvr_content in content_types:
        if xbmc.getCondVisibility('Window.IsActive(%s)' % pvr_content):
            current_content = content_types.get(pvr_content, None)
            break

    if current_content is None and xbmc.getCondVisibility('VideoPlayer.Content(LiveTV)'): current_content = 'livetv'

    # if no pvr related window there, clear properties and return
    if current_content is None:
        if win.getProperty('%s.present' % prefix) == 'true': Pmd.clear_properties(prefix)
        return ''

    label = 'VideoPlayer' if current_content == 'livetv' else 'ListItem'
    title = xbmc.getInfoLabel('%s.Title' % label)
    if label == 'ListItem' and not title: title = xbmc.getInfoLabel('%s.Label' % label)
    channel = xbmc.getInfoLabel('%s.ChannelName' % label)
    genre = xbmc.getInfoLabel('%s.Genre' % label)
    year = xbmc.getInfoLabel('%s.Year' % label)

    if not (title or channel): return ''

    if current_item != '%s-%s' % (title, channel) and win.getProperty('%s.Lookup' % prefix) != 'busy':
        try:
            Pmd.get_pvr_artwork(prefix, title, channel, genre, year, manual_select=False, ignore_cache=False)
        except:
            win.clearProperty('%s.Lookup' % prefix)
            xbmc.log('PVR Artwork module error', xbmcgui.NOTIFICATION_ERROR)

    return '%s-%s' % (title, channel)


if __name__ == '__main__':
    current_item = ''
    monitor = xbmc.Monitor()
    xbmc.log('PVR Artwork module wrapper started', level=xbmc.LOGINFO)

    while not monitor.abortRequested():
        if monitor.waitForAbort(0.5): break
        if xbmc.getCondVisibility('Skin.HasSetting(Skin_enablePvrArtwork)'):
            current_item = pvrartwork(current_item)

    xbmc.log('PVR Artwork module wrapper finished', level=xbmc.LOGINFO)
