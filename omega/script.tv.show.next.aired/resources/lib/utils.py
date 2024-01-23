#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.tv.show.next.aired
    TV Show - Next Aired
    utils.py
    Various helper methods
'''

import xbmc
import os
import sys
from traceback import format_exc
import re

DEBUG = False

ADDON_ID = "script.tv.show.next.aired"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
DATE_FORMAT = xbmc.getRegion('dateshort').lower()
if DATE_FORMAT[0] == 'd':
    DATE_FORMAT = '%d-%m-%y'
elif DATE_FORMAT[0] == 'm':
    DATE_FORMAT = '%m-%d-%y'
elif DATE_FORMAT[0] == 'y':
    DATE_FORMAT = '%y-%m-%d'

NICE_DATE_FORMAT = xbmc.getRegion('datelong').lower().replace('%d%d', '%d').replace("'", "")
for xx, yy in (('%a', '%(wday)s'), ('%b', '%(month)s'), ('%d', '%(day)s'), ('%y', '%(year)s'), ('%m', '%(mm)s')):
    NICE_DATE_FORMAT = NICE_DATE_FORMAT.replace(xx, yy)
NICE_DATE_FORMAT = re.sub(r"%[a-z]", '%(unk)s', NICE_DATE_FORMAT)
NICE_DATE_NO_YEAR = re.sub(r"(?<=\)s)[^%]*%\(year\)s[^%]*|^%\(year\)s[^%]*", ' ', NICE_DATE_FORMAT).strip()
NICE_SHORT_DATE = re.sub(r"%\(wday\)s[^%]*", '', NICE_DATE_NO_YEAR)



try:
    from multiprocessing.pool import ThreadPool
    SUPPORTS_POOL = True
except Exception:
    SUPPORTS_POOL = False


def log_msg(msg, loglevel=xbmc.LOGDEBUG):
    '''log message to kodi log'''
    msg = msg
    if DEBUG and loglevel == xbmc.LOGDEBUG:
        loglevel = xbmc.LOGINFO
    xbmc.log("%s --> %s" % (ADDON_ID, msg), level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log an exception'''
    log_msg("Exception in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGWARNING)


def process_method_on_list(method_to_run, items):
    all_items = []
    if SUPPORTS_POOL:
        pool = ThreadPool()
        try:
            all_items = pool.map(method_to_run, items)
        except Exception:
            # catch exception to prevent threadpool running forever
            log_msg(format_exc(sys.exc_info()))
            log_msg("Error in %s" % method_to_run)
        pool.close()
        pool.join()
    else:
        all_items = [method_to_run(item) for item in items]
    all_items = filter(None, all_items)
    return all_items
    
    
def try_encode(text):
    try:
        return text.encode(encoding, "ignore")
    except:
        return text


def try_decode(text):
    try:
        return text.decode(encoding, "ignore")
    except:
        return text

