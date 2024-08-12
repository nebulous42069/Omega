# -*- coding: utf-8 -*-
# https://github.com/Kodi-vStream/venom-xbmc-addons

import xbmcaddon, xbmcgui, xbmc, xbmcvfs 

"""System d'importation

from resources.lib.comaddon import addon, dialog, VSlog, xbmcgui, xbmc

"""

"""
from resources.lib.comaddon import addon

addons = addon() en haut de page.

utiliser une fonction comaddon ou xbmcaddon
https://codedocs.xyz/xbmc/xbmc/class_x_b_m_c_addon_1_1xbmcaddon_1_1_addon.html

addons.VSlang(30305)
addons.getLocalizedString(30305)
addons.openSettings()

utiliser la fonction avec un autre addon

addons2 = addon('plugin.video.youtube')
addons2.openSettings()
"""


"""
Ne pas utiliser :
class addon(xbmcaddon.Addon):

L'utilisation de subclass peut provoquer des fuites de mémoire, signalé par ce message :

the python script "\plugin.video.mando\default.py" has left several classes in memory that we couldn't clean up. The classes include: class XBMCAddon::xbmcaddon::Addon

# https://stackoverflow.com/questions/26588266/xbmc-addon-memory-leak

"""
ADDONVS = xbmcaddon.Addon('plugin.video.mando')    # singleton

# class addon(xbmcaddon.Addon):
class addon():

     
    def __init__(self, addonId = None):
        self.addonId = addonId

    def openSettings(self):
        return xbmcaddon.Addon(self.addonId).openSettings() if self.addonId else ADDONVS.openSettings()
        
    def getSetting(self, key):
        return xbmcaddon.Addon(self.addonId).getSetting(key) if self.addonId else ADDONVS.getSetting(key)
     
    def setSetting(self, key, value):
        return xbmcaddon.Addon(self.addonId).setSetting(key, value) if self.addonId else ADDONVS.setSetting(key, value)
     
    def getAddonInfo(self, info):
        return xbmcaddon.Addon(self.addonId).getAddonInfo(info) if self.addonId else ADDONVS.getAddonInfo(info)
     
    def VSlang(self, lang):
        return xbmc.translatePath(xbmcaddon.Addon(self.addonId).getLocalizedString(lang)) if self.addonId else xbmc.translatePath(ADDONVS.getLocalizedString(lang))
        #Bug avec accent xbmc.translatePath(xbmcaddon.Addon('plugin.video.mando').getLocalizedString(lang)).decode('utf-8')

"""
from resources.lib.comaddon import dialog

Utilisation :
dialogs = dialog()
dialogs.VSinfo('test')
https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html
"""

DIALOG = xbmcgui.Dialog() # Singleton

class dialog():
# class dialog(xbmcgui.Dialog):

    def VSok(self, desc, title = 'vStream'):
        return DIALOG.ok(title, desc)

    def VSyesno(self, desc, title = 'vStream'):
        return DIALOG.yesno(title, desc)

    def VSselect(self, desc, title = 'vStream'):
        return DIALOG.select(title, desc)

    def numeric(self, dialogType, heading, defaultt):
        return DIALOG.numeric(dialogType, heading, defaultt)

    def VSselectqual(self, list_qual, list_url):

        if len(list_url) == 0:
            return ''
        if len(list_url) == 1:
            return list_url[0]

        ret = DIALOG.select(addon().VSlang(30448), list_qual)
        if ret > -1:
            return list_url[ret]
        return ''

    def VSinfo(self, desc, title = 'vStream', iseconds = 0, sound = False):
        if (iseconds == 0):
            iseconds = 1000
        else:
            iseconds = iseconds * 1000

        if (addon().getSetting('Block_Noti_sound') == 'true'):
            sound = True

        return DIALOG.notification(str(title), str(desc), xbmcgui.NOTIFICATION_INFO, iseconds, sound)

    def VSerror(self, e):
        return DIALOG.notification('vStream', 'Erreur: ' + str(e), xbmcgui.NOTIFICATION_ERROR, 2000), VSlog('Erreur: ' + str(e))

    def VStextView(self, desc, title = "vStream"):
        return DIALOG.textviewer(title, desc)
    
"""
from resources.lib.comaddon import progress

Utilisation : 
progress_ = progress()
progress_.VScreate(SITE_NAME)
progress_.VSupdate(progress_, total)
if progress_.iscanceled():
    break
progress_.VSclose(progress_)

dialog = progress() non recommandé
progress = progress() non recommandé
https://codedocs.xyz/xbmc/xbmc/group__python___dialog_progress.html
"""

COUNT = 0
PROGRESS = None # Singleton

class empty():

    def VSupdate(self, dialog, total, text = '', search = False):
        pass

    def iscanceled(self):
        pass

    def VSclose(self, dialog):
        pass

class progress(xbmcgui.DialogProgress):

    def VScreate(self, title = 'vStream', desc = ''):

        currentWindow = xbmcgui.getCurrentWindowId()
#         if currentWindow == 10000 or currentWindow == 10103: # home, keyboard
        if currentWindow != 10025: # videonav
            return empty()

        global PROGRESS
        if PROGRESS == None:
            self.create(title, desc)
            PROGRESS = self

        return PROGRESS

    def VSupdate(self, dialog, total, text = '', search = False):

        global PROGRESS
        if not PROGRESS:    # Déjà refermé
            return
        
        if not search and window(10101).getProperty('search') == 'true':
            return
        
        global COUNT
        COUNT += 1
        iPercent = int(float(COUNT * 100) / total)
        dialog.update(iPercent, 'Loading: ' + str(COUNT) + '/' + str(total) + " " + text)

    def VSclose(self, dialog = ''):
        global PROGRESS
        if not dialog and PROGRESS:
            dialog = PROGRESS
        if not dialog:
            return

        if window(10101).getProperty('search') == 'true':
            return
        
        PROGRESS = None
        dialog.close()

    
"""
from resources.lib.comaddon import window

window(10101).getProperty('test')
https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__window.html
"""

class window(xbmcgui.Window):

    def __init__(self, winID):
        pass

"""
from resources.lib.comaddon import listitem
listitem.setLabel('test')
https://kodi.wiki/view/InfoLabels
https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
"""

class listitem(xbmcgui.ListItem):

    #ListItem([label, label2, iconImage, thumbnailImage, path])

    def __init__(self, label = '', label2 = '', iconImage = '', thumbnailImage = '', path = ''):
        pass

"""
from resources.lib.comaddon import VSlog
VSlog('testtttttttttttt')
"""

#xbmc des fonctions pas des class
def VSlog(e, level = xbmc.LOGDEBUG):
    try:
        #rapelle l'ID de l'addon pour être appelé hors addon
        if (ADDONVS.getSetting('debug') == 'true'):
            if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
                level = xbmc.LOGINFO
            else:
                level = xbmc.LOGNOTICE
        xbmc.log('\t[PLUGIN] vStream: ' + str(e), level)
        
    except:
        pass

def VSupdate():
    return xbmc.executebuiltin('Container.Refresh')

def VSshow_busy():
    xbmc.executebuiltin('ActivateWindow(busydialog)')

def VShide_busy():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    while xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        xbmc.sleep(100)

def isKrypton():
    try:
        version = xbmc.getInfoLabel('system.buildversion')
        if version[0:2] >= '17':
            return True
        else:
            return False
    except:
        return False

#Transforme les "special" en chemin normal.
def VSPath(pathSpecial):
    if xbmc.getInfoLabel('system.buildversion')[0:2] >= '19':
        path = xbmcvfs.translatePath(pathSpecial)
    else:
        path = xbmc.translatePath(pathSpecial)
    return path
