from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class AllDebridResolver(TorrentResolverBase):
    """
    Resolver for All Debrid
    """

    def __init__(self):
        super().__init__()
        self.debrid_module = AllDebrid()
        # Files are pre-normalised in _fetch_source_files; base_resolver's
        # normalization step is skipped.
        self._source_normalization = None
        self.magnet_id = None

    def _fetch_source_files(self, torrent, item_information):
        """
        Upload the selected magnet to AD and return its flat file list.

        Sequence (mirrors POV's parse_magnet_pack exactly):
          1. Upload full magnet URI → creates ONE transfer in AD account
          2. Poll magnet/status up to 5x with 500ms sleep (2.5s max)
          3. Check completionDate truthy — reliable across API versions
          4. Flatten status['files'] nested tree (not async 'links' field)
          5. On any failure: delete the transfer, raise CloudMiss

        :raises CloudMiss: if upload fails, not ready within 2.5s, or no files
        """
        import xbmc
        from resources.lib.modules.exceptions import CloudMiss

        # Prefer full magnet URI — dn= and tr= fields help AD resolve faster.
        # Bare hash is a valid fallback for older source dicts.
        magnet_uri = torrent.get('magnet') or torrent.get('hash', '')
        if not magnet_uri:
            raise CloudMiss("all_debrid", torrent.get("hash", ""))

        # Step 1: Upload — creates one transfer entry in user's AD account
        upload_result = self.debrid_module.upload_magnet(magnet_uri)
        if not upload_result or "magnets" not in upload_result:
            raise CloudMiss("all_debrid", torrent.get("hash", ""))

        try:
            self.magnet_id = upload_result["magnets"][0]["id"]
        except (KeyError, IndexError, TypeError):
            raise CloudMiss("all_debrid", torrent.get("hash", ""))

        # Steps 2–3: Poll until completionDate is set (truthy = ready).
        # 5 polls x 500ms = 2.5s max. POV uses 3x; 5 gives headroom under load.
        status = {}
        for _ in range(5):
            xbmc.sleep(500)
            result = self.debrid_module.magnet_status(self.magnet_id)
            status = result.get("magnets", {})
            if isinstance(status, dict) and status.get("completionDate"):
                break
        else:
            # Never became ready — genuinely not cached
            self.debrid_module.delete_magnet(self.magnet_id)
            raise CloudMiss("all_debrid", torrent.get("hash", ""))

        # Step 4: Read 'files' and flatten. DO NOT use 'links' — it is
        # populated asynchronously and is often empty right after upload.
        raw_files  = status.get('files', [])
        flat_files = self.debrid_module._flatten_files(raw_files)

        if not flat_files:
            self.debrid_module.delete_magnet(self.magnet_id)
            raise CloudMiss("all_debrid", torrent.get("hash", ""))

        # Normalise to the shape base_resolver expects: path + link + size
        return [
            {
                'path': f.get('n', ''),
                'link': f.get('l', ''),
                'size': f.get('s', 0),
            }
            for f in flat_files
            if f.get('n') and f.get('l')
        ]

    def resolve_stream_url(self, file_info):
        """
        Convert provided source file into a link playable through debrid service
        :param file_info: Normalised information on source file
        :return: streamable link
        """
        return self.debrid_module.resolve_hoster(file_info["link"])

    def _cleanup_other_upload_cached(self, played_magnet_id):
        """
        After successful resolution, delete all other magnets that were uploaded
        during the magnet/upload batch cache check for this scrape session.

        The played magnet is excluded — it is handled by the normal
        addtocloud / smartdelete / autodelete logic above. All other cached
        upload IDs are deleted in background so they don't accumulate.

        Called only on successful resolution (identified_file is not None)
        so that failed attempts do not prematurely clean up IDs that a
        subsequent source attempt might still need.
        """
        _AD_UPLOAD_IDS_KEY = "alldebrid.upload_cache_ids"
        stored = g.get_runtime_setting(_AD_UPLOAD_IDS_KEY)
        if not stored or not isinstance(stored, list):
            return

        # Clear immediately — one cleanup pass per scrape session
        g.clear_runtime_setting(_AD_UPLOAD_IDS_KEY)

        other_ids = [i for i in stored if i != played_magnet_id]
        if other_ids:
            g.log(
                f"AD MagnetUpload: deleting {len(other_ids)} other upload-cached magnets "
                f"after successful play",
                "info",
            )
            self.debrid_module.delete_magnets_background(other_ids)

    def _do_post_processing(self, item_information, torrent, identified_file):
        if identified_file is None:
            # Failed to identify file — always clean up
            self.debrid_module.delete_magnet(self.magnet_id)
        elif g.get_bool_setting("alldebrid.addtocloud"):
            pass  # Keep permanently in cloud
        elif g.get_bool_setting("alldebrid.smartdelete"):
            # Smart delete: defer cleanup to player — delete if fully watched
            from resources.lib.debrid.debrid_utils import store_pending_cleanup
            store_pending_cleanup("all_debrid", self.magnet_id, "delete_magnet")
        else:
            # autodelete=True or unconfigured — remove immediately after resolving
            self.debrid_module.delete_magnet(self.magnet_id)

        # On successful resolution, clean up other upload-cached magnets
        if identified_file is not None:
            self._cleanup_other_upload_cached(self.magnet_id)
