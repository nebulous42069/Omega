from resources.lib.debrid.torbox import TorBox
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class TorBoxResolver(TorrentResolverBase):
    """
    Resolver for TorBox

    Pipeline: source with debrid_provider="torbox" arrives here via
    Resolver._resolve_debrid_source() → resolve_magnet() (base class) →
    _fetch_source_files() → base class file selection → resolve_stream_url()

    Handles both torrent (magnet) and usenet (NZB) sources.
    NZB sources are identified by the 'nzb_url' field set by _torbox_usenet_search().
    """

    def __init__(self):
        super().__init__()
        self.debrid_module = TorBox()
        # Maps TorBox file fields → Seren's normalized fields
        # TorBox files have: short_name, name, size (bytes), id
        self._source_normalization = (
            ("short_name", ["release_title", "path"], None),
            ("name", ["release_title", "path"], None),
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("id", "id", None),
            ("link", "link", None),
        )
        self.torrent_id = None
        self._is_usenet = False
        self._usenet_id = None

    def _fetch_source_files(self, torrent, item_information):
        """Fetch file list from TorBox for a given torrent or NZB.

        Called by base class resolve_magnet() → _movie_resolve() or _multi_pack_resolve().

        For torrents: adds magnet → retrieves file list → attaches composite link IDs.
        For NZB sources: adds NZB URL → retrieves file list → attaches usenet composite links.

        Returns list of file dicts that get normalized via _source_normalization."""
        from resources.lib.modules.exceptions import CloudMiss

        nzb_url = torrent.get("nzb_url")
        if nzb_url:
            return self._fetch_nzb_files(torrent, nzb_url)

        # Standard torrent path
        magnet_result = self.debrid_module.add_magnet(torrent["magnet"])
        if not magnet_result or "torrent_id" not in magnet_result:
            raise CloudMiss("torbox", torrent.get("hash", ""))

        self.torrent_id = magnet_result["torrent_id"]
        torrent_info = self.debrid_module.torrent_info(self.torrent_id)

        if not torrent_info or "files" not in torrent_info:
            self.debrid_module.delete_torrent(self.torrent_id)
            raise CloudMiss("torbox", torrent.get("hash", ""))

        # Attach composite link that resolve_stream_url() will parse
        files = torrent_info["files"]
        for f in files:
            f["link"] = f"{self.torrent_id},{f['id']}"

        return files

    def _fetch_nzb_files(self, torrent, nzb_url):
        """Fetch file list from TorBox for an NZB source.

        Pipeline: add_nzb(url) → poll usenet_info(id) → file list with usenet: composite links.
        Reference: POV torbox_api.py resolve_nzb()."""
        import xbmc
        from resources.lib.modules.exceptions import CloudMiss

        self._is_usenet = True
        nzb_result = self.debrid_module.add_nzb(nzb_url)

        if not nzb_result:
            raise CloudMiss("torbox", torrent.get("hash", ""))

        # add_nzb returns dict with 'usenetdownload_id' (or may already be processed)
        self._usenet_id = nzb_result.get(
            "usenetdownload_id", nzb_result.get("id")
        )
        if not self._usenet_id:
            raise CloudMiss("torbox", torrent.get("hash", ""))

        # Poll until TorBox has indexed the files (cached NZBs are usually instant,
        # uncached ones need time to download from usenet first).
        usenet_info = None
        for _ in range(30):
            xbmc.sleep(1000)
            info = self.debrid_module.usenet_info(self._usenet_id)
            if info and info.get("files"):
                usenet_info = info
                break
            state = (info or {}).get("download_state", "")
            if state in ("error", "failed"):
                break

        if not usenet_info:
            self.debrid_module.delete_usenet(self._usenet_id)
            raise CloudMiss("torbox", torrent.get("hash", ""))

        # Attach usenet-prefixed composite links so resolve_stream_url()
        # routes to the usenet endpoint
        files = usenet_info["files"]
        for f in files:
            f["link"] = f"usenet:{self._usenet_id},{f['id']}"

        return files

    def resolve_stream_url(self, file_info):
        """Get final playable URL from TorBox.

        Called by base class _finalize_resolving() after file identification.
        Handles four source types:
        - Torrent files: composite 'torrent_id,file_id' link → torrents/requestdl
        - Usenet (NZB): 'usenet:usenet_id,file_id' link → usenet/requestdl
        - WebDL cloud: 'webdl:webdl_id,file_id' link → webdl/requestdl
        - Hoster URLs: http(s) URL → webdl/createwebdownload → webdl/requestdl"""
        link = file_info.get("link")
        if not link:
            return None

        link = str(link)

        # Usenet link (from NZB search or cloud)
        if link.startswith("usenet:"):
            return self.debrid_module.resolve_usenet(link[7:])
        # WebDL cloud link
        if link.startswith("webdl:"):
            return self.debrid_module.resolve_webdl(link[6:])
        # Hoster URL (http/https)
        if link.startswith("http"):
            return self.debrid_module.resolve_hoster_url(link)
        # Default: torrent composite link (id,id)
        return self.debrid_module.resolve_hoster(link)

    def _do_post_processing(self, item_information, torrent, identified_file):
        """Handle post-resolve cleanup.

        Unified cascade matching RD/AD:
        - Failed resolution: always delete immediately
        - addtocloud enabled: keep permanently in cloud
        - smartdelete enabled: deferred cleanup via player (delete if fully watched, keep if stopped early)
        - autodelete enabled: delete immediately
        - none set: stays in cloud (user's explicit choice)

        Uses the correct delete method for NZB vs torrent sources."""
        cleanup_id = self._usenet_id if self._is_usenet else self.torrent_id
        delete_method = "delete_usenet" if self._is_usenet else "delete_torrent"
        delete_fn = getattr(self.debrid_module, delete_method)

        if cleanup_id:
            if identified_file is None:
                delete_fn(cleanup_id)
            elif g.get_bool_setting("torbox.addtocloud"):
                pass  # Keep permanently in cloud
            elif g.get_bool_setting("torbox.smartdelete"):
                from resources.lib.debrid.debrid_utils import store_pending_cleanup
                store_pending_cleanup("torbox", cleanup_id, delete_method)
            elif g.get_bool_setting("torbox.autodelete"):
                delete_fn(cleanup_id)
