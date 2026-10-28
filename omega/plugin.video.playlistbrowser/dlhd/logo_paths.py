"""Keep bundled image references portable when a Kodi build moves devices."""
import re

ROOT = 'special://home/addons/plugin.video.playlistbrowser/resources/logos/'
MARKER = '/plugin.video.playlistbrowser/resources/logos/'


def portable_logo(value):
    if not isinstance(value, str) or value.startswith(('http://', 'https://', 'special://')):
        return value
    normalized = re.sub(r'/+', '/', value.replace('\\', '/'))
    position = normalized.lower().find(MARKER)
    if position < 0:
        return value
    relative = normalized[position + len(MARKER):]
    if not relative or any(part in ('', '.', '..') for part in relative.split('/')):
        return value
    return ROOT + relative


def portable_playlist(content):
    return re.sub(r'tvg-logo="([^"\r\n]*)"',
                  lambda match: 'tvg-logo="' + portable_logo(match.group(1)) + '"', content)
