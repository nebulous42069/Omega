# -*- coding: utf-8 -*-
# Bundled from script.trailer.bridge 1.1.2, provider Diggz.
import sys, json, urllib.parse, urllib.request, re, os, time, threading
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

CONFIG = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon/trailer-bridge.json')


def save_key(key):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG + '.tmp', 'w', encoding='utf-8') as stream:
        json.dump({'tmdb_api_key': key}, stream)
    os.replace(CONFIG + '.tmp', CONFIG)


def get_key():
    # Keep this outside skin settings.xml so flavors cannot replace it.
    if os.path.isfile(CONFIG):
        with open(CONFIG, encoding='utf-8') as stream:
            return str(json.load(stream).get('tmdb_api_key', '')).strip()
    if xbmc.getCondVisibility('System.HasAddon(script.trailer.bridge)'):
        key = xbmcaddon.Addon('script.trailer.bridge').getSetting('tmdb_api_key').strip()
        save_key(key)
        return key
    return ''


def configure():
    dialog = xbmcgui.Dialog()
    choice = dialog.select('Xenon trailer lookup', ['Set TMDb API key', 'Clear TMDb API key'])
    if choice == 0:
        key = dialog.input('TMDb API key (v3)').strip()
        if key:
            if not re.fullmatch(r'[A-Za-z0-9]+', key):
                dialog.ok('Xenon trailer lookup', 'Enter the TMDb v3 API key.')
                return
            save_key(key)
    elif choice == 1:
        save_key('')


API_KEY = '' 

def log(msg):
    xbmc.log("[Xenon trailer bridge] " + str(msg), xbmc.LOGINFO)

def qget():
    if len(sys.argv) > 1 and sys.argv[1].startswith("?"):
        return {k:(v[0] if isinstance(v, list) else v) for k,v in urllib.parse.parse_qs(sys.argv[1][1:]).items()}
    return {}

def http_get(url):
    req = urllib.request.Request(url, headers={"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8","ignore"))

def tmdb_external_ids(tmdb_id, ttype):
    if not API_KEY or not tmdb_id: return None
    base = "https://api.themoviedb.org/3"
    url = f"{base}/{'tv' if ttype=='tv' else 'movie'}/{tmdb_id}/external_ids?api_key={API_KEY}"
    return http_get(url)

def tmdb_search(title, year=None, ttype="movie"):
    if not API_KEY or not title or len(title.strip()) < 2: return None
    base = "https://api.themoviedb.org/3"
    params = {"api_key": API_KEY, "query": title}
    if year:
        y = re.findall(r'\d{4}', str(year))
        if y:
            key = "year" if ttype=="movie" else "first_air_date_year"
            params[key] = y[0]
    url = f"{base}/search/{ttype}?" + urllib.parse.urlencode(params)
    return http_get(url)

TRAILER_INFO_PROPERTY = 'Xenon.TrailerInfo.Pending'


def capture_info_item():
    """Capture the selected movie/show before playback changes ListItem labels."""
    def label(field):
        return xbmc.getInfoLabel('ListItem.' + field) or ''

    title = label('Title')
    path = label('FileNameAndPath') or label('Path')
    if not title and not path:
        return None
    item = xbmcgui.ListItem(label=title, path=path)
    info = {'title': title, 'mediatype': label('DBType') or 'movie'}
    for field, key in (
        ('OriginalTitle', 'originaltitle'), ('TVShowTitle', 'tvshowtitle'),
        ('Plot', 'plot'), ('Genre', 'genre'), ('MPAA', 'mpaa'),
        ('Premiered', 'premiered'), ('Studio', 'studio'),
        ('Director', 'director'), ('Writer', 'writer'),
        ('IMDBNumber', 'imdbnumber'), ('Trailer', 'trailer'),
    ):
        value = label(field)
        if value:
            info[key] = value
    for field, key in (('Year', 'year'), ('Season', 'season'),
                       ('Episode', 'episode'), ('DBID', 'dbid')):
        try:
            info[key] = int(label(field))
        except (ValueError, TypeError):
            pass
    item.setInfo('video', info)
    art = {key: label('Art({})'.format(key)) for key in (
        'poster', 'thumb', 'fanart', 'clearlogo', 'tvshow.clearlogo',
        'tvshow.fanart', 'tvshow.poster', 'landscape', 'banner', 'icon',
    )}
    item.setArt({key: value for key, value in art.items() if value})
    for key in ('tmdb_id', 'tmdbshow_id', 'tvdb_id', 'imdb_id', 'dbid',
                'dbtype', 'IsPlayable', 'tmdb_type'):
        value = label('Property({})'.format(key))
        if value:
            item.setProperty(key, value)
    ids = {key: label('UniqueID({})'.format(key)) for key in ('imdb', 'tmdb', 'tvdb')}
    ids = {key: value for key, value in ids.items() if value}
    if not ids.get('imdb') and info.get('imdbnumber'):
        ids['imdb'] = info['imdbnumber']
    if not ids.get('tmdb') and label('Property(tmdb_id)'):
        ids['tmdb'] = label('Property(tmdb_id)')
    if ids:
        try:
            item.getVideoInfoTag().setUniqueIDs(ids)
        except AttributeError:
            item.setUniqueIDs(ids)
    return item


def set_windowed_gui():
    response = json.loads(xbmc.executeJSONRPC(json.dumps({
        'jsonrpc': '2.0', 'id': 1,
        'method': 'GUI.SetFullscreen', 'params': {'fullscreen': False},
    })))
    if 'error' in response:
        log('Could not return trailer to the info window')
        return False
    return True


def trace_restored_info(context):
    monitor = xbmc.Monitor()
    for unused in range(4):
        if monitor.waitForAbort(0.5):
            return
        if context['home'].getProperty(TRAILER_INFO_PROPERTY) != context['token']:
            return
        try:
            focus = xbmcgui.Window(12003).getFocusId()
        except Exception:
            focus = -1
        log('Restoration status: info_visible={}, fullscreen_video={}, focus={}, trailer_panel={}'.format(
            xbmc.getCondVisibility('Window.IsVisible(movieinformation)'),
            xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'),
            focus, context['home'].getProperty('Xenon.TrailerInfo.Active')))


def keep_trailer_windowed(player, context=None, timeout=60.0, settle_time=2.0):
    """Wait through startup, then restore info if playback dismissed it."""
    monitor = xbmc.Monitor()
    log('Windowed trailer watcher started')
    deadline = time.monotonic() + timeout
    started_at = None
    while time.monotonic() < deadline:
        if monitor.abortRequested():
            return
        if context:
            if context['home'].getProperty(TRAILER_INFO_PROPERTY) != context['token']:
                log('Trailer info restoration cancelled by user')
                return
        elif not xbmc.getCondVisibility('Window.IsVisible(movieinformation)'):
            return

        if player.isPlayingVideo():
            if started_at is None:
                started_at = time.monotonic()
                log('Trailer video playback detected')
                if not set_windowed_gui():
                    return
            elif xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'):
                if not set_windowed_gui():
                    return

            if time.monotonic() - started_at >= settle_time:
                if context and not xbmc.getCondVisibility('Window.IsVisible(movieinformation)'):
                    if not set_windowed_gui():
                        return
                    log('Playback closed Video Info; restoring captured movie/show info')
                    # XML onload focuses the custom trailer control, exposing
                    # the embedded videowindow and its Stop Trailer button.
                    trace = threading.Thread(target=trace_restored_info, args=(context,), daemon=True)
                    trace.start()
                    opened = xbmcgui.Dialog().info(context['item'])
                    log('Restored Video Info returned (opened={})'.format(opened))
                else:
                    log('Trailer startup complete; Video Info remains visible')
                return
        elif started_at is not None:
            log('Trailer stopped before info restoration')
            return
        if monitor.waitForAbort(0.1):
            return
    log('Windowed trailer start timed out')


def play_imdb(imdb_id, windowed=False):
    if not imdb_id or not imdb_id.startswith("tt"):
        return False
    log("Launching IMDb trailer (windowed={})".format(windowed))
    url = f"plugin://plugin.video.imdb.trailers/?action=play_id&imdb={imdb_id}"
    if not windowed:
        xbmc.executebuiltin(f'PlayMedia({url})')
        return True

    context = None
    if xbmc.getCondVisibility('Window.IsVisible(movieinformation)'):
        item = capture_info_item()
        if item is not None:
            home = xbmcgui.Window(10000)
            token = str(time.monotonic())
            home.setProperty(TRAILER_INFO_PROPERTY, token)
            home.setProperty('Xenon.TrailerInfo.Active', 'true')
            context = {'home': home, 'token': token, 'item': item}
            log('Captured Video Info for windowed trailer restoration')
    player = None
    try:
        player = xbmc.Player()
        xbmc.executebuiltin(f'PlayMedia({url},1)')
        log('Windowed trailer launch queued; waiting for playback')
        keep_trailer_windowed(player, context)
    finally:
        if context and context['home'].getProperty(TRAILER_INFO_PROPERTY) == context['token']:
            context['home'].clearProperty(TRAILER_INFO_PROPERTY)
        if context and (player is None or not player.isPlayingVideo()):
            context['home'].clearProperty('Xenon.TrailerInfo.Active')
    return True

def open_imdb_search(keyword):
    if not keyword: return False
    url = 'plugin://plugin.video.imdb.trailers/?action=search_word&keyword=' + urllib.parse.quote(keyword)
    xbmc.executebuiltin(f'ActivateWindow(Videos,{url},return)')
    return True

def main():
    global API_KEY
    if len(sys.argv) > 1 and sys.argv[1] == 'settings':
        configure()
        return
    API_KEY = get_key()
    if not xbmc.getCondVisibility('System.HasAddon(plugin.video.imdb.trailers)'):
        xbmc.executebuiltin('Notification(Trailer,Install IMDb Trailers to play trailers,5000)')
        return
    q = qget()
    imdb = q.get("imdb","").strip()
    tmdb = q.get("tmdb","").strip()
    tmdbshow = q.get("tmdbshow","").strip()
    dbtype = q.get("dbtype","").strip().lower()
    mediatype = q.get("mediatype","").strip().lower()
    title = q.get("title","").strip()
    tvtitle = q.get("tvshowtitle","").strip()
    year = q.get("year","").strip()
    windowed = q.get("windowed","") in ("1","true","True","yes","on")

    # 1) Direct IMDb
    if imdb and imdb.startswith("tt"):
        if play_imdb(imdb, windowed): return

    # Guess type
    tguess = "movie"
    for s in (dbtype, mediatype):
        if s in ("tv","tvshow","episode"): tguess = "tv"

    # 2) TMDb direct
    for tid, ttype in ((tmdb, "movie"), (tmdbshow, "tv")):
        if tid:
            data = tmdb_external_ids(tid, ttype if ttype else tguess)
            if data and data.get("imdb_id"):
                if play_imdb(data["imdb_id"], windowed): return

    # 3) Title search
    candidates = []
    if title: candidates.append(("movie", title))
    if tvtitle: candidates.append(("tv", tvtitle))
    # Try guessed type first
    candidates = sorted(candidates, key=lambda x: 0 if x[0]==tguess else 1)
    for ttype, t in candidates:
        res = tmdb_search(t, year=year, ttype=ttype)
        if res and res.get("results"):
            tmdb_id = res["results"][0].get("id")
            if tmdb_id:
                data = tmdb_external_ids(tmdb_id, ttype)
                if data and data.get("imdb_id"):
                    if play_imdb(data["imdb_id"], windowed): return

    # 4) Last resort: open IMDb Trailers search UI
    if title or tvtitle:
        if open_imdb_search(title or tvtitle): return

    xbmc.executebuiltin('Notification(Trailer,No trailer found via IMDb,3500)')

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("Trailer lookup failed: " + type(e).__name__)  # Do not log API-key URLs.
        xbmc.executebuiltin('Notification(Trailer,Error launching trailer,3500)')
