"""Launch IMDb Trailers for the explicitly selected video-view container."""
import re
import sys
from urllib.parse import urlencode
import xbmc
import xbmcgui


def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        xbmc.log('[X2 View Trailer] Invalid view container ID', xbmc.LOGERROR)
        return
    view = sys.argv[1]
    prefix = 'Container(%s).ListItem.' % view
    def info(field):
        return xbmc.getInfoLabel(prefix + field).strip()
    if xbmc.getCondVisibility(prefix + 'IsParentFolder'):
        return
    kind = (info('DBType') or info('MediaType') or info('Property(tmdb_type)')).lower()
    if kind and kind not in ('movie', 'movies', 'tv', 'tvshow', 'tvshows'):
        return
    is_tv = kind in ('tv', 'tvshow', 'tvshows') or (not kind and xbmc.getCondVisibility('Container(%s).Content(tvshows)' % view))
    title = (info('TVShowTitle') or info('Title') or info('Label')) if is_tv else (info('Title') or info('Label'))
    imdb = next((v for v in (info('UniqueID(imdb)'), info('IMDBNumber')) if re.fullmatch(r'tt\d+', v)), '')
    if not imdb and not title:
        xbmcgui.Dialog().notification('Trailer', 'No title or IMDb ID is available.')
        return
    if not xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.imdb.trailers)'):
        xbmcgui.Dialog().ok('Trailer', 'IMDb Trailers is missing or disabled.')
        return
    query = {'action': 'play_id', 'imdb': imdb} if imdb else {
        'action': 'search_word', 'keyword': title + (' ' + info('Year') if info('Year') else '')}
    xbmc.log('[X2 View Trailer] View %s: %s for %r' % (view, query['action'], title), xbmc.LOGINFO)
    xbmc.executebuiltin('PlayMedia(plugin://plugin.video.imdb.trailers/?%s)' % urlencode(query))


if __name__ == '__main__':
    main()
