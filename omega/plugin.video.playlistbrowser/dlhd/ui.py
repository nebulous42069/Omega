import sys
import re
from urllib.parse import parse_qs
from urllib.request import build_opener, ProxyHandler, Request
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from dlhd import resolver


def run(tool, handle, root, params=None, on_export=None):
    addon = xbmcaddon.Addon()
    params = dict(params or {})
    action = tool
    dialog = xbmcgui.Dialog()


    def config():
        port = int(addon.getSetting('DLHD_port') or '8769')
        if not 1024 <= port <= 65535:
            raise ValueError('Choose a relay port between 1024 and 65535')
        player = 'auto' if addon.getSetting('DLHD_automatic') != 'false' else resolver.SERVERS[int(addon.getSetting('DLHD_player') or '0')]
        return 'http://127.0.0.1:' + str(port), player


    def ready(origin):
        try:
            if addon.getSetting('DLHD_enabled') == 'false':
                raise ValueError('DaddyLive is disabled in Playlist Browser settings')
            # A device/VPN proxy must never handle the loopback health check.
            with build_opener(ProxyHandler({})).open(Request(origin + '/health'), timeout=3) as response:
                data = response.read(16)
            if data != b'ok':
                raise ValueError('Unexpected relay response')
        except Exception as error:
            raise ValueError('Local relay is unavailable ({}). Use View debugging log or Export debugging log; these work without the relay. Check Enable integrated DaddyLive relay in settings.'.format(type(error).__name__))


    def channel_list():
        folder = addon.getSetting('DLHD_folder') or addon.getAddonInfo('profile')
        path = folder.rstrip('/\\') + '/daddylive.m3u'
        items = {}
        if xbmcvfs.exists(path):
            source = xbmcvfs.File(path)
            try:
                content = source.read()
            finally:
                source.close()
            if isinstance(content, bytes):
                content = content.decode('utf-8-sig', 'replace')
            for line in content.splitlines():
                if line.startswith('#EXTINF:') and ',' in line:
                    header, name = line.split(',', 1)
                    match = re.search(r'tvg-id="(\d+)"', header)
                    if match and int(match.group(1)) > 0:
                        items[int(match.group(1))] = name.strip()
        return sorted(items.items(), key=lambda item: item[1].casefold()) if items else resolver.channels((addon.getSetting('DLHD_base') or 'https://dlive.sx'))


    try:
        if not action:
            for title, route in [('Browse channels and IDs / test playback', 'channels'), ('Create / refresh M3U playlist', 'export'), ('Test channel playback by ID', 'play'), ('Check local relay', 'check'), ('View debugging log', 'log'), ('View EPG matching report', 'epgreport'), ('Export debugging log', 'exportlog'), ('Settings', 'settings')]:
                xbmcplugin.addDirectoryItem(handle, root + '?action=dlhd&tool=' + route, xbmcgui.ListItem(label=title), route == 'channels')
            xbmcplugin.endOfDirectory(handle)
        elif action == 'settings':
            addon.openSettings()
        elif action == 'channels':
            xbmcplugin.setContent(handle, 'videos')
            for channel, name in channel_list():
                item = xbmcgui.ListItem(label='{}  [ID: {}]'.format(name, channel))
                item.setProperty('IsPlayable', 'true')
                xbmcplugin.addDirectoryItem(handle, root + '?action=dlhd&tool=play&channel=' + str(channel), item, False)
            xbmcplugin.endOfDirectory(handle)
        else:
            if action not in ('log', 'exportlog', 'epgreport'):
                origin, player = config()
                ready(origin)
            if action == 'epgreport':
                report_path = addon.getAddonInfo('profile').rstrip('/\\') + '/dlhd/epg-matches.json'
                if not xbmcvfs.exists(report_path):
                    raise ValueError('Create / refresh the M3U first to generate an EPG matching report.')
                source = xbmcvfs.File(report_path)
                try:
                    text = source.read()
                finally:
                    source.close()
                dialog.textviewer('EPGTalk channel matching report', text)
            elif action in ('log', 'exportlog'):
                text = 'Playlist Browser version: ' + addon.getAddonInfo('version')
                text += '\nKodi: ' + xbmc.getInfoLabel('System.BuildVersion')
                text += '\nRelay enabled: ' + str(addon.getSetting('DLHD_enabled') != 'false')
                text += '\nPort setting: ' + repr(addon.getSetting('DLHD_port'))[:16]
                for filename in ('startup.log', 'debug.log'):
                    log_path = addon.getAddonInfo('profile').rstrip('/\\') + '/dlhd/' + filename
                    text += '\n\n--- ' + filename + ' ---\n'
                    if not xbmcvfs.exists(log_path):
                        text += 'No file. The service may not have started, or this profile may not be writable.'
                        continue
                    source = xbmcvfs.File(log_path)
                    try: content = source.read()
                    finally: source.close()
                    if isinstance(content, bytes): content = content.decode('utf-8', 'replace')
                    text += content
                if action == 'log':
                    dialog.textviewer('DaddyLive debugging log', text)
                else:
                    folder = dialog.browse(0, 'Choose folder for debugging log', 'files', '', False, True)
                    if folder:
                        output = xbmcvfs.File(folder.rstrip('/\\') + '/daddylive-debug.log', 'w')
                        try:
                            if not output.write(text):
                                raise ValueError('Unable to export debugging log')
                        finally:
                            output.close()
                        dialog.ok('Log exported', 'Saved daddylive-debug.log to the selected folder.')
            elif action == 'check':
                dialog.ok(addon.getAddonInfo('name'), 'Local relay is running. This does not verify upstream stream availability.')
            elif action == 'export':
                from dlhd.exporter import refresh
                path, channel_count, logo_count, logo_status = refresh(addon, origin, on_export)
                dialog.ok('M3U created', '{} channels; {} logos ({})\n{}\nRefresh channels in Playlist Browser, then open Channel Groups.'.format(channel_count, logo_count, logo_status, xbmcvfs.translatePath(path)))
            elif action == 'play':
                channel = params.get('channel', [''])[0] or dialog.input('Channel ID', type=xbmcgui.INPUT_NUMERIC)
                if channel and channel.isdigit() and int(channel) > 0:
                    url = origin + '/stream/{}.m3u8?server={}'.format(int(channel), player)
                    item = xbmcgui.ListItem(label='Channel ' + channel, path=url)
                    item.setMimeType('application/vnd.apple.mpegurl')
                    if 'channel' in params:
                        xbmcplugin.setResolvedUrl(handle, True, item)
                    else:
                        xbmc.Player().play(url, item)
    except Exception as error:
        if action == 'play' and 'channel' in params:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        message = str(error) if isinstance(error, ValueError) else 'Operation failed ({}). Check source availability and settings.'.format(type(error).__name__)
        dialog.ok('DaddyLive tools', message)
