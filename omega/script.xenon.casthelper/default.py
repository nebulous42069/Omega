# -*- coding: utf-8 -*-
"""Callable entry point for script.xenon.casthelper.

Used by DialogVideoInfo.xml to populate Window(Home).Property(MyCast.X.*)
for the current video-info item. The background service still handles home widgets.
"""
import json
import sys
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

import service


def log(msg):
    xbmc.log("[CastHelper Dialog] %s" % msg, xbmc.LOGINFO)



def execute_builtin(cmd, wait=False):
    """Run a Kodi builtin, using wait=True when the Kodi build supports it."""
    try:
        xbmc.executebuiltin(cmd, wait)
    except TypeError:
        xbmc.executebuiltin(cmd)


def close_info_stack():
    """Close DialogVideoInfo/custom-window layers without leaving the current Videos list.

    Keep a tiny pause because Kodi processes window changes asynchronously, but avoid
    the heavier delay from the earlier clean-stack builds.
    """
    execute_builtin("Dialog.Close(all,true)", True)
    xbmc.sleep(50)
    execute_builtin("ActivateWindow(Videos)", True)
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
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
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


def run_dialog_lookup(args):
    api_key, language, max_cast = service.get_settings()
    dbtype = clean(args.get("dbtype")) or clean(args.get("media_type"))
    media_type = normalize_media_type(dbtype)

    # Prefer the parent show TMDb id for seasons/episodes when the skin provides it.
    tmdb_id = ""
    if media_type == "tv":
        tmdb_id = clean(args.get("tmdbshow"))
    if not tmdb_id:
        tmdb_id = clean(args.get("tmdb")) or clean(args.get("tmdbprop"))

    imdb_id = clean(args.get("imdb")) or clean(args.get("imdb_id"))
    if not tmdb_id and imdb_id:
        tmdb_id = find_tmdb_from_imdb(api_key, imdb_id, media_type)

    if not api_key:
        log("No TMDb API key set. Clearing dialog cast fallback properties.")
        service.clear_cast_properties()
        return

    if not tmdb_id:
        log("No TMDb id found for DialogVideoInfo item. Clearing dialog cast fallback properties.")
        service.clear_cast_properties()
        return

    cast, info = service.fetch_cast_and_info_from_tmdb(
        api_key=api_key,
        language=language,
        tmdb_id=tmdb_id,
        media_type=media_type,
        max_cast=max_cast,
    )

    if cast:
        service.set_cast_properties(cast)
        service.set_info_properties(info)
        log("Loaded %d cast entries for DialogVideoInfo (%s %s)." % (len(cast), media_type, tmdb_id))
    else:
        service.clear_cast_properties()
        log("No cast returned for DialogVideoInfo (%s %s)." % (media_type, tmdb_id))



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
        home.setProperty("DVI.OriginTmdbId", tmdb_id)
    if dbid:
        home.setProperty("DVI.OriginDbid", dbid)
    home.setProperty("DVI.OriginTmdbType", tmdb_type)
    home.clearProperty("DVI.ReturnToCast")
    home.clearProperty("DVI.ShowCast")

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
    home.setProperty("DVI.ReturnToCast", "true")
    home.clearProperty("DVI.ShowCast")

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
