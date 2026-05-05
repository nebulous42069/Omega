# -*- coding: utf-8 -*-
#
# MP3 Streams Echoed — plugin.audio.m3sr2019
# Copyright (C) 2019 L2501
# Modernised and extended by Echostorm / Claude (2026)
#
# Logging note: xbmc.log() is used for all diagnostics that must appear in
# kodi.log. The standard Python logging module is silent in Kodi addon context.
# log.warning() / log.debug() calls below are retained for IDE/unit-test use
# only — they produce zero output at runtime inside Kodi.

import hashlib
import json
import logging
import os
import time
from urllib.parse import urljoin, quote as url_quote

import xbmc
import requests
from bs4 import BeautifulSoup
from http.cookiejar import LWPCookieJar

from .peewee import (
    SqliteDatabase, Model, CharField, TextField, IntegerField, FloatField
)
from . import isodate

log = logging.getLogger(__name__)

db = SqliteDatabase(None)

# Minimum number of "content" elements a listing page must have to be
# considered valid and worth caching.  A login-wall page has 0 of these.
_MIN_VALID_ELEMENTS = 1


# --------------------------------------------------------------------------- #
# Database models
# --------------------------------------------------------------------------- #

class BaseModel(Model):
    class Meta:
        database = db


class Track(BaseModel):
    """Cached track metadata. Written when an album page is fetched."""
    rel       = CharField(unique=True)
    track_id  = TextField()
    image     = TextField()
    duration  = TextField()
    album     = TextField()
    artist    = TextField()
    title     = TextField()
    album_url = TextField(default="")


class Favourite(BaseModel):
    """User-saved favourites. kind: 'album' | 'artist' | 'song'."""
    kind     = CharField()
    url      = CharField(unique=True)
    label    = TextField()
    thumb    = TextField(default="")
    artist   = TextField(default="")
    album    = TextField(default="")
    added_at = FloatField(default=0.0)


class PageCache(BaseModel):
    """
    Optional HTML cache for genre/artist listing pages.
    Keyed by url + a hash of the query params dict.
    expires_at is a Unix timestamp (float). 0 means never expires.
    Cache is skipped entirely when cache_hours setting is 0.
    """
    url         = TextField()
    params_hash = TextField()
    html        = TextField()
    expires_at  = FloatField()

    class Meta:
        indexes = ((("url", "params_hash"), True),)


# --------------------------------------------------------------------------- #
# Main API class
# --------------------------------------------------------------------------- #

class musicMp3:
    def __init__(self, cache_dir, timeout=15, cache_hours=6):
        if not os.path.exists(cache_dir):
            cache_dir = os.getcwd()

        self.timeout     = timeout
        self.cache_hours = cache_hours

        tracks_db_path   = os.path.join(cache_dir, "tracks.db")
        self._cookie_path = os.path.join(cache_dir, "lwp_cookies.dat")

        db.init(tracks_db_path)
        db.connect(reuse_if_open=True)
        db.create_tables([Track, Favourite, PageCache], safe=True)

        self.base_url   = "https://musicmp3.ru/"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0"
        )

        self.s = requests.Session()
        self.s.cookies = LWPCookieJar(filename=self._cookie_path)
        self.s.headers.update({"User-Agent": self.user_agent})

        if os.path.isfile(self._cookie_path):
            try:
                self.s.cookies.load(ignore_discard=True, ignore_expires=True)
            except Exception as exc:
                log.warning("Could not load cookie file: %s", exc)

    def __del__(self):
        try:
            db.close()
        except Exception:
            pass
        self._save_cookies()
        try:
            self.s.close()
        except Exception:
            pass

    # ----------------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------------- #

    def _save_cookies(self):
        """Persist cookies to disk. Safe to call at any time."""
        try:
            self.s.cookies.save(ignore_discard=True, ignore_expires=True)
        except Exception:
            pass

    def _save_tracks(self, tracks):
        """
        Insert/replace a list of track dicts into the Track table in chunks.

        SQLite has a limit on bound variables per statement (999 on older
        builds). Track has 8 fields, so a single replace_many() call blows
        up at ~124 rows on those builds. Large box sets (50–100+ tracks)
        routinely hit this. We chunk at 100 rows to stay well clear of the
        limit on all SQLite versions.
        """
        if not tracks:
            return
        chunk_size = 100
        with db.atomic():
            for i in range(0, len(tracks), chunk_size):
                Track.replace_many(tracks[i:i + chunk_size]).execute()

    def _quote(self, s):
        return url_quote(s, safe="")

    def image_url(self, url):
        """Append Kodi HTTP header injection for album art requests."""
        if not url:
            return ""
        return "{0}|User-Agent={1}&Referer={2}".format(
            url, self._quote(self.user_agent), self._quote(self.base_url)
        )

    def _params_hash(self, params):
        serialised = json.dumps(params, sort_keys=True)
        return hashlib.md5(serialised.encode()).hexdigest()

    def _has_valid_session(self):
        """
        Return True if the cookie jar contains a non-empty SessionId.
        A missing, blank, or obviously-placeholder value returns False.

        NOTE: This is a cookie-jar check only. A cookie can exist but be
        rejected by the server (stale session), which this cannot detect.
        For that reason this method is NOT used in the hot path — all
        listing fetches call _ensure_session() unconditionally instead.
        This method is retained as a diagnostic/utility helper.
        """
        cookies = requests.utils.dict_from_cookiejar(self.s.cookies)
        sid = cookies.get("SessionId", "")
        return bool(sid and len(sid) > 4)

    def _ensure_session(self, referer_url=None):
        """
        Guarantee a fresh SessionId cookie by hitting the site.
        Called before any authenticated request.
        """
        target = referer_url if referer_url else self.base_url
        try:
            self.s.get(
                target,
                headers={"Referer": self.base_url},
                timeout=self.timeout,
            )
            self._save_cookies()
        except Exception as exc:
            log.warning("Session refresh failed: %s", exc)

    def _page_has_content(self, soup):
        """
        Return True if the parsed page looks like a valid content page.

        Each check targets a CSS class or link pattern that only appears on
        real content pages — never on login walls, captcha pages, or redirects.

        Deliberately does NOT use soup.find("a") as a fallback: login walls
        always contain anchor tags (nav links, "login here", etc.) so that
        check would pass for any bad page and defeat poison detection entirely.

        Valid signals by page type:
          album_report        — genre/artist album grids, search album results
          artist_preview      — search artist results
          tr.song             — song rows (search songs, album tracks)
          a[href^=/artist_]   — main_artists listing pages
                                (URLs are /artist_name.html, NOT /artist/name)
          a[href*=__album_]   — album links on artist pages
                                (URLs are /artist_name__album_title.html)
        """
        if soup.find(class_="album_report"):
            return True
        if soup.find(class_="artist_preview"):
            return True
        if soup.find("tr", class_="song"):
            return True
        # Artist listing pages: hrefs start with /artist_ (e.g. /artist_the-beatles.html)
        if soup.find("a", href=lambda h: h and h.startswith("/artist_")):
            return True
        # Album links on artist pages: /artist_name__album_title.html
        if soup.find("a", href=lambda h: h and "__album_" in h):
            return True
        return False

    def _fetch_live(self, url, params, headers):
        """
        Execute a single live HTTP GET with basic retry on transient errors.
        Returns (response, soup) or raises on persistent failure.
        """
        last_exc = None
        for attempt in range(3):
            try:
                r = self.s.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
                r.raise_for_status()
                return r, BeautifulSoup(r.text, "html.parser")
            except requests.exceptions.HTTPError as exc:
                # 4xx errors won't be fixed by retrying
                if exc.response is not None and exc.response.status_code < 500:
                    raise
                last_exc = exc
            except requests.exceptions.RequestException as exc:
                last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
        raise last_exc

    def _cached_get(self, url, params=None, referer=None):
        """
        Fetch a URL, returning BeautifulSoup.

        v2026.3 improvements vs v2026.2:
        - Validates cached HTML before returning (detects stale/poisoned cache)
        - Validates live-fetched HTML before caching (never caches bad pages)
        - Ensures a valid session exists before fetching
        - Retries with a fresh session if the live fetch returns empty content
        """
        params  = params or {}
        headers = {"Referer": referer or self.base_url}
        p_hash  = self._params_hash(params)

        # ---- Check cache ----
        if self.cache_hours > 0:
            try:
                entry = PageCache.get(
                    (PageCache.url == url) & (PageCache.params_hash == p_hash)
                )
                if entry.expires_at == 0 or entry.expires_at > time.time():
                    soup = BeautifulSoup(entry.html, "html.parser")
                    if self._page_has_content(soup):
                        return soup
                    # Cached page is empty / poisoned — delete and re-fetch
                    log.warning(
                        "Cached page for %s appears empty/poisoned — discarding", url
                    )
                entry.delete_instance()
            except PageCache.DoesNotExist:
                pass

        # ---- Always refresh session before hitting listing pages ----
        # We do this unconditionally rather than only when the cookie looks
        # absent. A cookie can exist but be stale/rejected by the server —
        # _has_valid_session() can't detect that. The warmup GET is a single
        # cheap request that guarantees a fresh SessionId every time.
        self._ensure_session()

        # ---- Live fetch ----
        try:
            r, soup = self._fetch_live(url, params, headers)
        except Exception as exc:
            log.error("Live fetch failed for %s: %s", url, exc)
            return BeautifulSoup("", "html.parser")

        # ---- If page looks empty, refresh session and retry once ----
        if not self._page_has_content(soup):
            log.warning(
                "Empty response from %s — refreshing session and retrying", url
            )
            self._ensure_session()
            try:
                r, soup = self._fetch_live(url, params, headers)
            except Exception as exc:
                log.error("Retry fetch failed for %s: %s", url, exc)
                return BeautifulSoup("", "html.parser")

        # ---- Cache only if the page actually has content ----
        if self.cache_hours > 0 and self._page_has_content(soup):
            expires = time.time() + self.cache_hours * 3600
            try:
                PageCache.replace(
                    url=url, params_hash=p_hash, html=r.text, expires_at=expires
                ).execute()
            except Exception as exc:
                log.warning("Failed to write page cache: %s", exc)
        elif self.cache_hours > 0:
            log.warning(
                "Not caching %s — page has no recognisable content", url
            )

        # Save cookies after every successful listing fetch
        self._save_cookies()

        return soup

    def _find_album_sibling(self, album_el, css_class):
        """
        Locate an element with css_class that is associated with album_el,
        regardless of how many wrapper divs separate them.

        The site's HTML nesting depth is not consistent: sometimes
        album_report__artist is a direct sibling of the album_report div
        inside a <li>; other times album_report is itself wrapped in one or
        more intermediate divs, pushing the artist element further up the
        ancestor tree.

        Strategy (handles all observed structures):
          1. Try album_el.find() — catches the case where the target element
             is a descendant of album_report itself.
          2. Walk up the ancestor chain (up to 4 levels, stopping at body/html),
             checking each ancestor's *direct children* for the class. This
             catches sibling-at-parent, sibling-at-grandparent, etc., without
             accidentally bleeding into an unrelated album block at a higher level.
        """
        # Case 1: element is inside the album_report div
        el = album_el.find(class_=css_class)
        if el:
            return el
        # Case 2: element is a sibling at some ancestor level
        node = album_el.parent
        stop_tags = {None, "[document]", "body", "html"}
        for _ in range(4):
            if node is None or node.name in stop_tags:
                break
            for child in node.children:
                if hasattr(child, "get") and css_class in (child.get("class") or []):
                    return child
            node = node.parent
        return None

    def _parse_album_report(self, album_el):
        """
        Parse a single album_report element into a dict.
        Returns None if any *required* field is missing.

        HTML structure on musicmp3.ru (simplified):
          <li class="unstyled">          ← or possibly deeper nesting
            [optional wrapper divs]
            <div class="album_report">   ← album_el (our entry point)
              <img class="album_report__image">
              <a   class="album_report__link">
                <span class="album_report__name">Title</span>
              </a>
            </div>
            <a    class="album_report__artist">Artist</a>
            <span class="album_report__date">2023</span>
            <div  class="album_report__details_content">…</div>
          </li>

        The depth at which album_report__artist / date / details appear
        relative to album_report is not fixed — see _find_album_sibling()
        for how we handle this robustly.

        On ARTIST pages: album_report__artist and album_report__date are
        absent because the artist is the page owner. artist_albums()
        overrides artist with the page H1 anyway, so empty artist is fine.

        Required:  name, image, link  (without these we can't display or navigate)
        Optional:  artist, date, details  (missing = empty string, not a fatal error)
        """
        try:
            name_el   = album_el.find(class_="album_report__name")
            image_el  = album_el.find(class_="album_report__image")
            link_el   = album_el.find(class_="album_report__link")

            # Required fields — abort if any are missing
            if not all([name_el, image_el, link_el]):
                missing = [n for n, el in [
                    ("name", name_el), ("image", image_el), ("link", link_el),
                ] if not el]
                log.warning("album_report missing required fields %s — skipping", missing)
                return None

            # Optional fields — use ancestor-aware search so nesting depth doesn't matter
            artist_el  = self._find_album_sibling(album_el, "album_report__artist")
            date_el    = self._find_album_sibling(album_el, "album_report__date")
            details_el = self._find_album_sibling(album_el, "album_report__details_content")

            if not artist_el:
                log.debug("album_report__artist not found (expected on artist pages)")
            if not date_el:
                log.debug("album_report__date not found (expected on artist pages)")

            entry = {
                "title":       name_el.get_text(strip=True),
                "image":       self.image_url(image_el.get("src", "")),
                "link":        urljoin(self.base_url, link_el.get("href", "")),
                "artist_link": urljoin(self.base_url, artist_el.get("href", "")) if artist_el else "",
                "artist":      artist_el.get_text(strip=True) if artist_el else "",
                "date":        date_el.get_text(strip=True) if date_el else "",
                "details":     details_el.get_text(strip=True) if details_el else "",
            }
            return entry
        except Exception as exc:
            log.warning("Failed to parse album_report: %s", exc)
            return None

    def boo(self, track_id):
        """
        Compute the CDN authentication token from track_id + session cookie.
        Raises RuntimeError if SessionId cookie is absent.
        """
        cookies = requests.utils.dict_from_cookiejar(self.s.cookies)
        if "SessionId" not in cookies:
            raise RuntimeError(
                "SessionId cookie not found — the site may require login, "
                "or the cookie file is empty/corrupt."
            )

        def int32(x):
            if x > 0xFFFFFFFF:
                raise OverflowError
            if x > 0x7FFFFFFF:
                x = int(0x100000000 - x)
                if x < 2147483648:
                    return -x
                else:
                    return -2147483648
            return x

        _in = track_id[5:] + cookies["SessionId"][8:]
        a, c, b = 1234554321, 7, 305419896
        for f in _in:
            f = ord(f) & 255
            a = int(int32((a ^ ((a & 63) + c) * f + a << 8) & 0xFFFFFFFF))
            b = int(b + (int32(b << 8 & 0xFFFFFFFF) ^ a))
            c = c + f
        a = int(a & 0x7FFFFFFF)
        b = int(b & 0x7FFFFFFF)
        return format(a, '08x') + format(b, '08x')

    def play_url(self, track_id, rel, referer_url=None):
        self._ensure_session(referer_url)
        return (
            "https://listen.musicmp3.ru/{0}/{1}"
            "|seekable=0&verifypeer=false&User-Agent={2}&Referer={3}"
        ).format(
            self.boo(track_id),
            rel,
            self._quote(self.user_agent),
            self._quote(self.base_url),
        )

    # ----------------------------------------------------------------------- #
    # Favourites
    # ----------------------------------------------------------------------- #

    def add_favourite(self, kind, url, label, thumb="", artist="", album=""):
        Favourite.replace(
            kind=kind, url=url, label=label,
            thumb=thumb, artist=artist, album=album,
            added_at=time.time()
        ).execute()

    def remove_favourite(self, url):
        Favourite.delete().where(Favourite.url == url).execute()

    def is_favourite(self, url):
        return Favourite.select().where(Favourite.url == url).exists()

    def get_favourites(self, kind=None):
        q = Favourite.select().order_by(Favourite.added_at.desc())
        if kind:
            q = q.where(Favourite.kind == kind)
        return [
            {
                "kind":   f.kind,
                "url":    f.url,
                "label":  f.label,
                "thumb":  f.thumb,
                "artist": f.artist,
                "album":  f.album,
            }
            for f in q
        ]

    # ----------------------------------------------------------------------- #
    # Public API methods
    # ----------------------------------------------------------------------- #

    def search(self, text, cat, limit=None):
        """
        Search musicmp3.ru. cat: 'artists' | 'albums' | 'songs'.

        limit: max results to return for 'songs' only. The song search page
        returns ALL matching tracks in one response (no server-side pagination),
        which can be thousands of rows. Without a cap, Kodi receives too many
        ListItems to render and shows nothing. Default None = no cap.
        """
        params = {"text": text, "all": cat}

        # Always refresh session before search — stale session returns empty page
        self._ensure_session()

        try:
            r, soup = self._fetch_live(
                "https://musicmp3.ru/search.html",
                params,
                {"Referer": self.base_url},
            )
        except Exception as exc:
            xbmc.log("[m3sr2019] Search request failed: %s" % exc, xbmc.LOGWARNING)
            return []

        # If we got a bad page, refresh session and retry once
        if not self._page_has_content(soup):
            xbmc.log("[m3sr2019] Search returned empty page — refreshing session and retrying", xbmc.LOGWARNING)
            self._ensure_session()
            try:
                r, soup = self._fetch_live(
                    "https://musicmp3.ru/search.html",
                    params,
                    {"Referer": self.base_url},
                )
            except Exception as exc:
                xbmc.log("[m3sr2019] Search retry failed: %s" % exc, xbmc.LOGWARNING)
                return []

        self._save_cookies()
        results = []
        xbmc.log("[m3sr2019] search: cat=%s page_has_content=%s" % (cat, self._page_has_content(soup)), xbmc.LOGDEBUG)

        if cat == "artists":
            for artist in soup.find_all(class_="artist_preview"):
                if artist.a:
                    results.append({
                        "artist": artist.a.get_text(strip=True),
                        "link":   urljoin(self.base_url, artist.a.get("href", "")),
                    })

        elif cat == "albums":
            for album in soup.find_all(class_="album_report"):
                entry = self._parse_album_report(album)
                if entry:
                    results.append(entry)

        elif cat == "songs":
            tracks = []
            song_rows = soup.find_all("tr", class_="song")
            cap = limit if limit else len(song_rows)
            xbmc.log("[m3sr2019] search songs: found %d tr.song rows (capping at %d)" % (len(song_rows), cap), xbmc.LOGDEBUG)
            for song in song_rows[:cap]:
                try:
                    # Primary: use itemprop microdata (same structure as album track pages).
                    # Fallback: use CSS presentation classes (may change with site redesigns).
                    track_id = song.get("id", "")

                    # rel attribute on the play anchor — required for playback.
                    # Extract early so we can derive track_id from it if the
                    # <tr> has no id attribute (search results page dropped it).
                    play_a = song.find("a", rel=True) or song.find("a")
                    rel    = play_a.get("rel", [""])[0] if play_a and play_a.get("rel") else ""

                    # Reconstruct track_id when absent: rel == track_id[5:]
                    # (site uses "song_XXXX" as the tr id; rel carries "XXXX")
                    if not track_id and rel:
                        track_id = "song_" + rel

                    name_el   = song.find(itemprop="name")
                    artist_el = song.find(itemprop="byArtist")
                    album_el  = song.find(itemprop="inAlbum")
                    dur_el    = song.find(itemprop="duration")

                    if name_el:
                        title = name_el.get_text(strip=True)
                    else:
                        name_td = song.find("td", class_="song__name--search")
                        name_a  = name_td.find("a") if name_td else None
                        title   = name_a.get_text(strip=True) if name_a else (name_td.get_text(strip=True) if name_td else "")

                    if artist_el:
                        artist = artist_el.get("content", "") or artist_el.get_text(strip=True)
                    else:
                        artist_td = song.find("td", class_="song__artist--search")
                        a_el      = artist_td.find(["a", "span"]) if artist_td else None
                        artist    = a_el.get_text(strip=True) if a_el else ""

                    if album_el:
                        album = album_el.get("content", "") or album_el.get_text(strip=True)
                    else:
                        album_td = song.find("td", class_="song__album--search")
                        album_a  = album_td.find("a") if album_td else None
                        album    = album_a.get_text(strip=True) if album_a else (album_td.get_text(strip=True) if album_td else "")

                    if not rel or not track_id or not title:
                        xbmc.log(
                            "[m3sr2019] skip row id=%r rel=%r title=%r play_a=%r" % (
                                track_id, rel, title,
                                str(play_a)[:120] if play_a else None
                            ),
                            xbmc.LOGDEBUG
                        )
                        continue

                    if dur_el:
                        try:
                            duration = str(isodate.parse_duration(
                                dur_el.get("content", "PT0S")
                            ).total_seconds())
                        except Exception:
                            duration = ""
                    else:
                        duration = ""

                    try:
                        cached    = Track.get(Track.rel == rel)
                        duration  = cached.duration or duration
                        image     = cached.image
                        album_url = cached.album_url
                    except Track.DoesNotExist:
                        image     = ""
                        album_url = ""

                    tracks.append({
                        "title":     title,
                        "artist":    artist,
                        "album":     album,
                        "duration":  duration,
                        "image":     image,
                        "track_id":  track_id,
                        "rel":       rel,
                        "album_url": album_url,
                    })
                except Exception as exc:
                    log.warning("Skipping song search result: %s", exc)

            if tracks:
                self._save_tracks(tracks)
            else:
                xbmc.log("[m3sr2019] search songs: 0 tracks built from %d rows" % len(song_rows), xbmc.LOGWARNING)
            results = tracks

        return results

    def main_artists(self, gnr_id, start, count):
        """Fetch a paginated list of artists for a genre."""
        _page = 1 + start // 80
        results = []

        while len(results) < count:
            params = {"type": "artist", "page": _page}
            if gnr_id != "0":
                params["gnr_id"] = gnr_id

            soup = self._cached_get(
                "https://musicmp3.ru/main_artists.html", params=params
            )
            if not self._page_has_content(soup):
                log.warning("main_artists: _page_has_content failed for page %d gnr_id=%s", _page, gnr_id)
                break

            # Artist pages use the URL pattern /artist_name.html (note underscore,
            # NOT /artist/name). The small_list__link class wraps each artist anchor.
            artist_links = soup.find_all(
                "a", href=lambda h: h and h.startswith("/artist_")
            )
            log.debug("main_artists: page %d found %d artist links", _page, len(artist_links))

            if not artist_links:
                log.warning("main_artists: no /artist_ links on page %d gnr_id=%s — stopping", _page, gnr_id)
                break

            page_offset = (_page - 1) * 80
            for index, a in enumerate(artist_links, page_offset):
                if len(results) >= count:
                    break
                if index >= start:
                    results.append({
                        "artist": a.get_text(strip=True),
                        "link":   urljoin(self.base_url, a.get("href", "")),
                    })
            _page += 1

        log.debug("main_artists: returning %d results for gnr_id=%s start=%d", len(results), gnr_id, start)
        return results

    def main_albums(self, section, gnr_id, sort, start, count):
        """Fetch a paginated list of albums for a genre."""
        _page = 1 + start // 40
        results = []

        while len(results) < count:
            params = {"sort": sort, "type": "album", "page": _page}
            if gnr_id != "0":
                params["gnr_id"] = gnr_id
            if section:
                params["section"] = section

            soup = self._cached_get("https://musicmp3.ru/main_albums.html", params=params)
            if not self._page_has_content(soup):
                break

            page_offset = (_page - 1) * 40
            for index, album_el in enumerate(soup.find_all(class_="album_report"), page_offset):
                if len(results) >= count:
                    break
                if index >= start:
                    entry = self._parse_album_report(album_el)
                    if entry:
                        results.append(entry)
            _page += 1

        return results

    def artist_albums(self, url):
        """Fetch all albums for an artist page URL."""
        soup = self._cached_get(url)
        h1 = soup.find(class_="page_title__h1")
        _artist = h1.get_text(strip=True) if h1 else ""
        log.debug("artist_albums: url=%s artist=%r page_has_content=%s", url, _artist, self._page_has_content(soup))
        results = []
        album_els = soup.find_all(class_="album_report")
        log.debug("artist_albums: found %d album_report elements", len(album_els))
        for album_el in album_els:
            entry = self._parse_album_report(album_el)
            if entry:
                entry["artist"]      = _artist
                entry["artist_link"] = url
                results.append(entry)
        log.debug("artist_albums: returning %d albums", len(results))
        return results

    def album_tracks(self, url):
        """
        Fetch and parse the track listing for an album page.
        Always fetches live — we need fresh session state for play tokens.
        Returns (tracks, album_info).
        """
        # Always refresh session before fetching album page
        self._ensure_session()

        try:
            r, soup = self._fetch_live(
                url, {}, {"Referer": self.base_url}
            )
        except Exception as exc:
            log.error("album_tracks fetch failed for %s: %s", url, exc)
            return [], {}

        self._save_cookies()

        # --- Album-level metadata ---
        image_tag = soup.find(class_="art_wrap__img")
        image = self.image_url(image_tag.get("src")) if image_tag and image_tag.get("src") else ""

        album_info = {
            "title":       "",
            "artist":      "",
            "image":       image,
            "year":        "",
            "genre":       "",
            "description": "",
        }

        title_el = soup.find(itemprop="name", class_=lambda c: c and "album" in c.lower()) \
                   or soup.find(class_="album_info__title") \
                   or soup.find(itemprop="name")
        if title_el:
            album_info["title"] = title_el.get_text(strip=True)

        artist_el = soup.find(itemprop="byArtist") or soup.find(class_="album_info__artist")
        if artist_el:
            album_info["artist"] = artist_el.get_text(strip=True)

        date_el = soup.find(itemprop="datePublished") or soup.find(class_="album_info__date")
        if date_el:
            album_info["year"] = (date_el.get("content") or date_el.get_text(strip=True))[:4]

        genre_els = soup.find_all(class_="album_info__genre") or \
                    soup.find_all(itemprop="genre")
        if genre_els:
            album_info["genre"] = ", ".join(
                g.get_text(strip=True) for g in genre_els if g.get_text(strip=True)
            )

        desc_el = soup.find(class_="album_info__description") or \
                  soup.find(class_="album_description") or \
                  soup.find(itemprop="description")
        if desc_el:
            album_info["description"] = desc_el.get_text(separator=" ", strip=True)

        # --- Track list ---
        tracks = []
        for song in soup.find_all(class_="song"):
            try:
                track = {
                    "title":    song.find(itemprop="name").get_text(strip=True),
                    "artist":   song.find(itemprop="byArtist").get("content", ""),
                    "album":    song.find(itemprop="inAlbum").get("content", ""),
                    "duration": str(
                        isodate.parse_duration(
                            song.find(itemprop="duration").get("content", "PT0S")
                        ).total_seconds()
                    ),
                    "image":     image,
                    "track_id":  song.get("id", ""),
                    "rel":       song.a.get("rel", [""])[0],
                    "album_url": url,
                }
                tracks.append(track)
            except Exception as exc:
                log.warning("Skipping track in album_tracks: %s", exc)

        if tracks:
            self._save_tracks(tracks)

        return tracks, album_info

    def get_track(self, rel):
        try:
            return Track.get(Track.rel == rel)
        except Track.DoesNotExist:
            return Track()

    def clear_cache(self):
        """Delete all cached page entries. Safe to call at any time."""
        PageCache.delete().execute()


# --------------------------------------------------------------------------- #
# Genre ID table
# --------------------------------------------------------------------------- #

gnr_ids = [
    (
        "World",
        [
            ("World", "0"),
            ("Celtic", "3"),
            ("Jewish", "14"),
            ("Polynesian", "20"),
            ("African", "23"),
            ("Arabic", "79"),
            ("Brazilian", "93"),
            ("Caribbean", "135"),
            ("Turkish", "164"),
            ("Chinese", "169"),
            ("Japanese", "179"),
            ("Korean", "194"),
            ("South Asian", "200"),
            ("Spanish Folk", "212"),
            ("South American Folk", "220"),
            ("Slavic Folk", "229"),
            ("Nordic Folk", "241"),
            ("Italian Folk", "249"),
            ("French Folk", "252"),
            ("Balkan Folk", "259"),
            ("Latin", "268"),
            ("Compilations", "2"),
        ],
    ),
    (
        "Classical",
        [
            ("Classical", "313"),
            ("Baroque Period", "314"),
            ("Chamber", "315"),
            ("Choral", "316"),
            ("Classical Period", "317"),
            ("Medieval", "318"),
            ("Modern Classical", "326"),
            ("Opera", "343"),
            ("Orchestral", "348"),
            ("Renaissance", "352"),
            ("Romantic Period", "353"),
            ("Classical Crossover", "354"),
            ("Compilations", "313"),
        ],
    ),
    (
        "Metal",
        [
            ("Metal", "355"),
            ("Alternative Metal", "356"),
            ("Black Metal", "360"),
            ("Death Metal", "365"),
            ("Doom Metal", "373"),
            ("Folk Metal", "378"),
            ("Gothic Metal", "382"),
            ("Grindcore", "383"),
            ("Groove Metal", "386"),
            ("Heavy Metal", "387"),
            ("Industrial Metal", "389"),
            ("Metalcore", "391"),
            ("Neo-Classical Metal", "395"),
            ("Power Metal", "396"),
            ("Progressive Metal", "397"),
            ("Symphonic Metal", "398"),
            ("Thrash & Speed Metal", "399"),
            ("Sludge Metal", "404"),
            ("Glam Metal", "407"),
            ("Compilations", "355"),
        ],
    ),
    (
        "Alternative",
        [
            ("Alternative", "408"),
            ("Britpop", "409"),
            ("Dream Pop", "410"),
            ("Grunge", "412"),
            ("Indie Rock", "414"),
            ("Industrial Rock", "419"),
            ("Rap Rock", "420"),
            ("Garage Rock", "421"),
            ("Latin Alternative", "286"),
            ("Post-Punk", "424"),
            ("Emo", "431"),
            ("Punk Rock", "436"),
            ("Compilations", "408"),
        ],
    ),
    (
        "Rock",
        [
            ("Rock", "473"),
            ("Art Rock", "474"),
            ("Christian Rock", "481"),
            ("Comedy Rock", "482"),
            ("Folk Rock", "483"),
            ("Glam Rock", "489"),
            ("Hard Rock", "491"),
            ("Latin Rock", "292"),
            ("Progressive Rock", "494"),
            ("Psychedelic Rock", "500"),
            ("Rock & Roll", "507"),
            ("Southern Rock", "515"),
            ("Rockabilly", "516"),
            ("Compilations", "473"),
        ],
    ),
    (
        "R&B",
        [
            ("R&B", "517"),
            ("Contemporary R&B", "518"),
            ("Funk", "520"),
            ("Soul", "525"),
            ("Early R&B", "534"),
            ("Pop Soul", "537"),
            ("Neo-Soul", "538"),
            ("Compilations", "517"),
        ],
    ),
    (
        "Dance",
        [
            ("Dance", "539"),
            ("Teen Pop", "540"),
            ("Hi-NRG", "542"),
            ("Dance Pop", "543"),
            ("Electropop", "547"),
            ("Alternative Dance", "549"),
            ("Disco", "551"),
            ("Eurodance", "557"),
            ("Compilations", "539"),
        ],
    ),
    (
        "Pop",
        [
            ("Pop", "558"),
            ("Adult Contemporary", "559"),
            ("CCM", "560"),
            ("Euro Pop", "562"),
            ("French Pop", "564"),
            ("Indie Pop", "567"),
            ("Latin Pop", "291"),
            ("Pop Rock", "571"),
            ("Traditional Pop", "579"),
            ("New Wave", "582"),
            ("Easy Listening", "589"),
            ("Blue Eyed Soul", "595"),
            ("Compilations", "558"),
        ],
    ),
    (
        "Jazz",
        [
            ("Jazz", "596"),
            ("Acid Jazz", "597"),
            ("Free Jazz", "599"),
            ("Bebop", "600"),
            ("Big Band", "603"),
            ("Cool Jazz", "606"),
            ("Jazz Fusion", "607"),
            ("Soul Jazz", "610"),
            ("Swing", "611"),
            ("Vocal Jazz", "613"),
            ("Early Jazz", "614"),
            ("World Jazz", "622"),
            ("Compilations", "596"),
        ],
    ),
    (
        "Hip Hop",
        [
            ("Hip Hop", "623"),
            ("Alternative Hip Hop", "624"),
            ("Comedy Rap", "629"),
            ("East Coast Hip Hop", "630"),
            ("French Hip Hop", "631"),
            ("Hardcore Hip Hop", "632"),
            ("Instrumental Hip Hop", "637"),
            ("Political Hip Hop", "638"),
            ("Pop Rap", "639"),
            ("Religious Hip Hop", "640"),
            ("Southern Hip Hop", "644"),
            ("UK Hip Hop", "652"),
            ("West Coast Hip Hop", "653"),
            ("Compilations", "623"),
        ],
    ),
    (
        "Electronic",
        [
            ("Electronic", "654"),
            ("Breakbeat", "655"),
            ("Downtempo", "661"),
            ("Drum and Bass", "664"),
            ("EBM", "678"),
            ("Electro", "681"),
            ("Hardcore Techno", "686"),
            ("House", "698"),
            ("IDM", "717"),
            ("Indie Electronic", "718"),
            ("Techno", "720"),
            ("Trance", "728"),
            ("UK Garage", "737"),
            ("Ambient", "744"),
            ("Dubstep", "749"),
            ("Compilations", "654"),
        ],
    ),
    (
        "Country",
        [
            ("Country", "750"),
            ("Alternative Country", "751"),
            ("Contemporary Country", "755"),
            ("Country Pop", "756"),
            ("Traditional Country", "759"),
            ("Country Rock", "770"),
            ("Compilations", "750"),
        ],
    ),
    (
        "Blues",
        [
            ("Blues", "774"),
            ("Acoustic Blues", "775"),
            ("Electric Blues", "780"),
            ("Piano Blues", "784"),
            ("Blues Rock", "786"),
            ("Compilations", "774"),
        ],
    ),
    (
        "Soundtracks",
        [
            ("Soundtracks", "0"),
            ("Movie Soundtracks", "789"),
            ("TV Soundtracks", "792"),
            ("Game Soundtracks", "794"),
            ("Show Tunes", "796"),
            ("Spoken Word", "797"),
        ],
    ),
]
