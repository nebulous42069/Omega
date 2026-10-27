# PVR/EPG Quick Setup 1.4.5 — preset-aware TV launcher

This update is based on the attached plugin.program.pvr.setup.zip, version 1.4.4. It keeps the same add-on ID and normal setup workflow. Install the ZIP as an update.

## One shortcut for every provider

Set your skin's IPTV / Live TV menu custom action to:

    RunScript(plugin.program.pvr.setup,open_tv)

For the EPG guide instead of the channel list, use:

    RunScript(plugin.program.pvr.setup,open_guide)

These commands only open Kodi's PVR windows. They do not apply a preset, clear databases, disable clients or close Kodi. Running the add-on normally without arguments still opens the original setup/preset selector; applying a preset retains its existing reset and restart behavior.

DaddyLive defaults to Channels-USA-. Other bundled presets default to the normal TV list. If the preferred group is unavailable, PVR has not loaded, the playlist is unrecognized or multiple IPTV Simple configurations are enabled, the launcher opens the normal TV/guide window. This does not alter the skin's other TV shortcuts or force the group when TV is opened by a different route.

## Configure a different group

Open this add-on's Settings → TV launcher → Choose default group for a preset. Choose the provider and enter its exact Kodi group name, including capitalization and trailing hyphens. Leave the value blank to use the normal TV list. Cancelling preserves the previous preference. This action changes only navigation preferences; it does not reapply IPTV settings.

The same settings section provides Open TV using selected preset and Open guide using selected preset buttons for testing before changing your skin.

## Existing and future setups

You do not need to rerun Setup DaddyLive just to use the launcher. It compares the current IPTV Simple playlist location with the bundled preset locations. When setup is applied in future, the program also remembers the selected preset in its own profile, outside the IPTV Simple profile that the original setup process purges.

Before using a saved preset choice, the launcher rechecks the current playlist location. If another provider was configured outside this setup program, a stale DaddyLive preference is not used. EPG URL changes alone do not change provider identity. User-defined group preferences are saved per preset in group_overrides.json, and the last applied preset identity is stored in active_preset.json under the setup add-on's profile. The saved identity includes a hash of the source location, not the source URL itself.

The bundled DaddyLive preset's playlist field was corrected to Local path, using special://profile/addon_data/plugin.video.playlistbrowser/daddylive.m3u. Its EPGTalk combined URL is retained. That correction affects a future application of that preset; installing this update does not edit your current IPTV Simple instance. All other preset XMLs are retained from the attachment.

## Validation

Fourteen local tests passed: existing preset detection, stale-choice rejection after source changes, unknown/multiple-instance fallback, disabled-instance handling, per-preset overrides, URL-safe group paths, group availability, channel/guide launch, non-destructive launcher routing, keyboard cancellation, preference persistence and bundled preset/manifest validation. Python/XML/JSON and ZIP contents were also validated. Native Kodi and skin behavior remain to be tested on your device.

## 1.4.6 compatibility fix
Uses Files.GetDirectory to discover the actual Kodi channel group path, including client ID, rather than building an obsolete name-only path. Both open_tv and open_guide use this path. Equivalent translated/special profile playlist paths now match. Group discovery retries for about three seconds. Unknown playlists and ambiguous groups open the ordinary window.

Install this update without reapplying a setup preset. Existing commands remain unchanged. Diagnostic output is written to special://profile/addon_data/plugin.program.pvr.setup/launcher-debug.json each time either command runs, and also to Kodi's log. No playlist URLs or credentials are logged. Native Kodi testing is still required.

## 1.4.7
Adds direct xbmcvfs discovery of PVR group paths when Files.GetDirectory returns no groups. Diagnostics now include Kodi version, directory source, RPC errors and PVR.GetChannelGroups results. Commands and preset settings are unchanged. Eighteen local tests pass; native Kodi testing required.
