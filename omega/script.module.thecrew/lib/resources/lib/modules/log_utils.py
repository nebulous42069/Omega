# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file log_utils.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import os

from datetime import datetime
import xbmc
import traceback

from io import open

from resources.lib.modules import control
from resources.lib.modules.crewruntime import c

LOGDEBUG = xbmc.LOGDEBUG

name = c.name
pluginversion = c.pluginversion
moduleversion = c.moduleversion
kodiversion = c.kodiversion
sys_platform = c.platform

begincolor = begininfocolor = endcolor = ''

if control.setting('debug_in_color') == 'true':
    begincolor = '[COLOR red]'
    begininfocolor = '[COLOR lightblue]'
    endcolor = '[/color]'
DEBUGPREFIX = f'{begincolor}[ {name} {pluginversion} | {moduleversion} | {kodiversion} | {sys_platform} | DEBUG | old ]{endcolor}'
INFOPREFIX = f'{begininfocolor}[ {name} {pluginversion}/{moduleversion} | INFO ]{endcolor}'
LOGPATH = control.transPath('special://logpath/')
FILENAME = 'the_crew.log'
LOG_FILE = os.path.join(LOGPATH, FILENAME)
debug_enabled = control.setting('addon_debug')
debug_log = control.setting('debug.location')


def log(msg, trace=0):

    if not debug_enabled:
        return

    try:
        if isinstance(msg, str):
            if trace == 1:
                head = DEBUGPREFIX
                failure = str(traceback.format_exc())
                _msg = f'{msg}:\n    {failure}'
            else:
                head = INFOPREFIX
                _msg = f'\n    {msg}'

        else:
            raise TypeError('Logutils.log() msg not of type str!')

        if not debug_log == '0':
            if not os.path.exists(LOG_FILE):
                f = open(LOG_FILE, 'w', encoding='utf-8')
                f.write('\n\n\n\nstart\n')
                f.close()
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                line = ('[{} {}] {}: {}').format(datetime.now().date(), str(datetime.now().time())[:8], head, _msg)
                f.write(line.rstrip('\r\n') + '\n\n')
    except (TypeError, Exception) as e:
        try:
            xbmc.log(f'[ {name} ] Logging Failure: {e}', LOGDEBUG)
        except:
            pass
