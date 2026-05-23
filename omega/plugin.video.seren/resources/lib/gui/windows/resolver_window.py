from . import set_info_properties
from resources.lib.common import tools
from resources.lib.gui.windows.single_item_window import SingleItemWindow
from resources.lib.gui.windows.source_window import _get_quality_color
from resources.lib.modules.globals import g
from resources.lib.modules.resolver import Resolver
from resources.lib.modules.resolver.content_verifier import ContentVerifier


class ResolverWindow(SingleItemWindow):
    """
    Window for Resolver
    """

    def __init__(self, xml_file, location=None, item_information=None, close_callback=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.return_data = None, None
        self.progress = 1
        self.resolver = None
        self.sources = None
        self.pack_select = False
        self.item_information = item_information
        self.close_callback = close_callback

    def onInit(self):
        """
        Callback method from Kodi to trigger background threads to process resolving
        :param test: Used for Unit testing purposes only
        :type test: bool
        :return: None
        :rtype: None
        """
        super().onInit()

    def _resolve_source(self):
        stream_link = None
        release_title = None
        verifier = ContentVerifier(self.item_information, self.sources)
        cloud_miss_count = 0
        cloud_miss_threshold = g.get_int_setting("general.cloudMissThreshold", 3)

        for source in self.sources:
            if self.canceled:
                return None, None
            self._update_window_properties(source)
            try:
                stream_link, release_title = self.resolver.resolve_single_source(
                    source, self.item_information, self.pack_select
                )

                if stream_link is None and source.get('_cloud_miss'):
                    cloud_miss_count += 1
                    g.log(
                        f"Cloud miss {cloud_miss_count}/{cloud_miss_threshold} (visible): "
                        f"{source.get('debrid_provider', '?')} no longer has "
                        f"{source.get('release_title', 'N/A')}",
                        "warning",
                    )
                    if cloud_miss_count >= cloud_miss_threshold:
                        g.set_runtime_setting("cloud_miss_rescrape", "true")
                        break
                    continue

                if stream_link:
                    # Content verification: does the resolved source match expected content?
                    if not verifier.verify(source, release_title):
                        g.log(
                            f"Content verification (visible): Skipping mismatched source — "
                            f"'{release_title or source.get('release_title', 'N/A')}'",
                            "warning",
                        )
                        stream_link = None
                        release_title = None

                        if verifier.should_rescrape():
                            g.set_runtime_setting("content_verify_rescrape", "true")
                            break
                        continue
                    # Save the winning release title so reorder_sources() can
                    # bubble it to the top on the next play for the same series.
                    if release_title:
                        g.set_setting('resolver.last_played_source', release_title)
                    break
            except Exception:
                g.log_stacktrace()
                continue
        if stream_link is None:
            self.return_data = "none", "none"
        else:
            self.return_data = stream_link, release_title

    def get_return_data(self):
        return (None, None) if self.canceled else self.return_data

    def _update_window_properties(self, source):
        debrid_provider = source.get("debrid_provider", "None").replace("_", " ")
        if "size" in source and source["size"] != "Variable":
            self.setProperty("source_size", tools.source_size_display(source["size"]))

        seeds = source.get("seeds", 0)
        if seeds is None or (isinstance(seeds, str) and not seeds.isdigit()):
            seeds = 0
        self.setProperty("source_seeds", str(int(seeds)))

        self.setProperty("release_title", source["release_title"])
        self.setProperty("debrid_provider", debrid_provider)
        # Ensure "(Local Cache)" label for sources from local torrent cache
        provider = source["provider"]
        if source.get("_from_local_cache") and "(Local Cache)" not in provider:
            provider = f"{provider} (Local Cache)"
        self.setProperty("source_provider", provider)
        self.setProperty("source_resolution", source["quality"])
        self.setProperty("source_resolution_color", _get_quality_color(source["quality"]))

        # Inject source type tags (CACHED, SEASON, SHOW) into info set for display
        display_info = set(source.get("info", set()))
        if source.get("type") == "torrent" and source.get("debrid_provider"):
            display_info.add("CACHED")
        package = source.get("package", "single")
        if package == "season":
            display_info.add("SEASON")
        elif package == "show":
            display_info.add("SHOW")

        set_info_properties(display_info, self)
        self.setProperty("source_type", source["type"])

        provider_imports = source.get("provider_imports", [])
        source_icon = self.provider_class.get_icon(provider_imports)
        if source_icon is not None:
            self.setProperty("source.icon", source_icon)

    def doModal(
        self,
        sources=None,
        pack_select=False,
    ):
        """
        Opens window in an intractable mode and runs background scripts
        :param sources: List of sources to attempt to resolve
        :type sources: list
        :param pack_select: Set to True to enable manual file selection
        :type pack_select: bool
        :return: Stream link
        :rtype: str
        """
        self.sources = sources or []
        self.pack_select = pack_select

        if not self.sources:
            return None, None

        self.resolver = Resolver()

        self._update_window_properties(self.sources[0])
        self._resolve_source()

        super().doModal()

    def close(self):
        super().close()
        if self.close_callback:
            self.close_callback()
