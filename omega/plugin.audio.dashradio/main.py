# -*- coding: utf-8 -*-
# Original add-on: GPL v3. Updated station directory uses LITT Live's public catalog.
import json
import os
import sys
from urllib.parse import urlencode, parse_qsl, urlsplit
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
ROOT = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
sys.path.insert(0, os.path.join(ROOT, 'resources', 'lib'))
import catalog

BASE = sys.argv[0]
HANDLE = int(sys.argv[1])
CACHE = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'stations.json')
BUNDLED = os.path.join(ROOT, 'resources', 'stations.json')


def log(message):
    xbmc.log('[Litt Live] ' + message, xbmc.LOGWARNING)


def url(**params):
    return BASE + '?' + urlencode(params)


def station_item(station):
    item = xbmcgui.ListItem(label=station['station_name'])
    item.setInfo('video', {'title': station['station_name'],
                          'genre': station['station_genre'],
                          'plot': station.get('description') or '',
                          'mediatype': 'video'})
    logo = station.get('logo_url') or ADDON.getAddonInfo('icon')
    item.setArt({'thumb': logo, 'icon': logo,
                 'fanart': station.get('image_url') or ADDON.getAddonInfo('fanart')})
    item.setProperty('IsPlayable', 'true')
    item.addContextMenuItems([('Refresh station catalog',
                              'RunPlugin(%s)' % url(action='refresh'))])
    return item


def list_stations(stations, genre=None):
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.setPluginCategory(HANDLE, genre or 'All LITT Live stations')
    ordered = [station for name, group in catalog.groups(stations)
               for station in group if genre is None or name == genre]
    for station in ordered:
        xbmcplugin.addDirectoryItem(HANDLE, url(action='play', station=station['station_id']),
                                    station_item(station), False)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def main():
    params = dict(parse_qsl(sys.argv[2].lstrip('?')))
    action = params.get('action', '')
    stations, source = catalog.load(CACHE, BUNDLED, force=action == 'refresh', logger=log)
    if action == 'refresh':
        message = ('Station catalog updated' if source == 'live'
                   else 'Refresh unavailable; using saved stations')
        xbmcgui.Dialog().notification('LITT Live', message)
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'play':
        station = next((s for s in stations if s['station_id'] == params.get('station')), None)
        # Keep old favourites working when their stream mount still identifies
        # a current station. Do not silently play retired, arbitrary URLs.
        if station is None and params.get('video'):
            path = urlsplit(params['video']).path
            station = next((s for s in stations if urlsplit(s['stream_url']).path == path), None)
        if station is None:
            xbmcgui.Dialog().ok('LITT Live', 'This station is no longer listed. Choose a current station from the add-on.')
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        item = station_item(station)
        item.setPath(station['stream_url'])
        item.setContentLookup(False)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    elif action in ('all', 'listing'):
        genre = params.get('genre') or params.get('category')
        aliases = {'POP': 'Pop', 'Hip-Hop': 'Hip-Hop'}
        list_stations(stations, aliases.get(genre, genre))
    else:
        xbmcplugin.setContent(HANDLE, 'videos')
        xbmcplugin.setPluginCategory(HANDLE, 'LITT Live')
        item = xbmcgui.ListItem(label='All stations (%d)' % len(stations))
        item.setArt({'icon': ADDON.getAddonInfo('icon')})
        xbmcplugin.addDirectoryItem(HANDLE, url(action='all'), item, True)
        with open(os.path.join(ROOT, 'resources', 'genres.json'), encoding='utf-8') as stream:
            genre_art = json.load(stream)
        for genre, group in catalog.groups(stations):
            item = xbmcgui.ListItem(label=genre)
            item.setArt({'thumb': genre_art.get(genre) or ADDON.getAddonInfo('icon'),
                         'icon': genre_art.get(genre) or ADDON.getAddonInfo('icon')})
            xbmcplugin.addDirectoryItem(HANDLE, url(action='listing', genre=genre), item, True)
        xbmcplugin.addDirectoryItem(HANDLE, url(action='refresh'),
                                    xbmcgui.ListItem(label='Refresh station catalog'), False)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


if __name__ == '__main__':
    main()
