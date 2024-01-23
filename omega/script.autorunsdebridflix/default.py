"""Autoruns 2015 fightnight"""
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import re
import sys
import json
from pathlib import Path
from urllib.parse import quote_plus, parse_qsl

class Autoruns:
	
	def __init__(self):
		self.on_pattern = '(<extension.+?xbmc.service.+?>)'
		self.off_pattern = '(<!--<extension.+?xbmc.service.+?>-->)'
		self.data_path = Path(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile')))
		self.data_file = self.data_path / 'off_items.json'
		self.pathofaddons = Path(xbmcvfs.translatePath('special://home/addons'))
	
	def get_json(self, _file):
		with open(_file, 'r', encoding='utf-8') as f:
			   return json.load(f)['items']

	def list_addons(self):
		if not self.data_path.exists():
		    self.data_path.mkdir(parents=True, exist_ok=True)
		#info directory
		self.addDir("[COLOR blue][B]Set to OFF to disable the addon's services on startup.[/B][/COLOR]", '', '', xbmcaddon.Addon().getAddonInfo('icon'))
		# get the path of addons
		if self.data_file.exists():
			off_items = self.get_json(str(self.data_file))
			for individual_addon in off_items:
				path_to_addon = self.pathofaddons / individual_addon
				addon_xml_path = path_to_addon / 'addon.xml'
				if not addon_xml_path.exists():
				  	continue
				xml_content = self.openfile(addon_xml_path)
				on_check = re.search(self.on_pattern, xml_content)
				off_check = re.search(self.off_pattern, xml_content)
				if on_check is not None and off_check is None:
					on_match = re.findall(self.on_pattern, xml_content)[0]
					content = xml_content.replace(on_match, f'<!--{on_match}-->')
					self.savefile(addon_xml_path, content)
      
		#list with addons
		listofaddons = [x for x in self.pathofaddons.iterdir() if x.is_dir()]
		off_items = []
		for individual_addon in listofaddons:
			#path to individual addon, cycle for all the addons
			if individual_addon.name == xbmcaddon.Addon().getAddonInfo('id'):
				continue
			path_to_addon = self.pathofaddons / individual_addon
			# define addon.xml path
			addon_xml_path = path_to_addon / 'addon.xml'
			if not addon_xml_path.exists():
				continue
			# check the existence of addon.xml, if true, we continue
			xml_content = self.openfile(addon_xml_path)  # get addon.xml content
			on_check = re.search(self.on_pattern, xml_content)
			off_check = re.search(self.off_pattern, xml_content)
			try:
				if on_check is not None and off_check is None:
					self.addDir(f'[B][COLOR white]{individual_addon.name}[/B] (ON)[/COLOR]',str(path_to_addon), 'change_state', xbmcaddon.Addon(individual_addon.name).getAddonInfo('icon'))  # addon with service on
				elif off_check is not None:  # addon with service off
					self.addDir(f'[B][COLOR gold]{individual_addon.name}[/B] (OFF)[/COLOR]',str(path_to_addon), 'change_state', xbmcaddon.Addon(individual_addon.name).getAddonInfo('icon'))
					off_items.append(individual_addon.name)
			except RuntimeError:
				pass
		with open(self.data_file, 'w', encoding='utf-8') as f:
			json.dump({'items': off_items}, f, indent=4)
    
	def change_state(self, name, path):
		# define addon.xml path to change
		path = Path(path)
		addon_xml_path = path / 'addon.xml'
		# get addon.xml content
		content = self.openfile(addon_xml_path)
		on_match = re.findall(self.on_pattern, content)[0]
		with open(self.data_file, 'r', encoding='utf-8') as f:
			off_items = json.load(f)['items']
		if 'COLOR gold' in name:
			# service off to on, so we change from fake variable to service variable
			off_match = re.findall(self.off_pattern, content)[0]
			content = content.replace(off_match, on_match)
			cleanname = name.replace('[B][COLOR gold]', '').replace('[/B] (OFF)[/COLOR]', '')
			if cleanname in off_items:
				off_items.remove(cleanname)
		else:
			# service on to off, so we change from service variable to fake variable
			content = content.replace(on_match, f'<!--{on_match}-->')
			off_items.append(name)

		#change state on addon.xml
		self.savefile(addon_xml_path, content)
		with open(self.data_file, 'w', encoding='utf-8') as f:
			json.dump({'items': off_items}, f, indent=4)
		# refresh the list
		xbmc.executebuiltin("Container.Refresh")
      
	def openfile(self, path_to_the_file):
	       try:
	       	with open(path_to_the_file, 'r', encoding='utf-8') as f:
	       		return f.read()
	       except (RuntimeError, ValueError, FileNotFoundError) as e:
	       	xbmc.log(f'Unable to open file: {path_to_the_file} Error Info: {e}', xbmc.LOGINFO)
	       	return

	def savefile(self, path_to_the_file, content):
	       try:
	       	with open(path_to_the_file, 'w', encoding='utf-8') as f:
	       		f.write(content)  
	       except (RuntimeError, ValueError, FileNotFoundError) as e:
	       	xbmc.log(f'Unable to open file: {path_to_the_file} Error Info: {e}', xbmc.LOGINFO)
	       	return

	def addDir(self, name, path, mode, iconimage):
		listitem = xbmcgui.ListItem(name)
		listitem.setArt({'thumb': iconimage, 'icon': iconimage})
		return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=f'{sys.argv[0]}?path={quote_plus(path)}&mode={mode}&name={quote_plus(name)}',listitem=listitem,isFolder=False)

def router():
    p = dict(parse_qsl(sys.argv[2][1:]))
    a = Autoruns()
    
    name = p.get('name', '')
    mode = p.get('mode', 'list_addons')
    path = p.get('path', '')
    
    if mode == 'list_addons':
    	a.list_addons()
    
    elif mode == 'change_state':
    	a.change_state(name, path)
    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

if __name__ == '__main__':
	router()