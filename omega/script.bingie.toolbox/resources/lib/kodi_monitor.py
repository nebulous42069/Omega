#!/usr/bin/python
# -*- coding: utf-8 -*-

import os,sys
from resources.lib.utils import log_msg, json, prepare_win_props, log_exception, getCondVisibility, try_decode
import xbmc

class KodiMonitor(xbmc.Monitor):
    '''Monitor all events in Kodi'''
    all_window_props = []
    monitoring_stream = False
    infopanelshown = False
    bgtasks = 0
    