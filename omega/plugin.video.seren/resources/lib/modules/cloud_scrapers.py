from resources.lib.common import source_utils
from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.debrid.debrid_link import DebridLink
from resources.lib.debrid.offcloud import OffCloud
from resources.lib.debrid.premiumize import Premiumize
from resources.lib.debrid.real_debrid import RealDebrid
from resources.lib.debrid.torbox import TorBox
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.globals import g


class CloudScraper(ApiBase):
    def __init__(self, terminate_check):
        self.terminate_check = terminate_check
        self.provider_name = self.__class__.__name__.split("Scraper")[0]
        self.api_adapter = None
        self.language = "en"
        self.media_type = ""
        self.item_information = {}
        self.simple_info = None
        self.debrid_provider = ""
        self.episode_regex = None
        self.season_regex = None
        self.show_regex = None
        self._source_normalization = ()
        self._file_normalization = ()

    def _build_regex(self):
        self.episode_regex = source_utils.get_filter_single_episode_fn(self.simple_info)
        self.show_regex = source_utils.get_filter_show_pack_fn(self.simple_info)
        self.season_regex = source_utils.get_filter_season_pack_fn(self.simple_info)

    def _generate_regex(self):
        self.regex = source_utils.get_filter_single_episode_fn(self.simple_info)

    def _preterm_check(self):
        if self.terminate_check():
            g.log(f"{self.__class__.__name__} Pre-Terminated", "info")
            return True
        return False

    def get_sources(self, item_information, simple_info=None):

        if not self._is_enabled():
            return []
        self.item_information = item_information
        self.media_type = self.item_information['info']['mediatype']

        if type(simple_info) == dict and "show_title" in simple_info:
            self.simple_info = simple_info
            self._build_regex()

        cloud_items = self._fetch_cloud_items()

        if type(cloud_items) != list:
            g.log(f"There was a faliure at the API level getting the cloud files from {self.debrid_provider}", "error")
            return []

        if self._preterm_check():
            return []
        cloud_items = [self._normalize_item(i) for i in cloud_items]
        if self._preterm_check():
            return []
        cloud_items = [i for i in cloud_items if self._is_valid_pack(i)]
        if self._preterm_check():
            return []
        cloud_items = self._identify_items(cloud_items)
        if self._preterm_check():
            return []
        cloud_items = [self._source_to_file(i) for i in cloud_items]
        cloud_items = [i for i in cloud_items if i]
        if self._preterm_check():
            return []
        cloud_items = self._apply_general_filter(cloud_items)
        if self._preterm_check():
            return []
        cloud_items = self._finalise_identified_items(cloud_items)
        g.log(f"{self.debrid_provider} cloud scraper found {len(cloud_items)} source", "info")
        return cloud_items

    def _normalize_item(self, item):
        return self._normalize_info(self._source_normalization, item)

    @staticmethod
    def _apply_general_filter(cloud_items):
        return [i for i in cloud_items if i['release_title'].endswith(g.common_video_extensions)]

    def _identify_items(self, cloud_items):
        sources = []

        if self.media_type == g.MEDIA_EPISODE:
            # Build a set of clean show title + alias strings that must be
            # present in the filename — without this guard, S01E01 of any
            # show can match S01E01 of a completely different show that
            # happens to be in the same cloud folder (e.g. Faraway Paladin
            # matching "I Reincarnated as the 7th Prince").
            show_title = source_utils.clean_title(
                self.item_information.get("info", {}).get("tvshowtitle", "")
                or self.item_information.get("info", {}).get("title", "")
            )
            alias_list = self.simple_info.get("show_aliases", []) if self.simple_info else []
            clean_aliases = {source_utils.clean_title(a) for a in alias_list if a}
            clean_aliases.add(show_title)
            clean_aliases.discard("")

            for item in cloud_items:
                release_title = source_utils.clean_title(item["release_title"])
                # Require that the show title or one of its aliases appears
                # in the filename before running the episode/pack regex.
                if clean_aliases and not any(a in release_title for a in clean_aliases if a):
                    continue
                if (
                    self.episode_regex(release_title)
                    or self.show_regex(release_title)
                    or self.season_regex(release_title)
                ):
                    sources.append(item)

        else:
            simple_info = {
                "year": self.item_information.get("info", {}).get("year"),
                "title": self.item_information.get("info").get("title"),
            }
            sources.extend(
                item
                for item in cloud_items
                if source_utils.filter_movie_title(
                    None,
                    source_utils.clean_title(item['release_title']),
                    self.item_information['info']['title'],
                    simple_info,
                )
            )

            return sources

        return sources

    def _source_to_file(self, source):
        return source

    def _fetch_cloud_items(self):
        """
        Calls the api adapter and returns the api response
        :return:
        """
        return []

    def _finalise_identified_items(self, items):
        for item in items:
            item.update(
                {
                    "quality": source_utils.get_quality(item['release_title']),
                    "language": self.language,
                    "provider": self.provider_name,
                    "type": "cloud",
                    "info": source_utils.get_info(item['release_title']),
                    "debrid_provider": self.debrid_provider,
                }
            )

        return items

    @staticmethod
    def _get_clean_title(item):
        return source_utils.clean_title(item.get("release_title", ""))

    def _is_valid_pack(self, item):
        clean_title = self._get_clean_title(item)
        if self.media_type == g.MEDIA_EPISODE:
            return bool(
                self.episode_regex(clean_title) or self.season_regex(clean_title) or self.show_regex(clean_title)
            )

        else:
            # Always return true on a movie item as packs do not count
            return True

    def _is_enabled(self):
        return False


class PremiumizeCloudScraper(CloudScraper, ApiBase):
    def __init__(self, terminate_flag):
        super().__init__(terminate_flag)
        self.api_adapter = Premiumize()
        self.debrid_provider = "premiumize"
        self._source_normalization = (
            ("name", "release_title", None),
            ("id", "url", None),
            ("size", "size", lambda k: (int(k) / 1024) / 1024),
        )

    def _fetch_cloud_items(self):
        return source_utils.filter_files_for_resolving(self.api_adapter.list_folder_all(), self.item_information)

    def _is_valid_pack(self, item):
        return True

    def _finalise_identified_items(self, items):
        items = super()._finalise_identified_items(items)
        for item in items:
            item["_cloud_delete_info"] = {
                "service": "premiumize",
                "method": "delete_item",
                "id": item.get("url", ""),
            }
        return items

    def _is_enabled(self):
        return g.premiumize_enabled()


class RealDebridCloudScraper(CloudScraper):
    def __init__(self, terminate_flag):
        super().__init__(terminate_flag)
        self.api_adapter = RealDebrid()
        self.debrid_provider = "real_debrid"
        self._source_normalization = (
            ("path", "release_title", lambda k: k.lower().split("/")[-1]),
            ("bytes", "size", lambda k: (k / 1024) / 1024),
            ("size", "size", None),
            ("filename", "release_title", None),
            ("id", "id", None),
            ("links", "links", None),
            ("selected", "selected", None),
        )

    def _fetch_cloud_items(self):
        from concurrent.futures import ThreadPoolExecutor

        items = []

        def _scrape_torrents():
            try:
                torrents = self.api_adapter.list_torrents()
                return torrents if isinstance(torrents, list) else []
            except Exception as e:
                g.log(f"RD torrent cloud scrape error: {e}", "warning")
                return []

        def _scrape_downloads():
            try:
                downloads = self.api_adapter.list_downloads()
                if not isinstance(downloads, list):
                    return []
                # Convert download items to a format matching torrent files
                results = []
                for dl in downloads:
                    if dl.get("download") and dl.get("filename"):
                        results.append({
                            "filename": dl["filename"],
                            "release_title": dl["filename"],
                            "size": dl.get("filesize", 0),
                            "bytes": dl.get("filesize", 0),
                            "links": [dl["download"]],
                            "id": dl.get("id", ""),
                            "url": dl["download"],
                            "_rd_type": "download",
                        })
                return results
            except Exception as e:
                g.log(f"RD downloads cloud scrape error: {e}", "warning")
                return []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_scrape_torrents),
                executor.submit(_scrape_downloads),
            ]
            for future in futures:
                try:
                    items.extend(future.result(timeout=15))
                except Exception as e:
                    g.log(f"RD cloud scrape thread error: {e}", "warning")

        return items

    def _source_to_file(self, source):
        if "links" not in source:
            return None
        torrent_info = self.api_adapter.torrent_info(source['id'])
        if not torrent_info or 'files' not in torrent_info:
            g.log(f"RD cloud scraper: torrent_info for {source['id']} missing 'files' key, skipping", "warning")
            return None
        source_files = self._normalize_item(torrent_info['files'])
        source_files = [i for i in source_files if i["selected"]]
        [file.update({"idx": idx}) for idx, file in enumerate(source_files)]
        source_files = self._identify_items(source_files)
        links = source['links']
        # Guard against RD link/file count mismatch — skip files whose idx falls
        # outside the links list rather than crashing with IndexError.
        source_files = [f for f in source_files if f['idx'] < len(links)]
        if not source_files:
            g.log(
                f"RD cloud scraper: no valid links for {source.get('id')} "
                f"({len(links)} links, all matched files out of range)",
                "warning",
            )
            return None
        [file.update({"url": links[file['idx']]}) for file in source_files]
        if source_files:
            file = source_files[0]
            rd_type = source.get("_rd_type", "torrent")
            file["_cloud_delete_info"] = {
                "service": "real_debrid",
                "method": "delete_torrent" if rd_type == "torrent" else "delete_download",
                "id": source.get("id", ""),
            }
            return file
        return None

    def _is_enabled(self):
        return g.real_debrid_enabled()


class AllDebridCloudScraper(CloudScraper):
    def __init__(self, terminate_flag):
        super().__init__(terminate_flag)
        self.api_adapter = AllDebrid()
        self.debrid_provider = "all_debrid"
        # _scrape_magnets returns pre-built dicts with: path, link, size (bytes),
        # filename, _ad_magnet_id, _ad_type.
        # _scrape_links returns raw AD link records with: filename, link, size.
        self._source_normalization = (
            ("size",     "size",                    lambda k: (k / 1024) / 1024),
            ("filename", ["release_title", "path"], None),
            ("link",     ["link", "url"],            None),
        )

    def _fetch_cloud_items(self):
        from concurrent.futures import ThreadPoolExecutor

        items = []

        def _scrape_magnets():
            try:
                # statusCode 4 = Ready (integer, more reliable than 'Ready' string)
                magnets = [
                    m for m in self.api_adapter.saved_magnets()
                    if m.get('statusCode') == 4
                ]
                results = []
                for magnet in magnets:
                    # Use 'files' + _flatten_files — not 'links'.
                    # 'links' is populated asynchronously by AD and is frequently
                    # empty even for ready magnets. 'files' is the nested file tree
                    # populated synchronously and is always present when ready.
                    raw_files  = magnet.get('files', [])
                    flat_files = self.api_adapter._flatten_files(raw_files)
                    for f in flat_files:
                        if not f.get('n') or not f.get('l'):
                            continue
                        results.append({
                            'path':         f['n'],
                            'link':         f['l'],
                            'size':         f.get('s', 0),
                            'filename':     f['n'],
                            '_ad_magnet_id': magnet.get('id'),
                            '_ad_type':     'magnet',
                        })
                return results
            except Exception as e:
                g.log(f"AD magnet cloud scrape error: {e}", "warning")
                return []

        def _scrape_links():
            try:
                saved = self.api_adapter.saved_links().get('links', [])
                for link in saved:
                    link['_ad_type'] = 'link'
                return saved
            except Exception as e:
                g.log(f"AD links cloud scrape error: {e}", "warning")
                return []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_scrape_magnets),
                executor.submit(_scrape_links),
            ]
            for future in futures:
                try:
                    items.extend(future.result(timeout=15))
                except Exception as e:
                    g.log(f"AD cloud scrape thread error: {e}", "warning")

        return items

    def _finalise_identified_items(self, items):
        items = super()._finalise_identified_items(items)
        for item in items:
            ad_type = item.get("_ad_type", "magnet")
            if ad_type == "magnet":
                item["_cloud_delete_info"] = {
                    "service": "all_debrid",
                    "method": "delete_magnet",
                    "id": item.get("_ad_magnet_id", ""),
                }
            else:
                item["_cloud_delete_info"] = {
                    "service": "all_debrid",
                    "method": "delete_link",
                    "id": item.get("link", item.get("url", "")),
                }
        return items

    def _is_valid_pack(self, item):
        return True

    def _is_enabled(self):
        return g.all_debrid_enabled()


class TorBoxCloudScraper(CloudScraper):
    def __init__(self, terminate_flag):
        super().__init__(terminate_flag)
        self.api_adapter = TorBox()
        self.debrid_provider = "torbox"
        self._source_normalization = (
            ("short_name", ["release_title", "path"], None),
            ("name", ["release_title", "path"], None),
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("id", "id", None),
            ("link", ["link", "url"], None),
        )

    def _fetch_cloud_items(self):
        from concurrent.futures import ThreadPoolExecutor
        items = []

        def _scrape_torrents():
            torrents = self.api_adapter.list_torrents()
            if not isinstance(torrents, list):
                return []
            completed = [t for t in torrents if t.get("download_finished") and t.get("files")]
            results = []
            for t in completed:
                for f in t.get("files", []):
                    f["link"] = f"{t['id']},{f['id']}"
                    f["_tb_type"] = "torrent"
                    results.append(f)
            return results

        def _scrape_usenet():
            try:
                usenet = self.api_adapter.list_usenet()
                if not isinstance(usenet, list):
                    return []
                completed = [u for u in usenet if u.get("download_finished") and u.get("files")]
                results = []
                for u in completed:
                    for f in u.get("files", []):
                        f["link"] = f"usenet:{u['id']},{f['id']}"
                        f["_tb_type"] = "usenet"
                        results.append(f)
                return results
            except Exception as e:
                g.log(f"TorBox usenet cloud scrape error: {e}", "warning")
                return []

        def _scrape_webdl():
            try:
                webdl = self.api_adapter.list_webdl()
                if not isinstance(webdl, list):
                    return []
                completed = [w for w in webdl if w.get("download_finished") and w.get("files")]
                results = []
                for w in completed:
                    for f in w.get("files", []):
                        f["link"] = f"webdl:{w['id']},{f['id']}"
                        f["_tb_type"] = "webdl"
                        results.append(f)
                return results
            except Exception as e:
                g.log(f"TorBox webdl cloud scrape error: {e}", "warning")
                return []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(_scrape_torrents),
                executor.submit(_scrape_usenet),
                executor.submit(_scrape_webdl),
            ]
            for future in futures:
                try:
                    items.extend(future.result(timeout=15))
                except Exception as e:
                    g.log(f"TorBox cloud scrape thread error: {e}", "warning")

        return items

    def _finalise_identified_items(self, items):
        items = super()._finalise_identified_items(items)
        for item in items:
            link = item.get("link", item.get("url", ""))
            # Extract parent ID from composite link: "torrent_id,file_id" or "usenet:id,fid" or "webdl:id,fid"
            link_str = str(link)
            if link_str.startswith("usenet:"):
                parent_id = link_str[7:].split(",")[0]
                delete_method = "delete_usenet"
            elif link_str.startswith("webdl:"):
                parent_id = link_str[6:].split(",")[0]
                delete_method = "delete_webdl"
            else:
                parent_id = link_str.split(",")[0]
                delete_method = "delete_torrent"
            item["_cloud_delete_info"] = {
                "service": "torbox",
                "method": delete_method,
                "id": parent_id,
            }
        return items

    def _is_valid_pack(self, item):
        return True

    def _is_enabled(self):
        return g.torbox_enabled()


class DebridLinkCloudScraper(CloudScraper):
    def __init__(self, terminate_flag):
        super().__init__(terminate_flag)
        self.api_adapter = DebridLink()
        self.debrid_provider = "debrid_link"
        self._source_normalization = (
            ("name", ["release_title", "path"], None),
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("id", "id", None),
            ("downloadUrl", ["link", "url"], None),
        )

    def _fetch_cloud_items(self):
        torrents = self.api_adapter.list_torrents()
        if not isinstance(torrents, list):
            return []
        # Side benefit (S168b): populate the session oracle from this
        # list_torrents() call so _debridlink_worker can consult the hash
        # set without triggering a second /v2/seedbox/list API round-trip.
        self.api_adapter._populate_oracle_from_list(torrents)
        results = []
        for t in torrents:
            if t.get("status") not in (100, "100", "downloaded"):
                # Debrid-Link uses status=100 for completed seedbox items
                # Also accept string representations and "downloaded"
                if not (isinstance(t.get("status"), (int, float)) and t["status"] >= 100):
                    continue
            for f in t.get("files", []):
                f["_dl_torrent_id"] = t.get("id")
                results.append(f)
        return results

    def _finalise_identified_items(self, items):
        items = super()._finalise_identified_items(items)
        for item in items:
            item["_cloud_delete_info"] = {
                "service": "debrid_link",
                "method": "delete_torrent",
                "id": item.get("_dl_torrent_id", ""),
            }
        return items

    def _is_valid_pack(self, item):
        return True

    def _is_enabled(self):
        return g.debridlink_enabled()


class OffCloudCloudScraper(CloudScraper):
    def __init__(self, terminate_flag):
        super().__init__(terminate_flag)
        self.api_adapter = OffCloud()
        self.debrid_provider = "offcloud"
        self._source_normalization = (
            ("filename", ["release_title", "path"], None),
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("url", ["link", "url"], None),
        )

    def _fetch_cloud_items(self):
        """Fetch completed cloud items from Offcloud history.

        GET /api/cloud/history → filter status='downloaded'
        GET /api/cloud/explore/{id}?format=detailed → files list
        """
        history = self.api_adapter.list_torrents()
        if not isinstance(history, list):
            return []
        results = []
        for item in history:
            if item.get("status") != "downloaded":
                continue
            request_id = item.get("requestId")
            if not request_id:
                continue
            info = self.api_adapter.torrent_info(request_id)
            files = []
            if isinstance(info, dict):
                files = info.get("files") or []
            elif isinstance(info, list):
                # plain URL list (non-detailed format) — wrap as dicts
                files = [{"url": u, "filename": u.split("/")[-1], "size": 0} for u in info if isinstance(u, str)]
            for f in files:
                f["_oc_request_id"] = request_id
                results.append(f)
        return results

    def _finalise_identified_items(self, items):
        items = super()._finalise_identified_items(items)
        for item in items:
            item["_cloud_delete_info"] = {
                "service": "offcloud",
                "method": "delete_torrent",
                "id": item.get("_oc_request_id", ""),
            }
        return items

    def _is_valid_pack(self, item):
        return True

    def _is_enabled(self):
        return g.offcloud_enabled()
