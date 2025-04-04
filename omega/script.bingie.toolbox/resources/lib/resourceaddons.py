#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import urllib.request, urllib.error, urllib.parse
from resources.lib.utils import KODI_VERSION, ADDON_ID, log_exception, kodi_json, getCondVisibility, try_decode
from resources.lib.dialogselect import DialogSelect
import re
from simplecache import SimpleCache

def setresourceaddon(addontype, skinstring="", header=""):
    '''let the user choose a resource addon and set that as skin string'''
    cur_value = try_decode(xbmc.getInfoLabel("Skin.String(%s.name)" % skinstring))
    listing = []
    addon = xbmcaddon.Addon(ADDON_ID)
    if not header:
        header = addon.getLocalizedString(32008)

    # none option
    listitem = xbmcgui.ListItem(label=addon.getLocalizedString(32000))
    listitem.setArt({"icon": 'DefaultAddonNone.png'})
    listitem.setProperty("addonid", "none")
    listing.append(listitem)

    # custom path
    listitem = xbmcgui.ListItem(label=addon.getLocalizedString(32007))
    listitem.setArt({"icon": 'DefaultFolder.png'})
    listitem.setProperty("addonid", "custom")
    listing.append(listitem)

    # available resource addons
    for item in get_resourceaddons(addontype):
        label2 = "%s: %s" % (xbmc.getLocalizedString(21863), item["author"])
        listitem = xbmcgui.ListItem(label=item["name"], label2=label2)
        listitem.setArt({"icon": item["thumbnail"]})
        listitem.setPath(item["path"])
        listitem.setProperty("addonid", item["addonid"])
        listing.append(listitem)

    # show select dialog with choices
    dialog = DialogSelect("DialogSelect.xml", "", listing=listing, windowtitle=header,
                          richlayout=True, getmorebutton=addontype, autofocuslabel=cur_value)
    dialog.doModal()
    result = dialog.result
    del dialog

    # process selection...
    if isinstance(result, bool) and result:
        # refresh listing requested by getmore button
        del addon
        return setresourceaddon(addontype, skinstring)
    elif result:
        addon_id = result.getProperty("addonid")
        addon_name = result.getLabel()
        if addon_id == "none" and skinstring:
            # None
            xbmc.executebuiltin('Skin.Reset(%s)' % skinstring)
            xbmc.executebuiltin('Skin.Reset(%s.ext)' % skinstring)
            xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, addon_name))
            xbmc.executebuiltin('Skin.SetString(%s.label,%s)' % (skinstring, addon_name))
            xbmc.executebuiltin('Skin.Reset(%s.path)' % skinstring)
            xbmc.executebuiltin('Skin.Reset(%s.multi)' % skinstring)
        else:
            if addon_id == "custom":
                # custom path
                dialog = xbmcgui.Dialog()
                custom_path = dialog.browse(0, addon.getLocalizedString(32003), 'files')
                del dialog
                result.setPath(custom_path)
            addonpath = result.getPath()
            if addonpath:
                is_multi, extension = get_multi_extension(addonpath)
                xbmc.executebuiltin('Skin.SetString(%s,%s)' % (skinstring, addonpath))
                xbmc.executebuiltin('Skin.SetString(%s.path,%s)' % (skinstring, addonpath))
                xbmc.executebuiltin('Skin.SetString(%s.name,%s)' % (skinstring, addon_name))
                xbmc.executebuiltin('Skin.SetString(%s.label,%s)' % (skinstring, addon_name))
                xbmc.executebuiltin('Skin.SetString(%s.ext,%s)' % (skinstring, extension))
                if is_multi:
                    xbmc.executebuiltin('Skin.SetBool(%s.multi)' % skinstring)
                else:
                    xbmc.executebuiltin('Skin.Reset(%s.multi)' % skinstring)
    del addon


def downloadresourceaddons(addontype):
    '''show dialog with all available resource addons on the repo so the user can install one'''
    listitems = []
    addon = xbmcaddon.Addon(ADDON_ID)
    for item in get_repo_resourceaddons(addontype):
        if not getCondVisibility("System.HasAddon(%s)" % item["addonid"]):
            label2 = "%s: %s" % (xbmc.getLocalizedString(21863), item["author"])
            listitem = xbmcgui.ListItem(label=item["name"],
                                        label2=label2)
            listitem.setArt({"icon": item["thumbnail"]})                          
            listitem.setPath(item["path"])
            listitem.setProperty("addonid", item["addonid"])
            listitems.append(listitem)
    # if no addons available show OK dialog..
    if not listitems:
        dialog = xbmcgui.Dialog()
        dialog.ok(addon.getLocalizedString(32012), addon.getLocalizedString(32013))
        del dialog
    else:
        # show select dialog with choices
        dialog = DialogSelect("DialogSelect.xml", "", listing=listitems,
                              windowtitle=addon.getLocalizedString(32012), richlayout=True)
        dialog.doModal()
        result = dialog.result
        del dialog
        del addon
        # process selection...
        if result:
            addon_id = result.getProperty("addonid")
            # trigger install...
            monitor = xbmc.Monitor()
            if KODI_VERSION > 16:
                xbmc.executebuiltin("InstallAddon(%s)" % addon_id)
            else:
                xbmc.executebuiltin("RunPlugin(plugin://%s)" % addon_id)
            count = 0
            # wait (max 2 minutes) untill install is completed
            install_succes = False
            while not monitor.waitForAbort(1) and not install_succes and count < 120:
                install_succes = getCondVisibility("System.HasAddon(%s)" % addon_id)
            del monitor
            if install_succes:
                return True
    return False


def checkresourceaddons(addonslist):
    '''allow the skinner to perform a basic check if some required resource addons are available'''
    addon = xbmcaddon.Addon(ADDON_ID)
    for item in addonslist:
        setting = item.split(";")[0]
        addontype = item.split(";")[1]
        addontypelabel = item.split(";")[2]
        skinsetting = try_decode(xbmc.getInfoLabel("Skin.String(%s.path)" % setting))
        if not skinsetting or (skinsetting and
                               getCondVisibility("!System.HasAddon(%s)" %
                                                      skinsetting.replace("resource://", "").replace("/", ""))):
            # skin setting is empty or filled with non existing addon...
            if not checkresourceaddon(setting, addontype):
                ret = xbmcgui.Dialog().yesno(
                    heading=addon.getLocalizedString(32005) % addontypelabel,
                    message=addon.getLocalizedString(32006) % addontypelabel)
                xbmc.executebuiltin("Skin.Reset(%s.path)" % setting)
                if ret:
                    downloadresourceaddons(addontype)
                    checkresourceaddon(setting, addontype)
    del addon


def checkresourceaddon(skinstring="", addontype=""):
    ''' check for existing resource addons of specified type and set first one found'''
    if not addontype:
        addontype = params.get("addontype")
    if not skinstring:
        skinstring = params.get("skinstring")
    if addontype and skinstring:
        for item in get_resourceaddons(addontype):
            xbmc.executebuiltin("Skin.SetString(%s,%s)" % (skinstring, item['path']))
            xbmc.executebuiltin("Skin.SetString(%s.path,%s)" % (skinstring, item['path']))
            xbmc.executebuiltin("Skin.SetString(%s.name,%s)" % (skinstring, item['name']))
            xbmc.executebuiltin("Skin.SetString(%s.label,%s)" % (skinstring, item['name']))
            is_multi, extension = get_multi_extension(item["path"])
            if is_multi:
                xbmc.executebuiltin("Skin.SetBool(%s.multi)" % (skinstring))
            xbmc.executebuiltin("Skin.SetString(%s.ext,%s)" % (skinstring, extension))
            return True
    return False


def get_resourceaddons(filterstr=""):
    '''retrieve all installed resource addons'''
    result = []
    params = {"type": "kodi.resource.images",
              "properties": ["name", "thumbnail", "path", "author"]}
    for item in kodi_json("Addons.GetAddons", params, "addons"):
        if not filterstr or item['addonid'].lower().startswith(filterstr.lower()):
            item["path"] = "resource://%s/" % item["addonid"]
            result.append(item)

    return result


def get_multi_extension(filepath):
    '''check if resource addon or custom path has subfolders (multiimage)'''
    is_multi = False
    extension = ""
    dirs, files = xbmcvfs.listdir(filepath)
    if len(dirs) > 0:
        is_multi = True
    if not is_multi:
        for item in files:
            extension = "." + item.split(".")[-1]
            break
    return (is_multi, extension)


def get_repo_resourceaddons(filterstr=""):
    '''retrieve all available resource addons on the kodi repo'''
    result = []
    simplecache = SimpleCache()
    for item in xbmcvfs.listdir("addons://all/kodi.resource.images/")[1]:
        if not filterstr or item.lower().startswith(filterstr.lower()):
            addoninfo = get_repo_addoninfo(item, simplecache)
            if not addoninfo.get("name"):
                addoninfo = {"addonid": item, "name": item, "author": "Kodi"}
                addoninfo["thumbnail"] = "http://mirrors.kodi.tv/addons/nexus/%s/icon.png" % item
            addoninfo["path"] = "resource://%s/" % item
            result.append(addoninfo)
    simplecache.close()
    return result


def get_repo_addoninfo(addonid, simplecache=None):
    '''tries to grab info about the addon from kodi repo addons listing'''
    if simplecache:
        cache = simplecache
        cachestr = "BingieToolbox.addoninfo.%s" % addonid
        info = simplecache.get(cachestr)
    if not info:
        info = {"addonid": addonid, "name": "", "thumbnail": "", "author": "Kodi"}
        if simplecache:
            cache.set(cachestr, info)
    return info


def get_resourceimages(addontype, recursive=False):
    '''retrieve listing of specific resource addon images'''
    images = []
    for addon in get_resourceaddons(addontype):
        addonpath = addon["path"]
        if xbmcvfs.exists("special://home/addons/%s/resources/" % addon["addonid"]):
            addonpath = "special://home/addons/%s/resources/" % addon["addonid"]
        images += walk_directory(addonpath, recursive, addon["name"])
    return images


def walk_directory(browsedir, recursive=False, label2=""):
    '''list all images in a directory'''
    images = []
    if xbmcvfs.exists(browsedir):
        dirs = xbmcvfs.listdir(browsedir)[0]
        subdirs = [browsedir]
        for directory in dirs:
            directory = try_decode(directory)
            cur_dir = "%s%s/" % (browsedir, directory)
            if recursive:
                subdirs.append(cur_dir)
            else:
                label = directory
                images.append((label, cur_dir, label2, "DefaultFolder.png"))
        for subdir in subdirs:
            for imagefile in xbmcvfs.listdir(subdir)[1]:
                imagefile = try_decode(imagefile)
                label = imagefile
                imagepath = subdir + imagefile
                images.append((label, imagepath, label2, imagepath))
    return images
