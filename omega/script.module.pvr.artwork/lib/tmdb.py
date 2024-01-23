import xbmcgui
from operator import itemgetter
from difflib import SequenceMatcher as SM
from .tools import *


class Tmdb(object):
    api_key = None

    def __init__(self):
        self.api_key = ADDON.getSetting('tmdb_apikey')

    def search_movie(self, title, year="", manual_select=False):
        """
            Search tmdb for a specific movie, returns full details of best match
            parameters:
            title: (required) the title of the movie to search for
            year: (optional) the year of the movie to search for (enhances search result if supplied)
            manual_select: (optional) if True will show select dialog with all results
        """
        details = self.select_best_match(self.search_movies(title, year), manual_select=manual_select)
        if details:
            details = self.get_movie_details(details["id"])
        return details

    def search_movieset(self, title):
        """
            search for movieset details providing the title of the set
        """
        details = {}
        params = {"query": title, "language": LANGUAGE}
        result = self.get_tmdb_data("search/collection", params)
        if result:
            set_id = result[0]["id"]
            details = self.get_movieset_details(set_id)
        return details

    def search_movies(self, title, year=""):
        """
            Search tmdb for a specific movie, returns a list of all closest matches
            parameters:
            title: (required) the title of the movie to search for
            year: (optional) the year of the movie to search for (enhances search result if supplied)
        """
        params = {"query": title, "language": LANGUAGE}
        if year:
            params["year"] = parse_int(year)
        return self.get_tmdb_data("search/movie", params)

    def search_tvshow(self, title, year="", manual_select=False):
        """
            Search tmdb for a specific movie, returns full details of best match
            parameters:
            title: (required) the title of the movie to search for
            year: (optional) the year of the movie to search for (enhances search result if supplied)
            manual_select: (optional) if True will show select dialog with all results
        """
        details = self.select_best_match(self.search_tvshows(title, year), manual_select=manual_select)
        if details:
            details = self.get_tvshow_details(details["id"])
        return details

    def search_video(self, title, prefyear="", preftype="", manual_select=False):
        """
            Search tmdb for a specific entry (can be movie or tvshow), returns full details of best match
            parameters:
            title: (required) the title of the movie/tvshow to search for
            prefyear: (optional) prefer result if year matches
            preftype: (optional) prefer result if type matches
            manual_select: (optional) if True will show select dialog with all results
        """
        results = self.search_videos(title)
        details = self.select_best_match(results, prefyear=prefyear, preftype=preftype,
                                         preftitle=title, manual_select=manual_select)

        if details and details["media_type"] == "movie":
            details = self.get_movie_details(details["id"])
        elif details and "tv" in details["media_type"]:
            details = self.get_tvshow_details(details["id"])
        return details

    def search_videos(self, title):
        """
            Search tmdb for a specific entry (can be movie or tvshow), parameters:
            title: (required) the title of the movie/tvshow to search for
        """
        results = list()
        page = 1
        maxpages = 5
        while page < maxpages:
            params = {"query": title, "language": LANGUAGE, "page": page}
            subresults = self.get_tmdb_data("search/multi", params)
            page += 1
            if subresults:
                for item in subresults:
                    if item["media_type"] in ["movie", "tv"]: results.append(item)
            else:
                break
        return results

    def search_tvshows(self, title, year=""):
        """
            Search tmdb for a specific tvshow, returns a list of all closest matches
            parameters:
            title: (required) the title of the tvshow to search for
            year: (optional) the first air date year of the tvshow to search for (enhances search result if supplied)
        """
        params = {"query": title, "language": LANGUAGE}
        if year:
            params["first_air_date_year"] = parse_int(year)
        return self.get_tmdb_data("search/tv", params)

    def get_movie_details(self, movie_id):
        """
            get all moviedetails
        """
        params = {
            "append_to_response": "external_ids,credits,images",
            "include_image_language": "%s,en" % LANGUAGE,
            "language": LANGUAGE
        }
        log('Get movie details')
        data = self.get_tmdb_data("movie/%s" % movie_id, params)
        return self.map_details(data, "movie")

    def get_movieset_details(self, movieset_id):
        """
            get all moviesetdetails
        """
        details = {"art": {}}
        params = {"language": LANGUAGE}
        result = self.get_tmdb_data("collection/%s" % movieset_id, params)
        if result:
            details.update({'title': result['name'], 'plot': result['overview'], 'tmdb_id': result['id'],
                           'art': {'poster': 'https://image.tmdb.org/t/p/original%s' % result['poster_path'],
                                   'fanart': 'https://image.tmdb.org/t/p/original%s' % result['backdrop_path']},
                            'totalmovies': len(result['parts'])})
        return details

    def get_tvshow_details(self, tvshow_id):
        """
            get all tvshowdetails
        """
        params = {
            "append_to_response": "external_ids,credits,images",
            "include_image_language": "%s,en" % LANGUAGE,
            "language": LANGUAGE
        }
        log('Get tvshow details of id %s' % tvshow_id)
        data = self.get_tmdb_data('tv/%s' % tvshow_id, params)
        return self.map_details(data, "tvshow")

    def get_videodetails_by_externalid(self, extid, extid_type):
        """
            get metadata by external ID (like imdbid)
        """
        params = {"external_source": extid_type, "language": LANGUAGE}
        results = self.get_tmdb_data("find/%s" % extid, params)
        if results and results["movie_results"]:
            return self.get_movie_details(results["movie_results"][0]["id"])
        elif results and results["tv_results"]:
            return self.get_tvshow_details(results["tv_results"][0]["id"])
        return {}

    def get_tmdb_data(self, endpoint, params):
        """
            helper method to get data from tmdb json API
        """
        url = u'https://api.themoviedb.org/3/%s' % endpoint

        if self.api_key:
            # addon provided or personal api key
            params.update({'api_key': self.api_key})

        return get_json(url, params, prefix='results')

    def map_details(self, data, media_type):
        """helper method to map the details received from tmdb to kodi compatible formatting"""
        if not data:
            return {}
        details = {"tmdb_id": data["id"], 'tvdb_id': data['external_ids'].get('tvdb_id', None),
                   "ratings": {'tmdb': {'rating': data["vote_average"], 'votes': data["vote_count"]}},
                   "popularity": data["popularity"] * 1000, "popularity.tmdb": data["popularity"] * 1000,
                   "genre": [item["name"] for item in data["genres"]],
                   "country": [item['name'] for item in data["production_countries"]], "status": data["status"],
                   "cast": [], "writer": [], "studio": [item['name'] for item in data["production_companies"]],
                   "director": [], "production": data["production_companies"], "media_type": media_type}

        if media_type == 'tvshow': details.update({'description': data['overview']})
        if "release_date" in data: details.update({"released": data['release_date']})

        # cast
        if "credits" in data:
            if "cast" in data["credits"]:
                for cast in data["credits"]["cast"]:
                    thumb = "https://image.tmdb.org/t/p/original%s" % cast["profile_path"] if cast['profile_path'] else ''
                    details['cast'].append({'name': cast['name'], 'role': cast['character'], 'thumbnail': thumb})

            # crew (including writers and directors)
            if "crew" in data["credits"]:
                for crew in data["credits"]["crew"]:
                    if crew["job"] in ["Author", "Writer"]: details['writer'].append(crew['name'])
                    if crew["job"] in ["Producer", "Executive Producer"]: details['director'].append(crew['name'])

        # artwork
        if data.get("images", False):
            artwork = dict()
            if data["images"].get("backdrops", False):
                fanarts = self.get_best_images(data['images']['backdrops'])
                artwork.update({'fanart': fanarts[0]})
                artwork.update({'fanarts': fanarts[1:]})

            if data["images"].get("posters", False):
                posters = self.get_best_images(data["images"]["posters"])
                artwork.update({'poster': posters[0]})
                artwork.update({'posters': posters[1:]})
            else:
                # get poster_path preview poster
                if data.get('poster_path', False):
                    artwork.update({'poster': "https://image.tmdb.org/t/p/original%s" % data['poster_path']})

            if data["images"].get('logos', False):
                logos = self.get_best_images(data['images']['logos'], size='w500')
                artwork.update({'clearlogo': logos[0]})
            details.update({'art': artwork})
        return details

    @staticmethod
    def get_best_images(images, size='original'):
        """get the best 5 images based on number of likes and the language"""
        for image in images:
            score = 0
            score += image["vote_count"]
            score += image["vote_average"] * 10
            score += image["height"]
            if "iso_639_1" in image:
                if image["iso_639_1"] == LANGUAGE:
                    score += 1000
            image["score"] = score
            if not image["file_path"].startswith("https"):
                image["file_path"] = "https://image.tmdb.org/t/p/%s%s" % (size, image["file_path"])
        images = sorted(images, key=itemgetter("score"), reverse=True)
        return [image["file_path"] for image in images]

    @staticmethod
    def select_best_match(results, prefyear="", preftype="", preftitle="", manual_select=False):
        """
            helper to select best match or let the user manually select the best result from the search
        """
        details = dict()
        # score results if one or more preferences are given
        if results and (prefyear or preftype or preftitle):
            newdata = list()
            preftitle = preftitle.lower()
            for item in results:
                item["score"] = 0
                item_title = item.get('title', item.get('name', '')).lower()
                item_orgtitle = item.get('original_title', item.get('original_name', '')).lower()

                # high score if year matches
                if prefyear:
                    if item.get("first_air_date") and prefyear in item["first_air_date"]: item["score"] += 800  # matches preferred year
                    if item.get("release_date") and prefyear in item["release_date"]: item["score"] += 800  # matches preferred year

                # find exact match on title
                if preftitle and preftitle == item_title: item["score"] += 1000  # exact match!
                if preftitle and preftitle == item_orgtitle: item["score"] += 1000  # exact match!

                # match title by replacing some characters
                if preftitle and get_compare_string(preftitle) == get_compare_string(item_title): item["score"] += 750
                if preftitle and get_compare_string(preftitle) == get_compare_string(item_orgtitle): item["score"] += 750

                # add SequenceMatcher score to the results
                if preftitle:
                    stringmatchscore = SM(None, preftitle, item_title).ratio() + SM(None, preftitle, item_orgtitle).ratio()
                    if stringmatchscore > 1.6: item["score"] += stringmatchscore * 250

                # higher score if result ALSO matches our preferred type or native language
                # (only when we already have a score)
                if item["score"]:
                    if preftype and (item["media_type"] in preftype) or (preftype in item["media_type"]): item["score"] += 250  # matches preferred type
                    if item["original_language"] == LANGUAGE: item["score"] += 500  # native language!
                    if LANGUAGE.upper() in item.get("origin_country", []): item["score"] += 500  # native language!
                    if LANGUAGE in item.get("languages", []): item["score"] += 500  # native language!

                if item["score"] > 500 or manual_select: newdata.append(item)
            results = sorted(newdata, key=itemgetter("score"), reverse=True)

        if results and manual_select:

            # show selectdialog to manually select the item
            liz = list()
            for item in results:
                title = item.get('name', item.get('title', ''))
                year = item.get('release_date', item.get('first_air_date', '')).split('-')[0]
                if year: year = '(%s)' % year
                if item["poster_path"]:
                    icon = "https://image.tmdb.org/t/p/original%s" % item["poster_path"]
                else:
                    icon = ""
                label = "%s %s - %s" % (title, year, item["media_type"])
                listitem = xbmcgui.ListItem(label=label, label2=item["overview"])
                listitem.setArt({'icon': icon})
                liz.append(listitem)

            if manual_select and liz:
                dialog = xbmcgui.Dialog().select('%s - TMDB' % xbmc.getLocalizedString(283), list=liz, useDetails=True)
                if dialog > -1:
                    details = results[dialog]
                else:
                    results = []

        if not details and results:
            # just grab the first item as best match
            details = results[0]
        return details
