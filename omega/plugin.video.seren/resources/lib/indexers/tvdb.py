import contextlib
import time
import traceback
from functools import cached_property
from functools import wraps

import xbmcgui

from . import valid_id_or_none
from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

# TVDB v4 API keys — publicly distributed by TVDB for Kodi use
# Source: metadata.tvshows.thetvdb.com.v4.python (official TVDB Kodi plugin)
_ANON_API_KEY = "edae60dc-1b44-4bac-8db7-65c0aaf5258b"   # anonymous tier (no PIN)
_PIN_API_KEY = "51bdbd35-bcd5-40d9-9bc3-788e24454baf"    # subscriber tier (requires PIN)

# v4 artwork type integers → Seren art type names
# Type 7 (season poster) is handled separately in get_season_art()
_ART_TYPE_MAP = {
    1: "banner",
    2: "poster",
    3: "fanart",
    22: "clearart",
    23: "clearlogo",
}

# TVDB v4 returns 3-letter ISO 639-2 language codes; metadataHandler expects 2-letter ISO 639-1.
_TVDB_LANG_3TO2 = {
    "eng": "en", "fra": "fr", "deu": "de", "spa": "es", "ita": "it",
    "por": "pt", "rus": "ru", "pol": "pl", "jpn": "ja", "zho": "zh",
    "kor": "ko", "ara": "ar", "nld": "nl", "swe": "sv", "nor": "no",
    "fin": "fi", "dan": "da", "ces": "cs", "tur": "tr", "hun": "hu",
    "heb": "he", "ind": "id", "vie": "vi", "tha": "th",
}


def _norm_lang(lang):
    """Normalise a TVDB v4 3-letter language code to the 2-letter code metadataHandler expects.
    Returns None for absent/empty codes so _filter_art treats the artwork as language-neutral."""
    if not lang:
        return None
    return _TVDB_LANG_3TO2.get(lang, lang)


def tvdb_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        method_class = args[0]
        import requests

        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            if response.status_code == 401:
                with contextlib.suppress(RanOnceAlready):
                    with GlobalLock("tvdb.oauth", run_once=True, check_sum=method_class.jwToken):
                        if method_class.jwToken is not None:
                            method_class.try_refresh_token(True)
                if method_class.jwToken is not None:
                    return func(*args, **kwarg)

            error_message = TVDBAPI.http_codes.get(response.status_code, "Unknown error")
            g.log(
                f"TVDB returned a {response.status_code} ({error_message}): while requesting {response.url}",
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30024).format("TVDB"))
            if g.get_runtime_setting("run.mode") == "test":
                raise
            else:
                g.log_stacktrace()
            return None

    return wrapper


def wrap_tvdb_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {"tvdb_object": tvdb_art_sorter(func(*args, **kwarg))}

    return wrapper


def tvdb_art_sorter(item):
    if not item or not item.get("art"):
        return item

    for art_type in ["banner", "poster", "fanart", "clearart", "clearlogo"]:
        if art_type not in item.get("art", {}):
            continue
        # v4 languages are 3-letter ISO codes ("eng") — sort English/neutral first, then by score
        item["art"][art_type] = sorted(
            item["art"][art_type],
            key=lambda k: (
                0 if k.get("language") in ("eng", "en", None, "") else 1,
                -(k.get("rating") or 0),
            ),
        )
    return item


class TVDBAPI(ApiBase):
    baseUrl = "https://api4.thetvdb.com/v4/"

    normalization = [
        ("imdbId", ("imdbnumber", "imdb_id"), lambda i: valid_id_or_none(i)),
        ("id", "tvdb_id", None),
        ("firstAired", ("premiered", "aired"), lambda t: g.validate_date(t)),
        ("overview", ("plot", "plotoutline"), None),
        ("mediatype", "mediatype", None),
    ]

    show_normalization = tools.extend_array(
        [
            (
                "firstAired",
                "year",
                lambda t: g.validate_date(t)[:4] if g.validate_date(t) else None,
            ),
            ("status", "status", None),
            (
                "runtime",
                "runtime",
                lambda d: int(d) * 60 if d is not None and str(d).strip().isdigit() else None,
            ),
            ("network", "studio", None),
            ("genre", "genre", lambda t: sorted(set(t)) if t else None),
            ("seriesName", ("title", "tvshowtitle"), None),
            ("rating", "mpaa", None),
            ("language", "language", None),
            ("aliases", "aliases", None),
            (
                "country",
                "country_origin",
                lambda t: t.upper() if t else None,
            ),
        ],
        normalization,
    )

    http_codes = {
        200: "Success",
        201: "Success - new resource created (POST)",
        401: "Returned if your JWT token is missing or expired",
        404: "Returned if the given ID does not exist.",
        405: "Missing query params are given",
        409: "Returned if requested record could not be updated/deleted",
        422: "Invalid query params provided",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

    def __init__(self):
        self._load_settings()
        self.lang_code = g.get_language_code(False)
        self.preferred_artwork_size = g.get_int_setting("artwork.preferredsize")

        if not self.jwToken:
            self.init_token()
        else:
            self.try_refresh_token()

    @cached_property
    def meta_hash(self):
        return tools.md5_hash((self.baseUrl, bool(self.pin), self.preferred_artwork_size))

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    def _get_headers(self, lang=None):
        headers = {"content-type": "application/json"}
        if self.jwToken:
            headers["Authorization"] = f"Bearer {self.jwToken}"
        if lang is not None:
            headers["Accept-Language"] = lang
        return headers

    def _get_login_body(self):
        login_info = {"apikey": self.apiKey}
        if self.pin:
            login_info["pin"] = self.pin
        return login_info

    def _load_settings(self):
        self.pin = g.get_setting("tvdb.pin", "")
        self.apiKey = _PIN_API_KEY if self.pin else _ANON_API_KEY
        self.jwToken = g.get_setting("tvdb.jw")
        self.tokenExpires = g.get_float_setting("tvdb.expiry")

    def _save_settings(self, response):
        token = None
        if isinstance(response, dict):
            # v4 wraps token in {"data": {"token": "..."}, "status": "success"}
            token = (response.get("data") or {}).get("token")
        if token:
            g.set_setting("tvdb.jw", token)
            self.jwToken = token
            self.tokenExpires = time.time() + (24 * 60 * 60)
            g.set_setting("tvdb.expiry", str(self.tokenExpires))

    def try_refresh_token(self, force=False):
        if not force and self.tokenExpires > float(time.time()):
            return
        try:
            with GlobalLock(self.__class__.__name__, True, self.jwToken):
                try:
                    g.log("TVDB Token requires refreshing...")
                    # v4 has no /refresh_token endpoint — re-POST /login
                    response = self.session.post(
                        f"{self.baseUrl}login",
                        json=self._get_login_body(),
                        headers=self._get_headers(),
                    ).json()
                    self._save_settings(response)
                    g.log("Refreshed TVDB Token")
                except Exception:
                    g.log("Failed to refresh TVDB Access Token", "error")
                    return
        except RanOnceAlready:
            return

    def init_token(self):
        try:
            with GlobalLock(self.__class__.__name__, True):
                response = self.session.post(
                    f"{self.baseUrl}login",
                    json=self._get_login_body(),
                    headers=self._get_headers(),
                ).json()
                self._save_settings(response)
        except RanOnceAlready:
            return

    @tvdb_guard_response
    def get(self, url, **params):
        language = params.pop("language") if "language" in params else None
        timeout = params.pop("timeout", 10)
        return self.session.get(
            self.baseUrl + url,
            params=params,
            headers=self._get_headers(language),
            timeout=timeout,
        )

    @use_cache()
    def _get_show_extended(self, tvdb_id):
        """Fetch and cache the full v4 extended series response (show info + artwork + cast)."""
        response = self.get(f"series/{tvdb_id}/extended")
        if response is None:
            return None
        try:
            data = response.json()
            if data.get("status") != "success":
                g.log(
                    f"TVDB v4 non-success for series/{tvdb_id}: {data.get('message', '')}",
                    "warning",
                )
                return None
            return data.get("data")
        except (ValueError, AttributeError):
            traceback.print_exc()
            g.log(f"Failed to parse TVDB v4 extended response for {tvdb_id}", "error")
            return None

    def _preprocess_v4_show(self, raw):
        """Convert v4 extended series dict into a flat dict compatible with normalization."""
        if raw is None:
            return None

        # IMDB ID from remoteIds array
        imdb_id = None
        for rid in (raw.get("remoteIds") or []):
            if rid.get("sourceName") == "IMDB":
                imdb_id = rid.get("id")
                break

        # Content rating: prefer USA, fall back to first available
        content_rating = None
        for cr in (raw.get("contentRatings") or []):
            if cr.get("country") == "usa":
                content_rating = cr.get("name")
                break
        if content_rating is None:
            content_ratings = raw.get("contentRatings") or []
            content_rating = content_ratings[0].get("name") if content_ratings else None

        # Runtime: v4 uses averageRuntime (minutes); the runtime field is often empty
        runtime = raw.get("averageRuntime") or raw.get("runtime")

        return {
            "id": raw.get("id"),
            "seriesName": raw.get("name"),
            "overview": raw.get("overview"),
            "firstAired": raw.get("firstAired"),
            "runtime": str(runtime) if runtime is not None else "",
            "status": (raw.get("status") or {}).get("name"),
            "network": (raw.get("latestNetwork") or {}).get("name"),
            "rating": content_rating,
            "genre": [
                genre_item.get("name")
                for genre_item in (raw.get("genres") or [])
                if genre_item.get("name")
            ],
            "country": (raw.get("originalCountry") or "").upper() or None,
            "imdbId": imdb_id,
            "language": None,
            "aliases": [a.get("name") for a in (raw.get("aliases") or []) if a.get("name")],
            "mediatype": "tvshow",
        }

    def _extract_art_v4(self, raw):
        """Extract and categorize artwork from v4 extended response artworks[]."""
        result = {}
        artworks = raw.get("artworks") or []

        for art in artworks:
            art_type = art.get("type")
            if art_type not in _ART_TYPE_MAP:
                continue  # skip season posters (type 7) and unknown types here

            image_url = art.get("image")
            if not image_url:
                continue

            # Use thumbnail (smaller) when artwork.preferredsize == 2
            if self.preferred_artwork_size == 2 and art.get("thumbnail"):
                display_url = art["thumbnail"]
            else:
                display_url = image_url

            seren_type = _ART_TYPE_MAP[art_type]
            entry = {
                "url": display_url,
                "language": _norm_lang(art.get("language")),
                "rating": art.get("score") or 0,
                "size": art.get("height") or art.get("score") or 0,
            }

            if seren_type not in result:
                result[seren_type] = []
            result[seren_type].append(entry)

        return result

    def _handle_cast_v4(self, characters):
        """Extract actor cast from v4 characters array."""
        if not characters:
            return []

        # Filter for Actors (type 3). Fall back to all characters if none found.
        actors = [c for c in characters if c.get("type") == 3]
        if not actors:
            actors = characters

        cast = []
        for item in actors:
            name = item.get("personName")  # v4 field is "personName", not "peopleName"
            if not name:
                continue
            cast.append(
                {
                    "name": name,
                    "role": item.get("name") or "",
                    "thumbnail": item.get("personImgURL"),
                    "order": item.get("sort") or 0,
                }
            )

        cast.sort(key=lambda x: x["order"])
        return cast

    # -------------------------------------------------------------------------
    # Public show-level methods
    # -------------------------------------------------------------------------

    @wrap_tvdb_object
    def get_show(self, tvdb_id):
        """Return full show metadata: info + artwork + cast."""
        raw = self._get_show_extended(tvdb_id)
        if not raw:
            return None

        result = {}

        show_data = self._preprocess_v4_show(raw)
        if show_data:
            info = self._normalize_info(self.show_normalization, show_data)
            if info:
                result["info"] = info

        art = self._extract_art_v4(raw)
        if art:
            result["art"] = art

        cast = self._handle_cast_v4(raw.get("characters") or [])
        if cast:
            result["cast"] = cast

        return result or None

    @wrap_tvdb_object
    def get_show_art(self, tvdb_id):
        """Return show artwork only (no info, no cast)."""
        raw = self._get_show_extended(tvdb_id)
        if not raw:
            return None

        art = self._extract_art_v4(raw)
        return {"art": art} if art else None

    @wrap_tvdb_object
    def get_show_info(self, tvdb_id):
        """Return show info + cast (no artwork)."""
        raw = self._get_show_extended(tvdb_id)
        if not raw:
            return None

        result = {}

        show_data = self._preprocess_v4_show(raw)
        if show_data:
            info = self._normalize_info(self.show_normalization, show_data)
            if info:
                result["info"] = info

        cast = self._handle_cast_v4(raw.get("characters") or [])
        if cast:
            result["cast"] = cast

        return result or None

    @wrap_tvdb_object
    def get_show_rating(self, tvdb_id):
        """
        TVDB v4 score is a popularity/favorites count, not a 0–10 star rating.
        rating.tvdb is not populated in v4; TMDb/Trakt supply show ratings instead.
        """
        return None

    @wrap_tvdb_object
    def get_show_cast(self, tvdb_id):
        """Return show cast only."""
        raw = self._get_show_extended(tvdb_id)
        if not raw:
            return None

        cast = self._handle_cast_v4(raw.get("characters") or [])
        return {"cast": cast} if cast else None

    @wrap_tvdb_object
    def get_season_art(self, tvdb_id, season):
        """Return poster artwork for a specific season number."""
        raw = self._get_show_extended(tvdb_id)
        if not raw:
            return None

        seasons = raw.get("seasons") or []
        artworks = raw.get("artworks") or []

        # Find season IDs for the requested season number in Aired Order (type.id == 1)
        target_season_ids = {
            s.get("id")
            for s in seasons
            if s.get("id") and s.get("number") == season and s.get("type", {}).get("id") == 1
        }

        if not target_season_ids:
            return None

        posters = []

        # Primary: artworks[] type 7 (SEASONPOSTER) matching this season
        for art in artworks:
            if art.get("type") == 7 and art.get("seasonId") in target_season_ids:
                image_url = art.get("image")
                if not image_url:
                    continue
                if self.preferred_artwork_size == 2 and art.get("thumbnail"):
                    image_url = art["thumbnail"]
                posters.append(
                    {
                        "url": image_url,
                        "language": _norm_lang(art.get("language")),
                        "rating": art.get("score") or 0,
                        "size": art.get("height") or art.get("score") or 0,
                    }
                )

        # Fallback: use seasons[].image if no type-7 artworks found
        if not posters:
            for s in seasons:
                if s.get("number") == season and s.get("type", {}).get("id") == 1:
                    if s.get("image"):
                        posters.append(
                            {
                                "url": s["image"],
                                "language": "eng",
                                "rating": 1,
                                "size": 1,
                            }
                        )
                        break

        if not posters:
            return None

        posters.sort(key=lambda k: (k["rating"], k["url"]), reverse=True)
        return {"art": {"poster": posters}}

    # -------------------------------------------------------------------------
    # Episode methods — Option B: episode data handled by TMDb/Trakt
    # -------------------------------------------------------------------------

    def get_episode(self, tvdb_id, season, episode):
        """Episode data is provided by TMDb/Trakt in this implementation."""
        return None

    def get_episode_rating(self, tvdb_id, season, episode):
        """Episode ratings are provided by TMDb/Trakt in this implementation."""
        return None
