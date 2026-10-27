# Playlist Browser 2.8.0 — integrated DaddyLive

Built from the attached plugin.video.playlistbrowser(5).zip (2.7.4), incorporating the standalone exporter 0.1.6. Install as an update to the same plugin.video.playlistbrowser add-on ID. The displayed add-on name remains Diggz TV Guide Lite. This is a local test build, not a published upstream release.

## Setup

1. Install plugin.video.playlistbrowser-2.8.0.zip over Playlist Browser and restart Kodi.
2. Open Playlist Browser settings → DaddyLive. Set your preferred source URL/options if needed. Defaults are automatic selection enabled, logos enabled and relay port 8769. Existing standalone add-on preferences are not imported automatically.
3. Run Check local relay, then Create / refresh M3U playlist from that settings section. The same actions are available in the DaddyLive tools menu.
4. Open the existing DL source (source_id 117), then Channel Groups. Export updates its raw and parsed channel caches automatically. The original source name, numeric ID and configured EPG URL are retained.
5. After testing the integrated DL source, the separate plugin.video.dlhd.export add-on can be disabled or uninstalled. No dependency on it remains.

The output defaults to special://profile/addon_data/plugin.video.playlistbrowser/daddylive.m3u. The supplied baked_in.json DL entry now uses that location. A custom output folder in DaddyLive settings is also respected by that source automatically. Other applications using the previous standalone path must be changed to the new path. Existing favorites that store old 127.0.0.1:8768 stream URLs should be re-added from the integrated DL source; those old saved URLs are not rewritten.

## Settings and tools

The DaddyLive settings category contains source URL, relay port, automatic/manual player, logo lookup and output-folder settings, plus Browse channels and IDs, Create / refresh M3U playlist, Test channel playback by ID, Check local relay, View debugging log and Export debugging log actions. Port and enable changes need a Kodi restart. The top-level DaddyLive tools menu provides the same tools.

Playlist Browser's own background service runs the local relay on 127.0.0.1:8769, avoiding a clash with the standalone add-on on 8768. Although the main output is an M3U file, its stable stream URLs need this integrated relay for on-demand resolution, token renewal and image-wrapped video decoding. Kodi and Playlist Browser must remain running during playback. No external server or Node.js is required. The original service.py file and its existing manifest comment are retained; the new dlhd_service.py service runs only the integrated relay.

## Preserved exporter features

Channels-USA-/Channels-UK-/Sports-USA-/Sports-UK- and equivalent country groups; clean names without trailing IDs; numeric playback IDs; automatic player selection with availability probes; PNG/WebP segment decoding; primary/backup logo catalogs; parent-brand logo fallbacks; custom logo overrides; bounded debug logs.

Diagnostics and logo caches now live under special://profile/addon_data/plugin.video.playlistbrowser/dlhd/. The debug log is debug.log; logo matching details are logo-matches.json; manual overrides can be placed in channel_logos.json in this folder. Standalone diagnostics and overrides are not copied automatically.

Logo references come from iptv-org/api (https://github.com/iptv-org/api) and the backup tv-logo/tv-logos catalog (https://github.com/tv-logo/tv-logos). Image files are not bundled. Artwork belongs to its respective owners; follow the source projects' terms. Stream resolver algorithms credit Lunatic16 and sharoon7171/daddylive-stream-resolver; see dlhd/LICENSE.txt. The underlying Playlist Browser files and attribution are retained from the user's attachment.

## EPG and limits

No XMLTV programme guide is generated. The supplied source list's EPG settings are retained, but actual channel/schedule matching depends on those guide sources. All earlier resolver limitations remain: no guarantee of codec compatibility or uninterrupted streams, some embed formats remain unsupported, and channel/brand/logo classification can need correction. The relay and streams are local to this Kodi installation.

Thirty-two local tests passed, covering extraction, HLS proxying, automatic source selection, logs, grouping, logo matching, integrated settings routes, source registration, own-profile output, immediate channel cache updates and relay startup/shutdown. Python/XML/JSON parsing and ZIP packaging were also checked. Native Kodi UI, OS-matrix compatibility and live playback of this integrated build have not been verified.


## Version 2.8.1 — automatic M3U regeneration

DaddyLive now regenerates its M3U every 48 hours by default. Configure Automatically regenerate DaddyLive M3U and DaddyLive M3U refresh interval (hours) under Settings → DaddyLive. This scheduler is distinct from the existing Global Options playlist-cache refresh.

The integrated service checks once per minute while Kodi is running. When overdue at startup, the first check starts a background update. A missing output file also triggers generation. On upgrade, an existing M3U without refresh state uses its file modification time to avoid unnecessary immediate regeneration. A successful manual export resets the same timer. No exact wall-clock time is promised: the schedule is elapsed hours since the last successful export, not a fixed calendar time.

Scheduled and manual updates use the same channel parsing, grouping, name cleanup, logo matching and DL cache-update code. The complete M3U is staged before replacing the previous file. Network failures, empty channel lists and failed staging leave the old M3U intact. Failures are logged and retried after an hour. Manual/background jobs coordinate with an export lock so they do not overwrite each other concurrently. Local output paths use atomic replacement; network/VFS locations depend on their provider's rename support, and unsupported replacement reports an error rather than deleting the old file.

refresh-state.json in the add-on profile's dlhd folder records successful update time and retry state. The debug log records scheduled attempts and failures. The relay remains responsive while a background refresh runs. When Kodi is closed/asleep, no scheduled work runs; an overdue update runs after Kodi resumes/restarts. Stream token renewal continues to happen independently during playback.

Forty local tests passed, including the 48-hour threshold, disabled scheduling, existing-file timestamps, failed fetch preservation/backoff, successful manual export timer/cache updates, empty-list rejection, concurrent-job protection and invalid state recovery. Native Kodi UI/background scheduling still needs device testing. Install the update and restart Kodi to activate the new scheduler; no manual M3U export is required unless you want an immediate update.


## Version 2.8.2 — prefer logos designed for dark backgrounds

The tv-logo/tv-logos catalog is now preferred over iptv-org. Lookup tries its exact/alias match and supported parent-brand fallback first, then uses iptv-org if no preferred match is found. Similar-name matches also retain the preferred catalog URL when both sources offer the same candidate. A preferred parent-brand image may intentionally replace a more specific iptv-org image so the darker source does not override the user's chosen catalog. Manual channel_logos.json overrides retain highest priority.

Existing catalog caches can be reused; no seven-day wait or cache deletion is needed for the priority change. Install the update, restart Kodi and run Create / refresh M3U playlist once to replace old logo URLs immediately. The integrated DL channel cache updates automatically after export. Normal 48-hour refresh remains enabled. Some logos may remain absent or use iptv-org when the preferred catalog has no suitable match; individual image availability is not verified during export.

Forty-two local tests passed, including preferred-source exact-match priority, preferred brand priority over fallback-specific artwork, source fallback, and all existing refresh/export/stream tests. Native Kodi display still needs device verification.


## Version 2.8.3 — EPGTalk combined guide matching for USA and UK

Match USA/UK channels to EPGTalk combined guide is enabled by default in Settings → DaddyLive. Create / refresh M3U playlist now assigns matching EPGTalk XMLTV channel IDs to tvg-id, adds the guide's tvg-name and advertises the combined XMLTV URL in the M3U header. Numeric DaddyLive IDs remain in stream URLs, so playback routing does not change. Other countries and unmatched channels retain their numeric tvg-id. Groups, clean display names, dark-background logo preference and automatic 48-hour refresh remain.

Combined guide: https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/guide.xml.gz

For reliable country filtering, export downloads the combined guide and USA/UK lite channel catalogs. The lite catalogs supply country membership, not programme data; every exported mapped ID comes from the combined guide. Gracenote station IDs reconcile provider/channel-number differences. Explicit UK prefixes and unambiguous UK brands handle channels absent from the lite lineup. The mapping catalog is cached for 24 hours. If downloading fails, older mapping data can be reused. With no usable mapping cache, export fails without replacing the existing M3U; disable EPG matching if you intentionally need an export without guide metadata.

Matching uses exact normalized names and aliases, with country/feed safeguards. It does not use logo-style parent-brand fallback or fuzzy network substitution. SD/HD versions of the same guide feed can share a schedule mapping. When an unspecified US channel has a matching explicit East feed, that feed is a documented default; a source name explicitly saying West/Pacific is kept distinct. Generic local-network names and ambiguous region/feed matches remain unmapped. This is best-effort mapping and does not guarantee the live stream matches the selected regional schedule.

The supplied 899-entry playlist yielded 127 mappings among 178 channels classified USA/UK: 84 USA and 43 UK. Fifty-five local tests passed. The counts reflect the downloaded guide snapshot and automatic matching rules, not a promise that every channel will have listings. The original stream IDs and URLs were checked to remain numeric and unchanged.

View EPG matching report is available in the DaddyLive tools menu and settings. The report is stored at special://profile/addon_data/plugin.video.playlistbrowser/dlhd/epg-matches.json. It lists DaddyLive ID/name, country, matched XMLTV ID/name and matching method, including ambiguous/unmatched entries.

Manual corrections can be stored in dlhd/epg-overrides.json within the Playlist Browser profile: a JSON object mapping DaddyLive IDs to valid EPGTalk IDs, for example {"44":"the.actual.xmltv.id"}. Use IDs from the combined guide; country must agree with the source channel's inferred country. A blank string disables a mapping. Regenerate the M3U after editing overrides.

### Activate in Kodi

1. Install 2.8.3, restart Kodi and run Create / refresh M3U playlist once. The first mapping download may take longer than previous exports.
2. Playlist Browser's integrated DL source automatically uses EPGTalk combined when mapping is enabled. Refresh that source's EPG if its guide view still shows old cached data.
3. IPTV Simple Client is configured separately. Set its M3U location to Local path and choose special://profile/addon_data/plugin.video.playlistbrowser/daddylive.m3u (or your custom folder).
4. Set IPTV Simple's EPG location to Remote path and its XMLTV URL to https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/guide.xml.gz. An older explicit EPG URL overrides the M3U header and must be changed.
5. Reload IPTV Simple Client/Kodi so the new playlist IDs and EPG are loaded. If Kodi retains old programme data, clear its guide data and reload after confirming the two source settings.

This version does not generate a local XMLTV file or edit IPTV Simple Client's instance settings. Programme data continues to come from EPGTalk. Credit and source: https://github.com/acidjesuz/EPGTalk. Native Kodi EPG rendering remains to be verified on the user's device.


## Version 2.8.4 — USA local-network logo fallback

Logo matching recognizes local variants of ABC, CBS, CW, FOX and NBC, including spaced/joined NY names, New York, Philly/Philadelphia, PIX numbers and selected affiliate call signs. NVCNY is treated as an NBCNY logo-lookup typo. These aliases affect logos only; they do not alter channel names, playback, grouping or XMLTV schedule matching.

An exact affiliate match from either logo catalog wins over a generic local-network fallback. When there is no exact affiliate image, the matcher tries the generic network image in the preferred tv-logo catalog, then iptv-org. CBS's descriptive cbs-logo-white artwork is recognized as a generic CBS logo and preferred over iptv-org's generic logo. CW can use CW or The CW artwork. These are explicit USA-only rules, not unrestricted substring matching across countries.

Fox Weather Channel can match Fox Weather artwork, but it does not fall back to the unrelated FOX entertainment logo if no weather image is available. CBS Sports and other specialty channels do not silently receive a generic CBS affiliate logo. Existing logo overrides still take priority.

Install, restart Kodi and run Create / refresh M3U playlist. No logo catalog cache deletion is needed. The integrated DL channel cache updates during export. Kodi may retain an old cached image if a URL is unchanged; most newly assigned logos have different URLs.

Fifty-nine local tests passed, including all requested local-name examples, exact-affiliate priority, country/specialty safeguards and CBS white-artwork preference. Device display still needs verification.


## Version 2.8.5 — bundled local logos and custom image overrides

The add-on includes local PNG artwork and a manifest for all 899 entries in the supplied playlist. 643 channel entries use matched artwork downloaded from the existing preferred/fallback catalogs (608 unique images, with some shared network logos). The remaining 256 use readable channel-name tiles. Tiles are generic labels, not official broadcaster logos. A generic TV tile is included for future channels with neither a local image nor an online match. The bundle is approximately 14 MB before ZIP compression.

Bundled image files were decoded, resized to fit a 384×216 transparent canvas and saved as PNGs at build time. All PNG files were revalidated, and all 899 playlist entries were checked to resolve to existing local images with online lookup disabled. This avoids dependency on image hosts for the bundled entries. No imaging libraries are required on the Kodi device. Artwork references and source attribution are retained in resources/logos/manifest.json; original artwork belongs to its respective owners. Sources: https://github.com/tv-logo/tv-logos and https://github.com/iptv-org/api. The backup repository's personal-use/attribution terms apply to its artwork; this is a personal test build, not a public upstream release.

### Add a missing/replacement image

Find the numeric DaddyLive ID using Browse channels and IDs. It remains the number in /stream/44.m3u8, even when the M3U tvg-id is an EPGTalk identifier.

Preferred location (survives add-on updates):

    special://profile/addon_data/plugin.video.playlistbrowser/dlhd/logos/44.png

The folder is created during export. PNG, JPG/JPEG and WebP extensions are supported. You may also place 44.png in the installed add-on's resources/logos/custom/ folder, but an add-on update can overwrite installed files. Profile-local files take priority over installed custom files and bundled assets. An explicit channel_logos.json override still takes final priority and can now reference an absolute local file or special:// path as well as a web URL.

After adding a file, run Create / refresh M3U playlist. The image reference is written into tvg-logo and the integrated DL channel cache updates. If reusing exactly the same file path for a changed image, Kodi may still have an older texture cached.

### Selection and settings

Bundled images are used only when both the numeric ID and normalized channel name agree with the bundle manifest, preventing an old logo from being reused when an ID is reassigned. Bundled name tiles are deliberately preferred to broken remote matches from the earlier snapshot. Add a custom image to replace one. New/unbundled channels can still use online lookup, and the setting is now labeled Look up online logos for channels missing from local bundle. Turning online lookup off retains bundled and custom images.

The generated M3U contains paths resolved for the current Kodi installation; it is intended for that same device, as are its loopback playback URLs. In Playlist Browser keep Use logos from M3U/EPG if available enabled. In IPTV Simple Client choose Channel logos from XMLTV → Prefer M3U so guide-provided icons do not override bundled artwork. No IPTV Simple settings are changed automatically by installing this ZIP.

Install 2.8.5, restart Kodi and create/refresh the M3U once. Reload IPTV Simple if using its channel list. EPG matching, the 48-hour refresh and playback are retained. Sixty-seven local tests passed, including local/custom priority, offline use, ID/name mismatch safeguards, missing-file fallback and local M3U reference serialization. Native Kodi image display still needs device verification.

## 2.8.6 relay diagnostics and recovery
Startup status is written before importing relay modules. Import/bind failures record exception type, errno and source locations, and retry after 15 seconds. Disabled relay status is recorded. Local UI health probes bypass proxies with a three-second timeout. Debug viewing/export no longer parses relay port/player settings and can generate a report even when no service log exists. Logging setup replaces old rotating handlers during retries. Existing stream URLs, grouping, EPG and logos are unchanged. Four focused recovery tests pass; device verification required.

## 2.8.7 single service bootstrap
The supplied 2.8.5 archive and 2.8.6 both declared two xbmc.service extensions. Replace them with one service_entry.py bootstrap that runs playlist-cache refresh on a background thread and the relay on the service thread. A cache worker import failure cannot prevent relay startup. If the relay is disabled, the bootstrap keeps the cache worker alive until Kodi aborts. Existing playlist, EPG, logo and relay settings are preserved. Seven focused recovery/bootstrap tests pass. Restart Kodi after installation; device confirmation required.
