# -*- coding: utf-8 -*-
import sys
import os
import time
import urllib.parse as up
import urllib.request as urlreq
import re
import tempfile
import json
import uuid
import hashlib

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

# Diggz source module
try:
    import resources.lib.diggz_source as diggz_source
except Exception:
    diggz_source = None

# Robust import for scraper
try:
    from resources.lib import wc_scraper as wc
except Exception:
    _ADDON = xbmcaddon.Addon()
    _BASE = xbmcvfs.translatePath(_ADDON.getAddonInfo("path"))
    _LIBDIR = os.path.join(_BASE, "resources", "lib")
    if _LIBDIR not in sys.path:
        sys.path.insert(0, _LIBDIR)
    import wc_scraper as wc

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id") or "plugin.video.4kwallpapers.fixedid"
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else -1
BASE_URL = sys.argv[0] if len(sys.argv) > 0 else "plugin://plugin.video.4kwallpapers.fixedid"
BASE_SITE = "https://wallpaperscraft.com/"

# Profile dirs (for cached category thumbs)
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo("profile")) or xbmcvfs.translatePath(
    f"special://profile/addon_data/{ADDON_ID}"
)
try:
    if not xbmcvfs.exists(PROFILE_DIR):
        xbmcvfs.mkdirs(PROFILE_DIR)
except Exception:
    pass
CAT_THUMB_DIR = os.path.join(PROFILE_DIR, "cat_thumbs")
CATALOG_CACHE = os.path.join(PROFILE_DIR, "wallpaperscraft_categories.json")
CATALOG_MAX_AGE = 24 * 60 * 60
try:
    if not xbmcvfs.exists(CAT_THUMB_DIR):
        xbmcvfs.mkdirs(CAT_THUMB_DIR)
except Exception:
    pass

def _log(msg):
    try:
        xbmc.log(f"[{ADDON_ID}] {msg}", xbmc.LOGINFO)
    except Exception:
        print(f"[{ADDON_ID}] {msg}")

def _url(**kwargs):
    return BASE_URL + "?" + up.urlencode(kwargs)

def _get(setting, default=""):
    try:
        v = ADDON.getSetting(setting)
        return v if v not in ("", None) else default
    except Exception:
        return default

def _get_bool(setting, default=False):
    return (_get(setting, "true" if default else "false").lower() in ("true","1","yes","on"))

def _sanitize_name(name):
    bad = '<>:"/\\|?*'
    out = "".join(("_" if c in bad else c) for c in name).strip()
    return out[:120] or "wallpaper"

def _addon_path(*parts):
    base = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
    return os.path.join(base, *parts)

def _set_tile_art(item, art):
    item.setArt({"thumb": art, "icon": art, "poster": art, "landscape": art, "fanart": art})


def _http_get_small(url, timeout=5, max_bytes=2 * 1024 * 1024):
    try:
        req = urlreq.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": BASE_SITE})
        with urlreq.urlopen(req, timeout=timeout) as response:
            image = response.read(max_bytes + 1)
        if len(image) <= max_bytes and image.startswith(b"\xff\xd8") and image.endswith(b"\xff\xd9"):
            return image
    except Exception as e:
        _log(f"thumb fetch failed: {e}")
    return b""

def _cat_cache_path(slug):
    return os.path.join(CAT_THUMB_DIR, f"{slug}.jpg")

def _cat_local_art(slug):
    cat_dir = _addon_path("resources", "media", "categories")
    for ext in (".png", ".jpg", ".jpeg"):
        p = os.path.join(cat_dir, slug + ext)
        if xbmcvfs.exists(p):
            return p
    aliases = {
        "black_and_white": ["black-and-white", "bw"],
        "tv-series": ["tv_series", "tvseries", "serials", "tv"],
        "hi-tech": ["technologies", "technology", "tech"],
        "sport": ["sports"],
    }
    for alt in aliases.get(slug, []):
        for ext in (".png", ".jpg", ".jpeg"):
            p = os.path.join(cat_dir, alt + ext)
            if xbmcvfs.exists(p):
                return p
    fallback = _addon_path("resources", "media", "catalog_default.png")
    return fallback if xbmcvfs.exists(fallback) else ""

def _cat_thumb(slug):
    cached = _cat_cache_path(slug)
    if xbmcvfs.exists(cached):
        return cached
    return _cat_local_art(slug)

def _get_download_dir():
    raw = (_get("download_path", "").strip()
           or "special://home/addons/resource.images.skinbackgrounds.xenon/resources/custom")
    try:
        if not xbmcvfs.exists(raw):
            xbmcvfs.mkdirs(raw)
    except Exception:
        pass
    dest_dir = xbmcvfs.translatePath(raw)
    try:
        if not xbmcvfs.exists(dest_dir):
            xbmcvfs.mkdirs(dest_dir)
    except Exception:
        pass
    return dest_dir



def _should_abort():
    try:
        import xbmc
        return xbmc.Monitor().abortRequested()
    except Exception:
        return False

def _category_entries():
    try:
        with open(CATALOG_CACHE, encoding="utf-8") as cached:
            entries = json.load(cached)
        if isinstance(entries, list) and entries and all(
            isinstance(entry, list) and len(entry) == 3
            and isinstance(entry[0], str) and isinstance(entry[1], str)
            and re.fullmatch(r"[a-z0-9_-]+", entry[1]) and entry[2] == "catalog"
            for entry in entries
        ):
            return entries
    except (OSError, ValueError):
        pass
    return [
        ("3D", "3d", "catalog"),
        ("Abstract", "abstract", "catalog"),
        ("Anime", "anime", "catalog"),
        ("City", "city", "catalog"),
        ("Dark", "dark", "catalog"),
        ("Flowers", "flowers", "catalog"),
        ("Minimalism", "minimalism", "catalog"),
        ("Motorcycles", "motorcycles", "catalog"),
        ("Other", "other", "catalog"),
        ("Space", "space", "catalog"),
        ("Textures", "textures", "catalog"),
        ("Vector", "vector", "catalog"),

        ("Animals", "animals", "catalog"),
        ("Art", "art", "catalog"),
        ("Black", "black", "catalog"),
        ("Black and White", "black_and_white", "catalog"),
        ("Cars", "cars", "catalog"),
        ("Fantasy", "fantasy", "catalog"),
        ("Food", "food", "catalog"),
        ("Holidays", "holidays", "catalog"),
        ("Love", "love", "catalog"),
        ("Macro", "macro", "catalog"),
        ("Music", "music", "catalog"),
        ("Nature", "nature", "catalog"),
        ("Sport", "sport", "catalog"),
        ("Technologies", "hi-tech", "catalog"),
        ("Words", "words", "catalog"),
    ]

# -------------------------------
# Root (reports: files) + Search + My Wallpapers
# -------------------------------
def show_root():
    xbmcplugin.setContent(HANDLE, "files")

    # Search
    li = xbmcgui.ListItem(label="Search…")
    _set_tile_art(li, _addon_path("resources", "media", "search.png"))
    xbmcplugin.addDirectoryItem(HANDLE, _url(mode="search_prompt"), li, isFolder=False)

    # My Wallpapers (browse downloaded folder)
    mi = xbmcgui.ListItem(label="My Wallpapers")
    catalog_art = _addon_path("resources", "media", "catalog_default.png")
    _set_tile_art(mi, catalog_art)
    xbmcplugin.addDirectoryItem(HANDLE, _url(mode="my_wallpapers", dir=_get_download_dir()), mi, isFolder=True)
    # Diggz Wallpapers source
    di = xbmcgui.ListItem(label="Diggz Wallpapers")
    _set_tile_art(di, catalog_art)
    xbmcplugin.addDirectoryItem(HANDLE, _url(mode="diggz_root"), di, isFolder=True)


    # Categories (use cached/local art now; warm in background after opening)
    entries = _category_entries()
    for title, slug, kind in entries:
        li = xbmcgui.ListItem(label=title)
        thumb = _cat_thumb(slug)
        if thumb:
            _set_tile_art(li, thumb)
        url = _url(mode="category", kind=kind, slug=slug, page="1", title=title)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

    if _catalog_needs_refresh() or (
        not _get_bool("use_static_thumbs", False) and any(
            not xbmcvfs.exists(_cat_cache_path(slug)) for _, slug, _ in entries
        )
    ):
        xbmc.executebuiltin(f'RunPlugin("{_url(mode="warm_thumbs")}")')

def search_prompt(_params):
    """Prompt for a query, then open the Search results (page 1)."""
    try:
        dlg = xbmcgui.Dialog()
        query = dlg.input("Search Wallpapers", type=xbmcgui.INPUT_ALPHANUM)
    except Exception:
        query = ""
    if not query:
        try:
            xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        except Exception:
            pass
        return
    # Navigate to search results page 1, replacing the current view
    try:
        xbmc.executebuiltin(f'Container.Update("{_url(mode="search", q=query, page="1")}")')
    except Exception:
        pass
    try:
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
    except Exception:
        pass
    return



def _catalog_needs_refresh():
    try:
        return time.time() - os.path.getmtime(CATALOG_CACHE) >= CATALOG_MAX_AGE
    except OSError:
        return True


def warm_thumbs(_params):
    window = xbmcgui.Window(10000)
    running = f"{ADDON_ID}.warming_category_thumbs"
    if window.getProperty(running):
        return
    window.setProperty(running, "true")
    try:
        if _catalog_needs_refresh() and not _should_abort():
            try:
                entries = wc.list_categories()
                if entries:
                    _write_cache_file(CATALOG_CACHE, json.dumps(entries).encode("utf-8"))
            except Exception as e:
                _log(f"catalog refresh failed: {e}")
        if _get_bool("use_static_thumbs", False):
            return

        for _, slug, kind in _category_entries():
            if _should_abort():
                break
            cached = _cat_cache_path(slug)
            if xbmcvfs.exists(cached):
                continue
            try:
                items, _ = wc.list_wallpapers(kind, slug, 1)
                previews = [item.get("preview") for item in items[:5]]
                previews += [item.get("thumb") for item in items[:3]]
                for thumb in dict.fromkeys(previews):
                    if not thumb or _should_abort():
                        continue
                    image = _http_get_small(thumb)
                    if image:
                        _write_cache_file(cached, image)
                        break
            except Exception as e:
                _log(f"category thumb failed for {slug}: {e}")
    finally:
        window.clearProperty(running)


def _write_cache_file(path, data):
    # Publish the cache entry only after the entire file has been written.
    staged = tempfile.NamedTemporaryFile(dir=os.path.dirname(path), delete=False)
    try:
        with staged:
            staged.write(data)
        os.replace(staged.name, path)
    finally:
        if os.path.exists(staged.name):
            os.remove(staged.name)


def list_search_results(params):
    query = params.get("q", "")
    page = int(params.get("page", "1"))
    xbmcplugin.setContent(HANDLE, "movies")
    _log(f"Search '{query}' page={page}")

    if _should_abort():
        return
    # Retry the network search a few times before declaring "No results".
    # This avoids a premature notification while the site responds slowly.
    items, has_next = [], False
    max_wait_s = 10  # total extra wait budget (kept modest to avoid blocking UI too long)
    start = time.time()
    attempts = 0

    # Show a busy dialog while we give the search a fair chance to return.
    try:
        xbmc.executebuiltin("ActivateWindow(busydialog)")
    except Exception:
        pass

    while not items:
        attempts += 1
        try:
            items, has_next = wc.list_search(query, page)
        except Exception as e:
            _log(f"list_search error (attempt {attempts}): {e}")
            items, has_next = [], False

        # If we got items or we've waited long enough, break.
        if items or (time.time() - start) >= max_wait_s or attempts >= 2:
            break

        # Brief pause before a quick re-try in case the first attempt raced with a slow site.
        xbmc.sleep(800)

    # Close busy dialog if we opened it
    try:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    except Exception:
        pass

    if not items:
        try:
            xbmcgui.Dialog().notification("4K Wallpapers", f"No results for '{query}'",
                                          xbmcgui.NOTIFICATION_INFO, 3000)
        except Exception:
            pass

    for it in items:
        lbl = it.get("title") or "Wallpaper"
        li = xbmcgui.ListItem(label=lbl)
        th = it.get("thumb")
        if th:
            li.setArt({"thumb": th, "icon": th, "poster": th, "fanart": th})
        _set_video_title(li, lbl)
        url = _url(mode="wallpaper", page_url=it.get("href",""), title=lbl, thumb=th or "")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    if has_next:
        nli = xbmcgui.ListItem(label=f"Next (page {page+1})")
        _set_tile_art(nli, _addon_path("resources", "media", "next_page.png"))
        _set_video_title(nli, f"{query} — page {page+1}")
        nurl = _url(mode="search", q=query, page=str(page+1))
        xbmcplugin.addDirectoryItem(HANDLE, nurl, nli, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, updateListing=(page>1), cacheToDisc=False)


# -------------------------------
# Category (reports: movies) -> list wallpapers
# -------------------------------
def list_category(params):
    kind  = params.get("kind", "catalog")
    slug  = params.get("slug", "")
    title = params.get("title", slug or "Wallpapers")
    page  = int(params.get("page", "1"))

    if _should_abort():
        return
    _log(f"Opening '{title}' ({kind}:{slug}) page={page}")
    xbmcplugin.setContent(HANDLE, "movies")

    items, has_next = [], False
    try:
        items, has_next = wc.list_wallpapers(kind, slug, page)
    except Exception as e:
        _log(f"list_wallpapers error for {kind}:{slug} p{page}: {e}")

    if not items:
        aliases = {
            "black_and_white": ["black-and-white", "bw"],
            "tv-series": ["tv_series", "tvseries", "serials", "tv"],
            "hi-tech": ["technologies", "technology", "tech"],
            "sport": ["sports"],
        }
        candidates = [(kind, slug)]
        if slug in aliases:
            for s in aliases[slug]:
                candidates.append((kind, s))
        for s in [slug] + aliases.get(slug, []):
            candidates.append(("tag", s))

        seen = set()
        for k, s in candidates:
            key = f"{k}:{s}"
            if key in seen:
                continue
            seen.add(key)
            try:
                tmp_items, tmp_next = wc.list_wallpapers(k, s, page)
                if tmp_items:
                    kind, slug = k, s
                    items, has_next = tmp_items, tmp_next
                    break
            except Exception:
                continue

    if not items:
        try:
            xbmcgui.Dialog().notification("4K Wallpapers", f"{title}: No results or timed out",
                                          xbmcgui.NOTIFICATION_INFO, 3000)
        except Exception:
            pass

    for it in items:
        lbl = it.get("title") or title
        li = xbmcgui.ListItem(label=lbl)
        th = it.get("thumb")
        if th:
            li.setArt({"thumb": th, "icon": th, "poster": th, "fanart": th})
        _set_video_title(li, lbl)
        url = _url(mode="wallpaper", page_url=it.get("href",""), title=lbl, thumb=th or "")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    if has_next:
        nli = xbmcgui.ListItem(label=f"Next (page {page+1})")
        _set_tile_art(nli, _addon_path("resources", "media", "next_page.png"))
        _set_video_title(nli, f"{title} — page {page+1}")
        nurl = _url(mode="category", kind=kind, slug=slug, page=str(page+1), title=title)
        xbmcplugin.addDirectoryItem(HANDLE, nurl, nli, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, updateListing=(page>1), cacheToDisc=False)

# -------------------------------
# Wallpaper submenu (reports: files) -> 4K & 1080p; clicking downloads
# -------------------------------
def _set_video_title(li, title):
    try:
        vit = li.getVideoInfoTag()
        vit.setTitle(title)
    except Exception:
        li.setInfo("video", {"title": title})

def wallpaper_menu(params):
    page_url = params.get("page_url","")
    title    = params.get("title","Wallpaper")
    preview  = params.get("thumb", "")

    xbmcplugin.setContent(HANDLE, "files")

    try:
        sizes = wc.list_sizes(page_url)  # [{"label","url","thumb"}]
    except Exception as e:
        _log(f"list_sizes failed: {e}")
        sizes = []

    by_label = {(s.get("label") or "").lower(): s for s in (sizes or [])}
    picks = []

    if "3840x2160" in by_label:
        picks.append(("4K (3840x2160)", "3840x2160", by_label["3840x2160"]))
    elif "4096x2160" in by_label:
        picks.append(("4K (4096x2160)", "4096x2160", by_label["4096x2160"]))

    if "1920x1080" in by_label:
        picks.append(("1080p (1920x1080)", "1920x1080", by_label["1920x1080"]))

    if not picks:
        try:
            xbmcgui.Dialog().notification("4K Wallpapers", "No 4K or 1080p sizes found",
                                          xbmcgui.NOTIFICATION_INFO, 3000)
        except Exception:
            pass
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    for display_lbl, label_raw, s in picks:
        img_url = s.get("url") or page_url
        li = xbmcgui.ListItem(label=f"Download {display_lbl}")
        th = preview or s.get("thumb", "")
        if th:
            li.setArt({"thumb": th, "icon": th})
        url = _url(mode="download_image", img=img_url, title=title, label=label_raw, ref=page_url)
        li.setProperty("IsPlayable", "false")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

# -------------------------------
# Download selected image
# -------------------------------
def download_image(params):
    img_url = params.get("img", "")
    title   = params.get("title", "Wallpaper")
    label   = params.get("label", "")
    referer = params.get("ref", "")

    if not img_url:
        xbmcgui.Dialog().notification("4K Wallpapers", "Missing image URL",
                                      xbmcgui.NOTIFICATION_ERROR, 2500)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    dest_dir = _get_download_dir()

    base = _sanitize_name(f"{title}_{label}" if label else title)
    staged = os.path.join(dest_dir, f".wallpaper-{uuid.uuid4().hex}.part")

    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
        "Accept": "*/*",
    }
    if referer:
        headers["Referer"] = referer

    dp = xbmcgui.DialogProgress()
    try:
        dp.create("4K Wallpapers", "Starting download...")
        req = urlreq.Request(img_url, headers=headers)
        with urlreq.urlopen(req, timeout=20) as response:
            total = int(response.headers.get("Content-Length") or 0)
            if dp.iscanceled():
                return
            first = response.read(1024 * 1024)
            ext = _download_image_extension(first)
            if not ext:
                raise ValueError("Server response is not a supported image")

            written = 0
            last_update = 0
            file = xbmcvfs.File(staged, "w")
            try:
                chunk = first
                while chunk:
                    if dp.iscanceled():
                        return
                    if not file.write(bytearray(chunk)):
                        raise OSError("Could not write wallpaper")
                    written += len(chunk)
                    now = time.monotonic()
                    if now - last_update > 0.1:
                        percent = min(99, written * 100 // total) if total else 0
                        message = f"Downloading… {written / (1024 * 1024):.1f} MB"
                        if total:
                            message += f" / {total / (1024 * 1024):.1f} MB"
                        dp.update(percent, message)
                        last_update = now
                    chunk = response.read(1024 * 1024)
            finally:
                file.close()
            if total and written != total:
                raise OSError(f"Incomplete wallpaper: received {written} of {total} bytes")

        if dp.iscanceled():
            return
        saved_path = _publish_download(staged, dest_dir, base, ext)
        dp.update(100, "Download complete")
        xbmcgui.Dialog().notification("4K Wallpapers", f"Saved {os.path.basename(saved_path)}",
                                      xbmcgui.NOTIFICATION_INFO, 3500)
    except Exception as e:
        _log(f"Download failed: {e}")
        xbmcgui.Dialog().notification("4K Wallpapers", "Download failed",
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
    finally:
        try:
            if xbmcvfs.exists(staged) and not xbmcvfs.delete(staged):
                _log(f"Could not remove temporary wallpaper: {staged}")
        finally:
            dp.close()
            xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def _download_image_extension(data):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ""


def _publish_download(staged, dest_dir, base, ext):
    index = 0
    while True:
        suffix = f"_{index}" if index else ""
        path = os.path.join(dest_dir, f"{base}{suffix}{ext}")
        index += 1
        # Reserve the name across add-on invocations, including VFS destinations.
        key = hashlib.sha256(os.path.normcase(path).encode("utf-8")).hexdigest()
        lock = os.path.join(PROFILE_DIR, f"download-{key}.lock")
        try:
            os.mkdir(lock)
        except FileExistsError:
            continue
        try:
            if xbmcvfs.exists(path):
                continue
            if not xbmcvfs.rename(staged, path):
                raise OSError("Could not move wallpaper into place")
            return path
        finally:
            os.rmdir(lock)


# -------------------------------
# My Wallpapers: browse, view, delete, import
# -------------------------------
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")

def my_wallpapers(params):
    cur = params.get("dir") or _get_download_dir()
    cur = xbmcvfs.translatePath(cur)

    xbmcplugin.setContent(HANDLE, "images")

    # Top actions
    imp1 = xbmcgui.ListItem(label="[Import single image…]")
    art = _addon_path("resources", "media", "import_single.png")
    if not xbmcvfs.exists(art):
        art = _addon_path("resources", "media", "catalog_default.png")
    _set_tile_art(imp1, art)
    xbmcplugin.addDirectoryItem(HANDLE, _url(mode="import_image"), imp1, isFolder=False)
    imp2 = xbmcgui.ListItem(label="[Import multiple images…]")
    art = _addon_path("resources", "media", "import_multiple.png")
    if not xbmcvfs.exists(art):
        art = _addon_path("resources", "media", "catalog_default.png")
    _set_tile_art(imp2, art)
    xbmcplugin.addDirectoryItem(HANDLE, _url(mode="import_folder"), imp2, isFolder=False)

    dl = _get_download_dir().rstrip("/\\")
    if os.path.normpath(cur) != os.path.normpath(dl):
        par = os.path.dirname(cur.rstrip("/\\")) or cur
        pli = xbmcgui.ListItem(label="↥ Parent folder")
        _set_tile_art(pli, _addon_path("resources", "media", "parent_folder.png"))
        xbmcplugin.addDirectoryItem(HANDLE, _url(mode="my_wallpapers", dir=par), pli, isFolder=True)

    try:
        dirs, files = xbmcvfs.listdir(cur)
    except Exception:
        dirs, files = [], []
    for d in dirs:
        p = os.path.join(cur, d)
        li = xbmcgui.ListItem(label=f"[{d}]")
        li.setArt({"icon": "DefaultFolder.png", "thumb": "DefaultFolder.png"})
        xbmcplugin.addDirectoryItem(HANDLE, _url(mode="my_wallpapers", dir=p), li, isFolder=True)

    for f in files:
        if not f.lower().endswith(IMG_EXTS):
            continue
        p = os.path.join(cur, f)
        li = xbmcgui.ListItem(label=f)
        li.setArt({"thumb": p, "icon": p, "poster": p, "fanart": p})
        url = _url(mode="open_context", fp=p)
        cmi = [
            ("View",   f'RunPlugin("{_url(mode="view_file", fp=p)}")'),
            ("Delete", f'RunPlugin("{_url(mode="delete_file", fp=p)}")'),
        ]
        li.addContextMenuItems(cmi, replaceItems=False)
        li.setProperty("IsPlayable", "false")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def open_context(params):
    xbmc.executebuiltin('Action(ContextMenu)')
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def view_file(params):
    fp = params.get("fp","")
    if fp:
        xbmc.executebuiltin(f'ShowPicture("{fp}")')
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def delete_file(params):
    fp = params.get("fp","")
    if not fp or not xbmcvfs.exists(fp):
        xbmcgui.Dialog().notification("4K Wallpapers", "File not found",
                                      xbmcgui.NOTIFICATION_ERROR, 2500)
    else:
        if xbmcgui.Dialog().yesno("Delete", f"Delete this file?\\n{os.path.basename(fp)}"):
            ok = False
            try:
                ok = xbmcvfs.delete(fp)
            except Exception as e:
                _log(f"delete failed: {e}")
            if ok:
                xbmcgui.Dialog().notification("4K Wallpapers", "Deleted", xbmcgui.NOTIFICATION_INFO, 2000)
            else:
                xbmcgui.Dialog().notification("4K Wallpapers", "Delete failed", xbmcgui.NOTIFICATION_ERROR, 2500)
        xbmc.executebuiltin("Container.Refresh")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def import_image(_params):
    try:
        src = xbmcgui.Dialog().browse(2, "Select image", "files", ".jpg|.jpeg|.png|.webp")
    except TypeError:
        src = xbmcgui.Dialog().browse(1, "Select image", "files")
    if not src:
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    if not xbmcvfs.exists(src):
        xbmcgui.Dialog().notification("4K Wallpapers", "Source not found", xbmcgui.NOTIFICATION_ERROR, 2500)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    if not src.lower().endswith((".jpg",".jpeg",".png",".webp")):
        xbmcgui.Dialog().notification("4K Wallpapers", "Not an image file", xbmcgui.NOTIFICATION_ERROR, 2500)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    dest_dir = _get_download_dir()
    base = _sanitize_name(os.path.splitext(os.path.basename(src))[0])
    ext = os.path.splitext(src)[1].lower() or ".jpg"
    i = 0
    while True:
        name = f"{base}{'' if i == 0 else f'_{i}'}{ext}"
        dest = os.path.join(dest_dir, name)
        if not xbmcvfs.exists(dest):
            break
        i += 1
    ok = False
    try:
        ok = xbmcvfs.copy(src, dest)
    except Exception as e:
        _log(f"copy failed: {e}")
    if ok:
        xbmcgui.Dialog().notification("4K Wallpapers", "Imported", xbmcgui.NOTIFICATION_INFO, 2000)
    else:
        xbmcgui.Dialog().notification("4K Wallpapers", "Import failed", xbmcgui.NOTIFICATION_ERROR, 2500)
    xbmc.executebuiltin(f'Container.Update("{_url(mode="my_wallpapers", dir=dest_dir)}", replace)')

def import_folder(_params):
    try:
        src_dir = xbmcgui.Dialog().browse(3, "Select folder", "files")
    except TypeError:
        src_dir = xbmcgui.Dialog().browse(0, "Select folder", "files")
    if not src_dir:
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    if not xbmcvfs.exists(src_dir):
        xbmcgui.Dialog().notification("4K Wallpapers", "Folder not found", xbmcgui.NOTIFICATION_ERROR, 2500)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    dest_dir = _get_download_dir()
    try:
        dirs, files = xbmcvfs.listdir(src_dir)
    except Exception:
        dirs, files = [], []
    images = [f for f in files if f.lower().endswith((".jpg",".jpeg",".png",".webp"))]
    if not images:
        xbmcgui.Dialog().notification("4K Wallpapers", "No images in folder", xbmcgui.NOTIFICATION_INFO, 2500)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    dp = xbmcgui.DialogProgress()
    dp.create("Importing", f"{len(images)} image(s)…")
    copied, failed = 0, 0
    for idx, fname in enumerate(images, 1):
        if dp.iscanceled():
            break
        dp.update(int((idx * 100) / len(images)), f"{fname}")
        src = os.path.join(src_dir, fname)
        base = _sanitize_name(os.path.splitext(fname)[0])
        ext = os.path.splitext(fname)[1].lower()
        j = 0
        while True:
            name = f"{base}{'' if j == 0 else f'_{j}'}{ext}"
            dest = os.path.join(dest_dir, name)
            if not xbmcvfs.exists(dest):
                break
            j += 1
        try:
            if xbmcvfs.copy(src, dest):
                copied += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    try:
        dp.close()
    except Exception:
        pass

    xbmcgui.Dialog().notification("4K Wallpapers", f"Imported: {copied}, Failed: {failed}",
                                  xbmcgui.NOTIFICATION_INFO, 3500)
    xbmc.executebuiltin(f'Container.Update("{_url(mode="my_wallpapers", dir=dest_dir)}", replace)')



# -------------------------------
# Diggz Wallpapers integration
# -------------------------------
def diggz_root(_params):
    if not diggz_source:
        xbmcgui.Dialog().notification("4K Wallpapers", "Diggz source not available", xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    xbmcplugin.setContent(HANDLE, "files")
    try:
        cats = diggz_source.list_categories()
    except Exception as e:
        _log(f"Diggz list_categories failed: {e}")
        xbmcgui.Dialog().notification("4K Wallpapers", "Failed to load Diggz categories", xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    for c in cats:
        title = c.get("title") or "Folder"
        href  = c.get("href") or ""
        li = xbmcgui.ListItem(label=title)
        li.setArt({"icon": "DefaultFolder.png", "thumb": "DefaultFolder.png"})
        url = _url(mode="diggz_category", path=href, title=title)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def list_diggz_category(params):
    if not diggz_source:
        xbmcgui.Dialog().notification("4K Wallpapers", "Diggz source not available", xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return
    path = params.get("path", "")
    title = params.get("title", "Diggz")
    xbmcplugin.setContent(HANDLE, "images")
    try:
        imgs = diggz_source.list_images(path)
    except Exception as e:
        _log(f"Diggz list_images failed: {e}")
        xbmcgui.Dialog().notification("4K Wallpapers", "Failed to load images", xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    for it in imgs:
        name = it.get("title") or "Wallpaper"
        img  = it.get("img") or ""
        thumb = it.get("thumb") or img
        li = xbmcgui.ListItem(label=name)
        art = {"thumb": thumb, "icon": thumb, "fanart": thumb, "poster": thumb}
        li.setArt(art)
        li.setInfo("image", {"title": name})
        # Context menu: download
        cm = [("Download", f'RunPlugin("{_url(mode="download_image", img=img, title=title, label=name, ref="diggz")}")')]
        try:
            li.addContextMenuItems(cm, replaceItems=False)
        except Exception:
            pass
        # Clicking the item downloads immediately (consistent with add-on behavior)
        url = _url(mode="download_image", img=img, title=title, label=name, ref="diggz")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


# -------------------------------
# Router / Entry
# -------------------------------
def router(params):
    mode = params.get("mode", "root")
    if mode == "root":
        show_root()
    elif mode == "search_prompt":
        search_prompt(params)
    elif mode == "search":
        list_search_results(params)
    elif mode == "category":
        list_category(params)
    elif mode == "wallpaper":
        wallpaper_menu(params)
    elif mode == "download_image":
        download_image(params)
    elif mode == "my_wallpapers":
        my_wallpapers(params)
    elif mode == "open_context":
        open_context(params)
    elif mode == "view_file":
        view_file(params)
    elif mode == "delete_file":
        delete_file(params)
    elif mode == "import_image":
        import_image(params)
    elif mode == "import_folder":
        import_folder(params)
    elif mode == "warm_thumbs":
        warm_thumbs(params)
    elif mode == "diggz_root":
        diggz_root(params)
    elif mode == "diggz_category":
        list_diggz_category(params)
    else:
        show_root()

if __name__ == "__main__":
    qs = {}
    if len(sys.argv) > 2 and sys.argv[2]:
        qs = dict(up.parse_qsl(sys.argv[2][1:]))
    router(qs)

