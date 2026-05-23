from difflib import SequenceMatcher

import xbmcgui

from resources.lib.common.source_utils import get_accepted_resolution_set, is_foreign_release, build_user_language_sets, get_undesirables, is_undesirable
from resources.lib.common.tools import FixedSortPositionObject
from resources.lib.modules.globals import g


class SourceSorter:
    """
    Handles sorting of sources according to users preferences
    """

    FIXED_SORT_POSITION_OBJECT = FixedSortPositionObject()

    def __init__(self, item_information):
        """
        Handles sorting of sources according to users preference
        """
        self.item_information = item_information
        self.mediatype = self.item_information['info']['mediatype']

        # Filter settings
        self.resolution_set = get_accepted_resolution_set()
        self.disable_dv = False
        self.disable_hdr = False
        self.filter_set = self._get_filters()

        # Undesirables keyword filter
        self.undesirables = get_undesirables()

        # Anime dub/sub filter (Otaku-style hard filter + sort boost)
        self._anime_dub_sub_pref = g.get_int_setting("anime.dubSubPreference", 0)
        self._anime_dub_sub_filter = False
        if self._anime_dub_sub_pref != 0:
            genres = self.item_information.get("info", {}).get("genre", [])
            if genres:
                genre_list = genres if isinstance(genres, list) else [genres]
                self._anime_dub_sub_filter = any(
                    'anime' in genre.lower() or 'animation' in genre.lower()
                    for genre in genre_list
                )

        # AniDB ID for per-anime UDP fansub group lookup
        self._anidb_id = self.item_information.get("info", {}).get("anidb_id")

        # Size filter settings
        self.enable_size_limit = g.get_int_setting("general.enablesizelimit")
        setting_mediatype = g.MEDIA_EPISODE if self.mediatype == g.MEDIA_EPISODE else g.MEDIA_MOVIE
        self.size_limit = g.get_int_setting(f"general.sizelimit.{setting_mediatype}") * 1024
        self.size_minimum = int(g.get_float_setting(f"general.sizeminimum.{setting_mediatype}") * 1024)
        self.speed_limit = g.get_float_setting("general.speedlimit", 10)
        self.speed_minimum = g.get_float_setting("general.speedminimum", 0)

        # Sort Settings
        self.quality_priorities = {"4K": 3, "1080p": 2, "720p": 1, "SD": 0}

        # Foreign language filter settings
        self.filter_foreign_audio = g.get_bool_setting("filter.foreign.audio")
        if self.filter_foreign_audio:
            info = self.item_information.get("info", {})
            self._foreign_content_title = info.get("tvshowtitle") or info.get("title", "")
            self._foreign_year = str(info.get("year", ""))
            self._foreign_country = (info.get("country_origin") or "").upper().strip()
            genres = info.get("genre", [])
            self._foreign_is_anime = any(
                x in genre.lower() for genre in (genres if isinstance(genres, list) else [genres]) for x in ("anime", "animation")
            ) if genres else False

            # Build user's preferred language sets from Kodi settings
            user_lang_codes = set()
            try:
                audio_lang = g.json_rpc(
                    "Settings.GetSettingValue", {"setting": "locale.audiolanguage"}
                ).get("value", "")
                if audio_lang and audio_lang not in ("original", "default", "mediadefault"):
                    code = g.convert_language_iso(audio_lang)
                    if code:
                        user_lang_codes.add(code)
            except Exception:
                pass
            try:
                sub_lang = g.get_kodi_preferred_subtitle_language(iso_format=True)
                if sub_lang and sub_lang not in ("original", "default", "forced_only", "none"):
                    user_lang_codes.add(sub_lang)
            except Exception:
                pass
            # Fallback: if no language could be determined, assume English
            if not user_lang_codes:
                user_lang_codes.add("en")
            self._user_indicators, self._user_countries = build_user_language_sets(user_lang_codes)

        # Sort Methods
        self._get_sort_methods()

    def _get_filters(self):
        filter_string = g.get_setting("general.filters")
        current_filters = set() if filter_string is None else set(filter_string.split(","))

        # Set HR filters and remove from set before returning due to HYBRID
        self.disable_dv = "DV" in current_filters
        self.disable_hdr = "HDR" in current_filters

        return current_filters.difference({"HDR", "DV"})

    def filter_sources(self, source_list):
        # Iterate sources, yielding only those that are not filtered
        if self.enable_size_limit == 1 :
            duration = self.item_information["info"]["duration"] or (5400 if self.mediatype == "movie" else 2400)
            max_size = self.speed_limit * 0.125 * duration * 0.9
            min_size = self.speed_minimum * 0.125 * duration * 0.9
            
        for source in source_list:
            # Undesirables keyword filter (early exit — cheap substring check)
            if self.undesirables and is_undesirable(source.get("release_title", ""), self.undesirables):
                continue
            # Quality filter
            if (
                source['quality'] not in self.resolution_set
                and all(quality not in self.resolution_set for quality in source['quality'].split('/'))
                and source['quality'] != "Unknown"
            ):
                continue
            # Info Filter
            if self.filter_set & source['info']:
                continue
            # DV filter
            if self.disable_dv and "DV" in source['info'] and "HYBRID" not in source['info']:
                continue
            # HDR Filter
            if self.disable_hdr and "HDR" in source['info'] and "HYBRID" not in source['info']:
                continue
            # Hybrid Filter
            if self.disable_dv and self.disable_hdr and "HYBRID" in source['info']:
                continue
            if self.enable_size_limit:
                size = source.get("size", 0)
                if self.enable_size_limit == 1 and (
                    (
                        isinstance(size, (int, float))
                        and not max_size >= float(size) >= min_size
                    )
                    or isinstance(size, str)
                    and size != "Variable"
                ):
                    continue
                elif self.enable_size_limit == 2 and (
                    (
                        isinstance(size, (int, float))
                        and not (self.size_minimum <= float(size) <= self.size_limit)
                    )
                    or isinstance(size, str)
                    and size != "Variable"
                ):
                    continue

            # Foreign language filter (smart context-aware)
            if self.filter_foreign_audio and is_foreign_release(
                source.get("release_title", ""),
                self._foreign_content_title,
                self._foreign_year,
                self._foreign_country,
                self._foreign_is_anime,
                source.get("info", set()),
                self._user_indicators,
                self._user_countries,
            ):
                continue

            # Anime dub/sub hard filter (Otaku-style: remove non-matching sources)
            if self._anime_dub_sub_filter:
                from resources.lib.modules.anime.dub_data import should_filter_source
                if should_filter_source(source, self._anime_dub_sub_pref):
                    continue

            # If not filtered, yield source
            yield source

    def sort_sources(self, sources_list):
        """Takes in a list of sources and filters and sorts them according to Seren's sort settings

        :param sources_list: list of sources
        :type sources_list: list
        :return: sorted list of sources
        :rtype: list
        """
        if not sources_list:
            return []

        filtered_sources = list(self.filter_sources(sources_list))
        if not filtered_sources:
            response = (
                None
                if g.get_bool_runtime_setting('tempSilent')
                else xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30474))
            )

            if response or g.get_bool_runtime_setting('tempSilent'):
                sorted_sources = self._sort_sources(sources_list)
            else:
                return []
        else:
            sorted_sources = self._sort_sources(filtered_sources)

        # Post-sort deduplication: collapse identical sources keeping the best-ranked
        if g.get_bool_setting("general.removeduplicates", True):
            before_count = len(sorted_sources)
            sorted_sources = self._deduplicate_sources(sorted_sources)
            removed = before_count - len(sorted_sources)
            if removed > 0:
                g.log(
                    f"Source dedup: Removed {removed} duplicate sources "
                    f"({before_count} → {len(sorted_sources)})",
                    "info",
                )

        return sorted_sources

    @staticmethod
    def _deduplicate_sources(sources):
        """
        Remove duplicate sources from the sorted list, keeping the first (best-ranked)
        occurrence of each unique source.

        Dedup rules:
        - Torrent/cached: same hash + same debrid_provider → duplicate
          (same hash on different debrid services = different playback paths, kept)
        - Hoster: same URL + same debrid_provider → duplicate
        - Cloud: same URL + same debrid_provider → duplicate
        - Direct/adaptive: same URL → duplicate

        Sources are already sorted by user preference, so keeping the first occurrence
        preserves the best-ranked version (longest name, best provider, etc.).
        """
        seen_torrent_keys = set()
        seen_url_keys = set()
        deduped = []

        for source in sources:
            source_type = source.get("type", "")

            if source_type == "torrent":
                # Dedup by hash + debrid_provider
                h = source.get("hash", "").lower()
                dp = source.get("debrid_provider", "")
                if h:
                    key = f"{h}_{dp}"
                    if key in seen_torrent_keys:
                        continue
                    seen_torrent_keys.add(key)

            elif source_type in ("hoster", "cloud"):
                # Dedup by URL + debrid_provider
                url = source.get("url", "").lower()
                dp = source.get("debrid_provider", "")
                if url:
                    key = f"{url}_{dp}"
                    if key in seen_url_keys:
                        continue
                    seen_url_keys.add(key)

            elif source_type in ("direct", "adaptive"):
                # Dedup by URL only
                url = source.get("url", "").lower()
                if url:
                    if url in seen_url_keys:
                        continue
                    seen_url_keys.add(url)

            deduped.append(source)

        return deduped

    def _get_sort_methods(self):
        """
        Get Seren settings for sort methods
        """
        sort_methods = []
        sort_method_settings = {
            0: None,
            1: self._get_quality_sort_key,
            2: self._get_type_sort_key,
            3: self._get_debrid_priority_key,
            4: self._get_size_sort_key,
            5: self._get_low_cam_sort_key,
            6: self._get_hevc_sort_key,
            7: self._get_hdr_sort_key,
            8: self._get_audio_channels_sort_key,
            9: self._get_seeders_sort_key,
        }

        if self.mediatype == g.MEDIA_EPISODE and g.get_bool_setting("general.lastreleasenamepriority"):
            self.last_release_name = g.get_runtime_setting(
                f"last_resolved_release_title.{self.item_information['info']['trakt_show_id']}"
            )
            if self.last_release_name:
                sort_methods.append((self._get_last_release_name_sort_key, False))

        for i in range(1, 9):
            sm = g.get_int_setting(f"general.sortmethod.{i}")
            reverse = g.get_bool_setting(f"general.sortmethod.{i}.reverse")

            if sort_method_settings[sm] is None:
                break

            if sort_method_settings[sm] == self._get_type_sort_key:
                self._get_type_sort_order()
            if sort_method_settings[sm] == self._get_debrid_priority_key:
                self._get_debrid_sort_order()
                reverse = False
            if sort_method_settings[sm] == self._get_hdr_sort_key:
                self._get_hdr_sort_order()

            sort_methods.append((sort_method_settings[sm], reverse))

        # Anime fansub version preference: auto-append as tiebreaker for anime content.
        # Prefers v2 over v1, v3 over v2, etc. — always desirable for anime.
        if g.get_bool_setting("anime.versionPreference", True):
            genres = self.item_information.get("info", {}).get("genre", [])
            if genres:
                genre_list = genres if isinstance(genres, list) else [genres]
                if any(
                    'anime' in genre.lower() or 'animation' in genre.lower()
                    for genre in genre_list
                ):
                    sort_methods.append((self._get_fansub_version_sort_key, False))

        # Anime dub/sub preference: sort boost based on user's dubbed/subbed preference.
        # Uses _anime_dub_sub_filter from __init__ (already checked anime genre + preference).
        if self._anime_dub_sub_filter:
            sort_methods.append((self._get_dub_sub_sort_key, False))

        # Package type preference for episodes: prefer single-episode sources over
        # season packs, and season packs over full show packs. Appended as a final
        # tiebreaker so that two 1080p cached sources are separated by specificity
        # rather than seed count — reducing content verifier friction and resolver
        # work on large multi-season torrents.
        if self.mediatype == g.MEDIA_EPISODE:
            sort_methods.append((self._get_package_sort_key, False))

        self.sort_methods = sort_methods

    def _get_type_sort_order(self):
        """
        Get seren settings for type sort priority
        """
        type_priorities = {}
        type_priority_settings = {
            0: None,
            1: "cloud",
            2: "adaptive",
            3: "torrent",
            4: "hoster",
            5: "direct",
        }

        for i in range(1, 6):
            tp = type_priority_settings.get(g.get_int_setting(f"general.sourcetypesort.{i}"))
            if tp is None:
                break
            type_priorities[tp] = -i
        self.type_priorities = type_priorities

    def _get_hdr_sort_order(self):
        """
        Get seren settings for type sort priority
        """
        hdr_priorities = {}
        hdr_priority_settings = {
            0: None,
            1: "DV",
            2: "HDR",
        }

        for i in range(1, 3):
            hdrp = hdr_priority_settings.get(g.get_int_setting(f"general.hdrsort.{i}"))
            if hdrp is None:
                break
            hdr_priorities[hdrp] = -i
        self.hdr_priorities = hdr_priorities

    def _get_debrid_sort_order(self):
        """
        Get seren settings for debrid sort priority
        """
        debrid_priorities = {}
        debrid_priority_settings = {
            0: None,
            1: "premiumize",
            2: "real_debrid",
            3: "all_debrid",
            4: "torbox",
            5: "debrid_link",
        }

        for i in range(1, 6):
            debridp = debrid_priority_settings.get(g.get_int_setting(f"general.debridsort.{i}"))
            if debridp is None:
                break
            debrid_priorities[debridp] = -i
        self.debrid_priorities = debrid_priorities

    def _sort_sources(self, sources_list):
        """
        Sort a source list based on sort_methods defined by settings
        All sort method key methods should return key values for *descending* sort.  If a reversed sort is required,
        reverse is specified as a boolean for the second item of each tuple in sort_methods
        :param sources_list: The list of sources to sort
        :return: The list of sorted sources
        :rtype: list
        """
        sources_list = sorted(sources_list, key=lambda s: s['release_title'])
        return sorted(sources_list, key=self._get_sort_key_tuple, reverse=True)

    def _get_sort_key_tuple(self, source):
        return tuple(-sm(source) if reverse else sm(source) for (sm, reverse) in self.sort_methods if sm)

    def _get_type_sort_key(self, source):
        return self.type_priorities.get(source.get("type"), -99)

    def _get_quality_sort_key(self, source):
        quality = source.get("quality")
        if quality is not None and '/' in quality:
            quality = quality.split('/')[0]
        return self.quality_priorities.get(quality, -99)

    def _get_debrid_priority_key(self, source):
        return self.debrid_priorities.get(source.get("debrid_provider"), self.FIXED_SORT_POSITION_OBJECT)

    def _get_size_sort_key(self, source):
        size = source.get("size", None)
        if size is None or not isinstance(size, (int, float)) or size < 0:
            size = 0
        return size

    @staticmethod
    def _get_low_cam_sort_key(source):
        return "CAM" not in source.get("info", {})

    @staticmethod
    def _get_hevc_sort_key(source):
        return "HEVC" in source.get("info", {})

    def _get_hdr_sort_key(self, source):
        hdrp = -99
        dvp = -99

        if "HDR" in source.get("info", {}):
            hdrp = self.hdr_priorities.get("HDR", -99)
        if "DV" in source.get("info", {}):
            dvp = self.hdr_priorities.get("DV", -99)

        return max(hdrp, dvp)

    def _get_last_release_name_sort_key(self, source):
        sm = SequenceMatcher(None, self.last_release_name, source['release_title'], autojunk=False)
        if sm.real_quick_ratio() < 1:
            return 0
        ratio = sm.ratio()
        return 0 if ratio < 0.85 else ratio

    @staticmethod
    def _get_audio_channels_sort_key(source):
        audio_channels = None
        if info := source['info']:
            audio_channels = {"2.0", "5.1", "7.1"} & info
        return float(max(audio_channels)) if audio_channels else 0

    @staticmethod
    def _get_seeders_sort_key(source):
        seeds = source.get("seeds", 0)
        if seeds is None or (isinstance(seeds, str) and not seeds.isdigit()):
            return 0
        return int(seeds)

    @staticmethod
    def _get_fansub_version_sort_key(source):
        """Prefer higher fansub versions (v2 > v1, v3 > v2).

        Only meaningful for anime content — injected automatically when
        anime.versionPreference is enabled.
        """
        from resources.lib.modules.anime.source_filter import parse_fansub_version
        return parse_fansub_version(source.get('release_title', ''))

    def _get_dub_sub_sort_key(self, source):
        """Prefer sources matching user's dub/sub preference.

        Uses info tags (DUAL-AUDIO, DUB, MULTI-SUB) and fansub group category
        to score each source.  Only injected for anime content when
        anime.dubSubPreference != 0.
        """
        from resources.lib.modules.anime.dub_data import get_dub_sub_sort_score
        return get_dub_sub_sort_score(source, self._anime_dub_sub_pref, anidb_id=self._anidb_id)

    @staticmethod
    def _get_package_sort_key(source):
        """Prefer more specific package types for episode resolution.

        single (3) > season (2) > show (1) > unknown (0)

        Appended as a tiebreaker for all episode sources so that a single-episode
        torrent sorts above a season pack, which sorts above a full show pack.
        This reduces content verifier friction and resolver work on large torrents.
        """
        return {'single': 3, 'season': 2, 'show': 1}.get(
            source.get('package', ''), 0
        )
