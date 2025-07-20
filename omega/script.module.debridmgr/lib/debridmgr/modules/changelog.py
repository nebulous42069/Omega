# -*- coding: utf-8 -*-
"""
	Debrid Manager
"""
import xbmcvfs
from debridmgr.modules.control import addonPath, addonVersion, joinPath
from debridmgr.windows.textviewer import TextViewerXML

supported_path = xbmcvfs.translatePath('special://home/addons/script.module.debridmgr/resources/skins/Default/media/common/')

def get():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(debridmgr_path, 'changelog.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager -  v%s - ChangeLog[/B]' % debridmgr_version
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_debrid():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(supported_path, 'supported_debrid.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager - Supported Debrid Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_torbox():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(supported_path, 'supported_torbox.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager - Supported Torbox Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_easydebrid():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(supported_path, 'supported_easydebrid.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager - Supported Easy Debrid Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows
	
def get_supported_offcloud():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(supported_path, 'supported_offcloud.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager - Supported OffCloud Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_ext():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(supported_path, 'supported_ext.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager - Supported External Scrapers[/B]'
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_ext_addons():
	debridmgr_path = addonPath()
	debridmgr_version = addonVersion()
	changelogfile = joinPath(supported_path, 'supported_ext_addons.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]Debrid Manager - Supported CocoScrapers Addons[/B]'
	windows = TextViewerXML('textviewer.xml', debridmgr_path, heading=heading, text=text)
	windows.run()
	del windows
