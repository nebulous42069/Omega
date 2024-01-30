# -*- coding: utf-8 -*-

import os
import json

import xbmcaddon

from collections import OrderedDict

from lib.constants import *
from lib.common import translate_path, ensure_path_exists, generateMd5

ADDON = xbmcaddon.Addon()

RW_FILE = translate_path(os.path.join(ADDON.getAddonInfo('profile'), 'recently_watched.dat'))


def recently_watched_load():

    """ load recently watched from file into a variable """

    if os.path.exists( RW_FILE ):
        rw_str = open( RW_FILE ).read()
        if rw_str:
            return json.loads( rw_str, object_pairs_hook=OrderedDict )
    else:
        ensure_path_exists( ADDON.getAddonInfo('profile') )
    
    return OrderedDict({})

def recently_watched_add( name, url ):

    """ add to recently watched """

    url = url.replace( BASEURL, '' )

    if name and url:
        data = recently_watched_load()

        title_hash = generateMd5(url)

        # if exists, remove to ensure it get put at the end
        if data.get( title_hash, False ):
            del data[title_hash]

        data[title_hash] = { 'name': name, 'url': url }
        fav_file = open( RW_FILE, 'w' )
        fav_file.write(json.dumps(data))
        fav_file.close()
        return True

    return False

def recently_watched_remove( url ):

    """ remove from recently watched """

    url = url.replace( BASEURL, '' )

    if url:

        removed = False
        data = recently_watched_load()

        title_hash = generateMd5(url)

        # if exists, remove
        if data.get( title_hash, False ):
            del data[title_hash]
            removed = True

        fav_file = open( RW_FILE, 'w' )
        fav_file.write(json.dumps(data))
        fav_file.close()
        return removed

    return False
