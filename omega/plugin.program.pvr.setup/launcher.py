"""Read-only PVR navigation plus per-preset preferences. No PVR reset operations."""
import glob
import hashlib
import json
import os
import time
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET


def read_json(path):
    try:
        with open(path,encoding='utf-8') as stream:value=json.load(stream)
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}


def write_json(path,value):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    temp=path+'.tmp'
    with open(temp,'w',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
    os.replace(temp,path)


def canonical_location(location):
    try:
        import xbmcvfs
        location=xbmcvfs.translatePath(location)
    except (ImportError, AttributeError):
        pass
    return location.replace('\\','/').rstrip('/')


def instance_signature(path):
    try:
        values={node.get('id'):(node.text or '').strip() for node in ET.parse(path).getroot()}
        if values.get('kodi_addon_instance_enabled','true').casefold()=='false':return ''
        location=values.get('m3uPath','') if values.get('m3uPathType')=='0' else values.get('m3uUrl','')
        location=location or values.get('m3uUrl','') or values.get('m3uPath','')
        # Compare source locations across the old URL-field and corrected local-field presets.
        if not location:return ''
        return hashlib.sha256(canonical_location(location).encode('utf-8')).hexdigest()
    except (OSError,ET.ParseError):return ''


def remember(profile,xmlkey,instance_path):
    signature=instance_signature(instance_path)
    if not signature:raise ValueError('Cannot identify the applied IPTV playlist')
    write_json(os.path.join(profile,'active_preset.json'),{'preset':xmlkey,'signature':signature})


def active_preset(profile,iptv_profile,preset_folder,presets):
    configs=[path for path in glob.glob(os.path.join(iptv_profile,'instance-settings-*.xml')) if instance_signature(path)]
    if len(configs)!=1:return ''
    signature=instance_signature(configs[0])
    state=read_json(os.path.join(profile,'active_preset.json'))
    known={p['xmlkey'] for p in presets}
    if state.get('signature')==signature and state.get('preset') in known:return state['preset']
    # Existing setups can be recognized without reapplying the destructive setup routine.
    matches=[p['xmlkey'] for p in presets if instance_signature(os.path.join(preset_folder,p['xmlkey'],'instance-settings-1.xml'))==signature]
    return matches[0] if len(matches)==1 else ''


def preferred_group(profile,preset,presets):
    overrides=read_json(os.path.join(profile,'group_overrides.json'))
    if preset in overrides and isinstance(overrides[preset],str):return overrides[preset].strip()
    return next((p.get('default_group','').strip() for p in presets if p['xmlkey']==preset),'')


def command(group='',guide=False,path=''):
    window='TVGuide' if guide else 'TVChannels'
    if path:return 'ActivateWindow('+window+',"'+path.replace('"','%22')+'",return)'
    if not group:return 'ActivateWindow('+window+')'
    return 'ActivateWindow('+window+',pvr://channels/tv/'+quote(group,safe='')+',return)'


def vfs_groups(vfs):
    root='pvr://channels/tv/'
    directories,_=vfs.listdir(root)
    result=[]
    for entry in directories:
        path=entry if entry.startswith(root) else root+entry
        component=path.rstrip('/').rsplit('/',1)[-1]
        name,separator,client=component.rpartition('@')
        if not separator or not client.lstrip('-').isdigit():name=component
        result.append({'label':unquote(name),'file':path.rstrip('/')+'/'})
    return result


def open_pvr(addon,xbmc,jsonrpc,presets,iptv_profile,guide=False):
    import xbmcvfs
    profile=xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    preset_folder=os.path.join(addon.getAddonInfo('path'),'resources','Presets')
    preset=active_preset(profile,iptv_profile,preset_folder,presets)
    group=preferred_group(profile,preset,presets) if preset else ''
    path=''
    folders=[]
    errors={}
    source=''
    reason='No recognized single playlist or no preferred group'
    if group:
        for attempt in range(12):
            try:
                folders=vfs_groups(xbmcvfs)
            except Exception as exc:
                errors['vfs']=type(exc).__name__
                folders=[]
            source='xbmcvfs' if folders else 'jsonrpc'
            response=jsonrpc('Files.GetDirectory',{'directory':'pvr://channels/tv/','media':'files'})
            if isinstance(response,dict) and response.get('error'):errors['directory_rpc']=response['error']
            if not folders:folders=(response.get('result') or {}).get('files',[]) if isinstance(response,dict) else []
            matches=[item for item in folders if item.get('label','').strip().casefold()==group.casefold()
                     and item.get('file','').startswith('pvr://channels/tv/')]
            if len(matches)==1:
                path=matches[0]['file'];reason='Using Kodi channel group path';break
            if matches:
                reason='Multiple groups have the requested name';break
            reason='Preferred group not returned by Kodi'
            if attempt<11:xbmc.sleep(250)
    selected=command(guide=guide,path=path)
    # Store no playlist URLs, tokens, or configuration contents.
    status=jsonrpc('PVR.GetChannelGroups',{'channeltype':'tv'})
    pvr_groups=(status.get('result') or {}).get('channelgroups',[]) if isinstance(status,dict) else []
    if isinstance(status,dict) and status.get('error'):errors['groups_rpc']=status['error']
    report={'directory_source':source,'query_errors':errors,'pvr_groups':pvr_groups,
            'kodi_version':xbmc.getInfoLabel('System.BuildVersion'),'preset':preset,'requested_group':group,'group_path':path,
            'available_groups':[item.get('label','') for item in folders],
            'reason':reason,'command':selected}
    try:write_json(os.path.join(profile,'launcher-debug.json'),report)
    except OSError:pass
    xbmc.log('[PVR Setup launcher] '+json.dumps(report),getattr(xbmc,'LOGINFO',1))
    xbmc.executebuiltin(selected)


def edit_group(addon,dialog,presets):
    import xbmcvfs
    choice=dialog.select('Default TV group for preset',[p['label'] for p in presets])
    if choice<0 or choice>=len(presets):return
    preset=presets[choice]['xmlkey']
    profile=xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    current=preferred_group(profile,preset,presets)
    # Keyboard cancellation must not silently erase the current preference.
    import xbmc
    keyboard=xbmc.Keyboard(current,'Exact channel group name (blank = normal TV list)')
    keyboard.doModal()
    if not keyboard.isConfirmed():return
    group=keyboard.getText().strip()
    overrides=read_json(os.path.join(profile,'group_overrides.json'))
    overrides[preset]=group
    write_json(os.path.join(profile,'group_overrides.json'),overrides)
    dialog.ok(addon.getAddonInfo('name'),'Default group saved: '+(group or 'Normal TV list'))
