from urllib.parse import parse_qs, urlencode, urlsplit
import xbmc
from resources.lib import Utils

def choose_player(url):
    Utils.hide_busy()
    if not url:
        return
    target = urlsplit(url.replace('&amp;', '&'))
    if target.scheme != 'plugin' or target.netloc != 'plugin.video.themoviedb.helper':
        return
    params = parse_qs(target.query)
    if params.get('info') != ['play'] or params.get('type') not in (['movie'], ['episode']):
        return
    params['ignore_default'] = ['true']
    url = 'plugin://plugin.video.themoviedb.helper/?' + urlencode(params, doseq=True)
    xbmc.executebuiltin('PlayMedia(%s)' % url)
