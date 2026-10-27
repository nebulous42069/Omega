# -*- coding: utf-8 -*-
"""Resolve a trailer from the selected carousel container only when UP is pressed."""
import sys
from urllib.parse import urlencode
import xbmc
import xbmcgui


def main():
    xbmc.log('[X2 Carousel Trailer] UP helper started; arguments=%r' % sys.argv[1:], xbmc.LOGINFO)
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        xbmc.log('[X2 Carousel Trailer] Invalid container argument.', xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Widget trailer', 'The widget container ID was not resolved. Please send the Kodi log.')
        return
    prefix = 'Container(%s).ListItem.' % sys.argv[1]
    def info(field):
        return xbmc.getInfoLabel(prefix + field).strip()
    tail = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != 'primary' else ''
    hint = xbmc.getInfoLabel('Container(9000).ListItem.Property(widgetType%s)' % tail).lower()
    kind = (info('DBType') or info('MediaType') or info('Property(tmdb_type)')).lower()
    if kind in ('tv', 'tvshow', 'tvshows', 'episode', 'episodes') or hint in ('tv', 'tvshow', 'tvshows', 'episode', 'episodes'):
        kind = 'tvshow'
    elif not kind:
        kind = 'tvshow' if info('TVShowTitle') else 'movie'
    imdb = info('UniqueID(imdb)') or info('IMDBNumber')
    if not imdb.startswith('tt'):
        imdb = ''
    values = {'imdb': imdb, 'tmdb': info('Property(tmdb_id)') or info('UniqueID(tmdb)'),
              'tmdbshow': info('Property(tmdbshow_id)'), 'dbtype': kind,
              'mediatype': kind, 'title': info('TVShowTitle') if kind == 'tvshow' else (info('Title') or info('Label')),
              'tvshowtitle': info('TVShowTitle'), 'year': info('Year')}
    xbmc.log('[X2 Carousel Trailer] Selected item: type=%s, title=%r, imdb=%r, tmdb=%r' % (kind, values['title'], imdb, values['tmdb']), xbmc.LOGINFO)
    if not xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.imdb.trailers)'):
        xbmcgui.Dialog().ok('Widget trailer', 'IMDb Trailers is missing or disabled.')
        return
    if imdb:
        query = {'action': 'play_id', 'imdb': imdb}
    else:
        keyword = values['title'] or info('Label')
        if not keyword:
            xbmcgui.Dialog().ok('Widget trailer', 'No movie title or IMDb ID is available for this widget item.')
            return
        if values['year']:
            keyword += ' ' + values['year']
        query = {'action': 'search_word', 'keyword': keyword}
    url = 'plugin://plugin.video.imdb.trailers/?' + urlencode(query)
    xbmc.log('[X2 Carousel Trailer] Launching IMDb Trailers: %s' % query['action'], xbmc.LOGINFO)
    xbmc.executebuiltin('PlayMedia(%s)' % url)



if __name__ == '__main__':
    main()
