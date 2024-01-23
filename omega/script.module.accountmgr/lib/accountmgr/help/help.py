# -*- coding: utf-8 -*-
"""
	Account Manager
"""

from accountmgr.modules.control import addonPath, addonVersion, joinPath
from accountmgr.windows.textviewer import TextViewerXML

def get(file):
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	helpFile = joinPath(accountmgr_path, 'lib', 'accountmgr', 'help', file + '.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]My Accounts -  v%s - %s[/B]' % (accountmgr_version, file)
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_tmdb():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	helpFile = joinPath(accountmgr_path, 'lib', 'accountmgr', 'help', 'tmdbUser.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]My Accounts -  v%s - TMDb Login Help[/B]' % (accountmgr_version)
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_meta():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	helpFile = joinPath(accountmgr_path, 'lib', 'accountmgr', 'help', 'metaAuth.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]My Accounts -  v%s - Metadata API Help[/B]' % (accountmgr_version)
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_nondebrid():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	helpFile = joinPath(accountmgr_path, 'lib', 'accountmgr', 'help', 'nonDebrid.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]My Accounts -  v%s - Furk/Easynews/FilePursuit Help[/B]' % (accountmgr_version)
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows
