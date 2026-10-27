# -*- coding: utf-8 -*-
"""Callable entry point for script.xenon.casthelper.

Used by DialogVideoInfo.xml to populate Window(Home).Property(X2DVI.Cast.X.*)
for the current video-info item. The background service still handles home widgets.
"""
import json
import sys
import os
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x2_cast_service as service
import x2_cast_config


def log(msg):
    xbmc.log("[CastHelper Dialog] %s" % msg, xbmc.LOGINFO)



def execute_builtin(cmd, wait=False):
    """Run a Kodi builtin, using wait=True when the Kodi build supports it."""
    try:
        xbmc.executebuiltin(cmd, wait)
    except TypeError:
        xbmc.executebuiltin(cmd)


def close_info_stack():
    """Use the opaque TMDb host window while switching information dialogs."""
    xbmcgui.Window(10000).setProperty('X2DVI.ActorSession', 'true')
    execute_builtin('Dialog.Close(all,true)', True)
    execute_builtin('ActivateWindow(1190)', True)
    xbmc.sleep(75)


def parse_args():
    args = {}
    for raw in sys.argv[1:]:
        if not raw:
            continue
        raw = raw.strip()
        if raw.startswith("?"):
            raw = raw[1:]
        # RunScript can pass comma-separated args, but also tolerate query-style args.
        parts = raw.split("&") if "&" in raw else [raw]
        for part in parts:
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            args[key.strip().lower()] = urllib.parse.unquote_plus(value.strip())
    return args


def clean(value):
    value = (value or "").strip()
    # XML RunScript calls often quote $ESCINFO[...] values; strip only a matching
    # outside quote pair so names like O'Shea still survive.
    while len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    if not value or value.startswith("$INFO["):
        return ""
    return value


def normalize_media_type(dbtype):
    dbtype = (dbtype or "").lower()
    if dbtype in ("tv", "tvshow", "season", "episode"):
        return "tv"
    return "movie"


def find_tmdb_from_imdb(api_key, imdb_id, media_type):
    imdb_id = clean(imdb_id)
    if not api_key or not imdb_id:
        return ""

    data = service.fetch_tmdb_json(
        api_key,
        "/find/%s" % urllib.parse.quote(imdb_id),
        params={"external_source": "imdb_id"},
        timeout=10,
    )
    if not data:
        return ""

    bucket = "tv_results" if media_type == "tv" else "movie_results"
    results = data.get(bucket) or []
    if not results:
        # If the DB type was uncertain, take the first sensible result.
        results = (data.get("movie_results") or data.get("tv_results") or [])
    if results and results[0].get("id"):
        return str(results[0].get("id"))
    return ""


INFO_FIELDS = {'Year':'year', 'Genres':'genres', 'Rating':'rating', 'Votes':'votes',
    'Certification':'certification', 'Director':'director', 'Studio':'studio',
    'StudioLogo':'studio_logo', 'Network':'network', 'NetworkLogo':'network_logo',
    'Title':'title', 'Plot':'plot', 'Cast':'cast', 'Poster':'poster',
    'ClearLogo':'clearlogo', 'Trailer':'trailer'}


def publish_dialog(home, cast, info):
    for i in range(1, 51):
        person = cast[i-1] if i <= len(cast) else {}
        for label, field in [('Name','name'), ('Role','character'), ('Thumb','thumb')]:
            home.setProperty('X2DVI.Cast.%d.%s' % (i, label), str(person.get(field) or ''))
    for label, field in INFO_FIELDS.items():
        home.setProperty('X2DVI.Info.' + label, str(info.get(field) or ''))


def run_dialog_lookup(args):
    import uuid
    home = xbmcgui.Window(10000)
    request = uuid.uuid4().hex
    home.setProperty('X2DVI.Request', request)
    publish_dialog(home, [], {})
    home.clearProperty('X2DVI.OriginTmdbId')
    home.clearProperty('X2DVI.OriginDbid')
    dbid = clean(xbmc.getInfoLabel('ListItem.DBID'))
    if dbid:
        home.setProperty('X2DVI.OriginDbid', dbid)
    api_key, language, max_cast = service.get_settings()
    media_type = normalize_media_type(clean(args.get('dbtype')) or clean(args.get('media_type')))
    home.setProperty('X2DVI.OriginTmdbType', media_type)
    tmdb_id = clean(args.get('tmdbshow')) if media_type == 'tv' else ''
    tmdb_id = tmdb_id or clean(args.get('tmdb')) or clean(args.get('tmdbprop'))
    try:
        if not tmdb_id:
            tmdb_id = find_tmdb_from_imdb(api_key, clean(args.get('imdb')), media_type)
        if not api_key or not tmdb_id:
            log('No TMDb credentials or title identifier for video info.')
            return
        cast, info = service.fetch_cast_and_info_from_tmdb(
            api_key=api_key, language=language, tmdb_id=tmdb_id,
            media_type=media_type, max_cast=max_cast)
        if home.getProperty('X2DVI.Request') != request:
            return
        home.setProperty('X2DVI.OriginTmdbId', str(tmdb_id))
        publish_dialog(home, cast or [], info or {})
        if home.getProperty('X2DVI.ReturnToCast') == 'true':
            home.clearProperty('X2DVI.ReturnToCast')
            home.setProperty('X2DVI.ShowCast', 'true')
            actor = home.getProperty('X2DVI.ReturnActor')
            position = next((i for i, entry in enumerate(cast or [])
                             if entry.get('name') == actor), 0)
            # Allow Kodi's property-backed static items to become visible.
            xbmc.sleep(200)
            if home.getProperty('X2DVI.Request') == request:
                xbmc.executebuiltin('SetFocus(%d,%d)' % (5050 if cast else 50, position))
        log('Loaded %d video-info cast entries.' % len(cast or []))
    except Exception as exc:
        log('Video-info cast lookup failed: %s' % exc)



def run_open_person(args):
    """Open a TMDb Helper person page without leaving the source DialogVideoInfo underneath.

    Direct XML calls stacked the person-flavoured DialogVideoInfo on top of the original
    movie/show DialogVideoInfo. That made Back reveal the stale person dialog again after
    returning to the original title. This mode stores the origin, closes the current dialog
    stack first, then opens the person lookup cleanly.
    """
    person = clean(args.get("person") or args.get("name") or args.get("query"))
    tmdb_id = clean(args.get("tmdb")) or clean(args.get("tmdb_id"))
    dbid = clean(args.get("dbid"))
    tmdb_type = clean(args.get("tmdb_type")) or clean(args.get("type")) or "movie"
    if tmdb_type in ("tvshow", "episode", "season"):
        tmdb_type = "tv"
    elif tmdb_type not in ("movie", "tv"):
        tmdb_type = "movie"

    home = xbmcgui.Window(10000)
    if tmdb_id:
        home.setProperty("X2DVI.OriginTmdbId", tmdb_id)
    if dbid:
        home.setProperty("X2DVI.OriginDbid", dbid)
    home.setProperty("X2DVI.OriginTmdbType", tmdb_type)
    home.setProperty("X2DVI.ReturnActor", person)
    home.clearProperty("X2DVI.ReturnToCast")
    home.clearProperty("X2DVI.ShowCast")

    if not person:
        log("openperson: no person name supplied.")
        return

    query = urllib.parse.quote_plus(person)
    cmd = "RunScript(plugin.video.themoviedb.helper,add_query=%s,tmdb_type=person,call_auto=1190)" % query
    log("Opening person info cleanly with: %s" % cmd)
    close_info_stack()
    xbmc.executebuiltin(cmd)


def run_return_origin(args):
    """Close the current TMDb person info stack, then reopen the original title.

    XML-only return left the person DialogVideoInfo beneath the restored movie/show dialog.
    That made Back bounce between the two windows. Running the return through Python lets us
    close the current dialog stack first, wait briefly, and then open the original item cleanly.
    """
    tmdb_id = clean(args.get("tmdb")) or clean(args.get("tmdb_id"))
    dbid = clean(args.get("dbid"))
    tmdb_type = clean(args.get("tmdb_type")) or clean(args.get("type")) or "movie"
    if tmdb_type in ("tvshow", "episode", "season"):
        tmdb_type = "tv"
    elif tmdb_type not in ("movie", "tv"):
        tmdb_type = "movie"

    home = xbmcgui.Window(10000)
    home.setProperty("X2DVI.ReturnToCast", "true")
    home.clearProperty("X2DVI.ShowCast")

    if tmdb_id:
        cmd = "RunScript(plugin.video.themoviedb.helper,add_tmdb=%s,tmdb_type=%s,call_auto=1190)" % (tmdb_id, tmdb_type)
    elif dbid:
        cmd = "RunScript(plugin.video.themoviedb.helper,add_dbid=%s,tmdb_type=%s,call_auto=1190)" % (dbid, tmdb_type)
    else:
        log("returnorigin: no origin tmdb/dbid supplied; closing dialogs only.")
        xbmc.executebuiltin("Dialog.Close(all,true)")
        return

    log("Returning to original DialogVideoInfo with: %s" % cmd)
    close_info_stack()
    xbmc.executebuiltin(cmd)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'settings':
        x2_cast_config.configure()
        return
    args = parse_args()
    mode = (args.get("mode") or "").lower()
    if mode in ("videoinfo", "dialogvideoinfo", "dialog"):
        run_dialog_lookup(args)
    elif mode in ("openperson", "open_person", "person"):
        run_open_person(args)
    elif mode in ("returnorigin", "return_origin", "return"):
        run_return_origin(args)
    else:
        log("No supported mode supplied. Args: %s" % args)


if __name__ == "__main__":
    main()
