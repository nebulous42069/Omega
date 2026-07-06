import abc

import xbmcgui

from resources.lib.common import source_utils
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.exceptions import FileIdentification, InfringingFile
from resources.lib.modules.globals import g

# Maps debrid_provider source field to DebridCache DB service key.
# Imported here to avoid circular imports — same mapping as in resolver/__init__.py.
_DEBRID_PROVIDER_TO_DB_KEY = {
    'real_debrid': 'rd', 'all_debrid': 'ad', 'premiumize': 'pm',
    'torbox': 'tb', 'debrid_link': 'dl', 'offcloud': 'oc',
}


class TorrentResolverBase(ApiBase):
    """
    Base Class to resolve torrent from debrid provider
    Extend appropriate debrid torrent resolver with this class
    """

    def __init__(self):
        super().__init__()
        self.pack_select = False
        self.debrid_module = None
        self._source_normalization = None
        self.media_type = None
        self.item_information = None

    def resolve_magnet(self, item_information, torrent, pack_select=False):
        """
        Resolves torrent information into a playable stream link
        :param item_information: Dictionary of show/movies meta
        :param torrent: torrent information identified
        :param pack_select: allows manual selection of file within torrent
        :return:
        """
        self.item_information = item_information
        self.pack_select = pack_select
        if "tvshowtitle" not in item_information["info"]:
            self.media_type = "movie"
            return self._movie_resolve(item_information, torrent)
        else:
            self.media_type = "episode"
            return self._multi_pack_resolve(item_information, torrent)

    @abc.abstractmethod
    def _fetch_source_files(self, torrent, item_information):
        """
        Fetches files from debrid service
        :param torrent: source dictionary
        :return: list - normalized list of files
        """

    def _normalize_item(self, item):
        return self._normalize_info(self._source_normalization, item) if self._source_normalization else item

    @abc.abstractmethod
    def resolve_stream_url(self, file_info):
        """
        Makes final connection to debrid provider for the streamable link
        :param file_info: dict - normalized information for file
        :return: string - Streamable URL
        """

    @abc.abstractmethod
    def _do_post_processing(self, item_information, torrent, identified_file):
        """
        Perform any required processing after the resolving of the file or if a file could not be identified
        :param item_information: The item information
        :param torrent: The torrent information
        :param identified_file: The file that was identified or None if no file was identified in the torrent
        :return:
        """

    @staticmethod
    def _filter_non_playable_files(folder_details):
        return [i for i in folder_details if source_utils.is_file_ext_valid(i["path"])]

    def _user_selection(self, folder_details):
        folder_details = self._filter_non_playable_files(folder_details)
        folder_details = sorted(folder_details, key=lambda k: k['path'].split("/")[-1])
        selection = xbmcgui.Dialog().select(
            g.get_language_string(30483), [i['path'].split('/')[-1] for i in folder_details]
        )
        return folder_details[selection] if selection >= 0 else None

    def _finalize_resolving(self, item_information, torrent, identified_file, folder_details):
        if identified_file is None:
            self._do_post_processing(item_information, torrent, identified_file)
            # If resolving an episode and no matching file was found in the torrent,
            # write cached=False to the DB so the next scrape cycle doesn't restore
            # this hash as confirmed-cached and attempt it again silently.
            # Guard: skip when pack_select=True (user cancelled manual selection —
            # the torrent itself is fine) and skip for movies (different failure modes).
            if self.media_type == "episode" and not self.pack_select:
                db_key = _DEBRID_PROVIDER_TO_DB_KEY.get(torrent.get('debrid_provider', ''))
                if db_key and torrent.get('hash'):
                    g.log(
                        f"Episode file not found in torrent — invalidating DB cache: "
                        f"{torrent.get('debrid_provider')} / {torrent.get('hash', '')[:8]}... "
                        f"({torrent.get('release_title', 'N/A')})",
                        "warning",
                    )
                    try:
                        from resources.lib.database.debridCache import DebridCache
                        DebridCache().set_many_background(
                            [(torrent['hash'], 'False')], db_key
                        )
                    except Exception:
                        pass
            return None
        try:
            stream_link = self.resolve_stream_url(identified_file)
        except InfringingFile:
            # RD HTTP 451 / error_code=35: file is legally blocked (DMCA).
            # Write a 7-day False entry to DebridCache so this hash is suppressed
            # on all future scrape sessions without re-hitting the API.
            db_key = _DEBRID_PROVIDER_TO_DB_KEY.get(torrent.get('debrid_provider', ''))
            if db_key and torrent.get('hash'):
                try:
                    from resources.lib.database.debridCache import DebridCache
                    DebridCache().set_infringing([torrent['hash']], db_key)
                except Exception:
                    pass
            # Pass None to force torrent cleanup — player never starts for a blocked file
            self._do_post_processing(item_information, torrent, None)
            return None
        self._do_post_processing(item_information, torrent, identified_file)
        if not stream_link:
            raise FileIdentification([i["path"] for i in folder_details])
        return stream_link

    def _sort_and_filter_files(self, folder_details, item_information, sort=False):
        filtered_files = self._filter_non_playable_files(
            source_utils.filter_files_for_resolving(folder_details, item_information)
        )

        if sort:
            filtered_files = sorted(filtered_files, key=lambda i: int(i["size"]), reverse=True)
        return filtered_files

    def _multi_pack_resolve(self, item_information, torrent):
        folder_details = self._normalize_item(self._fetch_source_files(torrent, item_information))
        if self.pack_select:
            return self._finalize_resolving(
                item_information,
                torrent,
                self._user_selection(folder_details),
                folder_details,
            )
        folder_details = self._sort_and_filter_files(folder_details, item_information)

        # ── Single-file shortcut (mirrors Otaku's resolver behaviour) ───────
        # If after filtering only one playable file remains, use it directly
        # without running the episode regex.  This is the correct behaviour for
        # single-episode fansub releases (SubsPlease, Erai-raws, etc.) which
        # land as one .mkv inside the torrent — their filenames use "- 09"
        # style that the SxxExx regex never matches, causing a false
        # "episode file not found" failure even though the file is right there.
        # Otaku does exactly this: `if len(torrent_info['files']) == 1: best_match = torrent_files[0]`
        if len(folder_details) == 1:
            return self._finalize_resolving(item_information, torrent, folder_details[0], folder_details)

        best_match = source_utils.get_best_episode_match("path", folder_details, item_information)
        return self._finalize_resolving(item_information, torrent, best_match, folder_details)

    @staticmethod
    def _try_m2ts_resolving(folder_details):
        if any(i['path'].endswith(".m2ts") for i in folder_details):
            return sorted(folder_details, key=lambda s: s['size'], reverse=True)[0]

    def _movie_resolve(self, item_information, torrent):
        simple_info = {
            "year": item_information.get("info", {}).get("year"),
            "title": item_information.get("info").get("title"),
        }

        folder_details = self._sort_and_filter_files(
            self._normalize_item(self._fetch_source_files(torrent, item_information)), item_information, True
        )

        if self.pack_select:
            return self._finalize_resolving(
                item_information,
                torrent,
                self._user_selection(folder_details),
                folder_details,
            )

        if m2ts_check := self._try_m2ts_resolving(folder_details):
            return self._finalize_resolving(item_information, torrent, m2ts_check, [m2ts_check])

        if len(folder_details) == 1:
            return self._finalize_resolving(item_information, torrent, folder_details[0], folder_details)

        folder_details = source_utils.filter_files_for_resolving(folder_details, item_information)
        filter_list = [
            i
            for i in folder_details
            if source_utils.filter_movie_title(
                None,
                i["path"].split("/")[-1],
                item_information["info"]["originaltitle"],
                simple_info,
            )
        ]
        if len(filter_list) == 1:
            return self._finalize_resolving(item_information, torrent, filter_list[0], folder_details)

        raise FileIdentification([i["path"] for i in folder_details])
