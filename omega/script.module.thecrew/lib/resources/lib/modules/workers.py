# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * Genesis Add-on
 * Copyright (C) 2015 lambda
 * 
 * - Mofidied by The Crew
 * 
 * @file workers.py
 * @package script.module.thecrew
 *
 * @copyright 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import threading


# class Thread(threading.Thread):
    # def __init__(self, target, *args):
        # self._target = target
        # self._args = args
        # threading.Thread.__init__(self)
    # def run(self):
        # self._target(*self._args)

class Thread(threading.Thread):
    def __init__(self, target, *args):
        self._target = target
        self._args = args
        threading.Thread.__init__(self, target=self._target, args=self._args)

