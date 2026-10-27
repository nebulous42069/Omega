# -*- coding: utf-8 -*-
"""Resolve installed studio artwork without downloading images on the UI thread."""
import re
import hashlib
import os
import urllib.request
import struct
import time
import xbmcaddon
import xbmcvfs

_INDEX = {}
_REMOTE = {}


def _bundle_names(path):
    """Read filenames from an XBTF resource pack; Kodi renders the packed images."""
    stream = xbmcvfs.File(path)
    try:
        header = bytes(stream.readBytes(9))
        if len(header) != 9 or header[:4] != b'XBTF':
            return {}
        result = {}
        for _ in range(struct.unpack_from('<I', header, 5)[0]):
            raw = bytes(stream.readBytes(264))
            if len(raw) != 264:
                return {}
            name = raw[:256].split(b'\0', 1)[0].decode('utf-8')
            result[name.casefold()] = name
            frames = struct.unpack_from('<I', raw, 260)[0]
            stream.seek(frames * 40, 1)
        return result
    finally:
        stream.close()


def _resource_names(pack):
    cached = _INDEX.get(pack)
    if cached and time.monotonic() - cached[0] < 300:
        return cached[1]
    names = {}
    try:
        root = xbmcaddon.Addon(pack).getAddonInfo('path').rstrip('/\\') + '/resources/'
        dirs, files = xbmcvfs.listdir(root)
        for name in files:
            if name.lower().endswith('.png'):
                names[name.casefold()] = name
            elif name.lower().endswith('.xbt'):
                names.update(_bundle_names(root + name))
    except Exception:
        # An absent/disabled resource addon simply has no matching image.
        pass
    _INDEX[pack] = (time.monotonic(), names)
    return names


def pack_logo(pack, names):
    index = _resource_names(pack)
    for name in names:
        filename = name.strip() + '.png'
        if filename.casefold() in index:
            return 'resource://%s/%s' % (pack, index[filename.casefold()])
        # Also support providers exposing their images directly through VFS.
        path = 'resource://%s/%s' % (pack, filename)
        try:
            if xbmcvfs.exists(path):
                return path
        except Exception:
            pass
    return ''


def remote_logo(url):
    if not url:
        return ''
    cached = _REMOTE.get(url)
    if cached and time.monotonic() - cached[0] < (1800 if cached[1] else 60):
        return cached[1]
    result = ''
    try:
        folder = xbmcvfs.translatePath('special://temp/x2-studio-logos/')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, hashlib.sha256(url.encode('utf-8')).hexdigest() + '.png')
        if os.path.isfile(path):
            result = path
        else:
            request = urllib.request.Request(url, headers={'Accept':'image/*'})
            with urllib.request.urlopen(request, timeout=5) as response:
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) <= 2 * 1024 * 1024 and data.startswith(b'\x89PNG\r\n\x1a\n'):
                with open(path + '.tmp', 'wb') as stream:
                    stream.write(data)
                os.replace(path + '.tmp', path)
                result = path
    except Exception:
        pass
    _REMOTE[url] = (time.monotonic(), result)
    if len(_REMOTE) > 128:
        del _REMOTE[min(_REMOTE, key=lambda k: _REMOTE[k][0])]
    return result


def choose_logo(info):
    names = []
    for field in ('logo_studio', 'studio', 'network'):
        raw = str(info.get(field) or '').strip()
        for name in [raw] + re.split(r'\s+/\s+|;|\|', raw):
            if name and name not in names:
                names.append(name)
    coloured = pack_logo('resource.images.studios.coloured', names)
    white = pack_logo('resource.images.studios.white', names)
    remote = info.get('network_logo') or info.get('studio_logo') or ''
    if coloured:
        return coloured, ''
    return remote_logo(remote) or white, ''


def classification_logo(info):
    raw = str(info.get('certification') or '').strip()
    if not raw:
        return ''
    pack = 'resource.images.classificationicons.colour'
    # Honor the pack's full country-and-classification naming scheme first.
    exact = pack_logo(pack, [raw])
    if exact:
        return exact
    rating = re.sub(r'^(?:MPAA\s*:?\s*|Rated\s+|USA?\s*:?\s*)', '', raw, flags=re.I).strip()
    rating = re.sub(r'^Rated\s+', '', rating, flags=re.I).strip().upper()
    aliases = {'PG13':'PG-13', 'NC17':'NC-17', 'TV Y7':'TV-Y7',
               'TV MA':'TV-MA', 'TV PG':'TV-PG', 'TV 14':'TV-14',
               'TV-Y7-FV':'TV-Y7'}
    rating = aliases.get(rating, rating)
    if rating in ('G','PG','PG-13','R','NC-17','TV-Y','TV-Y7','TV-G','TV-PG','TV-14','TV-MA'):
        return pack_logo(pack, ['USA ' + rating, rating])
    return ''
