from resources.lib.common.source_utils import get_best_episode_match
from resources.lib.debrid.real_debrid import RealDebrid
from resources.lib.modules.exceptions import FileIdentification
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class RealDebridResolver(TorrentResolverBase):
    """
    Resolver for Real Debrid
    """

    def __init__(self):
        super().__init__()
        self.debrid_module = RealDebrid()
        self.torrent_id = None
        self._source_normalization = (
            ("path", "path", None),
            ("bytes", "size", lambda k: (k / 1024) / 1024),
            ("size", "size", None),
            ("filename", "release_title", None),
            ("id", "id", None),
            ("link", "link", None),
            ("selected", "selected", None),
        )

    def _get_selected_files(self, torrent_info):
        files = [i for i in torrent_info["files"] if i["selected"]]
        links = torrent_info.get("links", [])
        if len(files) != len(links):
            g.log(
                f"RD link/file count mismatch: {len(files)} selected files vs {len(links)} links",
                "warning",
            )
        for idx, f in enumerate(files):
            if idx < len(links):
                f["link"] = links[idx]
            else:
                f["link"] = None
        return [f for f in files if f.get("link")]

    def _fetch_source_files(self, torrent, item_information):
        from resources.lib.modules.exceptions import CloudMiss
        hash_check = self.debrid_module.check_hash(torrent["hash"])
        if torrent["hash"] not in hash_check:
            g.log(
                f"RD check_hash returned no results for {torrent['hash']} — torrent not cached",
                "warning",
            )
            raise CloudMiss("real_debrid", torrent["hash"])
        result = hash_check[torrent["hash"]]
        self.torrent_id = result["torrent_id"]
        return self._get_selected_files(result["torrent_info"])

    def resolve_stream_url(self, file_info):
        """
        Convert provided source file into a link playable through debrid service
        :param file_info: Normalised information on source file
        :return: streamable link
        """
        return self.debrid_module.resolve_hoster(file_info["link"])

    def _do_post_processing(self, item_information, torrent, identified_file):
        if not self.torrent_id:
            return
        if identified_file is None:
            # Failed to identify file — always clean up
            self.debrid_module.delete_torrent(self.torrent_id)
        elif g.get_bool_setting("rd.addtocloud"):
            pass  # Keep permanently in cloud
        elif g.get_bool_setting("rd.smartdelete"):
            # Smart delete: defer cleanup to player — delete if fully watched, keep if stopped early
            from resources.lib.debrid.debrid_utils import store_pending_cleanup
            store_pending_cleanup("real_debrid", self.torrent_id, "delete_torrent")
        elif g.get_bool_setting("rd.autodelete"):
            # Autodelete: remove now that the stream link has been obtained
            self.debrid_module.delete_torrent(self.torrent_id)
