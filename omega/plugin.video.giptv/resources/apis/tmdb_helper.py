# Ensure this utility correctly handles requests/session setup
from resources.utils.giptv import make_session
from resources.lib.manager.fetch_manager import cache_handler
import resources.apis.xtream_api as xtream_api
from resources.utils.xtream import STATE

# --- Constants from the provided scraper code ---
TMDB_API_KEY = "f090bb54758cabf231fb605d3e3e0468"
TMDB_PARAMS = {"api_key": TMDB_API_KEY}
BASE_URL = "https://api.themoviedb.org/3/{}"
MOVIE_URL = BASE_URL.format("movie/{}")
TV_URL = BASE_URL.format("tv/{}")
session = make_session("https://api.themoviedb.org/3")


class TMDbHelper:
    def __init__(self):
        self.image_base_url = None
        self._get_config()

    def _get_config(self):
        try:
            self.image_base_url = "https://image.tmdb.org/t/p/original"
        except Exception:
            self.image_base_url = "https://image.tmdb.org/t/p/original"

    def get_movie_details(self, tmdb_id, language="en"):
        if not tmdb_id:
            return None

        cache_key = f"{STATE.username}_movie_{tmdb_id}"
        cached = cache_handler.get("tmdb_data", cache_key)
        if cached:
            return cached

        response_data = self.movie_details(tmdb_id, TMDB_API_KEY)
        if not response_data:
            return None

        plot = (
            response_data.get("overview")
            or response_data.get("tagline")
            or "No plot available."
        )
        fanart_path = response_data.get("backdrop_path")
        poster_path = response_data.get("poster_path")

        art = {}
        if poster_path and self.image_base_url:
            art["poster"] = f"{self.image_base_url}{poster_path}"
            art["thumb"] = art["poster"]

        if fanart_path and self.image_base_url:
            art["fanart"] = f"{self.image_base_url}{fanart_path}"

        data = {
            "title": response_data.get("title"),
            "plot": plot,
            "year": response_data.get("release_date", "")[:4],
            "rating": response_data.get("vote_average"),
            "art": art,
        }

        cache_handler.set("tmdb_data", cache_key, data)
        return data

    def get_series_details(self, tmdb_id, language="en"):
        if not tmdb_id:
            return None

        cache_key = f"{STATE.username}_series_{tmdb_id}"
        cached = cache_handler.get("tmdb_data", cache_key)
        if cached:
            return cached

        response_data = self.tvshow_details(tmdb_id, TMDB_API_KEY)
        if not response_data:
            return None

        plot = (
            response_data.get("overview")
            or response_data.get("tagline")
            or "No plot available."
        )
        fanart_path = response_data.get("backdrop_path")
        poster_path = response_data.get("poster_path")

        cast = []
        if "credits" in response_data and "cast" in response_data["credits"]:
            cast = [
                c.get("name")
                for c in response_data["credits"]["cast"][:5]
                if c.get("name")
            ]

        art = {}
        if poster_path and self.image_base_url:
            art["poster"] = f"{self.image_base_url}{poster_path}"
            art["thumb"] = art["poster"]

        if fanart_path and self.image_base_url:
            art["fanart"] = f"{self.image_base_url}{fanart_path}"

        genres = [
            g.get("name") for g in response_data.get("genres", []) if g.get("name")
        ]

        data = {
            "title": response_data.get("name"),
            "plot": plot,
            "year": response_data.get("first_air_date", "")[:4],
            "rating": response_data.get("vote_average"),
            "genre": ", ".join(genres),
            "cast": cast,
            "art": art,
        }

        cache_handler.set("tmdb_data", cache_key, data)
        return data

    def get_season_details(self, tmdb_id, season_num, language="en"):
        if not tmdb_id:
            return None

        cache_key = f"{STATE.username}_season_{tmdb_id}_{season_num}"
        cached = cache_handler.get("tmdb_data", cache_key)
        if cached:
            return cached

        try:
            url = (
                f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}"
                f"?api_key={TMDB_API_KEY}&language={language}&append_to_response=images"
            )
            data = self.get_tmdb(url).json()
            cache_handler.set("tmdb_data", cache_key, data)
            return data
        except Exception:
            return None

    def get_episode_details(self, tmdb_id, season_num, episode_num, language="en"):
        if not tmdb_id:
            return None

        cache_key = f"{STATE.username}_episode_{tmdb_id}_{season_num}_{episode_num}"
        cached = cache_handler.get("tmdb_data", cache_key)
        if cached:
            return cached

        try:
            url = (
                f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}/episode/{episode_num}"
                f"?api_key={TMDB_API_KEY}&language={language}&append_to_response=images,credits"
            )
            data = self.get_tmdb(url).json()
            cache_handler.set("tmdb_data", cache_key, data)
            return data
        except Exception:
            return None

    def get_tmdb(self, url):
        try:
            return session.get(url, timeout=20.0)
        except:
            return None

    def movie_details(self, tmdb_id, api_key):
        try:
            url = (
                "https://api.themoviedb.org/3/movie/%s?api_key=%s&language=en&append_to_response=external_ids,videos,credits,release_dates,alternative_titles,translations,"
                "images,keywords&include_image_language=en" % (tmdb_id, api_key)
            )
            return self.get_tmdb(url).json()
        except:
            return None

    def tvshow_details(self, tmdb_id, api_key):
        try:
            url = (
                "https://api.themoviedb.org/3/tv/%s?api_key=%s&language=en&append_to_response=external_ids,videos,credits,content_ratings,alternative_titles,translations,"
                "images,keywords&include_image_language=en" % (tmdb_id, api_key)
            )
            return self.get_tmdb(url).json()
        except:
            return None

    def season_episodes_details(self, tmdb_id, season_no, api_key):
        try:
            url = (
                "https://api.themoviedb.org/3/tv/%s/season/%s?api_key=%s&language=en&append_to_response=credits"
                % (tmdb_id, season_no, api_key)
            )
            return self.get_tmdb(url).json()
        except:
            return None
