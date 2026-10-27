# -*- coding: utf-8 -*-
"""Repair path-only Custom Item selections in the Xenon 2 widget editor."""
import time
import os
import sys
import uuid
import xbmc
import xbmcgui
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x2_reorder_widgets import raw_properties, LiveEditorItem, selected_index, write_property, verify


def suffix(slot):
    return '.sel%d' % slot if slot>1 else ''


def active_slot():
    mode=xbmcgui.Window(10000).getProperty('skinshortcuts-management-widget')
    if mode=='1':return 1
    if mode.startswith('sel') and mode[3:].isdigit() and 2<=int(mode[3:])<=15:
        return int(mode[3:])
    return None


def missing_settings(slot, item, title):
    tail=suffix(slot)
    changes={}
    # Never overwrite an existing style/type/art selection.
    defaults={'widget':'addon','widgetType':'videos','widgetTarget':'videos',
              'widgetStyle':'Panel','widgetArt':'Poster'}
    for name,value in defaults.items():
        if not item.getProperty(name+tail):changes[name+tail]=value
    changes['widgetName'+tail]=title
    return changes


def repair(wid,window,index,slot,path,monitor):
    item=LiveEditorItem(index);tail=suffix(slot)
    if item.getProperty('widgetPath'+tail)!=path or item.getProperty('widgetName'+tail):
        return
    seed=item.getProperty('widgetTitle'+tail) or 'Custom Widget %d'%slot
    keyboard=xbmc.Keyboard(seed,xbmc.getLocalizedString(16105),False)
    keyboard.doModal()
    # Like the standard picker, cancelling a rename keeps a default title.
    title=(keyboard.getText().strip() if keyboard.isConfirmed() else '') or seed
    if monitor.abortRequested() or window.getProperty('groupname')!='mainmenu':return
    deadline=time.monotonic()+3
    while xbmcgui.getCurrentWindowDialogId()!=wid and time.monotonic()<deadline:
        if monitor.waitForAbort(.05):return
    if xbmcgui.getCurrentWindowDialogId()!=wid or selected_index()!=index or active_slot()!=slot:return
    item=LiveEditorItem(index)
    if item.getProperty('widgetPath'+tail)!=path or item.getProperty('widgetName'+tail):return
    changes=missing_settings(slot,item,title)
    before=raw_properties(item)
    applied=[];progress=xbmcgui.DialogProgress()
    progress.create('Custom Widget','Saving widget title and settings…')
    try:
        for n,(name,value) in enumerate(changes.items()):
            applied.append(name)
            write_property(wid,window,name,value,monitor)
            progress.update(int((n+1)*100/len(changes)))
        progress.close()
        if not verify(index,changes,monitor):
            progress.create('Custom Widget','Restoring previous settings…')
            raise RuntimeError('Custom widget could not be verified')
        xbmc.log('[X2 custom widget] Completed slot %d.'%slot,xbmc.LOGINFO)
    except Exception as exc:
        progress.close();progress.create('Custom Widget','Restoring previous settings…')
        restored=True
        for name in reversed(applied):
            try:write_property(wid,window,name,before.get(name,''),monitor)
            except Exception:restored=False
        progress.close()
        if restored:restored=verify(index,{name:before.get(name,'') for name in applied},monitor)
        xbmc.log('[X2 custom widget] Save failed: %s'%type(exc).__name__,xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('Custom Widget',
            'The widget title could not be saved. Please try again.' if restored else
            'Some widget settings could not be restored. Check this slot before closing the editor.')
    finally:
        progress.close()
        window.clearProperty('customProperty');window.clearProperty('customValue')


class PendingRepair:
    def __init__(self):
        self.candidate=None;self.since=0;self.attempted=None
    def quiet(self):
        self.candidate=None
    def ready(self,key,now):
        if key!=self.candidate:self.candidate,self.since=key,now
        if key==self.attempted or now-self.since<.65:return False
        self.attempted=key
        return True


def main():
    monitor=xbmc.Monitor();deadline=time.monotonic()+20;window=None;wid=None
    while time.monotonic()<deadline and not monitor.abortRequested():
        candidate=xbmcgui.getCurrentWindowDialogId()
        try:
            w=xbmcgui.Window(candidate);group=w.getProperty('groupname')
            if group=='mainmenu':wid,window=candidate,w;break
            if group:return  # Submenu/button-menu editor: no selector widgets here.
        except RuntimeError:pass
        if monitor.waitForAbort(.1):return
    if window is None:return
    if window.getProperty('X2Widgets.CustomWatch'):return
    token=uuid.uuid4().hex;window.setProperty('X2Widgets.CustomWatch',token)
    pending=PendingRepair()
    try:
        while not monitor.abortRequested() and window.getProperty('X2Widgets.CustomWatch')==token:
            if window.getProperty('groupname')!='mainmenu':break
            # Do not read the editor's container or open a keyboard over its picker.
            if xbmcgui.getCurrentWindowDialogId()!=wid or window.getProperty('X2Widgets.ReorderBusy'):
                pending.quiet();pending.attempted=None
            else:
                slot=active_slot();index=selected_index()
                if slot is not None and index>=0:
                    item=LiveEditorItem(index);tail=suffix(slot)
                    path=item.getProperty('widgetPath'+tail)
                    if path and not item.getProperty('widgetName'+tail):
                        key=(index,slot,path)
                        if pending.ready(key,time.monotonic()):repair(wid,window,index,slot,path,monitor)
                    else:pending.quiet();pending.attempted=None
                else:pending.quiet()
            if monitor.waitForAbort(.15):break
    except Exception as exc:
        xbmc.log('[X2 custom widget] Watcher stopped: %s'%type(exc).__name__,xbmc.LOGWARNING)
    finally:
        if window.getProperty('X2Widgets.CustomWatch')==token:window.clearProperty('X2Widgets.CustomWatch')


if __name__=='__main__':main()
