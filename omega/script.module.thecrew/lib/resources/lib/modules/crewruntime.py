# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file crewruntime.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''


import os
import sys
import re
import platform
from datetime import datetime
from io import open
#import traceback
from inspect import getframeinfo, stack

import xbmc
import xbmcvfs
import xbmcaddon



#from resources.lib.modules import control


class CrewRuntime:
    '''
    Global new superclass starting to run alongside the old code

    '''

    # ============================cm=
    # class variable shared by all instances
    # globals here

    transpath = xbmcvfs.translatePath

    # ============================cm=

    def __init__(self):

        '''
        # cm - can later be used on a child class as temp obj to super crewRuntime
        # super().__init__(self)
        # removed pylinting some lines for now, just setting up
        '''

        self.name = None
        self.platform = None
        self.kodiversion = None
        self.int_kodiversion = None

        self.moduleversion = None
        self.pluginversion = None
        self.addon = None
        self.toggle = None
        self.has_silent_boot = None

        self.initialize_all()

    def __del__(self):
        '''
        On destruction of the class
        '''
        self.deinit()

    def deinit(self):
        '''
        cleanup
        '''
        self.toggle = None
        self.addon = None

    def initialize_all(self):
        '''
        initialize all vars
        '''
        self.addon = xbmcaddon.Addon
        self.plugin_id = self.addon().getAddonInfo("id")
        self.pluginversion = self.addon().getAddonInfo("version")
        self.name = self.addon().getAddonInfo('name')

        self.name = self.strip_tags(text=self.name).title()
        self.platform = self._get_current_platform()

        self.module_addon = xbmcaddon.Addon("script.module.thecrew")
        self.module_id = self.module_addon.getAddonInfo(id="id")
        self.moduleversion = self.module_addon.getAddonInfo(id="version")

        self.kodiversion = self._get_kodi_version(as_string=True, as_full=True)
        #self.short_kodiversion = self._get_kodi_version(
            #as_string=True, as_full=False, as_shortened=True )
        self.int_kodiversion = self._get_kodi_version(as_string=False, as_full=False)
        self.has_silent_boot = self._has_silent_boot()

        self.toggle = 1 # cm - internal debugging

    def _has_silent_boot(self) -> bool:
        if self.get_setting('silent.boot') == 'true':
            return True
        return False

    def log_boot_option(self):
        if self.has_silent_boot:
            self.log('User enabled silent boot option')
        else:
            self.log('User disabled silent boot option')

    def _get_current_platform(self):

        platform_name = platform.uname()
        _system = platform_name[0]
        # _sysname = platform_name[1]
        # _sysrelease = platform_name[2]
        _sysversion = platform_name[3]
        # _sysmachine = platform_name[4]
        # _sysprocessor = platform_name[5]
        is_64bits = sys.maxsize > 2**32
        # pf = platform.python_version() # pylint disable=snake-case

        _64bits = '64bits' if is_64bits is True else '32bits'

        return f"{_system} {_sysversion} ({_64bits})"

    def _get_kodi_version(self, as_string=False, as_full=False):
        version_raw = xbmc.getInfoLabel("System.BuildVersion").split(" ")

        v_temp = version_raw[0]

        if as_full is False:
            version = v_temp.split(".")[0]
            fversion = ''
        else:
            v_major = v_temp.split(".")[0]
            v_minor = v_temp.split(".")[1]
            fversion = f"{v_major}.{v_minor}"
            version = ''

        if as_string is True:
            if as_full is False:
                return version
            else:
                return fversion
        return int(version)

    def log(self, msg, trace=0):
        '''
        General new log messages
        '''
        logdebug = xbmc.LOGDEBUG
        begincolor = begininfocolor = endcolor = ''


        #if self.get_setting('debug_in_color') == 'true':
            #begincolor = '[COLOR red]'
            #begininfocolor = '[COLOR lightblue]'
            #endcolor = '[/color]'

        begincolor = begininfocolor = endcolor = ''

        debug_prefix = f'{begincolor}[ {self.name} {self.pluginversion} | {self.moduleversion} | {self.kodiversion} | {self.platform} | DEBUG ]{endcolor}'
        info_prefix = f'{begininfocolor}[ {self.name} {self.pluginversion}/{self.moduleversion} | INFO ]{endcolor}'

        log_path = xbmcvfs.translatePath('special://logpath')
        filename = 'the_crew.log'
        log_file = os.path.join(log_path, filename)
        debug_enabled = self.get_setting('addon_debug')
        debug_log = self.get_setting('debug.location')

        if not debug_enabled:
            return
        try:
            if isinstance(msg, str):
                if trace == 1:
                    caller = getframeinfo(stack()[1][0])
                    #caller.filename, caller.lineno
                    head = debug_prefix

                    #failure = str(traceback.format_exc()){failure}
                    _msg = f'\n     {msg}:\n    \n--> called from file {caller.filename} @ {caller.lineno}'
                    #_msg = f'\n    {msg}'
                else:
                    head = info_prefix
                    _msg = f'\n    {msg}'

            else:
                raise Exception('c.log() msg not of type str!')


            if debug_log== '1':
                xbmc.log(f"\n\n--> addon name @ 147 = {self.name} | {self.pluginversion} | {self.moduleversion}  \n\n")

                if not os.path.exists(log_file):
                    _file = open(log_file, 'w', encoding='utf-8')#, encoding="utf8"
                    _file.close()
                with open(log_file, 'a', encoding='utf-8') as _file:#, encoding="utf8"
                    _date = datetime.now().date()
                    _time = str(datetime.now().time())
                    line = f'[{_date} {_time}] {head}: {msg}'
                    _file.write(line.rstrip('\r\n') + '\n\n')

        except Exception as exc:
            self.log(f'[ {self.name} ] Logging Failure: {exc}', 1)

    def scraper_error(self, msg, scraper, trace=0):
        """
        Logs an error message associated with a specific scraper.

        Args:
            msg (str): The error message to log.
            scraper (str): The name of the scraper where the error occurred.
            trace (int, optional): If set to 1, includes traceback information. Defaults to 0.
        """
        msg = f'\n============================================================\nScraper Error in scraper: {scraper}\n============================================================\n{msg}'
        self.log(msg, trace)


    def in_addon(self) -> bool:
        '''
        returns bool if we are inside addon
        '''
        return xbmc.getInfoLabel('Container.PluginName') == "plugin.video.thecrew"

    def get_setting(self, setting) -> str:
        '''
        return a setting value
        '''
        return xbmcaddon.Addon().getSetting(id=setting)

    def set_setting(self, setting, val) -> None:
        '''
        set a setting value
        .getSettingString
        .getSettingBool
        .getSettingNumber
        .setSettingInt
        .setSettingBool
        '''
        return xbmcaddon.Addon().setSetting(id=setting, value=val)

    def strip_tags(self, text):
        '''
        Strip the tags, added to the name in the addon.xml file
        '''

        clean = re.compile(r'\[.*?\]')
        return re.sub(clean, '', text)



c = CrewRuntime()
