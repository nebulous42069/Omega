# -*- coding: utf-8 -*-
"""
    ReAuthorize - the Trakt add-on's app key (1.3.8)

    script.trakt 3.9.0 (read from the bench, 2026-10-04) no longer has its Trakt app key
    written in resources/lib/traktapi.py. The two lines are now lists of numbers

        __client_id: str = [123, 39, 116, ...]
        __client_secret: str = [35, 32, 33, ...]

    that obfuscation.py turns back into text (each character XOR 0x42). Replacing the old
    literal key did nothing, so the add-on sent ReAuthorize's sign-in under its own app key:
    the same fault as The Crew (crew_trakt.py). The swap is by line here too, and the line
    remembers what it said so core's two revoke routes can put it back.
"""

import re

import xbmc
import xbmcvfs

from libs.common import var

LOG_TAG = '[ReAuthorize Trakt]'
MARK = '# ReAuthorize; was: '
XOR = 0x42

_KEY_LINE = re.compile(r'^(?P<head>[ \t]*__client_(?P<which>id|secret)[^=\r\n]*=[ \t]*)(?P<value>\[[^\]\r\n]*\])'
                       r'(?P<tail>[ \t]*(?:#.*)?)$', re.M)
_MARKED = re.compile(r'^([ \t]*__client_(?:id|secret)[^=\r\n]*=[ \t]*)\[[^\]\r\n]*\][ \t]*' + re.escape(MARK)
                     + r'(\[[^\]\r\n]*\])[ \t]*$', re.M)


def obfuscate(text):
    """The add-on's own encoding (its obfuscation.py)."""
    return '[%s]' % ', '.join(str(ord(c) ^ XOR) for c in text)


def installed():
    return xbmcvfs.exists(var.chk_trakt)


def swap_key(text, client, secret):
    """traktapi.py with ReAuthorize's app key on the __client_id / __client_secret lines."""
    ours = {'id': obfuscate(client), 'secret': obfuscate(secret)}

    def swap(m):
        if MARK in m.group('tail') or m.group('value').replace(' ', '') == ours[m.group('which')].replace(' ', ''):
            return m.group(0)
        return '%s%s  %s%s' % (m.group('head'), ours[m.group('which')], MARK, m.group('value'))
    swapped = _KEY_LINE.sub(swap, text)
    # Older versions wrote the key itself in this file.
    return swapped.replace(var.trakt_client, client).replace(var.trakt_secret, secret)


def restore_key(text):
    """The reverse: every marked line gets back what it said before."""
    return _MARKED.sub(lambda m: m.group(1) + m.group(2), text)


def ensure_key():
    """Make sure the Trakt add-on uses ReAuthorize's app key. True if the file was changed."""
    try:
        with open(var.path_trakt, encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return False
    swapped = swap_key(text, var.client_am, var.secret_am)
    if swapped == text:
        return False
    try:
        with open(var.path_trakt, 'w', encoding='utf-8') as f:
            f.write(swapped)
        xbmc.log('%s Trakt app key set in the Trakt add-on' % LOG_TAG, xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log('%s could not set the Trakt app key in the Trakt add-on: %s' % (LOG_TAG, e), xbmc.LOGINFO)
        return False
