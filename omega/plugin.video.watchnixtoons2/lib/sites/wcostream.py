import re
import six

from lib.constants import *
from lib.network import request_helper

SITE_SETTINGS = {
    'catalog': {
        'regex': r'''<li(?:\sdata\-id=\"[0-9]+\")?>\s*<a href=\"([^\"]+)\".*?>([^<]+)''',
        'start': '"anime-search"',
        'start_alt': '<div class="clear">',
        'end': '"bartitle"',
    },
    'episode': {
        'regex': '''<a href="([^"]+).*?>([^<]+)''',
        'start': '"catlist-listview"',
        'end': '</ul>',
    },
    'series_search': {
        'regex': r'''<a href="([^"]+).*?>([^<]+)</a>''',
        'start': 'aramamotoru',
        'end': 'cizgiyazisi',
    },
    'episode_search': {
        'regex': '''<a href="([^"]+)[^>]*>([^<]+)</a''',
        'start': 'submit',
        'end': 'cizgiyazisi',
    },
    'genre': {
        'regex': '''<a.*?"([^"]+).*?>(.*?)</''',
        'start': r'ddmcc">',
        'end': r'</div></div>',
    },
    'thumbnail': {
        'regex': '',
        'start': 'og:image" content="',
        'end': '',
    },
    'page_meta': {
        'regex': 'href="([^"]+)',
        'start': '"header-tag"',
        'end': '',
    },
    'page_plot': {
        'regex': r'class=\"iltext\"><p>(.*?)</p>',
        'start': 'katcont',
        'end': '',
    },
    'latest': {
        'regex': r'''<li><a href=\"([^\"]+)\" rel=\"bookmark\" ()title=\"(?:[^\"]+)\">\s*([^<]+)<''',
        'start': '="vsbaslik"',
        'end': '</ul>',
    },
    'latest_movies': {
        'regex': '''<li><a href="([^"]+).*?>([^<]+)''',
        'start': '"cat-listview cat-listbsize"',
        'end': '</ul>',
    },
    'popular': {
        'regex': '''<a href="([^"]+).*?>([^<]+)''',
        'start': 'class="menustyle">',
        'end': '</div>',
    },
    'parent': {
        'regex': r'class=\"ildate\">\s*<a href=\"([^\"]+)\"(?:[^\>]+)>([^/<]+)</a>',
        'start': '"lalyx"',
        'end': '',
    },
    'chapter': {
        'regex': r'<iframe id=\"(?:[a-zA-Z]+)uploads(?:[0-9]+)\" src=\"([^\"]+)\"',
    }
}

DECODE_SOURCE_REQUIRED = False

def premium_workaround_check( html ):

    """ checks if there is a work around for current domain """

    # get playlist link
    playlist_url = re.search(r'<a href="([^"]+)">Watch on Playlist</a>', html).group(1)

    if playlist_url:
        html = request_helper(playlist_url if playlist_url.startswith('http') else BASEURL + playlist_url).text
        guid = re.search(r'if\(liste\[i\]\[\"mediaid\"\] == ([0-9]+)\) {', html).group(1)
        if guid:
            playlist_url = re.search(r'playlist: \"(/playlist-cat-rss/[0-9]+\?[^\"]+)\",', html).group(1)
            if playlist_url:
                rss = request_helper(playlist_url if playlist_url.startswith('http') else BASEURL + playlist_url).text
                video_url = re.search(r'<guid>' + six.ensure_str( guid ) + r'</guid>\s*<jwplayer:image>(?:[^<]+)</jwplayer:image>\s*<jwplayer:source file=\"([^\"]+)\"', rss).group(1)
                if video_url:
                    return video_url

    return False
