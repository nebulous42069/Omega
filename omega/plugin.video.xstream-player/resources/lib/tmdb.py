# -*- coding: utf-8 -*-
import requests
import xbmc


class TMDB:
    BASE = "https://api.themoviedb.org/3"

    def __init__(self, api_key):
        self.api_key = api_key

    def _request(self, endpoint, params=None, log_prefix=""):
        """Make authenticated request to TMDB API with error handling."""
        if not self.api_key:
            return None
        url = f"{self.BASE}{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key
        try:
            resp = requests.get(url, params=params, timeout=10, allow_redirects=False)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            safe_error = (
                str(e).replace(self.api_key, "***REDACTED***")
                if self.api_key
                else str(e)
            )
            xbmc.log(
                f"[XStream Player] TMDB {log_prefix}error: {safe_error}",
                xbmc.LOGWARNING,
            )
            return None

    def search_movie(self, title):
        if not title:
            return None
        data = self._request(
            "/search/movie", {"query": title, "language": "en-US", "page": 1}, "search "
        )
        results = data.get("results", []) if data else []
        return results[0] if results else None

    def get_movie_details(self, tmdb_id):
        if not tmdb_id:
            return None
        return self._request(f"/movie/{tmdb_id}", {"language": "en-US"}, "details ")

    def get_movie_credits(self, tmdb_id):
        if not tmdb_id:
            return None
        return self._request(f"/movie/{tmdb_id}/credits", {}, "credits ")

    def search_tv(self, title):
        if not title:
            return None
        data = self._request(
            "/search/tv", {"query": title, "language": "en-US", "page": 1}, "TV search "
        )
        results = data.get("results", []) if data else []
        return results[0] if results else None

    def get_tv_details(self, tmdb_id):
        if not tmdb_id:
            return None
        return self._request(f"/tv/{tmdb_id}", {"language": "en-US"}, "TV details ")

    def get_tv_credits(self, tmdb_id):
        if not tmdb_id:
            return None
        return self._request(f"/tv/{tmdb_id}/credits", {}, "TV credits ")

    def enrich(self, title):
        return self._enrich(title, is_tv=False)

    def enrich_tv(self, title):
        return self._enrich(title, is_tv=True)

    def _enrich(self, title, is_tv=False):
        """Fetch and structure metadata for a movie or TV show."""
        result = {
            "plot": "",
            "poster_url": "",
            "rating": "",
            "year": "",
            "cast": [],
            "genre": "",
            "duration": 0,
        }
        if not self.api_key or not title:
            return result

        # Search and fetch details based on type
        if is_tv:
            search = self.search_tv(title)
            details = self.get_tv_details(search.get("id")) if search else None
            credits = self.get_tv_credits(search.get("id")) if search else None
            date_field = "first_air_date"
        else:
            search = self.search_movie(title)
            details = self.get_movie_details(search.get("id")) if search else None
            credits = self.get_movie_credits(search.get("id")) if search else None
            date_field = "release_date"

        if not search:
            return result

        if details:
            if is_tv:
                episode_run_time = details.get("episode_run_time", [])
                result["duration"] = int((episode_run_time[0] if episode_run_time else 0) or 0) * 60
            else:
                result["duration"] = int(details.get("runtime", 0) or 0) * 60

        src = details or search
        result["plot"] = src.get("overview") or ""
        result["rating"] = str(src.get("vote_average", ""))
        result["year"] = str(src.get(date_field, "")[:4]) if src.get(date_field) else ""

        # Parse genre
        genres = src.get("genres", [])
        if genres:
            result["genre"] = ", ".join([g.get("name", "") for g in genres[:3]])

        # Parse poster
        poster = src.get("poster_path") or search.get("poster_path")
        if poster:
            result["poster_url"] = f"https://image.tmdb.org/t/p/w500{poster}"

        # Parse cast
        if credits and credits.get("cast"):
            cast_list = []
            for actor in credits["cast"][:10]:  # Top 10 actors
                cast_list.append(
                    {
                        "name": actor.get("name", ""),
                        "role": actor.get("character", ""),
                        "thumbnail": f"https://image.tmdb.org/t/p/w185{actor.get('profile_path')}"
                        if actor.get("profile_path")
                        else "",
                    }
                )
            result["cast"] = cast_list

        return result
