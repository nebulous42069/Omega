# ReAuthorize 1.4.5 — audit test build

Built October 22, 2026 from the user's ReAuthorize 1.4.4 source. This is an unofficial review build, not an upstream release. Keep a backup of the existing addon and its profile. Use a separate Kodi profile first. Restart Kodi after installing or changing a shared Trakt/Simkl application identity, because receiving plugins may retain imported keys in memory.

## Installation

Install this ZIP through Kodi's Install from zip file. It contains the single script.module.reauthorize addon directory. The original script.module.reauthorize-core dependency remains required (minimum 1.4.0); this package does not replace core or any receiving plugin. No user profile or personal credential file is included.

## Included changes

- Preserve existing metadata credentials when a source field is blank; explicit wipes remain supported.
- Compare complete credential bundles for older debrid/Easynews/Linksnappy writers, repairing changed usernames/passwords and partial credentials.
- Verify destination setting writes through fresh Kodi handles; collect failures that older adapters catch internally and return them through the main sync runner.
- Fix Umbrella FilePursuit to use filepursuittoken; synchronize that importer mapping.
- Fix Seren Trakt client setting overrides, Umbrella's issuing-client marker and TMDb Helper's created_at/expires_in calculation.
- Add verified Seren TorBox/OffCloud/MDBList API-key and ResolveURL TorBox mappings; explicitly enable ResolveURL service destinations on explicit sync.
- Add Prism TMDb metadata key and Moria Trakt setting overrides; use explicit client settings for Homelander/Quicksilver/Absolution/Chain Reaction instead of relying on stale fallback secrets.
- Set The Archives' Trakt application constants through a checked, atomic, named-assignment patch, and remove unused alias setting writes. Preserve the original constant text in comments.
- Remove the obsolete POV metadata fields, Otaku's invalid token write to its simkl.login action, and The Archives username-as-account-ID transfer.
- Stop presenting EasyDebrid/Debrid-Link no-op paths and AudioDB-only sends as a successful verified send. They require further compatible adapters or receiving-addon changes.
- Fix RD's truthy failure tuple, bounded retry and authentication timeouts; preserve FilePursuit settings on cancel; hide Easynews password input; fix Premiumize's uninitialized response error.
- Match recipient credentials before removing them on the common service revoke/remove actions; retain independently authorized values. Include SQLite destinations and Realizer's token JSON. Clear TorBox/EasyDebrid duplicate key fields.
- Scrub Crew's Simkl recovery copies on Simkl sign-out; stop if Crew's Trakt application-key setup fails; allow marked key updates; escape XML backup values; include legacy settings*.bak recovery copies.
- Preserve Last.fm submission preferences and remove legacy matching session-key sign-ins.
- Capture YouTube issuing client keys with token capture and prefer an existing live sign-in's key bundle before a push. Partial client credentials are not treated as a complete bundle.
- Redact known stored credential values in ReAuthorize's logger and correct its Kodi logging argument formatting.
- Allow ordinary setting-based adapters to initialize a previously missing profile settings.xml through Kodi rather than silently skip it; keep database/Realizer JSON prerequisites.

## Offline validation

22 regression tests passed. They exercise blank metadata preservation and explicit wipes, complete credential comparison, password/username changes, consumer key names, new targets, shared-account-only removal, expiry math, source-key failure and rotation, XML escaping, unsupported action fields, FilePursuit cancellation, internal failure reporting and YouTube client-bundle capture. All packaged Python sources parse, and addon.xml parses. Run: python tests/test_audit_regressions.py from the installed addon source directory (or provide its full path). The tests install in-process Kodi stubs and never contact providers.

## Important unresolved scope

This is NOT a claim that every service/addon pair works or that every audit finding is closed. There has been no real Kodi execution, device authorization, refresh, playback, or multi-process concurrency test. Offline stubs cannot establish Kodi settings-cache timing or live provider acceptance.

1. Shared Trakt/MDBList/RD refresh ownership across independent addons and Kodi installations remains an architectural limitation. The patch repairs mappings and state but does not create a distributed refresh coordinator.
2. ResolveURL 5.1.211 can erase RD authorization on temporary refresh errors and logs token-exchange secrets. Those defects are in ResolveURL and are not fixed by this ReAuthorize-only ZIP.
3. Existing backup encryption and remote-server protocol are unchanged. Migrating to authenticated encryption needs a coordinated compatibility design and restore tests; this package must not be described as cryptographically hardened.
4. ResolveURL Linksnappy requires a cookie login lifecycle. This build does not implement it. Debrid-Link's manually supplied key has not been proven interchangeable with Seren's OAuth token. AudioDB has no verified destination. Otaku requires its own correct Simkl credential/identity adapter; simkl.login is an action. EasyDebrid is absent from supplied POV and disabled in Umbrella.
5. The source-patching integrations still require writable addon files and a restart when code is already loaded. Other unsupported source layouts are refused/reported rather than guessed. Existing legacy integrations outside the supplied versions remain unverified.
6. Not every older manual button has been rewritten around a structured per-addon result model. The main runner propagates collected settings failures, but original per-addon UI/diagnostic paths may still contain broad success messages. An install-based UI pass is required before a production release.
7. Ordinary removal matches stored credential values. This preserves independent authorizations, but does not revoke a provider-issued credential remotely unless the original service handler already does so. Missing/corrupt recipient databases, recovery files, or independently changed keys may require explicit cleanup.
8. The full historical audit is included as AUDIT_ORIGINAL.md. It describes original sources and contains superseded intermediate scope statements. This file documents what this build actually changes and what remains open.

Do not redistribute this as an official, fully validated ReAuthorize release. No receiving plugin archive has been modified or bundled.
