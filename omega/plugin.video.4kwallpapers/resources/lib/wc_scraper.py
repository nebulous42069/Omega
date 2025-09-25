# -*- coding: utf-8 -*-
import re
from urllib.parse import urljoin, quote_plus as _qp
from urllib.request import Request, urlopen
import time, random

# Optional Kodi logging
try:
    import xbmc  # type: ignore
except Exception:
    xbmc = None

def _log(msg):
    try:
        if xbmc:
            xbmc.log(f"[wc_scraper] {msg}", xbmc.LOGINFO)
        else:
            print(f"[wc_scraper] {msg}")
    except Exception:
        pass

BASE = "https://wallpaperscraft.com/"
CDN_BASE = "https://images.wallpaperscraft.com/image/single/"

# polite rate limiter & search URL winner (per-process; reset each Kodi invocation)
_MIN_REQ_GAP = 1.1
_LAST_REQ_TS = 0.0
_SEARCH_WINNER = None  # 'q_then_page' | 'page_then_q' | 'full_order_size'

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ---------- regex (listings) ----------
_RE_ITEM_STRICT = re.compile(
    r'<a[^>]+class="[^"]*\\bwallpapers__link\\b[^"]*"[^>]+href="(?P<href>/wallpaper/(?P<slug>[a-z0-9_\\-]+))"[^>]*?'
    r'(?:(?:data-srcset|srcset)="(?P<srcset>[^"]+)"|(?:data-src|src)="(?P<src>[^"]+)")',
    re.I | re.S,
)
_RE_ITEM_LOOSE = re.compile(
    r'<a[^>]+class="[^"]*\\bwallpapers__link\\b[^"]*"[^>]+href="(?P<href>/wallpaper/(?P<slug>[a-z0-9_\\-]+))"[^>]*>',
    re.I,
)
_RE_ITEM_ANY = re.compile(r'href="/wallpaper/(?P<slug>[a-z0-9_\\-]+)"', re.I)
_RE_REL_NEXT = re.compile(r'rel="next"', re.I)

# ---------- regex (sizes) ----------
# Accept relative/absolute, single/double quotes, optional trailing slash and query strings
_RE_SIZE_DOWNLOAD = re.compile(
    r'href\\s*=\\s*["\\\'](?P<u>/(?:download|image|images)/[a-z0-9_\\-]+(?:_[0-9]+)?/(?P<label>\\d{3,4}x\\d{3,4})(?:/)?(?:\\?[^"\\\']*)?)["\\\']',
    re.I
)
_RE_SIZE_DOWNLOAD_ABS = re.compile(
    r'href\\s*=\\s*["\\\'](?P<u>https?://[^"\\\']*/(?:download|image|images)/[a-z0-9_\\-]+(?:_[0-9]+)?/(?P<label>\\d{3,4}x\\d{3,4})(?:/)?(?:\\?[^"\\\']*)?)["\\\']',
    re.I
)
_RE_SIZE_DATA = re.compile(
    r'data-(?:href|url)\\s*=\\s*["\\\'](?P<u>/(?:download|image|images)/[a-z0-9_\\-]+(?:_[0-9]+)?/(?P<label>\\d{3,4}x\\d{3,4})(?:/)?(?:\\?[^"\\\']*)?)["\\\']',
    re.I
)
_RE_SIZE_ABSFILE = re.compile(
    r'href\\s*=\\s*["\\\'](?P<u>(?:https?:)?//[^"\\\']+?_(?P<label>\\d{3,4}x\\d{3,4})\\.(?:jpe?g|png))["\\\']', re.I
)
_RE_SIZE_TEXTFILE = re.compile(
    r'href\\s*=\\s*["\\\'](?P<u>[^"\\\']+\\.(?:jpe?g|png))["\\\'][^>]*>\\s*(?P<label>\\d{3,4}x\\d{3,4})\\s*<', re.I
)

_RE_WALLPAPER_SLUG = re.compile(r'/wallpaper/([a-z0-9_\\-]+)', re.I)
_RE_DOWNLOAD_SLUG  = re.compile(r'/download/([a-z0-9_\\-]+)', re.I)

# ---------- net ----------

def _fetch(url: str, timeout: int = 8) -> str:
    global _LAST_REQ_TS
    now = time.time()
    gap = _MIN_REQ_GAP - (now - _LAST_REQ_TS)
    if gap > 0:
        time.sleep(gap + random.uniform(0, 0.25))
    _LAST_REQ_TS = time.time()
    _log(f"GET {url}")
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:
        try:
            from urllib.error import HTTPError
            if isinstance(e, HTTPError) and getattr(e, 'code', None) == 429:
                ra = ''
                try:
                    ra = e.headers.get('Retry-After', '') if getattr(e, 'headers', None) else ''
                except Exception:
                    ra = ''
                try:
                    backoff = int(ra) if ra.strip().isdigit() else 3
                except Exception:
                    backoff = 3
                backoff = min(max(backoff, 2), 8) + random.uniform(0, 0.5)
                _log(f"429 backoff {backoff:.1f}s")
                time.sleep(backoff)
                with urlopen(req, timeout=timeout) as r2:
                    return r2.read().decode("utf-8", "ignore")
        except Exception:
            pass
        raise

def _head_or_probe(url: str, timeout: int = 6, referer: str = "") -> bool:
    """Return True if URL exists (200/206/302), HEAD first then tiny GET with Range."""
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    try:
        _log(f"HEAD {url}")
        req = Request(url, headers=headers, method="HEAD")
        with urlopen(req, timeout=timeout) as r:
            code = getattr(r, "status", 200)
            ok = 200 <= code < 400
            _log(f"HEAD {code} {'OK' if ok else 'NO'}")
            if ok:
                return True
    except Exception as e:
        _log(f"HEAD failed: {e}")
    try:
        headers2 = dict(headers)
        headers2["Range"] = "bytes=0-0"  # tiny probe
        _log(f"GET(probe) {url}")
        req = Request(url, headers=headers2)
        with urlopen(req, timeout=timeout) as r:
            code = getattr(r, "status", 200)
            ok = (200 <= code < 400) or code == 206
            _log(f"GET {code} {'OK' if ok else 'NO'}")
            return ok
    except Exception as e:
        _log(f"GET probe failed: {e}")
        return False

# ---------- parse listings ----------
def _best_src_from_srcset(srcset: str) -> str:
    if not srcset:
        return ""
    parts = [p.strip() for p in srcset.split(",") if p.strip()]
    if not parts:
        return ""
    return parts[-1].split(" ")[0].strip()


def _parse_items(html: str):
    out, seen = [], set()
    if not html:
        return out
    REL_STRICT = re.compile(
        r'<a[^>]+class="[^"]*\bwallpapers__link\b[^"]*"[^>]+href="(?P<href>/wallpaper/(?P<slug>[a-z0-9_\-]+))"[^>]*?'
        r'(?:(?:data-srcset|srcset)="(?P<srcset>[^"]+)"|(?:data-src|src)="(?P<src>[^"]+)")',
        re.I | re.S,
    )
    REL_LOOSE = re.compile(
        r'<a[^>]+class="[^"]*\bwallpapers__link\b[^"]*"[^>]+href="(?P<href>/wallpaper/(?P<slug>[a-z0-9_\-]+))"[^>]*>',
        re.I,
    )
    REL_ANY = re.compile(r'href="/wallpaper/(?P<slug>[a-z0-9_\-]+)"', re.I)
    ABS_STRICT = re.compile(
        r'<a[^>]+class="[^"]*\bwallpapers__link\b[^"]*"[^>]+href="(?P<href>(?:https?:)?//[^"\']*/wallpaper/(?P<slug>[a-z0-9_\-]+))"[^>]*?'
        r'(?:(?:data-srcset|srcset)="(?P<srcset>[^"]+)"|(?:data-src|src)="(?P<src>[^"]+)")',
        re.I | re.S,
    )
    ABS_LOOSE = re.compile(
        r'<a[^>]+class="[^"]*\bwallpapers__link\b[^"]*"[^>]+href="(?P<href>(?:https?:)?//[^"\']*/wallpaper/(?P<slug>[a-z0-9_\-]+))"[^>]*>',
        re.I,
    )
    ABS_ANY = re.compile(r'href="(?P<href>(?:https?:)?//[^"\']*/wallpaper/(?P<slug>[a-z0-9_\-]+))"', re.I)
    CDN_ANY = re.compile(r'(?:https?:)?//[^"\']*/image/single/(?P<slug>[a-z0-9_\-]+)_\d+x\d+\.(?:jpe?g|png)', re.I)

    def best_src_from_srcset(srcset):
        best = ""
        if not srcset:
            return best
        try:
            mx, url = -1, ""
            for part in srcset.split(","):
                p = part.strip().split()
                if not p: continue
                u = p[0]
                w = 0
                for t in p[1:]:
                    if t.endswith("w"):
                        try:
                            w = int(t[:-1])
                        except Exception:
                            w = 0
                if w >= mx:
                    mx, url = w, u
            return url
        except Exception:
            return ""

    def add_item(slug, href, srcset="", src=""):
        if not slug or slug in seen:
            return
        seen.add(slug)
        if not href:
            href = f"/wallpaper/{slug}"
        grid = best_src_from_srcset(srcset) or src
        if grid.startswith("//"):
            grid = "https:" + grid
        thumb = f"{CDN_BASE}{slug}_1280x720.jpg" if slug else grid
        title = slug.replace("_", " ").replace("-", " ").title()
        out.append({"title": title, "thumb": thumb or grid, "href": _norm_url(urljoin(BASE, href))})

    for rx in (REL_STRICT, ABS_STRICT):
        for m in rx.finditer(html):
            gd = m.groupdict()
            add_item(gd.get("slug") or "", gd.get("href"), gd.get("srcset",""), gd.get("src",""))

    if not out:
        for rx in (REL_LOOSE, ABS_LOOSE):
            for m in rx.finditer(html):
                gd = m.groupdict()
                add_item(gd.get("slug") or "", gd.get("href"))

    if not out:
        for rx in (REL_ANY, ABS_ANY):
            for m in rx.finditer(html):
                gd = m.groupdict()
                add_item(gd.get("slug") or "", gd.get("href"))

    if not out:
        for m in CDN_ANY.finditer(html):
            slug = (m.groupdict().get("slug") or "").strip()
            add_item(slug, f"/wallpaper/{slug}")

    _log(f"_parse_items -> {len(out)} items")
    return out

def _page_urls(kind: str, slug: str, page: int):
    base = "tag" if str(kind).lower() == "tag" else "catalog"
    if page <= 1:
        return [urljoin(BASE, f"{base}/{slug}/"),
                urljoin(BASE, f"{base}/{slug}/?page=1")]
    return [urljoin(BASE, f"{base}/{slug}/page{page}/"),
            urljoin(BASE, f"{base}/{slug}/?page={page}")]


def _has_next_in_html(html: str, kind: str, slug: str, page: int) -> bool:
    if not html:
        return False
    if _RE_REL_NEXT.search(html):
        return True
    base = "tag" if str(kind).lower() == "tag" else "catalog"
    if f"/{base}/{slug}/page{page+1}/" in html or f"/{base}/{slug}/?page={page+1}" in html:
        return True
    try:
        for m in re.finditer(rf'/{base}/{re.escape(slug)}/page(\d+)/', html, re.I):
            try:
                if int(m.group(1)) > int(page):
                    return True
            except Exception:
                pass
        for m in re.finditer(r'[?&]page=(\d+)\b', html, re.I):
            try:
                if int(m.group(1)) > int(page):
                    return True
            except Exception:
                pass
    except Exception:
        pass
    if re.search(r'Last page|\u2192|>\s*Next\s*<', html, re.I):
        return True
    return False

def _norm_url(u: str) -> str:
    if not u:
        return ""
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("/"):
        u = urljoin(BASE, u)
    return u

def _slug_from_url(u: str) -> str:
    if not u:
        return ""
    m = _RE_WALLPAPER_SLUG.search(u)
    if m:
        return m.group(1)
    m = _RE_DOWNLOAD_SLUG.search(u)
    if m:
        return m.group(1)
    return ""

def _collect_sizes_from_html(html: str, want: set, found: dict):
    count_before = len(found)
    for rx in (_RE_SIZE_DOWNLOAD, _RE_SIZE_DOWNLOAD_ABS, _RE_SIZE_DATA,
               _RE_SIZE_ABSFILE, _RE_SIZE_TEXTFILE):
        for m in rx.finditer(html or ""):
            label = (m.group("label") or "").lower()
            if label in want and label not in found:
                found[label] = _norm_url(m.group("u"))
    _log(f"_collect_sizes_from_html added {len(found) - count_before}")

# ---------- public API ----------

def list_wallpapers(kind: str, slug: str, page: int = 1):
    html = ""
    items = []
    for u in _page_urls(kind, slug, page):
        try:
            html = _fetch(u, timeout=8)
        except Exception as e:
            _log(f"fetch failed {u}: {e}")
            continue
        items = _parse_items(html)
        if items:
            break
    has_next = _has_next_in_html(html, kind, slug, page)
    return items, has_next


def list_search(query: str, page: int = 1):
    global _SEARCH_WINNER
    qs = _qp(query or "")
    def urls_for(p):
        if _SEARCH_WINNER == 'q_then_page':
            return [urljoin(BASE, f"search/?query={qs}&page={p}")]
        if _SEARCH_WINNER == 'page_then_q':
            return [urljoin(BASE, f"search/?page={p}&query={qs}")]
        if _SEARCH_WINNER == 'full_order_size':
            return [urljoin(BASE, f"search/?order=&page={p}&query={qs}&size=")]
        if p <= 1:
            return [urljoin(BASE, f"search/?query={qs}"),
                    urljoin(BASE, f"search/?query={qs}&page=1"),
                    urljoin(BASE, f"search/?page=1&query={qs}")]
        return [urljoin(BASE, f"search/?query={qs}&page={p}"),
                urljoin(BASE, f"search/?page={p}&query={qs}"),
                urljoin(BASE, f"search/?order=&page={p}&query={qs}&size=")]
    html = ""
    items = []
    for u in urls_for(page):
        try:
            html = _fetch(u, timeout=8)
        except Exception as e:
            _log(f"search fetch failed {u}: {e}")
            continue
        items = _parse_items(html)
        if items:
            if not _SEARCH_WINNER:
                if "query=" in u and "&page=" in u:
                    _SEARCH_WINNER = 'q_then_page'
                elif "page=" in u and "&query=" in u:
                    _SEARCH_WINNER = 'page_then_q'
                else:
                    _SEARCH_WINNER = 'full_order_size'
            break
    has_next = False
    if html:
        if _RE_REL_NEXT.search(html):
            has_next = True
        if re.search(r"[?&]page=%d\b" % (page+1), html):
            has_next = True
        if not has_next and re.search(r'rel="next"|>\s*Next\s*<|Last page|\u2192', html, re.I):
            has_next = True
    return items, has_next

def list_sizes(page_url: str):
    # Only return 4K and/or 1080p that the site actually offers.
    want = ["3840x2160", "4096x2160", "1920x1080"]  # priority order
    want_set = set([w.lower() for w in want])
    found = {}

    _log(f"list_sizes for {page_url}")
    # A) Parse sizes from the wallpaper page HTML
    try:
        html = _fetch(page_url, timeout=8)
    except Exception as e:
        _log(f"fetch wallpaper page failed: {e}")
        html = ""
    _collect_sizes_from_html(html, want_set, found)

    # B) If still missing, try the "download index" page (lists sizes in the HTML on many slugs)
    slug = _slug_from_url(page_url)
    _log(f"slug = {slug}")
    if slug and len(found) < 2:
        idx = urljoin(BASE, f"download/{slug}/1024x768")
        try:
            h2 = _fetch(idx, timeout=8)
            _collect_sizes_from_html(h2, want_set, found)
        except Exception as e:
            _log(f"fetch download index failed: {e}")

    # C) If still missing, PROBE the CDN directly (works even when site hides sizes)
    #    Try .jpg then .png, with Referer to the wallpaper page and Range=0-0 probe.
    if slug:
        for label in want:
            key = label.lower()
            if key in found:
                continue
            for ext in (".jpg", ".png"):
                cdn_url = f"{CDN_BASE}{slug}_{label}{ext}"
                if _head_or_probe(cdn_url, timeout=6, referer=page_url):
                    found[key] = cdn_url
                    _log(f"probe CDN OK -> {label} ({ext})")
                    break

    _log(f"found labels: {list(found.keys())}")

    out = []
    if "3840x2160" in found:
        u = found["3840x2160"]
        out.append({"label": "3840x2160", "url": u, "thumb": u})
    elif "4096x2160" in found:
        u = found["4096x2160"]
        out.append({"label": "4096x2160", "url": u, "thumb": u})
    if "1920x1080" in found:
        u = found["1920x1080"]
        out.append({"label": "1920x1080", "url": u, "thumb": u})

    _log(f"list_sizes returning {len(out)} entries")
    return out
