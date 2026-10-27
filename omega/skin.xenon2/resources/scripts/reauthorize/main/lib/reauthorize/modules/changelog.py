# -*- coding: utf-8 -*-
"""
	Auth Station
"""
import xbmcvfs
from reauthorize.modules.control import addonPath, addonVersion, joinPath
from reauthorize.windows.textviewer import TextViewerXML

def _supported_path():
	return xbmcvfs.translatePath('special://home/addons/script.module.reauthorize/resources/skins/Default/media/common/')

def get():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(accountmgr_path, 'changelog.txt')
	try:
		r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
		text = r.read()
		r.close()
	except Exception:
		text = 'No changelog available.'
	heading = '[B]ReAuthorize - v%s - Changelog[/B]' % accountmgr_version
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_trakt():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_trakt.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported Trakt Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_debrid():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_debrid.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported Debrid Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_torbox():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_torbox.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported Torbox Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_easydebrid():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_easydebrid.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported Easy Debrid Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows
	
def get_supported_offcloud():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_offcloud.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported OffCloud Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_easy():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_easy.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported Easynews Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows
	
def get_supported_filepursuit():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_file.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported FilePursuit Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows
	
def get_supported_meta():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_meta.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported Metadata Add-ons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_ext():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_ext.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported External Scrapers[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows

def get_supported_ext_addons():
	accountmgr_path = addonPath()
	accountmgr_version = addonVersion()
	changelogfile = joinPath(_supported_path(), 'supported_ext_addons.txt')
	r = open(changelogfile, 'r', encoding='utf-8', errors='ignore')
	text = r.read()
	r.close()
	heading = '[B]ReAuthorize - Supported CocoScrapers Addons[/B]'
	windows = TextViewerXML('textviewer.xml', accountmgr_path, heading=heading, text=text)
	windows.run()
	del windows
