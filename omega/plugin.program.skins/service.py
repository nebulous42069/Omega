#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, os, glob, sqlite3, json, base64
import xml.etree.ElementTree as ET
from urllib.request import urlopen
from urllib.request import Request
from addonvar import *
from datetime import datetime
from xml.dom.minidom import parse
	
def check_updates():
    if current_build != 'No Build Installed':
    	req = Request(buildfile, headers = headers)
    	response = urlopen(req).read()
    	version = 0.0
    	try:
    		builds = json.loads(response)['builds']
    		for build in builds:
    			if build.get('name') == current_build:
    				version = float(build.get('version'))
    	except:
    		builds = ET.fromstring(response)
    		for tag in builds.findall('build'):
    			if tag.find('name').text== current_build:
    				version = float(tag.find('version').text)
    	if version > current_version:
    		xbmcgui.Dialog().ok(addon_name, 'A new version of ' + current_build +' is available.' + '\n' + 'Installed Version: ' + str(current_version) + '\n' + 'New Version: ' + str(version) + '\n' + 'You can update from the Build Menu in ' + addon_name + '.')
    	else:
    		return