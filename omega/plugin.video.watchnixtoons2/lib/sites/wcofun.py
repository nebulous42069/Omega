
SITE_SETTINGS = {
    'catalog': {
        'regex': r'''<li(?:\sdata\-id=\"[0-9]+\")?>\s*<a href="([^"]+).*?>([^<]+)''',
        'start': '"ddmcc"',
        'start_alt': False,
        'end': '<script>',
    },
    'episode': {
        'regex': '''<a href="([^"]+).*?>([^<]+)''',
        'start': '"sidebar_right3"',
        'end': '"sidebar-all"',
    },
    'series_search': {
        'regex': r'''<li(?:\sdata\-id=\"[0-9]+\")?>\s*<a href="([^"]+).*?>([^<]+)''',
        'start': 'submit',
        'end': '<script>',
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
        'regex': r'</h3>\s*<p>(.*?)</p>',
        'start': 'Info:',
        'end': '',
    },
    'latest': {
        'regex': r'''<div class=\"img\">\s+?<a href=\"([^\"]+)\">\s+?<img class=\"hover-img1\" src=\"([^\"]+)\">\s+?</a>\s+?</div>\s+?<div class=\"recent-release-episodes\"><a href=\".*?\" rel=\"bookmark\">(.*?)</a''',
        'start': 'fourteen columns',
        'end': '</ul>',
    },
    'latest_movies': {
        'regex': '''<a href="([^"]+).*?>([^<]+)''',
        'start': '"sidebar_right3"',
        'end': '"sidebar-all"',
    },
    'popular': {
        'regex': '''<a href="([^"]+).*?>([^<]+)''',
        'start': '"sidebar-titles"',
        'end': '</div>',
    },
    'parent': {
        'regex': r'<h2><a href=\"([^\"]+)\"(?:[^\>]+)>([^/<]+)</a>',
        'start': '"header-tag"',
        'end': '',
    },
    'chapter': {
        'regex': r'onclick=\"myFunction.*<script',
    }
}

DECODE_SOURCE_REQUIRED = True

def premium_workaround_check( html ):

    """ checks if there is a work around for current domain """

    return False
