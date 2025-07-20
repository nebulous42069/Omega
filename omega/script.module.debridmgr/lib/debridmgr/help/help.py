# -*- coding: utf-8 -*-
"""
	Debrid Manager
"""

from debridmgr.modules.control import addonPath, addonVersion, joinPath
from debridmgr.windows.textviewer import TextViewerXML

def get(file):
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	helpFile = joinPath(debridmgr_path, 'lib', 'debridmgr', 'help', file + '.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - %s[/B]' % (debridmgr_version, file)
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_nondebrid():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	helpFile = joinPath(debridmgr_path, 'lib', 'debridmgr', 'help', 'nonDebrid.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - OffCloud/Easynews/FilePursuit[/B]' % (debridmgr_version)
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_service_sync():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	helpFile = joinPath(debridmgr_path, 'lib', 'debridmgr', 'help', 'service_sync.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - Auto-Sync Services Help[/B]' % (debridmgr_version)
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_restore():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	helpFile = joinPath(debridmgr_path, 'lib', 'debridmgr', 'help', 'restore.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - Restore to Default[/B]' % (debridmgr_version)
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_readme():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	helpFile = joinPath(debridmgr_path, 'lib', 'debridmgr', 'help', 'readme.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - Readme[/B]' % (debridmgr_version)
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_issues():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	helpFile = joinPath(debridmgr_path, 'lib', 'debridmgr', 'help', 'issues.txt')
	r = open(helpFile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - Reporting Issues[/B]' % (debridmgr_version)
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows
