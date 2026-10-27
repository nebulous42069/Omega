# -*- coding: utf-8 -*-
import json
import re
import os
import sys
import uuid
import time
import threading
import urllib.request
import urllib.parse
import urllib.error

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x2_cast_config as xenon_cast_config
from x2_home_focus import watch as watch_home_focus
from x2_view_studios import watch as watch_view_studios
from x2_studio_logos import choose_logo, classification_logo

SERVICE_LOCK = xbmcvfs.translatePath("special://profile/addon_data/skin.xenon2/casthelper-service.lock")
HOME_WINDOW_ID = 10000
INFO_VISIBLE = '!Skin.HasSetting(Disable.XenonWidgetInfo) + !String.IsEqual(Skin.String(MainMenu.Layout),vertical) + Window.IsActive(home) + !Player.HasVideo + [[Container.Content(movies) | Container.Content(tvshows) | Container.Content(episodes) | String.IsEqual(Container.ListItem.DBType,movie) | String.IsEqual(Container.ListItem.DBType,tvshow) | String.IsEqual(Container.ListItem.DBType,episode) | String.IsEqual(Container.ListItem.Property(tmdb_type),movie) | String.IsEqual(Container.ListItem.Property(tmdb_type),tv) | String.IsEqual(Container.ListItem.MediaType,movie) | String.IsEqual(Container.ListItem.MediaType,tvshow)] | [ControlGroup(90010).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType),videos)]] | [ControlGroup(90020).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.2),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.2),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.2),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.2),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.2),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.2),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.2),videos)]] | [ControlGroup(96002).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel2),videos)]] | [ControlGroup(96003).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel3),videos)]] | [ControlGroup(96004).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel4),videos)]] | [ControlGroup(96005).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel5),videos)]] | [ControlGroup(96006).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel6),videos)]] | [ControlGroup(96007).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel7),videos)]] | [ControlGroup(96008).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel8),videos)]] | [ControlGroup(96009).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel9),videos)]] | [ControlGroup(96010).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel10),videos)]] | [ControlGroup(96011).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel11),videos)]] | [ControlGroup(96012).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel12),videos)]] | [ControlGroup(96013).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel13),videos)]] | [ControlGroup(96014).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel14),videos)]] | [ControlGroup(96015).HasFocus + [String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),movie) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),movies) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),tvshow) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),tvshows) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),episodes) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),video) | String.IsEqual(Container(9000).ListItem.Property(widgetType.sel15),videos)]]] + [[ControlGroup(90010).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo)) | String.Contains(Container(9000).ListItem.Property(widgetStyle),List)]] | [ControlGroup(90020).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.2)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.2),List)]] | [ControlGroup(96002).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel2)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel2),List)]] | [ControlGroup(96003).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel3)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel3),List)]] | [ControlGroup(96004).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel4)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel4),List)]] | [ControlGroup(96005).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel5)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel5),List)]] | [ControlGroup(96006).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel6)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel6),List)]] | [ControlGroup(96007).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel7)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel7),List)]] | [ControlGroup(96008).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel8)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel8),List)]] | [ControlGroup(96009).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel9)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel9),List)]] | [ControlGroup(96010).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel10)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel10),List)]] | [ControlGroup(96011).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel11)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel11),List)]] | [ControlGroup(96012).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel12)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel12),List)]] | [ControlGroup(96013).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel13)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel13),List)]] | [ControlGroup(96014).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel14)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel14),List)]] | [ControlGroup(96015).HasFocus + [!String.IsEmpty(Container(9000).ListItem.Property(widgetPanelInfo.sel15)) | String.Contains(Container(9000).ListItem.Property(widgetStyle.sel15),List)]]]'

# Widget container IDs used by your skin
WIDGET_IDS = set()
_WIDGET_MTIME = None
_WIDGET_SOURCES = {}

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
DEFAULT_TMDB_CREDENTIAL = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJmNTYwOGZiYTZhYjQ5ZTk5ODU4MjhiMzVkNTY1MzMyMSIsIm5iZiI6MTUzMDI2NzI0OS44NDcwMDAxLCJzdWIiOiI1YjM2MDY3MTkyNTE0MTNjOTMwMjkzZDMiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.sY0aCEb0tkFBHMJIxNRMbjYEmBu1aQF7z-uzRhu_134"


def log(msg):
    xbmc.log("[CastHelper] %s" % msg, xbmc.LOGINFO)


def _setting(setting_id):
    try:
        return (xenon_cast_config.read().get(setting_id) or "").strip()
    except Exception:
        return ""


def get_settings():
    credential = _setting("tmdb_api_key")
    bearer_token = _setting("tmdb_bearer_token")

    if bearer_token:
        credential = bearer_token

    # Fallback to hardcoded default if Kodi settings are empty.
    if not credential:
        credential = DEFAULT_TMDB_CREDENTIAL

    language = _setting("language") or "en-US"
    try:
        max_cast = max(1, min(50, int(_setting("max_cast") or "20")))
    except ValueError:
        max_cast = 5
    return credential, language, max_cast


def is_bearer_credential(credential):
    credential = (credential or "").strip()
    if credential.lower().startswith("bearer "):
        return True
    # TMDb API Read Access Tokens are JWTs and usually begin with eyJ... and contain
    # two dots. The v3 API key is a short hexadecimal string, so this is safe enough
    # for deciding which authentication method to use.
    return credential.startswith("eyJ") and credential.count(".") >= 2


def get_bearer_token(credential):
    credential = (credential or "").strip()
    if credential.lower().startswith("bearer "):
        return credential[7:].strip()
    return credential


def fetch_tmdb_json(credential, path, params=None, timeout=10):
    """Fetch JSON from TMDb using either a v3 API key or v4 read access token."""
    credential = (credential or "").strip()
    if not credential:
        return None

    if not path.startswith("/"):
        path = "/" + path

    params = dict(params or {})
    headers = {"Accept": "application/json"}

    if is_bearer_credential(credential):
        headers["Authorization"] = "Bearer %s" % get_bearer_token(credential)
    else:
        params["api_key"] = credential

    url = TMDB_API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = ""
        if e.code == 401:
            log("TMDb authentication failed (HTTP 401). The configured credential was rejected. "
                "Use a valid TMDb v3 API Key or v4/API Read Access Token. %s" % detail)
        else:
            log("HTTP error fetching info from TMDb: %s" % e.code)
    except Exception as e:
        log("Error fetching info from TMDb: %s" % type(e).__name__)
    return None


def get_focused_widget():
    """Use generated Skin Shortcuts IDs, including user-added menu items."""
    global WIDGET_IDS, _WIDGET_MTIME, _WIDGET_SOURCES
    import xml.etree.ElementTree as ET
    path = xbmcvfs.translatePath('special://skin/16x9/script-skinshortcuts-includes.xml')
    try:
        stamp = os.stat(path).st_mtime_ns
        if stamp != _WIDGET_MTIME:
            ids = set()
            sources = {}
            tree = ET.parse(path)
            for include in tree.getroot().findall('include'):
                name = include.get('name', '')
                # Skin Shortcuts emits both wrapper includes and profile-specific
                # implementations (for example widget1-Master user).
                match = re.match(r'^skinshortcuts-template-widget([12])(?:X2S(10|[2-9]))?(?:-|$)', name)
                if match is None:
                    continue
                source_suffix = ('.sel' + match.group(2) if match.group(2)
                                 else '.2' if match.group(1) == '2' else '')
                for control in include.iter('control'):
                    cid = control.get('id', '')
                    if control.get('type') in ('list', 'panel', 'fixedlist', 'wraplist') and cid.isdigit():
                        ids.add(int(cid))
                        sources[int(cid)] = source_suffix
            WIDGET_IDS = ids
            _WIDGET_SOURCES = sources
            _WIDGET_MTIME = stamp
        focused = xbmcgui.Window(HOME_WINDOW_ID).getFocusId()
        return focused if focused in WIDGET_IDS else None
    except (OSError, ValueError, RuntimeError, ET.ParseError):
        return None


def item_label(widget_id, field):
    return xbmc.getInfoLabel('Container(%d).ListItem.%s' % (widget_id, field)).strip()


def item_identity(widget_id):
    return (widget_id,) + tuple(item_label(widget_id, field) for field in (
        'DBType', 'Title', 'TVShowTitle', 'Year', 'FilenameAndPath',
        'Property(tmdb_id)', 'Property(tmdbshow_id)', 'UniqueID(tmdb)', 'IMDBNumber'))


def get_tmdb_id_for_widget(widget_id):
    """Prefer the focused item's IDs; never reuse another add-on's stale globals."""
    dbtype = item_label(widget_id, 'DBType').lower()
    kind = item_label(widget_id, 'Property(tmdb_type)').lower()
    source = xbmc.getInfoLabel('Container(9000).ListItem.Property(widgetType%s)' % _WIDGET_SOURCES.get(widget_id, '')).lower()
    if not dbtype and not kind and source in ('tv', 'tvshow', 'tvshows', 'episodes', 'seasons'):
        kind = 'tv'
    if not dbtype and not kind and item_label(widget_id, 'TVShowTitle'):
        kind = 'tv'

    media = 'tv' if dbtype in ('tvshow', 'episode', 'season', 'tv') or kind in ('tv', 'tvshow') else 'movie'
    show_id = item_label(widget_id, 'Property(tmdbshow_id)')
    if show_id.isdigit():
        return show_id, 'tv'
    if dbtype not in ('episode', 'season'):
        for field in ('Property(tmdb_id)', 'UniqueID(tmdb)', 'Property(tmdb)'):
            value = item_label(widget_id, field)
            if value.isdigit():
                return value, media
    path = item_label(widget_id, 'FilenameAndPath')
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        value = (query.get('tmdbshow_id') or query.get('tmdb_id') or [''])[0]
        kind = (query.get('tmdb_type') or [media])[0]
        if value.isdigit() and kind in ('movie', 'tv', 'tvshow'):
            return value, 'tv' if kind in ('tv', 'tvshow') else 'movie'
    except ValueError:
        pass
    return None, media


def resolve_tmdb_id(widget_id, credential, language):
    tmdb_id, media = get_tmdb_id_for_widget(widget_id)
    if tmdb_id:
        return tmdb_id, media
    imdb = item_label(widget_id, 'IMDBNumber') or item_label(widget_id, 'UniqueID(imdb)')
    if imdb.startswith('tt') and imdb[2:].isdigit():
        result = fetch_tmdb_json(credential, '/find/' + imdb,
                                 {'external_source': 'imdb_id'}, timeout=6) or {}
        entries = result.get('tv_results' if media == 'tv' else 'movie_results') or []
        if entries:
            return str(entries[0]['id']), media
    title = (item_label(widget_id, 'TVShowTitle') if media == 'tv' else '') or item_label(widget_id, 'Title') or item_label(widget_id, 'Label')
    if not title:
        return None, media
    params = {'query': title, 'language': language}
    year = item_label(widget_id, 'Year')
    if len(year) == 4 and year.isdigit() and item_label(widget_id, 'DBType').lower() != 'episode':
        params['first_air_date_year' if media == 'tv' else 'year'] = year
    entries = (fetch_tmdb_json(credential, '/search/' + media, params, timeout=6) or {}).get('results') or []
    # Require an exact title match for title-only lookups to avoid unrelated cast.
    for entry in entries:
        names = (entry.get('title', ''), entry.get('original_title', ''),
                 entry.get('name', ''), entry.get('original_name', ''))
        if title.casefold() in [name.casefold() for name in names]:
            return str(entry['id']), media
    return None, media


def local_info(widget_id):
    fields = {'year': 'Year', 'genres': 'Genre', 'rating': 'Rating',
              'director': 'Director', 'studio': 'Studio', 'certification': 'MPAA',
              'title': 'Title', 'plot': 'Plot', 'cast': 'Cast',
              'clearlogo': 'Art(clearlogo)', 'trailer': 'Trailer'}
    result = {key: item_label(widget_id, field) for key, field in fields.items()}
    result['title'] = result['title'] or item_label(widget_id, 'Label')
    result['poster'] = next((item_label(widget_id, field) for field in (
        'Art(poster)', 'Art(tvshow.poster)', 'Art(thumb)', 'Icon') if item_label(widget_id, field)), '')
    return result


def build_image_url(path, size="w185"):
    """
    Build a TMDb image URL from a relative path.
    """
    if not path:
        return ""
    return "%s/%s%s" % (TMDB_IMAGE_BASE, size, path)


def fetch_cast_and_info_from_tmdb(api_key, language, tmdb_id, media_type, max_cast):
    """
    Fetch cast and extra metadata from TMDb using the given ID and media type.
    Returns (cast_list, info_dict)
      cast_list: list of dicts: {name, character, thumb}
      info_dict: {year, genres, rating, votes, certification, director,
                  studio, studio_logo, network, network_logo}
    """
    result_cast = []
    result_info = {}

    if not api_key or not tmdb_id:
        return result_cast, result_info

    media_type = (media_type or "movie").lower()
    if media_type in ("tv", "tvshow"):
        path = "/tv/%s" % tmdb_id
        append = "credits,content_ratings"
    else:
        path = "/movie/%s" % tmdb_id
        append = "credits,release_dates"

    params = {
        "language": language,
        "append_to_response": append,
    }

    data = fetch_tmdb_json(api_key, path, params=params, timeout=10)
    if not data:
        return result_cast, result_info

    # ---- Cast ----
    credits = data.get("credits", {})
    for person in credits.get("cast", [])[:max_cast]:
        name = person.get("name") or ""
        character = person.get("character") or ""
        profile = person.get("profile_path") or ""
        thumb = build_image_url(profile, size="w185") if profile else ""
        result_cast.append({
            "name": name,
            "character": character,
            "thumb": thumb,
        })

    # ---- Basic info: year, genres, rating, votes ----
    if media_type in ("tv", "tvshow"):
        first_air = data.get("first_air_date") or ""
        year = first_air[:4] if len(first_air) >= 4 else ""
    else:
        release_date = data.get("release_date") or ""
        year = release_date[:4] if len(release_date) >= 4 else ""

    genres = ", ".join(
        g.get("name")
        for g in (data.get("genres") or [])
        if g.get("name")
    )

    vote_avg = data.get("vote_average")
    rating = ""
    if isinstance(vote_avg, (int, float)) and vote_avg > 0:
        rating = "%.1f" % vote_avg

    vote_count = data.get("vote_count")
    votes = str(vote_count) if isinstance(vote_count, int) and vote_count > 0 else ""

    # ---- Certification / content rating ----
    certification = ""
    try:
        if media_type in ("tv", "tvshow"):
            cr = (data.get("content_ratings") or {}).get("results") or []
            # Prefer US rating, else first non-empty
            chosen = None
            for r in cr:
                if (r.get("iso_3166_1") or "").upper() == "US" and r.get("rating"):
                    chosen = r
                    break
            if not chosen:
                for r in cr:
                    if r.get("rating"):
                        chosen = r
                        break
            if chosen:
                certification = chosen.get("rating") or ""
        else:
            rd_results = (data.get("release_dates") or {}).get("results") or []
            chosen = None
            # Prefer US release cert
            for r in rd_results:
                if (r.get("iso_3166_1") or "").upper() == "US":
                    for rd in r.get("release_dates") or []:
                        if rd.get("certification"):
                            chosen = rd
                            break
                if chosen:
                    break
            if not chosen:
                for r in rd_results:
                    for rd in r.get("release_dates") or []:
                        if rd.get("certification"):
                            chosen = rd
                            break
                    if chosen:
                        break
            if chosen:
                certification = chosen.get("certification") or ""
    except Exception as e:
        log("Error parsing certification: %s" % e)

    # ---- Director / creator ----
    director = ""
    try:
        crew = credits.get("crew") or []
        if media_type in ("tv", "tvshow"):
            # Try created_by first
            created_by = data.get("created_by") or []
            if created_by:
                director = created_by[0].get("name") or ""
            if not director:
                # Fallback to "Director" or "Executive Producer" from crew
                for c in crew:
                    job = (c.get("job") or "").lower()
                    if job == "director":
                        director = c.get("name") or ""
                        break
                if not director:
                    for c in crew:
                        job = (c.get("job") or "").lower()
                        if "producer" in job:
                            director = c.get("name") or ""
                            break
        else:
            for c in crew:
                if (c.get("job") or "").lower() == "director":
                    director = c.get("name") or ""
                    break
    except Exception as e:
        log("Error parsing director/creator: %s" % e)

    # ---- Studio / production company ----
    studio = ""
    studio_logo = ""
    try:
        companies = data.get("production_companies") or []
        for comp in companies:
            logo_path = comp.get("logo_path") or ""
            if logo_path:
                studio = comp.get("name") or ""
                studio_logo = build_image_url(logo_path, size="w185")
                break
    except Exception as e:
        log("Error parsing studio info: %s" % e)

    # ---- Network (TV) ----
    network = ""
    network_logo = ""
    try:
        if media_type in ("tv", "tvshow"):
            networks = data.get("networks") or []
            if networks:
                n = networks[0]
                network = n.get("name") or ""
                logo_path = n.get("logo_path") or ""
                if logo_path:
                    network_logo = build_image_url(logo_path, size="w185")
    except Exception as e:
        log("Error parsing network info: %s" % e)

    result_info = {
        "year": year,
        "genres": genres,
        "rating": rating,
        "votes": votes,
        "certification": certification,
        "director": director,
        "studio": studio,
        "studio_logo": studio_logo,
        "network": network,
        "network_logo": network_logo,
    }

    return result_cast, result_info


def set_cast_properties(cast):
    """
    Expose the given cast list (list of dicts) as window properties:
      X2Cast.1.Name, X2Cast.1.Role, X2Cast.1.Thumb, etc.
    """
    win = xbmcgui.Window(HOME_WINDOW_ID)
    _, _, max_cast = get_settings()

    for i in range(1, 51):
        idx = i - 1
        if idx < len(cast):
            person = cast[idx]
            win.setProperty("X2Cast.%d.Name" % i, person.get("name", ""))
            win.setProperty("X2Cast.%d.Role" % i, person.get("character", ""))
            win.setProperty("X2Cast.%d.Thumb" % i, person.get("thumb", ""))
        else:
            win.clearProperty("X2Cast.%d.Name" % i)
            win.clearProperty("X2Cast.%d.Role" % i)
            win.clearProperty("X2Cast.%d.Thumb" % i)


def set_info_properties(info):
    """
    Expose extra TMDb metadata as window properties:
      X2Info.Year, X2Info.Genres, X2Info.Rating, X2Info.Votes,
      X2Info.Certification, X2Info.Director,
      X2Info.Studio, X2Info.StudioLogo,
      X2Info.Network, X2Info.NetworkLogo
    """
    win = xbmcgui.Window(HOME_WINDOW_ID)

    def set_prop(key, value):
        win.setProperty("X2Info.%s" % key, value or "")

    logo, fallback = info.get('_logo_result', ('', '')) if '_logo_result' in info else choose_logo(info)
    set_prop("ResolvedStudioLogo", logo)
    set_prop("StudioLogoFallback", fallback)
    set_prop("Year", info.get("year", ""))
    set_prop("Genres", info.get("genres", ""))
    set_prop("Rating", info.get("rating", ""))
    set_prop("Votes", info.get("votes", ""))
    set_prop("Certification", info.get("certification", ""))
    set_prop("ClassificationLogo", classification_logo(info))
    set_prop("Director", info.get("director", ""))
    set_prop("Studio", info.get("studio", ""))
    set_prop("StudioLogo", info.get("studio_logo", ""))
    set_prop("Network", info.get("network", ""))
    set_prop("NetworkLogo", info.get("network_logo", ""))
    for key, field in [('Title', 'title'), ('Plot', 'plot'), ('Cast', 'cast'),
                       ('Poster', 'poster'), ('ClearLogo', 'clearlogo'), ('Trailer', 'trailer')]:
        set_prop(key, info.get(field, ''))



def clear_cast_properties():
    win = xbmcgui.Window(HOME_WINDOW_ID)
    _, _, max_cast = get_settings()
    for i in range(1, 51):
        win.clearProperty("X2Cast.%d.Name" % i)
        win.clearProperty("X2Cast.%d.Role" % i)
        win.clearProperty("X2Cast.%d.Thumb" % i)


def clear_info_properties():
    win = xbmcgui.Window(HOME_WINDOW_ID)
    keys = [
        "Year", "Genres", "Rating", "Votes", "Certification",
        "Director", "Studio", "StudioLogo", "Network", "NetworkLogo",
        "Title", "Plot", "Cast", "Poster", "ClearLogo", "Trailer",
        "ResolvedStudioLogo", "StudioLogoFallback", "ClassificationLogo",
    ]
    for key in keys:
        win.clearProperty("X2Info.%s" % key)

def skin_active():
    path = xbmcvfs.translatePath('special://skin/').replace('\\', '/').rstrip('/')
    return path.rsplit('/', 1)[-1].lower() == 'skin.xenon2'


def acquire_service_lock():
    """Distinguish Kodi processes so a recent lock from the last boot cannot block startup."""
    os.makedirs(os.path.dirname(SERVICE_LOCK), exist_ok=True)
    token = uuid.uuid4().hex
    for _ in range(2):
        try:
            with open(SERVICE_LOCK, 'x') as stream:
                json.dump({'pid': os.getpid(), 'token': token}, stream)
            return token
        except FileExistsError:
            try:
                with open(SERVICE_LOCK) as stream:
                    try:
                        owner = json.load(stream)
                    except ValueError:
                        owner = {}
                if (isinstance(owner, dict) and owner.get('pid') == os.getpid()
                        and time.time() - os.path.getmtime(SERVICE_LOCK) < 60):
                    return None
                os.unlink(SERVICE_LOCK)
            except FileNotFoundError:
                pass
    return None


def release_service_lock(token):
    try:
        with open(SERVICE_LOCK) as stream:
            try:
                owner = json.load(stream)
            except ValueError:
                return
        if not isinstance(owner, dict) or owner.get('token') != token:
            return
        os.unlink(SERVICE_LOCK)
    except FileNotFoundError:
        pass


class CastRowScroller:
    def __init__(self):
        self.identity = None
        self.count = 0
        self.position = 0
        self.next_at = 0
        self.reset_until = 0

    def start(self, identity, count, now):
        self.identity, self.count = identity, count
        self.position = 0
        self.next_at = now + 6
        self.reset_until = now + 2.0

    def tick(self, now):
        if now <= self.reset_until:
            # CurrentItem is one-based. Move by the exact distance to item one;
            # arbitrary negative moves wrap, and Python getControl is not
            # reliable for every skin-defined container on supported Kodi builds.
            try:
                current = int(xbmc.getInfoLabel('Container(98760).CurrentItem') or 0)
            except (TypeError, ValueError):
                current = 0
            if current > 1:
                xbmc.executebuiltin('Control.Move(98760,%d)' % (1 - current))
            return
        if self.count <= 8 or now < self.next_at:
            return
        # Advance the selected position past the visible eight-item viewport.
        # The disabled list cannot steal the active widget's focus or clicks.
        if self.position == 0:
            step = 8
        elif self.position >= self.count - 1:
            step = -self.position
        else:
            step = 1
        xbmc.executebuiltin('Control.Move(98760,%d)' % step)
        self.position += step
        self.next_at = now + (6 if self.position == 0 else 3)


def run_loop():
    monitor = xbmc.Monitor()
    cast_scroller = CastRowScroller()
    pending = None
    pending_since = 0.0
    published = None
    cache = {}
    resolved = {}
    log('Xenon 2 widget cast and info helper started.')
    try:
        while not monitor.abortRequested() and skin_active():
            os.utime(SERVICE_LOCK, None)
            if not xbmc.getCondVisibility(INFO_VISIBLE):
                if pending is not None or published is not None:
                    clear_cast_properties()
                    clear_info_properties()
                pending = published = None
                if monitor.waitForAbort(0.2):
                    break
                continue
            widget_id = get_focused_widget()
            if widget_id is None:
                # Re-entering the same widget item is a fresh cast-row visit.
                pending = published = None
                if monitor.waitForAbort(0.2):
                    break
                continue
            identity = item_identity(widget_id)
            now = time.monotonic()
            if identity != pending:
                pending = identity
                pending_since = now
                published = None
                clear_cast_properties()
                clear_info_properties()
                set_info_properties(local_info(widget_id))
            if now - pending_since >= 0.25 and published != identity:
                credential, language, max_cast = get_settings()
                local = local_info(widget_id)
                local['logo_studio'] = local.get('studio', '')
                cast, info = [], local
                if credential:
                    resolve_key = (identity, language, credential)
                    old = resolved.get(resolve_key)
                    if old and now - old[0] < 1800:
                        tmdb_id, media = old[1:]
                    else:
                        tmdb_id, media = resolve_tmdb_id(widget_id, credential, language)
                        resolved[resolve_key] = (now, tmdb_id, media)
                    key = (media, tmdb_id, language, max_cast)
                    cached = cache.get(key)
                    if tmdb_id and cached and now - cached[0] < 1800:
                        cast, fetched = cached[1:]
                        info = dict(local, **{k: v for k, v in fetched.items() if v})
                    elif tmdb_id:
                        cast, fetched = fetch_cast_and_info_from_tmdb(
                            credential, language, tmdb_id, media, max_cast)
                        if cast or fetched:
                            cache[key] = (now, cast, fetched)
                            info = dict(local, **{k: v for k, v in fetched.items() if v})
                    if len(cache) > 128:
                        del cache[min(cache, key=lambda k: cache[k][0])]
                    if len(resolved) > 128:
                        del resolved[min(resolved, key=lambda k: resolved[k][0])]
                info['_logo_result'] = choose_logo(info)
                # A request may complete after the user has moved to another item.
                # Discard it instead of displaying that item's cast under a new title.
                if (skin_active() and xbmc.getCondVisibility(INFO_VISIBLE)
                        and get_focused_widget() == widget_id and item_identity(widget_id) == identity):
                    set_cast_properties(cast)
                    set_info_properties(info)
                    published = identity
                    cast_scroller.start(identity, len(cast), time.monotonic())
            if published == identity:
                cast_scroller.tick(time.monotonic())
            if monitor.waitForAbort(0.2):
                break
    except Exception as exc:
        # Log the exception class only; credentials and request URLs stay private.
        log('Widget helper stopped after %s' % type(exc).__name__)
    finally:
        clear_cast_properties()
        clear_info_properties()
        log('Xenon 2 widget cast and info helper stopped.')


def run():
    token = acquire_service_lock()
    if token is None:
        return
    focus_stop = threading.Event()
    focus_thread = threading.Thread(target=watch_home_focus, args=(focus_stop,), daemon=True)
    focus_thread.start()
    view_thread = threading.Thread(target=watch_view_studios,
                                   args=(focus_stop, get_settings, fetch_tmdb_json), daemon=True)
    view_thread.start()
    try:
        run_loop()
    finally:
        focus_stop.set()
        focus_thread.join(timeout=1)
        view_thread.join(timeout=1)
        release_service_lock(token)


if __name__ == "__main__":
    run()
