# -*- coding: utf-8 -*-
import sys, json, urllib.parse, urllib.request, re
import xbmc, xbmcaddon

ADDON = xbmcaddon.Addon()
API_KEY = ADDON.getSetting("tmdb_api_key").strip()

def log(msg):
    xbmc.log("[script.trailer.bridge] " + str(msg), xbmc.LOGINFO)

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
    log("GET " + url)
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
    log("GET " + url)
    return http_get(url)

def play_imdb(imdb_id, windowed=False):
    if not imdb_id or not imdb_id.startswith("tt"):
        return False
    url = f"plugin://plugin.video.imdb.trailers/?action=play_id&imdb={imdb_id}"
    xbmc.executebuiltin(f'PlayMedia({url}{",1" if windowed else ""})')
    return True

def open_imdb_search(keyword):
    if not keyword: return False
    url = 'plugin://plugin.video.imdb.trailers/?action=search_word&keyword=' + urllib.parse.quote(keyword)
    xbmc.executebuiltin(f'ActivateWindow(Videos,{url},return)')
    return True

def main():
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
        log("Exception: " + repr(e))
        xbmc.executebuiltin('Notification(Trailer,Error launching trailer,3500)')
