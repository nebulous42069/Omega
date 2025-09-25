
def _ytk_norm_thumb(u: str):
    if not u:
        return u
    if u.startswith('//'):
        return 'https:' + u
    return u

# -*- coding: utf-8 -*-
import sys, re, json, urllib.request, urllib.parse, ssl
import xbmcplugin, xbmcgui, xbmcaddon

ADDON  = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

RESULTS_LIMIT = 30
REGION = "US"
LANG   = "en"




def _ytk_add_playlist_item(pid, title, thumb):
    try:
        li = xbmcgui.ListItem(label=title)
        thumb = _ytk_norm_thumb(thumb)
        if thumb:
            li.setArt({"thumb": thumb, "icon": thumb, "poster": thumb, "banner": thumb, "fanart": f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/fanart.jpg"})
        u = build_url({"action": "playlist_v2", "list": pid})
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)
    except Exception:
        pass

def _ytk_add_channel_item(cid, title, thumb):
    try:
        li = xbmcgui.ListItem(label=title)
        thumb = _ytk_norm_thumb(thumb)
        if thumb:
            li.setArt({"thumb": thumb, "icon": thumb, "poster": thumb, "banner": thumb, "fanart": f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/fanart.jpg"})
        u = build_url({"action": "browse", "url": f"https://www.youtube.com/channel/{cid}/videos?view=0&sort=dd"})
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)
    except Exception:
        # Don't crash listing if one item is weird
        pass


# Stable Explore-style categories that work logged-out
EXPLORE_BASE = [
        ("Music",     "https://www.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ"),
    ("Live",      "https://www.youtube.com/live"),
    ("Gaming",    "https://www.youtube.com/gaming"),
    ("News",      "https://www.youtube.com/news"),
    ("Sports",    "https://www.youtube.com/sports"),
    ("Learning",  "https://www.youtube.com/learning"),
    ("Fashion & Beauty", "https://www.youtube.com/fashion"),
]

def _with_gl_hl(u: str) -> str:
    # Force US/English on every URL
    sep = '&' if '?' in u else '?'
    return f"{u}{sep}gl={REGION}&hl={LANG}&persist_gl=1&persist_hl=1"

def _chip_icon_for(label: str) -> str:
    L = label.lower()
    if "music" in L:   return "music.png"
    if "live" in L:    return "live.png"
    if "news" in L:    return "news.png"
    if "gaming" in L:  return "gaming.png"
    if "sport" in L:   return "sports.png"
    if "learning" in L:   return "learning.png"
    if "Fashion & Beauty" in L:   return "fashion.png"
    return "icon.png"

def add_category_item(label: str, url: str):
    li = xbmcgui.ListItem(label=label)
    icon = _chip_icon_for(label)
    art_base = f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/"
    li.setArt({"thumb": art_base + icon, "icon": art_base + icon, "fanart": art_base + "fanart.jpg"})
    u = build_url({"action": "chip", "label": label, "url": url})
    xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)

def add_explore_categories():
    for label, url in EXPLORE_BASE:
        add_category_item(label, _with_gl_hl(url))

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

# Relaxed SSL (some Kodi installs lack CA bundles)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ------------------------ Helpers ------------------------
def build_url(query: dict) -> str:
    return BASE_URL + "?" + urllib.parse.urlencode(query)


def _req(url: str) -> str:
    headers = {
        "User-Agent": UA,
        "Accept-Language": LANG,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip",
        "Cookie": f"PREF=gl={REGION}&hl={LANG}; SOCS=CAI; CONSENT=YES+",
        "Referer": "https://www.youtube.com/",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=CTX, timeout=20) as resp:
        data = resp.read()
        enc = resp.headers.get("Content-Encoding", "").lower()
        if enc == "gzip":
            try:
                import gzip
                data = gzip.decompress(data)
            except Exception:
                pass
        return data.decode("utf-8", "replace")
def add_dir(label, kind, icon):
    li = xbmcgui.ListItem(label=label)
    li.setArt({
        "thumb":  f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/{icon}",
        "icon":   f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/{icon}",
        "fanart": f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/fanart.jpg",
    })
    url = build_url({"action": "browse", "kind": kind})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)


def add_video(video_id, title, thumb=None):
    if not thumb:
        thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    li = xbmcgui.ListItem(label=title)
    # Omega+ prefers InfoTagVideo setters, but setInfo still works for quick plugins
    li.setInfo("video", {"title": title})
    thumb = _ytk_norm_thumb(thumb)
    li.setArt({
        "thumb": thumb,
        "icon": thumb,
        "poster": thumb,
        "banner": thumb,
        "fanart": f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/fanart.jpg",
    })
    play_url = f"plugin://plugin.video.youtube/play/?video_id={video_id}"
    xbmcplugin.addDirectoryItem(HANDLE, play_url, li, isFolder=False)

# -------------------- YouTube JSON parsing --------------------
def _extract_ytinitial_json(html: str):
    patterns = [
        r"var\s+ytInitialData\s*=\s*({.*?})\s*;\s*</script>",
        r"window\[\s*\"ytInitialData\"\s*\]\s*=\s*({.*?})\s*;\s*</script>",
        r"ytInitialData\"\s*:\s*({.*?})\s*[,<]"
    ]
    for p in patterns:
        m = re.search(p, html, re.DOTALL)
        if not m:
            continue
        blob = m.group(1)
        # Try as-is, then truncated to last closing brace if script tail present
        for candidate in (blob, blob[: blob.rfind("}") + 1] if "}" in blob else None):
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except Exception:
                pass
    return None

def _get_path(d, path):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list) and isinstance(key, int) and 0 <= key < len(cur):
            cur = cur[key]
        else:
            return None
    return cur

def _clean_accessibility_label(label: str) -> str:
    if not label:
        return ""
    s = label
    s = re.sub(r"\s*-\s*YouTube\s*$", "", s, flags=re.IGNORECASE)
    parts = s.split(" by ")
    if len(parts) > 1 and len(parts[0]) >= 4:
        s = parts[0]
    s = re.split(r"\s•\s", s)[0]
    return s.strip()

def _extract_title(node):
    # Common/direct fields across many renderers
    candidates = [
        _get_path(node, ("title","runs",0,"text")),
        _get_path(node, ("title","simpleText")),
        _get_path(node, ("titleText","runs",0,"text")),
        _get_path(node, ("displayedTitle","runs",0,"text")),
        _get_path(node, ("headline","runs",0,"text")),
        _get_path(node, ("inlinePlaybackRenderer","title","simpleText")),
        _get_path(node, ("label","simpleText")),
        _get_path(node, ("label","runs",0,"text")),
        _get_path(node, ("videoTitle","runs",0,"text")),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()

    # Accessibility fallbacks (reliable for mixes/podcasts/live)
    acc = (
        _get_path(node, ("title","accessibility","accessibilityData","label"))
        or _get_path(node, ("accessibility","accessibilityData","label"))
    )
    if isinstance(acc, str) and acc.strip():
        cleaned = _clean_accessibility_label(acc)
        if cleaned:
            return cleaned

    return None

def _best_thumb(node):
    # Try multiple possible thumbnail containers
    if isinstance(node, dict):
        if "thumbnail" in node and isinstance(node["thumbnail"], dict):
            arr = node["thumbnail"].get("thumbnails")
            if isinstance(arr, list) and arr:
                return arr[-1].get("url") or arr[0].get("url")
        if "richThumbnail" in node and isinstance(node["richThumbnail"], dict):
            arr = _get_path(node, ("richThumbnail","movingThumbnailRenderer","thumbnail","thumbnails"))
            if isinstance(arr, list) and arr:
                return arr[-1].get("url") or arr[0].get("url")
        if "thumbnails" in node and isinstance(node["thumbnails"], list) and node["thumbnails"]:
            return node["thumbnails"][-1].get("url") or node["thumbnails"][0].get("url")
    return None

def _walk_videos(node, out):
    if isinstance(node, dict):
        # Unwrap common containers
        for key in ("videoRenderer","compactVideoRenderer","playlistVideoRenderer",
                    "reelItemRenderer","gridVideoRenderer","richItemRenderer","richGridMedia",
                    "compactAutoplayRenderer","compactMovieRenderer"):
            if key in node and isinstance(node[key], dict):
                _walk_videos(node[key], out)

        # A direct renderer-like dict?
        if isinstance(node.get("videoId"), str):
            vid = node["videoId"]
            title = _extract_title(node) or vid
            thumb = _best_thumb(node)
            out.append((vid, title, thumb))

        # Recurse through values
        for v in node.values():
            _walk_videos(v, out)

    elif isinstance(node, list):
        for v in node:
            _walk_videos(v, out)

_watch_title_re = re.compile(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', re.IGNORECASE|re.DOTALL)

def _title_from_watch(video_id: str) -> str:
    try:
        html = _req(f"https://www.youtube.com/watch?v={video_id}&hl={LANG}&gl={REGION}")
        m = _watch_title_re.search(html)
        if m:
            t = m.group(1)
            # Unescape basic HTML entities YouTube might put here
            t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')
            return t.strip()
        # Fallback: try ytInitialData on watch page
        data = _extract_ytinitial_json(html)
        t = _get_path(data or {}, ("playerOverlays","playerOverlayRenderer","decoratedPlayerBarRenderer","decoratedPlayerBarRenderer","playerBar","title","simpleText"))
        if isinstance(t, str) and t.strip():
            return t.strip()
    except Exception:
        pass
    return ""

def parse_page_for_videos(html: str):
    data = _extract_ytinitial_json(html)
    found = []
    if data:
        _walk_videos(data, found)

    # Dedup while preserving order
    seen, result = set(), []
    need_fallback = []
    for vid, title, thumb in found:
        if not vid or vid in seen:
            continue
        seen.add(vid)
        if not title or title == vid or len(title) <= 3:
            need_fallback.append((vid, thumb))
            result.append([vid, vid, thumb])  # placeholder; we’ll swap title later
        else:
            result.append([vid, title, thumb])
        if len(result) >= RESULTS_LIMIT:
            break

    # Do watch-page title fallbacks for any placeholders (cap to avoid UI stalls)
    max_fallbacks = 15
    for i, (vid, thumb) in enumerate(need_fallback[:max_fallbacks]):
        fixed = _title_from_watch(vid)
        if fixed:
            # Locate in result and replace title
            for row in result:
                if row[0] == vid and (row[1] == vid or len(row[1]) <= 3):
                    row[1] = fixed
                    break

    # Ensure thumbnails
    for row in result:
        if not row[2]:
            row[2] = f"https://i.ytimg.com/vi/{row[0]}/hqdefault.jpg"

    # Convert to tuples for downstream
    return [(r[0], r[1], r[2]) for r in result]

# ------------------------ Sections ------------------------
MUSIC_CHANNEL_URL = "https://www.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ"
PODCASTS_URL      = "https://www.youtube.com/podcasts"

def list_section(url, empty_msg):
    try:
        html = _req(f"{url}?gl={REGION}&hl={LANG}")
        videos = parse_page_for_videos(html)
    except Exception:
        videos = []
    if not videos:
        xbmcgui.Dialog().notification("YouTube Kiosk", empty_msg, xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
        return
    for vid, title, thumb in videos:
        add_video(vid, title, thumb)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True)

def list_music():
    list_section(MUSIC_CHANNEL_URL, "No items in Music right now")

def list_podcasts():
    list_section(PODCASTS_URL, "No items in Podcasts right now")

def list_gaming():
    list_section("https://www.youtube.com/gaming", "No items in Gaming right now")

def list_news():
    list_section("https://www.youtube.com/news", "No items in News right now")

def list_live():
    list_section("https://www.youtube.com/live", "No items in Live right now")

def do_search(q: str):
    if not q:
        q = xbmcgui.Dialog().input("Search YouTube", type=xbmcgui.INPUT_ALPHANUM)
        if not q:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
            return
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
    list_section(url, "No results")

# -------------------- Router / UI --------------------


def add_search_entry():
    li = xbmcgui.ListItem(label="Search…")
    art_base = f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/"
    li.setArt({"thumb": art_base + "search.png", "icon": art_base + "search.png", "fanart": art_base + "fanart.jpg"})
    u = build_url({"action": "search"})
    xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=False)

# Map for search filters: videos, playlists, channels
SP_MAP = {
    "videos": "EgIQAQ%3D%3D",
    "playlists": "EgIQAw%3D%3D",
    "channels": "EgIQAg%3D%3D",
}

def _prompt_search_kind():
    opts = ["Videos", "Playlists", "Channels"]
    idx = xbmcgui.Dialog().select("Search type", opts)
    if idx < 0:
        return None
    return opts[idx].lower()

def _prompt_keyboard(title="Search YouTube"):
    kb = xbmc.Keyboard("", title, False)
    kb.doModal()
    if kb.isConfirmed():
        return kb.getText()
    return None

def search_flow():
    kind = _prompt_search_kind()
    if not kind:
        return
    q = _prompt_keyboard("Search " + kind.title())
    if not q or not q.strip():
        return
    q = q.strip()
    sp = SP_MAP.get(kind)
    base = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
    if sp:
        base += "&sp=" + sp
    url = _with_gl_hl(base)
    list_section(url, f"No results for '{q}'")



# ===== Search helpers (Videos / Playlists / Channels) =====
SP_MAP = {
    "videos": "EgIQAQ%3D%3D",
    "playlists": "EgIQAw%3D%3D",
    "channels": "EgIQAg%3D%3D",
}

def _prompt_keyboard(title="Search YouTube"):
    kb = xbmc.Keyboard("", title, False)
    kb.doModal()
    if kb.isConfirmed():
        return kb.getText()
    return None

def add_search_entry():
    li = xbmcgui.ListItem(label="Search…")
    art_base = f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/"
    li.setArt({"thumb": art_base + "search.png", "icon": art_base + "search.png", "fanart": art_base + "fanart.jpg"})
    u = build_url({"action": "search"})
    xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)

def show_search_menu():
    # Submenu to choose search type
    items = [("Search Videos…", "videos"), ("Search Playlists…", "playlists"), ("Search Channels…", "channels")]
    for label, kind in items:
        li = xbmcgui.ListItem(label=label)
        art_base = f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/"
        li.setArt({"thumb": art_base + "search.png", "icon": art_base + "search.png", "fanart": art_base + "fanart.jpg"})
        u = build_url({"action": "search_kind", "kind": kind})
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True)

def run_search_kind(kind: str):
    kind = (kind or "videos").lower()
    q = _prompt_keyboard(f"Search {kind.title()}")
    if not q or not q.strip():
        return
    q = q.strip()
    base = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
    sp = SP_MAP.get(kind)
    if sp:
        base += "&sp=" + sp
    url = _with_gl_hl(base)
    list_section(url, f"No results for '{q}'")



# ===== Search helpers (Videos / Playlists / Channels) =====
SP_MAP = {
    "videos": "EgIQAQ%3D%3D",
    "playlists": "EgIQAw%3D%3D",
    "channels": "EgIQAg%3D%3D",
}

def _prompt_keyboard(title="Search YouTube"):
    kb = xbmc.Keyboard("", title, False)
    kb.doModal()
    if kb.isConfirmed():
        return kb.getText()
    return None

def add_search_entry():
    li = xbmcgui.ListItem(label="Search…")
    art_base = f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/"
    li.setArt({"thumb": art_base + "search.png", "icon": art_base + "search.png", "fanart": art_base + "fanart.jpg"})
    u = build_url({"action": "search"})
    xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)

def show_search_menu():
    # Submenu to choose search type
    items = [("Search Videos…", "videos"), ("Search Playlists…", "playlists"), ("Search Channels…", "channels")]
    for label, kind in items:
        li = xbmcgui.ListItem(label=label)
        art_base = f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/"
        li.setArt({"thumb": art_base + "search.png", "icon": art_base + "search.png", "fanart": art_base + "fanart.jpg"})
        u = build_url({"action": "search_prompt", "kind": kind})
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True)

def run_search_prompt(kind: str):
    # Ask for query, then trigger a Container.Update to a new route that lists results
    kind = (kind or "videos").lower()
    q = _prompt_keyboard(f"Search {kind.title()}")
    if not q or not q.strip():
        return
    q = q.strip()
    # Jump to exec route so Kodi refreshes the directory
    target = build_url({"action": "search_exec", "kind": kind, "q": q})
    xbmc.executebuiltin(f"Container.Update({target})")

def run_search_exec(kind: str, q: str):
    kind = (kind or "videos").lower()
    q = (q or "").strip()
    if not q:
        xbmcgui.Dialog().notification("YouTube Kiosk", "Empty search query", xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
        return
    base = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
    sp = SP_MAP.get(kind)
    if sp:
        base += "&sp=" + sp
    url = _with_gl_hl(base)
    list_section(url, f"No results for '{q}'")


def show_root():
    add_search_entry()
    add_explore_categories()
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True)


def do_browse(url: str):
    url = (url or "").strip()
    if not url:
        xbmcgui.Dialog().notification("YouTube Kiosk", "Missing URL to browse", xbmcgui.NOTIFICATION_INFO, 3000)
        return
    list_section(url, "No results here")

import re as _re_pl2
import html as _html_pl2
import json as _json_pl2

def _ytk_extract_initial_json(html_text: str):
    try:
        m = _re_pl2.search(r"ytInitialData\s*=\s*(\{.*?\})\s*;\s*</script>", html_text, _re_pl2.DOTALL)
        if not m:
            return None
        return _json_pl2.loads(m.group(1))
    except Exception:
        return None

def _ytk_req(url: str) -> str:
    return _req(_with_gl_hl(url))


def _ytk_playlist_thumb(pid: str):
    try:
        page = _ytk_req(f"https://www.youtube.com/playlist?list={pid}")
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', page)
        return m.group(1) if m else None
    except Exception:
        return None

def _ytk_playlist_title(pid: str) -> str:
    try:
        page = _ytk_req(f"https://www.youtube.com/playlist?list={pid}")
        m = _re_pl2.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', page)
        if not m:
            m = _re_pl2.search(r"<title>([^<]+)</title>", page)
        title = m.group(1) if m else pid
        title = _html_pl2.unescape(title).replace(" - YouTube", "").strip()
        return title or pid
    except Exception:
        return pid

def _ytk_walk_playlists(node, out):
    if isinstance(node, dict):
        if "playlistRenderer" in node:
            pr = node["playlistRenderer"]
            pid = pr.get("playlistId")
            t = pr.get("title") or {}
            title = None
            if "runs" in t and t["runs"]:
                title = t["runs"][0].get("text")
            elif "simpleText" in t:
                title = t.get("simpleText")
            thumb = None
            tr = pr.get("thumbnail") or {}
            thumbs = tr.get("thumbnails") or []
            if thumbs:
                thumb = thumbs[-1].get("url")
            if pid:
                out.append((pid, title, thumb))
        for v in node.values():
            _ytk_walk_playlists(v, out)
    elif isinstance(node, list):
        for v in node:
            _ytk_walk_playlists(v, out)

def _ytk_walk_playlist_videos(node, out):
    if isinstance(node, dict):
        if "playlistVideoRenderer" in node:
            vr = node["playlistVideoRenderer"]
            vid = vr.get("videoId")
            t = vr.get("title") or {}
            title = None
            if "runs" in t and t["runs"]:
                title = t["runs"][0].get("text")
            elif "simpleText" in t:
                title = t.get("simpleText")
            thumb = None
            tr = vr.get("thumbnail") or {}
            thumbs = tr.get("thumbnails") or []
            if thumbs:
                thumb = thumbs[-1].get("url")
            if vid:
                out.append((vid, title, thumb))
        for v in node.values():
            _ytk_walk_playlist_videos(v, out)
    elif isinstance(node, list):
        for v in node:
            _ytk_walk_playlist_videos(v, out)



def _ytk_channel_title(cid: str) -> str:
    try:
        page = _ytk_req(f"https://www.youtube.com/channel/{cid}")
        m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', page) or re.search(r"<title>([^<]+)</title>", page)
        title = m.group(1) if m else cid
        title = html.unescape(title).replace(" - YouTube", "").strip()
        return title or cid
    except Exception:
        return cid

def _ytk_channel_thumb(cid: str):
    try:
        page = _ytk_req(f"https://www.youtube.com/channel/{cid}")
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', page)
        return m.group(1) if m else None
    except Exception:
        return None


def _ytk_walk_channels(node, out):
    if isinstance(node, dict):
        if "channelRenderer" in node:
            cr = node["channelRenderer"]
            cid = cr.get("channelId")
            t = cr.get("title") or {}
            title = None
            if isinstance(t, dict):
                if "simpleText" in t:
                    title = t.get("simpleText")
                elif "runs" in t and t["runs"]:
                    title = t["runs"][0].get("text")
            thumb = None
            tr = cr.get("thumbnail") or {}
            thumbs = tr.get("thumbnails") or []
            if thumbs:
                thumb = thumbs[-1].get("url")
            if cid:
                out.append((cid, title, thumb))
        for v in node.values():
            _ytk_walk_channels(v, out)
    elif isinstance(node, list):
        for v in node:
            _ytk_walk_channels(v, out)


def list_results_channels_v2(url, empty_msg):
    try:
        html_text = _ytk_req(url)
        data = _ytk_extract_initial_json(html_text)
    except Exception:
        data = None
        html_text = ""
    items = []
    if data:
        _ytk_walk_channels(data, items)
    if not items and html_text:
        for cid in re.findall(r'"channelId"\s*:\s*"([A-Za-z0-9_-]{10,})"', html_text):
            items.append((cid, None, None))

    seen = set()
    final = []
    for cid, title, thumb in items:
        if cid in seen:
            continue
        seen.add(cid)
        if not title:
            title = _ytk_channel_title(cid)
        if not thumb:
            thumb = _ytk_channel_thumb(cid)
        li = xbmcgui.ListItem(label=title)
        if thumb:
            thumb = _ytk_norm_thumb(thumb)
        li.setArt({"thumb": thumb, "icon": thumb, "fanart": f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/fanart.jpg"})
        u = build_url({"action": "browse", "url": f"https://www.youtube.com/channel/{cid}/videos?view=0&sort=dd"})
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)



def list_channel_v2(channel_id: str):
    if not channel_id:
        xbmcgui.Dialog().notification("YouTube Kiosk", "Missing channel id", xbmcgui.NOTIFICATION_INFO, 3000)
        _dbg("list_channel_v2: missing channel_id")
        return
    url = f"https://www.youtube.com/channel/{channel_id}/videos?view=0&sort=dd"
    _dbg(f"list_channel_v2: fetching {url}")
    list_section(url, "No videos in this channel")


def list_results_playlists_v2(url, empty_msg):
    try:
        html_text = _ytk_req(url)
        data = _ytk_extract_initial_json(html_text)
    except Exception:
        data = None
        html_text = ""
    items = []
    if data:
        _ytk_walk_playlists(data, items)
    if not items and html_text:
        for pid in _re_pl2.findall(r'"playlistId"\s*:\s*"([A-Za-z0-9_-]{10,})"', html_text):
            items.append((pid, None, None))
    seen = set()
    final = []
    for pid, title, thumb in items:
        if pid in seen:
            continue
        seen.add(pid)
        if not title:
            title = _ytk_playlist_title(pid)
        final.append((pid, title, thumb))
    if not final:
        xbmcgui.Dialog().notification("YouTube Kiosk", empty_msg, xbmcgui.NOTIFICATION_INFO, 3000)
        return
    for pid, title, thumb in final:
        if not thumb:
            thumb = _ytk_playlist_thumb(pid)
        thumb = _ytk_norm_thumb(thumb)
        li = xbmcgui.ListItem(label=title)
        if thumb:
            li.setArt({"thumb": thumb, "icon": thumb, "poster": thumb, "banner": thumb,
                       "fanart": f"special://home/addons/{ADDON.getAddonInfo('id')}/resources/media/fanart.jpg"})
        u = build_url({"action": "playlist_v2", "list": pid})
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=True)
def list_playlist_v2(playlist_id: str):
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    try:
        html_text = _ytk_req(url)
        data = _ytk_extract_initial_json(html_text)
    except Exception:
        data = None
        html_text = ""
    out = []
    if data:
        _ytk_walk_playlist_videos(data, out)
    if not out and html_text:
        for vid in _re_pl2.findall(r'"videoId"\s*:\s*"([A-Za-z0-9_-]{8,})"', html_text):
            out.append((vid, None, None))
    if not out:
        xbmcgui.Dialog().notification("YouTube Kiosk", "No videos in this playlist", xbmcgui.NOTIFICATION_INFO, 3000)
        return
    seen = set()
    for vid, title, thumb in out:
        if not vid or vid in seen:
            continue
        seen.add(vid)
        if not title:
            title = f"Video {vid}"
        add_video(vid, title, thumb)


def run_search_exec_v2(kind: str, q: str):
    kind = (kind or "videos").lower()
    q = (q or "").strip()
    if not q:
        xbmcgui.Dialog().notification("YouTube Kiosk", "Empty search query", xbmcgui.NOTIFICATION_INFO, 3000)
        return
    base = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
    sp = SP_MAP.get(kind)
    if sp:
        base += "&sp=" + sp
    url = _with_gl_hl(base)
    if kind == "playlists":
        list_results_playlists_v2(url, f"No playlists for '{q}'")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
    elif kind == "channels":
        list_results_channels_v2(url, f"No channels for '{q}'")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
    else:
        list_section(url, f"No results for '{q}'")




def _dbg(msg):
    try:
        xbmc.log("[YouTube Kiosk] " + str(msg), xbmc.LOGINFO)
    except Exception:
        pass

def router(paramstring: str):
    _dbg(f"router: paramstring={paramstring}")
    # Parse params
    params = {}
    if paramstring.startswith('?'):
        paramstring = paramstring[1:]
    try:
        for k, v in urllib.parse.parse_qsl(paramstring, keep_blank_values=True):
            params[k] = v
    except Exception:
        pass
    action = params.get("action", "")

    # Dispatch
    if action == "browse":
        do_browse(params.get("url", ""))
    elif action == "chip":
        list_section(params.get("url", ""), f"Nothing in {params.get('label','this category')} right now")
    elif action == "search":
        show_search_menu()
    elif action == "search_prompt":
        run_search_prompt(params.get("kind", "videos"))
    elif action == "search_exec":
        run_search_exec_v2(params.get("kind", "videos"), params.get("q", ""))
    elif action == "playlist_v2":
        list_playlist_v2(params.get("list", ""))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=True)
    else:
        show_root()

# Entry point
router(sys.argv[2] if len(sys.argv) > 2 else "")
