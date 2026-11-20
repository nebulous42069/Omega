"""MDBList device authorization using the supplied Diggz public OAuth application."""
import time, uuid, threading
import requests
import xbmc, xbmcgui, xbmcaddon

CLIENT_ID = '6LDlMF3ygMFKZkGsNYPkmxs2D1qUZs48wtkk5cY3'
API = 'https://api.mdblist.com'
_LOCK = threading.RLock()

def addon(): return xbmcaddon.Addon()

def post(path, data):
    try:
        r = requests.post(API + path, data=dict(data, client_id=CLIENT_ID), timeout=15)
        data=r.json()
        return r.status_code, data if isinstance(data, dict) else {}
    except (requests.RequestException, ValueError):
        return 0, {}

def store(data, new=False):
    a=addon()
    a.setSetting('mdblist_access_token',data['access_token'])
    a.setSetting('mdblist_refresh_token',data.get('refresh_token') or ('' if new else a.getSetting('mdblist_refresh_token')))
    a.setSetting('mdblist_expires',str(int(time.time()+int(data.get('expires_in') or 2592000))))
    if new:
        a.setSetting('mdblist_identity',uuid.uuid4().hex)
        a.setSetting('mdblist_key','')

def login():
    status, data=post('/oauth/device-authorization/',{'scope':'write'})
    if not data.get('device_code') or not data.get('user_code'):
        raise RuntimeError('MDBList device authorization failed')
    interval=max(1,int(data.get('interval') or 5)); lifetime=int(data.get('expires_in') or 900)
    start=time.monotonic(); monitor=xbmc.Monitor(); dialog=xbmcgui.DialogProgress()
    message='Open '+(data.get('verification_uri') or 'https://mdblist.com/oauth/device/')+' and enter code: '+data['user_code']
    dialog.create('Authorize MDBList',message)
    try:
        while time.monotonic()-start<lifetime and not dialog.iscanceled():
            if monitor.waitForAbort(interval) or dialog.iscanceled(): return False
            status, token=post('/oauth/token/',{'grant_type':'urn:ietf:params:oauth:grant-type:device_code','device_code':data['device_code']})
            if token.get('access_token'):
                with _LOCK: store(token,new=True)
                return True
            error=token.get('error')
            if error in ('access_denied','expired_token','invalid_client','invalid_grant'): return False
            if error=='slow_down' or status==429: interval+=5
            dialog.update(min(99,int((time.monotonic()-start)*100/lifetime)),message)
        return False
    finally: dialog.close()

def token(rejected=None):
    with _LOCK:
        a=addon(); current=a.getSetting('mdblist_access_token')
        try: expires=float(a.getSetting('mdblist_expires'))
        except ValueError: expires=0
        if current and current!=rejected and expires>time.time()+60: return current
        refresh=a.getSetting('mdblist_refresh_token')
        if not refresh: raise RuntimeError('Authorize MDBList in Accounts settings')
        status,data=post('/oauth/token/',{'grant_type':'refresh_token','refresh_token':refresh})
        if status!=200 or not data.get('access_token'): raise RuntimeError('MDBList renewal failed; authorize again if expired')
        store(data); return data['access_token']

def request(path, params=None):
    try:
        access=token()
        for attempt in range(2):
            r=requests.get(API+'/'+path,params=params or {},headers={'Authorization':'Bearer '+access},timeout=15)
            if r.status_code==401 and attempt==0:
                access=token(rejected=access); continue
            if not r.ok: raise RuntimeError('MDBList request failed (%s)'%r.status_code)
            return r.json(),r.headers
    except requests.RequestException:
        raise RuntimeError('MDBList connection failed') from None
