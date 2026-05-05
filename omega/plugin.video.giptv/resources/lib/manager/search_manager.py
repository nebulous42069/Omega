try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import sys
import difflib
import unicodedata

from resources.utils.config import ensure_api_ready
import xbmc  # Necessary for functions like xbmc.sleep() and xbmc.Keyboard().
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib.manager.index_manager import _read_index
import resources.lib.navigator as navigator
import resources.utils.giptv as giptv

# Global constants for the Kodi API.
ADDON = xbmcaddon.Addon()
# PLUGIN_HANDLE: The unique identifier Kodi gives to this running addon instance.
# We use this to tell Kodi where to put our list items.
# SAFE plugin handle assignment (service.py will not crash)
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    PLUGIN_HANDLE = int(sys.argv[1])
else:
    PLUGIN_HANDLE = -1  # special value meaning "not in plugin mode"
ADDON_ID = ADDON.getAddonInfo("id")


def _normalize_title(s):
    if not s:
        return ""
    # strip accents and lowercase
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _fuzzy_score(query, candidate):
    """
    Returns a similarity score (0.0 - 1.0) between query and candidate.
    1.0 = exact match; uses containment + difflib as a fallback.
    """
    if not query or not candidate:
        return 0.0

    q = _normalize_title(query)
    c = _normalize_title(candidate)

    if not q or not c:
        return 0.0

    if q == c:
        return 1.0

    if q in c:
        return 0.95

    # difflib SequenceMatcher is fast enough for our sizes
    return difflib.SequenceMatcher(None, q, c).ratio()


def global_vod_search():
    """
    Search all VOD (Movies) using the prebuilt VOD index.
    Opens the stream lists for up to 5 best-matching unique categories.
    """
    if not ensure_api_ready():
        return

    # Ask user for search query
    keyboard = xbmc.Keyboard("", "Search ALL Movies")
    keyboard.doModal()
    if not keyboard.isConfirmed():
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    query = keyboard.getText().strip()
    if not query:
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Load VOD index
    vod_index = _read_index("vod")
    if not vod_index:
        giptv.notification(
            "Search",
            "No VOD index found. Rebuild Search Index first.",
            icon="INFO",
        )
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, f"Global Movie Search: {query}")
    xbmcplugin.setContent(PLUGIN_HANDLE, "movies")

    # --- Fuzzy match (threshold 0.65) ---
    matches = [
        (entry, _fuzzy_score(query, entry.get("lower", ""))) for entry in vod_index
    ]
    matches = [(e, s) for e, s in matches if s >= 0.65]

    if not matches:
        giptv.notification("Search", "No matching movies found.", icon="INFO")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)

    # --- Track added categories to avoid duplicates ---
    seen_categories = set()
    count = 0
    for entry, _ in matches:
        category_name = entry.get("category_name", "Unknown Category")

        if category_name in seen_categories:
            continue
        seen_categories.add(category_name)

        url = (
            sys.argv[0]
            + "?"
            + urlparse.urlencode(
                {
                    "mode": "list_streams",
                    "stream_type": "vod",
                    "category_id": entry.get("category_id", ""),
                    "category_name": category_name,
                    "search_query": query,
                }
            )
        )

        xbmcplugin.addDirectoryItem(
            PLUGIN_HANDLE,
            url,
            xbmcgui.ListItem(label=category_name),
            isFolder=True,
        )

        count += 1
        if count >= 5:  # Limit to top 5 unique categories
            break

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def global_live_search():
    """
    Search all live channels using the prebuilt live index.
    Opens the stream lists for up to 5 best-matching categories.
    Ensures duplicate categories are not displayed.
    """
    if not ensure_api_ready():
        return

    # Ask user for search query
    keyboard = xbmc.Keyboard("", "Search ALL Live TV")
    keyboard.doModal()
    if not keyboard.isConfirmed():
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    query = keyboard.getText().strip()
    if not query:
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Load live index
    live_index = _read_index("live")
    if not live_index:
        giptv.notification(
            "Search",
            "No Live index found. Rebuild Search Index first.",
            icon="INFO",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, f"Global Live Search: {query}")
    xbmcplugin.setContent(PLUGIN_HANDLE, "videos")

    # --- Fuzzy match (stricter threshold 0.65) ---
    matches = [
        (entry, _fuzzy_score(query, entry.get("lower", ""))) for entry in live_index
    ]
    matches = [(e, s) for e, s in matches if s >= 0.65]

    if not matches:
        giptv.return_action()
        giptv.notification("Search", "No matching channels found.", icon="INFO")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Sort by score descending and limit to top 20 matches
    matches.sort(key=lambda x: x[1], reverse=True)
    matches = matches[:20]

    # --- Track added categories to avoid duplicates ---
    seen_categories = set()
    for entry, _ in matches:
        category_id = entry.get("category_id", "")
        category_name = entry.get("category_name", "Unknown Category")

        # Skip if this category was already added
        if category_id in seen_categories:
            continue
        seen_categories.add(category_id)

        url = (
            sys.argv[0]
            + "?"
            + urlparse.urlencode(
                {
                    "mode": "list_streams",
                    "stream_type": "live",
                    "category_id": category_id,
                    "category_name": category_name,
                    "search_query": query,
                }
            )
        )

        xbmcplugin.addDirectoryItem(
            PLUGIN_HANDLE,
            url,
            xbmcgui.ListItem(label=category_name),
            isFolder=True,
        )

        # Stop after 5 unique categories
        if len(seen_categories) >= 5:
            break

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def global_search():
    """
    Global search across Live TV, Movies (VOD), and Series.
    Live results are shown first, then VOD, then Series.
    Opens the relevant list for up to 2 best-matching items per type.
    """
    if not ensure_api_ready():
        return

    # Ask user for search query
    keyboard = xbmc.Keyboard("", "Global Search (Live / Movies / Series)")
    keyboard.doModal()
    if not keyboard.isConfirmed():
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    query = keyboard.getText().strip()

    if not query:
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Load indexes
    live_index = _read_index("live") or []
    vod_index = _read_index("vod") or []
    series_index = _read_index("series") or []

    if not (live_index or vod_index or series_index):
        giptv.notification(
            "Search", "No search index found. Rebuild index first.", icon="ERROR"
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, f"Global Search: {query}")
    xbmcplugin.setContent(PLUGIN_HANDLE, "videos")

    # --- Helper functions ---
    def get_top_matches(index, key="lower", threshold=0.65, top_n=2):
        matches = [(entry, _fuzzy_score(query, entry.get(key, ""))) for entry in index]
        matches = [(e, s) for e, s in matches if s >= threshold]
        matches.sort(key=lambda x: x[1], reverse=True)
        return [e for e, _ in matches[:top_n]]

    def add_category_items(index, stream_type, max_items=2):
        seen_categories = set()
        count = 0
        for entry in index:
            category_id = entry.get("category_id", "")
            category_name = entry.get("category_name", "Unknown Category")
            if category_name in seen_categories:
                continue
            seen_categories.add(category_name)

            url = (
                sys.argv[0]
                + "?"
                + urlparse.urlencode(
                    {
                        "mode": "list_streams",
                        "stream_type": stream_type,
                        "category_id": category_id,
                        "category_name": category_name,
                        "search_query": query,
                    }
                )
            )
            xbmcplugin.addDirectoryItem(
                PLUGIN_HANDLE,
                url,
                xbmcgui.ListItem(label=category_name),
                isFolder=True,
            )

            count += 1
            if count >= max_items:
                break

    # --- Live TV first ---
    top_live = get_top_matches(live_index)
    add_category_items(top_live, "live", max_items=2)

    # --- Then VOD (Movies) ---
    top_vod = get_top_matches(vod_index)
    add_category_items(top_vod, "vod", max_items=2)

    # --- Then Series ---
    top_series = get_top_matches(
        series_index,
        key="lower" if series_index and "lower" in series_index[0] else "title",
        top_n=2,
    )

    if not top_live and not top_vod and not top_series:
        giptv.return_action()
        giptv.notification("No matches")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    for entry in top_series:
        series_id = entry.get("id")
        title = entry.get("title") or "Unknown Series"
        thumb = entry.get("thumb") or ""
        tmdb_id = entry.get("tmdb")

        list_item = xbmcgui.ListItem(label=title)
        if thumb:
            list_item.setArt({"thumb": thumb, "poster": thumb})

        list_item.setInfo("video", {"title": title, "mediatype": "tvshow"})

        if tmdb_id:
            list_item.setProperty("tmdbnumber", str(tmdb_id))
            list_item.setProperty("imdbnumber", str(tmdb_id))

        url = (
            sys.argv[0]
            + "?"
            + urlparse.urlencode(
                {
                    "mode": "list_series_seasons",
                    "series_id": series_id,
                    "series_name": title,
                }
            )
        )
        xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, url, list_item, isFolder=True)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def global_series_search():
    """
    Search all TV Series using the prebuilt Series index.
    Displays up to 5 best-matching series directly.
    """
    if not ensure_api_ready():
        return

    # Ask user for search query
    keyboard = xbmc.Keyboard("", "Search ALL TV Series")
    keyboard.doModal()
    if not keyboard.isConfirmed():
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    query = keyboard.getText().strip()
    if not query:
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Load Series index
    series_index = _read_index("series")
    if not series_index:
        giptv.notification(
            "Search",
            "No Series index found. Rebuild Search Index first.",
            icon="INFO",
        )
        giptv.return_action()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, f"Global Series Search: {query}")
    xbmcplugin.setContent(PLUGIN_HANDLE, "tvshows")

    # --- Fuzzy match (threshold 0.65) ---
    matches = [
        (s, _fuzzy_score(query, s.get("lower") or s.get("title", "")))
        for s in series_index
    ]
    matches = [(s, score) for s, score in matches if score >= 0.65]

    if not matches:
        giptv.notification("Search", "No matching series found.", icon="INFO")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # Sort by score and limit to top 5
    matches.sort(key=lambda x: x[1], reverse=True)
    top_series = [s for s, _ in matches[:5]]

    if not top_series:
        giptv.return_action()
        giptv.notification("No matches")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    # --- Add series items ---
    for entry in top_series:
        series_id = entry.get("id")
        title = entry.get("title") or "Unknown Series"
        thumb = entry.get("thumb") or ""
        tmdb_id = entry.get("tmdb")

        list_item = xbmcgui.ListItem(label=title)
        if thumb:
            list_item.setArt({"thumb": thumb, "poster": thumb})

        info = {
            "title": title,
            "mediatype": "tvshow",
        }
        list_item.setInfo("video", info)

        # TMDb properties if enabled
        if tmdb_id:
            list_item.setProperty("tmdbnumber", str(tmdb_id))
            list_item.setProperty("imdbnumber", str(tmdb_id))

        # URL to open series seasons
        url = (
            sys.argv[0]
            + "?"
            + urlparse.urlencode(
                {
                    "mode": "list_series_seasons",
                    "series_id": series_id,
                    "series_name": title,
                }
            )
        )

        xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, url, list_item, isFolder=True)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def dynamic_filter_search(items, search_query=None):
    """
    Filters the given list of items (category or streams) by a search term.
    items: list of dictionaries representing streams or series.
    search_query: optional, if not provided, prompts user for input.
    """
    if not ensure_api_ready():
        return

    if not items:
        giptv.notification("Search", "No items to search", icon="INFO")
        xbmcplugin.endOfDirectory(navigator.PLUGIN_HANDLE)
        return

    # Prompt keyboard if search_query is not given
    if not search_query:
        keyboard = xbmc.Keyboard("", "Filter items")
        keyboard.doModal()
        if not keyboard.isConfirmed():
            xbmcplugin.endOfDirectory(navigator.PLUGIN_HANDLE)
            return
        search_query = keyboard.getText().strip()
        if not search_query:
            xbmcplugin.endOfDirectory(navigator.PLUGIN_HANDLE)
            return

    xbmcplugin.setPluginCategory(navigator.PLUGIN_HANDLE, f"Filter: {search_query}")
    xbmcplugin.setContent(navigator.PLUGIN_HANDLE, "videos")

    # Filter items using fuzzy match
    matches = []
    for entry in items:
        text = (
            entry.get("title") or entry.get("name") or entry.get("category_name") or ""
        )
        score = _fuzzy_score(search_query, text.lower())
        if score >= 0.65:
            matches.append((entry, score))

    if not matches:
        giptv.notification("Search", "No matching items found", icon="INFO")
        xbmcplugin.endOfDirectory(navigator.PLUGIN_HANDLE)
        return

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)

    # Add filtered items back to the directory
    for entry, _ in matches:
        label = (
            entry.get("title")
            or entry.get("name")
            or entry.get("category_name")
            or "Unknown"
        )
        list_item = xbmcgui.ListItem(label=label)

        # If series, add artwork and info
        if entry.get("id") or entry.get("type") == "series":
            thumb = entry.get("thumb") or ""
            fanart = entry.get("fanart") or ""
            list_item.setArt({"thumb": thumb, "poster": thumb, "fanart": fanart})
            list_item.setInfo("video", {"title": label, "mediatype": "tvshow"})

            url_params = {
                "mode": "list_series_seasons",
                "series_id": entry.get("id"),
                "series_name": label,
            }
        else:
            url_params = {
                "mode": "play_stream" if entry.get("url") else "list_streams",
                "stream_type": entry.get("stream_type", ""),
                "category_id": entry.get("category_id", ""),
                "category_name": label,
                "url": entry.get("url", ""),
            }

        url = sys.argv[0] + "?" + urlparse.urlencode(url_params)
        xbmcplugin.addDirectoryItem(
            navigator.PLUGIN_HANDLE, url, list_item, isFolder=True
        )

    xbmcplugin.endOfDirectory(navigator.PLUGIN_HANDLE)
