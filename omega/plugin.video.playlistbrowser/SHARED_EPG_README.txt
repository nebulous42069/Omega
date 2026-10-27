Playlist Browser / Diggz TV Guide Lite 2.7.4 - shared EPG cache

Install this ZIP using Kodi's Install from zip file to update the supplied add-on. Alternatively, close Kodi and replace the installed plugin.video.playlistbrowser add-on folder with the folder inside this ZIP. Keep userdata/addon_data/plugin.video.playlistbrowser and your settings.

Sources using the same EPG URL now use one epg_shared_<SHA256>.xml file in the add-on's existing data folder. URL query strings and Kodi URL headers are part of the identity. Only surrounding whitespace is ignored. Different shortened URLs pointing to the same destination are not automatically merged; use the same configured URL to share.

Existing baked_in.json, source IDs, artwork and playlist settings are preserved. New sources require no special settings: set the same EPG URL on each source that should share a guide. Playlist and channel caches remain per source.

MIGRATION
On first access to each EPG, the newest valid existing source XML/gzip cache for its configured sources is moved into the shared scheme, preserving its age. Once a shared copy is available, those old source copies are removed automatically. Cache groups that have not been accessed yet are migrated when opened. Files belonging to removed/unconfigured sources are not automatically deleted because their EPG identity is unknown.

The cache stores a single decompressed XML file per EPG, rather than keeping both XML and gzip copies. Compressed downloads and legacy gzip caches are supported. Existing TTL settings are respected. Separate Kodi invocations coordinate through a cache lock and use atomic file replacement.

Refresh EPG now refreshes the shared guide for every source using it. Refresh All refreshes each distinct EPG once, including EPGs used only by alias/group sources. Failed downloads or malformed responses retain any working cache. The optional background service remains disabled in addon.xml, as in your original ZIP; its code uses shared caching if enabled separately.

VALIDATION
13 automated tests passed, covering cache sharing, distinct URLs, XML/gzip migration and duplicate cleanup, cache age, failed refreshes, forced refreshes, concurrent processes, Source guide loading, and Refresh All deduplication. All Python files parse with Python 3.8 syntax. Kodi runtime testing was not available.

Changed: main.py, service.py, addon.xml. Added: epg_cache.py and this README. Stale bundled __pycache__ files are excluded.
