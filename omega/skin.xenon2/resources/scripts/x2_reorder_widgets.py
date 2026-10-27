# -*- coding: utf-8 -*-
"""Swap complete adjacent selector widgets using Skin Shortcuts' editor API."""
import ast
import re
import sys
import time
import xbmc
import xbmcgui
from x2_selector_state import swap as swap_selector

FIELDS = ['widgetShowRowTitle','widget','widgetArt','widgetBack','widgetCase','widgetDisableFanart',
          'widgetHide','widgetLimit','widgetList','widgetLiveTV','widgetName',
          'widgetPanelInfo','widgetPath','widgetSort','widgetSortby','widgetStyle',
          'widgetTitle','widgetType','widgetreload','widgetreload2']
SLOT_PROPERTY = re.compile(r'^(widget[A-Za-z0-9_-]*)(?:\.sel(1[0-5]|[2-9]))?$')


def key(field, slot):
    return field + ('.sel%d' % slot if slot > 1 else '')


def raw_properties(item):
    raw = item.getProperty('additionalListItemProperties') or '[]'
    values = ast.literal_eval(raw)
    if not isinstance(values, list):
        raise ValueError('Unsupported Skin Shortcuts property list')
    return {p[0]:str(p[1]) for p in values
            if isinstance(p, (list, tuple)) and len(p)==2 and isinstance(p[0],str)}


def swap_plan(item, source, target):
    if source not in range(1,16) or target not in range(1,16) or abs(source-target)!=1:
        raise ValueError('Expected adjacent selector slots 1-15')
    raw = raw_properties(item)
    # Include future/custom widget properties as well as all known skin settings.
    fields = {f.casefold():f for f in FIELDS}
    for name in raw:
        match = SLOT_PROPERTY.fullmatch(name)
        if match:
            fields[match[1].casefold()] = match[1]
    changes = []
    for field in sorted(fields.values()):
        a,b = key(field,source),key(field,target)
        av,bv = raw.get(a,item.getProperty(a)),raw.get(b,item.getProperty(b))
        for name,value in [(a,bv),(b,av)]:
            if raw.get(name,'') != value:
                changes.append((name,value,raw.get(name,'')))
    return changes


def localized_id(value):
    if value.isdigit():
        return value
    match = re.fullmatch(r'\$LOCALIZE\[(\d+)\]|\$ADDON\[script.skinshortcuts (\d+)\]|\$SKIN\[(\d+)\|[^]]*\]|::(?:LOCAL|SCRIPT)::(\d+)',value)
    return next((s for s in match.groups() if s),None) if match else None


def equivalent(a,b):
    return a==b or (localized_id(a) is not None and localized_id(a)==localized_id(b))


def editor():
    for wid in [xbmcgui.getCurrentWindowDialogId(),xbmcgui.getCurrentWindowId()]:
        try:
            window=xbmcgui.Window(wid)
            if window.getProperty('groupname')=='mainmenu':
                return wid,window
        except RuntimeError:
            pass
    raise RuntimeError('Open a main-menu widget customizer first')


class LiveEditorItem:
    def __init__(self, index):
        self.prefix='Container(211).ListItemAbsolute(%d).' % index
    def getProperty(self, name):
        return xbmc.getInfoLabel(self.prefix+'Property(%s)' % name)


def selected_index():
    try:
        return int(xbmc.getInfoLabel('Container(211).CurrentItem') or 0)-1
    except ValueError:
        return -1


def write_property(wid,window,name,value,monitor):
    # The modal progress dialog prevents changing the selected editor menu.
    # Do not read Container(211) through that modal dialog or a Python wrapper.
    if window.getProperty('groupname')!='mainmenu':
        raise RuntimeError('The menu editor closed during the move')
    window.setProperty('customProperty',name)
    if value:
        window.setProperty('customValue',value)
    else:
        window.clearProperty('customValue')
    xbmc.executebuiltin('SendClick(%d,404)' % wid)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline and not monitor.abortRequested():
        if not window.getProperty('customProperty'):
            # Skin Shortcuts has copied this request into its callback's local
            # variables. Callbacks are queued serially; the next cannot overtake it.
            if monitor.waitForAbort(.04):
                break
            return
        if monitor.waitForAbort(.02):
            break
    raise RuntimeError('Skin Shortcuts did not acknowledge a widget setting')


def verify(index, expected, monitor):
    # Run after closing progress so GUI info resolves against the editor again.
    deadline=time.monotonic()+5
    while time.monotonic()<deadline and not monitor.abortRequested():
        raw=raw_properties(LiveEditorItem(index))
        if all(equivalent(raw.get(name,''),value) for name,value in expected.items()):
            return True
        if monitor.waitForAbort(.05):
            break
    return False


def main():
    args=dict(arg.split('=',1) for arg in sys.argv[1:] if '=' in arg)
    source=int(args.get('slot','0'))
    direction=args.get('direction','')
    target=source+(-1 if direction=='left' else 1 if direction=='right' else 0)
    if not (1<=source<=15 and 1<=target<=15 and abs(source-target)==1):
        return
    wid,window=editor()
    if window.getProperty('X2Widgets.ReorderBusy'):
        return
    index=selected_index()
    if index<0:
        raise RuntimeError('No selected editor menu')
    changes=swap_plan(LiveEditorItem(index),source,target)
    if not changes:
        return
    window.setProperty('X2Widgets.ReorderBusy','true')
    progress=xbmcgui.DialogProgress();monitor=xbmc.Monitor();applied=[]
    progress.create('Move Widget','Moving slot %d to slot %d…' % (source,target))
    try:
        for n,(name,value,previous) in enumerate(changes):
            if progress.iscanceled():
                raise RuntimeError('Move cancelled')
            applied.append((name,previous))
            write_property(wid,window,name,value,monitor)
            progress.update(int((n+1)*100/len(changes)))
        progress.close()
        if not verify(index, {name:value for name,value,_ in changes}, monitor):
            progress.create('Move Widget','Restoring the original settings…')
            raise RuntimeError('The moved settings could not be verified')
    except Exception as exc:
        rollback_failed=False
        for name,value in reversed(applied):
            try:
                write_property(wid,window,name,value,monitor)
            except Exception:
                rollback_failed=True
        progress.close()
        if not rollback_failed:
            rollback_failed=not verify(index, {name:value for name,value in applied}, monitor)
        message=('The move could not finish. Close the editor without saving and reopen it.'
                 if rollback_failed else 'The move was cancelled or failed; the original settings were restored.')
        xbmc.log('[X2 Widget reorder] %s' % type(exc).__name__,xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('Move Widget',message)
        return
    finally:
        progress.close()
        window.clearProperty('X2Widgets.ReorderBusy')
        window.clearProperty('customProperty');window.clearProperty('customValue')
    home=xbmcgui.Window(10000)
    mode='sel%d' % target if target>1 else '1'
    home.setProperty('skinshortcuts-management-widget',mode)
    # Keep the selected Home widget pointing at the configuration that moved.
    swap_selector(source, target)
    xbmc.executebuiltin('Control.SetFocus(%d)' % (312 if target==1 else 100002+target*100))
    xbmcgui.Dialog().notification('Widget moved','Slot %d → slot %d' % (source,target),xbmcgui.NOTIFICATION_INFO,2500)


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        xbmc.log('[X2 Widget reorder] %s' % type(exc).__name__,xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('Move Widget','The move could not start. Please reopen the widget customizer and try again.')
