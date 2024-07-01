# -*- coding: utf-8 -*-

import xbmc
import subprocess

class Browser():
    @staticmethod
    def open(url):
        osWin = xbmc.getCondVisibility('System.Platform.Windows')
        osOsx = xbmc.getCondVisibility('System.Platform.OSX')
        osLinux = xbmc.getCondVisibility('System.Platform.Linux')
        osAndroid = xbmc.getCondVisibility('System.Platform.Android')

        if xbmc.getCondVisibility('System.Platform.OSX'):
            # ___ Open the url with the default web browser
            xbmc.executebuiltin("System.Exec(open " + url + ")")
            proc = subprocess.Popen(['open', url])
        elif xbmc.getCondVisibility('System.Platform.Windows'):
            # ___ Open the url with the default web browser
            proc = subprocess.Popen(['cmd.exe', '/c', 'start', url])
        elif osLinux and not osAndroid:
            # ___ Need the xdk-utils package
            proc = subprocess.Popen(['xdg-open', url])
        elif osAndroid:
            # ___ Open media with standard android web browser
            xbmc.executebuiltin("StartAndroidActivity(com.android.browser,android.intent.action.VIEW,," + url + ")")

            # # ___ Open media with Mozilla Firefox
            # xbmc.executebuiltin("StartAndroidActivity(org.mozilla.firefox,android.intent.action.VIEW,," + url + ")")
            #
            # # ___ Open media with Chrome
            # xbmc.executebuiltin("StartAndroidActivity(com.android.chrome,,," + url + ")")
