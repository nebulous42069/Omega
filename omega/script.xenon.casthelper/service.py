# -*- coding: utf-8 -*-
import json
import time
import urllib.request
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
HOME_WINDOW_ID = 10000

# Widget container IDs used by your skin
WIDGET_IDS = list(range(8000, 8046)) + [int(f"{i}1") for i in range(8000, 8046)]  # 8000–8045 poster; 80001–80451 thumb

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def log(msg):
    xbmc.log("[CastHelper] %s" % msg, xbmc.LOGINFO)


def get_settings():
    api_key = ADDON.getSetting("tmdb_api_key").strip()
    language = ADDON.getSetting("language") or "en-US"
    try:
        max_cast = int(ADDON.getSetting("max_cast") or "5")
    except ValueError:
        max_cast = 5
    return api_key, language, max_cast


def get_focused_widget():
    """
    Return the ID of the widget container that currently has focus, or None.
    """
    for cid in WIDGET_IDS:
        if xbmc.getCondVisibility("Control.HasFocus(%d)" % cid):
            return cid
    return None


def get_tmdb_id_for_widget(widget_id):
    """
    Try to find a TMDb ID for the focused item in the given widget.
    Strategy:
      1) Use TMDb Helper's global property if available
      2) Fall back to common listitem properties
      3) Fall back to uniqueid(tmdb)
      4) As a last resort, parse the tmdb_id from the plugin URL
         (for favourites / Trakt 'next episodes' etc.)
    Returns (tmdb_id, media_type) where media_type is 'movie' or 'tv'.
    """
    # 1) TMDb Helper global property if present
    tmdb_id = xbmc.getInfoLabel("Window(Home).Property(TMDbHelper.ListItem.TMDB_Id)")
    if tmdb_id:
        media_type = xbmc.getInfoLabel("Window(Home).Property(TMDbHelper.ListItem.Type)")
        if media_type.lower() not in ("movie", "tv"):
            media_type = xbmc.getInfoLabel("Container(%d).ListItem.DBType" % widget_id)
        return tmdb_id, (media_type or "movie")

    # 2) Direct listitem property: tmdb_id
    tmdb_id = xbmc.getInfoLabel("Container(%d).ListItem.Property(tmdb_id)" % widget_id)
    if tmdb_id:
        media_type = xbmc.getInfoLabel("Container(%d).ListItem.DBType" % widget_id)
        return tmdb_id, (media_type or "movie")

    # 3) Unique ID 'tmdb' if set
    tmdb_id = xbmc.getInfoLabel("Container(%d).ListItem.UniqueId(tmdb)" % widget_id)
    if tmdb_id:
        media_type = xbmc.getInfoLabel("Container(%d).ListItem.DBType" % widget_id)
        return tmdb_id, (media_type or "movie")

    # 4) Parse TMDb id from plugin URL for TMDb Helper favourites / Trakt lists
    path = xbmc.getInfoLabel("Container(%d).ListItem.FilenameAndPath" % widget_id)
    if not path:
        path = xbmc.getInfoLabel("Container(%d).ListItem.FileNameAndPath" % widget_id)

    if path.startswith("plugin://plugin.video.themoviedb.helper"):
        try:
            parsed = urllib.parse.urlparse(path)
            qs = urllib.parse.parse_qs(parsed.query)
            tmdb_id = (qs.get("tmdb_id") or [""])[0]
            media_type = (qs.get("tmdb_type") or ["tv"])[0]  # default to 'tv' for next episodes
            if tmdb_id:
                return tmdb_id, media_type or "tv"
        except Exception as e:
            log("Error parsing tmdb_id from path: %s" % e)

    return None, None



def build_image_url(path, size="w185"):
    """
    Build a TMDb image URL from a relative path.
    """
    if not path:
        return ""
    return "%s/%s%s" % (TMDB_IMAGE_BASE, size, path)



def wrap_image_url(url: str) -> str:
    """
    Kodi loads remote images more reliably via the image:// protocol (cached/encoded).
    Returns an empty string if url is empty.
    """
    if not url:
        return ""
    # Encode EVERYTHING (including : and /) for image://
    encoded = urllib.parse.quote(url, safe="")
    return f"image://{encoded}/"


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
        "api_key": api_key,
        "language": language,
        "append_to_response": append,
    }
    url = TMDB_API_BASE + path + "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log("Error fetching info from TMDb: %s" % e)
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
                studio_logo = wrap_image_url(build_image_url(logo_path, size="w185"))
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
                    network_logo = wrap_image_url(build_image_url(logo_path, size="w185"))
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
      MyCast.1.Name, MyCast.1.Role, MyCast.1.Thumb, etc.
    """
    win = xbmcgui.Window(HOME_WINDOW_ID)
    _, _, max_cast = get_settings()

    for i in range(1, max_cast + 1):
        idx = i - 1
        if idx < len(cast):
            person = cast[idx]
            win.setProperty("MyCast.%d.Name" % i, person.get("name", ""))
            win.setProperty("MyCast.%d.Role" % i, person.get("character", ""))
            win.setProperty("MyCast.%d.Thumb" % i, person.get("thumb", ""))
        else:
            win.clearProperty("MyCast.%d.Name" % i)
            win.clearProperty("MyCast.%d.Role" % i)
            win.clearProperty("MyCast.%d.Thumb" % i)


def set_info_properties(info):
    """
    Expose extra TMDb metadata as window properties:
      MyInfo.Year, MyInfo.Genres, MyInfo.Rating, MyInfo.Votes,
      MyInfo.Certification, MyInfo.Director,
      MyInfo.Studio, MyInfo.StudioLogo,
      MyInfo.Network, MyInfo.NetworkLogo
    """
    win = xbmcgui.Window(HOME_WINDOW_ID)

    def set_prop(key, value):
        win.setProperty("MyInfo.%s" % key, value or "")

    set_prop("Year", info.get("year", ""))
    set_prop("Genres", info.get("genres", ""))
    set_prop("Rating", info.get("rating", ""))
    set_prop("Votes", info.get("votes", ""))
    set_prop("Certification", info.get("certification", ""))
    set_prop("Director", info.get("director", ""))
    set_prop("Studio", info.get("studio", ""))
    set_prop("StudioLogo", info.get("studio_logo", ""))
    set_prop("Network", info.get("network", ""))
    set_prop("NetworkLogo", info.get("network_logo", ""))

    # Optional: also alias some of these into TMDbHelper.* namespace so existing
    # skin code that reads TMDbHelper.ListItem.Year/Genre/Rating can benefit.
    win.setProperty("TMDbHelper.ListItem.Year", info.get("year", ""))
    win.setProperty("TMDbHelper.ListItem.Genre", info.get("genres", ""))
    win.setProperty("TMDbHelper.ListItem.Rating", info.get("rating", ""))
    win.setProperty("TMDbHelper.ListItem.Certification", info.get("certification", ""))


def clear_cast_properties():
    win = xbmcgui.Window(HOME_WINDOW_ID)
    _, _, max_cast = get_settings()
    for i in range(1, max_cast + 1):
        win.clearProperty("MyCast.%d.Name" % i)
        win.clearProperty("MyCast.%d.Role" % i)
        win.clearProperty("MyCast.%d.Thumb" % i)


def clear_info_properties():
    win = xbmcgui.Window(HOME_WINDOW_ID)
    keys = [
        "Year", "Genres", "Rating", "Votes", "Certification",
        "Director", "Studio", "StudioLogo", "Network", "NetworkLogo",
    ]
    for key in keys:
        win.clearProperty("MyInfo.%s" % key)
    # Also clear aliases we set into TMDbHelper namespace
    for key in ("Year", "Genre", "Rating", "Certification"):
        win.clearProperty("TMDbHelper.ListItem.%s" % key)


def run():
    api_key, language, max_cast = get_settings()
    monitor = xbmc.Monitor()
    last_tmdb_id = None
    last_media_type = None

    if not api_key:
        log("No TMDb API key set in add-on settings. Cast helper will idle.")
        # Still run the loop so we can react if user sets key later.
    else:
        log("Cast & info helper started.")

    try:
        while not monitor.abortRequested():
            # Only bother when Home is visible
            if xbmc.getCondVisibility("Window.IsVisible(home)"):
                widget_id = get_focused_widget()
                if widget_id:
                    # Skip episode items: TMDb IDs for episodes often resolve to the parent show and give "wrong" info.
                    dbtype = xbmc.getInfoLabel(f"Container({widget_id}).ListItem.DBType").lower()
                    season = xbmc.getInfoLabel(f"Container({widget_id}).ListItem.Season")
                    episode = xbmc.getInfoLabel(f"Container({widget_id}).ListItem.Episode")

                    if dbtype == "episode" or season or episode:
                        clear_cast_properties()
                        clear_info_properties()
                        last_tmdb_id = None
                        last_media_type = None
                        if monitor.waitForAbort(0.7):
                            break
                        continue

                    tmdb_id, media_type = get_tmdb_id_for_widget(widget_id)

                    if tmdb_id and (tmdb_id != last_tmdb_id or media_type != last_media_type):
                        api_key, language, max_cast = get_settings()
                        if api_key:
                            cast, info = fetch_cast_and_info_from_tmdb(
                                api_key, language, tmdb_id, media_type, max_cast
                            )
                            set_cast_properties(cast)
                            set_info_properties(info)
                            last_tmdb_id = tmdb_id
                            last_media_type = media_type
                        else:
                            clear_cast_properties()
                            clear_info_properties()
                    # If no tmdb_id, clear properties so skin hides the row
                    elif not tmdb_id:
                        clear_cast_properties()
                        clear_info_properties()
                        last_tmdb_id = None
                        last_media_type = None

            # Sleep a bit; react faster than a sloth, slower than a CPU hog
            if monitor.waitForAbort(0.7):
                break

    finally:
        clear_cast_properties()
        clear_info_properties()
        log("Cast & info helper stopped.")


if __name__ == "__main__":
    run()
