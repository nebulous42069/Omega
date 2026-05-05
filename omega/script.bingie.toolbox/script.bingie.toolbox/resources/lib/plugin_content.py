#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
from simplecache import SimpleCache
import urllib.parse
from resources.lib.utils import log_msg, KODI_VERSION, log_exception, urlencode, getCondVisibility, try_decode

class PluginContent:
    '''Hidden plugin entry point providing some toolbox features'''
    params = {}
    win = None

    def __init__(self):
        self.cache = SimpleCache()
        self.win = xbmcgui.Window(10000)
        try:
            self.params = dict(urllib.parse.parse_qsl(sys.argv[2].replace('?', '').lower()))
            log_msg("plugin called with parameters: %s" % self.params)
            self.main()
        except Exception as exc:
            log_exception(__name__, exc)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def close(self):
        '''Cleanup Kodi Cpython instances'''
        self.cache.close()
        self.close()
        del self.win

    def main(self):
        '''main action, load correct function'''
        action = self.params.get("action", "")
        if self.win.getProperty("BingieToolboxShutdownRequested"):
            # do not proceed if kodi wants to exit
            log_msg("%s --> Not forfilling request: Kodi is exiting" % __name__, xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        else:
            try:
                if hasattr(self.__class__, action):
                    # launch module for action provided by this plugin
                    getattr(self, action)()
                else:
                    # legacy (widget) path called !!!
                    self.load_widget()
            except Exception as exc:
                log_exception(__name__, exc)

    def resourceimages(self):
        '''retrieve listing of specific resource addon images'''
        log_msg("bingietoolbox plugin resourceimages function", xbmc.LOGWINFO)
        from .resourceaddons import get_resourceimages
        addontype = self.params.get("addontype", "")
        for item in get_resourceimages(addontype, True):
            listitem = xbmcgui.ListItem(item[0], label2=item[2], path=item[1])
            listitem.setArt({"icon":item[3]})
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                        url=item[1], listitem=listitem, isFolder=False)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    @staticmethod
    def alphabet():
        '''display an alphabet scrollbar in listings'''
        all_letters = []
        if xbmc.getInfoLabel("Container.NumItems"):
            for i in range(int(xbmc.getInfoLabel("Container.NumItems"))):
                all_letters.append(xbmc.getInfoLabel("Listitem(%s).SortLetter" % i).upper())
            start_number = ""
            for number in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                if number in all_letters:
                    start_number = number
                    break
            for letter in [start_number, "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L",
                           "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]:
                if letter == start_number:
                    label = "#"
                else:
                    label = letter
                listitem = xbmcgui.ListItem(label=label)
                if letter not in all_letters:
                    lipath = "noop"
                    listitem.setProperty("NotAvailable", "true")
                else:
                    lipath = "plugin://script.bingie.toolbox/?action=alphabetletter&letter=%s" % letter
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), lipath, listitem, isFolder=False)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def alphabetletter(self):
        '''used with the alphabet scrollbar to jump to a letter'''
        if KODI_VERSION > 16:
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
        letter = self.params.get("letter", "").upper()
        jumpcmd = ""
        if letter in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            jumpcmd = "firstpage"
        elif letter in ["A", "B", "C"]:
            jumpcmd = "jumpsms2"
        elif letter in ["D", "E", "F"]:
            jumpcmd = "jumpsms3"
        elif letter in ["G", "H", "I"]:
            jumpcmd = "jumpsms4"
        elif letter in ["J", "K", "L"]:
            jumpcmd = "jumpsms5"
        elif letter in ["M", "N", "O"]:
            jumpcmd = "jumpsms6"
        elif letter in ["P", "Q", "R", "S"]:
            jumpcmd = "jumpsms7"
        elif letter in ["T", "U", "V"]:
            jumpcmd = "jumpsms8"
        elif letter in ["W", "X", "Y", "Z"]:
            jumpcmd = "jumpsms9"
        if jumpcmd:
            xbmc.executebuiltin("SetFocus(50)")
            for i in range(40):
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Input.ExecuteAction",\
                    "params": { "action": "%s" }, "id": 1 }' % (jumpcmd))
                xbmc.sleep(50)
                if xbmc.getInfoLabel("ListItem.Sortletter").upper() == letter:
                    break
