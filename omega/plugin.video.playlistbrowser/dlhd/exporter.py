"""One shared export path for manual and scheduled updates."""
import json
import os
import threading
import time
import uuid
import xbmcvfs
from dlhd import resolver
from dlhd.debuglog import LOG, reason


def profile_folder(addon):
    return xbmcvfs.translatePath(addon.getAddonInfo('profile').rstrip('/\\')+'/dlhd')


def output_path(addon):
    folder=addon.getSetting('DLHD_folder') or addon.getAddonInfo('profile')
    return folder.rstrip('/\\')+'/daddylive.m3u'


def state_path(addon):
    return os.path.join(profile_folder(addon),'refresh-state.json')


def read_state(addon):
    try:
        with open(state_path(addon),encoding='utf-8') as stream:
            value=json.load(stream)
        if not isinstance(value,dict):return {}
        for key in ('last_success','retry_after'):
            if key in value and not isinstance(value[key],(int,float)):return {}
        return value
    except (OSError,ValueError):return {}


def save_state(addon,state):
    path=state_path(addon)
    os.makedirs(os.path.dirname(path),exist_ok=True)
    temp=path+'.'+uuid.uuid4().hex+'.tmp'
    try:
        with open(temp,'w',encoding='utf-8') as stream:json.dump(state,stream)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def atomic_write(path,content):
    local=xbmcvfs.translatePath(path)
    if os.path.isabs(local):
        os.makedirs(os.path.dirname(local),exist_ok=True)
        temp=local+'.'+uuid.uuid4().hex+'.tmp'
        try:
            with open(temp,'w',encoding='utf-8',newline='\n') as stream:stream.write(content)
            os.replace(temp,local)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    else:
        # Stage before rename for network/VFS destinations; a failed rename retains the old file.
        temp=path+'.'+uuid.uuid4().hex+'.tmp'
        output=xbmcvfs.File(temp,'w')
        try:
            if not output.write(content):raise ValueError('Unable to stage updated M3U')
        finally:output.close()
        try:
            if not xbmcvfs.rename(temp,path):raise ValueError('Cannot replace M3U at this VFS location; choose a local output folder')
        finally:xbmcvfs.delete(temp)


def refresh(addon,origin,on_export=None):
    folder=profile_folder(addon)
    os.makedirs(folder,exist_ok=True)
    os.makedirs(os.path.join(folder,'logos'),exist_ok=True)
    lock=os.path.join(folder,'export.lock')
    try:
        # Exclusive directory creation coordinates the service with Kodi's separate plugin interpreter.
        if os.path.isdir(lock) and time.time()-os.path.getmtime(lock)>15*60:
            os.rmdir(lock)
        os.mkdir(lock)
    except OSError:
        raise ValueError('A DaddyLive M3U refresh is already running. Try again shortly.')
    try:
        items=resolver.channels(addon.getSetting('DLHD_base') or 'https://dlive.sx')
        if not items:raise ValueError('Channel list is empty; existing M3U retained')
        logos={}
        status='logos disabled'
        from dlhd.logos import match_logos
        addon_path=xbmcvfs.translatePath(addon.getAddonInfo('path') or '')
        logos,status=match_logos(items,folder,addon_path,online=addon.getSetting('DLHD_logos')!='false')
        player='auto' if addon.getSetting('DLHD_automatic')!='false' else resolver.SERVERS[int(addon.getSetting('DLHD_player') or '0')]
        epg={}
        guide_url=None
        if addon.getSetting('DLHD_epg')!='false':
            from dlhd.epg import map_channels, GUIDE_URL
            epg,epg_status=map_channels(items,folder)
            guide_url=GUIDE_URL
            status+='; {} EPG matches ({})'.format(len(epg),epg_status)
            LOG.info('EPGTalk mapping matched=%s of %s channels',len(epg),len(items))
        content=resolver.playlist(items,origin,player,logos,epg,guide_url)
        path=output_path(addon)
        xbmcvfs.mkdirs(path.rsplit('/',1)[0])
        atomic_write(path,content)
        # The 48-hour timer resets after a successful manual or scheduled file update.
        state=read_state(addon)
        state.update({'last_success':time.time(),'path':path,'retry_after':0})
        save_state(addon,state)
        if on_export:on_export(path,content)
        LOG.info('M3U refreshed channels=%s logos=%s',len(items),len(logos))
        return path,len(items),len(logos),status
    finally:
        os.rmdir(lock)


class Scheduler:
    def __init__(self,addon,origin,on_export=None):
        self.addon,self.origin,self.on_export=addon,origin,on_export
        self.worker=None
        self.last_check=0
    def due(self,now):
        if self.addon.getSetting('DLHD_auto_refresh')=='false':return False
        try:hours=max(1,int(self.addon.getSetting('DLHD_refresh_hours') or '48'))
        except ValueError:hours=48
        path=output_path(self.addon)
        state=read_state(self.addon)
        if state.get('path')!=path:state={}
        if float(state.get('retry_after',0))>now:return False
        if not xbmcvfs.exists(path):return True
        last=float(state.get('last_success',0))
        if not last:
            try:last=xbmcvfs.Stat(path).st_mtime()
            except Exception:last=0
        return now-last>=hours*3600
    def tick(self,now=None):
        now=time.time() if now is None else now
        if self.worker and self.worker.is_alive():return
        if self.last_check and now-self.last_check<60:return
        self.last_check=now
        if self.due(now):
            self.worker=threading.Thread(target=self.run,daemon=True)
            self.worker.start()
    def run(self):
        try:
            LOG.info('Scheduled M3U refresh started')
            refresh(self.addon,self.origin,self.on_export)
        except Exception as error:
            LOG.warning('Scheduled M3U refresh failed: %s; retry in one hour',reason(error))
            state=read_state(self.addon)
            state.update({'path':output_path(self.addon),'retry_after':time.time()+3600})
            save_state(self.addon,state)
