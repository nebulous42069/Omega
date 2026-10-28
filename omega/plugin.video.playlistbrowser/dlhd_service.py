"""Start diagnostics before importing the relay; retry transient startup failures."""
import os
import threading
import traceback
import xbmc
import xbmcaddon
import xbmcvfs

addon = xbmcaddon.Addon('plugin.video.playlistbrowser')
monitor = xbmc.Monitor()
folder = addon.getAddonInfo('profile').rstrip('/\\') + '/dlhd'


def startup_note(message):
    # Only internal status, exception classes and source locations: no URLs/tokens.
    xbmc.log('DLHD service: ' + message, xbmc.LOGERROR)
    try:
        xbmcvfs.mkdirs(folder)
        stream = xbmcvfs.File(folder + '/startup.log', 'w')
        try: stream.write(message)
        finally: stream.close()
    except Exception:
        pass


startup_note('Service entered; loading relay modules. Version ' + addon.getAddonInfo('version'))
while not monitor.abortRequested():
    relay = None
    serving = False
    try:
        if addon.getSetting('DLHD_enabled') == 'false':
            startup_note('Relay disabled in Playlist Browser settings.')
            break
        from dlhd.debuglog import LOG, setup, reason
        from dlhd.relay import Relay
        from dlhd.exporter import Scheduler
        log_path = setup(xbmcvfs.translatePath(folder))
        port = int(addon.getSetting('DLHD_port') or '8769')
        if not 1024 <= port <= 65535:
            raise ValueError('Relay port must be between 1024 and 65535')
        LOG.info('Integrated relay version=%s starting port=%s', addon.getAddonInfo('version'), port)
        relay = Relay(port, addon.getSetting('DLHD_base') or 'https://dlive.sx', addon.getSetting('DLHD_automatic') != 'false', log_path)
        thread = threading.Thread(target=relay.serve_forever, daemon=True)
        thread.start()
        serving = True
        startup_note('Relay listening on 127.0.0.1:' + str(relay.server_port))
        def update_cache(path, content):
            from main import dlhd_exported
            dlhd_exported(path, content)
        scheduler = Scheduler(addon, relay.origin, update_cache)
        while not monitor.waitForAbort(1):
            if not thread.is_alive():
                raise RuntimeError('Relay serving thread stopped')
            base = addon.getSetting('DLHD_base') or 'https://dlive.sx'
            if relay.base != base:
                with relay.lock:
                    relay.sessions.clear()
                    relay.selected.clear()
                    relay.failures.clear()
                    relay.blocked.clear()
                relay.base = base
            relay.automatic = addon.getSetting('DLHD_automatic') != 'false'
            try: scheduler.tick()
            except Exception as error: LOG.warning('Scheduler check failed: %s', reason(error))
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        locations = '\n'.join('{}:{} in {}'.format(os.path.basename(f.filename), f.lineno, f.name) for f in frames)
        detail = '{} errno={}\n{}'.format(type(error).__name__, getattr(error, 'errno', None), locations)
        if isinstance(error, (ImportError, ModuleNotFoundError)):
            detail += '\nModule: ' + str(getattr(error, 'name', '') or '')
        startup_note('Service failure; retrying in 15 seconds.\n' + detail)
    finally:
        if relay:
            if serving: relay.shutdown()
            relay.server_close()
    if monitor.waitForAbort(15): break
