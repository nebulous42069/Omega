from resources.lib.debrid.debrid_link import DebridLink
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class DebridLinkResolver(TorrentResolverBase):
    """
    Resolver for Debrid-Link

    Pipeline: source with debrid_provider="debrid_link" arrives here via
    Resolver._resolve_debrid_source() → resolve_magnet() (base class) →
    _fetch_source_files() → base class file selection → resolve_stream_url()

    Debrid-Link seedbox files have: name, size, downloadUrl
    """

    def __init__(self):
        super().__init__()
        self.debrid_module = DebridLink()
        self._source_normalization = (
            ("name", ["release_title", "path"], None),
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("id", "id", None),
            ("downloadUrl", "link", None),
        )
        self.torrent_id = None

    def _fetch_source_files(self, torrent, item_information):
        """Fetch file list from Debrid-Link for a given torrent.

        Adds magnet to seedbox synchronously (async=false) so the files list is
        populated immediately in the response. The async=true path (used by
        cacheAssist) returns files=[] and would always raise CloudMiss here."""
        from resources.lib.modules.exceptions import CloudMiss

        magnet_result = self.debrid_module.add_magnet_sync(torrent["magnet"])
        if not magnet_result or "id" not in magnet_result:
            raise CloudMiss("debrid_link", torrent.get("hash", ""))

        self.torrent_id = magnet_result["id"]
        files = magnet_result.get("files", [])

        if not files:
            self.debrid_module.delete_torrent(self.torrent_id)
            raise CloudMiss("debrid_link", torrent.get("hash", ""))

        return files

    def resolve_stream_url(self, file_info):
        """Get final playable URL from Debrid-Link.

        Debrid-Link files already contain direct downloadUrl from the seedbox,
        so no additional resolution step is needed."""
        link = file_info.get("link")
        if not link:
            return None
        return link

    def _do_post_processing(self, item_information, torrent, identified_file):
        """Handle post-resolve cleanup.

        Unified cascade matching RD/AD/TB:
        - Failed resolution: always delete immediately
        - addtocloud enabled: keep permanently in cloud
        - smartdelete enabled: deferred cleanup via player
        - autodelete enabled: delete immediately
        - none set: stays in cloud

        Probe cleanup:
        When the user plays a cached probe source, every OTHER probe-cached
        torrent ID (the ones the user didn't pick) is deleted immediately in
        the background here.  debridlink.probe_ids is then cleared so that the
        router.py cleanup hook finds nothing and exits early — mirroring the
        AD MagnetUpload pattern.  If resolution fails, probe IDs are left for
        the router hook to delete at source-select close."""
        if self.torrent_id:
            if identified_file is None:
                self.debrid_module.delete_torrent(self.torrent_id)
            else:
                # ── Delete unplayed probe-cached IDs ─────────────────────────
                # The probe may have added up to _DL_PROBE_MAX magnets and
                # stored the cached IDs in the runtime setting.  Now that the
                # user has picked a source, only the played torrent is kept;
                # all others are removed from the user's seedbox immediately.
                _probe_ids = g.get_runtime_setting("debridlink.probe_ids")
                if _probe_ids and isinstance(_probe_ids, list):
                    _others = [pid for pid in _probe_ids if pid != self.torrent_id]
                    if _others:
                        self.debrid_module.delete_torrents_background(_others)
                        g.log(
                            f"DL SeedboxProbe: play resolved — deleting "
                            f"{len(_others)} unplayed cached probe torrent(s)",
                            "info",
                        )
                    g.clear_runtime_setting("debridlink.probe_ids")

                # ── Handle the played torrent ─────────────────────────────────
                if g.get_bool_setting("debridlink.addtocloud"):
                    pass
                elif g.get_bool_setting("debridlink.smartdelete"):
                    from resources.lib.debrid.debrid_utils import store_pending_cleanup
                    store_pending_cleanup("debrid_link", self.torrent_id, "delete_torrent")
                elif g.get_bool_setting("debridlink.autodelete"):
                    self.debrid_module.delete_torrent(self.torrent_id)
