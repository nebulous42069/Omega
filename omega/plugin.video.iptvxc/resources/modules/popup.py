#!/usr/bin/python                                                          #
# -*- coding: utf-8 -*-                                                    #
############################################################################
#							  /T /I										   #
#							   / |/ | .-~/								   #
#						   T\ Y	 I	|/	/  _							   #
#		  /T			   | \I	 |	I  Y.-~/							   #
#		 I l   /I		T\ |  |	 l	|  T  /								   #
#	  T\ |	\ Y l  /T	| \I  l	  \ `  l Y								   #
# __  | \l	 \l	 \I l __l  l   \   `  _. |								   #
# \ ~-l	 `\	  `\  \	 \ ~\  \   `. .-~	|								   #
#  \   ~-. "-.	`  \  ^._ ^. "-.  /	 \	 |								   #
#.--~-._  ~-  `	 _	~-_.-"-." ._ /._ ." ./								   #
# >--.	~-.	  ._  ~>-"	  "\   7   7   ]								   #
#^.___~"--._	~-{	 .-~ .	`\ Y . /	|								   #
# <__ ~"-.	~		/_/	  \	  \I  Y	  : |								   #
#	^-.__			~(_/   \   >._:	  | l______							   #
#		^--.,___.-~"  /_/	!  `-.~"--l_ /	   ~"-.						   #
#			   (_/ .  ~(   /'	  "~"--,Y	-=b-. _)					   #
#				(_/ .  \  Fire TV Guru/ l	   c"~o \					   #
#				 \ /	`.	  .		.^	 \_.-~"~--.	 )					   #
#				  (_/ .	  `	 /	   /	   !	   )/					   #
#				   / / _.	'.	 .':	  /		   '					   #
#				   ~(_/ .	/	 _	`  .-<_								   #
#					 /_/ . ' .-~" `.  / \  \		  ,z=.				   #
#					 ~( /	'  :   | K	 "-.~-.______//					   #
#					   "-,.	   l   I/ \_	__{--->._(==.				   #
#						//(		\  <	~"~"	 //						   #
#					   /' /\	 \	\	  ,v=.	((						   #
#					 .^. / /\	  "	 }__ //===-	 `						   #
#					/ / ' '	 "-.,__ {---(==-							   #
#				  .^ '		 :	T  ~"	ll								   #
#				 / .  .	 . : | :!		 \								   #
#				(_/	 /	 | | j-"		  ~^							   #
#				  ~-<_(_.^-~"											   #
#																		   #
############################################################################

#############################=IMPORTS=######################################
	#Kodi Specific
import xbmc,xbmcaddon,xbmcgui,xbmcplugin,xbmcvfs
	#Python Specific
import os,sys,glob,webbrowser

############################################################################
	#Addon Specific
from . import tools


##########################=VARIABLES=#######################################

ADDON = xbmcaddon.Addon()
ADDONPATH = ADDON.getAddonInfo("path")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_ID = ADDON.getAddonInfo('id')

DIALOG         = xbmcgui.Dialog()
DP             = xbmcgui.DialogProgress()
HOME           = xbmcvfs.translatePath('special://home/')
ADDONS         = os.path.join(HOME,     'addons')
USERDATA       = os.path.join(HOME,     'userdata')
PLUGIN         = os.path.join(ADDONS,   ADDON_ID)
PACKAGES       = os.path.join(ADDONS,   'packages')
ADDONDATA      = os.path.join(USERDATA, 'addon_data', ADDON_ID)
FANART         = os.path.join(ADDONPATH,   'fanart.jpg')
ICON           = os.path.join(ADDONPATH,   'icon.png')
ART            = os.path.join(ADDONPATH,   'resources', 'art')
SKINFOLD       = os.path.join(ADDONPATH,   'resources', 'skins', 'Default', 'media')
ADVANCED       = os.path.join(USERDATA,  'advancedsettings.xml')
KODIV          = float(xbmc.getInfoLabel("System.BuildVersion")[:4])
ADDONTITLE     = ADDON_NAME
COLOR1         = 'white'
COLOR2         = 'blue'
SIGNUP_URL     = ''
############################################################################

ACTION_PREVIOUS_MENU 			=  10	## ESC action
ACTION_NAV_BACK 				=  92	## Backspace action
ACTION_MOVE_LEFT				=   1	## Left arrow key
ACTION_MOVE_RIGHT 				=   2	## Right arrow key
ACTION_MOVE_UP 					=   3	## Up arrow key
ACTION_MOVE_DOWN 				=   4	## Down arrow key
ACTION_MOUSE_WHEEL_UP 			= 104	## Mouse wheel up
ACTION_MOUSE_WHEEL_DOWN			= 105	## Mouse wheel down
ACTION_MOVE_MOUSE 				= 107	## Down arrow key
ACTION_SELECT_ITEM				=   7	## Number Pad Enter
ACTION_BACKSPACE				= 110	## ?
ACTION_MOUSE_LEFT_CLICK 		= 100
ACTION_MOUSE_LONG_CLICK 		= 108

def autoConfigQ():
	class FTGac(xbmcgui.WindowXMLDialog):
		def __init__(self,*args,**kwargs):
			self.title   ='[COLOR %s]Quick Advanced Settings Configurator[/COLOR]' % (COLOR2)
			freeMemory = int(float(tools.getInfo('System.Memory(free)')[:-2])*.33)
			recMemory = int(float(tools.getInfo('System.Memory(free)')[:-2])*.23)
			self.videomin = 0; self.videomax = freeMemory if freeMemory < 2000 else 2000
			self.recommendedVideo = recMemory if recMemory < 500 else 500; self.currentVideo = self.recommendedVideo
			current1 = '[COLOR %s]Video Cache Size[/COLOR]=[COLOR %s]%s MB[/COLOR]' % (COLOR1, COLOR2, self.currentVideo)
			recommended1 = '[COLOR %s]Video Cache Size:[/COLOR] [COLOR %s]%s MB[/COLOR]' % (COLOR1, COLOR2, self.recommendedVideo)
			self.curlmin = 0; self.curlmax = 20
			self.recommendedCurl = 10; self.currentCurl = self.recommendedCurl
			curlpos = tools.percentage(self.currentCurl, self.curlmax)
			recommended2 = '[COLOR %s]CURL Timeout/CURL Low Speed:[/COLOR] [COLOR %s]%ss[/COLOR]' % (COLOR1, COLOR2, self.recommendedCurl)
			self.recommendedRead = 5; self.currentRead = self.recommendedRead
			recommended3 = '[COLOR %s]Read Buffer Factor:[/COLOR] [COLOR %s]%s[/COLOR]' % (COLOR1, COLOR2, self.recommendedRead)
			recommended4 = '[COLOR %s]Buffer Mode:[/COLOR] [COLOR %s]2[/COLOR]' %(COLOR1, COLOR2)
			self.msgbox='[COLOR %s]These are the best settings currently for your device.\n\nChoose write and these will be written to the advancesettings.xml[/COLOR]\r\n\r\n%s\r\n%s\r\n%s\r\n%s' %(COLOR1, recommended4, recommended1, recommended3, recommended2)
		
		def onInit(self):
			self.header    = 100
			self.Tbox      = 101
			self.writeAS  = 201
			self.exit = 202
			self.show_set()
			
		def show_set(self):
			self.getControl(self.header).setLabel(self.title)
			self.getControl(self.Tbox).setText(self.msgbox)
			self.setFocusId(self.exit)
		
		def doWrite(self):
			buffermode = 2
			if os.path.exists(ADVANCED):
				choice = DIALOG.yesno(ADDONTITLE, "[COLOR %s]There is currently an active [COLOR %s]AdvancedSettings.xml[/COLOR], would you like to remove it and continue?[/COLOR]" % (COLOR2, COLOR1), yeslabel="[B][COLOR green]Remove Settings[/COLOR][/B]", nolabel="[B][COLOR red]Cancel Write[/COLOR][/B]")
				if choice == 0: return
				try: os.remove(ADVANCED)
				except: f = open(ADVANCED, 'w'); f.close()
			if KODIV < 17:
				with open(ADVANCED, 'w+') as f:
					f.write('<advancedsettings>\n')
					f.write('	<network>\n')
					f.write('		<buffermode>%s</buffermode>\n' % buffermode)
					f.write('		<cachemembuffersize>%s</cachemembuffersize>\n' % int(self.currentVideo*1024*1024))
					f.write('		<readbufferfactor>%s</readbufferfactor>\n' % self.currentRead)
					f.write('		<curlclienttimeout>%s</curlclienttimeout>\n' % self.currentCurl)
					f.write('		<curllowspeedtime>%s</curllowspeedtime>\n' % self.currentCurl)
					f.write('	</network>\n')
					f.write('</advancedsettings>\n')
				f.close()
			else:
				with open(ADVANCED, 'w+') as f:
					f.write('<advancedsettings>\n')
					f.write('	<cache>\n')
					f.write('		<buffermode>%s</buffermode>\n' % buffermode)
					f.write('		<memorysize>%s</memorysize>\n' % int(self.currentVideo*1024*1024))
					f.write('		<readfactor>%s</readfactor>\n' % self.currentRead)
					f.write('	</cache>\n')
					f.write('	<network>\n')
					f.write('		<curlclienttimeout>%s</curlclienttimeout>\n' % self.currentCurl)
					f.write('		<curllowspeedtime>%s</curllowspeedtime>\n' % self.currentCurl)
					f.write('	</network>\n')
					f.write('</advancedsettings>\n')
				f.close()
				tools.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), '[COLOR %s]AdvancedSettings.xml have been written[/COLOR]' % COLOR2)
			self.CloseWindow()

		def onClick(self, controlId):
			if (controlId == self.writeAS): 
				self.doWrite()
			if (controlId == self.exit): 
				#xbmc.executebuiltin("Action(ParentDir,%s)" % xbmcgui.getCurrentWindowId())
				self.doCancel()

		def doCancel(self):
			self.close()

		def onAction(self,action):
			if   action == ACTION_PREVIOUS_MENU: self.doCancel()
			elif action == ACTION_NAV_BACK: self.doCancel()

		def CloseWindow(self):
			self.close()
	
	FTGw = FTGac('advanced_settings.xml', ADDON.getAddonInfo('path'), 'Default')
	FTGw.doModal()
	del FTGw 

def popup():
	class MyWindow(xbmcgui.WindowXMLDialog):
		def __init__(self,*args,**kwargs):
			self.title   ='[COLOR %s][B]Welcome to insert iptvservice here[/B][/COLOR]' % (COLOR1)
			line1 = '[COLOR %s]Fast service that offers something..... [/COLOR]' % (COLOR1)
			line2 = '[COLOR %s]Great customer service & fast response![/COLOR]' % (COLOR1)
			line3 = '[COLOR %s]If you have an account press next.[/COLOR]' % (COLOR1)
			line4 = '[COLOR %s]If you need an account press Sign Up[/COLOR]' %(COLOR1)
			
			self.msgbox='\r\n\r\n%s\r\n%s\r\n%s\r\n%s' %(line1, line2, line3, line4)
		
		def onInit(self):
			self.header    = 100
			self.Tbox      = 101
			self.signup  = 201
			self.haveacc = 202
			self.exit = 203
			self.show_set()
			
		def show_set(self):
			self.getControl(self.header).setLabel(self.title)
			self.getControl(self.Tbox).setText(self.msgbox)
			self.setFocusId(self.exit)
		
		def opensite(self):
			if xbmc.getCondVisibility('system.platform.android'):
				xbmc.executebuiltin('StartAndroidActivity(,android.intent.action.VIEW,,%s)' % (SIGNUP_URL) )
			if xbmc.getCondVisibility('system.platform.osx'):
				os.system("open -a /Applications/Safari.app %s") % (SIGNUP_URL)
			else:
				webbrowser.open(SIGNUP_URL)

		def onClick(self, controlId):
			if (controlId == self.signup): 
				self.opensite()
			if (controlId == self.exit): 
				xbmc.executebuiltin("Action(ParentDir,%s)" % xbmcgui.getCurrentWindowId())
				self.doCancel()
			if (controlId == self.haveacc): 
				xbmc.executebuiltin('ActivateWindow(10025, "plugin://%s/?mode=start&signin=true", return)' % ADDON_ID)
				self.doCancel()
				
		
		def doCancel(self):
			self.close()

		def onAction(self,action):
			if   action == ACTION_PREVIOUS_MENU: self.doCancel()
			elif action == ACTION_NAV_BACK: self.doCancel()

		def CloseWindow(self):
			self.close()
	
	popup = MyWindow('popup.xml', ADDON.getAddonInfo('path'), 'Default')
	popup.doModal()
	del popup 