# -*- coding: utf-8 -*-
#
# MP3 Streams Echoed — plugin.audio.m3sr2019
# Copyright (C) 2019 L2501
# Modernised and extended by Echostorm / Claude (2026)
#
# Logging note: xbmc.log() only — Python's standard logging module
# produces zero output in Kodi addon context.

import os
import random
import sys
from urllib.parse import quote, unquote

from routing import Plugin
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

from resources.lib.musicmp3 import musicMp3, gnr_ids

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

# --------------------------------------------------------------------------- #
# Add-on setup
# --------------------------------------------------------------------------- #

addon  = xbmcaddon.Addon()
plugin = Plugin()
plugin.name = addon.getAddonInfo("name")

USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))
MEDIA_DIR     = os.path.join(translatePath(addon.getAddonInfo("path")), "resources", "media")
FANART        = os.path.join(MEDIA_DIR, "fanart.jpg")
MUSICMP3_DIR  = os.path.join(USER_DATA_DIR, "musicmp3")

if not os.path.exists(MUSICMP3_DIR):
    os.makedirs(MUSICMP3_DIR)

fixed_view_mode  = addon.getSetting("fixed_view_mode") == "true"
albums_view_mode = addon.getSetting("albums_view_mode")
songs_view_mode  = addon.getSetting("songs_view_mode")


def _make_musicmp3():
    try:
        timeout = int(addon.getSetting("request_timeout"))
    except (ValueError, TypeError):
        timeout = 15
    try:
        cache_hours = int(addon.getSetting("cache_hours"))
    except (ValueError, TypeError):
        cache_hours = 6
    return musicMp3(MUSICMP3_DIR, timeout=timeout, cache_hours=cache_hours)


def _page_size():
    try:
        return int(addon.getSetting("page_size"))
    except (ValueError, TypeError):
        return 40


def _genre_icon(genre_name):
    filename = genre_name.lower().replace(" ", "").replace("&", "_") + ".jpg"
    return os.path.join(MEDIA_DIR, "genre", filename)


def _sub_genre_icon(parent_name, sub_name):
    filename = sub_name.lower().replace(" ", "").replace("&", "_") + ".jpg"
    return os.path.join(MEDIA_DIR, "genre", parent_name.lower(), filename)


def _set_view(content_type, view_mode):
    xbmcplugin.setContent(plugin.handle, content_type)
    if fixed_view_mode:
        xbmc.executebuiltin("Container.SetViewMode({0})".format(view_mode))



def _link_url(route_func, link):
    return plugin.url_for(route_func) + "?link=" + quote(link, safe="")


def _get_link():
    return unquote(plugin.args.get("link", [""])[0])


def _set_music_tag(li, title="", artist="", album="", year="", genre="",
                   duration=0, tracknumber=0, description=""):
    """Populate a ListItem MusicInfoTag using the Kodi 19+ API.

    setAlbumArtist() is called alongside setArtist() whenever an artist is
    present. When content type is 'albums', Kodi and most skins (including
    Aeon Nox Silvo) display albumartist — not artist — as the subtitle on
    album ListItems. setArtist() alone populates the track-level field, which
    skins only read in song/track context. Both fields must be set so the
    artist name appears correctly in both album listings and track listings.
    """
    tag = li.getMusicInfoTag()
    if title:  tag.setTitle(title)
    if artist:
        tag.setArtist(artist)
        tag.setAlbumArtist(artist)
    if album:       tag.setAlbum(album)
    if year:
        try:        tag.setYear(int(str(year)[:4]))
        except (ValueError, TypeError): pass
    if genre:
        tag.setGenres([g.strip() for g in genre.split(",")] if "," in genre else [genre])
    if duration:
        try:        tag.setDuration(int(float(duration)))
        except (ValueError, TypeError): pass
    if tracknumber: tag.setTrack(tracknumber)
    if description: tag.setComment(description)


def _kind_label(kind):
    """Map kind key to a human-readable list name shown in context menus."""
    return {"song": "My Songs", "album": "My Albums", "artist": "My Artists"}.get(kind, "My List")


def _fav_add_action(kind, url, label, thumb="", artist="", album=""):
    """Build the RunPlugin URL string for the Save to <list> action."""
    action = (
        plugin.url_for(fav_add)
        + "?kind="  + quote(kind,   safe="")
        + "&url="   + quote(url,    safe="")
        + "&label=" + quote(label,  safe="")
        + "&thumb=" + quote(thumb,  safe="")
        + "&artist="+ quote(artist, safe="")
        + "&album=" + quote(album,  safe="")
    )
    return "RunPlugin({0})".format(action)


def _fav_remove_action(url):
    """Build the RunPlugin URL string for the Remove from <list> action."""
    action = plugin.url_for(fav_remove) + "?url=" + quote(url, safe="")
    return "RunPlugin({0})".format(action)


def _fav_context(api, kind, url, label, thumb="", artist="", album=""):
    """
    Return context menu entry for albums and artists (Save OR Remove, not both).
    Shows whichever action is relevant based on current saved state.
    Label is kind-specific: My Albums, My Artists.
    """
    kl = _kind_label(kind)
    if api.is_favourite(url):
        return [("✕  Remove from {0}".format(kl), _fav_remove_action(url))]
    return [("★  Save to {0}".format(kl), _fav_add_action(kind, url, label, thumb, artist, album))]


def _song_fav_context(api, kind, url, label, thumb="", artist="", album=""):
    """
    Return BOTH Save and Remove context menu entries for song items.
    Both are always visible so you can save or remove without re-opening the menu.
    Label is kind-specific: My Songs.
    """
    kl = _kind_label(kind)
    return [
        ("★  Save to {0}".format(kl),      _fav_add_action(kind, url, label, thumb, artist, album)),
        ("✕  Remove from {0}".format(kl),  _fav_remove_action(url)),
    ]


def _album_context(album_url, label):
    """
    Return Play Album + Shuffle Album context menu entries for an album item.
    These build and start a Kodi playlist immediately without opening the album.
    """
    base = plugin.url_for(play_album) + "?album_url=" + quote(album_url, safe="")
    return [
        ("▶  Play Album",    "RunPlugin({0})".format(base)),
        ("🔀  Shuffle Album", "RunPlugin({0}&shuffle=1)".format(base)),
    ]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _notify_error(msg):
    """Show a visible error toast in Kodi and log it."""
    xbmc.log("[m3sr2019] error: %s" % msg, xbmc.LOGWARNING)
    xbmcgui.Dialog().notification(
        plugin.name, msg, xbmcgui.NOTIFICATION_ERROR, 5000
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@plugin.route("/")
def index():
    items = [
        ("Artists",           plugin.url_for(musicmp3_artist_main),          os.path.join(MEDIA_DIR, "artists.jpg")),
        ("Top Albums",        plugin.url_for(musicmp3_albums_main, "top"),    os.path.join(MEDIA_DIR, "topalbums.jpg")),
        ("New Albums",        plugin.url_for(musicmp3_albums_main, "new"),    os.path.join(MEDIA_DIR, "newalbums.jpg")),
        ("Favourite Albums",  plugin.url_for(favourites, "album"),            os.path.join(MEDIA_DIR, "favouritealbums.jpg")),
        ("Favourite Artists", plugin.url_for(favourites, "artist"),           os.path.join(MEDIA_DIR, "favouriteartists.jpg")),
        ("Favourite Songs",        plugin.url_for(favourites, "song"),              os.path.join(MEDIA_DIR, "favouritesongs.jpg")),
        ("Shuffle Favourite Songs", plugin.url_for(shuffle_favourites),              os.path.join(MEDIA_DIR, "mixfavouritesongs.jpg")),
        ("Search Artists",         plugin.url_for(musicmp3_search, "artists"),      os.path.join(MEDIA_DIR, "searchartists.jpg")),
        ("Search Albums",     plugin.url_for(musicmp3_search, "albums"),      os.path.join(MEDIA_DIR, "searchalbums.jpg")),
        ("Search Songs",      plugin.url_for(musicmp3_search, "songs"),       os.path.join(MEDIA_DIR, "searchsongs.jpg")),
        ("Clear Page Cache",  plugin.url_for(musicmp3_clear_cache),           os.path.join(MEDIA_DIR, "clearplaylist.jpg")),
    ]
    for label, url, icon in items:
        li = xbmcgui.ListItem(label)
        li.setArt({"fanart": FANART, "icon": icon})
        xbmcplugin.addDirectoryItem(plugin.handle, url, li, True)
    xbmcplugin.endOfDirectory(plugin.handle)


# --------------------------------------------------------------------------- #
# Favourites
# --------------------------------------------------------------------------- #

@plugin.route("/favourites/<kind>")
def favourites(kind):
    """Browse saved favourites. kind: album | artist | song."""
    api   = _make_musicmp3()
    items = api.get_favourites(kind=kind)

    if not items:
        xbmcgui.Dialog().notification(
            plugin.name, "No favourites saved yet.", xbmcgui.NOTIFICATION_INFO, 3000
        )
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=True)
        return

    directory_items = []
    for f in items:
        _fav_label = (
            "{0} — {1}".format(f["artist"], f["label"])
            if kind == "album" and f.get("artist") else f["label"]
        )
        li = xbmcgui.ListItem(_fav_label)
        # setLabel2 carries the artist name into skins that show it as a subtitle.
        # kind=="artist" is intentionally excluded: the artist IS the primary label.
        if kind in ("album", "song"):
            li.setLabel2(f["artist"])
        li.setArt({"thumb": f["thumb"], "icon": f["thumb"], "fanart": FANART})
        _set_music_tag(li, title=f["label"], artist=f["artist"], album=f["album"])
        remove_url = plugin.url_for(fav_remove) + "?url=" + quote(f["url"], safe="")
        li.addContextMenuItems([
            ("✕  Remove from {0}".format(_kind_label(kind)), "RunPlugin({0})".format(remove_url))
        ])

        if kind == "album":
            directory_items.append((_link_url(musicmp3_album, f["url"]), li, True))
        elif kind == "artist":
            directory_items.append((_link_url(artists_albums, f["url"]), li, True))
        elif kind == "song":
            track = api.get_track(f["url"])   # f["url"] is the rel key for songs
            li.setProperty("IsPlayable", "true")
            play_qs = (
                "?track_id="  + quote(track.track_id  or "", safe="")
                + "&rel="     + quote(f["url"],              safe="")
                + "&album_url="+ quote(track.album_url or "", safe="")
            )
            directory_items.append((plugin.url_for(musicmp3_play) + play_qs, li, False))

    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    _set_view("songs" if kind == "song" else "",
              songs_view_mode if kind == "song" else albums_view_mode)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/fav/add")
def fav_add():
    kind   = unquote(plugin.args.get("kind",   [""])[0])
    url    = unquote(plugin.args.get("url",    [""])[0])
    label  = unquote(plugin.args.get("label",  [""])[0])
    thumb  = unquote(plugin.args.get("thumb",  [""])[0])
    artist = unquote(plugin.args.get("artist", [""])[0])
    album  = unquote(plugin.args.get("album",  [""])[0])
    api = _make_musicmp3()
    api.add_favourite(kind, url, label, thumb=thumb, artist=artist, album=album)
    xbmcgui.Dialog().notification(
        plugin.name, u"\u2605  Saved to {0}: {1}".format(_kind_label(kind), label),
        xbmcgui.NOTIFICATION_INFO, 2500
    )


@plugin.route("/fav/remove")
def fav_remove():
    url = unquote(plugin.args.get("url", [""])[0])
    api = _make_musicmp3()
    api.remove_favourite(url)
    xbmcgui.Dialog().notification(
        plugin.name, "Removed from saved list.", xbmcgui.NOTIFICATION_INFO, 2000
    )
    xbmc.executebuiltin("Container.Refresh")


# --------------------------------------------------------------------------- #
# Shuffle Favourite Songs
# --------------------------------------------------------------------------- #

@plugin.route("/favourites/shuffle_songs")
def shuffle_favourites():
    """
    Home screen action: build a shuffled playlist from all favourite songs
    and start playing immediately.
    """
    api   = _make_musicmp3()
    items = api.get_favourites(kind="song")

    if not items:
        xbmcgui.Dialog().notification(
            plugin.name, "No favourite songs saved yet.", xbmcgui.NOTIFICATION_INFO, 3000
        )
        return

    random.shuffle(items)
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    for f in items:
        track = api.get_track(f["url"])   # f["url"] is the rel key
        if not track.track_id:
            continue
        url = api.play_url(track.track_id, f["url"], referer_url=track.album_url or None)
        li  = xbmcgui.ListItem(f["label"], path=url)
        li.setArt({"thumb": f["thumb"], "icon": f["thumb"], "fanart": f["thumb"]})
        li.setMimeType("audio/mpeg")
        li.setContentLookup(False)
        _set_music_tag(li, title=f["label"], artist=f["artist"], album=f["album"])
        playlist.add(url, li)

    if playlist.size() > 0:
        xbmc.Player().play(playlist)
    else:
        xbmcgui.Dialog().notification(
            plugin.name, "Could not load track data — open albums first.",
            xbmcgui.NOTIFICATION_WARNING, 4000
        )


# --------------------------------------------------------------------------- #
# Visualizer toggle
# --------------------------------------------------------------------------- #

@plugin.route("/viz/toggle")
def viz_toggle():
    """
    Toggle the Kodi visualizer on/off.
    If the visualisation window is currently active, send Back to close it.
    Otherwise open it. Works correctly whether called from a context menu
    while music is playing or from any other trigger.
    """
    if xbmc.getCondVisibility("Window.IsActive(visualisation)"):
        xbmc.executebuiltin("Action(Back)")
    else:
        xbmc.executebuiltin("ActivateWindow(Visualisation)")


# --------------------------------------------------------------------------- #
# Stereo Upmix toggle (Kodi built-in surround upmix)
# --------------------------------------------------------------------------- #

@plugin.route("/virt/toggle")
def virt_toggle():
    """
    Toggle Kodi's stereo upmix (Settings > System > Audio > Surround sound upmix).
    Reads the current state, flips it, shows a notification. Falls back silently
    if the setting is unavailable (e.g. on a device where the option doesn't exist).
    """
    import json
    try:
        raw = xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","id":1,"method":"Settings.GetSettingValue",'
            '"params":{"setting":"audiooutput.stereoupmix"}}'
        )
        current = json.loads(raw).get("result", {}).get("value", None)
        if current is None:
            xbmcgui.Dialog().notification("Stereo Upmix", "Setting not available on this device.", time=3000)
            return
        new_val = not current
        xbmc.executeJSONRPC(
            '{{"jsonrpc":"2.0","id":2,"method":"Settings.SetSettingValue",'
            '"params":{{"setting":"audiooutput.stereoupmix","value":{0}}}}}'.format(
                "true" if new_val else "false"
            )
        )
        label = "Stereo Upmix: ON" if new_val else "Stereo Upmix: OFF"
        xbmcgui.Dialog().notification(label, "", time=2500)
    except Exception as exc:
        xbmcgui.Dialog().notification("Stereo Upmix", "Error: {0}".format(exc), time=3000)


def _virt_label():
    """
    Read the current stereo upmix state once and return a context menu label
    that reflects it. Called once per directory load, not once per item.
    Falls back to a neutral label if the state can't be determined.
    """
    import json
    try:
        raw = xbmc.executeJSONRPC(
            '{"jsonrpc":"2.0","id":1,"method":"Settings.GetSettingValue",'
            '"params":{"setting":"audiooutput.stereoupmix"}}'
        )
        val = json.loads(raw).get("result", {}).get("value", None)
        if val is True:  return u"\U0001f50a  Stereo Upmix: ON  [toggle off]"
        if val is False: return u"\U0001f507  Stereo Upmix: OFF [toggle on]"
    except Exception:
        pass
    return u"\U0001f50a  Toggle Stereo Upmix"


# --------------------------------------------------------------------------- #
# Play Album / Shuffle Album
# --------------------------------------------------------------------------- #

@plugin.route("/musicmp3/play_album")
def play_album():
    """
    Context menu action: fetch all tracks for an album and start playing
    immediately as a Kodi playlist — no need to open the album first.
    Accepts 'shuffle=1' query param to randomise the order.
    """
    album_url = unquote(plugin.args.get("album_url", [""])[0])
    shuffle   = plugin.args.get("shuffle", ["0"])[0] == "1"

    if not album_url:
        return

    api = _make_musicmp3()
    tracks, album_info = api.album_tracks(album_url)

    if not tracks:
        xbmcgui.Dialog().notification(
            plugin.name, "No tracks found.", xbmcgui.NOTIFICATION_WARNING, 3000
        )
        return

    if shuffle:
        tracks = list(tracks)
        random.shuffle(tracks)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    ai_image  = album_info.get("image",  "")
    ai_title  = album_info.get("title",  "")
    ai_artist = album_info.get("artist", "")
    ai_year   = album_info.get("year",   "")
    ai_genre  = album_info.get("genre",  "")

    for i, t in enumerate(tracks, 1):
        track_id = t.get("track_id", "")
        rel      = t.get("rel", "")
        if not track_id or not rel:
            continue

        url = api.play_url(track_id, rel, referer_url=album_url)
        art = t.get("image", "") or ai_image

        li = xbmcgui.ListItem(t.get("title", ""), path=url)
        li.setArt({"thumb": art, "icon": art, "fanart": art})
        li.setMimeType("audio/mpeg")
        li.setContentLookup(False)
        _set_music_tag(li,
            title=t.get("title", ""),
            artist=t.get("artist", "") or ai_artist,
            album=t.get("album", "") or ai_title,
            year=ai_year, genre=ai_genre,
            duration=t.get("duration", 0),
            tracknumber=0 if shuffle else i)
        playlist.add(url, li)

    xbmc.Player().play(playlist)


# --------------------------------------------------------------------------- #
# Utility
# --------------------------------------------------------------------------- #

@plugin.route("/musicmp3/clear_cache")
def musicmp3_clear_cache():
    api = _make_musicmp3()
    api.clear_cache()
    xbmcgui.Dialog().notification(
        plugin.name, "Page cache cleared.", xbmcgui.NOTIFICATION_INFO, 3000
    )
    xbmc.executebuiltin("Container.Refresh")


# --------------------------------------------------------------------------- #
# Genre / artist browse
# --------------------------------------------------------------------------- #

@plugin.route("/musicmp3/albums_main/<sort>")
def musicmp3_albums_main(sort):
    directory_items = []
    for i, gnr in enumerate(gnr_ids):
        li = xbmcgui.ListItem("{0} {1} Albums".format(sort.title(), gnr[0]))
        li.setArt({"fanart": FANART, "icon": _genre_icon(gnr[0])})
        directory_items.append((plugin.url_for(musicmp3_albums_gnr, sort, i), li, True))
    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/musicmp3/albums_gnr/<sort>/<gnr>")
def musicmp3_albums_gnr(sort, gnr):
    gnr_index = int(gnr)
    parent    = gnr_ids[gnr_index]
    directory_items = []
    for sub_gnr in parent[1]:
        section = "compilations" if sub_gnr[0] == "Compilations" else \
                  "soundtracks"  if sub_gnr[0] == "Soundtracks"  else "main"
        li = xbmcgui.ListItem("{0} {1} Albums".format(sort.title(), sub_gnr[0]))
        li.setArt({"fanart": FANART, "icon": _sub_genre_icon(parent[0], sub_gnr[0])})
        directory_items.append(
            (plugin.url_for(musicmp3_main_albums, section, sub_gnr[1], sort, "0"), li, True)
        )
    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/musicmp3/artists_main")
def musicmp3_artist_main():
    directory_items = []
    for i, gnr in enumerate(gnr_ids):
        li = xbmcgui.ListItem("{0} Artists".format(gnr[0]))
        li.setArt({"fanart": FANART, "icon": _genre_icon(gnr[0])})
        directory_items.append((plugin.url_for(musicmp3_artists_gnr, i), li, True))
    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/musicmp3/artists_gnr/<gnr>")
def musicmp3_artists_gnr(gnr):
    gnr_index = int(gnr)
    parent    = gnr_ids[gnr_index]
    directory_items = []
    for sub_gnr in parent[1]:
        if sub_gnr[0] in ("Compilations", "Soundtracks"):
            continue
        li = xbmcgui.ListItem("{0} Artists".format(sub_gnr[0]))
        li.setArt({"fanart": FANART, "icon": _sub_genre_icon(parent[0], sub_gnr[0])})
        directory_items.append(
            (plugin.url_for(musicmp3_main_artists, sub_gnr[1], "0"), li, True)
        )
    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/musicmp3/main_albums/<section>/<gnr_id>/<sort>/<index>/dir")
def musicmp3_main_albums(section, gnr_id, sort, index):
    api   = _make_musicmp3()
    count = _page_size()
    index = int(index)
    _section = "" if section == "main" else section

    try:
        albums = api.main_albums(_section, gnr_id, sort, index, count)
    except Exception as exc:
        _notify_error("Could not load albums: {0}".format(exc))
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return
    directory_items = []

    for a in albums:
        _title  = a.get("title",  "")
        _artist = a.get("artist", "")
        _label  = "{0} — {1}".format(_artist, _title) if _artist else _title
        li = xbmcgui.ListItem(_label)
        li.setLabel2(_artist)
        li.setArt({"thumb": a.get("image", ""), "icon": a.get("image", ""), "fanart": FANART})
        _set_music_tag(li,
            title=_title, artist=_artist,
            album=_title, year=a.get("date", ""))
        li.addContextMenuItems(
            _album_context(a.get("link", ""), _title)
            + _fav_context(api, "album", a.get("link", ""), _title,
                           thumb=a.get("image", ""), artist=_artist)
        )
        directory_items.append((_link_url(musicmp3_album, a.get("link", "")), li, True))

    if len(albums) >= count:
        next_index = str(index + count)
        li = xbmcgui.ListItem("More {0}+".format(next_index))
        li.setArt({"icon": os.path.join(MEDIA_DIR, "nextpage.jpg")})
        directory_items.append(
            (plugin.url_for(musicmp3_main_albums, section, gnr_id, sort, next_index), li, True)
        )

    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    _set_view("", albums_view_mode)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/musicmp3/main_artists/<gnr_id>/<index>/dir")
def musicmp3_main_artists(gnr_id, index):
    api   = _make_musicmp3()
    count = _page_size()
    index = int(index)

    try:
        artists = api.main_artists(gnr_id, index, count)
    except Exception as exc:
        _notify_error("Could not load artists: {0}".format(exc))
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return
    directory_items = []

    for a in artists:
        li = xbmcgui.ListItem(a.get("artist", ""))
        li.setArt({"fanart": FANART})
        _set_music_tag(li, title=a.get("artist", ""), artist=a.get("artist", ""))
        li.addContextMenuItems(_fav_context(
            api, "artist", a.get("link", ""), a.get("artist", "")
        ))
        directory_items.append((_link_url(artists_albums, a.get("link", "")), li, True))

    if len(artists) >= count:
        next_index = str(index + count)
        li = xbmcgui.ListItem("More {0}+".format(next_index))
        li.setArt({"icon": os.path.join(MEDIA_DIR, "nextpage.jpg")})
        directory_items.append(
            (plugin.url_for(musicmp3_main_artists, gnr_id, next_index), li, True)
        )

    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    _set_view("", albums_view_mode)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/musicmp3/artists_albums")
def artists_albums():
    api    = _make_musicmp3()
    url    = _get_link()
    try:
        albums = api.artist_albums(url)
    except Exception as exc:
        _notify_error("Could not load artist albums: {0}".format(exc))
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return
    directory_items = []

    for a in albums:
        _title  = a.get("title",  "")
        _artist = a.get("artist", "")
        _label  = "{0} — {1}".format(_artist, _title) if _artist else _title
        li = xbmcgui.ListItem(_label)
        li.setLabel2(_artist)
        li.setArt({"thumb": a.get("image", ""), "icon": a.get("image", ""), "fanart": FANART})
        _set_music_tag(li,
            title=_title, artist=_artist,
            album=_title, year=a.get("date", ""),
            description=a.get("details", ""))
        li.addContextMenuItems(
            _album_context(a.get("link", ""), _title)
            + _fav_context(api, "album", a.get("link", ""), a.get("title", ""),
                           thumb=a.get("image", ""), artist=a.get("artist", ""))
        )
        directory_items.append((_link_url(musicmp3_album, a.get("link", "")), li, True))

    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    _set_view("", albums_view_mode)
    xbmcplugin.endOfDirectory(plugin.handle)


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #

@plugin.route("/musicmp3/search/<cat>")
def musicmp3_search(cat):
    keyboardinput = ""
    keyboard = xbmc.Keyboard("", "Search")
    keyboard.doModal()
    if keyboard.isConfirmed():
        keyboardinput = keyboard.getText().strip()

    if not keyboardinput:
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return

    api = _make_musicmp3()
    try:
        results = api.search(keyboardinput, cat, limit=_page_size() if cat == "songs" else None)
    except Exception as exc:
        _notify_error("Search failed: {0}".format(exc))
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return
    if not results:
        xbmcgui.Dialog().notification(
            plugin.name, "No results found.", xbmcgui.NOTIFICATION_INFO, 3000
        )
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=True)
        return
    directory_items = []

    if cat == "artists":
        for a in results:
            li = xbmcgui.ListItem(a.get("artist", ""))
            li.setArt({"fanart": FANART})
            _set_music_tag(li, title=a.get("artist", ""), artist=a.get("artist", ""))
            li.addContextMenuItems(_fav_context(
                api, "artist", a.get("link", ""), a.get("artist", "")
            ))
            directory_items.append((_link_url(artists_albums, a.get("link", "")), li, True))
        xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
        _set_view("", albums_view_mode)
        xbmcplugin.endOfDirectory(plugin.handle)

    elif cat == "albums":
        for a in results:
            _title  = a.get("title",  "")
            _artist = a.get("artist", "")
            _label  = "{0} — {1}".format(_artist, _title) if _artist else _title
            li = xbmcgui.ListItem(_label)
            li.setLabel2(_artist)
            li.setArt({"thumb": a.get("image", ""), "icon": a.get("image", ""), "fanart": FANART})
            _set_music_tag(li,
                title=_title, artist=_artist,
                album=_title, year=a.get("date", ""),
                description=a.get("details", ""))
            li.addContextMenuItems(
                _album_context(a.get("link", ""), _title)
                + _fav_context(api, "album", a.get("link", ""), _title,
                               thumb=a.get("image", ""), artist=_artist)
            )
            directory_items.append((_link_url(musicmp3_album, a.get("link", "")), li, True))
        xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
        _set_view("", albums_view_mode)
        xbmcplugin.endOfDirectory(plugin.handle)

    elif cat == "songs":
        _virt_url = "RunPlugin({0})".format(plugin.url_for(virt_toggle))
        _virt_lbl = _virt_label()
        for t in results:
            _title  = t.get("title",  "")
            _artist = t.get("artist", "")
            _label  = "{0} — {1}".format(_artist, _title) if _artist else _title
            li = xbmcgui.ListItem(_label)
            li.setProperty("IsPlayable", "true")
            li.setLabel2(_artist)
            li.setArt({"thumb": t.get("image", ""), "icon": t.get("image", "")})
            _set_music_tag(li,
                title=_title, artist=_artist,
                album=t.get("album", ""), duration=t.get("duration", 0))
            li.addContextMenuItems(
                [
                    ("🎬  Toggle Visualizer", "RunPlugin({0})".format(plugin.url_for(viz_toggle))),
                    (_virt_lbl,               _virt_url),
                ]
                + _song_fav_context(api, "song", t.get("rel", ""), t.get("title", ""),
                               thumb=t.get("image", ""), artist=t.get("artist", ""),
                               album=t.get("album", ""))
            )
            play_qs = (
                "?track_id=" + quote(t.get("track_id", ""), safe="")
                + "&rel="    + quote(t.get("rel", ""),      safe="")
                + "&album_url=" + quote(t.get("album_url", ""), safe="")
            )
            directory_items.append((plugin.url_for(musicmp3_play) + play_qs, li, False))
        xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
        _set_view("songs", songs_view_mode)
        xbmcplugin.endOfDirectory(plugin.handle)


# --------------------------------------------------------------------------- #
# Album track listing
# --------------------------------------------------------------------------- #

@plugin.route("/musicmp3/album")
def musicmp3_album():
    api = _make_musicmp3()
    url = _get_link()
    try:
        tracks, album_info = api.album_tracks(url)
    except Exception as exc:
        _notify_error("Could not load album: {0}".format(exc))
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return
    if not tracks:
        _notify_error("No tracks found — the site may be temporarily unavailable.")
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return

    ai_title  = album_info.get("title",  "")
    ai_artist = album_info.get("artist", "")
    ai_image  = album_info.get("image",  "")
    ai_year   = album_info.get("year",   "")
    ai_genre  = album_info.get("genre",  "")
    ai_desc   = album_info.get("description", "")

    directory_items = []
    _virt_url = "RunPlugin({0})".format(plugin.url_for(virt_toggle))
    _virt_lbl = _virt_label()
    for i, t in enumerate(tracks, 1):
        art = t.get("image", "") or ai_image
        li  = xbmcgui.ListItem(t.get("title", ""))
        li.setProperty("IsPlayable", "true")
        li.setArt({"thumb": art, "icon": art, "fanart": art})
        _set_music_tag(li,
            title=t.get("title", ""),
            artist=t.get("artist", "") or ai_artist,
            album=t.get("album",  "") or ai_title,
            year=ai_year, genre=ai_genre, description=ai_desc,
            duration=t.get("duration", 0), tracknumber=i)
        li.addContextMenuItems(
            [
                ("🎬  Toggle Visualizer", "RunPlugin({0})".format(plugin.url_for(viz_toggle))),
                (_virt_lbl,               _virt_url),
                ("🔀  Shuffle Album",
                 "RunPlugin({0})".format(
                     plugin.url_for(play_album)
                     + "?album_url=" + quote(t.get("album_url", ""), safe="")
                     + "&shuffle=1"
                 )),
            ]
            + _song_fav_context(api, "song", t.get("rel", ""), t.get("title", ""),
                           thumb=art,
                           artist=t.get("artist", "") or ai_artist,
                           album=t.get("album",  "") or ai_title)
        )
        play_qs = (
            "?track_id="  + quote(t.get("track_id",  ""), safe="")
            + "&rel="     + quote(t.get("rel",        ""), safe="")
            + "&album_url="+ quote(t.get("album_url", ""), safe="")
        )
        directory_items.append((plugin.url_for(musicmp3_play) + play_qs, li, False))

    xbmcplugin.addDirectoryItems(plugin.handle, directory_items, len(directory_items))
    _set_view("songs", songs_view_mode)
    xbmcplugin.endOfDirectory(plugin.handle)


# --------------------------------------------------------------------------- #
# Playback
# --------------------------------------------------------------------------- #

@plugin.route("/musicmp3/play")
def musicmp3_play():
    track_id  = unquote(plugin.args.get("track_id",   [""])[0])
    rel       = unquote(plugin.args.get("rel",         [""])[0])
    album_url = unquote(plugin.args.get("album_url",   [""])[0])

    api    = _make_musicmp3()
    _track = api.get_track(rel)
    url    = api.play_url(track_id, rel, referer_url=album_url or None)

    art = _track.image or ""
    li  = xbmcgui.ListItem(_track.title or "", path=url)
    # Fanart = album art fills the Now Playing background in most Kodi skins
    li.setArt({"thumb": art, "icon": art, "fanart": art})
    li.setMimeType("audio/mpeg")
    li.setContentLookup(False)
    _set_music_tag(li,
        title=_track.title    or "",
        artist=_track.artist  or "",
        album=_track.album    or "",
        duration=_track.duration or 0)
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


if __name__ == "__main__":
    plugin.run(sys.argv)
