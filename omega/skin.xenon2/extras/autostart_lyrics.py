"""Start CU LRC once when the fullscreen music player becomes ready."""
import time
import xbmc
import xbmcgui

LOCK = 'Xenon.AutoLyrics.Launching'
DISABLED = 'Skin.HasSetting(Disable.AutoLyrics)'


def main():
    home = xbmcgui.Window(10000)
    monitor = xbmc.Monitor()
    try:
        if time.time() - float(home.getProperty(LOCK)) < 45:
            return
    except (ValueError, TypeError):
        pass
    token = str(time.time())
    home.setProperty(LOCK, token)
    try:
        # Give the window's other onload actions time to open any first-run
        # warning. This helper never changes the current player/window itself.
        if monitor.waitForAbort(0.3):
            return
        deadline = time.monotonic() + 30
        while not monitor.abortRequested() and time.monotonic() < deadline:
            if (xbmc.getCondVisibility(DISABLED)
                    or not xbmc.getCondVisibility('Window.IsVisible(12006)')
                    or not xbmc.getCondVisibility('System.AddonIsEnabled(script.cu.lrclyrics)')):
                return
            if home.getProperty('culrc.guirunning') == 'TRUE':
                return
            # Do not open lyrics over the OSD/settings or a first-use dialog.
            busy = (xbmc.getCondVisibility('Window.IsVisible(musicosd)')
                    or xbmc.getCondVisibility('Window.IsVisible(1114)')
                    or xbmc.getCondVisibility('Window.IsVisible(1126)'))
            if xbmc.getCondVisibility('Player.HasAudio') and not busy:
                xbmc.executebuiltin('RunScript(script.cu.lrclyrics)')
                return
            if monitor.waitForAbort(0.2):
                return
    finally:
        if home.getProperty(LOCK) == token:
            home.clearProperty(LOCK)


if __name__ == '__main__':
    main()
