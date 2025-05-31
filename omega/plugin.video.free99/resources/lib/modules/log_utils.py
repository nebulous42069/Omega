# -*- coding: utf-8 -*-

import os
import six
import traceback

from datetime import datetime
from io import open
from kodi_six import xbmc
from resources.lib.modules import control

LOGDEBUG = xbmc.LOGDEBUG
LOGINFO = xbmc.LOGINFO
LOGNOTICE = xbmc.LOGNOTICE if control.getKodiVersion() < 19 else xbmc.LOGINFO
LOGWARNING = xbmc.LOGWARNING
LOGERROR = xbmc.LOGERROR
LOGFATAL = xbmc.LOGFATAL
LOGNONE = xbmc.LOGNONE

version = control.addonInfo('version')
ChangeLog_head = '--[Free99 - %s - ChangeLog]--' % version
DebugLog_head = '--[Free99 - %s - DebugLog]--' % version
DEBUGPREFIX = '[Free99 - %s - DEBUG]' % version

LOGPATH = control.transPath('special://logpath/')
log_file = os.path.join(LOGPATH, 'free99.log')
changelogfile = os.path.join(control.addonPath, 'resources', 'changelog.txt')

debug_enabled = control.setting('addon.debug')
debugtime_enabled = control.setting('addon.debugtime')
debugspacer_enabled = control.setting('addon.debugspacer')


def log(msg, trace=0, level=LOGDEBUG):
    if not debug_enabled == 'true':
        return
    try:
        if trace == 1:
            failure = six.ensure_str(traceback.format_exc())
            _msg = '%s: %s' % (six.ensure_text(msg), failure)
        else:
            _msg = '%s' % six.ensure_text(msg)
        if not os.path.exists(log_file):
            f = open(log_file, 'w')
            f.close()
        with open(log_file, 'a', encoding='utf-8') as f:
            if not debugtime_enabled == 'true':
                line = '%s: %s' % (DEBUGPREFIX, _msg)
            else:
                line = '[%s %s] %s: %s' % (datetime.now().date(), str(datetime.now().time())[:8], DEBUGPREFIX, _msg)
            if not debugspacer_enabled == 'true':
                f.write(line.rstrip('\r\n') + '\n')
            else:
                f.write('' + '\n')
                f.write(line.rstrip('\r\n') + '\n')
                f.write('' + '\n')
    except Exception as e:
        xbmc.log('%s Logging Failure: %s' % (DEBUGPREFIX, e), level)
        pass


def changelog():
    try:
        control.textViewer(changelogfile, ChangeLog_head)
    except:
        log('changelog', 1)
        control.infoDialog('Error opening changelog')
        pass


def previous_changelogs():
    try:
        import requests
        previous_changelogs_link = 'https://'
        previous_changelogs_html = requests.get(previous_changelogs_link).text
        control.textViewer2(previous_changelogs_html, ChangeLog_head)
    except:
        log('previous_changelogs', 1)
        control.infoDialog('Error opening previous_changelogs')
        pass


def view_log():
    try:
        control.textViewer(log_file, DebugLog_head)
    except:
        log('view_log', 1)
        control.infoDialog('Error opening log file')
        pass


def empty_log():
    try:
        open(log_file, 'w').close()
    except:
        log('empty_log', 1)
        control.infoDialog('Error emptying log file')
        pass


