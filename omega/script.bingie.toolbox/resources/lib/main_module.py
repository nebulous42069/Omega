#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from .skinsettings import SkinSettings
import urllib.parse
from .dialogselect import DialogSelect
from resources.lib.utils import log_msg, KODI_VERSION, kodi_json, clean_string, getCondVisibility
from resources.lib.utils import log_exception, get_current_content_type, ADDON_ID, recursive_delete_dir, try_decode
from xml.dom.minidom import parse

class MainModule:
    '''mainmodule provides the script methods for the bingietoolbox addon'''

    def __init__(self):
        '''Initialization and main code run'''
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)

        self.params = self.get_params()
        log_msg("MainModule called with parameters: %s" % self.params)
        action = self.params.get("action", "")
        # launch module for action provided by this script
        try:
            getattr(self, action)()
        except AttributeError:
            log_exception(__name__, "No such action: %s" % action)
        except Exception as exc:
            log_exception(__name__, exc)
        finally:
            xbmc.executebuiltin("dialog.Close(busydialog)")

    def close(self):
        '''Cleanup Kodi Cpython instances on exit'''
        self.close()
        del self.win
        del self.addon
        log_msg("MainModule exited")

    @classmethod
    def get_params(self):
        '''extract the params from the called script path'''
        params = {}
        for arg in sys.argv[1:]:
            paramname = arg.split('=')[0]
            paramvalue = arg.replace(paramname + "=", "")
            paramname = paramname.lower()
            if paramname == "action":
                paramvalue = paramvalue.lower()
            params[paramname] = paramvalue
        return params

    def deprecated_method(self, newaddon):
        '''
            used when one of the deprecated methods is called
            print warning in log and call the external script with the same parameters
        '''
        action = self.params.get("action")
        log_msg("Deprecated method: %s. Please call %s directly" % (action, newaddon), xbmc.LOGWARNING)
        paramstring = ""
        for key, value in self.params.items():
            paramstring += ",%s=%s" % (key, value)
        if getCondVisibility("System.HasAddon(%s)" % newaddon):
            xbmc.executebuiltin("RunAddon(%s%s)" % (newaddon, paramstring))
        else:
            # trigger install of the addon
            if KODI_VERSION > 16:
                xbmc.executebuiltin("InstallAddon(%s)" % newaddon)
            else:
                xbmc.executebuiltin("RunPlugin(plugin://%s)" % newaddon)

    def setview(self):
        '''sets the selected viewmode for the container'''
        content_type = get_current_content_type()
        if not content_type:
            content_type = "files"
        current_view = try_decode(xbmc.getInfoLabel("Container.Viewmode"))
        view_id, view_label = self.selectview(content_type, current_view)
        current_forced_view = xbmc.getInfoLabel("Skin.String(BingieToolbox.ForcedViews.%s)" % content_type)

        if view_id is not None:
            # also store forced view
            if (content_type and current_forced_view and current_forced_view != "None" and
                    getCondVisibility("Skin.HasSetting(BingieToolbox.ForcedViews.Enabled)")):
                xbmc.executebuiltin("Skin.SetString(BingieToolbox.ForcedViews.%s,%s)" % (content_type, view_id))
                xbmc.executebuiltin("Skin.SetString(BingieToolbox.ForcedViews.%s.label,%s)" % (content_type, view_label))
                self.win.setProperty("BingieToolbox.ForcedView", view_id)
                if not getCondVisibility("Control.HasFocus(%s)" % current_forced_view):
                    xbmc.sleep(100)
                    xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)
                    xbmc.executebuiltin("SetFocus(%s)" % view_id)
            else:
                self.win.clearProperty("BingieToolbox.ForcedView")
            # set view
            xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    def selectview(self, content_type="other", current_view=None, display_none=False):
        '''reads skinfile with all views to present a dialog to choose from'''
        cur_view_select_id = None
        label = ""
        all_views = []
        if display_none:
            listitem = xbmcgui.ListItem(label="None")
            listitem.setProperty("id", "None")
            all_views.append(listitem)
        # read the special skin views file
        views_file = try_decode(xbmcvfs.translatePath('special://skin/extras/bingieviews.xml'))
        if xbmcvfs.exists(views_file):
            doc = parse(views_file)
            listing = doc.documentElement.getElementsByTagName('view')
            itemcount = 0
            for view in listing:
                label = xbmc.getLocalizedString(int(view.attributes['languageid'].nodeValue))
                viewid = view.attributes['value'].nodeValue
                mediatypes = view.attributes['type'].nodeValue.lower().split(",")
                if label.lower() == current_view.lower() or viewid == current_view:
                    cur_view_select_id = itemcount
                    if display_none:
                        cur_view_select_id += 1
                if (("all" in mediatypes or content_type.lower() in mediatypes) and
                    (not "!" + content_type.lower() in mediatypes) and not
                        getCondVisibility("Skin.HasSetting(BingieToolbox.view.Disabled.%s)" % viewid)):
                    image = "special://skin/extras/viewthumbs/%s.jpg" % viewid
                    listitem = xbmcgui.ListItem(label=label)
                    listitem.setArt({'icon': image})
                    listitem.setProperty("viewid", viewid)
                    listitem.setProperty("icon", image)
                    all_views.append(listitem)
                    itemcount += 1
        dialog = DialogSelect("DialogSelect.xml", "", listing=all_views,
                              windowtitle=self.addon.getLocalizedString(32009), richlayout=True)
        dialog.autofocus_id = cur_view_select_id
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            viewid = result.getProperty("viewid")
            label = try_decode(result.getLabel())
            return (viewid, label)
        else:
            return (None, None)

    # pylint: disable-msg=too-many-local-variables
    def enableviews(self):
        '''show select dialog to enable/disable views'''
        all_views = []
        views_file = try_decode(xbmcvfs.translatePath('special://skin/extras/bingieviews.xml'))
        richlayout = self.params.get("richlayout", "") == "true"
        if xbmcvfs.exists(views_file):
            doc = parse(views_file)
            listing = doc.documentElement.getElementsByTagName('view')
            for view in listing:
                view_id = view.attributes['value'].nodeValue
                label = xbmc.getLocalizedString(int(view.attributes['languageid'].nodeValue))
                desc = label + " (" + str(view_id) + ")"
                image = "special://skin/extras/viewthumbs/%s.jpg" % view_id
                listitem = xbmcgui.ListItem(label=label, label2=desc)
                listitem.setArt({'icon': image})
                listitem.setProperty("viewid", view_id)
                if not getCondVisibility("Skin.HasSetting(BingieToolbox.view.Disabled.%s)" % view_id):
                    listitem.select(selected=True)
                excludefromdisable = False
                try:
                    excludefromdisable = view.attributes['excludefromdisable'].nodeValue == "true"
                except Exception:
                    pass
                if not excludefromdisable:
                    all_views.append(listitem)

        dialog = DialogSelect(
            "DialogSelect.xml",
            "",
            listing=all_views,
            windowtitle=self.addon.getLocalizedString(32010),
            multiselect=True, richlayout=richlayout)
        dialog.doModal()
        result = dialog.result
        del dialog
        if result:
            for item in result:
                view_id = item.getProperty("viewid")
                if item.isSelected():
                    # view is enabled
                    xbmc.executebuiltin("Skin.Reset(BingieToolbox.view.Disabled.%s)" % view_id)
                else:
                    # view is disabled
                    xbmc.executebuiltin("Skin.SetBool(BingieToolbox.view.Disabled.%s)" % view_id)
    # pylint: enable-msg=too-many-local-variables

    def setforcedview(self):
        '''sets a forced view for a specific content type'''
        content_type = self.params.get("contenttype")
        if content_type:
            current_view = xbmc.getInfoLabel("Skin.String(BingieToolbox.ForcedViews.%s)" % content_type)
            if not current_view:
                current_view = "0"
            view_id, view_label = self.selectview(content_type, current_view, True)
            if view_id or view_label:
                xbmc.executebuiltin("Skin.SetString(BingieToolbox.ForcedViews.%s,%s)" % (content_type, view_id))
                xbmc.executebuiltin("Skin.SetString(BingieToolbox.ForcedViews.%s.label,%s)" % (content_type, view_label))

    def setfocus(self):
        '''set focus on a list or control'''
        control = self.params.get("control")
        fallback = self.params.get("fallback")
        position = self.params.get("position", "0")
        relativeposition = self.params.get("relativeposition")
        if relativeposition:
            position = int(relativeposition) - 1
        count = 0
        if control:
            while not getCondVisibility("Control.HasFocus(%s)" % control):
                if getCondVisibility("Window.IsActive(busydialog)"):
                    xbmc.sleep(150)
                    continue
                elif count == 20 or (getCondVisibility(
                        "!Control.IsVisible(%s) | "
                        "!Integer.IsGreater(Container(%s).NumItems,0)" % (control, control))):
                    if fallback:
                        xbmc.executebuiltin("Control.SetFocus(%s)" % fallback)
                    break
                else:
                    xbmc.executebuiltin("Control.SetFocus(%s,%s)" % (control, position))
                    xbmc.sleep(50)
                    count += 1

    def setwidgetcontainer(self):
        '''reports the current selected widget container/control'''
        controls = self.params.get("controls", "").split("-")
        if controls:
            xbmc.sleep(50)
            for i in range(10):
                for control in controls:
                    if getCondVisibility("Control.IsVisible(%s) + Integer.IsGreater(Container(%s).NumItems,0)"
                                              % (control, control)):
                        self.win.setProperty("BingieToolbox.WidgetContainer", control)
                        return
                xbmc.sleep(50)

    def saveskinimage(self):
        '''let the user select an image and save it to addon_data for easy backup'''
        skinstring = self.params.get("skinstring", "")
        allow_multi = self.params.get("multi", "") == "true"
        header = self.params.get("header", "")
        value = SkinSettings().save_skin_image(skinstring, allow_multi, header)
        if value:
            xbmc.executebuiltin("Skin.SetString(%s,%s)" % (skinstring, value))

    @staticmethod
    def checkskinsettings():
        '''performs check of all default skin settings and labels'''
        SkinSettings().correct_skin_settings()

    def setskinsetting(self):
        '''allows the user to set a skin setting with a select dialog'''
        setting = self.params.get("setting", "")
        org_id = self.params.get("id", "")
        if "$" in org_id:
            org_id = xbmc.getInfoLabel(org_id)
        header = self.params.get("header", "")
        SkinSettings().set_skin_setting(setting=setting, window_header=header, original_id=org_id)

    def setskinconstant(self):
        '''allows the user to set a skin constant with a select dialog'''
        setting = self.params.get("setting", "")
        value = self.params.get("value", "")
        header = self.params.get("header", "")
        SkinSettings().set_skin_constant(setting, header, value)

    def setskinconstants(self):
        '''allows the skinner to set multiple skin constants'''
        settings = self.params.get("settings", "").split("|")
        values = self.params.get("values", "").split("|")
        SkinSettings().set_skin_constants(settings, values)

    def setskinshortcutsproperty(self):
        '''allows the user to make a setting for skinshortcuts using the special skinsettings dialogs'''
        setting = self.params.get("setting", "")
        prop = self.params.get("property", "")
        header = self.params.get("header", "")
        SkinSettings().set_skinshortcuts_property(setting, header, prop)

    def togglekodisetting(self):
        '''toggle kodi setting'''
        settingname = self.params.get("setting", "")
        cur_value = getCondVisibility("system.getbool(%s)" % settingname)
        if cur_value:
            new_value = "false"
        else:
            new_value = "true"
        xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s}}' %
            (settingname, new_value))

    def setkodisetting(self):
        '''set kodi setting'''
        settingname = self.params.get("setting", "")
        value = self.params.get("value", '')
        numvalue = self.params.get("numvalue", '')
        if numvalue:
            value = '%s' % numvalue 
        else:
            value = '"%s"' % value   
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue",\
            "params":{"setting":"%s","value":%s}}' % (settingname, value))   

    def overlaytexture(self):
        '''legacy: let the user choose a background overlay from a skin defined folder'''
        skinstring = self.params.get("skinstring", "BackgroundOverlayTexture")
        self.params["skinstring"] = skinstring
        self.params["resourceaddon"] = "resource.images.backgroundoverlays"
        self.params["customfolder"] = "special://skin/extras/bgoverlays/"
        self.params["allowmulti"] = "false"
        self.params["header"] = self.addon.getLocalizedString(32001)
        self.selectimage()

    def busytexture(self):
        '''legacy: lets the user select a busy spinner from predefined spinners in the skin'''
        skinstring = self.params.get("skinstring", "BingieToolbox.SpinnerTexture")
        self.params["skinstring"] = skinstring
        self.params["resourceaddon"] = "resource.images.busyspinners"
        self.params["customfolder"] = "special://skin/extras/busy_spinners/"
        self.params["allowmulti"] = "true"
        self.params["header"] = self.addon.getLocalizedString(32004)
        self.selectimage()

    def selectimage(self):
        '''lets the user select an image or imagepath from resourceaddons or custom path'''
        skinsettings = SkinSettings()
        skinstring = self.params.get("skinstring", "")
        skinshortcutsprop = self.params.get("skinshortcutsproperty", "")
        current_value = self.params.get("currentvalue", "")
        resource_addon = self.params.get("resourceaddon", "")
        allow_multi = self.params.get("allowmulti", "false") == "true"
        windowheader = self.params.get("header", "")
        label, value = skinsettings.select_image(
            skinstring, allow_multi=allow_multi, windowheader=windowheader, resource_addon=resource_addon,
            current_value=current_value)
        if label:
            if skinshortcutsprop:
                # write value to skinshortcuts prop
                from .skinshortcuts import set_skinshortcuts_property
                set_skinshortcuts_property(skinshortcutsprop, value, label)
            else:
                # write the values to skin strings
                if value.startswith("$INFO"):
                    # we got an dynamic image from window property
                    skinsettings.set_skin_variable(skinstring, value)
                    value = "$VAR[%s]" % skinstring
                skinstring = skinstring
                label = label
                xbmc.executebuiltin("Skin.SetString(%s.label,%s)" % (skinstring, label))
                xbmc.executebuiltin("Skin.SetString(%s.name,%s)" % (skinstring, label))
                xbmc.executebuiltin("Skin.SetString(%s,%s)" % (skinstring, value))
                xbmc.executebuiltin("Skin.SetString(%s.path,%s)" % (skinstring, value))
        del skinsettings

    def dialogok(self):
        '''show an OK dialog with a message'''
        headertxt = clean_string(self.params.get("header", ""))
        bodytxt = clean_string(self.params.get("message", ""))
        dialog = xbmcgui.Dialog()
        dialog.ok(heading=headertxt, message=bodytxt)
        del dialog

    def dialogyesno(self):
        '''show a YES/NO dialog with a message'''
        headertxt = clean_string(self.params.get("header", ""))
        bodytxt = clean_string(self.params.get("message", ""))
        yesactions = self.params.get("yesaction", "").split("|")
        noactions = self.params.get("noaction", "").split("|")
        if xbmcgui.Dialog().yesno(heading=headertxt, message=bodytxt):
            for action in yesactions:
                xbmc.executebuiltin(action)
        else:
            for action in noactions:
                xbmc.executebuiltin(action)

    def textviewer(self):
        '''show a textviewer dialog with a message'''
        headertxt = clean_string(self.params.get("header", ""))
        bodytxt = clean_string(self.params.get("message", ""))
        xbmcgui.Dialog().textviewer(headertxt, bodytxt)
        
    def getfilename(self, filename=""):
        '''display a sanitized filename in the vidoeinfo dialog'''
        output = self.params.get("output")
        if not filename:
            filename = xbmc.getInfoLabel("ListItem.FileNameAndPath")
        if not filename:
            filename = xbmc.getInfoLabel("ListItem.FileName")
        if "filename=" in filename:
            url_params = dict(urllib.parse.parse_qsl(filename))
            filename = url_params.get("filename")
        self.win.setProperty(output, filename)    
        
    def getplayerfilename(self):
        '''parse the filename from a plugin (e.g. emby) filename'''
        filename = xbmc.getInfoLabel("Player.FileNameAndPath")
        if not filename:
            filename = xbmc.getInfoLabel("Player.FileName")
        self.getfilename(filename)          

    def setresourceaddon(self):
        '''let the user choose a resource addon and set that as skin string'''
        from .resourceaddons import setresourceaddon
        addontype = self.params.get("addontype", "")
        skinstring = self.params.get("skinstring", "")
        setresourceaddon(addontype, skinstring)

    def checkresourceaddons(self):
        '''allow the skinner to perform a basic check if some required resource addons are available'''
        from .resourceaddons import checkresourceaddons
        addonslist = self.params.get("addonslist", [])
        if addonslist:
            addonslist = addonslist.split("|")
        checkresourceaddons(addonslist)
        