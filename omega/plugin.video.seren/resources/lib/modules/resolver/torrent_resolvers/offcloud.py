from resources.lib.debrid.offcloud import OffCloud
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import TorrentResolverBase


class OffCloudResolver(TorrentResolverBase):
    """
    Resolver for Offcloud

    Pipeline: source with debrid_provider="offcloud" arrives here via
    Resolver._resolve_debrid_source() → resolve_magnet() (base class) →
    _fetch_source_files() → base class file selection → resolve_stream_url()

    Offcloud cached files come from POST /api/cache/download which returns
    a list of {url, filename, size} directly — no persistent cloud ID is
    created on the cached path, so there is nothing to clean up after play.
    The addtocloud / smartdelete / autodelete settings apply only if
    uncached sources are stored via create_transfer() in future.
    """

    def __init__(self):
        super().__init__()
        self.debrid_module = OffCloud()
        self._source_normalization = (
            ("filename", ["release_title", "path"], None),
            ("size", "size", lambda k: (k / 1024) / 1024),
            ("url", "link", None),
        )

    def _fetch_source_files(self, torrent, item_information):
        """Fetch file list via POST /api/cache/download for a cached OC torrent."""
        from resources.lib.modules.exceptions import CloudMiss

        magnet = torrent.get("magnet") or f"magnet:?xt=urn:btih:{torrent['hash']}"
        files = self.debrid_module.resolve_cached_files(magnet)

        if not files:
            raise CloudMiss("offcloud", torrent.get("hash", ""))

        return files

    def resolve_stream_url(self, file_info):
        """Offcloud cache/download returns direct CDN URLs — no extra step needed."""
        return file_info.get("link")

    def _do_post_processing(self, item_information, torrent, identified_file):
        """No cloud ID to track for Offcloud cached plays (cache/download is stateless).

        If uncached resolution via create_transfer is added in future, track
        the requestId here and apply addtocloud / smartdelete / autodelete."""
        pass
